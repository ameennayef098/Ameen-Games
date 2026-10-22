#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulk question generator for ألعاب أمين (Ameen Games).

Appends validated questions to data/questions/all.json through an exclusive
lock file, so two generators running at the same time never lose each other's
writes. Every item is validated with the SAME rules the Flask server uses
(Arabic-only, letter match, points match) before it is stored.

Each (category, difficulty) target is generated in rounds of `batch` items
until the requested count is reached or `max_rounds` is exhausted, so a few
rejected items never leave the target short.

Usage
-----
Quiz, one category, all three difficulties split evenly:
    python tools/bulk_gen.py --game quiz --category sports --all-difficulties --count 100

Quiz, every category, all difficulties:
    python tools/bulk_gen.py --game quiz --all-categories --all-difficulties --count 100

Letters, one letter:
    python tools/bulk_gen.py --game letters --letter ز --count 10

Letters, every letter:
    python tools/bulk_gen.py --game letters --all-letters --count 10

Report current bank (no API calls):
    python tools/bulk_gen.py --report

Options
-------
--workers N      parallel API calls (default 3, keep <= 4 to respect rate limits)
--dry-run        validate and print, do NOT write to all.json
--max-rounds N   rounds per target before giving up (default 10)
"""
import argparse
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from gsema import limit

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, 'data')
QFILE = os.path.join(DATA_DIR, 'questions', 'all.json')
CATFILE = os.path.join(DATA_DIR, 'categories', 'categories.json')
LOCKFILE = os.path.join(DATA_DIR, '.all.lock')
ENVFILE = os.path.join(BASE, '.env')

AR_LETTERS = ['أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ر', 'ز', 'س', 'ش', 'ص',
              'ط', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ي']

FOREIGN_CHARS = re.compile(
    r'[\u0400-\u04FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF\u0E00-\u0E7F\u0590-\u05FF]')

# Latin tokens that are legitimate knowledge rather than a leaked foreign
# language: chemical element symbols (written this way in Arabic textbooks),
# compounds/units, blood groups, and technology acronyms. Anything else Latin
# is a model leak ("material", "meter", "the") and gets rejected.
ALLOWED_LATIN = set(x.upper() for x in """
H HE LI BE B C N O F NE NA MG AL SI P S CL AR K CA SC TI V CR MN FE CO NI CU ZN
GA GE AS SE BR KR RB SR Y ZR NB MO TC RU RH PD AG CD IN SN SB TE I XE CS BA LA
CE PR ND PM SM EU GD TB DY HO ER TM YB LU HF TA W RE OS IR PT AU HG TL PB BI PO
AT RN FR RA AC TH PA U NP PU AM CM BK CF ES FM MD NO LR RF DB SG BH HS MT DS RG
CN NH FL MC LV TS OG
HCL NACL H2O CO2 NO2 SO2 O2 N2 H2 NH3 CH4 NAOH H2SO4 KOH CAO MGO SIO2 AL2O3
FE2O3 FE3O4 HNO3 H2CO3 KMNO4 K2CR2O7 CACO3 NANO3 CUSO4 ZNSO4 MGCL2 HBR HI HF
A B AB O
ATP ADP AMP DNA RNA RNA PCR HIV AIDS HPV TB BCG MRI CT ECG EEG EMG ICU ER OR
BP BMI DNA GMO
JS TS HTML CSS HTTP HTTPS API CPU GPU RAM ROM USB AI ML IT TV PC GPS URL URI SQL
PHP XML JSON YAML VPN DNS IP TCP UDP FTP SSH SSL TLS WIFI LAN WAN OS UI UX IDE SDK
CEO CFO NASA ESA ISRO FBI CIA USA UK EU UN WHO IMF GDP GNP ATM PIN SMS
CD DVD MP3 MP4 PDF JPG PNG GIF SVG CSV XLS DOC PPT IoT VR AR
X Y Z T M J W Q V
HZ KHZ MHZ GHZ PH DB DBM
""" .split())


def has_foreign(text):
    """True when the text holds a non-Arabic script we cannot justify.

    Arabic textbooks legitimately carry chemical symbols (Fe, Au, Na), blood
    groups (O, AB) and tech acronyms (HTTP, JS) in Latin — those are allowed.
    A whole Latin *word* such as "material" or "meter" is a model leak and is
    rejected, as is any Cyrillic/CJK/Hebrew/Thai text.
    """
    t = str(text or '')
    if FOREIGN_CHARS.search(t):
        return True
    for tok in re.findall(r'[A-Za-z]+', t):
        if tok.upper() not in ALLOWED_LATIN:
            return True
    return False


# --------------------------------------------------------------------------
# config / api
# --------------------------------------------------------------------------
def load_env():
    env = {}
    if not os.path.exists(ENVFILE):
        return env
    with open(ENVFILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
API_KEY = ENV.get('NVIDIA_API_KEY', '')
MODEL = ENV.get('NVIDIA_MODEL', 'nvidia/nemotron-3.5-lightning-30b-a3b')
URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
VERIFY = False

# The account may not be entitled to the model chosen in .env (NVIDIA returns
# HTTP 404 "Function ... not found for account" even though the model is listed
# publicly). Rather than making generation hard-fail, fall back to a model the
# account IS entitled to, and report the switch once per process.
FALLBACK_MODELS = ['nvidia/nemotron-3-ultra-550b-a55b',
                   'nvidia/nemotron-3.5-lightning-30b-a3b']
_USED_MODEL = {'name': MODEL}
_fallback_warned = {'done': False}


def current_model():
    """The model actually being used (may be a fallback)."""
    return _USED_MODEL['name']


def _call_model(model, prompt, timeout, temperature):
    # Every process on the machine shares one API budget: 10 generation agents
    # with their own workers would otherwise push ~30 concurrent calls and the
    # account answers with 429s.
    with limit('nvidia', slots=int(os.environ.get('AMEEN_API_SLOTS', 6))):
        return _call_model_raw(model, prompt, timeout, temperature)


def _call_model_raw(model, prompt, timeout, temperature):
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': temperature,
        'chat_template_kwargs': {'enable_thinking': False},
    }).encode('utf-8')
    req = urllib.request.Request(
        URL, data=body,
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + API_KEY})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data['choices'][0]['message']['content']


def nvidia_chat(prompt, timeout=120, temperature=0.85, retries=3):
    last = ''
    for attempt in range(retries):
        for model in [MODEL] + FALLBACK_MODELS:
            try:
                out = _call_model(model, prompt, timeout, temperature)
                if model != MODEL:
                    _USED_MODEL['name'] = model
                    if not _fallback_warned['done']:
                        _fallback_warned['done'] = True
                        print('    (model %s unavailable — using %s instead)'
                              % (MODEL, model))
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode('utf-8')[:160]
                last = 'HTTP %s %s' % (e.code, detail)
                # 404 = not entitled to this model -> try the next one.
                # 429/5xx = transient -> retry the same model after a pause.
                if e.code == 404:
                    continue
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
            except Exception as e:  # timeout, connection reset, ...
                last = '%s: %s' % (type(e).__name__, e)
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(last)


def extract_json_array(text):
    """Parse a JSON array out of a model reply.

    Models wrap the array in prose or code fences, truncate it, or leave a
    dangling comma. Scan for a *balanced* bracket region first, then fall back
    to parsing each object individually.
    """
    if not text or not str(text).strip():
        raise ValueError('empty model response')
    t = re.sub(r'```(?:json|JSON)?', '', str(text)).strip()

    start = t.find('[')
    while start != -1:
        depth = 0
        instr = False
        esc = False
        for i in range(start, len(t)):
            ch = t[i]
            if instr:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    instr = False
                continue
            if ch == '"':
                instr = True
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    cand = t[start:i + 1]
                    cand = re.sub(r',\s*([\]}])', r'\1', cand)
                    try:
                        return json.loads(cand)
                    except Exception:
                        break
        start = t.find('[', start + 1)

    # last resort: pull out every {...} object on its own
    objs = []
    for m in re.finditer(r'\{[^{}]*\}', t):
        try:
            objs.append(json.loads(m.group()))
        except Exception:
            continue
    if objs:
        return objs
    raise ValueError('no JSON array found in model response')


# --------------------------------------------------------------------------
# validation (mirrors server.py)
# --------------------------------------------------------------------------
def norm_ar(t):
    if not t:
        return ''
    t = str(t)
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    t = re.sub(r'[أإآٱ]', 'ا', t)
    t = t.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    t = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def first_letter_of(answer):
    a = norm_ar(answer)
    if not a:
        return ''
    if a[0] in ('إ', 'آ', 'ٱ'):
        a = 'أ' + a[1:]
    if a[0] == 'ه':
        a = 'هـ' + a[1:]
    if a.startswith('ال') and len(a) > 2:
        a = a[2:]
    return a[:1] if a else ''


def validate_quiz_item(item):
    if not isinstance(item, dict):
        return False
    q = str(item.get('question', '')).strip()
    a = str(item.get('answer', '')).strip()
    if not q or not a:
        return False
    if has_foreign(q) or has_foreign(a):
        return False
    if len(a) > 60:
        return False
    if a in q:
        return False
    return True


def validate_letters_item(item, letter, difficulty='medium'):
    if not isinstance(item, dict):
        return False
    q = str(item.get('question', '')).strip()
    a = str(item.get('answer', '')).strip()
    if not q or not a:
        return False
    if has_foreign(q) or has_foreign(a):
        return False
    if first_letter_of(a) != norm_ar(letter):
        return False
    # easy must be a single word, medium at most two, hard at most three —
    # otherwise the difficulty label is a lie the player can see.
    limit = {'easy': 1, 'medium': 2, 'hard': 3}[difficulty]
    if len(a.split()) > limit:
        return False
    return True


# --------------------------------------------------------------------------
# locked append
# --------------------------------------------------------------------------
def acquire_lock(timeout=180):
    start = time.time()
    while True:
        try:
            fd = os.open(LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(LOCKFILE)
            except OSError:
                age = 0
            if age > 90:
                try:
                    os.remove(LOCKFILE)
                except OSError:
                    pass
                continue
            if time.time() - start > timeout:
                raise TimeoutError('all.json lock busy for %ss' % timeout)
            time.sleep(0.4)


def read_all():
    with open(QFILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _replace_with_retry(tmp, dst, attempts=15, delay=0.4):
    """os.replace fails with WinError 5 when another process holds the
    destination open for an instant — the Flask server reads all.json on every
    /api/questions call. Retry briefly instead of losing a whole generation
    round to a race that resolves itself in milliseconds."""
    last = None
    for _ in range(attempts):
        try:
            os.replace(tmp, dst)
            return
        except OSError as e:
            last = e
            time.sleep(delay)
    raise last


def append_locked(items):
    """Append items to all.json atomically under an exclusive lock."""
    if not items:
        return 0
    acquire_lock()
    try:
        data = read_all()
        data.extend(items)
        tmp = QFILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _replace_with_retry(tmp, QFILE)
        return len(items)
    finally:
        try:
            os.remove(LOCKFILE)
        except OSError:
            pass


def existing_keys(game):
    out = set()
    for q in read_all():
        if q.get('game') != game:
            continue
        out.add(q.get('game', '') + '|' + norm_ar(q.get('question', '')))
    return out


# --------------------------------------------------------------------------
# prompts
# --------------------------------------------------------------------------
DIFF_AR = {'easy': 'سهل', 'medium': 'متوسط', 'hard': 'صعب'}
DIFF_HINT = {
    'easy': 'معلومة معروفة للجميع، مباشرة جداً',
    'medium': 'معلومة ثقافية عامة يتوقع المثقف معرفتها',
    'hard': 'معلومة متخصصة أو نادرة تحتاج تركيزاً',
}

# محاور مقترحة لكل فئة — تمنع النموذج من حشر كل الأسئلة في جانب واحد
CAT_TOPICS = {
    'sports': 'كرة القدم، البطولات، اللاعبون، الأولمبياد، الرياضات الأخرى، الأندية',
    'science': 'الفيزياء، الكيمياء، الأحياء، الفلك، الأرض، الاكتشافات العلمية',
    'history': 'الحضارات، الحروب، الخلفاء، الدول، الأحداث المصيرية، التواريخ',
    'geography': 'القارات، التضاريس، المناخ، الجزر، الأقاليم، الحدود',
    'movies': 'أفلام مشهورة، مخرجون، ممثلون، جوائز، رسوم متحركة، مسلسلات',
    'general': 'معلومات عامة متنوعة: أعلام، عادات، أرقام قياسية، ثقافات',
    'tech': 'البرمجة، الشركات، الأجهزة، الإنترنت، الذكاء الاصطناعي، لغات البرمجة',
    'literature': 'الشعر، النثر، المؤلفون، الكتب، النقد الأدبي، المسرح',
    'puzzles': 'ألغاز منطقية، رياضيات ترفيهية، متسلسلات عددية، ألعاب ذكاء',
    'islamic': 'القرآن، السنة، السيرة، الفقه، العبادات، التاريخ الإسلامي',
    'arabic': 'النحو، الصرف، البلاغة، المعاجم، الأدب، الأخطاء الشائعة',
    'math': 'الجبر، الهندسة، التفاضل والتكامل، الاحتمالات، الأعداد، النظريات',
    'physics': 'الميكانيكا، الكهرباء، الضوء، الحرارة، الفيزياء الحديثة',
    'chemistry': 'العناصر، التفاعلات، الروابط، الأحماض والقواعد، الجدول الدوري',
    'biology': 'الخلية، الوراثة، التصنيف، الأجهزة، البيئة، التطور',
    'space': 'الكواكب، النجوم، المجرات، المركبات الفضائية، رواد الفضاء',
    'countries': 'العواصم، المساحات، السكان، اللغات، أعلام الدول، الانتماءات',
    'health': 'التغذية، الأمراض، الأعضاء، الفيتامينات، الإسعافات، الطب',
    'food': 'الأطباق، المكونات، المشروبات، الفواكه، الحلويات، العادات الغذائية',
    'arts': 'الرسم، النحت، الخط، الموسيقى البصرية، الفنانون، المدارس الفنية',
    'music': 'المقامات، الآلات، المطربون، الملحنون، الأغاني، العروض',
    'economy': 'الأسواق، التجارة، التضخم، الشركات، العملات، الموارد',
    'politics': 'الأنظمة، الأحزاب، الانتخابات، الدساتير، المنظمات، العلاقات',
    'e6e3c106': 'جغرافيا الأردن، تاريخه، آثاره، مدنه، عملته، محافظاته، شخصياته',
    'transport': 'السيارات، القطارات، الطائرات، السفن، الطرق، المواصلات العامة',
    'agriculture': 'المحاصيل، التربة، الري، الثروة الحيوانية، البيئة، الغابات',
    'inventions': 'المخترعون، تواريخ الاختراع، براءات الاختراع، الاختراعات القديمة والحديثة',
    'currencies': 'العملات، البنوك، أسعار الصرف، الرموز، العملات القديمة، التضخم',
    'internet': 'الشبكات، البروتوكولات، المواقع، الاختراقات، التواصل الاجتماعي، الحوسبة السحابية',
    'energy': 'الكهرباء، الطاقة المتجددة، النفط، الغاز، المفاعلات، التوليد',
    'tourism': 'المعالم، المتاحف، المواقع الأثرية، المدن السياحية، الطبيعة',
    'basketball': 'كرة السلة، الدوري، اللاعبون، الفرق، القوانين، البطولات',
    'history_figures': 'الزعماء، العلماء، المستكشفون، القادة العسكريون، المصلحون',
    'human_body': 'الأعضاء، العظام، العضلات، الدم، الأعصاب، الحواس، الهرمونات',
}


def cat_topics(cat_id):
    """Topic axes for a category: the row's own `topics` if present, else the
    built-in table. New categories carry their axes on the row so they are
    visible and editable in the admin panel instead of hidden in code."""
    try:
        for c in json.load(open(CATFILE, encoding='utf-8')):
            if c.get('id') == cat_id:
                return c.get('topics') or CAT_TOPICS.get(cat_id, '')
    except Exception:
        pass
    return CAT_TOPICS.get(cat_id, '')


def quiz_prompt(cat_name, difficulty, n, avoid_lines, cat_id=''):
    avoid = ''
    if avoid_lines:
        # Feed the WHOLE existing bank (capped) so a late-stage category whose
        # bank already holds ~90 questions is not re-served the same 60 it saw
        # last time. A 60-item window made the model recycle its own answers.
        avoid = '\n\nهذه الأسئلة موجودة بالفعل — يُمنع تكرارها أو إعادة صياغتها:\n' + \
                '\n'.join('- ' + t for t in avoid_lines[:400])
    topics = cat_topics(cat_id)
    topic_rule = ''
    if topics:
        topic_rule = ('8) وزّع الأسئلة على محاور الفئة المختلفة: ' + topics +
                      '.\n')
    return (
        'أنت معدّ أسئلة مسابقات ثقافية للعبة «س.ج».\n'
        'المطلوب: ' + str(n) + ' سؤالاً جديداً في فئة «' + cat_name + '» '
        'بمستوى صعوبة ' + DIFF_AR[difficulty] + '.\n\n'
        'القواعد الصارمة:\n'
        '1) الإجابة كلمة أو رقم أو اسم قصير — لا جملة طويلة.\n'
        '2) كل النصوص عربية فقط — ممنوع أي حرف لاتيني أو أجنبي إطلاقاً.\n'
        '3) نص السؤال لا يحتوي على الإجابة.\n'
        '4) لا تكرر أي سؤال ولا قريباً من معنى موجود.\n'
        '5) مستوى الصعوبة ' + DIFF_AR[difficulty] + ': ' + DIFF_HINT[difficulty] + '.\n'
        '6) المعلومة يجب أن تكون صحيحة وموثوقة.\n'
        '7) نوّع الموضوعات داخل الفئة: لا تجعل كل الأسئلة عن جانب واحد.\n'
        + topic_rule +
        '\nالصيغة: [{"question":"...","answer":"...","explanation":"..."}]\n'
        'أعد مصفوفة JSON فقط بلا أي نص إضافي.' + avoid
    )


def letters_prompt(letter, n, avoid_lines):
    avoid = ''
    if avoid_lines:
        avoid = '\n\nهذه الأسئلة موجودة بالفعل — يُمنع تكرارها:\n' + \
                '\n'.join('- ' + t for t in avoid_lines[:60])
    return (
        'أنت معدّ أسئلة مسابقات عربية دقيقة جداً.\n'
        'المطلوب: ' + str(n) + ' سؤالاً إجابته كلمة عربية واحدة تبدأ بحرف «' + letter + '».\n\n'
        'كل سؤال يجب أن يكون عن معلومة محددة ومعروفة من هذه المجالات فقط: '
        'العواصم والدول، الحيوانات، الكواكب والفضاء، المخترعون والعلماء، العناصر الكيميائية، '
        'الجبال والأنهار والبحار، الرياضة والرياضيون، الأحداث التاريخية المشهورة، '
        'جسم الإنسان، النباتات المشهورة.\n\n'
        'أمثلة على الشكل الصحيح:\n'
        '{"question":"ما هو الحيوان الملقب بسفينة الصحراء؟","answer":"الجمل"}\n'
        '{"question":"ما اسم أكبر كوكب في المجموعة الشمسية؟","answer":"المشتري"}\n'
        '{"question":"ما هي عاصمة المملكة العربية السعودية؟","answer":"الرياض"}\n\n'
        'أمثلة على الشكل الخاطئ — لا تفعل هذا إطلاقاً:\n'
        '{"question":"ما اسم الشيء الذي يبدأ بحرف «' + letter + '»؟","answer":"' + letter + 'دان"}\n'
        '(السبب: السؤال يذكر الحرف المطلوب، والإجابة كلمة غير حقيقية أو مختلقة)\n\n'
        'القواعد الصارمة:\n'
        '1) الإجابة كلمة واحدة فقط (أو كلمتان بحد أقصى) — لا جملة ولا شرح.\n'
        '2) الإجابة مكتوبة بالحروف العربية فقط. ممنوع أي حرف لاتيني أو أجنبي.\n'
        '3) الإجابة تبدأ فعلاً بحرف «' + letter + '». إن كانت معرفة بـ«ال» فالحرف بعدها.\n'
        '4) الإجابة كلمة عربية حقيقية ومعروفة ومستخدمة — ممنوع اختراع كلمات أو تحريفها.\n'
        '5) المعلومة يجب أن تكون صحيحة وموثوقة تماماً. لا تخمّن ولا تقل شيئاً غير متأكد منه.\n'
        '6) نص السؤال لا يحتوي على الإجابة، ولا يذكر اسم الحرف أو عبارات مثل «يبدأ بحرف».\n'
        '7) لا تكرر أي سؤال.\n'
        '\nالصيغة: [{"question":"...","answer":"...","explanation":"..."}]\n'
        'أعد مصفوفة JSON فقط بلا أي نص إضافي.' + avoid
    )


# --------------------------------------------------------------------------
# batch builders
# --------------------------------------------------------------------------
def _ts():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def build_quiz_item(it, cat_id, cat_name, difficulty):
    return {
        'id': uuid.uuid4().hex[:8],
        'game': 'quiz',
        'question': str(it['question']).strip(),
        'answer': str(it['answer']).strip(),
        'explanation': str(it.get('explanation', '')).strip(),
        'category_id': cat_id,
        'category_name': cat_name,
        'difficulty': difficulty,
        'points': {'easy': 200, 'medium': 400, 'hard': 600}[difficulty],
        'status': 'approved',
        'source': 'ai',
        'created_at': _ts(),
        'updated_at': _ts(),
    }


def build_letters_item(it, letter, difficulty='medium'):
    return {
        'id': uuid.uuid4().hex[:8],
        'game': 'letters',
        'letter': letter,
        'question': str(it['question']).strip(),
        'answer': str(it['answer']).strip(),
        'explanation': str(it.get('explanation', '')).strip(),
        'difficulty': difficulty,
        'status': 'approved',
        'source': 'ai',
        'created_at': _ts(),
        'updated_at': _ts(),
    }


def fetch_quiz_batch(cat_id, cat_name, difficulty, n, temperature=0.95):
    avoid = [q['question'] for q in read_all()
             if q.get('game') == 'quiz' and q.get('category_id') == cat_id]
    content = nvidia_chat(quiz_prompt(cat_name, difficulty, n, avoid, cat_id),
                          temperature=temperature)
    out = []
    for it in extract_json_array(content):
        if validate_quiz_item(it):
            out.append(build_quiz_item(it, cat_id, cat_name, difficulty))
    if VERIFY:
        out = verify_items(out)
    return out


def fetch_letter_words(letter, n, difficulty='medium'):
    """Step 1: ask the model for real Arabic words starting with the letter.

    Difficulty is driven by how common the word must be, so the same letter can
    hold easy (everyone knows it) and hard (rare / specialist) items.
    """
    hint = {'easy': 'كلمات شائعة جداً يعرفها الجميع',
            'medium': 'كلمات معروفة لعامة الناس المثقفين',
            'hard': 'كلمات أقل شيوعاً أو متخصصة، لكنها حقيقية ومستخدمة'}[difficulty]
    prompt = (
        'أعط ' + str(n) + ' كلمة عربية مختلفة تبدأ بحرف «' + letter + '».\n'
        'مستوى الصعوبة المطلوب: ' + DIFF_AR[difficulty] + ' — ' + hint + '.\n'
        'يُمنع التكرار. الكلمة يجب أن تكون حقيقية مستخدمة في اللغة العربية '
        'ومعروفة فعلاً — ممنوع اختراع كلمات أو تحريفها.\n'
        'أعد مصفوفة JSON من الكلمات فقط: ["...","..."]'
    )
    content = nvidia_chat(prompt, temperature=0.7, timeout=120)
    out = []
    seen = set()
    for w in extract_json_array(content):
        w = str(w).strip() if not isinstance(w, dict) else str(w.get('word', '')).strip()
        if not w or has_foreign(w) or w in seen:
            continue
        if first_letter_of(w) != norm_ar(letter):
            continue
        seen.add(w)
        out.append(w)
    return out


def fetch_letters_batch(letter, n, difficulty='medium'):
    """Two-step: real words first, then one question per word.

    Asking the model to invent both the question AND an answer with a forced
    first letter makes it hallucinate words. Giving it the answer first makes
    the question-writing step reliable.
    """
    words = fetch_letter_words(letter, n + 8, difficulty)
    if not words:
        return []
    avoid = [q['question'] for q in read_all()
             if q.get('game') == 'letters' and q.get('letter') == letter]
    avoid_block = ''
    if avoid:
        avoid_block = '\n\nهذه الأسئلة موجودة بالفعل — يُمنع تكرارها:\n' + \
                      '\n'.join('- ' + t for t in avoid[:60])
    words_block = json.dumps(words, ensure_ascii=False)
    prompt = (
        'لكل كلمة من الكلمات التالية اكتب سؤالاً مسابقات تكون إجابته هي الكلمة نفسها حرفياً.\n'
        'مستوى الصعوبة المطلوب: ' + DIFF_AR[difficulty] + '.\n'
        'القواعد:\n'
        '1) الإجابة هي الكلمة المعطاة نفسها بلا تغيير.\n'
        '2) المعلومة يجب أن تكون صحيحة تماماً وموثوقة.\n'
        '3) نص السؤال لا يحتوي على الكلمة نفسها ولا يذكر الحرف المطلوب.\n'
        '4) لا تكرر السؤال بصياغة مختلفة.\n'
        '5) كل النصوص عربية فقط.\n'
        'الصيغة: [{"question":"...","answer":"...","explanation":"..."}]\n'
        'الكلمات: ' + words_block + avoid_block
    )
    content = nvidia_chat(prompt, temperature=0.6, timeout=150)
    out, seen_q = [], set()
    for it in extract_json_array(content):
        if not validate_letters_item(it, letter, difficulty):
            continue
        if norm_ar(it['question']) in seen_q:
            continue
        seen_q.add(norm_ar(it['question']))
        out.append(build_letters_item(it, letter, difficulty))
    if VERIFY:
        out = verify_items(out)
    return out


def verify_items(items):
    """Second model pass: drop factually wrong or invented items.

    The model answers with a boolean array in the SAME order as the input, so
    nothing depends on it echoing the question text back verbatim.
    """
    if not items:
        return items
    payload = [{'question': it['question'], 'answer': it['answer']} for it in items]
    prompt = (
        'أنت مدقق حقائق صارم للغة العربية. راجع أزواج السؤال/الإجابة التالية.\n'
        'اعتبر العنصر صحيحاً فقط إذا كانت الإجابة حقيقة صحيحة تماماً، وكلمة عربية '
        'حقيقية معروفة غير مختلقة، ونص السؤال سليم.\n'
        'أعد مصفوفة JSON من قيم منطقية فقط، بنفس عدد العناصر وبنفس الترتيب تماماً:\n'
        '[true, false, ...]\n'
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        content = nvidia_chat(prompt, temperature=0.2, timeout=120)
        flags = _parse_flags(content, len(items))
        if flags is None:
            print('    (verify ignored: bad flag list)')
            return items
        out = [it for it, ok in zip(items, flags) if ok]
        if len(out) < len(items):
            print('    (verify kept %d of %d)' % (len(out), len(items)))
        return out
    except Exception as e:
        print('    (verify skipped: %s)' % e)
        return items


def _parse_flags(content, n):
    """Accept [true,false], ["true","false"], [{"ok":true}] or bare tokens."""
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


# --------------------------------------------------------------------------
# round-based parallel generation
# --------------------------------------------------------------------------
def split_evenly(total, parts):
    base = max(1, total // len(parts))
    out = {p: base for p in parts}
    rem = total - base * len(parts)
    for p in parts:
        if rem <= 0:
            break
        out[p] += 1
        rem -= 1
    return out


def run_quiz(targets, workers, dry_run, batch=20, max_rounds=10):
    """targets: list of (cat_id, cat_name, difficulty, need)."""
    keys = existing_keys('quiz')
    accepted, rejected = [], 0
    remaining = {i: t[3] for i, t in enumerate(targets)}

    for rnd in range(1, max_rounds + 1):
        jobs = []
        for i, t in enumerate(targets):
            if remaining[i] > 0:
                jobs.append((i, t, min(batch, remaining[i])))
        if not jobs:
            break

        def work(j):
            i, t, n = j
            cid, cname, d, _ = t
            last = ''
            for attempt in range(3):
                try:
                    return i, fetch_quiz_batch(cid, cname, d, n)
                except Exception as e:
                    last = e
                    time.sleep(2)
            print('    ! batch failed (%s/%s): %s' % (cname, d, last))
            return i, []

        got_this_round = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(work, jobs):
                cid, cname, d, _ = targets[i]
                fresh = [it for it in items
                         if (it['game'] + '|' + norm_ar(it['question'])) not in keys]
                rejected += len(items) - len(fresh)
                for it in fresh:
                    keys.add(it['game'] + '|' + norm_ar(it['question']))
                accepted.extend(fresh)
                remaining[i] -= len(fresh)
                got_this_round += len(fresh)
        print('    round %d: +%d (total %d)' % (rnd, got_this_round, len(accepted)))

    for i, t in enumerate(targets):
        if remaining[i] > 0:
            print('    ! short: %s / %s got %d of %d'
                  % (t[1], t[2], t[3] - remaining[i], t[3]))
    return accepted, rejected


def run_letters(targets, workers, dry_run, batch=20, max_rounds=10):
    """targets: list of (letter, difficulty, need)."""
    keys = existing_keys('letters')
    accepted, rejected = [], 0
    remaining = {i: t[2] for i, t in enumerate(targets)}

    for rnd in range(1, max_rounds + 1):
        jobs = []
        for i, t in enumerate(targets):
            if remaining[i] > 0:
                jobs.append((i, t[0], t[1], min(batch, remaining[i])))
        if not jobs:
            break

        def work(j):
            i, letter, difficulty, n = j
            last = ''
            for attempt in range(3):
                try:
                    return i, fetch_letters_batch(letter, n, difficulty)
                except Exception as e:
                    last = e
                    time.sleep(2)
            print('    ! batch failed (حرف %s/%s): %s' % (letter, difficulty, last))
            return i, []

        got_this_round = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, items in ex.map(work, jobs):
                letter = targets[i][0]
                fresh = [it for it in items
                         if (it['game'] + '|' + norm_ar(it['question'])) not in keys]
                rejected += len(items) - len(fresh)
                for it in fresh:
                    keys.add(it['game'] + '|' + norm_ar(it['question']))
                accepted.extend(fresh)
                remaining[i] -= len(fresh)
                got_this_round += len(fresh)
        print('    round %d: +%d (total %d)' % (rnd, got_this_round, len(accepted)))

    for i, t in enumerate(targets):
        if remaining[i] > 0:
            print('    ! short: حرف %s/%s got %d of %d'
                  % (t[0], t[1], t[2] - remaining[i], t[2]))
    return accepted, rejected


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def report():
    cats = json.load(open(CATFILE, encoding='utf-8'))
    qs = read_all()
    quiz = [q for q in qs if q.get('game') == 'quiz']
    letters = [q for q in qs if q.get('game') == 'letters']
    print('total questions: %d (quiz %d, letters %d, million %d)'
          % (len(qs), len(quiz), len(letters),
             len([q for q in qs if q.get('game') == 'million'])))
    print('categories: %d' % len(cats))
    print()
    print('%-22s %6s %6s %6s %6s   %s' % ('category', 'total', 'easy', 'medium', 'hard', 'points/mismatch'))
    byc = {}
    for q in quiz:
        byc.setdefault(q.get('category_id'), []).append(q)
    for c in cats:
        lst = byc.get(c['id'], [])
        d = Counter(x.get('difficulty') for x in lst)
        p = Counter(x.get('points') for x in lst)
        bad = len([x for x in lst
                   if (x.get('difficulty') == 'easy' and x.get('points') != 200) or
                      (x.get('difficulty') == 'medium' and x.get('points') != 400) or
                      (x.get('difficulty') == 'hard' and x.get('points') != 600)])
        print('%-22s %6d %6d %6d %6d   %s  mismatch:%d'
              % (c['name'][:22], len(lst), d.get('easy', 0), d.get('medium', 0),
                 d.get('hard', 0), dict(p), bad))
    print()
    print('%-4s %6s' % ('letter', 'count'))
    byl = Counter(q.get('letter') for q in letters)
    for l in AR_LETTERS:
        print('%-4s %6d' % (l, byl.get(l, 0)))
    print('letters with no letter field: %d'
          % len([q for q in letters if not q.get('letter')]))
    return 0


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', choices=['quiz', 'letters'])
    ap.add_argument('--category')
    ap.add_argument('--difficulty', choices=['easy', 'medium', 'hard'])
    ap.add_argument('--all-difficulties', action='store_true')
    ap.add_argument('--all-categories', action='store_true')
    ap.add_argument('--letter')
    ap.add_argument('--all-letters', action='store_true')
    ap.add_argument('--count', type=int, default=100)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--max-rounds', type=int, default=10)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verify', action='store_true',
                    help='run a second model pass to drop factually wrong items')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()

    global VERIFY
    VERIFY = a.verify

    if a.report:
        return report()
    if not a.game:
        ap.print_help()
        return 1
    if not API_KEY:
        print('NVIDIA_API_KEY missing from .env')
        return 1
    print('model: %s   workers: %d   count/target: %d' % (MODEL, a.workers, a.count))

    if a.game == 'quiz':
        cats = json.load(open(CATFILE, encoding='utf-8'))
        if a.all_categories:
            # Don't regenerate categories that already meet the target — the
            # point is to fill the gaps, not to pile more onto the full ones.
            cur = Counter(q.get('category_id') for q in read_all()
                          if q.get('game') == 'quiz')
            full = [c['name'] for c in cats if cur.get(c['id'], 0) >= a.count]
            targets_cats = [(c['id'], c['name']) for c in cats
                            if cur.get(c['id'], 0) < a.count]
            if full:
                print('skipping %d categories already at target: %s'
                      % (len(full), ', '.join(full)))
        else:
            if not a.category:
                print('--category is required (or use --all-categories)')
                return 1
            match = [c for c in cats if c['id'] == a.category]
            if not match:
                print('unknown category: %s' % a.category)
                return 1
            targets_cats = [(match[0]['id'], match[0]['name'])]
        difficulties = (['easy', 'medium', 'hard'] if a.all_difficulties
                        else [a.difficulty or 'medium'])
        per = split_evenly(a.count, difficulties)
        print('targets: %d categories  (%s)' % (len(targets_cats), {d: per[d] for d in difficulties}))
        # Write after EVERY category: a crash or rate limit then only costs the
        # categories still to come, not the whole run.
        total_acc = 0
        for cid, cname in targets_cats:
            targets = [(cid, cname, d, per[d]) for d in difficulties]
            print('=== %s (%s) ===' % (cname, cid))
            acc, rej = run_quiz(targets, a.workers, a.dry_run, max_rounds=a.max_rounds)
            total_acc += len(acc)
            if acc and not a.dry_run:
                print('saved %d quiz questions for %s' % (append_locked(acc), cname))
            elif acc:
                print('[dry-run] would save %d quiz questions for %s' % (len(acc), cname))
        print('DONE quiz: %d accepted across %d categories' % (total_acc, len(targets_cats)))
        return 0

    # letters
    if a.all_letters:
        letters = AR_LETTERS
    else:
        if not a.letter or a.letter not in AR_LETTERS:
            print('--letter must be one of the 28 Arabic letters')
            return 1
        letters = [a.letter]
    difficulties = (['easy', 'medium', 'hard'] if a.all_difficulties
                    else [a.difficulty or 'medium'])
    per = split_evenly(a.count, difficulties)
    targets = [(l, d, per[d]) for l in letters for d in difficulties if per[d] > 0]
    acc, rej = run_letters(targets, a.workers, a.dry_run, max_rounds=a.max_rounds)
    if acc and not a.dry_run:
        print('saved %d letter questions' % append_locked(acc))
    elif acc:
        print('[dry-run] would save %d letter questions' % len(acc))
    print('DONE letters: %d accepted, %d rejected' % (len(acc), rej))
    return 0


if __name__ == '__main__':
    sys.exit(main())
