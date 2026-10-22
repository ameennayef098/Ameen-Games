# -*- coding: utf-8 -*-
"""Fill حروف مع أمين's «تحت المتوسط» tier answer-first.

Asking the model for "a question whose answer starts with ص" makes it ignore the
letter (~90% wrong). Giving it the word and asking for the question is reliable:
the answer is correct by construction and only the question text can be wrong.

A third of each batch is asked for in «لغز وصفي» form (describe the answer
without naming it) — that is the trick-question style requested.
"""
import sys, os, json, time, argparse, random, threading, re
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server as S

M = 'nvidia/nemotron-3.5-lightning-30b-a3b'
S._USED_MODEL['name'] = M
LOGLOCK = threading.Lock()


def log(m):
    line = '[%s] %s' % (time.strftime('%H:%M:%S'), m)
    with LOGLOCK:
        print(line, flush=True)


# Letters whose bank has too few single-word answers to harvest from.
CURATED = {
    'أ': ['أثر', 'أرض', 'أخ', 'أم', 'أمل', 'أنف', 'أسد', 'إناء', 'أذن', 'أرز',
          'إمام', 'أنس', 'إيثار', 'أدب', 'إنشاء'],
    'هـ': ['هدى', 'هالة', 'همسة', 'هند', 'هيثم', 'هاني', 'هشام', 'هناء', 'همة',
           'هواء', 'هاتف', 'هرم', 'هجرة', 'هدهد', 'هيبة'],
    'ذ': ['ذئب', 'ذكرى', 'ذقن', 'ذهن', 'ذهب', 'ذكر', 'ذيل', 'ذرة', 'مذاق', 'ذكاء'],
    'ض': ['ضفة', 'ضرس', 'ضوء', 'ضمير', 'ضيف', 'ضب', 'ضأن', 'ضاحك', 'ضفدع', 'ضباب'],
    'ظ': ['ظل', 'ظرف', 'ظمأ', 'ظبي', 'ظهر', 'ظفر', 'نظارة', 'مظلة', 'حظ', 'لظى'],
}
CURATED['أ'] = ['أثر', 'أرض', 'أخ', 'أم', 'أمل', 'أنف', 'أسد', 'إناء', 'أذن', 'أرز',
                'إمام', 'أنس', 'إيثار', 'أدب', 'إنشاء', 'إبريق']


def word_pool():
    """Keyed by the NORMALISED letter — first_letter_of() returns the normalised
    form ('أثر' -> 'ا', not 'أ'), so comparing against the raw AR_LETTERS value
    silently matches nothing."""
    d = S.load_json(S.Q_FILE, [])
    used, pool = {}, {}
    for L in S.AR_LETTERS:
        used[S.norm_ar(L)] = set()
        pool[S.norm_ar(L)] = set()
    for q in d:
        if q.get('game') != 'letters':
            continue
        a = str(q.get('answer', '')).strip()
        L = S.first_letter_of(a)
        if L in used:
            used[L].add(S.norm_ar(a))
        if a and ' ' not in a and 3 <= len(a) <= 9 and not S.has_foreign(a) \
                and not re.search(r'[ً-ٕـ]', a):
            if L in pool:
                pool[L].add(a)
    for L, ws in CURATED.items():
        for w in ws:
            if S.first_letter_of(w) == S.norm_ar(L) and not S.has_foreign(w):
                pool[S.norm_ar(L)].add(w)
    return pool, used


def build_prompt(letter, words):
    n_riddle = max(1, len(words) // 3)
    return (
        'أنت معدّ أسئلة مسابقات عربية. المطلوب: ' + str(len(words)) + ' سؤالاً، '
        'جواب كل منها الكلمة المكتوبة أمامه في هذه القائمة وبنفس الترتيب:\n'
        + json.dumps(words, ensure_ascii=False) + '\n'
        'كل سؤال يجب أن تكون الكلمة المعطاة هي جوابه الصحيح، وأصعب من السؤال '
        'السهل الشائع وأسهل من المتوسط.\n'
        'ممنوع ظهور الجواب نفسه في نص السؤال (بعد تجاهل التشكيل والتطويل '
        'وتوحيد الألف والتاء المربوطة).\n'
        'أول ' + str(n_riddle) + ' سؤال تكون بصيغة «اللغز الوصفي»: صِف الجواب '
        'وصفاً غير مباشر لا يذكر الجواب.\n'
        'الباقي أسئلة معلومات عامة عادية.\n'
        'كل النصوص بالعربية فقط — ممنوع أي حرف لاتيني أو صيني أو كوري.\n'
        'أعد مصفوفة JSON فقط بلا أي نص إضافي: [{"question":"..."},"]\n'
        .replace('{"question":"..."},"]', '{"question":"..."}]\n'))


def gen_letter(job):
    letter, want = job
    pool, used = word_pool()
    key = S.norm_ar(letter)
    avail = sorted(pool.get(key, set()) - used.get(key, set()))
    if len(avail) < want:
        avail = sorted(pool.get(key, set()))
    if not avail:
        log('%-3s no words available' % letter)
        return []
    random.shuffle(avail)
    picked = avail[:want]
    try:
        out = S._nvidia_call(M, build_prompt(letter, picked), 180, 0.8)
        items = S.extract_json_array(out)
    except Exception as e:
        log('%-3s call failed: %s' % (letter, str(e)[:80]))
        return []

    got = []
    for w, it in zip(picked, items):
        if not isinstance(it, dict):
            continue
        qtext = str(it.get('question', '')).strip()
        if not qtext:
            continue
        q = {'id': S.gen_id(), 'game': 'letters', 'letter': letter,
             'question': qtext, 'answer': w,
             'explanation': '', 'difficulty': 'under', 'status': 'approved',
             'source': 'ai', 'created_at': S.now(), 'updated_at': S.now(),
             'alternatives': [], 'hint': '', 'image': ''}
        nq, na = S.norm_ar(qtext), S.norm_ar(w)
        if na and na in nq:
            continue                                    # الجواب مذكور في السؤال
        ok, err = S.validate_question(q)
        if not ok:
            continue
        if any(S.q_key(q) == S.q_key(x) for x in S.load_json(S.Q_FILE, [])
               if x.get('game') == 'letters'):
            continue
        got.append(q)
    log('%-3s picked %d -> kept %d' % (letter, len(picked), len(got)))
    return got


def append(rows):
    cur = S.load_json(S.Q_FILE, [])
    cur.extend(rows)
    S.save_json(S.Q_FILE, cur)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-letter', type=int, default=8)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--only', default='')
    a = ap.parse_args()

    letters = [L for L in S.AR_LETTERS if not a.only or L == a.only]
    jobs = [(L, a.per_letter) for L in letters]
    log('letters: %d   per letter: %d' % (len(jobs), a.per_letter))

    total = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for got in ex.map(gen_letter, jobs):
            if got:
                append(got)
                total += len(got)
    log('DONE: added %d letters «تحت المتوسط» questions' % total)


if __name__ == '__main__':
    main()
