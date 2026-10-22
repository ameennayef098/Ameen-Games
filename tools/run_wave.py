#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run one generation wave (shard) to completion, crash-safe.

A wave is a JSON plan of targets. After EVERY batch the accepted items are
appended to all.json under the shared lock, so a crash, a rate limit or a
manual stop only costs the batch in flight — never the whole run.

Usage
-----
    python tools/run_wave.py --plan data/waves/letters-a.json --workers 2

Plan format
-----------
    {"game": "quiz", "targets": [["sports", "easy", 80], ...]}
    {"game": "letters", "targets": [["أ", "easy", 60], ...]}

Key is category_id for quiz, the Arabic letter for letters.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))

import bulk_gen as B  # noqa: E402
from gsema import limit, used as sema_used  # noqa: E402

B.MODEL = B.ENV.get('NVIDIA_MODEL', 'nvidia/nemotron-3.5-lightning-30b-a3b')
WAVES = os.path.join(BASE, 'data', 'waves')


def log(msg):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def cat_name(cid):
    for c in json.load(open(B.CATFILE, encoding='utf-8')):
        if c['id'] == cid:
            return c['name']
    return cid


def run_quiz(targets, workers, batch, max_rounds, progress_path):
    """targets: [(cid, difficulty, need), ...]"""
    keys = B.existing_keys('quiz')
    remaining = {i: t[2] for i, t in enumerate(targets)}
    accepted_total = 0
    rejected_total = 0

    for rnd in range(1, max_rounds + 1):
        jobs = [(i, t, min(batch, remaining[i])) for i, t in enumerate(targets)
                if remaining[i] > 0]
        if not jobs:
            break

        def work(j):
            i, t, n = j
            cid, difficulty, _ = t
            name = cat_name(cid)
            last = ''
            for attempt in range(3):
                try:
                    return i, B.fetch_quiz_batch(cid, name, difficulty, n)
                except Exception as e:
                    last = '%s: %s' % (type(e).__name__, e)
                    time.sleep(3 * (attempt + 1))
            log('  ! batch failed %s/%s: %s' % (name, difficulty, last))
            return i, []

        got = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(work, jobs):
                cid, difficulty, _ = targets[i]
                fresh = [it for it in items
                         if (it['game'] + '|' + B.norm_ar(it['question'])) not in keys]
                rejected_total += len(items) - len(fresh)
                for it in fresh:
                    keys.add(it['game'] + '|' + B.norm_ar(it['question']))
                if fresh:
                    B.append_locked(fresh)          # crash-safe: write at once
                remaining[i] -= len(fresh)
                accepted_total += len(fresh)
                got += len(fresh)
        log('  round %d: +%d (wave total %d, api slots busy %d)'
            % (rnd, got, accepted_total, sema_used('nvidia')))
        save_progress(progress_path, targets, remaining, accepted_total)

    for i, t in enumerate(targets):
        if remaining[i] > 0:
            log('  ! short: %s/%s got %d of %d'
                % (cat_name(t[0]), t[1], t[2] - remaining[i], t[2]))
    return accepted_total, rejected_total


def run_letters(targets, workers, batch, max_rounds, progress_path):
    """targets: [(letter, difficulty, need), ...]"""
    keys = B.existing_keys('letters')
    remaining = {i: t[2] for i, t in enumerate(targets)}
    accepted_total = 0
    rejected_total = 0

    for rnd in range(1, max_rounds + 1):
        jobs = [(i, t, min(batch, remaining[i])) for i, t in enumerate(targets)
                if remaining[i] > 0]
        if not jobs:
            break

        def work(j):
            i, t, n = j
            letter, difficulty, _ = t
            last = ''
            for attempt in range(3):
                try:
                    return i, B.fetch_letters_batch(letter, n, difficulty)
                except Exception as e:
                    last = '%s: %s' % (type(e).__name__, e)
                    time.sleep(3 * (attempt + 1))
            log('  ! batch failed %s/%s: %s' % (letter, difficulty, last))
            return i, []

        got = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(work, jobs):
                letter, difficulty, _ = targets[i]
                fresh = [it for it in items
                         if (it['game'] + '|' + B.norm_ar(it['question'])) not in keys]
                rejected_total += len(items) - len(fresh)
                for it in fresh:
                    keys.add(it['game'] + '|' + B.norm_ar(it['question']))
                if fresh:
                    B.append_locked(fresh)
                remaining[i] -= len(fresh)
                accepted_total += len(fresh)
                got += len(fresh)
        log('  round %d: +%d (wave total %d, api slots busy %d)'
            % (rnd, got, accepted_total, sema_used('nvidia')))
        save_progress(progress_path, targets, remaining, accepted_total)

    for i, t in enumerate(targets):
        if remaining[i] > 0:
            log('  ! short: حرف %s/%s got %d of %d'
                % (t[0], t[1], t[2] - remaining[i], t[2]))
    return accepted_total, rejected_total


def save_progress(path, targets, remaining, accepted):
    out = {'accepted': accepted,
           'remaining': [{'key': t[0], 'difficulty': t[1],
                          'need': t[2], 'left': remaining[i]}
                         for i, t in enumerate(targets)],
           'updated': time.strftime('%Y-%m-%dT%H:%M:%S')}
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--batch', type=int, default=20)
    ap.add_argument('--max-rounds', type=int, default=14)
    a = ap.parse_args()

    if not B.API_KEY:
        print('NVIDIA_API_KEY missing from .env')
        return 1

    plan = json.load(open(a.plan, encoding='utf-8'))
    game = plan['game']
    targets = [tuple(t) for t in plan['targets']]
    name = os.path.splitext(os.path.basename(a.plan))[0]
    progress_path = os.path.join(WAVES, name + '.progress.json')

    log('wave %s | game=%s | targets=%d | workers=%d | api_slots=%s'
        % (name, game, len(targets), a.workers,
           os.environ.get('AMEEN_API_SLOTS', 6)))

    t0 = time.time()
    if game == 'quiz':
        acc, rej = run_quiz(targets, a.workers, a.batch, a.max_rounds, progress_path)
    else:
        acc, rej = run_letters(targets, a.workers, a.batch, a.max_rounds, progress_path)

    log('WAVE DONE %s: accepted=%d rejected=%d wall=%.1fmin'
        % (name, acc, rej, (time.time() - t0) / 60))
    return 0


if __name__ == '__main__':
    sys.exit(main())
