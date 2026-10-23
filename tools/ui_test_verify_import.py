# -*- coding: utf-8 -*-
"""هل الاستيراد يعمل فعلاً؟ نجرّب الملف المرفق (التقرير) ثم ملف الأسئلة الحقيقي.

يفتح لوحة الإدارة في متصفح حقيقي على tools/ui_test_server.py (نفس كود المشروع
ونفس مخازنه) ويمرّ على الحالتين بالتسلسل.
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
REPORT = r'C:\Users\Ameen Dawaghreh\Downloads\ameen-questions-final-report.json'
QUESTIONS = r'C:\Users\Ameen Dawaghreh\Downloads\ameen-questions.json'
Q_FILE = os.path.join(ROOT, 'data', 'questions', 'all.json')
STORES = [Q_FILE, os.path.join(ROOT, 'data', 'questions', 'import_history.json'),
          os.path.join(ROOT, 'data', 'questions', 'import_draft.json')]


def letters():
    return [q for q in json.load(open(Q_FILE, encoding='utf-8')) if q.get('game') == 'letters']


def other_games():
    return [q['id'] for q in json.load(open(Q_FILE, encoding='utf-8')) if q.get('game') != 'letters']


def run_batch(page, text, mode, label):
    page.select_option('#impGame', 'letters')
    page.wait_for_selector('#impLetter', timeout=5000)
    page.select_option('#impMode', mode)
    page.wait_for_timeout(400)
    page.evaluate("""([sel, val]) => {
        const el = document.querySelector(sel);
        el.value = val;
        el.dispatchEvent(new Event('input', {bubbles: true}));
    }""", ['#impText', text])
    page.click('#impAnalyzeBtn')
    # التنبيه يُزال بعد 3 ثوانٍ، فنلتقطه فوراً
    toasts = []
    for _ in range(12):
        page.wait_for_timeout(250)
        got = page.eval_on_selector_all('.toast', 'els => els.map(e => e.className + ": " + e.textContent)')
        if got:
            toasts = got
            break
    if toasts:
        print('  التنبيه:', toasts)
    try:
        page.wait_for_selector('#impSummaryCard', state='visible', timeout=90000)
    except Exception:
        print('  لا تظهر نتيجة — التنبيهات:', toasts)
        return 'NO SUMMARY (error toast shown)', True
    page.wait_for_timeout(1200)
    final = (page.text_content('#impFinal') or '').replace('\n', ' | ')
    print('  final  :', final[:230])
    btn_disabled = page.eval_on_selector('#impSaveBtn', 'e => e.disabled')
    print('  save btn disabled:', btn_disabled)
    return final, btn_disabled


def main():
    snap = {p: (open(p, 'rb').read() if os.path.exists(p) else None) for p in STORES}
    report_text = io.open(REPORT, encoding='utf-8').read()
    q_text = io.open(QUESTIONS, encoding='utf-8').read()

    print('الملف المرفق (التقرير):')
    print('  الحجم:', len(report_text), 'حرف')
    print('  المحتوى:', json.dumps(json.loads(report_text), ensure_ascii=False)[:200])
    print('  عدد الأسئلة بداخله:',
          len(json.loads(report_text).get('questions', [])) if isinstance(json.loads(report_text), dict) else '?')
    print()
    print('ملف الأسئلة الحقيقي:', len(q_text), 'حرف،',
          len(json.loads(q_text)), 'سؤالًا')

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

            print()
            print('=== 1) الملف المرفق (التقرير) بوضع الاستبدال ===')
            before = len(letters())
            run_batch(page, report_text, 'replace', 'report')
            print('  أسئلة الحروف قبل/بعد:', before, '->', len(letters()))

            print()
            print('=== 2) ملف الأسئلة الحقيقي بوضع الاستبدال ===')
            before = len(letters())
            other_before = other_games()
            page.wait_for_timeout(300)
            final, disabled = run_batch(page, q_text, 'replace', 'questions')
            if not disabled:
                page.click('#impSaveBtn')
                page.wait_for_selector('#confirmModal', state='visible', timeout=20000)
                print('  confirm:', (page.text_content('#cfmBody') or '').replace('\n', ' | '))
                page.click('#cfmOk')
                page.wait_for_selector('#impResultCard', state='visible', timeout=90000)
                page.wait_for_timeout(1500)
                print('  result :', (page.text_content('#impResult') or '').replace('\n', ' | ')[:230])

            want = {(x['letter'], x['question'], x['answer']) for x in json.loads(q_text)}
            got = {(q['letter'], q['question'], q['answer']) for q in letters()}
            print()
            print('  أسئلة الحروف قبل/بعد:', before, '->', len(got))
            print('  مطابق للملف          :', got == want,
                  '| فرق شكل الحرف فقط:', len(want - got))
            print('  الألعاب الأخرى سليمة  :', other_before == other_games())
            print('  أخطاء JavaScript     :', errs[:3])
            browser.close()
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
