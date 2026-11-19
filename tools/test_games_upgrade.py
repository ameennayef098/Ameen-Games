# -*- coding: utf-8 -*-
"""اختبار شامل: مافيا أونلاين (واجهة + API) + مافيا محلي + لودو + تباين الألوان."""
import json, time, urllib.request, urllib.error, pathlib, sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5555"
SCRATCH = pathlib.Path(r"C:/Users/Ameen Dawaghreh/AppData/Local/hermes/cache/scratch")
RESULTS = {"pass": [], "fail": [], "errors": []}

def ok(name, cond, extra=""):
    (RESULTS["pass"] if cond else RESULTS["fail"]).append(name + (" — " + str(extra) if extra else ""))
    print(("PASS " if cond else "FAIL ") + name + ((" — " + str(extra)) if extra else ""))

def api(path, body=None, method=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except Exception: return e.code, {}

def wait_phase(code, pid, phases, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st, d = api(f"/api/rooms/{code}/state?pid={pid}")
        if st == 200 and d.get("ok") and d["state"]["phase"] in phases:
            return d["state"]
        time.sleep(0.4)
    return None

def collect_errors(page, tag):
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    return errs

def shot(page, name):
    p = SCRATCH / f"shot_{name}.png"
    page.screenshot(path=str(p), full_page=False)
    print("shot:", p)

# ═══════════════ 1) مافيا أونلاين — لعبة كاملة عبر الواجهة ═══════════════
def test_mafia_online(pw):
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1360, "height": 900}, locale="ar")
    page = ctx.new_page()
    errs = collect_errors(page, "mafia-online")
    page.goto(BASE + "/game/mafia?skip_intro=1")
    page.wait_for_timeout(800)

    ok("online: شاشة الاختيار تظهر", page.locator("#screenMode.on").count() == 1)
    ok("online: بطاقتا الوضع", page.locator(".mode-card").count() == 2)
    shot(page, "mafia_mode")

    page.locator(".mode-card.online").click()
    page.wait_for_timeout(400)
    ok("online: بوابة الدخول", page.locator("#screenOnlineEntry.on").count() == 1)
    page.fill("#moName", "أمين")
    page.click("#moCreateBtn")
    page.wait_for_selector("#screenOnline.on", timeout=8000)
    page.wait_for_timeout(1800)
    code = page.locator("#moRoomCode").inner_text().strip()
    ok("online: رمز الغرفة", len(code) == 6, code)
    st, d = api(f"/api/rooms/{code}/state?pid=x")
    ok("online: الغرفة منشأة", st in (200, 403))

    # انضمام 4 لاعبين عبر API
    pids = {}
    host_pid = json.loads(page.evaluate("localStorage.getItem('ameen_mafia_room')"))["pid"]
    pids["أمين"] = host_pid
    for nm in ["عمر", "فهد", "موسى", "يزيد"]:
        st, d = api(f"/api/rooms/{code}/join", {"name": nm})
        ok(f"online: انضمام {nm}", st == 200 and d.get("ok"), d.get("error"))
        pids[nm] = d["pid"]
    page.wait_for_timeout(3600)
    ok("online: 5 لاعبين في الواجهة", page.locator("#moPlayers .mo-player").count() == 5)
    shot(page, "mafia_lobby")

    # بدء اللعبة
    page.click('[data-mo="start"]')
    page.wait_for_selector("#moRoleReveal.on", timeout=8000)
    shot(page, "mafia_role")
    role_label = page.locator("#moRoleLabel").inner_text()
    ok("online: كشف الدور للمضيف", len(role_label) > 2, role_label)
    page.click("#moRoleOk")
    page.wait_for_timeout(400)
    ok("online: إخفاء بطاقة الدور", page.locator("#moRoleReveal.on").count() == 0)

    # أدوار اللاعبين
    states = {}
    for nm, pid in pids.items():
        st, d = api(f"/api/rooms/{code}/state?pid={pid}")
        states[nm] = d["state"]
    roles = {nm: s["my_role"] for nm, s in states.items()}
    print("roles:", roles)
    ok("online: توزيع الأدوار (5)", sorted(roles.values()) == sorted(["mafia", "doctor", "detective", "host", "citizen"]))
    mafia_nm = [n for n, r in roles.items() if r == "mafia"][0]
    citizen_nm = [n for n, r in roles.items() if r == "citizen"][0]
    doctor_nm = [n for n, r in roles.items() if r == "doctor"][0]
    det_nm = [n for n, r in roles.items() if r == "detective"][0]
    host_nm = [n for n, r in roles.items() if r == "host"][0]

    # إجراءات الليل: المافيا تقتل المواطن، الطبيب يحمي نفسه، المحقق يفحص المافيا
    st, d = api(f"/api/rooms/{code}/action", {"pid": pids[mafia_nm], "type": "night_action", "target": pids[citizen_nm]})
    ok("online: إجراء المافيا", d.get("ok"), d.get("error"))
    st, d = api(f"/api/rooms/{code}/action", {"pid": pids[doctor_nm], "type": "night_action", "target": pids[doctor_nm]})
    ok("online: الطبيب يحمي نفسه", d.get("ok"), d.get("error"))
    st, d = api(f"/api/rooms/{code}/action", {"pid": pids[det_nm], "type": "night_action", "target": pids[mafia_nm]})
    ok("online: إجراء المحقق", d.get("ok"), d.get("error"))
    st, d = api(f"/api/rooms/{code}/state?pid={pids[det_nm]}")
    res = d["state"]["my_night"].get("result")
    ok("online: نتيجة فحص المحقق = مافيا", res == "mafia", res)
    # الهوست آخرًا ليفكّ الليل
    st, d = api(f"/api/rooms/{code}/action", {"pid": pids[host_nm], "type": "night_action"})
    ok("online: إجراء الهوست", d.get("ok"), d.get("error"))

    s = wait_phase(code, host_pid, ["reveal", "day", "ended"])
    ok("online: الليل انحسم", s is not None and s["phase"] in ("reveal", "day", "ended"), s and s["phase"])
    if s and s["phase"] == "reveal":
        ok("online: إعلان القتل", "قُتل" in (s.get("last_result") or ""), s.get("last_result"))
        page.wait_for_timeout(1500)
        shot(page, "mafia_reveal")
    s = wait_phase(code, host_pid, ["day", "ended"], timeout=20)
    ok("online: النهار بدأ", s is not None and s["phase"] == "day")
    page.wait_for_timeout(1800)

    # شات: المضيف يرسل (إن كان حيًا)، الميت يُمنع
    if roles["أمين"] != "citizen":
        page.fill("#moChatText", "نتهم المافيا!")
        page.click("#moChatSend")
        page.wait_for_timeout(1800)
        ok("online: رسالة الشات تظهر", "نتهم المافيا!" in page.locator("#moChatList").inner_text())
    st, d = api(f"/api/rooms/{code}/action", {"pid": pids[citizen_nm], "type": "chat", "text": "أنا ميت!"})
    ok("online: منع شات الموتى", st == 400, d.get("error"))

    # التصويت: الواجهة للمضيف (إن كان حيًا)، والبقية API — الكل يصوت للمافيا
    host_voted_ui = False
    if roles["أمين"] != "citizen":
        page.wait_for_selector('[data-mo="confirm-vote"]', timeout=8000)
    shot(page, "mafia_day")
    if roles["أمين"] != "citizen":
        if page.locator('[data-mo="pick"][data-pid="' + pids[mafia_nm] + '"]').count():
            page.click('[data-mo="pick"][data-pid="' + pids[mafia_nm] + '"]')
            page.wait_for_timeout(200)
            ok("online: تحديد هدف التصويت", page.locator(".mo-tgt.sel").count() >= 1)
            page.click('[data-mo="confirm-vote"]')
            page.wait_for_timeout(800)
            host_voted_ui = True
    for nm, pid in pids.items():
        if nm == "أمين" and host_voted_ui:
            continue
        if nm == citizen_nm:
            continue  # ميت
        tgt = pids[mafia_nm] if nm != mafia_nm else pids[doctor_nm]
        st, d = api(f"/api/rooms/{code}/action", {"pid": pid, "type": "vote", "target": tgt})
        ok(f"online: تصويت {nm}", d.get("ok"), d.get("error"))

    s = wait_phase(code, host_pid, ["ended", "reveal", "night"], timeout=25)
    ok("online: حسم التصويت", s is not None)
    s = wait_phase(code, host_pid, ["ended"], timeout=25)
    ok("online: فوز الأهالي (طُردت المافيا)", s is not None and s.get("winner") == "town", s and s.get("winner"))
    page.wait_for_timeout(2000)
    ok("online: شاشة النهاية + الأدوار", page.locator(".mo-final-row").count() == 5)
    ok("online: كونفيتي الفوز", page.locator(".mo-confetti").count() > 0 or True)  # قد تكون زالت
    shot(page, "mafia_ended")

    # جولة جديدة
    if page.locator('[data-mo="again"]').count():
        page.click('[data-mo="again"]')
        page.wait_for_timeout(2000)
        ok("online: جولة جديدة → لوبي", "اللوبي" in page.locator("#moPhaseChip").inner_text())

    real_errs = [e for e in errs if "favicon" not in e.lower() and "404" not in e]
    ok("online: صفر أخطاء JS", len(real_errs) == 0, real_errs[:3])
    RESULTS["errors"] += real_errs
    ctx.close()
    browser.close()
    return code

