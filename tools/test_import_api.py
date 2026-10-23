# -*- coding: utf-8 -*-
"""اختبارات مسارات الاستيراد الجماعي على الخادم (الحالات 13-18).

تعمل على مخزن حقيقي لكنها تأخذ نسخة من الملفات وتعيدها حرفياً في النهاية،
فلا تبقى أي بيانات تجريبية في قاعدة البيانات.

شغّلها:  python tools/test_import_api.py
"""
import os
import sys
import json
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import server  # noqa: E402

Q_FILE = os.path.join(ROOT, 'data', 'questions', 'all.json')
HIST_FILE = os.path.join(ROOT, 'data', 'questions', 'import_history.json')
CONTENT_FILE = os.path.join(ROOT, 'data', 'content', 'codenames.json')
TOKEN = 'test-import-token'
server.ADMIN_TOKENS.add(TOKEN)
H = {'X-Admin-Token': TOKEN, 'Content-Type': 'application/json'}
STORES = [Q_FILE, HIST_FILE, CONTENT_FILE]


def q(count, prefix='سؤال اختبار'):
    """(count) أسئلة بصيغة س/ج جاهزة للصق."""
    out = []
    for i in range(1, count + 1):
        out.append('س%d: %s رقم %d؟' % (i, prefix, i))
        out.append('ج%d: جواب رقم %d' % (i, i))
    return '\n\n'.join(out)


class ImportAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = server.app.test_client()
        cls.snapshot = {}
        for p in STORES:
            if os.path.exists(p):
                with open(p, 'rb') as f:
                    cls.snapshot[p] = f.read()
            else:
                cls.snapshot[p] = None

    @classmethod
    def tearDownClass(cls):
        for p, data in cls.snapshot.items():
            if data is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                with open(p, 'wb') as f:
                    f.write(data)

    # ---------------- helpers ----------------
    def store(self):
        with open(Q_FILE, encoding='utf-8') as f:
            return json.load(f)

    def parse(self, text, game='quiz', target=None):
        r = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'text': text, 'game': game,
                                              'target': target or {}}))
        return r

    def save(self, text, game='quiz', target=None, idem=None, keep=None, partial=False):
        p = self.parse(text, game, target).get_json()
        body = {'game': game, 'target': target or {}, 'records': p['records'],
                'keep_duplicates': keep or [], 'allow_partial': partial}
        if idem:
            body['idempotency_key'] = idem
        return self.client.post('/api/import/save', headers=H, data=json.dumps(body))

    def authless(self):
        return self.client.post('/api/import/parse', data=json.dumps({'text': 'س1: س',
                                                                      'game': 'quiz'}))

    # ---------------- tests ----------------
    def test_13_selectors_are_per_game(self):
        games = self.client.get('/api/import/games').get_json()['games']
        by = {g['game']: g for g in games}
        self.assertIn('letters', by)
        self.assertIn('quiz', by)
        # a letters import must never be offered quiz categories
        self.assertNotIn('category', by['letters']['selectors'])
        self.assertIn('letter', by['letters']['selectors'])
        self.assertIn('category', by['quiz']['selectors'])
        self.assertNotIn('letter', by['quiz']['selectors'])
        self.assertEqual(by['letters']['letters'][0]['id'], 'أ')
        self.assertTrue(by['quiz']['categories'])

    def test_13b_quiz_without_category_is_flagged(self):
        p = self.parse('س1: سؤال بلا فئة؟\nج1: جواب', 'quiz', {}).get_json()
        self.assertEqual(p['records'][0]['status'], 'needs_review')
        self.assertEqual(p['records'][0]['savable'], False)

    def test_14_save_failure_writes_nothing(self):
        before = len(self.store())
        text = ('س1: سؤال صحيح؟\nج1: جواب صحيح\n\n'
                'س2: سؤال بلا إجابة؟\n')
        r = self.save(text, 'quiz', {'category_id': 'sports', 'category_name': 'رياضة'})
        self.assertEqual(r.status_code, 400)
        body = r.get_json()
        self.assertEqual(body['saved'], 0)
        self.assertEqual(len(body['rejected']), 1)
        self.assertIn('reason', body['rejected'][0])
        self.assertEqual(len(self.store()), before)   # nothing partial

    def test_15_retry_after_failure_is_safe(self):
        before = len(self.store())
        bad = 'س1: سؤال صحيح؟\nج1: جواب\n\nس2: ناقص؟\n'
        self.assertEqual(self.save(bad, 'quiz', {'category_id': 'sports'}).status_code, 400)
        self.assertEqual(len(self.store()), before)
        # fix the record and retry — must save exactly once, no duplicates
        good = 'س1: سؤال صحيح؟\nج1: جواب\n\nس2: سؤال مكتمل؟\nج2: جواب ثانٍ'
        r = self.save(good, 'quiz', {'category_id': 'sports'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['saved'], 2)
        after = len(self.store())
        self.assertEqual(after, before + 2)
        qs = [x for x in self.store() if x.get('question') == 'سؤال صحيح؟']
        self.assertEqual(len(qs), 1)

    def test_16_repeated_save_does_not_double_add(self):
        before = len(self.store())
        text = q(5, 'تكرار الطلب')
        target = {'category_id': 'science', 'category_name': 'العلوم'}
        r1 = self.save(text, 'quiz', target, idem='job-abc-1')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json()['saved'], 5)
        self.assertEqual(len(self.store()), before + 5)

        r2 = self.save(text, 'quiz', target, idem='job-abc-1')
        self.assertEqual(r2.status_code, 200)
        body = r2.get_json()
        self.assertTrue(body.get('cached'))
        self.assertEqual(len(self.store()), before + 5)   # no second copy

    def test_16b_double_click_without_key_still_no_duplicates(self):
        before = len(self.store())
        text = q(3, 'نقر مزدوج')
        target = {'category_id': 'science'}
        self.save(text, 'quiz', target)
        self.assertEqual(len(self.store()), before + 3)
        # a second click re-parses and finds every record already in the store
        p = self.parse(text, 'quiz', target).get_json()
        self.assertEqual(p['summary']['duplicates'], 3)
        r = self.save(text, 'quiz', target)
        self.assertEqual(r.get_json()['saved'], 0)

    def test_17_new_questions_land_in_the_right_game_and_category(self):
        before = len(self.store())
        text = q(4, 'الفئة المستهدفة')
        target = {'category_id': 'science', 'category_name': 'العلوم'}
        self.assertEqual(self.save(text, 'quiz', target).get_json()['saved'], 4)
        got = self.client.get('/api/questions?game=quiz&category=science&per_page=5000',
                              headers=H).get_json()
        new = [x for x in got['questions'] if x['question'].startswith('الفئة المستهدفة')]
        self.assertEqual(len(new), 4)
        for x in new:
            self.assertEqual(x['game'], 'quiz')
            self.assertEqual(x['category_id'], 'science')
            self.assertEqual(x['source'], 'import')
            self.assertEqual(x['status'], 'approved')
        self.assertEqual(len(self.store()), before + 4)

    def test_18_existing_questions_untouched(self):
        before = self.store()
        signature = [(x['id'], x['question'], x['answer'], x.get('updated_at'))
                     for x in before]
        text = q(3, 'لا مساس')
        self.save(text, 'quiz', {'category_id': 'science'})
        after = self.store()
        self.assertEqual(len(after), len(before) + 3)
        by_id = {x['id']: x for x in after}
        for qid, question, answer, updated in signature:
            self.assertIn(qid, by_id)
            self.assertEqual(by_id[qid]['question'], question)
            self.assertEqual(by_id[qid]['answer'], answer)
            self.assertEqual(by_id[qid].get('updated_at'), updated)

    def test_import_100_questions(self):
        before = len(self.store())
        text = q(100, 'المئة')
        target = {'category_id': 'sports', 'category_name': 'رياضة'}
        p = self.parse(text, 'quiz', target).get_json()
        self.assertEqual(p['summary']['detected'], 100)
        self.assertEqual(p['summary']['valid'], 100)
        r = self.save(text, 'quiz', target)
        body = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(body['saved'], 100)
        self.assertEqual(len(self.store()), before + 100)

    def test_duplicates_detected_against_the_store(self):
        text = q(1, 'مكرر مخزن')
        target = {'category_id': 'science'}
        self.save(text, 'quiz', target)
        p = self.parse(text, 'quiz', target).get_json()
        self.assertEqual(p['summary']['duplicates'], 1)
        self.assertEqual(p['records'][0]['duplicate']['kind'], 'store')

    def test_letters_batch_with_letter_rule(self):
        before = len(self.store())
        # حرف الفاء: «الفهد» صحيحة و«الصحراء» تبدأ بالصاد — تُرفض
        text = ('س1: ما أسرع حيوان بري؟\nج1: الفهد\n\n'
                'س2: ما أكبر صحراء في العالم؟\nج2: الصحراء\n')
        r = self.save(text, 'letters', {'letter': 'ف'})
        body = r.get_json()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(body['saved'], 0)
        self.assertEqual(len(self.store()), before)
        self.assertEqual(len(body['rejected']), 1)
        fixed = 'س1: ما أسرع حيوان بري؟\nج1: الفهد'
        r2 = self.save(fixed, 'letters', {'letter': 'ف'})
        self.assertEqual(r2.get_json()['saved'], 1)
        got = self.client.get('/api/questions?game=letters&letter=%D9%81&per_page=50',
                              headers=H).get_json()
        self.assertTrue(any(x['answer'] == 'الفهد' for x in got['questions']))

    def test_million_batch(self):
        before = len(self.store())
        text = ('س1: ما الحيوان الملقب بسفينة الصحراء؟\n'
                'خيارات: الحصان | الجمل | الفيل | الغزال\nج1: ب\n\n'
                'س2: كم عدد الكواكب؟\nخيارات: سبعة | ثمانية | تسعة | عشرة\nج2: ثمانية')
        p = self.parse(text, 'million', {}).get_json()
        self.assertEqual(p['summary']['valid'], 2)
        r = self.save(text, 'million', {})
        self.assertEqual(r.get_json()['saved'], 2)
        self.assertEqual(len(self.store()), before + 2)
        items = [x for x in self.store() if x.get('game') == 'million'
                 and x['question'].startswith('ما الحيوان الملقب')]
        self.assertEqual(items[0]['answer'], 'الجمل')
        self.assertEqual(len(items[0]['options']), 4)

    def test_lastone_batch_appends_to_category(self):
        path = server.LASTONE_FILE
        with open(path, 'rb') as f:
            original = f.read()
        try:
            data = json.loads(original.decode('utf-8'))
            cat = sorted(data.keys())[0]
            n0 = len(data[cat])
            # unique answers, so the batch is not flagged as a duplicate
            text = 'زوركوف اختبار\nميترنيتش اختبار'
            r = self.save(text, 'lastone', {'category_name': cat})
            self.assertEqual(r.status_code, 200, r.get_json())
            with open(path, encoding='utf-8') as f:
                data2 = json.load(f)
            self.assertEqual(len(data2[cat]), n0 + 2)
        finally:
            with open(path, 'wb') as f:
                f.write(original)

    def test_content_game_batch(self):
        with open(CONTENT_FILE, encoding='utf-8') as f:
            before = json.load(f)
        used = {x.get('word') for x in before}
        cands = [w for w in ['غيمة', 'تنين', 'مروحة', 'قلعة', 'قمر', 'نخلة',
                             'سيف', 'بستان'] if w not in used]
        w1, w2 = cands[0], cands[1]
        text = ('س1:\nالكلمة: %s\nالمعنى: معنى أول\nالتصنيف: اختبار\n'
                'مترابطة: أ | ب\n\n'
                'س2:\nالكلمة: %s\nالمعنى: معنى ثانٍ\n' % (w1, w2))
        p = self.parse(text, 'codenames', {}).get_json()
        self.assertEqual(p['summary']['valid'], 2)
        r = self.save(text, 'codenames', {})
        self.assertEqual(r.get_json()['saved'], 2)
        with open(CONTENT_FILE, encoding='utf-8') as f:
            after = json.load(f)
        self.assertEqual(len(after), len(before) + 2)

    def test_history_is_recorded(self):
        self.save(q(2, 'السجل'), 'quiz', {'category_id': 'science'})
        h = self.client.get('/api/import/history', headers=H).get_json()['history']
        self.assertTrue(h)
        self.assertEqual(h[0]['saved'], 2)
        self.assertEqual(h[0]['game'], 'quiz')

    def test_template_and_export(self):
        t = self.client.get('/api/import/template?game=quiz&category=العلوم')
        self.assertIn('س1:', t.get_data(as_text=True))
        p = self.parse(q(2, 'تصدير'), 'quiz', {'category_id': 'science'}).get_json()
        e = self.client.post('/api/import/export', headers=H,
                             data=json.dumps({'records': p['records'], 'format': 'csv'}))
        self.assertIn('question', e.get_data(as_text=True))
        j = self.client.post('/api/import/export', headers=H,
                             data=json.dumps({'records': p['records'], 'format': 'json'}))
        self.assertEqual(j.get_json()['count'], 2)

    def test_import_is_admin_guarded(self):
        r = self.client.post('/api/import/parse',
                             data=json.dumps({'text': 'س1: س', 'game': 'quiz'}))
        self.assertEqual(r.status_code, 401)

    def test_unknown_game_rejected(self):
        r = self.client.post('/api/import/save', headers=H,
                             data=json.dumps({'game': 'nope', 'target': {},
                                              'records': [{'question': 'س', 'answer': 'ج'}]}))
        self.assertEqual(r.status_code, 400)

    def test_draft_roundtrip(self):
        self.client.post('/api/import/draft', headers=H,
                         data=json.dumps({'game': 'quiz', 'target': {'category_id': 'science'},
                                          'text': 'س1: مسودة؟\nج1: جواب'}))
        d = self.client.get('/api/import/draft', headers=H).get_json()
        self.assertEqual(d['text'], 'س1: مسودة؟\nج1: جواب')
        self.client.post('/api/import/draft', headers=H,
                         data=json.dumps({'game': '', 'target': {}, 'text': ''}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
