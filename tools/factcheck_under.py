# -*- coding: utf-8 -*-
"""Fact-check the generated «تحت المتوسط» questions with the model itself.

A riddle/letter-constrained prompt makes the model invent answers (observed:
«صوف» for a desert plant, «نحاس» for a silver-coloured metal). The prompt alone
is not enough — every generated row goes back to the model for a yes/no verdict
and the «لا» rows are dropped.
"""
import sys, os, json, time
sys.path.insert(0, r'C:\Users\Ameen Dawaghreh\Desktop\ألعاب-أمين')
import server as S

M = 'nvidia/nemotron-3.5-lightning-30b-a3b'
S._USED_MODEL['name'] = M


def verdict(items, _depth=0):
    """items: [{'question','answer'}] -> list[bool] | None (fail-open).

    Compact «س: ... / ج: ...» lines rather than a JSON dump — the JSON form made
    the model think longer and the call timed out on nearly half the chunks.
    """
    lines = '\n'.join('%d) س: %s\n   ج: %s' % (i + 1, it['question'], it['answer'])
                       for i, it in enumerate(items))
    prompt = (
        'أنت مدقق معلومات. هل الجواب المعطى هو الجواب الصحيح للسؤال؟ '
        'أعد مصفوفة قيم منطقية بنفس العدد والترتيب، بلا أي نص آخر:\n'
        '[true, false, ...]\n' + lines)
    try:
        out = S._nvidia_call(M, prompt, 280, 0.1)
        return S.parse_bool_array(out, len(items))
    except Exception as e:
        if _depth == 0:
            time.sleep(2)
            return verdict(items, 1)
        print('   verdict call failed:', str(e)[:100])
        return None


def main():
    apply = '--apply' in sys.argv
    d = S.load_json(S.Q_FILE, [])
    rows = [q for q in d if q.get('difficulty') == 'under']
    print('under rows:', len(rows))
    keep, drop = [], []
    for i in range(0, len(rows), 14):
        chunk = rows[i:i + 14]
        v = verdict([{'question': q['question'], 'answer': q['answer']} for q in chunk])
        if v is None:
            keep.extend(chunk)
            print('  chunk %d: fail-open, kept %d' % (i // 20, len(chunk)))
            continue
        for q, ok in zip(chunk, v):
            (keep if ok else drop).append(q)
        print('  chunk %d: %d/%d kept' % (i // 20, sum(v), len(v)))
    print('\nkept %d / %d   (dropped %d)' % (len(keep), len(rows), len(drop)))
    print('\n== sample of DROPPED (should be the wrong ones) ==')
    for q in drop[:14]:
        print('  -', q['question'][:62], '||', q['answer'])
    if apply and drop:
        drop_ids = {q['id'] for q in drop}
        S.save_json(S.Q_FILE, [q for q in d if q['id'] not in drop_ids])
        print('\nAPPLIED: dropped %d rows from the bank' % len(drop))


if __name__ == '__main__':
    main()
