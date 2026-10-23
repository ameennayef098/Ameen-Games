# -*- coding: utf-8 -*-
"""البرهان الأخير: ملف المستخدم الحقيقي (1684 سؤالاً) عبر الواجهة نفسها.

يفتح لوحة الإدارة في متصفح حقيقي، يختار «حروف مع أمين»، يضبط وضع الحفظ على
«استبدال»، يلصق الملف كاملاً، يحلّل، ثم يحفظ ويؤكد — ويتحقق أن البنك صار
مطابقاً للملف وأن الألعاب الأخرى لم تُمسّ.
"""
import io
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
FILE = r'C:\Users\Ameen Dawaghreh\Downloads\ameen-questions.json'
Q_FILE = os.path.join(ROOT, 'data', 'questions', 'all.json')
STORES = [Q_FILE, os.path.join(ROOT, 'data', 'questions', 'import_history.json'),
          os.path.join(ROOT, 'data', 'questions', 'import_draft.json')]


def letters():
    return [q for q in json.load(open(Q_FILE, encoding='utf-8')) if q.get('game') == 'letters']


def main():
    snap = {p: (open(p, 'rb').read() if os.path.exists(p) else None) for p in STORES}
    text = io.open(FILE, encoding='utf-8').read()
    want = {(x['letter'], x['question'], x['answer'])
            for x in json.loads(text)}
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, 'tools', 'ui_test_server.py')],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(40):
            time.sleep(0.5)
            try:
                urllib.request.urlopen(BASE + '/admin', timeout=2)
                break
            except Exception:
                continue

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1400, 'height': 1000})
            errs = []
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)

            page.goto(BASE + '/admin')
            page.evaluate("t => sessionStorage.setItem('ameen_admin_token', t)", TOKEN)
            page.reload()
            page.wait_for_selector('#adminDash', state='visible', timeout=15000)
            page.click('.tab[data-tab="import"]')
            page.wait_for_function("document.getElementById('impGame').options.length > 5",
                                   timeout=15000)

            page.select_option('#impGame', 'letters')
            page.wait_for_selector('#impLetter', timeout=5000)
            page.select_option('#impMode', 'replace')
            page.wait_for_timeout(500)
            note = page.text_content('#impModeNote') or ''
            print('note:', note)

            before_other = [q['id'] for q in json.load(open(Q_FILE, encoding='utf-8'))
                            if q.get('game') != 'letters']
            before_n = len(letters())

            # fill البطيء لا يحتمل 700 ألف حرف — نضبط القيمة ونُرسل حدث input
            page.evaluate("""([sel, val]) => {
                const el = document.querySelector(sel);
                el.value = val;
                el.dispatchEvent(new Event('input', {bubbles: true}));
            }""", ['#impText', text])
            page.click('#impAnalyzeBtn')
            page.wait_for_selector('#impSummaryCard', state='visible', timeout=60000)
            page.wait_for_timeout(1200)
            final = page.text_content('#impFinal') or ''
            print('final:', final.replace('\n', ' | ')[:220])

            page.click('#impSaveBtn')
            page.wait_for_selector('#confirmModal', state='visible', timeout=20000)
            print('confirm:', (page.text_content('#cfmBody') or '').replace('\n', ' | '))
            page.click('#cfmOk')
            page.wait_for_selector('#impResultCard', state='visible', timeout=60000)
            page.wait_for_timeout(1500)
            print('result:', (page.text_content('#impResult') or '').replace('\n', ' | ')[:240])
            browser.close()

        got = {(q['letter'], q['question'], q['answer']) for q in letters()}
        after_other = [q['id'] for q in json.load(open(Q_FILE, encoding='utf-8'))
                       if q.get('game') != 'letters']
        print()
        print('before letters :', before_n)
        print('after  letters :', len(got))
        print('file   letters :', len(want))
        print('store == file  :', got == want)
        print('only letter-form differs:', len(want - got), sorted(want - got)[:3])
        print('other games untouched   :', before_other == after_other)
        print('js errors              :', errs[:3])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        for p, data in snap.items():
            if data is None:
                if os.path.exists(p):
                    os.remove(p)
            else:
                open(p, 'wb').write(data)


if __name__ == '__main__':
    main()
