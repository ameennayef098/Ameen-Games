#!/usr/bin/env python3
"""ألعاب أمين | AMEEN GAMES - Main Server"""
import os, json, uuid, re, tempfile, hashlib, time, csv, io
import random as _rnd
import qimport as qi
from datetime import datetime
from flask import (Flask, render_template, request, jsonify, send_from_directory,
                   send_file, redirect, make_response)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE_DIR, 'data')
SETTINGS_FILE = os.path.join(DATA, 'settings.json')


def load_env():
    """Load .env so the API key never lives inside the code."""
    path = os.path.join(BASE_DIR, '.env')
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass


load_env()
Q_FILE = os.path.join(DATA, 'questions', 'all.json')
PENDING_FILE = os.path.join(DATA, 'questions', 'pending.json')
CAT_FILE = os.path.join(DATA, 'categories', 'categories.json')
PL_FILE = os.path.join(DATA, 'players', 'players.json')
UPLOAD_DIR = os.path.join(DATA, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
REPORTS_DIR = os.path.join(DATA, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

ALLOWED_IMG = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}
MAX_IMG_BYTES = 4 * 1024 * 1024

AR_LETTERS = ['أ','ب','ت','ث','ج','ح','خ','د','ذ','ر','ز','س','ش','ص','ض','ط','ظ','ع','غ','ف','ق','ك','ل','م','ن','ه','و','ي']


def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        last = None
        for attempt in range(15):
            try:
                os.replace(tmp, path)
                break
            except OSError as e:
                last = e
                if attempt == 14:
                    raise
                time.sleep(0.4)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def gen_id():
    return uuid.uuid4().hex[:8]


# ============ مخبأ بنك الأسئلة ============
# البنك 14,895 سطرًا، وقراءته وتحليله تكلف ~2.5 ثانية. كان كل طلب يعيد قراءته،
# وبعض المسارات (حروف) كانت تعيد قراءته لكل حرف = 28 قراءة = ~29 ثانية.
# المفتاح (mtime, size) لأن تغيير المحتوى يغيّرهما معًا، فأي كتابة تبطل المخبأ.
_BANK_CACHE = {'key': None, 'data': None}


def load_bank():
    # بنك الأسئلة من الذاكرة عند عدم تغيّر الملف — بدل إعادة تحليله كل طلب.
    try:
        st = os.stat(Q_FILE)
        key = (int(st.st_mtime), st.st_size)
    except OSError:
        _BANK_CACHE['key'] = None
        _BANK_CACHE['data'] = None
        return []
    if _BANK_CACHE['key'] != key or _BANK_CACHE['data'] is None:
        _BANK_CACHE['data'] = load_json(Q_FILE, [])
        _BANK_CACHE['key'] = key
    return _BANK_CACHE['data']


# فهرس الحروف وخريطة id يشتقان من البنك فقط، فهما يُخزَّنان على نفس
# مفتاح البنك — بدونهما كانت كل استدعاءات الحروف تعيد بناءهما من 14,895 سطر.
_LETTERS_CACHE = {'key': None, 'idx': None}
_BYID_CACHE = {'key': None, 'm': None}


def _bank_by_id():
    # خريطة id ← سؤال؛ تُبنى مرة واحدة لكل نسخة من البنك.
    key = _BANK_CACHE['key']
    if _BYID_CACHE['key'] == key and _BYID_CACHE['m'] is not None:
        return _BYID_CACHE['m']
    m = {q.get('id'): q for q in load_bank() if q.get('id')}
    _BYID_CACHE['m'] = m
    _BYID_CACHE['key'] = key
    return m


def now():
    return datetime.now().isoformat(timespec='seconds')


def norm_ar(t):
    if not t:
        return ''
    t = str(t)
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    t = re.sub(r'[أإآٱ]', 'ا', t)
    t = t.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    t = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def q_key(q):
    """Duplicates are per-game: the same wording may legitimately exist in two games."""
    return str(q.get('game', '')) + '|' + norm_ar(q.get('question', ''))


# ============ حروف مع أمين / شطب الحروف — شكل موحّد للحرف ============
# لا نوحّد الهمزة هنا إلى «أ»: حروف مع أمين يستخدم «أ» على اللوحة بينما س.ج
# يخزّن الإجابة بصيغتها الأصلية، فالتوحيد إلى «ا» يكسر مطابقة الحروف في س.ج.
# الشكل الموحّد للمقارنة: همزة فوق نقيّة (0623) أو همزة على نبرة (0625) أو
# همزة ممدودة (0622) أو ألف (0627) ← «أ»، وتاء مربوطة (0629) ← «ه».
# تعمدنا عدم طيّ الألف المقصورة والياء والتاء المفتوحة حتى لا تندمج لوحة
# الـ28 خلية إلى 24: اللوحة تُبنى في الواجهة من هذه المصفوفة مباشرة.
L_CANON = {
    '\u0623': '\u0627',   # أ
    '\u0624': '\u0628',   # ؤ
    '\u0625': '\u0623',   # إ
    '\u0626': '\u062a',   # ئ
    '\u0622': '\u0623',   # آ
    '\u0627': '\u0623',   # ا
    '\u0649': '\u064a',   # ى
    '\u0629': '\u0647',   # ة
}


def letter_canon(ch):
    """الشكل الموحّد للحرف العربي الواحد (يُستخدم في مطابقة الحروف)."""
    return L_CANON.get(str(ch or ''), ch)


def canon_letter_match(v):
    """يعيد حرف اللوحة الموحّد: «أ» لكل أشكال الألف، و«ه» للتاء المربوطة.

    يُقارَن ناتج هذه الدالة بـ AR_LETTERS (لوحتا حروف مع أمين وشطب الحروف)،
    لذلك يجب أن يطابق شكل اللوحة حرفيًّا — «أ» وليس «ا».
    """
    a = re.sub('[\u064B-\u0652\u0670\u0640]', '', str(v or '').strip())
    if not a:
        return ''
    a = re.sub('[\u0623\u0625\u0622\u0671]', '\u0627', a)   # طيّ الألف
    c = a[0]
    if c == '\u0627':
        return '\u0623'                       # كل أشكال الألف ← «أ»
    if c == '\u0629':
        return '\u0647'                       # تاء مربوطة ← «ه»
    return c


def letter_of(answer):
    """أول حرف من الإجابة بعد تجاهل «ال» التعريف، بنفس أشكال canon_letter_match.

    أمثلة: «الفواكه» ← «ف»، «أبو بكر» ← «أ»، «ألكسندر» ← «ك»، «الهرم» ← «ه».
    هذه النسخة هي مرجع اللعبتين الجديدتين؛ نسخة حروف مع أمين أقدم وتُترك كما هي.
    """
    a = re.sub('[\u064B-\u0652\u0670\u0640]', '', str(answer or '').strip())
    if not a:
        return ''
    a = re.sub('[\u0623\u0625\u0622\u0671]', '\u0627', a)   # 1. طيّ الألف
    if a.startswith('\u0627\u0644') and len(a) > 2:
        a = a[2:]                                                # 2. إسقاط أل التعريف
    if not a:
        return ''
    return 'أ' if a[0] == 'ا' else a[0]              # 3. حرف اللوحة الموحّد


# Anything outside Arabic letters / digits / basic punctuation means the model
# leaked another language (seen in practice: Korean "미터", Cyrillic).
# Latin is NOT treated as a leak: Arabic textbooks legitimately carry chemical
# element symbols (Fe, Au), blood groups (O, AB) and tech acronyms (HTTP, JS).
FOREIGN_CHARS = re.compile(
    r'[\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF\u0E00-\u0E7F\u0590-\u05FF]')

ALLOWED_LATIN = set(x.upper() for x in """
H HE LI BE B C N O F NE NA MG AL SI P S CL AR K CA SC TI V CR MN FE CO NI CU ZN
GA GE AS SE BR KR RB SR Y ZR NB MO TC RU RH PD AG CD IN SN SB TE I XE CS BA LA
CE PR ND PM SM EU GD TB DY HO ER TM YB LU HF TA W RE OS IR PT AU HG TL PB BI PO
AT RN FR RA AC TH PA U NP PU AM CM BK CF ES FM MD NO LR RF DB SG BH HS MT DS RG
CN NH FL MC LV TS OG
HCL NACL H2O CO2 NO2 SO2 O2 N2 H2 NH3 CH4 NAOH H2SO4 KOH CAO MGO SIO2 AL2O3
FE2O3 FE3O4 HNO3 H2CO3 KMNO4 K2CR2O7 CACO3 NANO3 CUSO4 ZNSO4 MGCL2 HBR HI HF
ATP ADP AMP DNA RNA PCR HIV AIDS HPV TB BCG MRI CT ECG EEG EMG ICU ER OR BP BMI GMO
JS TS HTML CSS HTTP HTTPS API CPU GPU RAM ROM USB AI ML IT TV PC GPS URL URI SQL
PHP XML JSON YAML VPN DNS IP TCP UDP FTP SSH SSL TLS WIFI LAN WAN OS UI UX IDE SDK
CEO CFO NASA ESA ISRO FBI CIA USA UK EU UN WHO IMF GDP GNP ATM PIN SMS
CD DVD MP3 MP4 PDF JPG PNG GIF SVG CSV XLS DOC PPT IoT VR AR
X Y Z T M J W Q V
HZ KHZ MHZ GHZ PH DB DBM
""" .split())


def collect_text(obj, skip_keys=None):
    """Join every *string value* found in a nested content item.

    Serialising the item to JSON and scanning that is wrong twice over: the
    Arabic field names become Latin tokens ("name", "category") and the
    structural enums ("medium", "pending_review") are Latin by design. Both made
    the foreign-script guard reject perfectly good Arabic content.
    """
    skip_keys = skip_keys or set()
    parts = []

    def walk(node, key=None):
        if key in skip_keys:
            return
        if isinstance(node, str):
            parts.append(node)
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v, key)

    walk(obj)
    return ' '.join(parts)


def has_foreign(text):
    """True when the text holds a non-Arabic script we cannot justify.

    A whole Latin *word* such as "material" or "meter" is a model leak and is
    rejected; chemical symbols, blood groups and tech acronyms are allowed.
    """
    t = str(text or '')
    if FOREIGN_CHARS.search(t):
        return True
    for tok in re.findall(r'[A-Za-z]+', t):
        if tok.upper() not in ALLOWED_LATIN:
            return True
    return False


def is_arabic_answer(text):
    """The answer itself must be Arabic letters/spaces only."""
    t = str(text or '').strip()
    if not t:
        return False
    return not has_foreign(t)


def first_letter_of(answer):
    """أول حرف من الإجابة بعد تجاهل «ال» التعريف وتوحيد الألف.

    أمثلة: «الفواكه» ← «ف»، «أبو بكر» ← «أ»، «ألكسندر» ← «ك»، «الهرم» ← «ه».
    """
    a = re.sub('[ً-ْٰـ]', '', str(answer or '').strip())
    if not a:
        return ''
    a = re.sub('[أإآٱ]', 'ا', a)
    if a.startswith('ال') and len(a) > 2:
        a = a[2:]
    if not a:
        return ''
    return 'أ' if a[0] == 'ا' else a[:1]


def canon_letter(v):
    """توحيد شكل الحرف: الألف بكل أشكالها «أ»، و«هـ» تُكتب «ه»."""
    a = re.sub('[ً-ْٰـ]', '', str(v or '').strip())
    if not a:
        return ''
    return 'أ' if a[0] in ('أ', 'إ', 'آ', 'ٱ', 'ا') else a[:1]


def validate_question(q):
    if not str(q.get('question', '')).strip():
        return False, 'نص السؤال مطلوب'
    if not str(q.get('answer', '')).strip():
        return False, 'الإجابة مطلوبة'
    game = q.get('game')
    if game not in ('letters', 'quiz', 'million'):
        return False, 'اللعبة غير صحيحة'
    if has_foreign(q.get('question', '')) or has_foreign(q.get('answer', '')):
        return False, 'السؤال أو الإجابة يحتوي على حروف غير عربية'
    if game == 'letters':
        letter = canon_letter(q.get('letter'))
        if not letter:
            return False, 'الحرف مطلوب لأسئلة الحروف'
        if letter not in AR_LETTERS:
            return False, 'الحرف غير صحيح'
        ans = str(q.get('answer', '')).strip()
        if not is_arabic_answer(ans):
            return False, 'الإجابة يجب أن تكون كلمة عربية'
        if first_letter_of(ans) != letter:
            return False, 'الإجابة لا تبدأ بالحرف المطلوب (' + str(q.get('letter')) + ')'
    if game == 'quiz':
        if q.get('points') not in (200, 400, 600):
            return False, 'قيمة النقاط يجب أن تكون 200 أو 400 أو 600'
    if game == 'million':
        opts = q.get('options') or []
        if len(opts) != 4:
            return False, 'أسئلة «من سيربح المليون» تحتاج 4 خيارات بالضبط'
        cleaned = [str(o).strip() for o in opts if str(o).strip()]
        if len(cleaned) != 4:
            return False, 'الخيارات الأربعة يجب أن تكون غير فارغة'
        if len(set(cleaned)) != 4:
            return False, 'الخيارات الأربعة يجب أن تكون مختلفة'
        if str(q.get('answer', '')).strip() not in cleaned:
            return False, 'الإجابة الصحيحة يجب أن تكون إحدى الخيارات الأربعة'
    return True, ''


# ============ QUESTIONS ============
@app.route('/api/questions', methods=['GET'])
def list_questions():
    game = request.args.get('game', '')
    letter = request.args.get('letter', '')
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    status = request.args.get('status', '')
    source = request.args.get('source', '')
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'newest')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(5000, max(1, int(request.args.get('per_page', 50))))
    include_archived = request.args.get('include_archived', '0') == '1'

    out = load_bank()
    if game:
        out = [q for q in out if q.get('game') == game]
    if letter:
        out = [q for q in out if q.get('letter') == letter]
    if category:
        out = [q for q in out if q.get('category_id') == category]
    if difficulty:
        out = [q for q in out if q.get('difficulty') == difficulty]
    if status:
        out = [q for q in out if q.get('status') == status]
    elif not include_archived:
        out = [q for q in out if q.get('status') != 'archived']
    if source:
        out = [q for q in out if q.get('source') == source]
    if search:
        s = norm_ar(search)
        out = [q for q in out if s in norm_ar(q.get('question', '')) or s in norm_ar(q.get('answer', ''))]

    if sort == 'newest':
        out = sorted(out, key=lambda q: q.get('created_at', ''), reverse=True)
    elif sort == 'oldest':
        out = sorted(out, key=lambda q: q.get('created_at', ''))
    elif sort == 'az':
        out = sorted(out, key=lambda q: norm_ar(q.get('question', '')))

    total = len(out)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    start = (page - 1) * per_page
    return jsonify({'questions': out[start:start + per_page], 'total': total,
                    'page': page, 'pages': pages, 'per_page': per_page})


@app.route('/api/questions/<qid>', methods=['GET'])
def get_question(qid):
    q = next((x for x in load_bank() if x['id'] == qid), None)
    if q:
        return jsonify(q)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/questions', methods=['POST'])
def add_question():
    data = request.get_json(silent=True) or {}
    ok, err = validate_question(data)
    if not ok:
        return jsonify({'error': err}), 400
    data['id'] = data.get('id') or gen_id()
    data['created_at'] = now()
    data.setdefault('updated_at', data['created_at'])
    data.setdefault('status', 'approved')
    data.setdefault('source', 'manual')
    data.setdefault('alternatives', [])
    data.setdefault('hint', '')
    data.setdefault('explanation', '')
    data.setdefault('image', '')
    all_qs = load_bank()
    all_qs.append(data)
    save_json(Q_FILE, all_qs)
    return jsonify(data), 201


@app.route('/api/questions/<qid>', methods=['PUT'])
def update_question(qid):
    data = request.get_json(silent=True) or {}
    all_qs = load_bank()
    for i, q in enumerate(all_qs):
        if q['id'] == qid:
            merged = dict(q)
            merged.update(data)
            merged['id'] = qid
            ok, err = validate_question(merged)
            if not ok:
                return jsonify({'error': err}), 400
            merged['updated_at'] = now()
            all_qs[i] = merged
            save_json(Q_FILE, all_qs)
            return jsonify(merged)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/questions/<qid>', methods=['DELETE'])
def delete_question(qid):
    save_json(Q_FILE, [q for q in load_bank() if q['id'] != qid])
    return jsonify({'ok': True})


@app.route('/api/questions/<qid>/archive', methods=['POST'])
def archive_question(qid):
    all_qs = load_bank()
    for q in all_qs:
        if q['id'] == qid:
            q['status'] = 'archived'
            q['updated_at'] = now()
            save_json(Q_FILE, all_qs)
            return jsonify(q)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/questions/<qid>/duplicate', methods=['POST'])
def duplicate_question(qid):
    all_qs = load_bank()
    src = next((q for q in all_qs if q['id'] == qid), None)
    if not src:
        return jsonify({'error': 'not found'}), 404
    copy = dict(src)
    copy['id'] = gen_id()
    copy['created_at'] = now()
    copy['updated_at'] = copy['created_at']
    copy['question'] = copy['question'] + ' (نسخة)'
    copy['status'] = 'pending_review'
    all_qs.append(copy)
    save_json(Q_FILE, all_qs)
    return jsonify(copy), 201


@app.route('/api/questions/export', methods=['GET'])
def export_questions():
    game = request.args.get('game', '')
    all_qs = load_bank()
    if game:
        all_qs = [q for q in all_qs if q.get('game') == game]
    path = os.path.join(tempfile.gettempdir(), 'ameen-questions-export.json')
    save_json(path, all_qs)
    return send_file(path, as_attachment=True, download_name='ameen-questions.json',
                     mimetype='application/json')


@app.route('/api/questions/import', methods=['POST'])
def import_questions():
    body = request.get_json(silent=True) or {}
    incoming = body.get('questions') or []
    mode = body.get('mode', 'preview')
    replace = bool(body.get('replace'))
    if not isinstance(incoming, list):
        return jsonify({'error': 'صيغة الملف غير صحيحة'}), 400

    all_qs = load_bank()
    existing_ids = {q['id'] for q in all_qs}
    existing_keys = {q_key(q) for q in all_qs}

    valid, invalid, dups, new, upd = [], [], [], [], []
    seen = set()
    for q in incoming:
        if not isinstance(q, dict):
            invalid.append({'question': str(q)[:80], 'reason': 'عنصر غير صالح'})
            continue
        ok, err = validate_question(q)
        if not ok:
            invalid.append({'question': q.get('question', ''), 'reason': err})
            continue
        k = q_key(q)
        if k in existing_keys or k in seen:
            dups.append({'question': q.get('question', ''), 'reason': 'سؤال مكرر'})
            continue
        seen.add(k)
        (upd if q.get('id') in existing_ids else new).append(q)
        valid.append(q)

    if mode == 'apply':
        removed = 0
        if replace and new:
            # استبدال: إسقاط أسئلة الألعاب الموجودة في الملف ثم إضافة ملفه
            games = {q.get('game') for q in new if q.get('game')}
            if games:
                kept = [q for q in all_qs if q.get('game') not in games]
                removed = len(all_qs) - len(kept)
                all_qs = kept
        for q in new:
            q['id'] = gen_id()
            q.setdefault('created_at', now())
            q['updated_at'] = now()
            all_qs.append(q)
        for q in upd:
            for i, e in enumerate(all_qs):
                if e['id'] == q['id']:
                    q['updated_at'] = now()
                    all_qs[i] = q
        save_json(Q_FILE, all_qs)

    return jsonify({'mode': mode, 'replace': replace, 'removed': removed,
                    'total_in_file': len(incoming),
                    'valid_count': len(valid), 'invalid_count': len(invalid),
                    'duplicate_count': len(dups), 'new_count': len(new),
                    'update_count': len(upd),
                    'invalid': invalid[:50], 'duplicates': dups[:50]})


@app.route('/api/questions/import-xlsx', methods=['POST'])
def import_questions_xlsx():
    game = request.form.get('game', '').strip()
    mode = request.form.get('mode', 'preview')
    replace = request.form.get('replace') == '1'
    target = request.form.get('target')
    if game not in GAME_IMPORT_DEFS:
        return jsonify({'error': 'اللعبة غير مدعومة'}), 400
    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({'error': 'ارفع ملف Excel (.xlsx)'}), 400
    fd, tmp = tempfile.mkstemp(suffix='.xlsx')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(uploaded.read())
        parsed = qi.parse_xlsx(tmp, game, target)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    recs = parsed.get('records', [])
    valid, invalid, dups, new, upd = [], [], [], [], []
    all_qs = load_bank()
    existing_ids = {q['id'] for q in all_qs}
    existing_keys = {q_key(q) for q in all_qs}
    seen = set()
    for rec in recs:
        item, ok, err = qi.validate_and_build(game, rec, target)
        if not ok:
            invalid.append({'question': item.get('question', ''), 'reason': err})
            continue
        k = game + '|' + norm_ar(item.get('question', ''))
        if k in existing_keys or k in seen:
            dups.append({'question': item.get('question', ''), 'reason': 'سؤال مكرر'})
            continue
        seen.add(k)
        (upd if item.get('id') in existing_ids else new).append(item)
        valid.append(item)
    if mode == 'apply':
        removed = 0
        if replace and new:
            games = {game}
            kept = [q for q in all_qs if q.get('game') not in games]
            removed = len(all_qs) - len(kept)
            all_qs = kept
        for q in new:
            q['id'] = gen_id()
            q.setdefault('created_at', now())
            q['updated_at'] = now()
            all_qs.append(q)
        for q in upd:
            for i, e in enumerate(all_qs):
                if e['id'] == q['id']:
                    q['updated_at'] = now()
                    all_qs[i] = q
        save_json(Q_FILE, all_qs)
    return jsonify({'mode': mode, 'replace': replace, 'removed': removed,
                    'total_in_file': len(recs),
                    'valid_count': len(valid), 'invalid_count': len(invalid),
                    'duplicate_count': len(dups), 'new_count': len(new),
                    'update_count': len(upd),
                    'invalid': invalid[:50], 'duplicates': dups[:50]})


REPORTS_FILE = os.path.join(DATA, 'reports', 'question_reports.json')

@app.route('/api/questions/report', methods=['POST'])
def report_question():
    body = request.get_json(silent=True) or {}
    qid = body.get('question_id', '')
    game = body.get('game', '')
    reason = body.get('reason', '')
    reported_by = body.get('reported_by', 'لاعب')
    if not qid or not game:
        return jsonify({'error': 'question_id و game مطلوبان'}), 400
    report = {
        'id': gen_id(),
        'question_id': qid,
        'game': game,
        'reason': reason or 'السؤال Seems wrong',
        'reported_by': reported_by,
        'status': 'open',
        'created_at': now()
    }
    reports = load_json(REPORTS_FILE, [])
    reports.append(report)
    save_json(REPORTS_FILE, reports)
    return jsonify({'ok': True, 'report': report})

@app.route('/api/reports', methods=['GET'])
def list_reports():
    reports = load_json(REPORTS_FILE, [])
    status = request.args.get('status', '')
    if status:
        reports = [r for r in reports if r.get('status') == status]
    return jsonify({'reports': reports})

