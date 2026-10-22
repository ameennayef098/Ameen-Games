#!/usr/bin/env python3
"""Test the Detective game using Playwright - matches actual served HTML."""
import json
import re
from playwright.sync_api import sync_playwright

def run_detective_tests():
    results = {
        "game": "detective",
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
            page.goto("http://localhost:5555/game/detective")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_01_loaded.png")
            results["screenshots"].append("detective_01_loaded.png")
            
            title = page.title()
            h1 = page.locator("h1").first.text_content()
            print(f"Title: {title}, H1: {h1}")
            results["tests"].append({"test": "page_load", "status": "pass", "detail": f"Title: {title}, H1: {h1}"})
            
            # Test 2: Case selection loads
            print("\n=== Test 2: Case selection ===")
            page.wait_for_timeout(2000)
            
            case_list = page.locator("#caseList")
            case_list_visible = case_list.is_visible()
            case_cards = page.locator("#caseList .inv-card")
            case_count = case_cards.count()
            print(f"Case list visible: {case_list_visible}")
            print(f"Case cards found: {case_count}")
            
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_02_cases.png")
            results["screenshots"].append("detective_02_cases.png")
            
            if case_count == 0:
                case_html = case_list.inner_html()
                print(f"Case list HTML: {case_html[:500]}")
                results["bugs"].append({
                    "severity": "critical",
                    "description": "No case cards loaded. API may be failing.",
                    "reproduction_steps": "1. Go to detective game 2. No cases displayed"
                })
                results["tests"].append({"test": "case_cards", "status": "fail", "detail": f"Found 0 cases"})
            else:
                results["tests"].append({"test": "case_cards", "status": "pass", "detail": f"Found {case_count} cases"})
            
            # Test 3: Select a case
            print("\n=== Test 3: Select case ===")
            if case_count > 0:
                case_cards.first.click()
                page.wait_for_timeout(2000)
                
                play_area = page.locator("#playArea")
                is_visible = play_area.is_visible()
                print(f"Play area visible: {is_visible}")
                
                case_intro = page.locator("#caseIntro").text_content()
                case_setting = page.locator("#caseSetting").text_content()
                print(f"Case intro: {case_intro[:100]}...")
                print(f"Case setting: {case_setting[:100]}...")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_03_case_loaded.png")
                results["screenshots"].append("detective_03_case_loaded.png")
                
                results["tests"].append({"test": "select_case", "status": "pass" if is_visible else "fail", "detail": f"Case loaded, intro: {case_intro[:50]}..."})
            
            # Test 4: Characters display
            print("\n=== Test 4: Characters display ===")
            char_items = page.locator("#charList div")
            char_count = char_items.count()
            print(f"Characters found: {char_count}")
            results["tests"].append({"test": "characters", "status": "pass" if char_count > 0 else "fail", "detail": f"Found {char_count} characters"})
            
            # Test 5: Evidence display
            print("\n=== Test 5: Evidence display ===")
            evidence_items = page.locator("#evidenceList .inv-evidence")
            evidence_count = evidence_items.count()
            unlocked = page.locator("#evidenceList .inv-evidence.unlocked")
            locked = page.locator("#evidenceList .inv-evidence.locked")
            unlocked_count = unlocked.count()
            locked_count = locked.count()
            print(f"Evidence: {evidence_count}, Unlocked: {unlocked_count}, Locked: {locked_count}")
            
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_04_evidence.png")
            results["screenshots"].append("detective_04_evidence.png")
            
            results["tests"].append({"test": "evidence", "status": "pass" if evidence_count > 0 else "fail", "detail": f"Total: {evidence_count}, Unlocked: {unlocked_count}, Locked: {locked_count}"})
            
            # Test 6: Unlock hidden evidence
            print("\n=== Test 6: Unlock hidden evidence ===")
            points_text = page.locator("#invPoints").text_content()
            initial_points = int(re.search(r"(\d+)", points_text).group(1)) if re.search(r"(\d+)", points_text) else 0
            print(f"Initial points: {initial_points}")
            
            if locked_count > 0:
                locked.first.click()
                page.wait_for_timeout(1000)
                
                points_text = page.locator("#invPoints").text_content()
                new_points = int(re.search(r"(\d+)", points_text).group(1)) if re.search(r"(\d+)", points_text) else 0
                print(f"Points after unlock: {new_points}")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_05_unlocked.png")
                results["screenshots"].append("detective_05_unlocked.png")
                
                results["tests"].append({"test": "unlock_evidence", "status": "pass" if new_points < initial_points else "fail", "detail": f"Points: {initial_points} -> {new_points}"})
            
            # Test 7: Timeline
            print("\n=== Test 7: Timeline ===")
            timeline_items = page.locator("#timeline div")
            timeline_count = timeline_items.count()
            print(f"Timeline items: {timeline_count}")
            results["tests"].append({"test": "timeline", "status": "pass" if timeline_count > 0 else "fail", "detail": f"Found {timeline_count} timeline items"})
            
            # Test 8: Submit theory incomplete
            print("\n=== Test 8: Submit incomplete theory ===")
            submit_btn = page.locator("button:has-text(\"تقديم النظرية\")")
            submit_btn.click()
            page.wait_for_timeout(500)
            
            theory_result = page.locator("#theoryResult")
            result_visible = theory_result.is_visible()
            print(f"Theory result visible (should be False): {result_visible}")
            results["tests"].append({"test": "submit_incomplete", "status": "pass" if not result_visible else "fail", "detail": f"Result shown: {result_visible}"})
            
            # Test 9: Submit correct theory
            print("\n=== Test 9: Submit correct theory ===")
            who_input = page.locator("#theoryWho")
            how_input = page.locator("#theoryHow")
            ev_input = page.locator("#theoryEvidence")
            
            who_input.fill("د. سامي")
            how_input.fill("د. سامي سرق الحاسوب باستخدام مفتاح استعاره من م. هالة ودخل ليلاً")
            ev_input.fill("سجل الدخول, بصمات, كاميرا")
            
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_06_theory_filled.png")
            results["screenshots"].append("detective_06_theory_filled.png")
            
            submit_btn.click()
            page.wait_for_timeout(2000)
            
            theory_result = page.locator("#theoryResult")
            result_visible = theory_result.is_visible()
            print(f"Theory result visible: {result_visible}")
            
            if result_visible:
                result_html = theory_result.text_content()
                print(f"Result: {result_html[:200]}...")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_07_theory_result.png")
                results["screenshots"].append("detective_07_theory_result.png")
                
                is_correct = "صحيحة" in result_html
                score_match = re.search(r"(\d+)", result_html.split("النقاط:")[1]) if "النقاط:" in result_html else None
                score = score_match.group(1) if score_match else "?"
                
                results["tests"].append({"test": "submit_correct", "status": "pass" if is_correct else "fail", "detail": f"Correct: {is_correct}, Score: {score}"})
                
                if "الحل الصحيح" in result_html:
                    results["tests"].append({"test": "solution_reveal", "status": "pass", "detail": "Solution revealed"})
                if "التبرير" in result_html:
                    results["tests"].append({"test": "reasoning_shown", "status": "pass", "detail": "Reasoning shown"})
            else:
                results["tests"].append({"test": "submit_correct", "status": "fail", "detail": "Result not visible"})
            
            # Test 10: Wrong answer
            print("\n=== Test 10: Wrong answer ===")
            show_case_btn = page.locator("#theoryResult button:has-text(\"قضية أخرى\")")
            if show_case_btn.count() > 0:
                show_case_btn.click()
                page.wait_for_timeout(1000)
                
                case_cards = page.locator("#caseList .inv-card")
                if case_cards.count() > 0:
                    case_cards.first.click()
                    page.wait_for_timeout(2000)
                    
                    who_input = page.locator("#theoryWho")
                    how_input = page.locator("#theoryHow")
                    ev_input = page.locator("#theoryEvidence")
                    
                    who_input.fill("شخص مجهول")
                    how_input.fill("دخل من النافذة")
                    ev_input.fill("لا يوجد دليل")
                    
                    submit_btn = page.locator("button:has-text(\"تقديم النظرية\")")
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    
                    theory_result = page.locator("#theoryResult")
                    if theory_result.is_visible():
                        result_html = theory_result.text_content()
                        is_incorrect = "غير دقيقة" in result_html
                        print(f"Wrong answer marked incorrect: {is_incorrect}")
                        
                        page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_08_wrong_answer.png")
                        results["screenshots"].append("detective_08_wrong_answer.png")
                        
                        results["tests"].append({"test": "wrong_answer", "status": "pass" if is_incorrect else "fail", "detail": f"Correctly incorrect: {is_incorrect}"})
            
            # Test 11: Reset case
            print("\n=== Test 11: Reset case ===")
            reset_btn = page.locator("button:has-text(\"إعادة\")")
            if reset_btn.count() > 0:
                reset_btn.click()
                page.wait_for_timeout(2000)
                
                points_text = page.locator("#invPoints").text_content()
                points = int(re.search(r"(\d+)", points_text).group(1)) if re.search(r"(\d+)", points_text) else 0
                print(f"After reset points: {points}")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_09_reset.png")
                results["screenshots"].append("detective_09_reset.png")
                
                results["tests"].append({"test": "reset_case", "status": "pass" if points == 10 else "fail", "detail": f"Points after reset: {points}"})
            
            # Test 12: Full playthrough - unlock all and solve
            print("\n=== Test 12: Full playthrough ===")
            # Unlock all hidden evidence
            for i in range(10):
                locked = page.locator("#evidenceList .inv-evidence.locked")
                if locked.count() == 0:
                    break
                locked.first.click()
                page.wait_for_timeout(500)
            
            unlocked = page.locator("#evidenceList .inv-evidence.unlocked")
            total = page.locator("#evidenceList .inv-evidence")
            print(f"Evidence: {unlocked.count()}/{total.count()} unlocked")
            
            who_input = page.locator("#theoryWho")
            how_input = page.locator("#theoryHow")
            ev_input = page.locator("#theoryEvidence")
            
            who_input.fill("د. سامي")
            how_input.fill("د. سامي سرق الحاسوب باستخدام مفتاح استعاره من م. هالة")
            ev_input.fill("سجل الدخول, بصمات, كاميرا")
            
            submit_btn = page.locator("button:has-text(\"تقديم النظرية\")")
            submit_btn.click()
            page.wait_for_timeout(2000)
            
            theory_result = page.locator("#theoryResult")
            if theory_result.is_visible():
                result_html = theory_result.text_content()
                is_correct = "صحيحة" in result_html
                score_match = re.search(r"(\d+)", result_html.split("النقاط:")[1]) if "النقاط:" in result_html else None
                score = score_match.group(1) if score_match else "?"
                
                print(f"Full playthrough - Correct: {is_correct}, Score: {score}")
                
                page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_10_full_solved.png")
                results["screenshots"].append("detective_10_full_solved.png")
                
                results["tests"].append({"test": "full_playthrough", "status": "pass" if is_correct else "fail", "detail": f"Correct: {is_correct}, Score: {score}"})
            
            # Test 13: Second case
            print("\n=== Test 13: Second case ===")
            show_case_btn = page.locator("#theoryResult button:has-text(\"قضية أخرى\")")
            if show_case_btn.count() > 0:
                show_case_btn.click()
                page.wait_for_timeout(1000)
                
                case_cards = page.locator("#caseList .inv-card")
                if case_cards.count() > 1:
                    case_cards.nth(1).click()
                    page.wait_for_timeout(2000)
                    
                    case_intro = page.locator("#caseIntro").text_content()
                    print(f"Second case: {case_intro[:80]}...")
                    
                    # Unlock all
                    for i in range(10):
                        locked = page.locator("#evidenceList .inv-evidence.locked")
                        if locked.count() == 0:
                            break
                        locked.first.click()
                        page.wait_for_timeout(500)
                    
                    who_input = page.locator("#theoryWho")
                    how_input = page.locator("#theoryHow")
                    ev_input = page.locator("#theoryEvidence")
                    
                    who_input.fill("أ. سمير")
                    how_input.fill("أ. سمير سرق الطرد أثناء استراحته")
                    ev_input.fill("كاميرا, استراحة, سجل")
                    
                    submit_btn = page.locator("button:has-text(\"تقديم النظرية\")")
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    
                    theory_result = page.locator("#theoryResult")
                    if theory_result.is_visible():
                        result_html = theory_result.text_content()
                        is_correct = "صحيحة" in result_html
                        score_match = re.search(r"(\d+)", result_html.split("النقاط:")[1]) if "النقاط:" in result_html else None
                        score = score_match.group(1) if score_match else "?"
                        
                        print(f"Second case - Correct: {is_correct}, Score: {score}")
                        
                        page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_11_case2_solved.png")
                        results["screenshots"].append("detective_11_case2_solved.png")
                        
                        results["tests"].append({"test": "second_case", "status": "pass" if is_correct else "fail", "detail": f"Correct: {is_correct}, Score: {score}"})
            
            # Test 14: No difficulty selection
            print("\n=== Test 14: Difficulty selection check ===")
            diff_btn = page.locator(".diff-btn")
            diff_count = diff_btn.count()
            print(f"Difficulty buttons: {diff_count}")
            if diff_count == 0:
                results["tests"].append({"test": "difficulty_selection", "status": "fail", "detail": "No difficulty selection in served page"})
                results["bugs"].append({
                    "severity": "minor",
                    "description": "No difficulty selection in served detective page.",
                    "reproduction_steps": "1. Go to detective game 2. No difficulty buttons"
                })
            
            # Test 15: No timer mode
            print("\n=== Test 15: Timer mode check ===")
            timer_checkbox = page.locator("#timerMode")
            timer_count = timer_checkbox.count()
            print(f"Timer checkbox: {timer_count}")
            if timer_count == 0:
                results["tests"].append({"test": "timer_mode", "status": "fail", "detail": "No timer mode in served page"})
                results["bugs"].append({
                    "severity": "minor",
                    "description": "No timer mode in served detective page.",
                    "reproduction_steps": "1. Go to detective game 2. No timer checkbox"
                })
            
            # Test 16: No hint system
            print("\n=== Test 16: Hint system check ===")
            hint_btn = page.locator("#hintBtn")
            hint_count = hint_btn.count()
            print(f"Hint button: {hint_count}")
            if hint_count == 0:
                results["tests"].append({"test": "hint_system", "status": "fail", "detail": "No hint system in served page"})
                results["bugs"].append({
                    "severity": "minor",
                    "description": "No hint system in served detective page.",
                    "reproduction_steps": "1. Go to detective game 2. No hint button"
                })
            
            # Test 17: No progress tracking
            print("\n=== Test 17: Progress tracking check ===")
            progress_text = page.locator("#progressText")
            progress_count = progress_text.count()
            print(f"Progress text: {progress_count}")
            if progress_count == 0:
                results["tests"].append({"test": "progress_tracking", "status": "fail", "detail": "No progress tracking in served page"})
                results["bugs"].append({
                    "severity": "minor",
                    "description": "No progress tracking bar in served detective page.",
                    "reproduction_steps": "1. Go to detective game 2. No progress bar"
                })
            
            # Test 18: Console errors
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
            
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_12_final.png")
            results["screenshots"].append("detective_12_final.png")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            results["bugs"].append({
                "severity": "critical",
                "description": f"Test execution error: {str(e)}",
                "reproduction_steps": "N/A - infrastructure error"
            })
            page.screenshot(path="C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_error.png")
        
        browser.close()
    
    return results


if __name__ == "__main__":
    results = run_detective_tests()
    
    with open("C:/Users/Ameen Dawaghreh/Desktop/ألعاب-أمين/agent-reports/detective_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("DETECTIVE GAME TEST SUMMARY")
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
