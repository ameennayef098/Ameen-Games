/* ==========================================================================
   ألعاب أمين | UI KIT — shared components (vanilla JS, no dependencies)
   Exposed on window.UI:
     UI.el(tag, cls, html)                 element helper
     UI.esc(str)                           HTML escape
     UI.enhanceSettings(root, opts)        shared settings-panel skin
     UI.renderCategoryPicker(root, opts)   grouped category catalogue grid
     UI.modal(opts)                        promise-based modal
   ========================================================================== */
(function (global) {
    'use strict';

    var UI = {};

    /* ---------------------------------------------------------------- utils */
    UI.el = function (tag, cls, html) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (html != null) n.innerHTML = html;
        return n;
    };

    UI.esc = function (s) {
        return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
    };

    UI.fmtTime = function (sec) {
        sec = Math.max(0, Math.round(sec || 0));
        if (sec < 60) return sec + ' ثانية';
        var m = Math.floor(sec / 60), s = sec % 60;
        if (m < 60) return m + ' دقيقة' + (s ? ' و ' + s + ' ثانية' : '');
        return Math.floor(m / 60) + ' ساعة و ' + (m % 60) + ' دقيقة';
    };

    /* ------------------------------------------------- settings panel skin */
    /* Re-lays-out an existing setup container without touching the game's own
       inputs or ids: an optional header, a responsive field grid, an actions
       row. Anything the game already renders (its own headings, its own
       category picker) is kept in place. */
    UI.enhanceSettings = function (root, opts) {
        opts = opts || {};
        if (!root) return root;
        root.classList.add('gsp');

        var hasHeading = root.querySelector(':scope > h1, :scope > h2, :scope > h3, :scope > h4');
        if (!hasHeading && !root.querySelector(':scope > .gsp-head')) {
            var head = UI.el('div', 'gsp-head');
            head.appendChild(UI.el('h3', null, UI.esc(opts.icon || '⚙️') + ' ' + UI.esc(opts.title || 'الإعدادات')));
            if (opts.sub) head.appendChild(UI.el('span', 'gsp-sub', UI.esc(opts.sub)));
            root.insertBefore(head, root.firstChild);
        }

        var gridKids = [], actionKids = [];
        Array.prototype.slice.call(root.children).forEach(function (n) {
            if (n.classList.contains('gsp-head') || n.classList.contains('gsp-body')
                || n.classList.contains('gsp-actions')) return;
            // the game's own title stays a direct child, above the field grid
            if (/^H[1-6]$/.test(n.tagName)) return;
            var isActions = n.classList.contains('setup-actions') || n.classList.contains('gsp-actions');
            if (!isActions && n.tagName === 'BUTTON') isActions = true;
            if (!isActions && n.tagName === 'DIV' && n.children.length
                && Array.prototype.every.call(n.children, function (c) { return c.tagName === 'BUTTON'; })) {
                isActions = true;
            }
            (isActions ? actionKids : gridKids).push(n);
        });

        if (gridKids.length) {
            var body = UI.el('div', 'gsp-body');
            var grid = UI.el('div', 'gsp-grid');
            gridKids.forEach(function (n) { grid.appendChild(n); });
            body.appendChild(grid);
            root.insertBefore(body, actionKids[0] || null);
        }

        if (actionKids.length) {
            var acts = UI.el('div', 'gsp-actions');
            actionKids.forEach(function (n) {
                if (n.classList.contains('setup-actions')) {
                    Array.prototype.slice.call(n.children).forEach(function (c) { acts.appendChild(c); });
                } else {
                    acts.appendChild(n);
                }
            });
            root.appendChild(acts);
        }
        return root;
    };

    /* Applies the shared skin to whichever setup screen this page has. Games
       keep their own markup; this only normalises the chrome around it. */
    var SETUP_BY_PATH = {
        '/game/letters': ['letters-setup', { icon: '🔤', title: 'إعداد المباراة', sub: 'فريقان على نفس الجهاز' }],
        '/game/quiz': ['quiz-setup', { icon: '❓', title: 'إعداد المباراة', sub: 'اختر الفئات والنقاط' }],
        '/game/auction': ['auction-setup', { icon: '💰', title: 'إعداد المزاد', sub: 'الميزانية والمشاركون' }],
        '/game/million': ['mil-setup', { icon: '💵', title: 'إعداد المباراة', sub: 'الصعوبة والوقت' }],
        '/game/lastone': ['setup', { icon: '🏆', title: 'إعداد المباراة', sub: 'التصنيف والجولات' }],
        '/game/whoplayer': ['setup', { icon: '⚽', title: 'إعداد المباراة', sub: 'الصعوبة وعدد الجولات' }],
        '/game/link': ['setup', { icon: '🔗', title: 'إعداد المباراة', sub: 'الصعوبة والجولات' }],
        '/game/spy': ['spyStep2', { icon: '👥', title: 'إعداد اللاعبين', sub: 'الموضوع يُختار عشوائياً عند البدء' }],
        '/game/detective': ['detSettings', { icon: '🔍', title: 'إعدادات اللعبة', sub: 'الصعوبة والمؤقت' }],
        '/game/culprit': ['culpSettings', { icon: '⚖️', title: 'إعدادات اللعبة', sub: 'وضع الفرق' }]
    };

    UI.autoEnhanceSettings = function () {
        var conf = SETUP_BY_PATH[location.pathname];
        if (!conf) return;
        var root = document.getElementById(conf[0]);
        if (root) UI.enhanceSettings(root, conf[1]);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', UI.autoEnhanceSettings);
    } else {
        UI.autoEnhanceSettings();
    }

    /* ---------------------------------------------------- category picker */
    /* Renders the categories as a catalogue: a coloured pill per classification
       and a card per category, exactly like a printed category catalogue. */
    UI.renderCategoryPicker = function (root, opts) {
        opts = opts || {};
        if (!root) return;
        var cats = (opts.categories || []).slice();
        if (opts.filter) cats = cats.filter(opts.filter);

        var selected = {};
        (opts.selected || []).forEach(function (id) { selected[id] = true; });

        var groups = [];
        cats.forEach(function (c) {
            var name = (c.group || '').trim() || 'عام';
            var g = null;
            for (var i = 0; i < groups.length; i++) if (groups[i].name === name) { g = groups[i]; break; }
            if (!g) {
                g = { name: name, color: c.group_color || '#4f8cff', icon: c.group_icon || '🗂️', cats: [] };
                groups.push(g);
            }
            g.cats.push(c);
        });

        root.classList.add('catpick');
        root.innerHTML = '';

        var search = UI.el('input');
        search.type = 'text';
        search.placeholder = opts.searchPlaceholder || 'ابحث باسم الفئة...';
        search.setAttribute('aria-label', opts.searchPlaceholder || 'ابحث باسم الفئة');
        var top = UI.el('div', 'cp-search');
        top.appendChild(search);
        if (opts.random) {
            var randBtn = UI.el('button', 'btn btn-gold btn-sm', '🎲 ' + UI.esc(opts.randomLabel || 'فئات عشوائية'));
            randBtn.type = 'button';
            randBtn.onclick = function () {
                var pool = cats.slice();
                for (var i = pool.length - 1; i > 0; i--) {
                    var j = Math.floor(Math.random() * (i + 1));
                    var t = pool[i]; pool[i] = pool[j]; pool[j] = t;
                }
                var n = Math.max(1, Math.min(parseInt(opts.randomCount || 3, 10), pool.length));
                var picked = pool.slice(0, n).map(function (c) { return c.id; });
                if (opts.onRandom) opts.onRandom(picked);
                else { root.dispatchEvent(new CustomEvent('cp:random', { detail: picked })); }
            };
            top.appendChild(randBtn);
        }
        root.appendChild(top);

        var list = UI.el('div');
        root.appendChild(list);

        function draw(text) {
            list.innerHTML = '';
            var shown = 0;
            groups.forEach(function (g) {
                var items = g.cats.filter(function (c) {
                    return !text || String(c.name).indexOf(text) > -1;
                });
                if (!items.length) return;
                shown += items.length;
                var sec = UI.el('div', 'cp-group');
                var head = UI.el('div', 'cp-group-head');
                var pill = UI.el('span', 'cp-group-pill', UI.esc(g.icon) + ' ' + UI.esc(g.name));
                pill.style.background = g.color;
                head.appendChild(pill);
                head.appendChild(UI.el('span', 'cp-group-count', items.length + ' فئة'));
                sec.appendChild(head);

                var grid = UI.el('div', 'cp-grid');
                items.forEach(function (c) {
                    var card = UI.el('div', 'cp-card' + (selected[c.id] ? ' sel' : ''));
                    card.dataset.id = c.id;
                    card.title = c.description || c.name;
                    card.appendChild(UI.el('span', 'cp-info', 'i'));
                    card.appendChild(UI.el('span', 'cp-ico', c.icon || '📚'));
                    card.appendChild(UI.el('span', 'cp-name', UI.esc(c.name)));
                    var n = (c.approved_count != null) ? c.approved_count : c.question_count;
                    if (opts.showCount && n != null) {
                        card.appendChild(UI.el('span', 'cp-n', n + ' سؤال'));
                    }
                    card.onclick = function () {
                        if (opts.multi) {
                            selected[c.id] = !selected[c.id];
                            card.classList.toggle('sel', !!selected[c.id]);
                        } else {
                            Object.keys(selected).forEach(function (k) { delete selected[k]; });
                            selected[c.id] = true;
                            Array.prototype.forEach.call(list.querySelectorAll('.cp-card'), function (x) {
                                x.classList.remove('sel');
                            });
                            card.classList.add('sel');
                        }
                        if (opts.onPick) opts.onPick(c, card);
                    };
                    grid.appendChild(card);
                });
                sec.appendChild(grid);
                list.appendChild(sec);
            });
            if (!shown) list.appendChild(UI.el('div', 'cp-empty', 'لا توجد فئات مطابقة'));
        }

        var timer = null;
        search.oninput = function () {
            clearTimeout(timer);
            timer = setTimeout(function () { draw(search.value.trim()); }, 140);
        };
        draw('');
        UI._cpRedraw = draw;
        return { redraw: draw, getSelected: function () { return Object.keys(selected).map(function (k) { return k; }); } };
    };

    /* ------------------------------------------------------------- modal */
    /* UI.modal({title, tag, body, buttons:[{label, class, value, block}]})
       Resolves with the clicked value, or null when dismissed. */
    UI.modal = function (opts) {
        opts = opts || {};
        return new Promise(function (resolve) {
            var overlay = UI.el('div', 'qmodal-overlay');
            var box = UI.el('div', 'qmodal');
            var head = UI.el('div', 'qmodal-head');
            head.appendChild(UI.el('h3', null, UI.esc(opts.title || '')));
            if (opts.tag) head.appendChild(UI.el('span', 'qmodal-tag', UI.esc(opts.tag)));
            box.appendChild(head);

            var body = UI.el('div', 'qmodal-body');
            if (typeof opts.body === 'string') body.innerHTML = opts.body;
            else if (opts.body) body.appendChild(opts.body);
            box.appendChild(body);

            var btns = UI.el('div', 'qmodal-btns');
            var done = function (val) {
                if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
                resolve(val);
            };
            (opts.buttons || []).forEach(function (b) {
                var btn = UI.el('button', 'btn ' + (b.class || 'btn-secondary'), UI.esc(b.label));
                btn.type = 'button';
                if (b.block) btn.className += ' btn-block';
                btn.onclick = function () { done(b.value); };
                btns.appendChild(btn);
            });
            if (btns.children.length) box.appendChild(btns);

            overlay.appendChild(box);
            overlay.onclick = function (e) { if (e.target === overlay) done(null); };
            document.addEventListener('keydown', function onKey(e) {
                if (e.key === 'Escape') { document.removeEventListener('keydown', onKey); done(null); }
            });
            document.body.appendChild(overlay);
        });
    };

    global.UI = UI;
})(window);
