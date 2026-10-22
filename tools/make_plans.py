#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the wave plans for the 20,000-question target.

Three buckets, as requested:
  (a) NEW categories for س.ج          -> 24 new categories
  (b) EXISTING categories for س.ج     -> top the 35 current ones up
  (c) حروف مع أمين                    -> the 25 letters that are on the board

Existing counts are read at plan time so `need` is exact, and the shards are
disjoint (no two shards touch the same category/letter) so nothing is generated
twice.

    python tools/make_plans.py
"""
import json
import os
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))

import bulk_gen as B  # noqa: E402
import fill_categories as FC  # noqa: E402

WAVES = os.path.join(BASE, 'data', 'waves')
os.makedirs(WAVES, exist_ok=True)

# The 25 letters that actually appear on the board (LETTERS_25 in
# game_letters.html). ذ ض ظ are NOT on the board, so questions for them can
# never be reached by a player — the wave targets the playable letters only.
BOARD_LETTERS = ['أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ر', 'ز', 'س', 'ش',
                 'ص', 'ط', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي']

TARGET_NEW_CATS = 24
TARGET_EXISTING = 280          # questions per existing category
TARGET_LETTER = 170            # questions per board letter
NEW_CAT_TARGET = 270           # questions per brand-new category

DIFFS = ['easy', 'medium', 'hard']


def split(n, parts):
    """Distribute n as evenly as possible over `parts`, largest first."""
    base = n // len(parts)
    rem = n - base * len(parts)
    out = []
    for i in range(len(parts)):
        out.append(base + (1 if i < rem else 0))
    return out


def write_plan(name, game, targets):
    path = os.path.join(WAVES, name + '.json')
    plan = {'game': game, 'targets': [list(t) for t in targets],
            'created': B._ts()}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    return path, sum(t[2] for t in targets)


def main():
    cats = json.load(open(B.CATFILE, encoding='utf-8'))
    quiz = [q for q in B.read_all() if q.get('game') == 'quiz']
    letters = [q for q in B.read_all() if q.get('game') == 'letters']

    # current per (category, difficulty)
    qcount = defaultdict(Counter)
    for q in quiz:
        qcount[q.get('category_id')][q.get('difficulty')] += 1
    # current per (letter, difficulty)
    lcount = defaultdict(Counter)
    for q in letters:
        lcount[q.get('letter')][q.get('difficulty')] += 1

    print('current: %d quiz, %d letters, %d categories'
          % (len(quiz), len(letters), len(cats)))
    print()

    # ---------------------------------------------------- (a) new categories
    specs = FC.new_cat_specs(TARGET_NEW_CATS)
    added = FC.create_categories(specs)
    print('(a) created %d new categories: %s' % (len(added), ', '.join(added)))
    new_ids = [s[0] for s in specs]
    new_names = {s[0]: s[1] for s in specs}

    # ---------------------------------------------------- targets
    targets_new = []
    for cid in new_ids:
        per = split(NEW_CAT_TARGET, DIFFS)
        for d, n in zip(DIFFS, per):
            if n:
                targets_new.append((cid, d, n))

    targets_ext = []
    ext_cats = [c for c in cats if c['id'] not in set(new_ids)]
    for c in ext_cats:
        per = split(TARGET_EXISTING, DIFFS)
        for d, n in zip(DIFFS, per):
            have = qcount[c['id']].get(d, 0)
            if have < n:
                targets_ext.append((c['id'], d, n - have))

    targets_letters = []
    for letter in BOARD_LETTERS:
        per = split(TARGET_LETTER, DIFFS)
        for d, n in zip(DIFFS, per):
            have = lcount[letter].get(d, 0)
            if have < n:
                targets_letters.append((letter, d, n - have))

    # ---------------------------------------------------- disjoint shards
    half = len(targets_ext) // 2
    ext_a, ext_b = targets_ext[:half], targets_ext[half:]
    nhalf = len(targets_new) // 2
    new_a, new_b = targets_new[:nhalf], targets_new[nhalf:]
    lhalf = len(targets_letters) // 2
    let_a, let_b = targets_letters[:lhalf], targets_letters[lhalf:]

    plans = [
        ('quiz-new-a', 'quiz', new_a),
        ('quiz-new-b', 'quiz', new_b),
        ('quiz-ext-a', 'quiz', ext_a),
        ('quiz-ext-b', 'quiz', ext_b),
        ('letters-a', 'letters', let_a),
        ('letters-b', 'letters', let_b),
    ]

    total = 0
    for name, game, tg in plans:
        path, n = write_plan(name, game, tg)
        total += n
        print('%-12s %-8s %4d targets  -> %5d questions'
              % (name, game, len(tg), n))
    print()
    print('TOTAL planned: %d new questions' % total)
    print('projected grand total: %d' % (len(quiz) + len(letters) + total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
