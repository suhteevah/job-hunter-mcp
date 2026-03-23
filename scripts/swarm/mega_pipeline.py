"""
MEGA PIPELINE — Unified Scrape + Score + Apply
================================================
Single entry point for the entire job hunting pipeline.

Phases:
  1. SCRAPE  — Hit Greenhouse/Ashby/Lever APIs, insert to DB
  2. RESCORE — Fetch full descriptions for title-only scored jobs, rescore
  3. APPLY   — Playwright-based apply for Ashby + Greenhouse, track results

Usage:
  python mega_pipeline.py --scrape              # scrape only
  python mega_pipeline.py --rescore             # fetch descriptions + rescore
  python mega_pipeline.py --apply               # apply to viable jobs
  python mega_pipeline.py --apply --platform ashby --limit 20
  python mega_pipeline.py --all                 # scrape + rescore + apply
  python mega_pipeline.py --retry-failed        # retry apply_failed jobs
  python mega_pipeline.py --stats               # show current stats
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import hashlib
import imaplib
import email as email_lib
import json
import os
import re
import sqlite3
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

# ═══════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
LOG_DIR = r"J:\job-hunter-mcp\scripts\swarm\logs"
GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "yzpn qern vrax fvta")

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

# ═══════════════════════════════════════════════════════════════════════
# COMPANY BOARDS
# ═══════════════════════════════════════════════════════════════════════

GREENHOUSE_BOARDS = {
    # AI / ML
    "anthropic": "Anthropic", "openai": "OpenAI", "cohere": "Cohere",
    "mistral": "Mistral", "huggingface": "Hugging Face", "replicate": "Replicate",
    "togetherai": "Together AI", "fireworksai": "Fireworks AI", "wandb": "Weights & Biases",
    "anysphere": "Cursor", "scaleai": "Scale AI", "modal": "Modal",
    "anyscale": "Anyscale", "replit": "Replit", "deepmind": "DeepMind",
    "stability": "Stability AI", "jasper": "Jasper AI", "adeptailabs": "Adept AI",
    "inflectionai": "Inflection AI", "characterai": "Character AI",
    "runwayml": "Runway", "midjourney": "Midjourney", "elevenlab": "ElevenLabs",
    "descript": "Descript",
    # Infrastructure / Cloud
    "vercel": "Vercel", "supabase": "Supabase", "netlify": "Netlify",
    "render": "Render", "railway": "Railway", "fly": "Fly.io",
    "cloudflare": "Cloudflare", "hashicorp": "HashiCorp", "temporal": "Temporal",
    "tailscale": "Tailscale", "coreweave": "CoreWeave", "lambda": "Lambda",
    "vultr": "Vultr", "equinix": "Equinix Metal",
    # Developer Tools
    "gitlab": "GitLab", "sourcegraph": "Sourcegraph", "linear": "Linear",
    "retool": "Retool", "postman": "Postman", "snyk": "Snyk",
    "launchdarkly": "LaunchDarkly", "circleci": "CircleCI",
    "datadog": "Datadog", "grafanalabs": "Grafana Labs", "elastic": "Elastic",
    "newrelic": "New Relic", "pagerduty": "PagerDuty", "opsgeniecom": "OpsGenie",
    "sentry": "Sentry", "bugsnag": "Bugsnag", "lightstep": "Lightstep",
    "honeycomb": "Honeycomb", "chronosphere": "Chronosphere",
    # Data
    "databricks": "Databricks", "snowflake": "Snowflake", "fivetran": "Fivetran",
    "dbt": "dbt Labs", "airbyte": "Airbyte", "confluent": "Confluent",
    "clickhouse": "ClickHouse", "cockroachlabs": "Cockroach Labs",
    "planetscale": "PlanetScale", "timescale": "Timescale", "neon": "Neon",
    "singlestore": "SingleStore", "starburst": "Starburst",
    "mongodb": "MongoDB", "redis": "Redis", "arangodb": "ArangoDB",
    # Fintech
    "stripe": "Stripe", "plaid": "Plaid", "brex": "Brex", "ramp": "Ramp",
    "mercury": "Mercury", "moderntreasury": "Modern Treasury",
    "coinbase": "Coinbase", "blockchain": "Blockchain.com",
    "chainalysis": "Chainalysis", "alchemy": "Alchemy", "phantom": "Phantom",
    "robinhood": "Robinhood", "sofi": "SoFi",
    # Consumer / Social
    "reddit": "Reddit", "discord": "Discord", "snap": "Snap",
    "pinterest": "Pinterest", "spotify": "Spotify",
    "notion": "Notion", "figma": "Figma", "canva": "Canva",
    "miro": "Miro", "airtable": "Airtable", "coda": "Coda",
    # E-Commerce / Marketplace
    "instacart": "Instacart", "doordash": "DoorDash",
    "lyft": "Lyft", "nuro": "Nuro", "cruise": "Cruise",
    "airbnb": "Airbnb", "faire": "Faire", "flexport": "Flexport",
    # Enterprise
    "twilio": "Twilio", "sendgrid": "SendGrid",
    "okta": "Okta", "auth0": "Auth0", "onelogin": "OneLogin",
    "crowdstrike": "CrowdStrike", "sentinelone": "SentinelOne",
    "chainguard": "Chainguard", "lacework": "Lacework",
    "ziprecruiter": "ZipRecruiter", "ashbyhq": "Ashby",
    "rippling": "Rippling", "gusto": "Gusto", "justworks": "Justworks",
    "lattice": "Lattice", "culturamp": "Culture Amp",
    # Productivity
    "asana": "Asana", "monday": "monday.com", "clickup": "ClickUp",
    "loom": "Loom", "calendly": "Calendly", "drata": "Drata",
    "vanta": "Vanta",
    # Health / Bio
    "tempus": "Tempus", "flatiron": "Flatiron Health",
    "nuvancehealth": "Nuvance Health", "colorhealth": "Color Health",
    # Comms
    "assemblyai": "AssemblyAI", "deepgram": "Deepgram",
    "livekit": "LiveKit", "mux": "Mux", "agora": "Agora",
    # Gaming
    "epicgames": "Epic Games", "riotgames": "Riot Games",
    # Education
    "khanacademy": "Khan Academy", "duolingo": "Duolingo", "coursera": "Coursera",
    # Security
    "regscale": "RegScale", "wiz": "Wiz", "orca": "Orca Security",
    "bitwarden": "Bitwarden", "1password": "1Password",
    # Other notable
    "samsara": "Samsara", "verkada": "Verkada", "matterport": "Matterport",
    "onboardmeetings": "OnBoard Meetings", "pathward": "Pathward",
    "censys": "Censys", "shodan": "Shodan",
    "zapier": "Zapier", "make": "Make", "n8n": "n8n",
    "segment": "Segment", "amplitude": "Amplitude", "mixpanel": "Mixpanel",
    "heap": "Heap", "fullstory": "FullStory",
    "warp": "Warp", "iterm2": "iTerm2",
}

ASHBY_BOARDS = {
    "perplexity": "Perplexity AI", "openai": "OpenAI", "anthropic": "Anthropic",
    "cohere": "Cohere", "mistral": "Mistral AI", "together": "Together AI",
    "reka": "Reka", "adept": "Adept AI", "inflection": "Inflection AI",
    "characterai": "Character AI", "elevenlab": "ElevenLabs", "descript": "Descript",
    "deepgram": "Deepgram", "assemblyai": "AssemblyAI", "livekit": "LiveKit",
    "baseten": "Baseten", "modal": "Modal", "anyscale": "Anyscale",
    "replicate": "Replicate", "wandb": "Weights & Biases", "langchain": "LangChain",
    "pinecone": "Pinecone", "weaviate": "Weaviate", "qdrant": "Qdrant",
    "chroma": "Chroma", "lancedb": "LanceDB",
    "render": "Render", "railway": "Railway", "vercel": "Vercel",
    "supabase": "Supabase", "netlify": "Netlify", "fly": "Fly.io",
    "neon": "Neon", "upstash": "Upstash", "cloudflare": "Cloudflare",
    "tailscale": "Tailscale", "temporal": "Temporal",
    "replit": "Replit", "sourcegraph": "Sourcegraph", "linear": "Linear",
    "retool": "Retool", "sentry": "Sentry", "posthog": "PostHog",
    "grafana": "Grafana Labs", "highlight": "Highlight", "axiom": "Axiom",
    "stripe": "Stripe", "plaid": "Plaid", "mercury": "Mercury",
    "ramp": "Ramp", "brex": "Brex", "coinbase": "Coinbase",
    "phantom": "Phantom", "alchemy": "Alchemy",
    "clickhouse": "ClickHouse", "cockroach": "Cockroach Labs",
    "planetscale": "PlanetScale", "timescale": "Timescale",
    "motherduck": "MotherDuck", "duckdb": "DuckDB",
    "fivetran": "Fivetran", "airbyte": "Airbyte",
    "chainguard": "Chainguard", "wiz": "Wiz", "orca": "Orca Security",
    "bitwarden": "Bitwarden", "1password": "1Password",
    "snyk": "Snyk", "lacework": "Lacework", "vanta": "Vanta",
    "notion": "Notion", "figma": "Figma", "coda": "Coda",
    "miro": "Miro", "airtable": "Airtable",
    "discord": "Discord", "reddit": "Reddit",
    "rippling": "Rippling", "gusto": "Gusto", "lattice": "Lattice",
    "ashby": "Ashby", "lever": "Lever",
    "zapier": "Zapier", "make": "Make",
    "resend": "Resend", "clerk": "Clerk", "stytch": "Stytch",
    "turso": "Turso", "drizzle": "Drizzle",
    "cal": "Cal.com", "documenso": "Documenso",
    "harvey": "Harvey AI", "casetext": "Casetext",
    "cursor": "Cursor", "tabnine": "Tabnine", "codeium": "Codeium",
}

LEVER_BOARDS = {
    "plaid": "Plaid", "twitch": "Twitch", "netflix": "Netflix",
    "github": "GitHub", "figma": "Figma", "webflow": "Webflow",
    "atlassian": "Atlassian", "shopify": "Shopify",
    "hashicorp": "HashiCorp", "gitlab": "GitLab",
    "datadog": "Datadog", "confluent": "Confluent",
    "elastic": "Elastic", "pagerduty": "PagerDuty",
    "circleci": "CircleCI", "launchdarkly": "LaunchDarkly",
    "cockroachlabs": "Cockroach Labs", "yugabyte": "YugabyteDB",
    "temporal": "Temporal", "airbyte": "Airbyte",
    "dbt-labs": "dbt Labs", "fivetran": "Fivetran",
    "rudderstack": "RudderStack", "segment": "Segment",
    "amplitude": "Amplitude", "mixpanel": "Mixpanel",
    "heap": "Heap", "fullstory": "FullStory",
    "sentry": "Sentry", "snyk": "Snyk",
    "chainguard": "Chainguard", "lacework": "Lacework",
    "postman": "Postman", "mux": "Mux",
    "livekit": "LiveKit", "agora": "Agora",
    "cal-com": "Cal.com", "n8n": "n8n",
    "langchain": "LangChain", "chroma-core": "Chroma",
    "anyscale": "Anyscale", "modal-labs": "Modal",
    "weights-and-biases": "Weights & Biases",
    "huggingface": "Hugging Face",
}

# Board token lookup for wrapped Greenhouse URLs
KNOWN_GH_BOARDS = {
    "samsara": "samsara", "databricks": "databricks", "stripe": "stripe",
    "datadog": "datadog", "coreweave": "coreweave", "cockroach labs": "cockroachlabs",
    "airbnb": "airbnb", "elastic": "elastic", "brex": "brex", "mongodb": "mongodb",
    "instacart": "instacart", "coinbase": "coinbase", "cloudflare": "cloudflare",
    "nuro": "nuro", "reddit": "reddit", "anthropic": "anthropic", "scale ai": "scaleai",
    "airtable": "airtable", "gitlab": "gitlab", "gusto": "gusto", "twilio": "twilio",
    "assemblyai": "assemblyai", "clickhouse": "clickhouse", "chainguard": "chainguard",
    "planetscale": "planetscale", "ziprecruiter": "ziprecruiter",
    "figma": "figma", "notion": "notion", "plaid": "plaid",
    "ramp": "ramp", "anyscale": "anyscale", "modal": "modal", "vercel": "vercel",
    "hashicorp": "hashicorp", "grafana labs": "grafanalabs", "snap": "snap",
    "pinterest": "pinterest", "lyft": "lyft", "doordash": "doordash",
    "robinhood": "robinhood", "discord": "discord",
    "confluent": "confluent", "temporal": "temporal", "tailscale": "tailscale",
    "supabase": "supabase", "retool": "retool", "linear": "linear", "replit": "replit",
    "sourcegraph": "sourcegraph", "mux": "mux", "livekit": "livekit",
    "together ai": "togetherai", "fireworks ai": "fireworksai", "replicate": "replicate",
    "cursor": "anysphere", "cohere": "cohere", "openai": "openai", "mistral": "mistral",
    "khan academy": "khanacademy", "censys": "censys", "grafana": "grafanalabs",
    "deepmind": "deepmind", "mercury": "mercury",
}

# ═══════════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════════

TITLE_KEYWORDS = {
    "ai": 15, "automation": 15, "llm": 15, "prompt engineer": 20,
    "ai engineer": 20, "ml engineer": 15, "qa": 12, "quality": 10,
    "devops": 12, "infrastructure": 10, "backend": 10,
    "full stack": 12, "fullstack": 12, "python": 12, "rust": 15,
    "sales engineer": 12, "solutions engineer": 12,
    "technical consultant": 12, "developer advocate": 10,
    "platform": 10, "sre": 12, "data engineer": 10, "mcp": 20,
    "agent": 15, "software engineer": 8,
}

SKILL_KEYWORDS = [
    "ai", "automation", "llm", "claude", "anthropic", "openai",
    "python", "rust", "javascript", "typescript", "react", "next.js",
    "docker", "kubernetes", "devops", "ci/cd", "linux",
    "qa", "testing", "selenium", "playwright",
    "web scraping", "data pipeline", "mcp", "model context protocol",
    "api", "rest", "graphql", "fastapi", "flask", "django",
    "postgresql", "redis", "mongodb", "sqlite",
    "aws", "gcp", "azure", "cloud",
    "machine learning", "deep learning", "neural", "nlp",
    "rag", "vector", "embedding", "inference",
    "agent", "agentic", "autonomous",
    "n8n", "make.com", "zapier",
    "git", "github", "gitlab",
    "ollama", "gpu", "cuda",
]

NEGATIVE_KEYWORDS = [
    "senior staff", "principal", "director", "vp ",
    "phd required", "15+ years",
    "clearance required", "ts/sci", "security clearance",
    "java ", "c# ", ".net ", "angular", "php ",
    "ios ", "swift ", "kotlin ", "android ",
    "mandarin required", "japanese required", "korean required",
]

BONUS_KEYWORDS = {"remote": 5, "contractor": 3, "freelance": 3, "startup": 3}


def score_job(title: str, description: str = "") -> float:
    score = 0.0
    tl = title.lower()
    dl = (description or "").lower()
    text = tl + " " + dl
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in tl:
            score += pts
    for kw in SKILL_KEYWORDS:
        if kw in dl:
            score += 3
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score -= 10
    for kw, pts in BONUS_KEYWORDS.items():
        if kw in text:
            score += pts
    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════

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
# DB HELPERS
# ═══════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def insert_jobs(jobs: list) -> int:
    if not jobs:
        return 0
    conn = get_db()
    inserted = 0
    for job in jobs:
        try:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE url = ? OR (source = ? AND source_id = ?)",
                (job["url"], job["source"], job["source_id"])
            ).fetchone()
            if existing:
                continue
            conn.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  description, date_posted, date_found, fit_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                job["id"], job["source"], job["source_id"], job["title"],
                job["company"], job["url"], job["location"],
                job.get("description", ""), job.get("date_posted", ""),
                datetime.now(timezone.utc).isoformat(), job["fit_score"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def update_job_status(job_id: str, status: str, cover_letter: str = None):
    try:
        conn = get_db()
        if cover_letter:
            conn.execute(
                "UPDATE jobs SET status=?, applied_date=?, cover_letter=? WHERE id=?",
                (status, datetime.now(timezone.utc).isoformat(), cover_letter, job_id))
        else:
            conn.execute(
                "UPDATE jobs SET status=?, applied_date=? WHERE id=?",
                (status, datetime.now(timezone.utc).isoformat(), job_id))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"  DB error: {e}")


def get_viable_jobs(platform: str = None, min_score: float = 60.0,
                    status: str = "new", limit: int = 0) -> list:
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


# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: SCRAPE
# ═══════════════════════════════════════════════════════════════════════

def scrape_greenhouse_board(board_token: str, company: str) -> list:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 JobHunter/1.0"})
        if resp.status_code != 200:
            return []
        jobs_data = resp.json().get("jobs", [])
        results = []
        for j in jobs_data:
            title = j.get("title", "")
            jid = str(j.get("id", ""))
            location = j.get("location", {}).get("name", "Remote")
            job_url = j.get("absolute_url", f"https://boards.greenhouse.io/{board_token}/jobs/{jid}")
            stable_id = hashlib.md5(f"greenhouse:{board_token}:{jid}".encode()).hexdigest()[:8]
            results.append({
                "id": stable_id, "source": "greenhouse", "source_id": jid,
                "title": title, "company": company, "url": job_url,
                "location": location, "description": "",
                "date_posted": j.get("updated_at", ""),
                "fit_score": score_job(title),
            })
        return results
    except Exception:
        return []


def scrape_ashby_board(slug: str, company: str) -> list:
    url = f"https://jobs.ashbyhq.com/{slug}"
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        if resp.status_code != 200:
            return []
        # Try __NEXT_DATA__ first
        json_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
        if json_match:
            try:
                next_data = json.loads(json_match.group(1))
                props = next_data.get("props", {}).get("pageProps", {})
                postings = props.get("jobPostings", props.get("jobs", []))
                results = []
                for p in postings:
                    title = p.get("title", "")
                    job_id = p.get("id", p.get("jobPostingId", ""))
                    location = p.get("locationName", p.get("location", "Remote"))
                    stable_id = hashlib.md5(f"ashby:{slug}:{job_id}".encode()).hexdigest()[:8]
                    results.append({
                        "id": stable_id, "source": "ashby", "source_id": str(job_id),
                        "title": title, "company": company,
                        "url": f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                        "location": location or "Remote", "description": "",
                        "date_posted": "", "fit_score": score_job(title),
                    })
                return results
            except json.JSONDecodeError:
                pass
        # Fallback: regex extract links
        job_links = re.findall(rf'href="/{re.escape(slug)}/([a-f0-9-]{{36}})"[^>]*>([^<]+)', resp.text)
        results = []
        for job_id, title in job_links:
            title = title.strip()
            if not title or len(title) < 3:
                continue
            stable_id = hashlib.md5(f"ashby:{slug}:{job_id}".encode()).hexdigest()[:8]
            results.append({
                "id": stable_id, "source": "ashby", "source_id": job_id,
                "title": title, "company": company,
                "url": f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                "location": "Remote", "description": "", "date_posted": "",
                "fit_score": score_job(title),
            })
        return results
    except Exception:
        return []


def scrape_lever_board(slug: str, company: str) -> list:
    url = f"https://api.lever.co/v0/postings/{slug}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 JobHunter/1.0"})
        if resp.status_code != 200:
            return []
        postings = resp.json()
        if not isinstance(postings, list):
            return []
        results = []
        for p in postings:
            title = p.get("text", "")
            job_id = p.get("id", "")
            location = p.get("categories", {}).get("location", "Remote")
            job_url = p.get("hostedUrl", f"https://jobs.lever.co/{slug}/{job_id}")
            desc = p.get("descriptionPlain", "")
            stable_id = hashlib.md5(f"lever:{slug}:{job_id}".encode()).hexdigest()[:8]
            results.append({
                "id": stable_id, "source": "lever", "source_id": str(job_id),
                "title": title, "company": company, "url": job_url,
                "location": location or "Remote",
                "description": desc[:2000],
                "date_posted": "",
                "fit_score": score_job(title, desc),
            })
        return results
    except Exception:
        return []


def scrape_worker(task: dict) -> dict:
    platform = task["platform"]
    slug = task["slug"]
    company = task["company"]
    try:
        if platform == "greenhouse":
            jobs = scrape_greenhouse_board(slug, company)
        elif platform == "ashby":
            jobs = scrape_ashby_board(slug, company)
        elif platform == "lever":
            jobs = scrape_lever_board(slug, company)
        else:
            jobs = []
        if jobs:
            new_count = insert_jobs(jobs)
            return {"company": company, "platform": platform, "total": len(jobs), "new": new_count}
        return {"company": company, "platform": platform, "total": 0, "new": 0}
    except Exception as e:
        return {"company": company, "platform": platform, "total": 0, "new": 0, "error": str(e)}


def run_scrape(max_workers: int = 100):
    log(f"\n{'='*70}")
    log(f"PHASE 1: MEGA SCRAPE")
    log(f"{'='*70}")
    start = time.time()

    tasks = []
    for slug, company in GREENHOUSE_BOARDS.items():
        tasks.append({"platform": "greenhouse", "slug": slug, "company": company})
    for slug, company in ASHBY_BOARDS.items():
        tasks.append({"platform": "ashby", "slug": slug, "company": company})
    for slug, company in LEVER_BOARDS.items():
        tasks.append({"platform": "lever", "slug": slug, "company": company})

    log(f"Boards: {len(GREENHOUSE_BOARDS)} GH + {len(ASHBY_BOARDS)} Ashby + {len(LEVER_BOARDS)} Lever = {len(tasks)} total")
    log(f"Workers: {max_workers}")

    total_found = 0
    total_new = 0
    successes = 0
    top_companies = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_worker, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                r = future.result(timeout=30)
                if r["total"] > 0:
                    total_found += r["total"]
                    total_new += r["new"]
                    successes += 1
                    if r["new"] > 0:
                        log(f"  +{r['new']:3d} new  {r['company']} ({r['platform']}) [{r['total']} total]")
                        top_companies.append(r)
            except Exception:
                pass

    elapsed = time.time() - start

    conn = get_db()
    viable = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60").fetchone()[0]
    total_db = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()

    log(f"\nSCRAPE DONE in {elapsed:.0f}s")
    log(f"  Found: {total_found} jobs across {successes} boards")
    log(f"  New inserted: {total_new}")
    log(f"  Viable (fit>=60, new): {viable}")
    log(f"  Total DB: {total_db}")

    if top_companies:
        top = sorted(top_companies, key=lambda x: -x["new"])[:15]
        log(f"\nTop by new jobs:")
        for r in top:
            log(f"  {r['company']:25s} +{r['new']} ({r['platform']})")

    return total_new


# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: RESCORE — Fetch full descriptions for Greenhouse jobs
# ═══════════════════════════════════════════════════════════════════════

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def get_text(self):
        return " ".join(self.text)


def strip_html(html: str) -> str:
    s = HTMLStripper()
    s.feed(html or "")
    return s.get_text()


def rescore_worker(job: dict) -> dict:
    """Fetch full description from Greenhouse API and rescore."""
    url = job["url"]
    m = re.search(r'boards(?:-api)?\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if not m:
        m = re.search(r'job-boards\.(?:eu\.)?greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if not m:
        return {"id": job["id"], "rescored": False}
    board, jid = m.group(1), m.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}"
    try:
        resp = requests.get(api_url, timeout=10, headers={"User-Agent": "Mozilla/5.0 JobHunter/1.0"})
        if resp.status_code != 200:
            return {"id": job["id"], "rescored": False}
        data = resp.json()
        desc_html = data.get("content", "")
        desc = strip_html(desc_html)[:3000]
        new_score = score_job(job["title"], desc)
        conn = get_db()
        conn.execute("UPDATE jobs SET description=?, fit_score=? WHERE id=?",
                     (desc[:2000], new_score, job["id"]))
        conn.commit()
        conn.close()
        return {"id": job["id"], "rescored": True, "old": job["fit_score"], "new": new_score, "title": job["title"]}
    except Exception:
        return {"id": job["id"], "rescored": False}


def run_rescore(max_workers: int = 100):
    log(f"\n{'='*70}")
    log(f"PHASE 2: RESCORE — Fetching full descriptions")
    log(f"{'='*70}")
    start = time.time()

    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, url, fit_score FROM jobs
        WHERE source = 'greenhouse' AND status = 'new'
          AND (description IS NULL OR description = '' OR LENGTH(description) < 50)
        ORDER BY fit_score DESC
    """).fetchall()
    conn.close()
    jobs = [dict(r) for r in rows]
    log(f"Jobs to rescore: {len(jobs)}")

    if not jobs:
        log("Nothing to rescore.")
        return

    rescored = 0
    promoted = 0
    demoted = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(rescore_worker, j): j for j in jobs}
        for future in as_completed(futures):
            try:
                r = future.result(timeout=15)
                if r.get("rescored"):
                    rescored += 1
                    old, new = r.get("old", 0), r.get("new", 0)
                    if new >= 60 and old < 60:
                        promoted += 1
                        log(f"  PROMOTED {old}->{new}: {r['title'][:50]}")
                    elif new < 60 and old >= 60:
                        demoted += 1
            except Exception:
                pass

    elapsed = time.time() - start
    log(f"\nRESCORE DONE in {elapsed:.0f}s — {rescored} rescored, {promoted} promoted to viable, {demoted} demoted")


