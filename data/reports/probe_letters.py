from playwright.sync_api import sync_playwright

JS_BOARD = r"""
() => {
  const out = [];
  document.querySelectorAll('svg').forEach(s => out.push('svg id=' + s.id + ' class=' + (s.className.baseVal || '')));
  ['lettersBoard', 'board', 'lettersSvg', 'hexBoard'].forEach(id => {
    const e = document.getElementById(id);
    if (e) out.push('found #' + id + ' tag=' + e.tagName);
  });
  const g = document.querySelectorAll('[data-i]');
  out.push('data-i count=' + g.length);
  if (g[0]) out.push('first=' + g[0].tagName + ' parent=' + g[0].parentNode.tagName + ' pid=' + (g[0].parentNode.id || ''));
  return out.join('\n');
}
"""

JS_BTNS = r"""
() => [...document.querySelectorAll('#letters-setup button')].map(b => b.textContent.trim().slice(0, 24)).join(' | ')
"""

JS_MODAL = r"""
() => {
  const ids = ['questionModal', 'qLetterBadge', 'correctAnswer', 'letters-game', 'letters-setup'];
  return ids.map(id => {
    const e = document.getElementById(id);
    return id + '=' + (e ? (e.tagName + ' display=' + getComputedStyle(e).display) : 'MISSING');
  }).join('\n');
}
"""

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://localhost:5555/game/letters')
    pg.wait_for_selector('#letters-setup', timeout=20000)
    print('--- setup buttons ---')
    print(pg.evaluate(JS_BTNS))
    pg.evaluate("""() => { const b=[...document.querySelectorAll('#letters-setup button')].find(x=>/ابدأ|بدء/.test(x.textContent)); if(b) b.click(); }""")
    pg.wait_for_timeout(2000)
    print('--- board ---')
    print(pg.evaluate(JS_BOARD))
    print('--- ids present ---')
    print(pg.evaluate(JS_MODAL))
    print('--- page errors ---', errs[:3])
    b.close()
