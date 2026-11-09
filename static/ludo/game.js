/* ═══════════════════════════════════════════════════════════════════
   لودو الأسئلة والكروت — منطق اللعبة الكامل (JavaScript خالص)
   ─────────────────────────────────────────────────────────────────
   المحتويات:
   ⚙️ إعدادات قابلة للتعديل (نسب الكروت والمؤقت وعدد اللاعبين)
   1) ثوابت الرقعة والألوان والكروت
   2) محرك اللعبة (الحركات والالتقاط وتأثيرات الكروت)
   3) بنك الأسئلة (سحب بلا تكرار + خلط الخيارات)
   4) الحالة العامة ومخفّض الأفعال (Reducer)
   5) العرض (الرقعة + الشريط الجانبي + النوافذ)
   6) الاستمرار التلقائي بعد عرض نتيجة الإجابة
   7) ربط الأحداث والإقلاع
   ═══════════════════════════════════════════════════════════════════ */
"use strict";

/* ═══════════════ ⚙️ إعدادات قابلة للتعديل ═══════════════ */
const CONFIG = {
  // فرصة الكرت بعد كل إجابة صحيحة وحركة:
  // 60% من الأدوار بفرصة 15%، و40% من الأدوار بفرصة 30% (متوسط ~21%)
  CHANCE_A: 0.15,
  WEIGHT_A: 60,   // وزن الاحتمال الأول (٪)
  CHANCE_B: 0.30,
  MAX_CARDS: 4,        // الحد الأقصى لحيازة الكروت
  TIMER_SECONDS: 20,   // مدة مؤقت السؤال (ثانية)
  RESULT_PAUSE: 2600,  // مدة عرض نتيجة الإجابة قبل الانتقال (مللي ثانية)
  DEFAULT_PLAYERS: 2,  // عدد اللاعبين الافتراضي
};

/* ═══════════════ 1) الثوابت ═══════════════ */

const COLORS = ["red", "green", "yellow", "blue"];
const COLOR_HEX = { red: "#E53935", green: "#43A047", yellow: "#FDD835", blue: "#1E88E5" };
const COLOR_NAME_AR = { red: "الأحمر", green: "الأخضر", yellow: "الأصفر", blue: "الأزرق" };

const CARD_INFO = {
  steps: { name: "كرت تحديد الخطوات", label: "🎯 كرت الخطوات", emoji: "🎯", color: "#7B1FA2",
    desc: "اختر رقمًا من 1 إلى 12 وتحرك به قطعة من قطعك بدل النرد — بلا سؤال في هذا الدور." },
  swap:  { name: "كرت تبديل المواقع", label: "🔄 كرت التبديل", emoji: "🔄", color: "#00897B",
    desc: "بدّل موقع أحد أحجارك على المسار مع حجر خصم على المسار — فورًا ثم ترمي النرد كالمعتاد." },
  back4: { name: "كرت الإرجاع 4 خطوات", label: "↩️ كرت الإرجاع", emoji: "↩️", color: "#D84315",
    desc: "أرجع حجرك أو حجر خصم 4 خطوات إلى الوراء على المسار الرئيسي — ثم ترمي النرد كالمعتاد." },
  bomb:  { name: "كرت القنبلة", label: "💣 كرت القنبلة", emoji: "💣", color: "#FF6D00",
    desc: "اختر كلمة: أحمر / أزرق / أسود / قنبلة — وتغير اللعب كله!" },
};
const MAX_CARDS = CONFIG.MAX_CARDS;
const FINISH = 56;

// خلايا انطلاق كل لون على مسار الـ 52 خلية
const STARTS = { red: 0, green: 13, yellow: 26, blue: 39 };
// الخلايا الآمنة: 4 بدايات + 4 نجوم
const SAFE_CELLS = new Set([0, 13, 26, 39, 8, 21, 34, 47]);

// كلمات كرت القنبلة وتأثيراتها
const BOMB_WORDS = [
  { key: "red",    label: "أحمر",  color: "#E53935", effect: "red" },
  { key: "blue",   label: "أزرق", color: "#1E88E5", effect: "blue" },
  { key: "black",  label: "أسود", color: "#111827", effect: "black" },
  { key: "bomb",   label: "قنبلة", color: "#FF6D00", effect: "bomb" },
];

// مواقع القواعد (أركان الرقعة 6×6) وفُرش الأحجار داخلها
const BASE_ORIGIN = { red: [0, 0], green: [9, 0], yellow: [9, 9], blue: [0, 9] };
const BASE_SLOTS = [[2, 2], [4, 2], [2, 4], [4, 4]];

// أعمدة البيت (المسار النهائي 5 خلايا لكل لون)
const HOME_COLUMN = {
  red:    [1, 2, 3, 4, 5].map((x) => [x, 7]),
  green:  [1, 2, 3, 4, 5].map((y) => [7, y]),
  yellow: [13, 12, 11, 10, 9].map((x) => [x, 7]),
  blue:   [13, 12, 11, 10, 9].map((y) => [7, y]),
};

// المسار الرئيسي — 52 خلية بترتيب السير
const TRACK = [
  ...[1, 2, 3, 4, 5].map((x) => [x, 6]),
  ...[5, 4, 3, 2, 1, 0].map((y) => [6, y]),
  ...[7, 8].map((x) => [x, 0]),
  ...[1, 2, 3, 4, 5].map((y) => [8, y]),
  ...[9, 10, 11, 12, 13, 14].map((x) => [x, 6]),
  ...[7, 8].map((y) => [14, y]),
  ...[13, 12, 11, 10, 9].map((x) => [x, 8]),
  ...[9, 10, 11, 12, 13, 14].map((y) => [8, y]),
  ...[7, 6].map((x) => [x, 14]),
  ...[13, 12, 11, 10, 9].map((y) => [6, y]),
  ...[5, 4, 3, 2, 1, 0].map((x) => [x, 8]),
  ...[7, 6].map((y) => [0, y]),
];

// نقاط النرد (مواضع الأزرار في شبكة 3×3)
const PIPS = {
  0: [],
  1: [4],
  2: [0, 8],
  3: [0, 4, 8],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
};

/* ═══════════════ 2) محرك اللعبة ═══════════════ */

function absCell(color, pos) {
  if (pos < 0 || pos > 50) return null;
  return TRACK[(STARTS[color] + pos) % 52];
}

