// ألعاب أمين | Main JavaScript

// ============ MOBILE MENU ============
function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    if (!menu) return;
    const open = menu.classList.toggle('active');
    const btn = document.querySelector('.mobile-menu-btn');
    if (btn) {
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        btn.setAttribute('aria-label', open ? 'إغلاق القائمة' : 'فتح القائمة');
    }
}

function closeMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    if (!menu) return;
    menu.classList.remove('active');
    const btn = document.querySelector('.mobile-menu-btn');
    if (btn) {
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-label', 'فتح القائمة');
    }
}

// ============ TOAST NOTIFICATIONS ============
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ============ الوضع الفاتح / الداكن ============
// يُحفظ الاختيار في localStorage، ويُتزامن معه زرّا الشريط والقائمة الجوالة.
var ThemeCtl = (function () {
    var KEY = 'ameen_theme';

    function current() {
        return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    }

    // يحدّث الأيقونة والنص لكل أزرار التبديل الموجودة في الصفحة
    function sync(theme) {
        var light = theme === 'light';
        var label = light ? 'التبديل إلى الوضع الداكن' : 'التبديل إلى الوضع الفاتح';
        document.querySelectorAll('.theme-btn').forEach(function (btn) {
            btn.setAttribute('aria-pressed', light ? 'true' : 'false');
            btn.setAttribute('aria-label', label);
            btn.title = light ? 'الوضع الداكن' : 'الوضع الفاتح';
            var use = btn.querySelector('use');
            if (use) use.setAttribute('href', light ? '#i-sun' : '#i-moon');
            var txt = btn.querySelector('span');
            if (txt) txt.textContent = light ? 'الوضع الليلي' : 'الوضع النهاري';
        });
        // لون شريط المتصفح في الجوال يتبع السطح لا قيمة ثابتة
        var tc = document.querySelector('meta[name="theme-color"]');
        if (tc) tc.setAttribute('content', light ? '#f4f6fc' : '#0a0c1a');
    }

    function apply(theme, persist) {
        document.documentElement.setAttribute('data-theme', theme);
        var cs = document.querySelector('meta[name="color-scheme"]');
        if (cs) cs.setAttribute('content', theme);
        if (persist) { try { localStorage.setItem(KEY, theme); } catch (e) {} }
        sync(theme);
    }

    function init() {
        document.querySelectorAll('.theme-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                apply(current() === 'light' ? 'dark' : 'light', true);
            });
        });
        sync(current());

        // نتبع نظام الجهاز فقط إذا لم يختر المستخدم وضعًا بنفسه
        try {
            var mq = window.matchMedia('(prefers-color-scheme: light)');
            var onChange = function (e) {
                if (localStorage.getItem(KEY)) return;
                apply(e.matches ? 'light' : 'dark', false);
            };
            if (mq.addEventListener) mq.addEventListener('change', onChange);
            else if (mq.addListener) mq.addListener(onChange);
        } catch (e) {}
    }

    return { init: init, current: current, apply: apply };
})();

// ============ MODAL ============
let _lastFocused = null;

// ============ جسر وضع البطولة ============
// تستدعيه اللعبة الحقيقية (س.ج / حروف / ارسم) عند انتهاء مباراتها لتُبلغ
// صفحة البطولة بالنتيجة، فتتقدم الشجرة من نفسها. يعمل فقط داخل إطار.
window.AmeenTournament = {
    _send: function (payload) {
        try {
            if (window.parent && window.parent !== window) {
                window.parent.postMessage(payload, '*');
            }
        } catch (e) {
            console.warn('[tournament] تعذّر إرسال الرسالة', e);
        }
        return payload;
    },
    // اللعبة جاهزة للّعب فعليًا (اللوحة رُسمت) — عندها فقط يُخفى مكان التحميل
    ready: function () {
        return this._send({ ameenTournament: true, ready: true });
    },
    report: function (winnerIndex, scoreA, scoreB, detail) {
        return this._send({
            ameenTournament: true,
            winner: winnerIndex,      // 0 = الفريق الأول، 1 = الثاني، null = تعادل
            scoreA: scoreA || 0,
            scoreB: scoreB || 0,
            detail: detail || ''
        });
    }
};

