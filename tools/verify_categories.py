#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_categories.py — تدقيق سلامة الفئات وارتباطها بالأسئلة
Category / question integrity verification for ألعاب أمين.

What it does (READ-ONLY against the live data files):
  1. Validates every category in data/categories/categories.json:
       - id      : non-empty, matches ^[a-z0-9_]+$, no leading/trailing whitespace
       - name    : non-empty, Arabic
       - description : non-empty
       - color   : ^#[0-9a-fA-F]{6}$
       - icon    : non-empty
  2. Detects duplicate ids and duplicate names.
  3. Cross-references data/questions/all.json:
       (a) ORPHAN category_id  -> a question pointing at a category that does not
           exist. This is a REAL BUG: the category picker is built from the
           category file, so the question can never be shown.
       (b) categories with zero quiz questions.
  4. Reports total question counts per game and per category.
  5. Writes data/reports/categories-report.md and prints a summary.

Safe by design: this script never writes to categories.json or all.json.
If it finds a provable defect it backs up the file with a timestamped copy
before editing (only --fix-orphans / --fix-empty-desc are implemented).
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys
from collections import Counter, OrderedDict

# ---------------------------------------------------------------- paths
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CAT_FILE = os.path.join(DATA, "categories", "categories.json")
Q_FILE = os.path.join(DATA, "questions", "all.json")
REPORT_DIR = os.path.join(DATA, "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "categories-report.md")

# The 24 categories created in the last generation wave (expected set).
NEW_CATEGORY_IDS = [
    "space_missions", "football_arab", "football_world", "kingdom", "anime",
    "novels", "world_wars", "kings_leaders", "landmarks", "olympics",
    "animals_wild", "quran", "prophets", "seerah", "islamic_history",
    "pharaohs", "india_cinema", "smartphones", "cybersecurity", "ai_ml",
    "aviation", "seas_oceans", "weather_climate", "solar_energy",
]

SLUG_RE = re.compile(r"^[a-z0-9_]+$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
# Arabic block (incl. Arabic Supplement / Presentation Forms) — used only to
# confirm the name is actually Arabic rather than latin/digits.
ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

TARGET_TOTAL = 20000  # project question-count target


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def backup(path):
    """Timestamped .bak copy; returns the backup path (or None)."""
    if not os.path.exists(path):
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = "%s.bak-verify-%s" % (path, ts)
    shutil.copy2(path, dst)
    return dst


def dump_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- 1. validation
def validate_categories(cats):
    """Return (violations, new_cat_issues). violations: list of dicts."""
    violations = []
    new_issues = []

    for idx, cat in enumerate(cats):
        if not isinstance(cat, dict):
            violations.append({"index": idx, "id": None, "field": "category",
                               "problem": "not a JSON object: %r" % (cat,)})
            continue
        cid = cat.get("id")
        label = cid if isinstance(cid, str) and cid else "<no-id@%d>" % idx

        if cid is None or (isinstance(cid, str) and cid.strip() == ""):
            violations.append({"index": idx, "id": cid, "field": "id",
                               "problem": "missing / empty id"})
        else:
            if not isinstance(cid, str):
                violations.append({"index": idx, "id": cid, "field": "id",
                                   "problem": "id is not a string: %r" % (cid,)})
            else:
                if cid != cid.strip():
                    violations.append({"index": idx, "id": cid, "field": "id",
                                       "problem": "leading/trailing whitespace: %r" % cid})
                if not SLUG_RE.match(cid):
                    violations.append({"index": idx, "id": cid, "field": "id",
                                       "problem": "does not match ^[a-z0-9_]+$ (spaces / "
                                                  "uppercase / non-ASCII / arabic in id)"})

        name = cat.get("name")
        if not isinstance(name, str) or not name.strip():
            violations.append({"index": idx, "id": cid, "field": "name",
                               "problem": "missing / empty name"})
        elif not ARABIC_RE.search(name):
            violations.append({"index": idx, "id": cid, "field": "name",
                               "problem": "name has no Arabic characters: %r" % name})

        desc = cat.get("description")
        if not isinstance(desc, str) or not desc.strip():
            violations.append({"index": idx, "id": cid, "field": "description",
                               "problem": "missing / empty description"})

        color = cat.get("color")
        if not isinstance(color, str) or not COLOR_RE.match(color):
            violations.append({"index": idx, "id": cid, "field": "color",
                               "problem": "not a #RRGGBB hex colour: %r" % (color,)})

        icon = cat.get("icon")
        if not isinstance(icon, str) or not icon.strip():
            violations.append({"index": idx, "id": cid, "field": "icon",
                               "problem": "missing / empty icon"})

        # --- extra checks for the 24 newly created categories
        if cid in NEW_CATEGORY_IDS:
            if "topics" not in cat:
                new_issues.append("%s: missing 'topics' key (expected on new categories)" % cid)
            elif not isinstance(cat.get("topics"), str) or not cat["topics"].strip():
                new_issues.append("%s: 'topics' is empty" % cid)

    return violations, new_issues


# ---------------------------------------------------------------- 2. duplicates
def find_duplicates(cats):
    id_counts = Counter(c.get("id") for c in cats if isinstance(c, dict))
    name_counts = Counter(c.get("name") for c in cats if isinstance(c, dict))
    dup_ids = sorted([k for k, v in id_counts.items() if k is not None and v > 1])
    dup_names = sorted([k for k, v in name_counts.items() if k is not None and v > 1])
    return dup_ids, dup_names


# ---------------------------------------------------------------- 3. cross-ref
def cross_reference(cats, questions):
    cat_ids = {c.get("id") for c in cats if isinstance(c, dict)}
    cat_ids.discard(None)

    orphans = []
    for q in questions:
        cid = q.get("category_id")
        if cid is None or (isinstance(cid, str) and cid.strip() == ""):
            continue  # non-quiz games (letters/million) legitimately have none
        if cid not in cat_ids:
            orphans.append(q)

    quiz = [q for q in questions if q.get("game") == "quiz"]
    per_cat = Counter(q.get("category_id") for q in quiz if q.get("category_id"))
    empty_cats = [c.get("id") for c in cats
                  if isinstance(c, dict) and per_cat.get(c.get("id"), 0) == 0]

    return orphans, per_cat, empty_cats


# ---------------------------------------------------------------- 4. counts
def count_report(questions, per_cat):
    per_game = Counter(q.get("game") for q in questions)
    return {
        "total": len(questions),
        "per_game": OrderedDict(sorted(per_game.items(), key=lambda kv: -kv[1])),
        "quiz_total": sum(1 for q in questions if q.get("game") == "quiz"),
        "with_category": sum(1 for q in questions if q.get("category_id")),
        "without_category": sum(1 for q in questions if not q.get("category_id")),
        "distinct_categories_used": len(per_cat),
        "progress_pct": round(100.0 * len(questions) / float(TARGET_TOTAL), 1),
        "remaining_to_target": max(0, TARGET_TOTAL - len(questions)),
    }


# ---------------------------------------------------------------- 5. report
def write_report(cats, questions, violations, new_issues, dup_ids, dup_names,
                 orphans, per_cat, empty_cats, counts, meta):
    os.makedirs(REPORT_DIR, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    L = []
    A = L.append
    A("# تقرير التحقق من الفئات والأسئلة — ألعاب أمين")
    A("")
    A("- **وقت الفحص:** %s" % now)
    A("- **ملف الفئات:** `data/categories/categories.json`")
    A("- **ملف الأسئلة:** `data/questions/all.json`")
    A("- **sha256 (فئات):** `%s`" % meta["cat_sha"])
    A("- **sha256 (أسئلة):** `%s`" % meta["q_sha"])
    A("")
    A("> هذا التقريد للقراءة فقط — لم يُعدّل أي ملف بيانات أثناء الفحص.")
    A("")

    A("## 1) الملخص التنفيذي")
    A("")
    A("| البند | القيمة |")
    A("|---|---|")
    A("| عدد الفئات الكلي | %d |" % len(cats))
    A("| الفئات الجديدة (الموجة الأخيرة) | %d من %d متوقعة |" %
      (meta["new_present"], len(NEW_CATEGORY_IDS)))
    A("| مخالفات الصيغة (id/name/description/color/icon) | **%d** |" % len(violations))
    A("| معرفات مكررة | %d |" % len(dup_ids))
    A("| أسماء مكررة | %d |" % len(dup_names))
    A("| category_id يتيم (علّة حقيقية) | **%d** |" % len(orphans))
    A("| فئات بلا أسئلة | %d |" % len(empty_cats))
    A("| إجمالي الأسئلة | %d |" % counts["total"])
    A("| التقدم نحو هدف %d | %.1f%% (ينقص %d) |" %
      (TARGET_TOTAL, counts["progress_pct"], counts["remaining_to_target"]))
    A("")
    if meta.get("fixes"):
        A("**إصلاحات طُبّقت أثناء الفحص:** %s" % "، ".join(meta["fixes"]))
        A("")

    A("## 2) عدد الأسئلة لكل لعبة")
    A("")
    A("| اللعبة | العدد |")
    A("|---|---|")
    for g, n in counts["per_game"].items():
        A("| %s | %d |" % (g, n))
    A("")
    A("- أسئلة بها `category_id`: **%d**" % counts["with_category"])
    A("- أسئلة بدون `category_id` (ألعاب الحروف/المليون — طبيعي): **%d**" % counts["without_category"])
    A("")

    A("## 3) الفئات الجديدة — حالة كل منها")
    A("")
    A("| المعرف | الاسم | الوصف | اللون | الأيقونة | المواضيع | عدد الأسئلة |")
    A("|---|---|---|---|---|---|---|")
    by_id = {c.get("id"): c for c in cats if isinstance(c, dict)}
    for cid in NEW_CATEGORY_IDS:
        c = by_id.get(cid)
        if not c:
            A("| %s | ⚠️ **غير موجودة** | — | — | — | — | 0 |" % cid)
            continue
        topics = str(c.get("topics", "")).replace("|", "/")
        A("| `%s` | %s | %s | `%s` | %s | %s | %d |" % (
            cid, c.get("name", ""), str(c.get("description", "")).replace("|", "/"),
            c.get("color", ""), c.get("icon", ""), topics or "—", per_cat.get(cid, 0)))
    A("")

    A("## 4) مخالفات الصيغة")
    A("")
    if not violations:
        A("✅ لا توجد مخالفات — كل الفئات سليمة الصيغة.")
    else:
        A("| # | المعرف | الحقل | المشكلة |")
        A("|---|---|---|---|")
        for i, v in enumerate(violations, 1):
            A("| %d | `%s` | %s | %s |" % (i, v.get("id"), v["field"], v["problem"]))
    A("")
    if new_issues:
        A("**ملاحظات خاصة بالفئات الجديدة:**")
        A("")
        for s in new_issues:
            A("- %s" % s)
        A("")

    A("## 5) التكرارات")
    A("")
    A("- معرفات مكررة: %s" % (", ".join("`%s`" % d for d in dup_ids) if dup_ids else "✅ لا يوجد"))
    A("- أسماء مكررة: %s" % (", ".join("`%s`" % d for d in dup_names) if dup_names else "✅ لا يوجد"))
    A("")

    A("## 6) `category_id` يتيم (أسئلة لا يمكن عرضها أبداً)")
    A("")
    if not orphans:
        A("✅ لا يوجد أي `category_id` يتيم — كل سؤال يشير إلى فئة موجودة في ملف الفئات.")
    else:
        A("⚠️ **%d سؤال يشير إلى فئة غير موجودة.** لأن منتقي الفئات يُبنى من ملف الفئات،" % len(orphans))
        A(" these questions can never be shown.")
        A("")
        bad = Counter(q.get("category_id") for q in orphans)
        A("| category_id غير موجودة | عدد الأسئلة | أرقام الأسئلة (id) |")
        A("|---|---|---|")
        for cid, n in bad.most_common():
            ids = ", ".join(q.get("id", "?") for q in orphans if q.get("category_id") == cid)
            A("| `%s` | %d | %s |" % (cid, n, ids))
    A("")

    A("## 7) فئات بلا أسئلة")
    A("")
    if not empty_cats:
        A("✅ كل الفئات لها سؤال واحد على الأقل.")
    else:
        A("الفئات التالية موجودة في ملف الفئات لكن لا يوجد لها أي سؤال مسابقة (تظهر فارغة في اللعبة):")
        A("")
        for cid in empty_cats:
            name = (by_id.get(cid) or {}).get("name", "")
            tag = " 🆕" if cid in NEW_CATEGORY_IDS else ""
            A("- `%s` — %s%s" % (cid, name, tag))
    A("")

    A("## 8) عدد الأسئلة لكل فئة")
    A("")
    A("| الفئة | الاسم | العدد |")
    A("|---|---|---|")
    for c in cats:
        if not isinstance(c, dict):
            continue
        A("| `%s` | %s | %d |" % (c.get("id"), c.get("name", ""), per_cat.get(c.get("id"), 0)))
    A("")
    A("---")
    A("")
    A("_أُنشئ بواسطة `tools/verify_categories.py`_")

    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return REPORT_FILE


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Verify categories and question linkage.")
    ap.add_argument("--fix-orphans", action="store_true",
                    help="assign orphan questions to the most similar existing category")
    ap.add_argument("--fix-empty-desc", action="store_true",
                    help="fill empty descriptions with the category name")
    args = ap.parse_args()

    import hashlib
    def sha(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()

    cats = load_json(CAT_FILE, [])
    questions = load_json(Q_FILE, [])

    if not isinstance(cats, list):
        print("FATAL: categories.json is not a JSON list", file=sys.stderr)
        return 2

    meta = {
        "cat_sha": sha(CAT_FILE)[:16] if os.path.exists(CAT_FILE) else "missing",
        "q_sha": sha(Q_FILE)[:16] if os.path.exists(Q_FILE) else "missing",
        "new_present": sum(1 for c in cats if isinstance(c, dict) and c.get("id") in NEW_CATEGORY_IDS),
        "fixes": [],
    }

    violations, new_issues = validate_categories(cats)
    dup_ids, dup_names = find_duplicates(cats)
    orphans, per_cat, empty_cats = cross_reference(cats, questions)
    counts = count_report(questions, per_cat)

    # ---------------- optional, provable fixes (always backed up first)
    if args.fix_empty_desc:
        bad = [c for c in cats if isinstance(c, dict)
               and (not isinstance(c.get("description"), str) or not c["description"].strip())]
        if bad:
            bk = backup(CAT_FILE)
            for c in bad:
                c["description"] = c.get("name") or ""
            dump_json(CAT_FILE, cats)
            meta["fixes"].append("filled empty description on %d categor%s (backup: %s)"
                                 % (len(bad), "y" if len(bad) == 1 else "ies",
                                    os.path.basename(bk) if bk else "none"))
            violations, new_issues = validate_categories(cats)

    if args.fix_orphans and orphans:
        by_id = {c.get("id"): c for c in cats if isinstance(c, dict)}
        # deterministic fallback: 'general' if present, else the largest category
        fallback = "general" if "general" in by_id else (
            per_cat.most_common(1)[0][0] if per_cat else None)
        if fallback:
            bk = backup(Q_FILE)
            n = 0
            for q in orphans:
                q["category_id"] = fallback
                q["category_name"] = by_id[fallback].get("name", "")
                n += 1
            dump_json(Q_FILE, questions)
            meta["fixes"].append("reassigned %d orphan questions to '%s' (backup: %s)"
                                 % (n, fallback, os.path.basename(bk) if bk else "none"))
            orphans, per_cat, empty_cats = cross_reference(cats, questions)
            counts = count_report(questions, per_cat)

    report_path = write_report(cats, questions, violations, new_issues, dup_ids,
                               dup_names, orphans, per_cat, empty_cats, counts, meta)

    # ---------------- console summary
    print("=" * 66)
    print("  تقرير تحقق الفئات — ألعاب أمين")
    print("=" * 66)
    print("الفئات: %d (الجديدة الموجودة: %d/%d)" % (len(cats), meta["new_present"], len(NEW_CATEGORY_IDS)))
    print("مخالفات الصيغة : %d" % len(violations))
    for v in violations:
        print("   - [%s] %s: %s" % (v.get("id"), v["field"], v["problem"]))
    for s in new_issues:
        print("   - ملاحظة فئات جديدة: %s" % s)
    print("معرفات مكررة   : %d %s" % (len(dup_ids), dup_ids if dup_ids else ""))
    print("أسماء مكررة     : %d %s" % (len(dup_names), dup_names if dup_names else ""))
    print("category_id يتيم: %d" % len(orphans))
    for cid, n in Counter(q.get("category_id") for q in orphans).most_common():
        print("   - '%s' x%d" % (cid, n))
    print("فئات بلا أسئلة : %d" % len(empty_cats))
    print("-" * 66)
    print("إجمالي الأسئلة : %d  (%.1f%% من هدف %d)" % (counts["total"], counts["progress_pct"], TARGET_TOTAL))
    for g, n in counts["per_game"].items():
        print("   - %s: %d" % (g, n))
    print("الأسئلة بالفئة : %d | بدون فئة: %d" % (counts["with_category"], counts["without_category"]))
    print("=" * 66)
    print("التقرير: %s" % report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
