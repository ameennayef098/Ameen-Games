# -*- coding: utf-8 -*-
"""فحص إضافي لواجهة الاستيراد: مئة سؤال عبر المتصفح، وشاشة صغيرة (موبايل).

شغّلها:  python tools/ui_test_import_extra.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = 'http://127.0.0.1:5599'
TOKEN = 'uitest-token'
STORES = [os.path.join(ROOT, 'data', 'questions', 'all.json'),
          os.path.join(ROOT, 'data', 'questions', 'import_history.json'),
          os.path.join(ROOT, 'data', 'questions', 'import_draft.json')]
RESULTS = []


def check(name, cond, extra=''):
    RESULTS.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (('  -> ' + str(extra)) if extra else ''))


def hundred(prefix):
    out = []
    for i in range(1, 101):
        out.append('س%d: %s رقم %d؟' % (i, prefix, i))
        out.append('ج%d: جواب %d' % (i, i))
    return '\n\n'.join(out)


def main():
    snap = {}
    for p in STORES:
        if os.path.exists(p):
            with open(p, 'rb') as f:
                snap[p] = f.read()

    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, 'tools', 'ui_test_server.py')],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            time.sleep(0.5)
            try:
                urllib.request.urlopen(BASE + '/admin', timeout=2)
                break
            except Exception:
                continue

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)

            # ---------------- 100 questions through the real UI ----------------
            page = browser.new_page(viewport={'width': 1400, 'height': 950})
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(BASE + '/admin')
            page.evaluate("t => sessionStorage.setItem('ameen_admin_token', t)", TOKEN)
            page.reload()
            page.wait_for_selector('#adminDash', state='visible', timeout=15000)
            page.click('.tab[data-tab="import"]')
            page.wait_for_function("document.getElementById('impGame').options.length > 5", timeout=15000)

            page.select_option('#impGame', 'quiz')
            page.wait_for_selector('#impCat', timeout=5000)
            page.select_option('#impCat', 'science')
            page.wait_for_timeout(300)
            page.fill('#impText', hundred('المئة'))
            pasted = page.input_value('#impText')
            counter = page.text_content('#impTextInfo') or ''
            check('العداد يطابق النص الملصق (100 سؤال)',
                  str(pasted.count(chr(10)) + 1) in counter and str(len(pasted)) in counter,
                  counter + ' vs ' + str(pasted.count(chr(10)) + 1) + ' lines')

            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=30000)
            page.wait_for_timeout(1500)
            rows = page.eval_on_selector_all('#impBody tr', 'els => els.length')
            check('المعاينة تعرض 100 سجل', rows == 100, rows)
            fin = page.text_content('#impFinal') or ''
            check('المتوقع 100', 'التي ستضاف: 100' in fin, fin[:150])

            page.click('#impSaveBtn')
            page.wait_for_selector('#confirmModal.active', timeout=5000)
            page.click('#cfmOk')
            page.wait_for_selector('#impResultCard', state='visible', timeout=30000)
            page.wait_for_timeout(1500)
            res = page.text_content('#impResult') or ''
            check('حفظ 100 سؤال عبر الواجهة', '100' in res and 'تم الحفظ بنجاح' in res, res[:140])

            url = BASE + '/api/questions?game=quiz&category=science&per_page=5000'
            req = urllib.request.Request(url, headers={'X-Admin-Token': TOKEN})
            data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
            new = [x for x in data['questions'] if x['question'].startswith('المئة')]
            check('المئة سؤال في المخزن', len(new) == 100, len(new))
            check('لا أخطاء JavaScript', not errors, errors[:2])
            page.close()

            # ---------------- small screen -----------------------------------
            m = browser.new_page(viewport={'width': 390, 'height': 844})
            merrs = []
            m.on('pageerror', lambda e: merrs.append(str(e)))
            m.goto(BASE + '/admin')
            m.evaluate("t => sessionStorage.setItem('ameen_admin_token', t)", TOKEN)
            m.reload()
            m.wait_for_selector('#adminDash', state='visible', timeout=15000)
            m.click('.tab[data-tab="import"]')
            m.wait_for_function("document.getElementById('impGame').options.length > 5", timeout=15000)
            m.wait_for_timeout(600)
            overflow = m.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check('لا تمرير أفقي على الشاشة الصغيرة', overflow <= 2, overflow)
            box = m.eval_on_selector('#impText', 'e => { const r = e.getBoundingClientRect();'
                                               ' return {w: Math.round(r.width), vw: window.innerWidth}; }')
            check('مربع النص داخل الشاشة', box['w'] <= box['vw'], box)
            check('تبويب الاستيراد ظاهر على الموبايل',
                  m.eval_on_selector('.tab[data-tab="import"]', 'e => getComputedStyle(e).display') != 'none')
            check('لا أخطاء JavaScript على الموبايل', not merrs, merrs[:2])
            m.select_option('#impGame', 'million')
            m.wait_for_timeout(500)
            m.fill('#impText', 'س1: سؤال؟\nخيارات: أ | ب | ج | د\nج1: ب')
            m.click('#impAnalyzeBtn')
            m.wait_for_selector('#impSummaryCard', state='visible', timeout=20000)
            m.wait_for_timeout(800)
            check('الموبايل: تحليل المليون يعمل',
                  '1' in (m.text_content('#impFinal') or ''), (m.text_content('#impFinal') or '')[:150])
            m.screenshot(path=os.path.join(ROOT, 'agent-reports', 'import-mobile.png'))
            m.close()
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        for p, blob in snap.items():
            with open(p, 'wb') as f:
                f.write(blob)

    failed = [r for r in RESULTS if not r[1]]
    print('\n===== %d/%d passed =====' % (len(RESULTS) - len(failed), len(RESULTS)))
    for n, _ in failed:
        print('FAILED: ' + n)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
