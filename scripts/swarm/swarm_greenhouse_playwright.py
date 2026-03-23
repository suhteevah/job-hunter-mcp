"""
Greenhouse Playwright Swarm — Overnight Autonomous Applicant
=============================================================
Uses Greenhouse API to pre-fetch questions, Playwright to fill + submit forms.
Pulls ALL viable Greenhouse jobs from DB, applies in sequence with smart delays.

Run: .venv\Scripts\python.exe swarm_greenhouse_playwright.py [--limit N] [--resume-from N]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import sqlite3
import os
import re
import time
import traceback
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
PENDING_CODES_PATH = r"J:\job-hunter-mcp\pending_security_codes.json"

# Gmail IMAP for security code fetching (set GMAIL_APP_PASSWORD env var)
GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
LOG_PATH = r"J:\job-hunter-mcp\swarm_pw_log.txt"
RESULTS_PATH = r"J:\job-hunter-mcp\swarm_pw_results.md"

APPLICANT = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
}

# Board token lookup for wrapped URLs
KNOWN_BOARDS = {
    "samsara": "samsara", "databricks": "databricks", "stripe": "stripe",
    "datadog": "datadog", "coreweave": "coreweave", "cockroach labs": "cockroachlabs",
    "airbnb": "airbnb", "elastic": "elastic", "brex": "brex", "mongodb": "mongodb",
    "instacart": "instacart", "coinbase": "coinbase", "cloudflare": "cloudflare",
    "nuro": "nuro", "reddit": "reddit", "anthropic": "anthropic", "scale ai": "scaleai",
    "airtable": "airtable", "gitlab": "gitlab", "gusto": "gusto", "twilio": "twilio",
    "assemblyai": "assemblyai", "clickhouse": "clickhouse", "chainguard": "chainguard",
    "planetscale": "planetscale", "ziprecruiter": "ziprecruiter", "within": "agencywithin",
    "remote people": "remotepeople", "figma": "figma", "notion": "notion", "plaid": "plaid",
    "ramp": "ramp", "anyscale": "anyscale", "modal": "modal", "vercel": "vercel",
    "hashicorp": "hashicorp", "grafana labs": "grafanalabs", "snap": "snap",
    "pinterest": "pinterest", "lyft": "lyft", "doordash": "doordash",
    "robinhood": "robinhood", "discord": "discord", "square": "square",
    "confluent": "confluent", "temporal": "temporal", "tailscale": "tailscale",
    "supabase": "supabase", "retool": "retool", "linear": "linear", "replit": "replit",
    "sourcegraph": "sourcegraph", "mux": "mux", "livekit": "livekit",
    "weights & biases": "wandb", "wandb": "wandb", "hugging face": "huggingface",
    "together ai": "togetherai", "fireworks ai": "fireworksai", "replicate": "replicate",
    "cursor": "anysphere", "perplexity": "perplexity", "cohere": "cohere",
    "openai": "openai", "mistral": "mistral", "khan academy": "khanacademy",
    "censys": "censys", "regscale": "regscale", "grafana": "grafanalabs",
    "onboard meetings": "onboardmeetings", "pathward": "pathward",
}


def fetch_security_code_imap(company: str, max_wait: int = 15) -> str:
    """Fetch Greenhouse security code from Gmail via IMAP."""
    if not GMAIL_APP_PASSWORD:
        return ""
    try:
        import imaplib
        import email as email_lib
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        # Search for recent security code email from greenhouse for this company
        search_query = f'(FROM "greenhouse" SUBJECT "security code" SUBJECT "{company}" UNSEEN)'
        for attempt in range(max_wait // 3):
            status, data = mail.search(None, search_query)
            if status == "OK" and data[0]:
                msg_ids = data[0].split()
                # Get the latest one
                latest_id = msg_ids[-1]
                status, msg_data = mail.fetch(latest_id, "(RFC822)")
                if status == "OK":
                    msg = email_lib.message_from_bytes(msg_data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                    # Extract code — pattern: "code into the security code field on your application: XXXXXXXX"
                    import re
                    code_match = re.search(r'application:\s*([A-Za-z0-9]{6,12})', body)
                    if code_match:
                        mail.logout()
                        return code_match.group(1)
            time.sleep(3)
        mail.logout()
    except Exception as e:
        log(f"    IMAP error: {e}")
    return ""


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── Cover Letters ───────────────────────────────────────────────────

def generate_cover_letter(company: str, title: str) -> str:
    tl = title.lower()
    if any(kw in tl for kw in ["ai", "ml", "machine learning", "data scientist", "llm", "nlp", "genai"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years of software engineering "
            f"experience, I have built production AI/ML systems including LLM-powered applications, "
            f"RAG pipelines, autonomous agents, and ML inference infrastructure. I deployed a weather "
            f"prediction trading bot achieving 20x returns and built distributed AI inference fleets. "
            f"My expertise in Python, FastAPI, vector databases, and cloud infrastructure makes me "
            f"a strong fit for {company}'s engineering team."
        )
    if any(kw in tl for kw in ["infrastructure", "platform", "sre", "devops", "cloud", "systems"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years building scalable "
            f"infrastructure, distributed systems, and cloud-native platforms, I bring deep expertise "
            f"in CI/CD automation, container orchestration, and production reliability. My experience "
            f"spans industrial automation (ESP32, PID controllers) to cloud infrastructure (AWS, "
            f"Docker, Kubernetes). I bring strong systems thinking to {company}'s team."
        )
    if any(kw in tl for kw in ["full stack", "fullstack", "frontend", "react", "typescript"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years spanning full-stack "
            f"development, I have built production apps using React, TypeScript, Next.js, and Python. "
            f"My recent work includes AI-powered browser automation (27K lines Rust), real-time "
            f"trading interfaces, and developer tooling. I am passionate about building quality "
            f"user experiences backed by robust engineering."
        )
    if any(kw in tl for kw in ["backend", "back-end", "api", "server"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years building production "
            f"backend systems in Python, Rust, TypeScript, and distributed architectures, I have "
            f"built high-performance APIs, data pipelines, and microservices at real-world scale. "
            f"My background spans ML infrastructure, real-time systems, and developer tooling."
        )
    if any(kw in tl for kw in ["security", "appsec"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years including browser security "
            f"research, TLS fingerprinting, and building secure systems from embedded hardware to "
            f"cloud, I bring deep understanding of both offensive and defensive security."
        )
    return (
        f"I am excited about the {title} role at {company}. With 10 years spanning AI/ML systems, "
        f"cloud infrastructure, full-stack development, and industrial automation, I bring a versatile "
        f"skillset and proven track record shipping production systems at scale."
    )


# ─── URL Parsing ─────────────────────────────────────────────────────

def extract_greenhouse_board_and_id(url: str, company: str) -> tuple:
    """Returns (board_token, job_id) or (None, None)."""
    # Direct: job-boards.greenhouse.io/{board}/jobs/{id}
    m = re.search(r'job-boards\.(?:eu\.)?greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)

    # boards.greenhouse.io/{board}/jobs/{id}
    m = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)

    # Wrapped: gh_jid= param
    m = re.search(r'gh_jid=(\d+)', url)
    if m:
        job_id = m.group(1)
        # Check for explicit board in URL
        board_match = re.search(r'[?&]board=([^&]+)', url)
        if board_match:
            return board_match.group(1), job_id
        # Guess from company name
        cl = company.lower().strip()
        if cl in KNOWN_BOARDS:
            return KNOWN_BOARDS[cl], job_id
        # Try company name as board token
        guess = cl.replace(" ", "").replace(".", "").replace(",", "").replace("'", "")
        return guess, job_id

    return None, None


def verify_board_token(board: str, job_id: str) -> bool:
    """Quick check if board token resolves via API."""
    try:
        r = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}",
            timeout=8
        )
        return r.status_code == 200
    except Exception:
        return False


# ─── Smart Question Answering ────────────────────────────────────────

def answer_for_label(label: str, company: str, title: str) -> str:
    """Given a question label, return the best text answer."""
    ll = label.lower()
    if "linkedin" in ll:
        return APPLICANT["linkedin"]
    if "github" in ll or "portfolio" in ll or "website" in ll:
        return APPLICANT["github"]
    if "salary" in ll or "compensation" in ll or "pay" in ll:
        return "$150,000 USD"
    if "location" in ll or "city" in ll or "based" in ll or "where" in ll:
        return APPLICANT["location"]
    if "year" in ll and ("experience" in ll or "ai" in ll or "ml" in ll or "python" in ll or "software" in ll):
        return "10"
    if "preferred" in ll and "name" in ll:
        return APPLICANT["first_name"]
    if "refer" in ll and "name" not in ll:
        return "No"
    if "how did you" in ll and ("find" in ll or "hear" in ll):
        return "Job board"
    if "current" in ll and "company" in ll:
        return "Self-employed / Freelance"
    if any(x in ll for x in ["facebook", "instagram", "twitter", "social media"]):
        return "N/A"
    if "cover" in ll or "additional" in ll or "anything else" in ll:
        return generate_cover_letter(company, title)
    if "why" in ll and ("interest" in ll or "excite" in ll or "join" in ll or "work" in ll or "apply" in ll):
        return generate_cover_letter(company, title)
    if "tell us" in ll or "about your" in ll or "background" in ll or "describe" in ll:
        return generate_cover_letter(company, title)
    if "what excites" in ll or "motivation" in ll or "passion" in ll:
        return generate_cover_letter(company, title)
    if "notice" in ll or "start date" in ll or "available" in ll:
        return "Immediately"
    if "country" in ll:
        return "United States"
    if "state" in ll or "province" in ll:
        return "California"
    if "zip" in ll or "postal" in ll:
        return "95928"
    if "pronoun" in ll:
        return "he/him"
    if "address" in ll:
        return "Chico, CA"
    return ""


def pick_select_value(label: str, options: list) -> str:
    """Pick the best option for a select/radio question."""
    ll = label.lower()

    # Work authorization
    if "authorized" in ll or "authorization" in ll or "lawfully" in ll or "eligible" in ll:
        for opt in options:
            ol = opt.lower()
            if "do not require" in ol or ("authorized" in ol and "do not" in ol):
                return opt
        for opt in options:
            if "yes" in opt.lower() and "not" not in opt.lower():
                return opt

    # Sponsorship — we do NOT require sponsorship (US citizen)
    if "sponsor" in ll or "visa" in ll or "immigration" in ll:
        for opt in options:
            ol = opt.lower()
            if ol == "no" or "will not" in ol or "do not" in ol or "not require" in ol:
                return opt

    # Agree / consent
    if any(kw in ll for kw in ["agree", "privacy", "consent", "acknowledge"]):
        for opt in options:
            if any(x in opt.lower() for x in ["agree", "yes", "i agree"]):
                return opt

    # ML/AI experience
    if any(kw in ll for kw in ["ml", "machine learning", "ai", "deploy", "production", "pipeline"]):
        for opt in options:
            ol = opt.lower()
            if any(x in ol for x in ["yes", "personally", "owned", "production"]):
                return opt
        return options[-1] if options else ""

    # Gender/race/veteran — decline
    if any(kw in ll for kw in ["gender", "race", "veteran", "disability", "ethnicity"]):
        for opt in options:
            if "decline" in opt.lower() or "prefer not" in opt.lower():
                return opt
        return options[-1] if options else ""

    # Remote / hybrid / office
    if any(kw in ll for kw in ["remote", "hybrid", "office", "on-site", "relocation"]):
        for opt in options:
            if "yes" in opt.lower():
                return opt

    # Default: first option
    return options[0] if options else ""


# ─── Playwright Form Filler ─────────────────────────────────────────

def apply_with_playwright(page, board: str, job_id: str, company: str, title: str) -> dict:
    """Fill and submit a Greenhouse form using Playwright.

    Greenhouse React SPA renders inputs with id= attributes:
      first_name, last_name, email, phone (tel), candidate-location,
      resume (file), cover_letter (file), question_XXXXX, school--N,
      degree--N, discipline--N, gender, hispanic_ethnicity, veteran_status,
      disability_status. Custom dropdowns use React Select (div-based).
    """
    form_url = f"https://boards.greenhouse.io/{board}/jobs/{job_id}"

    try:
        page.goto(form_url, wait_until="networkidle", timeout=30000)
    except PWTimeout:
        try:
            page.goto(form_url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            return {"success": False, "error": f"Page load timeout: {e}"}

    # Wait for form to render
    try:
        page.wait_for_selector("#application-form", timeout=15000)
    except PWTimeout:
        text = page.text_content("body") or ""
        if "not found" in text.lower() or "no longer" in text.lower():
            return {"success": False, "error": "Job no longer available"}
        return {"success": False, "error": "Form did not render in 15s"}

    time.sleep(1.5)  # Let React fully hydrate

    cover_letter = generate_cover_letter(company, title)

    # ── Step 1: Fill standard fields by id ───────────────────────────
    id_fills = {
        "first_name": APPLICANT["first_name"],
        "last_name": APPLICANT["last_name"],
        "email": APPLICANT["email"],
    }
    for field_id, value in id_fills.items():
        try:
            el = page.query_selector(f"#{field_id}")
            if el and el.is_visible():
                el.fill(value)
        except Exception:
            pass

    # Phone is input[type=tel]
    try:
        phone_el = page.query_selector("#phone, input[type='tel']")
        if phone_el and phone_el.is_visible():
            phone_el.fill(APPLICANT["phone"])
    except Exception:
        pass

    # Country — React Select dropdown, click and select "United States"
    try:
        country_el = page.query_selector("#country")
        if country_el and country_el.is_visible():
            country_el.click()
            time.sleep(0.3)
            country_el.fill("United States")
            time.sleep(0.5)
            us_option = page.query_selector("[class*='option']:has-text('United States')")
            if us_option:
                us_option.click()
                log(f"    Country = United States")
            else:
                page.keyboard.press("Enter")
            time.sleep(0.3)
    except Exception:
        pass

    # Location — has autocomplete, type and select from dropdown
    try:
        loc_el = page.query_selector("#candidate-location")
        if loc_el and loc_el.is_visible():
            loc_el.click()
            time.sleep(0.2)
            loc_el.fill("Chico")
            time.sleep(1.0)
            # Try to click a matching autocomplete suggestion
            suggestion = page.query_selector(
                "[class*='option']:has-text('Chico'), "
                "[class*='suggestion']:has-text('Chico'), "
                "[class*='autocomplete'] [class*='item']:has-text('Chico'), "
                "li:has-text('Chico, CA'), li:has-text('Chico')"
            )
            if suggestion:
                suggestion.click()
                log(f"    Location = Chico (autocomplete)")
            else:
                # No autocomplete, just type full value and dismiss
                loc_el.fill(APPLICANT["location"])
                time.sleep(0.3)
                page.keyboard.press("Escape")
                log(f"    Location = {APPLICANT['location']} (typed)")
            time.sleep(0.3)
    except Exception:
        pass

    # ── Step 2: Upload resume (first file input) ─────────────────────
    try:
        resume_input = page.query_selector("#resume, input[type='file']")
        if resume_input and os.path.exists(RESUME_PATH):
            resume_input.set_input_files(RESUME_PATH)
            log(f"    Uploaded resume")
            time.sleep(1)
    except Exception as e:
        log(f"    Resume upload issue: {e}")

    # Upload cover letter as file if there's a second file input
    try:
        cl_file = page.query_selector("#cover_letter[type='file']")
        if cl_file:
            # Write cover letter to temp file
            cl_path = os.path.join(os.environ.get("TEMP", "/tmp"), "cover_letter.txt")
            with open(cl_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            cl_file.set_input_files(cl_path)
            log(f"    Uploaded cover letter file")
    except Exception:
        pass

    # ── Helper: React Select filler ─────────────────────────────────
    def fill_react_select(element_id: str, search_terms: list, fallback_index: int = -1):
        """Fill a React Select dropdown by clicking, typing, and selecting."""
        try:
            el = page.query_selector(f"#{element_id}")
            if not el or not el.is_visible():
                return False
            el.click()
            time.sleep(0.4)
            for term in search_terms:
                el.fill(term)
                time.sleep(0.5)
                option = page.query_selector("[class*='option']")
                if option and option.is_visible():
                    option.click()
                    time.sleep(0.3)
                    return True
            page.keyboard.press("Escape")
            time.sleep(0.2)
            return False
        except Exception:
            return False

    # ── Step 3: Fill custom questions ────────────────────────────────
    # Use the Greenhouse API to get question labels + types
    try:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?questions=true"
        api_resp = requests.get(api_url, timeout=8)
        if api_resp.status_code == 200:
            questions = api_resp.json().get("questions", [])
        else:
            questions = []
    except Exception:
        questions = []

    for q in questions:
        q_label = q.get("label", "")
        q_required = q.get("required", False)
        fields = q.get("fields", [])

        for field in fields:
            fname = field.get("name", "")
            ftype = field.get("type", "")
            fvalues = field.get("values", [])

            # Skip standard fields already handled
            if fname in ("first_name", "last_name", "email", "phone",
                         "resume", "resume_text", "cover_letter", "cover_letter_text"):
                continue

            # Text inputs — fill by question_XXXXX id
            if ftype in ("input_text", "textarea", "input_hidden"):
                answer = answer_for_label(q_label, company, title)
                if not answer and q_required:
                    answer = "N/A"
                if answer:
                    try:
                        el = page.query_selector(f"#{fname}")
                        if el and el.is_visible():
                            el.fill(answer)
                            log(f"    Q: {q_label[:40]} = {answer[:40]}")
                    except Exception:
                        pass
                continue

            # Select/radio — React Select dropdowns (click to open, then pick)
            if ftype in ("multi_value_single_select", "multi_value_multi_select"):
                if not fvalues:
                    continue
                # Find the best answer
                opt_labels = [v.get("label", "") for v in fvalues]
                choice = pick_select_value(q_label, opt_labels)
                if not choice:
                    choice = opt_labels[0] if opt_labels else ""
                if choice:
                    # Use the React Select helper
                    if fill_react_select(fname, [choice, choice[:15]]):
                        log(f"    Q: {q_label[:40]} = {choice[:40]}")
                    else:
                        log(f"    Q: {q_label[:40]} = FAILED to select")
                continue

    # ── Step 4: Handle EEOC React Select dropdowns ────────────────────
    # Find ALL unfilled React Select dropdowns and fill them with "Decline" options
    # These are divs with class containing "select" that have unfilled inputs
    try:
        unfilled_selects = page.evaluate('''() => {
            const form = document.querySelector('#application-form');
            if (!form) return [];
            const results = [];
            // Find all inputs that are empty and part of a select component
            const inputs = form.querySelectorAll('input[type="text"]');
            inputs.forEach(inp => {
                const parent = inp.closest('.application--field, [class*="field"]');
                if (!parent) return;
                const hasSelect = parent.querySelector('[class*="select"]');
                const label = parent.querySelector('label, legend');
                if (hasSelect && !inp.value && inp.id) {
                    results.push({
                        id: inp.id,
                        label: label ? label.textContent.trim().substring(0, 80) : '',
                    });
                }
            });
            return results;
        }''')

        for sel in unfilled_selects:
            sid = sel["id"]
            slabel = sel.get("label", "").lower()

            # Skip fields we already handled (standard + custom questions)
            if sid in ("first_name", "last_name", "email", "phone", "candidate-location", "country"):
                continue

            # Determine best answer based on label
            if any(kw in slabel for kw in ["gender", "sex"]):
                terms = ["Decline", "Prefer not"]
            elif any(kw in slabel for kw in ["hispanic", "latino", "ethnicity", "race"]):
                terms = ["Decline", "Prefer not", "Two"]
            elif any(kw in slabel for kw in ["veteran"]):
                terms = ["prefer not", "not a protected", "Decline"]
            elif any(kw in slabel for kw in ["disability", "handicap"]):
                terms = ["prefer not", "do not wish", "Decline"]
            elif any(kw in slabel for kw in ["how did you hear", "where did you", "how did you find"]):
                terms = ["Job Board", "Website", "Online", "Internet"]
            elif any(kw in slabel for kw in ["acknowledge", "agree", "consent", "privacy"]):
                terms = ["I agree", "Yes", "Acknowledge"]
            elif any(kw in slabel for kw in ["education", "degree"]):
                terms = ["Associate", "Some College", "Bachelor"]
            else:
                # Try first option for unknown selects
                terms = [""]

            if fill_react_select(sid, terms):
                log(f"    Select {sid}: {slabel[:40]} = {terms[0]}")
    except Exception as e:
        log(f"    EEOC/select handler error: {e}")

    # ── Step 5: Education fields (optional, fill if present) ─────────
    try:
        school = page.query_selector("#school--0")
        if school and school.is_visible():
            school.fill("Butte College")
        degree = page.query_selector("#degree--0")
        if degree and degree.is_visible():
            degree.click()
            time.sleep(0.3)
            assoc = page.query_selector("[class*='option']:has-text('Associate')")
            if assoc:
                assoc.click()
            else:
                page.keyboard.press("Escape")
        discipline = page.query_selector("#discipline--0")
        if discipline and discipline.is_visible():
            discipline.fill("Computer Science")
    except Exception:
        pass

    time.sleep(0.5)

    # ── Step 6: Submit ───────────────────────────────────────────────
    try:
        submit_btn = page.query_selector(
            'button[type="submit"], input[type="submit"]'
        )
        if not submit_btn or not submit_btn.is_visible():
            submit_btn = page.query_selector('button:has-text("Submit")')
        if submit_btn and submit_btn.is_visible():
            submit_btn.scroll_into_view_if_needed()
            time.sleep(0.3)
            submit_btn.click()
            log(f"    Clicked submit")
        else:
            return {"success": False, "error": "Submit button not found"}
    except Exception as e:
        return {"success": False, "error": f"Submit click failed: {e}"}

    # ── Step 7: Check result ─────────────────────────────────────────
    time.sleep(4)

    try:
        page_text = page.text_content("body") or ""
        page_url = page.url
        page_text_lower = page_text.lower()

        # SECURITY CODE CHECK — Greenhouse email verification
        if "security code" in page_text_lower or "verification code" in page_text_lower:
            # Try to fetch code via IMAP if credentials available
            code = fetch_security_code_imap(company)
            if code:
                log(f"    Got security code: {code}")
                code_input = page.query_selector(
                    'input[name*="security"], input[id*="security"], '
                    'input[placeholder*="code"], input[type="text"]'
                )
                if code_input and code_input.is_visible():
                    code_input.fill(code)
                    time.sleep(0.5)
                    # Click verify/submit button
                    verify_btn = page.query_selector(
                        'button:has-text("Verify"), button:has-text("Submit"), '
                        'button[type="submit"]'
                    )
                    if verify_btn:
                        verify_btn.click()
                        time.sleep(4)
                        # Re-check for confirmation
                        page_text2 = page.text_content("body") or ""
                        if any(x in page_text2.lower() for x in [
                            "thank you", "application has been", "submitted",
                            "received your application", "confirmation",
                            "we have received", "successfully"
                        ]):
                            return {"success": True, "msg": "Confirmed after security code"}
            # If we couldn't get/enter code, mark as needs_code
            return {"success": False, "error": "NEEDS_SECURITY_CODE", "needs_code": True}

        # Check for actual confirmation
        if any(x in page_text_lower for x in [
            "thank you for applying", "application has been received",
            "we have received your application", "successfully submitted",
            "thanks for your interest", "your application was submitted"
        ]):
            return {"success": True, "msg": "Confirmation detected"}

        if any(x in page_text_lower for x in ["already applied", "already submitted"]):
            return {"success": False, "error": "Already applied", "already": True}

        # Check for validation errors
        errors = page.query_selector_all('[class*="error"], [role="alert"]')
        err_texts = [e.text_content().strip() for e in errors if e.text_content().strip() and len(e.text_content().strip()) < 200]
        if err_texts:
            return {"success": False, "error": f"Validation: {'; '.join(err_texts[:3])[:150]}"}

        # If URL changed to confirmation path
        if "confirmation" in page_url.lower() or "thank" in page_url.lower():
            return {"success": True, "msg": "Redirected to confirmation"}

        # Generic redirect — could be success OR security code page
        # Be conservative: check page content more carefully
        if page_url != form_url and page_url != form_url + "/":
            # Check if we're on a confirmation page (not security code)
            if any(x in page_text_lower for x in ["thank", "received", "submitted", "confirmation"]):
                if "security code" not in page_text_lower:
                    return {"success": True, "msg": f"Confirmed at {page_url[:80]}"}
            # Unknown redirect — might be security code on some companies
            if "security" in page_text_lower or "code" in page_text_lower:
                return {"success": False, "error": "NEEDS_SECURITY_CODE", "needs_code": True}
            return {"success": True, "msg": f"Redirected to {page_url[:80]}"}

        return {"success": False, "error": "No confirmation after submit"}
    except Exception as e:
        return {"success": False, "error": f"Result check: {e}"}


# ─── DB Operations ──────────────────────────────────────────────────

def get_greenhouse_jobs(min_score: float = 60.0) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score, source
        FROM jobs
        WHERE status = 'new'
          AND fit_score >= ?
          AND (source = 'greenhouse' OR url LIKE '%greenhouse%')
        ORDER BY fit_score DESC
    """, (min_score,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_status(job_id: str, status: str, cover_letter: str = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        if cover_letter:
            conn.execute(
                "UPDATE jobs SET status=?, applied_date=?, cover_letter=? WHERE id=?",
                (status, datetime.now(timezone.utc).isoformat(), cover_letter, job_id)
            )
        else:
            conn.execute(
                "UPDATE jobs SET status=?, applied_date=? WHERE id=?",
                (status, datetime.now(timezone.utc).isoformat(), job_id)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"  DB error: {e}")


# ─── Main Swarm ─────────────────────────────────────────────────────

def run_swarm(
    min_score: float = 60.0,
    limit: int = 0,
    resume_from: int = 0,
    delay: float = 3.0,
    headless: bool = True,
):
    start_time = datetime.now(timezone.utc)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"=== GREENHOUSE PLAYWRIGHT SWARM {start_time.isoformat()} ===\n")

    log("=" * 70)
    log("GREENHOUSE PLAYWRIGHT SWARM — Overnight Mode")
    log("=" * 70)

    all_jobs = get_greenhouse_jobs(min_score)
    log(f"Found {len(all_jobs)} Greenhouse jobs (score >= {min_score})")

    # Parse board tokens and filter to submittable
    submittable = []
    no_board = []
    for job in all_jobs:
        board, job_id = extract_greenhouse_board_and_id(job["url"], job["company"])
        if board and job_id:
            submittable.append({**job, "board": board, "gh_job_id": job_id})
        else:
            no_board.append(job)

    log(f"Submittable (have board+id): {len(submittable)}")
    log(f"No board token: {len(no_board)}")

    # Apply resume_from and limit
    batch = submittable[resume_from:]
    if limit > 0:
        batch = batch[:limit]

    log(f"This batch: {len(batch)} jobs (resume_from={resume_from}, limit={limit or 'all'})")
    log(f"Delay between apps: {delay}s")
    log(f"Headless: {headless}")
    log("")

    # Verify a sample of board tokens (first 5 unique)
    verified_boards = set()
    bad_boards = set()
    for job in batch[:50]:
        b = job["board"]
        if b in verified_boards or b in bad_boards:
            continue
        if verify_board_token(b, job["gh_job_id"]):
            verified_boards.add(b)
            log(f"  Board verified: {b}")
        else:
            bad_boards.add(b)
            log(f"  Board FAILED: {b}")
        time.sleep(0.3)

    # Results tracking
    successes = []
    failures = []
    already_applied = []
    needs_code = []  # Jobs that need security code entry

    # Launch Playwright
    log(f"\nLaunching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = context.new_page()

        log(f"Browser ready. Starting applications...\n")

        for i, job in enumerate(batch):
            job_num = i + 1 + resume_from
            board = job["board"]
            gh_id = job["gh_job_id"]

            # Skip bad boards
            if board in bad_boards:
                log(f"[{job_num}] SKIP (bad board={board}) {job['company']} — {job['title'][:50]}")
                failures.append({**job, "error": f"Board token '{board}' not found"})
                continue

            log(f"[{job_num}/{len(batch)+resume_from}] {job['company']} — {job['title'][:50]} (score={job['fit_score']}, board={board})")

            try:
                result = apply_with_playwright(page, board, gh_id, job["company"], job["title"])

                if result.get("success"):
                    log(f"  >>> SUCCESS: {result.get('msg', '')} <<<")
                    successes.append(job)
                    cl = generate_cover_letter(job["company"], job["title"])
                    update_job_status(job["id"], "applied", cover_letter=cl)
                elif result.get("needs_code"):
                    log(f"  NEEDS SECURITY CODE — check Gmail")
                    needs_code.append(job)
                    update_job_status(job["id"], "needs_code")
                elif result.get("already"):
                    log(f"  Already applied")
                    already_applied.append(job)
                    update_job_status(job["id"], "applied")
                else:
                    error = result.get("error", "unknown")
                    log(f"  FAILED: {error[:120]}")
                    failures.append({**job, "error": error})
                    update_job_status(job["id"], "apply_failed")

            except Exception as e:
                tb = traceback.format_exc()
                log(f"  EXCEPTION: {e}")
                log(f"  {tb[:200]}")
                failures.append({**job, "error": str(e)})
                update_job_status(job["id"], "apply_failed")

                # Re-create page if crashed
                try:
                    page.close()
                except Exception:
                    pass
                page = context.new_page()

            # Progress report every 25 apps
            if (i + 1) % 25 == 0:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                rate = (i + 1) / (elapsed / 60) if elapsed > 0 else 0
                log(f"\n--- Progress: {i+1}/{len(batch)} | OK={len(successes)} FAIL={len(failures)} DUP={len(already_applied)} | {rate:.1f}/min ---\n")

            # Delay
            if i < len(batch) - 1:
                time.sleep(delay)

        browser.close()

    # ── Final Report ─────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Save pending security codes to JSON for later processing
    if needs_code:
        import json as _json
        with open(PENDING_CODES_PATH, "w", encoding="utf-8") as f:
            _json.dump([{"id": j["id"], "company": j["company"], "title": j["title"],
                         "url": j["url"], "board": j["board"], "gh_job_id": j["gh_job_id"]}
                        for j in needs_code], f, indent=2)
        log(f"Saved {len(needs_code)} pending code jobs to {PENDING_CODES_PATH}")

    log(f"\n{'='*70}")
    log(f"GREENHOUSE SWARM COMPLETE")
    log(f"{'='*70}")
    log(f"Duration: {elapsed:.0f}s ({elapsed/60:.1f}min, {elapsed/3600:.1f}hr)")
    log(f"Success:  {len(successes)}")
    log(f"Needs Code: {len(needs_code)} (check Gmail)")
    log(f"Failed:   {len(failures)}")
    log(f"Already:  {len(already_applied)}")
    log(f"Rate:     {len(successes)/(elapsed/60):.1f} apps/min" if elapsed > 60 else "")
    log(f"{'='*70}")

    # Write markdown results
    with open(RESULTS_PATH, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# Greenhouse Playwright Swarm Results\n\n")
        f.write(f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**Duration**: {elapsed/60:.1f} min ({elapsed/3600:.1f} hr)\n\n")
        f.write(f"## Summary\n")
        f.write(f"- **Success**: {len(successes)}\n")
        f.write(f"- **Failed**: {len(failures)}\n")
        f.write(f"- **Already Applied**: {len(already_applied)}\n")
        f.write(f"- **Total Attempted**: {len(successes)+len(failures)+len(already_applied)}\n\n")

        if successes:
            f.write(f"## Successful Applications ({len(successes)})\n\n")
            for j in successes:
                f.write(f"- [{j['fit_score']}] **{j['company']}** — {j['title']}\n")

        if failures:
            f.write(f"\n## Failed ({len(failures)})\n\n")
            # Group by error type
            by_error = {}
            for j in failures:
                err = j.get("error", "unknown")[:60]
                if err not in by_error:
                    by_error[err] = []
                by_error[err].append(j)
            for err, jobs in sorted(by_error.items(), key=lambda x: -len(x[1])):
                f.write(f"### {err} ({len(jobs)})\n")
                for j in jobs[:10]:
                    f.write(f"- {j['company']} — {j['title'][:50]}\n")
                if len(jobs) > 10:
                    f.write(f"- *...and {len(jobs)-10} more*\n")
                f.write("\n")

        if already_applied:
            f.write(f"\n## Already Applied ({len(already_applied)})\n\n")
            for j in already_applied:
                f.write(f"- {j['company']} — {j['title']}\n")

        if no_board:
            f.write(f"\n## Could Not Determine Board Token ({len(no_board)})\n\n")
            companies = {}
            for j in no_board:
                c = j["company"]
                if c not in companies:
                    companies[c] = 0
                companies[c] += 1
            for c, n in sorted(companies.items(), key=lambda x: -x[1])[:20]:
                f.write(f"- {c} ({n} jobs)\n")

    log(f"Results: {RESULTS_PATH}")
    log(f"Log: {LOG_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Greenhouse Playwright Swarm")
    parser.add_argument("--min-score", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=0, help="Max jobs (0=unlimited)")
    parser.add_argument("--resume-from", type=int, default=0, help="Skip first N jobs")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between apps")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    run_swarm(
        min_score=args.min_score,
        limit=args.limit,
        resume_from=args.resume_from,
        delay=args.delay,
        headless=not args.headed,
    )
