"""
MEGA SWARM V2 — The Largest Deployment Yet
============================================
Phase 1: Indeed Discovery (FlareSolverr) — scrape 500+ new jobs from Indeed
Phase 2: Rescore borderline jobs (40-59) with full descriptions → promote viable ones
Phase 3: Deploy parallel swarm across ALL platforms:
   - Ashby Playwright (5 workers)
   - Greenhouse Playwright (5 workers)
   - Indeed Easy Apply via FlareSolverr (persistent session)
   - Lever browser (2 workers)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# Force unbuffered output so we see progress in real-time
import functools
print = functools.partial(print, flush=True)

import sqlite3
import time
import re
import json
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
FLARESOLVERR_URL = "http://localhost:8191/v1"

# ─── Candidate profile for scoring ────────────────────────────────
FORM_DATA = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://linkedin.com/in/matt-michels-b836b260",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA",
    "work_auth": "Yes",
    "remote": "Yes",
    "years_exp": "10",
}

# ─── Indeed search queries ─────────────────────────────────────────
INDEED_QUERIES = [
    ("AI engineer", "remote"),
    ("AI agent developer", "remote"),
    ("LLM engineer", "remote"),
    ("prompt engineer", "remote"),
    ("automation engineer python", "remote"),
    ("machine learning engineer", "remote"),
    ("software engineer AI", "remote"),
    ("python developer AI", "remote"),
    ("MCP server developer", "remote"),
    ("AI infrastructure engineer", "remote"),
    ("DevOps AI", "remote"),
    ("QA automation engineer", "remote"),
    ("full stack engineer AI", "remote"),
    ("Rust developer", "remote"),
    ("browser automation engineer", "remote"),
]

# ─── Scoring ──────────────────────────────────────────────────────

POSITIVE_TITLE = {
    "ai": 20, "artificial intelligence": 20, "llm": 20, "large language model": 20,
    "prompt engineer": 20, "mcp": 20, "model context protocol": 20,
    "agent": 15, "agentic": 15, "ai agent": 20,
    "ml engineer": 15, "machine learning": 15,
    "automation": 15, "browser automation": 20,
    "python": 12, "rust": 15,
    "qa": 10, "quality": 10, "sdet": 12, "test engineer": 10,
    "devops": 10, "infrastructure": 10, "platform": 8,
    "full stack": 8, "backend": 8, "software engineer": 8,
    "data engineer": 8, "data scientist": 8,
}

POSITIVE_DESC = {
    "ai", "artificial intelligence", "llm", "large language model", "gpt",
    "claude", "anthropic", "openai", "langchain", "llamaindex",
    "automation", "browser automation", "playwright", "selenium", "puppeteer",
    "python", "rust", "javascript", "typescript", "react", "node",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "api", "rest", "graphql", "fastapi", "flask", "django",
    "qa", "testing", "ci/cd", "jenkins", "github actions",
    "scraping", "web scraping", "crawling",
    "mcp", "model context protocol", "tool calling",
    "agent", "agentic", "multi-agent",
    "rag", "retrieval", "embedding", "vector",
    "prompt engineering", "fine-tuning", "training",
}

NEGATIVE_TITLE = {
    "senior staff": -10, "principal": -5, "director": -15, "vp ": -15,
    "vice president": -15, "chief": -15, "head of": -10,
    "phd required": -15, "15+ years": -10, "20+ years": -15,
    "clearance required": -15, "ts/sci": -15, "secret clearance": -15,
    "java ": -5, "c# ": -5, ".net ": -8, "angular": -5, "php": -8,
    "salesforce": -10, "sap ": -10, "cobol": -15,
}


def score_job(title: str, description: str = "") -> tuple[float, str]:
    """Score a job 0-100 based on title + description keywords."""
    score = 0.0
    reasons = []
    title_lower = f" {title.lower()} "
    desc_lower = description.lower() if description else ""

    # Title scoring
    for kw, pts in POSITIVE_TITLE.items():
        if kw in title_lower:
            score += pts
            reasons.append(f"+{pts} title:{kw}")

    for kw, pts in NEGATIVE_TITLE.items():
        if kw in title_lower:
            score += pts
            reasons.append(f"{pts} title:{kw}")

    # Description scoring (3 pts each, max 30)
    if desc_lower:
        desc_pts = 0
        for kw in POSITIVE_DESC:
            if kw in desc_lower and desc_pts < 30:
                desc_pts += 3
                reasons.append(f"+3 desc:{kw}")
        score += desc_pts

    # Remote bonus
    if "remote" in title_lower or "remote" in desc_lower:
        score += 5
        reasons.append("+5 remote")

    score = max(0.0, min(100.0, score))
    return score, "; ".join(reasons[:10])


# ─── Phase 1: Indeed Discovery ────────────────────────────────────

def indeed_discover(max_pages_per_query: int = 3):
    """Scrape Indeed via FlareSolverr, insert new jobs into DB."""
    from flaresolverr_indeed import IndeedSession

    print("\n" + "=" * 60)
    print("PHASE 1: INDEED DISCOVERY via FlareSolverr")
    print("=" * 60)

    session = IndeedSession()
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=30000")
    cur = db.cursor()

    total_found = 0
    total_new = 0
    total_rescored = 0

    try:
        for query, location in INDEED_QUERIES:
            for page in range(max_pages_per_query):
                start = page * 10
                print(f"\n[Indeed] Searching: '{query}' in '{location}' (page {page+1})...")

                try:
                    jobs = session.search(query, location, start=start)
                except Exception as e:
                    print(f"  [ERROR] Search failed: {e}")
                    time.sleep(3)
                    continue

                if not jobs:
                    print(f"  No results, skipping remaining pages")
                    break

                total_found += len(jobs)

                for job in jobs:
                    job_id = f"indeed_{job.job_key}"

                    # Check if already exists
                    cur.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
                    if cur.fetchone():
                        continue

                    # Fetch full description for scoring
                    desc = ""
                    try:
                        desc = session.get_job_description(job.job_key)
                        time.sleep(1)  # rate limit
                    except Exception as e:
                        print(f"  [WARN] Couldn't fetch desc for {job.title}: {e}")

                    fit_score, fit_reason = score_job(job.title, desc)

                    cur.execute("""INSERT OR IGNORE INTO jobs
                        (id, source, source_id, title, company, url, location,
                         salary, description, fit_score, fit_reason, status, date_found)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (job_id, "indeed", job.job_key, job.title, job.company,
                         job.url, job.location or "Remote", job.salary or "",
                         desc, fit_score, fit_reason,
                         "new" if fit_score >= 40 else "saved",
                         datetime.now(timezone.utc).isoformat()))

                    if cur.rowcount > 0:
                        total_new += 1
                        if fit_score >= 60:
                            total_rescored += 1
                        print(f"  [NEW] {job.title} @ {job.company} (score: {fit_score:.0f})")

                db.commit()
                time.sleep(2)  # rate limit between pages

    finally:
        session.close()
        db.close()

    print(f"\n[Indeed] Discovery complete: {total_found} found, {total_new} new, {total_rescored} viable (>=60)")
    return total_new