// الإحداثيات البصرية لحجر: -1 قاعدة، 0..50 مسار، 51..55 عمود البيت، 56 المركز
function cellXY(color, pos, pieceSlot) {
  if (pos === -1) {
    const [bx, by] = BASE_ORIGIN[color];
    const [sx, sy] = BASE_SLOTS[pieceSlot % 4];
    return [bx + sx, by + sy];
  }
  if (pos === FINISH) return [7, 7];
  if (pos >= 51) {
    const [x, y] = HOME_COLUMN[color][Math.min(4, pos - 51)];
    return [x, y];
  }
  return absCell(color, pos);
}

// الحركات القانونية برمية النرد: الخروج من القاعدة بالسادس فقط
function legalPieceMoves(player, n) {
  const out = [];
  player.pieces.forEach((pos, i) => {
    if (pos === FINISH) return;
    if (pos === -1) { if (n === 6) out.push(i); return; }
    if (pos + n <= FINISH) out.push(i);
  });
  return out;
}

// الحركات القانونية لكرت الخطوات: الإخراج من القاعدة بأي رقم
function legalStepsMoves(player, n) {
  const out = [];
  player.pieces.forEach((pos, i) => {
    if (pos === FINISH) return;
    if (pos === -1) { out.push(i); return; }
    if (pos + n <= FINISH) out.push(i);
  });
  return out;
}

function enemiesAtAbsCell(state, cellIdx, exceptPlayer) {
  const out = [];
  state.players.forEach((p, pi) => {
    if (pi === exceptPlayer) return;
    p.pieces.forEach((pos, ii) => {
      if (pos >= 0 && pos <= 50 && (STARTS[p.color] + pos) % 52 === cellIdx) out.push({ player: pi, piece: ii });
    });
  });
  return out;
}

function deep(s) { return JSON.parse(JSON.stringify(s)); }

// تحريك حجر بعدد خطوات مع الالتقاط (نرد أو كرت خطوات)
function applyMove(state, playerIdx, pieceIdx, n, fromStepsCard) {
  const s = deep(state);
  const p = s.players[playerIdx];
  const prevPos = p.pieces[pieceIdx];
  const released = prevPos === -1;
  const pos = released ? 0 : prevPos + n;
  p.pieces[pieceIdx] = pos;
  const captured = [];

  if (pos >= 0 && pos <= 50) {
    const cellIdx = (STARTS[p.color] + pos) % 52;
    if (!SAFE_CELLS.has(cellIdx)) {
      const enemies = enemiesAtAbsCell(s, cellIdx, playerIdx);
      if (enemies.length === 1) {
        const e = enemies[0];
        s.players[e.player].pieces[e.piece] = -1;
        captured.push(e);
      }
    }
  }

  let logMsg = released
    ? `${p.name}: أخرج حجرًا إلى خلية البداية${fromStepsCard ? " (كرت الخطوات)" : ""}`
    : `${p.name}: تحرك ${n} خطوة${captured.length ? " والتقط حجر خصم!" : ""}`;
  if (pos === FINISH) logMsg = `${p.name}: وصل حجر إلى المركز! 🏁`;

  s.lastCaptured = captured[0] || null;
  s.log = [logMsg, ...s.log].slice(0, 30);
  const finished = p.pieces.every((v) => v === FINISH);
  if (finished && !s.winnerOrder.includes(playerIdx)) s.winnerOrder.push(playerIdx);
  return { state: s, captured, finished };
}

// تبديل موقعين (كرت التبديل) — بلا التقاط
function applySwap(state, aPlayer, aPiece, bPlayer, bPiece) {
  const s = deep(state);
  const pa = s.players[aPlayer].pieces;
  const pb = s.players[bPlayer].pieces;
  const tmp = pa[aPiece];
  pa[aPiece] = pb[bPiece];
  pb[bPiece] = tmp;
  s.log = [`${s.players[aPlayer].name}: بدّل موقع حجره مع حجر ${s.players[bPlayer].name}`, ...s.log].slice(0, 30);
  return s;
}

// إرجاع 4 خطوات (كرت الإرجاع) — بلا التقاط
function applyBack4(state, playerIdx, pieceIdx) {
  const s = deep(state);
  const p = s.players[playerIdx];
  p.pieces[pieceIdx] = Math.max(0, p.pieces[pieceIdx] - 4);
  s.log = [`${s.players[playerIdx].name}: أرجع حجر ${p.name} 4 خطوات`, ...s.log].slice(0, 30);
  return s;
}

// محرك احتمالية الكرت: نسبة WEIGHT_A% من الأدوار بفرصة CHANCE_A والباقي بفرصة CHANCE_B
function decideCardProb() {
  return Math.random() * 100 < CONFIG.WEIGHT_A ? CONFIG.CHANCE_A : CONFIG.CHANCE_B;
}

function drawCardType() {
  const r = Math.random();
  if (r < 0.25) return "steps";
  if (r < 0.5) return "swap";
  if (r < 0.75) return "back4";
  return "bomb";
}

function drawBombWord() {
  return BOMB_WORDS[Math.floor(Math.random() * BOMB_WORDS.length)];
}

// أهداف كرت الإرجاع: أي حجر (لك أو لخصم) على المسار عند 4 خطوات فأكثر
function back4Targets(state) {
  const out = [];
  state.players.forEach((p, pi) => {
    p.pieces.forEach((pos, ii) => { if (pos >= 4 && pos <= 50) out.push({ player: pi, piece: ii }); });
  });
  return out;
}

// أهداف كرت التبديل
function swapTargets(state, currentPlayer) {
  const me = state.players[currentPlayer];
  const own = me.pieces.map((pos, i) => (pos >= 0 && pos <= 50 ? i : -1)).filter((i) => i >= 0);
  const enemy = [];
  state.players.forEach((p, pi) => {
    if (pi === currentPlayer) return;
    p.pieces.forEach((pos, ii) => { if (pos >= 0 && pos <= 50) enemy.push({ player: pi, piece: ii }); });
  });
  return { own, enemy };
}

/* ═══════════════ 3) الأسئلة ═══════════════ */

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// يسحب سؤالًا جديدًا للاعب (بلا تكرار حتى استنفاد البنك) ويخلط الخيارات
function drawQuestion(state, playerIdx) {
  const used = new Set(state.usedQuestions[playerIdx] || []);
  let pool = QUESTION_BANK.filter((q) => !used.has(q.id));
  if (pool.length === 0) pool = QUESTION_BANK;
  const q = pool[Math.floor(Math.random() * pool.length)];
  const correctText = q.options[q.answer];
  const options = shuffle(q.options);
  return { text: q.question, options, correct: options.indexOf(correctText), sourceId: q.id };
}

