"""Apply to Grafana Labs Senior AI Engineer via Playwright browser automation.
v2 - Uses exact element IDs discovered from first run to avoid strict mode violations."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time
import sqlite3

URL = "https://job-boards.greenhouse.io/grafanalabs/jobs/5802159004"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
DB = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
SCREENSHOTS_DIR = r"J:\job-hunter-mcp"

COVER_LETTER = """Dear Grafana Labs Hiring Team,

I'm deeply excited about this role because it sits at the exact intersection of my two strongest domains: AI/ML engineering and observability infrastructure.

What I bring:

Production Observability: I run Prometheus + Grafana monitoring stacks daily for my GPU inference fleet and AI agent systems. I understand metrics, traces, and logs not as abstract concepts but as tools I depend on to keep production AI systems healthy.

AI Agent Systems: I've built 10+ production MCP servers for Claude Code integration, a 27K-line Rust browser automation engine with MCTS action planning and multi-step agent orchestration, and an autonomous trading bot using ML prediction models (20x returns).

LLM Application Development: I build with OpenAI, Anthropic/Claude, LangChain, and custom inference stacks daily. Prompt engineering, RAG pipelines, tool calling, streaming - these are my daily tools, not buzzwords.

Infrastructure: Docker/Kubernetes container orchestration, CI/CD pipelines with safety gates, Python/Rust/TypeScript polyglot development, and GPU inference optimization.

The opportunity to build AI-powered features that help users understand and respond to their observability data is exactly where I want to be.

Best regards,
Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""

# Artifacts text for the LLM artifacts question
ARTIFACTS_TEXT = (
    "GitHub: https://github.com/suhteevah - 10+ MCP servers for Claude Code, "
    "27K-line Rust browser automation engine with MCTS action planning, "
    "autonomous trading bot with ML prediction models. "
    "Built production Prometheus+Grafana monitoring for GPU inference fleet. "
    "RAG pipelines, LLM tool calling, streaming inference optimization."
)

ANYTHING_ELSE = (
    "I run Prometheus + Grafana monitoring stacks daily for my GPU inference fleet "
    "and AI agent systems. I'm passionate about the intersection of AI and observability. "
    "Cover letter with more details: " + COVER_LETTER[:200] + "..."
)


def fill_combobox_by_id(page, element_id, value, label_desc="", list_options=False):
    """Fill a React-Select combobox by targeting its exact element ID."""
    combo = page.locator(f'input[id="{element_id}"]')
    combo.scroll_into_view_if_needed()
    time.sleep(0.2)
    combo.click()
    time.sleep(0.5)

    if list_options:
        # List all available options before selecting
        options = page.locator('[class*="option"]').all()
        print(f"    Available options for {label_desc or element_id}:")
        for opt in options:
            try:
                if opt.is_visible():
                    print(f"      - '{opt.text_content().strip()}'")
            except:
                pass

    combo.fill(value)
    time.sleep(0.8)

    # Try to find and click the matching option
    option = page.locator('[class*="option"]').filter(has_text=value).first
    if option.count() > 0 and option.is_visible():
        option.click()
        print(f"  - {label_desc or element_id}: '{value}' (clicked option)")
    else:
        # Fallback: arrow down + enter
        combo.press("ArrowDown")
        time.sleep(0.2)
        combo.press("Enter")
        print(f"  - {label_desc or element_id}: '{value}' (ArrowDown+Enter)")
    time.sleep(0.3)


