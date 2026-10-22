#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill quiz categories that hold fewer than TARGET_TOTAL questions.

Uses the same NVIDIA call + validation as tools/bulk_gen.py, but works to a
FINAL per-category count rather than a per-difficulty target, and writes a
per-(category, difficulty) target so every difficulty band keeps at least
MIN_PER_DIFF questions (the س.ج board draws 2 per band per match).

Reuses bulk_gen's helpers so prompts/validation stay identical.
"""
import importlib.util
import json
import os
import sys
import time
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

spec = importlib.util.spec_from_file_location(
    'bulk_gen', os.path.join(BASE, 'tools', 'bulk_gen.py'))
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)

TARGET_TOTAL = 100
MIN_PER_DIFF = 34          # ~1/3 of the target, keeps the board drawable
BATCH = 20
WORKERS = 3
MAX_ROUNDS = 25


def quiz_counts():
    qs = bg.read_all()
    out = {}
    for q in qs:
        if q.get('game') == 'quiz':
            out.setdefault(q.get('category_id'), Counter())[q.get('difficulty')] += 1
    return out


def targets(counts):
    """[(cid, cname, difficulty, need)] for every category under TARGET_TOTAL."""
    cats = json.load(open(bg.CATFILE, encoding='utf-8'))
    out = []
    for c in cats:
        cid, cname = c['id'], c['name']
        cur = counts.get(cid, Counter())
        total = sum(cur.values())
        if total >= TARGET_TOTAL:
            continue
        # Bring every band up to MIN_PER_DIFF first, then spread the rest evenly.
        need = TARGET_TOTAL - total
        per = {d: max(0, MIN_PER_DIFF - cur.get(d, 0)) for d in ('easy', 'medium', 'hard')}
        base = sum(per.values())
        if base >= need:
            # Not enough room: scale the per-band need down proportionally.
            scale = need / float(base)
            per = {d: int(per[d] * scale) for d in per}
        else:
            extra = need - base
            third = extra // 3
            for d in ('easy', 'medium', 'hard'):
                per[d] += third
            for i, d in enumerate(('easy', 'medium', 'hard')):
                if i < extra % 3:
                    per[d] += 1
        for d in ('easy', 'medium', 'hard'):
            if per[d] > 0:
                out.append((cid, cname, d, per[d]))
    return out


def main():
    counts = quiz_counts()
    tg = targets(counts)
    if not tg:
        print('all categories already at %d' % TARGET_TOTAL)
        return 0
    print('categories below %d:' % TARGET_TOTAL)
    for cid, cname, d, n in tg:
        print('   %-14s %-24s %-7s need %3d' % (cid, cname[:24], d, n))
    print('total need:', sum(t[3] for t in tg))
    return tg


if __name__ == '__main__':
    t = main()
    if t:
        with open(os.path.join(bg.DATA_DIR, 'questions', '_fill_targets.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(t, f, ensure_ascii=False, indent=1)
        print('wrote _fill_targets.json')