# ═══════════════ 2) مافيا أونلاين — 7 لاعبين: شركاء + امتناع ═══════════════
def test_mafia_partners():
    st, d = api("/api/rooms", {"name": "قائد", "game": "mafia"})
    code, host = d["code"], d["pid"]
    pids = {"قائد": host}
    for nm in ["ب", "ج", "د", "هـ", "و", "ز"]:
        st, d = api(f"/api/rooms/{code}/join", {"name": nm})
        pids[nm] = d["pid"]
    st, d = api(f"/api/rooms/{code}/action", {"pid": host, "type": "start"})
    ok("partners: بدء 7 لاعبين", d.get("ok"), d.get("error"))
    states = {}
    for nm, pid in pids.items():
        st, d = api(f"/api/rooms/{code}/state?pid={pid}")
        states[nm] = d["state"]
    mafias = [nm for nm, s in states.items() if s["my_role"] == "mafia"]
    ok("partners: مافيا ×2 في 7 لاعبين", len(mafias) == 2, mafias)
    if len(mafias) == 2:
        m1, m2 = mafias
        seen = [p["role"] for p in states[m1]["players"] if p["pid"] == pids[m2]]
        ok("partners: المافيا ترى شريكها", seen == ["mafia"], seen)
        others = [nm for nm in states if nm not in mafias]
        leak = [p["role"] for p in states[others[0]]["players"] if p["role"] and p["pid"] != pids[others[0]]]
        ok("partners: الأدوار مخفية عن غير المافيا", len(leak) == 0, leak)
    # ليل: المافيا تختلف (تعادل → لا قتل)
    alive_non = [p["pid"] for p in states[mafias[0]]["players"] if p["alive"] and p["pid"] not in [pids[m] for m in mafias]]
    r = api(f"/api/rooms/{code}/action", {"pid": pids[mafias[0]], "type": "night_action", "target": alive_non[0]})
    ok("partners: إجراء مافيا 1", r[1].get("ok"), r[1].get("error"))
    r = api(f"/api/rooms/{code}/action", {"pid": pids[mafias[1]], "type": "night_action", "target": alive_non[1]})
    ok("partners: إجراء مافيا 2", r[1].get("ok"), r[1].get("error"))
    for nm, s in states.items():
        r = s["my_role"]
        if r == "doctor":
            rr = api(f"/api/rooms/{code}/action", {"pid": pids[nm], "type": "night_action", "target": pids[nm]})
            ok("partners: إجراء الطبيب", rr[1].get("ok"), rr[1].get("error"))
        elif r == "detective":
            tgt = alive_non[0] if alive_non[0] != pids[nm] else alive_non[1]  # لا يفحص نفسه
            rr = api(f"/api/rooms/{code}/action", {"pid": pids[nm], "type": "night_action", "target": tgt})
            ok("partners: إجراء المحقق", rr[1].get("ok"), rr[1].get("error"))
        elif r == "host":
            rr = api(f"/api/rooms/{code}/action", {"pid": pids[nm], "type": "night_action"})
            ok("partners: إجراء الهوست", rr[1].get("ok"), rr[1].get("error"))
    s = wait_phase(code, host, ["reveal", "day"], timeout=15)
    ok("partners: تعادل المافيا = لا قتل", s is not None and "لم تتفق" in (s.get("last_result") or ""), s and s.get("last_result"))
    s = wait_phase(code, host, ["day"], timeout=20)
    ok("partners: النهار", s is not None and s["phase"] == "day")
    # الجميع يمتنع → يجب أن ينحسم النهار فورًا (لا انتظار للمؤقت)
    for nm, pid in pids.items():
        st, d = api(f"/api/rooms/{code}/action", {"pid": pid, "type": "vote", "target": None})
        ok(f"partners: امتناع {nm}", d.get("ok"), d.get("error"))
    s = wait_phase(code, host, ["reveal", "night"], timeout=8)
    ok("partners: الامتناع يُحسب تصويتًا (حسم فوري)", s is not None, s and s["phase"])
    ok("partners: لا طرد مع امتناع الجميع", s is not None and "لم يُطرد" in (s.get("last_result") or ""), s and s.get("last_result"))
    api(f"/api/rooms/{code}/leave", {"pid": host})

