#!/usr/bin/env python3
"""Test the Debate game using Playwright - matches actual served HTML."""
import json
import re
from playwright.sync_api import sync_playwright

def run_debate_tests():
    results = {
        "game": "debate",
        "tests": [],
        "bugs": [],
        "console_errors": [],
        "screenshots": []
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        page.on("console", lambda msg: 
            results["console_errors"].append(f"{msg.type}: {msg.text}") if msg.type == "error" else None
        )
        
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        
        alerts = []
        page.on("dialog", lambda dialog: alerts.append(dialog.message) or dialog.accept())
        
        try:
            # Test 1: Page loads
            print("=== Test 1: Page loads ===")
            page.goto("http://localhost:5555/game/debate")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_01_loaded.png")
            results["screenshots"].append("debate_01_loaded.png")
            
            title = page.title()
            h1 = page.locator("h1").first.text_content()
            print(f"Title: {title}, H1: {h1}")
            results["tests"].append({"test": "page_load", "status": "pass", "detail": f"Title: {title}, H1: {h1}"})
            
            # Test 2: Topic selection loads
            print("\n=== Test 2: Topic selection ===")
            page.wait_for_timeout(2000)
            
            topic_list = page.locator("#topicList")
            topic_list_visible = topic_list.is_visible()
            topic_cards = page.locator("#topicList .debate-card")
            topic_count = topic_cards.count()
            print(f"Topic list visible: {topic_list_visible}")
            print(f"Topic cards found: {topic_count}")
            
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_02_topics.png")
            results["screenshots"].append("debate_02_topics.png")
            
            if topic_count == 0:
                topic_html = topic_list.inner_html()
                print(f"Topic list HTML: {topic_html[:500]}")
                results["bugs"].append({
                    "severity": "critical",
                    "description": "No topic cards loaded in the topic list. The API call to /api/content/debate may be failing or returning empty results.",
                    "reproduction_steps": "1. Go to http://localhost:5555/game/debate 2. Wait for page to load 3. Observe that no topic cards are displayed in the topic selection area"
                })
                results["tests"].append({"test": "topic_cards", "status": "fail", "detail": f"Found 0 topic cards, HTML: {topic_html[:200]}"})
            else:
                results["tests"].append({"test": "topic_cards", "status": "pass", "detail": f"Found {topic_count} topic cards"})
            
            # Test 3: Select a topic
            print("\n=== Test 3: Select topic ===")
            if topic_count > 0:
                topic_cards.first.click()
                page.wait_for_timeout(2000)
                
                play_area = page.locator("#playArea")
                is_visible = play_area.is_visible()
                print(f"Play area visible: {is_visible}")
                
                pro_side = page.locator("#proSide").text_content()
                con_side = page.locator("#conSide").text_content()
                print(f"Pro side: {pro_side[:80]}...")
                print(f"Con side: {con_side[:80]}...")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_03_debate_started.png")
                results["screenshots"].append("debate_03_debate_started.png")
                
                results["tests"].append({"test": "select_topic", "status": "pass" if is_visible else "fail", "detail": f"Play area: {is_visible}, Pro: {pro_side[:50]}..."})
            
            # Test 4: Submit pro arguments
            print("\n=== Test 4: Submit pro arguments ===")
            pro_input = page.locator("#proInput")
            pro_visible = pro_input.is_visible()
            print(f"Pro input visible: {pro_visible}")
            
            if pro_visible:
                pro_input.fill("التعليم بالمشاريع يطور مهارات العمل الجماعي ويحفز الإبداع لدى الطلاب بشكل أفضل من الاختبارات التقليدية التي تعتمد على الحفظ والتلقين.")
                page.locator("button:has-text(\"تقديم الحجة\")").first.click()
                page.wait_for_timeout(500)
                
                pro_args = page.locator("#proArgs .debate-arg")
                pro_args_count = pro_args.count()
                print(f"Pro arguments after submit: {pro_args_count}")
                
                pro_input.fill("الاختبارات التقليدية لا تقيس المهارات الحقيقية للطلاب.")
                page.locator("button:has-text(\"تقديم الحجة\")").first.click()
                page.wait_for_timeout(500)
                
                pro_args_count = pro_args.count()
                print(f"Pro arguments after 2nd submit: {pro_args_count}")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_04_pro_args.png")
                results["screenshots"].append("debate_04_pro_args.png")
                
                results["tests"].append({"test": "submit_pro_args", "status": "pass" if pro_args_count >= 2 else "fail", "detail": f"Submitted {pro_args_count} pro arguments"})
            
            # Test 5: Submit con arguments
            print("\n=== Test 5: Submit con arguments ===")
            con_input = page.locator("#conInput")
            con_visible = con_input.is_visible()
            
            if con_visible:
                con_input.fill("الاختبارات التقليدية تضمن تقييماً عادلاً وموضوياً لجميع الطلاب وتمنع الغش والتلاعب.")
                page.locator("button:has-text(\"تقديم الحجة\")").nth(1).click()
                page.wait_for_timeout(500)
                
                con_args = page.locator("#conArgs .debate-arg")
                con_args_count = con_args.count()
                print(f"Con arguments after submit: {con_args_count}")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_05_con_args.png")
                results["screenshots"].append("debate_05_con_args.png")
                
                results["tests"].append({"test": "submit_con_args", "status": "pass" if con_args_count >= 1 else "fail", "detail": f"Submitted {con_args_count} con arguments"})
            
            # Test 6: Timer display
            print("\n=== Test 6: Timer display ===")
            timer = page.locator("#debateTimer")
            timer_text = timer.text_content()
            print(f"Timer: {timer_text}")
            results["tests"].append({"test": "timer_display", "status": "pass" if ":" in timer_text else "fail", "detail": f"Timer: {timer_text}"})
            
            # Test 7: Finish debate
            print("\n=== Test 7: Finish debate ===")
            finish_btn = page.locator("button:has-text(\"إنهاء النقاش\")")
            if finish_btn.count() > 0 and finish_btn.is_visible():
                finish_btn.click()
                page.wait_for_timeout(2000)
                
                result_area = page.locator("#resultArea")
                result_visible = result_area.is_visible()
                print(f"Result area visible: {result_visible}")
                
                if result_visible:
                    result_html = result_area.text_content()
                    print(f"Result text: {result_html[:200]}...")
                    
                    has_winner = "الفائز" in result_html or "تعادل" in result_html
                    has_scores = "VS" in result_html
                    
                    page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_06_results.png")
                    results["screenshots"].append("debate_06_results.png")
                    
                    results["tests"].append({"test": "finish_debate", "status": "pass" if result_visible else "fail", "detail": f"Winner: {has_winner}, Scores: {has_scores}"})
                    
                    score_match = re.search(r"(\d+)\s*VS\s*(\d+)", result_html.replace("\n", " ").replace("\r", ""))
                    if score_match:
                        pro_score = int(score_match.group(1))
                        con_score = int(score_match.group(2))
                        print(f"Pro score: {pro_score}, Con score: {con_score}")
                        
                        if abs(pro_score - con_score) <= 3:
                            results["bugs"].append({
                                "severity": "minor",
                                "description": f"Debate scoring appears random. Pro: {pro_score}, Con: {con_score}. Difference: {abs(pro_score - con_score)}.",
                                "reproduction_steps": "1. Go to debate game 2. Select topic 3. Submit 2+ args each 4. Click finish 5. Scores are very close"
                            })
                else:
                    results["tests"].append({"test": "finish_debate", "status": "fail", "detail": "Result area not visible"})
            else:
                results["tests"].append({"test": "finish_debate", "status": "fail", "detail": "Finish button not found"})
            
            # Test 8: Back to topic select
            print("\n=== Test 8: Back to topic select ===")
            if result_visible:
                back_btn = page.locator("button:has-text(\"موضوع آخر\")")
                if back_btn.count() > 0:
                    back_btn.first.click()
                    page.wait_for_timeout(1000)
                    topic_list = page.locator("#topicList")
                    is_visible = topic_list.is_visible()
                    print(f"Topic list visible: {is_visible}")
                    results["tests"].append({"test": "back_to_topics", "status": "pass" if is_visible else "fail", "detail": f"Topic list: {is_visible}"})
            
            # Test 9: Select another topic
            print("\n=== Test 9: Select another topic ===")
            if is_visible and topic_count > 1:
                topic_cards.nth(1).click()
                page.wait_for_timeout(2000)
                play_area = page.locator("#playArea")
                is_visible = play_area.is_visible()
                print(f"Second topic play area: {is_visible}")
                results["tests"].append({"test": "second_topic", "status": "pass" if is_visible else "fail", "detail": f"Play area: {is_visible}"})
            
            # Test 10: No AI evaluation feature
            print("\n=== Test 10: AI evaluation check ===")
            ai_btn = page.locator("button:has-text(\"الذكاء الاصطناعي\")")
            ai_btn_count = ai_btn.count()
            print(f"AI buttons: {ai_btn_count}")
            if ai_btn_count == 0:
                results["tests"].append({"test": "ai_evaluation", "status": "fail", "detail": "No AI evaluation button - uses local random scoring"})
                results["bugs"].append({
                    "severity": "major",
                    "description": "Debate game has NO AI evaluation. The served page uses finishDebate() with random scoring, not the AI judging system from the template.",
                    "reproduction_steps": "1. Go to debate game 2. No AI evaluation button exists 3. Scoring is random"
                })
            else:
                results["tests"].append({"test": "ai_evaluation", "status": "pass", "detail": "AI evaluation found"})
            
            # Test 11: No AI topic generation
            print("\n=== Test 11: AI topic generation check ===")
            ai_topic_btn = page.locator("button:has-text(\"توليد موضوع\")")
            ai_topic_count = ai_topic_btn.count()
            print(f"AI topic buttons: {ai_topic_count}")
            if ai_topic_count == 0:
                results["tests"].append({"test": "ai_topic_generation", "status": "fail", "detail": "No AI topic generation button"})
                results["bugs"].append({
                    "severity": "minor",
                    "description": "No AI topic generation feature in served page.",
                    "reproduction_steps": "1. Go to debate game 2. No AI topic generation button"
                })
            
            # Test 12: No phase system
            print("\n=== Test 12: Phase system check ===")
            phase_label = page.locator("#phaseLabel")
            phase_text = phase_label.text_content() if phase_label.count() > 0 else ""
            next_phase_btn = page.locator("button:has-text(\"التالي\")")
            next_btn_count = next_phase_btn.count()
            print(f"Phase label: {phase_text}, Next buttons: {next_btn_count}")
            if next_btn_count == 0:
                results["tests"].append({"test": "phase_system", "status": "fail", "detail": "No phase system - both teams submit simultaneously"})
                results["bugs"].append({
                    "severity": "minor",
                    "description": "No debate phase system in served page.",
                    "reproduction_steps": "1. Go to debate game 2. Both teams submit simultaneously"
                })
            
            # Test 13: Console errors
            print("\n=== Console Errors ===")
            if results["console_errors"]:
                print(f"Found {len(results['console_errors'])} console errors:")
                for err in results["console_errors"]:
                    print(f"  - {err}")
            else:
                print("No console errors found")
            
            if page_errors:
                print(f"Found {len(page_errors)} page errors:")
                for err in page_errors:
                    print(f"  - {err}")
            
            results["console_errors"].extend(page_errors)
            
            if alerts:
                print(f"\nAlerts: {alerts}")
            
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_14_final.png")
            results["screenshots"].append("debate_14_final.png")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            results["bugs"].append({
                "severity": "critical",
                "description": f"Test execution error: {str(e)}",
                "reproduction_steps": "N/A - infrastructure error"
            })
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_error.png")
        
        browser.close()
    
    return results


if __name__ == "__main__":
    results = run_debate_tests()
    
    with open("C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/debate_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("DEBATE GAME TEST SUMMARY")
    print("="*60)
    for test in results["tests"]:
        status_icon = "PASS" if test["status"] == "pass" else "FAIL"
        print(f"  [{status_icon}] {test['test']}: {test['detail']}")
    
    print(f"\nBugs found: {len(results['bugs'])}")
    for bug in results["bugs"]:
        print(f"  [{bug['severity']}] {bug['description'][:100]}...")
    
    print(f"\nConsole errors: {len(results['console_errors'])}")
    for err in results["console_errors"]:
        print(f"  - {err}")
