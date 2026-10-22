#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run every wave plan in ONE durable process.

Replaces six separate per-shard processes: one process, a fixed worker pool,
and the cross-process semaphore still caps total API concurrency. Because it
is a single process it survives independently of any shell session, and
because it appends after every batch a crash costs only the batch in flight.

    python tools/run_all_waves.py                 # all plans in data/waves/
    python tools/run_all_waves.py --workers 6
    python tools/run_all_waves.py --only letters  # filter by plan name substring
"""
import argparse
import faulthandler
import glob
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))

import bulk_gen as B  # noqa: E402
from gsema import used as sema_used  # noqa: E402

# The .env may name a model this account is not entitled to (or a very large
# one). Benchmarks: nemotron-3.5-lightning-30b-a3b returns ~200 quiz
# questions/min, while the 550B fallback took ~69s per call and dropped the
# whole run to ~38 questions/min. Pin the fast model explicitly.
FAST_MODEL = 'nvidia/nemotron-3.5-lightning-30b-a3b'
B.MODEL = FAST_MODEL
B.FALLBACK_MODELS = []
WAVES = os.path.join(BASE, 'data', 'waves')

_lock = threading.Lock()
_state = {'accepted': 0, 'rejected': 0, 'batches': 0, 'failures': 0,
          'start': time.time(), 'done': set()}


def log(msg):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def cat_name(cid):
    for c in json.load(open(B.CATFILE, encoding='utf-8')):
        if c['id'] == cid:
            return c['name']
    return cid


def save_progress(plans, remaining):
    out = {'accepted': _state['accepted'], 'rejected': _state['rejected'],
           'batches': _state['batches'], 'failures': _state['failures'],
           'elapsed_min': round((time.time() - _state['start']) / 60, 1),
           'api_slots_busy': sema_used('nvidia'),
           'remaining': remaining, 'updated': B._ts()}
    tmp = os.path.join(WAVES, '_progress.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(WAVES, '_progress.json'))


def make_job(plan_name, game, key, difficulty, need, batch):
    """Return a zero-arg callable performing ONE batch, or None when done."""
    if need <= 0:
        return None

    def job():
        n = min(batch, need)
        label = key if game == 'letters' else key
        log('  start %s/%s/%s' % (plan_name, label, difficulty))
        last = ''
        for attempt in range(3):
            try:
                if game == 'quiz':
                    cid, name = key, cat_name(key)
                    items = B.fetch_quiz_batch(cid, name, difficulty, n)
                else:
                    items = B.fetch_letters_batch(key, n, difficulty)
                log('  done  %s/%s/%s -> %d' % (plan_name, label, difficulty, len(items)))
                return plan_name, game, key, difficulty, need, items
            except Exception as e:
                last = '%s: %s' % (type(e).__name__, e)
                log('  retry %s/%s/%s (%d): %s'
                    % (plan_name, label, difficulty, attempt, last[:160]))
                time.sleep(3 * (attempt + 1))
        log('  ! FAILED %s/%s/%s: %s' % (plan_name, key, difficulty, last))
        with _lock:
            _state['failures'] += 1
        return plan_name, game, key, difficulty, need, None

    return job


def handle(result, remaining, keys, batch, retry):
    plan_name, game, key, difficulty, need, items = result
    if items is None:
        # count the failure against this target so it is not retried forever
        retry[(plan_name, game, key, difficulty)] = \
            retry.get((plan_name, game, key, difficulty), 0) + 1
        if retry[(plan_name, game, key, difficulty)] >= 2:
            with _lock:
                remaining[(plan_name, game, key, difficulty)] = 0
                _state['done'].add((plan_name, game, key, difficulty))
        return
    fresh = [it for it in items
             if (it['game'] + '|' + B.norm_ar(it['question'])) not in keys]
    with _lock:
        for it in fresh:
            keys.add(it['game'] + '|' + B.norm_ar(it['question']))
        _state['rejected'] += len(items) - len(fresh)
        if fresh:
            B.append_locked(fresh)          # crash-safe: write immediately
            _state['accepted'] += len(fresh)
        _state['batches'] += 1
        k = (plan_name, game, key, difficulty)
        remaining[k] -= len(fresh)
        if remaining[k] <= 0:
            _state['done'].add(k)
        acc = _state['accepted']
        rej = _state['rejected']
        batches = _state['batches']
    label = key if game == 'letters' else cat_name(key)
    log('  +%d %s/%s/%s (accepted %d, rejected %d, batches %d, slots %d)'
        % (len(fresh), plan_name, label, difficulty, acc, rej, batches,
           sema_used('nvidia')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--batch', type=int, default=20)
    ap.add_argument('--max-rounds', type=int, default=16)
    ap.add_argument('--only', default='')
    a = ap.parse_args()

    if not B.API_KEY:
        print('NVIDIA_API_KEY missing from .env')
        return 1

    # Dump every thread's stack every 60s so a stall can be diagnosed from the
    # log instead of guessed at.
    faulthandler.dump_traceback_later(60, repeat=True)

    plans = []
    for path in sorted(glob.glob(os.path.join(WAVES, '*.json'))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith('_'):
            continue
        if a.only and a.only not in name:
            continue
        p = json.load(open(path, encoding='utf-8'))
        plans.append((name, p['game'], [tuple(t) for t in p['targets']]))

    if not plans:
        print('no plans matched')
        return 1

    # remaining[(plan, game, key, difficulty)] = questions still wanted
    remaining = {}
    for name, game, targets in plans:
        for key, difficulty, need in targets:
            if need > 0:
                remaining[(name, game, key, difficulty)] = need

    total = sum(remaining.values())
    log('orchestrator: %d plans, %d targets, %d questions, workers=%d, api_slots=%s'
        % (len(plans), len(remaining), total, a.workers,
           os.environ.get('AMEEN_API_SLOTS', 6)))

    keys = B.existing_keys('quiz') | B.existing_keys('letters')
    retry = {}
    rounds = 0

    while remaining and rounds < a.max_rounds:
        rounds += 1
        live = {k: v for k, v in remaining.items()
                if v > 0 and retry.get(k, 0) < 2}
        if not live:
            break
        jobs = [make_job(k[0], k[1], k[2], k[3], v, a.batch)
                for k, v in live.items()]
        jobs = [j for j in jobs if j]
        if not jobs:
            break
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            for result in ex.map(lambda j: j(), jobs):
                handle(result, remaining, keys, a.batch, retry)
        save_progress(plans, { '|'.join(map(str, k)): v
                              for k, v in remaining.items()})

    short = [(k, v) for k, v in remaining.items() if v > 0]
    log('ORCHESTRATOR DONE: accepted=%d rejected=%d failures=%d wall=%.1fmin'
        % (_state['accepted'], _state['rejected'], _state['failures'],
           (time.time() - _state['start']) / 60))
    if short:
        log('%d targets still short:' % len(short))
        for (name, game, key, difficulty), left in short[:20]:
            label = key if game == 'letters' else cat_name(key)
            log('   %s %s/%s -> %d left' % (name, label, difficulty, left))
    return 0


if __name__ == '__main__':
    sys.exit(main())
