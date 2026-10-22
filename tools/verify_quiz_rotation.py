#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify quiz question rotation: a second game must not repeat the first game's questions."""
import json
import sys
from playwright.sync_api import sync_playwright

URL = 'http://localhost:5555/game/quiz'
results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + (('  -> ' + str(extra)) if extra else ''))


def board_ids(pg):
    return pg.evaluate('JSON.stringify(QS.boards)')


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.wait_for_timeout(1500)

    # clear any previous rotation history, then re-render the category list
    pg.evaluate("localStorage.removeItem('ameen_quiz_used')")
    pg.evaluate('loadCategories()')
    pg.wait_for_timeout(1500)

    # pick 6 categories (AFTER the re-render, or the selection is wiped)
    boxes = pg.locator('#categorySelection input')
    n = boxes.count()
    check('categories are listed', n >= 30, n)
    for i in range(6):
        boxes.nth(i).check()
    check('counter shows 6/6', '6/6' in pg.locator('#catCount').inner_text(),
          pg.locator('#catCount').inner_text())

    # ---- game 1 ----
    pg.click('button:has-text("ابدأ اللعبة")')
    pg.wait_for_timeout(6000)
    check('game 1 board rendered', pg.locator('#quizBoard .jcell').count() == 36,
          pg.locator('#quizBoard .jcell').count())
    b1 = json.loads(board_ids(pg))
    used1 = pg.evaluate("JSON.parse(localStorage.getItem('ameen_quiz_used')||'{}')")
    check('rotation history stored after game 1', len(used1) == 6, list(used1.keys()))
    ids1 = {cid: [q['id'] for q in board] for cid, board in b1.items()}

    # ---- game 2 with the same 6 categories ----
    pg.click('button:has-text("العب مرة أخرى")') if pg.locator('#winnerModal.active').count() else None
    pg.evaluate('resetQuizGame()')
    pg.wait_for_timeout(500)
    for i in range(6):
        pg.locator('#categorySelection input').nth(i).check()
    pg.click('button:has-text("ابدأ اللعبة")')
    pg.wait_for_timeout(6000)
    b2 = json.loads(board_ids(pg))
    ids2 = {cid: [q['id'] for q in board] for cid, board in b2.items()}

    rotated = []
    for cid in ids1:
        if cid in ids2:
            overlap = set(ids1[cid]) & set(ids2[cid])
            rotated.append((cid, len(overlap)))
    check('game 2 reuses no question from game 1 (same 6 categories)',
          all(o == 0 for _, o in rotated), rotated)

    # ---- reset clears the history ----
    pg.evaluate('resetQuizGame()')
    pg.wait_for_timeout(600)
    pg.click('button:has-text("تصفير الكل")')
    pg.wait_for_timeout(400)
    check('تصفير الكل clears the history',
          pg.evaluate("localStorage.getItem('ameen_quiz_used')") in (None, '{}', ''))

    check('no page errors', not errors, errors[:3])
    b.close()

fails = [r for r in results if not r[1]]
print()
print('TOTAL: %d checks, %d passed, %d failed' % (len(results), len(results) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
