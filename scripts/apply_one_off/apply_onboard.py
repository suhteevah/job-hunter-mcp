"""Apply to OnBoard Meetings Senior Software Engineer, eScribe - AI via Greenhouse."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import sqlite3
from playwright.sync_api import sync_playwright

URL = "https://job-boards.greenhouse.io/onboardmeetings/jobs/5813540004"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
COVER = r"J:\job-hunter-mcp\cover_onboard.txt"
DB = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"


def greenhouse_combobox(page, field_id, value, timeout=5000):
    """Fill a Greenhouse React combobox by its input id."""
    try:
        inp = page.locator(f"#{field_id}")
        inp.scroll_into_view_if_needed()
        time.sleep(0.3)
        inp.click()
        time.sleep(0.3)
        inp.fill("")
        time.sleep(0.2)
        inp.fill(value)
        time.sleep(0.8)
        # Wait for listbox options to appear
        listbox = page.locator(f"[id='{field_id}-listbox'] li, [role='listbox'] li").first
        try:
            listbox.wait_for(state="visible", timeout=timeout)
            time.sleep(0.3)
        except:
            pass
        inp.press("ArrowDown")
        time.sleep(0.2)
        inp.press("Enter")
        time.sleep(0.4)
        print(f"  [OK] Combobox #{field_id} -> '{value}'")
        return True
    except Exception as e:
        print(f"  [ERR] Combobox #{field_id}: {e}")
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=200)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.set_default_timeout(15000)

        print(f"[NAV] {URL}")
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)

        # === STANDARD TEXT FIELDS ===
        print("\n=== STANDARD FIELDS ===")
        page.locator("#first_name").fill("Matt")
        print("  [OK] First Name")
        page.locator("#last_name").fill("Gates")
        print("  [OK] Last Name")
        page.locator("#email").fill("ridgecellrepair@gmail.com")
        print("  [OK] Email")
        page.locator("#phone").fill("5307863655")
        print("  [OK] Phone")

        # Country (combobox)
        greenhouse_combobox(page, "country", "United States")

        # Resume
        print("  [UPLOAD] Resume...")
        page.locator("#resume").set_input_files(RESUME)
        print("  [OK] Resume uploaded")
        time.sleep(1)

        # Cover letter
        print("  [UPLOAD] Cover letter...")
        page.locator("#cover_letter").set_input_files(COVER)
        print("  [OK] Cover letter uploaded")
        time.sleep(1)

        # === CUSTOM QUESTIONS ===
        print("\n=== CUSTOM QUESTIONS ===")

        # Location (City + Province) - text field
        page.locator("#question_15505050004").fill("Chico, CA")
        print("  [OK] Location -> Chico, CA")

        # Salary range - text field
        page.locator("#question_15505051004").fill("Open to discussion")
        print("  [OK] Salary -> Open to discussion")

        # Work Authorization - combobox (exact option text)
        greenhouse_combobox(page, "question_15505052004", "United States Citizen")

        # Sponsorship - combobox
        greenhouse_combobox(page, "question_15505053004", "No")

        # Personal pronouns - combobox
        greenhouse_combobox(page, "question_15505054004", "He/Him")

        # How did you hear - combobox
        greenhouse_combobox(page, "question_15505055004", "Indeed")

        # If other specify - text (optional, skip or fill)
        try:
            other_field = page.locator("#question_15505056004")
            if other_field.is_visible():
                other_field.fill("Online job board search")
                print("  [OK] 'If other' -> Online job board search")
        except:
            pass

        # Do you have a LinkedIn profile? - combobox
        greenhouse_combobox(page, "question_15627841004", "Yes")

        # LinkedIn Profile URL - text field
        page.locator("#question_15505057004").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        print("  [OK] LinkedIn URL")

        # Time zone - text field
        page.locator("#question_15627797004").fill("Pacific Time (PT)")
        print("  [OK] Time zone -> Pacific Time (PT)")

        # === EEO SECTION ===
        print("\n=== EEO SECTION ===")
        greenhouse_combobox(page, "gender", "Male")
        greenhouse_combobox(page, "hispanic_ethnicity", "No")
        greenhouse_combobox(page, "veteran_status", "not a protected veteran")
        greenhouse_combobox(page, "disability_status", "do not want to answer")

        # === SCREENSHOT BEFORE SUBMIT ===
        print("\n=== PRE-SUBMIT ===")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        page.screenshot(path=r"J:\job-hunter-mcp\onboard_pre_submit.png", full_page=True)
        print("  [OK] Saved onboard_pre_submit.png")

        # === SUBMIT ===
        print("\n=== SUBMITTING ===")
        submit_btn = page.locator("button[type='submit'], input[type='submit']").first
        submit_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit_btn.click()
        print("  [OK] Clicked submit")

        time.sleep(8)

        # === SCREENSHOT AFTER SUBMIT ===
        page.screenshot(path=r"J:\job-hunter-mcp\onboard_post_submit.png", full_page=True)
        print("  [OK] Saved onboard_post_submit.png")

        # Check result
        try:
            body = page.inner_text("body")
            if any(kw in body.lower() for kw in ["thank", "submitted", "received", "application has been"]):
                print("\n[SUCCESS] Application submitted!")
                update_db()
            else:
                print("\n[WARN] Could not confirm submission. Check screenshots.")
                errors = page.query_selector_all("[class*='error'], [role='alert']")
                for err in errors:
                    try:
                        txt = err.inner_text().strip()
                        if txt:
                            print(f"  [ERROR] {txt}")
                    except:
                        pass
        except Exception as e:
            print(f"  [WARN] Post-submit check: {e}")

        browser.close()


def update_db():
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""UPDATE jobs SET status='applied', applied_date=datetime('now'),
                       notes='Applied via Playwright 2026-03-20.'
                       WHERE url LIKE '%onboardmeetings%'""")
        print(f"  [DB] Updated {cur.rowcount} row(s)")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [DB ERR] {e}")


if __name__ == "__main__":
    main()