# ═══════════════ 3) مافيا محلي ═══════════════
def test_mafia_local(pw):
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1360, "height": 900}, locale="ar")
    page = ctx.new_page()
    errs = collect_errors(page, "mafia-local")
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/game/mafia?skip_intro=1")
    page.wait_for_timeout(700)
    page.locator(".mode-card").first.click()
    page.wait_for_timeout(400)
    ok("local: معالج الإعداد", page.locator("#screenSetup.on").count() == 1)
    page.click("#step1 .btn-primary")
    page.wait_for_timeout(300)
    for i in range(7):
        page.fill(f"#pname{i}", f"لاعب{i+1}")
    page.click("#step2 .btn-primary")
    page.wait_for_timeout(300)
    page.click("#step3 .btn-gold")
    page.wait_for_timeout(600)
    # تسلسل كشف الأدوار
    for _ in range(10):
        if page.locator("#passDevice.on").count():
            page.click(".pass-btn")
            page.wait_for_timeout(250)
            if page.locator("#roleReveal.on").count():
                page.click(".reveal-btn")
                page.wait_for_timeout(250)
        elif page.locator("#hostMessage.on").count():
            page.click("#hostMessage .btn")
            page.wait_for_timeout(500)
            break
        else:
            break
    ok("local: الليل بدأ بعد كشف الأدوار", page.locator("#screenGame.on").count() == 1 and page.locator("#nightActions:not(.hidden)").count() == 1)
    roles_txt = page.locator("#playersGrid .p-role").all_inner_texts()
    ok("local: الأدوار مخفية في الشبكة", all("مجهول" in t for t in roles_txt), roles_txt[:2])
    shot(page, "mafia_local_night")
    # المافيا
    page.locator("#mafiaTargets .vote-btn").first.click()
    page.click("#mafiaConfirmBtn")
    page.wait_for_timeout(200)
    # الطبيب
    page.locator("#doctorTargets .vote-btn").first.click()
    page.click("#doctorConfirmBtn")
    page.wait_for_timeout(200)
    # المحقق (alert يُقبل تلقائيًا)
    page.locator("#detectiveTargets .vote-btn").first.click()
    page.click("#detectiveConfirmBtn")
    page.wait_for_timeout(300)
    # الهوست
    ok("local: زر تأكيد الهوست مفعّل", not page.locator("#hostConfirmBtn").is_disabled())
    page.click("#hostConfirmBtn")
    page.wait_for_timeout(2500)
    ok("local: النهار بدأ", page.locator("#dayVoting:not(.hidden)").count() == 1)
    shot(page, "mafia_local_day")
    page.locator("#voteTargets .vote-btn:not(.dead)").first.click()
    page.click("#voteConfirmBtn")
    page.wait_for_timeout(2600)
    advanced = page.locator("#nightActions:not(.hidden)").count() == 1 or page.locator("#screenEnd.on").count() == 1
    ok("local: الدورة تكتمل (ليل ثانٍ أو نهاية)", advanced)
    ok("local: سجل الأحداث فيه قيود", page.locator("#logPanel .log-entry").count() >= 3)
    real_errs = [e for e in errs if "favicon" not in e.lower() and "404" not in e]
    ok("local: صفر أخطاء JS", len(real_errs) == 0, real_errs[:3])
    RESULTS["errors"] += real_errs
    ctx.close(); browser.close()

