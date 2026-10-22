#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the reworked letters game: 5x5 board, timer/buzzer, change-team."""
import sys
from playwright.sync_api import sync_playwright

URL = 'http://localhost:5555/game/letters'
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
    pg.wait_for_timeout(1500)

    # setup
    pg.fill('#team1Name', 'فريق الأحمر')
    pg.fill('#team2Name', 'فريق الأزرق')
    pg.select_option('#timerDuration', '5')
    check('timer select offers 5 and 10',
          pg.locator('#timerDuration option').count() == 2)

    # start
    pg.click('button:has-text("ابدأ اللعبة")')
    pg.wait_for_timeout(1500)

    n = pg.locator('#hexBoard .hexg').count()
    check('board has exactly 25 cells', n == 25, n)

    txt = pg.locator('#letters-game').inner_text()
    check('turn indicator text removed',
          'دور الفريق الأول' not in txt and 'دور الفريق الثاني' not in txt, txt[:60].replace('\n', ' '))

    check('fullscreen button present', pg.locator('#fullscreenBtn').count() == 1)
    check('change-team button present', pg.locator('button:has-text("تصحيح آخر إجابة")').count() >= 1)

    # ---- question 1: bell -> answered within time ----
    pg.locator('#hexBoard .hexg').nth(0).click()
    pg.wait_for_timeout(500)
    check('question modal opened', pg.locator('#questionModal.active').count() == 1)
    check('answer NOT revealed before bell', pg.locator('#revealSection').is_hidden())

    pg.click('#bellBtn1')
    pg.wait_for_timeout(300)
    check('bell winner recorded', pg.evaluate('bellWinner') == 1, pg.evaluate('bellWinner'))
    check('timer row visible', pg.locator('#timerRow').is_visible())
    check('لقد أجبت button visible', pg.locator('button:has-text("لقد أجبت")').is_visible())

    pg.click('button:has-text("لقد أجبت")')
    pg.wait_for_timeout(300)
    check('answer revealed after لقد أجبت', pg.locator('#revealSection').is_visible())
    check('claim section visible', pg.locator('#claimSection').is_visible())

    pg.click('#claimBtn1')
    pg.wait_for_timeout(400)
    check('team1 score = 1', pg.locator('#score1Value').inner_text().strip() == '1',
          pg.locator('#score1Value').inner_text())

    # ---- question 2: bell -> let the timer expire -> passes to team 2 ----
    pg.locator('#hexBoard .hexg').nth(1).click()
    pg.wait_for_timeout(500)
    pg.click('#bellBtn1')
    pg.wait_for_timeout(300)
    check('q2 bell winner is 1', pg.evaluate('bellWinner') == 1)
    pg.wait_for_timeout(5600)  # 5s timer expires
    tm = pg.evaluate('timerTeam')
    check('timeout handed the question to team 2', tm == 2, tm)
    check('timer still running for team 2', pg.locator('#timerRow').is_visible())

    pg.click('button:has-text("لقد أجبت")')
    pg.wait_for_timeout(300)
    pg.click('#claimBtn2')
    pg.wait_for_timeout(400)
    check('team2 score = 1', pg.locator('#score2Value').inner_text().strip() == '1',
          pg.locator('#score2Value').inner_text())

    # ---- change-team correction ----
    pg.click('button:has-text("تصحيح آخر إجابة")')
    pg.wait_for_timeout(400)
    s2 = pg.locator('#score2Value').inner_text().strip()
    s1 = pg.locator('#score1Value').inner_text().strip()
    check('change-team moved the claim from team2 to team1',
          s2 == '0' and s1 == '2', 't1=%s t2=%s' % (s1, s2))

    # ---- stable ordering: same letter always same order ----
    order1 = pg.evaluate('JSON.stringify(Object.keys(questionsByLetter).map(function(k){return questionsByLetter[k].map(function(q){return q.id});}))')
    pg.reload()
    pg.wait_for_timeout(1500)
    pg.click('button:has-text("ابدأ اللعبة")')
    pg.wait_for_timeout(1500)
    order2 = pg.evaluate('JSON.stringify(Object.keys(questionsByLetter).map(function(k){return questionsByLetter[k].map(function(q){return q.id});}))')
    check('question order per letter is identical across games', order1 == order2)

    check('no page errors', not errors, errors[:3])
    b.close()

fails = [r for r in results if not r[1]]
print()
print('TOTAL: %d checks, %d passed, %d failed' % (len(results), len(results) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