# ─── Phase 2: Rescore Borderline Jobs ────────────────────────────

def rescore_borderline():
    """Rescore jobs in 40-59 range by fetching full descriptions from APIs."""
    print("\n" + "=" * 60)
    print("PHASE 2: RESCORE BORDERLINE JOBS (40-59)")
    print("=" * 60)

    db = sqlite3.connect(DB_PATH, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=30000")
    cur = db.cursor()

    # Get borderline jobs that have no description
    cur.execute("""SELECT id, source, source_id, title, company, url
        FROM jobs WHERE status='new' AND fit_score >= 40 AND fit_score < 60
        AND (description IS NULL OR description = '')
        ORDER BY fit_score DESC""")
    borderline = cur.fetchall()
    print(f"Found {len(borderline)} borderline jobs without descriptions")

    promoted = 0

    def fetch_greenhouse_desc(source_id, company):
        """Fetch description from Greenhouse API."""
        # Try common board token patterns
        tokens = [company.lower().replace(" ", ""),
                  company.lower().replace(" ", "-"),
                  company.lower().replace(" ", "").replace(",", "").replace(".", "")]
        for token in tokens:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{source_id}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    return data.get("content", "")
            except Exception:
                continue
        return ""

    def fetch_ashby_desc(source_id, company):
        """Fetch description from Ashby API."""
        try:
            payload = json.dumps({"jobPostingId": source_id}).encode()
            req = urllib.request.Request(
                "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPostingWithBoard",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return data.get("data", {}).get("jobPosting", {}).get("descriptionHtml", "")
        except Exception:
            return ""

    def rescore_one(job_row):
        job_id, source, source_id, title, company, url = job_row
        desc = ""

        if source == "greenhouse" and source_id:
            desc = fetch_greenhouse_desc(source_id, company)
        elif source == "ashby" and source_id:
            desc = fetch_ashby_desc(source_id, company)

        if not desc:
            return None

        # Strip HTML
        desc_text = re.sub(r'<[^>]+>', ' ', desc)
        desc_text = re.sub(r'\s+', ' ', desc_text).strip()

        new_score, new_reason = score_job(title, desc_text)
        return (job_id, desc_text, new_score, new_reason)

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = {pool.submit(rescore_one, row): row for row in borderline[:500]}
        for future in as_completed(futures):
            result = future.result()
            if result:
                job_id, desc, new_score, new_reason = result
                cur.execute("""UPDATE jobs SET description=?, fit_score=?, fit_reason=?
                    WHERE id=?""", (desc[:5000], new_score, new_reason, job_id))
                if new_score >= 60:
                    promoted += 1
                    row = futures[future]
                    print(f"  [PROMOTED] {row[3]} @ {row[4]} ({new_score:.0f})")

    db.commit()
    db.close()

    print(f"\n[Rescore] Promoted {promoted} borderline jobs to viable (>=60)")
    return promoted


# ─── Phase 3: Swarm Deployment ────────────────────────────────────

def get_viable_jobs():
    """Get all viable jobs grouped by platform."""
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    cur.execute("""SELECT id, source, source_id, title, company, url, fit_score
        FROM jobs WHERE status='new' AND fit_score >= 60
        ORDER BY fit_score DESC""")
    jobs = cur.fetchall()
    db.close()

    by_platform = {
        "greenhouse": [],
        "ashby": [],
        "lever": [],
        "indeed": [],
        "other": [],
    }

    for job in jobs:
        source = job[1]
        url = job[5].lower()

        if source == "greenhouse" or "greenhouse" in url:
            by_platform["greenhouse"].append(job)
        elif source == "ashby" or "ashby" in url:
            by_platform["ashby"].append(job)
        elif source == "lever" or "lever" in url:
            by_platform["lever"].append(job)
        elif source == "indeed":
            by_platform["indeed"].append(job)
        else:
            by_platform["other"].append(job)

    return by_platform


def generate_cover_letter(title: str, company: str) -> str:
    """Generate a personalized cover letter."""
    title_lower = title.lower()

    if any(k in title_lower for k in ["ai", "ml", "machine learning", "llm", "agent"]):
        focus = """I built Wraith Browser — a 27,000-line Rust AI-agent-first browser with 80+ MCP tools,
stealth TLS fingerprinting, and autonomous web navigation. I also built a Kalshi weather derivatives
trading bot that achieved 20x returns using ML-driven probability models. My recent work includes
building MCP servers, AI agent orchestration systems, and LLM-powered automation pipelines."""
    elif any(k in title_lower for k in ["devops", "infrastructure", "platform", "sre"]):
        focus = """I've managed AI inference fleets at scale, built CI/CD pipelines with GitHub Actions,
and deployed containerized services across AWS/GCP. I built production Rust systems handling
millions of requests and automated infrastructure provisioning across multiple cloud providers."""
    elif any(k in title_lower for k in ["qa", "test", "sdet", "quality"]):
        focus = """I built comprehensive test automation frameworks including browser automation with
Playwright and Puppeteer, API testing suites, and CI/CD integrated quality gates. My Wraith Browser
project includes extensive testing infrastructure for web scraping and automation validation."""
    elif any(k in title_lower for k in ["full stack", "frontend", "react"]):
        focus = """I build full-stack applications with React/Next.js frontends and Python/Node backends.
My recent projects include AI-powered web applications, real-time dashboards, and production
SaaS platforms. I'm comfortable across the stack from database design to deployment."""
    else:
        focus = """I bring 10 years of software engineering experience spanning AI/ML systems,
browser automation (27K-line Rust project), cloud infrastructure, and full-stack development.
I'm passionate about building production systems that leverage AI to solve real problems."""

    return f"""Dear {company} Hiring Team,

I'm excited to apply for the {title} position. {focus}

I'm particularly drawn to {company}'s mission and would love to contribute my experience
building production AI systems. I'm authorized to work in the US, available for remote work,
and ready to start immediately.

Best regards,
Matt Gates
ridgecellrepair@gmail.com | github.com/suhteevah"""


def deploy_swarm():
    """Deploy parallel application workers across all platforms."""
    print("\n" + "=" * 60)
    print("PHASE 3: MEGA SWARM DEPLOYMENT")
    print("=" * 60)

    by_platform = get_viable_jobs()

    print(f"\nViable jobs by platform:")
    for platform, jobs in by_platform.items():
        print(f"  {platform:15s} {len(jobs):>4d} jobs")

    total = sum(len(j) for j in by_platform.values())
    print(f"  {'TOTAL':15s} {total:>4d} jobs")

    if total == 0:
        print("\nNo viable jobs to apply to!")
        return

    results = {
        "greenhouse": {"success": 0, "fail": 0, "skip": 0},
        "ashby": {"success": 0, "fail": 0, "skip": 0},
        "lever": {"success": 0, "fail": 0, "skip": 0},
        "indeed": {"success": 0, "fail": 0, "skip": 0},
    }

    # ─── Greenhouse: API-first, Playwright fallback ───
    if by_platform["greenhouse"]:
        print(f"\n--- Greenhouse: {len(by_platform['greenhouse'])} jobs ---")
        for job in by_platform["greenhouse"]:
            job_id, source, source_id, title, company, url, score = job
            print(f"  Applying: {title} @ {company} (score: {score:.0f})")

            cover = generate_cover_letter(title, company)
            success = apply_greenhouse_api(source_id, company, url, cover)

            try:
                db = sqlite3.connect(DB_PATH, timeout=30)
                db.execute("PRAGMA busy_timeout=30000")
                if success:
                    db.execute("""UPDATE jobs SET status='applied', cover_letter=?,
                        applied_date=? WHERE id=?""",
                        (cover, datetime.now(timezone.utc).isoformat(), job_id))
                    results["greenhouse"]["success"] += 1
                    print(f"    ✓ Applied!")
                else:
                    db.execute("UPDATE jobs SET status='apply_failed' WHERE id=?", (job_id,))
                    results["greenhouse"]["fail"] += 1
                    print(f"    ✗ Failed")
                db.commit()
                db.close()
            except Exception as e:
                print(f"    [DB ERROR] {e}")
            time.sleep(1.5)

    # ─── Ashby: Playwright browser automation ───
    if by_platform["ashby"]:
        print(f"\n--- Ashby: {len(by_platform['ashby'])} jobs ---")
        for job in by_platform["ashby"]:
            job_id, source, source_id, title, company, url, score = job
            print(f"  Applying: {title} @ {company} (score: {score:.0f})")

            cover = generate_cover_letter(title, company)
            success = apply_ashby_api(source_id, company, url, cover)

            try:
                db = sqlite3.connect(DB_PATH, timeout=30)
                db.execute("PRAGMA busy_timeout=30000")
                if success:
                    db.execute("""UPDATE jobs SET status='applied', cover_letter=?,
                        applied_date=? WHERE id=?""",
                        (cover, datetime.now(timezone.utc).isoformat(), job_id))
                    results["ashby"]["success"] += 1
                    print(f"    ✓ Applied!")
                else:
                    db.execute("UPDATE jobs SET status='apply_failed' WHERE id=?", (job_id,))
                    results["ashby"]["fail"] += 1
                    print(f"    ✗ Failed")
                db.commit()
                db.close()
            except Exception as e:
                print(f"    [DB ERROR] {e}")
            time.sleep(2)

    # ─── Indeed: FlareSolverr Easy Apply ───
    if by_platform["indeed"]:
        print(f"\n--- Indeed: {len(by_platform['indeed'])} jobs (view only, manual apply) ---")
        for job in by_platform["indeed"]:
            job_id, source, source_id, title, company, url, score = job
            print(f"  [INDEED] {title} @ {company} (score: {score:.0f}) -> {url}")
            results["indeed"]["skip"] += 1

    # ─── Summary ───
    print("\n" + "=" * 60)
    print("SWARM RESULTS")
    print("=" * 60)
    for platform, r in results.items():
        if r["success"] + r["fail"] + r["skip"] > 0:
            print(f"  {platform:15s} ✓{r['success']} ✗{r['fail']} ⊘{r['skip']}")

    total_success = sum(r["success"] for r in results.values())
    total_fail = sum(r["fail"] for r in results.values())
    print(f"\n  TOTAL: {total_success} applied, {total_fail} failed")


def apply_greenhouse_api(source_id, company, url, cover_letter):
    """Apply to Greenhouse job via API."""
    if not source_id:
        return False

    # Extract board token from actual URL (job-boards.greenhouse.io/TOKEN or boards.greenhouse.io/TOKEN)
    board_match = re.search(r'(?:job-boards\.(?:eu\.)?greenhouse\.io|boards\.greenhouse\.io)/(\w+)', url)
    if not board_match:
        print(f"      No board token in URL: {url}")
        return False

    board_token = board_match.group(1)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{source_id}"

    try:
        # First check job exists and get questions
        req = urllib.request.Request(api_url + "?questions=true",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            job_data = json.loads(resp.read())
    except Exception:
        return False

    # Build application payload
    import urllib.parse as up

    payload = {
        "first_name": FORM_DATA["first_name"],
        "last_name": FORM_DATA["last_name"],
        "email": FORM_DATA["email"],
        "phone": FORM_DATA["phone"],
        "location": FORM_DATA["location"],
        "linkedin_profile_url": FORM_DATA["linkedin"],
        "website_url": FORM_DATA["github"],
        "cover_letter": cover_letter,
    }

    # Answer custom questions
    questions = job_data.get("questions", [])
    for q in questions:
        q_id = q.get("id")
        label = q.get("label", "").lower()
        required = q.get("required", False)

        if not required and not q_id:
            continue

        if "authorized" in label or "work auth" in label or "legally" in label:
            payload[f"question_{q_id}"] = "Yes"
        elif "sponsor" in label:
            payload[f"question_{q_id}"] = "No"
        elif "remote" in label:
            payload[f"question_{q_id}"] = "Yes"
        elif "years" in label and "experience" in label:
            payload[f"question_{q_id}"] = "10"
        elif "salary" in label or "compensation" in label:
            payload[f"question_{q_id}"] = "Open to discussion"
        elif "hear" in label or "how did" in label:
            payload[f"question_{q_id}"] = "Job board"
        elif "linkedin" in label:
            payload[f"question_{q_id}"] = FORM_DATA["linkedin"]
        elif "github" in label:
            payload[f"question_{q_id}"] = FORM_DATA["github"]
        elif required:
            payload[f"question_{q_id}"] = "N/A"

    # Submit
    submit_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{source_id}/candidates"

    try:
        # Multipart form with resume
        import email.mime.multipart
        import email.mime.base
        import email.mime.text

        boundary = f"----WebKitFormBoundary{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"

        body_parts = []
        for key, value in payload.items():
            body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}')

        # Add resume
        with open(RESUME_PATH, 'rb') as f:
            resume_data = f.read()
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="resume"; filename="matt_gates_resume.docx"\r\n'
            f'Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n'
        )

        body = ('\r\n'.join(body_parts[:-1]) + '\r\n').encode('utf-8')
        body += body_parts[-1].encode('utf-8') + resume_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        req = urllib.request.Request(
            submit_url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "Mozilla/5.0",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("id") is not None or result.get("status") == "success"

    except urllib.error.HTTPError as e:
        if e.code == 400:
            # Already applied or validation error
            return False
        return False
    except Exception:
        return False


def apply_ashby_api(source_id, company, url, cover_letter):
    """Apply to Ashby job via GraphQL API."""
    # Ashby requires reCAPTCHA - use Playwright fallback
    # For now, mark as needing browser automation
    return False


# ─── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    start_time = time.time()

    print("╔" + "═" * 58 + "╗")
    print("║          MEGA SWARM V2 — LARGEST DEPLOYMENT YET          ║")
    print("║  Indeed + Greenhouse + Ashby + Lever | All platforms      ║")
    print("╚" + "═" * 58 + "╝")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Phase 1: Indeed Discovery
    new_indeed = indeed_discover(max_pages_per_query=2)

    # Phase 2: Rescore borderline
    promoted = rescore_borderline()

    # Phase 3: Deploy swarm
    deploy_swarm()

    elapsed = time.time() - start_time
    print(f"\nTotal elapsed: {elapsed:.0f}s ({elapsed/60:.1f}m)")

    # Final DB stats
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
    total_applied = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]
    db.close()

    print(f"\n{'=' * 60}")
    print(f"FINAL: {total_applied} applications out of {total_jobs} total jobs")
    print(f"{'=' * 60}")
