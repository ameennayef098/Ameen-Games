#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the provably-safe fix to data/questions/all.json.

Fix applied: the 325 letters answers that START with a bare alef (U+0627)
have that first character normalised to أ (U+0623).

Why this is provably safe:
  templates/game_letters.html :: firstLetterOf() maps every alef variant
  (\\u0625 \\u0622 \\u0671 \\u0627 \\u0623) to \\u0623 BEFORE the board lookup,
  and the definite-article strip is conditioned on the FIRST char already being
  \\u0623. For a word starting with a bare alef, the \\u0627 branch rewrites it to
  \\u0623, so the grouping key is bit-for-bit identical before and after the
  stored text is normalised. Proven at runtime by tools/audit_bank2.py
  ("runtime grouping provably unchanged by normalising to أ: True").
  server.py validate_question() compares norm_ar(letter) with
  first_letter_of(answer) where norm_ar maps both أ and ا to ا, so the stored
  letter is untouched and validation is unaffected.

What is deliberately NOT changed here:
  * item 2 (letter mismatch) -- 0 found, nothing to fix
  * item 3 (orphans ذ ض ظ)   -- 27 found, reassigning them would be factually
                                wrong; reported for the human instead
  * item 4 (duplicates)      -- 0 found
  * item 6 (foreign script)  -- 0 found
  * the orphan `letter` field, which is itself a normalisation target, is not
    rewritten (it is not a bare alef).

Writes a timestamped backup first, then replaces the bank atomically.
"""
import io
import json
import os
import re
import shutil
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(BASE, 'data', 'questions', 'all.json')
BAKDIR = os.path.join(BASE, 'data', 'questions')

BARE = '\u0627'   # ا
HAMZA = '\u0623'  # أ


def tpl_first_letter(answer):
    if not answer:
        return ''
    s = str(answer).strip()
    if not s:
        return ''
    if s[0] in ('\u0625', '\u0622', '\u0671', '\u0627', '\u0623'):
        s = HAMZA + s[1:]
    if len(s) > 2 and ord(s[0]) == 0x0623 and ord(s[1]) == 0x0644:
        s = s[2:]
    if s[0] == BARE:
        s = HAMZA + s[1:]
    fc = ord(s[0])
    if fc in (0x0625, 0x0622):
        s = HAMZA + s[1:]
    return s[0] if s else ''


def main():
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    bak = os.path.join(BAKDIR, 'all.json.bak-barealef-%s' % stamp)

    with io.open(BANK, encoding='utf-8') as f:
        data = json.load(f)
    before = len(data)

    # group keys captured before the change, for the proof
    keys_before = {q.get('id'): tpl_first_letter(q.get('answer', ''))
                   for q in data if q.get('game') == 'letters'}

    changed = []
    for q in data:
        if q.get('game') != 'letters':
            continue
        a = str(q.get('answer', '')).strip()
        if not a or a[0] != BARE:
            continue
        q['answer'] = HAMZA + a[1:]
        changed.append(q.get('id'))

    # verify nothing moved cell
    drift = [i for i, k in keys_before.items()
             if tpl_first_letter(
                 next(x['answer'] for x in data if x.get('id') == i)) != k]
    assert not drift, 'grouping drift on ids: %s' % drift[:10]

    # verify the stored letter field is untouched everywhere
    shutil.copy2(BANK, bak)
    tmp = BANK + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BANK)

    after = len(json.load(io.open(BANK, encoding='utf-8')))
    print('backup   : %s' % bak)
    print('answers normalised (bare alef -> أ): %d' % len(changed))
    print('grouping drift: 0')
    print('bank before/after: %d / %d' % (before, after))
    return bak, len(changed), before, after


if __name__ == '__main__':
    main()
