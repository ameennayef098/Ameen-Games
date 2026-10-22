#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full integrity + content check of the Ameen Games question bank."""
import collections
import json
import re

QS = json.load(open('data/questions/all.json', encoding='utf-8'))
CATS = json.load(open('data/categories/categories.json', encoding='utf-8'))

print('total rows:', len(QS))
print('by game:', dict(collections.Counter(q.get('game') for q in QS)))

ids = [q.get('id') for q in QS]
dups = [k for k, v in collections.Counter(ids).items() if v > 1]
print('duplicate ids:', len(dups), dups[:5])

quiz = [q for q in QS if q.get('game') == 'quiz']
mis = [q for q in quiz if (q.get('difficulty') == 'easy' and q.get('points') != 200)
       or (q.get('difficulty') == 'medium' and q.get('points') != 400)
       or (q.get('difficulty') == 'hard' and q.get('points') != 600)]
print('quiz rows:', len(quiz), '| points/difficulty mismatches:', len(mis))

key = collections.Counter(
    q.get('game', '') + '|' + re.sub(r'\s+', ' ', str(q.get('question', '')).strip())
    for q in QS)
print('duplicate question texts:', len([k for k, v in key.items() if v > 1]))

FOREIGN = re.compile(r'[A-Za-z\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF\u0E00-\u0E7F\u0590-\u05FF]')
bad = [q for q in QS if FOREIGN.search(str(q.get('question', ''))) or FOREIGN.search(str(q.get('answer', '')))]
print('rows with foreign chars:', len(bad))

empty = [q for q in QS if not str(q.get('question', '')).strip() or not str(q.get('answer', '')).strip()]
print('rows with empty question/answer:', len(empty))

c = collections.Counter(q.get('category_id') for q in quiz)
print('categories:', len(CATS), '| quiz category_ids:', len(c))
print('categories with 0 quiz:', [x['id'] for x in CATS if x['id'] not in c])
print('per-cat min/max:', min(c.values()), max(c.values()))

letters = [q for q in QS if q.get('game') == 'letters']
bl = collections.Counter(q.get('letter') for q in letters)
print('letters rows:', len(letters), '| distinct letters:', len(bl))
print('letters with 0 rows:', [l for l in
      ['أ','ب','ت','ث','ج','ح','خ','د','ذ','ر','ز','س','ش','ص','ض','ط','ظ','ع','غ','ف','ق','ك','ل','م','ن','ه','و','ي']
      if bl.get(l, 0) == 0])

million = [q for q in QS if q.get('game') == 'million']
bad_opts = [q for q in million if len(q.get('options') or []) != 4]
print('million rows:', len(million), '| rows without 4 options:', len(bad_opts))