# ═══════════════════════════════════════════════════════════════════════
# COVER LETTERS
# ═══════════════════════════════════════════════════════════════════════

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
    if any(kw in tl for kw in ["security", "appsec"]):
        return (
            f"I am drawn to the {title} role at {company}. With 10 years including browser security "
            f"research, TLS fingerprinting, and building secure systems from embedded hardware to "
            f"cloud, I bring deep understanding of both offensive and defensive security."
        )
    if any(kw in tl for kw in ["qa", "quality", "test", "sdet"]):
        return (
            f"I am excited about the {title} role at {company}. With 10 years spanning test automation, "
            f"CI/CD, and quality engineering, I've built browser automation frameworks (27K lines Rust, "
            f"Playwright, Selenium), test infrastructure, and production monitoring systems. "
            f"I bring deep expertise in Python, TypeScript, and automated testing at scale."
        )
    return (
        f"I am excited about the {title} role at {company}. With 10 years spanning AI/ML systems, "
        f"cloud infrastructure, full-stack development, and industrial automation, I bring a versatile "
        f"skillset and proven track record shipping production systems at scale. I've built autonomous "
        f"AI agents, distributed inference infrastructure, and 10+ production MCP servers."
    )


# ═══════════════════════════════════════════════════════════════════════
# FORM HELPERS
# ═══════════════════════════════════════════════════════════════════════

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
    if "country" in ll or "residence" in ll:
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
    # Work authorization questions (text field variant)
    if "authorized" in ll or "authorization" in ll or "legally" in ll or "eligible" in ll or "lawfully" in ll:
        return "Yes"
    if "sponsor" in ll or "visa" in ll or "immigration" in ll:
        return "No"
    if "business trip" in ll or "travel" in ll or "relocat" in ll or "willing to" in ll:
        return "Yes"
    if "clearance" in ll:
        return "No"
    # AI/tech questions — answer with relevant experience
    if any(x in ll for x in ["how are you using ai", "ai experiment", "ai today", "ai tool"]):
        return (
            "I use AI daily in my work — I've built 10+ production MCP servers, a 27K-line Rust browser "
            "automation framework with AI agent orchestration, and deployed LLM-powered RAG pipelines. "
            "My latest experiment is an autonomous job application agent using Claude + browser automation."
        )
    if any(x in ll for x in ["project", "achievement", "accomplishment", "proud of"]):
        return (
            "Built a weather prediction trading bot achieving 20x returns with 4 beta testers, "
            "a 27K-line Rust browser automation framework (Wraith), and distributed AI inference "
            "infrastructure serving multiple models across heterogeneous GPU hardware."
        )
    if "education" in ll or "degree" in ll or "school" in ll or "university" in ll:
        return "Butte College — Associates level coursework in Computer Science"
    if "race" in ll or "gender" in ll or "ethnic" in ll or "veteran" in ll or "disability" in ll:
        return "Decline to self-identify"
    # Catch-all: if the field is required and we don't know, give a short relevant answer
    # rather than leaving blank (which causes validation failures)
    if any(x in ll for x in ["required", "*"]):
        return "Yes"
    return ""


