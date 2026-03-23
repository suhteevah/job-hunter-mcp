"""
Greenhouse Security Code Retry — Re-applies and enters verification codes in real-time.
Targets jobs with status='needs_code'. Fetches codes from Gmail IMAP in the same session.

Run: .venv\Scripts\python.exe greenhouse_code_retry.py [--limit N] [--delay N]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import email as email_lib
import imaplib
import json
import os
import re
import sqlite3
import time
import traceback
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
LOG_PATH = r"J:\job-hunter-mcp\code_retry_log.txt"

GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "yzpn qern vrax fvta")

APPLICANT = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
}

KNOWN_BOARDS = {
    "reddit": "reddit", "gitlab": "gitlab", "chainguard": "chainguard",
    "clickhouse": "clickhouse", "regscale": "regscale", "tailscale": "tailscale",
    "anthropic": "anthropic", "twilio": "twilio", "discord": "discord",
    "stripe": "stripe", "databricks": "databricks", "samsara": "samsara",
    "coinbase": "coinbase", "cloudflare": "cloudflare", "figma": "figma",
    "notion": "notion", "plaid": "plaid", "grafana labs": "grafanalabs",
    "grafana": "grafanalabs",
}


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


def generate_cover_letter(company: str, title: str) -> str:
    tl = title.lower()
    if any(kw in tl for kw in ["ai", "ml", "machine learning", "data scientist", "llm", "nlp", "genai"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years of software engineering "
            f"experience, I have built production AI/ML systems including LLM-powered applications, "
            f"RAG pipelines, autonomous agents, and ML inference infrastructure. I deployed a weather "
            f"prediction trading bot achieving 20x returns and built distributed AI inference fleets. "
            f"I've authored 10+ production MCP servers and a 27K-line Rust browser automation framework. "
            f"My expertise in Python, FastAPI, vector databases, and cloud infrastructure makes me "
            f"a strong fit for {company}'s engineering team."
        )
    if any(kw in tl for kw in ["infrastructure", "platform", "sre", "devops", "cloud", "systems"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years building scalable "
            f"infrastructure and distributed systems, I bring deep expertise in CI/CD automation, "
            f"container orchestration, and production reliability. I've built GPU inference clusters "
            f"and cloud infrastructure. Strong systems thinking for {company}'s team."
        )
    return (
        f"I am excited about the {title} role at {company}. With 10 years spanning AI/ML systems, "
        f"cloud infrastructure, full-stack development, and industrial automation, I bring a versatile "
        f"skillset and proven track record shipping production systems at scale."
    )


def answer_for_label(label: str, company: str, title: str) -> str:
    ll = label.lower()
    if "linkedin" in ll: return APPLICANT["linkedin"]
    if "github" in ll or "portfolio" in ll or "website" in ll: return APPLICANT["github"]
    if "salary" in ll or "compensation" in ll: return "$150,000 USD"
    if "location" in ll or "city" in ll or "where" in ll: return APPLICANT["location"]
    if "year" in ll and "experience" in ll: return "10"
    if "how did you" in ll and ("find" in ll or "hear" in ll): return "Job board"
    if "current" in ll and "company" in ll: return "Self-employed / Freelance"
    if "cover" in ll or "additional" in ll or "why" in ll: return generate_cover_letter(company, title)
    if "tell us" in ll or "about your" in ll or "background" in ll: return generate_cover_letter(company, title)
    if "notice" in ll or "start date" in ll or "available" in ll: return "Immediately"
    if "country" in ll: return "United States"
    if "pronoun" in ll: return "he/him"
    if "address" in ll: return "Chico, CA"
    return ""


def pick_select_value(label: str, options: list) -> str:
    ll = label.lower()
    if "authorized" in ll or "authorization" in ll or "lawfully" in ll or "eligible" in ll:
        for opt in options:
            if "yes" in opt.lower() or "authorized" in opt.lower() or "do not require" in opt.lower():
                return opt
    if "sponsor" in ll or "visa" in ll:
        for opt in options:
            ol = opt.lower()
            if ol == "no" or "will not" in ol or "do not" in ol or "not require" in ol:
                return opt
    if any(kw in ll for kw in ["agree", "privacy", "consent", "acknowledge"]):
        for opt in options:
            if any(x in opt.lower() for x in ["agree", "yes", "i agree"]):
                return opt
    if any(kw in ll for kw in ["gender", "race", "veteran", "disability", "ethnicity"]):
        for opt in options:
            if "decline" in opt.lower() or "prefer not" in opt.lower():
                return opt
        return options[-1] if options else ""
    if any(kw in ll for kw in ["how did you hear", "where did you"]):
        for opt in options:
            if any(x in opt.lower() for x in ["job board", "website", "online", "other"]):
                return opt
    return options[0] if options else ""


def snapshot_known_codes(company: str) -> int:
    """Get current inbox message count BEFORE form submit."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        result, data = mail.select("inbox")
        count = int(data[0]) if result == "OK" else 0
        mail.logout()
        return count
    except Exception:
        return 0


