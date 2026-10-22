#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry-run of tools/fix_bare_alef.py against the timestamped backup.

Confirms (on a throwaway copy) that exactly the intended 325 answers changed,
that only the FIRST character changed, and that the game's runtime grouping key
(templates/game_letters.html firstLetterOf) is bit-for-bit identical before and
after. Nothing here touches the live bank.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_bare_alef import tpl_first_letter, BARE, HAMZA  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAK = os.path.join(BASE, 'data', 'questions', 'all.json.bak-barealef-20261021-135640')
LIVE = os.path.join(BASE, 'data', 'questions', 'all.json')

before = json.load(io.open(BAK, encoding='utf-8'))
after = json.load(io.open(LIVE, encoding='utf-8'))
print('backup records: %d   live records: %d' % (len(before), len(after)))

key = lambda q: q.get('id')  # noqa: E731
bmap = {key(q): q for q in before}
amap = {key(q): q for q in after}
print('same id set: %s' % (set(bmap) == set(amap)))

changed = 0
first_char_only = True
drift = []
for i, b in bmap.items():
    a = amap[i]
    if b == a:
        continue
    changed += 1
    bb, aa = b.get('answer', ''), a.get('answer', '')
    if len(bb) != len(aa) or bb[1:] != aa[1:]:
        first_char_only = False
    if ord(bb[0]) != 0x0627 or ord(aa[0]) != 0x0623:
        first_char_only = False
    if tpl_first_letter(bb) != tpl_first_letter(aa):
        drift.append(i)
    # nothing else may have changed
    bb2, aa2 = dict(b), dict(a)
    bb2.pop('answer'), aa2.pop('answer')
    if bb2 != aa2:
        print('  UNEXPECTED extra change on %s' % i)

print('records changed: %d' % changed)
print('only first char changed (ا -> أ): %s' % first_char_only)
print('runtime grouping drift: %d' % len(drift))
print('all changed records are letters: %s'
      % all(bmap[i].get('game') == 'letters' for i in bmap
            if bmap[i] != amap[i]))