def pick_select_value(label: str, options: list) -> str:
    ll = label.lower()
    if "authorized" in ll or "authorization" in ll or "lawfully" in ll or "eligible" in ll:
        for opt in options:
            ol = opt.lower()
            if "do not require" in ol or ("authorized" in ol and "do not" in ol):
                return opt
        for opt in options:
            if "yes" in opt.lower() and "not" not in opt.lower():
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
    if any(kw in ll for kw in ["ml", "machine learning", "ai", "deploy", "production"]):
        for opt in options:
            if any(x in opt.lower() for x in ["yes", "personally", "owned", "production"]):
                return opt
        return options[-1] if options else ""
    if any(kw in ll for kw in ["gender", "race", "veteran", "disability", "ethnicity"]):
        for opt in options:
            if "decline" in opt.lower() or "prefer not" in opt.lower():
                return opt
        return options[-1] if options else ""
    if any(kw in ll for kw in ["remote", "hybrid", "office", "on-site", "relocation"]):
        for opt in options:
            if "yes" in opt.lower():
                return opt
    if any(kw in ll for kw in ["how did you hear", "where did you", "source"]):
        for opt in options:
            if any(x in opt.lower() for x in ["job board", "website", "online", "other"]):
                return opt
    return options[0] if options else ""


# ═══════════════════════════════════════════════════════════════════════
# IMAP SECURITY CODE
# ═══════════════════════════════════════════════════════════════════════

