#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke-test «حروف مع أمين» in a real browser: board shape, letter set,
question opens for the clicked letter, answer reveal, and no dead letters."""
import sys
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5555'
LETTERS_25 = ['أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ر', 'ز', 'س', 'ش', 'ص',
              'ط', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي']
results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print('%s %s %s' % ('PASS' if ok else 'FAIL', name, detail), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_context().new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    page.goto(BASE + '/game/letters')
    page.wait_for_selector('#letters-setup', timeout=20000)
    page.evaluate("() => { const s=document.getElementById('timerDuration'); if(s) s.value='10'; }")
    page.evaluate("() => { const b=[...document.querySelectorAll('#letters-setup button')].find(x=>/ابدأ|بدء/.test(x.textContent)); if(b) b.click(); }")
    page.wait_for_selector('#letters-game', state='visible', timeout=20000)
    page.wait_for_timeout(1500)

    # T1 board has 25 cells
    n = page.evaluate("() => document.querySelectorAll('#hexBoard g[data-i]').length")
    check('T1 board has 25 cells', n == 25, 'cells=%s' % n)

    # T2 letters are exactly the expected set
    got = page.evaluate(
        "() => [...document.querySelectorAll('#hexBoard g[data-i]')]"
        ".map(g => (g.textContent || '').trim()).filter(Boolean).sort()")
    check('T2 letter set is LETTERS_25', got == sorted(LETTERS_25),
          'got=%d distinct=%d' % (len(got), len(set(got))))

    # T3 question opens with the clicked cell's letter
    clicked = page.evaluate("""() => {
        const gs = [...document.querySelectorAll('#hexBoard g[data-i]')];
        const g = gs.find(x => !x.dataset.owner || x.dataset.owner === '' || x.dataset.owner === 'null') || gs[0];
        const letter = (g.textContent || '').trim();
        g.dispatchEvent(new MouseEvent('click', {bubbles: true}));
        return letter;
    }""")
    page.wait_for_selector('#questionModal.active', timeout=10000)
    badge = (page.text_content('#qLetterBadge') or '').strip()
    check('T3 question opens for the clicked letter', clicked in badge,
          'cell=%r badge=%r' % (clicked, badge))

    # T4 answer reveal works
    page.evaluate("() => { const b=[...document.querySelectorAll('#questionModal button')].find(x=>/إظهار|أظهر|الإجابة/.test(x.textContent)); if(b) b.click(); }")
    page.wait_for_timeout(400)
    ans = (page.text_content('#correctAnswer') or '').strip()
    check('T4 answer reveals', len(ans) > 0, 'answer=%r' % ans[:30])

    # T5 no dead letters: every board letter has at least one question
    dead = page.evaluate("""(letters) => {
        return fetch('/api/questions?game=letters&per_page=5000')
            .then(r => r.json())
            .then(d => {
                const norm = a => {
                    let s = String(a || '').trim();
                    if (!s) return '';
                    if ('إآٱاأ'.includes(s.charAt(0))) s = 'أ' + s.slice(1);
                    if (s.length > 2 && s.charCodeAt(0) === 0x0623 && s.charCodeAt(1) === 0x0644) s = s.slice(2);
                    if (s.charAt(0) === 'ا') s = 'أ' + s.slice(1);
                    return s.charAt(0);
                };
                const have = new Set((d.questions || []).map(q => norm(q.answer)));
                return letters.filter(l => !have.has(l));
            });
    }""", LETTERS_25)
    check('T5 no dead board letters', not dead, 'dead=%s' % dead)

    # T6 reset returns to the setup screen
    page.evaluate("() => { const b=[...document.querySelectorAll('#letters-game button')].find(x=>/إعادة|重置/.test(x.textContent)); if(b) b.click(); }")
    page.wait_for_timeout(600)
    setup_visible = page.evaluate(
        "() => { const s=document.getElementById('letters-setup'); return s && getComputedStyle(s).display !== 'none'; }")
    check('T6 reset returns to setup', setup_visible, 'visible=%s' % setup_visible)

    check('no JS page errors', not errors, '; '.join(errors[:3]))

    b.close()

passed = sum(1 for _, ok in results if ok)
print()
print('RESULT: %d/%d passed' % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
