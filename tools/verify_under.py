# -*- coding: utf-8 -*-
"""Verify the «تحت المتوسط» bank after the fill run."""
import sys, os, json, collections
sys.path.insert(0, r'C:\Users\Ameen Dawaghreh\Desktop\ألعاب-أمين')
import server as S

d = S.load_json(S.Q_FILE, [])
print('bank total:', len(d))

print('\n== difficulty by game ==')
for g in ('quiz', 'letters', 'million'):
    rows = [q for q in d if q.get('game') == g]
    print('  %-8s %s' % (g, dict(collections.Counter(q.get('difficulty') for q in rows))))

easy = [q for q in d if q.get('difficulty') == 'easy']
print('\neasy questions left:', len(easy))

# points must line up with the tier
bad_pts = [q for q in d if q.get('game') == 'quiz'
           and q.get('difficulty') == 'under' and q.get('points') != 200]
print('under questions with wrong points:', len(bad_pts))

# the trick constraint: the answer word must not appear in the question
under = [q for q in d if q.get('difficulty') == 'under']
leaks = [q for q in under if S.norm_ar(q['answer']) and S.norm_ar(q['answer']) in S.norm_ar(q['question'])]
print('under questions leaking the answer:', len(leaks), '/', len(under))

# foreign-script / validation pass over everything new
bad = []
for q in under:
    ok, err = S.validate_question(q)
    if not ok:
        bad.append((q['question'][:50], err))
print('under questions failing validate_question:', len(bad))
for t, e in bad[:10]:
    print('   ', t, '->', e)

# letters answers must start with the right letter
lbad = []
for q in d:
    if q.get('game') == 'letters' and q.get('difficulty') == 'under':
        if S.first_letter_of(str(q.get('answer', '')).strip()) != S.norm_ar(q['letter']):
            lbad.append((q['letter'], q['answer']))
print('under letters with wrong initial letter:', len(lbad), lbad[:5])

# million options
mbad = []
for q in d:
    if q.get('game') == 'million' and q.get('difficulty') == 'under':
        if len(q.get('options') or []) != 4 or q['answer'] not in q['options']:
            mbad.append(q['question'][:50])
print('under million with bad options:', len(mbad))

# per-category coverage
cats = {c['id']: c['name'] for c in S.load_json(S.CAT_FILE, [])}
cov = collections.Counter(q['category_id'] for q in under if q.get('game') == 'quiz')
print('\nquiz categories with under questions: %d / %d' % (len(cov), len(cats)))
missing = [cats[c] for c in cats if c not in cov]
print('  missing:', missing[:10] if missing else 'none')
print('  min per category:', min(cov.values()) if cov else 0,
      '| max:', max(cov.values()) if cov else 0)

# sample of trick-style questions
print('\n== sample under questions ==')
for q in under[:6]:
    print('  -', q['question'][:78], '||', q['answer'])
riddle = [q for q in under if q['question'].startswith('أنا') or 'من أنا' in q['question']]
print('\nriddle-style (أنا / من أنا):', len(riddle))
for q in riddle[:5]:
    print('  -', q['question'][:78], '||', q['answer'])