@app.route('/api/reports/<rid>', methods=['PUT'])
def update_report(rid):
    data = request.get_json(silent=True) or {}
    reports = load_json(REPORTS_FILE, [])
    for r in reports:
        if r.get('id') == rid:
            r.update(data)
            r['updated_at'] = now()
            save_json(REPORTS_FILE, reports)
            return jsonify(r)
    return jsonify({'error': 'not found'}), 404

@app.route('/api/reports/<rid>', methods=['DELETE'])
def delete_report(rid):
    reports = load_json(REPORTS_FILE, [])
    reports = [r for r in reports if r.get('id') != rid]
    save_json(REPORTS_FILE, reports)
    return jsonify({'ok': True})

@app.route('/api/questions/duplicates', methods=['GET'])
def find_duplicates():
    seen, dups = {}, []
    for q in load_bank():
        k = q_key(q)
        if not k:
            continue
        if k in seen:
            dups.append({'a': seen[k], 'b': {'id': q['id'], 'question': q['question']}})
        else:
            seen[k] = {'id': q['id'], 'question': q['question']}
    return jsonify({'duplicates': dups, 'count': len(dups)})


@app.route('/api/questions/bulk-delete', methods=['POST'])
def bulk_delete():
    ids = set((request.get_json(silent=True) or {}).get('ids', []))
    save_json(Q_FILE, [q for q in load_bank() if q['id'] not in ids])
    return jsonify({'ok': True, 'deleted': len(ids)})


@app.route('/api/questions/bulk-status', methods=['POST'])
def bulk_status():
    body = request.get_json(silent=True) or {}
    ids = set(body.get('ids', []))
    status = body.get('status', 'approved')
    all_qs = load_bank()
    n = 0
    for q in all_qs:
        if q['id'] in ids:
            q['status'] = status
            q['updated_at'] = now()
            n += 1
    save_json(Q_FILE, all_qs)
    return jsonify({'ok': True, 'updated': n})


# ============ PENDING / REVIEW ============
# Generated questions live in the SAME store as everything else, only flagged
# status='pending_review'. A separate file meant the library never saw them.
def pending_items():
    return [q for q in load_bank() if q.get('status') == 'pending_review']


@app.route('/api/pending', methods=['GET'])
def list_pending():
    return jsonify({'questions': pending_items()})


@app.route('/api/pending/purge-bad', methods=['POST'])
def purge_bad_pending():
    """Drop queued questions that are malformed (foreign characters, wrong letter,
    missing options). Useful after a model misbehaves."""
    all_qs = load_bank()
    keep, dropped = [], []
    for q in all_qs:
        if q.get('status') != 'pending_review':
            keep.append(q)
            continue
        ok, err = validate_question(q)
        if ok:
            keep.append(q)
        else:
            dropped.append({'question': str(q.get('question', ''))[:70], 'reason': err})
    save_json(Q_FILE, keep)
    return jsonify({'ok': True, 'dropped': len(dropped),
                    'remaining': len([q for q in keep if q.get('status') == 'pending_review']),
                    'sample': dropped[:15]})


@app.route('/api/pending/approve', methods=['POST'])
def approve_pending():
    body = request.get_json(silent=True) or {}
    ids = body.get('ids')
    all_qs = load_bank()
    existing = {q_key(q) for q in all_qs if q.get('status') == 'approved'}
    approved, seen = 0, set()
    for q in all_qs:
        if q.get('status') != 'pending_review':
            continue
        if ids is not None and q['id'] not in ids:
            continue
        ok, _ = validate_question(q)
        if not ok:
            continue
        k = q_key(q)
        if k in existing and k not in seen:
            q['status'] = 'archived'      # duplicate of an approved question
            continue
        seen.add(k)
        q['status'] = 'approved'
        q['updated_at'] = now()
        approved += 1
    save_json(Q_FILE, all_qs)
    return jsonify({'ok': True, 'approved': approved,
                    'remaining': len([q for q in all_qs if q.get('status') == 'pending_review'])})


@app.route('/api/pending/reject', methods=['POST'])
def reject_pending():
    ids = set((request.get_json(silent=True) or {}).get('ids', []))
    all_qs = [q for q in load_bank()
              if not (q.get('status') == 'pending_review' and q.get('id') in ids)]
    save_json(Q_FILE, all_qs)
    return jsonify({'ok': True,
                    'remaining': len([q for q in all_qs if q.get('status') == 'pending_review'])})


# ============ بنك اللعبتين الجديدتين ============
# «شطب الحروف» و«سباق النرد» يقرآن نفس بنك «س.ج». التوسم يتم عند الطلب
# (GET /api/letters-strikeout/seed) ويكون إضافيًا فقط: كل سؤال موسوم يبقى
# ظاهرًا في س.ج ولا يُحذف منها أبدًا. التوسم عملية idempotent — لا صفوف مكررة.
STRIKEOUT_MARKS = {
    'dice_race': 'dice_race_ok',
    'letters_strikeout': 'letters_strikeout_ok',
}


def bank_letters_index():
    """الحرف الموحّد لكل سؤال في البنك — يُبنى مرة واحدة ثم يُخزَّن."""
    key = _BANK_CACHE['key']
    if _LETTERS_CACHE['key'] == key and _LETTERS_CACHE['idx'] is not None:
        return _LETTERS_CACHE['idx']
    idx = {}
    for q in load_bank():
        if q.get('status') == 'archived':
            continue
        ans = str(q.get('answer', '') or '').strip()
        L = letter_of(ans)
        if not L or L not in AR_LETTERS:
            continue
        idx.setdefault(L, []).append(q['id'])
    _LETTERS_CACHE['idx'] = idx
    _LETTERS_CACHE['key'] = key
    return idx


def letters_strikeout_pool(letter, limit=6):
    """أسئلة «شطب الحروف» لحرف معيّن — تُختار من البنك مباشرة."""
    ids = bank_letters_index().get(letter, [])
    if not ids:
        return []
    # خريطة id تأتي من المخبأ — بناء قاموس 14,895 عنصرًا لكل حرف كان السبب
    # في أن حمّال الحروف استغرق ~14 ثانية.
    by_id = _bank_by_id()
    return [by_id[i] for i in ids if i in by_id][:int(limit or 6)]


def seed_new_game_banks():
    """توسم أسئلة البنك للعبتين الجديدتين. يعيد عدّادات ما أُضيف.

    «سباق النرد» يحتاج سؤالًا واحدًا لكل حرف من الـ28 — إن قلّ عدد أسئلة حرف
    ما يُوسم من أسئلته الموجودة (لا يُخترع سؤال أبدًا)، وإن لم يبقَ حرف مكتملًا
    تُسجَّل الثغرة في 'letters_missing' لتظهر في الواجهة بدل لعبة ناقصة.
    """
    all_qs = load_bank()
    counts = {k: 0 for k in STRIKEOUT_MARKS.values()}
    per_letter = {}

    for q in all_qs:
        if q.get('game') != 'quiz':
            continue
        ans = str(q.get('answer', '') or '').strip()
        L = letter_of(ans)
        # سباق النرد: حرف واحد لكل حرف من الـ28 — وسم فقط، بلا أسئلة جديدة.
        if L in AR_LETTERS:
            mark = STRIKEOUT_MARKS['dice_race']
            if not q.get(mark):
                q[mark] = True
                counts[mark] += 1
            if len(per_letter.get(L, [])) < 1:
                per_letter.setdefault(L, []).append(q['id'])
        # شطب الحروف: كل سؤال مخزّن مسبقًا في البنك موسوم — بلا حد أقصى.
        mark = STRIKEOUT_MARKS['letters_strikeout']
        if not q.get(mark):
            q[mark] = True
            counts[mark] += 1

    save_json(Q_FILE, all_qs)
    missing = [l for l in AR_LETTERS if not per_letter.get(l)]
    return {'dice_race_marked': counts[STRIKEOUT_MARKS['dice_race']],
            'letters_strikeout_marked': counts[STRIKEOUT_MARKS['letters_strikeout']],
            'letters_missing': missing}


# ============ BATCH IMPORT (manual paste — local parsing, no AI) ============
# إضافة مئة سؤال أو أكثر دفعة واحدة. التحليل يتم في qimport.py بمنطق برمجي
# محض، والخادم هنا مسؤول عن التحقق من المخطط والحفظ الآمن.
IMPORT_HISTORY_FILE = os.path.join(DATA, 'questions', 'import_history.json')
IMPORT_DRAFT_FILE = os.path.join(DATA, 'questions', 'import_draft.json')
IMPORT_JOBS = {}          # idempotency_key -> stored result (يمنع الحفظ المزدوج)
IMPORT_MAX_HISTORY = 50
LASTONE_FILE = os.path.join(BASE_DIR, 'static', 'lastone_categories.json')
LASTONE_MIRROR = os.path.join(DATA, 'lastone_categories.json')


def lastone_data():
    return load_json(LASTONE_FILE, {}) or {}


def _lastone_category(target):
    """«آخر واحد!» يخزّن قوائمه باسم التصنيف لا بمعرّفه."""
    t = target or {}
    return str(t.get('category_name') or t.get('category') or '').strip()


def _import_existing_keys(game, target=None):
    """مفاتيح التكرار والإجابات الموجودة فعلاً في هدف الاستيراد."""
    gdef = qi.GAME_IMPORT_DEFS.get(game)
    if not gdef:
        return set(), set()
    keys, answers = set(), set()
    tgt = target or {}

    if gdef['storage'] == 'questions':
        letter = str(tgt.get('letter') or '').strip()
        cat = str(tgt.get('category_id') or tgt.get('category') or '').strip()
        for q in load_bank():
            if q.get('game') != game:
                continue
            if game == 'letters' and letter and q.get('letter') != letter:
                continue
            if game == 'quiz' and cat and q.get('category_id') != cat:
                continue
            keys.add(q_key(q))
            answers.add(norm_ar(q.get('answer', '')))
        return keys, answers

    if gdef['storage'] == 'content':
        cat = str(tgt.get('category_name') or tgt.get('category') or '').strip()
        for it in load_json(content_file(game), []):
            if cat and str(it.get('category') or '').strip() != cat:
                continue
            keys.add(qi.record_key(game, it))
            answers.add(norm_ar(str(it.get('answer') or '')))
        return keys, answers

    if gdef['storage'] == 'players':
        for p in load_json(PL_FILE, []):
            keys.add(qi.record_key(game, p))
            answers.add(norm_ar(p.get('name', '')))
        return keys, answers

    for arr in lastone_data().values():
        for a in arr:
            answers.add(norm_ar(a))
            keys.add('lastone|' + norm_ar(a))
    return keys, answers


def _import_history():
    h = load_json(IMPORT_HISTORY_FILE, [])
    return h if isinstance(h, list) else []


def _import_log(entry):
    h = _import_history()
    h.insert(0, entry)
    save_json(IMPORT_HISTORY_FILE, h[:IMPORT_MAX_HISTORY])


def _import_difficulties(game):
    if game == 'quiz':
        return [{'id': 'under', 'name': 'تحت المتوسط'}, {'id': 'easy', 'name': 'سهل'},
                {'id': 'medium', 'name': 'متوسط'}, {'id': 'hard', 'name': 'صعب'}]
    return [{'id': 'easy', 'name': 'سهل'}, {'id': 'medium', 'name': 'متوسط'},
            {'id': 'hard', 'name': 'صعب'}]


# ============ اللعبتان الجديدتان — يقرآن بنك «س.ج» ============
@app.route('/api/letters-strikeout/seed', methods=['GET'])
def letters_strikeout_seed():
    """يبني نسخة اللعبة من بنك س.ج عند أول تشغيل — وسم إضافي فقط."""
    return jsonify(seed_new_game_banks())


@app.route('/api/letters-strikeout/letters', methods=['GET'])
def letters_strikeout_letters():
    """الحروف المتاحة مع عدد الأسئلة الفعلي لكل حرف في بنك س.ج."""
    idx = bank_letters_index()
    return jsonify({'letters': [{'letter': l, 'count': len(idx.get(l, []))}
                                for l in AR_LETTERS]})


@app.route('/api/letters-strikeout/questions', methods=['GET'])
def letters_strikeout_questions():
    letter = canon_letter_match(request.args.get('letter', ''))
    if letter not in AR_LETTERS:
        return jsonify({'error': 'الحرف غير صحيح'}), 400
    limit = min(20, max(1, int(request.args.get('limit', 6))))
    qs = letters_strikeout_pool(letter, limit)
    if not qs:
        return jsonify({'error': 'لا توجد أسئلة لهذا الحرف في بنك س.ج'}), 404
    return jsonify({'letter': letter, 'questions': qs})


@app.route('/api/letters-strikeout/random', methods=['GET'])
def letters_strikeout_random():
    """حرف عشوائي له أسئلة فعلًا في البنك + أسئلته (لا حرف فارغ أبدًا)."""
    idx = bank_letters_index()
    avail = [l for l in AR_LETTERS if idx.get(l)]
    if not avail:
        return jsonify({'error': 'البنك فارغ'}), 404
    letter = avail[_rnd.randrange(len(avail))]
    qs = letters_strikeout_pool(letter, 6)
    return jsonify({'letter': letter, 'questions': qs})


@app.route('/api/dice-race/seed', methods=['GET'])
def dice_race_seed():
    """نفس التوسم — نقطة دخول مستقلة حتى لا تعتمد اللعبتان على بعضهما."""
    return jsonify(seed_new_game_banks())


@app.route('/api/dice-race/questions', methods=['GET'])
def dice_race_questions():
    """سؤال واحد لكل حرف مطلوب — يقرأ من بنك س.ج مباشرة."""
    letters = [l for l in (request.args.get('letters') or '').split(',') if l]
    if not letters:
        letters = list(AR_LETTERS)
    out = {}
    missing = []
    for raw in letters:
        L = canon_letter_match(raw)
        if L not in AR_LETTERS:
            continue
        pool = letters_strikeout_pool(L, 1)
        if pool:
            out[L] = pool[0]
        else:
            missing.append(L)
    if not out:
        return jsonify({'error': 'لا توجد أسئلة للأحرف المطلوبة'}), 404
    return jsonify({'questions': out, 'letters': list(out.keys()), 'missing': missing})


@app.route('/api/dice-race/questions/random', methods=['GET'])
def dice_race_random():
    """مسار سباق عشوائي كامل: 28 سؤالًا (واحد لكل حرف) بلا حرف فارغ."""
    idx = bank_letters_index()
    avail = [l for l in AR_LETTERS if idx.get(l)]
    if not avail:
        return jsonify({'error': 'البنك فارغ'}), 404
    import random as _rnd
    picks = []
    for L in AR_LETTERS:
        if not idx.get(L):
            continue
        qid = idx[L][int(_rnd.random() * len(idx[L]))]
        q = next((x for x in load_bank() if x.get('id') == qid), None)
        if q:
            picks.append(q)
    return jsonify({'questions': picks, 'letters': [letter_of(q.get('answer', '')) for q in picks]})


@app.route('/api/import/games', methods=['GET'])
def import_games():
    """كل لعبة موجودة فعلاً في المشروع، مع محدداتها وعدّاداتها الحقيقية."""
    cats = load_json(CAT_FILE, [])
    cat_counts, letter_counts = {}, {}
    for q in load_bank():
        if q.get('game') == 'quiz':
            cid = q.get('category_id')
            cat_counts[cid] = cat_counts.get(cid, 0) + 1
        elif q.get('game') == 'letters':
            lt = q.get('letter')
            letter_counts[lt] = letter_counts.get(lt, 0) + 1
    players = load_json(PL_FILE, [])
    leagues = sorted({p.get('league') for p in players if p.get('league')})

    out = []
    for g, d in qi.GAME_IMPORT_DEFS.items():
        entry = {'game': g, 'name': d['name'], 'mode': d['mode'], 'storage': d['storage'],
                 'selectors': d['selectors'], 'mandatory': d['mandatory'],
                 'max_records': d['max_records'],
                 'template': qi.template_for(g, {}),
                 'difficulties': _import_difficulties(g)}
        if 'category' in d['selectors']:
            if g == 'lastone':
                entry['categories'] = [{'id': k, 'name': k, 'count': len(v)}
                                       for k, v in lastone_data().items()]
            elif d['storage'] == 'content':
                vals = sorted({str(x.get('category') or '').strip() for x in
                               load_json(content_file(g), []) if x.get('category')})
                entry['categories'] = [{'id': v, 'name': v} for v in vals]
            else:
                entry['categories'] = [{'id': c['id'], 'name': c['name'],
                                        'count': cat_counts.get(c['id'], 0)} for c in cats]
        if 'letter' in d['selectors']:
            entry['letters'] = [{'id': l, 'name': l, 'count': letter_counts.get(l, 0)}
                                for l in AR_LETTERS]
        if 'points' in d['selectors']:
            entry['points'] = [{'id': p, 'name': str(p)} for p in (200, 400, 600)]
        if 'league' in d['selectors']:
            entry['leagues'] = [{'id': l, 'name': LEAGUE_NAMES.get(l, l)} for l in leagues]
        if 'position' in d['selectors']:
            entry['positions'] = [{'id': p, 'name': p} for p in PLAYER_POSITIONS]
        if 'subcategory' in d['selectors']:
            vals = sorted({str(x.get('subcategory') or '').strip() for x in
                           load_json(content_file(g), []) if x.get('subcategory')})
            entry['subcategories'] = [{'id': v, 'name': v} for v in vals]
        out.append(entry)
    return jsonify({'games': out})


@app.route('/api/import/parse', methods=['POST'])
def import_parse():
    """تحليل النص محلياً: فصل السجلات والتحقق منها وكشف التكرار."""
    body = request.get_json(silent=True) or {}
    game = str(body.get('game') or '')
    text = str(body.get('text') or '')
    target = body.get('target') or {}
    mode = str(body.get('mode') or 'append')
    try:
        res = qi.parse_batch(text, game, target)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # في وضع الاستبدال السجل المكرر هو نفسه السجل الذي سيُحلّ محله، فمقارنته
    # بالمخزن خطأ: ستظهر كل الدفعة «مكررة» ولا يُحفظ شيء.
    if mode == 'replace':
        keys, answers = set(), set()
    else:
        keys, answers = _import_existing_keys(game, target)
    qi.detect_duplicates(res['records'], game, keys, answers)

    # حكم المخطط على كل سجل، ليكون ما تراه المعاينة هو ما سيقوله الحفظ
    for rec in res['records']:
        if rec.get('status') in ('ok', 'needs_review'):
            item, ok, err = qi.validate_and_build(game, rec, target)
            rec['savable'] = ok
            rec['schema_error'] = err
        else:
            rec['savable'] = False
            rec['schema_error'] = ''
    res['summary'] = qi.summarize(res['records'])
    return jsonify(res)


@app.route('/api/import/check', methods=['POST'])
def import_check():
    """حكم المخطط على سجل واحد بعد تعديله في المعاينة."""
    body = request.get_json(silent=True) or {}
    game = str(body.get('game') or '')
    rec = body.get('record')
    if game not in qi.GAME_IMPORT_DEFS or not isinstance(rec, dict):
        return jsonify({'error': 'سجل غير صالح'}), 400
    item, ok, err = qi.validate_and_build(game, rec, body.get('target') or {})
    return jsonify({'savable': ok, 'schema_error': err, 'item': item})


@app.route('/api/import/summary', methods=['POST'])
def import_summary():
    body = request.get_json(silent=True) or {}
    records = body.get('records') or []
    if not isinstance(records, list):
        return jsonify({'error': 'صيغة غير صحيحة'}), 400
    return jsonify(qi.summarize(records))


def _import_scope_pred(game, target, scope):
    """محمول على عناصر المخزن: True حين ينتمي العنصر إلى نطاق الحذف المختار."""
    t = target or {}
    if scope != 'target':
        return lambda x: x.get('game') == game
    if game == 'letters':
        lt = canon_letter(t.get('letter'))
        return lambda x: x.get('game') == 'letters' and canon_letter(x.get('letter')) == lt
    if game == 'quiz':
        cid = str(t.get('category_id') or t.get('category') or '').strip()
        return lambda x: x.get('game') == 'quiz' and str(x.get('category_id') or '').strip() == cid
    if game == 'million':
        return lambda x: x.get('game') == 'million'
    if game == 'auction':
        lg = str(t.get('league') or '').strip()
        pos = str(t.get('position') or '').strip()

        def _auction(x):
            if lg and str(x.get('league') or '').strip() != lg:
                return False
            return not (pos and str(x.get('position') or '').strip() != pos)
        return _auction
    cat = str(t.get('category_name') or t.get('category') or '').strip()
    return lambda x: str(x.get('category') or '').strip() == cat


def _import_store_items(game):
    """عناصر مخزن اللعبة الواحدة (دون عناصر الألعاب الأخرى)."""
    gdef = qi.GAME_IMPORT_DEFS.get(game) or {}
    if gdef.get('storage') == 'questions':
        return [q for q in load_bank() if q.get('game') == game]
    if gdef.get('storage') == 'content':
        return load_json(content_file(game), [])
    if gdef.get('storage') == 'players':
        return load_json(PL_FILE, [])
    return []


def _import_counts(game, target, scope):
    """(عدد ما سيُحذف، إجمالي الموجود) — للمعاينة قبل أي كتابة."""
    gdef = qi.GAME_IMPORT_DEFS.get(game)
    if not gdef:
        return 0, 0
    if gdef['storage'] == 'lastone':
        data = lastone_data()
        total = sum(len(v) for v in data.values())
        if scope == 'target':
            return len(data.get(_lastone_category(target), [])), total
        return total, total
    items = _import_store_items(game)
    if scope != 'target':
        return len(items), len(items)
    pred = _import_scope_pred(game, target, 'target')
    return sum(1 for x in items if pred(x)), len(items)