def fetch_security_code(company: str, platform: str = "greenhouse", max_wait: int = 15) -> str:
    if not GMAIL_APP_PASSWORD:
        return ""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        if platform == "greenhouse":
            search_q = f'(FROM "greenhouse" SUBJECT "security code" UNSEEN)'
        else:
            search_q = f'(FROM "ashby" SUBJECT "verification" UNSEEN)'
        for attempt in range(max_wait // 3):
            status, data = mail.search(None, search_q)
            if status == "OK" and data[0]:
                msg_ids = data[0].split()
                latest_id = msg_ids[-1]
                status, msg_data = mail.fetch(latest_id, "(RFC822)")
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
# PHASE 3: APPLY — Ashby (Playwright)
# ═══════════════════════════════════════════════════════════════════════

def apply_ashby(page, url: str, company: str, title: str) -> dict:
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            return {"success": False, "error": f"Load timeout: {e}"}

    time.sleep(3)
    page_text = (page.text_content("body") or "").lower()
    if "not found" in page_text or "no longer" in page_text or "expired" in page_text:
        return {"success": False, "error": "Job no longer available"}

    # Click Apply button if present
    try:
        apply_btn = page.query_selector(
            'button:has-text("Apply"), a:has-text("Apply"), '
            '[data-testid*="apply"], button[class*="apply"]')
        if apply_btn and apply_btn.is_visible():
            apply_btn.scroll_into_view_if_needed()
            apply_btn.click()
            time.sleep(2)
    except Exception:
        pass

    cover_letter = generate_cover_letter(company, title)

    # Fill by CSS selectors
    field_fills = [
        ('input[name*="name" i]:not([name*="last"]):not([name*="company"]), input[placeholder*="Full name" i], input[placeholder*="Name" i]', APPLICANT["name"]),
        ('input[name*="first_name" i], input[placeholder*="First" i]', APPLICANT["first_name"]),
        ('input[name*="last_name" i], input[placeholder*="Last" i]', APPLICANT["last_name"]),
        ('input[type="email"], input[name*="email" i], input[placeholder*="Email" i]', APPLICANT["email"]),
        ('input[type="tel"], input[name*="phone" i], input[placeholder*="Phone" i]', APPLICANT["phone"]),
        ('input[name*="linkedin" i], input[placeholder*="LinkedIn" i]', APPLICANT["linkedin"]),
        ('input[name*="github" i], input[placeholder*="GitHub" i], input[name*="portfolio" i]', APPLICANT["github"]),
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

    # Fill by label association
    try:
        label_pairs = page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('label').forEach(label => {
                let input = null;
                const forId = label.getAttribute('for');
                if (forId) input = document.getElementById(forId);
                if (!input) input = label.querySelector('input, textarea, select');
                if (!input) {
                    const next = label.nextElementSibling;
                    if (next) input = next.matches('input,textarea,select') ? next : next.querySelector('input,textarea,select');
                }
                if (input && input.offsetParent !== null) {
                    results.push({
                        label: label.textContent.trim().substring(0, 100),
                        id: input.id || '', name: input.name || '',
                        tag: input.tagName.toLowerCase(), type: input.type || '',
                        value: input.value || '', placeholder: input.placeholder || ''
                    });
                }
            });
            return results;
        }''')
        for pair in label_pairs:
            if pair["value"]:
                continue
            selector = f"#{pair['id']}" if pair["id"] else f"[name='{pair['name']}']" if pair["name"] else None
            if not selector:
                continue
            if pair["tag"] in ("input", "textarea") and pair["type"] not in ("file", "checkbox", "radio", "hidden"):
                answer = answer_for_label(pair["label"], company, title)
                if answer:
                    try:
                        el = page.query_selector(selector)
                        if el and el.is_visible():
                            el.fill(answer)
                            time.sleep(0.2)
                    except Exception:
                        pass
    except Exception:
        pass

    # Upload resume
    try:
        file_input = page.query_selector('input[type="file"]')
        if file_input and os.path.exists(RESUME_PATH):
            file_input.set_input_files(RESUME_PATH)
            time.sleep(1.5)
    except Exception:
        pass

    # Fill textareas (cover letter)
    try:
        textareas = page.query_selector_all('textarea')
        for ta in textareas:
            if ta.is_visible() and not ta.input_value():
                ta.fill(cover_letter)
                break
    except Exception:
        pass

    # Handle selects
    try:
        for sel in page.query_selector_all('select'):
            if sel.is_visible():
                label_el = page.evaluate('''(el) => {
                    const l = el.closest('label') || document.querySelector('label[for="'+el.id+'"]');
                    return l ? l.textContent.trim().substring(0,80) : '';
                }''', sel)
                options = sel.evaluate('''(el) => Array.from(el.options).map(o => ({value:o.value, text:o.text}))''')
                opt_texts = [o["text"] for o in options if o["value"]]
                if opt_texts:
                    choice = pick_select_value(label_el, opt_texts)
                    if choice:
                        matching = next((o for o in options if o["text"] == choice), None)
                        if matching:
                            sel.select_option(value=matching["value"])
                            time.sleep(0.2)
    except Exception:
        pass

    # Handle checkboxes
    try:
        for cb in page.query_selector_all('input[type="checkbox"]'):
            if cb.is_visible() and not cb.is_checked():
                lbl = page.evaluate('''(el) => {
                    const l = el.closest('label') || document.querySelector('label[for="'+el.id+'"]');
                    return l ? l.textContent.trim().substring(0,80) : '';
                }''', cb)
                if any(kw in lbl.lower() for kw in ["agree", "consent", "acknowledge", "privacy", "terms", "confirm"]):
                    cb.check()
    except Exception:
        pass

    time.sleep(0.5)

    # Submit
    try:
        submit_btn = page.query_selector(
            'button[type="submit"], input[type="submit"], '
            'button:has-text("Submit"), button:has-text("Apply"), '
            'button:has-text("Send Application")')
        if not submit_btn or not submit_btn.is_visible():
            submit_btn = page.query_selector('form button:last-of-type, [class*="submit"] button')
        if submit_btn and submit_btn.is_visible():
            submit_btn.scroll_into_view_if_needed()
            time.sleep(0.3)
            submit_btn.click()
        else:
            return {"success": False, "error": "Submit button not found"}
    except Exception as e:
        return {"success": False, "error": f"Submit failed: {e}"}

    time.sleep(4)
    return check_result(page, company, "ashby")


def check_result(page, company: str, platform: str) -> dict:
    try:
        page_text = (page.text_content("body") or "").lower()
        page_url = page.url

        if "security code" in page_text or "verification code" in page_text or "verify your email" in page_text:
            code = fetch_security_code(company, platform)
            if code:
                log(f"    Got code: {code}")
                code_input = page.query_selector(
                    'input[name*="code"], input[name*="verify"], '
                    'input[placeholder*="code"], input[type="text"]:not([value])')
                if code_input and code_input.is_visible():
                    code_input.fill(code)
                    time.sleep(0.5)
                    verify_btn = page.query_selector('button:has-text("Verify"), button:has-text("Submit"), button[type="submit"]')
                    if verify_btn:
                        verify_btn.click()
                        time.sleep(4)
                        t2 = (page.text_content("body") or "").lower()
                        if any(x in t2 for x in ["thank", "submitted", "received", "confirmation", "successfully"]):
                            return {"success": True, "msg": "Confirmed after verification"}
            return {"success": False, "error": "NEEDS_VERIFICATION_CODE", "needs_code": True}

        if any(x in page_text for x in [
            "thank you", "application has been", "submitted",
            "received your application", "confirmation",
            "we have received", "successfully", "thanks for applying",
            "thanks for your interest"
        ]):
            return {"success": True, "msg": "Confirmation detected"}

        if "already applied" in page_text or "already submitted" in page_text:
            return {"success": False, "error": "Already applied", "already": True}

        errors = page.query_selector_all('[class*="error"], [role="alert"], [class*="invalid"]')
        err_texts = [e.text_content().strip() for e in errors if e.text_content().strip() and len(e.text_content().strip()) < 200]
        if err_texts:
            return {"success": False, "error": f"Validation: {'; '.join(err_texts[:3])[:150]}"}

        if any(x in page_url.lower() for x in ["confirmation", "thank", "success"]):
            return {"success": True, "msg": "Redirected to confirmation"}

        return {"success": False, "error": "No confirmation after submit"}
    except Exception as e:
        return {"success": False, "error": f"Result check: {e}"}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: APPLY — Greenhouse (Playwright)
# ═══════════════════════════════════════════════════════════════════════

def extract_gh_board_and_id(url: str, company: str) -> tuple:
    m = re.search(r'(?:boards|job-boards)\.(?:eu\.)?greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'gh_jid=(\d+)', url)
    if m:
        job_id = m.group(1)
        cl = company.lower().strip()
        board = KNOWN_GH_BOARDS.get(cl, cl.replace(" ", "").replace(".", ""))
        return board, job_id
    return None, None


def apply_greenhouse(page, board: str, job_id: str, company: str, title: str) -> dict:
    form_url = f"https://boards.greenhouse.io/{board}/jobs/{job_id}"
    try:
        page.goto(form_url, wait_until="networkidle", timeout=30000)
    except Exception:
        try:
            page.goto(form_url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            return {"success": False, "error": f"Load timeout: {e}"}

    try:
        page.wait_for_selector("#application-form", timeout=15000)
    except Exception:
        text = page.text_content("body") or ""
        if "not found" in text.lower() or "no longer" in text.lower():
            return {"success": False, "error": "Job no longer available"}
        return {"success": False, "error": "Form did not render"}

    time.sleep(1.5)
    cover_letter = generate_cover_letter(company, title)

    # Standard ID fills
    for fid, val in {"first_name": APPLICANT["first_name"], "last_name": APPLICANT["last_name"],
                     "email": APPLICANT["email"]}.items():
        try:
            el = page.query_selector(f"#{fid}")
            if el and el.is_visible():
                el.fill(val)
        except Exception:
            pass

    # Phone
    try:
        el = page.query_selector("#phone, input[type='tel']")
        if el and el.is_visible():
            el.fill(APPLICANT["phone"])
    except Exception:
        pass

    # Country dropdown (React Select)
    try:
        el = page.query_selector("#country")
        if el and el.is_visible():
            el.click()
            time.sleep(0.3)
            el.fill("United States")
            time.sleep(0.5)
            us_opt = page.query_selector("[class*='option']:has-text('United States')")
            if us_opt:
                us_opt.click()
            else:
                page.keyboard.press("Enter")
            time.sleep(0.3)
    except Exception:
        pass

    # Location autocomplete
    try:
        el = page.query_selector("#candidate-location")
        if el and el.is_visible():
            el.click()
            time.sleep(0.2)
            el.fill("Chico")
            time.sleep(1.0)
            suggestion = page.query_selector("[class*='option'], [class*='suggestion'], [role='option']")
            if suggestion and suggestion.is_visible():
                suggestion.click()
            else:
                page.keyboard.press("Enter")
            time.sleep(0.3)
    except Exception:
        pass

    # Resume upload
    try:
        file_input = page.query_selector("#resume, input[type='file']")
        if file_input and os.path.exists(RESUME_PATH):
            file_input.set_input_files(RESUME_PATH)
            time.sleep(1.5)
    except Exception:
        pass

    # Cover letter upload or text
    try:
        cl_file = page.query_selector("#cover_letter[type='file']")
        if cl_file:
            pass  # Skip file-based cover letter
        else:
            cl_text = page.query_selector("#cover_letter, textarea[name*='cover']")
            if cl_text and cl_text.is_visible():
                cl_text.fill(cover_letter)
    except Exception:
        pass

    # LinkedIn field
    try:
        for sel in ['input[name*="linkedin" i]', 'input[placeholder*="LinkedIn" i]',
                    'input[id*="linkedin" i]', 'input[autocomplete="url"]']:
            el = page.query_selector(sel)
            if el and el.is_visible() and not el.input_value():
                el.fill(APPLICANT["linkedin"])
                break
    except Exception:
        pass

    # Custom question fields — scan labels
    try:
        label_pairs = page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('label').forEach(label => {
                let input = null;
                const forId = label.getAttribute('for');
                if (forId) input = document.getElementById(forId);
                if (!input) input = label.querySelector('input, textarea, select');
                if (!input) {
                    const next = label.nextElementSibling;
                    if (next) input = next.matches('input,textarea,select') ? next : next.querySelector('input,textarea,select');
                }
                if (input && input.offsetParent !== null) {
                    results.push({
                        label: label.textContent.trim().substring(0, 100),
                        id: input.id || '', name: input.name || '',
                        tag: input.tagName.toLowerCase(), type: input.type || '',
                        value: input.value || ''
                    });
                }
            });
            return results;
        }''')
        for pair in label_pairs:
            if pair["value"]:
                continue
            sel = f"#{pair['id']}" if pair["id"] else f"[name='{pair['name']}']" if pair["name"] else None
            if not sel:
                continue
            if pair["tag"] == "select":
                try:
                    sel_el = page.query_selector(sel)
                    if sel_el and sel_el.is_visible():
                        options = sel_el.evaluate('''(el) => Array.from(el.options).map(o => ({value:o.value, text:o.text}))''')
                        opt_texts = [o["text"] for o in options if o["value"]]
                        if opt_texts:
                            choice = pick_select_value(pair["label"], opt_texts)
                            if choice:
                                matching = next((o for o in options if o["text"] == choice), None)
                                if matching:
                                    sel_el.select_option(value=matching["value"])
                except Exception:
                    pass
            elif pair["tag"] in ("input", "textarea") and pair["type"] not in ("file", "checkbox", "radio", "hidden"):
                answer = answer_for_label(pair["label"], company, title)
                if answer:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            el.fill(answer)
                    except Exception:
                        pass
    except Exception:
        pass

    # Checkboxes
    try:
        for cb in page.query_selector_all('input[type="checkbox"]'):
            if cb.is_visible() and not cb.is_checked():
                lbl = page.evaluate('''(el) => {
                    const l = el.closest('label') || document.querySelector('label[for="'+el.id+'"]');
                    return l ? l.textContent.trim().substring(0,80) : '';
                }''', cb)
                if any(kw in lbl.lower() for kw in ["agree", "consent", "acknowledge", "privacy", "terms"]):
                    cb.check()
    except Exception:
        pass

    # EEO selects — decline
    for eid in ["gender", "hispanic_ethnicity", "veteran_status", "disability_status", "race"]:
        try:
            el = page.query_selector(f"#{eid}")
            if el and el.is_visible():
                options = el.evaluate('''(el) => Array.from(el.options).map(o => ({value:o.value, text:o.text}))''')
                for o in options:
                    if "decline" in o["text"].lower() or "prefer not" in o["text"].lower():
                        el.select_option(value=o["value"])
                        break
        except Exception:
            pass

    time.sleep(0.5)

    # Submit
    try:
        submit_btn = page.query_selector(
            '#submit_app, button[type="submit"], input[type="submit"], '
            'button:has-text("Submit Application"), button:has-text("Submit")')
        if submit_btn and submit_btn.is_visible():
            # Enable if disabled (Greenhouse sometimes disables submit)
            page.evaluate('''(el) => { el.disabled = false; el.removeAttribute('disabled'); }''', submit_btn)
            submit_btn.scroll_into_view_if_needed()
            time.sleep(0.3)
            submit_btn.click()
        else:
            return {"success": False, "error": "Submit button not found"}
    except Exception as e:
        return {"success": False, "error": f"Submit failed: {e}"}

    time.sleep(4)
    return check_result(page, company, "greenhouse")


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: APPLY — Main orchestrator
# ═══════════════════════════════════════════════════════════════════════