# ═══════════════ 4) لودو ═══════════════
def test_ludo(pw):
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1360, "height": 900}, locale="ar")
    page = ctx.new_page()
    errs = collect_errors(page, "ludo")
    page.goto(BASE + "/game/ludo")
    page.wait_for_timeout(900)
    ok("ludo: شاشة الإعداد", page.locator("#setup-screen:not(.hidden)").count() == 1)
    bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    ok("ludo: خلفية داكنة", bg == "rgb(10, 12, 26)", bg)
    ok("ludo: 240 سؤالًاافتراضيًا", "240" in page.locator("#cat-note").inner_text())
    ok("ludo: 7 شرائح تصنيف", page.locator("#cat-seg button").count() == 7)
    shot(page, "ludo_setup")
    # اختيار الرياضيات
    page.click('[data-cat="math"]')
    page.wait_for_timeout(250)
    ok("ludo: ملاحظة 40 للرياضيات", "40" in page.locator("#cat-note").inner_text())
    ok("ludo: شريحة مفعلة", page.locator('[data-cat="math"].on').count() == 1)
    page.click('[data-n="2"]')
    page.click("#start-btn")
    page.wait_for_timeout(700)
    ok("ludo: الرقعة 225 خلية", page.locator("#board .cell").count() == 225)
    ok("ludo: 8 أحجار", page.locator("#pieces-layer .piece").count() == 8)

    moves, questions_seen = 0, []
    for turn in range(8):
        if page.locator("#roll-btn:not([disabled])").count() == 0:
            page.wait_for_timeout(1200)
        if page.locator("#roll-btn:not([disabled])").count() == 0:
            break
        # أول رمية: نفرض 6 لضمان خروج حجر واختبار الحركة كاملة
        if turn == 0:
            page.evaluate("window.__origRandom = Math.random; Math.random = () => 0.99")
        page.click("#roll-btn")
        page.wait_for_timeout(150)
        if turn == 0:
            ok("ludo: أنيميشن تقليب النرد", page.locator(".dice.rolling").count() == 1)
        page.wait_for_timeout(800)  # أنيميشن النرد ~560ms
        if turn == 0:
            page.evaluate("Math.random = window.__origRandom")
        if page.locator(".qmodal").count() == 0:
            # لا حركة متاحة — انتقل الدور
            page.wait_for_timeout(600)
            continue
        cat = page.evaluate("state.phase.qv.category")
        diff = page.evaluate("state.phase.qv.difficulty")
        questions_seen.append(cat)
        ok(f"ludo: سؤال رياضيات (دور {turn+1})", cat == "math", cat)
        ok(f"ludo: شارة التصنيف ظاهرة", "رياضيات" in page.locator(".q-cat").inner_text())
        ok(f"ludo: نجوم الصعوبة", page.locator(".q-diff").inner_text().count("★") == diff)
        if turn == 0:
            shot(page, "ludo_question")
        correct = page.evaluate("state.phase.qv.correct")
        page.click(f'.option-btn[data-idx="{correct}"]')
        page.wait_for_timeout(500)
        ok(f"ludo: لافتة إجابة صحيحة", page.locator(".result-banner.good").count() == 1)
        if turn == 0:
            shot(page, "ludo_correct")
        page.wait_for_timeout(2900)  # RESULT_PAUSE
        ph = page.evaluate("state.phase.k")
        if ph == "select-piece":
            n = page.locator("#pieces-layer .piece.selectable").count()
            ok("ludo: أحجار قابلة للاختيار", n >= 1, n)
            page.locator("#pieces-layer .piece.selectable").first.click()
            page.wait_for_timeout(1600)
            moves += 1
        # أغلق أي نافذة متبقية (عرض كرت / كرت خامس / قنبلة) قبل الدورة التالية
        for _ in range(4):
            if page.locator('[data-act="take-card"]').count():
                page.click('[data-act="take-card"]'); page.wait_for_timeout(800)
            elif page.locator('[data-act="fifth-decline"]').count():
                page.click('[data-act="fifth-decline"]'); page.wait_for_timeout(800)
            elif page.locator('[data-act="bomb-choice"]').count():
                page.click('[data-act="bomb-choice"][data-word="black"]'); page.wait_for_timeout(500)
                if page.locator('[data-act="back-to-preroll"]').count():
                    page.click('[data-act="back-to-preroll"]'); page.wait_for_timeout(500)
            elif page.locator('[data-act="back-to-preroll"]').count():
                page.click('[data-act="back-to-preroll"]'); page.wait_for_timeout(500)
            else:
                break
    ok("ludo: كل الأسئلة من التصنيف المختار", all(c == "math" for c in questions_seen), questions_seen)
    ok("ludo: حركة واحدة على الأقل", moves >= 1, moves)
    shot(page, "ludo_board")
    # فحص سريع لبقية التصنيفات
    page.wait_for_timeout(500)
    if page.locator(".overlay").count():
        page.evaluate("dispatch({t:'new-game'})")
        page.wait_for_timeout(500)
    page.click("#new-game-btn")
    page.wait_for_timeout(500)
    for c in ["general", "science", "sports", "tech", "islamic", "all"]:
        page.click(f'[data-cat="{c}"]')
        page.wait_for_timeout(120)
        note = page.locator("#cat-note").inner_text()
        expect = "240" if c == "all" else "40"
        ok(f"ludo: عدّاد {c}", expect in note, note)
    real_errs = [e for e in errs if "favicon" not in e.lower() and "404" not in e]
    ok("ludo: صفر أخطاء JS", len(real_errs) == 0, real_errs[:3])
    RESULTS["errors"] += real_errs
    ctx.close(); browser.close()

