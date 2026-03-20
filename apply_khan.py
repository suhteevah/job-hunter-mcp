"""Apply to Khan Academy Sr. AI Engineer via Playwright."""
import sys, time, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

URL = "https://job-boards.greenhouse.io/khanacademy/jobs/7724300"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
COVER_LETTER = r"J:\job-hunter-mcp\cover_khan_academy.txt"
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
SCREENSHOT_DIR = r"J:\job-hunter-mcp"


def fill_combobox_by_id(page, element_id, value, debug=False):
    """Handle React combobox by element ID: click, type, wait, ArrowDown+Enter."""
    try:
        inp = page.locator(f"#{element_id}")
        inp.scroll_into_view_if_needed()
        inp.click()
        time.sleep(0.3)

        if debug:
            # List all visible options before typing
            options = page.query_selector_all('[class*="option"], [role="option"]')
            print(f"  [DEBUG] #{element_id} has {len(options)} options visible before typing")
            for o in options[:10]:
                print(f"    Option: '{o.inner_text().strip()}'")

        inp.fill(value)
        time.sleep(0.8)

        if debug:
            # List options after typing
            options = page.query_selector_all('[class*="option"], [role="option"]')
            print(f"  [DEBUG] #{element_id} has {len(options)} options after typing '{value}'")
            for o in options[:10]:
                print(f"    Option: '{o.inner_text().strip()}'")

        inp.press("ArrowDown")
        time.sleep(0.2)
        inp.press("Enter")
        time.sleep(0.3)

        # Verify selection stuck by checking the hidden input
        hidden_val = page.evaluate(f'''() => {{
            const el = document.querySelector('input[name="question_{element_id.replace("question_", "")}"], input[type="hidden"][id*="{element_id}"]');
            return el ? el.value : "N/A";
        }}''')
        print(f"  [OK] Combobox #{element_id} -> '{value}' (hidden={hidden_val})")
    except Exception as e:
        print(f"  [WARN] Combobox #{element_id} failed: {e}")


def fill_combobox(page, label_text, value, exact=False):
    """Handle React combobox by label."""
    try:
        if exact:
            inp = page.get_by_label(label_text, exact=True)
        else:
            inp = page.get_by_label(label_text)
        inp.click()
        inp.fill(value)
        time.sleep(0.5)
        inp.press("ArrowDown")
        time.sleep(0.2)
        inp.press("Enter")
        time.sleep(0.3)
        print(f"  [OK] Combobox '{label_text}' -> '{value}'")
    except Exception as e:
        print(f"  [WARN] Combobox '{label_text}' failed: {e}")


def fill_field(page, label_text, value, exact=True):
    """Fill a simple text input by label."""
    try:
        field = page.get_by_label(label_text, exact=exact)
        field.fill(value)
        print(f"  [OK] Field '{label_text}' -> '{value}'")
    except Exception as e:
        print(f"  [WARN] Field '{label_text}' failed: {e}")


def fill_field_by_id(page, element_id, value):
    """Fill a field by element ID."""
    try:
        field = page.locator(f"#{element_id}")
        field.fill(value)
        print(f"  [OK] Field #{element_id} -> '{value[:60]}...'")
    except Exception as e:
        print(f"  [WARN] Field #{element_id} failed: {e}")


def enumerate_fields(page):
    """Print all form fields for debugging."""
    print("\n=== ENUMERATING ALL FORM FIELDS ===")
    fields = page.query_selector_all("input, select, textarea, [role='combobox']")
    for f in fields:
        tag = f.evaluate("el => el.tagName")
        ftype = f.get_attribute("type") or ""
        fid = f.get_attribute("id") or ""
        fname = f.get_attribute("name") or ""
        freq = f.get_attribute("required") or f.get_attribute("aria-required") or ""
        flabel = f.get_attribute("aria-label") or ""
        label_text = ""
        if fid:
            label_el = page.query_selector(f'label[for="{fid}"]')
            if label_el:
                label_text = label_el.inner_text().strip()
        placeholder = f.get_attribute("placeholder") or ""
        role = f.get_attribute("role") or ""
        # Get current value
        val = f.evaluate("el => el.value") or ""
        print(f"  {tag} | id={fid} | type={ftype} | label='{label_text}' | aria='{flabel}' | req={freq} | role={role} | val='{val[:40]}'")
    print(f"=== Total: {len(fields)} fields ===\n")


