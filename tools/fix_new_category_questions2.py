# -*- coding: utf-8 -*-
"""Second pass: the remaining factual errors in the new-category questions.

Matches on the question OR the answer — three of the bad rows had the giveaway
in the answer («أرزة نيموترون», «الدب الأكبر», «الدورة الشهرية»).
"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server as S

# (substring found in the question or the answer, new question, new answer)
FIX = [
    ('نيموترون',
     'ما اسم الشجرة المعمرة المعروفة في لبنان والتي تُستخدم أخشابها في البناء؟',
     'الأرز'),
    ('الدب الأكبر',
     'ما هو اسم الكوكبة التي تحتوي على النجمة القطبية؟',
     'الدب الأصغر'),
    ('الدورة الشهرية',
     'ما اسم الظاهرة الفلكية التي يتكرر فيها اكتمال القمر كل 29.5 يوم تقريباً؟',
     'الشهر القمري'),
    ('بومبيي',
     'ما اسم المدينة الأثرية التي دُمرت بثوران جبل فيزوف عام 79م وحُفظت تحت الرماد؟',
     'بومبي'),
    ('الجائزة الكبرى موناكو',
     'ما اسم الحلبة الحضرية الأشهر في سباقات الفورمولا 1؟',
     'مونت كارلو'),
    ('PVC',
     'ماذا يعني الرمز المطبوع على المنتجات البلاستيكية والمكوّن من ثلاثة أهمّة متصلة؟',
     'قابل لإعادة التدوير'),
]


def main():
    d = S.load_json(S.Q_FILE, [])
    used = set()
    fixed = 0
    out = []
    for q in d:
        t = str(q.get('question', ''))
        a = str(q.get('answer', ''))
        hit = None
        for sub, nq, na in FIX:
            if sub not in used and (sub in t or sub in a):
                hit = (nq, na)
                used.add(sub)
                break
        if hit:
            q['question'], q['answer'] = hit[0], hit[1]
            q['updated_at'] = S.now()
            fixed += 1
        out.append(q)
    S.save_json(S.Q_FILE, out)
    print('fixed %d / %d' % (fixed, len(FIX)))
    print('NOT MATCHED:', [s for s, _, _ in FIX if s not in used])
    print('bank', len(out))


if __name__ == '__main__':
    main()