function markQuestionUsed(state, playerIdx, qid) {
  const used = { ...state.usedQuestions };
  used[playerIdx] = [...(used[playerIdx] || []), qid];
  if (used[playerIdx].length >= QUESTION_BANK.length) used[playerIdx] = [];
  return used;
}

/* ═══════════════ 4) الحالة العامة ومخفّض الأفعال ═══════════════ */

// ألوان اللاعبين حسب عددهم — لاعبان يتقابلان في القطرين (الأحمر مقابل الأصفر)
const COUNT_COLORS = {
  2: ["red", "yellow"],
  3: ["red", "green", "yellow"],
  4: COLORS,
};

function initialState() {
  return {
    players: [], current: 0, sixStreak: 0, cardProb: 0.15,
    phase: { k: "setup" }, dice: null, log: [], usedQuestions: {},
    timerOn: false, lastCaptured: null, winnerOrder: [],
    bombColor: null,
  };
}

let state = initialState();
let lastQv = null;       // آخر سؤال معروض (لعرض النتيجة)
let lastSelected = null; // فهرس خيار اللاعب الأخير
let playerCount = CONFIG.DEFAULT_PLAYERS;
let timerOn = false;
let autoTimer = null;    // مؤقت الاستمرار التلقائي بعد عرض النتيجة
let qInterval = null;    // عدّاد المؤقت داخل نافذة السؤال
let selectableSet = new Set();
let lastDiceShown = null;

function makePlayer(color, order) {
  return {
    id: order, color,
    name: `لاعب ${order + 1}`,
    cards: [], pieces: [-1, -1, -1, -1],
  };
}

function advanceTurn(s) {
  s.current = (s.current + 1) % s.players.length;
  s.sixStreak = 0;
  s.cardProb = decideCardProb();
  s.phase = { k: "pre-roll" };
  s.log = [`دور ${s.players[s.current].name}`, ...s.log].slice(0, 30);
  s.bombColor = null;
}

// بعد إتمام الحركة: فحص الفوز ثم رمية إضافية أو انتقال الدور
function afterMove(s) {
  const p = s.players[s.current];
  if (p.pieces.every((v) => v === FINISH)) {
    s.phase = { k: "game-over", winner: s.current };
    s.log = [`🏆 ${p.name} فاز بالجولة!`, ...s.log].slice(0, 30);
    s.bombColor = null;
    return;
  }
  if (s.dice === 6) {
    s.phase = { k: "pre-roll" };
    s.log = [`${p.name}: رمية إضافية! 🎲`, ...s.log].slice(0, 30);
    s.bombColor = null;
    return;
  }
  advanceTurn(s);
}

