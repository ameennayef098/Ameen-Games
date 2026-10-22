# -*- coding: utf-8 -*-
"""Fill the «تحت المتوسط» tier.

Deletes every difficulty=='easy' question from the bank and generates
replacement questions at the new lowest tier (تحت المتوسط) plus extra
متوسط ones. A share of the «تحت المتوسط» questions are «لغز وصفي» trick
questions whose answer word must NOT appear in the question text.

Usage:  python tools/fill_under.py [--dry-run] [--only quiz] [--limit N] [--workers 4]
"""
import sys, os, time, argparse, threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server as S

MODEL = 'nvidia/nemotron-3.5-lightning-30b-a3b'
S._USED_MODEL['name'] = MODEL

BATCH = 14
TRIES = 6
LOGLOCK = threading.Lock()
LOGPATH = os.path.join(ROOT, 'fill_under.log')


def log(msg):
    line = '[%s] %s' % (time.strftime('%H:%M:%S'), msg)
    with LOGLOCK:
        print(line, flush=True)
        try:
            with open(LOGPATH, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass


def chat(prompt, temperature=0.85, timeout=150):
    """One call, with a single retry — the API rate-limits under concurrency."""
    for attempt in (0, 1):
        try:
            return S._nvidia_call(MODEL, prompt, timeout, temperature)
        except Exception:
            if attempt:
                return S.nvidia_chat(prompt, timeout=timeout, temperature=temperature)
            time.sleep(1.5)


# ------------------------------------------------------------------ prompts
# The trick style is folded into the «تحت المتوسط» prompt: asking for a
# separate trick slot doubled the call count for no gain in variety.
TRICK_RULE = (
    '\nقاعدة إضافية لبعض الأسئلة (نحو الثلث): اكتب السؤال بصيغة «اللغز الوصفي» — '
    'صِف الجواب وصفاً غير مباشر دون أن تظهر كلمة الجواب نفسها في نص السؤال. '
    'مثال: «ما الشيء الذي كلّما أخذت منه كبر؟» جوابه «الحفرة».\n')

UNDER_NOTE = (
    '\nملاحظة على المستوى المطلوب: «تحت المتوسط» يعني أسئلة أصعب من الأسئلة '
    'السهلة المعروفة للجميع وأسهل من المتوسطة. ممنوع سؤال مباشر عن معلومة '
    'عامة شهيرة من نوع «كم عدد ...؟» أو «ما اسم ...؟» يكون جوابه معروفاً عند '
    'الجميع. المطلوب معلومة أدق أو سؤال يحتاج تفكيراً أو ربط معلومات.\n')


def build(game, letter, cat_name, cat_desc, difficulty, ask, avoid):
    p = S.build_ai_prompt(game, letter, cat_name, ask, difficulty, avoid,
                          strict=False, cat_desc=cat_desc)
    if difficulty == 'under':
        p += UNDER_NOTE
        if game != 'million':
            p += TRICK_RULE
    return p


# ------------------------------------------------------------------ helpers
def answer_leaks(question, answer):
    """True when the answer word literally appears inside the question."""
    nq, na = S.norm_ar(question), S.norm_ar(answer)
    return bool(na) and na in nq


STOP = set('هل هو هي من في ما ماذا الذي التي الذين يعرف اسم مجال عمل شخصية شخصيات يعتبر تنتمي ينتمي و ثم او أو لا نعم كل غير بين بعد قبل مع عن على الى إلى كان كانت يكون أحد احد'.split())


def toks(t):
    return set(x for x in S.norm_ar(t).split() if len(x) > 2 and x not in STOP)


def near_dup(question, others, limit=0.88):
    """Reject a near-copy of an existing question in the same slot.

    Deliberately high: at 0.72 it also killed legitimate «same template,
    different fact» questions («في أي عام فازت البرازيل...» / «...ألمانيا...»).
    Paraphrase avoidance is the avoid-block's job, not this guard's.
    """
    a = toks(question)
    if not a:
        return '?'
    for o in others:
        b = toks(o)
        if not b:
            continue
        if len(a & b) / max(1, len(a | b)) >= limit:
            return o
    return None


def slot_questions(game, letter, cat):
    """Existing questions in the same slot — used for the avoid block."""
    out = S.load_json(S.Q_FILE, [])
    if game == 'letters':
        return [q for q in out if q.get('game') == 'letters' and q.get('letter') == letter]
    if game == 'million':
        return [q for q in out if q.get('game') == 'million']
    cid = (cat or {}).get('id', '')
    return [q for q in out if q.get('game') == 'quiz' and q.get('category_id') == cid]


def gen_slot(job):
    """Generate up to `want` validated questions for one (game, key, difficulty)."""
    game, letter, cat, difficulty, want = job
    cat_name = (cat or {}).get('name', '')
    cat_desc = (cat or {}).get('description', '') or ''
    prior = slot_questions(game, letter, cat)
    prior_texts = [str(q.get('question', '')).strip() for q in prior if q.get('question')]
    slot_texts = list(prior_texts)
    avoid = ''
    if prior_texts:
        avoid = ('\n\nلا تكرر هذه الأسئلة ولا تعد صياغتها:\n' +
                 '\n'.join('- ' + t for t in prior_texts[-40:]))
    got, rejected, parse_fail = [], [], 0

    for _ in range(TRIES):
        if len(got) >= want:
            break
        ask = min(BATCH, max(want - len(got) + 4, 5))
        prompt = build(game, letter, cat_name, cat_desc, difficulty, ask, avoid)
        try:
            items = S.extract_json_array(chat(prompt))
        except Exception:
            parse_fail += 1
            continue

        for it in items:
            if len(got) >= want:
                break
            if not isinstance(it, dict) or not it.get('question') or not it.get('answer'):
                rejected.append('بيانات ناقصة')
                continue
            q = {'id': S.gen_id(), 'game': game,
                 'question': str(it['question']).strip(),
                 'answer': str(it['answer']).strip(),
                 'explanation': str(it.get('explanation', '')).strip(),
                 'difficulty': difficulty, 'status': 'approved', 'source': 'ai',
                 'created_at': S.now(), 'updated_at': S.now(),
                 'alternatives': [], 'hint': '', 'image': ''}
            if game == 'letters':
                q['letter'] = letter
            elif game == 'million':
                q['options'] = [str(o).strip() for o in (it.get('options') or [])][:4]
                q['points'] = 200 if difficulty == 'under' else (
                    600 if difficulty == 'hard' else 400)
            else:
                q['category_id'] = (cat or {}).get('id', '')
                q['category_name'] = cat_name
                q['points'] = 200 if difficulty == 'under' else (
                    600 if difficulty == 'hard' else 400)

            if answer_leaks(q['question'], q['answer']):
                rejected.append('الجواب مذكور في السؤال')
                continue
            if near_dup(q['question'], slot_texts):
                rejected.append('قريب من سؤال موجود')
                continue
            ok, err = S.validate_question(q)
            if not ok:
                rejected.append(err)
                continue
            slot_texts.append(q['question'])
            got.append(q)

    label = ('%s/%s' % (letter, cat_name or 'المليون'))[:30]
    log('%-8s %-6s %-30s want=%-3d got=%-3d%s'
        % (game, difficulty, label, want, len(got),
           ('  [رفض %d]' % len(rejected)) if rejected else ''))
    if parse_fail:
        log('    ! %d parse failures' % parse_fail)
    return got


def append(rows):
    cur = S.load_json(S.Q_FILE, [])
    cur.extend(rows)
    S.save_json(S.Q_FILE, cur)


def bulk_relevance(rows):
    """One model call per chunk judges every new question against its category."""
    if not rows:
        return rows
    keep, checked = [], 0
    for i in range(0, len(rows), 40):
        chunk = rows[i:i + 40]
        cats = {}
        for q in chunk:
            cats.setdefault((q.get('category_id'), q.get('category_name')), []).append(q)
        for (cid, cname), qs in cats.items():
            cat = {}
            for c in S.load_json(S.CAT_FILE, []):
                if c['id'] == cid:
                    cat = c
                    break
            verdicts = S.verify_relevance(
                [{'question': q['question']} for q in qs], cname, cat.get('description', ''))
            if verdicts is None:
                keep.extend(qs)
                continue
            for q, ok in zip(qs, verdicts):
                checked += 1
                if ok:
                    keep.append(q)
    log('relevance: checked %d, dropped %d off-topic' % (checked, len(rows) - len(keep)))
    return keep


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=2)
    args = ap.parse_args()

    allq = S.load_json(S.Q_FILE, [])
    before = len(allq)
    # Only حروف مع أمين loses its easy tier — س.ج and المليون keep theirs.
    easy = [q for q in allq
            if q.get('difficulty') == 'easy' and q.get('game') == 'letters']
    log('bank before: %d  (letters easy: %d)' % (before, len(easy)))
    log('  easy %-8s %d' % ('quiz', len([q for q in allq if q.get('game') == 'quiz' and q.get('difficulty') == 'easy'])))
    log('  easy %-8s %d' % ('million', len([q for q in allq if q.get('game') == 'million' and q.get('difficulty') == 'easy'])))

    if args.dry_run:
        log('DRY RUN — nothing changed')
        return
    if easy:
        S.save_json(S.Q_FILE, [q for q in allq
                               if not (q.get('difficulty') == 'easy'
                                       and q.get('game') == 'letters')])
        log('deleted letters-easy -> bank now %d' % (before - len(easy)))

    jobs = []
    # «تحت المتوسط» replaces the deleted easy tier in حروف مع أمين only —
    # س.ج and المليون keep their own easy tier.
    if args.only in ('', 'letters'):
        for L in S.AR_LETTERS:
            jobs.append(('letters', L, None, 'under', 8))
    if args.only == 'quiz':
        for c in S.load_json(S.CAT_FILE, []):
            jobs.append(('quiz', '', c, 'under', 16))
    if args.only == 'million':
        jobs.append(('million', '', None, 'under', 14))
    if args.limit:
        jobs = jobs[:args.limit]

    log('slots: %d   workers: %d' % (len(jobs), args.workers))
    t0 = time.time()
    added = {'under': 0, 'medium': 0}
    stamp = time.strftime('%Y-%m-%dT%H:%M')

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for got in ex.map(gen_slot, jobs):
            if not got:
                continue
            append(got)
            added[got[0]['difficulty']] = added.get(got[0]['difficulty'], 0) + len(got)

    log('generation done in %.1f د — relevance pass next' % ((time.time() - t0) / 60))
    new = [q for q in S.load_json(S.Q_FILE, [])
           if q.get('difficulty') == 'under' and q.get('category_name')
           and str(q.get('created_at', '')) >= stamp]
    kept = bulk_relevance(new)
    if len(kept) != len(new):
        drop_ids = {q['id'] for q in new} - {q['id'] for q in kept}
        S.save_json(S.Q_FILE, [q for q in S.load_json(S.Q_FILE, [])
                               if q['id'] not in drop_ids])

    final = S.load_json(S.Q_FILE, [])
    log('DONE. bank %d -> %d  (+%d: under=%d medium=%d)  in %.1f د'
        % (before, len(final), len(final) - before,
           added.get('under', 0), added.get('medium', 0),
           (time.time() - t0) / 60))


if __name__ == '__main__':
    main()
