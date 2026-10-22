#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT of data/questions/all.json (read-only).

Mirrors, byte for byte, the two normalisations the game actually uses:
  * templates/game_letters.html :: firstLetterOf()  -> the RUNTIME GROUPING key
       (this is what decides which board cell a letters question lands in)
  * server.py                   :: first_letter_of() -> the VALIDATION check
       (norm_ar(q['letter']) == first_letter_of(answer))

Read-only by design: the background wave job is appending to all.json, so this
script never writes to it. All reports go to stdout / data/reports/.
"""
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(BASE, 'data', 'questions', 'all.json')

# ---------------------------------------------------------------- mirrors ----
# templates/game_letters.html LETTERS_25 (the 25 playable board cells)
LETTERS_25 = ['أ', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ر', 'ز',
              'س', 'ش', 'ص', 'ط', 'ع', 'غ', 'ف', 'ق', 'ك',
              'ل', 'م', 'ن', 'ه', 'و', 'ي']


def tpl_first_letter(answer):
    """Exact port of templates/game_letters.html firstLetterOf()."""
    if not answer:
        return ''
    s = str(answer).strip()
    if not s:
        return ''
    # normalize ALL alif variants to أ (U+0623)
    c1 = s[0]
    if c1 in ('\u0625', '\u0622', '\u0671', '\u0627', '\u0623'):
        s = '\u0623' + s[1:]
    # remove definite article ال
    if len(s) > 2 and ord(s[0]) == 0x0623 and ord(s[1]) == 0x0644:
        s = s[2:]
    # safety checks
    if s[0] == '\u0627':
        s = '\u0623' + s[1:]
    fc = ord(s[0])
    if fc in (0x0625, 0x0622):
        s = '\u0623' + s[1:]
    return s[0] if s else ''


# --- server.py norm_ar ---
def norm_ar(t):
    if not t:
        return ''
    t = str(t)
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    t = re.sub(r'[أإآٱ]', 'ا', t)
    t = t.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    t = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def srv_first_letter(answer):
    """Exact port of server.py first_letter_of()."""
    a = norm_ar(answer)
    if not a:
        return ''
    if a[0] in ('إ', 'آ', 'ٱ'):      # note: dead code, norm_ar already did this
        a = 'أ' + a[1:]
    if a[0] == 'ه':
        a = 'هـ' + a[1:]
    if a.startswith('ال') and len(a) > 2:
        a = a[2:]
    return a[:1] if a else ''


# --- server.py foreign-script detector ---
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


def has_foreign(text):
    t = str(text or '')
    if FOREIGN_CHARS.search(t):
        return True
    for tok in re.findall(r'[A-Za-z]+', t):
        if tok.upper() not in ALLOWED_LATIN:
            return True
    return False


def foreign_runs(text):
    """Return the actual non-Arabic-script runs found, for reporting."""
    t = str(text or '')
    out = []
    for m in FOREIGN_CHARS.finditer(t):
        out.append(m.group(0))
    for tok in re.findall(r'[A-Za-z]+', t):
        if tok.upper() not in ALLOWED_LATIN:
            out.append(tok)
    return out


def q_key(q):
    return str(q.get('game', '')) + '|' + norm_ar(q.get('question', ''))


# ------------------------------------------------------------------ audit ----
def main():
    data = json.load(io.open(BANK, encoding='utf-8'))
    n = len(data)
    by_game = Counter(q.get('game') for q in data)
    print('BANK: %s' % BANK)
    print('TOTAL QUESTIONS: %d' % n)
    print('BY GAME: %s' % dict(by_game))
    print('=' * 72)

    letters = [q for q in data if q.get('game') == 'letters']
    quiz = [q for q in data if q.get('game') == 'quiz']

    # ---- 1. bare alef -----------------------------------------------------
    bare = []
    for q in letters:
        a = str(q.get('answer', '')).strip()
        if a and a[0] == '\u0627':          # ا  (U+0627), not أ (U+0623)
            bare.append(q)
    print('\n[1] BARE ALEF answers (letters): %d' % len(bare))
    print('    -> runtime grouping is UNAFFECTED: tpl_first_letter() maps '
          '\\u0627 -> \\u0623 before the board lookup.')
    for q in bare[:3]:
        print('       e.g. %r letter=%s' % (q.get('answer'), q.get('letter')))

    # ---- 2. letter mismatch ----------------------------------------------
    mism = []
    for q in letters:
        ans = str(q.get('answer', '')).strip()
        if not ans:
            continue
        g = tpl_first_letter(ans)            # runtime grouping key
        stored = q.get('letter')
        if g != stored:
            mism.append((q, stored, g))
    print('\n[2] LETTER MISMATCH (stored != runtime grouping key): %d' % len(mism))
    for q, stored, g in mism:
        print('    id=%s  stored=%r  runtime=%r  answer=%r'
              % (q.get('id'), stored, g, q.get('answer')))

    # cross-check with the server-side validator, to show whether the two agree
    srv_mism = [q for q in letters
                if str(q.get('answer', '')).strip()
                and srv_first_letter(q['answer']) != norm_ar(q.get('letter'))]
    print('    (server.py first_letter_of() vs norm_ar(letter) mismatches: %d)'
          % len(srv_mism))
    for q in srv_mism[:5]:
        print('       id=%s stored=%r srv=%r answer=%r'
              % (q.get('id'), q.get('letter'),
                 srv_first_letter(q['answer']), q.get('answer')))

    # ---- 3. orphan letters ------------------------------------------------
    orphan = [q for q in letters if q.get('letter') not in LETTERS_25]
    print('\n[3] ORPHAN LETTERS (letter not in the 25 board cells): %d'
          % len(orphan))
    print('    %s' % dict(Counter(q.get('letter') for q in orphan)))
    for q in orphan[:5]:
        print('       id=%s letter=%r answer=%r'
              % (q.get('id'), q.get('letter'), q.get('answer')))
    # sanity: every orphan's answer genuinely starts with that letter
    genuinely = [q for q in orphan
                 if q.get('letter') in (tpl_first_letter(q.get('answer', ''))
                                        and [q.get('letter')] or [])]
    print('    -> grouping key of each orphan equals its stored letter: '
          '%s' % all(tpl_first_letter(q.get('answer', '')) == q.get('letter')
                     for q in orphan))

    # ---- 4. duplicates ----------------------------------------------------
    seen = defaultdict(list)
    for q in quiz:
        seen[q_key(q)].append(q)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    print('\n[4] DUPLICATE quiz questions (same game + normalised text): %d'
          % len(dups))
    for k, v in dups.items():
        print('    key=%r  count=%d' % (k, len(v)))
        for q in v:
            print('       id=%s pts=%s diff=%s cat=%s'
                  % (q.get('id'), q.get('points'), q.get('difficulty'),
                     q.get('category_name')))
        print('       text=%r' % v[0].get('question'))

    # ---- 5. points / difficulty ------------------------------------------
    want = {'easy': 200, 'medium': 400, 'hard': 600}
    bad = [(q, want.get(q.get('difficulty')), q.get('points'))
           for q in quiz if want.get(q.get('difficulty')) != q.get('points')]
    print('\n[5] POINTS/DIFFICULTY mismatches for quiz: %d' % len(bad))
    for q, w, got in bad[:10]:
        print('    id=%s diff=%s expected=%s got=%s'
              % (q.get('id'), q.get('difficulty'), w, got))
    print('    quiz difficulty histogram: %s'
          % dict(Counter(q.get('difficulty') for q in quiz)))

    # ---- 6. foreign script leaks ----------------------------------------
    print('\n[6] FOREIGN SCRIPT / non-allowlisted Latin leaks:')
    hits = []
    for q in data:
        for field in ('question', 'answer'):
            runs = foreign_runs(q.get(field, ''))
            if runs:
                hits.append((q, field, runs))
    print('    total fields with leaks: %d' % len(hits))
    per_game = Counter(q.get('game') for q, _, _ in hits)
    print('    by game: %s' % dict(per_game))
    for q, field, runs in hits[:15]:
        print('    id=%s game=%s field=%s runs=%s'
              % (q.get('id'), q.get('game'), field, runs))
        print('       %s=%r' % (field, q.get(field)))

    # ---- summary of the 25 playable cells --------------------------------
    print('\n' + '=' * 72)
    print('SUMMARY')
    print('  total questions .......... %d' % n)
    print('  bare-alef answers ........ %d' % len(bare))
    print('  letter mismatches ........ %d' % len(mism))
    print('  orphan letters ........... %d  (%s)'
          % (len(orphan), dict(Counter(q.get('letter') for q in orphan))))
    print('  duplicate quiz groups .... %d' % len(dups))
    print('  points/difficulty bad .... %d' % len(bad))
    print('  foreign-script fields .... %d' % len(hits))


if __name__ == '__main__':
    main()