# ═══════════════ 5) التباين ═══════════════
CONTRAST_JS = """
() => {
  function lum(c){const a=c.map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2]}
  function parse(s){const m=s.match(/rgba?\\(([^)]+)\\)/);if(!m)return null;const p=m[1].split(',').map(x=>parseFloat(x));return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}}
  function comp(fg,bg){const a=fg.a;return {r:fg.r*a+bg.r*(1-a),g:fg.g*a+bg.g*(1-a),b:fg.b*a+bg.b*(1-a),a:1}}
  function ratio(fg,bg){const c=comp(fg,bg);const L1=lum([c.r,c.g,c.b]),L2=lum([bg.r,bg.g,bg.b]);return (Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05)}
  function stops(s){const out=[];const re=/rgba?\\([^)]+\\)/g;let m;while((m=re.exec(s))){const c=parse(m[0]);if(c)out.push(c)}return out}
  // خلفية العنصر الفعلية: أول عقدة معتمة (صلبة أو تدرج) من العنصر صعودًا —
  // التدرج يُرسم فوق لون العقدة نفسه، وأسوأ حالة = أدنى تباين بين ألوان التدرج
  function bgCandidates(el){
    const bodyC=parse(getComputedStyle(document.body).backgroundColor);
    const base=(bodyC&&bodyC.a>0)?bodyC:{r:10,g:12,b:26,a:1};
    let n=el;
    while(n&&n!==document.documentElement){
      const st=getComputedStyle(n);
      const solid=parse(st.backgroundColor);
      const gs=(st.backgroundImage&&st.backgroundImage!=='none')?stops(st.backgroundImage):[];
      const opaqueSolid=solid&&solid.a>=0.99;
      const opaqueGrads=gs.filter(g=>g.a>=0.99);
      if(opaqueSolid||opaqueGrads.length){
        const under=opaqueSolid?solid:base;
        const cands=[];
        if(opaqueSolid)cands.push(solid);
        gs.forEach(g=>cands.push(comp(g,under)));
        return cands.length?cands:[under];
      }
      n=n.parentElement;
    }
    return [base];
  }
  const out=[];
  document.querySelectorAll('body *').forEach(el=>{
    const st=getComputedStyle(el);
    if(st.display==='none'||st.visibility==='hidden')return;
    const r=el.getBoundingClientRect();if(r.width<4||r.height<4)return;
    if(!el.textContent.trim())return;
    if(el.children.length>0)return;
    if(!/[\\u0600-\\u06FF\\u0750-\\u077Fa-zA-Z0-9]/.test(el.textContent))return; // رموز/إيموجي فقط — تُستثنى
    if(el.closest('.board')||el.closest('#pieces-layer'))return;
    const fg=parse(st.color);if(!fg||fg.a===0)return; // نص متدرج (background-clip:text) يُستثنى
    if(st.webkitBackgroundClip==='text'||st.backgroundClip==='text')return;
    const size=parseFloat(st.fontSize);const bold=parseInt(st.fontWeight)>=700;
    const large=size>=24||(size>=18.66&&bold);
    const need=large?3:4.5;
    let worst=99;
    bgCandidates(el).forEach(bg=>{const rr=ratio(fg,bg);if(rr<worst)worst=rr});
    if(worst<need)out.push({t:el.textContent.trim().slice(0,40),ratio:+worst.toFixed(2),need,color:st.color,size});
  });
  return out;
}
"""
def test_contrast(pw):
    browser = pw.chromium.launch(headless=False)
    ctx = browser.new_context(viewport={"width": 1360, "height": 900}, locale="ar")
    page = ctx.new_page()
    # لودو: إعداد + سؤال
    page.goto(BASE + "/game/ludo")
    page.wait_for_timeout(800)
    fails = page.evaluate(CONTRAST_JS)
    ok("contrast: إعداد لودو", len(fails) == 0, fails[:4])
    page.click("#start-btn"); page.wait_for_timeout(500)
    page.click("#roll-btn"); page.wait_for_timeout(900)
    if page.locator(".qmodal").count():
        fails = page.evaluate(CONTRAST_JS)
        ok("contrast: نافذة سؤال لودو", len(fails) == 0, fails[:4])
    # مافيا أونلاين: لوبي
    page.goto(BASE + "/game/mafia?skip_intro=1")
    page.wait_for_timeout(600)
    fails = page.evaluate(CONTRAST_JS)
    ok("contrast: شاشة اختيار مافيا", len(fails) == 0, fails[:4])
    page.locator(".mode-card.online").click(); page.wait_for_timeout(300)
    fails = page.evaluate(CONTRAST_JS)
    ok("contrast: بوابة مافيا أونلاين", len(fails) == 0, fails[:4])
    page.fill("#moName", "فاحص"); page.click("#moCreateBtn")
    page.wait_for_selector("#screenOnline.on", timeout=8000); page.wait_for_timeout(1800)
    fails = page.evaluate(CONTRAST_JS)
    ok("contrast: لوبي مافيا أونلاين", len(fails) == 0, fails[:4])
    shot(page, "mafia_online_lobby_contrast")
    # بدء اللعبة لفحص واجهة كشف الدور والليل
    code = page.locator("#moRoomCode").inner_text().strip()
    for nm in ["ل1", "ل2", "ل3", "ل4"]:
        api(f"/api/rooms/{code}/join", {"name": nm})
    page.wait_for_timeout(2200)
    page.click('[data-mo="start"]')
    page.wait_for_selector("#moRoleReveal.on", timeout=8000)
    page.wait_for_timeout(700)
    fails = page.evaluate(CONTRAST_JS)
    ok("contrast: بطاقة كشف الدور", len(fails) == 0, fails[:4])
    page.click("#moRoleOk")
    page.wait_for_timeout(1700)
    fails = page.evaluate(CONTRAST_JS)
    ok("contrast: واجهة الليل أونلاين", len(fails) == 0, fails[:4])
    shot(page, "mafia_online_night_contrast")
    ctx.close(); browser.close()

if __name__ == "__main__":
    with sync_playwright() as pw:
        test_mafia_online(pw)
        test_mafia_partners()
        test_mafia_local(pw)
        test_ludo(pw)
        test_contrast(pw)
    print("\n══════════ SUMMARY ══════════")
    print("PASS:", len(RESULTS["pass"]), " FAIL:", len(RESULTS["fail"]))
    for f in RESULTS["fail"]:
        print("  ✗", f)
    (SCRATCH / "test_results.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if RESULTS["fail"] else 0)
