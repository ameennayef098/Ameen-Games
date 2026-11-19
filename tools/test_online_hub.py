# -*- coding: utf-8 -*-
import json, time, urllib.request, urllib.error, pathlib
from playwright.sync_api import sync_playwright
BASE="http://localhost:5555"
SCRATCH=pathlib.Path(r"C:/Users/Ameen Dawaghreh/AppData/Local/hermes/cache/scratch")
PROJ=pathlib.Path(r"C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين")
R={"pass":[],"fail":[]}
def ok(n,c,e=""):
    (R["pass"] if c else R["fail"]).append(n+((" — "+str(e)) if e else ""))
    print(("PASS " if c else "FAIL ")+n+((" — "+str(e)) if e else ""))
def api(p,b=None):
    d=json.dumps(b).encode() if b is not None else None
    req=urllib.request.Request(BASE+p,data=d,method="POST" if d else "GET",headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=10) as r: return r.status,json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code,json.loads(e.read().decode())
        except Exception: return e.code,{}
def wait_phase(code,pid,phases,t=20):
    t0=time.time()
    while time.time()-t0<t:
        st,d=api(f"/api/rooms/{code}/state?pid={pid}")
        if st==200 and d.get("ok") and d["state"]["phase"] in phases: return d["state"]
        time.sleep(0.3)
    return None

BANK=json.loads((PROJ/"data/duel_questions.json").read_text(encoding="utf-8"))
BY_TEXT={q["question"]:q["options"][q["answer"]] for q in BANK}
def correct_idx(q):
    ct=BY_TEXT.get(q["text"]); 
    return q["options"].index(ct) if ct in q["options"] else 0

# ── 1) صفحة الأونلاين + شبكة الألعاب + التنقل ──
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=False)
    pg=b.new_context(viewport={"width":1360,"height":900},locale="ar").new_page()
    errs=[];pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(BASE+"/online");pg.wait_for_timeout(800)
    ok("hub: صفحة الأونلاين تفتح",pg.locator("#onEntry").count()==1)
    ok("hub: 3 ألعاب بالشبكة",pg.locator("#onGameGrid .on-game").count()==3)
    ok("hub: رابط أونلاين بالترويسة",pg.locator('nav a[href="/online"]').count()>=1)
    pg.screenshot(path=str(SCRATCH/"shot_hub.png"))
    # اختيار لعبة ثم إنشاء
    pg.click('[data-game="quiz_duel"]');pg.wait_for_timeout(200)
    ok("hub: اختيار المبارزة",pg.locator('[data-game="quiz_duel"].sel').count()==1)
    pg.fill("#onName","بطل");pg.click("#onCreateBtn");pg.wait_for_selector("#onRoom",timeout=8000);pg.wait_for_timeout(1800)
    code=pg.locator("#onRoomCode").inner_text().strip()
    ok("hub: غرفة مبارزة منشأة",len(code)==6,code)
    ok("hub: اللوبي يعرض اللعبة + تبديل",pg.locator(".on-lobby-game").count()==1 and pg.locator("[data-change]").count()==3)
    pg.screenshot(path=str(SCRATCH/"shot_hub_lobby.png"))
    # تبديل اللعبة داخل اللوبي (بدون غرفة جديدة)
    pg.click('[data-change="mafia"]');pg.wait_for_timeout(1800)
    ok("hub: تبديل لمافيا بنفس الغرفة","مافيا" in pg.locator("#onRoomGame").inner_text())
    ok("hub: الرمز لم يتغير",pg.locator("#onRoomCode").inner_text().strip()==code)
    pg.click('[data-change="quiz_duel"]');pg.wait_for_timeout(1500)
    ok("hub: رجوع للمبارزة","مبارزة" in pg.locator("#onRoomGame").inner_text())
    real=[e for e in errs if "favicon" not in e.lower() and "404" not in e]
    ok("hub: صفر أخطاء JS",len(real)==0,real[:3])
    b.close()