def fetch_security_code_imap(company: str, max_wait_seconds: int = 60, known_ids: int = 0) -> str:
    """Fetch NEW security code by checking messages AFTER the known count.
    Uses direct sequence-number fetch — no IMAP search needed."""
    baseline_count = known_ids  # This is actually the message count before submit
    log(f"    Polling Gmail for {company} code (max {max_wait_seconds}s, baseline={baseline_count})...")
    company_lower = company.lower()

    attempts = max_wait_seconds // 5

    for attempt in range(attempts):
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            result, data = mail.select("inbox")
            current_count = int(data[0]) if result == "OK" else 0

            if current_count > baseline_count:
                # New messages arrived! Check them
                new_start = baseline_count + 1
                fetch_range = f"{new_start}:{current_count}"
                log(f"    {current_count - baseline_count} new msgs (fetching {fetch_range})")

                status2, msg_data = mail.fetch(fetch_range, "(RFC822)")
                if status2 == "OK":
                    for i in range(0, len(msg_data)):
                        item = msg_data[i]
                        if isinstance(item, tuple) and len(item) == 2:
                            raw = item[1]
                            if isinstance(raw, bytes) and len(raw) > 500:
                                msg = email_lib.message_from_bytes(raw)
                                subject = msg.get("Subject", "")

                                if "security code" in subject.lower() and company_lower in subject.lower():
                                    # Extract code from HTML or plain text
                                    body = ""
                                    for part in msg.walk():
                                        ct = part.get_content_type()
                                        if ct in ("text/html", "text/plain"):
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                body = payload.decode("utf-8", errors="replace")
                                                break

                                    # Try multiple patterns
                                    for pattern in [
                                        r'<h1>([A-Za-z0-9]{6,12})</h1>',
                                        r'application:\s*([A-Za-z0-9]{6,12})',
                                        r'code[^A-Za-z0-9]*([A-Za-z0-9]{6,12})',
                                    ]:
                                        code_match = re.search(pattern, body)
                                        if code_match:
                                            code = code_match.group(1)
                                            log(f"    Got code: {code} (attempt {attempt+1})")
                                            mail.logout()
                                            return code

            mail.logout()
        except Exception as e:
            log(f"    IMAP poll error: {e}")

        if attempt < attempts - 1:
            time.sleep(5)

    log(f"    No code found after {max_wait_seconds}s")
    return ""