def _import_write(game, target, items, mode='append', scope='game'):
    """كتابة واحدة ذرّية لكل مخزن.

    ترجع (عدد المحفوظ، قائمة الفاشل، المتجاوز، عدد المحذوف). وضع «الاستبدال»
    يحذف أسئلة النطاق أولاً ثم يضيف الدفعة، فيكون المخزن مطابقاً للدفعة.
    """
    gdef = qi.GAME_IMPORT_DEFS[game]
    ts = now()
    deleted = 0
    replacing = mode == 'replace'

    if gdef['storage'] == 'questions':
        store = load_bank()
        if replacing:
            pred = _import_scope_pred(game, target, scope)
            kept = [q for q in store if not pred(q)]
            deleted = len(store) - len(kept)
            store = kept
        for it in items:
            it['id'] = gen_id()
            it['created_at'] = ts
            it['updated_at'] = ts
            it['status'] = 'approved'
            it['source'] = 'import'
            store.append(it)
        save_json(Q_FILE, store)
        return len(items), [], 0, deleted

    if gdef['storage'] == 'content':
        store = load_json(content_file(game), [])
        if replacing:
            pred = _import_scope_pred(game, target, scope)
            kept = [x for x in store if not pred(x)]
            deleted = len(store) - len(kept)
            store = kept
        for it in items:
            it['id'] = gen_id()
            it['created_at'] = ts
            it['updated_at'] = ts
            it.setdefault('status', 'approved')
            it['source'] = 'import'
            store.append(it)
        save_json(content_file(game), store)
        return len(items), [], 0, deleted

    if gdef['storage'] == 'players':
        store = load_json(PL_FILE, [])
        if replacing:
            pred = _import_scope_pred(game, target, scope)
            kept = [x for x in store if not pred(x)]
            deleted = len(store) - len(kept)
            store = kept
        for it in items:
            it['id'] = gen_id()
            it.setdefault('verified', False)
            store.append(it)
        save_json(PL_FILE, store)
        return len(items), [], 0, deleted

    # «آخر واحد!»: الإجابات تُضاف إلى قائمة التصنيف المستهدف
    cat = _lastone_category(target)
    data = lastone_data()
    if not cat:
        raise ValueError('التصنيف مطلوب')
    if cat not in data:
        raise ValueError('التصنيف غير موجود في آخر واحد')
    if replacing:
        if scope == 'game':
            for k in list(data.keys()):
                deleted += len(data[k])
            data = {}
        else:
            deleted = len(data.get(cat, []))
    arr = [str(x).strip() for x in data.get(cat, []) if str(x).strip()]
    seen = {norm_ar(x) for x in arr}
    saved = 0
    for it in items:
        a = str(it.get('answer') or '').strip()
        if not a or norm_ar(a) in seen:
            continue
        seen.add(norm_ar(a))
        arr.append(a)
        saved += 1
    data[cat] = arr
    save_json(LASTONE_FILE, data)
    if os.path.abspath(LASTONE_MIRROR) != os.path.abspath(LASTONE_FILE):
        save_json(LASTONE_MIRROR, data)
    return saved, [], len(items) - saved, deleted


@app.route('/api/import/save', methods=['POST'])
def import_save():
    """تحقق من كل السجلات أولاً، ثم اكتب الدفعة كاملة في عملية واحدة."""
    body = request.get_json(silent=True) or {}
    game = str(body.get('game') or '')
    target = body.get('target') or {}
    records = body.get('records') or []
    keep_dups = set(body.get('keep_duplicates') or [])
    idem = str(body.get('idempotency_key') or '').strip()
    allow_partial = bool(body.get('allow_partial'))
    mode = str(body.get('mode') or 'append')
    scope = str(body.get('scope') or 'game')
    if mode not in ('append', 'replace'):
        return jsonify({'error': 'وضع حفظ غير معروف'}), 400
    if scope not in ('game', 'target'):
        scope = 'game'

    gdef = qi.GAME_IMPORT_DEFS.get(game)
    if not gdef:
        return jsonify({'error': 'اللعبة غير مدعومة'}), 400
    if not isinstance(records, list) or not records:
        return jsonify({'error': 'لا توجد سجلات للحفظ'}), 400
    if idem and idem in IMPORT_JOBS:
        cached = dict(IMPORT_JOBS[idem])
        cached['cached'] = True
        return jsonify(cached)

    accepted, rejected = [], []
    for rec in records:
        if not isinstance(rec, dict):
            rejected.append({'idx': None, 'question': '', 'reason': 'سجل غير صالح'})
            continue
        if rec.get('excluded'):
            continue
        if rec.get('duplicate') and rec.get('idx') not in keep_dups:
            continue
        item, ok, err = qi.validate_and_build(game, rec, target)
        if not ok:
            rejected.append({
                'idx': rec.get('idx'),
                'question': str(item.get('question') or item.get('name')
                                or item.get('word') or '')[:120],
                'reason': err})
            continue
        accepted.append(item)

    # لا معاملة حقيقية في مخزن JSON، لذا القاعدة: تحقق قبل الكتابة + كتابة
    # ذرّية واحدة. عند رفض أي سجل لا يُكتب شيء، فيكون إعادة المحاولة آمنة.
    if rejected and not allow_partial:
        return jsonify({'ok': False, 'strategy': 'validate-then-atomic-write',
                        'saved': 0, 'failed': len(rejected), 'rejected': rejected,
                        'error': 'بعض السجلات غير صالحة — لم يُحفظ شيء'}), 400
    if not accepted:
        return jsonify({'ok': False, 'saved': 0, 'failed': len(rejected),
                        'rejected': rejected, 'error': 'لا توجد سجلات صالحة'}), 400

    try:
        saved, failed, skipped, deleted = _import_write(game, target, accepted, mode, scope)
    except Exception as e:
        return jsonify({'ok': False, 'saved': 0, 'failed': len(accepted),
                        'rejected': rejected,
                        'error': 'فشل الحفظ في طبقة التخزين: ' + str(e),
                        'strategy': 'validate-then-atomic-write'}), 500

    result = {'ok': True, 'strategy': 'validate-then-atomic-write',
              'game': game, 'target': target, 'mode': mode, 'scope': scope,
              'requested': len(records), 'accepted': len(accepted),
              'saved': saved, 'skipped': skipped, 'deleted': deleted,
              'failed': len(failed) + len(rejected),
              'rejected': rejected + failed,
              'duplicates_kept': len(keep_dups)}
    _import_log({'id': gen_id(), 'at': now(), 'game': game, 'target': target,
                 'mode': mode, 'scope': scope, 'deleted': deleted,
                 'requested': len(records), 'saved': saved,
                 'excluded': len(records) - len(accepted),
                 'duplicates_kept': len(keep_dups), 'ok': True})
    if idem:
        IMPORT_JOBS[idem] = result
        if len(IMPORT_JOBS) > 200:
            for k in list(IMPORT_JOBS)[:100]:
                IMPORT_JOBS.pop(k, None)
    return jsonify(result)


@app.route('/api/import/count', methods=['GET'])
def import_count():
    """عدد الأسئلة التي سيحذفها وضع الاستبدال — للمعاينة قبل الكتابة."""
    # هذا المسار GET، وbefore_request لا يحرس القراءات — يُحرس هنا حتى لا
    # يقرأ عدد أسئلة البنك أي زائر.
    if not is_admin(request):
        return jsonify({'error': 'غير مصرّح — سجّل الدخول إلى لوحة الإدارة'}), 401
    game = request.args.get('game', '')
    gdef = qi.GAME_IMPORT_DEFS.get(game)
    if not gdef:
        return jsonify({'error': 'اللعبة غير مدعومة'}), 400
    scope = request.args.get('scope') or 'game'
    if scope not in ('game', 'target'):
        scope = 'game'
    target = {'letter': request.args.get('letter', ''),
              'category_id': request.args.get('category', ''),
              'category_name': request.args.get('category', ''),
              'league': request.args.get('league', ''),
              'position': request.args.get('position', '')}
    deleted, total = _import_counts(game, target, scope)
    return jsonify({'game': game, 'scope': scope, 'deleted': deleted, 'total': total})


@app.route('/api/import/history', methods=['GET'])
def import_history():
    return jsonify({'history': _import_history()[:IMPORT_MAX_HISTORY]})


@app.route('/api/import/draft', methods=['GET'])
def import_draft_get():
    return jsonify(load_json(IMPORT_DRAFT_FILE, {}) or {})


@app.route('/api/import/draft', methods=['POST'])
def import_draft_save():
    """حفظ النص الملصوق مؤقتاً إذا تعطّل التحليل قبل أن يُفقد."""
    body = request.get_json(silent=True) or {}
    save_json(IMPORT_DRAFT_FILE, {
        'at': now(),
        'game': str(body.get('game') or ''),
        'target': body.get('target') or {},
        'text': str(body.get('text') or '')[:qi.MAX_TEXT_CHARS]})
    return jsonify({'ok': True})


@app.route('/api/import/template', methods=['GET'])
def import_template():
    game = request.args.get('game', '')
    target = {'category_name': request.args.get('category', ''),
              'letter': request.args.get('letter', '')}
    return qi.template_for(game, target), 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': 'attachment; filename="ameen-import-template.txt"'}


@app.route('/api/import/export', methods=['POST'])
def import_export():
    """تصدير السجلات المستخرجة JSON أو CSV — بلا حفظ في الخادم."""
    body = request.get_json(silent=True) or {}
    records = body.get('records') or []
    fmt = str(body.get('format') or 'json')
    fields = ['idx', 'num', 'question', 'answer', 'status', 'duplicate',
              'schema_error', 'options', 'difficulty']
    rows = []
    for r in records:
        if r.get('excluded'):
            continue
        merged = r.get('merged') or {}
        rows.append({
            'idx': r.get('idx'), 'num': r.get('num'),
            'question': r.get('question') or '', 'answer': r.get('answer') or '',
            'status': r.get('status'),
            'duplicate': (r.get('duplicate') or {}).get('why', ''),
            'schema_error': r.get('schema_error') or '',
            'options': ' | '.join((r.get('coerced') or {}).get('options') or []),
            'difficulty': merged.get('difficulty', '')})
    if fmt == 'csv':
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for row in rows:
            w.writerow(row)
        return buf.getvalue().encode('utf-8-sig'), 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename="ameen-import.csv"'}
    return jsonify({'records': rows, 'count': len(rows)})


# ============ CATEGORIES ============
@app.route('/api/categories', methods=['GET'])
def list_categories():
    cats = load_json(CAT_FILE, [])
    all_qs = load_bank()
    for cat in cats:
        qs = [q for q in all_qs if q.get('category_id') == cat['id']]
        cat['question_count'] = len(qs)
        for v in (200, 400, 600):
            cat['count_' + str(v)] = len([q for q in qs if q.get('points') == v])
        cat['approved_count'] = len([q for q in qs if q.get('status') == 'approved'])
        cat['pending_count'] = len([q for q in qs if q.get('status') == 'pending_review'])
        cat['complete'] = cat['approved_count'] >= 36
    return jsonify({'categories': cats})


@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.get_json(silent=True) or {}
    if not str(data.get('name', '')).strip():
        return jsonify({'error': 'اسم الفئة مطلوب'}), 400
    data['id'] = data.get('id') or gen_id()
    data['created_at'] = now()
    data.setdefault('description', '')
    data.setdefault('image', '')
    data.setdefault('color', '#8b5cf6')
    data.setdefault('icon', '📚')
    data.setdefault('group', '')
    cats = load_json(CAT_FILE, [])
    cats.append(data)
    save_json(CAT_FILE, cats)
    return jsonify(data), 201


@app.route('/api/categories/<cid>', methods=['PUT'])
def update_category(cid):
    data = request.get_json(silent=True) or {}
    cats = load_json(CAT_FILE, [])
    for i, c in enumerate(cats):
        if c['id'] == cid:
            merged = dict(c)
            merged.update(data)
            merged['id'] = cid
            cats[i] = merged
            save_json(CAT_FILE, cats)
            return jsonify(merged)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/categories/<cid>', methods=['DELETE'])
def delete_category(cid):
    save_json(CAT_FILE, [c for c in load_json(CAT_FILE, []) if c['id'] != cid])
    return jsonify({'ok': True})


def _save_upload(req, store_file, item_id):
    if 'file' not in req.files:
        return jsonify({'error': 'لم يتم إرسال ملف'}), 400
    f = req.files['file']
    ext = os.path.splitext(f.filename or '')[1].lower()
    if ext not in ALLOWED_IMG:
        return jsonify({'error': 'نوع الملف غير مدعوم (png / jpg / webp / gif / svg)'}), 400
    blob = f.read()
    if len(blob) > MAX_IMG_BYTES:
        return jsonify({'error': 'حجم الصورة أكبر من 4 ميجابايت'}), 400
    fname = item_id + '-' + uuid.uuid4().hex[:6] + ext
    with open(os.path.join(UPLOAD_DIR, fname), 'wb') as out:
        out.write(blob)
    url = '/uploads/' + fname
    items = load_json(store_file, [])
    for it in items:
        if it['id'] == item_id:
            it['image'] = url
            save_json(store_file, items)
            return jsonify({'ok': True, 'image': url})
    return jsonify({'error': 'العنصر غير موجود'}), 404


@app.route('/api/categories/<cid>/image', methods=['POST'])
def upload_category_image(cid):
    return _save_upload(request, CAT_FILE, cid)


@app.route('/api/questions/<qid>/image', methods=['POST'])
def upload_question_image(qid):
    return _save_upload(request, Q_FILE, qid)


# ============ PLAYERS ============
@app.route('/api/players', methods=['GET'])
def list_players():
    players = load_json(PL_FILE, [])
    for key, arg in (('club', 'club'), ('league', 'league'), ('nationality', 'nation'),
                     ('era', 'era'), ('position', 'position')):
        val = request.args.get(arg, '')
        if val:
            players = [p for p in players if p.get(key) == val]
    return jsonify({'players': players, 'total': len(players)})


@app.route('/api/players/meta', methods=['GET'])
def players_meta():
    players = load_json(PL_FILE, [])
    def uniq(k):
        return sorted({p.get(k) for p in players if p.get(k)})
    return jsonify({'leagues': uniq('league'), 'clubs': uniq('club'),
                    'nations': uniq('nationality'), 'eras': uniq('era'),
                    'positions': uniq('position')})


@app.route('/api/players', methods=['POST'])
def add_player():
    data = request.get_json(silent=True) or {}
    if not str(data.get('name', '')).strip():
        return jsonify({'error': 'اسم اللاعب مطلوب'}), 400
    data['id'] = data.get('id') or gen_id()
    data.setdefault('verified', False)
    data.setdefault('source', 'manual')
    players = load_json(PL_FILE, [])
    players.append(data)
    save_json(PL_FILE, players)
    return jsonify(data), 201


@app.route('/api/players/<pid>', methods=['PUT'])
def update_player(pid):
    data = request.get_json(silent=True) or {}
    players = load_json(PL_FILE, [])
    for i, p in enumerate(players):
        if p['id'] == pid:
            merged = dict(p); merged.update(data); merged['id'] = pid
            players[i] = merged
            save_json(PL_FILE, players)
            return jsonify(merged)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/players/<pid>', methods=['DELETE'])
def delete_player(pid):
    save_json(PL_FILE, [p for p in load_json(PL_FILE, []) if p['id'] != pid])
    return jsonify({'ok': True})


@app.route('/api/players/export', methods=['GET'])
def export_players():
    path = os.path.join(tempfile.gettempdir(), 'ameen-players-export.json')
    save_json(path, load_json(PL_FILE, []))
    return send_file(path, as_attachment=True, download_name='ameen-players.json',
                     mimetype='application/json')


@app.route('/api/players/import', methods=['POST'])
def import_players():
    body = request.get_json(silent=True) or {}
    incoming = body.get('players') or []
    mode = body.get('mode', 'preview')
    if not isinstance(incoming, list):
        return jsonify({'error': 'صيغة الملف غير صحيحة'}), 400
    players = load_json(PL_FILE, [])
    names = {norm_ar(p.get('name', '')) for p in players}
    new, dups, invalid = [], [], []
    for p in incoming:
        if not isinstance(p, dict) or not str(p.get('name', '')).strip():
            invalid.append(p); continue
        if norm_ar(p['name']) in names:
            dups.append(p); continue
        names.add(norm_ar(p['name']))
        new.append(p)
    if mode == 'apply':
        for p in new:
            p['id'] = gen_id()
            p.setdefault('verified', False)
            players.append(p)
        save_json(PL_FILE, players)
    return jsonify({'mode': mode, 'total_in_file': len(incoming), 'new_count': len(new),
                    'duplicate_count': len(dups), 'invalid_count': len(invalid)})


# ============ GAME CONTENT LIBRARIES (7 new games) ============
CONTENT_DIR = os.path.join(DATA, 'content')
os.makedirs(CONTENT_DIR, exist_ok=True)


def content_file(game):
    return os.path.join(CONTENT_DIR, game + '.json')


# Each game declares its own required fields — one giant table would not fit them all.
GAME_SCHEMAS = {
    'codenames': {
        'name': 'كود نيمز',
        'required': ['word'],
        'fields': ['word', 'category', 'difficulty', 'meaning', 'related', 'ambiguous', 'status', 'source'],
        'prompt': (
            'أنشئ {n} كلمة عربية مناسبة للعبة كود نيمز (Codenames).\n'
            'لكل كلمة أعد: الكلمة، معناها المختصر، تصنيفها الدلالي، و3 إلى 5 كلمات ترتبط بها دلالياً، '
            'وكلمتين قد تسببان التباساً معها، ومستوى الصعوبة.\n'
            'شروط: الكلمة مفردة ومفهومة وشائعة، بلا حروف أجنبية، ولا تكرر كلمة.\n'
            'الصيغة: [{{"word":"...","meaning":"...","category":"...","related":["..."],"ambiguous":["..."],'
            '"difficulty":"easy|medium|hard"}}]'
        ),
    },
    'detective': {
        'name': 'المحقق',
        'required': ['title', 'solution'],
        'fields': ['title', 'intro', 'setting', 'characters', 'evidence', 'timeline', 'solution',
                   'reasoning', 'key_evidence', 'difficulty', 'status', 'source'],
        'prompt': (
            'أنشئ {n} قضية تحقيق جنائي خيالي للعبة «المحقق».\n'
            'لكل قضية أعد حقولاً بهذا الشكل الدقيق:\n'
            '{{"title":"عنوان القضية","intro":"مقدمة مختصرة","setting":"المكان والظروف",'
            '"characters":[{{"name":"اسم","role":"دوره","statement":"قول الشاهد"}}],'
            '"evidence":[{{"id":"e1","text":"وصف الدليل","hidden":false}}],'
            '"timeline":["حدث 1","حدث 2"],"solution":"ما حدث فعلاً",'
            '"reasoning":"تسلسل الاستنتاج","key_evidence":["e1","e3"],'
            '"difficulty":"easy|medium|hard"}}\n'
            'شروط: 3 إلى 5 شخصيات، 4 إلى 7 أدلة (بعضها hidden:true)، الأقوال متسقة مع الحل، '
            'والحل مدعوم فعلاً بالأدلة المذكورة في key_evidence. كل النصوص عربية.'
        ),
    },
    'culprit': {
        'name': 'من الفاعل؟',
        'required': ['title', 'culprit'],
        'fields': ['title', 'incident', 'suspects', 'initial_info', 'clues', 'culprit',
                   'explanation', 'difficulty', 'status', 'source'],
        'prompt': (
            'أنشئ {n} قضية للعبة «من الفاعل؟» — تحديد المسؤول عن حادثة خيالية.\n'
            'الصيغة:\n'
            '{{"title":"عنوان","incident":"وصف الحادثة",'
            '"suspects":[{{"name":"اسم","motive":"دافعه المحتمل"}}],'
            '"initial_info":["معلومة أولية"],'
            '"clues":[{{"text":"دليل","eliminates":"اسم من يستبعده أو فارغ"}}],'
            '"culprit":"اسم المسؤول","explanation":"لماذا هو المسؤول ولماذا استُبعد الباقون",'
            '"difficulty":"easy|medium|hard"}}\n'
            'شروط: 3 إلى 6 مشتبهين، دافع كل واحد موجود، و4 إلى 6 أدلة. '
            'يجب أن توجد أدلة تستبعد كل مشتبه بريء — الدافع وحده لا يكفي. كل النصوص عربية.'
        ),
    },
    'spy': {
        'name': 'الجاسوس',
        'required': ['word'],
        'fields': ['word', 'category', 'difficulty', 'similar', 'status', 'source'],
        'prompt': (
            'أنشئ {n} كلمة سرية للعبة «الجاسوس».\n'
            'الصيغة: [{{"word":"الكلمة","category":"فئتها","difficulty":"easy|medium|hard",'
            '"similar":["كلمتان قريبتان منها يسهل الخلط بينهما"]}}]\n'
            'شروط: الكلمة قابلة للوصف بعدة طرق دون قولها، ليست ملتبسة بصورة غير عادلة، '
            'وليست عامة جداً. كل النصوص عربية.'
        ),
    },
    'debate': {
        'name': 'أقنعني!',
        'required': ['topic'],
        'fields': ['topic', 'side_a', 'side_b', 'category', 'difficulty', 'key_arguments', 'fallacies', 'status', 'source'],
        'prompt': (
            'أنشئ {n} موضوع نقاش متوازناً للعبة «أقنعني!».\n'
            'الصيغة: [{{"topic":"الموضوع كسؤال","side_a":"الموقف المؤيد","side_b":"الموقف المعارض",'
            '"category":"تصنيف","difficulty":"easy|medium|hard",'
            '"key_arguments":["حجتان قويتان لكل طرف"],"fallacies":["مغالطة محتملة يجب تجنبها"]}}]\n'
            'شروط: الموضوع متوازن (لكل طرف حجج حقيقية)، غير سياسي ولا ديني حساس، '
            'ومناسب للنقاش المدرسي. كل النصوص عربية.'
        ),
    },
    'whoplayer': {
        'name': 'مين اللاعب؟',
        'required': ['player', 'hints'],
        'fields': ['player', 'hints', 'difficulty', 'status', 'source'],
        'prompt': (
            'أنشئ {n} مجموعة تلميحات للعبة «مين اللاعب؟» عن لاعبي كرة القدم.\n'
            'الصيغة: [{\"player\":\"اسم اللاعب الكامل\",\"hints\":[\"تلميح عام\",\"تلميح متوسط\",\"تلميح متوسط\",\"تلميح كاشف\",\"تلميح كاشف\"],\"difficulty\":\"easy|medium|hard\"}]\n'
            'شروط: التلميحات متدرجة من العام إلى الخاص (المركز، الجنسية، النادي، الدوري، الإنجازات)، '
            'ومعلومات صحيحة موثوقة فقط. لا تخترع انتقالات أو ألقاباً. كل النصوص عربية.'
        ),
    },
    'seen_jeem': {
        'name': 'سين جيم',
        'required': ['question', 'answer', 'category', 'points'],
        'fields': ['question', 'answer', 'category', 'points', 'difficulty', 'status', 'source'],
        'prompt': (
            'أنشئ {n} سؤالاً للعبة "سين جيم" (Seen Jeem) - لعبة اختيار الإجابة مع فئات ونقاط.\n'
            'الصيغة: [{"question":"السؤال بالعربية","answer":"الإجابة الصحيحة","category":"الفئة","points":"200|400|600","difficulty":"easy|medium|hard"}]\n'
            'شروط: الأسئلة عربية واضحة ومختصرة، الإجابات دقيقة، الفئات متنوعة (علوم، تاريخ، جغرافيا، رياضة، تكنولوجيا، أدب)، '
            'لا توجد حروف لاتينية، لا تكرر الأسئلة.'
        ),
    },
    'minebali': {
        'name': 'مين في بالي؟',
        'required': ['name', 'gender', 'category', 'field', 'difficulty'],
        'fields': ['name', 'aliases', 'category', 'subcategory', 'work', 'gender',
                   'real', 'main', 'powers', 'field', 'role', 'country', 'era',
                   'difficulty', 'status', 'source'],
        'prompt': (
            'أنشئ {n} شخصية للعبة «مين في بالي؟» (تخمين شخصية بأسئلة نعم/لا).\n'
            'الصيغة الدقيقة لكل شخصية:\n'
            '{"name":"الاسم الكامل","aliases":["اسم شائع"],"category":"اسم الفئة نفسه بالضبط",'
            '"subcategory":"العمل أو المجال","work":"العمل الأشهر","gender":"ذكر أو أنثى",'
            '"real":true أو false,"main":true أو false,"powers":true أو false,'
            '"field":"المجال (مثال: نينجا، قرصان، مهاجم)","role":"نوع الشخصية",'
            '"country":"الجنسية أو فارغ","era":"الحقبة أو فارغ","difficulty":"easy|medium|hard"}\n'
            'قواعد إلزامية:\n'
            '1) gender يجب أن تكون «ذكر» أو «أنثى» فقط، وصحيحة فعلاً — لا تخمّن.\n'
            '2) real=true فقط للشخصيات الحقيقية (بشر موجودون)، وfalse للخيالية.\n'
            '3) powers=true فقط لمن لديه قدرات خارقة أو سحر أو قوة غير طبيعية.\n'
            '4) main=true إذا كانت بطلة أو من أبطال العمل الرئيسيين.\n'
            '5) كل الحقول النصية عربية، ممنوع حروف لاتينية أو أجنبية إلا الأسماء العلمية الضرورية.\n'
            '6) لا تكرر نفس الشخصية بصياغة مختلفة.\n'
            '7) كل معلومة يجب أن تكون صحيحة وموثوقة — لا تختلق شخصيات.\n'
        ),
    },
    'link': {
        'name': 'الرابط المشترك',
        'required': ['items', 'answer'],
        'fields': ['items', 'link', 'answer', 'alternatives', 'explanation', 'category', 'difficulty', 'status', 'source'],
        'prompt': (
            'أنشئ {n} لغز «الرابط المشترك» — مجموعة عناصر وعلاقة تجمعها.\n'
            'الصيغة: [{{"items":["عنصر1","عنصر2","عنصر3","عنصر4"],"link":"وصف الرابط",'
            '"answer":"الإجابة القصيرة","alternatives":["إجابات مقبولة بديلة"],'
            '"explanation":"لماذا تنتمي كل العناصر للرابط","category":"تصنيف","difficulty":"easy|medium|hard"}}]\n'
            'شروط: 4 عناصر كلها تدعم الرابط فعلاً، والرابط محدد (لا يقبل عشرات الإجابات)، '
            'والإجابة قصيرة. كل النصوص عربية.'
        ),
    },
    'draw_guess': {
        'name': 'ارسم وخمّن',
        'required': ['word'],
        'fields': ['word', 'category', 'difficulty', 'altAccepted', 'status', 'source'],
        'prompt': (
            'أنشئ {n} كلمةلعبة «ارسم وخمّن» (لوطة رسم + تخمين شفهي).\n'
            'الصيغة: [{"word":"الكلمة","category":"الفئة","difficulty":"سهل|متوسط|صعب|خلط","altAccepted":["بديل1","بديل2"]}]\n'
            'شروط: الكلمة عربية مفردة وواضحة، لا تحوي حروفا أجنبية، لا تكرر، '
            'واضحة للرسم (لاENTITY ولا jملة)، '
            'altAccepted تحتوي كلمة أو كلمتين فقط كبدائل مقبولة. '
            'الفئات: الحيوانات، الأفعال، الأشياء، الطعام، المشاهير، الأماكن، الكل. '
            'كل النصوص عربية.'
        ),
    },
}

