#!/usr/bin/env python3
"""الجاسوس — الموضوع يُختار عشوائياً ولا يظهر في صفحة البداية.

The start screen used to list ten secret words for the group to pick from,
which both spoiled the round and let the spy choose a category it knew best.
The topic is now drawn at random when the match actually starts.
"""
import io
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'templates', 'game_spy.html')

html = io.open(SRC, encoding='utf-8').read()
orig = html

# 1) drop step 1 from the start screen
html = re.sub(
    r'<div class="spy-step active" id="spyStep1">.*?</div>\s*\n\s*\n',
    '', html, count=1, flags=re.DOTALL)

# 2) step 2 becomes the landing step
html = html.replace('<div class="spy-step" id="spyStep2">',
                    '<div class="spy-step active" id="spyStep2">', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">👥 الخطوة 2: عدد اللاعبين</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">👥 عدد اللاعبين</h3>', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">✏️ الخطوة 3: أسماء اللاعبين</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">✏️ أسماء اللاعبين</h3>', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">🎭 الخطوة 4: توزيع الأدوار</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">🎭 توزيع الأدوار</h3>', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">🗣️ الخطوة 5: الوصف</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">🗣️ الوصف</h3>', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">🗳️ الخطوة 6: التصويت</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">🗳️ التصويت</h3>', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">🎯 فرصة الجاسوس</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">🎯 فرصة الجاسوس</h3>', 1)
html = html.replace('<h3 style="text-align:center;margin-bottom:1rem">🏆 النتائج النهائية</h3>',
                    '<h3 style="text-align:center;margin-bottom:1rem">🏆 النتائج النهائية</h3>', 1)

# 3) no more topic grid on the start screen
old_init = """async function initSpy(){
spyTopicPool=await loadSpyContent();
if(!spyTopicPool.length){alert('لا توجد كلمات في المكتبة');return}
var shuffled=[...spyTopicPool].sort(function(){return Math.random()-.5});
var topics=shuffled.slice(0,10);
var grid=document.getElementById('spyTopics');
grid.innerHTML=topics.map(function(t,i){
return '<button class="spy-topic-btn" id="spyTopic'+i+'" onclick="selectTopic('+i+')">'+t.word+'</button>';
}).join('');
spyTopicPool=topics;
}
function selectTopic(i){
document.querySelectorAll('.spy-topic-btn').forEach(function(b){b.classList.remove('selected')});
document.getElementById('spyTopic'+i).classList.add('selected');
spyTopic=spyTopicPool[i];
setTimeout(function(){showStep('spyStep2')},300);
}
"""
new_init = """async function initSpy(){
spyTopicPool=await loadSpyContent();
if(!spyTopicPool.length){alert('لا توجد كلمات في المكتبة');return}
// الموضوع يُسحب عشوائياً عند بدء المباراة فقط — لا يظهر في صفحة البداية
showStep('spyStep2');
}
"""
assert old_init in html, 'initSpy block not found'
html = html.replace(old_init, new_init, 1)

# 4) always draw a fresh random topic at start (never reuse the previous round's)
old_start = """if(!spyTopic){
var r=await fetch('/api/content/spy?status=approved&per_page=500');
var d=await r.json();var pool=d.items||[];
spyTopic=pool[Math.floor(Math.random()*pool.length)];
}"""
new_start = """var r=await fetch('/api/content/spy?status=approved&per_page=500');
var d=await r.json();var pool=d.items||[];
if(!pool.length){alert('لا توجد كلمات في المكتبة');return}
spyTopic=pool[Math.floor(Math.random()*pool.length)];"""
assert old_start in html, 'startGame topic block not found'
html = html.replace(old_start, new_start, 1)

# 5) reset goes back to the player-count step, not the topic step
html = html.replace("showStep('spyStep1');", "showStep('spyStep2');", 1)

assert html != orig
with io.open(SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html)
print('game_spy.html patched')
print('spyTopics grid present:', 'spyTopics' in html)
print('selectTopic present:', 'selectTopic' in html)
print('spyStep1 present:', 'spyStep1' in html)