def extract_board_and_id(url: str, company: str):
    m = re.search(r'job-boards\.(?:eu\.)?greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m: return m.group(1), m.group(2)
    m = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m: return m.group(1), m.group(2)
    m = re.search(r'gh_jid=(\d+)', url)
    if m:
        job_id = m.group(1)
        cl = company.lower().strip()
        board = KNOWN_BOARDS.get(cl, cl.replace(" ", "").replace(".", ""))
        return board, job_id
    return None, None


def fill_and_submit(page, board: str, job_id: str, company: str, title: str) -> dict:
    """Fill Greenhouse form, submit, handle security code in real-time."""
    import requests

    form_url = f"https://boards.greenhouse.io/{board}/jobs/{job_id}"

    try:
        page.goto(form_url, wait_until="networkidle", timeout=30000)
    except PWTimeout:
        try:
            page.goto(form_url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            return {"success": False, "error": f"Page load timeout: {e}"}

    try:
        page.wait_for_selector("#application-form", timeout=15000)
    except PWTimeout:
        text = page.text_content("body") or ""
        if "not found" in text.lower() or "no longer" in text.lower():
            return {"success": False, "error": "Job no longer available"}
        return {"success": False, "error": "Form did not render"}

    time.sleep(1.5)

    cover_letter = generate_cover_letter(company, title)

    # Fill standard fields
    for fid, val in {"first_name": APPLICANT["first_name"], "last_name": APPLICANT["last_name"], "email": APPLICANT["email"]}.items():
        try:
            el = page.query_selector(f"#{fid}")
            if el and el.is_visible(): el.fill(val)
        except Exception: pass

    try:
        phone_el = page.query_selector("#phone, input[type='tel']")
        if phone_el and phone_el.is_visible(): phone_el.fill(APPLICANT["phone"])
    except Exception: pass

    # Country — React Select dropdown
    try:
        country_el = page.query_selector("#country")
        if country_el and country_el.is_visible():
            country_el.click(); time.sleep(0.3)
            country_el.fill("United States"); time.sleep(0.5)
            us_option = page.query_selector("[class*='option']:has-text('United States')")
            if us_option: us_option.click(); log(f"    Country = United States")
            else: page.keyboard.press("Enter")
            time.sleep(0.3)
    except Exception: pass

    # Location
    try:
        loc_el = page.query_selector("#candidate-location")
        if loc_el and loc_el.is_visible():
            loc_el.click(); time.sleep(0.2)
            loc_el.fill("Chico"); time.sleep(1.0)
            suggestion = page.query_selector("li:has-text('Chico'), [class*='option']:has-text('Chico')")
            if suggestion: suggestion.click()
            else: loc_el.fill(APPLICANT["location"]); page.keyboard.press("Escape")
    except Exception: pass

    # Resume
    try:
        resume_input = page.query_selector("#resume, input[type='file']")
        if resume_input and os.path.exists(RESUME_PATH):
            resume_input.set_input_files(RESUME_PATH)
            log(f"    Uploaded resume"); time.sleep(1)
    except Exception as e:
        log(f"    Resume issue: {e}")

    # Cover letter file
    try:
        cl_file = page.query_selector("#cover_letter[type='file']")
        if cl_file:
            cl_path = os.path.join(os.environ.get("TEMP", "/tmp"), "cover_letter.txt")
            with open(cl_path, "w", encoding="utf-8") as f: f.write(cover_letter)
            cl_file.set_input_files(cl_path)
    except Exception: pass

    # Custom questions via API
    try:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?questions=true"
        api_resp = requests.get(api_url, timeout=8)
        questions = api_resp.json().get("questions", []) if api_resp.status_code == 200 else []
    except Exception:
        questions = []

    def fill_react_select(element_id, search_terms):
        try:
            el = page.query_selector(f"#{element_id}")
            if not el or not el.is_visible(): return False
            el.click(); time.sleep(0.4)
            for term in search_terms:
                el.fill(term); time.sleep(0.5)
                option = page.query_selector("[class*='option']")
                if option and option.is_visible():
                    option.click(); time.sleep(0.3); return True
            page.keyboard.press("Escape"); return False
        except Exception: return False

    for q in questions:
        q_label = q.get("label", "")
        fields = q.get("fields", [])
        for field in fields:
            fname = field.get("name", "")
            ftype = field.get("type", "")
            fvalues = field.get("values", [])
            if fname in ("first_name", "last_name", "email", "phone", "resume", "resume_text", "cover_letter", "cover_letter_text"):
                continue
            if ftype in ("input_text", "textarea", "input_hidden"):
                answer = answer_for_label(q_label, company, title)
                if not answer and q.get("required"): answer = "N/A"
                if answer:
                    try:
                        el = page.query_selector(f"#{fname}")
                        if el and el.is_visible():
                            el.fill(answer)
                            log(f"    Q: {q_label[:35]} = {answer[:35]}")
                    except Exception: pass
            elif ftype in ("multi_value_single_select", "multi_value_multi_select"):
                if not fvalues: continue
                opt_labels = [v.get("label", "") for v in fvalues]
                choice = pick_select_value(q_label, opt_labels)
                if choice:
                    fill_react_select(fname, [choice, choice[:15]])

    # EEOC selects — scan ALL React Select dropdowns on the page
    try:
        unfilled = page.evaluate('''() => {
            const form = document.querySelector('#application-form');
            if (!form) return [];
            const results = [];
            // Find all div-based select components (React Select)
            const selectContainers = form.querySelectorAll('[class*="select__control"], [class*="Select__control"], [class*="select-container"]');
            selectContainers.forEach(container => {
                const parent = container.closest('.application--field, [class*="field"], .field');
                if (!parent) return;
                const input = parent.querySelector('input[id]');
                const label = parent.querySelector('label, legend, [class*="label"]');
                if (input && input.id) {
                    results.push({id: input.id, label: label ? label.textContent.trim().substring(0, 100) : '', hasValue: !!input.value});
                }
            });
            // Also find by looking at empty text inputs inside select-like parents
            form.querySelectorAll('input[type="text"], input[type="hidden"]').forEach(inp => {
                if (!inp.id) return;
                const parent = inp.closest('.application--field, [class*="field"]');
                if (!parent) return;
                const hasSelect = parent.querySelector('[class*="select"], [class*="Select"]');
                const label = parent.querySelector('label, legend, [class*="label"]');
                if (hasSelect && !inp.value) {
                    const exists = results.find(r => r.id === inp.id);
                    if (!exists) {
                        results.push({id: inp.id, label: label ? label.textContent.trim().substring(0, 100) : '', hasValue: false});
                    }
                }
            });
            return results;
        }''')
        for sel in unfilled:
            sid = sel["id"]
            if sel.get("hasValue"): continue
            slabel = sel.get("label", "").lower()
            if sid in ("first_name", "last_name", "email", "phone", "candidate-location", "country"): continue
            if any(kw in slabel for kw in ["gender", "sex", "identity"]):
                terms = ["Decline", "Prefer not", "I don't wish"]
            elif any(kw in slabel for kw in ["hispanic", "ethnicity", "race"]):
                terms = ["Decline", "Prefer not", "Two or More"]
            elif any(kw in slabel for kw in ["veteran"]):
                terms = ["prefer not", "not a protected", "Decline"]
            elif any(kw in slabel for kw in ["disability"]):
                terms = ["prefer not", "do not wish", "Decline"]
            elif any(kw in slabel for kw in ["how did you hear", "where did you", "source"]):
                terms = ["Job Board", "Website", "Online", "Internet", "Other"]
            elif any(kw in slabel for kw in ["acknowledge", "agree", "consent", "privacy"]):
                terms = ["I agree", "Yes", "Acknowledge"]
            elif any(kw in slabel for kw in ["education", "degree"]):
                terms = ["Associate", "Some College", "Bachelor"]
            else:
                terms = ["Decline", "Prefer not", "N/A", "Other"]
            if fill_react_select(sid, terms):
                log(f"    EEOC: {slabel[:35]} = {terms[0]}")
            else:
                # Fallback: try clicking and selecting first visible option
                try:
                    el = page.query_selector(f"#{sid}")
                    if el:
                        el.click(); time.sleep(0.5)
                        first_opt = page.query_selector("[class*='option']")
                        if first_opt and first_opt.is_visible():
                            first_opt.click()
                            log(f"    EEOC fallback: {slabel[:30]} = first option")
                        else:
                            page.keyboard.press("Escape")
                except Exception: pass
    except Exception as e:
        log(f"    EEOC handler error: {e}")

    # Explicit EEOC fields — use JavaScript to find and fill ALL unfilled React Selects
    try:
        eeoc_result = page.evaluate('''() => {
            const results = [];
            // Find ALL elements with "select" in class that contain an input
            document.querySelectorAll('[class*="select__control"], [class*="Select-control"], [role="combobox"]').forEach(ctrl => {
                const wrapper = ctrl.closest('[class*="field"], [class*="Field"], .application--field, div[id]');
                if (!wrapper) return;
                const input = wrapper.querySelector('input');
                const label = wrapper.querySelector('label, legend, [class*="label"], [class*="Label"]');
                const labelText = label ? label.textContent.trim() : '';
                // Check if this select has a value already
                const singleValue = wrapper.querySelector('[class*="single-value"], [class*="singleValue"]');
                const hasValue = singleValue && singleValue.textContent.trim().length > 0;
                if (!hasValue && input) {
                    results.push({
                        inputId: input.id || '',
                        label: labelText.substring(0, 100),
                        wrapperClass: wrapper.className || '',
                    });
                }
            });
            return results;
        }''')
        log(f"    Found {len(eeoc_result)} unfilled React Selects")
        for sel in eeoc_result:
            sid = sel.get("inputId", "")
            slabel = sel.get("label", "").lower()
            if sid in ("first_name", "last_name", "email", "phone", "candidate-location", "country"):
                continue

            if any(kw in slabel for kw in ["gender", "sex", "identity"]):
                terms = ["Decline", "Prefer not", "I don't wish"]
            elif any(kw in slabel for kw in ["hispanic", "ethnicity", "race"]):
                terms = ["Decline", "Prefer not", "Two or More"]
            elif any(kw in slabel for kw in ["veteran"]):
                terms = ["prefer not", "not a protected", "Decline"]
            elif any(kw in slabel for kw in ["disability"]):
                terms = ["prefer not", "do not wish", "Decline"]
            elif any(kw in slabel for kw in ["how did you hear", "where did you", "source"]):
                terms = ["Job Board", "Website", "Online", "Other"]
            elif any(kw in slabel for kw in ["acknowledge", "agree", "consent"]):
                terms = ["I agree", "Yes"]
            elif any(kw in slabel for kw in ["authorized", "authorization"]):
                terms = ["Yes"]
            elif any(kw in slabel for kw in ["sponsor", "visa"]):
                terms = ["No", "will not"]
            else:
                terms = ["Decline", "Prefer not", "N/A", "Other", "No"]

            filled = False
            if sid:
                filled = fill_react_select(sid, terms)
            if not filled and sid:
                # Try clicking the container div instead of the input
                try:
                    container = page.evaluate(f'''() => {{
                        const inp = document.getElementById("{sid}");
                        if (!inp) return null;
                        const ctrl = inp.closest('[class*="select__control"], [class*="select"]');
                        return ctrl ? true : false;
                    }}''')
                    if container:
                        # Click the input's parent select control
                        page.click(f"#{sid}")
                        time.sleep(0.3)
                        # Type search term
                        page.keyboard.type(terms[0][:10])
                        time.sleep(0.5)
                        opt = page.query_selector("[class*='option']")
                        if opt and opt.is_visible():
                            opt.click()
                            filled = True
                            time.sleep(0.3)
                        else:
                            page.keyboard.press("Escape")
                except Exception:
                    pass
            if not filled and sid:
                # Brute force: click the control, then pick first matching option
                try:
                    ctrl = page.query_selector(f"#{sid}")
                    if not ctrl:
                        # Try finding by label text
                        ctrl = page.evaluate(f'''() => {{
                            const labels = document.querySelectorAll('label, legend');
                            for (const l of labels) {{
                                if (l.textContent.toLowerCase().includes("{slabel[:20]}")) {{
                                    const wrapper = l.closest('[class*="field"]');
                                    if (wrapper) {{
                                        const inp = wrapper.querySelector('input');
                                        return inp ? inp.id : null;
                                    }}
                                }}
                            }}
                            return null;
                        }}''')
                        if ctrl:
                            filled = fill_react_select(ctrl, terms)

                    if not filled and ctrl:
                        page.click(f"#{sid}" if isinstance(sid, str) and sid else f"#{ctrl}")
                        time.sleep(0.5)
                        for term in terms:
                            opt = page.query_selector(f"[class*='option']:has-text('{term}')")
                            if opt and opt.is_visible():
                                opt.click()
                                filled = True
                                break
                        if not filled:
                            first = page.query_selector("[class*='option']")
                            if first and first.is_visible():
                                first.click()
                                filled = True
                            else:
                                page.keyboard.press("Escape")
                except Exception:
                    pass

            if filled:
                log(f"    EEOC: {slabel[:35]} = {terms[0]}")
            else:
                log(f"    EEOC MISS: {slabel[:35]} (id={sid})")
    except Exception as e:
        log(f"    EEOC handler error: {e}")

    # Education
    try:
        school = page.query_selector("#school--0")
        if school and school.is_visible(): school.fill("Butte College")
    except Exception: pass

    time.sleep(0.5)

    # Snapshot existing security codes BEFORE submit so we can detect new ones
    known_code_ids = snapshot_known_codes(company)

    # Submit
    try:
        submit_btn = page.query_selector('button[type="submit"], input[type="submit"]')
        if not submit_btn or not submit_btn.is_visible():
            submit_btn = page.query_selector('button:has-text("Submit")')
        if submit_btn and submit_btn.is_visible():
            submit_btn.scroll_into_view_if_needed()
            time.sleep(0.3)
            submit_btn.click()
            log(f"    Clicked submit")
        else:
            return {"success": False, "error": "No submit button"}
    except Exception as e:
        return {"success": False, "error": f"Submit failed: {e}"}

    # Wait for response
    time.sleep(4)

    page_text = (page.text_content("body") or "").lower()

    # Check for immediate success
    if any(x in page_text for x in ["thank you for applying", "application has been received", "successfully submitted", "thanks for your interest"]):
        return {"success": True, "msg": "Direct confirmation"}

    if "already applied" in page_text or "already submitted" in page_text:
        return {"success": False, "error": "Already applied", "already": True}

    # SECURITY CODE HANDLING — the main event
    if "security code" in page_text or "verification code" in page_text:
        log(f"    Security code requested — fetching from Gmail (waiting up to 45s)...")

        # Poll Gmail for the code — 90s to account for Gmail IMAP index lag
        code = fetch_security_code_imap(company, max_wait_seconds=90, known_ids=known_code_ids)

        if code:
            log(f"    Entering code: {code}")

            # Use JavaScript to find and fill the security code input + click submit
            js_result = page.evaluate(f'''() => {{
                // Find the security code input
                const inputs = document.querySelectorAll('input[type="text"]');
                let codeInput = null;
                for (const inp of inputs) {{
                    const name = (inp.name || '').toLowerCase();
                    const id = (inp.id || '').toLowerCase();
                    const placeholder = (inp.placeholder || '').toLowerCase();
                    const label = inp.closest('label, .field, [class*="field"]');
                    const labelText = label ? label.textContent.toLowerCase() : '';
                    if (name.includes('security') || name.includes('code') || name.includes('token') ||
                        id.includes('security') || id.includes('code') ||
                        placeholder.includes('code') || labelText.includes('security code')) {{
                        codeInput = inp;
                        break;
                    }}
                }}
                // Fallback: look for any visible empty text input
                if (!codeInput) {{
                    for (const inp of inputs) {{
                        if (inp.offsetParent !== null && !inp.value && inp.type === 'text') {{
                            codeInput = inp;
                            break;
                        }}
                    }}
                }}
                if (!codeInput) return 'NO_INPUT';

                // Set value using React-compatible method
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(codeInput, '{code}');
                codeInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                codeInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

                // Find and enable the submit/verify button
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {{
                    const text = btn.textContent.toLowerCase();
                    if (text.includes('verify') || text.includes('submit') || text.includes('confirm')) {{
                        btn.disabled = false;
                        btn.removeAttribute('disabled');
                        setTimeout(() => btn.click(), 300);
                        return 'CLICKED:' + text.trim().substring(0, 30);
                    }}
                }}
                // Try submit button by type
                const submitBtn = document.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {{
                    submitBtn.disabled = false;
                    submitBtn.removeAttribute('disabled');
                    setTimeout(() => submitBtn.click(), 300);
                    return 'CLICKED:submit';
                }}
                return 'NO_BUTTON';
            }}''')

            log(f"    JS result: {js_result}")

            if js_result and js_result.startswith("CLICKED"):
                time.sleep(5)
                page_text2 = (page.text_content("body") or "").lower()
                if any(x in page_text2 for x in ["thank you", "submitted", "received", "confirmation", "successfully"]):
                    return {"success": True, "msg": f"Confirmed after code {code}"}
                if "security code" in page_text2 or "invalid" in page_text2:
                    return {"success": False, "error": f"Code {code} rejected"}
                # Check URL change
                if "confirmation" in page.url.lower() or "thank" in page.url.lower():
                    return {"success": True, "msg": f"Confirmed (URL) after code {code}"}
                return {"success": True, "msg": f"Code {code} entered + submitted"}
            elif js_result == "NO_INPUT":
                return {"success": False, "error": "Could not find code input field"}
            else:
                return {"success": False, "error": f"Could not submit code: {js_result}"}
        else:
            return {"success": False, "error": "NEEDS_CODE_TIMEOUT", "needs_code": True}

    # Check for validation errors
    errors = page.query_selector_all('[class*="error"], [role="alert"]')
    err_texts = [e.text_content().strip() for e in errors if e.text_content().strip() and len(e.text_content().strip()) < 200]
    if err_texts:
        return {"success": False, "error": f"Validation: {'; '.join(err_texts[:3])[:150]}"}

    return {"success": False, "error": "No confirmation after submit"}


def get_needs_code_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score, source
        FROM jobs WHERE status = 'needs_code'
        ORDER BY fit_score DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job(job_id, status, cover_letter=None):
    conn = sqlite3.connect(DB_PATH)
    if cover_letter:
        conn.execute("UPDATE jobs SET status=?, applied_date=?, cover_letter=? WHERE id=?",
                      (status, datetime.now(timezone.utc).isoformat(), cover_letter, job_id))
    else:
        conn.execute("UPDATE jobs SET status=?, applied_date=? WHERE id=?",
                      (status, datetime.now(timezone.utc).isoformat(), job_id))
    conn.commit()
    conn.close()


def main(limit=0, delay=5.0):
    start = datetime.now(timezone.utc)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"=== SECURITY CODE RETRY {start.isoformat()} ===\n")

    jobs = get_needs_code_jobs()
    log(f"Found {len(jobs)} jobs needing security codes")

    if limit > 0:
        jobs = jobs[:limit]

    successes, failures, still_needs = [], [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}, locale="en-US",
        )
        page = context.new_page()

        for i, job in enumerate(jobs):
            board, gh_id = extract_board_and_id(job["url"], job["company"])
            if not board or not gh_id:
                log(f"[{i+1}] SKIP (no board) {job['company']} — {job['title'][:40]}")
                failures.append(job)
                continue

            log(f"[{i+1}/{len(jobs)}] {job['company']} — {job['title'][:45]} (board={board})")

            try:
                result = fill_and_submit(page, board, gh_id, job["company"], job["title"])

                if result.get("success"):
                    log(f"  >>> SUCCESS: {result.get('msg', '')} <<<")
                    successes.append(job)
                    cl = generate_cover_letter(job["company"], job["title"])
                    update_job(job["id"], "applied", cover_letter=cl)
                elif result.get("needs_code"):
                    log(f"  Still needs code (timeout)")
                    still_needs.append(job)
                elif result.get("already"):
                    log(f"  Already applied")
                    update_job(job["id"], "applied")
                    successes.append(job)
                else:
                    log(f"  FAILED: {result.get('error', '')[:100]}")
                    failures.append(job)
                    update_job(job["id"], "apply_failed")
            except Exception as e:
                log(f"  EXCEPTION: {e}")
                failures.append(job)
                try: page.close()
                except: pass
                page = context.new_page()

            time.sleep(delay)

        browser.close()

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log(f"\n{'='*60}")
    log(f"CODE RETRY DONE: {len(successes)} success, {len(failures)} fail, {len(still_needs)} still need code")
    log(f"Duration: {elapsed/60:.1f}min")
    log(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=5.0)
    args = parser.parse_args()
    main(limit=args.limit, delay=args.delay)