CONTENT_GAMES = list(GAME_SCHEMAS.keys())


def validate_content(game, item):
    """Deterministic checks per game — the model alone is not trusted."""
    if game not in GAME_SCHEMAS:
        return False, 'لعبة غير معروفة'
    schema = GAME_SCHEMAS[game]
    if not isinstance(item, dict):
        return False, 'عنصر غير صالح'
    for f in schema['required']:
        v = item.get(f)
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v):
            return False, 'الحقل المطلوب ناقص: ' + f
    # no foreign scripts anywhere — but only in the content itself. Serialising
    # the item as JSON drags in the *keys* ("name", "category", ...) and the
    # structural enums ("difficulty":"medium"), which are legitimately Latin and
    # made every AI-generated row fail this check. Collect only string values.
    SKIP_KEYS = {'id', 'status', 'source', 'difficulty', 'created_at',
                 'updated_at', 'image', 'verified', 'answers_count', 'hidden'}
    if has_foreign(collect_text(item, SKIP_KEYS)):
        return False, 'يحتوي حروفاً غير عربية'
    if game == 'codenames':
        if len(str(item['word']).split()) > 3:
            return False, 'كلمة كود نيمز يجب أن تكون قصيرة'
    if game == 'detective':
        chars = item.get('characters') or []
        ev = item.get('evidence') or []
        if len(chars) < 3:
            return False, 'القضية تحتاج 3 شخصيات على الأقل'
        if len(ev) < 4:
            return False, 'القضية تحتاج 4 أدلة على الأقل'
        ids = [str(e.get('id')) for e in ev if isinstance(e, dict)]
        for k in (item.get('key_evidence') or []):
            if str(k) not in ids:
                return False, 'دليل أساسي غير موجود في قائمة الأدلة'
    if game == 'culprit':
        sus = item.get('suspects') or []
        if len(sus) < 3:
            return False, 'القضية تحتاج 3 مشتبهين على الأقل'
        names = [str(s.get('name')) for s in sus if isinstance(s, dict)]
        if str(item['culprit']) not in names:
            return False, 'المسؤول يجب أن يكون أحد المشتبهين'
    if game == 'link':
        if len(item.get('items') or []) < 3:
            return False, 'اللغز يحتاج 3 عناصر على الأقل'
    if game == 'whoplayer':
        if len(item.get('hints') or []) < 3:
            return False, 'يحتاج 3 تلميحات على الأقل'
    if game == 'minebali':
        if item.get('gender') not in ('ذكر', 'أنثى'):
            return False, 'الجنس يجب أن يكون «ذكر» أو «أنثى»'
        for k in ('real', 'main', 'powers'):
            if not isinstance(item.get(k), bool):
                return False, 'الحقل ' + k + ' يجب أن يكون قيمة منطقية'
        if not str(item.get('field', '')).strip():
            return False, 'مجال الشخصية مطلوب'
        if not str(item.get('category', '')).strip():
            return False, 'الفئة مطلوبة'
    return True, ''


def content_key(game, item):
    if game == 'codenames' or game == 'spy':
        return norm_ar(item.get('word', ''))
    if game == 'link':
        return norm_ar(' '.join(sorted(str(x) for x in (item.get('items') or []))))
    if game == 'whoplayer':
        return norm_ar(item.get('player', ''))
    if game == 'minebali':
        return norm_ar(item.get('name', ''))
    return norm_ar(item.get('title', '') or item.get('topic', ''))


def content_keys(game, item):
    """All keys that must be unique for this item.

    Character names get an extra key on the first token: the model happily
    writes «ميكاسا أكرمان» and «ميكاسا أكيرمان» in the same run, and the
    full-name key alone lets both through.
    """
    base = content_key(game, item)
    if game == 'minebali':
        n = norm_ar(item.get('name', ''))
        first = n.split(' ')[0] if n else ''
        return {base} | ({'first:' + first} if first else set())
    return {base}


@app.route('/api/content/games', methods=['GET'])
def content_games():
    out = []
    for g, s in GAME_SCHEMAS.items():
        items = load_json(content_file(g), [])
        out.append({'game': g, 'name': s['name'], 'count': len(items),
                    'approved': len([x for x in items if x.get('status') == 'approved']),
                    'pending': len([x for x in items if x.get('status') == 'pending_review']),
                    'archived': len([x for x in items if x.get('status') == 'archived'])})
    return jsonify({'games': out})


@app.route('/api/content/<game>', methods=['GET'])
def list_content(game):
    if game not in GAME_SCHEMAS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    items = load_json(content_file(game), [])
    status = request.args.get('status', '')
    source = request.args.get('source', '')
    search = request.args.get('search', '').strip()
    difficulty = request.args.get('difficulty', '')
    if status:
        items = [x for x in items if x.get('status') == status]
    elif request.args.get('include_archived') != '1':
        items = [x for x in items if x.get('status') != 'archived']
    if source:
        items = [x for x in items if x.get('source') == source]
    if difficulty:
        items = [x for x in items if x.get('difficulty') == difficulty]
    if search:
        s = norm_ar(search)
        items = [x for x in items if s in norm_ar(json.dumps(x, ensure_ascii=False))]
    return jsonify({'game': game, 'name': GAME_SCHEMAS[game]['name'],
                    'items': items, 'total': len(items)})


@app.route('/api/content/<game>', methods=['POST'])
def add_content(game):
    if game not in GAME_SCHEMAS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    item = request.get_json(silent=True) or {}
    item['id'] = item.get('id') or gen_id()
    item.setdefault('status', 'approved')
    item.setdefault('source', 'manual')
    item.setdefault('created_at', now())
    item['updated_at'] = now()
    ok, err = validate_content(game, item)
    if not ok:
        return jsonify({'error': err}), 400
    items = load_json(content_file(game), [])
    if any(content_keys(game, x) & content_keys(game, item) for x in items):
        return jsonify({'error': 'عنصر مكرر'}), 400
    items.append(item)
    save_json(content_file(game), items)
    return jsonify(item), 201


@app.route('/api/content/<game>/<cid>', methods=['PUT'])
def update_content(game, cid):
    if game not in GAME_SCHEMAS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    data = request.get_json(silent=True) or {}
    items = load_json(content_file(game), [])
    for i, it in enumerate(items):
        if it['id'] == cid:
            merged = dict(it); merged.update(data); merged['id'] = cid
            merged['updated_at'] = now()
            ok, err = validate_content(game, merged)
            if not ok:
                return jsonify({'error': err}), 400
            items[i] = merged
            save_json(content_file(game), items)
            return jsonify(merged)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/content/<game>/<cid>', methods=['DELETE'])
def delete_content(game, cid):
    if game not in GAME_SCHEMAS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    save_json(content_file(game), [x for x in load_json(content_file(game), []) if x['id'] != cid])
    return jsonify({'ok': True})


@app.route('/api/content/<game>/<cid>/status', methods=['POST'])
def set_content_status(game, cid):
    st = (request.get_json(silent=True) or {}).get('status', 'approved')
    items = load_json(content_file(game), [])
    for it in items:
        if it['id'] == cid:
            it['status'] = st
            it['updated_at'] = now()
            save_json(content_file(game), items)
            return jsonify(it)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/content/<game>/bulk-status', methods=['POST'])
def bulk_content_status(game):
    body = request.get_json(silent=True) or {}
    ids = set(body.get('ids', []))
    st = body.get('status', 'approved')
    items = load_json(content_file(game), [])
    n = 0
    for it in items:
        if it['id'] in ids:
            it['status'] = st; it['updated_at'] = now(); n += 1
    save_json(content_file(game), items)
    return jsonify({'ok': True, 'updated': n})


@app.route('/api/content/<game>/purge-bad', methods=['POST'])
def purge_content(game):
    items = load_json(content_file(game), [])
    keep, dropped = [], []
    for it in items:
        if it.get('status') == 'pending_review':
            ok, err = validate_content(game, it)
            if not ok:
                dropped.append({'item': str(it.get('word') or it.get('title') or '')[:50], 'reason': err})
                continue
        keep.append(it)
    save_json(content_file(game), keep)
    return jsonify({'ok': True, 'dropped': len(dropped), 'sample': dropped[:10]})


@app.route('/api/content/<game>/export', methods=['GET'])
def export_content(game):
    path = os.path.join(tempfile.gettempdir(), 'ameen-' + game + '-export.json')
    save_json(path, load_json(content_file(game), []))
    return send_file(path, as_attachment=True, download_name=game + '-content.json',
                     mimetype='application/json')


@app.route('/api/content/<game>/import', methods=['POST'])
def import_content(game):
    body = request.get_json(silent=True) or {}
    incoming = body.get('items') or []
    mode = body.get('mode', 'preview')
    items = load_json(content_file(game), [])
    keys = set()
    for x in items:
        keys |= content_keys(game, x)
    new, dups, invalid = [], [], []
    for it in incoming:
        ok, err = validate_content(game, it)
        if not ok:
            invalid.append({'item': str(it)[:60], 'reason': err}); continue
        k = content_keys(game, it)
        if k & keys:
            dups.append({'item': str(it.get('word') or it.get('title') or it.get('name') or '')[:50], 'reason': 'مكرر'}); continue
        keys |= k
        new.append(it)
    if mode == 'apply':
        for it in new:
            it['id'] = gen_id(); it.setdefault('status', 'approved')
            it.setdefault('source', 'import'); it.setdefault('created_at', now())
            items.append(it)
        save_json(content_file(game), items)
    return jsonify({'mode': mode, 'total_in_file': len(incoming), 'new_count': len(new),
                    'duplicate_count': len(dups), 'invalid_count': len(invalid),
                    'invalid': invalid[:20], 'duplicates': dups[:20]})


@app.route('/api/content/<game>/generate', methods=['POST'])
def generate_content(game):
    if game not in GAME_SCHEMAS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ'}), 400
    body = request.get_json(silent=True) or {}
    want = max(1, min(int(body.get('count', 5)), 10))
    difficulty = body.get('difficulty', 'medium')
    category = str(body.get('category', '')).strip()

    items = load_json(content_file(game), [])
    existing = set()
    for x in items:
        existing |= content_keys(game, x)
    avoid = ''
    if existing:
        sample = [str(x.get('word') or x.get('title') or x.get('topic') or x.get('player') or x.get('name') or '') for x in items]
        sample = [s for s in sample if s][-25:]
        if sample:
            avoid = '\nلا تكرر هذه العناصر: ' + '، '.join(sample)

    diff_ar = {'easy': 'سهل', 'medium': 'متوسط', 'hard': 'صعب'}.get(difficulty, 'متوسط')
    prompt = GAME_SCHEMAS[game]['prompt'].replace('{n}', str(want))
    if '__CATEGORY__' in prompt:
        prompt = prompt.replace('__CATEGORY__', category or GAME_SCHEMAS[game]['name'])
    prompt += '\nمستوى الصعوبة المطلوب: ' + diff_ar + '.'
    if category:
        prompt += '\nالموضوع/الفئة المطلوبة: ' + category + '.'
    prompt += avoid + '\nأعد مصفوفة JSON فقط بلا أي نص إضافي.'

    validated, rejected = [], []
    last_error = ''
    for attempt in range(2):
        if len(validated) >= want:
            break
        try:
            p = prompt if attempt == 0 else prompt + (
                '\n\nتذكير: كل النصوص عربية فقط، ولا حروف لاتينية أو أجنبية إطلاقاً. '
                'التزم بالحقول المذكورة حرفياً. أعد JSON صالحاً فقط.')
            content = nvidia_chat(p, timeout=90, temperature=0.85 if attempt else 0.7)
            got = extract_json_array(content)
        except Exception as e:
            last_error = str(e)
            continue
        for it in got:
            if len(validated) >= want:
                break
            if not isinstance(it, dict):
                continue
            it['id'] = gen_id()
            it['status'] = 'pending_review'
            it['source'] = 'ai'
            it['created_at'] = now()
            it['updated_at'] = now()
            it.setdefault('difficulty', difficulty)
            ok, err = validate_content(game, it)
            if not ok:
                rejected.append({'item': str(it.get('word') or it.get('title') or '')[:50], 'reason': err})
                continue
            k = content_keys(game, it)
            if k & keys:
                rejected.append({'item': str(it.get('name') or it.get('word') or it.get('title') or '')[:50], 'reason': 'مكرر'})
                continue
            keys |= k
            validated.append(it)

    items.extend(validated)
    save_json(content_file(game), items)
    resp = {'items': validated, 'count': len(validated), 'requested': want,
            'rejected': rejected[:20], 'rejected_count': len(rejected)}
    if not validated and last_error:
        resp['error'] = 'تعذّر التوليد: ' + last_error
        return jsonify(resp), 500
    if not validated:
        resp['error'] = 'لم يُقبل أي عنصر من النموذج — أعد المحاولة'
    return jsonify(resp)


@app.route('/api/content/stats', methods=['GET'])
def content_stats():
    total = approved = pending = 0
    per_game = {}
    for g in CONTENT_GAMES:
        items = load_json(content_file(g), [])
        a = len([x for x in items if x.get('status') == 'approved'])
        p = len([x for x in items if x.get('status') == 'pending_review'])
        per_game[g] = {'name': GAME_SCHEMAS[g]['name'], 'total': len(items), 'approved': a, 'pending': p}
        total += len(items); approved += a; pending += p
    return jsonify({'total': total, 'approved': approved, 'pending': pending, 'per_game': per_game})


# ============ MINE BALI — أسئلة اللاعبين المخصصة ============
# Questions the asker types are often about a trait the character bank does not
# model ("هل هو نينجا؟"). Instead of dead-ending with "غير متاحة", the second
# player answers and the pair is stored, so the same question about the same
# character is answered instantly next time.
MB_QA_FILE = os.path.join(CONTENT_DIR, 'minebali_qa.json')


def mb_qa_key(question, char_id):
    return norm_ar(question) + '|' + str(char_id or '')


@app.route('/api/minebali/qa', methods=['GET'])
def list_mb_qa():
    items = load_json(MB_QA_FILE, [])
    q = request.args.get('q', '').strip()
    char_id = request.args.get('char_id', '').strip()
    if q:
        nq = norm_ar(q)
        hits = [x for x in items if norm_ar(x.get('question', '')) == nq]
        if char_id:
            same = [x for x in hits if str(x.get('char_id', '')) == char_id]
            if same:
                hits = same
        return jsonify({'items': hits, 'total': len(hits)})
    return jsonify({'items': items, 'total': len(items)})


@app.route('/api/minebali/qa', methods=['POST'])
def save_mb_qa():
    body = request.get_json(silent=True) or {}
    q = str(body.get('question', '')).strip()
    a = str(body.get('answer', '')).strip()
    char_id = str(body.get('char_id', '')).strip()
    char_name = str(body.get('char_name', '')).strip()
    if not q:
        return jsonify({'error': 'نص السؤال مطلوب'}), 400
    if a not in ('نعم', 'لا'):
        return jsonify({'error': 'الإجابة يجب أن تكون «نعم» أو «لا»'}), 400
    items = load_json(MB_QA_FILE, [])
    k = mb_qa_key(q, char_id)
    for i, x in enumerate(items):
        if mb_qa_key(x.get('question', ''), x.get('char_id', '')) == k:
            items[i].update({'answer': a,
                             'char_name': char_name or x.get('char_name', ''),
                             'updated_at': now(),
                             'answers_count': int(x.get('answers_count', 1)) + 1})
            save_json(MB_QA_FILE, items)
            return jsonify(items[i])
    row = {'id': gen_id(), 'question': q, 'answer': a, 'char_id': char_id,
           'char_name': char_name,
           'asked_by': str(body.get('asked_by', '')).strip(),
           'answered_by': str(body.get('answered_by', '')).strip(),
           'created_at': now(), 'updated_at': now(), 'answers_count': 1}
    items.append(row)
    save_json(MB_QA_FILE, items)
    return jsonify(row), 201


@app.route('/api/minebali/qa/<qid>', methods=['DELETE'])
def delete_mb_qa(qid):
    if not is_admin(request):
        return jsonify({'error': 'غير مصرّح'}), 401
    save_json(MB_QA_FILE, [x for x in load_json(MB_QA_FILE, []) if x.get('id') != qid])
    return jsonify({'ok': True})


@app.route('/api/categories/groups', methods=['GET'])
def category_groups():
    cats = load_json(CAT_FILE, [])
    groups = {}
    for c in cats:
        g = (c.get('group') or '').strip() or 'عام'
        groups.setdefault(g, []).append(c['id'])
    out = [{'name': g, 'count': len(ids), 'category_ids': ids} for g, ids in groups.items()]
    out.sort(key=lambda x: -x['count'])
    return jsonify({'groups': out})


# ============ ADMIN AUTH ============
# Two kinds of credential unlock the admin panel — either one works:
#   1. One configured in the hosting dashboard:
#        ADMIN_PASSWORD      — plain text (simplest to set)
#        ADMIN_PASSWORD_HASH — SHA-256 hex, 64 characters
#   2. The built-in recovery password (below), which is ALWAYS accepted.
# The recovery credential exists so a wrong value typed into a hosting dashboard
# can never lock the admin out for good. Note this repository is public, so the
# built-in password is already visible to anyone reading the code — a dashboard
# value adds obscurity, not real secrecy. Make the repo private if you need a
# genuinely secret admin password.
DEFAULT_ADMIN_PASSWORD = 'ameen2323'
DEFAULT_ADMIN_HASH = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode('utf-8')).hexdigest()


def _configured_admin_hashes():
    """Collect the extra credentials configured through the environment."""
    found = []
    plain = (os.environ.get('ADMIN_PASSWORD') or '').strip()
    if plain:
        found.append(('ADMIN_PASSWORD', hashlib.sha256(plain.encode('utf-8')).hexdigest()))
    raw = (os.environ.get('ADMIN_PASSWORD_HASH') or '').strip()
    if raw:
        if re.fullmatch(r'[0-9a-fA-F]{64}', raw):
            found.append(('ADMIN_PASSWORD_HASH', raw.lower()))
        else:
            print('[admin] WARNING: ADMIN_PASSWORD_HASH is not a valid 64-character '
                  'SHA-256 hex value, so it was ignored. Set ADMIN_PASSWORD (plain '
                  'text) instead if you want your own password.', flush=True)
    return found


ADMIN_HASHES = _configured_admin_hashes()
# The recovery hash is always accepted, so a bad dashboard value cannot lock us out.
if not any(h == DEFAULT_ADMIN_HASH for _, h in ADMIN_HASHES):
    ADMIN_HASHES.append(('built-in recovery password', DEFAULT_ADMIN_HASH))
ADMIN_TOKENS = set()
print('[admin] admin password sources: ' + ', '.join(n for n, _ in ADMIN_HASHES), flush=True)


def is_admin_password(pw):
    """True when pw matches any accepted admin credential."""
    if not pw:
        return False
    digest = hashlib.sha256(str(pw).encode('utf-8')).hexdigest()
    return any(digest == h for _, h in ADMIN_HASHES)


def is_admin(req):
    return req.headers.get('X-Admin-Token', '') in ADMIN_TOKENS


