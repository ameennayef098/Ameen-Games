#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill categories to a target (existing categories get extended, brand-new
categories are created). Drives tools/bulk_gen.py, whose validate/build
functions are imported so the SAME rules the Flask server uses apply here.

Existing categories (extend the bank that is already there):
    python tools/fill_categories.py --mode extend --target 320

New categories (create the category rows, then fill them):
    python tools/fill_categories.py --mode new --new-cats 24 --target 420

Both:
    python tools/fill_categories.py --mode both --target 320 --new-cats 24 --target-new 420
"""
import argparse
import json
import os
import re
import sys
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))

import bulk_gen as B  # noqa: E402

CATFILE = B.CATFILE
QFILE = B.QFILE


# ---------------------------------------------------------------- new categories
# id, name, description, colour, icon, topic axes (fed to the model so it
# spreads questions across sub-topics instead of clustering on one).
NEW_CATEGORIES = [
    ('space_missions', 'رحلات الفضاء واكتشافه',
     'أسئلة عن رحلات الفضاء والصواريخ والمركبات الفضائية واكتشاف الفضاء',
     '#38bdf8', '🛰️',
     'الصواريخ، المركبات الفضائية، المحطات الفضائية، الأقمار الصناعية، الرواد، المهمات إلى القمر والمريخ'),
    ('football_arab', 'كرة القدم العربية',
     'أسئلة عن كرة القدم العربية: المنتخبات والأندية والبطولات العربية واللاعبون العرب',
     '#22c55e', '🏆',
     'المنتخبات العربية، الأندية الخليجية، الأندية المصرية، دوري أبطال آسيا، كأس العرب، اللاعبون العرب'),
    (' football_world'.strip(), 'كرة القدم العالمية',
     'أسئلة عن كرة القدم العالمية: الدوريات الأوروبية والأندية الكبرى والبطولات الدولية',
     '#16a34a', '🌍',
     'الدوريات الأوروبية، الأندية الكبرى، كأس العالم، الدوريات الإنجليزية والإسبانية، الأرقام القياسية'),
    ('kingdom', 'المملكة العربية السعودية',
     'أسئلة عن المملكة العربية السعودية: تاريخها وجغرافياها ومدنها ومبادراتها',
     '#0d9488', '🇸🇦',
     'التاريخ السعودي، المدن، المحافظات، رؤية 2030، الآثار، الاقتصاد، الجغرافيا'),
    ('anime', 'الأنمي والمانجا',
     'أسئلة عن الأنمي والمانجا اليابانية المشهورة',
     '#e11d48', '🌸',
     'هجوم العمالقة، ون بيس، ناروتو، سينين كيميتسو، المحقق كونان، أسماء المانغاكا، الاستوديوهات'),
    ('novels', 'الروايات والكتب',
     'أسئلة عن الروايات والكتب المشهورة عربياً وعالمياً',
     '#92400e', '📖',
     'الروايات العربية الكلاسيكية، الروايات العالمية، الكتّاب، الشخصيات الأدبية، الجوائز الأدبية'),
    ('world_wars', 'الحروب والنزاعات',
     'أسئلة عن الحروب والنزاعات عبر التاريخ وأسبابها ونتائجها',
     '#7f1d1d', '⚔️',
     'الحرب العالمية الأولى، الحرب العالمية الثانية، الحروب القديمة، المعاهدات، الأسلحة، القادة'),
    ('kings_leaders', 'الملوك والقادة',
     'أسئلة عن الملوك والخلفاء والقادة والزعماء عبر التاريخ',
     '#b45309', '👑',
     'الخلفاء الراشدون، الأمويون، العباسيون، ملوك المملكة، القادة العالميون، الزعماء'),
    ('landmarks', 'المعالم والآثار',
     'أسئلة عن المعالم والآثار والأماكن الأثرية المشهورة في العالم',
     '#d97706', '🗿',
     'الأهرامات، برج إيفل، البتراء، Machu Picchu، سور الصين العظيم، الكولوسيوم، تاج محل'),
    ('olympics', 'الأولمبياد والألعاب الأولمبية',
     'أسئلة عن الألعاب الأولمبية ودوراتها وأبطالها',
     '#0ea5e9', '🏅',
     'دورات الأولمبياد، الرياضيون الأولمبيون، الأرقام القياسية، الدول المستضيفة، الميداليات'),
    ('animals_wild', 'الحيوانات البرية',
     'أسئلة عن الحيوانات البرية وسلوكها وبيئاتها',
     '#65a30d', '🦁',
     'الثدييات، الطيور الجارحة، الزواحف، الحيوانات المفترسة، البيئة الصحراوية، أعماق البحار'),
    ('quran', 'القرآن الكريم',
     'أسئلة عن القرآن الكريم: سوره وآياته وأحكامه وقصار السور',
     '#059669', '📗',
     'أطول السور، أقصر السور، أسماء السور، عدد الآيات، أسباب النزول، القراءات'),
    ('prophets', 'الأنبياء والرسل',
     'أسئلة عن الأنبياء والرسل وقصصهم',
     '#15803d', '🕯️',
     'قصص الأنبياء، أبناء الأنبياء، الكتب المنزلة، أولي العزم من الرسل، معجزات الأنبياء'),
    ('seerah', 'السيرة النبوية',
     'أسئلة عن السيرة النبوية وغزواتها وأحداثها',
     '#166534', '🕌',
     'الغزوات، الهجرة، الغزوات الكبرى، الصحابة، الأحداث المشهورة، المعاهدات'),
    ('islamic_history', 'التاريخ الإسلامي',
     'أسئلة عن التاريخ الإسلامي وحضارته ودوله',
     '#15803d', '🏛️',
     'الدولة الأموية، الدولة العباسية، الأندلس، الدولة العثمانية، الفتوحات، الحضارة الإسلامية'),
    ('pharaohs', 'الحضارة المصرية القديمة',
     'أسئلة عن الحضارة المصرية القديمة والفراعنة وحياتهم',
     '#ca8a04', '🏺',
     'الفراعنة، الأهرامات، الكتابة الهيروغليفية، المومياوات، المعابد، توت عنخ آمون'),
    ('india_cinema', 'السينما والدراما',
     'أسئلة عن السينما والدراما والمسلسلات التلفزيونية المشهورة',
     '#db2777', '🎭',
     'المسلسلات العربية، المسلسلات التركية، الممثلون، المخرجون، الجوائز'),
    ('smartphones', 'الهواتف والتطبيقات',
     'أسئلة عن الهواتف الذكية والتطبيقات وشركات التقنية',
     '#4f46e5', '📱',
     'أنظمة التشغيل، الشركات المصنعة، التطبيقات، المطورون، التقنيات الحديثة'),
    ('cybersecurity', 'الأمن السيبراني',
     'أسئلة عن الأمن السيبراني والحماية الرقمية والاختراقات',
     '#0f766e', '🔐',
     'أنواع الهجمات، التشفير، كلمات المرور، الحماية، الفيروسات، الشبكات'),
    ('ai_ml', 'الذكاء الاصطناعي',
     'أسئلة عن الذكاء الاصطناعي وتعلم الآلة وتقنياته',
     '#7c3aed', '🤖',
     'تعلم الآلة، الشبكات العصبية، النماذج اللغوية، التطبيقات، الرؤية الحاسوبية، الأخلاقيات'),
    ('aviation', 'الطيران والطائرات',
     'أسئلة عن الطيران والطائرات والمطارات وشركات الطيران',
     '#0284c7', '✈️',
     'أنواع الطائرات، شركات الطيران، المطارات، الطيارون، الطائرات الحربية'),
    ('seas_oceans', 'البحار والمحيطات',
     'أسئلة عن البحار والمحيطات والأنهار والممرات المائية',
     '#0891b2', '🌊',
     'المحيطات الخمسة، البحار، أطول الأنهار، أعمق النقاط، التيارات البحرية'),
    ('weather_climate', 'الطقس والمناخ',
     'أسئلة عن الطقس والمناخ والظواهر الجوية',
     '#64748b', '⛈️',
     'الظواهر الجوية، الفصول، الأعاصير، الغلاف الجوي، التساقطات'),
    ('solar_energy', 'الطاقة الشمسية',
     'أسئلة عن الطاقة الشمسية وتقنياتها واستخداماتها',
     '#f59e0b', '☀️',
     'الألواح الشمسية، التحويل الكهروضوئي، الخلايا، المشاريع، التخزين'),
]

# Arabic script colours that already exist in the bank, so the palette stays varied
COLOURS = ['#38bdf8', '#22c55e', '#e11d48', '#92400e', '#7f1d1d', '#b45309',
           '#d97706', '#0ea5e9', '#65a30d', '#059669', '#166534', '#ca8a04',
           '#db2777', '#4f46e5', '#0f766e', '#7c3aed', '#0284c7', '#0891b2',
           '#64748b', '#f59e0b', '#0d9488', '#16a34a']


def cat_exists(cid):
    cats = json.load(open(CATFILE, encoding='utf-8'))
    return any(c['id'] == cid for c in cats)


def create_categories(specs):
    """Create the category rows first — questions cannot exist without them."""
    cats = json.load(open(CATFILE, encoding='utf-8'))
    have = {c['id'] for c in cats}
    added = []
    for cid, name, desc, colour, icon, topics in specs:
        if cid in have:
            continue
        cats.append({'id': cid, 'name': name, 'description': desc,
                     'color': colour, 'icon': icon, 'topics': topics})
        have.add(cid)
        added.append(name)
    with open(CATFILE, 'w', encoding='utf-8') as f:
        json.dump(cats, f, ensure_ascii=False, indent=2)
    return added


def new_cat_specs(n):
    """Pick n categories that are not in the bank yet."""
    cats = json.load(open(CATFILE, encoding='utf-8'))
    have = {c['id'] for c in cats}
    specs = [s for s in NEW_CATEGORIES if s[0] not in have]
    if n > len(specs):
        print('only %d new categories available' % len(specs))
        n = len(specs)
    return specs[:n]


def bank_counts(game):
    qs = B.read_all()
    out = Counter(q.get('category_id') for q in qs if q.get('game') == game)
    return out


def targets_for(cats, target, counts, difficulties):
    """How many of each difficulty each category still needs."""
    out = []
    for c in cats:
        cid = c['id']
        cur = counts.get(cid, 0)
        if cur >= target:
            continue
        need_total = target - cur
        per = B.split_evenly(need_total, difficulties)
        for d in difficulties:
            if per[d] > 0:
                out.append((cid, c['name'], d, per[d]))
    return out


def run(targets, workers, max_rounds=12, batch=20):
    keys = B.existing_keys('quiz')
    accepted, rejected = [], 0
    remaining = {i: t[3] for i, t in enumerate(targets)}
    for rnd in range(1, max_rounds + 1):
        jobs = [(i, t, min(batch, remaining[i])) for i, t in enumerate(targets)
                if remaining[i] > 0]
        if not jobs:
            break

        def work(j):
            i, t, n = j
            cid, cname, d, _ = t
            last = ''
            for attempt in range(3):
                try:
                    return i, B.fetch_quiz_batch(cid, cname, d, n)
                except Exception as e:
                    last = e
                    time.sleep(2)
            print('    ! failed %s/%s: %s' % (cname, d, last), flush=True)
            return i, []

        got = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(work, jobs):
                cid, cname, d, _ = targets[i]
                fresh = [it for it in items
                         if (it['game'] + '|' + B.norm_ar(it['question'])) not in keys]
                rejected += len(items) - len(fresh)
                for it in fresh:
                    keys.add(it['game'] + '|' + B.norm_ar(it['question']))
                accepted.extend(fresh)
                remaining[i] -= len(fresh)
                got += len(fresh)
        print('    round %d: +%d (total %d)' % (rnd, got, len(accepted)), flush=True)
    for i, t in enumerate(targets):
        if remaining[i] > 0:
            print('    ! short: %s/%s got %d of %d'
                  % (t[1], t[2], t[3] - remaining[i], t[3]), flush=True)
    return accepted, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['extend', 'new', 'both'], required=True)
    ap.add_argument('--target', type=int, default=320,
                    help='questions per EXISTING category')
    ap.add_argument('--new-cats', type=int, default=24)
    ap.add_argument('--target-new', type=int, default=420,
                    help='questions per NEW category')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--max-rounds', type=int, default=12)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    if not B.API_KEY:
        print('NVIDIA_API_KEY missing from .env')
        return 1

    cats = json.load(open(CATFILE, encoding='utf-8'))
    counts = bank_counts('quiz')
    total_acc = 0

    if a.mode in ('new', 'both'):
        specs = new_cat_specs(a.new_cats)
        added = create_categories(specs)
        print('created %d categories: %s' % (len(added), ', '.join(added) or 'none'))
        cats = json.load(open(CATFILE, encoding='utf-8'))

    if a.mode in ('extend', 'both'):
        targets = targets_for(cats, a.target, counts, ['easy', 'medium', 'hard'])
        print('extend: %d category/difficulty targets' % len(targets))
        acc, rej = run(targets, a.workers, a.max_rounds)
        total_acc += len(acc)
        if acc and not a.dry_run:
            print('saved %d quiz questions' % B.append_locked(acc))

    if a.mode in ('new', 'both'):
        new_cats = [c for c in cats if c['id'] in {s[0] for s in NEW_CATEGORIES}]
        targets = targets_for(new_cats, a.target_new, counts, ['easy', 'medium', 'hard'])
        print('new: %d category/difficulty targets' % len(targets))
        acc, rej = run(targets, a.workers, a.max_rounds)
        total_acc += len(acc)
        if acc and not a.dry_run:
            print('saved %d quiz questions' % B.append_locked(acc))

    print('DONE: %d accepted' % total_acc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