function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    _lastFocused = document.activeElement;
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    const focusable = modal.querySelector('input, select, textarea, button, [tabindex]:not([tabindex="-1"])');
    if (focusable) setTimeout(() => focusable.focus(), 30);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    if (_lastFocused && _lastFocused.focus) _lastFocused.focus();
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay.active').forEach(m => closeModal(m.id));
}

// ============ TIMER CLASS ============
class GameTimer {
    constructor(duration, onTick, onEnd) {
        this.duration = duration;
        this.remaining = duration;
        this.onTick = onTick;
        this.onEnd = onEnd;
        this.interval = null;
        this.endTime = null;
    }
    
    start() {
        this.endTime = Date.now() + this.remaining * 1000;
        this.interval = setInterval(() => {
            this.remaining = Math.max(0, Math.floor((this.endTime - Date.now()) / 1000));
            if (this.onTick) this.onTick(this.remaining);
            if (this.remaining <= 0) {
                this.stop();
                if (this.onEnd) this.onEnd();
            }
        }, 100);
    }
    
    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }
    
    reset() {
        this.stop();
        this.remaining = this.duration;
    }
}

// ============ SOUND EFFECTS ============
const SoundManager = {
    enabled: true,
    sounds: {
        correct: null,
        wrong: null,
        buzzer: null,
        win: null,
        bid: null,
    },
    
    init() {
        // Create audio context
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    },
    
    play(type) {
        if (!this.enabled || !this.ctx) return;
        
        const oscillator = this.ctx.createOscillator();
        const gainNode = this.ctx.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.ctx.destination);
        
        switch(type) {
            case 'correct':
                oscillator.frequency.value = 800;
                gainNode.gain.value = 0.3;
                oscillator.start();
                oscillator.stop(this.ctx.currentTime + 0.2);
                break;
            case 'wrong':
                oscillator.frequency.value = 200;
                gainNode.gain.value = 0.3;
                oscillator.start();
                oscillator.stop(this.ctx.currentTime + 0.3);
                break;
            case 'buzzer':
                oscillator.frequency.value = 1000;
                gainNode.gain.value = 0.5;
                oscillator.start();
                oscillator.stop(this.ctx.currentTime + 0.5);
                break;
            case 'win':
                // Play a victory arpeggio
                [523, 659, 784, 1047].forEach((freq, i) => {
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    osc.connect(gain);
                    gain.connect(this.ctx.destination);
                    osc.frequency.value = freq;
                    gain.gain.value = 0.3;
                    osc.start(this.ctx.currentTime + i * 0.15);
                    osc.stop(this.ctx.currentTime + i * 0.15 + 0.3);
                });
                break;
            case 'bid':
                oscillator.frequency.value = 600;
                gainNode.gain.value = 0.2;
                oscillator.start();
                oscillator.stop(this.ctx.currentTime + 0.1);
                break;
        }
    },
    
    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
};

// ============ ARABIC TEXT NORMALIZATION ============
function normalizeArabic(text) {
    if (!text) return '';
    return text
        .replace(/[أإآ]/g, 'ا')
        .replace(/ة/g, 'ه')
        .replace(/ى/g, 'ي')
        .replace(/ؤ/g, 'و')
        .replace(/ئ/g, 'ي')
        .replace(/\s+/g, ' ')
        .trim();
}

function getFirstLetter(text) {
    const normalized = normalizeArabic(text);
    if (!normalized) return '';
    const firstChar = normalized.charAt(0);
    // Skip "ال" prefix
    if (normalized.startsWith('ال') && normalized.length > 2) {
        return normalized.charAt(2);
    }
    return firstChar;
}

// ============ LOCAL STORAGE HELPERS ============
function saveGameState(key, state) {
    try {
        localStorage.setItem(`ameen_games_${key}`, JSON.stringify(state));
    } catch (e) {
        console.error('Failed to save game state:', e);
    }
}

function loadGameState(key) {
    try {
        const data = localStorage.getItem(`ameen_games_${key}`);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        return null;
    }
}

function clearGameState(key) {
    localStorage.removeItem(`ameen_games_${key}`);
}

// ============ API HELPERS ============
async function apiGet(url) {
    const res = await fetch(url);
    return res.json();
}

async function apiPost(url, data) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function apiPut(url, data) {
    const res = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function apiDelete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    return res.json();
}

