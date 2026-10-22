#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate من سيربح المليون questions (4 options, one correct).

Million questions differ from quiz questions: each one carries FOUR options and
the correct answer must be one of them, so the prompt and the validator both
work on the option set.

Reuses tools/bulk_gen.py for the NVIDIA call, JSON extraction, validation and
the locked append to data/questions/all.json.

Usage
-----
    python tools/gen_million.py --count 15
    python tools/gen_million.py --count 15 --difficulty easy
    python/tools/gen_million.py --count 15 --dry-run
"""
import argparse
import importlib.util
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location(
    'bulk_gen', os.path.join(BASE, 'tools', 'bulk_gen.py'))
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)

POINTS = {'easy': 200, 'medium': 400, 'hard': 600}


def million_prompt(difficulty, n, avoid_lines):
    avoid = ''
    if avoid_lines:
        avoid = '\n\nهذه الأسئلة موجودة بالفعل — يُمنع تكرارها أو إعادة صياغتها:\n' + \
                '\n'.join('- ' + t for t in avoid_lines[:200])
    return (
        'أنت معدّ أسئلة للعبة «من سيربح المليون».\n'
        'المطلوب: ' + str(n) + ' سؤالاً بمستوى صعوبة ' + bg.DIFF_AR[difficulty] + '.\n\n'
        'كل سؤال يتكون من:\n'
        '1) نص السؤال.\n'
        '2) أربعة خيارات مختلفة عن بعضها تماماً.\n'
        '3) الإجابة الصحيحة — يجب أن تكون أحد الخيارات الأربعة حرفياً.\n'
        '4) شرح قصير يوضح لماذا الإجابة صحيحة.\n\n'
        'القواعد الصارمة:\n'
        '1) الخيارات الأربعة كلها قريبة من بعضها في الطول ومن نفس نوع المعلومة '
        '(مثلاً كلها عواصم، أو كلها حيوانات) — لا تجعل الإجابة الواضحة مختلفة '
        'تماماً عن الباقي.\n'
        '2) كل النصوص عربية فقط. يُسمح بالرموز العلمية مثل Fe و Au والاختصارات '
        'التقنية مثل HTTP.\n'
        '3) نص السؤال لا يحتوي على الإجابة ولا على أي خيار.\n'
        '4) لا تكرر أي سؤال ولا قريباً من معنى موجود.\n'
        '5) مستوى الصعوبة ' + bg.DIFF_AR[difficulty] + ': ' + bg.DIFF_HINT[difficulty] + '.\n'
        '6) المعلومة يجب أن تكون صحيحة وموثوقة تماماً. لا تخمّن.\n'
        '7) نوّع الموضوعات: تاريخ، جغرافيا، علوم، رياضة، فنون، تقنية، معلومات عامة.\n'
        '\nالصيغة:\n'
        '[{"question":"...","options":["...","...","...","..."],'
        '"answer":"...","explanation":"..."}]\n'
        'أعد مصفوفة JSON فقط بلا أي نص إضافي.' + avoid
    )


def validate_million_item(it):
    if not isinstance(it, dict):
        return False
    q = str(it.get('question', '')).strip()
    opts = it.get('options') or []
    a = str(it.get('answer', '')).strip()
    if not q or not a or not isinstance(opts, list) or len(opts) != 4:
        return False
    opts = [str(o).strip() for o in opts]
    if len(set(opts)) != 4:                 # four DISTINCT options
        return False
    if any(not o for o in opts):
        return False
    if a not in opts:                       # the answer must be an option
        return False
    if bg.has_foreign(q) or bg.has_foreign(' '.join(opts) + ' ' + a):
        return False
    if len(a) > 40:
        return False
    if a in q:
        return False
    return True


def build_item(it, difficulty):
    return {
        'id': bg.uuid.uuid4().hex[:8] if hasattr(bg, 'uuid') else None,
        'game': 'million',
        'question': str(it['question']).strip(),
        'options': [str(o).strip() for o in it['options']],
        'answer': str(it['answer']).strip(),
        'explanation': str(it.get('explanation', '')).strip(),
        'difficulty': difficulty,
        'points': POINTS[difficulty],
        'status': 'approved',
        'source': 'ai',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'alternatives': [],
        'hint': '',
        'image': '',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=15)
    ap.add_argument('--difficulty', choices=['easy', 'medium', 'hard'],
                    default='easy')
    ap.add_argument('--all-difficulties', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--max-rounds', type=int, default=8)
    a = ap.parse_args()

    import uuid
    bg.uuid = uuid
    if not bg.API_KEY:
        print('NVIDIA_API_KEY missing from .env')
        return 1

    diffs = ['easy', 'medium', 'hard'] if a.all_difficulties else [a.difficulty]
    # Split the requested count across the chosen difficulties, largest share
    # to easy (the million ladder starts easy).
    per = {}
    rem = a.count
    weights = [0.5, 0.3, 0.2][:len(diffs)]
    for i, d in enumerate(diffs):
        if i == len(diffs) - 1:
            per[d] = rem
        else:
            take = max(1, int(round(a.count * weights[i])))
            take = min(take, rem - (len(diffs) - i - 1))
            per[d] = max(0, take)
            rem -= per[d]
    print('model: %s   (entitlement fallback list: %s)'
          % (bg.MODEL, bg.FALLBACK_MODELS))
    print('targets: %s' % {d: per[d] for d in diffs if per[d] > 0})
    if a.dry_run:
        print('DRY RUN — nothing will be written')

    accepted = []
    short = []
    saved_total = 0
    for difficulty in diffs:
        need = per[difficulty]
        if need <= 0:
            continue
        got = 0
        for rnd in range(1, a.max_rounds + 1):
            if need <= 0:
                break
            existing = bg.read_all()
            avoid = [q['question'] for q in existing if q.get('game') == 'million']
            # Keys are rebuilt from the file, so a question accepted in an
            # earlier round must be written immediately or the next round will
            # generate it again (observed: the same "مخترع المصباح" twice).
            keys = bg.existing_keys('million')
            # Ask for a SMALL batch. Requesting 20+ items makes the model
            # degenerate into a single topic (28 capitals in a row); 5-6 items
            # per call keeps the subjects varied. More rounds cost less than a
            # rejected wall.
            n = min(6, need + 2)
            try:
                content = bg.nvidia_chat(
                    million_prompt(difficulty, n, avoid), temperature=0.9)
            except Exception as e:
                print('    ! generation failed: %s' % e)
                break
            try:
                items = bg.extract_json_array(content)
            except Exception as e:
                print('    ! unparsable reply: %s' % e)
                items = []
            fresh = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                if not validate_million_item(it):
                    continue
                key = 'million|' + bg.norm_ar(it['question'])
                if key in keys:
                    continue
                keys.add(key)
                fresh.append(build_item(it, difficulty))
            accepted.extend(fresh)
            got += len(fresh)
            need -= len(fresh)
            # Write after every round so later rounds cannot re-emit these.
            if fresh and not a.dry_run:
                saved_total += bg.append_locked(fresh)
            print('    %s round %d: +%d (need %d more)'
                  % (bg.DIFF_AR[difficulty], rnd, len(fresh), max(0, need)))
            if not fresh:
                break
        if need > 0:
            short.append((difficulty, per[difficulty] - need, per[difficulty]))

    print('accepted: %d (saved this run: %d)' % (len(accepted), saved_total))
    for d, got, want in short:
        print('   ! short: %s got %d of %d' % (bg.DIFF_AR[d], got, want))
    return 0


if __name__ == '__main__':
    sys.exit(main())
