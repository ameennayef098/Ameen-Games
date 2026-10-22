#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revert tools/fix_bare_alef.py.

fix_bare_alef.py rewrote 325 letters answers whose first character was a bare
alef (U+0627) to أ (U+0623). That is a REGRESSION in the user-visible text:

  * templates/game_letters.html line 374 renders the answer verbatim
    (`correctAnswer.textContent = q.answer`), so players see it.
  * 323 of the 325 words are ألف الوصل (الفاتحة، الفهد، الفاتيكان ...) and 2
    are ابن النفيس / انكسار الضوء. In standard Arabic all of them are written
    WITHOUT a hamza on the article's alef. The rewrite produced ألفاتحة /
    ألفهد / ألفاتيكان / أبن النفيس / أنكسار الضوء -- misspellings.
  * The runtime is unaffected either way: firstLetterOf() maps every alef
    variant to أ before the board lookup (proven: 0 grouping drift), and
    server.py validate_question() compares norm_ar(letter) with
    first_letter_of(answer) where norm_ar maps both ا and أ to ا.

So the stored text is left exactly as it was. This script restores the original
first character for precisely the ids that fix_bare_alef.py touched, and never
touches records the background generator added since.
"""
import io
import json
import os
import shutil
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(BASE, 'data', 'questions', 'all.json')
BAK = os.path.join(BASE, 'data', 'questions',
                   'all.json.bak-barealef-20261021-135640')
REPORTS = os.path.join(BASE, 'data', 'reports')

BARE = '\u0627'
HAMZA = '\u0623'


def main():
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    bak2 = os.path.join(REPORTS, 'all.json.pre-revert-%s' % stamp)

    before = json.load(io.open(BAK, encoding='utf-8'))
    live = json.load(io.open(BANK, encoding='utf-8'))
    bmap = {q.get('id'): q for q in before}

    reverted = 0
    for q in live:
        b = bmap.get(q.get('id'))
        if not b:
            continue                       # record added after the backup
        ba, ca = str(b.get('answer', '')), str(q.get('answer', ''))
        if ba[:1] == BARE and ca == HAMZA + ba[1:]:
            q['answer'] = ba
            reverted += 1

    shutil.copy2(BANK, bak2)
    tmp = BANK + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(live, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BANK)

    print('reverted answers: %d' % reverted)
    print('backup of pre-revert state: %s' % bak2)
    print('live records: %d' % len(live))


if __name__ == '__main__':
    main()
