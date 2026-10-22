#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove duplicate questions from the bank (safe, deterministic).

Duplicates are keyed exactly as the server keys them:
`game + '|' + normalised question text` (server.py :: q_key), so a duplicate here
is a duplicate the app would also consider one.

Keeps the FIRST occurrence, drops later ones. Writes atomically via a temp file
and makes a timestamped backup first.

    python tools/dedupe_bank.py --dry-run
    python tools/dedupe_bank.py
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QFILE = os.path.join(BASE, 'data', 'questions', 'all.json')


def norm_ar(t):
    """Same normalisation the server applies before comparing."""
    s = str(t or '')
    s = re.sub(r'[ً-ْـ]', '', s)              # diacritics + tatweel
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٱ', 'ا')
    s = s.replace('ة', 'ه').replace('ى', 'ي')
    return re.sub(r'\s+', '', s)


def q_key(q):
    return str(q.get('game', '')) + '|' + norm_ar(q.get('question', ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    with io.open(QFILE, encoding='utf-8') as f:
        data = json.load(f)

    seen = {}
    kept, dropped = [], []
    for q in data:
        k = q_key(q)
        if k in seen:
            dropped.append(q)
        else:
            seen[k] = q
            kept.append(q)

    print('total: %d  unique: %d  duplicates: %d' % (len(data), len(kept), len(dropped)))
    if dropped:
        by_game = {}
        for q in dropped:
            by_game[q.get('game')] = by_game.get(q.get('game'), 0) + 1
        print('duplicates by game: %s' % by_game)
        for q in dropped[:10]:
            print('  - [%s] %s' % (q.get('game'), str(q.get('question'))[:70]))

    if a.dry_run or not dropped:
        return 0

    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = QFILE + '.bak-dedupe-' + stamp
    shutil.copy2(QFILE, backup)
    print('backup: %s' % backup)

    tmp = QFILE + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
    os.replace(tmp, QFILE)
    print('wrote %d questions (removed %d duplicates)' % (len(kept), len(dropped)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