def run_apply(platform: str = None, min_score: float = 60.0, limit: int = 0,
              resume_from: int = 0, delay: float = 3.0, retry_failed: bool = False):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    log(f"\n{'='*70}")
    log(f"PHASE 3: APPLY {'(retry failed)' if retry_failed else ''}")
    log(f"{'='*70}")
    start = time.time()

    status = "apply_failed" if retry_failed else "new"

    # Get jobs per platform
    platforms_to_run = []
    if platform:
        platforms_to_run = [platform]
    else:
        platforms_to_run = ["ashby", "greenhouse"]  # Lever apply uses Wraith, not Playwright

    all_jobs = {}
    for p in platforms_to_run:
        jobs = get_viable_jobs(platform=p, min_score=min_score, status=status)
        if jobs:
            all_jobs[p] = jobs
            log(f"  {p}: {len(jobs)} jobs")

    if not all_jobs:
        log("No viable jobs to apply to.")
        return

    total_jobs = sum(len(v) for v in all_jobs.values())
    log(f"Total: {total_jobs} jobs across {len(all_jobs)} platforms")

    successes = 0
    failures = 0
    needs_code_count = 0
    job_num = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}, locale="en-US")
        page = context.new_page()

        # Interleave platforms for variety (reduces rate-limit risk)
        interleaved = []
        max_len = max(len(v) for v in all_jobs.values())
        for i in range(max_len):
            for plat in platforms_to_run:
                if plat in all_jobs and i < len(all_jobs[plat]):
                    interleaved.append((plat, all_jobs[plat][i]))

        batch = interleaved[resume_from:]
        if limit > 0:
            batch = batch[:limit]

        for i, (plat, job) in enumerate(batch):
            job_num = i + 1 + resume_from
            log(f"\n[{job_num}/{len(batch)}] {plat.upper()} | {job['company']} — {job['title'][:50]} (score={job['fit_score']})")

            try:
                if plat == "ashby":
                    result = apply_ashby(page, job["url"], job["company"], job["title"])
                elif plat == "greenhouse":
                    board, jid = extract_gh_board_and_id(job["url"], job["company"])
                    if not board or not jid:
                        log(f"  SKIP: Can't extract board/id from {job['url'][:60]}")
                        update_job_status(job["id"], "apply_failed")
                        failures += 1
                        continue
                    result = apply_greenhouse(page, board, jid, job["company"], job["title"])
                else:
                    log(f"  SKIP: {plat} not supported for Playwright apply")
                    continue

                cl = generate_cover_letter(job["company"], job["title"])

                if result.get("success"):
                    log(f"  >>> SUCCESS: {result.get('msg', '')} <<<")
                    successes += 1
                    update_job_status(job["id"], "applied", cover_letter=cl)
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
                try:
                    page.close()
                except Exception:
                    pass
                page = context.new_page()

            # Progress report every 10
            if job_num % 10 == 0:
                elapsed = time.time() - start
                log(f"--- Progress: {job_num} done | OK={successes} FAIL={failures} CODE={needs_code_count} | {elapsed/60:.1f}min ---")

            if i < len(batch) - 1:
                time.sleep(delay)

        browser.close()

    elapsed = time.time() - start
    log(f"\nAPPLY DONE in {elapsed/60:.1f}min")
    log(f"  Success: {successes}")
    log(f"  Failed: {failures}")
    log(f"  Needs code: {needs_code_count}")
    log(f"  Rate: {(successes + failures + needs_code_count) / (elapsed/60):.1f} apps/min")