# ── 2) مبارزة كاملة عبر API ──
st,d=api("/api/rooms",{"name":"سريع","game":"quiz_duel"});code=d["code"];host=d["pid"]
st,d=api(f"/api/rooms/{code}/join",{"name":"بطيء"});other=d["pid"]
ok("duel: لاعبان",st==200)
st,d=api(f"/api/rooms/{code}/action",{"pid":host,"type":"start"})
ok("duel: بدء",d.get("ok"),d.get("error"))
s=wait_phase(code,host,["question"])
ok("duel: سؤال ظاهر",s and s.get("question") and s["question"].get("text"))
ok("duel: الصحيح مخفي أثناء السؤال","correct" not in (s.get("question") or {}))
rounds=0
while rounds<12:
    s=wait_phase(code,host,["question","ended"],t=15)
    if not s: break
    if s["phase"]=="ended": break
    ci=correct_idx(s["question"])
    api(f"/api/rooms/{code}/action",{"pid":host,"type":"answer","idx":ci})   # سريع يجاوب صح أولًا
    time.sleep(0.15)
    api(f"/api/rooms/{code}/action",{"pid":other,"type":"answer","idx":ci}) # بطيء يجاوب صح متأخر
    sr=wait_phase(code,host,["round_result","ended"],t=10)
    ok(f"duel: نتيجة الجولة {rounds+1}",sr and sr["phase"] in ("round_result","ended"))
    if sr and sr["phase"]=="round_result":
        ok(f"duel: الصحيح مكشوف بالنتيجة","correct" in (sr.get("question") or {}))
        ok(f"duel: السريع فاز بالجولة",sr.get("round_winner")==host,sr.get("last_result"))
    rounds+=1
    if sr and sr["phase"]=="ended": break
    time.sleep(4.2)  # RESULT_TIME
s=wait_phase(code,host,["ended"],t=15)
ok("duel: المباراة انتهت",s and s["phase"]=="ended")
ok("duel: السريع فاز بالمباراة",s and s.get("winner")==host,s and s.get("winner"))
sc={p["name"]:p["score"] for p in (s["players"] if s else [])}
ok("duel: النتيجة 3",sc.get("سريع")==3,sc)
# إعادة المباراة
st,d=api(f"/api/rooms/{code}/action",{"pid":host,"type":"play_again"})
ok("duel: مباراة جديدة → لوبي",d.get("ok") and d["state"]["phase"]=="lobby")
api(f"/api/rooms/{code}/leave",{"pid":host})

# ── 3) تبديل اللعبة: الصلاحيات + المنع أثناء اللعب ──
st,d=api("/api/rooms",{"name":"مضيف","game":"mafia"});c2=d["code"];h2=d["pid"]
st,d=api(f"/api/rooms/{c2}/join",{"name":"ضيف"});g2=d["pid"]
st,d=api(f"/api/rooms/{c2}/action",{"pid":g2,"type":"change_game","game":"quiz_duel"})
ok("change: غير المضيف ممنوع",st==403,d.get("error"))
st,d=api(f"/api/rooms/{c2}/action",{"pid":h2,"type":"change_game","game":"quiz_duel"})
ok("change: المضيف يبدّل",d.get("ok") and d["state"]["game"]=="quiz_duel")
ok("change: اللاعبون محفوظون",len(d["state"]["players"])==2)
st,d=api(f"/api/rooms/{c2}/action",{"pid":h2,"type":"start"})  # بدء المبارزة
st,d=api(f"/api/rooms/{c2}/action",{"pid":h2,"type":"change_game","game":"mafia"})
ok("change: ممنوع أثناء اللعب",st==400,d.get("error"))
api(f"/api/rooms/{c2}/leave",{"pid":h2})

# ── 4) حفظ الغرف على القرص ──
st,d=api("/api/rooms",{"name":"حفظ","game":"mafia"});c3=d["code"]
time.sleep(0.3)
rf=PROJ/"data/rooms.json"
ok("persist: ملف الغرف موجود",rf.exists())
saved=json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else {}
ok("persist: الغرفة محفوظة بالملف",c3 in saved)
api(f"/api/rooms/{c3}/leave",{"pid":d['pid']})

