"""
MEGA SWARM — Overnight Autonomous Application Dispatcher
=========================================================
Pulls ALL viable jobs from DB (score >= 60), applies via every available channel:
  1. Greenhouse Direct → API (board + job_id from URL)
  2. Greenhouse Wrapped → API (guess board token from company/URL)
  3. Ashby → GraphQL API (may hit captcha on some)
  4. Lever → Log for Wraith browser follow-up
  5. Everything else → Log with classification

Run and go to bed. Wake up to results.
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
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
RESULTS_PATH = r"J:\job-hunter-mcp\swarm_mega_results.md"
LOG_PATH = r"J:\job-hunter-mcp\swarm_mega_log.txt"

APPLICANT = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
}

# Board token guesses for wrapped Greenhouse URLs
KNOWN_BOARDS = {
    "samsara": "samsara",
    "databricks": "databricks",
    "stripe": "stripe",
    "datadog": "datadog",
    "coreweave": "coreweave",
    "cockroach labs": "cockroachlabs",
    "airbnb": "airbnb",
    "elastic": "elastic",
    "brex": "brex",
    "mongodb": "mongodb",
    "instacart": "instacart",
    "coinbase": "coinbase",
    "cloudflare": "cloudflare",
    "nuro": "nuro",
    "reddit": "reddit",
    "anthropic": "anthropic",
    "scale ai": "scaleai",
    "airtable": "airtable",
    "gitlab": "gitlab",
    "gusto": "gusto",
    "twilio": "twilio",
    "assemblyai": "assemblyai",
    "clickhouse": "clickhouse",
    "chainguard": "chainguard",
    "planetscale": "planetscale",
    "ziprecruiter": "ziprecruiter",
    "within": "agencywithin",
    "remote people": "remotepeople",
    "figma": "figma",
    "notion": "notion",
    "plaid": "plaid",
    "ramp": "ramp",
    "anyscale": "anyscale",
    "modal": "modal",
    "vercel": "vercel",
    "hashicorp": "hashicorp",
    "grafana labs": "grafanalabs",
    "snap": "snap",
    "pinterest": "pinterest",
    "lyft": "lyft",
    "doordash": "doordash",
    "robinhood": "robinhood",
    "discord": "discord",
    "square": "square",
    "block": "block",
    "dbt labs": "daboracleinc",
    "confluent": "confluent",
    "cockroach": "cockroachlabs",
    "temporal": "temporal",
    "tailscale": "tailscale",
    "fly.io": "flyio",
    "supabase": "supabase",
    "retool": "retool",
    "linear": "linear",
    "replit": "replit",
    "sourcegraph": "sourcegraph",
    "mux": "mux",
    "livekit": "livekit",
    "weights & biases": "wandb",
    "wandb": "wandb",
    "hugging face": "huggingface",
    "huggingface": "huggingface",
    "together ai": "togetherai",
    "fireworks ai": "fireworksai",
    "replicate": "replicate",
    "cursor": "anysphere",
    "midjourney": "midjourney",
    "stability ai": "stabilityai",
    "perplexity": "perplexity",
    "cohere": "cohere",
    "adept": "adept",
    "deepmind": "deepmind",
    "openai": "openai",
    "mistral": "mistral",
    "inflection": "inflection",
    "character.ai": "characterai",
}


def log(msg: str):
    """Write to both stdout and log file."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── Cover Letter Generation ────────────────────────────────────────

