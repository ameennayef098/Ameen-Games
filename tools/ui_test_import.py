# -*- coding: utf-8 -*-
"""اختبار واجهة «استيراد دفعة أسئلة» في لوحة الإدارة عبر متصفح حقيقي.

يشغّل tools/ui_test_server.py (منفذ 5599) ثم يفتح اللوحة بـ Playwright ويجرّب:
اختيار اللعبة، اختيار الفئة، لصق النص، التحليل، المعاينة، التعديل، الاستبعاد،
ثم الحفظ والتأكد أن الأسئلة وصلت إلى اللعبة والفئة الصحيحين.

يأخذ نسخة من المخازن ويعيدها في النهاية حتى لا تبقى بيانات تجريبية.

شغّلها:  python tools/ui_test_import.py
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
STORES = [
    os.path.join(ROOT, 'data', 'questions', 'all.json'),
    os.path.join(ROOT, 'data', 'questions', 'import_history.json'),
    os.path.join(ROOT, 'data', 'questions', 'import_draft.json'),
]
RESULTS = []


def check(name, cond, extra=''):
    RESULTS.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + (('  -> ' + str(extra)) if extra else ''))


def q(n, prefix):
    out = []
    for i in range(1, n + 1):
        out.append('س%d: %s %d؟' % (i, prefix, i))
        out.append('ج%d: جواب %d' % (i, i))
    return '\n\n'.join(out)


def main():
    snapshot = {}
    for p in STORES:
        if os.path.exists(p):
            with open(p, 'rb') as f:
                snapshot[p] = f.read()

    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, 'tools', 'ui_test_server.py')],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            time.sleep(0.5)
            if proc.poll() is not None:
                raise SystemExit('ui_test_server exited early')
            try:
                import urllib.request
                urllib.request.urlopen(BASE + '/admin', timeout=2)
                break
            except Exception:
                continue

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1400, 'height': 950})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)

            # --- login via a pre-set session token -------------------------------
            page.goto(BASE + '/admin')
            page.evaluate("t => sessionStorage.setItem('ameen_admin_token', t)", TOKEN)
            page.reload()
            page.wait_for_selector('#adminDash', state='visible', timeout=15000)

            # --- open the import tab --------------------------------------------
            page.click('.tab[data-tab="import"]')
            page.wait_for_function("document.getElementById('impGame').options.length > 5", timeout=15000)
            games = page.eval_on_selector_all('#impGame option', 'els => els.map(e => e.value)')
            check('قائمة الألعاب حقيقية (13 لعبة)', len(games) == 13, games)

            # --- game = quiz, category = sports ---------------------------------
            page.select_option('#impGame', 'quiz')
            page.wait_for_selector('#impCat', timeout=5000)
            cats = page.eval_on_selector_all('#impCat option', 'els => els.map(e => e.value)')
            check('فئات س.ج تظهر ولا تظهر الحروف', len(cats) > 3 and 'sports' in cats, cats[:4])
            page.select_option('#impCat', 'sports')
            page.wait_for_timeout(300)
            check('قالب اللعبة يظهر', 'س1:' in (page.text_content('#impTpl') or ''),
                  (page.text_content('#impTpl') or '')[:60])

            # --- switch to letters: no category selector may appear -------------
            page.select_option('#impGame', 'letters')
            page.wait_for_timeout(500)
            check('حروف مع أمين تعرض الحروف ولا تعرض فئات',
                  page.query_selector('#impLetter') is not None
                  and page.query_selector('#impCat') is None)

            # --- back to quiz and analyse --------------------------------------
            page.select_option('#impGame', 'quiz')
            page.wait_for_selector('#impCat', timeout=5000)
            page.select_option('#impCat', 'sports')
            page.wait_for_timeout(200)

            text = q(3, 'واجهة الاختبار')
            page.fill('#impText', text)
            # the counter must agree with the text actually in the box
            pasted = page.input_value('#impText')
            counter = page.text_content('#impTextInfo') or ''
            check('عداد الأسطر والحروف يعمل',
                  str(pasted.count(chr(10)) + 1) in counter and str(len(pasted)) in counter,
                  counter + ' vs ' + str(pasted.count(chr(10)) + 1) + ' lines / ' + str(len(pasted)) + ' chars')
            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=20000)
            page.wait_for_timeout(800)

            rows = page.eval_on_selector_all('#impBody tr', 'els => els.length')
            check('المعاينة تعرض 3 سجلات', rows == 3, rows)
            nums = page.text_content('#impSummary') or ''
            check('الملخص يقول 3 صالح', '3' in nums, nums[:120])
            check('«متوقع إضافته» = 3', '3' in (page.text_content('#impFinal') or ''),
                  (page.text_content('#impFinal') or '')[:200])

            # --- edit one record inline ----------------------------------------
            page.click('#impBody tr:nth-child(2) button:has-text("تعديل")')
            page.wait_for_selector('#impEditModal.active', timeout=5000)
            page.fill('#impEditQ', 'سؤال معدَّل في الواجهة؟')
            page.click('#impEditSave')
            page.wait_for_timeout(900)
            body = page.text_content('#impBody') or ''
            check('التعديل داخل المعاينة يُحفظ', 'سؤال معدَّل في الواجهة؟' in body)

            # --- exclude one record --------------------------------------------
            page.click('#impBody tr:nth-child(3) button:has-text("استبعاد")')
            page.wait_for_timeout(900)
            check('الاستبعاد يُنقص العدد المتوقع', '2' in (page.text_content('#impFinal') or ''),
                  (page.text_content('#impFinal') or '')[:200])
            page.click('#impBody tr:nth-child(3) button:has-text("استعادة")')
            page.wait_for_timeout(900)

            # --- save with the confirmation summary ----------------------------
            page.click('#impSaveBtn')
            page.wait_for_selector('#confirmModal.active', timeout=5000)
            confirm = page.text_content('#cfmBody') or ''
            check('الملخص النهائي قبل الحفظ يظهر',
                  'عدد الأسئلة التي ستضاف' in confirm and '3' in confirm, confirm[:160])
            page.click('#cfmOk')
            page.wait_for_selector('#impResultCard', state='visible', timeout=20000)
            page.wait_for_timeout(1200)
            res = page.text_content('#impResult') or ''
            check('نتيجة الحفظ تقول 3', '3' in res and 'تم الحفظ بنجاح' in res, res[:200])

            # --- verify in the store -------------------------------------------
            import urllib.request
            url = BASE + '/api/questions?game=quiz&category=sports&per_page=5000'
            req = urllib.request.Request(url, headers={'X-Admin-Token': TOKEN})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
            new = [x for x in data['questions'] if x['question'].startswith(('واجهة الاختبار', 'سؤال معدَّل'))]
            check('الأسئلة وصلت إلى س.ج/الرياضة', len(new) == 3,
                  [x['question'][:24] for x in new])
            check('المصدر «استيراد» والحالة معتمد',
                  all(x['source'] == 'import' and x['status'] == 'approved' for x in new))

            # --- duplicate detection in the UI ---------------------------------
            page.fill('#impText', q(1, 'واجهة الاختبار'))
            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=20000)
            page.wait_for_timeout(800)
            body_dup = page.text_content('#impBody') or ''
            check('الواجهة تكشف التكرار الموجود مسبقاً', 'موجود مسبقاً' in body_dup, body_dup[:160])
            check('مربع «الاحتفاظ به» يظهر للمكرر',
                  page.query_selector('#impKeep-0') is not None)
            # one record in the batch and it is a duplicate -> nothing to add
            check('المكرر لا يُحسب ضمن المتوقع', 'التي ستضاف: 0' in (page.text_content('#impFinal') or ''),
                  (page.text_content('#impFinal') or '')[:200])
            page.check('#impKeep-0')
            page.wait_for_timeout(400)
            check('الاحتفاظ بالمكرر يعيده للمتوقع', 'التي ستضاف: 1' in (page.text_content('#impFinal') or ''),
                  (page.text_content('#impFinal') or '')[:200])
            page.uncheck('#impKeep-0')
            page.wait_for_timeout(300)

            # --- million needs options -----------------------------------------
            page.select_option('#impGame', 'million')
            page.wait_for_timeout(600)
            page.fill('#impText', 'س1: سؤال بلا خيارات؟\nج1: جواب')
            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=20000)
            page.wait_for_timeout(800)
            check('المليون يرفض سجلًا بلا 4 خيارات',
                  '4 خيارات' in (page.text_content('#impBody') or ''),
                  (page.text_content('#impBody') or '')[:200])

            # --- clear asks for confirmation -----------------------------------
            page.click('button:has-text("مسح النص")')
            page.wait_for_selector('#confirmModal.active', timeout=5000)
            page.click('#cfmOk')
            page.wait_for_timeout(400)
            check('مسح النص لا يحدث إلا بعد التأكيد', page.input_value('#impText') == '')

            # --- history recorded ----------------------------------------------
            page.wait_for_timeout(600)
            hist = page.text_content('#impHistory') or ''
            check('سجل الاستيراد يظهر في الواجهة', 'quiz' in hist and 'حُفظ 3' in hist, hist[:160])

            check('لا أخطاء JavaScript أثناء الاختبار', not errors, errors[:3])
            page.screenshot(path=os.path.join(ROOT, 'agent-reports', 'import-ui.png'),
                            full_page=False)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        for p, blob in snapshot.items():
            with open(p, 'wb') as f:
                f.write(blob)

    failed = [r for r in RESULTS if not r[1]]
    print('\n===== %d/%d passed =====' % (len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        for n, _, e in failed:
            print('FAILED: ' + n + ' -> ' + str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