// ============ SCROLL REVEAL ============
function initReveal() {
    const targets = document.querySelectorAll('.reveal, .reveal-stagger');
    if (!targets.length) return;

    const revealAll = () => targets.forEach(t => t.classList.add('in'));

    // No IntersectionObserver (old browser): show everything at once.
    if (!('IntersectionObserver' in window)) {
        revealAll();
        return;
    }

    const io = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('in');
                io.unobserve(e.target);
            }
        });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    targets.forEach(t => io.observe(t));

    // Safety nets: content must never be able to stay invisible.
    // 1) on load, reveal anything already on screen
    window.addEventListener('load', () => {
        const vh = window.innerHeight;
        targets.forEach(t => {
            if (t.getBoundingClientRect().top < vh) t.classList.add('in');
        });
    });
    // 2) catch-up pass: reveal whatever is currently on screen (2s), then
    //    guarantee everything is visible (8s) so nothing can get stuck hidden.
    setTimeout(() => {
        const vh = window.innerHeight;
        targets.forEach(t => {
            if (t.getBoundingClientRect().top < vh * 1.2) t.classList.add('in');
        });
    }, 2000);
    setTimeout(revealAll, 8000);
}

// ============ BACK TO TOP ============
function initToTop() {
    const btn = document.getElementById('toTop');
    if (!btn) return;
    const onScroll = () => btn.classList.toggle('show', window.scrollY > 420);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ============ INIT ============
document.addEventListener('DOMContentLoaded', () => {
    // Initialize sound manager on first interaction
    document.addEventListener('click', () => {
        if (!SoundManager.ctx) {
            SoundManager.init();
        }
    }, { once: true });

    // Close modals on overlay click + Escape
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
                overlay.setAttribute('aria-hidden', 'true');
            }
        });
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
            closeMobileMenu();
        }
    });

    // Mobile menu: close after choosing a destination
    const mobileMenu = document.getElementById('mobileMenu');
    if (mobileMenu) {
        mobileMenu.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', () => {
                if (!a.target || a.target === '_self') closeMobileMenu();
            });
        });
    }

    initReveal();
    initToTop();
    ThemeCtl.init();
});

/* =====================================================================
   تكبير/تصغير الرقعة — ينطبق على كل الصفحات والألعاب.
    Ctrl + / Ctrl - / Ctrl 0 هي اختصارات لوحة المفاتيح.
   ===================================================================== */
var ZoomCtl = (function () {
    var KEY = "ameen_zoom";
    var MIN = 70, MAX = 150, STEP = 10, DEF = 100;

    function read() {
        var v = parseInt(localStorage.getItem(KEY) || "", 10);
        if (isNaN(v) || v < MIN || v > MAX) v = DEF;
        return v;
    }
    function paint(v) {
        var label = document.getElementById("zoomVal");
        if (label) label.textContent = v + "%";
    }
    function apply(v) {
        document.documentElement.style.zoom = (v / 100);
        paint(v);
        try { localStorage.setItem(KEY, String(v)); } catch (e) {}
    }
    function set(v) {
        v = Math.max(MIN, Math.min(MAX, Math.round(v / STEP) * STEP));
        if (v === DEF) {
            document.documentElement.style.zoom = "";
            paint(DEF);
            try { localStorage.removeItem(KEY); } catch (e) {}
            return;
        }
        apply(v);
    }
    function init() {
        set(read());
        var inBtn = document.getElementById("zoomIn");
        var outBtn = document.getElementById("zoomOut");
        var resetBtn = document.getElementById("zoomReset");
        if (inBtn) inBtn.addEventListener("click", function () { set(read() + STEP); });
        if (outBtn) outBtn.addEventListener("click", function () { set(read() - STEP); });
        if (resetBtn) resetBtn.addEventListener("click", function () { set(DEF); });
        document.addEventListener("keydown", function (e) {
            if (!e.ctrlKey) return;
            if (e.key === "=" || e.key === "+") { e.preventDefault(); set(read() + STEP); }
            else if (e.key === "-") { e.preventDefault(); set(read() - STEP); }
            else if (e.key === "0") { e.preventDefault(); set(DEF); }
        });
    }
    return { init: init, set: set, get: read };
})();

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ZoomCtl.init);
} else {
    ZoomCtl.init();
}
