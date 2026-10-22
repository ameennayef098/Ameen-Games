import asyncio
from playwright.async_api import async_playwright

BASE = 'http://localhost:5555'
ASK = 'هل هو من سكان المريخ؟'


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        p = await b.new_page()
        p.on('console', lambda m: print('CONSOLE[%s] %s' % (m.type, m.text[:200])))
        p.on('pageerror', lambda e: print('PAGEERROR', str(e)[:300]))
        await p.goto(BASE + '/game/minebali', wait_until='domcontentloaded')
        await p.wait_for_timeout(1500)
        await p.click('button:has-text("ابدأ اللعبة")')
        await p.wait_for_timeout(500)
        for _ in range(2):
            await p.locator('#selGrid .mb-cell').first.click()
            await p.click('button:has-text("تأكيد الاختيار")')
            await p.wait_for_timeout(300)
            await p.click('button:has-text("إخفاء والمتابعة")')
            await p.wait_for_timeout(400)
        print('play visible:', await p.locator('#play').is_visible())
        print('fallback value:', await p.evaluate("document.getElementById('mbFallback') && document.getElementById('mbFallback').value"))
        await p.fill('#mbQInput', ASK)
        await p.click('button:has-text("إرسال")')
        await p.wait_for_timeout(1500)
        print('overlays:', await p.locator('.qmodal-overlay').count())
        print('handover:', await p.locator('.mb-handover').count())
        html = await p.evaluate("document.body.innerHTML.length")
        print('body len', html)
        txt = await p.evaluate("(() => { var o=document.querySelector('.qmodal-overlay'); return o? o.innerText : 'NO OVERLAY'; })()")
        print('overlay text:', txt[:400])
        print('mbAnswer:', (await p.locator('#mbAnswer').inner_text())[:200])
        await b.close()


asyncio.run(main())
