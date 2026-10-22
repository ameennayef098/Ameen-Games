#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT the question bank against the defects suspected by the caller.

Read-only with respect to data/questions/all.json: it prints a report and, only
when asked, writes a proposed-fix copy to data/reports/ (never to the bank).

Mirrors byte-for-byte the two normalisations the game actually uses:
  * templates/game_letters.html :: firstLetterOf()   -> RUNTIME GROUPING key
  * server.py                   :: first_letter_of() -> VALIDATION check
"""
import io
import json
import os
import re
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(BASE, 'data', 'questions', 'all.json')
REPORTS = os.path.join(BASE, 'data', 'reports')

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


def srv_first_letter(answer):
    """Exact port of server.py first_letter_of()."""
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


def foreign_runs(text):
    t = str(text or '')
    out = [m.group(0) for m in FOREIGN_CHARS.finditer(t)]
    for tok in re.findall(r'[A-Za-z]+', t):
        if tok.upper() not in ALLOWED_LATIN:
            out.append(tok)
    return out


def main():
    data = json.load(io.open(BANK, encoding='utf-8'))
    letters = [q for q in data if q.get('game') == 'letters']
    quiz = [q for q in data if q.get('game') == 'quiz']
    out = {}
    lines = []

    def p(s=''):
        lines.append(s)

    # 1. bare alef
    bare = [q for q in letters
            if str(q.get('answer', '')).strip()
            and str(q.get('answer', '')).strip()[0] == '\u0627']
    # prove grouping unchanged: answer with ا swapped to أ must yield same key
    grouping_proof = all(
        tpl_first_letter(q['answer']) == tpl_first_letter(
            '\u0623' + str(q['answer']).strip()[1:])
        for q in bare)
    p('[1] BARE ALEF answers (letters): %d' % len(bare))
    p('    runtime grouping provably unchanged by normalising to أ: %s' % grouping_proof)
    p('    distinct stored `letter` values among them: %s'
      % dict(Counter(q.get('letter') for q in bare)))
    for q in bare[:3]:
        p('      id=%s answer=%r letter=%r' % (q.get('id'), q.get('answer'), q.get('letter')))
    out['bare_alef'] = len(bare)

    # 2. letter mismatch
    mism = []
    for q in letters:
        ans = str(q.get('answer', '')).strip()
        if not ans:
            continue
        g = tpl_first_letter(ans)
        if g != q.get('letter'):
            mism.append((q, q.get('letter'), g))
    srv_mism = [q for q in letters
                if str(q.get('answer', '')).strip()
                and srv_first_letter(q['answer']) != norm_ar(q.get('letter'))]
    p('')
    p('[2] LETTER MISMATCH (stored != runtime grouping key): %d' % len(mism))
    for q, stored, g in mism:
        p('    id=%s stored=%r runtime=%r answer=%r' % (q.get('id'), stored, g, q.get('answer')))
    p('    server.py first_letter_of() vs norm_ar(letter) mismatches: %d' % len(srv_mism))
    out['letter_mismatch'] = len(mism)
    out['letter_mismatch_items'] = [
        {'id': q.get('id'), 'stored': s, 'runtime': g, 'answer': q.get('answer')}
        for q, s, g in mism]

    # 3. orphan letters
    orphan = [q for q in letters if q.get('letter') not in LETTERS_25]
    p('')
    p('[3] ORPHAN LETTERS (letter not in the 25 board cells): %d' % len(orphan))
    p('    %s' % dict(Counter(q.get('letter') for q in orphan)))
    p('    every orphan answer genuinely starts with its stored letter: %s'
      % all(tpl_first_letter(q['answer']) == q.get('letter') for q in orphan))
    for q in orphan[:8]:
        p('      id=%s letter=%r answer=%r' % (q.get('id'), q.get('letter'), q.get('answer')))
    out['orphans'] = len(orphan)
    out['orphan_hist'] = dict(Counter(q.get('letter') for q in orphan))

    # 4. duplicates (per game, and specifically quiz)
    def qkey(q):
        return str(q.get('game', '')) + '|' + norm_ar(q.get('question', ''))

    seen = defaultdict(list)
    for q in data:
        seen[qkey(q)].append(q)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    dup_quiz = {k: v for k, v in dups.items() if k.startswith('quiz|')}
    p('')
    p('[4] DUPLICATE questions (same game + normalised text): all-games=%d quiz-only=%d'
      % (len(dups), len(dup_quiz)))
    for k, v in list(dups.items())[:10]:
        p('    key=%r count=%d ids=%s' % (k, len(v), [x.get('id') for x in v]))
    # also a looser raw-text check
    raw = defaultdict(list)
    for q in quiz:
        raw[str(q.get('question', '')).strip()].append(q)
    rawdups = {k: v for k, v in raw.items() if len(v) > 1}
    p('    raw-exact-text duplicate quiz groups: %d' % len(rawdups))
    for k, v in list(rawdups.items())[:5]:
        p('      count=%d ids=%s text=%r' % (len(v), [x.get('id') for x in v], k))
    out['duplicates_all'] = len(dups)
    out['duplicates_quiz'] = len(dup_quiz)
    out['duplicates_raw_quiz'] = len(rawdups)

    # 5. points / difficulty
    want = {'easy': 200, 'medium': 400, 'hard': 600}
    bad = [q for q in quiz if want.get(q.get('difficulty')) != q.get('points')]
    p('')
    p('[5] POINTS/DIFFICULTY mismatches for quiz: %d' % len(bad))
    p('    quiz difficulty histogram: %s' % dict(Counter(q.get('difficulty') for q in quiz)))
    out['points_bad'] = len(bad)

    # 6. foreign script leaks
    hits = []
    for q in data:
        for field in ('question', 'answer'):
            runs = foreign_runs(q.get(field, ''))
            if runs:
                hits.append((q, field, runs))
    p('')
    p('[6] FOREIGN SCRIPT / non-allowlisted Latin leaks: %d fields' % len(hits))
    for q, field, runs in hits[:10]:
        p('    id=%s game=%s field=%s runs=%s' % (q.get('id'), q.get('game'), field, runs))
    out['foreign_hits'] = len(hits)

    p('')
    p('BANK total: %d  letters=%d quiz=%d million=%d'
      % (len(data), len(letters), len(quiz), len([q for q in data if q.get('game') == 'million'])))

    text = '\n'.join(lines)
    print(text)

    rp = os.path.join(REPORTS, 'bank_audit_report.md')
    with io.open(rp, 'w', encoding='utf-8') as f:
        f.write('# Question-bank audit\n\n```\n' + text + '\n```\n')
    print('\n[report written] %s' % rp)
    return out


if __name__ == '__main__':
    main()
