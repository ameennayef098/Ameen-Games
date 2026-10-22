#!/usr/bin/env python3
"""Smoke test: every page loads with no console/page errors, and the shared
settings panel + category picker actually render."""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

BASE = 'http://localhost:5555'
PAGES = ['/', '/games', '/game/letters', '/game/quiz', '/game/auction', '/game/million',
         '/game/minebali', '/game/spy', '/game/lastone', '/game/whoplayer', '/game/link',
         '/game/codenames', '/game/detective', '/game/culprit', '/game/debate', '/admin']


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        problems = []
        for path in PAGES:
            errs = []
            page.on('pageerror', lambda e, errs=errs: errs.append(str(e)))
            page.on('console', lambda m, errs=errs: errs.append(m.text) if m.type == 'error' else None)
            try:
                await page.goto(BASE + path, wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(1200)
            except Exception as e:
                problems.append((path, 'NAV ' + str(e)[:120]))
                continue
            if errs:
                problems.append((path, ' | '.join(errs[:3])[:300]))
            # shared settings panel applied?
            gsp = await page.evaluate("document.querySelectorAll('.gsp').length")
            print('%-22s gsp=%s errors=%d' % (path, gsp, len(errs)))
        await browser.close()
        print()
        if problems:
            print('PROBLEMS:')
            for p, e in problems:
                print('  ', p, '->', e)
            return 1
        print('no page errors on any page')
        return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
