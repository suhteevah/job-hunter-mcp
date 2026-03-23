"""
Wraith CDP Apply Swarm — Autonomous job application using Wraith browser (MCP).
Uses CDP engine for React SPAs (Greenhouse, Ashby). No Playwright dependency.

Usage:
  python wraith_apply_swarm.py --platform greenhouse --limit 10
  python wraith_apply_swarm.py --platform ashby --limit 20
  python wraith_apply_swarm.py --all
  python wraith_apply_swarm.py --retry-failed --platform greenhouse
  python wraith_apply_swarm.py --min-score 40
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import imaplib
import email as email_lib
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

from wraith_mcp_client import WraithMCPClient

# ═══════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
LOG_DIR = r"J:\job-hunter-mcp\scripts\swarm\logs"
GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "yzpn qern vrax fvta")

APPLICANT = {
    "first_name": "Matt", "last_name": "Gates", "name": "Matt Gates",
    "email": "ridgecellrepair@gmail.com", "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
    "current_company": "Ridge Cell Repair LLC",
}

LOG_PATH = None

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if LOG_PATH:
        try:
            with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
                f.write(line + "\n")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
# DB
# ═══════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def get_viable_jobs(platform=None, min_score=60.0, status="new", limit=0):
    conn = get_db()
    q = "SELECT * FROM jobs WHERE status = ? AND fit_score >= ?"
    params = [status, min_score]
    if platform:
        q += " AND source = ?"
        params.append(platform)
    q += " ORDER BY fit_score DESC"
    if limit > 0:
        q += f" LIMIT {limit}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_job_status(job_id, status, cover_letter=None):
    try:
        conn = get_db()
        if cover_letter:
            conn.execute("UPDATE jobs SET status=?, applied_date=?, cover_letter=? WHERE id=?",
                         (status, datetime.now(timezone.utc).isoformat(), cover_letter, job_id))
        else:
            conn.execute("UPDATE jobs SET status=?, applied_date=? WHERE id=?",
                         (status, datetime.now(timezone.utc).isoformat(), job_id))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"  DB error: {e}")


# ═══════════════════════════════════════════════════════════════════════
# COVER LETTERS
# ═══════════════════════════════════════════════════════════════════════

def generate_cover_letter(company, title):
    tl = title.lower()
    if any(kw in tl for kw in ["ai", "ml", "machine learning", "data scientist", "llm", "nlp", "genai", "agent"]):
        return (f"I am excited about the {title} role at {company}. With 10 years of software engineering "
                f"experience, I have built production AI/ML systems including LLM-powered applications, "
                f"RAG pipelines, autonomous agents, and ML inference infrastructure. I deployed a weather "
                f"prediction trading bot achieving 20x returns and built distributed AI inference fleets. "
                f"I've authored 10+ production MCP servers and a 27K-line Rust browser automation framework. "
                f"My expertise in Python, FastAPI, vector databases, and cloud infrastructure makes me "
                f"a strong fit for {company}'s engineering team.")
    if any(kw in tl for kw in ["infrastructure", "platform", "sre", "devops", "cloud", "systems"]):
        return (f"I am drawn to the {title} role at {company}. With 10 years building scalable "
                f"infrastructure, distributed systems, and cloud-native platforms, I bring deep expertise "
                f"in CI/CD automation, container orchestration, and production reliability. I've built "
                f"GPU inference clusters, industrial automation systems (ESP32, PID controllers), and "
                f"cloud infrastructure (AWS, Docker, Kubernetes).")
    if any(kw in tl for kw in ["full stack", "fullstack", "frontend", "react", "typescript"]):
        return (f"I am excited about the {title} role at {company}. With 10 years spanning full-stack "
                f"development, I have built production apps using React, TypeScript, Next.js, and Python. "
                f"My recent work includes AI-powered browser automation (27K lines Rust), real-time "
                f"trading interfaces, and developer tooling including 10+ MCP servers.")
    if any(kw in tl for kw in ["backend", "back-end", "api", "server", "data engineer"]):
        return (f"I am excited about the {title} role at {company}. With 10 years building production "
                f"backend systems in Python, Rust, TypeScript, and distributed architectures, I have "
                f"built high-performance APIs, data pipelines, and microservices at real-world scale.")
    if any(kw in tl for kw in ["qa", "quality", "test", "sdet"]):
        return (f"I am excited about the {title} role at {company}. With 10 years spanning test automation, "
                f"CI/CD, and quality engineering, I've built browser automation frameworks (27K lines Rust), "
                f"test infrastructure, and production monitoring systems.")
    return (f"I am excited about the {title} role at {company}. With 10 years spanning AI/ML systems, "
            f"cloud infrastructure, full-stack development, and industrial automation, I bring a versatile "
            f"skillset and proven track record shipping production systems at scale.")


# ═══════════════════════════════════════════════════════════════════════
# FORM INTELLIGENCE — Parse snapshot, fill fields
# ═══════════════════════════════════════════════════════════════════════

def parse_snapshot_refs(snapshot: str) -> list:
    """Parse Wraith snapshot into list of {ref, tag, text, type, name, value} dicts."""
    elements = []
    for line in snapshot.split("\n"):
        m = re.match(r'^(@\w+)\s+\[(\w+)\]\s+(.*)', line.strip())
        if m:
            ref, tag, text = m.group(1), m.group(2), m.group(3).strip().strip('"')
            elements.append({"ref": ref, "tag": tag, "text": text})
    return elements


def guess_field_answer(text: str, company: str, title: str) -> str:
    """Given a field label/placeholder, return the best answer."""
    ll = text.lower()
    if "first name" in ll or "first_name" in ll:
        return APPLICANT["first_name"]
    if "last name" in ll or "last_name" in ll:
        return APPLICANT["last_name"]
    if "full name" in ll or (ll.strip() == "name"):
        return APPLICANT["name"]
    if "email" in ll:
        return APPLICANT["email"]
    if "phone" in ll or "mobile" in ll or "cell" in ll:
        return APPLICANT["phone"]
    if "linkedin" in ll:
        return APPLICANT["linkedin"]
    if "github" in ll or "portfolio" in ll or "website" in ll or "url" in ll:
        return APPLICANT["github"]
    if "location" in ll or "city" in ll or "where" in ll or "based" in ll:
        return APPLICANT["location"]
    if "current" in ll and "company" in ll:
        return APPLICANT["current_company"]
    if "salary" in ll or "compensation" in ll or "expectation" in ll:
        return "$150,000 USD"
    if "year" in ll and ("experience" in ll or "ai" in ll or "python" in ll or "software" in ll):
        return "10"
    if "how did you" in ll and ("hear" in ll or "find" in ll):
        return "Job board"
    if "authorized" in ll or "authorization" in ll or "eligible" in ll or "lawfully" in ll:
        return "Yes"
    if "sponsor" in ll or "visa" in ll:
        return "No"
    if "country" in ll or "residence" in ll:
        return "United States"
    if "state" in ll or "province" in ll:
        return "California"
    if "zip" in ll or "postal" in ll:
        return "95928"
    if "address" in ll:
        return "Chico, CA"
    if "notice" in ll or "start date" in ll or "available" in ll:
        return "Immediately"
    if "refer" in ll and "name" not in ll:
        return "No"
    if "pronoun" in ll:
        return "he/him"
    if any(x in ll for x in ["cover letter", "additional", "anything else", "why", "tell us", "about your",
                              "motivation", "excite", "interest", "passion", "background", "describe"]):
        return generate_cover_letter(company, title)
    if any(x in ll for x in ["how are you using ai", "ai experiment", "ai tool"]):
        return ("I use AI daily — built 10+ production MCP servers, a 27K-line Rust browser automation "
                "framework with AI agent orchestration, and deployed LLM-powered RAG pipelines.")
    if "business trip" in ll or "travel" in ll or "relocat" in ll or "willing" in ll:
        return "Yes"
    if "education" in ll or "degree" in ll or "school" in ll:
        return "Butte College — Associates level coursework in Computer Science"
    return ""


def guess_select_answer(text: str) -> str:
    """Return best keyword to type into a dropdown given its label."""
    ll = text.lower()
    if "authorized" in ll or "authorization" in ll or "eligible" in ll or "lawfully" in ll:
        return "Yes"
    if "sponsor" in ll or "visa" in ll:
        return "No"
    if "country" in ll or "residence" in ll:
        return "United States"
    if "how did you hear" in ll or "source" in ll:
        return "Job board"
    if "gender" in ll or "race" in ll or "veteran" in ll or "disability" in ll or "ethnicity" in ll:
        return "Decline"
    if "remote" in ll or "hybrid" in ll or "relocation" in ll:
        return "Yes"
    if "agree" in ll or "consent" in ll or "acknowledge" in ll:
        return "agree"
    return "Yes"


# ═══════════════════════════════════════════════════════════════════════
# IMAP SECURITY CODE
# ═══════════════════════════════════════════════════════════════════════

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def get_text(self):
        return " ".join(self.text)

def strip_html(html):
    s = HTMLStripper()
    s.feed(html or "")
    return s.get_text()

def fetch_security_code(company, platform="greenhouse", max_wait=15):
    if not GMAIL_APP_PASSWORD:
        return ""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        search_q = '(FROM "greenhouse" SUBJECT "security code" UNSEEN)' if platform == "greenhouse" \
            else '(FROM "ashby" SUBJECT "verification" UNSEEN)'
        for _ in range(max_wait // 3):
            status, data = mail.search(None, search_q)
            if status == "OK" and data[0]:
                msg_ids = data[0].split()
                status, msg_data = mail.fetch(msg_ids[-1], "(RFC822)")
                if status == "OK":
                    msg = email_lib.message_from_bytes(msg_data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ct = part.get_content_type()
                            if ct == "text/plain":
                                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                                break
                            elif ct == "text/html" and not body:
                                body = strip_html(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                    code_match = re.search(r'application:\s*([A-Za-z0-9]{6,12})', body)
                    if not code_match:
                        code_match = re.search(r'(?:code|pin)[:\s]*([A-Za-z0-9]{4,12})', body)
                    if code_match:
                        mail.logout()
                        return code_match.group(1)
            time.sleep(3)
        mail.logout()
    except Exception as e:
        log(f"    IMAP error: {e}")
    return ""


# ═══════════════════════════════════════════════════════════════════════
# APPLY — Greenhouse via Wraith CDP
# ═══════════════════════════════════════════════════════════════════════

def apply_greenhouse_cdp(wraith: WraithMCPClient, url: str, company: str, title: str) -> dict:
    """Apply to a Greenhouse job using Wraith CDP."""
    # Convert custom career page URLs to standard Greenhouse embed URLs
    gh_jid_match = re.search(r'gh_jid=(\d+)', url)
    if gh_jid_match and 'greenhouse.io' not in url:
        # Custom career page (stripe.com, samsara.com, etc.) — use embed URL
        jid = gh_jid_match.group(1)
        url = f"https://boards.greenhouse.io/embed/job_app?token={jid}"
        log(f"  Converted to embed URL: {url[:60]}")
    elif 'job-boards.greenhouse.io' in url:
        # job-boards URL — convert to embed for reliable form rendering
        jid_match = re.search(r'/jobs/(\d+)', url)
        if jid_match:
            jid = jid_match.group(1)
            url = f"https://boards.greenhouse.io/embed/job_app?token={jid}"
    # Navigate to the job page using CDP for React SPA rendering
    snap = wraith.navigate_cdp(url)
    if "not found" in snap.lower() or "no longer" in snap.lower():
        return {"success": False, "error": "Job no longer available"}

    time.sleep(2)
    snap = wraith.snapshot()
    elements = parse_snapshot_refs(snap)

    cover_letter = generate_cover_letter(company, title)

    # Find and fill all input fields
    for el in elements:
        if el["tag"] in ("input", "textarea"):
            answer = guess_field_answer(el["text"], company, title)
            if answer:
                wraith.fill(el["ref"], answer)
                time.sleep(0.3)

    # Upload resume — find file input
    for el in elements:
        if el["tag"] == "input" and "file" in el["text"].lower():
            wraith.upload_file(el["ref"], RESUME_PATH)
            time.sleep(1)
            break
    else:
        # Try finding by re-snapshot after fills
        snap2 = wraith.snapshot()
        for line in snap2.split("\n"):
            if "file" in line.lower() and "resume" in line.lower():
                m = re.match(r'^(@\w+)', line.strip())
                if m:
                    wraith.upload_file(m.group(1), RESUME_PATH)
                    time.sleep(1)
                    break

    # Handle select dropdowns
    snap3 = wraith.snapshot()
    elements3 = parse_snapshot_refs(snap3)
    for el in elements3:
        if el["tag"] == "select":
            answer = guess_select_answer(el["text"])
            if answer:
                wraith.select(el["ref"], answer)
                time.sleep(0.3)

    # Handle React Select custom dropdowns (look for combobox-like divs)
    for el in elements3:
        if el["tag"] in ("div", "span") and any(x in el["text"].lower() for x in
                ["select...", "choose", "country", "authorized", "hear about", "source"]):
            answer = guess_select_answer(el["text"])
            if answer:
                wraith.custom_dropdown(el["ref"], answer)
                time.sleep(0.5)

    # Fill cover letter textarea if not already filled
    snap4 = wraith.snapshot()
    for el in parse_snapshot_refs(snap4):
        if el["tag"] == "textarea" and not el["text"]:
            wraith.fill(el["ref"], cover_letter)
            time.sleep(0.3)
            break

    time.sleep(0.5)

    # Find and click submit button
    snap5 = wraith.snapshot()
    submit_ref = None
    for el in parse_snapshot_refs(snap5):
        if el["tag"] == "button" and any(x in el["text"].lower() for x in
                ["submit", "apply", "send application"]):
            submit_ref = el["ref"]
            break

    if not submit_ref:
        return {"success": False, "error": "Submit button not found"}

    wraith.click(submit_ref)
    time.sleep(4)

    # Check result
    verify = wraith.verify_submission()
    verify_lower = verify.lower()

    if "confirmed" in verify_lower or "success" in verify_lower:
        return {"success": True, "msg": "Wraith verified: confirmed"}

    if "likely" in verify_lower:
        return {"success": True, "msg": "Wraith verified: likely success"}

    snap_final = wraith.snapshot()
    snap_lower = snap_final.lower()

    if "security code" in snap_lower or "verification code" in snap_lower:
        code = fetch_security_code(company, "greenhouse")
        if code:
            log(f"    Got code: {code}")
            # Find code input and fill
            for el in parse_snapshot_refs(snap_final):
                if el["tag"] == "input" and any(x in el["text"].lower() for x in ["code", "verify"]):
                    wraith.fill(el["ref"], code)
                    time.sleep(0.5)
                    # Click verify/submit
                    snap6 = wraith.snapshot()
                    for el2 in parse_snapshot_refs(snap6):
                        if el2["tag"] == "button" and any(x in el2["text"].lower() for x in ["verify", "submit"]):
                            wraith.click(el2["ref"])
                            time.sleep(4)
                            v2 = wraith.verify_submission()
                            if "confirmed" in v2.lower() or "success" in v2.lower() or "likely" in v2.lower():
                                return {"success": True, "msg": "Confirmed after verification code"}
                            break
                    break
        return {"success": False, "error": "NEEDS_VERIFICATION_CODE", "needs_code": True}

    if any(x in snap_lower for x in ["thank you", "submitted", "received", "confirmation", "successfully"]):
        return {"success": True, "msg": "Confirmation text detected"}

    if "already applied" in snap_lower or "already submitted" in snap_lower:
        return {"success": False, "error": "Already applied", "already": True}

    return {"success": False, "error": "No confirmation after submit"}


# ═══════════════════════════════════════════════════════════════════════
# APPLY — Ashby via Wraith CDP
# ═══════════════════════════════════════════════════════════════════════

def apply_ashby_cdp(wraith: WraithMCPClient, url: str, company: str, title: str) -> dict:
    """Apply to an Ashby job using Wraith CDP."""
    snap = wraith.navigate_cdp(url)
    if "not found" in snap.lower() or "no longer" in snap.lower() or "expired" in snap.lower():
        return {"success": False, "error": "Job no longer available"}

    time.sleep(3)
    snap = wraith.snapshot()

    # Click "Apply" button if present
    for el in parse_snapshot_refs(snap):
        if el["tag"] in ("button", "a") and "apply" in el["text"].lower():
            wraith.click(el["ref"])
            time.sleep(2)
            snap = wraith.snapshot()
            break

    cover_letter = generate_cover_letter(company, title)
    elements = parse_snapshot_refs(snap)

    # Fill all input fields
    for el in elements:
        if el["tag"] in ("input", "textarea"):
            answer = guess_field_answer(el["text"], company, title)
            if not answer and el["tag"] == "textarea":
                answer = cover_letter
            if answer:
                wraith.fill(el["ref"], answer)
                time.sleep(0.3)

    # Upload resume
    for el in elements:
        if el["tag"] == "input" and ("file" in el["text"].lower() or "resume" in el["text"].lower()):
            wraith.upload_file(el["ref"], RESUME_PATH)
            time.sleep(1)
            break

    # Handle selects
    snap2 = wraith.snapshot()
    for el in parse_snapshot_refs(snap2):
        if el["tag"] == "select":
            answer = guess_select_answer(el["text"])
            if answer:
                wraith.select(el["ref"], answer)
                time.sleep(0.3)

    # Handle checkboxes (consent/agree)
    for el in parse_snapshot_refs(snap2):
        if el["tag"] == "input" and any(x in el["text"].lower() for x in ["agree", "consent", "acknowledge", "terms"]):
            wraith.click(el["ref"])
            time.sleep(0.2)

    time.sleep(0.5)

    # Submit
    snap3 = wraith.snapshot()
    submit_ref = None
    for el in parse_snapshot_refs(snap3):
        if el["tag"] == "button" and any(x in el["text"].lower() for x in ["submit", "apply", "send"]):
            submit_ref = el["ref"]
            break

    if not submit_ref:
        return {"success": False, "error": "Submit button not found"}

    wraith.click(submit_ref)
    time.sleep(4)

    # Check result
    verify = wraith.verify_submission()
    verify_lower = verify.lower()

    if "confirmed" in verify_lower or "success" in verify_lower or "likely" in verify_lower:
        return {"success": True, "msg": f"Wraith verified: {verify[:50]}"}

    snap_final = wraith.snapshot()
    snap_lower = snap_final.lower()

    if any(x in snap_lower for x in ["thank you", "submitted", "received", "confirmation", "successfully"]):
        return {"success": True, "msg": "Confirmation text detected"}

    if "already applied" in snap_lower:
        return {"success": False, "error": "Already applied", "already": True}

    if "verification" in snap_lower or "security code" in snap_lower:
        code = fetch_security_code(company, "ashby")
        if code:
            log(f"    Got code: {code}")
            for el in parse_snapshot_refs(snap_final):
                if el["tag"] == "input":
                    wraith.fill(el["ref"], code)
                    time.sleep(0.5)
                    snap6 = wraith.snapshot()
                    for el2 in parse_snapshot_refs(snap6):
                        if el2["tag"] == "button" and any(x in el2["text"].lower() for x in ["verify", "submit"]):
                            wraith.click(el2["ref"])
                            time.sleep(4)
                            v2 = wraith.verify_submission()
                            if any(x in v2.lower() for x in ["confirmed", "success", "likely"]):
                                return {"success": True, "msg": "Confirmed after verification"}
                            break
                    break
        return {"success": False, "error": "NEEDS_VERIFICATION_CODE", "needs_code": True}

    return {"success": False, "error": "No confirmation after submit"}


# ═══════════════════════════════════════════════════════════════════════
# APPLY — Lever via Wraith native
# ═══════════════════════════════════════════════════════════════════════

def apply_lever_native(wraith: WraithMCPClient, url: str, company: str, title: str) -> dict:
    """Apply to a Lever job using Wraith native renderer (server-rendered HTML)."""
    # Lever apply page is at {url}/apply
    apply_url = url.rstrip("/") + "/apply"
    snap = wraith.navigate(apply_url)

    if "not found" in snap.lower() or "no longer" in snap.lower() or "page not found" in snap.lower():
        return {"success": False, "error": "Job no longer available"}

    time.sleep(2)
    snap = wraith.snapshot()
    elements = parse_snapshot_refs(snap)

    if not elements:
        # Maybe we're on the job detail, need to click "Apply" link
        snap = wraith.navigate(url)
        time.sleep(2)
        snap = wraith.snapshot()
        for el in parse_snapshot_refs(snap):
            if el["tag"] in ("a", "button") and "apply" in el["text"].lower():
                wraith.click(el["ref"])
                time.sleep(2)
                snap = wraith.snapshot()
                elements = parse_snapshot_refs(snap)
                break

    if not elements:
        return {"success": False, "error": "No form elements found"}

    cover_letter = generate_cover_letter(company, title)

    # Fill text inputs
    for el in elements:
        if el["tag"] in ("input", "textarea"):
            answer = guess_field_answer(el["text"], company, title)
            if not answer and el["tag"] == "textarea":
                answer = cover_letter
            if answer:
                wraith.fill(el["ref"], answer)
                time.sleep(0.3)

    # Upload resume
    for el in elements:
        if el["tag"] == "input" and any(x in el["text"].lower() for x in ["file", "resume", "cv", "upload"]):
            wraith.upload_file(el["ref"], RESUME_PATH)
            time.sleep(1)
            break

    # Handle native selects
    snap2 = wraith.snapshot()
    for el in parse_snapshot_refs(snap2):
        if el["tag"] == "select":
            answer = guess_select_answer(el["text"])
            if answer:
                wraith.select(el["ref"], answer)
                time.sleep(0.3)

    # Handle radio buttons (yes/no work auth, etc.)
    for el in parse_snapshot_refs(snap2):
        if el["tag"] == "input" and el["text"].lower().strip() in ("yes", "true"):
            # Check if it's a yes/no question about authorization
            wraith.click(el["ref"])
            time.sleep(0.2)

    # Handle checkboxes (consent/agree)
    for el in parse_snapshot_refs(snap2):
        if el["tag"] == "input" and any(x in el["text"].lower() for x in ["agree", "consent", "acknowledge", "terms"]):
            wraith.click(el["ref"])
            time.sleep(0.2)

    time.sleep(0.5)

    # Submit
    snap3 = wraith.snapshot()
    submit_ref = None
    for el in parse_snapshot_refs(snap3):
        if el["tag"] in ("button", "input") and any(x in el["text"].lower() for x in ["submit", "apply", "send"]):
            submit_ref = el["ref"]
            break

    if not submit_ref:
        return {"success": False, "error": "Submit button not found"}

    wraith.click(submit_ref)
    time.sleep(4)

    # Check result
    verify = wraith.verify_submission()
    verify_lower = verify.lower()

    if "confirmed" in verify_lower or "success" in verify_lower or "likely" in verify_lower:
        return {"success": True, "msg": f"Wraith verified: {verify[:50]}"}

    snap_final = wraith.snapshot()
    snap_lower = snap_final.lower()

    if any(x in snap_lower for x in ["thank you", "submitted", "received", "confirmation", "successfully", "thanks for applying"]):
        return {"success": True, "msg": "Confirmation text detected"}

    if "already applied" in snap_lower or "already submitted" in snap_lower:
        return {"success": False, "error": "Already applied", "already": True}

    return {"success": False, "error": "No confirmation after submit"}


# ═══════════════════════════════════════════════════════════════════════
# MAIN SWARM
# ═══════════════════════════════════════════════════════════════════════

def run_swarm(platform=None, min_score=60.0, limit=0, retry_failed=False, delay=3.0):
    global LOG_PATH

    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_PATH = os.path.join(LOG_DIR, f"wraith_apply_{ts}.txt")

    status = "apply_failed" if retry_failed else "new"
    platforms = [platform] if platform else ["ashby", "greenhouse", "lever"]

    log(f"{'='*70}")
    log(f"WRAITH CDP APPLY SWARM")
    log(f"{'='*70}")

    all_jobs = {}
    for p in platforms:
        jobs = get_viable_jobs(platform=p, min_score=min_score, status=status, limit=limit)
        if jobs:
            all_jobs[p] = jobs
            log(f"  {p}: {len(jobs)} jobs")

    if not all_jobs:
        log("No viable jobs found.")
        return

    total = sum(len(v) for v in all_jobs.values())
    log(f"Total: {total} jobs")

    # Start Wraith
    log("Starting Wraith MCP client...")
    wraith = WraithMCPClient()
    wraith.start()
    time.sleep(2)

    engine = wraith.engine_status()
    log(f"Engine: {engine[:100]}")

    successes, failures, needs_code_count = 0, 0, 0

    # Interleave platforms
    interleaved = []
    max_len = max(len(v) for v in all_jobs.values())
    for i in range(max_len):
        for p in platforms:
            if p in all_jobs and i < len(all_jobs[p]):
                interleaved.append((p, all_jobs[p][i]))

    start_time = time.time()

    for i, (plat, job) in enumerate(interleaved):
        log(f"\n[{i+1}/{len(interleaved)}] {plat.upper()} | {job['company']} — {job['title'][:50]} (score={job['fit_score']})")

        try:
            if plat == "ashby":
                result = apply_ashby_cdp(wraith, job["url"], job["company"], job["title"])
            elif plat == "greenhouse":
                result = apply_greenhouse_cdp(wraith, job["url"], job["company"], job["title"])
            elif plat == "lever":
                result = apply_lever_native(wraith, job["url"], job["company"], job["title"])
            else:
                log(f"  SKIP: unsupported platform {plat}")
                continue

            cl = generate_cover_letter(job["company"], job["title"])

            if result.get("success"):
                log(f"  >>> SUCCESS: {result.get('msg', '')} <<<")
                successes += 1
                update_job_status(job["id"], "applied", cover_letter=cl)
                wraith.dedup_record(job["url"], job["company"], job["title"], plat)
            elif result.get("needs_code"):
                log(f"  NEEDS CODE")
                needs_code_count += 1
                update_job_status(job["id"], "needs_code")
            elif result.get("already"):
                log(f"  Already applied")
                update_job_status(job["id"], "applied")
            else:
                log(f"  FAILED: {result.get('error', '')[:120]}")
                failures += 1
                update_job_status(job["id"], "apply_failed")
        except Exception as e:
            log(f"  EXCEPTION: {e}")
            failures += 1
            update_job_status(job["id"], "apply_failed")

        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            log(f"--- Progress: {i+1}/{len(interleaved)} | OK={successes} FAIL={failures} CODE={needs_code_count} | {elapsed/60:.1f}min ---")

        if i < len(interleaved) - 1:
            time.sleep(delay)

    wraith.stop()

    elapsed = time.time() - start_time
    log(f"\n{'='*70}")
    log(f"WRAITH APPLY SWARM DONE — {elapsed/60:.1f}min")
    log(f"  Success: {successes}")
    log(f"  Failed: {failures}")
    log(f"  Needs code: {needs_code_count}")
    log(f"  Rate: {(successes+failures+needs_code_count)/(elapsed/60+0.01):.1f} apps/min")
    log(f"{'='*70}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wraith CDP Apply Swarm")
    parser.add_argument("--platform", type=str, default=None, help="ashby, greenhouse, or omit for both")
    parser.add_argument("--min-score", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--all", action="store_true", help="Apply to all platforms")
    args = parser.parse_args()
    run_swarm(platform=args.platform, min_score=args.min_score,
              limit=args.limit, retry_failed=args.retry_failed, delay=args.delay)