def apply():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context()
        page = context.new_page()

        print(f"[1] Navigating to {URL}")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # Enumerate all fields
        enumerate_fields(page)

        # === STANDARD FIELDS ===
        print("[2] Filling standard fields...")
        fill_field(page, "First Name", "Matt", exact=True)
        fill_field(page, "Last Name", "Gates", exact=True)
        fill_field(page, "Email", "ridgecellrepair@gmail.com", exact=True)
        fill_field(page, "Phone", "5307863655", exact=True)

        # LinkedIn
        fill_field(page, "LinkedIn Profile", "https://www.linkedin.com/in/matt-michels-b836b260/", exact=True)

        # Website / GitHub - use exact label from enumeration
        fill_field_by_id(page, "question_64567654", "https://github.com/suhteevah")

        # === RESUME UPLOAD ===
        print("[3] Uploading resume...")
        try:
            resume_inputs = page.query_selector_all('input[type="file"]')
            print(f"  Found {len(resume_inputs)} file inputs")
            if len(resume_inputs) >= 1:
                resume_inputs[0].set_input_files(RESUME)
                print(f"  [OK] Resume uploaded")
                time.sleep(1)
            if len(resume_inputs) >= 2:
                resume_inputs[1].set_input_files(COVER_LETTER)
                print(f"  [OK] Cover letter uploaded")
                time.sleep(1)
        except Exception as e:
            print(f"  [WARN] File upload failed: {e}")

        # === COUNTRY (React combobox) - use ID to avoid label conflict ===
        print("[4] Setting Country...")
        fill_combobox_by_id(page, "country", "United States")

        # === LOCATION ===
        print("[5] Setting Location...")
        fill_combobox_by_id(page, "candidate-location", "Chico, CA")

        # === LEGAL NAME ===
        print("[6] Filling Legal Name...")
        fill_field_by_id(page, "question_64567651", "Matt Gates")

        # === SCREENING QUESTIONS (all React comboboxes) ===
        print("[7] Filling screening questions...")

        # How did you hear about this opportunity? (combobox id=question_64567655)
        # First try to discover options
        fill_combobox_by_id(page, "question_64567655", "Other", debug=True)

        # Have you used Khan Academy before? (combobox id=question_64567656)
        fill_combobox_by_id(page, "question_64567656", "Yes")

        # Will you now, or in the future, require sponsorship? (combobox id=question_64567657)
        fill_combobox_by_id(page, "question_64567657", "No")

        # Have you developed user-facing experiences powered by LLMs? (combobox id=question_64568392)
        fill_combobox_by_id(page, "question_64568392", "Yes")

        # Briefly describe your experience using Generative AI / LLMs (textarea id=question_64568393)
        genai_text = (
            "I build production AI systems daily including prompt chaining, RAG pipelines, "
            "tool calling, and multi-step agent orchestration. I've built 10+ MCP servers "
            "and a full AI browser automation engine (27K lines of Rust) with MCTS planning "
            "and knowledge graph integration. I work extensively with OpenAI, Anthropic/Claude, "
            "LangChain, and FastAPI to build user-facing AI products with evaluation frameworks "
            "and automated testing."
        )
        fill_field_by_id(page, "question_64568393", genai_text)

        # 5+ years transferable technical experience? (combobox id=question_64570350)
        fill_combobox_by_id(page, "question_64570350", "Yes")

        # 2+ years AI/ML/NLP? (combobox id=question_64570351)
        fill_combobox_by_id(page, "question_64570351", "Yes")

        # 1+ years education experience? (combobox id=question_64570352)
        fill_combobox_by_id(page, "question_64570352", "Yes")

        # Describe education experience (textarea id=question_64570353)
        edu_text = (
            "I have built educational technology tools including AI-powered tutoring systems "
            "and interactive learning platforms. I've developed curriculum content for technical "
            "training programs and mentored junior engineers. I'm a regular user of Khan Academy "
            "and deeply understand the learning experience from a student perspective."
        )
        fill_field_by_id(page, "question_64570353", edu_text)

        # === EEO SECTION (all React comboboxes by ID) ===
        print("[8] Filling EEO fields...")
        fill_combobox_by_id(page, "gender", "Male")
        fill_combobox_by_id(page, "hispanic_ethnicity", "No")
        fill_combobox_by_id(page, "race", "White")
        fill_combobox_by_id(page, "veteran_status", "I am not a protected veteran")
        fill_combobox_by_id(page, "disability_status", "I do not want to answer")

        # === PRE-SUBMIT SCREENSHOT ===
        print("[9] Taking pre-submit screenshot...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        page.screenshot(path=f"{SCREENSHOT_DIR}/khan_pre_submit.png", full_page=True)
        print(f"  Saved: {SCREENSHOT_DIR}/khan_pre_submit.png")

        # Re-enumerate to verify
        print("\n[9b] Re-enumerating to verify completion...")
        enumerate_fields(page)

        # === SUBMIT ===
        print("[10] Clicking Submit...")
        try:
            submit_btn = page.get_by_role("button", name="Submit application", exact=False)
            if submit_btn.count() > 0:
                submit_btn.first.click()
                print("  [OK] Clicked 'Submit application'")
            else:
                submit_btn = page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    submit_btn.click()
                    print("  [OK] Clicked submit button (fallback)")
                else:
                    print("  [FAIL] No submit button found!")
        except Exception as e:
            print(f"  [WARN] Submit click error: {e}")

        # Wait for response
        print("  Waiting 8s for submission...")
        time.sleep(8)

        # Post-submit screenshot
        page.screenshot(path=f"{SCREENSHOT_DIR}/khan_post_submit.png", full_page=True)
        print(f"  Saved: {SCREENSHOT_DIR}/khan_post_submit.png")

        # === CHECK SUCCESS ===
        print("[11] Checking submission result...")
        page_text = page.inner_text("body").lower()
        success_markers = ["thank", "submitted", "received", "confirmation", "application has been"]
        submit_still_visible = False
        try:
            btn = page.get_by_role("button", name="Submit application", exact=False)
            submit_still_visible = btn.count() > 0 and btn.first.is_visible()
        except:
            pass

        found_success = any(m in page_text for m in success_markers)

        if found_success and not submit_still_visible:
            print("  [SUCCESS] Application submitted successfully!")
            update_db()
        elif not submit_still_visible:
            print("  [LIKELY SUCCESS] Submit button gone.")
            errors = page.query_selector_all('[class*="error"], [class*="Error"], .field-error, [role="alert"]')
            if errors:
                print(f"  [INFO] Found {len(errors)} error elements on page")
                for err in errors[:5]:
                    print(f"    Error: {err.inner_text().strip()}")
            else:
                update_db()
        else:
            print("  [FAIL] Submit button still visible. Checking errors...")
            errors = page.query_selector_all('[class*="error"], [class*="Error"], .field-error, [role="alert"]')
            for err in errors[:10]:
                print(f"    Error: {err.inner_text().strip()}")

        print("\n[12] Keeping browser open for 5s for manual inspection...")
        time.sleep(5)
        browser.close()
        print("[DONE]")


def update_db():
    """Update jobs.db to mark Khan Academy as applied."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE jobs
            SET status='applied', applied_date=datetime('now'),
                notes='Applied via Playwright 2026-03-20. Personalized cover letter.'
            WHERE url LIKE '%khanacademy%'
        """)
        rows = cur.rowcount
        conn.commit()
        conn.close()
        print(f"  [DB] Updated {rows} row(s) in jobs.db")
    except Exception as e:
        print(f"  [DB WARN] DB update failed: {e}")


if __name__ == "__main__":
    apply()
