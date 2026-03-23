"""
Ashby Playwright Swarm — Headless Browser Application Submitter
================================================================
Navigates Ashby React SPA forms, fills fields, uploads resume, submits.
Run: .venv\Scripts\python.exe swarm_ashby_playwright.py [--limit N] [--resume-from N]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

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
LOG_PATH = r"J:\job-hunter-mcp\swarm_ashby_pw_log.txt"
RESULTS_PATH = r"J:\job-hunter-mcp\swarm_ashby_pw_results.md"

GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

APPLICANT = {
    "first_name": "Matt",
    "last_name": "Gates",
    "name": "Matt Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "phone_intl": "+15307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
    "current_company": "Ridge Cell Repair LLC",
}


def log(msg: str, log_path: str = None):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(log_path or LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


def generate_cover_letter(company: str, title: str) -> str:
    tl = title.lower()
    if any(kw in tl for kw in ["ai", "ml", "machine learning", "data scientist", "llm", "nlp", "genai", "agent"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years of software engineering "
            f"experience, I have built production AI/ML systems including LLM-powered applications, "
            f"RAG pipelines, autonomous agents, and ML inference infrastructure. I deployed a weather "
            f"prediction trading bot achieving 20x returns and built distributed AI inference fleets "
            f"serving multiple models across heterogeneous GPU hardware. I've authored 10+ production "
            f"MCP servers and a 27K-line Rust browser automation framework. "
            f"My expertise in Python, FastAPI, vector databases, and cloud infrastructure makes me "
            f"a strong fit for {company}'s engineering team."
        )
    if any(kw in tl for kw in ["infrastructure", "platform", "sre", "devops", "cloud", "systems"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years building scalable "
            f"infrastructure, distributed systems, and cloud-native platforms, I bring deep expertise "
            f"in CI/CD automation, container orchestration, and production reliability. I've built "
            f"GPU inference clusters, industrial automation systems (ESP32, PID controllers), and "
            f"cloud infrastructure (AWS, Docker, Kubernetes). I bring strong systems thinking "
            f"and hands-on engineering to {company}'s team."
        )
    if any(kw in tl for kw in ["full stack", "fullstack", "frontend", "react", "typescript", "growth"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years spanning full-stack "
            f"development, I have built production apps using React, TypeScript, Next.js, and Python. "
            f"My recent work includes AI-powered browser automation (27K lines Rust), real-time "
            f"trading interfaces, and developer tooling including 10+ MCP servers. "
            f"I am passionate about building quality user experiences backed by robust engineering."
        )
    if any(kw in tl for kw in ["backend", "back-end", "api", "server", "data engineer", "data "]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years building production "
            f"backend systems in Python, Rust, TypeScript, and distributed architectures, I have "
            f"built high-performance APIs, data pipelines, and microservices at real-world scale. "
            f"My background spans ML infrastructure, real-time systems, and developer tooling."
        )
    return (
        f"I am excited about the {title} role at {company}. With 10 years spanning AI/ML systems, "
        f"cloud infrastructure, full-stack development, and industrial automation, I bring a versatile "
        f"skillset and proven track record shipping production systems at scale. I've built autonomous "
        f"AI agents, distributed inference infrastructure, and 10+ production MCP servers."
    )


def answer_for_label(label: str, company: str, title: str) -> str:
    ll = label.lower()
    if "linkedin" in ll:
        return APPLICANT["linkedin"]
    if "github" in ll or "portfolio" in ll or "website" in ll or "url" in ll:
        return APPLICANT["github"]
    if "salary" in ll or "compensation" in ll or "pay" in ll or "expectation" in ll:
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
        return APPLICANT["current_company"]
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
    if any(x in ll for x in ["phone", "mobile", "cell"]):
        return APPLICANT["phone"]
    return ""


def pick_select_value(label: str, options: list) -> str:
    ll = label.lower()
    if "authorized" in ll or "authorization" in ll or "lawfully" in ll or "eligible" in ll:
        for opt in options:
            ol = opt.lower()
            if "yes" in ol or "authorized" in ol or "do not require" in ol:
                return opt
    if "sponsor" in ll or "visa" in ll or "immigration" in ll:
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
    if any(kw in ll for kw in ["remote", "hybrid", "relocation"]):
        for opt in options:
            if "yes" in opt.lower():
                return opt
    if any(kw in ll for kw in ["how did you hear", "where did you", "source"]):
        for opt in options:
            if any(x in opt.lower() for x in ["job board", "website", "online", "other"]):
                return opt
    return options[0] if options else ""


def fetch_security_code_imap(company: str, max_wait: int = 15) -> str:
    if not GMAIL_APP_PASSWORD:
        return ""
    try:
        import imaplib
        import email as email_lib
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        for attempt in range(max_wait // 3):
            status, data = mail.search(None, f'(FROM "ashby" SUBJECT "verification" UNSEEN)')
            if status == "OK" and data[0]:
                msg_ids = data[0].split()
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
                    code_match = re.search(r'(?:code|pin)[:\s]*([A-Za-z0-9]{4,12})', body)
                    if code_match:
                        mail.logout()
                        return code_match.group(1)
            time.sleep(3)
        mail.logout()
    except Exception as e:
        log(f"    IMAP error: {e}")
    return ""


def apply_ashby(page, url: str, company: str, title: str) -> dict:
    """Fill and submit an Ashby application form."""
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except PWTimeout:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            return {"success": False, "error": f"Page load timeout: {e}"}

    # Wait for React to render the apply section
    time.sleep(3)

    # Check if page loaded
    page_text = (page.text_content("body") or "").lower()
    if "not found" in page_text or "no longer" in page_text or "expired" in page_text:
        return {"success": False, "error": "Job no longer available"}

    # Look for "Apply" button to get to the form
    try:
        apply_btn = page.query_selector(
            'button:has-text("Apply"), a:has-text("Apply"), '
            '[data-testid*="apply"], button[class*="apply"]'
        )
        if apply_btn and apply_btn.is_visible():
            apply_btn.scroll_into_view_if_needed()
            apply_btn.click()
            time.sleep(2)
            log(f"    Clicked Apply button")
    except Exception:
        pass

    cover_letter = generate_cover_letter(company, title)

    # ── Fill form fields ──────────────────────────────────────────
    # Ashby uses various patterns: name/id/placeholder/label associations
    # Strategy: find all visible inputs and fill based on label/placeholder

    # Try filling by common field patterns
    field_fills = [
        # (selectors, value)
        ('input[name*="name" i]:not([name*="last"]):not([name*="company"]), input[placeholder*="Full name" i], input[placeholder*="Name" i]', APPLICANT["name"]),
        ('input[name*="first_name" i], input[placeholder*="First" i]', APPLICANT["first_name"]),
        ('input[name*="last_name" i], input[placeholder*="Last" i]', APPLICANT["last_name"]),
        ('input[type="email"], input[name*="email" i], input[placeholder*="Email" i]', APPLICANT["email"]),
        ('input[type="tel"], input[name*="phone" i], input[placeholder*="Phone" i]', APPLICANT["phone"]),
        ('input[name*="linkedin" i], input[placeholder*="LinkedIn" i]', APPLICANT["linkedin"]),
        ('input[name*="github" i], input[placeholder*="GitHub" i], input[name*="portfolio" i], input[placeholder*="Portfolio" i]', APPLICANT["github"]),
        ('input[name*="location" i], input[placeholder*="Location" i], input[placeholder*="City" i]', APPLICANT["location"]),
        ('input[name*="company" i]:not([name*="name"]), input[placeholder*="Current company" i]', APPLICANT["current_company"]),
    ]

    for selector, value in field_fills:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(value)
                time.sleep(0.2)
        except Exception:
            pass

    # ── Fill by label association ─────────────────────────────────
    # Find all labels and their associated inputs
    try:
        label_input_pairs = page.evaluate('''() => {
            const results = [];
            const labels = document.querySelectorAll('label');
            labels.forEach(label => {
                const forId = label.getAttribute('for');
                let input = null;
                if (forId) {
                    input = document.getElementById(forId);
                }
                if (!input) {
                    input = label.querySelector('input, textarea, select');
                }
                if (!input) {
                    const next = label.nextElementSibling;
                    if (next && (next.tagName === 'INPUT' || next.tagName === 'TEXTAREA' || next.tagName === 'SELECT' || next.querySelector('input, textarea, select'))) {
                        input = next.tagName === 'INPUT' || next.tagName === 'TEXTAREA' || next.tagName === 'SELECT' ? next : next.querySelector('input, textarea, select');
                    }
                }
                if (input && input.offsetParent !== null) {
                    results.push({
                        label: label.textContent.trim().substring(0, 100),
                        id: input.id || '',
                        name: input.name || '',
                        tag: input.tagName.toLowerCase(),
                        type: input.type || '',
                        value: input.value || '',
                        placeholder: input.placeholder || '',
                    });
                }
            });
            return results;
        }''')

        for pair in label_input_pairs:
            if pair["value"]:
                continue  # Already filled

            label = pair["label"]
            selector = f"#{pair['id']}" if pair["id"] else f"[name='{pair['name']}']" if pair["name"] else None
            if not selector:
                continue

            if pair["tag"] in ("input", "textarea") and pair["type"] not in ("file", "checkbox", "radio", "hidden"):
                answer = answer_for_label(label, company, title)
                if answer:
                    try:
                        el = page.query_selector(selector)
                        if el and el.is_visible():
                            el.fill(answer)
                            log(f"    Field: {label[:40]} = {answer[:40]}")
                            time.sleep(0.2)
                    except Exception:
                        pass

    except Exception as e:
        log(f"    Label scan error: {e}")

    # ── Upload resume ─────────────────────────────────────────────
    try:
        file_input = page.query_selector('input[type="file"]')
        if file_input and os.path.exists(RESUME_PATH):
            file_input.set_input_files(RESUME_PATH)
            log(f"    Uploaded resume")
            time.sleep(1.5)
    except Exception as e:
        log(f"    Resume upload issue: {e}")

    # ── Fill cover letter textarea ────────────────────────────────
    try:
        textareas = page.query_selector_all('textarea')
        for ta in textareas:
            if ta.is_visible() and not ta.input_value():
                placeholder = ta.get_attribute("placeholder") or ""
                name = ta.get_attribute("name") or ""
                if any(kw in (placeholder + name).lower() for kw in ["cover", "letter", "why", "additional", "message", "note"]):
                    ta.fill(cover_letter)
                    log(f"    Cover letter filled")
                    break
                # If it's the only textarea, fill it with cover letter
                if len(textareas) <= 2:
                    ta.fill(cover_letter)
                    log(f"    Textarea filled with cover letter")
                    break
    except Exception:
        pass

    # ── Handle dropdowns/selects ──────────────────────────────────
    try:
        selects = page.query_selector_all('select')
        for sel in selects:
            if sel.is_visible():
                label_el = page.evaluate('''(el) => {
                    const label = el.closest('label') || document.querySelector('label[for="' + el.id + '"]');
                    return label ? label.textContent.trim().substring(0, 80) : '';
                }''', sel)
                options = sel.evaluate('''(el) => Array.from(el.options).map(o => ({value: o.value, text: o.text}))''')
                opt_texts = [o["text"] for o in options if o["value"]]
                if opt_texts:
                    choice = pick_select_value(label_el, opt_texts)
                    if choice:
                        matching_opt = next((o for o in options if o["text"] == choice), None)
                        if matching_opt:
                            sel.select_option(value=matching_opt["value"])
                            log(f"    Select: {label_el[:30]} = {choice[:30]}")
                            time.sleep(0.2)
    except Exception:
        pass

    # ── Handle checkboxes (consent, agree) ────────────────────────
    try:
        checkboxes = page.query_selector_all('input[type="checkbox"]')
        for cb in checkboxes:
            if cb.is_visible() and not cb.is_checked():
                label_el = page.evaluate('''(el) => {
                    const label = el.closest('label') || document.querySelector('label[for="' + el.id + '"]');
                    return label ? label.textContent.trim().substring(0, 80) : '';
                }''', cb)
                ll = label_el.lower()
                if any(kw in ll for kw in ["agree", "consent", "acknowledge", "privacy", "terms", "confirm"]):
                    cb.check()
                    log(f"    Checked: {label_el[:40]}")
    except Exception:
        pass

    time.sleep(0.5)

    # ── Submit ────────────────────────────────────────────────────
    try:
        submit_btn = page.query_selector(
            'button[type="submit"], input[type="submit"], '
            'button:has-text("Submit"), button:has-text("Apply"), '
            'button:has-text("Send Application")'
        )
        if not submit_btn or not submit_btn.is_visible():
            # Try any button at the bottom of the form
            submit_btn = page.query_selector(
                'form button:last-of-type, [class*="submit"], [class*="apply"] button'
            )
        if submit_btn and submit_btn.is_visible():
            submit_btn.scroll_into_view_if_needed()
            time.sleep(0.3)
            submit_btn.click()
            log(f"    Clicked submit")
        else:
            return {"success": False, "error": "Submit button not found"}
    except Exception as e:
        return {"success": False, "error": f"Submit click failed: {e}"}

    # ── Check result ──────────────────────────────────────────────
    time.sleep(4)

    try:
        page_text = (page.text_content("body") or "").lower()
        page_url = page.url

        # Security code / verification
        if "security code" in page_text or "verification code" in page_text or "verify your email" in page_text:
            code = fetch_security_code_imap(company)
            if code:
                log(f"    Got verification code: {code}")
                code_input = page.query_selector(
                    'input[name*="code"], input[name*="verify"], '
                    'input[placeholder*="code"], input[type="text"]:not([value])'
                )
                if code_input and code_input.is_visible():
                    code_input.fill(code)
                    time.sleep(0.5)
                    verify_btn = page.query_selector(
                        'button:has-text("Verify"), button:has-text("Submit"), button[type="submit"]'
                    )
                    if verify_btn:
                        verify_btn.click()
                        time.sleep(4)
                        page_text2 = (page.text_content("body") or "").lower()
                        if any(x in page_text2 for x in ["thank", "submitted", "received", "confirmation", "successfully"]):
                            return {"success": True, "msg": "Confirmed after verification code"}
            return {"success": False, "error": "NEEDS_VERIFICATION_CODE", "needs_code": True}

        # Success checks
        if any(x in page_text for x in [
            "thank you", "application has been", "submitted",
            "received your application", "confirmation",
            "we have received", "successfully", "thanks for applying",
            "thanks for your interest"
        ]):
            return {"success": True, "msg": "Confirmation detected"}

        if "already applied" in page_text or "already submitted" in page_text:
            return {"success": False, "error": "Already applied", "already": True}

        # Validation errors
        errors = page.query_selector_all('[class*="error"], [role="alert"], [class*="invalid"]')
        err_texts = [e.text_content().strip() for e in errors if e.text_content().strip() and len(e.text_content().strip()) < 200]
        if err_texts:
            return {"success": False, "error": f"Validation: {'; '.join(err_texts[:3])[:150]}"}

        if "confirmation" in page_url.lower() or "thank" in page_url.lower() or "success" in page_url.lower():
            return {"success": True, "msg": "Redirected to confirmation"}

        return {"success": False, "error": "No confirmation after submit"}
    except Exception as e:
        return {"success": False, "error": f"Result check: {e}"}


# ─── DB ──────────────────────────────────────────────────────────────

def get_ashby_jobs(min_score: float = 60.0) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score, source
        FROM jobs WHERE status = 'new' AND fit_score >= ? AND source = 'ashby'
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


# ─── Main ────────────────────────────────────────────────────────────

def run_swarm(min_score=60.0, limit=0, resume_from=0, delay=3.0, worker_id=0):
    start_time = datetime.now(timezone.utc)
    log_file = LOG_PATH.replace(".txt", f"_w{worker_id}.txt") if worker_id else LOG_PATH

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"=== ASHBY PW SWARM W{worker_id} {start_time.isoformat()} ===\n")

    log(f"{'='*60}", log_file)
    log(f"ASHBY PLAYWRIGHT SWARM — Worker {worker_id}", log_file)
    log(f"{'='*60}", log_file)

    all_jobs = get_ashby_jobs(min_score)
    log(f"Total Ashby jobs: {len(all_jobs)}", log_file)

    batch = all_jobs[resume_from:]
    if limit > 0:
        batch = batch[:limit]

    log(f"Batch: {len(batch)} (from={resume_from}, limit={limit or 'all'})", log_file)

    successes, failures, already, needs_code = [], [], [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}, locale="en-US",
        )
        page = context.new_page()

        for i, job in enumerate(batch):
            job_num = i + 1 + resume_from
            log(f"[{job_num}] {job['company']} — {job['title'][:50]} (score={job['fit_score']})", log_file)

            try:
                result = apply_ashby(page, job["url"], job["company"], job["title"])

                if result.get("success"):
                    log(f"  >>> SUCCESS: {result.get('msg', '')} <<<", log_file)
                    successes.append(job)
                    cl = generate_cover_letter(job["company"], job["title"])
                    update_job_status(job["id"], "applied", cover_letter=cl)
                elif result.get("needs_code"):
                    log(f"  NEEDS CODE — check Gmail", log_file)
                    needs_code.append(job)
                    update_job_status(job["id"], "needs_code")
                elif result.get("already"):
                    log(f"  Already applied", log_file)
                    already.append(job)
                    update_job_status(job["id"], "applied")
                else:
                    error = result.get("error", "unknown")
                    log(f"  FAILED: {error[:120]}", log_file)
                    failures.append({**job, "error": error})
                    update_job_status(job["id"], "apply_failed")
            except Exception as e:
                log(f"  EXCEPTION: {e}", log_file)
                failures.append({**job, "error": str(e)})
                update_job_status(job["id"], "apply_failed")
                try:
                    page.close()
                except Exception:
                    pass
                page = context.new_page()

            if (i + 1) % 10 == 0:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                log(f"--- W{worker_id} Progress: {i+1}/{len(batch)} OK={len(successes)} FAIL={len(failures)} ---", log_file)

            if i < len(batch) - 1:
                time.sleep(delay)

        browser.close()

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"\nW{worker_id} DONE: {len(successes)} success, {len(failures)} fail, {elapsed/60:.1f}min", log_file)

    results_file = RESULTS_PATH.replace(".md", f"_w{worker_id}.md") if worker_id else RESULTS_PATH
    with open(results_file, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# Ashby Swarm W{worker_id} Results\n\n")
        f.write(f"**Duration**: {elapsed/60:.1f} min | **Success**: {len(successes)} | **Failed**: {len(failures)}\n\n")
        if successes:
            f.write("## Success\n")
            for j in successes:
                f.write(f"- [{j['fit_score']}] **{j['company']}** — {j['title']}\n")
        if failures:
            f.write("\n## Failed\n")
            for j in failures[:30]:
                f.write(f"- {j['company']} — {j['title'][:50]} — {j.get('error','')[:60]}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume-from", type=int, default=0)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--worker-id", type=int, default=0)
    args = parser.parse_args()
    run_swarm(args.min_score, args.limit, args.resume_from, args.delay, args.worker_id)
