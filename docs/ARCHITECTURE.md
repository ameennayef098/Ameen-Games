# ألعاب أمين — المعمارية

موقع ألعاب ومسابقات عربي (RTL) مبني بـ **Flask + Jinja2 + JavaScript خام**، بدون أي
إطار واجهات أمامية. كل صفحة عبارة عن قالب Jinja2 يمتد من `templates/base.html`
ويجلب أنماطاً مشتركة وملفّ سكربت واحد.

## التشغيل

```bash
python server.py          # http://localhost:5555
```

| متغير بيئة | الافتراضي | الوظيفة |
|---|---|---|
| `PORT` | `5555` | منفذ الخادم |
| `AMEEN_DEBUG` | `0` | `1` لتفعيل وضع debug في Flask |
| `NVIDIA_API_KEY` | — | من `.env`، لازم لتوليد المحتوى |
| `ADMIN_PASSWORD` | — | كلمة مرور لوحة الإدارة نصًا صريحًا (أولوية أعلى) |
| `ADMIN_PASSWORD_HASH` | — | SHA-256 لكلمة المرور (64 حرفًا)؛ قيمة غير صالحة تُتجاهَل |
| `AMEEN_API_SLOTS` | `6` | حد التزامن الأقصى لطلبات الـ API |

الخادم يستمع على `0.0.0.0` فيصبح متاحاً على شبكة الواي فاي أيضاً (مفيد للعرض على
شاشة أو جهاز آخر).

## بنية الملفات

```
ألعاب-أمين/
├── server.py              التطبيق كله: المسارات + واجهات API + التوليد
├── qimport.py            محلل دفعات الأسئلة اليدوي (مستقل عن Flask)
├── templates/             قوالب Jinja2
│   ├── base.html          الهيكل المشترك (navbar, footer, mobile menu)
│   ├── index.html         الرئيسية (hero + بطاقات الألعاب)
│   ├── games.html         فهرس الألعاب
│   ├── about.html         عن الموقع
│   ├── how_to_play.html   طريقة اللعب
│   ├── library.html       قالب قديم — المسار /library يعيد التوجيه إلى /admin
│   ├── admin.html         لوحة الإدارة (96KB — إدارة الأسئلة واللاعبين والمحتوى)
│   └── game_*.html        صفحة لكل لعبة (letters, quiz, auction, million, ...)
├── static/
│   ├── css/style.css      نظام التصميم الكامل (tokens + مكوّنات)
│   └── js/main.js         أدوات مشتركة: toast, modal, timer, SoundManager, normalizeArabic
├── data/
│   ├── questions/all.json     بنك الأسئلة (مصدر الحقيقة الوحيد)
│   ├── categories/categories.json
│   ├── content/*.json         محتوى الألعاب الإضافية (codenames, spy, ...)
│   ├── players/players.json   بيانات لاعبي المزاد
│   ├── uploads/               صور مرفوعة
│   ├── settings.json          إعدادات الموقع
│   ├── waves/*.json           خطط التوليد + ملفات التقدّم
│   └── .sema/nvidia.lock      عدّاد التزامن المشترك بين العمليات
└── tools/                 أدوات التوليد والفحص (انظر CONTENT-PIPELINE.md)
```

## مجموعات المسارات