def apply():
    print(f"[*] Starting Grafana Labs Senior AI Engineer application v2...")
    print(f"    URL: {URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle")
        time.sleep(3)

        # =====================================================
        # STEP 1: Discover all form fields (for logging)
        # =====================================================
        print("\n" + "="*70)
        print("[*] STEP 1: Discovering all form fields...")
        print("="*70)

        fields = page.locator('input, select, textarea').all()
        print(f"Found {len(fields)} form elements")

        # Print labels for context
        labels = page.locator('label').all()
        print(f"\nAll labels on page:")
        for label in labels:
            try:
                text = label.text_content().strip()
                for_attr = label.get_attribute("for") or ""
                if text:
                    print(f"  label[for={for_attr}]: {text[:120]}")
            except:
                pass

        # =====================================================
        # STEP 2: Fill standard text fields
        # =====================================================
        print("\n" + "="*70)
        print("[*] STEP 2: Filling standard fields...")
        print("="*70)

        # First Name
        page.locator('input[id="first_name"]').fill("Matt")
        print("  - First Name: Matt")

        # Last Name
        page.locator('input[id="last_name"]').fill("Gates")
        print("  - Last Name: Gates")

        # Email
        page.locator('input[id="email"]').fill("ridgecellrepair@gmail.com")
        print("  - Email: ridgecellrepair@gmail.com")

        # Country (React combobox - target by ID to avoid strict mode)
        print("[*] Setting Country...")
        fill_combobox_by_id(page, "country", "United States", "Country")

        # Phone
        page.locator('input[id="phone"]').fill("5307863655")
        print("  - Phone: 5307863655")

        # Resume upload
        print("[*] Uploading resume...")
        page.locator('input[id="resume"][type="file"]').set_input_files(RESUME)
        time.sleep(1)
        print("  - Resume uploaded")

        # Cover Letter - check if field exists
        print("[*] Checking for cover letter field...")
        cl_upload = page.locator('input[id="cover_letter"][type="file"]')
        if cl_upload.count() > 0:
            cl_path = r"J:\job-hunter-mcp\grafana_cover_letter.txt"
            with open(cl_path, 'w', encoding='utf-8') as f:
                f.write(COVER_LETTER)
            cl_upload.set_input_files(cl_path)
            time.sleep(0.5)
            print("  - Cover letter uploaded as file")
        else:
            cl_text = page.locator('[id="cover_letter_text"], textarea[name*="cover"]').first
            if cl_text.count() > 0 and cl_text.is_visible():
                cl_text.fill(COVER_LETTER)
                print("  - Cover letter text filled")
            else:
                print("  - No cover letter field found (will use 'Anything else' field)")

        # Website
        page.locator('input[id="question_15411263004"]').fill("https://github.com/suhteevah")
        print("  - Website: https://github.com/suhteevah")

        # LinkedIn Profile
        page.locator('input[id="question_15556389004"]').fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        print("  - LinkedIn Profile: filled")

        # =====================================================
        # STEP 3: Fill screening questions (by discovered IDs)
        # =====================================================
        print("\n" + "="*70)
        print("[*] STEP 3: Filling screening questions by ID...")
        print("="*70)

        # candidate-location (combobox)
        print("[*] Setting Location...")
        loc = page.locator('input[id="candidate-location"]')
        loc.scroll_into_view_if_needed()
        loc.click()
        time.sleep(0.3)
        loc.fill("Chico")
        time.sleep(1.0)
        option = page.locator('[class*="option"]').filter(has_text="Chico").first
        if option.count() > 0 and option.is_visible():
            option.click()
            print("  - Location: Chico (clicked option)")
        else:
            loc.press("ArrowDown")
            time.sleep(0.2)
            loc.press("Enter")
            print("  - Location: Chico (ArrowDown+Enter)")
        time.sleep(0.3)

        # question_15411265004 = "Are you based and plan to work from the US?"
        fill_combobox_by_id(page, "question_15411265004", "Yes",
                           "Are you based and plan to work from the US?")

        # LLM artifacts question (text field)
        page.locator('input[id="question_15411266004"]').fill(ARTIFACTS_TEXT)
        print("  - LLM artifacts: filled")

        # question_15411267004 = "Are you currently eligible to work in your country of residence?"
        fill_combobox_by_id(page, "question_15411267004", "Yes",
                           "Eligible to work in country of residence?")

        # question_15411268004 = "Do you now or in the future require visa sponsorship?"
        fill_combobox_by_id(page, "question_15411268004", "No",
                           "Require visa sponsorship?")

        # Anything else you'd like to share
        page.locator('input[id="question_15411270004"]').fill(ANYTHING_ELSE[:500])
        print("  - Anything else: filled")

        # question_15411271004 = "Which of the following best describes you?"
        # Options: "I am an AI or automated program", "I am a human being"
        print("[*] Setting 'Which best describes you'...")
        fill_combobox_by_id(page, "question_15411271004", "I am a human being",
                           "Which best describes you?")

        # question_15519177004 = "How did you hear about this opportunity at Grafana?"
        # Options: Built-In, Company Website, Grafana Event, Grot Community, LinkedIn, Referral, Other
        fill_combobox_by_id(page, "question_15519177004", "Other",
                           "How did you hear about Grafana?")

        # =====================================================
        # STEP 4: EEO / Demographics fields (by ID)
        # =====================================================
        print("\n" + "="*70)
        print("[*] STEP 4: Filling EEO/Demographics fields...")
        print("="*70)

        # 4000681004 = "What gender identity do you most closely identify with?"
        fill_combobox_by_id(page, "4000681004", "Man",
                           "Gender identity")

        # 4000682004 = Race (likely "Are you a person of transgender experience?" or Race)
        # From the error output it showed as "Race*"
        fill_combobox_by_id(page, "4000682004", "White",
                           "Race")

        # 4000691004 = "Are you a person of transgender experience?"
        fill_combobox_by_id(page, "4000691004", "No",
                           "Transgender experience?")

        # gender (voluntary EEO - separate from the required one)
        fill_combobox_by_id(page, "gender", "Male", "Gender (EEO)")

        # hispanic_ethnicity
        fill_combobox_by_id(page, "hispanic_ethnicity", "No",
                           "Hispanic/Latino (EEO)")

        # veteran_status
        fill_combobox_by_id(page, "veteran_status", "I am not a protected veteran",
                           "Veteran Status (EEO)")

        # disability_status
        fill_combobox_by_id(page, "disability_status", "I do not want to answer",
                           "Disability Status (EEO)")

        # =====================================================
        # STEP 5: Final validation
        # =====================================================
        print("\n" + "="*70)
        print("[*] STEP 5: Final validation...")
        print("="*70)

        required_fields = page.locator('[aria-required="true"]').all()
        all_ok = True
        for req in required_fields:
            try:
                label = req.get_attribute("aria-label") or req.get_attribute("id") or "?"
                try:
                    val = req.input_value()
                except:
                    val = "(non-input)"
                status = "OK" if val else "EMPTY"
                if not val:
                    all_ok = False
                print(f"  {status}: {label} = '{str(val)[:60]}'")
            except Exception as e:
                print(f"  [!] Validation error: {e}")

        # Screenshot before submit
        print("\n[*] Taking pre-submit screenshot...")
        page.screenshot(path=f"{SCREENSHOTS_DIR}\\grafana_pre_submit.png", full_page=True)
        print(f"  Saved: grafana_pre_submit.png")

        if not all_ok:
            print("\n[!] Some required fields may be empty. Attempting submit anyway...")

        # =====================================================
        # STEP 6: Submit
        # =====================================================
        print("\n" + "="*70)
        print("[*] STEP 6: SUBMITTING APPLICATION...")
        print("="*70)

        submit_btn = page.get_by_role("button", name="Submit application")
        submit_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit_btn.click()
        print("  -> Submit button clicked!")

        # Wait for response
        time.sleep(6)

        # Screenshot after submit
        page.screenshot(path=f"{SCREENSHOTS_DIR}\\grafana_post_submit.png", full_page=True)
        print(f"  Saved: grafana_post_submit.png")

        # Check for success
        body_text = page.locator("body").text_content()
        success_indicators = ["thank", "received", "submitted", "application has been", "confirmation"]
        found_success = False
        for indicator in success_indicators:
            if indicator.lower() in body_text.lower():
                found_success = True
                print(f"  [SUCCESS] Found success indicator: '{indicator}'")
                break

        if found_success:
            print("\n[SUCCESS] Application appears to have been submitted successfully!")
        else:
            errors = page.locator('[class*="error"], [class*="Error"], .field--error').all()
            if errors:
                print(f"\n[WARNING] Found {len(errors)} error elements on page:")
                for err in errors:
                    try:
                        txt = err.text_content().strip()
                        if txt:
                            print(f"  - {txt[:100]}")
                    except:
                        pass
            else:
                print("\n[INFO] No clear success or error indicators found. Check screenshots.")

        time.sleep(2)
        browser.close()

    return found_success