function reducer(st, a) {
  if (a.t === "start") {
    // كل اللاعبين بشر يلعبون على نفس الجهاز — بلا كمبيوتر
    const players = COUNT_COLORS[a.count ?? 2].map((color, i) => makePlayer(color, i));
    const s = initialState();
    s.players = players;
    s.timerOn = !!a.timerOn;
    s.cardProb = decideCardProb();
    s.phase = { k: "pre-roll" };
    s.log = [`بدأت الجولة! دور ${players[0].name}`];
    return s;
  }
  if (a.t === "new-game") return initialState();

  const s = deep(st);
  const cur = s.players[s.current];
  const ph = s.phase;

  switch (a.t) {
    case "roll": {
      if (ph.k !== "pre-roll") return st;
      const dice = 1 + Math.floor(Math.random() * 6);
      s.dice = dice;
      if (dice === 6) {
        s.sixStreak += 1;
        if (s.sixStreak >= 3) {
          s.log = [`💀 ${cur.name}: ثلاث ستات متتالية — ضاع الدور!`, ...s.log].slice(0, 30);
          advanceTurn(s);
          return s;
        }
      } else {
        s.sixStreak = 0;
      }
      const legal = legalPieceMoves(cur, dice);
      if (legal.length === 0) {
        s.log = [`🚫 ${cur.name}: لا توجد حركة متاحة برمية ${dice}`, ...s.log].slice(0, 30);
        advanceTurn(s);
        return s;
      }
      s.phase = { k: "question", qv: drawQuestion(s, s.current) };
      return s;
    }

    case "answer": {
      if (ph.k !== "question") return st;
      const idx = a.idx ?? -1;
      s.usedQuestions = markQuestionUsed(s, s.current, ph.qv.sourceId);
      const correct = idx === ph.qv.correct;
      lastQv = ph.qv;
      lastSelected = idx;
      s.phase = { k: "answer-result", correct, dice: s.dice ?? 0 };
      s.log = [correct ? `✅ ${cur.name}: إجابة صحيحة!` : `❌ ${cur.name}: إجابة خاطئة — لا تتحرك`, ...s.log].slice(0, 30);
      return s;
    }

    case "answer-continue": {
      if (ph.k !== "answer-result") return st;
      if (!ph.correct) { advanceTurn(s); return s; }
      s.phase = { k: "select-piece", dice: s.dice ?? 0, legal: legalPieceMoves(cur, s.dice ?? 0) };
      return s;
    }

    case "select-piece": {
      if (ph.k !== "select-piece") return st;
      const dice = ph.dice;
      const res = applyMove(s, s.current, a.idx ?? 0, dice, false);
      const ns = res.state;
      ns.dice = dice;
      // فرصة الكرت بعد الإجابة الصحيحة والحركة
      if (Math.random() * 100 < ns.cardProb * 100) {
        const card = drawCardType();
        if (ns.players[s.current].cards.length < MAX_CARDS) ns.phase = { k: "card-offer", card };
        else ns.phase = { k: "fifth-choice", card };
        return ns;
      }
      afterMove(ns);
      return ns;
    }

    case "play-card": {
      if (ph.k !== "pre-roll") return st;
      const card = a.card;
      if (!card || !cur.cards.includes(card)) return st;
      s.dice = null; // استخدام كرت يلغي النرد الحالي
      if (card === "steps") { s.phase = { k: "steps-number" }; return s; }
      if (card === "swap") {
        const t = swapTargets(s, s.current);
        if (t.own.length === 0 || t.enemy.length === 0) {
          s.log = [`🚫 لا يوجد هدف صالح للتبديل الآن`, ...s.log].slice(0, 30);
          return st;
        }
        s.phase = { k: "swap-own", legal: t.own };
        return s;
      }
      if (card === "bomb") {
        const word = drawBombWord();
        s.phase = { k: "bomb-offer", word };
        return s;
      }
      const targets = back4Targets(s);
      if (targets.length === 0) {
        s.log = [`🚫 لا يوجد هدف صالح للإرجاع الآن`, ...s.log].slice(0, 30);
        return st;
      }
      s.phase = { k: "back4-select", legal: targets.map((t) => t.player * 4 + t.piece) };
      return s;
    }

    case "back-to-preroll": {
      if (ph.k !== "steps-number") return st;
      s.phase = { k: "pre-roll" };
      return s;
    }

    case "bomb-close": {
      if (ph.k !== "bomb-result") return st;
      if (ph.word && ph.word.effect === "black") advanceTurn(s);
      else s.phase = { k: "pre-roll" };
      return s;
    }

    case "steps-number": {
      if (ph.k !== "steps-number") return st;
      const n = Math.max(1, Math.min(12, a.n ?? 1));
      const legal = legalStepsMoves(cur, n);
      if (legal.length === 0) return st;
      s.phase = { k: "steps-piece", n, legal };
      return s;
    }

    case "steps-piece": {
      if (ph.k !== "steps-piece") return st;
      const stepsIdx = cur.cards.indexOf("steps");
      if (stepsIdx === -1) return st;
      cur.cards.splice(stepsIdx, 1); // استهلاك الكرت
      s.dice = null;
      s.log = [`🎯 ${cur.name}: استخدم كرت الخطوات (${ph.n} خطوات)`, ...s.log].slice(0, 30);
      const res = applyMove(s, s.current, a.idx ?? 0, ph.n, true);
      const ns = res.state;
      afterMove(ns);
      return ns;
    }

    case "swap-own": {
      if (ph.k !== "swap-own") return st;
      if (!ph.legal.includes(a.idx ?? -1)) return st;
      s.phase = {
        k: "swap-enemy", ownPieceIdx: a.idx ?? 0, ownPlayerIdx: s.current,
        legal: swapTargets(s, s.current).enemy.map((t) => t.player * 4 + t.piece),
      };
      return s;
    }

    case "swap-enemy": {
      if (ph.k !== "swap-enemy") return st;
      const code = (a.player ?? 0) * 4 + (a.piece ?? 0);
      if (!ph.legal.includes(code)) return st;
      const swapIdx = cur.cards.indexOf("swap");
      if (swapIdx === -1) return st;
      cur.cards.splice(swapIdx, 1);
      const ns = applySwap(s, ph.ownPlayerIdx, ph.ownPieceIdx, a.player ?? 0, a.piece ?? 0);
      ns.phase = { k: "pre-roll" };
      ns.log = [`🔄 استخدم ${ns.players[s.current].name} كرت التبديل`, ...ns.log].slice(0, 30);
      return ns;
    }

    case "back4": {
      if (ph.k !== "back4-select") return st;
      const code = (a.player ?? 0) * 4 + (a.piece ?? 0);
      if (!ph.legal.includes(code)) return st;
      const backIdx = cur.cards.indexOf("back4");
      if (backIdx === -1) return st;
      cur.cards.splice(backIdx, 1);
      const ns = applyBack4(s, a.player ?? 0, a.piece ?? 0);
      ns.phase = { k: "pre-roll" };
      ns.log = [`↩️ استخدم ${ns.players[s.current].name} كرت الإرجاع 4 خطوات`, ...ns.log].slice(0, 30);
      return ns;
    }

    case "take-card": {
      if (ph.k !== "card-offer") return st;
      cur.cards.push(ph.card);
      const arName = ph.card === "steps" ? "الخطوات" : ph.card === "swap" ? "التبديل" : "الإرجاع";
      s.log = [`🎁 ${cur.name}: أخذ كرت ${arName}`, ...s.log].slice(0, 30);
      afterMove(s);
      return s;
    }

    case "fifth-swap": {
      if (ph.k !== "fifth-choice") return st;
      const di = a.discardIdx ?? 0;
      if (di < 0 || di >= cur.cards.length) return st;
      cur.cards[di] = ph.card;
      s.log = [`🔄 ${cur.name}: استبدل كرتًا بالكرت الخامس`, ...s.log].slice(0, 30);
      afterMove(s);
      return s;
    }

    case "fifth-decline": {
      if (ph.k !== "fifth-choice") return st;
      s.log = [`✋ ${cur.name}: رفض الكرت الخامس`, ...s.log].slice(0, 30);
      afterMove(s);
      return s;
    }

    case "bomb-choice": {
      if (ph.k !== "bomb-offer") return st;
      const choice = a.word ?? "black";
      const word = BOMB_WORDS.find(w => w.key === choice) || BOMB_WORDS[2];
      s.log = [`💣 ${cur.name}: اختار "${word.label}"`, ...s.log].slice(0, 30);
      if (word.effect === "bomb") {
        s.phase = { k: "bomb-anim", word };
      } else if (word.effect === "black") {
        s.phase = { k: "bomb-result", effect: "black", word };
      } else {
        s.bombColor = word.effect;
        s.phase = { k: "bomb-result", effect: word.effect, color: word.color, word };
      }
      return s;
    }

    case "bomb-finish": {
      if (ph.k !== "bomb-anim") return st;
      s.phase = { k: "game-over", winner: s.current };
      s.bombColor = null;
      return s;
    }

    default:
      return st;
  }
}

function dispatch(action) {
  const prev = snapshotPieces();
  const ns = reducer(state, action);
  if (ns === state) return;
  state = ns;
  render(prev);
  scheduleAuto();
}

/* ═══════════════ 5) العرض ═══════════════ */

const $ = (id) => document.getElementById(id);

function instrText(ph) {
  switch (ph.k) {
    case "pre-roll":      return "ارمِ النرد أو استخدم كرتًا";
    case "question":      return "جاوب على السؤال!";
    case "answer-result": return ph.correct ? "إجابة صحيحة!" : "إجابة خاطئة";
    case "select-piece":  return `اختر حجرًا للتحرك ${ph.dice} خطوات`;
    case "card-offer":    return "كرت جديد يصلك!";
    case "fifth-choice":  return "حيازتك ممتلئة — استبدل أو ارفض";
    case "steps-number":  return "اختر عدد الخطوات";
    case "steps-piece":   return `اختر حجرًا للتحرك ${ph.n} خطوات`;
    case "swap-own":      return "اختر حجرك المراد تبديله";
    case "swap-enemy":    return "اختر حجر الخصم للتبديل معه";
    case "back4-select":  return "اختر الحجر المراد إرجاعه 4 خطوات";
    case "bomb-offer":    return "اختر كلمة القنبلة!";
    case "game-over":     return "انتهت الجولة!";
  }
  return "";
}

