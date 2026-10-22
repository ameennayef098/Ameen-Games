#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end verification of ألعاب أمين after the fixes.

Checks, against the LIVE server on PORT:
  1. حروف مع أمين — the board letter layout changes between matches
  2. حروف مع أمين — every one of the 25 letters draws a different first question
  3. س.ج — every category now holds >= 100 approved questions, with all three
     point bands present, so a 6-category board can always be built
  4. س.ج — a full board renders 6 columns x 6 cells and opening a cell shows
     the question + a working answer reveal

Usage: python tools/verify_all.py [--per-letter 3]
"""
import argparse
import json
import os
import sys
import urllib.request

PORT = int(os.environ.get('VERIFY_PORT', '5555'))
BASE_URL = 'http://localhost:%d' % PORT
LETTERS_25 = ['أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ر', 'ز', 'س', 'ش', 'ص',
              'ط', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي']


def api(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-letter', type=int, default=3)
    a = ap.parse_args()
    failures = []

    # ---------- 3) category coverage ----------
    cats = api('/api/categories')['categories']
    under = [c for c in cats if c.get('approved_count', 0) < 100]
    print('=== 1. س.ج category coverage ===')
    print('categories: %d   min approved: %d   max approved: %d'
          % (len(cats), min(c['approved_count'] for c in cats),
             max(c['approved_count'] for c in cats)))
    if under:
        failures.append('%d categories still under 100' % len(under))
        for c in under:
            print('   ! %-24s %d' % (c['name'], c['approved_count']))
    else:
        print('OK  every category has >= 100 approved questions')
    # every band present in every category
    thin = [c for c in cats if min(c.get('count_200', 0), c.get('count_400', 0),
                                   c.get('count_600', 0)) < 2]
    if thin:
        failures.append('%d categories lack a full 200/400/600 spread' % len(thin))
        for c in thin:
            print('   ! %-24s 200:%d 400:%d 600:%d'
                  % (c['name'], c.get('count_200', 0), c.get('count_400', 0),
                     c.get('count_600', 0)))
    else:
        print('OK  every category carries all three point bands (200/400/600)')

    # ---------- browser checks ----------
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))

        # ---------- 1+2) letters randomness ----------
        print()
        print('=== 2. حروف مع أمين — random first question per letter ===')
        page.goto(BASE_URL + '/game/letters', wait_until='load')
        page.wait_for_selector('#letters-setup')
        seen = {L: [] for L in LETTERS_25}
        layouts = []
        for L in LETTERS_25:
            for s in range(a.per_letter):
                page.evaluate("""() => {
                    localStorage.removeItem('ameen_letters_state');
                    const g = document.getElementById('letters-game');
                    const su = document.getElementById('letters-setup');
                    if (g) g.style.display = 'none';
                    if (su) su.style.display = 'block';
                    const q = document.getElementById('questionModal');
                    if (q) q.classList.remove('active');
                }""")
                page.fill('#team1Name', 'ت' + str(s))
                page.fill('#team2Name', 'ث' + str(s))
                page.click('button:has-text("ابدأ اللعبة")')
                page.wait_for_selector('#letters-game', state='visible')
                layout = page.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('#hexBoard .hexg').forEach(g => {
                        const t = g.querySelector('text');
                        out.push(t ? t.textContent : '?');
                    });
                    return out;
                }""")
                if not layouts or layouts[-1] != layout:
                    layouts.append(layout)
                idx = page.evaluate("""(target) => {
                    const gs = document.querySelectorAll('#hexBoard .hexg');
                    for (let i = 0; i < gs.length; i++) {
                        const t = gs[i].querySelector('text');
                        if (t && t.textContent === target) return i;
                    }
                    return -1;
                }""", L)
                if idx < 0:
                    break
                page.click('#hexBoard .hexg:nth-of-type(%d)' % (idx + 1))
                page.wait_for_selector('#questionModal.active', timeout=10000)
                seen[L].append((page.text_content('#questionText') or '').strip())
                page.evaluate("""() => {
                    const m = document.getElementById('questionModal');
                    if (m) m.classList.remove('active');
                }""")
                page.wait_for_timeout(60)

        distinct = len({tuple(l) for l in layouts})
        print('distinct board layouts: %d' % distinct)
        if distinct < 2:
            failures.append('board letter layout never changed')
        fixed_letters = [L for L in LETTERS_25
                         if len(seen[L]) > 1 and len(set(seen[L])) == 1]
        if fixed_letters:
            failures.append('letters with a fixed first question: %s' % ','.join(fixed_letters))
            for L in fixed_letters:
                print('   ! letter %s always -> %s' % (L, seen[L][0][:50]))
        else:
            print('OK  all 25 letters draw a different first question')
        for L in LETTERS_25:
            u = len(set(seen[L]))
            print('   letter %-3s : %d distinct / %d samples' % (L, u, len(seen[L])))

        # ---------- 4) س.ج board ----------
        print()
        print('=== 3. س.ج — board build ===')
        page.goto(BASE_URL + '/game/quiz', wait_until='load')
        page.wait_for_selector('#quiz-setup')
        page.evaluate("localStorage.removeItem('ameen_quiz_used')")
        page.evaluate("""() => { if (typeof loadCategories === 'function') loadCategories(); }""")
        page.wait_for_timeout(2500)
        # pick the first six categories
        picked = page.evaluate("""() => {
            const boxes = document.querySelectorAll('#categorySelection input');
            const out = [];
            for (let i = 0; i < boxes.length && out.length < 6; i++) {
                if (!boxes[i].checked) { boxes[i].checked = true; boxes[i].onchange(boxes[i]); }
                out.push(boxes[i].value);
            }
            return out;
        }""")
        page.click('button:has-text("ابدأ اللعبة")')
        page.wait_for_selector('#quiz-game', state='visible', timeout=30000)
        cols = page.evaluate("document.querySelectorAll('#quizBoard .jcol').length")
        cells = page.evaluate("document.querySelectorAll('#quizBoard .jcell').length")
        print('categories picked: %d   columns: %d   cells: %d' % (len(picked), cols, cells))
        if cols != 6 or cells != 36:
            failures.append('quiz board built %d cols / %d cells (expected 6/36)' % (cols, cells))
        else:
            print('OK  board is 6 columns x 6 cells')
        # open a cell and reveal the answer
        page.click('#quizBoard .jcell')
        page.wait_for_selector('#questionModal.active', timeout=10000)
        qtext = (page.text_content('#questionText') or '').strip()
        page.click('button:has-text("إظهار الإجابة")')
        page.wait_for_timeout(400)
        ans_visible = page.evaluate("""() => {
            const s = document.getElementById('answerSection');
            return s ? s.style.display !== 'none' : false;
        }""")
        ans = (page.text_content('#correctAnswer') or '').strip()
        print('question: %s' % qtext[:60])
        print('answer after reveal: %s   (answer section visible: %s)'
              % (ans[:40], ans_visible))
        if not ans_visible or not ans:
            failures.append('quiz answer reveal did not work')
        else:
            print('OK  question opens and the answer reveal works')

        browser.close()
        if errors:
            print()
            print('PAGE ERRORS:', errors[:5])
            failures.append('%d page JS errors' % len(errors))

    print()
    print('=' * 50)
    if failures:
        print('FAILED:')
        for f in failures:
            print('  - ' + f)
        return 1
    print('ALL CHECKS PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