def require_admin(fn):
    def wrapper(*a, **kw):
        if not is_admin(request):
            return jsonify({'error': 'غير مصرّح — سجّل الدخول إلى لوحة الإدارة'}), 401
        return fn(*a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    body = request.get_json(silent=True) or {}
    pw = str(body.get('password', ''))
    if is_admin_password(pw):
        token = uuid.uuid4().hex
        ADMIN_TOKENS.add(token)
        return jsonify({'ok': True, 'token': token})
    return jsonify({'error': 'كلمة المرور غير صحيحة'}), 401


@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    return jsonify({'ok': is_admin(request)})


# Any write to content APIs requires an admin token. Public gameplay stays open:
# players only need to READ questions, and the AI match judge is part of gameplay.
GUARDED_PREFIXES = ('/api/questions', '/api/categories', '/api/players', '/api/import',
                    '/api/pending', '/api/settings', '/api/ai/generate',
                    '/api/ai/run', '/api/ai/job', '/api/ai/progress/clear')


@app.before_request
def guard_admin_writes():
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    if request.path == '/api/admin/login':
        return None
    if request.path.startswith(GUARDED_PREFIXES) and not is_admin(request):
        return jsonify({'error': 'غير مصرّح — سجّل الدخول إلى لوحة الإدارة'}), 401
    return None


# ============ SETTINGS ============
DEFAULT_SETTINGS = {
    'siteTitle': 'ألعاب أمين',
    'defaultQuizTimer': 30,
    'defaultAuctionBudget': 100,
    'defaultAuctionUnit': 'مليون',
    'defaultBidDuration': 30,
    'defaultPlayersNeeded': 5,
    'defaultBoardCells': 28,
    'soundDefault': True,
    'aiBatchSize': 10,
    'aiModel': 'nvidia/nemotron-3-super-120b-a12b',
    'aiUnderPct': 20,
    'aiMediumPct': 60,
    'aiHardPct': 20,
}


@app.route('/api/settings', methods=['GET'])
def get_settings():
    s = dict(DEFAULT_SETTINGS)
    s.update(load_json(SETTINGS_FILE, {}))
    return jsonify(s)


@app.route('/api/settings', methods=['POST'])
@require_admin
def save_settings():
    body = request.get_json(silent=True) or {}
    s = dict(DEFAULT_SETTINGS)
    s.update(load_json(SETTINGS_FILE, {}))
    s.update(body)
    save_json(SETTINGS_FILE, s)
    return jsonify(s)


# ============ AI (NVIDIA) ============
NVIDIA_API_KEY = os.environ.get('NVIDIA_API_KEY', '')
NVIDIA_MODEL = os.environ.get('NVIDIA_MODEL', 'nvidia/nemotron-3-super-120b-a12b')
NVIDIA_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'


def current_model():
    """The model actually in use (falls back from the .env choice if needed)."""
    if _USED_MODEL['name']:
        return _USED_MODEL['name']
    s = load_json(SETTINGS_FILE, {})
    return s.get('aiModel') or NVIDIA_MODEL


FALLBACK_MODELS = ['nvidia/nemotron-3-ultra-550b-a55b',
                   'nvidia/nemotron-3.5-lightning-30b-a3b']
_USED_MODEL = {'name': ''}


def _nvidia_call(model, prompt, timeout, temperature):
    import urllib.request
    req = urllib.request.Request(
        NVIDIA_URL,
        data=json.dumps({
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': temperature,
            'chat_template_kwargs': {'enable_thinking': False},
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + NVIDIA_API_KEY})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode('utf-8'))
    return result['choices'][0]['message']['content']


def nvidia_chat(prompt, timeout=90, temperature=0.7):
    """Call the configured model, falling back when the account lacks access.

    NVIDIA returns HTTP 404 "Function ... not found for account" for a model the
    account is not entitled to, even though the model is listed publicly. The
    admin panel still shows the .env choice; generation degrades to a model that
    works instead of failing outright.
    """
    import urllib.error
    chosen = current_model()
    last = ''
    for model in [chosen] + [m for m in FALLBACK_MODELS if m != chosen]:
        try:
            out = _nvidia_call(model, prompt, timeout, temperature)
            _USED_MODEL['name'] = model
            return out
        except urllib.error.HTTPError as e:
            last = 'HTTP %s %s' % (e.code, e.read().decode('utf-8')[:160])
            if e.code == 404:
                continue          # not entitled to this one -> try the next
            if e.code in (429, 500, 502, 503, 504):
                continue
            raise
        except Exception as e:
            last = '%s: %s' % (type(e).__name__, e)
    raise RuntimeError(last or 'all models failed')


AVAILABLE_MODELS = [
    'nvidia/nemotron-3-super-120b-a12b',
    'nvidia/nemotron-3.5-lightning-30b-a3b',
    'nvidia/nemotron-3-ultra-550b-a55b',
    'nvidia/nemotron-4-340b-instruct',
    'openai/gpt-oss-20b',
    'moonshotai/kimi-k2.6',
]


@app.route('/api/ai/models', methods=['GET'])
def ai_models():
    return jsonify({'models': AVAILABLE_MODELS, 'current': current_model()})


@app.route('/api/ai/test', methods=['GET'])
def ai_test():
    if not NVIDIA_API_KEY:
        return jsonify({'status': 'no_key',
                        'message': 'لم يتم إعداد NVIDIA_API_KEY. أضفه في ملف .env ثم أعد تشغيل الخادم.'})
    try:
        out = nvidia_chat('قل كلمة: جاهز', timeout=25)
        return jsonify({'status': 'ok', 'model': current_model(), 'response': out.strip()[:200]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def extract_json_array(text):
    """Robust extraction: strip markdown fences, tolerate prose around the array
    and trailing commas. The model sometimes wraps JSON in ```json blocks."""
    if not text or not str(text).strip():
        raise ValueError('رد فارغ من النموذج')
    t = str(text).strip()
    t = re.sub(r'```(?:json|JSON)?', '', t).strip()
    m = re.search(r'\[.*\]', t, re.DOTALL)
    raw = m.group() if m else t
    raw = re.sub(r',\s*([\]}])', r'\1', raw)
    return json.loads(raw)


def build_ai_prompt(game, letter, cat_name, ask, difficulty, avoid_block, strict, cat_desc=''):
    """strict=True is the retry prompt: explicit examples + hard rules."""
    diff_ar = {'under': 'تحت المتوسط', 'easy': 'سهل', 'medium': 'متوسط', 'hard': 'صعب'}.get(difficulty, 'متوسط')

    if game == 'letters':
        base = ('أنت معدّ أسئلة مسابقات عربية. المطلوب: ' + str(ask) + ' سؤالاً جديداً '
                'إجابتها كلمة عربية واحدة تبدأ بحرف «' + letter + '».\n'
                'مستوى الصعوبة: ' + diff_ar + '.\n')
        rules = (
            'قواعد صارمة:\n'
            '1) الإجابة كلمة واحدة فقط (أو كلمتان بحد أقصى) — لا جملة ولا شرح.\n'
            '2) الإجابة مكتوبة بالحروف العربية فقط. ممنوع أي حرف لاتيني أو صيني أو كوري.\n'
            '3) الإجابة تبدأ فعلاً بحرف «' + letter + '». إن كانت معرفة بـ«ال» فالحرف بعدها.\n'
            '4) نص السؤال لا يحتوي على الإجابة نفسها.\n'
            '5) لا تكرر أي سؤال ولا تعِد صياغة سؤال بمعنى قريب.\n'
            '6) كل سؤال معلومة صحيحة وواقعية.\n'
            '7) أعد مصفوفة JSON فقط بلا أي نص إضافي، كل عنصر بالشكل: '
            '{"question":"...","answer":"...","explanation":"..."}.\n')
        if strict:
            rules += ('\nأمثلة على الشكل الصحيح (لحرف آخر للتوضيح):\n'
                      '{"question": "ما هي عاصمة اليابان؟", "answer": "طوكيو", "explanation": "عاصمة اليابان"}\n'
                      '{"question": "ما هو الحيوان الذي ينسج الشباك؟", "answer": "العنكبوت", "explanation": "يُعرف بنسج الشباك"}\n'
                      'لاحظ: الإجابة كلمة واحدة، عربية، تبدأ بالحرف المطلوب.\n'
                      'أعد الآن مصفوفة JSON فقط بلا أي نص إضافي.\n')
        return base + rules + avoid_block

    if game == 'million':
        base = ('أنت معدّ أسئلة برامج المسابقات. المطلوب: ' + str(ask) + ' سؤال اختيار من متعدد.\n'
                'مستوى الصعوبة: ' + diff_ar + '.\n')
        rules = (
            'قواعد صارمة:\n'
            '1) كل سؤال له 4 خيارات بالضبط، خيار واحد صحيح والثلاثة الأخرى خاطئة لكنها مقنعة.\n'
            '2) الإجابة الصحيحة مطابقة حرفياً لأحد الخيارات الأربعة.\n'
            '3) كل النصوص بالعربية فقط — ممنوع أي حرف لاتيني أو صيني أو كوري.\n'
            '4) الخيارات الأربعة مختلفة عن بعضها.\n'
            '5) لا تكرر أي سؤال.\n'
            '6) أعد مصفوفة JSON فقط بلا أي نص إضافي، كل عنصر بالشكل: '
            '{"question":"...","options":["...","...","...","..."],"answer":"...","explanation":"..."}.\n')
        if strict:
            rules += ('\nمثال على الشكل الصحيح:\n'
                      '{"question": "ما هي عاصمة اليابان؟", "options": ["طوكيو","أوساكا","كيوتو","ناغويا"], '
                      '"answer": "طوكيو", "explanation": "عاصمة اليابان"}\n'
                      'أعد الآن مصفوفة JSON فقط بلا أي نص إضافي.\n')
        return base + rules + avoid_block

    base = ('أنت معدّ أسئلة مسابقات ثقافية. المطلوب: ' + str(ask) +
            ' سؤالاً في فئة «' + cat_name + '».\nمستوى الصعوبة: ' + diff_ar + '.\n')
    if cat_desc:
        base += ('\nوصف الفئة: ' + cat_desc + '\n'
                 'كل سؤال يجب أن يكون عن هذا الموضوع حصراً.\n')
    rules = (
        'قواعد صارمة:\n'
        '1) الإجابة كلمة أو رقم أو اسم قصير — لا جملة طويلة.\n'
        '2) كل النصوص بالعربية فقط — ممنوع أي حرف لاتيني أو صيني أو كوري.\n'
        '3) نص السؤال لا يحتوي على الإجابة.\n'
        '4) لا تكرر أي سؤال، وكل سؤال معلومة صحيحة.\n'
        '5) كل سؤال يجب أن يكون عن فئة «' + cat_name + '» فقط. '
        'ممنوع سؤال عن موضوع آخر (رياضة، تاريخ، دين، تقنية...) مهما كان قريباً.\n'
        '6) أعد مصفوفة JSON فقط بلا أي نص إضافي، كل عنصر بالشكل: '
        '{"question":"...","answer":"...","explanation":"..."}.\n')
    if strict:
        rules += ('\nمثال على الشكل الصحيح (فئة مختلفة للتوضيح فقط):\n'
                  '{"question": "ما هي أكبر قارة مساحةً؟", "answer": "آسيا", "explanation": "قارات العالم"}\n'
                  'لاحظ: المهم هو الشكل، أما الموضوع فيجب أن يكون عن فئة «' + cat_name + '».\n'
                  'أعد الآن مصفوفة JSON فقط بلا أي نص إضافي.\n')
    return base + rules + avoid_block


def parse_bool_array(content, n):
    """Accept [true,false], ["true","false"], [{"ok":true}] or bare tokens.

    Returns a list of n bools, or None when the reply cannot be trusted — the
    caller then keeps everything, because dropping valid questions is worse
    than admitting one bad one.
    """
    m = re.search(r'\[.*\]', content, re.DOTALL)
    if m:
        try:
            arr = json.loads(m.group())
        except Exception:
            arr = None
        if isinstance(arr, list) and len(arr) == n:
            out = []
            for x in arr:
                if isinstance(x, bool):
                    out.append(x)
                elif isinstance(x, str) and x.strip().lower() in ('true', 'false'):
                    out.append(x.strip().lower() == 'true')
                elif isinstance(x, dict) and 'ok' in x:
                    out.append(bool(x['ok']))
                else:
                    return None
            return out
    toks = re.findall(r'\b(true|false)\b', content, re.IGNORECASE)
    if len(toks) >= n:
        return [t.lower() == 'true' for t in toks[:n]]
    return None


def verify_relevance(items, cat_name, cat_desc):
    """Ask the model which generated questions really belong to the category.

    A term-overlap filter is too brittle here: for a broad category such as
    'الثقافة الإسلامية' the model's phrasing ('كم عدد سور القرآن الكريم؟')
    shares no token with the category name, yet the question is perfectly on
    topic. The model itself is the reliable judge.
    """
    if not items:
        return []
    payload = [{'question': it.get('question', '')} for it in items]
    prompt = (
        'أنت مدقق لمحتوى مسابقات. الفئة المطلوبة هي: «' + cat_name + '».\n'
        'وصف الفئة: ' + (cat_desc or 'غير محدد') + '\n\n'
        'هل كل سؤال من الأسئلة التالية عن هذه الفئة تحديداً؟ '
        'اعتبر السؤال صحيحاً (true) فقط إذا كان موضوعه فعلاً داخل الفئة، '
        'وأعد مصفوفة JSON من قيم منطقية بنفس العدد وبنفس الترتيب تماماً:\n'
        '[true, false, ...]\n\n'
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        content = nvidia_chat(prompt, timeout=60, temperature=0.15)
        return parse_bool_array(content, len(items))
    except Exception:
        return None


# ============ AI GENERATION PROGRESS ============
AI_PROGRESS = {'running': False, 'label': '', 'requested': 0, 'completed': 0,
               'accepted': 0, 'rejected': 0, 'current_attempt': 0, 'total_attempts': 0,
               'items': [], 'last_error': '', 'finished_at': ''}

def ai_progress_start(label, requested, total_attempts=2):
    global AI_PROGRESS
    AI_PROGRESS = {'running': True, 'label': label, 'requested': int(requested),
                   'completed': 0, 'accepted': 0, 'rejected': 0,
                   'current_attempt': 0, 'total_attempts': int(total_attempts),
                   'items': [], 'last_error': '', 'finished_at': ''}
    return dict(AI_PROGRESS)

def ai_progress_add(item, ok, reason=''):
    if ok:
        AI_PROGRESS['accepted'] += 1
        AI_PROGRESS['items'].append({'question': item.get('question', ''), 'answer': item.get('answer', ''), 'ok': True})
    else:
        AI_PROGRESS['rejected'] += 1
        AI_PROGRESS['items'].append({'question': str(item)[:80], 'ok': False, 'reason': reason})
    AI_PROGRESS['completed'] = AI_PROGRESS['accepted'] + AI_PROGRESS['rejected']

def ai_progress_finish(error=''):
    AI_PROGRESS['running'] = False
    AI_PROGRESS['last_error'] = error
    AI_PROGRESS['finished_at'] = now()
    return dict(AI_PROGRESS)


@app.route('/api/ai/progress/clear', methods=['POST'])
def ai_generation_progress_clear():
    global AI_PROGRESS
    AI_PROGRESS = {'running': False, 'label': '', 'requested': 0, 'completed': 0,
                   'accepted': 0, 'rejected': 0, 'current_attempt': 0, 'total_attempts': 0,
                   'items': [], 'last_error': '', 'finished_at': now()}
    return jsonify(dict(AI_PROGRESS))


@app.route('/api/ai/generate', methods=['POST'])
def ai_generate():
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ — راجع إعدادات الذكاء الاصطناعي'}), 400

    data = request.get_json(silent=True) or {}
    game = data.get('game', 'quiz')
    letter = data.get('letter', '')
    category_id = data.get('category', '')
    want = max(1, min(int(data.get('count', 5)), 20))
    difficulty = data.get('difficulty', 'medium')

    label = 'توليد ' + str(want) + ' سؤال (' + game + ((' - حرف ' + letter) if letter else '') + ')'
    ai_progress_start(label, want)

    cats = {c['id']: c for c in load_json(CAT_FILE, [])}
    cat = cats.get(category_id) or {}
    cat_name = cat.get('name', '')
    cat_desc = cat.get('description', '') or ''
    if not cat_name:
        ai_progress_finish('الفئة غير موجودة')
        return jsonify({'error': 'الفئة غير موجودة — اختر فئة صحيحة'}), 400

    existing_all = load_bank()
    if game == 'letters':
        prior = [q for q in existing_all if q.get('letter') == letter]
    elif game == 'million':
        prior = [q for q in existing_all if q.get('game') == 'million']
    else:
        prior = [q for q in existing_all if q.get('category_id') == category_id]
    prior_texts = [str(q.get('question', '')).strip() for q in prior if q.get('question')]
    prior_sample = prior_texts[-20:] if len(prior_texts) > 20 else prior_texts
    avoid_block = ''
    if prior_sample:
        avoid_block = ('\n\nلا تكرر هذه الأسئلة:\n' +
                       '\n'.join('- ' + t for t in prior_sample))

    existing_keys = {q_key(q) for q in existing_all}
    validated, rejected = [], []
    last_error = ''

    # Two attempts only: the 120B model is slow, so keep the total under ~2 minutes.
    for attempt in range(2):
        need = want - len(validated)
        if need <= 0:
            break
        ask = min(20, max(need * 2, need + 2))     # ask for a few extras to survive rejects
        AI_PROGRESS['current_attempt'] = attempt + 1
        prompt = build_ai_prompt(game, letter, cat_name, ask, difficulty, avoid_block,
                                strict=(attempt > 0), cat_desc=cat_desc)
        try:
            content = nvidia_chat(prompt, timeout=75, temperature=0.85 if attempt else 0.7)
            items = extract_json_array(content)
        except Exception as e:
            last_error = str(e)
            continue

        # Batch relevance gate (quiz only): one model call judges every item of
        # this round against the category, instead of a brittle term-overlap.
        off_topic = set()
        if game == 'quiz':
            cands = [it for it in items
                     if isinstance(it, dict) and it.get('question')]
            verdicts = verify_relevance(cands, cat_name, cat_desc)
            if verdicts is not None:
                for it, ok in zip(cands, verdicts):
                    if not ok:
                        off_topic.add(norm_ar(it.get('question', '')))
                if off_topic:
                    print('    ( relevance check: %d/%d off-topic )'
                          % (len(off_topic), len(cands)))

        for it in items:
            if len(validated) >= want:
                break
            if not isinstance(it, dict) or not it.get('question') or not it.get('answer'):
                ai_progress_add(it, False, 'بيانات ناقصة')
                continue
            # Reject anything off-topic for the chosen category: the model
            # otherwise fills a niche category (an anime, a novel) with generic
            # trivia about whatever the prompt reminded it of.
            if game == 'quiz' and norm_ar(str(it.get('question', ''))) in off_topic:
                ai_progress_add(it, False, 'خارج عن الفئة')
                rejected.append({'question': str(it.get('question', ''))[:80],
                                 'answer': str(it.get('answer', ''))[:40],
                                 'reason': 'خارج عن الفئة'})
                continue
            q = {'id': gen_id(), 'game': game,
                 'question': str(it['question']).strip(),
                 'answer': str(it['answer']).strip(),
                 'explanation': str(it.get('explanation', '')).strip(),
                 'difficulty': difficulty, 'status': 'pending_review', 'source': 'ai',
                 'created_at': now(), 'updated_at': now(),
                 'alternatives': [], 'hint': '', 'image': ''}
            if game == 'letters':
                q['letter'] = letter
            elif game == 'million':
                q['options'] = [str(o).strip() for o in (it.get('options') or [])][:4]
                q['points'] = 200 if difficulty in ('easy', 'under') else (600 if difficulty == 'hard' else 400)
            else:
                q['category_id'] = category_id
                q['category_name'] = cat_name
                q['points'] = 200 if difficulty in ('easy', 'under') else (600 if difficulty == 'hard' else 400)

            ok, err = validate_question(q)
            if not ok:
                rejected.append({'question': q['question'][:80], 'answer': q['answer'][:40], 'reason': err})
                ai_progress_add(q, False, err)
                continue
            if q_key(q) in existing_keys:
                rejected.append({'question': q['question'][:80], 'answer': q['answer'][:40], 'reason': 'سؤال مكرر'})
                ai_progress_add(q, False, 'مكرر')
                continue
            existing_keys.add(q_key(q))
            validated.append(q)
            ai_progress_add(q, True)

    all_qs = load_bank()
    all_qs.extend(validated)
    save_json(Q_FILE, all_qs)

    resp = {'questions': validated, 'count': len(validated),
            'requested': want, 'rejected': rejected, 'rejected_count': len(rejected)}
    if not validated and last_error:
        resp['error'] = 'تعذّر التوليد: ' + last_error
        ai_progress_finish(last_error)
        return jsonify(resp), 500
    if not validated:
        resp['error'] = 'لم يُقبل أي سؤال من النموذج — أعد المحاولة أو جرّب حرفاً/فئة أخرى'
        ai_progress_finish(resp['error'])
    else:
        ai_progress_finish()
    return jsonify(resp)


@app.route('/api/ai/match', methods=['POST'])
def ai_match():
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ — راجع إعدادات الذكاء الاصطناعي'}), 400
    body = request.get_json(silent=True) or {}
    squads = body.get('squads') or []
    if len(squads) < 2:
        return jsonify({'error': 'مطلوب تشكيلتان على الأقل'}), 400
    lines = []
    for s in squads:
        names = '، '.join(str(p.get('name', '')) + ' (' + str(p.get('rating', '')) + ')' for p in s.get('squad', []))
        lines.append('- ' + str(s.get('name', '?')) + ' — التقييم ' + str(s.get('rating', 0)) +
                     ' — اللاعبون: ' + (names or 'لا يوجد'))
    prompt = ('أنت معلّق رياضي عربي. هذه فرق تشكّلت من مزاد لاعبين:\n' + '\n'.join(lines) + '\n\n'
              'اكتب سيناريو مباراة قصير (5 إلى 8 أسطر) بينهم بأسلوب معلّق مشوّق، '
              'ثم حدّد الفائز والنتيجة النهائية.\n'
              'أعد النتيجة بصيغة JSON فقط:\n'
              '{"scenario": "نص السيناريو", "winner": "اسم الفريق الفائز", "score": "3-1", "reason": "سبب مختصر"}')
    try:
        content = nvidia_chat(prompt, temperature=0.9)
        m = re.search(r'\{.*\}', content, re.DOTALL)
        return jsonify(json.loads(m.group() if m else content))
    except Exception as e:
        return jsonify({'error': 'تعذّر توليد سيناريو المباراة: ' + str(e)}), 500


@app.route('/api/ai/evaluate-debate', methods=['POST'])
def ai_evaluate_debate():
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ'}), 400
    body = request.get_json(silent=True) or {}
    topic = str(body.get('topic', '')).strip()
    side_a_args = body.get('side_a_args') or []
    side_b_args = body.get('side_b_args') or []
    if not topic:
        return jsonify({'error': 'الموضوع مطلوب'}), 400
    if not side_a_args and not side_b_args:
        return jsonify({'error': 'حجج مطلوبة'}), 400
    a_text = '\n'.join('- ' + str(a) for a in side_a_args) if side_a_args else '(لا حجج)'
    b_text = '\n'.join('- ' + str(a) for a in side_b_args) if side_b_args else '(لا حجج)'
    prompt = (
        'أنت مُحكّم نقاش محترف. قيّم حجج الفريقين في النقاش التالي.\n\n'
        'الموضوع: ' + topic + '\n\n'
        'حجج الفريق الأول (المؤيد):\n' + a_text + '\n\n'
        'حجج الفريق الثاني (المعارض):\n' + b_text + '\n\n'
        'معايير التقييم:\n'
        '1. وضوح الفكرة (0-10)\n'
        '2. الترابط المنطقي (0-10)\n'
        '3. قوة الأدلة (0-10)\n'
        '4. الاستجابة للاعتراضات (0-10)\n'
        '5. الدقة (0-10)\n\n'
        'أعد النتيجة بصيغة JSON فقط:\n'
        '{"side_a":{"scores":{"وضوح الفكرة":8,"الترابط المنطقي":7,"قوة الأدلة":9,'
        '"الاستجابة للاعتراضات":6,"الدقة":8},"feedback":"تقييم مفصل","total":38},'
        '"side_b":{"scores":{"وضوح الفكرة":7,"الترابط المنطقي":8,"قوة الأدلة":7,'
        '"الاستجابة للاعتراضات":9,"الدقة":8},"feedback":"تقييم مفصل","total":39},'
        '"winner":"side_a أو side_b أو tie"}'
    )
    try:
        content = nvidia_chat(prompt, timeout=90, temperature=0.3)
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return jsonify({'error': 'تعذّر تحليل رد النموذج'}), 500
        result = json.loads(m.group())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'تعذّر تقييم النقاش: ' + str(e)}), 500


@app.route('/api/ai/check-answer', methods=['POST'])
def ai_check_answer():
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ'}), 400
    body = request.get_json(silent=True) or {}
    items = body.get('items') or []
    answer = str(body.get('answer', '')).strip()
    if not items or not answer:
        return jsonify({'error': 'العناصر والإجابة مطلوبة'}), 400
    items_text = '، '.join(str(i) for i in items)
    prompt = (
        'أنت مُحكم لعبة "الرابط المشترك". حدد ما إذا كانت إجابة اللاعب قريبة من الإجابة الصحيحة أم بعيدة.\n\n'
        'العناصر: ' + items_text + '\n'
        'إجابة اللاعب: ' + answer + '\n\n'
        'حدد النتيجة:\n'
        '- "صحيح": إذا كانت الإجابة صحيحة أو مرادفة تماماً\n'
        '- "قريب": إذا كانت الإجابة قريبة من الصحيحة لكنها ليست دقيقة\n'
        '- "بعيد": إذا كانت الإجابة بعيدة عن الصحيحة\n\n'
        'أعد النتيجة بصيغة JSON فقط:\n'
        '{"result":"قريب أو بعيد أو صحيح","explanation":"شرح مختصر"}'
    )
    try:
        content = nvidia_chat(prompt, timeout=60, temperature=0.3)
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return jsonify({'error': 'تعذّر تحليل رد النموذج'}), 500
        result = json.loads(m.group())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'تعذّر فحص الإجابة: ' + str(e)}), 500