// علامة ترتيب القطع في الخلية نفسها
function offsets(count, index) {
  if (count <= 1) return { dx: 0, dy: 0 };
  const spread = [
    { dx: -0.16, dy: -0.16 }, { dx: 0.16, dy: -0.16 },
    { dx: -0.16, dy: 0.16 },  { dx: 0.16, dy: 0.16 },
  ];
  return spread[index % 4];
}

function diceFaceHtml(value) {
  const dots = PIPS[value] || [];
  let cells = "";
  for (let i = 0; i < 9; i++) cells += dots.includes(i) ? "<i></i>" : "<span></span>";
  return `<div class="dice" aria-label="${value ? "النرد يظهر " + value : "النرد — ارمِ لتظهر النتيجة"}">${cells}</div>`;
}

// خريطة أنواع خلايا الرقعة 15×15 — تُبنى مرة واحدة
const LIGHT = { red: "#F8D0CE", green: "#CFE8CC", yellow: "#FDF3C0", blue: "#CCE0F5" };
const CELL_TYPE_MAP = (() => {
  const grid = Array.from({ length: 15 }, () => Array.from({ length: 15 }, () => ({ t: "track", c: null })));
  COLORS.forEach((c) => {
    const [bx, by] = BASE_ORIGIN[c];
    for (let x = bx; x < bx + 6; x++)
      for (let y = by; y < by + 6; y++) grid[y][x] = { t: "base", c };
  });
  for (let x = 6; x <= 8; x++)
    for (let y = 6; y <= 8; y++) grid[y][x] = { t: "center", c: null };
  TRACK.forEach(([x, y], idx) => {
    grid[y][x] = { t: SAFE_CELLS.has(idx) && ![0, 13, 26, 39].includes(idx) ? "safe-star" : "track", c: null };
  });
  COLORS.forEach((c) => {
    const [x, y] = TRACK[STARTS[c]];
    grid[y][x] = { t: "start", c };
  });
  COLORS.forEach((c) => {
    HOME_COLUMN[c].forEach(([x, y]) => { grid[y][x] = { t: "home", c }; });
  });
  return grid;
})();

/* ═══════════════ طبقة الأحجار المتحركة ═══════════════ */
let piecesLayer = null;
let animatingPieces = 0;
const pieceEls = {};

function getPiecesLayer() {
  if (!piecesLayer) {
    piecesLayer = document.createElement("div");
    piecesLayer.id = "pieces-layer";
  }
  return piecesLayer;
}

function snapshotPieces() {
  const m = {};
  state.players.forEach((p, pi) => p.pieces.forEach((pos, ii) => { m[pi + "-" + ii] = pos; }));
  return m;
}

function setPiece(el, x, y, off, sizePct) {
  const s = 100 / 15;
  el.style.left = ((x + 0.5) * s + (off ? off.dx * 2.4 : 0)) + "%";
  el.style.top = ((y + 0.5) * s + (off ? off.dy * 2.4 : 0)) + "%";
  el.style.width = sizePct + "%";
  el.style.height = sizePct + "%";
}

function piecePath(color, fromPos, toPos, slot) {
  const path = [];
  if (fromPos === -1) path.push(cellXY(color, -1, slot));
  const start = fromPos === -1 ? 0 : fromPos;
  const limit = Math.min(toPos, 55);
  for (let p = start; p <= limit; p++) path.push(cellXY(color, p, slot));
  if (toPos === FINISH) path.push([7, 7]);
  return path;
}

function animatePiece(el, color, fromPos, toPos, slot, done) {
  const path = piecePath(color, fromPos, toPos, slot);
  if (!path.length) { done(); return; }
  animatingPieces++;
  const s = 100 / 15;
  el.style.transition = "none";
  el.style.zIndex = 30;
  el.style.left = ((path[0][0] + 0.5) * s) + "%";
  el.style.top = ((path[0][1] + 0.5) * s) + "%";
  el.style.width = "5.4%";
  el.style.height = "5.4%";
  void el.offsetWidth;
  el.style.transition = "";
  let i = 1;
  const step = () => {
    if (i >= path.length) {
      animatingPieces--;
      el.style.zIndex = "";
      done();
      return;
    }
    el.style.left = ((path[i][0] + 0.5) * s) + "%";
    el.style.top = ((path[i][1] + 0.5) * s) + "%";
    el.classList.remove("hop");
    void el.offsetWidth;
    el.classList.add("hop");
    i++;
    setTimeout(step, 115);
  };
  setTimeout(step, 115);
}

function renderPieces(prev) {
  const layer = getPiecesLayer();
  const byCell = new Map();
  const targets = new Map();
  state.players.forEach((p, pi) => {
    p.pieces.forEach((pos, ii) => {
      if (pos === FINISH) return;
      const [x, y] = cellXY(p.color, pos, ii);
      const key = x + "," + y;
      if (!byCell.has(key)) byCell.set(key, []);
      byCell.get(key).push({ player: pi, piece: ii, color: p.color });
      targets.set(pi + "-" + ii, { x, y });
    });
  });

  const seen = new Set();
  targets.forEach((t, key) => {
    seen.add(key);
    const parts = key.split("-");
    const pi = Number(parts[0]), ii = Number(parts[1]);
    const p = state.players[pi];
    let el = pieceEls[key];
    if (!el) {
      el = document.createElement("button");
      el.className = "piece";
      el.dataset.player = pi;
      el.dataset.piece = ii;
      layer.appendChild(el);
      pieceEls[key] = el;
    }
    el.style.background = COLOR_HEX[p.color];
    el.style.display = "";
    const list = byCell.get(t.x + "," + t.y);
    const idx = list.findIndex((o) => o.player === pi && o.piece === ii);
    const off = offsets(list.length, idx);
    const size = list.length > 1 ? 4.4 : 5.4;

    const from = prev ? prev[key] : null;
    const cur = p.pieces[ii];
    if (from !== null && from !== undefined && from !== cur && !el._anim) {
      el._anim = true;
      animatePiece(el, p.color, from, cur, ii, () => {
        el._anim = false;
        el.classList.remove("hop");
        setPiece(el, t.x, t.y, off, size);
      });
    } else if (!el._anim) {
      setPiece(el, t.x, t.y, off, size);
    }
  });

  Object.keys(pieceEls).forEach((k) => {
    if (!seen.has(k)) { pieceEls[k].remove(); delete pieceEls[k]; }
  });

  Object.keys(pieceEls).forEach((k) => {
    const el = pieceEls[k];
    const pi = Number(k.split("-")[0]);
    const base = "حجر " + COLOR_NAME_AR[state.players[pi].color];
    el.setAttribute("aria-label", selectableSet.has(k) ? base + " (قابل للاختيار)" : base);
    if (selectableSet.has(k)) el.classList.add("selectable");
    else el.classList.remove("selectable");
  });
}