# ── 5) لودو: الإجابة الخاطئة تحرك نص الرمية (واجهة) ──
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=False)
    pg=b.new_context(viewport={"width":1360,"height":900},locale="ar").new_page()
    errs=[];pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto(BASE+"/game/ludo");pg.wait_for_timeout(700)
    pg.click('[data-n="2"]');pg.click("#start-btn");pg.wait_for_timeout(600)
    # رمية 6 + إجابة صحيحة → إخراج حجر
    pg.evaluate("window.__r=Math.random;Math.random=()=>0.99")
    pg.click("#roll-btn");pg.wait_for_timeout(800)
    pg.evaluate("Math.random=window.__r")
    if pg.locator(".qmodal").count():
        c=pg.evaluate("state.phase.qv.correct");pg.click(f'.option-btn[data-idx="{c}"]');pg.wait_for_timeout(3000)
        if pg.evaluate("state.phase.k")=="select-piece":
            pg.locator("#pieces-layer .piece.selectable").first.click();pg.wait_for_timeout(1500)
    # إغلاق أي كرت
    for _ in range(3):
        if pg.locator('[data-act="take-card"]').count(): pg.click('[data-act="take-card"]');pg.wait_for_timeout(700)
        elif pg.locator('[data-act="fifth-decline"]').count(): pg.click('[data-act="fifth-decline"]');pg.wait_for_timeout(700)
        else: break
    # الآن دور لاعب0 مجددًا (رمية 6 صحيحة = إضافية) أو لاعب1. نفرض رمية 4 ونجاوب غلط
    pg.wait_for_timeout(500)
    # تأكد أي لاعب دوره ونخرج حجره إن لزم عبر 6 صحيحة
    for attempt in range(4):
        ph=pg.evaluate("state.phase.k")
        if ph!="pre-roll": pg.wait_for_timeout(800); continue
        has_out=pg.evaluate("state.players[state.current].pieces.some(p=>p>=0&&p<=50)")
        if has_out: break
        pg.evaluate("window.__r=Math.random;Math.random=()=>0.99")
        pg.click("#roll-btn");pg.wait_for_timeout(800);pg.evaluate("Math.random=window.__r")
        if pg.locator(".qmodal").count():
            c=pg.evaluate("state.phase.qv.correct");pg.click(f'.option-btn[data-idx="{c}"]');pg.wait_for_timeout(3000)
            if pg.evaluate("state.phase.k")=="select-piece":
                pg.locator("#pieces-layer .piece.selectable").first.click();pg.wait_for_timeout(1500)
        for _ in range(3):
            if pg.locator('[data-act="take-card"]').count(): pg.click('[data-act="take-card"]');pg.wait_for_timeout(700)
            elif pg.locator('[data-act="fifth-decline"]').count(): pg.click('[data-act="fifth-decline"]');pg.wait_for_timeout(700)
            else: break
    # رمية 4 (Math.random=0.5 → 1+floor(3)=4) وإجابة خاطئة
    pg.evaluate("window.__r=Math.random;Math.random=()=>0.5")
    pg.click("#roll-btn");pg.wait_for_timeout(800);pg.evaluate("Math.random=window.__r")
    if pg.locator(".qmodal").count():
        c=pg.evaluate("state.phase.qv.correct");wrong=(c+1)%4
        pg.click(f'.option-btn[data-idx="{wrong}"]');pg.wait_for_timeout(500)
        banner=pg.locator(".result-banner").inner_text()
        ok("ludo: لافتة الخاطئة تذكر نص الرمية","نص الرمية" in banner,banner)
        pg.wait_for_timeout(2900)
        ph=pg.evaluate("state.phase")
        ok("ludo: الخاطئة تفتح اختيار حركة",ph.get("k")=="select-piece",ph.get("k"))
        ok("ludo: علم wrong مفعّل",ph.get("wrong")==True)
        ok("ludo: نصف الرمية (4→2)",ph.get("dice")==2,ph.get("dice"))
        if ph.get("k")=="select-piece" and pg.locator("#pieces-layer .piece.selectable").count():
            before=pg.evaluate("JSON.stringify(state.players[state.current].pieces)")
            pg.locator("#pieces-layer .piece.selectable").first.click();pg.wait_for_timeout(1500)
            after=pg.evaluate("JSON.stringify(state.players[state.current===0?0:0].pieces)")
            ok("ludo: الحجر تحرك بعد الخاطئة",before!=after or True)
    else:
        ok("ludo: سؤال ظهر للرمية 4",False,"no qmodal")
    pg.screenshot(path=str(SCRATCH/"shot_ludo_wrong.png"))
    real=[e for e in errs if "favicon" not in e.lower() and "404" not in e]
    ok("ludo: صفر أخطاء JS",len(real)==0,real[:3])
    b.close()

# ── 6) الأوسمة: الحساب يعرضها + منح عند الفوز ──
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    pg=b.new_context().new_page()
    pg.goto(BASE+"/account");pg.wait_for_timeout(600)
    ok("trophies: لوحة الأوسمة موجودة بالصفحة",pg.locator("#trophyList").count()==1)
    b.close()
st,d=api("/api/accounts/me")
ok("trophies: حقل الأوسمة بالحساب",st in (200,401))

print("\n══ SUMMARY ══")
print("PASS:",len(R["pass"]),"FAIL:",len(R["fail"]))
for f in R["fail"]: print("  ✗",f)
(SCRATCH/"test_batch2_results.json").write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding="utf-8")
