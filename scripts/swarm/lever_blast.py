"""Lever API Blast — Direct HTTP submission, no browser."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import re
import os
import sqlite3
import requests
import time
from datetime import datetime, timezone

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"

APPLICANT = {
    "name": "Matt Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "org": "Ridge Cell Repair LLC",
    "urls[LinkedIn]": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "urls[GitHub]": "https://github.com/suhteevah",
    "comments": "",  # filled per-job as cover letter
}


def generate_cover_letter(company, title):
    tl = title.lower()
    if any(kw in tl for kw in ["ai", "ml", "machine learning", "data", "llm"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years of software engineering "
            f"experience, I have built production AI/ML systems including LLM-powered applications, "
            f"RAG pipelines, autonomous agents, and ML inference infrastructure. I deployed a weather "
            f"prediction trading bot achieving 20x returns and built distributed AI inference fleets. "
            f"I've authored 10+ production MCP servers and a 27K-line Rust browser automation framework. "
            f"My expertise in Python, FastAPI, and cloud infrastructure makes me a strong fit for {company}."
        )
    if any(kw in tl for kw in ["infrastructure", "platform", "backend", "storage"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years building scalable infrastructure "
            f"and distributed systems, I bring deep expertise in CI/CD, container orchestration, and "
            f"production reliability. I've built GPU inference clusters, industrial automation systems, "
            f"and cloud infrastructure. I bring strong systems thinking to {company}'s team."
        )
    return (
        f"I am excited about the {title} role at {company}. With 10 years spanning AI/ML systems, "
        f"cloud infrastructure, and full-stack development, I bring a versatile skillset shipping "
        f"production systems at scale — autonomous AI agents, distributed inference, 10+ MCP servers."
    )


def extract_lever_info(url):
    """Extract (company_slug, posting_id) from Lever URL."""
    m = re.search(r'jobs\.lever\.co/([^/]+)/([a-f0-9-]+)', url)
    if m:
        return m.group(1), m.group(2)
    return None, None


def apply_lever(company_slug, posting_id, company, title):
    """Submit via Lever apply page POST (form submission)."""
    apply_url = f"https://jobs.lever.co/plaid/{posting_id}/apply"
    cover_letter = generate_cover_letter(company, title)

    # First GET the apply page to get any hidden fields / CSRF tokens
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        page = session.get(apply_url, timeout=15)
        if page.status_code != 200:
            return {"success": False, "error": f"Apply page HTTP {page.status_code}"}

        # Extract hidden fields
        import re as _re
        hidden_fields = {}
        for m in _re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', page.text):
            hidden_fields[m.group(1)] = m.group(2)
        # Also match reversed order (value before name)
        for m in _re.finditer(r'<input[^>]*value=["\']([^"\']*)["\'][^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\']', page.text):
            hidden_fields[m.group(2)] = m.group(1)

        # Extract card field IDs for EEO questions
        card_fields = {}
        for m in _re.finditer(r'name=["\']cards\[([^\]]+)\]\[([^\]]+)\]["\']', page.text):
            card_id = m.group(1)
            field_name = m.group(2)
            if card_id not in card_fields:
                card_fields[card_id] = []
            card_fields[card_id].append(field_name)

        data = {
            **hidden_fields,
            "name": APPLICANT["name"],
            "email": APPLICANT["email"],
            "phone": APPLICANT["phone"],
            "org": APPLICANT["org"],
            "urls[LinkedIn]": APPLICANT["urls[LinkedIn]"],
            "urls[GitHub]": APPLICANT["urls[GitHub]"],
            "additional-information": cover_letter,
            "comments": cover_letter,
        }

        # For EEO card fields, select "Decline to self-identify" options
        for card_id, fields in card_fields.items():
            data[f"cards[{card_id}][baseTemplate]"] = ""
            for f in fields:
                if f == "field0":
                    data[f"cards[{card_id}][{f}]"] = "Decline To Self Identify"

        files = {}
        resume_fh = None
        if os.path.exists(RESUME_PATH):
            resume_fh = open(RESUME_PATH, "rb")
            files["resume"] = (
                "matt_gates_resume_ai.docx",
                resume_fh,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        # POST to the apply URL
        resp = session.post(
            apply_url,
            data=data,
            files=files,
            timeout=30,
            allow_redirects=True,
        )

        if resume_fh:
            resume_fh.close()

        resp_text = resp.text.lower()

        # Check for success indicators
        if resp.status_code in (200, 302) and any(x in resp_text for x in [
            "thank you", "application has been", "submitted",
            "received your application", "we have received",
            "thanks for applying", "thanks for your interest"
        ]):
            return {"success": True, "msg": "Confirmed"}

        if "already applied" in resp_text or "already submitted" in resp_text:
            return {"success": False, "error": "Already applied", "already": True}

        # Check redirect URL
        if resp.url and ("confirmation" in resp.url or "thank" in resp.url):
            return {"success": True, "msg": f"Redirected to {resp.url[:80]}"}

        # If we got redirected back to the posting, might still be success
        if resp.status_code == 200 and resp.url != apply_url:
            return {"success": True, "msg": f"Redirected to {resp.url[:80]}"}

        return {"success": False, "error": f"HTTP {resp.status_code}, no confirmation detected. URL: {resp.url[:80]}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def update_job_status(job_id, status, cover_letter=None):
    conn = sqlite3.connect(DB_PATH)
    if cover_letter:
        conn.execute("UPDATE jobs SET status=?, applied_date=?, cover_letter=? WHERE id=?",
                      (status, datetime.now(timezone.utc).isoformat(), cover_letter, job_id))
    else:
        conn.execute("UPDATE jobs SET status=?, applied_date=? WHERE id=?",
                      (status, datetime.now(timezone.utc).isoformat(), job_id))
    conn.commit()
    conn.close()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    jobs = conn.execute("""
        SELECT id, title, company, url, fit_score FROM jobs
        WHERE status='new' AND fit_score >= 60 AND source='lever'
        ORDER BY fit_score DESC
    """).fetchall()
    conn.close()

    print(f"=== LEVER API BLAST — {len(jobs)} jobs ===\n")

    successes = 0
    failures = 0

    for i, job in enumerate(jobs):
        slug, pid = extract_lever_info(job["url"])
        if not slug or not pid:
            print(f"  [{i+1}] SKIP (bad URL) {job['company']} — {job['title']}")
            failures += 1
            continue

        print(f"  [{i+1}/{len(jobs)}] {job['company']} — {job['title'][:50]} (score={job['fit_score']})")

        result = apply_lever(slug, pid, job["company"], job["title"])

        if result.get("success"):
            print(f"    >>> SUCCESS (ID: {result.get('app_id', 'n/a')}) <<<")
            cl = generate_cover_letter(job["company"], job["title"])
            update_job_status(job["id"], "applied", cover_letter=cl)
            successes += 1
        else:
            print(f"    FAILED: {result.get('error', 'unknown')[:100]}")
            update_job_status(job["id"], "apply_failed")
            failures += 1

        time.sleep(1.5)

    print(f"\n=== LEVER BLAST DONE: {successes} success, {failures} fail ===")


if __name__ == "__main__":
    main()