function renderBoard(prev) {
  const board = $("board");
  let html = "";
  for (let i = 0; i < 225; i++) {
    const x = i % 15, y = Math.floor(i / 15);
    const info = CELL_TYPE_MAP[y][x];
    let cls = "cell";
    if (info.t === "base") cls += " base b-" + info.c;
    else if (info.t === "home") cls += " home h-" + info.c;
    else if (info.t === "start") cls += " start c-" + info.c;
    else if (info.t === "center") cls += " center";
    else if (info.t === "safe-star") cls += " safe-star";

    html += `<div class="${cls}"></div>`;
  }

  // المركز: مثلثات الأربعة + شارات الأحجار المكتملة
  let badges = "";
  state.players.forEach((p) => {
    const done = p.pieces.filter((v) => v === FINISH).length;
    if (done) badges += `<span class="done-badge pos-${p.color}">×${done}</span>`;
  });
  html += `<div class="center-tri">` +
    `<div class="tri" style="clip-path:polygon(0 0,0 100%,50% 50%);background:${COLOR_HEX.red}"></div>` +
    `<div class="tri" style="clip-path:polygon(0 0,100% 0,50% 50%);background:${COLOR_HEX.green}"></div>` +
    `<div class="tri" style="clip-path:polygon(100% 0,100% 100%,50% 50%);background:${COLOR_HEX.yellow}"></div>` +
    `<div class="tri" style="clip-path:polygon(0 100%,100% 100%,50% 50%);background:${COLOR_HEX.blue}"></div>` +
    `${badges}</div>`;

  board.innerHTML = html;
  board.appendChild(getPiecesLayer());
  board.className = "board" + (state.bombColor ? " bomb-" + state.bombColor : "");
  renderPieces(prev);
}

function renderSidebar() {
  const cur = state.players[state.current];
  const ph = state.phase;

  $("turn-box").innerHTML = `
    <div class="turn-head">
      <div class="who">
        <span class="dot" style="background:${COLOR_HEX[cur.color]}"></span>
        <b>دور: ${cur.name}</b>
      </div>
      <span class="badge">فرصة كرت الدور: ${Math.round(state.cardProb * 100)}%</span>
    </div>
    <p class="instruction">${instrText(ph)}</p>
    <div class="dice-row">
      ${diceFaceHtml(state.dice ?? 0)}
      <button id="roll-btn" class="btn" ${ph.k === "pre-roll" ? "" : "disabled"}>🎲 ارمِ النرد</button>
    </div>
    ${state.sixStreak > 0 ? `<p class="streak">سلسلة الستات: ${state.sixStreak} (ثلاث = ضياع الدور)</p>` : ""}`;

  const diceEl = document.querySelector(".dice");
  const shown = state.dice ?? 0;
  if (diceEl && lastDiceShown !== null && lastDiceShown !== shown) {
    diceEl.classList.add("rolled");
    setTimeout(() => diceEl.classList.remove("rolled"), 500);
  }
  lastDiceShown = shown;

  const usable = ph.k === "pre-roll";
  const cardsHtml = cur.cards.length === 0
    ? `<p class="muted">لا كروت بعد — أجب صحيحًا لتصلك الكروت!</p>`
    : cur.cards.map((c) =>
        `<button class="card-btn" data-card="${c}" ${usable ? "" : "disabled"} style="background:${CARD_INFO[c].color}">` +
        `${CARD_INFO[c].label}${usable ? " — استخدم الآن" : ""}</button>`).join("");
  $("cards-box").innerHTML = `<p class="box-title">كرتي (${cur.cards.length}/${MAX_CARDS})</p>${cardsHtml}`;

  $("players-box").innerHTML = `<p class="box-title">اللاعبون</p>` + state.players.map((p) => {
    const base = p.pieces.filter((v) => v === -1).length;
    const track = p.pieces.filter((v) => v >= 0 && v <= 50).length;
    const home = p.pieces.filter((v) => v >= 51 && v < 56).length;
    const done = p.pieces.filter((v) => v === 56).length;
    return `<div class="player-row${p.id === state.current ? " current" : ""}">` +
      `<div class="who"><span class="dot sm" style="background:${COLOR_HEX[p.color]}"></span>` +
      `<span class="pname">${p.name}</span></div>` +
      `<div class="counts">قاعدة ${base} • مسار ${track} • بيت ${home} • مركز ${done} • 🎴 ${p.cards.length}</div></div>`;
  }).join("");

  $("log-box").innerHTML = `<p class="box-title">سجل الأحداث</p><ul class="log">` +
    state.log.map((l, i) => `<li${i === 0 ? ' class="first"' : ""}>${l}</li>`).join("") + `</ul>`;
}

function cardVisualHtml(card, small) {
  const info = CARD_INFO[card];
  return `<div class="card-visual${small ? " small" : ""}" style="background:${info.color}">` +
    `<div class="big">${info.emoji}</div><div class="cname">${info.name}</div></div>`;
}

