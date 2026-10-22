#!/usr/bin/env python3
"""«مين في بالي؟» — bring every category up to a healthy size.

Two jobs:
  1. Fix the obviously wrong gender/attribute rows already in the bank (the bank
     shipped with every anime character marked «أنثى», which made the game
     unplayable the moment someone asked "ذكر؟").
  2. Generate 20 NEW characters per category through the NVIDIA model, validated
     by the same rules the API uses, and append them approved.

Usage:
    python tools/fill_minebali.py            # fix + generate 20 per category
    python tools/fill_minebali.py --fix-only
"""
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

import server  # noqa: E402  (registers nothing; app.run is under __main__)

CATEGORIES = ['أنمي', 'مسلسلات', 'مشاهير', 'الصحابة',
              'أبطال الأفلام', 'أبطال الألعاب', 'شخصيات كرتونية',
              'العلماء والمخترعون']
TARGET_PER_CATEGORY = 20
BATCH = 10

# The model keeps re-serving the most famous names for these categories. Naming
# acceptable alternatives in the prompt is what makes the extra rows land.
CATEGORY_HINTS = {
    'الصحابة': ('اختر صحابة لم تُذكر في القائمة أعلاه. أمثلة مقبولة: معاذ بن جبل، أبو هريرة، '
                 'أنس بن مالك، سلمان الفارسي، بلال بن رباح، زيد بن حارثة، جعفر بن أبي طالب، '
                 'حمزة بن عبد المطلب، خالد بن الوليد، سعد بن أبي وقاص، الزبير بن العوام، '
                 'طلحة بن عبيد الله، عبد الرحمن بن عوف، أبو عبيدة بن الجراح، سعيد بن زيد، '
                 'شرحبيل بن حسنة، أسماء بنت أبي بكر، أم سلمة، عائشة بنت أبي بكر، '
                 'حفصة بنت عمر، زينب بنت خزيمة، المقداد بن عمرو، عبادة بن الصامت.'),
    'العلماء والمخترعون': ('اختر علماء ومخترعين لم يُذكروا أعلاه. أمثلة مقبولة: ابن سينا، الخوارزمي، '
                            'ابن الهيثم، جابر بن حيان، ابن النفيس، الكندي، الفارابي، ابن رشد، '
                            'ماري كوري، نيكولا تسلا، توماس إديسون، غراهام بيل، ألبرت أينشتاين، '
                            'إسحاق نيوتن، تشارلز داروين، لويس باستور، أرخميدس، '
                            'غاليليو غاليلي، يوهانس كيبلر، جيمس وات، ميتشل فاراداي.'),
    'شخصيات كرتونية': ('اختر شخصيات كرتونية وأنيميشن شهيرة لم تُذكر أعلاه. أمثلة مقبولة: توم، جيري، '
                        'ميكي ماوس، بطوط، سندريلا، بياض الثلج، غريندايزر، كابتن ماجد، '
                        'سندباد، عدنان، لينا، سونيك، سلاحف النينجا، تن تن، لاكي لوك.'),
}

# name -> correct gender (the shipped bank had these wrong)
GENDER_FIX = {
    'ناروتو أوزوماكي': 'ذكر', 'ساسكي أوتشيها': 'ذكر', 'كاكاشي هاتاكي': 'ذكر',
    'إيتاتشي أوتشيها': 'ذكر', 'لوفي': 'ذكر', 'زورو': 'ذكر', 'سانجي': 'ذكر',
    'إيرين ييغر': 'ذكر', 'أرمين أرليرت': 'ذكر', 'ليفاي أكرمان': 'ذكر',
    'لايت ياغامي': 'ذكر', 'غوكو': 'ذكر', 'فيجيتا': 'ذكر', 'تانجيرو كامادو': 'ذكر',
    'زينيتسو أغاتسوما': 'ذكر', 'يوجي إيتادوري': 'ذكر', 'غوجو ساتورو': 'ذكر',
    'سونغ جين-وو': 'ذكر', 'كونان إيدوگاوا': 'ذكر', 'كوغورو موري': 'ذكر',
    'سينكو إيشيگامي': 'ذكر', 'إيليفين': 'أنثى', 'ميسا أمانه': 'أنثى',
    'نوبارا كوجيساكي': 'أنثى', 'تشا هاي-إن': 'أنثى', 'ران موري': 'أنثى',
    'بولما': 'أنثى', 'نيزوكو كامادو': 'أنثى', 'كرومي': 'أنثى', 'نامي': 'أنثى',
    'ساكورا هارونو': 'أنثى', 'ميكاسا أكرمان': 'أنثى', 'هرميون گرانجر': 'أنثى',
    'دينيريس تارغيريان': 'أنثى', 'أريا ستارك': 'أنثى', 'لارا كروفت': 'أنثى',
    'نيروبي': 'أنثى', 'طوكيو': 'أنثى', 'جوليت نيكولز': 'أنثى',
    'ماري كوري': 'أنثى', 'بيونسيه': 'أنثى', 'أوبرا وينفري': 'أنثى',
    'خديجة بنت خويلد': 'أنثى', 'فاطمة الزهراء': 'أنثى',
}
POWERS_FIX = {'كونان إيدوگاوا': False, 'كوغورو موري': False, 'مايكل سكوفيلد': False}


