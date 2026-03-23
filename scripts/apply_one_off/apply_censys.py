"""Apply to Censys Senior Software Engineer, AI/LLM via Greenhouse - v3."""
import sys, time, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

URL = "https://job-boards.greenhouse.io/censys/jobs/8245155002"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
SCREENSHOT_DIR = r"J:\job-hunter-mcp\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

COVER_LETTER = """Dear Censys Hiring Team,

Building AI-powered features on top of Internet-scale data is exactly the kind of challenge I thrive on. My background combines production AI systems with the infrastructure expertise needed to make them reliable at scale.

Relevant experience:

Production AI/LLM Systems: I build and deploy LLM-powered applications daily - RAG pipelines, vector search, tool calling agents, and streaming interfaces. I've built 10+ MCP servers exposing platform capabilities to AI systems, and a 27K-line Rust browser engine with embedded knowledge graphs and semantic search.

Scale and Infrastructure: I operate GPU inference fleets with Docker container orchestration, Prometheus/Grafana monitoring, and CI/CD pipelines. I understand K8s networking, scaling, and monitoring for AI services.

Python and Full Stack: Python is my primary language for AI work, alongside Rust for performance-critical systems and TypeScript for web interfaces.

I'm a US citizen based in California, available immediately.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""

AI_SERVICE_ANSWER = """I built and deployed an autonomous job-hunting agent powered by LLMs that processes thousands of job listings daily. The system uses a RAG pipeline with vector embeddings to match resumes against job descriptions, an LLM scoring engine that evaluates fit across multiple dimensions, and a Playwright-based browser automation layer that fills and submits applications across different ATS platforms (Greenhouse, Lever, iCIMS). The stack includes Python, SQLite for state management, and MCP (Model Context Protocol) servers for tool integration. I also built a 27K-line Rust browser engine with embedded knowledge graphs and semantic search capabilities that serves as an AI-powered research tool in production."""


def fill_react_select(page, field_id, search_text, timeout=3000):
    """Fill a Greenhouse React Select combobox.
    Click to open dropdown, type to filter, then select matching option.
    """
    try:
        field = page.locator(f"#{field_id}")
        # Click to focus and open
        field.click()
        time.sleep(0.5)
        # Clear existing and type
        field.fill(search_text)
        time.sleep(1.0)

        # Wait for and click the dropdown option
        # Greenhouse uses div[id*='option'] or [role='option']
        option_selectors = [
            f"div[id*='option']:has-text('{search_text}')",
            f"[role='option']:has-text('{search_text}')",
            f"li:has-text('{search_text}')",
            f"div[class*='option']:has-text('{search_text}')",
        ]

        for sel in option_selectors:
            try:
                opt = page.locator(sel).first
                if opt.is_visible(timeout=1500):
                    opt.click()
                    print(f"  Filled #{field_id} = '{search_text}' via {sel}")
                    time.sleep(0.3)
                    return True
            except:
                continue

        # Fallback: keyboard navigation
        field.press("ArrowDown")
        time.sleep(0.3)
        field.press("Enter")
        print(f"  Filled #{field_id} = '{search_text}' via ArrowDown+Enter")
        return True
    except Exception as e:
        print(f"  ERROR #{field_id}: {e}")
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1024})
        page = ctx.new_page()
        page.set_default_timeout(15000)

        print("[1] Navigating to job page...")
        page.goto(URL, wait_until="networkidle")
        time.sleep(3)

        # ── Discover form fields ──
        print("\n[2] Discovering form fields...")
        fields = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('input, textarea, select').forEach(el => {
                let label = '';
                if (el.id) {
                    const lbl = document.querySelector('label[for="' + el.id + '"]');
                    if (lbl) label = lbl.textContent.trim();
                }
                if (!label) label = el.getAttribute('aria-label') || '';
                results.push({
                    tag: el.tagName, type: el.type || '', id: el.id || '',
                    name: el.name || '', label: label.substring(0, 150),
                    required: el.required || el.getAttribute('aria-required') === 'true',
                    visible: el.offsetParent !== null,
                    role: el.getAttribute('role') || '',
                    className: (el.className || '').substring(0, 100)
                });
            });
            return results;
        }""")
        for f in fields:
            if f['visible']:
                req = "REQ" if f['required'] else "opt"
                print(f"  [{req}] <{f['tag'].lower()} type={f['type']}> id='{f['id']}' role='{f['role']}' label='{f['label']}'")

        # ── Also discover the phone country code select ──
        print("\n  Looking for phone country code dropdown...")
        phone_area = page.evaluate("""() => {
            // Greenhouse phone fields often have intl-tel-input with a country selector
            const iti = document.querySelector('.iti, [class*="intl-tel"], [class*="phone-country"]');
            if (iti) {
                return {found: true, html: iti.innerHTML.substring(0, 500), className: iti.className};
            }
            // Also check for select near phone
            const selects = document.querySelectorAll('select');
            const selectInfo = [];
            selects.forEach(s => {
                selectInfo.push({id: s.id, name: s.name, optCount: s.options.length, visible: s.offsetParent !== null});
            });
            return {found: false, selects: selectInfo};
        }""")
        print(f"  Phone area: {phone_area}")

        # ── Fill standard text fields ──
        print("\n[3] Filling standard fields...")

        page.locator("#first_name").fill("Matt")
        print("  First Name: Matt")

        page.locator("#last_name").fill("Gates")
        print("  Last Name: Gates")

        page.locator("#email").fill("ridgecellrepair@gmail.com")
        print("  Email: ridgecellrepair@gmail.com")

        # Phone - handle the intl-tel-input country code first
        # The Greenhouse intl-tel-input uses a button to open country list
        print("\n[4] Handling phone with country code...")
        try:
            # Look for the country button/flag selector in intl-tel-input
            country_btn = page.locator(".iti__selected-flag, .iti__flag-container button, button[class*='iti']").first
            if country_btn.is_visible(timeout=3000):
                country_btn.click()
                time.sleep(0.5)
                # Search for United States in the dropdown
                search = page.locator("#iti-0__search-input, input[type='search']").first
                if search.is_visible(timeout=2000):
                    search.fill("United States")
                    time.sleep(0.5)
                    # Click the US option
                    try:
                        us_opt = page.locator("li[data-country-code='us'], li:has-text('United States')").first
                        us_opt.click()
                        print("  Phone country: United States selected")
                    except:
                        page.keyboard.press("ArrowDown")
                        page.keyboard.press("Enter")
                        print("  Phone country: selected via keyboard")
                else:
                    # Try clicking US directly
                    try:
                        page.locator("li[data-country-code='us']").first.click()
                        print("  Phone country: US clicked directly")
                    except:
                        page.keyboard.press("Escape")
                        print("  Phone country: could not select, escaped")
                time.sleep(0.3)
        except Exception as e:
            print(f"  Phone country WARN: {e}")

        page.locator("#phone").fill("5307863655")
        print("  Phone: 5307863655")

        # Resume upload
        page.locator("input#resume[type='file']").set_input_files(RESUME)
        print("  Resume: uploaded")
        time.sleep(1)

        # Cover letter upload
        try:
            page.locator("input#cover_letter[type='file']").set_input_files(RESUME)
            print("  Cover Letter: uploaded as file")
        except Exception as e:
            print(f"  Cover letter file WARN: {e}")

        # LinkedIn
        page.locator("#question_33790828002").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        print("  LinkedIn: filled")

        # Location
        page.locator("#question_33790830002").fill("Chico, CA")
        print("  Location: Chico, CA")

        # Accommodations
        page.locator("#question_33790831002").fill("No")
        print("  Accommodations: No")

        # AI service example
        page.locator("#question_33790833002").fill(AI_SERVICE_ANSWER)
        print("  AI service example: filled")

        # ── React Select comboboxes ──
        print("\n[5] Filling Country combobox...")
        fill_react_select(page, "country", "United States")
        time.sleep(0.5)

        print("\n[6] Filling sponsorship combobox...")
        fill_react_select(page, "question_33790829002", "No")
        time.sleep(0.5)

        # Verify sponsorship actually stuck
        spons_val = page.locator("#question_33790829002").input_value()
        print(f"  Sponsorship field value after fill: '{spons_val}'")
        if not spons_val or spons_val == "":
            print("  Sponsorship empty, trying alternative approach...")
            # Try clicking the container div instead
            try:
                # Greenhouse React Select: the actual clickable area might be a parent div
                container = page.locator("#question_33790829002").locator("..")
                container.click()
                time.sleep(0.5)
                page.keyboard.type("No")
                time.sleep(1.0)
                page.keyboard.press("ArrowDown")
                time.sleep(0.3)
                page.keyboard.press("Enter")
                time.sleep(0.3)
                print("  Sponsorship: tried via parent container")
            except Exception as e:
                print(f"  Sponsorship alt WARN: {e}")

        # ── EEO Demographics ──
        print("\n[7] Filling EEO demographics...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)

        fill_react_select(page, "gender", "Male")
        time.sleep(0.3)

        fill_react_select(page, "hispanic_ethnicity", "No")
        time.sleep(0.3)

        fill_react_select(page, "veteran_status", "I am not a protected veteran")
        time.sleep(0.3)

        fill_react_select(page, "disability_status", "I do not want to answer")
        time.sleep(0.3)

        # ── Verify all values using JS ──
        print("\n[8] Verifying field values via JS...")
        values = page.evaluate("""() => {
            const ids = ['first_name','last_name','email','phone','country',
                          'question_33790828002','question_33790829002',
                          'question_33790830002','question_33790831002',
                          'question_33790833002','gender','hispanic_ethnicity',
                          'veteran_status','disability_status'];
            const result = {};
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) result[id] = el.value || '(empty)';
                else result[id] = '(not found)';
            });
            return result;
        }""")
        for k, v in values.items():
            status = "OK" if v != "(empty)" and v != "(not found)" else "EMPTY!"
            print(f"  {status} {k}: {v[:60]}")

        # ── Check the phone country code select ("Select..." error) ──
        print("\n[9] Checking for any 'Select...' dropdown that needs filling...")
        # The error might be from the phone country code intl-tel-input
        # Let's check if there's a visible select with no value
        select_info = page.evaluate("""() => {
            const divs = document.querySelectorAll('[class*="select"], [role="listbox"]');
            const results = [];
            divs.forEach(d => {
                if (d.offsetParent !== null) {
                    results.push({
                        tag: d.tagName,
                        class: d.className.substring(0, 100),
                        text: d.textContent.substring(0, 100),
                        id: d.id || ''
                    });
                }
            });
            // Also check for intl-tel-input selected country
            const iti = document.querySelector('.iti__selected-country-primary, .iti__selected-flag');
            if (iti) {
                results.push({tag: 'ITI', class: iti.className, text: iti.textContent, id: 'iti-country', title: iti.getAttribute('title') || ''});
            }
            return results;
        }""")
        for si in select_info[:10]:
            print(f"  Select-like: tag={si['tag']} id={si.get('id','')} text='{si['text'][:50]}'")

        # ── Screenshot before submit ──
        print("\n[10] Taking pre-submit screenshots...")
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "censys_v3_before_top.png"), full_page=False)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "censys_v3_before_bottom.png"), full_page=False)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "censys_v3_before_full.png"), full_page=True)
        print("  Screenshots saved!")

        # ── Submit ──
        print("\n[11] Submitting application...")
        submit_btn = page.locator("button[type='submit'], input[type='submit']").first
        submit_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit_btn.click()
        print("  Clicked submit!")

        # Wait and screenshot
        print("\n[12] Waiting for result...")
        time.sleep(6)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "censys_v3_after_submit.png"), full_page=True)

        current_url = page.url
        print(f"  Current URL: {current_url}")

        page_text = page.text_content("body") or ""
        page_lower = page_text.lower()

        if "thank" in page_lower and ("application" in page_lower or "submitted" in page_lower):
            print("\n  SUCCESS! Application submitted.")
        elif current_url != URL:
            print(f"\n  URL changed - likely submitted successfully.")
        else:
            print("\n  Submission may have failed. Checking errors...")
            errors = page.locator(".field-error, .error-message, [class*='error']").all()
            for err in errors:
                try:
                    if err.is_visible(timeout=500):
                        txt = err.text_content().strip()
                        if txt:
                            print(f"  ERROR: {txt[:100]}")
                except:
                    pass

            # Take a detailed screenshot of errors
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "censys_v3_errors.png"), full_page=True)

        time.sleep(2)
        browser.close()
        print("\nDone!")


if __name__ == "__main__":
    main()
