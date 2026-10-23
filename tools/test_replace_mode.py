# -*- coding: utf-8 -*-
"""اختبارات وضع الاستبدال في الاستيراد + لصق ملف JSON + توحيد الحرف.

تعمل على مخزن حقيقي لكنها تأخذ نسخة وتعيدها حرفياً في النهاية. كل اختبار
يبدأ من حالة معروفة (ثلاثة أسئلة حروف قديمة) لأن اختباراً قد يستبدل البنك.

شغّلها:  python tools/test_replace_mode.py
"""
import os
import sys
import json
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import server  # noqa: E402
import qimport as qi  # noqa: E402

Q_FILE = os.path.join(ROOT, 'data', 'questions', 'all.json')
HIST_FILE = os.path.join(ROOT, 'data', 'questions', 'import_history.json')
TOKEN = 'test-replace-token'
server.ADMIN_TOKENS.add(TOKEN)
H = {'X-Admin-Token': TOKEN, 'Content-Type': 'application/json'}
STORES = [Q_FILE, HIST_FILE]

# ملف JSON صغير يحاكي الذي يلصقه المستخدم: ثلاثة أسئلة لثلاثة أحرف
LETTERS_JSON = json.dumps([
    {"id": "x1", "game": "letters", "letter": "ف", "question": "ما أسرع حيوان بري؟",
     "answer": "الفهد", "difficulty": "medium", "status": "approved", "source": "manual"},
    {"id": "x2", "game": "letters", "letter": "ف", "question": "ما أكبر صحراء في العالم؟",
     "answer": "الفاتيكان", "difficulty": "hard", "status": "approved", "source": "manual"},
    {"id": "x3", "game": "letters", "letter": "بـ", "question": "ما أول سورة في المصحف؟",
     "answer": "البقرة", "difficulty": "easy", "status": "approved", "source": "manual"},
], ensure_ascii=False)

# نص «س/ج» بإجابات لا توجد في البنك، حتى لا يتداخل كشف التكرار مع الاختبار
LETTERS_TEXT = ('س1: ما ثمرة حمراء للاختبار؟\nج1: فراولة\n\n'
                'س2: ما مكسرات للاختبار؟\nج2: فستق')

OLD_LETTERS = [
    {'id': 'old1', 'game': 'letters', 'letter': 'ف', 'question': 'سؤال قديم ألف؟',
     'answer': 'فيل', 'difficulty': 'medium', 'status': 'approved', 'source': 'manual',
     'created_at': '2020-01-01T00:00:00'},
    {'id': 'old2', 'game': 'letters', 'letter': 'ف', 'question': 'سؤال قديم باء؟',
     'answer': 'بغل', 'difficulty': 'medium', 'status': 'approved', 'source': 'manual',
     'created_at': '2020-01-01T00:00:00'},
    {'id': 'old3', 'game': 'letters', 'letter': 'س', 'question': 'سؤال قديم سين؟',
     'answer': 'سمور', 'difficulty': 'medium', 'status': 'approved', 'source': 'manual',
     'created_at': '2020-01-01T00:00:00'},
]


class ReplaceModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = server.app.test_client()
        cls.snapshot = {}
        for p in STORES:
            cls.snapshot[p] = open(p, 'rb').read() if os.path.exists(p) else None

    @classmethod
    def tearDownClass(cls):
        for p, data in cls.snapshot.items():
            if data is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                open(p, 'wb').write(data)

    def setUp(self):
        self.store = lambda: json.load(open(Q_FILE, encoding='utf-8'))
        # حالة معروفة: فقط أسئلة الحروف الثلاثة القديمة
        server.save_json(Q_FILE, [q for q in self.store() if q.get('game') != 'letters']
                         + [dict(q) for q in OLD_LETTERS])

    def letters(self):
        return [q for q in self.store() if q.get('game') == 'letters']

    def canon(self, q):
        return server.canon_letter(q.get('letter'))

    # ------------------------------------------------------------------ parse
    def test_json_paste_is_detected(self):
        p = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'game': 'letters', 'text': LETTERS_JSON,
                                              'target': {}})).get_json()
        self.assertEqual(p['format'], 'json')
        self.assertEqual(p['summary']['detected'], 3)
        self.assertEqual(p['summary']['valid'], 3)
        self.assertEqual(p['records'][0]['question'], 'ما أسرع حيوان بري؟')
        self.assertEqual(p['records'][0]['merged']['letter'], 'ف')

    def test_json_envelope_object_is_accepted(self):
        wrapped = json.dumps({'questions': json.loads(LETTERS_JSON)}, ensure_ascii=False)
        p = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'game': 'letters', 'text': wrapped,
                                              'target': {}})).get_json()
        self.assertEqual(p['summary']['detected'], 3)

    def test_bad_json_is_reported_not_swallowed(self):
        r = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'game': 'letters',
                                              'text': '[{"question": "ناقص"'})).get_json()
        self.assertIn('error', r)
        self.assertIn('JSON', r['error'])

    def test_json_letter_with_tatweel_is_normalised(self):
        p = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'game': 'letters', 'text': LETTERS_JSON,
                                              'target': {}})).get_json()
        letters = {r['merged']['letter'] for r in p['records']}
        self.assertIn('ب', letters)          # «بـ» → «ب»
        self.assertNotIn('بـ', letters)

    def test_replace_mode_does_not_flag_store_duplicates(self):
        """في الاستبدال السجل المكرر هو من سيُستبدل، فمقارنته بالمخزن خطأ."""
        r = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'game': 'letters', 'text': LETTERS_TEXT,
                                              'target': {'letter': 'ف'},
                                              'mode': 'replace'})).get_json()
        self.assertEqual(r['summary']['duplicates'], 0)
        # نفس النص في وضع الإضافة: كلا السؤالين موجودان في البنك → مكرر
        self._save(LETTERS_TEXT, 'append', 'game', {'letter': 'ف'})
        r2 = self.client.post('/api/import/parse', headers=H,
                              data=json.dumps({'game': 'letters', 'text': LETTERS_TEXT,
                                               'target': {'letter': 'ف'}})).get_json()
        self.assertEqual(r2['summary']['duplicates'], 2)

    # ------------------------------------------------------------------ count
    def test_count_endpoint_reports_the_scope(self):
        game = self.client.get('/api/import/count?game=letters&scope=game', headers=H).get_json()
        self.assertEqual(game['deleted'], game['total'])
        self.assertEqual(game['deleted'], len(self.letters()))

        fa = self.client.get('/api/import/count?game=letters&scope=target&letter=%D9%81',
                             headers=H).get_json()
        old_fa = [q for q in self.letters() if self.canon(q) == 'ف']
        self.assertEqual(fa['deleted'], len(old_fa))
        self.assertEqual(fa['total'], len(self.letters()))

    def test_count_is_admin_guarded(self):
        r = self.client.get('/api/import/count?game=letters&scope=game')
        self.assertEqual(r.status_code, 401)

    # ------------------------------------------------------------------ save
    def _save(self, text, mode, scope='game', target=None, game='letters', idem=None):
        p = self.client.post('/api/import/parse', headers=H,
                             data=json.dumps({'game': game, 'text': text,
                                              'target': target or {}, 'mode': mode})).get_json()
        body = {'game': game, 'target': target or {}, 'records': p['records'],
                'keep_duplicates': [], 'mode': mode, 'scope': scope}
        if idem:
            body['idempotency_key'] = idem
        return self.client.post('/api/import/save', headers=H, data=json.dumps(body))

    def test_replace_game_swaps_the_whole_bank(self):
        before_other = [q['id'] for q in self.store() if q.get('game') != 'letters']
        before_n = len(self.letters())
        r = self._save(LETTERS_JSON, 'replace', 'game')
        body = r.get_json()
        self.assertEqual(r.status_code, 200, body)
        self.assertEqual(body['deleted'], before_n)
        self.assertEqual(body['saved'], 3)

        now = self.letters()
        self.assertEqual(len(now), 3)
        self.assertEqual({q['question'] for q in now},
                         {'ما أسرع حيوان بري؟', 'ما أكبر صحراء في العالم؟',
                          'ما أول سورة في المصحف؟'})
        self.assertFalse(any(q['id'].startswith('old') for q in now))
        # الألعاب الأخرى لم تُمسّ
        self.assertEqual([q['id'] for q in self.store() if q.get('game') != 'letters'],
                         before_other)

    def test_replace_scope_target_keeps_other_letters(self):
        before = self.letters()
        other = [q for q in before if self.canon(q) != 'ف']
        r = self._save(LETTERS_JSON, 'replace', 'target', {'letter': 'ف'})
        body = r.get_json()
        self.assertEqual(r.status_code, 200, body)
        self.assertEqual(body['scope'], 'target')
        self.assertEqual(body['deleted'], len(before) - len(other))
        kept = [q for q in self.letters() if self.canon(q) != 'ف']
        # بقي الحرف الآخر القديم + سؤال الباء الجديد
        self.assertEqual(len(kept), len(other) + 1)
        self.assertTrue(any(q['question'] == 'سؤال قديم سين؟' for q in kept))

    def test_append_mode_is_unchanged(self):
        before = len(self.letters())
        r = self._save(LETTERS_JSON, 'append', 'game')
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(len(self.letters()), before + 3)

    def test_replace_mode_is_idempotent(self):
        self._save(LETTERS_JSON, 'replace', 'game', idem='replace-once')
        n = len(self.letters())
        r = self._save(LETTERS_JSON, 'replace', 'game', idem='replace-once')
        self.assertTrue(r.get_json().get('cached'))
        self.assertEqual(len(self.letters()), n)

    def test_failed_batch_in_replace_mode_writes_nothing(self):
        """سجل واحد غير صالح يمنع الحذف والإضافة معاً — لا دفعة جزئية."""
        bad = json.dumps(json.loads(LETTERS_JSON) +
                         [{"game": "letters", "letter": "ف",
                           "question": "سؤال بلا إجابة؟"}], ensure_ascii=False)
        before = self.store()
        r = self._save(bad, 'replace', 'game')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.store(), before)

    def test_unknown_mode_rejected(self):
        r = self.client.post('/api/import/save', headers=H,
                             data=json.dumps({'game': 'letters', 'target': {},
                                              'records': [{'question': 'س', 'answer': 'ج'}],
                                              'mode': 'drop-everything'}))
        self.assertEqual(r.status_code, 400)

    # ------------------------------------------------------- old file importer
    def test_legacy_file_import_replace(self):
        r = self.client.post('/api/questions/import', headers=H, data=json.dumps({
            'questions': json.loads(LETTERS_JSON), 'mode': 'apply', 'replace': True})).get_json()
        self.assertEqual(r['new_count'], 3)
        self.assertEqual(r['removed'], 3)
        self.assertEqual(len(self.letters()), 3)          # استبدال كامل

        r2 = self.client.post('/api/questions/import', headers=H, data=json.dumps({
            'questions': json.loads(LETTERS_JSON), 'mode': 'apply'})).get_json()
        self.assertEqual(r2['duplicate_count'], 3)        # الإضافة بلا استبدال
        self.assertEqual(len(self.letters()), 3)

    # ------------------------------------------------------------- normaliser
    def test_canon_letter_matches_first_letter_of(self):
        for ans, letter in [('الفهد', 'ف'), ('أبو بكر', 'أ'), ('ألكسندر', 'ك'),
                            ('هرم', 'هـ'), ('اسلام', 'ا'), ('إديسون', 'إ')]:
            self.assertEqual(qi.first_letter_of(ans), qi.canon_letter(letter),
                             '%s / %s' % (ans, letter))

    def test_letter_list_has_no_tatweel_form(self):
        self.assertIn('ه', qi.AR_LETTERS)
        self.assertNotIn('هـ', qi.AR_LETTERS)
        self.assertEqual(len(qi.AR_LETTERS), 28)


if __name__ == '__main__':
    unittest.main(verbosity=2)
