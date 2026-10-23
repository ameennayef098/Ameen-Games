# -*- coding: utf-8 -*-
"""اختبار واجهة «وضع الحفظ: إضافة / استبدال» في تبويب استيراد دفعة.

يشغّل tools/ui_test_server.py (منفذ 5599) ثم يفتح اللوحة بـ Playwright ويجرّب:
اختيار وضع الاستبدال، ظهور نطاق الحذف وعدّاده، لصق ملف JSON، التحليل،
الحفظ مع التأكيد، ثم يتأكد أن الأسئلة وصلت إلى اللعبة.

يأخذ نسخة من المخازن ويعيدها في النهاية.

شغّلها:  python tools/ui_test_replace.py
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from playwright.sync_api import sync_playwright  # noqa: E402

BASE = 'http://127.0.0.1:5599'
TOKEN = 'uitest-token'
Q_FILE = os.path.join(ROOT, 'data', 'questions', 'all.json')
HIST_FILE = os.path.join(ROOT, 'data', 'questions', 'import_history.json')
DRAFT_FILE = os.path.join(ROOT, 'data', 'questions', 'import_draft.json')
STORES = [Q_FILE, HIST_FILE, DRAFT_FILE]
RESULTS = []

LETTERS_JSON = json.dumps([
    {"game": "letters", "letter": "ف", "question": "ما أسرع حيوان بري؟",
     "answer": "الفهد", "difficulty": "medium"},
    {"game": "letters", "letter": "ف", "question": "ما أكبر صحراء في العالم؟",
     "answer": "الفاتيكان", "difficulty": "hard"},
    {"game": "letters", "letter": "بـ", "question": "ما أول سورة في المصحف؟",
     "answer": "البقرة", "difficulty": "easy"},
], ensure_ascii=False)


def check(name, cond, extra=''):
    RESULTS.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (('  -> ' + str(extra)) if extra else ''))


def store():
    return json.load(open(Q_FILE, encoding='utf-8'))


def letters():
    return [q for q in store() if q.get('game') == 'letters']


def main():
    snapshot = {}
    for p in STORES:
        snapshot[p] = open(p, 'rb').read() if os.path.exists(p) else None

    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, 'tools', 'ui_test_server.py')],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(40):
            time.sleep(0.5)
            if proc.poll() is not None:
                raise SystemExit('ui_test_server exited early')
            try:
                urllib.request.urlopen(BASE + '/admin', timeout=2)
                break
            except Exception:
                continue

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1400, 'height': 1000})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)

            page.goto(BASE + '/admin')
            page.evaluate("t => sessionStorage.setItem('ameen_admin_token', t)", TOKEN)
            page.reload()
            page.wait_for_selector('#adminDash', state='visible', timeout=15000)

            page.click('.tab[data-tab="import"]')
            page.wait_for_function("document.getElementById('impGame').options.length > 5",
                                   timeout=15000)

            # --- لا يوجد زر وضع الحفظ قبل التحديث؟ يجب أن يوجد الآن ---------
            check('قائمة «وضع الحفظ» موجودة', page.query_selector('#impMode') is not None)
            modes = page.eval_on_selector_all('#impMode option', 'els => els.map(e => e.value)')
            check('الوضعان متاحان (إضافة / استبدال)', modes == ['append', 'replace'], modes)

            # --- اختيار لعبة الحروف -----------------------------------------
            page.select_option('#impGame', 'letters')
            page.wait_for_selector('#impLetter', timeout=5000)
            check('نطاق الحذف مخفي في وضع الإضافة',
                  page.eval_on_selector('#impScopeWrap', 'e => getComputedStyle(e).display') == 'none')

            # --- التبديل إلى الاستبدال يظهر النطاق والعدّاد -----------------
            page.select_option('#impMode', 'replace')
            page.wait_for_timeout(600)
            check('نطاق الحذف يظهر في وضع الاستبدال',
                  page.eval_on_selector('#impScopeWrap', 'e => getComputedStyle(e).display') != 'none')
            note = page.text_content('#impModeNote') or ''
            check('ملاحظة الاستبدال تحذر من الحذف',
                  'حذف' in note and 'سؤالاً قديماً' in note, note[:140])
            check('عدّاد الحذف يظهر عدداً', any(ch.isdigit() for ch in note), note[:160])
            scopes = page.eval_on_selector_all('#impScope option', 'els => els.map(e => e.value)')
            check('نطاقان متاحان (اللعبة / الحرف أو الفئة)', scopes == ['game', 'target'], scopes)

            # --- لصق ملف JSON وتحليله ---------------------------------------
            page.fill('#impText', LETTERS_JSON)
            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=25000)
            page.wait_for_timeout(700)
            rows = page.eval_on_selector_all('#impBody tr', 'els => els.length')
            check('المعاينة تعرض 3 سجلات من ملف JSON', rows == 3, rows)
            final = page.text_content('#impFinal') or ''
            check('الملخص يذكر وضع الاستبدال', 'استبدال' in final, final[:200])
            check('«متوقع إضافته» = 3', '3' in final, final[:200])

            # --- حفظ الاستبدال مع التأكيد ----------------------------------
            before_other = [q['id'] for q in store() if q.get('game') != 'letters']
            before_n = len(letters())
            page.click('#impSaveBtn')
            page.wait_for_selector('#confirmModal', state='visible', timeout=15000)
            body = page.text_content('#cfmBody') or ''
            check('التأكيد يذكر عدد المحذوف', str(before_n) in body, body[:220])
            check('التأكيد يحذر من الحذف النهائي', 'نهائياً' in body, body[:220])
            page.click('#cfmOk')
            page.wait_for_selector('#impResultCard', state='visible', timeout=25000)
            page.wait_for_timeout(900)
            result = page.text_content('#impResult') or ''
            check('نتيجة الحفظ تقول إن الحفظ نجح', 'تم الحفظ بنجاح' in result, result[:200])
            check('نتيجة الحفظ تذكر عدد المحذوف', str(before_n) in result, result[:260])

            now = letters()
            check('أسئلة الحروف أصبحت 3 فقط (استبدال كامل)', len(now) == 3,
                  '%d -> %s' % (before_n, [q['question'] for q in now]))
            check('الأسئلة هي أسئلة الملف',
                  {q['question'] for q in now} ==
                  {'ما أسرع حيوان بري؟', 'ما أكبر صحراء في العالم؟', 'ما أول سورة في المصحف؟'})
            check('حرف الباء المُطوَّل خُزّن «ب»',
                  any(q.get('letter') == 'ب' for q in now),
                  sorted({q.get('letter') for q in now}))
            check('الألعاب الأخرى لم تُمسّ',
                  [q['id'] for q in store() if q.get('game') != 'letters'] == before_other)

            # --- اللعبة نفسها ترى الأسئلة الجديدة --------------------------
            page.goto(BASE + '/game/letters')
            page.wait_for_timeout(1200)
            page.goto(BASE + '/api/questions?game=letters&per_page=5000')
            data = json.loads(page.text_content('body') or '{}')
            check('واجهة اللعبة تقرأ الأسئلة الثلاثة', data.get('total') == 3, data.get('total'))

            # --- وضع الإضافة ما زال يعمل -----------------------------------
            page.goto(BASE + '/admin')
            page.reload()
            page.wait_for_selector('#adminDash', state='visible', timeout=15000)
            page.click('.tab[data-tab="import"]')
            page.wait_for_function("document.getElementById('impGame').options.length > 5",
                                   timeout=15000)
            page.select_option('#impGame', 'letters')
            page.wait_for_selector('#impLetter', timeout=5000)
            page.select_option('#impLetter', 'ف')
            page.select_option('#impMode', 'append')
            page.wait_for_timeout(300)
            page.fill('#impText', 'س1: ما ثمرة حمراء للاختبار؟\nج1: فراولة')
            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=25000)
            page.wait_for_timeout(600)
            n_before = len(letters())
            page.click('#impSaveBtn')
            page.wait_for_selector('#confirmModal', state='visible', timeout=15000)
            page.click('#cfmOk')
            page.wait_for_selector('#impResultCard', state='visible', timeout=25000)
            page.wait_for_timeout(900)
            check('وضع الإضافة أضاف سؤالاً دون حذف', len(letters()) == n_before + 1,
                  '%d -> %d' % (n_before, len(letters())))

            check('لا أخطاء JavaScript أثناء الاختبار', not errors, errors[:3])

            page.screenshot(path=os.path.join(ROOT, 'agent-reports', 'replace-mode-ui.png'),
                            full_page=False)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        for p, data in snapshot.items():
            if data is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                open(p, 'wb').write(data)

    bad = [n for n, ok in RESULTS if not ok]
    print('\n%d/%d passed' % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        print('FAILED: ' + '; '.join(bad))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