def generate_cover_letter(company: str, title: str) -> str:
    """Generate a personalized cover letter based on company and role."""
    cl = company.lower()
    tl = title.lower()

    # AI/ML focused
    if any(kw in tl for kw in ["ai", "ml", "machine learning", "data scientist", "llm", "nlp", "genai"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years of software engineering "
            f"experience, I have built production AI/ML systems including LLM-powered applications, "
            f"RAG pipelines, autonomous agents, and ML inference infrastructure. I have personally "
            f"deployed end-to-end ML solutions serving real users — from a weather prediction trading "
            f"bot achieving 20x returns to distributed AI inference fleets. My hands-on experience "
            f"with Python, FastAPI, vector databases, and cloud infrastructure makes me a strong "
            f"fit for {company}'s engineering team."
        )

    # Infrastructure/Platform
    if any(kw in tl for kw in ["infrastructure", "platform", "sre", "devops", "cloud", "systems"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years of experience building "
            f"scalable infrastructure, distributed systems, and cloud-native platforms, I bring deep "
            f"expertise in CI/CD automation, container orchestration, and production reliability. "
            f"I have built and maintained systems handling high-throughput workloads and have "
            f"experience with both industrial automation (ESP32, PID controllers) and cloud "
            f"infrastructure (AWS, Docker, Kubernetes). I would bring strong systems thinking "
            f"to {company}'s infrastructure team."
        )

    # Full-stack/Frontend
    if any(kw in tl for kw in ["full stack", "fullstack", "frontend", "front-end", "react", "typescript"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years of software "
            f"engineering experience spanning full-stack development, I have built production "
            f"applications using React, TypeScript, Next.js, and Python backends. My recent "
            f"work includes AI-powered browser automation tools (27K lines Rust), real-time "
            f"trading interfaces, and developer tooling. I am passionate about building "
            f"high-quality user experiences backed by robust engineering."
        )

    # Backend/API
    if any(kw in tl for kw in ["backend", "back-end", "api", "server", "microservice"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years building "
            f"production backend systems, I bring deep expertise in Python, Rust, TypeScript, "
            f"and distributed architectures. I have built high-performance APIs, data pipelines, "
            f"and microservices handling real-world scale. My background spans ML infrastructure, "
            f"real-time systems, and developer tooling — making me a versatile addition to "
            f"{company}'s engineering team."
        )

    # Security
    if any(kw in tl for kw in ["security", "appsec", "infosec", "cyber"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years of engineering "
            f"experience including browser security research, TLS fingerprinting, and building "
            f"secure systems from embedded hardware to cloud infrastructure, I bring a deep "
            f"understanding of both offensive and defensive security. My work on AI-driven "
            f"browser automation required solving real-world security challenges including "
            f"anti-bot detection, credential management, and secure communication protocols."
        )

    # Default
    return (
        f"I am excited about the {title} role at {company}. With 10 years of software "
        f"engineering experience spanning AI/ML systems, cloud infrastructure, full-stack "
        f"development, and industrial automation, I bring a versatile skillset and proven "
        f"track record of shipping production systems. I have built everything from autonomous "
        f"trading bots to distributed inference fleets to hardware test fixtures, and I am "
        f"passionate about solving hard problems with great engineering."
    )


# ─── Greenhouse API Applier ─────────────────────────────────────────

def answer_question(label: str, field_name: str, field_type: str, values: list, company: str, title: str):
    """Smart question answerer for Greenhouse forms."""
    ll = label.lower()
    fn = field_name.lower() if field_name else ""

    # Standard fields handled by top-level params
    if fn in ("first_name", "last_name", "email", "phone", "resume", "resume_text",
              "cover_letter", "cover_letter_text"):
        return None

    # Text input questions
    if field_type in ("input_text", "textarea", "input_hidden"):
        if "linkedin" in ll:
            return APPLICANT["linkedin"]
        if "github" in ll or "portfolio" in ll or "website" in ll:
            return APPLICANT["github"]
        if "personal email" in ll:
            return APPLICANT["email"]
        if "salary" in ll or "compensation" in ll or "pay" in ll:
            return "$150,000 USD"
        if "location" in ll or "city" in ll or "based" in ll or "where" in ll:
            return APPLICANT["location"]
        if "year" in ll and ("experience" in ll or "ai" in ll or "ml" in ll or "python" in ll or "software" in ll):
            return "10"
        if "refer" in ll:
            return "No"
        if "how did you" in ll and ("find" in ll or "hear" in ll):
            return "Job board"
        if "current" in ll and "company" in ll:
            return "Self-employed / Freelance"
        if any(x in ll for x in ["facebook", "instagram", "twitter", "social media"]):
            return "N/A"
        if any(x in ll for x in ["connection", "client", "partner"]):
            return "N/A"
        if "cover" in ll or "additional" in ll or "anything else" in ll:
            return generate_cover_letter(company, title)
        if "notice" in ll or "start date" in ll or "available" in ll:
            return "Immediately"
        if "country" in ll:
            return "United States"
        if "state" in ll or "province" in ll:
            return "California"
        if "zip" in ll or "postal" in ll:
            return "95928"
        if "address" in ll or "street" in ll:
            return "Chico, CA"
        if "pronoun" in ll:
            return "he/him"
        return None

    # Select/radio questions
    if field_type in ("multi_value_single_select", "multi_value_multi_select"):
        if not values:
            return None

        # Work authorization
        if "authorized" in ll or "authorization" in ll or "lawfully" in ll or "eligible" in ll:
            for v in values:
                vl = v.get("label", "").lower()
                if "do not require" in vl or ("authorized" in vl and "do not" in vl):
                    return v["value"]
            for v in values:
                if "yes" in v.get("label", "").lower() and "not" not in v.get("label", "").lower():
                    return v["value"]
            return values[0]["value"]

        # Sponsorship
        if "sponsor" in ll or "visa" in ll or "immigration" in ll:
            for v in values:
                vl = v.get("label", "").lower()
                if vl == "no" or "will not" in vl or "do not" in vl:
                    return v["value"]
            return values[0]["value"]

        # Remote/hybrid/office
        if any(kw in ll for kw in ["hybrid", "remote", "office", "in-person", "on-site", "relocation"]):
            for v in values:
                if v.get("label", "").lower() == "yes":
                    return v["value"]
            return values[0]["value"]

        # Comfortable with / agree / consent
        if any(kw in ll for kw in ["comfortable", "agree", "privacy", "consent", "acknowledge", "dog"]):
            for v in values:
                vl = v.get("label", "").lower()
                if any(x in vl for x in ["agree", "yes", "i agree"]):
                    return v["value"]
            return values[0]["value"]

        # ML/AI experience
        if any(kw in ll for kw in ["ml", "machine learning", "ai", "deploy", "production", "pipeline", "measurable"]):
            for v in values:
                vl = v.get("label", "").lower()
                if any(x in vl for x in ["yes", "personally built", "owned", "measurable", "distributed", "production"]):
                    return v["value"]
            return values[-1]["value"]

        # Gender/race/veteran/disability — decline
        if any(kw in ll for kw in ["gender", "race", "veteran", "disability", "ethnicity", "demographic"]):
            for v in values:
                vl = v.get("label", "").lower()
                if "decline" in vl or "prefer not" in vl:
                    return v["value"]
            return values[-1]["value"]

        # Connection / referral — no
        if "connection" in ll or "client" in ll:
            for v in values:
                if v.get("label", "").lower() == "no":
                    return v["value"]
            return values[0]["value"]

        # Default: pick first
        return values[0]["value"]

    return None


def extract_greenhouse_info(url: str, company: str) -> dict:
    """Extract board token and job_id from a Greenhouse URL."""
    # Direct: job-boards.greenhouse.io/{board}/jobs/{id}
    m = re.search(r'job-boards\.(?:eu\.)?greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return {"board": m.group(1), "job_id": m.group(2), "eu": "eu." in url}

    # boards.greenhouse.io/{board}/jobs/{id}
    m = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return {"board": m.group(1), "job_id": m.group(2), "eu": False}

    # Wrapped: extract gh_jid and guess board
    m = re.search(r'gh_jid=(\d+)', url)
    if m:
        job_id = m.group(1)

        # Check if board is explicitly in the URL (e.g., CoreWeave)
        board_match = re.search(r'[?&]board=([^&]+)', url)
        if board_match:
            return {"board": board_match.group(1), "job_id": job_id, "eu": False}

        # Guess board from known companies
        cl = company.lower().strip()
        if cl in KNOWN_BOARDS:
            return {"board": KNOWN_BOARDS[cl], "job_id": job_id, "eu": False}

        # Try company name variations as board token
        guesses = [
            cl.replace(" ", "").replace(".", "").replace(",", ""),
            cl.replace(" ", "-"),
            cl.replace(" ", ""),
            cl.split()[0] if cl else "",
        ]
        return {"board": guesses[0], "job_id": job_id, "eu": False, "guesses": guesses}

    return None


def apply_greenhouse_api(job: dict) -> dict:
    """Apply to a Greenhouse job via their public boards API."""
    url = job["url"]
    company = job["company"]
    title = job["title"]

    info = extract_greenhouse_info(url, company)
    if not info:
        return {"success": False, "error": "Could not extract board/job_id from URL"}

    board = info["board"]
    job_id = info["job_id"]
    eu = info.get("eu", False)
    guesses = info.get("guesses", [board])

    if eu:
        api_base = "https://boards-api.eu.greenhouse.io/v1/boards"
    else:
        api_base = "https://boards-api.greenhouse.io/v1/boards"

    # Try board token (and guesses if needed)
    boards_to_try = [board] + [g for g in guesses if g != board] if "guesses" in info else [board]

    for try_board in boards_to_try:
        if not try_board:
            continue

        api_url = f"{api_base}/{try_board}/jobs/{job_id}"

        try:
            resp = requests.get(api_url, params={"questions": "true"}, timeout=15)
            if resp.status_code == 200:
                board = try_board  # This one worked
                break
            elif resp.status_code == 404:
                continue  # Try next guess
            else:
                continue
        except Exception:
            continue
    else:
        return {"success": False, "error": f"Board token not found (tried: {boards_to_try[:3]})"}

    # Parse questions
    try:
        job_data = resp.json()
        questions = job_data.get("questions", [])
    except Exception as e:
        return {"success": False, "error": f"Failed to parse questions: {e}"}

    # Build form data
    form_data = {}
    cover_letter = generate_cover_letter(company, title)

    for q in questions:
        q_label = q.get("label", "")
        q_required = q.get("required", False)
        fields = q.get("fields", [])

        for field in fields:
            fname = field.get("name", "")
            ftype = field.get("type", "")
            fvalues = field.get("values", [])

            if fname == "first_name":
                form_data[fname] = APPLICANT["first_name"]
            elif fname == "last_name":
                form_data[fname] = APPLICANT["last_name"]
            elif fname == "email":
                form_data[fname] = APPLICANT["email"]
            elif fname == "phone":
                form_data[fname] = APPLICANT["phone"]
            elif fname == "resume":
                pass  # Handled in multipart
            elif fname == "resume_text":
                form_data[fname] = ""
            elif fname == "cover_letter":
                form_data[fname] = cover_letter
            elif fname == "cover_letter_text":
                form_data[fname] = cover_letter
            else:
                answer = answer_question(q_label, fname, ftype, fvalues, company, title)
                if answer is not None:
                    form_data[fname] = answer
                elif q_required and ftype in ("input_text", "textarea"):
                    form_data[fname] = "N/A"

    # Submit
    submit_url = f"{api_base}/{board}/jobs/{job_id}/candidates"

    files = {}
    if os.path.exists(RESUME_PATH):
        files["resume"] = (
            "matt_gates_resume_ai.docx",
            open(RESUME_PATH, "rb"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    try:
        resp = requests.post(submit_url, data=form_data, files=files, headers=headers, timeout=30)
        status = resp.status_code
        body = resp.text[:500]

        if status in (200, 201):
            return {"success": True, "msg": f"HTTP {status}", "board": board}
        elif status == 422 and "already" in body.lower():
            return {"success": False, "error": f"Already applied", "skip_db_update": True}
        else:
            return {"success": False, "error": f"HTTP {status}: {body[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if "resume" in files:
            files["resume"][1].close()


# ─── Ashby API Applier (import from existing) ───────────────────────

try:
    from apply_ashby_api import apply_to_job as ashby_apply_fn
    ASHBY_AVAILABLE = True
except Exception as e:
    log(f"Ashby module not available: {e}")
    ASHBY_AVAILABLE = False


def apply_ashby_api(job: dict) -> dict:
    """Apply to an Ashby job via GraphQL API."""
    if not ASHBY_AVAILABLE:
        return {"success": False, "error": "Ashby module not available"}
    try:
        result = ashby_apply_fn(job["url"], dry_run=False)
        if result.get("success"):
            return {"success": True, "msg": "Ashby API"}
        else:
            return {"success": False, "error": result.get("error", "Unknown")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── DB Operations ──────────────────────────────────────────────────

def get_viable_jobs(min_score: float = 60.0) -> list:
    """Get all new jobs with score >= min_score."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score, source
        FROM jobs
        WHERE status = 'new' AND fit_score >= ?
        ORDER BY fit_score DESC
    """, (min_score,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_job_status(job_id: str, status: str, cover_letter: str = None):
    """Update job status in DB."""
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
        log(f"  DB error updating {job_id}: {e}")


# ─── Job Classification ─────────────────────────────────────────────

def classify_for_swarm(job: dict) -> str:
    """Classify job into: greenhouse_api, ashby_api, lever_wraith, skip."""
    url = job["url"]
    source = job["source"]
    domain = urlparse(url).netloc.lower()

    # Greenhouse direct or wrapped
    if source == "greenhouse" or "greenhouse" in domain:
        info = extract_greenhouse_info(url, job["company"])
        if info:
            return "greenhouse_api"
        return "greenhouse_unknown"

    # Ashby
    if source == "ashby" or "ashbyhq.com" in domain:
        return "ashby_api"

    # Lever
    if source == "lever" or "lever.co" in domain:
        return "lever_wraith"

    # LinkedIn
    if "linkedin.com" in domain:
        return "skip_linkedin"

    # Indeed
    if "indeed.com" in domain:
        return "skip_indeed"

    # Other
    return f"skip_{source}"


# ─── Main Swarm ─────────────────────────────────────────────────────

def run_mega_swarm(
    min_score: float = 60.0,
    greenhouse_delay: float = 1.5,
    ashby_delay: float = 2.0,
    max_greenhouse: int = 0,  # 0 = unlimited
    max_ashby: int = 0,
    resume_from: int = 0,  # Skip first N greenhouse jobs (for resuming)
):
    """Deploy the mega swarm."""
    start_time = datetime.now(timezone.utc)

    # Clear log
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"=== MEGA SWARM STARTED {start_time.isoformat()} ===\n")

    log("=" * 70)
    log("MEGA SWARM — Overnight Autonomous Application Dispatcher")
    log("=" * 70)

    # Get all viable jobs
    all_jobs = get_viable_jobs(min_score)
    log(f"Loaded {len(all_jobs)} viable jobs (score >= {min_score})")

    # Classify
    greenhouse_jobs = []
    ashby_jobs = []
    lever_jobs = []
    skipped = {}

    for job in all_jobs:
        cat = classify_for_swarm(job)
        if cat == "greenhouse_api":
            greenhouse_jobs.append(job)
        elif cat == "ashby_api":
            ashby_jobs.append(job)
        elif cat == "lever_wraith":
            lever_jobs.append(job)
        else:
            if cat not in skipped:
                skipped[cat] = []
            skipped[cat].append(job)

    log(f"\nClassification:")
    log(f"  Greenhouse API:  {len(greenhouse_jobs)}")
    log(f"  Ashby API:       {len(ashby_jobs)}")
    log(f"  Lever (Wraith):  {len(lever_jobs)}")
    for cat, jobs in sorted(skipped.items(), key=lambda x: -len(x[1])):
        log(f"  {cat}: {len(jobs)}")
    log("")

    # Tracking
    results = {
        "greenhouse_success": [],
        "greenhouse_fail": [],
        "greenhouse_already": [],
        "ashby_success": [],
        "ashby_fail": [],
        "lever_pending": lever_jobs,
        "skipped": skipped,
    }

    # ── Phase 1: Greenhouse API ──────────────────────────────────────
    gh_batch = greenhouse_jobs[resume_from:]
    if max_greenhouse > 0:
        gh_batch = gh_batch[:max_greenhouse]

    log(f"{'='*70}")
    log(f"PHASE 1: Greenhouse API — {len(gh_batch)} jobs")
    log(f"{'='*70}\n")

    for i, job in enumerate(gh_batch):
        job_num = i + 1 + resume_from
        log(f"[GH {job_num}/{len(gh_batch)+resume_from}] {job['company']} — {job['title'][:50]} (score={job['fit_score']})")

        result = apply_greenhouse_api(job)

        if result.get("success"):
            log(f"  >>> SUCCESS ({result.get('board', '?')}) <<<")
            results["greenhouse_success"].append(job)
            cl = generate_cover_letter(job["company"], job["title"])
            update_job_status(job["id"], "applied", cover_letter=cl)
        elif "already" in result.get("error", "").lower():
            log(f"  Already applied — skipping")
            results["greenhouse_already"].append(job)
            update_job_status(job["id"], "applied")
        else:
            log(f"  FAILED: {result.get('error', 'unknown')[:120]}")
            results["greenhouse_fail"].append({**job, "error": result.get("error", "unknown")})
            if not result.get("skip_db_update"):
                update_job_status(job["id"], "apply_failed")

        # Rate limit
        if i < len(gh_batch) - 1:
            time.sleep(greenhouse_delay)

    # ── Phase 2: Ashby API ───────────────────────────────────────────
    ashby_batch = ashby_jobs
    if max_ashby > 0:
        ashby_batch = ashby_batch[:max_ashby]

    log(f"\n{'='*70}")
    log(f"PHASE 2: Ashby API — {len(ashby_batch)} jobs")
    log(f"{'='*70}\n")

    for i, job in enumerate(ashby_batch):
        log(f"[ASH {i+1}/{len(ashby_batch)}] {job['company']} — {job['title'][:50]} (score={job['fit_score']})")

        result = apply_ashby_api(job)

        if result.get("success"):
            log(f"  >>> SUCCESS <<<")
            results["ashby_success"].append(job)
            update_job_status(job["id"], "applied")
        else:
            error = result.get("error", "unknown")
            log(f"  FAILED: {error[:120]}")
            results["ashby_fail"].append({**job, "error": error})
            # Don't mark captcha failures as apply_failed - we might retry with browser
            if "captcha" not in error.lower() and "recaptcha" not in error.lower():
                update_job_status(job["id"], "apply_failed")

        if i < len(ashby_batch) - 1:
            time.sleep(ashby_delay)

    # ── Write Results Report ─────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    gh_ok = len(results["greenhouse_success"])
    gh_fail = len(results["greenhouse_fail"])
    gh_dup = len(results["greenhouse_already"])
    ash_ok = len(results["ashby_success"])
    ash_fail = len(results["ashby_fail"])
    total_ok = gh_ok + ash_ok
    total_attempted = gh_ok + gh_fail + gh_dup + ash_ok + ash_fail

    log(f"\n{'='*70}")
    log(f"MEGA SWARM COMPLETE")
    log(f"{'='*70}")
    log(f"Duration: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    log(f"Greenhouse: {gh_ok} success / {gh_fail} fail / {gh_dup} already applied")
    log(f"Ashby:      {ash_ok} success / {ash_fail} fail")
    log(f"TOTAL APPLIED: {total_ok}")
    log(f"Lever pending (needs Wraith): {len(lever_jobs)}")
    for cat, jobs in sorted(skipped.items(), key=lambda x: -len(x[1])):
        log(f"Skipped ({cat}): {len(jobs)}")
    log(f"{'='*70}")

    # Write markdown report
    with open(RESULTS_PATH, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# Mega Swarm Results\n\n")
        f.write(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Duration**: {elapsed:.0f}s ({elapsed/60:.1f}min)\n\n")
        f.write(f"## Summary\n")
        f.write(f"| Platform | Success | Failed | Already | Total |\n")
        f.write(f"|----------|---------|--------|---------|-------|\n")
        f.write(f"| Greenhouse | {gh_ok} | {gh_fail} | {gh_dup} | {gh_ok+gh_fail+gh_dup} |\n")
        f.write(f"| Ashby | {ash_ok} | {ash_fail} | — | {ash_ok+ash_fail} |\n")
        f.write(f"| **Total** | **{total_ok}** | **{gh_fail+ash_fail}** | **{gh_dup}** | **{total_attempted}** |\n\n")

        f.write(f"## Successful Applications ({total_ok})\n\n")
        for j in results["greenhouse_success"]:
            f.write(f"- [{j['fit_score']}] **{j['company']}** — {j['title']} (Greenhouse)\n")
        for j in results["ashby_success"]:
            f.write(f"- [{j['fit_score']}] **{j['company']}** — {j['title']} (Ashby)\n")

        if results["greenhouse_fail"] or results["ashby_fail"]:
            f.write(f"\n## Failed Applications ({gh_fail+ash_fail})\n\n")
            for j in results["greenhouse_fail"]:
                f.write(f"- **{j['company']}** — {j['title']}\n")
                f.write(f"  - Error: `{j.get('error', '?')[:150]}`\n")
            for j in results["ashby_fail"]:
                f.write(f"- **{j['company']}** — {j['title']}\n")
                f.write(f"  - Error: `{j.get('error', '?')[:150]}`\n")

        if results["greenhouse_already"]:
            f.write(f"\n## Already Applied ({gh_dup})\n\n")
            for j in results["greenhouse_already"]:
                f.write(f"- {j['company']} — {j['title']}\n")

        if lever_jobs:
            f.write(f"\n## Lever Jobs — Pending Wraith Browser ({len(lever_jobs)})\n\n")
            for j in lever_jobs[:20]:
                f.write(f"- [{j['fit_score']}] {j['company']} — {j['title']}\n")
                f.write(f"  `{j['url'][:100]}`\n")
            if len(lever_jobs) > 20:
                f.write(f"- *...and {len(lever_jobs)-20} more*\n")

    log(f"\nResults written to: {RESULTS_PATH}")
    log(f"Full log at: {LOG_PATH}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mega Swarm — Overnight Application Dispatcher")
    parser.add_argument("--min-score", type=float, default=60.0, help="Minimum fit score")
    parser.add_argument("--gh-delay", type=float, default=1.5, help="Delay between Greenhouse apps (seconds)")
    parser.add_argument("--ash-delay", type=float, default=2.0, help="Delay between Ashby apps (seconds)")
    parser.add_argument("--max-gh", type=int, default=0, help="Max Greenhouse apps (0=unlimited)")
    parser.add_argument("--max-ash", type=int, default=0, help="Max Ashby apps (0=unlimited)")
    parser.add_argument("--resume-from", type=int, default=0, help="Skip first N Greenhouse jobs (resume)")
    args = parser.parse_args()

    run_mega_swarm(
        min_score=args.min_score,
        greenhouse_delay=args.gh_delay,
        ashby_delay=args.ash_delay,
        max_greenhouse=args.max_gh,
        max_ashby=args.max_ash,
        resume_from=args.resume_from,
    )
