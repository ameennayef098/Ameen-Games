#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature: turn retention in س.ج (game_quiz.html).

Rule the host asked for:
  * a team that does not answer keeps its turn
  * the question moves to the OTHER team as a steal attempt
  * if the other team answers it takes the points AND keeps the turn
  * if the other team also does not answer, the question is closed and the
    team that was offered it keeps the turn

Implemented as a single "turn retention" mechanic: `QS.keepTurn` is set by the
correct-answer branch, and the alternation at the end of markAnswer() only runs
when nobody earned the right to hold the turn.
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'templates', 'game_quiz.html')

s = io.open(P, encoding='utf-8').read()
orig = s
log = []


def sub(old, new, label):
    global s
    if old not in s:
        print('MISS: %s' % label)
        return False
    if s.count(old) != 1:
        print('AMBIGUOUS (%d): %s' % (s.count(old), label))
        return False
    s = s.replace(old, new)
    log.append(label)
    return True


# ---------------------------------------------------------------- 1. setup UI
sub(
    '''        <div class="form-group"><label><input type="checkbox" id="allowSteal" checked> السماح بالسرقة</label></div>''',
    '''        <div class="form-group"><label><input type="checkbox" id="allowSteal" checked> السماح بالسرقة</label></div>
        <div class="form-group"><label><input type="checkbox" id="allowNoAnswer" checked> «لم يجب» ينقل السؤال ولا يضيع الدور</label></div>''',
    'setup checkbox')

# ---------------------------------------------------------------- 2. state
sub(
    '''        turn: 1, s1: 0, s2: 0, used: {}, boards: {}, stats: {},
        correct: 0, wrong: 0, skipped: 0, over: false, stealPending: false
    };''',
    '''        turn: 1, s1: 0, s2: 0, used: {}, boards: {}, stats: {},
        correct: 0, wrong: 0, skipped: 0, noAnswer: 0, over: false, stealPending: false
    };
    // الفريق الذي أجاب إجابة صحيحة يحتفظ بدوره ولا ينتقل إليه تلقائياً
    QS.keepTurn = false;
    QS.allowNoAnswer = document.getElementById('allowNoAnswer').checked;''',
    'state keepTurn')

# ---------------------------------------------------------------- 3. modal buttons
sub(
    '''            <div style="display:flex;gap:.8rem;justify-content:center;">
                <button class="btn btn-success" onclick="markAnswer(true)">✅ صحيحة</button>
                <button class="btn btn-danger" onclick="markAnswer(false)">❌ خاطئة</button>
            </div>''',
    '''            <div style="display:flex;gap:.8rem;justify-content:center;flex-wrap:wrap;">
                <button class="btn btn-success" onclick="markAnswer(true)">✅ صحيحة</button>
                <button class="btn btn-danger" onclick="markAnswer(false)">❌ خاطئة</button>
                <button class="btn btn-secondary" id="noAnswerBtn" onclick="markNoAnswer()">🤐 لم يجب</button>
            </div>''',
    'noAnswer button')

# ---------------------------------------------------------------- 4. the mechanic
sub(
    '''    if (isCorrect) {
        QS.used[key] = true;
        if (QS.turn === 1) QS.s1 += pts; else QS.s2 += pts;
        QS.correct++;
        bumpStat(cid, 'correct', pts);
        SoundManager.play('correct');
        QS.stealPending = false;
    } else {''',
    '''    if (isCorrect) {
        QS.used[key] = true;
        if (QS.turn === 1) QS.s1 += pts; else QS.s2 += pts;
        QS.correct++;
        bumpStat(cid, 'correct', pts);
        SoundManager.play('correct');
        QS.stealPending = false;
        // الإجابة الصحيحة تكسب الفريق النقاط وتُبقي الدور عنده
        QS.keepTurn = true;
    } else {''',
    'correct sets keepTurn')