# ═══════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════

def show_stats():
    conn = get_db()
    c = conn.cursor()

    print(f"\n{'='*60}")
    print(f"JOB HUNTER STATS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # Status breakdown
    rows = c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY COUNT(*) DESC").fetchall()
    print(f"\n  Status Distribution:")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")

    total = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"    {'TOTAL':20s} {total:>6d}")

    # Platform breakdown
    rows = c.execute("SELECT source, COUNT(*) FROM jobs WHERE status='applied' GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
    print(f"\n  Applied by Platform:")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")

    # Viable unapplied
    rows = c.execute("SELECT source, COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60 GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
    print(f"\n  Viable Unapplied (fit>=60):")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")
    viable = c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60").fetchone()[0]
    print(f"    {'TOTAL':20s} {viable:>6d}")

    # Score brackets for new
    rows = c.execute("""
        SELECT CASE WHEN fit_score >= 80 THEN '80+'
                    WHEN fit_score >= 60 THEN '60-79'
                    WHEN fit_score >= 40 THEN '40-59'
                    ELSE '<40' END as bracket, COUNT(*)
        FROM jobs WHERE status='new'
        GROUP BY bracket ORDER BY bracket DESC
    """).fetchall()
    print(f"\n  Score Brackets (new jobs):")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")

    # Top scorers
    rows = c.execute("""
        SELECT company, title, fit_score, source FROM jobs
        WHERE status='new' AND fit_score >= 70
        ORDER BY fit_score DESC LIMIT 15
    """).fetchall()
    if rows:
        print(f"\n  Top 15 Unapplied Jobs:")
        for r in rows:
            print(f"    [{r[2]:3.0f}] {r[0][:20]:20s} {r[1][:45]} ({r[3]})")

    conn.close()
    print(f"\n{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    global LOG_PATH

    parser = argparse.ArgumentParser(description="Mega Pipeline — Scrape + Score + Apply")
    parser.add_argument("--scrape", action="store_true", help="Run scrape phase")
    parser.add_argument("--rescore", action="store_true", help="Fetch descriptions + rescore")
    parser.add_argument("--apply", action="store_true", help="Run apply phase")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    parser.add_argument("--stats", action="store_true", help="Show current stats")
    parser.add_argument("--retry-failed", action="store_true", help="Retry apply_failed jobs")
    parser.add_argument("--platform", type=str, default=None, help="Filter apply to platform (ashby/greenhouse)")
    parser.add_argument("--min-score", type=float, default=60.0, help="Minimum fit score")
    parser.add_argument("--limit", type=int, default=0, help="Max jobs to apply to (0=all)")
    parser.add_argument("--resume-from", type=int, default=0, help="Skip first N jobs")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between applies (seconds)")
    parser.add_argument("--workers", type=int, default=100, help="Max concurrent scrape workers")
    args = parser.parse_args()

    # Setup logging
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_PATH = os.path.join(LOG_DIR, f"mega_pipeline_{ts}.txt")

    log(f"MEGA PIPELINE started at {datetime.now().isoformat()}")
    log(f"Args: {vars(args)}")

    if args.stats:
        show_stats()
        return

    if args.all:
        args.scrape = True
        args.rescore = True
        args.apply = True

    if not any([args.scrape, args.rescore, args.apply, args.retry_failed]):
        parser.print_help()
        print("\nExample: python mega_pipeline.py --all")
        print("Example: python mega_pipeline.py --apply --platform ashby --limit 20")
        return

    pipeline_start = time.time()

    if args.scrape:
        run_scrape(max_workers=args.workers)

    if args.rescore:
        run_rescore(max_workers=args.workers)

    if args.apply or args.retry_failed:
        run_apply(
            platform=args.platform, min_score=args.min_score,
            limit=args.limit, resume_from=args.resume_from,
            delay=args.delay, retry_failed=args.retry_failed)

    elapsed = time.time() - pipeline_start
    log(f"\n{'='*70}")
    log(f"MEGA PIPELINE COMPLETE — {elapsed/60:.1f}min total")
    log(f"{'='*70}")

    show_stats()


if __name__ == "__main__":
    main()
