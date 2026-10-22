#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prove the س.ج turn-retention mechanic behaves as the host asked.

Rule: a team that answers correctly keeps the turn. A team that does NOT answer
offers the question to the other team; if they answer they take the points AND
keep the turn; if they also do not answer, the team that was offered it keeps
the turn. Skip keeps the turn too.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5555'
results = []


def check(name, ok, detail=''):
    results.append((name, ok, detail))
    print('%s %s %s' % ('PASS' if ok else 'FAIL', name, detail), flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    page.goto(BASE + '/game/quiz')
    page.wait_for_selector('#quiz-setup', timeout=20000)

    # exactly 6 categories, no timer
    page.evaluate("""() => {
        const boxes = [...document.querySelectorAll('#categorySelection input')];
        boxes.slice(0, 6).forEach(b => { if (!b.checked) b.click(); });
        const sel = document.getElementById('timerDuration');
        if (sel) sel.value = '0';
    }""")
    page.wait_for_timeout(400)
    count = page.text_content('#catCount') or ''
    check('setup: 6 categories selected', '(6/6)' in count, count)

    page.evaluate("() => document.querySelector('#quiz-setup button.btn-primary, #quiz-setup .setup-actions .btn-primary').click()")
    page.wait_for_selector('#quiz-game', state='visible', timeout=20000)
    page.wait_for_timeout(1500)

    cells = page.locator('#quizBoard .jcell')
    n = cells.count()
    check('board has cells', n >= 36, 'cells=%d' % n)

    def turn():
        return (page.text_content('#turnIndicator') or '').strip()

    def scores():
        return (page.text_content('#score1Value') or '0').strip(), \
               (page.text_content('#score2Value') or '0').strip()

    def open_first_free():
        """Open the first enabled board cell and reveal the answer."""
        idx = page.evaluate("""() => {
            const bs = [...document.querySelectorAll('#quizBoard .jcell')];
            const i = bs.findIndex(b => !b.disabled);
            return i;
        }""")
        if idx < 0:
            return None
        page.evaluate("(i) => document.querySelectorAll('#quizBoard .jcell')[i].click()", idx)
        page.wait_for_selector('#questionModal.active', timeout=10000)
        page.evaluate("() => { const b=[...document.querySelectorAll('#answerSection button, #showAnswerRow button')].find(x=>x.textContent.includes('إظهار')); if(b) b.click(); }")
        page.wait_for_timeout(300)
        return idx

    def click_answer(label):
        page.evaluate("""(label) => {
            const b = [...document.querySelectorAll('#answerSection button')]
                .find(x => x.textContent.includes(label));
            if (b) b.click();
        }""", label)
        page.wait_for_timeout(600)

    # ---------------- T1: correct keeps the turn
    open_first_free()
    t0 = turn(); s0 = scores()
    click_answer('صحيحة')
    page.wait_for_timeout(700)
    t1 = turn(); s1 = scores()
    check('T1 correct KEEPS turn', t0 == t1, 'before=%r after=%r' % (t0, t1))
    check('T1 correct awards points',
          (s1[0] != s0[0]) or (s1[1] != s0[1]),
          'before=%s after=%s' % (s0, s1))

    # ---------------- T2: wrong offers a STEAL to the other team
    open_first_free()
    t2 = turn()
    s2a = scores()
    click_answer('خاطئة')
    page.wait_for_timeout(700)
    t3 = turn()
    steal_open = page.evaluate(
        "() => document.getElementById('questionModal').classList.contains('active')")
    check('T2 wrong PASSES turn (steal offered)', t2 != t3,
          'before=%r after=%r' % (t2, t3))
    check('T2 question stays open for the steal', steal_open, 'open=%s' % steal_open)

    # ---------------- T2b: the stealing team answers correctly -> points + keeps turn
    s2b = scores()
    click_answer('صحيحة')
    page.wait_for_timeout(700)
    t3b = turn()
    s2c = scores()
    check('T2b steal-correct KEEPS turn with the stealing team', t3b == t3,
          'stealing=%r now=%r' % (t3, t3b))
    check('T2b steal-correct awards points',
          (s2c[0] != s2b[0]) or (s2c[1] != s2b[1]),
          'before=%s after=%s' % (s2b, s2c))

    # ---------------- T3: no-answer moves it to the other team
    open_first_free()
    t4 = turn()
    click_answer('لم يجب')
    page.wait_for_timeout(900)
    t5 = turn()
    check('T3 no-answer MOVES to other team', t4 != t5,
          'before=%r after=%r' % (t4, t5))
    modal_open = page.evaluate(
        "() => document.getElementById('questionModal').classList.contains('active')")
    check('T3 question still open after no-answer', modal_open, 'modal=%s' % modal_open)

    # ---------------- T4: second no-answer closes it, offered team keeps the turn
    offered = t5
    click_answer('لم يجب')
    page.wait_for_timeout(900)
    t6 = turn()
    closed = not page.evaluate(
        "() => document.getElementById('questionModal').classList.contains('active')")
    check('T4 second no-answer CLOSES the question', closed, 'closed=%s' % closed)
    check('T4 offered team KEEPS the turn', t6 == offered,
          'offered=%r now=%r' % (offered, t6))

    # ---------------- T5: skip keeps the turn
    open_first_free()
    t7 = turn()
    page.evaluate("() => { const b=[...document.querySelectorAll('#questionModal button')].find(x=>x.textContent.includes('تجاوز')); if(b) b.click(); }")
    page.wait_for_timeout(700)
    t8 = turn()
    check('T5 skip KEEPS turn', t7 == t8, 'before=%r after=%r' % (t7, t8))

    # ---------------- T6: the opened cells are consumed
    # T1 (correct) + T2/T2b (wrong then steal-correct) + T3/T4 (no-answer twice)
    # + T5 (skip) = 4 resolved cells.
    consumed = page.evaluate("""() => {
        const bs = [...document.querySelectorAll('#quizBoard .jcell')];
        return bs.filter(b => b.disabled).length;
    }""")
    check('T6 resolved cells are disabled', consumed >= 4,
          'disabled=%d of %d' % (consumed, n))

    check('no JS page errors', not errors, '; '.join(errors[:3]))

    ctx.close()
    b.close()

passed = sum(1 for _, ok, _ in results if ok)
print()
print('RESULT: %d/%d passed' % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