@app.route('/api/ai/generate-debate-topic', methods=['POST'])
def ai_generate_debate_topic():
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ'}), 400
    prompt = (
        'أنشئ موضوع نقاش متوازناً للعبة "أقنعني!".\n\n'
        'الموضوع يجب أن يكون:\n'
        '- متوازناً (لكل طرف حجج حقيقية)\n'
        '- غير سياسي ولا ديني حساس\n'
        '- مناسب للنقاش المدرسي\n'
        '- مثير للاهتمام\n\n'
        'أعد النتيجة بصيغة JSON فقط:\n'
        '{"topic":"الموضوع كسؤال","side_a":"الموقف المؤيد","side_b":"الموقف المعارض"}'
    )
    try:
        content = nvidia_chat(prompt, timeout=60, temperature=0.8)
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return jsonify({'error': 'تعذّر تحليل رد النموذج'}), 500
        result = json.loads(m.group())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'تعذّر توليد الموضوع: ' + str(e)}), 500


# ============ UNIFIED AI GENERATION (all games, live job dashboard) ============
# One console drives every game: the client picks the game, then whatever that
# game actually has — categories, subcategories, letters, difficulties, points —
# and the job dashboard shows how many items are in flight plus an ETA.

QUESTION_GAME_DEFS = {
    'letters': {'name': 'حروف مع أمين', 'kind': 'questions',
                'selectors': ['category', 'letter', 'difficulty'],
                'count_label': 'عدد الأسئلة لكل حرف', 'max_count': 200},
    'quiz': {'name': 'س.ج', 'kind': 'questions',
             'selectors': ['category', 'difficulty', 'points'],
             'count_label': 'عدد الأسئلة', 'max_count': 200},
    'million': {'name': 'من سيربح المليون', 'kind': 'questions',
                'selectors': ['category', 'difficulty'],
                'count_label': 'عدد الأسئلة', 'max_count': 200},
    'lastone': {'name': 'آخر واحد!', 'kind': 'lastone',
                'selectors': ['category', 'difficulty'],
                'count_label': 'عدد الإجابات لكل تصنيف', 'max_count': 300},
    'auction': {'name': 'مزاد اللاعبين', 'kind': 'players',
                'selectors': ['league', 'position', 'difficulty'],
                'count_label': 'عدد اللاعبين', 'max_count': 60},
}

CONTENT_GAME_DEFS = {
    'codenames': {'name': 'كود نيمز', 'selectors': ['category', 'difficulty']},
    'detective': {'name': 'المحقق', 'selectors': ['difficulty']},
    'culprit': {'name': 'من الفاعل؟', 'selectors': ['difficulty']},
    'spy': {'name': 'الجاسوس', 'selectors': ['category', 'difficulty']},
    'debate': {'name': 'أقنعني!', 'selectors': ['category', 'difficulty']},
    'whoplayer': {'name': 'مين اللاعب؟', 'selectors': ['difficulty']},
    'link': {'name': 'الرابط المشترك', 'selectors': ['category', 'difficulty']},
    'minebali': {'name': 'مين في بالي؟', 'selectors': ['category', 'subcategory', 'difficulty']},
}

PLAYER_POSITIONS = ['GK', 'CB', 'LB', 'RB', 'CDM', 'CM', 'CAM', 'LW', 'RW', 'ST', 'CF']
LEAGUE_NAMES = {'laliga': 'الدوري الإسباني', 'epl': 'الدوري الإنجليزي',
                'bundesliga': 'الدوري الألماني', 'seriea': 'الدوري الإيطالي',
                'ligue1': 'الدوري الفرنسي', 'saudi': 'دوري روشن السعودي'}


def ai_game_defs():
    out = {}
    for g, d in QUESTION_GAME_DEFS.items():
        out[g] = dict(d)
    for g, d in CONTENT_GAME_DEFS.items():
        out[g] = {'name': d['name'], 'kind': 'content', 'selectors': d['selectors'],
                  'count_label': 'عدد العناصر', 'max_count': 40}
    return out


AI_GAME_DEFS = ai_game_defs()


def ai_game_categories(game):
    """Category options for a game: the real values present in its own library."""
    if game in ('letters', 'quiz', 'million'):
        cats = load_json(CAT_FILE, [])
        return [{'id': c['id'], 'name': c['name']} for c in cats]
    if game == 'lastone':
        data = load_json(os.path.join(BASE_DIR, 'static', 'lastone_categories.json'), {})
        return [{'id': k, 'name': k} for k in (data.keys() if isinstance(data, dict) else [])]
    if game == 'auction':
        players = load_json(PL_FILE, [])
        leagues = sorted({p.get('league') for p in players if p.get('league')})
        return [{'id': l, 'name': LEAGUE_NAMES.get(l, l)} for l in leagues]
    items = load_json(content_file(game), [])
    vals = sorted({str(x.get('category') or '').strip() for x in items if x.get('category')})
    return [{'id': v, 'name': v} for v in vals]


@app.route('/api/ai/games', methods=['GET'])
def ai_games():
    cats = load_json(CAT_FILE, [])
    groups = {}
    for c in cats:
        g = (c.get('group') or '').strip() or 'عام'
        groups.setdefault(g, []).append(c['id'])
    out = []
    for g, d in AI_GAME_DEFS.items():
        entry = {'game': g, 'name': d['name'], 'kind': d['kind'],
                 'selectors': d['selectors'], 'count_label': d['count_label'],
                 'max_count': d['max_count'],
                 'categories': ai_game_categories(g),
                 'difficulties': ([{'id': 'under', 'name': 'تحت المتوسط'},
                                   {'id': 'easy', 'name': 'سهل'},
                                   {'id': 'medium', 'name': 'متوسط'},
                                   {'id': 'hard', 'name': 'صعب'}]
                                  if d['kind'] == 'questions' else
                                  [{'id': 'easy', 'name': 'سهل'},
                                   {'id': 'medium', 'name': 'متوسط'},
                                   {'id': 'hard', 'name': 'صعب'}]),
                 'letters': AR_LETTERS if g == 'letters' else [],
                 'points': [{'id': 200, 'name': '200'}, {'id': 400, 'name': '400'},
                            {'id': 600, 'name': '600'}] if g == 'quiz' else [],
                 'positions': [{'id': p, 'name': p} for p in PLAYER_POSITIONS] if g == 'auction' else []}
        if d['kind'] == 'content':
            items = load_json(content_file(g), [])
            subs = sorted({str(x.get('subcategory') or '').strip()
                           for x in items if x.get('subcategory')})
            entry['subcategories'] = [{'id': s, 'name': s} for s in subs]
            entry['current_count'] = len(items)
        elif g == 'auction':
            entry['current_count'] = len(load_json(PL_FILE, []))
        elif g == 'lastone':
            data = load_json(os.path.join(BASE_DIR, 'static', 'lastone_categories.json'), {})
            entry['current_count'] = sum(len(v) for v in data.values()) if isinstance(data, dict) else 0
        else:
            entry['current_count'] = len(load_bank())
        out.append(entry)
    return jsonify({'games': out, 'categories': cats,
                    'category_groups': [{'name': k, 'count': len(v)} for k, v in groups.items()]})


# ---- job bookkeeping: the live dashboard reads this -------------------------
AI_JOBS = {}
AI_ACTIVE_JOB = {'id': None}


def ai_job_summary(job):
    elapsed = (job.get('finished_at') or time.time()) - job.get('started_at', time.time())
    done = job.get('done', 0)
    remaining = max(0, job.get('target', 0) - done)
    per = (elapsed / done) if done > 0 else 25.0
    eta = int(remaining * per) if job.get('finished_at') else int(remaining * per)
    return {'id': job.get('id'), 'game': job.get('game'), 'game_name': job.get('game_name'),
            'label': job.get('label', ''), 'target': job.get('target', 0),
            'done': done, 'accepted': job.get('accepted', 0), 'rejected': job.get('rejected', 0),
            'items': job.get('items', []), 'rejected_items': job.get('rejected_items', []),
            'running': not job.get('finished_at'), 'finished_at': job.get('finished_at', ''),
            'error': job.get('error', ''), 'started_at': job.get('started_at', 0),
            'elapsed_seconds': int(elapsed), 'eta_seconds': eta,
            'progress_pct': int(100 * done / job['target']) if job.get('target') else 0}


@app.route('/api/ai/job/start', methods=['POST'])
def ai_job_start():
    body = request.get_json(silent=True) or {}
    game = str(body.get('game', '')).strip()
    if game not in AI_GAME_DEFS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    target = max(1, min(int(body.get('target', 10)), 500))
    job_id = gen_id()
    job = {'id': job_id, 'game': game, 'game_name': AI_GAME_DEFS[game]['name'],
           'label': 'توليد حتى ' + str(target) + ' — ' + AI_GAME_DEFS[game]['name'],
           'target': target, 'done': 0, 'accepted': 0, 'rejected': 0,
           'items': [], 'rejected_items': [], 'started_at': time.time(),
           'finished_at': '', 'error': ''}
    AI_JOBS[job_id] = job
    AI_ACTIVE_JOB['id'] = job_id
    return jsonify(ai_job_summary(job))


@app.route('/api/ai/job/<job_id>', methods=['GET'])
def ai_job_get(job_id):
    job = AI_JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'المهمة غير موجودة'}), 404
    return jsonify(ai_job_summary(job))


@app.route('/api/ai/job/<job_id>/finish', methods=['POST'])
def ai_job_finish(job_id):
    job = AI_JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'المهمة غير موجودة'}), 404
    job['finished_at'] = time.time()
    job['error'] = str((request.get_json(silent=True) or {}).get('error', ''))
    if AI_ACTIVE_JOB['id'] == job_id:
        AI_ACTIVE_JOB['id'] = None
    return jsonify(ai_job_summary(job))


def ai_job_push(job, item, ok, reason=''):
    """Record one generated item on the live job and on the legacy dashboard."""
    title = (item.get('question') or item.get('word') or item.get('title')
             or item.get('topic') or item.get('player') or item.get('name') or '')
    answer = (item.get('answer') or item.get('meaning') or item.get('solution')
              or item.get('culprit') or item.get('link') or '')
    if ok:
        job['accepted'] += 1
        job['items'].append({'title': str(title)[:120], 'detail': str(answer)[:120],
                             'ok': True, 'at': time.time()})
    else:
        job['rejected'] += 1
        job['rejected_items'].append({'title': str(title)[:120], 'reason': reason, 'at': time.time()})
    job['done'] = job['accepted'] + job['rejected']
    job['updated_at'] = time.time()
    ai_progress_add(item, ok, reason)


def _ai_gen_questions(game, letter, category_id, want, difficulty, points=None,
                      job=None, job_id=''):
    """Generate up to `want` validated questions for a question-bank game."""
    cats = {c['id']: c for c in load_json(CAT_FILE, [])}
    cat = cats.get(category_id) or {}
    cat_name = cat.get('name', '')
    cat_desc = cat.get('description', '') or ''
    if not cat_name:
        raise ValueError('الفئة غير موجودة — اختر فئة صحيحة')

    existing_all = load_bank()
    if game == 'letters':
        prior = [q for q in existing_all if q.get('letter') == letter]
    elif game == 'million':
        prior = [q for q in existing_all if q.get('game') == 'million']
    else:
        prior = [q for q in existing_all if q.get('category_id') == category_id]
    prior_texts = [str(q.get('question', '')).strip() for q in prior if q.get('question')]
    prior_sample = prior_texts[-20:] if len(prior_texts) > 20 else prior_texts
    avoid_block = ''
    if prior_sample:
        avoid_block = ('\n\nلا تكرر هذه الأسئلة:\n' + '\n'.join('- ' + t for t in prior_sample))

    existing_keys = {q_key(q) for q in existing_all}
    validated, rejected = [], []
    last_error = ''

    for attempt in range(2):
        need = want - len(validated)
        if need <= 0:
            break
        ask = min(20, max(need * 2, need + 2))
        prompt = build_ai_prompt(game, letter, cat_name, ask, difficulty, avoid_block,
                                strict=(attempt > 0), cat_desc=cat_desc)
        try:
            content = nvidia_chat(prompt, timeout=75, temperature=0.85 if attempt else 0.7)
            items = extract_json_array(content)
        except Exception as e:
            last_error = str(e)
            continue

        off_topic = set()
        if game == 'quiz':
            cands = [it for it in items if isinstance(it, dict) and it.get('question')]
            verdicts = verify_relevance(cands, cat_name, cat_desc)
            if verdicts is not None:
                for it, ok in zip(cands, verdicts):
                    if not ok:
                        off_topic.add(norm_ar(it.get('question', '')))

        for it in items:
            if len(validated) >= want:
                break
            if not isinstance(it, dict) or not it.get('question') or not it.get('answer'):
                rejected.append({'question': str(it)[:80], 'answer': '', 'reason': 'بيانات ناقصة'})
                if job:
                    ai_job_push(job, {'question': str(it)[:80]}, False, 'بيانات ناقصة')
                continue
            if game == 'quiz' and norm_ar(str(it.get('question', ''))) in off_topic:
                rejected.append({'question': str(it.get('question', ''))[:80],
                                 'answer': str(it.get('answer', ''))[:40], 'reason': 'خارج عن الفئة'})
                if job:
                    ai_job_push(job, it, False, 'خارج عن الفئة')
                continue
            q = {'id': gen_id(), 'game': game,
                 'question': str(it['question']).strip(),
                 'answer': str(it['answer']).strip(),
                 'explanation': str(it.get('explanation', '')).strip(),
                 'difficulty': difficulty, 'status': 'pending_review', 'source': 'ai',
                 'created_at': now(), 'updated_at': now(),
                 'alternatives': [], 'hint': '', 'image': ''}
            if game == 'letters':
                q['letter'] = letter
            elif game == 'million':
                q['options'] = [str(o).strip() for o in (it.get('options') or [])][:4]
                q['points'] = 200 if difficulty in ('easy', 'under') else (600 if difficulty == 'hard' else 400)
            else:
                q['category_id'] = category_id
                q['category_name'] = cat_name
                q['points'] = points if points in (200, 400, 600) else (
                    200 if difficulty == 'under' else (600 if difficulty == 'hard' else 400))

            ok, err = validate_question(q)
            if not ok:
                rejected.append({'question': q['question'][:80], 'answer': q['answer'][:40], 'reason': err})
                if job:
                    ai_job_push(job, q, False, err)
                continue
            if q_key(q) in existing_keys:
                rejected.append({'question': q['question'][:80], 'answer': q['answer'][:40], 'reason': 'سؤال مكرر'})
                if job:
                    ai_job_push(job, q, False, 'مكرر')
                continue
            existing_keys.add(q_key(q))
            validated.append(q)
            if job:
                ai_job_push(job, q, True)

    all_qs = load_bank()
    all_qs.extend(validated)
    save_json(Q_FILE, all_qs)
    return {'items': validated, 'count': len(validated), 'requested': want,
            'rejected': rejected, 'rejected_count': len(rejected), 'last_error': last_error}


def _ai_gen_content(game, want, difficulty, category, job=None):
    """Generate up to `want` validated content items for a content-library game."""
    items = load_json(content_file(game), [])
    keys = set()
    for x in items:
        keys |= content_keys(game, x)
    avoid = ''
    if keys:
        sample = [str(x.get('word') or x.get('title') or x.get('topic')
                      or x.get('player') or x.get('name') or '') for x in items]
        sample = [s for s in sample if s][-25:]
        if sample:
            avoid = '\nلا تكرر هذه العناصر: ' + '، '.join(sample)

    diff_ar = {'easy': 'سهل', 'medium': 'متوسط', 'hard': 'صعب'}.get(difficulty, 'متوسط')
    prompt = GAME_SCHEMAS[game]['prompt'].replace('{n}', str(want))
    if '__CATEGORY__' in prompt:
        prompt = prompt.replace('__CATEGORY__', category or GAME_SCHEMAS[game]['name'])
    prompt += '\nمستوى الصعوبة المطلوب: ' + diff_ar + '.'
    if category:
        prompt += '\nالموضوع/الفئة المطلوبة: ' + category + '.'
    prompt += avoid + '\nأعد مصفوفة JSON فقط بلا أي نص إضافي.'

    validated, rejected = [], []
    last_error = ''
    for attempt in range(2):
        if len(validated) >= want:
            break
        try:
            p = prompt if attempt == 0 else prompt + (
                '\n\nتذكير: كل النصوص عربية فقط، ولا حروف لاتينية أو أجنبية إطلاقاً. '
                'التزم بالحقول المذكورة حرفياً. أعد JSON صالحاً فقط.')
            content = nvidia_chat(p, timeout=90, temperature=0.85 if attempt else 0.7)
            got = extract_json_array(content)
        except Exception as e:
            last_error = str(e)
            continue
        for it in got:
            if len(validated) >= want:
                break
            if not isinstance(it, dict):
                continue
            it['id'] = gen_id()
            it['status'] = 'pending_review'
            it['source'] = 'ai'
            it['created_at'] = now()
            it['updated_at'] = now()
            it.setdefault('difficulty', difficulty)
            if game == 'minebali' and category and not str(it.get('category', '')).strip():
                it['category'] = category
            ok, err = validate_content(game, it)
            if not ok:
                rejected.append({'question': str(it.get('name') or it.get('word') or it.get('title') or '')[:80],
                                 'answer': '', 'reason': err})
                if job:
                    ai_job_push(job, it, False, err)
                continue
            k = content_keys(game, it)
            if k & keys:
                rejected.append({'question': str(it.get('name') or it.get('word') or it.get('title') or '')[:80],
                                 'answer': '', 'reason': 'مكرر'})
                if job:
                    ai_job_push(job, it, False, 'مكرر')
                continue
            keys |= k
            validated.append(it)
            if job:
                ai_job_push(job, it, True)

    items.extend(validated)
    save_json(content_file(game), items)
    return {'items': validated, 'count': len(validated), 'requested': want,
            'rejected': rejected, 'rejected_count': len(rejected), 'last_error': last_error}


def _ai_gen_lastone(want, category, difficulty, job=None):
    """«آخر واحد!» has no questions — each category is a list of valid answers."""
    path = os.path.join(BASE_DIR, 'static', 'lastone_categories.json')
    data = load_json(path, {}) or {}
    if not isinstance(data, dict) or not data:
        raise ValueError('ملف تصنيفات آخر واحد غير موجود')
    cat_name = category or ''
    if cat_name not in data:
        raise ValueError('التصنيف غير موجود في آخر واحد')
    current = [str(x).strip() for x in data[cat_name] if str(x).strip()]
    existing = {norm_ar(x) for x in current}
    diff_ar = {'easy': 'سهل وشائع', 'medium': 'متوسط', 'hard': 'صعب ونادر'}.get(difficulty, 'متوسط')
    prompt = (
        'أنت معدّ محتوى للعبة «آخر واحد!». المطلوب: ' + str(want * 2) +
        ' إجابة صحيحة تنتمي إلى تصنيف «' + cat_name + '».\n'
        'مستوى الصعوبة: ' + diff_ar + '.\n'
        'الصيغة: [{"answer":"إجابة قصيرة"}]\n'
        'قواعد: كل إجابة عربية قصيرة (كلمة أو كلمتان)، تنتمي فعلاً للتصنيف، '
        'لا تكرر إجابة، ممنوع حروف أجنبية.\n'
        'لا تكرر هذه الإجابات الموجودة: ' + '، '.join(current[-60:]) + '\n'
        'أعد مصفوفة JSON فقط بلا أي نص إضافي.')
    out, rejected = [], []
    try:
        got = extract_json_array(nvidia_chat(prompt, timeout=90, temperature=0.9))
    except Exception as e:
        if job:
            job['error'] = str(e)
        return {'items': out, 'count': 0, 'requested': want,
                'rejected': [{'question': '', 'answer': '', 'reason': str(e)}],
                'rejected_count': 1, 'last_error': str(e)}
    for it in got:
        if len(out) >= want:
            break
        a = str((it.get('answer') if isinstance(it, dict) else it) or '').strip()
        if not a or has_foreign(a) or norm_ar(a) in existing:
            rejected.append({'question': a[:80], 'answer': '', 'reason': 'غير صالح أو مكرر'})
            if job:
                ai_job_push(job, {'answer': a}, False, 'غير صالح أو مكرر')
            continue
        existing.add(norm_ar(a))
        current.append(a)
        out.append({'answer': a})
        if job:
            ai_job_push(job, {'question': a}, True)
    data[cat_name] = current
    save_json(path, data)
    mirror = os.path.join(DATA, 'lastone_categories.json')
    if os.path.abspath(mirror) != os.path.abspath(path):
        save_json(mirror, data)
    return {'items': out, 'count': len(out), 'requested': want,
            'rejected': rejected, 'rejected_count': len(rejected), 'last_error': ''}