| المجموعة | المسارات |
|---|---|
| الصفحات | `/`, `/games`, `/library` (→ `/admin`), `/how-to-play`, `/offline`, `/about`, `/admin`, `/game/<game>` |
| الأسئلة | `/api/questions` (GET/POST), `/api/questions/<id>` (GET/PUT/DELETE), `/archive`, `/duplicate`, `/export`, `/import`, `/duplicates`, `/bulk-delete`, `/bulk-status` |
| الفئات | `/api/categories` (GET/POST), `/api/categories/<id>` (PUT/DELETE), `/image` |
| اللاعبون | `/api/players` + `/meta` + `/export` + `/import` |
| المحتوى | `/api/content/games`, `/api/content/<game>` (GET/POST/PUT/DELETE), `/status`, `/bulk-status`, `/purge-bad`, `/export`, `/import` |
| الذكاء الاصطناعي | `/api/ai/models`, `/api/ai/test`, `/api/ai/progress`, `/api/ai/generate`, `/api/ai/match`, `/api/ai/evaluate-debate`, `/api/ai/check-answer` |
| الإدارة | `/api/admin/login`, `/api/admin/check`, `/api/settings` |
| استيراد الدفعات | `/api/import/games`, `/api/import/parse`, `/api/import/check`, `/api/import/summary`, `/api/import/save`, `/api/import/history`, `/api/import/draft`, `/api/import/template`, `/api/import/export` — انظر `docs/IMPORT.md` |

## بوابة الإدارة

أي **كتابة** على مسارات المحتوى تتطلب رمز جلسة:

```python
GUARDED_PREFIXES = ('/api/questions', '/api/categories', '/api/players',
                    '/api/import', '/api/pending', '/api/settings',
                    '/api/ai/generate')

@app.before_request
def guard_admin_writes():
    if request.method in ('GET','HEAD','OPTIONS'): return None
    if request.path == '/api/admin/login': return None
    if request.path.startswith(GUARDED_PREFIXES) and not is_admin(request):
        return jsonify({'error': '...'}), 401
    return None
```

- كلمة المرور تُشفَّر بـ **SHA-256** وتُخزَّن كمصفرة في `.env` — النص الصريح غير موجود في المستودع.
- عند تسجيل الدخول يُنشأ `uuid` ويُضاف إلى مجموعة في الذاكرة (`ADMIN_TOKENS`).
- كل التعديلات تمر عبر دالة `is_admin(request)` (رأس الرمز).

**القراءات عامّة عمداً**: اللاعبون يحتاجون قراءة الأسئلة فقط، والحكم بالذكاء الاصطناعي جزء من اللعب.
لا تُقيَّد إلا كتابات المحتوى.

## مخطّط سؤال

مفتاح التكرار هو `game + '|' + norm_ar(question)` — نفس النص مسموح في لعبتين مختلفتين.

حقول `game: 'quiz'`:
```
id, game, category_id, category_name, question, answer, explanation,
difficulty ('easy'|'medium'|'hard'), points (200|400|600),
status ('approved'|'pending_review'|'archived'), source ('manual'|'ai'),
created_at, updated_at, image, hint, alternatives
```

حقول `game: 'letters'`:
```
id, game, letter, question, answer, explanation,
difficulty, status, source, created_at, updated_at, image, hint, alternatives
```

حقول `game: 'million'`:
```
id, game, question, options[], answer, explanation,
difficulty, points, status, source, created_at, updated_at, image, hint, alternatives
```

## الفئات

```json
{ "id": "sports", "name": "كرة القدم والرياضة",
  "description": "...", "color": "#10b981", "icon": "⚽", "topics": "محاور توليد اختيارية" }
```

`topics` اختياري؛  presenceه يجعل محاور التوليد قابلة للقراءة والتعديل من البيانات بدل أن
تكون مخفيّة في الكود (`tools/bulk_gen.py :: cat_topics`).

## ملاحظات تشغيلية

- **تخزين القوالب مؤقتاً:** Flask يخزّن قوالب Jinja2 في الذاكرة — بعد تعديل أي `templates/*.html`
  يجب إعادة تشغيل الخادم. ملفات CSS/JS الثابتة تظهر فوراً.
- **التخزين المؤقّت لواجهة الأسئلة:** `per_page` الافتراضي 50 بسقف 5000. الألعاب تطلب
  `per_page=5000` لأن الترقيم الافتراضي يجوّع اللعبة (يجلب أسئلة 5 حروف من 28).
- **نسخة Python:** `pip` قد يشير لمفسّر مختلف عن `python` — استخدم `python -m pip`.