if __name__ == "__main__":
    print("="*70)
    print("Grafana Labs - Senior AI Engineer Application v2")
    print("="*70)

    success = apply()

    # Update DB
    print("\n[*] Updating database...")
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("SELECT id, status FROM jobs WHERE url LIKE '%grafanalabs%'")
        row = c.fetchone()

        if row:
            c.execute("""UPDATE jobs SET status='applied', applied_date=datetime('now'),
                        notes='Applied via Playwright 2026-03-20. Personalized cover letter.'
                        WHERE url LIKE '%grafanalabs%'""")
            conn.commit()
            print(f"  -> DB updated: job {row[0]} marked as applied")
        else:
            c.execute("""INSERT INTO jobs (title, company, url, status, applied_date, notes)
                        VALUES (?, ?, ?, 'applied', datetime('now'), ?)""",
                      ("Senior AI Engineer", "Grafana Labs", URL,
                       "Applied via Playwright 2026-03-20. Personalized cover letter."))
            conn.commit()
            print("  -> DB: inserted new job record and marked as applied")

        c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
        total = c.fetchone()[0]
        print(f"  Total applied in DB: {total}")
        conn.close()
    except Exception as e:
        print(f"  [!] DB error: {e}")

    print("\n" + "="*70)
    print("DONE.")
    print("="*70)