function renderModal() {
  const root = $("modal-root");
  const cur = state.players[state.current];
  const ph = state.phase;

  // ── نافذة السؤال (أول مرة) ──
  if (ph.k === "question") {
    root.innerHTML = `<div class="overlay"><div class="modal qmodal">
      <div class="q-top">
        <span class="q-player" style="background:${COLOR_HEX[cur.color]}">${cur.name}</span>
        ${state.timerOn ? `<span id="q-timer" class="timer"><i class="tbar"><b id="q-tbar"></b></i><b id="q-tnum">${CONFIG.TIMER_SECONDS}</b></span>` : ""}
      </div>
      <div class="q-badge"><span class="q-ico">؟</span><span>جاوب لتتحرك</span></div>
      <p class="q-text">${ph.qv.text}</p>
      <div class="q-grid">${ph.qv.options.map((op, i) =>
        `<button class="option-btn" data-idx="${i}"><span class="opt-key">${["أ", "ب", "ج", "د"][i] || (i + 1)}</span><span class="opt-txt">${op}</span></button>`).join("")}</div>
    </div></div>`;

    if (state.timerOn) {
      let left = CONFIG.TIMER_SECONDS;
      qInterval = setInterval(() => {
        left = Math.max(0, left - 1);
        const el = $("q-timer");
        if (el) {
          const num = $("q-tnum");
          if (num) num.textContent = left;
          const bar = $("q-tbar");
          if (bar) bar.style.width = (left / CONFIG.TIMER_SECONDS * 100) + "%";
          if (left <= 5) el.classList.add("urgent");
        }
        if (left === 0) { clearInterval(qInterval); qInterval = null; dispatch({ t: "answer", idx: -1 }); }
      }, 1000);
    }
    return;
  }

  // ── نافذة السؤال (نتيجة مكشوفة) ──
  if (ph.k === "answer-result" && lastQv) {
    const sel = lastSelected, corr = lastQv.correct;
    const bannerText = sel === corr ? "إجابة صحيحة! تتحرك الآن 🎉"
      : sel === -1 ? "انتهى الوقت! لن تتحرك هذا الدور"
      : "إجابة خاطئة! لن تتحرك هذا الدور";
    root.innerHTML = `<div class="overlay"><div class="modal qmodal">
      <div class="q-top">
        <span class="q-player" style="background:${COLOR_HEX[cur.color]}">${cur.name}</span>
      </div>
      <p class="q-text">${lastQv.text}</p>
      <div class="q-grid">${lastQv.options.map((op, i) => {
        let cls = "option-btn";
        if (i === corr) cls += " correct";
        else if (i === sel) cls += " wrong";
        else cls += " dim";
        return `<button class="${cls}" disabled><span class="opt-key">${["أ", "ب", "ج", "د"][i] || (i + 1)}</span><span class="opt-txt">${op}</span></button>`;
      }).join("")}</div>
      <div class="result-banner ${sel === corr ? "good" : "bad"}">${bannerText}</div>
    </div></div>`;
    return;
  }

  // ── نافذة عرض الكرت ──
  if (ph.k === "card-offer") {
    root.innerHTML = `<div class="overlay"><div class="modal narrow" style="text-align:center">
      <p class="muted-line">🎁 مكافأة الإجابة الصحيحة — كرت خاص!</p>
      ${cardVisualHtml(ph.card, false)}
      <p class="cdesc">${CARD_INFO[ph.card].desc}</p>
      <button class="btn wfull" data-act="take-card">خذ الكرت ✔</button>
    </div></div>`;
    return;
  }

  // ── نافذة الكرت الخامس: استبدال أو رفض ──
  if (ph.k === "fifth-choice") {
    root.innerHTML = `<div class="overlay"><div class="modal" style="text-align:center">
      <p class="strong">حيازتك ممتلئة (4 كروت)!</p>
      <p class="muted">جاء لك كرت خامس — استبدله بأحد كروتك أو ارفضه:</p>
      ${cardVisualHtml(ph.card, true)}
      <div id="fifth-main" style="display:flex;flex-direction:column;gap:.75rem">
        <button class="btn teal wfull" id="fifth-swap-open">🔄 استبدل بأحد كروتي</button>
        <button class="btn gray wfull" data-act="fifth-decline">✋ ارفض الكرت الجديد</button>
      </div>
      <div id="fifth-pick" class="hidden">
        <p style="font-weight:700;color:#404040;margin:0 0 .5rem">اختر الكرت الذي ستتخلى عنه:</p>
        <div class="fifth-list">${cur.cards.map((c, i) =>
          `<button class="discard-btn" data-act="fifth-swap" data-idx="${i}">
             <span>${CARD_INFO[c].emoji} ${CARD_INFO[c].name}</span><span class="small">استبدال</span>
           </button>`).join("")}</div>
        <button class="link-btn" id="fifth-back" style="margin-top:.75rem">رجوع</button>
      </div>
    </div></div>`;
    return;
  }

  // ── نافذة أرقام كرت الخطوات ──
  if (ph.k === "steps-number") {
    const legalByN = {};
    for (let n = 1; n <= 12; n++) legalByN[n] = legalStepsMoves(cur, n);
    root.innerHTML = `<div class="overlay"><div class="modal" style="text-align:center">
      <p class="strong">🎯 كرت تحديد الخطوات</p>
      <p class="muted" style="margin-bottom:1rem">اختر عدد الخطوات من 1 إلى 12 ثم اختر حجرًا:</p>
      <div class="num-grid">${Array.from({ length: 12 }, (_, i) => {
        const n = i + 1;
        const ok = (legalByN[n] || []).length > 0;
        return `<button class="num-btn" data-act="steps-number" data-n="${n}" ${ok ? "" : "disabled"}>${n}</button>`;
      }).join("")}</div>
      <button class="link-btn" data-act="back-to-preroll">إلغاء استخدام الكرت</button>
    </div></div>`;
    return;
  }

  // ── نافذة كرت القنبلة: اختر كلمة ──
  if (ph.k === "bomb-offer") {
    const word = ph.word || BOMB_WORDS[2];
    root.innerHTML = `<div class="overlay"><div class="modal narrow" style="text-align:center">
      <p class="strong">💣 كرت القنبلة</p>
      <p class="muted" style="margin-bottom:1rem">اختر كلمة — ومش شوية ألوان!</p>
      <div class="q-grid">${BOMB_WORDS.map((w) =>
        `<button class="option-btn" data-act="bomb-choice" data-word="${w.key}" style="font-weight:900;font-size:1.2rem">${w.label}</button>`
      ).join("")}</div>
    </div></div>`;
    return;
  }

  // ── نافذة انفجار القنبلة ──
  if (ph.k === "bomb-anim") {
    root.innerHTML = `<div class="overlay"><div class="modal narrow" style="text-align:center">
      <div class="win-emoji bomb-explode">💥</div>
      <p class="win-title" style="color:#FF6D00">انفجار!</p>
      <p class="win-name" style="color:#FF6D00">اللعبة انتهت — فوز ${cur.name}!</p>
    </div></div>`;
    setTimeout(() => dispatch({ t: "bomb-finish" }), 1000);
    return;
  }

  // ── نافذة نتيجة القنبلة ──
  if (ph.k === "bomb-result") {
    const eff = ph.effect;
    const isBomb = eff === "bomb";
    const isBlack = eff === "black";
    const color = isBomb ? "#FF6D00" : (isBlack ? "#111827" : (ph.color || "#E53935"));
    const title = isBomb ? "💥 قنبلة!" : (isBlack ? "🖤 أسود — انتهى الدور" : "🎨 غيّر اللون!");
    const sub = isBomb ? "انفجار! اللعبة انتهت." : (isBlack ? "لا تحرك — دورك انتهى" : `الخلايا الآن ${ph.word.label}`);
    root.innerHTML = `<div class="overlay"><div class="modal narrow" style="text-align:center">
      <div class="win-emoji">${isBomb ? "💥" : (isBlack ? "🖤" : "🎨")}</div>
      <p class="win-title" style="color:${color}">${title}</p>
      <p class="win-name" style="color:${color}">${sub}</p>
      ${isBomb ? `<button class="btn wfull" data-act="new-game">لعبة جديدة 🎲</button>` : `<button class="btn wfull" data-act="back-to-preroll">حسناً</button>`}
    </div></div>`;
    return;
  }

  // ── نافذة الفوز ──
  if (ph.k === "game-over") {
    const w = state.players[ph.winner];
    root.innerHTML = `<div class="overlay"><div class="modal narrow" style="text-align:center">
      <div class="win-emoji">🏆</div>
      <p class="win-title">مبروك! فاز</p>
      <p class="win-name" style="color:${COLOR_HEX[w.color]}">${w.name}</p>
      <button class="btn wfull" data-act="new-game">لعبة جديدة 🎲</button>
    </div></div>`;
    return;
  }

  root.innerHTML = "";
}