def _ai_gen_players(want, league, position, difficulty, job=None):
    """Generate real football players for the auction game."""
    players = load_json(PL_FILE, [])
    existing = {norm_ar(p.get('name', '')) for p in players}
    avoid = ''
    sample = [str(p.get('name', '')) for p in players][-25:]
    if sample:
        avoid = '\nلا تكرر هؤلاء اللاعبين: ' + '، '.join(sample)
    lg = LEAGUE_NAMES.get(league, league or '')
    pos_ar = {'GK': 'حارس مرمى', 'CB': 'مدافع وسط', 'LB': 'ظهير أيسر', 'RB': 'ظهير أيمن',
              'CDM': 'وسط دفاعي', 'CM': 'وسط', 'CAM': 'وسط هجومي', 'LW': 'جناح أيسر',
              'RW': 'جناح أيمن', 'ST': 'مهاجم', 'CF': 'مهاجم صريح'}.get(position, position or '')
    diff_ar = {'easy': 'لاعبون معروفون جداً', 'medium': 'لاعبون معروفون',
               'hard': 'لاعبون أقل شهرة لكنهم حقيقيون'}.get(difficulty, 'لاعبون معروفون')
    prompt = (
        'أنشئ ' + str(want * 2) + ' لاعب كرة قدم حقيقي للعبة مزاد اللاعبين.\n'
        'الصيغة: [{"name":"الاسم الكامل بالإنجليزية","position":"GK أو CB أو ...",'
        '"rating":85,"pace":70,"shooting":70,"passing":70,"dribbling":70,"defending":70,'
        '"physical":70,"club":"النادي الحالي","league":"laliga أو epl أو bundesliga أو seriea أو ligue1 أو saudi",'
        '"nationality":"الجنسية بالعربية","era":"current أو retired","price":25}]\n'
        'مستوى الشهرة: ' + diff_ar + '.\n'
        + ('الدوري المطلوب: ' + lg + '.\n' if lg else '')
        + ('المركز المطلوب: ' + pos_ar + '.\n' if pos_ar else '')
        + 'قواعد: اللاعب حقيقي وموجود فعلاً، الأرقام بين 1 و99، السعر بالمليون، '
          'لا تختلق لاعبين ولا أندية.'
        + avoid + '\nأعد مصفوفة JSON فقط بلا أي نص إضافي.')
    out, rejected = [], []
    last_error = ''
    for attempt in range(2):
        if len(out) >= want:
            break
        try:
            p = prompt if attempt == 0 else prompt + '\nأعد JSON صالحاً فقط.'
            got = extract_json_array(nvidia_chat(p, timeout=90, temperature=0.85 if attempt else 0.7))
        except Exception as e:
            last_error = str(e)
            continue
        for it in got:
            if len(out) >= want:
                break
            if not isinstance(it, dict):
                continue
            name = str(it.get('name', '')).strip()
            pos = str(it.get('position', '')).strip().upper()
            try:
                rating = int(it.get('rating', 0))
            except Exception:
                rating = 0
            if not name or pos not in PLAYER_POSITIONS or not (40 <= rating <= 99):
                rejected.append({'question': name[:60], 'answer': pos, 'reason': 'بيانات غير صالحة'})
                if job:
                    ai_job_push(job, {'question': name}, False, 'بيانات غير صالحة')
                continue
            if norm_ar(name) in existing:
                rejected.append({'question': name[:60], 'answer': pos, 'reason': 'مكرر'})
                if job:
                    ai_job_push(job, {'question': name}, False, 'مكرر')
                continue

            def num(key, lo=1, hi=99, default=70):
                try:
                    v = int(it.get(key, default))
                except Exception:
                    v = default
                return max(lo, min(hi, v))

            lg_code = str(it.get('league', '') or league or '').strip()
            if lg_code not in LEAGUE_NAMES:
                lg_code = league or 'saudi'
            row = {'id': gen_id(), 'name': name, 'position': pos, 'rating': rating,
                   'pace': num('pace'), 'shooting': num('shooting'), 'passing': num('passing'),
                   'dribbling': num('dribbling'), 'defending': num('defending'),
                   'physical': num('physical'),
                   'club': str(it.get('club', '')).strip() or 'بدون نادي',
                   'league': lg_code, 'league_name': LEAGUE_NAMES.get(lg_code, lg_code),
                   'nationality': str(it.get('nationality', '')).strip() or 'غير معروفة',
                   'era': 'retired' if str(it.get('era', '')) == 'retired' else 'current',
                   'price': max(1, num('price', 1, 200, 20)),
                   'image': '', 'verified': False, 'source': 'ai',
                   'created_at': now()}
            existing.add(norm_ar(name))
            out.append(row)
            if job:
                ai_job_push(job, row, True)

    players.extend(out)
    save_json(PL_FILE, players)
    return {'items': out, 'count': len(out), 'requested': want,
            'rejected': rejected, 'rejected_count': len(rejected), 'last_error': last_error}


@app.route('/api/ai/run', methods=['POST'])
def ai_run():
    """One batch of a generation job — the client loops it and polls the job."""
    body = request.get_json(silent=True) or {}
    game = str(body.get('game', '')).strip()
    if game not in AI_GAME_DEFS:
        return jsonify({'error': 'لعبة غير معروفة'}), 404
    if not NVIDIA_API_KEY:
        return jsonify({'error': 'NVIDIA_API_KEY غير مُعدّ — راجع إعدادات الذكاء الاصطناعي'}), 400
    want = max(1, min(int(body.get('count', 5)), 12))
    job_id = str(body.get('job_id', '') or AI_ACTIVE_JOB['id'] or '')
    job = AI_JOBS.get(job_id)
    if job is None:
        job_id = gen_id()
        job = {'id': job_id, 'game': game, 'game_name': AI_GAME_DEFS[game]['name'],
               'label': 'توليد — ' + AI_GAME_DEFS[game]['name'], 'target': want,
               'done': 0, 'accepted': 0, 'rejected': 0, 'items': [], 'rejected_items': [],
               'started_at': time.time(), 'finished_at': '', 'error': ''}
        AI_JOBS[job_id] = job
        AI_ACTIVE_JOB['id'] = job_id
    req_target = int(body.get('target', 0) or 0)
    if req_target > int(job.get('target', 0) or 0):
        job['target'] = req_target

    difficulty = body.get('difficulty', 'medium')
    category = str(body.get('category', '') or '').strip()
    letter = str(body.get('letter', '') or '').strip()
    subcategory = str(body.get('subcategory', '') or '').strip()
    points = body.get('points')
    try:
        points = int(points) if points not in (None, '') else None
    except Exception:
        points = None
    t0 = time.time()
    try:
        if AI_GAME_DEFS[game]['kind'] == 'questions':
            res = _ai_gen_questions(game, letter, category, want, difficulty, points, job, job_id)
        elif AI_GAME_DEFS[game]['kind'] == 'content':
            res = _ai_gen_content(game, want, difficulty, category or subcategory, job)
        elif AI_GAME_DEFS[game]['kind'] == 'lastone':
            res = _ai_gen_lastone(want, category, difficulty, job)
        else:
            res = _ai_gen_players(want, body.get('league', ''), body.get('position', ''),
                                  difficulty, job)
    except Exception as e:
        job['error'] = str(e)
        return jsonify({'error': str(e), 'job': ai_job_summary(job)}), 400

    job['elapsed'] = time.time() - t0
    job['updated_at'] = time.time()
    resp = {'items': res['items'], 'count': res['count'], 'requested': want,
            'rejected': res.get('rejected', [])[:20],
            'rejected_count': res.get('rejected_count', 0),
            'job': ai_job_summary(job)}
    if not res['items'] and res.get('last_error'):
        resp['error'] = 'تعذّر التوليد: ' + res['last_error']
    return jsonify(resp)


@app.route('/api/ai/progress', methods=['GET'])
def ai_generation_progress():
    job = AI_JOBS.get(AI_ACTIVE_JOB['id']) if AI_ACTIVE_JOB['id'] else None
    if job:
        s = ai_job_summary(job)
        # legacy keys so the existing dashboard keeps working
        s.update({'running': s['running'], 'label': s['label'], 'requested': s['target'],
                  'completed': s['done'], 'accepted': s['accepted'], 'rejected': s['rejected'],
                  'current_attempt': 0, 'total_attempts': 0})
        return jsonify(s)
    return jsonify(dict(AI_PROGRESS))


# ============ STATS ============
@app.route('/api/stats', methods=['GET'])
def stats():
    all_qs = load_bank()
    per_letter = {l: len([q for q in all_qs if q.get('letter') == l]) for l in AR_LETTERS}
    return jsonify({
        'total': len(all_qs),
        'approved': len([q for q in all_qs if q.get('status') == 'approved']),
        'pending_review': len([q for q in all_qs if q.get('status') == 'pending_review']),
        'archived': len([q for q in all_qs if q.get('status') == 'archived']),
        'ai_generated': len([q for q in all_qs if q.get('source') == 'ai']),
        'letters': len([q for q in all_qs if q.get('game') == 'letters']),
        'quiz': len([q for q in all_qs if q.get('game') == 'quiz']),
        'million': len([q for q in all_qs if q.get('game') == 'million']),
        'categories': len(load_json(CAT_FILE, [])),
        'players': len(load_json(PL_FILE, [])),
        'pending_queue': len([q for q in all_qs if q.get('status') == 'pending_review']),
        'per_letter': per_letter,
        'ai_ready': bool(NVIDIA_API_KEY),
        'ai_model': current_model() if NVIDIA_API_KEY else '',
    })


# ============ PAGES ============
@app.route('/')
def home():
    return render_template('index.html')


# ============ شاشة شرح اللعبة (تظهر قبل شاشة الإعداد) ============
# كل لعبة لها شرح قصير يظهر مرة، مع زر «لا تظهر الشرح لهذه اللعبة فقط»
# وزر «لا تظهر الشرح لجميع الألعاب». القرار محفوظ في كوكيز يقرؤه الخادم،
# فالصفحة تُبنى في الخادم بدل إعادة توجيه من المتصفح.
INTRO_COOKIE = 'ameen_intro'
INTRO_ALL_COOKIE = 'ameen_intro_all'
# كوكيز جلسة فقط (بدون max-age): زر «التالي» يستخدمه ليتجاوز الشرح مرة واحدة
# دون أن يحفظ قراراً دائماً — وإلا كان يدور في حلقة: الشرح يفتح /game/<x>
# والخادم يعيد عرض الشرح لأنه لا يعرف أن الزائر تجاوزه للتو.
INTRO_VISIT_COOKIE = 'ameen_intro_visit'

GAME_INTROS = {
    'letters': {
        'name': 'حروف مع أمين',
        'type': 'لعبة لوحة',
        'icon': 'i-shield', 'color': 'var(--accent-green)',
        'lead': 'مسابقة سباق الحروف بين فريقين على لوحة سداسية، الهدف بناء مسار متصل قبل الخصم.',
        'steps': [
            'قسّم الحضور إلى فريقين واختر لكل فريق لونه.',
            'الفريق صاحب الدور يضغط على خلية متاحة من اللوحة.',
            'يظهر السؤال ويبدأ الجرس — من يصل إليه أولاً يحصل على حق الإجابة.',
            'الإجابة الصحيحة تمنح الخلية لون فريقك فورًا.',
            'فريق يكمل مسارًا أفقيًا وآخر عموديًا — أول من يصل يفوز بالجولة.',
        ],
        'tip': 'زر التكبير والتصغير في الأسفل يكبّر الشاشة كاملةً للعرض على التلفزيون أو البروجيكتور.',
    },
    'quiz': {
        'name': 'س.ج',
        'type': 'مسابقة',
        'icon': 'i-question', 'color': 'var(--accent-purple)',
        'lead': 'مسابقة ثقافية بين فريقين: اختر الفئة وقيمة النقاط، وأجب قبل انتهاء الوقت.',
        'steps': [
            'من شاشة الإعداد اختر 6 فئات ومدة الإجابة ونقاط الأسئلة.',
            'الفريق صاحب الدور يختار فئة ثم قيمة النقاط.',
            'يظهر السؤال ويبدأ المؤقّت.',
            'اضغط «👁️ إظهار الإجابة» ثم حدّد: صحيحة أم خاطئة.',
            'الإجابة الصحيحة تضيف النقاط، والخطأ ينقل السؤال للفريق الآخر.',
            'عند استهلاك أسئلة اللوحة يُعلَن الفائز صاحب أعلى رصيد.',
        ],
        'tip': 'زر «✏️ تعديل النقاط» يتيح للمضيف تصحيح النقاط يدويًا في أي لحظة.',
    },
    'auction': {
        'name': 'مزاد اللاعبين',
        'type': 'استراتيجية',
        'icon': 'i-gavel', 'color': 'var(--accent-gold)',
        'lead': 'مزاد سريع يبني لكل مشارك تشكيلته ضمن ميزانية محدودة.',
        'steps': [
            'أدخل أسماء المشاركين وميزانية كل واحد.',
            'يعرض النظام لاعبًا في كل جولة مع سعر افتتاحي.',
            'يتنافس المشاركون بالمزايدة خلال الوقت — كل مزايدة تجاوز سابقتها.',
            'صاحب أعلى مزايدة يحصل على اللاعب ويُخصَم السعر.',
            'يتكرر المزاد حتى اكتمال التشكيلات، ثم تُقارن ويُعلَن الفائز.',
        ],
        'tip': 'يمكن للمشارك التمرير (التعليق) في أي لحظة.',
    },
    'million': {
        'name': 'من سيربح المليون',
        'type': 'استراتيجية',
        'icon': 'i-crown', 'color': 'var(--accent-cyan)',
        'lead': 'مسابقة فردية بمبالغ تصاعدية، والمخاطرة قرار اللاعب وحده.',
        'steps': [
            'أجب على خمسة عشر سؤالًا متتالياً، لكل سؤال أربعة خيارات.',
            'ترتفع قيمة السؤال مع التقدّم، وهناك محطات مضمونة.',
            'ثلاث وسائل مساعدة: حذف إجابتين، اتصال بصديق، رأي الجمهور.',
            'يمكنك الانسحاب في أي لحظة واستلام ما تحقّق.',
            'الخطأ ينهي الجولة، وتحتفظ بآخر محطة مضمونة وصلت إليها.',
        ],
        'tip': 'الصعوبة تتصاعد تدريجيًا؛ لا تنسحب مبكّراً إن كانت إجاباتك الصحيحة مرتفعة.',
    },
    'codenames': {
        'name': 'كود نيمز',
        'type': 'كلمات ومهارات',
        'icon': 'i-eye', 'color': 'var(--accent-purple)',
        'lead': 'فريقان يتناوبان على تخمين كلمات شبكتهم من تلميح قائد الفريق.',
        'steps': [
            'قسّم إلى فريقين وعيّن قائدًا لكل فريق.',
            'القائد وحده يرى كلمات فريقه والكلمة الخاسرة.',
            'القائد يعطي تلميحًا: كلمة + عدد الكلمات المرتبطة بها.',
            'فريقه يخمّن ويلعب الكلمات — له عدد محاولات يساوي التلميح + 1.',
            'الكلمة الخاسرة تنهي الجولة فورًا لصالح الخصم.',
            'أول فريق يكشف كل كلماته يفوز بالجولة.',
        ],
        'tip': 'إن لم يخمّن الفريق أي كلمة صحيحة، ينتقل الدور للفريق الآخر.',
    },
    'detective': {
        'name': 'المحقق',
        'type': 'ألغاز وتحقيق',
        'icon': 'i-search', 'color': 'var(--accent-blue)',
        'lead': 'اجمع الأدلة من مسرح الحادثة واستجوب الشهود ثم قدّم استناجك.',
        'steps': [
            'اقرأ وقائع القضية والشخصيات المتورطة.',
            'افحص الأدلة واحدًا تلو الآخر.',
            'حدّد الأدلة الأساسية التي تدعم استنتاجك.',
            'قدّم المتورط والأدلة الداعمة.',
            'يُكشف الحل الصحيح وتُحتَسب نقاطك.',
        ],
        'tip': 'ليست كل الأدلة أساسية — اختيارها الصحيح هو نصف النقاط.',
    },
    'culprit': {
        'name': 'من الفاعل؟',
        'type': 'ألغاز وتحقيق',
        'icon': 'i-scale', 'color': 'var(--accent-red)',
        'lead': 'وقائع وأقوال مشتبه بهم متضاربة؛ مهمتك وزن القرائن وتحديد المسؤول.',
        'steps': [
            'اقرأ وقائع الحادثة.',
            'راجع أقوال المشتبه بهم — بعضها متناقض.',
            'حدّد المشتبه المسؤول والأدلة التي تدعم اختيارك.',
            'يُكشف الحل وتُحتَسب نقاطك.',
        ],
        'tip': 'ابحث عن التناقض بين الأقوال؛ فهو أقوى قرينة.',
    },
    'spy': {
        'name': 'الجاسوس',
        'type': 'ألغاز وتحقيق',
        'icon': 'i-eye', 'color': 'var(--accent-gold)',
        'lead': 'الجميع يعرف السؤال إلّا شخصًا واحدًا يتلقى إجابة مختلفة.',
        'steps': [
            'يحصل كل لاعب على بطاقة سؤال، واحدة منها مختلفة.',
            'يتناوبون على طرح الأسئلة والإجابة عليها.',
            'اقرأ ردود الفعل ولغة الجسد.',
            'صوّتوا لكشف الجاسوس.',
            'الجاسوس يكشف نفسه ويحاول تخمين السؤال الأصلي.',
        ],
        'tip': 'الإجابات العامّة جدّا أو الخاصّة جدّا تفضحك.',
    },
    'debate': {
        'name': 'أقنعني!',
        'type': 'كلمات ومهارات',
        'icon': 'i-megaphone', 'color': 'var(--accent-green)',
        'lead': 'قضية للنقاش يُقسَم الحضور حولها إلى مؤيد ومعارض.',
        'steps': [
            'يقرأ المضيف القضية للجميع.',
            'يُقسَم الحضور إلى مؤيد ومعارض.',
            'كل فريق يقدّم حججه ضمن وقته.',
            'تصويت الجمهور بعد انتهاء النقاش.',
            'الفريق صاحب الأغلبية يحصد النقاط.',
        ],
        'tip': 'وقّت كل تدخّل؛ النقاش المفتوح بلا وقت يفقد تركيز الجمهور.',
    },
    'whoplayer': {
        'name': 'مين اللاعب؟',
        'type': 'مسابقات',
        'icon': 'i-football', 'color': 'var(--accent-cyan)',
        'lead': 'تلميحات تتكشف تدريجيًا عن لاعب مجهول.',
        'steps': [
            'يظهر أوّل تلميح عن اللاعب.',
            'خمّن فورًا لتحصد أعلى نقاط.',
            'كل تلميح إضافي ياخفض قيمة النقاط.',
            'من يصيب يحصل على نقاط التلميح الذي \عنده.',
            'تنتهي الجولة عند كشف اللاعب أو نفاد التلميحات.',
        ],
        'tip': 'أوّل تلميح يساوي ضعف الأخير؛ لا تستعجل إن كان التلميح واضحًا.',
    },
    'link': {
        'name': 'الرابط المشترك',
        'type': 'كلمات ومهارات',
        'icon': 'i-link', 'color': 'var(--accent-pink)',
        'lead': 'عناصر من مجالات مختلفة تجمعها علاقة واحدة خفيّة.',
        'steps': [
            'تظهر مجموعة عناصر من مجالات مختلفة.',
            'اكتشف العلاقة التي تجمعها جميعًا.',
            'الفريق صاحب الدور يجيب قبل انتهاء الوقت.',
            'الإجابة الصحيحة تمنح النقاط.',
            'يمكن للفريق الآخر السرقة إن كان ذلك مفعًًا.',
        ],
        'tip': 'إن لم تجد الرابط، اسأل نفسك: ما الشيء الذي يحتاجه كل عنصر؟',
    },
    'draw_guess': {
        'name': 'ارسم وخمّن',
        'type': 'كلمات ومهارات',
        'icon': 'i-pen', 'color': 'var(--accent-blue)',
        'lead': 'رسّام من كل فريق يرسم كلمة سرية، وفريقه يخمّن قبل انتهاء الوقت — والفريق الآخر يترقب السرقة.',
        'steps': [
            'أدخل أسماء الفريقين واسم الرسّام ولون كل فريق.',
            'اختر مدة الرسم وعدد الأدوار والفئة والصعوبة.',
            'أعطِ الجهاز للرسّام، ثم يضغط على «✅ أنا الرسّام».',
            'يختار الرسّام كلمته من ثلاث مقترحات خلال 10 ثوانٍ.',
            'يرسم على اللوحة — ممنوع كتابة حروف أو أرقام.',
            'فريقه يخمّن شفهيًا، ويضغط المضيف «✅ إجابة صحيحة» عند الإصابة.',
            'النصف الأوّل من الوقت لفريقك وحده، وفي النصف الثاني تُفعَّل السرقة ويظهر زرها للفريق الآخر.',
            'نقاط الإجابة المبكّرة 300، وبعد نصف الوقت 200، والسرقة الناجحة 100.',
        ],
        'tip': 'زر «👁️ أرني الكلمة» يعمل بالضغط المستمر فقط؛ ارفع يدك فتختفي.',
    },
    'minebali': {
        'name': 'مين في بالي؟',
        'type': 'كلمات ومهارات',
        'icon': 'i-help', 'color': 'var(--accent-gold)',
        'lead': 'لعبة تخمين الشخصية بأسئلة نعم/لا.',
        'steps': [
            'يفكّر لاعب في شخصية ويدخل اسمها.',
            'يطرح الجميع أسئلة بنعم/لا لكشفها.',
            'كل إجابة تضيّق دائرة الاحتمالات.',
            'خمّن الشخصية قبل نفاد الأسئلة.',
            'من يصيب يحصل على النقاط.',
        ],
        'tip': 'اسأل عن الصفات العامّة أولًا (حقيقية/خيالية، ذكر/أنثى، مجال العمل) ثم ضيّق.',
    },
    'letters_strikeout': {
        'name': 'شطب الحروف',
        'type': 'مسابقات',
        'icon': 'i-target', 'color': 'var(--accent-gold)',
        'lead': 'مسابقة حروف سريعة تقرأ من بنك «س.ج»: كل حرف له مجموعة أسئلة، ومن يجيب أكثر يشطب الحروف.',
        'steps': [
            'اختر الحروف التي تريدها (حتى 28 حرفًا) وعدد الأسئلة لكل حرف.',
            'اضغط «🎲 حرف عشوائي» لبدء الجولة على حرف يُسحب من البنك.',
            'يظهر السؤال ويبدأ المؤقّت — الفريق صاحب الدور يجيب قبل انتهائه.',
            'اضغط «✅ صحيحة» أو «❌ خاطئة» ليُحسب النقاط فورًا.',
            'عند نفاد الأسئلة تُعلن النتيجة، ويمكن بدء جولة جديدة بحرف آخر.',
        ],
        'tip': 'الأسئلة تُسحب من بنك «س.ج» الموجود أصلًا — كل حرف يعرض أسئلته الحقيقية.',
    },
    'dice_race': {
        'name': 'سباق النرد',
        'type': 'لعبة لوحة',
        'icon': 'i-dice', 'color': 'var(--accent-green)',
        'lead': 'سباق على لوحة مسار: أجب إجابة صحيحة تبدأ بالحرف المطلوب لترمي النرد وتتقدم.',
        'steps': [
            'اضبط عدد اللاعبين (2-4) واسم كل لاعب.',
            'اللاعب صاحب الدور يضغط الخلية التي تحمل حرفه أو يرمي النرد.',
            'يظهر سؤال من بنك «س.ج» — الجواب الصحيح يبدأ بالحرف المطلوب.',
            'الإجابة الصحيحة ترمي النرد (1-6) وتحرّك قطعتك على المسار.',
            'أول لاعب يصل إلى خط النهاية يفوز بالسباق.',
        ],
        'tip': 'الجواب يجب أن يبدأ بالحرف الظاهر على الخلية — إن أخطأت ينتقل الدور.',
    },
    'lastone': {
        'name': 'آخر واحد!',
        'type': 'مسابقات',
        'icon': 'i-target', 'color': 'var(--accent-gold)',
        'lead': 'أعطِ إجابات صحيحة ومختلفة ضمن التصنيف — من يتعثّر يخسر!',
        'steps': [
            'اختر التصنيف وعدد اللاعبين.',
            'يظهر تصنيف ويبدأ الوقت.',
            'كل لاعب يعطي إجابة صحيحة لم تُذكَر من قبل.',
            'الإجابة المكررة أو الخاطئة تُخرجك من الجولة.',
            'آخر لاعب صامد يفوز.',
        ],
        'tip': 'راقب الإجابات السابقة جيدًا؛ التكرار هو أكثر سبب للخروج.',
    },
}

