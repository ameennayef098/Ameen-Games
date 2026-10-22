#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the FIRST question shown for each Arabic letter is random, not fixed.

For each of the 25 board letters it:
  1. starts a fresh match (the letters reshuffle on every match)
  2. finds the cell holding that letter
  3. clicks it, records the question text, closes the modal
It repeats this SAMPLES times per letter, so every letter is exercised many
times even though a single match only reveals one letter.

Also asserts the board letter LAYOUT differs between matches.

Usage: python tools/verify_letters_random2.py [--per-letter 4]
"""
import argparse
import os
import socket
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 5599
LETTERS_25 = ['أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ر', 'ز', 'س', 'ش', 'ص',
              'ط', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي']


def wait_port(port, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = socket.socket()
        s.settimeout(1)
        try:
            s.connect(('127.0.0.1', port))
            s.close()
            return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-letter', type=int, default=4)
    a = ap.parse_args()

    env = dict(os.environ, PORT=str(PORT))
    proc = subprocess.Popen([sys.executable, 'server.py'], cwd=BASE, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_port(PORT):
            print('FAIL: server did not come up')
            return 1

        from playwright.sync_api import sync_playwright
        url = 'http://localhost:%d/game/letters' % PORT

        seen = {L: [] for L in LETTERS_25}
        layouts = []
        errors = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url, wait_until='load')
            page.wait_for_selector('#letters-setup')

            for L in LETTERS_25:
                for s in range(a.per_letter):
                    # fresh match each time -> letters reshuffle, used list resets
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
                        print('  !! letter %s not on board' % L)
                        break

                    page.click('#hexBoard .hexg:nth-of-type(%d)' % (idx + 1))
                    page.wait_for_selector('#questionModal.active', timeout=10000)
                    qtext = (page.text_content('#questionText') or '').strip()
                    ans = (page.text_content('#correctAnswer') or '').strip()
                    seen[L].append(qtext + ' => ' + ans)
                    page.evaluate("""() => {
                        const m = document.getElementById('questionModal');
                        if (m) m.classList.remove('active');
                    }""")
                    page.wait_for_timeout(80)

            browser.close()
            if errors:
                print('PAGE ERRORS:', errors[:5])

        print('distinct board layouts: %d' % len({tuple(l) for l in layouts}))
        print()
        all_ok = True
        for L in LETTERS_25:
            qs = seen[L]
            if not qs:
                print('  ?? letter %s : no samples' % L)
                continue
            uniq = len(set(qs))
            ok = uniq > 1
            all_ok = all_ok and ok
            print('  %s letter %-3s : %d distinct / %d samples'
                  % ('OK ' if ok else 'SAME', L, uniq, len(qs)))
            if not ok:
                for q in qs:
                    print('        - %s' % q[:78])
        print()
        if len({tuple(l) for l in layouts}) < 2:
            print('FAIL: board layout never changed')
            return 1
        if not all_ok:
            print('FAIL: at least one letter always produced the same first question')
            return 1
        print('PASS: every letter draws a different first question across matches')
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == '__main__':
    sys.exit(main())