function renderSetup() {
  document.querySelectorAll("#count-seg button").forEach((b) => {
    b.classList.toggle("on", Number(b.dataset.n) === playerCount);
  });
  $("timer-toggle").className = "toggle" + (timerOn ? " on" : "");
  $("timer-toggle").setAttribute("aria-pressed", timerOn ? "true" : "false");
}

function render(prev) {
  clearInterval(qInterval);
  qInterval = null;
  const setupEl = $("setup-screen"), gameEl = $("game-screen");

  if (state.phase.k === "setup") {
    setupEl.classList.remove("hidden");
    gameEl.classList.add("hidden");
    $("new-game-btn").classList.add("hidden");
    $("modal-root").innerHTML = "";
    renderSetup();
    return;
  }

  setupEl.classList.add("hidden");
  gameEl.classList.remove("hidden");
  $("new-game-btn").classList.remove("hidden");

  const cur = state.players[state.current];
  const ph = state.phase;

  // القطع القابلة للاختيار حسب المرحلة
  selectableSet = new Set();
  {
    const c = state.current;
    if (ph.k === "select-piece" || ph.k === "steps-piece" || ph.k === "swap-own")
      ph.legal.forEach((i) => selectableSet.add(c + "-" + i));
    else if (ph.k === "swap-enemy" || ph.k === "back4-select")
      ph.legal.forEach((code) => selectableSet.add(Math.floor(code / 4) + "-" + (code % 4)));
  }

  renderBoard(prev);
  renderSidebar();
  renderModal();
}

/* ═══════════════ 6) الاستمرار التلقائي بعد عرض النتيجة ═══════════════ */

function scheduleAuto() {
  clearTimeout(autoTimer);
  const ph = state.phase;
  if (ph.k !== "answer-result") return;
  // نعرض نتيجة الإجابة مدة محددة ثم ننتقل تلقائيًا
  autoTimer = setTimeout(() => dispatch({ t: "answer-continue" }), CONFIG.RESULT_PAUSE);
}

/* ═══════════════ 7) ربط الأحداث والإقلاع ═══════════════ */

function init() {
  // شاشة الإعداد
  $("count-seg").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-n]");
    if (!b) return;
    playerCount = Number(b.dataset.n);
    renderSetup();
  });
  $("timer-toggle").addEventListener("click", () => { timerOn = !timerOn; renderSetup(); });
  $("start-btn").addEventListener("click", () => dispatch({ t: "start", count: playerCount, timerOn }));

  // شاشة اللعب
  $("new-game-btn").addEventListener("click", () => dispatch({ t: "new-game" }));
  $("turn-box").addEventListener("click", (e) => {
    const b = e.target.closest("#roll-btn");
    if (b && !b.disabled) dispatch({ t: "roll" });
  });
  $("cards-box").addEventListener("click", (e) => {
    const b = e.target.closest(".card-btn");
    if (b && !b.disabled) dispatch({ t: "play-card", card: b.dataset.card });
  });

  // الرقعة: اختيار الأحجار
  $("board").addEventListener("click", (e) => {
    const p = e.target.closest(".piece");
    if (!p || !p.classList.contains("selectable")) return;
    const player = Number(p.dataset.player), piece = Number(p.dataset.piece);
    const ph = state.phase;
    switch (ph.k) {
      case "select-piece": if (player === state.current) dispatch({ t: "select-piece", idx: piece }); break;
      case "steps-piece":  if (player === state.current) dispatch({ t: "steps-piece", idx: piece }); break;
      case "swap-own":     dispatch({ t: "swap-own", idx: piece }); break;
      case "swap-enemy":   dispatch({ t: "swap-enemy", player, piece }); break;
      case "back4-select": dispatch({ t: "back4", player, piece }); break;
    }
  });

  // النوافذ المنبثقة
  $("modal-root").addEventListener("click", (e) => {
    const t = e.target.closest("button");
    if (!t || t.disabled) return;
    const ph = state.phase;

    if (ph.k === "question") {
      if (t.classList.contains("option-btn")) dispatch({ t: "answer", idx: Number(t.dataset.idx) });
      return;
    }
    if (ph.k === "card-offer") {
      if (t.dataset.act === "take-card") dispatch({ t: "take-card" });
      return;
    }
    if (ph.k === "fifth-choice") {
      if (t.id === "fifth-swap-open") {
        $("fifth-main").classList.add("hidden");
        $("fifth-pick").classList.remove("hidden");
      } else if (t.id === "fifth-back") {
        $("fifth-pick").classList.add("hidden");
        $("fifth-main").classList.remove("hidden");
      } else if (t.dataset.act === "fifth-decline") {
        dispatch({ t: "fifth-decline" });
      } else if (t.dataset.act === "fifth-swap") {
        dispatch({ t: "fifth-swap", discardIdx: Number(t.dataset.idx) });
      }
      return;
    }
    if (ph.k === "steps-number") {
      if (t.dataset.act === "steps-number") dispatch({ t: "steps-number", n: Number(t.dataset.n) });
      else if (t.dataset.act === "back-to-preroll") dispatch({ t: "back-to-preroll" });
      return;
    }
    if (ph.k === "bomb-offer") {
      if (t.dataset.act === "bomb-choice") dispatch({ t: "bomb-choice", word: t.dataset.word });
      return;
    }
    if (ph.k === "bomb-result") {
      if (t.dataset.act === "new-game") dispatch({ t: "new-game" });
      else if (t.dataset.act === "back-to-preroll") dispatch({ t: "bomb-close" });
      return;
    }
    if (ph.k === "game-over") {
      if (t.dataset.act === "new-game") dispatch({ t: "new-game" });
      return;
    }
  });

  render();
}

document.addEventListener("DOMContentLoaded", init);
