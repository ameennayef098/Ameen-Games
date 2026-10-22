#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify من سيربح المليون plays end-to-end against the live server.

Covers:
  1. The game page loads and builds its question pool from the API
  2. A question renders with FOUR options and the correct answer among them
  3. Picking the right option advances the level; the ladder progresses
  4. Every question the game can serve is well-formed (4 options, answer inside)

Run with the server already up:  python tools/verify_million.py
"""
import json
import os
import sys
import urllib.request

PORT = int(os.environ.get('VERIFY_PORT', '5555'))
BASE = 'http://localhost:%d' % PORT


def api(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    failures = []
    print('=== 1. API pool ===')
    data = api('/api/questions?game=million&per_page=5000&status=approved')
    pool = data['questions']
    print('million approved: %d' % len(pool))
    bad = [q for q in pool
           if len(q.get('options') or []) != 4
           or q.get('answer') not in (q.get('options') or [])
           or len(set(q.get('options') or [])) != 4]
    print('malformed in pool: %d' % len(bad))
    if bad:
        failures.append('%d malformed million questions in the API pool' % len(bad))
        for q in bad[:5]:
            print('   ! %s | %s' % (q['question'][:50], q.get('options')))
    else:
        print('OK  every question has 4 distinct options containing the answer')

    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE + '/game/million', wait_until='load')
        page.wait_for_selector('#mil-setup')

        print()
        print('=== 2. game boot ===')
        page.click('button[onclick="startMillion()"]')
        page.wait_for_selector('#mil-game', state='visible', timeout=20000)
        qtext = (page.text_content('#milQuestion') or '').strip()
        opts = page.evaluate("Array.from(document.querySelectorAll('#milOptions button')).map(b=>b.textContent.trim())")
        print('question: %s' % qtext[:60])
        print('options : %s' % ' | '.join(opts))
        if len(opts) != 4:
            failures.append('game rendered %d options instead of 4' % len(opts))
        else:
            print('OK  question rendered with 4 options')

        print()
        print('=== 3. answering advances the level ===')
        lvl_before = (page.text_content('#milQNum') or '').strip()
        # click the correct option (the game stores the answer in the pool)
        correct = None
        for q in pool:
            if q['question'] == qtext:
                correct = q['answer']
                break
        clicked = False
        if correct:
            # Each option button is <span class="k">KEY</span><span>text</span>, so
            # textContent concatenates them ("أالأرض") — match on the tail.
            for i, o in enumerate(opts):
                if o.endswith(correct):
                    page.click('#milOptions button:nth-of-type(%d)' % (i + 1))
                    clicked = True
                    break
        if clicked:
            # answerMillion() bumps M.level immediately but only re-renders the
            # question number ~1.2s later inside nextQuestion().
            page.wait_for_timeout(2200)
            lvl_after = (page.text_content('#milQNum') or '').strip()
            info = (page.text_content('#milInfo') or '').strip()
            print('level: %s -> %s' % (lvl_before, lvl_after))
            print('feedback: %s' % info[:60])
            if lvl_after == lvl_before:
                failures.append('level did not advance after a correct answer')
            else:
                print('OK  correct answer advanced the level')
        else:
            failures.append('could not find the correct option on the page')
            print('! correct answer %r not among the rendered options' % (correct,))

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
    print('ALL MILLION CHECKS PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