sub(
    '''        QS.used[key] = true;
        QS.stealPending = false;
    }

    // every resolved question hands the turn to the other team
    QS.turn = QS.turn === 1 ? 2 : 1;
    updateHUD();
    closeQuestionModal();
    renderBoard();
    if (isBoardDone()) endQuizGame();
}''',
    '''        QS.used[key] = true;
        QS.stealPending = false;
    }

    // من لم يجب إجابة صحيحة لا يحتفظ بدوره — ينتقل الدور للفريق الآخر.
    // الاستثناء الوحيد: الإجابة الصحيحة (أعلاه) تُبقي الدور عند صاحبها.
    if (QS.keepTurn) {
        QS.keepTurn = false;
        showToast('✅ إجابة صحيحة — الدور يبقى مع ' + turnName());
    } else {
        QS.turn = QS.turn === 1 ? 2 : 1;
    }
    updateHUD();
    closeQuestionModal();
    renderBoard();
    if (isBoardDone()) endQuizGame();
}

// «لم يجب»: الفريق المعني لم يجب، فينتقل السؤال للفريق الآخر لمحاولة أخيرة.
// إن لم يجب الثاني أيضاً يُغلق السؤال، ويحتفظ الفريق الذي عُرض عليه السؤال
// بدوره لأنه لم يجب — فلا يضيع منه الدور.
function markNoAnswer() {
    if (!currentQuestion) return;
    var cid = currentQuestion._cid, idx = currentQuestion._idx;
    var key = cid + '-' + idx;
    if (QS.used[key]) { showToast('سُجّلت نتيجة هذا السؤال مسبقًا', 'error'); return; }
    stopTimer();
    var pts = currentQuestion.points;
    var whoFailed = QS.turn;

    QS.noAnswer++;
    QS.wrong++;
    bumpStat(cid, 'wrong', pts);
    if (QS.allowPenalty) {
        if (whoFailed === 1) QS.s1 = Math.max(0, QS.s1 - pts);
        else QS.s2 = Math.max(0, QS.s2 - pts);
    }
    if (QS.allowSteal && !QS.stealPending) {
        QS.stealPending = true;
        QS.turn = whoFailed === 1 ? 2 : 1;
        showToast('لم يجب ' + turnName() + ' — السؤال الآن لـ ' + turnName(), 'error');
        document.getElementById('answerSection').style.display = 'none';
        document.getElementById('showAnswerRow').style.display = 'block';
        document.getElementById('noAnswerBtn').disabled = true;
        var tb = document.getElementById('turnBanner');
        tb.textContent = '🤐 لم يجب ' + (whoFailed === 1 ? QS.team1 : QS.team2) +
                         ' — فرصة لـ ' + turnName();
        tb.style.color = turnColor();
        startTimer(QS.timerDuration || 20);
        updateHUD();
        return;
    }
    // لم يجب الفريقان: يُغلق السؤال ويحتفظ الفريق الذي عُرض عليه الدور
    QS.used[key] = true;
    QS.stealPending = false;
    QS.turn = whoFailed;
    showToast('لم يجب الفريقان — يبقى الدور مع ' + turnName());
    updateHUD();
    closeQuestionModal();
    renderBoard();
    if (isBoardDone()) endQuizGame();
}''',
    'markNoAnswer mechanic')

# ---------------------------------------------------------------- 5. skip keeps the turn
sub(
    '''function skipQuestion() {
    if (!currentQuestion) return;
    QS.used[currentQuestion._cid + '-' + currentQuestion._idx] = true;
    QS.skipped++;
    QS.stealPending = false;
    QS.turn = QS.turn === 1 ? 2 : 1;
    stopTimer(); closeQuestionModal(); renderBoard(); updateHUD();
    if (isBoardDone()) endQuizGame();
}''',
    '''function skipQuestion() {
    if (!currentQuestion) return;
    QS.used[currentQuestion._cid + '-' + currentQuestion._idx] = true;
    QS.skipped++;
    QS.stealPending = false;
    // التجاوز لا يضيع الدور عن الفريق — يبقى دوره ويختار سؤالاً آخر
    stopTimer(); closeQuestionModal(); renderBoard(); updateHUD();
    if (isBoardDone()) endQuizGame();
}''',
    'skip keeps turn')

# ---------------------------------------------------------------- 6. openQuestion resets
sub(
    '''    currentQuestion = q;
    currentQuestion._cid = cid;
    currentQuestion._idx = idx;
    QS.stealPending = false;''',
    '''    currentQuestion = q;
    currentQuestion._cid = cid;
    currentQuestion._idx = idx;
    QS.stealPending = false;
    QS.keepTurn = false;
    var nab = document.getElementById('noAnswerBtn');
    if (nab) { nab.disabled = false; nab.style.display = QS.allowNoAnswer ? '' : 'none'; }''',
    'openQuestion reset')

# ---------------------------------------------------------------- 7. HUD summary
sub(
    '''        '<p style="text-align:center;color:var(--text-secondary)">صحيحة: ' + QS.correct + ' · خاطئة: ' + QS.wrong +
        ' · متجاوزة: ' + QS.skipped + '</p>' +''',
    '''        '<p style="text-align:center;color:var(--text-secondary)">صحيحة: ' + QS.correct + ' · خاطئة: ' + QS.wrong +
        ' · متجاوزة: ' + QS.skipped + ' · لم يجب: ' + (QS.noAnswer || 0) + '</p>' +''',
    'HUD summary')

# ---------------------------------------------------------------- 8. sudden death reset
sub(
    '''            QS.stealPending = false;
            document.getElementById('questionCategory').textContent = '⚔️ جولة فاصلة';''',
    '''            QS.stealPending = false;
            QS.keepTurn = false;
            document.getElementById('questionCategory').textContent = '⚔️ جولة فاصلة';''',
    'suddenDeath reset')

if s != orig:
    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    print('patched %s (%d edits)' % (os.path.basename(P), len(log)))
    for l in log:
        print('  + ' + l)
else:
    print('NO CHANGE')
    sys.exit(1)
