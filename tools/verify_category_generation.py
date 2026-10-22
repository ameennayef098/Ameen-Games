"""End-to-end test of /api/ai/generate for a niche category.

Calls the real view function (the admin guard lives in before_request, so the
view itself can be invoked directly with a test request context) and then
reports what was stored.
"""
import json
import os
import sys

CAT_ID = 'f87726c2'          # اتاك اون تايتين
COUNT = 5

src = open('server.py', encoding='utf-8').read()
marker = "if __name__ == '__main__'"
ns = {'__name__': 'srvtest', '__file__': os.path.abspath('server.py')}
exec(compile(src[:src.find(marker)], 'server.py', 'exec'), ns)

app = ns['app']
ai_generate = ns['ai_generate']

cats = {c['id']: c for c in json.load(open('data/categories/categories.json', encoding='utf-8'))}
cat = cats.get(CAT_ID)
print('category: %s' % (cat or {}).get('name'))
print('description: %s' % (cat or {}).get('description'))
print()

with app.test_request_context(
        '/api/ai/generate', method='POST',
        data=json.dumps({'game': 'quiz', 'category': CAT_ID,
                         'count': COUNT, 'difficulty': 'medium'}),
        content_type='application/json'):
    resp = ai_generate()
    body = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
    if isinstance(resp, tuple):
        body = resp[0].get_json()
        status = resp[1]
    else:
        body = resp.get_json()
        status = resp.status_code

print('HTTP %s' % status)
if body.get('error'):
    print('ERROR: %s' % body['error'])
print('requested: %s   accepted: %s   rejected: %s'
      % (body.get('requested'), body.get('count'), body.get('rejected_count')))
print()
print('rejected reasons:')
for r in (body.get('rejected') or [])[:10]:
    print('   - [%s] %s' % (r.get('reason'), r.get('question', '')[:55]))
print()
print('=== generated questions ===')
for q in (body.get('questions') or []):
    print('  %s' % q['question'][:72])
    print('     -> %s' % q.get('answer', '')[:45])
print()

# report what actually landed in the store
d = json.load(open('data/questions/all.json', encoding='utf-8'))
sub = [q for q in d if q.get('category_id') == CAT_ID]
print('questions now stored for %s: %d' % (cat['name'], len(sub)))
for q in sub:
    print('   [%s] %s -> %s' % (q.get('status'), q['question'][:55], q.get('answer', '')[:30]))
