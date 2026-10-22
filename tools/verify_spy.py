#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the spy game hand-over screen actually hides the next player's secret."""
import sys
from playwright.sync_api import sync_playwright

URL = 'http://localhost:5555/game/spy'
results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + (('  -> ' + str(extra)) if extra else ''))


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.wait_for_timeout(1200)

    # step 1: pick a topic
    pg.locator('.spy-topic-btn').first.click()
    pg.wait_for_timeout(600)

    # step 2: player count
    pg.fill('#spyCount', '3')
    pg.click('button:has-text("التالي ←")')
    pg.wait_for_timeout(400)

    # step 3: names
    names = ['لاعب أ', 'لاعب ب', 'لاعب ج']
    for i, n in enumerate(names):
        pg.fill('#spyName%d' % i, n)
    pg.click('button:has-text("بدء")')
    pg.wait_for_timeout(500)

    check('role step is visible', pg.locator('#spyStep4.active').count() == 1)

    # --- walk the whole role phase ---
    leaked = []
    revealed = []
    for turn in range(3):
        # hand-over screen must be black card + hand-over text, and must NOT show the topic
        card = pg.locator('#spyRoleCard').inner_text()
        check('turn %d: hand-over text present' % (turn + 1), 'اعطي الجهاز ل' in card, card[:60].replace('\n', ' '))
        check('turn %d: black card class present' % (turn + 1),
              pg.locator('#spyRoleCard .spy-handover-card').count() == 1)
        # the topic word must not be visible before revealing
        body_txt = pg.locator('body').inner_text()
        topic = pg.evaluate('spyTopic ? spyTopic.word : ""')
        if topic and topic in card:
            leaked.append((turn + 1, topic))
        # reveal
        pg.locator('#spyHandoverBtn').click()
        pg.wait_for_timeout(300)
        revealed.append(pg.locator('#spyRoleCard').inner_text()[:70].replace('\n', ' '))
        # advance (the last advance moves on to the description phase)
        pg.click('button:has-text("مرر الجهاز")')
        pg.wait_for_timeout(300)

    check('topic never leaked on hand-over screens', not leaked, leaked)
    check('all 3 players got a reveal', len(revealed) == 3, revealed)

    # after the last player we should be in the description phase
    check('description phase reached after last player',
          pg.locator('#spyStep5.active').count() == 1)

    check('no page errors', not errors, errors[:3])
    b.close()

fails = [r for r in results if not r[1]]
print()
print('TOTAL: %d checks, %d passed, %d failed' % (len(results), len(results) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
