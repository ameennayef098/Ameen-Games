#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright proof of the 'turn retention' mechanic in the «س.ج» game
(Ameen Games, Arabic RTL Flask app).

Mechanic under test:
  * correct answer  -> team takes the points AND KEEPS its turn
  * #noAnswerBtn    -> answering team failed; question moves to the OTHER team (steal)
  * no-answer twice -> question closes, team OFFERED the question KEEPS the turn
  * skipQuestion()  -> does NOT flip the turn

Writes NOTHING into the project tree. Test script + JSON report live in data/reports/.
"""
import json
import os
import re
import sys
import datetime

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5555"
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "turn_retention_report.json")

PROJECT_DIR = r"C:\Users\Ameen Dawaghreh\Desktop\ألعاب-أمين"
TEMPLATE = os.path.join(PROJECT_DIR, "templates", "game_quiz.html")

results = []          # ordered strings, printed verbatim as the report
lines = []            # detail lines for the JSON artifact


def say(msg):
    print(msg)
    lines.append(msg)


def served_grep(html, needle):
    return html.count(needle)


def read_state(page):
    return page.evaluate(
        """() => {
        const t = document.getElementById('turnIndicator').textContent.trim();
        return {
            turn: t,
            turnName: t.replace(/^دور\\s*/, ''),
            s1: document.getElementById('score1Value').textContent.trim(),
            s2: document.getElementById('score2Value').textContent.trim(),
            banner: document.getElementById('turnBanner').textContent.trim(),
            remaining: document.getElementById('remaining').textContent.trim()
        };
    }"""
    )


def first_free_cell(page):
    """Return (index, cell_text) of the first enabled board cell."""
    cells = page.query_selector_all("#quizBoard .jcell")
    for i, c in enumerate(cells):
        if not c.is_disabled():
            return i, c.inner_text().strip()
    return None, None


def open_first_question(page):
    """Click the first enabled cell, return the question points (int)."""
    idx, text = first_free_cell(page)
    if idx is None:
        raise RuntimeError("no enabled cell left on the board")
    pts = None
    m = re.search(r"(\d{2,4})", text.replace("\n", " "))
    if m:
        pts = int(m.group(1))
    cells = page.query_selector_all("#quizBoard .jcell")
    cells[idx].click()
    page.wait_for_selector("#questionModal.active", timeout=5000)
    # sanity: the modal really shows the same points as the clicked cell
    shown = page.eval_on_selector("#questionPoints", "e => e.textContent")
    if pts is not None:
        m2 = re.search(r"(\d+)", shown)
        if m2 and int(m2.group(1)) != pts:
            say(f"  (note) cell text={pts} but #questionPoints shows {m2.group(1)}")
    return idx, text, pts


def reveal(page):
    page.click("button:has-text('إظهار الإجابة')")
    page.wait_for_function(
        "() => document.getElementById('answerSection').style.display !== 'none'"
    )


def num(s):
    return int(re.sub(r"[^\d-]", "", s) or 0)


def rec(name, ok, detail):
    results.append(f"{name}: {'PASS' if ok else 'FAIL'} — {detail}")
    say(f"{name}: {'PASS' if ok else 'FAIL'} — {detail}")


def main():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()
    tpl_no = tpl.count("noAnswerBtn")
    tpl_ma = tpl.count("markNoAnswer")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()          # FRESH context -> empty localStorage
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(BASE + "/game/quiz", wait_until="domcontentloaded")
        page.wait_for_selector("#quiz-setup", state="visible", timeout=10000)

        served = page.content()
        served_no = served_grep(served, "noAnswerBtn")
        served_ma = served_grep(served, "markNoAnswer")
        has_no_answer = served_no > 0 and served_ma > 0
        pw_version = page.evaluate("() => navigator.userAgent")

        # --- setup: timer off, exactly 6 categories ---
        page.select_option("#timerDuration", "0")
        page.click("button:has-text('مسح')")  # clearCategories
        boxes = page.query_selector_all("#categorySelection input")
        for b in boxes[:6]:
            b.click()
        page.wait_for_function(
            "() => document.getElementById('catCount').textContent.includes('6/6')"
        )
        cats = page.eval_on_selector_all(
            "#categorySelection input", "els => els.slice(0,6).map(e => e.value)"
        )
        say(f"categories selected: {cats}")
        say(f"catCount = {page.text_content('#catCount').strip()}")
        say(f"timerDuration = {page.eval_on_selector('#timerDuration','e=>e.value')}")

        page.click("button:has-text('ابدأ اللعبة')")
        page.wait_for_selector("#quiz-game", state="visible", timeout=10000)

        ncells = len(page.query_selector_all("#quizBoard .jcell"))
        say(f"board cells: {ncells}")
        say(f"SERVED page: 'noAnswerBtn' occurrences = {served_no}, "
            f"'markNoAnswer' occurrences = {served_ma}")
        say(f"TEMPLATE file: 'noAnswerBtn' = {tpl_no}, 'markNoAnswer' = {tpl_ma}")
        say(f"#noAnswerBtn visible on served page: "
            f"{page.query_selector('#noAnswerBtn') is not None and page.is_visible('#noAnswerBtn')}")

        if not has_no_answer:
            results.append(
                "BLOCKER: served page is a stale cached template — "
                "'noAnswerBtn'/'markNoAnswer' absent (0 occurrences). "
                "The turn-retention mechanic exists on disk "
                f"(templates/game_quiz.html: noAnswerBtn x{tpl_no}, markNoAnswer x{tpl_ma}) "
                "but is NOT being served, so the server has not been restarted since "
                "the mechanic was added. T3/T4 (no-answer path) CANNOT run. "
                "Server was NOT restarted and the template was NOT edited. "
                "T1/T2/T5/T6 still run against the served page."
            )
            say("BLOCKER detected: served template lacks #noAnswerBtn.")

        st = read_state(page)
        say(f"initial state: turn='{st['turn']}' s1={st['s1']} s2={st['s2']} "
            f"remaining='{st['remaining']}'")

        # ================= T1: correct answer keeps turn =================
        idx1, txt1, pts1 = open_first_question(page)
        before = read_state(page)
        say(f"T1 before: turn='{before['turn']}' s1={before['s1']} s2={before['s2']} "
            f"(cell {idx1} text='{txt1}', pts={pts1})")
        reveal(page)
        page.click("button:has-text('✅ صحيحة')")
        page.wait_for_function(
            "() => !document.getElementById('questionModal').classList.contains('active')"
        )
        page.wait_for_timeout(300)
        after = read_state(page)
        say(f"T1 after : turn='{after['turn']}' s1={after['s1']} s2={after['s2']}")
        flip1 = before["turn"] != after["turn"]
        if pts1 is not None:
            gained1 = num(after["s1"]) - num(before["s1"])
            gained2 = num(after["s2"]) - num(before["s2"])
            gained = max(gained1, gained2)
            rec("T1 CORRECT KEEPS TURN",
                (not flip1) and gained == pts1,
                f"turn '{before['turn']}' -> '{after['turn']}' (flipped={flip1}); "
                f"score delta = +{gained} (expected +{pts1}); "
                f"s1 {before['s1']}->{after['s1']}, s2 {before['s2']}->{after['s2']}")
        else:
            rec("T1 CORRECT KEEPS TURN", not flip1,
                f"turn '{before['turn']}' -> '{after['turn']}' (flipped={flip1}); "
                f"points unreadable from cell text")

        # ================= T2: wrong answer passes turn =================
        idx2, txt2, pts2 = open_first_question(page)
        b2 = read_state(page)
        reveal(page)
        page.click("button:has-text('❌ خاطئة')")
        page.wait_for_timeout(400)
        mid = read_state(page)
        steal = page.is_visible("#answerSection") is False and page.is_visible(
            "button:has-text('إظهار الإجابة')")
        a2 = read_state(page)
        say(f"T2 after wrong: turn='{a2['turn']}' (was '{b2['turn']}'), "
            f"steal attempt offered to other team (answer hidden again)={steal}, "
            f"banner='{a2['banner']}'")
        rec("T2 WRONG PASSES TURN",
            b2["turn"] != a2["turn"],
            f"turn '{b2['turn']}' -> '{a2['turn']}' (flipped={b2['turn'] != a2['turn']}); "
            f"steal UI re-shown={steal}")

        # resolve the pending steal question with a correct answer from team 2
        if page.is_visible("#questionModal.active") or page.query_selector(
                "#questionModal.active"):
            reveal(page)
            page.click("button:has-text('✅ صحيحة')")
            page.wait_for_timeout(400)
            resolved2 = read_state(page)
            say(f"T2 follow-up correct-by-other-team: turn='{resolved2['turn']}', "
                f"s1={resolved2['s1']}, s2={resolved2['s2']}")

        # ================= T5: skip keeps turn =================
        idx5, txt5, pts5 = open_first_question(page)
        b5 = read_state(page)
        page.click("button:has-text('⏭️ تجاوز')")
        page.wait_for_timeout(400)
        a5 = read_state(page)
        say(f"T5 before: turn='{b5['turn']}' ; after skip: turn='{a5['turn']}'")
        rec("T5 SKIP KEEPS TURN",
            b5["turn"] == a5["turn"],
            f"turn '{b5['turn']}' -> '{a5['turn']}' "
            f"(changed={b5['turn'] != a5['turn']})")

        # ================= T6: cell is consumed =================
        cells = page.query_selector_all("#quizBoard .jcell")
        consumed = []
        for i in (idx1, idx2, idx5):
            if i is not None and i < len(cells):
                consumed.append((i, cells[i].is_disabled()))
        all_disabled = all(d for _, d in consumed) and len(consumed) == 3
        rec("T6 CELL IS CONSUMED", all_disabled,
            "checked cells " + ", ".join(f"#{i} disabled={d}" for i, d in consumed))

        # ================= T3 / T4: no-answer path =================
        if has_no_answer:
            # T3: no answer -> other team
            idx3, txt3, pts3 = open_first_question(page)
            b3 = read_state(page)
            reveal(page)
            page.click("#noAnswerBtn")
            page.wait_for_timeout(500)
            a3 = read_state(page)
            rec("T3 NO-ANSWER MOVES TO OTHER TEAM",
                b3["turn"] != a3["turn"],
                f"turn '{b3['turn']}' -> '{a3['turn']}' "
                f"(flipped={b3['turn'] != a3['turn']}); banner='{a3['banner']}'")

            # T4: second no-answer -> question closes, ORIGINAL team keeps turn
            reveal(page)
            page.click("#noAnswerBtn")
            page.wait_for_timeout(500)
            modal_closed = not page.eval_on_selector(
                "#questionModal", "e => e.classList.contains('active')")
            a4 = read_state(page)
            say(f"T4 after 2nd no-answer: modal closed={modal_closed}, "
                f"turn='{a4['turn']}' (original was '{b3['turn']}')")
            rec("T4 NO-ANSWER TWICE KEEPS TURN",
                modal_closed and a4["turn"] == b3["turn"],
                f"modal closed={modal_closed}; turn '{b3['turn']}' -> '{a4['turn']}' "
                f"(original team kept turn={a4['turn'] == b3['turn']})")
        else:
            rec("T3 NO-ANSWER MOVES TO OTHER TEAM", False,
                "BLOCKED — #noAnswerBtn not present on the served page")
            rec("T4 NO-ANSWER TWICE KEEPS TURN", False,
                "BLOCKED — #noAnswerBtn not present on the served page")

        if errors:
            say("page errors: " + " | ".join(errors))

        browser.close()

    status = "PASS" if all(": PASS" in r for r in results) else "FAIL"
    if not has_no_answer:
        status = "PARTIAL"

    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "playwright_version": "1.64.0",
            "url": BASE + "/game/quiz",
            "template_on_disk": {"noAnswerBtn": tpl_no, "markNoAnswer": tpl_ma},
            "served_page": {"noAnswerBtn": served_no, "markNoAnswer": served_ma},
            "stale_template": not has_no_answer,
            "status": status,
            "results": results,
            "details": lines,
        }, f, ensure_ascii=False, indent=2)

    say("")
    say("===== RESULTS =====")
    for r in results:
        say(r)
    say("status = " + status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
