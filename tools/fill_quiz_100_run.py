#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bring every quiz category up to 100 questions (even split across difficulties).

Reads the target list produced by tools/fill_quiz_100.py, generates in
rounds of BATCH per (category, difficulty), validates with the SAME rules as
tools/bulk_gen.py, and appends to data/questions/all.json under the exclusive
lock after every category so an interruption only costs the current category.

Usage
-----
    python tools/fill_quiz_100_run.py                 # everything below 100
    python tools/fill_quiz_100_run.py --category countries
    python tools/fill_quiz_100_run.py --dry-run       # validate, do not write
    python tools/fill_quiz_100_run.py --workers 4 --max-rounds 30
"""
import argparse
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location(
    'bulk_gen', os.path.join(BASE, 'tools', 'bulk_gen.py'))
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)

TARGET_TOTAL = 100
MIN_PER_DIFF = 34
BATCH = 20
WORKERS = 3
MAX_ROUNDS = 25


def quiz_counts():
    out = {}
    for q in bg.read_all():
        if q.get('game') == 'quiz':
            out.setdefault(q.get('category_id'), Counter())[q.get('difficulty')] += 1
    return out


def build_targets(category=None):
    """[(cid, cname, difficulty, need)] — every category still under TARGET_TOTAL."""
    counts = quiz_counts()
    cats = json.load(open(bg.CATFILE, encoding='utf-8'))
    out = []
    for c in cats:
        cid, cname = c['id'], c['name']
        if category and cid != category:
            continue
        cur = counts.get(cid, Counter())
        total = sum(cur.values())
        if total >= TARGET_TOTAL:
            continue
        need = TARGET_TOTAL - total
        # Order the bands from most-starved to least so a tiny remaining need
        # (a category sitting at 99, needing one more) always lands somewhere
        # instead of being scaled down to zero in every band.
        order = sorted(('easy', 'medium', 'hard'),
                       key=lambda d: (cur.get(d, 0), d))
        per = {d: 0 for d in order}
        # 1) bring each band up to MIN_PER_DIFF
        for d in order:
            if need <= 0:
                break
            gap = max(0, MIN_PER_DIFF - cur.get(d, 0))
            take = min(gap, need)
            per[d] = take
            need -= take
        # 2) spread whatever is left over the most-starved bands
        i = 0
        while need > 0:
            d = order[i % 3]
            per[d] += 1
            need -= 1
            i += 1
        for d in ('easy', 'medium', 'hard'):
            if per[d] > 0:
                out.append((cid, cname, d, per[d]))
    return out


def run(tg, workers, dry_run, max_rounds):
    keys = bg.existing_keys('quiz')
    remaining = {i: t[3] for i, t in enumerate(tg)}
    accepted_total = 0
    short = []

    for rnd in range(1, max_rounds + 1):
        # Always request a full batch: when a category needs only 1-2 questions
        # the model still has to search a wide space to avoid recycling its own
        # 99 existing items, so a 4-item batch almost never yields anything new.
        jobs = [(i, tg[i], BATCH) for i in range(len(tg)) if remaining[i] > 0]
        if not jobs:
            break

        def work(j):
            i, t, n = j
            cid, cname, d, _ = t
            last = ''
            for _attempt in range(3):
                try:
                    return i, bg.fetch_quiz_batch(cid, cname, d, n)
                except Exception as e:
                    last = e
                    time.sleep(2)
            return i, []

        got = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(work, jobs):
                cid, cname, d, _ = tg[i]
                fresh = [it for it in items
                         if (it['game'] + '|' + bg.norm_ar(it['question'])) not in keys]
                for it in fresh:
                    keys.add(it['game'] + '|' + bg.norm_ar(it['question']))
                remaining[i] -= len(fresh)
                got += len(fresh)
                # save after every category batch: an interruption costs at most
                # the categories still to come, never the ones already written
                if fresh and not dry_run:
                    bg.append_locked(fresh)
                    accepted_total += len(fresh)
                    print('    +%3d  %-24s %-7s  (cat total so far saved)'
                          % (len(fresh), cname[:24], d))
        print('  round %2d: +%d' % (rnd, got))
        if got == 0:
            print('  no progress this round — stopping')
            break

    for i, t in enumerate(tg):
        if remaining[i] > 0:
            short.append((t[1], t[2], t[3] - remaining[i], t[3]))
    return accepted_total, short


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--category')
    ap.add_argument('--workers', type=int, default=WORKERS)
    ap.add_argument('--max-rounds', type=int, default=MAX_ROUNDS)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    bg.VERIFY = a.verify
    tg = build_targets(a.category)
    if not tg:
        print('nothing to do — every category is at %d' % TARGET_TOTAL)
        return 0

    print('model: %s   workers: %d' % (bg.MODEL, a.workers))
    print('targets (%d):' % len(tg))
    for cid, cname, d, n in tg:
        print('   %-14s %-24s %-7s %3d' % (cid, cname[:24], d, n))
    print('total need: %d' % sum(t[3] for t in tg))
    if a.dry_run:
        print('DRY RUN — nothing will be written')

    t0 = time.time()
    acc, short = run(tg, a.workers, a.dry_run, a.max_rounds)
    print('DONE: %d accepted in %.0fs' % (acc, time.time() - t0))
    for name, d, got, want in short:
        print('   ! short: %-24s %-7s %d of %d' % (name[:24], d, got, want))
    return 0


if __name__ == '__main__':
    sys.exit(main())