def load():
    return json.load(open(server.content_file('minebali'), encoding='utf-8'))


def save(items):
    with open(server.content_file('minebali'), 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def fix_existing(items):
    fixed = 0
    for c in items:
        name = str(c.get('name', '')).strip()
        g = GENDER_FIX.get(name)
        if g and c.get('gender') != g:
            c['gender'] = g
            fixed += 1
        p = POWERS_FIX.get(name)
        if p is not None and c.get('powers') != p:
            c['powers'] = p
            fixed += 1
        if not str(c.get('field', '')).strip():
            c['field'] = str(c.get('role', '') or c.get('subcategory', '') or 'عام').strip()
            fixed += 1
        if not str(c.get('category', '')).strip():
            c['category'] = 'عام'
            fixed += 1
        c.setdefault('status', 'approved')
        c.setdefault('source', 'manual')
        c.setdefault('difficulty', 'medium')
        if 'real' not in c:
            c['real'] = False
        if 'main' not in c:
            c['main'] = False
        if 'powers' not in c:
            c['powers'] = False
    return fixed


def generate(items, category, want):
    keys = set()
    for c in items:
        keys |= server.content_keys('minebali', c)
    hint = CATEGORY_HINTS.get(category, '')
    added, rounds = [], 0
    while len(added) < want and rounds < 6:
        rounds += 1
        need = want - len(added)
        res = server._ai_gen_content('minebali', min(BATCH, need + 3), 'medium',
                                     category + (('\n' + hint) if hint else ''))
        fresh = [it for it in res['items']
                 if not (server.content_keys('minebali', it) & keys)
                 and server.validate_content('minebali', it)[0]]
        for it in fresh:
            if len(added) >= want:
                break
            keys |= server.content_keys('minebali', it)
            added.append(it)
        print('    round %d: +%d (total %d/%d) rejected=%d err=%s'
              % (rounds, len(fresh), len(added), want,
                 res.get('rejected_count', 0), (res.get('last_error') or '')[:60]))
        if not fresh:
            time.sleep(2)
    return added


def dedupe(items):
    """Drop near-duplicates: same first token («ميكاسا أكرمان» / «ميكاسا أكيرمان»).

    Keeps the record with the most filled fields, so the richer row survives.
    """
    def score(c):
        return sum(1 for k in ('subcategory', 'work', 'field', 'role', 'country', 'era')
                   if str(c.get(k, '')).strip())
    best = {}
    order = []
    for c in items:
        key = 'first:' + server.norm_ar(c.get('name', '')).split(' ')[0]
        if key not in best:
            best[key] = c
            order.append(key)
        elif score(c) > score(best[key]):
            best[key] = c
    out = [best[k] for k in order]
    return out, len(items) - len(out)


def main():
    fix_only = '--fix-only' in sys.argv
    items = load()
    print('bank before:', len(items))
    fixed = fix_existing(items)
    print('attribute fixes:', fixed)
    items, dropped = dedupe(items)
    print('near-duplicates dropped:', dropped)

    total_added = 0
    if not fix_only:
        for cat in CATEGORIES:
            cur = len([c for c in items if c.get('category') == cat])
            need = max(0, TARGET_PER_CATEGORY - cur)
            print('  %s — have %d, generating %d' % (cat, cur, need))
            if not need:
                continue
            added = generate(items, cat, need)
            for it in added:
                it['status'] = 'approved'
                it['source'] = 'ai'
                it.setdefault('created_at', server.now())
                items.append(it)
            total_added += len(added)
            print('    -> added %d' % len(added))
            save(items)

    save(items)
    print('bank after:', len(items))
    from collections import Counter
    for cat, n in Counter(c.get('category') for c in items).most_common():
        print('  %-24s %d' % (cat, n))
    print('TOTAL NEW:', total_added)
    return 0


if __name__ == '__main__':
    sys.exit(main())
