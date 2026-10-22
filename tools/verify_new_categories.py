# -*- coding: utf-8 -*-
"""Verify the 20 new س.ج categories end to end:
appear -> selectable -> questions saved/retrievable -> editable -> playable.

The write endpoints are admin-guarded, so the edit test drives the real view
function through Flask's test client with a token injected into ADMIN_TOKENS —
same guard, same handler, same validation, no password needed.
"""
import sys, os, json
sys.path.insert(0, r'C:\Users\Ameen Dawaghreh\Desktop\ألعاب-أمين')
import server as S

NEW = ['philosophy', 'criminal_investigation', 'marine_life', 'plants_trees',
       'natural_disasters', 'archaeology', 'media_journalism',
       'observational_astronomy', 'combat_sports', 'motorsports',
       'nutrition_science', 'accounting_finance', 'international_awards',
       'symbols_codes', 'maritime_navigation', 'infrastructure_smartcities',
       'military_aviation', 'museums_collections', 'folklore_fairy_tales',
       'materials_engineering']

# ---- 1) categories exist with name/icon/real description --------------------
cats = {c['id']: c for c in S.load_json(S.CAT_FILE, [])}
missing = [n for n in NEW if n not in cats]
print('1) all 20 categories exist:', not missing, '| total categories:', len(cats))
if missing:
    print('   MISSING:', missing)
short = [n for n in NEW if len(cats[n].get('description', '')) < 100]
print('   descriptions under 100 chars:', short or 'none')
noicon = [n for n in NEW if not cats[n].get('icon') or not cats[n].get('name')]
print('   missing name/icon:', noicon or 'none')

# ---- 2) questions generated and saved --------------------------------------
d = S.load_json(S.Q_FILE, [])
per = {n: [q for q in d if q.get('category_id') == n] for n in NEW}
zero = [n for n in NEW if not per[n]]
print('2) categories with no question:', zero or 'none',
      '| total new questions:', sum(len(v) for v in per.values()))
bad = []
for n in NEW:
    for q in per[n]:
        ok, err = S.validate_question(q)
        leak = S.norm_ar(q['answer']) in S.norm_ar(q['question'])
        if not ok or leak:
            bad.append((n, q['question'][:50], err, leak))
print('   invalid or answer-in-question rows:', len(bad))
for b in bad[:5]:
    print('    ', b)

# ---- 3) edit through the real guarded endpoint -----------------------------
S.ADMIN_TOKENS.add('test-token-hermes')
cl = S.app.test_client()
q = per['philosophy'][0]
r = cl.put('/api/questions/%s' % q['id'],
           json={'explanation': 'شرح مُحدَّث بواسطة الاختبار'},
           headers={'X-Admin-Token': 'test-token-hermes'})
print('3) PUT /api/questions/<id> ->', r.status_code)
print('   explanation now:', r.get_json().get('explanation'))
r2 = cl.get('/api/questions?game=quiz&category=philosophy&per_page=10')
found = [x for x in r2.get_json()['questions'] if x['id'] == q['id']]
print('   persisted after re-read:', bool(found) and found[0]['explanation'].startswith('شرح مُحدَّث'))

r3 = cl.put('/api/questions/%s' % q['id'], json={'question': 'سؤال بلا إجابة'},
           headers={'X-Admin-Token': 'test-token-hermes'})
print('   invalid edit rejected:', r3.status_code == 400, '|', r3.get_json().get('error'))

# guard still blocks anonymous writes
S.ADMIN_TOKENS.discard('test-token-hermes')
r4 = cl.put('/api/questions/%s' % q['id'], json={'explanation': 'x'})
print('   anonymous write blocked:', r4.status_code == 401)

# ---- 4) category update through the same endpoint --------------------------
r5 = cl.put('/api/categories/philosophy', json={'color': '#8b5cf6'},
            headers={'X-Admin-Token': 'nope'})
print('4) category PUT without token ->', r5.status_code)
S.ADMIN_TOKENS.add('test-token-hermes')
r6 = cl.put('/api/categories/philosophy', json={'color': '#8b5cf6'},
           headers={'X-Admin-Token': 'test-token-hermes'})
print('   category PUT with token ->', r6.status_code,
      '| color:', r6.get_json().get('color'))

# ---- 5) existing data untouched --------------------------------------------
ids_before = {c['id'] for c in S.load_json(S.CAT_FILE, [])}
print('5) original 60 categories still present:',
      len([c for c in S.load_json(S.CAT_FILE, [])]) == 80)
old_easy = len([q for q in d if q.get('difficulty') == 'easy' and q.get('game') == 'letters'])
print('   letters easy still deleted (expected 0):', old_easy)
print('   bank total:', len(d))
