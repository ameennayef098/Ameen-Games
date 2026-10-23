# -*- coding: utf-8 -*-
"""اختبارات محلل دفعات الأسئلة (qimport.py) — بلا Flask وبلا شبكة.

شغّلها هكذا:
    python tools/test_qimport.py
أو:
    python -m unittest tools.test_qimport -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import qimport as qi


def recs(text, game, target=None):
    return qi.parse_batch(text, game, target)['records']


def one(text, game, target=None):
    r = recs(text, game, target)
    assert len(r) == 1, 'expected exactly one record, got %d' % len(r)
    return r[0]


class TestBasicParsing(unittest.TestCase):
    def test_1_three_valid_questions(self):
        text = ('س1: ما الكوكب المعروف بالكوكب الأحمر؟\nج1: المريخ\n\n'
                'س2: ما الغاز الذي تمتصه النباتات؟\nج2: ثاني أكسيد الكربون\n\n'
                'س3: ما وحدة قياس شدة التيار؟\nج3: الأمبير\n')
        out = qi.parse_batch(text, 'quiz', {'category_id': 'science', 'category_name': 'العلوم'})
        self.assertEqual(out['summary']['detected'], 3)
        self.assertEqual(out['summary']['valid'], 3)
        self.assertEqual(out['summary']['problems'], 0)
        self.assertEqual(out['records'][0]['question'], 'ما الكوكب المعروف بالكوكب الأحمر؟')
        self.assertEqual(out['records'][0]['answer'], 'المريخ')

    def test_2_hundred_questions_one_paste(self):
        lines = []
        for i in range(1, 101):
            lines.append('س%d: سؤال رقم %d؟' % (i, i))
            lines.append('ج%d: جواب %d' % (i, i))
        text = '\n\n'.join(lines)
        out = qi.parse_batch(text, 'quiz', {'category_id': 'science', 'category_name': 'العلوم'})
        self.assertEqual(out['summary']['detected'], 100)
        self.assertEqual(out['summary']['valid'], 100)
        self.assertEqual(out['summary']['to_add'], 100)
        self.assertEqual(out['records'][-1]['num'], 100)

    def test_3_large_batch_250(self):
        lines = []
        for i in range(1, 251):
            lines.append('السؤال %d: نص السؤال %d' % (i, i))
            lines.append('الإجابة %d: نص الجواب %d' % (i, i))
        out = qi.parse_batch('\n'.join(lines), 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['detected'], 250)
        self.assertEqual(out['summary']['valid'], 250)
        self.assertEqual(out['records'][0]['question'], 'نص السؤال 1')
        self.assertEqual(out['records'][0]['answer'], 'نص الجواب 1')

    def test_4_blank_lines_between_records(self):
        text = ('س1: سؤال أول؟\n\n\nج1: جواب أول\n\n\n\n'
                'س2: سؤال ثانٍ؟\n\nج2: جواب ثانٍ\n')
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['detected'], 2)
        self.assertEqual(out['summary']['valid'], 2)

    def test_5_missing_answer(self):
        text = 'س1: سؤال له جواب؟\nج1: الجواب\n\nس2: سؤال بلا جواب؟\n\nس3: سؤال ثالث؟\nج3: ثالث'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['incomplete'], 1)
        self.assertEqual(out['records'][1]['status'], 'incomplete')
        codes = [w['code'] for w in out['records'][1]['warnings']]
        self.assertIn('no_answer', codes)

    def test_6_answer_without_question(self):
        out = qi.parse_batch('ج1: جواب بلا سؤال', 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['orphan'], 1)
        self.assertEqual(out['records'][0]['status'], 'orphan')

    def test_7_non_sequential_numbering(self):
        text = ('س5: سؤال خامس؟\nج5: جوابه\n\n'
                'س9: سؤال تاسع؟\nج9: جوابه\n\n'
                'س12: سؤال ثاني عشر؟\nج12: جوابه\n')
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['valid'], 3)
        self.assertEqual([r['num'] for r in out['records']], [5, 9, 12])
        codes = [w['code'] for w in out['warnings']]
        self.assertIn('numbering', codes)

    def test_8_duplicate_number_kept(self):
        text = 'س1: سؤال أول؟\nج1: أول\n\nس1: سؤال ثانٍ بنفس الرقم؟\nج1: ثانٍ'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['detected'], 2)
        codes = [w['code'] for w in out['records'][1]['warnings']]
        self.assertIn('duplicate_number', codes)

    def test_9_duplicates_against_store(self):
        text = 'س1: ما  capital of France؟\n'.replace(' capital of France', 'عاصمة فرنسا')
        text += 'ج1: باريس'
        existing = {qi.record_key('quiz', {'question': 'ما عاصمة فرنسا؟'})}
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        qi.detect_duplicates(out['records'], 'quiz', existing)
        self.assertEqual(out['records'][0]['duplicate']['kind'], 'store')

    def test_10_mixed_arabic_english(self):
        # English element symbols are legitimate in the science curriculum.
        text = ('س1: ما الرمز الكيميائي للحديد؟\nج1: Fe\n\n'
                'س2: ما وحدة قياس الطول في النظام الدولي؟\nج2: المتر\n')
        out = qi.parse_batch(text, 'quiz', {'category_id': 'science'})
        self.assertEqual(out['summary']['valid'], 2)

    def test_11_multiword_answer_and_punctuation(self):
        rec = one('س1: متى انتهت الحرب العالمية الثانية؟\nج1: في عام 1945م.', 'quiz',
                  {'category_id': 'history'})
        self.assertEqual(rec['answer'], 'في عام 1945م.')
        self.assertEqual(rec['status'], 'ok')

    def test_12_multiline_question_and_answer(self):
        text = ('س1: ما هي العوامل الثلاثة التي تؤثر في\nسرعة التفاعل الكيميائي؟\n'
                'ج1: التركيز، ودرجة الحرارة،\nومساحة السطح')
        rec = one(text, 'quiz', {'category_id': 'science'})
        self.assertIn('سرعة التفاعل الكيميائي؟', rec['question'])
        self.assertIn('التركيز', rec['answer'])
        self.assertIn('مساحة السطح', rec['answer'])

    def test_numbering_variants(self):
        for text in ('س1: س؟\nج1: ج', 'س 1: س؟\nج 1: ج', 'السؤال 1: س؟\nالإجابة 1: ج',
                     'Question 1: س؟\nAnswer 1: ج', 'Q1: س؟\nA1: ج',
                     'س1 - س؟\nج1 - ج', 'س1) س؟\nج1) ج',
                     'س1: س؟ ج1: ج'):
            out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
            self.assertEqual(out['summary']['valid'], 1, 'failed on: ' + repr(text))
            self.assertEqual(out['records'][0]['status'], 'ok', 'failed on: ' + repr(text))

    def test_arabic_indic_digits(self):
        out = qi.parse_batch('س١: سؤال؟\nج١: جواب', 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['valid'], 1)
        self.assertEqual(out['records'][0]['num'], 1)

    def test_plain_words_not_mistaken_for_markers(self):
        # «جملة» and «سؤال» inside a sentence must not split the record.
        text = 'س1: ما معنى جملة مفيدة؟\nج1: جملة لها معنى'
        rec = one(text, 'quiz', {'category_id': 'sports'})
        self.assertEqual(rec['question'], 'ما معنى جملة مفيدة؟')
        self.assertEqual(rec['answer'], 'جملة لها معنى')

    def test_text_never_reworded(self):
        # only the surrounding whitespace is trimmed; the wording is untouched
        rec = one('س1:   سؤال طويل   فيه أسطر\n\nمتعددة   هنا  ؟   \n\n\nج1:    جواب   ',
                  'quiz', {'category_id': 'sports'})
        self.assertEqual(rec['question'], 'سؤال طويل   فيه أسطر\nمتعددة   هنا  ؟')
        self.assertEqual(rec['answer'], 'جواب')
        self.assertFalse(rec['question'].startswith(' '))
        self.assertFalse(rec['question'].endswith(' '))


class TestGameAdapters(unittest.TestCase):
    def test_letters_requires_letter_and_first_letter(self):
        out = qi.parse_batch('س1: ما أسرع حيوان بري؟\nج1: الفهد', 'letters', {'letter': 'ف'})
        self.assertEqual(out['summary']['valid'], 1)
        item, _ = qi.build_item('letters', out['records'][0], {'letter': 'ف'})
        self.assertEqual(item['letter'], 'ف')
        ok, err = qi.validate_item('letters', item)
        self.assertTrue(ok, err)

    def test_letters_wrong_letter_is_flagged(self):
        out = qi.parse_batch('س1: ما أسرع حيوان بري؟\nج1: الفهد', 'letters', {'letter': 'ب'})
        item, _ = qi.build_item('letters', out['records'][0], {'letter': 'ب'})
        ok, err = qi.validate_item('letters', item)
        self.assertFalse(ok)
        self.assertIn('الحرف', err)

    def test_quiz_category_is_mandatory(self):
        out = qi.parse_batch('س1: سؤال؟\nج1: جواب', 'quiz', {})
        self.assertEqual(out['records'][0]['status'], 'needs_review')

    def test_million_needs_four_options(self):
        text = ('س1: ما الحيوان الملقب بسفينة الصحراء؟\n'
                'خيارات: الحصان | الجمل | الفيل | الغزال\nج1: ب')
        out = qi.parse_batch(text, 'million', {})
        item, _ = qi.build_item('million', out['records'][0], {})
        self.assertEqual(item['options'], ['الحصان', 'الجمل', 'الفيل', 'الغزال'])
        self.assertEqual(item['answer'], 'الجمل')  # option letter resolved to text
        ok, err = qi.validate_item('million', item)
        self.assertTrue(ok, err)

    def test_million_missing_option_fails(self):
        text = 'س1: سؤال؟\nخيارات: أ | ب | ج\nج1: أ'
        out = qi.parse_batch(text, 'million', {})
        item, _ = qi.build_item('million', out['records'][0], {})
        ok, err = qi.validate_item('million', item)
        self.assertFalse(ok)

    def test_quiz_points_from_target_and_from_record(self):
        out = qi.parse_batch('س1: سؤال؟\nج1: جواب\nنقاط: 400', 'quiz',
                             {'category_id': 'sports', 'points': 200})
        item, _ = qi.build_item('quiz', out['records'][0], {'category_id': 'sports'})
        self.assertEqual(item['points'], 400)   # record wins over the target

    def test_lastone_lines_mode(self):
        out = qi.parse_batch('السعودية\nمصر\n\nالأردن', 'lastone', {'category_name': 'دول العالم'})
        self.assertEqual(out['summary']['detected'], 3)
        self.assertEqual(out['summary']['valid'], 3)
        self.assertEqual(out['records'][0]['answer'], 'السعودية')

    def test_lastone_requires_category(self):
        out = qi.parse_batch('السعودية', 'lastone', {})
        self.assertEqual(out['records'][0]['status'], 'needs_review')

    def test_codenames_fields(self):
        text = ('س1:\nالكلمة: صقر\nالمعنى: طائر جارح\nالتصنيف: حيوانات\n'
                'مترابطة: نسر | عقاب | شاهين\n\n'
                'س2:\nالكلمة: مفتاح\n- المعنى: أداة تفتح الأقفال\n- التصنيف: أدوات')
        out = qi.parse_batch(text, 'codenames', {})
        self.assertEqual(out['summary']['valid'], 2)
        item, _ = qi.build_item('codenames', out['records'][0], {})
        self.assertEqual(item['word'], 'صقر')
        self.assertEqual(item['related'], ['نسر', 'عقاب', 'شاهين'])
        ok, err = qi.validate_item('codenames', item)
        self.assertTrue(ok, err)
        item2, _ = qi.build_item('codenames', out['records'][1], {})
        self.assertEqual(item2['meaning'], 'أداة تفتح الأقفال')   # bullet lines

    def test_link_fields(self):
        text = 'س1:\nالعناصر: تفاح | موز | برتقال\nالرابط: فواكه\nج1: الفواكه'
        out = qi.parse_batch(text, 'link', {})
        item, _ = qi.build_item('link', out['records'][0], {})
        self.assertEqual(len(item['items']), 3)
        ok, err = qi.validate_item('link', item)
        self.assertTrue(ok, err)

    def test_whoplayer_needs_three_hints(self):
        text = 'س1:\nاللاعب: محمد صلاح\nالتلميحات: أفريقى | يمين | إنجليزي | مصري'
        out = qi.parse_batch(text, 'whoplayer', {})
        item, _ = qi.build_item('whoplayer', out['records'][0], {})
        ok, err = qi.validate_item('whoplayer', item)
        self.assertTrue(ok, err)

    def test_detective_nested_items(self):
        text = ('س1:\nالعنوان: سرقة المعمل\n'
                'الشخصيات: اسم: أحمد ، دور: مشرف ، قول: غادرت | اسم: سارة ، دور: طالبة ، قول: رأيته | اسم: خالد ، دور: حارس ، قول: مغلق\n'
                'الأدلة: معرف: d1 ، نص: باب مفتوح ، مخفي: لا | معرف: d2 ، نص: كاميرا ، مخفي: لا | معرف: d3 ، نص: مفتاح مفقود ، مخفي: نعم | معرف: d4 ، نص: طين ، مخفي: نعم\n'
                'الحل: خالد استخدم المفتاح')
        out = qi.parse_batch(text, 'detective', {})
        item, _ = qi.build_item('detective', out['records'][0], {})
        self.assertEqual(len(item['characters']), 3)
        self.assertEqual(len(item['evidence']), 4)
        self.assertIs(item['evidence'][2]['hidden'], True)
        ok, err = qi.validate_item('detective', item)
        self.assertTrue(ok, err)

    def test_minebali_boolean_coercion(self):
        text = ('س1:\nالاسم: صلاح الدين\nالجنس: ذكر\nحقيقية: نعم\nرئيسية: نعم\n'
                'قدرات: لا\nالمجال: قائد\nالفئة: تاريخيات')
        out = qi.parse_batch(text, 'minebali', {})
        item, _ = qi.build_item('minebali', out['records'][0], {})
        self.assertIs(item['real'], True)
        self.assertIs(item['powers'], False)
        ok, err = qi.validate_item('minebali', item)
        self.assertTrue(ok, err)

    def test_minebali_bad_gender_rejected(self):
        text = 'س1:\nالاسم: فلان\nالجنس: غير ذلك\nحقيقية: لا\nرئيسية: لا\nقدرات: لا\nالمجال: فلان'
        out = qi.parse_batch(text, 'minebali', {})
        item, _ = qi.build_item('minebali', out['records'][0], {})
        ok, err = qi.validate_item('minebali', item)
        self.assertFalse(ok)

    def test_auction_numeric_coercion(self):
        text = 'س1:\nالاسم: فينيسيوس جونيور\nالتقييم: 88\nالسرعة: 92'
        out = qi.parse_batch(text, 'auction', {})
        item, _ = qi.build_item('auction', out['records'][0], {})
        self.assertEqual(item['rating'], 88)
        self.assertEqual(item['pace'], 92)

    def test_no_options_fabricated(self):
        # a schema that needs options must never get invented ones
        out = qi.parse_batch('س1: سؤال؟\nج1: جواب', 'million', {})
        item, _ = qi.build_item('million', out['records'][0], {})
        self.assertEqual(item['options'], [])


class TestDuplicates(unittest.TestCase):
    def test_within_batch(self):
        text = 'س1: سؤال مكرر؟\nج1: أ\n\nس2: سؤال مكرر؟\nج2: ب'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        qi.detect_duplicates(out['records'], 'quiz', set())
        self.assertIsNone(out['records'][0]['duplicate'])
        self.assertEqual(out['records'][1]['duplicate']['kind'], 'batch')
        self.assertEqual(out['summary']['duplicates'], 0)   # summary is pre-dedupe

    def test_question_matching_existing_answer(self):
        text = 'س1: المريخ\nج1: كوكب أحمر'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        qi.detect_duplicates(out['records'], 'quiz', set(), {'المريخ'})
        self.assertEqual(out['records'][0]['duplicate']['kind'], 'answer')

    def test_normalisation_ignores_formatting(self):
        # norm_ar collapses whitespace and unifies alef/taa marbuta, so the same
        # question written two ways yields one key.  («؟» is deliberately kept —
        # the production q_key in server.py behaves the same way.)
        a = qi.record_key('quiz', {'question': 'ما  عاصمة   فرنسا'})
        b = qi.record_key('quiz', {'question': 'ما عاصمة فرنسا'})
        self.assertEqual(a, b)
        c = qi.record_key('quiz', {'question': 'ما عاصمه فرنسا'})
        self.assertEqual(a, c)
        self.assertNotEqual(a, qi.record_key('quiz', {'question': 'ما عاصمة فرنسا العاصمة'}))

    def test_excluded_record_skipped_by_dedupe(self):
        text = 'س1: س؟\nج1: أ\n\nس2: س؟\nج2: ب'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        out['records'][0]['excluded'] = True
        qi.detect_duplicates(out['records'], 'quiz', set())
        self.assertIsNone(out['records'][0]['duplicate'])
        self.assertIsNone(out['records'][1]['duplicate'])

    def test_duplicates_never_deleted(self):
        # detection only flags; nothing is removed from the record list
        text = 'س1: س؟\nج1: أ\n\nس2: س؟\nج2: ب'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'sports'})
        qi.detect_duplicates(out['records'], 'quiz', set())
        self.assertEqual(len(out['records']), 2)


class TestEdgeCases(unittest.TestCase):
    def test_empty_text(self):
        out = qi.parse_batch('   \n\n ', 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['detected'], 0)

    def test_preamble_is_reported_not_guessed(self):
        text = '# أسئلة العلوم\nمن إعداد المعلم\n\nس1: سؤال؟\nج1: جواب'
        out = qi.parse_batch(text, 'quiz', {'category_id': 'science'})
        self.assertEqual(out['summary']['valid'], 1)
        self.assertTrue(any(w['code'] == 'preamble' for w in out['warnings']))
        self.assertEqual(len(out['unparsed']), 2)

    def test_unknown_game_raises(self):
        with self.assertRaises(ValueError):
            qi.parse_batch('س1: س؟\nج1: ج', 'nope', {})

    def test_over_max_records_is_truncated(self):
        lines = []
        for i in range(1, 601):
            lines.append('س%d: السؤال رقم %d؟' % (i, i))
            lines.append('ج%d: الجواب رقم %d' % (i, i))
        out = qi.parse_batch('\n'.join(lines), 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['summary']['detected'], 500)
        self.assertEqual(out['truncated'], 100)
        self.assertTrue(any(w['code'] == 'too_many' for w in out['warnings']))

    def test_template_always_returned(self):
        for game in qi.GAME_IMPORT_DEFS:
            self.assertTrue(qi.template_for(game, {}), 'no template for ' + game)

    def test_status_never_silently_ok_for_missing_answer(self):
        out = qi.parse_batch('س1: سؤال بلا إجابة؟\n', 'quiz', {'category_id': 'sports'})
        self.assertEqual(out['records'][0]['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main(verbosity=2)
