#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure real generation throughput before committing to a wave size.

Runs a fixed small sample of quiz and letter batches, times them, and prints
questions-per-minute per game so the wave plan is based on measurement.
"""
import os
import sys
import time
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))
import bulk_gen as B  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

B.MODEL = B.ENV.get('NVIDIA_MODEL', 'nvidia/nemotron-3.5-lightning-30b-a3b')
SLOTS = int(os.environ.get('AMEEN_API_SLOTS', 6))
print('model=%s  api_slots=%d' % (B.MODEL, SLOTS))

CATS = json.load(open(B.CATFILE, encoding='utf-8'))
t0 = time.time()

# ---- quiz: 4 categories x 1 difficulty, 16 each
quiz_jobs = [(c['id'], c['name'], 'medium') for c in CATS[:4]]
def q(j):
    cid, name, d = j
    try:
        return len(B.fetch_quiz_batch(cid, name, d, 16))
    except Exception as e:
        print('  quiz fail %s: %s' % (name, e))
        return 0

with ThreadPoolExecutor(max_workers=4) as ex:
    qn = list(ex.map(q, quiz_jobs))
t1 = time.time()
print('QUIZ: %d questions in %.1fs (%.1f q/min with 4 workers)'
      % (sum(qn), t1 - t0, sum(qn) / (t1 - t0) * 60))
print('  per batch:', qn)

# ---- letters: 4 letters, easy
letters = ['أ', 'ب', 'ت', 'ث']
def l(tr):
    letter, d = tr
    try:
        return len(B.fetch_letters_batch(letter, 8, d))
    except Exception as e:
        print('  letters fail %s/%s: %s' % (letter, d, e))
        return 0

with ThreadPoolExecutor(max_workers=4) as ex:
    ln = list(ex.map(l, [(x, 'easy') for x in letters]))
t2 = time.time()
print('LETTERS easy: %d questions in %.1fs (%.1f q/min with 4 workers)'
      % (sum(ln), t2 - t1, sum(ln) / (t2 - t1) * 60))
print('  per letter:', ln)

# ---- letters hard
with ThreadPoolExecutor(max_workers=4) as ex:
    ln2 = list(ex.map(l, [(x, 'hard') for x in letters]))
t3 = time.time()
print('LETTERS hard: %d questions in %.1fs (%.1f q/min)'
      % (sum(ln2), t3 - t2, sum(ln2) / (t3 - t2) * 60))
print('  per letter:', ln2)

print()
print('TOTAL wall %.1fs' % (t3 - t0))
