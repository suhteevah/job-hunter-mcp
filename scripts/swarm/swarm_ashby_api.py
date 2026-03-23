"""
Ashby API Swarm — Pure HTTP Application Submitter
===================================================
Uses Ashby's public API to submit applications directly.
NO browser needed — fetches form definitions, builds payload, submits via HTTP.

Run: .venv\Scripts\python.exe swarm_ashby_api.py [--limit N] [--resume-from N]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import re
import sqlite3
import time
import traceback
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
LOG_PATH = r"J:\job-hunter-mcp\swarm_ashby_log.txt"
RESULTS_PATH = r"J:\job-hunter-mcp\swarm_ashby_results.md"

ASHBY_API = "https://api.ashbyhq.com"

APPLICANT = {
    "name": "Matt Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "+15307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
    "current_company": "Ridge Cell Repair LLC (Self-employed)",
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


# ─── Cover Letters ───────────────────────────────────────────────────

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
    if any(kw in tl for kw in ["backend", "back-end", "api", "server", "data engineer"]):
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


# ─── Ashby API ───────────────────────────────────────────────────────

def extract_ashby_posting_id(url: str) -> str:
    """Extract the job posting UUID from an Ashby URL."""
    # Pattern: jobs.ashbyhq.com/{company}/{uuid}
    m = re.search(r'jobs\.ashbyhq\.com/[^/]+/([a-f0-9-]{36})', url)
    return m.group(1) if m else ""


def fetch_job_posting_info(posting_id: str) -> dict:
    """Fetch job posting info including form definition from Ashby API."""
    try:
        resp = requests.post(
            f"{ASHBY_API}/posting-api/job-board-posting",
            json={"jobPostingId": posting_id},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        log(f"    API info failed: HTTP {resp.status_code}")
        return {}
    except Exception as e:
        log(f"    API info error: {e}")
        return {}


def build_field_submissions(form_def: dict, company: str, title: str) -> list:
    """Build field submissions based on form definition."""
    submissions = []
    fields = form_def.get("formDefinition", {}).get("sections", [])

    cover_letter = generate_cover_letter(company, title)

    for section in fields:
        for field_entry in section.get("fieldEntries", []):
            field = field_entry.get("field", {})
            descr = field_entry.get("descriptionPlain", "")
            path = field.get("path", "")
            ftype = field.get("type", "")
            is_required = field_entry.get("isRequired", False)
            title_text = field.get("title", "").lower()

            # System fields
            if path == "_systemfield_name":
                submissions.append({"path": path, "value": APPLICANT["name"]})
            elif path == "_systemfield_email":
                submissions.append({"path": path, "value": APPLICANT["email"]})
            elif path == "_systemfield_phone":
                submissions.append({"path": path, "value": APPLICANT["phone"]})
            elif path == "_systemfield_resume":
                # File upload — handled separately in multipart
                submissions.append({"path": path, "value": "resume_file"})
            elif path == "_systemfield_cover_letter":
                submissions.append({"path": path, "value": cover_letter})
            elif path == "_systemfield_current_company":
                submissions.append({"path": path, "value": APPLICANT["current_company"]})
            elif path == "_systemfield_current_location":
                submissions.append({"path": path, "value": APPLICANT["location"]})
            elif path == "_systemfield_linkedin_url" or "linkedin" in title_text:
                submissions.append({"path": path, "value": APPLICANT["linkedin"]})
            elif path == "_systemfield_github_url" or "github" in title_text:
                submissions.append({"path": path, "value": APPLICANT["github"]})
            elif path == "_systemfield_website_url" or "website" in title_text or "portfolio" in title_text:
                submissions.append({"path": path, "value": APPLICANT["github"]})
            else:
                # Custom fields — answer based on label
                answer = answer_custom_field(title_text, descr, ftype, company, title, field, is_required)
                if answer is not None:
                    submissions.append({"path": path, "value": answer})

    return submissions


def answer_custom_field(label: str, descr: str, ftype: str, company: str, title: str, field: dict, required: bool):
    """Answer a custom Ashby field based on its label and type."""
    ll = label.lower() + " " + descr.lower()

    # ValueSelect / MultiValueSelect
    if ftype in ("ValueSelect", "MultiValueSelect"):
        options = field.get("selectableValues", [])
        opt_labels = [o.get("label", "") for o in options]
        opt_values = [o.get("value", "") for o in options]

        # Work authorization
        if any(kw in ll for kw in ["authorized", "authorization", "lawfully", "eligible to work"]):
            for i, o in enumerate(opt_labels):
                ol = o.lower()
                if "yes" in ol or "authorized" in ol or "do not require" in ol:
                    return opt_values[i]

        # Sponsorship
        if any(kw in ll for kw in ["sponsor", "visa", "immigration"]):
            for i, o in enumerate(opt_labels):
                ol = o.lower()
                if ol == "no" or "not require" in ol or "will not" in ol or "do not" in ol:
                    return opt_values[i]

        # How did you hear
        if any(kw in ll for kw in ["how did you", "where did you", "hear about"]):
            for i, o in enumerate(opt_labels):
                if any(x in o.lower() for x in ["job board", "website", "online", "other"]):
                    return opt_values[i]
            return opt_values[-1] if opt_values else None

        # Remote / relocation
        if any(kw in ll for kw in ["remote", "relocation", "relocate", "hybrid"]):
            for i, o in enumerate(opt_labels):
                if "yes" in o.lower():
                    return opt_values[i]

        # Gender/race/veteran/disability — decline
        if any(kw in ll for kw in ["gender", "race", "veteran", "disability", "ethnicity", "demographic"]):
            for i, o in enumerate(opt_labels):
                if any(x in o.lower() for x in ["decline", "prefer not", "not wish"]):
                    return opt_values[i]
            return opt_values[-1] if opt_values else None

        # Agree/consent
        if any(kw in ll for kw in ["agree", "consent", "acknowledge", "privacy"]):
            for i, o in enumerate(opt_labels):
                if any(x in o.lower() for x in ["agree", "yes", "i agree", "acknowledge"]):
                    return opt_values[i]

        # Boolean yes/no — default to first option
        if required and opt_values:
            return opt_values[0]
        return None

    # Boolean
    if ftype == "Boolean":
        if any(kw in ll for kw in ["authorized", "legally", "eligible", "background", "drug"]):
            return True
        if any(kw in ll for kw in ["sponsor", "visa"]):
            return False
        if required:
            return True
        return None

    # Number
    if ftype in ("Number", "Score"):
        if any(kw in ll for kw in ["year", "experience"]):
            return 10
        if any(kw in ll for kw in ["salary", "compensation", "pay"]):
            return 150000
        if required:
            return 0
        return None

    # String / LongText / Email
    if ftype in ("String", "LongText"):
        if "linkedin" in ll:
            return APPLICANT["linkedin"]
        if "github" in ll or "portfolio" in ll or "website" in ll:
            return APPLICANT["github"]
        if any(kw in ll for kw in ["salary", "compensation", "pay", "expectation"]):
            return "$150,000 USD"
        if any(kw in ll for kw in ["year", "experience"]):
            return "10"
        if any(kw in ll for kw in ["location", "city", "where", "based"]):
            return APPLICANT["location"]
        if any(kw in ll for kw in ["notice", "start", "available"]):
            return "Immediately"
        if any(kw in ll for kw in ["cover", "why", "interest", "excite", "motivation", "tell us", "about you"]):
            return generate_cover_letter(company, title)
        if any(kw in ll for kw in ["current company", "employer"]):
            return APPLICANT["current_company"]
        if any(kw in ll for kw in ["refer", "who referred"]):
            return "N/A"
        if any(kw in ll for kw in ["how did you", "hear about", "find us", "find this"]):
            return "Job board"
        if any(kw in ll for kw in ["pronoun"]):
            return "he/him"
        if any(kw in ll for kw in ["country"]):
            return "United States"
        if any(kw in ll for kw in ["address"]):
            return "Chico, CA"
        if required:
            return "N/A"
        return None

    # Phone
    if ftype == "Phone":
        return APPLICANT["phone"]

    # SocialLink
    if ftype == "SocialLink":
        if "linkedin" in ll:
            return APPLICANT["linkedin"]
        if "github" in ll:
            return APPLICANT["github"]
        return APPLICANT["github"]

    # Date
    if ftype == "Date":
        if any(kw in ll for kw in ["start", "available", "earliest"]):
            return datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return None

    # File — handled separately
    if ftype == "File":
        return "resume_file"

    return None


def submit_application(posting_id: str, field_submissions: list, company: str) -> dict:
    """Submit application via Ashby API using multipart form data."""
    try:
        # Build the applicationForm JSON
        app_form = {
            "fieldSubmissions": [
                s for s in field_submissions if s.get("value") != "resume_file"
            ]
        }

        # Check if we need to upload a resume
        has_resume = any(s.get("value") == "resume_file" for s in field_submissions)

        if has_resume and os.path.exists(RESUME_PATH):
            # Multipart submission with file
            files = {
                "resume_file": (
                    "matt_gates_resume_ai.docx",
                    open(RESUME_PATH, "rb"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
            }
            data = {
                "applicationForm": json.dumps(app_form),
                "jobPostingId": posting_id,
            }
            resp = requests.post(
                f"{ASHBY_API}/posting-api/application-form/submit",
                data=data,
                files=files,
                timeout=30,
            )
        else:
            # JSON-only submission
            resp = requests.post(
                f"{ASHBY_API}/posting-api/application-form/submit",
                json={
                    "applicationForm": app_form,
                    "jobPostingId": posting_id,
                },
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

        if resp.status_code == 200:
            result = resp.json()
            if result.get("blocked"):
                block_msg = result.get("blockMessageForCandidateHtml", "Blocked")
                return {"success": False, "error": f"Blocked: {block_msg[:100]}"}
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── DB Operations ──────────────────────────────────────────────────

def get_ashby_jobs(min_score: float = 60.0) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score, source
        FROM jobs
        WHERE status = 'new'
          AND fit_score >= ?
          AND source = 'ashby'
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
    delay: float = 2.0,
):
    start_time = datetime.now(timezone.utc)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"=== ASHBY API SWARM {start_time.isoformat()} ===\n")

    log("=" * 70)
    log("ASHBY API SWARM — Pure HTTP, No Browser")
    log("=" * 70)

    all_jobs = get_ashby_jobs(min_score)
    log(f"Found {len(all_jobs)} Ashby jobs (score >= {min_score})")

    batch = all_jobs[resume_from:]
    if limit > 0:
        batch = batch[:limit]

    log(f"This batch: {len(batch)} jobs (resume_from={resume_from}, limit={limit or 'all'})")
    log(f"Delay between apps: {delay}s")
    log("")

    successes = []
    failures = []
    blocked = []

    for i, job in enumerate(batch):
        job_num = i + 1 + resume_from
        posting_id = extract_ashby_posting_id(job["url"])

        if not posting_id:
            log(f"[{job_num}] SKIP (no posting ID) {job['company']} — {job['title'][:50]}")
            failures.append({**job, "error": "Could not extract posting ID"})
            continue

        log(f"[{job_num}/{len(batch)+resume_from}] {job['company']} — {job['title'][:50]} (score={job['fit_score']})")

        try:
            # Step 1: Fetch form definition
            info = fetch_job_posting_info(posting_id)
            if not info:
                log(f"  FAILED: Could not fetch job info")
                failures.append({**job, "error": "API info fetch failed"})
                update_job_status(job["id"], "apply_failed")
                time.sleep(delay)
                continue

            job_info = info.get("info", info)
            if not info.get("formDefinition") and not job_info.get("formDefinition"):
                # Try alternate response structure
                log(f"  WARN: No form definition in response, attempting submission anyway")

            # Step 2: Build field submissions
            field_subs = build_field_submissions(info, job["company"], job["title"])
            cl = generate_cover_letter(job["company"], job["title"])
            log(f"  Built {len(field_subs)} field submissions")

            # Step 3: Submit
            result = submit_application(posting_id, field_subs, job["company"])

            if result.get("success"):
                log(f"  >>> SUCCESS <<<")
                successes.append(job)
                update_job_status(job["id"], "applied", cover_letter=cl)
            elif "Blocked" in result.get("error", "") or "already" in result.get("error", "").lower():
                log(f"  BLOCKED: {result.get('error', '')[:100]}")
                blocked.append({**job, "error": result.get("error", "")})
                update_job_status(job["id"], "apply_failed")
            else:
                error = result.get("error", "unknown")
                log(f"  FAILED: {error[:150]}")
                failures.append({**job, "error": error})
                update_job_status(job["id"], "apply_failed")

        except Exception as e:
            tb = traceback.format_exc()
            log(f"  EXCEPTION: {e}")
            log(f"  {tb[:200]}")
            failures.append({**job, "error": str(e)})
            update_job_status(job["id"], "apply_failed")

        # Progress every 25
        if (i + 1) % 25 == 0:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            rate = (i + 1) / (elapsed / 60) if elapsed > 0 else 0
            log(f"\n--- Progress: {i+1}/{len(batch)} | OK={len(successes)} FAIL={len(failures)} | {rate:.1f}/min ---\n")

        if i < len(batch) - 1:
            time.sleep(delay)

    # ── Final Report ─────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

    log(f"\n{'='*70}")
    log(f"ASHBY API SWARM COMPLETE")
    log(f"{'='*70}")
    log(f"Duration: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    log(f"Success:  {len(successes)}")
    log(f"Failed:   {len(failures)}")
    log(f"Blocked:  {len(blocked)}")
    log(f"Rate:     {len(successes)/(elapsed/60):.1f} apps/min" if elapsed > 60 else "")
    log(f"{'='*70}")

    with open(RESULTS_PATH, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# Ashby API Swarm Results\n\n")
        f.write(f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**Duration**: {elapsed/60:.1f} min\n")
        f.write(f"**Method**: Pure HTTP API (no browser)\n\n")
        f.write(f"## Summary\n")
        f.write(f"- **Success**: {len(successes)}\n")
        f.write(f"- **Failed**: {len(failures)}\n")
        f.write(f"- **Blocked**: {len(blocked)}\n")
        f.write(f"- **Total Attempted**: {len(successes)+len(failures)+len(blocked)}\n\n")

        if successes:
            f.write(f"## Successful Applications ({len(successes)})\n\n")
            for j in successes:
                f.write(f"- [{j['fit_score']}] **{j['company']}** — {j['title']}\n")

        if failures:
            f.write(f"\n## Failed ({len(failures)})\n\n")
            by_error = {}
            for j in failures:
                err = j.get("error", "unknown")[:60]
                by_error.setdefault(err, []).append(j)
            for err, jobs in sorted(by_error.items(), key=lambda x: -len(x[1])):
                f.write(f"### {err} ({len(jobs)})\n")
                for j in jobs[:10]:
                    f.write(f"- {j['company']} — {j['title'][:50]}\n")
                if len(jobs) > 10:
                    f.write(f"- *...and {len(jobs)-10} more*\n")
                f.write("\n")

        if blocked:
            f.write(f"\n## Blocked ({len(blocked)})\n\n")
            for j in blocked:
                f.write(f"- {j['company']} — {j['title']} — {j.get('error','')[:60]}\n")

    log(f"Results: {RESULTS_PATH}")
    log(f"Log: {LOG_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ashby API Swarm")
    parser.add_argument("--min-score", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=0, help="Max jobs (0=unlimited)")
    parser.add_argument("--resume-from", type=int, default=0, help="Skip first N jobs")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between apps")
    args = parser.parse_args()

    run_swarm(
        min_score=args.min_score,
        limit=args.limit,
        resume_from=args.resume_from,
        delay=args.delay,
    )
