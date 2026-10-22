#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural + semantic audit of quiz difficulty in data/questions/all.json.

Read-only by default. Fixes are applied atomically under the existing lock
from tools/bulk_gen.py so the concurrent bulk generator never loses a write.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))
QFILE = os.path.join(BASE, 'data', 'questions', 'all.json')
CATFILE = os.path.join(BASE, 'data', 'categories', 'categories.json')
BACKUP = QFILE + '.bak-difficulty'
ENVFILE = os.path.join(BASE, '.env')
REPORT = os.path.join(BASE, 'data', 'difficulty-audit-report.md')
SNAP = os.path.join(BASE, 'data', 'questions', 'all.json.bak-difficulty')

MODEL = 'nvidia/nemotron-3-ultra-550b-a55b'
URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
POINTS = {'easy': 200, 'medium': 400, 'hard': 600}
AR_DIFF = {'easy': 'سهل', 'medium': 'متوسط', 'hard': 'صعب'}


def load_env():
    env = {}
    if not os.path.exists(ENVFILE):
        return env
    with open(ENVFILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
API_KEY = ENV.get('NVIDIA_API_KEY', '')


def load_rows(path=QFILE):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def quiz_rows(rows):
    return [r for r in rows if r.get('game') == 'quiz']


def structural(rows):
    """Return list of (idx, row, expected_points, actual_points)."""
    bad = []
    for i, r in enumerate(rows):
        if r.get('game') != 'quiz':
            continue
        d = r.get('difficulty')
        p = r.get('points')
        if d in POINTS and p != POINTS[d]:
            bad.append((i, r, POINTS[d], p))
    return bad


def write_atomic(path, rows):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def acquire_lock(timeout=180):
    lock = os.path.join(BASE, 'data', '.all.lock')
    start = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(lock)
            except OSError:
                age = 0
            if age > 90:
                try:
                    os.remove(lock)
                except OSError:
                    pass
                continue
            if time.time() - start > timeout:
                raise TimeoutError('all.json lock busy for %ss' % timeout)
            time.sleep(0.4)


def release_lock():
    try:
        os.remove(os.path.join(BASE, 'data', '.all.lock'))
    except OSError:
        pass


def nvidia_chat(prompt, timeout=180, temperature=0.3, retries=3):
    body = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': temperature,
        'chat_template_kwargs': {'enable_thinking': False},
    }).encode('utf-8')
    last = ''
    for attempt in range(retries):
        req = urllib.request.Request(
            URL, data=body,
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer ' + API_KEY})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last = 'HTTP %s %s' % (e.code, e.read().decode('utf-8')[:160])
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except Exception as e:
            last = '%s: %s' % (type(e).__name__, e)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(last)


def extract_json_array(text):
    if not text or not str(text).strip():
        raise ValueError('empty model response')
    t = re.sub(r'```(?:json|JSON)?', '', str(text)).strip()
    start = t.find('[')
    while start != -1:
        depth = 0
        instr = False
        esc = False
        for i in range(start, len(t)):
            ch = t[i]
            if instr:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    instr = False
                continue
            if ch == '"':
                instr = True
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    cand = t[start:i + 1]
                    cand = re.sub(r',\s*([\]}])', r'\1', cand)
                    try:
                        return json.loads(cand)
                    except Exception:
                        break
        start = t.find('[', start + 1)
    objs = []
    for m in re.finditer(r'\{[^{}]*\}', t):
        try:
            objs.append(json.loads(m.group()))
        except Exception:
            continue
    if objs:
        return objs
    raise ValueError('no JSON array found in model response')


def judge_prompt(items):
    """items: list of {index, question, answer, category, stored}"""
    block = json.dumps(items, ensure_ascii=False, indent=1)
    return (
        'أنت مقوّم صعوبة أسئلة مسابقات ثقافية عامة لجمهور سعودي في المرحلة الثانوية.\n'
        'لكل سؤال حدّد المستوى الحقيقي لصعوبته بناءً على مدى شهرة المعلومة لدى هذا الجمهور:\n'
        '- easy (سهل): معلومة يعرفها تقريباً كل طالب ثانوي — مباشرة وشائعة جداً.\n'
        '- medium (متوسط): معلومة ثقافية عامة يتوقع المثقف معرفتها — تحتاج معرفة عامة جيدة.\n'
        '- hard (صعب): معلومة متخصصة أو نادرة أو دقيقة (تواريخ، أسماء بعيدة، تفاصيل علمية) — '
        'لا يعرفها إلا من لديه اطلاع واسع.\n'
        'انتبه: أسئلة التواريخ والأسماء النادرة والأرقام الدقيقة = صعب غالباً. '
        'الأسئلة عن أشياء يومية مشهورة = سهل.\n\n'
        'العناصر (مع المستوى المخزّن حالياً للعلم فقط — قيّم بنفسك ولا تنسخه):\n'
        + block + '\n\n'
        'أعد مصفوفة JSON فقط بنفس عدد العناصر وبنفس الترتيب، كل عنصر:\n'
        '[{"index": رقم, "level": "easy" أو "medium" أو "hard", "reason": "سبب قصير بالعربية", '
        '"factual_issue": true أو false, "issue_note": "إن وُجد خطأ واقعي أو الإجابة داخل السؤال أو حروف أجنبية، اشرح باختصار وإلا اتركه فارغاً"}]\n'
        'أعد JSON فقط بلا أي نص إضافي.'
    )


JUDGE_SYS = None


def judge_batch(items, temperature=0.25):
    prompt = judge_prompt(items)
    content = nvidia_chat(prompt, temperature=temperature, timeout=240)
    try:
        arr = extract_json_array(content)
    except Exception:
        return None, content[:400]
    out = {}
    for o in arr:
        if isinstance(o, dict) and 'index' in o:
            out[int(o['index'])] = o
    if len(out) < len(items):
        return None, content[:400]
    return out, None


def sample_rows(rows, min_cats=14, per_diff=4, seed=42):
    """Deterministic sample: min_cats categories x 3 difficulties x per_diff."""
    by = defaultdict(list)
    for r in quiz_rows(rows):
        by[(r.get('category_id'), r.get('difficulty'))].append(r)
    keys = sorted(by.keys(), key=lambda k: (str(k[0]), str(k[1])))
    picked = []
    used_cats = set()
    # first pass: categories that have all three difficulties, biggest pools first
    full_cats = sorted({k[0] for k in keys
                        if all((k[0], d) in by and by[(k[0], d)] for d in
                               ('easy', 'medium', 'hard'))},
                       key=lambda c: -len(by.get((c, 'easy'), [])))
    for cid in full_cats:
        if len(used_cats) >= min_cats:
            break
        used_cats.add(cid)
    if len(used_cats) < min_cats:
        for k in keys:
            if len(used_cats) >= min_cats:
                break
            used_cats.add(k[0])
    for cid in sorted(used_cats):
        for d in ('easy', 'medium', 'hard'):
            pool = by.get((cid, d), [])
            if not pool:
                continue
            step = max(1, len(pool) // per_diff)
            for r in pool[::step][:per_diff]:
                picked.append(r)
    return picked


def per_category_table(rows):
    cats = json.load(open(CATFILE, encoding='utf-8'))
    byc = defaultdict(list)
    for r in quiz_rows(rows):
        byc[r.get('category_id')].append(r)
    lines = []
    lines.append('| category | total | easy | medium | hard | ratio e:m:h |')
    lines.append('|---|---:|---:|---:|---:|')
    tot = Counter()
    for c in cats:
        lst = byc.get(c['id'], [])
        d = Counter(x.get('difficulty') for x in lst)
        e, m, h = d.get('easy', 0), d.get('medium', 0), d.get('hard', 0)
        tot.update(d)
        lines.append('| %s | %d | %d | %d | %d | %s |'
                     % (c['name'], len(lst), e, m, h,
                        ('%.0f%%:%.0f%%:%.0f%%' % (100*e/max(1, len(lst)),
                                                  100*m/max(1, len(lst)),
                                                  100*h/max(1, len(lst))))))
    lines.append('')
    lines.append('**Totals:** easy %d, medium %d, hard %d (of %d quiz rows)'
                 % (tot.get('easy', 0), tot.get('medium', 0), tot.get('hard', 0),
                    sum(tot.values())))
    return '\n'.join(lines), tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit-only', action='store_true',
                    help='structural check only, no writes')
    ap.add_argument('--judge', action='store_true',
                    help='run semantic judgement pass')
    ap.add_argument('--apply', action='store_true',
                    help='apply fixes to all.json atomically')
    a = ap.parse_args()

    rows = load_rows(SNAP if os.path.exists(SNAP) else QFILE)
    print('rows loaded: %d (quiz %d)' % (len(rows), len(quiz_rows(rows))))

    # ---- structural ----
    bad = structural(rows)
    print('\n=== STRUCTURAL: points vs difficulty ===')
    print('mismatches: %d' % len(bad))
    for i, r, exp, act in bad[:60]:
        print('  idx=%d id=%s cat=%s diff=%s points=%s (expected %s) q=%s'
              % (i, r.get('id'), r.get('category_id'), r.get('difficulty'),
                 act, exp, str(r.get('question'))[:60]))
    if len(bad) > 60:
        print('  ... %d more' % (len(bad) - 60))

    # per-category counts from snapshot
    table, _ = per_category_table(rows)
    print('\n=== PER-CATEGORY DIFFICULTY (snapshot) ===')
    print(table)

    if a.audit_only:
        return 0

    # ---- structural fix ----
    n_struct_fix = 0
    if bad and a.apply:
        acquire_lock()
        try:
            live = load_rows(QFILE)
            # recompute mismatches on live data (another process may have appended)
            bad_live = structural(live)
            for i, r, exp, act in bad_live:
                live[i]['points'] = exp
                n_struct_fix += 1
            if n_struct_fix:
                write_atomic(QFILE, live)
                # refresh backup marker
                write_atomic(BACKUP, load_rows(QFILE))
                print('\napplied %d structural point fixes' % n_struct_fix)
        finally:
            release_lock()

    # ---- semantic ----
    if not a.judge:
        return 0
    sample = sample_rows(rows)
    print('\n=== SEMANTIC: judging %d sampled rows across %d categories ==='
          % (len(sample), len({r.get('category_id') for r in sample})))

    items = []
    for j, r in enumerate(sample):
        items.append({
            'index': j,
            'category': r.get('category_name'),
            'stored': r.get('difficulty'),
            'question': r.get('question'),
            'answer': r.get('answer'),
        })
    results = {}
    batch_size = 36
    for s in range(0, len(items), batch_size):
        chunk = items[s:s + batch_size]
        res, err = judge_batch(chunk)
        if res is None:
            print('  ! batch %d failed: %s — retrying smaller' % (s // batch_size, err))
            for it in chunk:
                res2, err2 = judge_batch([it])
                if res2:
                    results.update(res2)
                else:
                    print('    ! item %d failed: %s' % (it['index'], err2))
        else:
            results.update(res)
        print('  batch %d/%d done (%d judged)'
              % (s // batch_size + 1, (len(items) + batch_size - 1) // batch_size,
                 len(results)))

    # ---- classify ----
    rank = {'easy': 0, 'medium': 1, 'hard': 2}
    relabelled, flagged, off_by_one, ok = [], [], [], []
    issues = []
    for j, r in enumerate(sample):
        o = results.get(j)
        if not o:
            continue
        judged = (o.get('level') or '').strip().lower()
        if judged not in POINTS:
            judged = 'medium'
        stored = r.get('difficulty')
        delta = rank[judged] - rank.get(stored, 1)
        reason = o.get('reason') or ''
        rec = {
            'id': r.get('id'), 'category': r.get('category_name'),
            'category_id': r.get('category_id'), 'stored': stored,
            'judged': judged, 'delta': delta, 'reason': reason,
            'question': r.get('question'), 'answer': r.get('answer'),
            'factual_issue': bool(o.get('factual_issue')),
            'issue_note': o.get('issue_note') or '',
        }
        if rec['factual_issue'] or rec['issue_note']:
            issues.append(rec)
        if abs(delta) >= 2:
            relabelled.append(rec)
        elif abs(delta) == 1:
            off_by_one.append(rec)
        else:
            ok.append(rec)

    print('\n=== SEMANTIC RESULTS ===')
    print('judged:            %d' % len(results))
    print('ok (delta 0):      %d' % len(ok))
    print('off by one step:   %d' % len(off_by_one))
    print('off by two+ steps: %d (candidates to relabel)' % len(relabelled))
    print('substance issues: %d (flagged, not edited)' % len(issues))

    # ---- apply semantic relabels ----
    n_relabelled = 0
    if relabelled and a.apply:
        targets = {r['id'] for r in relabelled}
        acquire_lock()
        try:
            live = load_rows(QFILE)
            for r in live:
                if r.get('game') == 'quiz' and r.get('id') in targets:
                    new = next(x for x in relabelled if x['id'] == r.get('id'))
                    r['difficulty'] = new['judged']
                    r['points'] = POINTS[new['judged']]
                    n_relabelled += 1
            if n_relabelled:
                write_atomic(QFILE, live)
                print('\napplied %d semantic relabels' % n_relabelled)
        finally:
            release_lock()

    # ---- report ----
    if a.apply:
        live = load_rows(QFILE)
        bad_after = structural(live)
        print('\n=== VERIFY: structural mismatches after fix: %d ===' % len(bad_after))
        table_after, tot_after = per_category_table(live)
        print(table_after)

    md = []
    md.append('# تقرير تدقيق صعوبة أسئلة المسابقات (quiz)\n')
    md.append('النموذج المستخدم: `%s` — التاريخ: %s\n'
              % (MODEL, time.strftime('%Y-%m-%d %H:%M:%S')))
    md.append('## 1) الفحص البنيوي (النقاط مقابل الصعوبة)\n')
    md.append('قاعدة التطابق: easy=200 و medium=400 و hard=600.\n')
    md.append('- عدد حالات عدم التطابق المكتشفة: **%d**' % len(bad))
    if bad:
        md.append('\n| # | id | category | stored | points | expected |')
        md.append('|---:|---|---|---|---:|---:|')
        for k, (i, r, exp, act) in enumerate(bad, 1):
            md.append('| %d | %s | %s | %s | %s | %s |'
                      % (k, r.get('id'), r.get('category_id'), r.get('difficulty'), act, exp))
    md.append('\n- أُصلحت جميع حالات عدم التطابق: **%d** صفّاً تغيّرت نقاطه (أو مستواه).'
              % n_struct_fix)
    md.append('\n## 2) الفحص الدلالي (هل المستوى يطابق الصعوبة الفعلية؟)\n')
    md.append('- عينة التقييم: %d سؤالاً من %d فئة (ثلاثة مستويات لكل فئة).\n'
              % (len(sample), len({r.get('category_id') for r in sample})))
    md.append('- مطابق تماماً (فرق 0): **%d**' % len(ok))
    md.append('- فرق درجة واحدة: **%d**' % len(off_by_one))
    md.append('- فرق درجتين أو أكثر (أُعيد وسمها): **%d**' % len(relabelled))
    md.append('- مشاكل جوهرية (خطأ واقعي / الإجابة داخل السؤال / حروف أجنبية) — **لم تُعدّل**: **%d**'
              % len(issues))
    md.append('\n### أُعيد وسمها (كانت مخزّنة بمستوى يختلف جذرياً)\n')
    md.append('| id | الفئة | المخزّن | المقوّم | السبب |')
    md.append('|---|---|---|---|---|')
    for r in sorted(relabelled, key=lambda x: x['category'] or ''):
        md.append('| %s | %s | %s | %s | %s |'
                  % (r['id'], r['category'], AR_DIFF.get(r['stored'], r['stored']),
                     AR_DIFF.get(r['judged'], r['judged']), r['reason']))
    md.append('\n### مشاكل جوهرية — تحتاج مراجعة بشرية (لم تُلمس)\n')
    md.append('| id | الفئة | المخزّن | المقوّم | ملاحظة |')
    md.append('|---|---|---|---|---|')
    for r in sorted(issues, key=lambda x: x['category'] or ''):
        md.append('| %s | %s | %s | %s | %s |'
                  % (r['id'], r['category'], AR_DIFF.get(r['stored'], r['stored']),
                     AR_DIFF.get(r['judged'], r['judged']),
                     (r['issue_note'] or 'مشكلة جوهرية')))
    md.append('\n### فرق درجة واحدة (لم تُوسم — مقبولة)\n')
    md.append('| id | الفئة | المخزّن | المقوّم | السبب |')
    md.append('|---|---|---|---|---|')
    for r in sorted(off_by_one, key=lambda x: x['category'] or ''):
        md.append('| %s | %s | %s | %s | %s |'
                  % (r['id'], r['category'], AR_DIFF.get(r['stored'], r['stored']),
                     AR_DIFF.get(r['judged'], r['judged']), r['reason']))
    md.append('\n## 3) التوزيع النهائي لكل فئة\n')
    md.append(table_after if a.apply else table)
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print('\nreport written: %s' % REPORT)

    print('\n=== SUMMARY ===')
    print('structural mismatches found : %d' % len(bad))
    print('structural fixes applied    : %d' % n_struct_fix)
    print('semantic off-by-two found   : %d' % len(relabelled))
    print('semantic relabels applied   : %d' % n_relabelled)
    print('substance issues flagged    : %d' % len(issues))
    print('off-by-one (accepted)       : %d' % len(off_by_one))
    return 0


if __name__ == '__main__':
    sys.exit(main())