INTRO_KEYS = ('name', 'type', 'icon', 'color', 'lead', 'steps', 'tip')


def intro_skipped(game):
    """هل الشرح مُعفى لهذه اللعبة؟ (كوكيز دائم / جلسة / لكل الألعاب)"""
    # في وضع البطولة تفتح اللعبة داخل إطار، وشاشة الشرح ستفسد تدفق المباراة
    if request.args.get('tourn') == '1':
        return True
    if request.cookies.get(INTRO_ALL_COOKIE) == '1':
        return True
    if request.cookies.get(INTRO_VISIT_COOKIE) == '1':
        return True
    raw = request.cookies.get(INTRO_COOKIE) or ''
    return game in [x.strip() for x in raw.split(',') if x.strip()]


def game_intro_ctx(game):
    info = GAME_INTROS.get(game) or {}
    ctx = {'game': game}
    for k in INTRO_KEYS:
        ctx[k] = info.get(k, [] if k == 'steps' else '')
    return ctx


def serve_game(game, template):
    """يدير شاشة الشرح قبل شاشة الإعداد."""
    if not intro_skipped(game):
        return render_template('game_intro.html', **game_intro_ctx(game))
    return render_template(template, game=game)


@app.route('/games')
def games():
    return render_template('games.html')

@app.route('/game/letters_strikeout')
def game_letters_strikeout():
    return serve_game('letters_strikeout', 'game_letters_strikeout.html')


@app.route('/game/dice_race')
def game_dice_race():
    return serve_game('dice_race', 'game_dice_race.html')


@app.route('/game/letters')
def game_letters():
    return serve_game('letters', 'game_letters.html')

@app.route('/game/quiz')
def game_quiz():
    return serve_game('quiz', 'game_quiz.html')

@app.route('/game/auction')
def game_auction():
    return serve_game('auction', 'game_auction.html')

@app.route('/game/lastone')
def game_lastone():
    return serve_game('lastone', 'game_lastone.html')


@app.route('/game/seen_jeem')
def game_seen_jeem():
    return serve_game('seen_jeem', 'game_seen_jeem.html')

@app.route('/game/million')
def game_million():
    return serve_game('million', 'game_million.html')

@app.route('/game/minebali')
def game_minebali():
    return serve_game('minebali', 'game_minebali.html')

@app.route('/game/<game>/intro')
def game_intro(game):
    """شاشة شرح اللعبة وحدها."""
    if game not in GAME_INTROS:
        return redirect('/games')
    return render_template('game_intro.html', **game_intro_ctx(game))

@app.route('/game/<game>')
def game(game):
    valid = ['codenames','detective','culprit','spy','debate','whoplayer','link','draw_guess',
             'letters_strikeout','dice_race']
    if game not in valid:
        return redirect('/games')
    return serve_game(game, 'game_' + game + '.html')

@app.route('/library')
def question_library():
    """Question management now lives inside the protected admin panel."""
    return redirect('/admin')

@app.route('/how-to-play')
def how_to_play():
    return render_template('how_to_play.html')

@app.route('/offline')
def offline_page():
    from flask import send_from_directory
    return send_from_directory(os.path.join(os.path.dirname(__file__)), 'ألعاب-بدون-إنترنت.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/me')
def me_page():
    return render_template('me.html', title='من أنا')

@app.route('/login')
def login_page():
    """لوحة تسجيل الدخول وإنشاء الحساب."""
    return render_template('login.html', title='تسجيل الدخول')


@app.route('/account')
def account_page():
    """الملف الشخصي — صفحة ترحب بالزائر وتطلب تسجيل الدخول إن لم يكن مسجلًا."""
    return render_template('account.html', title='حسابي')


@app.route('/tournament')
def tournament_page():
    """وضع البطولة: اختر اللعبة وعدد الفرق وابدأ شجرة المباريات."""
    return render_template('tournament.html', title='وضع البطولة')

@app.route('/admin')
def admin():
    return render_template('admin.html')



# ==========================================================================
#   الحسابات (تسجيل الدخول) + البطولات
#   Accounts live in their own file, separate from the football-player bank
#   (/api/players) — that one is the auction game's catalogue, not users.
# ==========================================================================
ACC_FILE = os.path.join(DATA, 'accounts.json')
TOURN_FILE = os.path.join(DATA, 'tournaments.json')
ACCOUNT_COOKIE = 'ameen_account'
ACCOUNT_TOKENS = {}          # token -> account id (process-local, like ADMIN_TOKENS)

AVATARS = ['🦊', '🐺', '🦁', '🐯', '🦅', '🐉', '🦈', '🐋',
           '🦉', '🐆', '🦄', '🐙', '🦖', '🐢', '🦜', '🐬', '🦩', '🐨']
TEAM_COLORS = ['#4f8cff', '#17c38f', '#f6a714', '#f0524f', '#a16bff', '#18c8e6',
               '#ec4899', '#84cc16', '#f97316', '#06b6d4', '#e11d48', '#a855f7',
               '#eab308', '#14b8a6', '#6366f1', '#d946ef']

# The three games that can host a bracket. Kept server-side so the client never
# hardcodes ids that the question banks could disagree with.
TOURNAMENT_GAMES = {
    'quiz': {
        'name': 'س.ج', 'full': 'س.ج — المسابقة الثقافية', 'icon': 'i-question',
        'color': '#a16bff', 'type': 'مسابقات',
        'desc': 'أسئلة من بنك س.ج بفئاته الحقيقية. كل إجابة صحيحة تمنح فريقك نقاط سؤالها.',
        'duel': 'سؤال لكل فريق وبالدور، مع المؤقّت والسرقة — الأعلى نقاطًا يتأهّل.',
    },
    'letters': {
        'name': 'حروف مع أمين', 'full': 'حروف مع أمين — سباق الحروف', 'icon': 'i-shield',
        'color': '#17c38f', 'type': 'مسابقات',
        'desc': 'تحدي الحروف: حرف وسؤال، والإجابة الصحيحة تمنح فريقك نقطة في المباراة.',
        'duel': 'تحدّي حرف لكل فريق وبالدور من بنك «حروف مع أمين» — الأكثر إصابة يتأهّل.',
    },
    'draw_guess': {
        'name': 'ارسم وخمّن', 'full': 'ارسم وخمّن — لوحة وتخمين', 'icon': 'i-draw',
        'color': '#4f8cff', 'type': 'كلمات ومهارات',
        'desc': 'ارسم الكلمة السرية على اللوحة وفريقك يخمّن قبل انتهاء الوقت.',
        'duel': 'جولة رسم لكل فريق وبالدور — إصابة أبكر تمنح نقاطًا أكثر.',
    },
}


def _hash_pw(password, salt=None):
    """PBKDF2-HMAC-SHA256. The plain password is never stored, not even reversed."""
    if not salt:
        salt = uuid.uuid4().hex[:16]
    digest = hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'),
                                 salt.encode('utf-8'), 120000).hex()
    return salt, digest


def _verify_pw(password, salt, digest):
    if not salt or not digest:
        return False
    try:
        return _hash_pw(password, salt)[1] == digest
    except Exception:
        return False


def load_accounts():
    return load_json(ACC_FILE, [])


def save_accounts(accounts):
    save_json(ACC_FILE, accounts)


def find_account(username):
    key = norm_ar(username).strip().lower()
    if not key:
        return None
    for a in load_accounts():
        if norm_ar(a.get('username', '')).strip().lower() == key:
            return a
    return None


def public_account(a):
    """Only the fields a browser may see — never the salt or the digest."""
    if not a:
        return None
    return {
        'id': a.get('id'),
        'username': a.get('username', ''),
        'name': a.get('name', ''),
        'avatar': a.get('avatar', '🎮'),
        'color': a.get('color', TEAM_COLORS[0]),
        'createdAt': a.get('createdAt', ''),
        'stats': a.get('stats', {}),
        'trophies': a.get('trophies', []),
    }


def current_account():
    token = request.cookies.get(ACCOUNT_COOKIE) or request.headers.get('X-Account-Token', '')
    if not token:
        return None
    acc_id = ACCOUNT_TOKENS.get(token)
    if not acc_id:
        return None
    for a in load_accounts():
        if a.get('id') == acc_id:
            return a
    return None


@app.context_processor
def inject_account():
    """Every template can read the signed-in account without a fetch."""
    return {'current_account': public_account(current_account())}


def _account_stats(acc):
    return acc.setdefault('stats', {
        'tournamentsPlayed': 0, 'tournamentsWon': 0,
        'matchesPlayed': 0, 'matchesWon': 0, 'points': 0,
    })


def _bump_account(acc_id, **kw):
    accounts = load_accounts()
    for a in accounts:
        if a.get('id') == acc_id:
            st = _account_stats(a)
            for k, v in kw.items():
                st[k] = int(st.get(k, 0)) + int(v)
            a['stats'] = st
            save_accounts(accounts)
            return a
    return None


@app.route('/api/accounts/register', methods=['POST'])
def account_register():
    body = request.get_json(silent=True) or {}
    username = str(body.get('username', '')).strip()
    name = str(body.get('name', '')).strip()
    password = str(body.get('password', ''))

    if len(username) < 3 or len(username) > 24:
        return jsonify({'error': 'اسم المستخدم لازم يكون بين 3 و 24 حرفًا'}), 400
    # \w in Python 3 already covers Arabic letters, so this admits Arabic and
    # Latin usernames alike while still rejecting spaces and punctuation.
    if not re.fullmatch(r'\w{3,24}', username):
        return jsonify({'error': 'اسم المستخدم يقبل الحروف والأرقام والشرطة السفلية فقط'}), 400
    if find_account(username):
        return jsonify({'error': 'اسم المستخدم هذا محجوز — جرّب اسمًا آخر'}), 409
    if len(password) < 4:
        return jsonify({'error': 'كلمة المرور لازم تكون 4 أحرف على الأقل'}), 400
    if not name:
        name = username

    accounts = load_accounts()
    salt, digest = _hash_pw(password)
    acc = {
        'id': gen_id(),
        'username': username,
        'name': name,
        'salt': salt,
        'pass': digest,
        'avatar': AVATARS[len(accounts) % len(AVATARS)],
        'color': TEAM_COLORS[len(accounts) % len(TEAM_COLORS)],
        'createdAt': now(),
        'stats': {'tournamentsPlayed': 0, 'tournamentsWon': 0,
                  'matchesPlayed': 0, 'matchesWon': 0, 'points': 0},
        'trophies': [],
    }
    accounts.append(acc)
    save_accounts(accounts)

    token = uuid.uuid4().hex
    ACCOUNT_TOKENS[token] = acc['id']
    resp = make_response(jsonify({'ok': True, 'account': public_account(acc)}), 201)
    resp.set_cookie(ACCOUNT_COOKIE, token, max_age=60 * 60 * 24 * 365,
                    samesite='Lax', httponly=True)
    return resp


@app.route('/api/accounts/login', methods=['POST'])
def account_login():
    body = request.get_json(silent=True) or {}
    username = str(body.get('username', '')).strip()
    password = str(body.get('password', ''))
    acc = find_account(username)
    # Same message either way: never reveal which of the two was wrong.
    if not acc or not _verify_pw(password, acc.get('salt'), acc.get('pass')):
        return jsonify({'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401
    token = uuid.uuid4().hex
    ACCOUNT_TOKENS[token] = acc['id']
    resp = make_response(jsonify({'ok': True, 'account': public_account(acc)}))
    resp.set_cookie(ACCOUNT_COOKIE, token, max_age=60 * 60 * 24 * 365,
                    samesite='Lax', httponly=True)
    return resp


@app.route('/api/accounts/logout', methods=['POST'])
def account_logout():
    token = request.cookies.get(ACCOUNT_COOKIE) or ''
    ACCOUNT_TOKENS.pop(token, None)
    resp = make_response(jsonify({'ok': True}))
    resp.delete_cookie(ACCOUNT_COOKIE, path='/')
    return resp


@app.route('/api/accounts/me', methods=['GET'])
def account_me():
    return jsonify({'account': public_account(current_account())})


@app.route('/api/accounts', methods=['GET'])
def account_list():
    """Public directory: safe fields only, so the tournament can credit a win."""
    out = [public_account(a) for a in load_accounts()]
    out.sort(key=lambda a: (a.get('stats', {}).get('tournamentsWon', 0),
                            a.get('stats', {}).get('points', 0)), reverse=True)
    return jsonify({'accounts': out, 'total': len(out)})


@app.route('/api/accounts/me', methods=['PUT'])
def account_update():
    acc = current_account()
    if not acc:
        return jsonify({'error': 'سجّل الدخول أولًا'}), 401
    body = request.get_json(silent=True) or {}
    accounts = load_accounts()
    target = None
    for a in accounts:
        if a.get('id') == acc['id']:
            target = a
            break
    if target is None:
        return jsonify({'error': 'الحساب غير موجود'}), 404

    if body.get('name'):
        target['name'] = str(body['name']).strip()[:40]
    if body.get('avatar') in AVATARS:
        target['avatar'] = body['avatar']
    if body.get('color') in TEAM_COLORS:
        target['color'] = body['color']

    new_pw = str(body.get('password', '') or '')
    if new_pw:
        cur = str(body.get('currentPassword', '') or '')
        if not _verify_pw(cur, target.get('salt'), target.get('pass')):
            return jsonify({'error': 'كلمة المرور الحالية غير صحيحة'}), 400
        if len(new_pw) < 4:
            return jsonify({'error': 'كلمة المرور الجديدة لازم تكون 4 أحرف على الأقل'}), 400
        target['salt'], target['pass'] = _hash_pw(new_pw)

    save_accounts(accounts)
    return jsonify({'ok': True, 'account': public_account(target)})


@app.route('/api/accounts/<aid>', methods=['DELETE'])
def account_delete(aid):
    """Only an admin may delete an account — players cannot wipe each other."""
    if not is_admin(request):
        return jsonify({'error': 'غير مصرّح'}), 401
    accounts = load_accounts()
    target = next((a for a in accounts if a.get('id') == aid), None)
    if not target:
        return jsonify({'error': 'الحساب غير موجود'}), 404
    save_accounts([a for a in accounts if a.get('id') != aid])
    for tok, owner in list(ACCOUNT_TOKENS.items()):
        if owner == aid:
            ACCOUNT_TOKENS.pop(tok, None)
    return jsonify({'ok': True})


# ============ TOURNAMENTS ============
@app.route('/api/tournament/config', methods=['GET'])
def tournament_config():
    return jsonify({
        'games': TOURNAMENT_GAMES,
        'sizes': [4, 8, 16],
        'defaultSize': 8,
        'perTeamRounds': 3,
        'avatars': AVATARS,
        'colors': TEAM_COLORS,
    })


@app.route('/api/tournament/pool', methods=['GET'])
def tournament_pool():
    """عينة عشوائية جاهزة لمباريات البطولة.

    تُختار جهة الخادم عن قصد: تنزيل بنك الأسئلة كاملًا إلى المتصفح عند كل
    بطولة كان سيعيد إرسال عشرات الآلاف من الأسئلة لشيء يحتاج أقل من عشرين.
    """
    game = request.args.get('game', '')
    if game not in TOURNAMENT_GAMES:
        return jsonify({'error': 'اللعبة غير مدعومة في وضع البطولة'}), 400
    try:
        count = int(request.args.get('count', 24) or 24)
    except (TypeError, ValueError):
        count = 24
    count = max(6, min(60, count))

    if game == 'quiz':
        bank = [q for q in load_bank()
                if q.get('game') == 'quiz'
                and q.get('status') == 'approved'
                and norm_ar(q.get('answer'))]
        _rnd.shuffle(bank)
        qs = [{
            'id': q.get('id'),
            'question': q.get('question', ''),
            'answer': q.get('answer', ''),
            'points': int(q.get('points') or 200),
            'difficulty': q.get('difficulty') or 'medium',
            'category': q.get('category_name') or '',
            'explanation': q.get('explanation') or '',
            'image': q.get('image') or '',
            'alternatives': q.get('alternatives') or [],
        } for q in bank[:count]]
        if not qs:
            return jsonify({'error': 'بنك أسئلة س.ج فاضي — أضف أسئلة أولًا'}), 404
        return jsonify({'game': game, 'challenges': qs, 'total': len(qs)})

    if game == 'letters':
        # نفس الدالة التي تستخدمها لعبة «شطب الحروف» حتى لا تختلف البطولة عن اللعبة.
        idx = bank_letters_index()
        avail = [l for l in AR_LETTERS if idx.get(l)]
        if not avail:
            return jsonify({'error': 'ما فيه أسئلة حروف متاحة في البنك'}), 404
        _rnd.shuffle(avail)
        # نوزّع الطلب على أكبر عدد ممكن من الحروف المختلفة بدل ملء كل المقاعد
        # من الحرف الأول — وإلا صارت كل التحديات حرفًا واحدًا مكررًا.
        per_letter = max(1, count // max(1, len(avail)))
        out = []
        for letter in avail:
            if len(out) >= count:
                break
            for q in letters_strikeout_pool(letter, per_letter):
                if len(out) >= count:
                    break
                out.append({
                    'letter': letter,
                    'id': q.get('id'),
                    'question': q.get('question', ''),
                    'answer': q.get('answer', ''),
                    'difficulty': q.get('difficulty') or 'medium',
                    'explanation': q.get('explanation') or '',
                })
        if not out:
            return jsonify({'error': 'ما فيه أسئلة حروف متاحة في البنك'}), 404
        return jsonify({'game': game, 'challenges': out, 'total': len(out)})

    # draw_guess
    items = load_json(content_file('draw_guess'), [])
    items = [x for x in items if x.get('status') == 'approved' and norm_ar(x.get('word'))]
    _rnd.shuffle(items)
    words = [{
        'id': x.get('id'),
        'word': x.get('word', ''),
        'altAccepted': x.get('altAccepted') or [],
        'category': x.get('category') or '',
        'difficulty': x.get('difficulty') or 'easy',
    } for x in items[:count]]
    if not words:
        return jsonify({'error': 'بنك كلمات الرسم فاضي — أضف كلمات أولًا'}), 404
    return jsonify({'game': game, 'challenges': words, 'total': len(words)})

@app.route('/api/tournaments', methods=['GET'])
def tournament_list():
    rows = load_json(TOURN_FILE, [])
    rows.sort(key=lambda r: r.get('createdAt', ''), reverse=True)
    return jsonify({'tournaments': rows[:40], 'total': len(rows)})


@app.route('/api/tournaments', methods=['POST'])
def tournament_save():
    body = request.get_json(silent=True) or {}
    game = body.get('game')
    if game not in TOURNAMENT_GAMES:
        return jsonify({'error': 'اللعبة غير مدعومة في وضع البطولة'}), 400
    teams = body.get('teams') or []
    if not isinstance(teams, list) or len(teams) < 2:
        return jsonify({'error': 'البطولة تحتاج فريقين على الأقل'}), 400
    champion = body.get('champion') or {}
    if not champion.get('name'):
        return jsonify({'error': 'لا يمكن حفظ بطولة بلا فائز'}), 400

    host = current_account()
    record = {
        'id': gen_id(),
        'game': game,
        'size': int(body.get('size') or len(teams)),
        'champion': {'id': champion.get('id'), 'name': champion.get('name')},
        'teams': [{'id': t.get('id'), 'name': t.get('name'),
                   'accountId': t.get('accountId')} for t in teams],
        'matches': body.get('matches') or [],
        'roundsPlayed': int(body.get('roundsPlayed') or 0),
        'host': {'id': host.get('id'), 'name': host.get('name')} if host else None,
        'createdAt': now(),
    }
    rows = load_json(TOURN_FILE, [])
    rows.append(record)
    # Keep the file bounded: history beyond the newest 200 is not useful.
    save_json(TOURN_FILE, rows[-200:])

    # Credit every account that took part, and the champion's win.
    credited = set()
    for t in record['teams']:
        aid = t.get('accountId')
        if not aid or aid in credited:
            continue
        credited.add(aid)
        won = 1 if (champion.get('accountId') and champion['accountId'] == aid) else 0
        _bump_account(aid, tournamentsPlayed=1, tournamentsWon=won)

    for m in record.get('matches', []):
        for key, delta in (('winner', 'matchesWon'),):
            w = m.get(key) or {}
            wid = w.get('accountId')
            if wid:
                _bump_account(wid, **{delta: 1})
        for side in ('a', 'b'):
            t = m.get(side) or {}
            if t.get('accountId'):
                _bump_account(t['accountId'], matchesPlayed=1, points=int(m.get('score' + side.upper()) or 0))

    return jsonify({'ok': True, 'tournament': record})


@app.route('/api/tournaments/leaderboard', methods=['GET'])
def tournament_leaderboard():
    accounts = [public_account(a) for a in load_accounts()]
    accounts = [a for a in accounts if a.get('stats')]
    accounts.sort(key=lambda a: (a['stats'].get('tournamentsWon', 0),
                                 a['stats'].get('points', 0)), reverse=True)
    return jsonify({'leaderboard': accounts[:20]})

# ============ STATIC / UPLOADS ============
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/uploads/<path:path>')
def send_upload(path):
    return send_from_directory(UPLOAD_DIR, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5555))
    debug = os.environ.get('AMEEN_DEBUG', '0') == '1'
    print('ألعاب أمين — http://localhost:' + str(port))
    print('مكتبة الأسئلة — http://localhost:' + str(port) + '/library')
    print('NVIDIA API: ' + ('مُعد' if NVIDIA_API_KEY else 'غير مُعد'))
    app.run(host='0.0.0.0', port=port, debug=debug)
