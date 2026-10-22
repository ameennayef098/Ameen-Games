#!/usr/bin/env python3
"""«مين في بالي؟» — end-to-end test of the second-player answer path.

Covers exactly what was asked for:
  * the question is NOT answerable from the bank
  * the game offers «اللاعب الثاني يجيب» instead of dead-ending
  * the board hands over to player 2, player 2 answers, control returns to
    player 1 with an exclude hint
  * the question + answer is persisted, so asking it again is answered instantly
"""
import asyncio
import json
import sys
import urllib.request

from playwright.async_api import async_playwright

BASE = 'http://localhost:5555'
ASK = 'هل هو من سكان المريخ؟'      # deliberately outside every character's data


def api(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.load(r)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)

        await page.goto(BASE + '/game/minebali', wait_until='domcontentloaded')
        await page.wait_for_timeout(1500)

        ok = []

        # 1) catalogue picker rendered with classification sections
        groups = await page.locator('#mbCatPick .cp-group').count()
        cards = await page.locator('#mbCatPick .cp-card').count()
        pills = await page.locator('#mbCatPick .cp-group-pill').count()
        ok.append(('picker groups', groups > 0, '%d groups' % groups))
        ok.append(('picker cards', cards > 20, '%d cards' % cards))
        ok.append(('classification pills', pills > 0, '%d pills' % pills))

        # 2) start a match
        await page.click('button:has-text("ابدأ اللعبة")')
        await page.wait_for_timeout(600)
        cells = await page.locator('#selGrid .mb-cell').count()
        ok.append(('character select grid', cells >= 10, '%d cells' % cells))

        for player in (1, 2):
            await page.locator('#selGrid .mb-cell').first.click()
            await page.click('button:has-text("تأكيد الاختيار")')
            await page.wait_for_timeout(300)
            await page.click('button:has-text("إخفاء والمتابعة")')
            await page.wait_for_timeout(400)

        play_visible = await page.locator('#play').is_visible()
        ok.append(('play screen', play_visible, 'visible=%s' % play_visible))

        # 3) an answerable preset still resolves from the bank
        await page.locator('#mbPresets button').first.click()
        await page.wait_for_timeout(800)
        ans = (await page.locator('#mbAnswer').inner_text()).strip()
        ok.append(('bank answer', ans in ('نعم', 'لا'), 'answer=%s' % ans.split('\n')[0]))
        modal_open = await page.locator('.qmodal-overlay').count()
        ok.append(('no modal for a bank answer', modal_open == 0, 'modals=%d' % modal_open))

        # 4) an unanswerable question offers the second player
        await page.fill('#mbQInput', ASK)
        await page.click('button:has-text("إرسال")')
        await page.wait_for_timeout(900)
        offer = await page.locator('.qmodal-overlay button:has-text("اللاعب الثاني يجيب")').count()
        ok.append(('second-player option offered', offer == 1, 'buttons=%d' % offer))

        # 5) hand the device over, reveal the secret to player 2, answer
        await page.click('.qmodal-overlay button:has-text("اللاعب الثاني يجيب")')
        await page.wait_for_timeout(500)
        handover = await page.locator('.mb-handover').is_visible()
        ok.append(('handover screen', handover, 'visible=%s' % handover))
        # player 1's secret must not be visible on the handover screen
        leak = await page.locator('.mb-handover').inner_text()
        secret_name = await page.evaluate("STATE.secrets[0].name")
        ok.append(('secret hidden during handover', secret_name not in leak, ''))

        await page.click('.mb-handover button')
        await page.wait_for_timeout(400)
        reveal = await page.locator('.mb-handover .who').inner_text()
        ok.append(('secret shown to player 2', reveal.strip() == secret_name, reveal.strip()))

        await page.click('.mb-handover button')
        await page.wait_for_timeout(400)
        await page.click('.qmodal-overlay button:has-text("نعم")')
        await page.wait_for_timeout(700)

        # 6) back to player 1 with an exclude hint
        turn = await page.locator('#mbTurn').inner_text()
        ok.append(('turn returned to player 1', 'اللاعب 1' in turn, turn.strip()))
        hint = await page.locator('#mbHint').get_attribute('class') or ''
        ok.append(('exclude hint shown', 'on' in hint, hint))
        ans2 = (await page.locator('#mbAnswer').inner_text()).strip()
        ok.append(('answer displayed', 'نعم' in ans2, ans2.split('\n')[0]))
        src = (await page.locator('#mbLog').inner_text()).strip()
        ok.append(('log marks the source', 'اللاعب الثاني' in src, ''))

        # 7) the Q&A was persisted
        char_id = await page.evaluate("STATE.secrets[1].id")
        saved = api('/api/minebali/qa?q=%s&char_id=%s'
                    % (urllib.parse.quote(ASK), urllib.parse.quote(char_id)))
        ok.append(('saved to the database', saved.get('total', 0) >= 1,
                   'rows=%s' % saved.get('total')))

        # 8) asking it again is answered instantly, with no modal
        await page.fill('#mbQInput', ASK)
        await page.click('button:has-text("إرسال")')
        await page.wait_for_timeout(900)
        modal2 = await page.locator('.qmodal-overlay').count()
        ok.append(('repeat question needs no modal', modal2 == 0, 'modals=%d' % modal2))
        log2 = await page.locator('#mbLog').inner_text()
        ok.append(('repeat marked as saved', 'محفوظ' in log2, ''))

        await browser.close()

        print()
        bad = 0
        for name, passed, detail in ok:
            print('%s  %-38s %s' % ('PASS' if passed else 'FAIL', name, detail))
            if not passed:
                bad += 1
        if errors:
            print('\npage errors:')
            for e in errors[:5]:
                print('  ', e[:200])
            bad += 1
        print('\n%s' % ('ALL PASS' if not bad else '%d FAILURES' % bad))
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
