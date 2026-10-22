# Question-bank audit

```
[1] BARE ALEF answers (letters): 325
    runtime grouping provably unchanged by normalising to أ: True
    distinct stored `letter` values among them: {'أ': 22, 'ف': 15, 'ب': 23, 'ت': 13, 'ث': 8, 'ج': 17, 'ح': 12, 'خ': 8, 'د': 11, 'ذ': 7, 'م': 16, 'ر': 12, 'ز': 12, 'س': 13, 'ش': 9, 'ص': 10, 'ض': 9, 'ط': 9, 'ظ': 9, 'ع': 7, 'غ': 8, 'ق': 9, 'ك': 14, 'ل': 8, 'ن': 16, 'ه': 12, 'و': 6, 'ي': 10}
      id=49bb55ff answer='الألف' letter='أ'
      id=2d967c4a answer='الفاتحة' letter='ف'
      id=bd060fb8 answer='الفهد' letter='ف'

[2] LETTER MISMATCH (stored != runtime grouping key): 0
    server.py first_letter_of() vs norm_ar(letter) mismatches: 0

[3] ORPHAN LETTERS (letter not in the 25 board cells): 27
    {'ذ': 8, 'ض': 9, 'ظ': 10}
    every orphan answer genuinely starts with its stored letter: True
      id=0a45828a letter='ذ' answer='الذهب'
      id=1b07d0b0 letter='ذ' answer='الذئب'
      id=f2877ddb letter='ذ' answer='الذرة'
      id=fc7273ec letter='ذ' answer='الذاكرة'
      id=c992353d letter='ذ' answer='الذيل'
      id=d4921e8b letter='ذ' answer='الذبابة'
      id=c8dc272a letter='ذ' answer='الذكاء'
      id=4665ad9d letter='ذ' answer='ذو القرنين'

[4] DUPLICATE questions (same game + normalised text): all-games=0 quiz-only=0
    raw-exact-text duplicate quiz groups: 0

[5] POINTS/DIFFICULTY mismatches for quiz: 0
    quiz difficulty histogram: {'easy': 1683, 'medium': 1577, 'hard': 1550}

[6] FOREIGN SCRIPT / non-allowlisted Latin leaks: 0 fields

BANK total: 5986  letters=1044 quiz=4810 million=132
```
