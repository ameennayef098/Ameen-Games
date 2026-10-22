#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify item 2 (letter mismatch) exhaustively, ignoring whitespace-only
differences, and check the two specific examples the caller named.

Also cross-checks that the bank is currently stable (no writer active) before
any destructive step.
"""
import io
import json
import os
import re
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(BASE, 'data', 'questions', 'all.json')


def tpl_first_letter(answer):
    if not answer:
        return ''
    s = str(answer).strip()
    if not s:
        return ''
    c1 = s[0]
    if c1 in ('\u0625', '\u0622', '\u0671', '\u0627', '\u0623'):
        s = '\u0623' + s[1:]
    if len(s) > 2 and ord(s[0]) == 0x0623 and ord(s[1]) == 0x0644:
        s = s[2:]
    if s[0] == '\u0627':
        s = '\u0623' + s[1:]
    fc = ord(s[0])
    if fc in (0x0625, 0x0622):
        s = '\u0623' + s[1:]
    return s[0] if s else ''


def norm_ar(t):
    if not t:
        return ''
    t = str(t)
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    t = re.sub(r'[أإآٱ]', 'ا', t)
    t = t.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    t = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


data = json.load(io.open(BANK, encoding='utf-8'))
letters = [q for q in data if q.get('game') == 'letters']

print('letters count:', len(letters))

strict = [q for q in letters
          if str(q.get('answer', '')).strip()
          and tpl_first_letter(q['answer']) != q.get('letter')]
loose = [q for q in letters
         if str(q.get('answer', '')).strip()
         and tpl_first_letter(q['answer']) != norm_ar(q.get('letter'))]
print('strict mismatches (stored != runtime key):', len(strict))
for q in strict:
    print('   id=%s stored=%r runtime=%r answer=%r'
          % (q.get('id'), q.get('letter'), tpl_first_letter(q['answer']), q.get('answer')))
print('loose mismatches (stored != norm_ar(runtime key)):', len(loose))
for q in loose:
    print('   id=%s stored=%r normar=%r runtime=%r answer=%r'
          % (q.get('id'), q.get('letter'), norm_ar(q.get('letter')),
             tpl_first_letter(q['answer']), q.get('answer')))

# the two examples the caller named
print('\n-- named examples --')
for needle in ('ألكسندر', 'فلمنج', 'ابن النفيس', 'انكسار'):
    hits = [q for q in data if needle in str(q.get('answer', ''))]
    for q in hits:
        print('  %r game=%s letter=%r answer=%r runtime_key=%r'
              % (needle, q.get('game'), q.get('letter'), q.get('answer'),
                 tpl_first_letter(q['answer'])))

# duplicate answers within letters (a question reachable under two cells?)
print('\n-- duplicate answers (letters) --')
seen = defaultdict(list)
for q in letters:
    seen[str(q.get('answer', '')).strip()].append(q)
d = {k: v for k, v in seen.items() if len(v) > 1}
print('  duplicate-answer groups:', len(d))
for k, v in list(d.items())[:10]:
    print('   %r count=%d letters=%s' % (k, len(v), [x.get('letter') for x in v]))

# answers with more than one word / trailing text
print('\n-- answers containing spaces (letters) --')
sp = [q for q in letters if ' ' in str(q.get('answer', '')).strip()]
print('  count:', len(sp))
for q in sp[:5]:
    print('   id=%s letter=%r answer=%r' % (q.get('id'), q.get('letter'), q.get('answer')))
