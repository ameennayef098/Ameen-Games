# -*- coding: utf-8 -*-
"""Generate 2 verified questions for each of the 20 new س.ج categories.

Uses the exact pipeline the /api/ai/generate endpoint uses (build_ai_prompt ->
nvidia_chat -> extract_json_array -> verify_relevance -> validate_question),
so this exercises the real generation path rather than a parallel one.
"""
import sys, os, json, time, threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server as S

M = 'nvidia/nemotron-3.5-lightning-30b-a3b'
S._USED_MODEL['name'] = M
LOCK = threading.Lock()


def log(m):
    with LOCK:
        print('[%s] %s' % (time.strftime('%H:%M:%S'), m), flush=True)


def chat(prompt, temperature=0.85, timeout=180):
    try:
        return S._nvidia_call(M, prompt, timeout, temperature)
    except Exception:
        return S.nvidia_chat(prompt, timeout=timeout, temperature=temperature)


def gen(cat, difficulty):
    """One verified question for (category, difficulty)."""
    name, desc = cat['name'], cat.get('description', '')
    for attempt in (0, 1):
        prompt = S.build_ai_prompt('quiz', '', name, 6, difficulty, '',
                                   strict=(attempt > 0), cat_desc=desc)
        try:
            items = S.extract_json_array(chat(prompt, 0.85 if attempt == 0 else 0.7))
        except Exception as e:
            log('   call failed: %s' % str(e)[:80])
            continue
        cands = [it for it in items
                 if isinstance(it, dict) and it.get('question') and it.get('answer')]
        verdicts = S.verify_relevance(
            [{'question': it['question']} for it in cands], name, desc)
        off = set()
        if verdicts is not None:
            for it, ok in zip(cands, verdicts):
                if not ok:
                    off.add(S.norm_ar(it['question']))
        for it in cands:
            q = {'id': S.gen_id(), 'game': 'quiz',
                 'question': str(it['question']).strip(),
                 'answer': str(it['answer']).strip(),
                 'explanation': str(it.get('explanation', '')).strip(),
                 'difficulty': difficulty, 'status': 'approved', 'source': 'ai',
                 'created_at': S.now(), 'updated_at': S.now(),
                 'alternatives': [], 'hint': '', 'image': '',
                 'category_id': cat['id'], 'category_name': name,
                 'points': 200 if difficulty == 'easy' else (
                     600 if difficulty == 'hard' else 400)}
            if S.norm_ar(q['question']) in off:
                continue
            ok, err = S.validate_question(q)
            if not ok:
                continue
            return q
    return None


def job(args):
    cat, difficulty = args
    q = gen(cat, difficulty)
    log('%-28s %-7s %s' % (cat['id'], difficulty,
                           'OK' if q else 'FAILED'))
    return q


def main():
    cats = {c['id']: c for c in S.load_json(S.CAT_FILE, [])}
    new = ['philosophy', 'criminal_investigation', 'marine_life', 'plants_trees',
           'natural_disasters', 'archaeology', 'media_journalism',
           'observational_astronomy', 'combat_sports', 'motorsports',
           'nutrition_science', 'accounting_finance', 'international_awards',
           'symbols_codes', 'maritime_navigation', 'infrastructure_smartcities',
           'military_aviation', 'museums_collections', 'folklore_fairy_tales',
           'materials_engineering']
    jobs = [(cats[i], d) for i in new for d in ('easy', 'hard')]
    log('jobs: %d' % len(jobs))

    out = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for q in ex.map(job, jobs):
            if q:
                out.append(q)
                # append as we go: a crash mid-run must not lose the work
                cur = S.load_json(S.Q_FILE, [])
                cur.append(q)
                S.save_json(S.Q_FILE, cur)
    log('generated %d questions -> bank %d' % (len(out), len(S.load_json(S.Q_FILE, []))))
    missing = [i for i in new
               if not any(q['category_id'] == i for q in out)]
    log('categories with no question: %s' % (missing or 'none'))


if __name__ == '__main__':
    main()
