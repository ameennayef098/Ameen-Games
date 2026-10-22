#!/usr/bin/env python3
"""تنظيف بنك «مين في بالي؟» بعد التوليد.

The model is good at facts and bad at packaging: it returns names with
parenthetical notes, transliterates Western names into Arabic script, splits
one person into two spellings, and writes a whole sentence into `subcategory`.
This pass repairs what is repairable and drops what is not.
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

import server  # noqa: E402

FILE = server.content_file('minebali')

# Names that cannot be repaired.
DROP = {
    'باونتي هانتر (ساموس آران مستبعد، بديل: رايدن)',
    'بوكيمون بيكاتشو',
    'آانغ',
    'كولومبو',
}

# One person, two spellings — keep the Arabic form.
MERGE = {
    'حسن بن الهيثم': 'الحسن بن الهيثم',
    'كريتوس': 'كراتوس',
    'إيزيكييل': 'كراتوس',
}

# Repairable name problems.
NAME_FIX = {
    'إل (L)': 'إل',
    'نairobi': 'نيروبي',
    'ليوناردو ديكابrio': 'ليوناردو دي كابريو',
    'غوغلييلمو ماركوني': 'غولييلمو ماركوني',
    'ناساو دنيس غابور': 'دينيس غابور',
    'سكويدويد تينتاكلز': 'سكويدوارد',
    'ساندى تشيكز': 'ساندي تشيز',
    'جيري ماوس': 'جيري',
    'دافي داك': 'دافي داك',
    'تويتى بيرد': 'تويتي',
    'آلادين': 'علاء الدين',
    'سونيك القنفذ': 'سونيك',
    'سوليد سنيك': 'سنيك',
    'كلود سترايف': 'كلود',
    'إيزيو أوديتوري': 'إيزيو',
    'جيرالت أوف ريفيا': 'جيرالت',
    'إيلي ويليامز': 'إيلي',
}

# A short, human subcategory for the rows that got a sentence instead.
SUBCAT_FIX = {
    'ثابت بن قرة': 'رياضيات وفلك',
    'الحسن بن الهيثم': 'بصريات وفيزياء',
    'الزهراوي': 'جراحة وطب',
    'ماكس بلانك': 'فيزياء نظرية',
    'نيلز بور': 'فيزياء ذرية',
    'إروين شرودنغر': 'فيزياء كمومية',
    'فيرنر هايزنبرغ': 'ميكانيكا الكم',
    'ريتشارد فاينمان': 'فيزياء الجسيمات',
    'دينيس غابور': 'فيزياء وهندسة',
    'ويليام شوكلي': 'فيزياء وإلكترونيات',
    'فنتون سيرف': 'علم الحاسوب',
    'شريك': 'دريم ووركس',
    'سكوبي دو': 'هانا-باربيرا',
    'باز لايت يير': 'قصة لعبة',
    'سونيك': 'ألعاب الفيديو',
    'كراتوس': 'ألعاب الفيديو',
    'بايلورث': 'ألعاب تقمص أدوار',
    'سنيك': 'ميتال غير سوليد',
    'كلود': 'فانتازي 7',
    'إيزيو': 'يوبسوفت',
    'ناثان دريك': 'سوني',
    'جيرالت': 'سي دي بروجكت ريد',
    'ألويا': 'سوني',
    'لينك': 'نينتندو',
    'ساموس آران': 'نينتندو',
    'جوردون فريمان': 'فالف',
    'آرثر مورغان': 'ريد ديد ريدمبشن',
    'إيلي': 'ذا لاست أوف أس',
    'كاسومي': 'ديد أو ألايف',
    'تشون لي': 'ستريت فايتر',
    'دانتي': 'ديفل ماي كراي',
    'سيلور مون': 'أنمي ومانجا',
    'هومر سيمبسون': 'السيمبسونز',
    'شين تشان': 'كرايون شين تشان',
    'علاء الدين': 'ديزني',
    'مولان': 'ديزني',
    'ميكي ماوس': 'ديزني',
    'باغز باني': 'لوني تونز',
    'تويتي': 'لوني تونز',
}

# Nisba / laqab tails to strip when a name runs long.
TAIL_WORDS = {'التميمي', 'الأسدي', 'الزهري', 'العدوي', 'المخزومي', 'الحبشي',
              'الخزرجي', 'الصديق', 'القرشي', 'الأموي', 'العباسي'}


def shorten(name):
    parts = name.split()
    while len(parts) > 4 and parts[-1] in TAIL_WORDS:
        parts = parts[:-1]
    if len(parts) > 4:
        parts = parts[:4]
    return ' '.join(parts)


def main():
    items = json.load(open(FILE, encoding='utf-8'))
    before = len(items)
    kept, dropped, renamed = [], [], []

    for c in items:
        n = str(c.get('name', '')).strip()
        if n in DROP:
            dropped.append(n)
            continue
        # mixed Arabic+Latin inside one name = unusable
        if re.search(r'[A-Za-z]{3,}', n):
            dropped.append(n + '  (حروف لاتينية)')
            continue
        if n in MERGE:
            n = MERGE[n]
        if n in NAME_FIX:
            new = NAME_FIX[n]
            if new != n:
                renamed.append(n + ' <- ' + new)
            n = new
        if len(n.split()) > 4:
            n = shorten(n)
        c['name'] = n

        if n in SUBCAT_FIX:
            c['subcategory'] = SUBCAT_FIX[n]
        else:
            s = str(c.get('subcategory', '') or '').split('،')[0].split(',')[0].strip()
            if s:
                c['subcategory'] = s
        kept.append(c)

    # fold first-token duplicates, keeping the richer record
    seen, final = {}, []
    for c in kept:
        key = 'first:' + server.norm_ar(c['name']).split(' ')[0]
        if key in seen:
            def score(x):
                return sum(1 for k in ('subcategory', 'work', 'field', 'role')
                           if str(x.get(k, '')).strip())
            if score(c) > score(seen[key]):
                final[final.index(seen[key])] = c
                seen[key] = c
            dropped.append(c['name'] + '  (مكرر)')
            continue
        seen[key] = c
        final.append(c)

    with open(FILE, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print('before:', before, '-> after:', len(final))
    print('renamed %d:' % len(renamed))
    for r in renamed:
        print('   ~', r)
    print('dropped %d:' % len(dropped))
    for d in dropped:
        print('   -', d)
    from collections import Counter
    for cat, n in Counter(c.get('category') for c in final).most_common():
        print('  %-24s %d' % (cat, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
