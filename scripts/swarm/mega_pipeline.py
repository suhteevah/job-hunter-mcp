"""
MEGA PIPELINE — Unified Scrape + Score + Apply (Wraith-Only)
=============================================================
Single entry point for the entire job hunting pipeline.
Zero Playwright dependency — all browser automation via Wraith CDP/native.

Phases:
  1. SCRAPE  — Hit Greenhouse/Ashby/Lever APIs, insert to DB
  2. RESCORE — Fetch full descriptions for title-only scored jobs, rescore
  3. APPLY   — Wraith CDP for Greenhouse+Ashby, Wraith native for Lever

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
# WRAITH FORM INTELLIGENCE — Parse snapshot, fill fields
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
    if "education" in ll or "degree" in ll or "school" in ll:
        return "Butte College — Associates level coursework in Computer Science"
    if "business trip" in ll or "travel" in ll or "relocat" in ll or "willing" in ll:
        return "Yes"
    if "clearance" in ll:
        return "No"
    if "race" in ll or "gender" in ll or "ethnic" in ll or "veteran" in ll or "disability" in ll:
        return "Decline to self-identify"
    if any(x in ll for x in ["how are you using ai", "ai experiment", "ai tool"]):
        return ("I use AI daily — built 10+ production MCP servers, a 27K-line Rust browser automation "
                "framework with AI agent orchestration, and deployed LLM-powered RAG pipelines.")
    if any(x in ll for x in ["project", "achievement", "accomplishment", "proud of"]):
        return ("Built a weather prediction trading bot achieving 20x returns, "
                "a 27K-line Rust browser automation framework (Wraith), and distributed AI inference "
                "infrastructure serving multiple models across heterogeneous GPU hardware.")
    if any(x in ll for x in ["cover letter", "additional", "anything else", "why", "tell us", "about your",
                              "motivation", "excite", "interest", "passion", "background", "describe",
                              "what excites"]):
        return generate_cover_letter(company, title)
    if any(x in ll for x in ["facebook", "instagram", "twitter", "social media"]):
        return "N/A"
    if any(x in ll for x in ["required", "*"]) and not any(x in ll for x in ["name", "email", "phone"]):
        return "Yes"
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

def fetch_security_code(company: str, platform: str = "greenhouse", max_wait: int = 15) -> str:
    if not GMAIL_APP_PASSWORD:
        return ""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        if platform == "greenhouse":
            search_q = '(FROM "greenhouse" SUBJECT "security code" UNSEEN)'
        else:
            search_q = '(FROM "ashby" SUBJECT "verification" UNSEEN)'
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
# PHASE 3: APPLY — Greenhouse via Wraith CDP
# ═══════════════════════════════════════════════════════════════════════

def apply_greenhouse_cdp(wraith: WraithMCPClient, url: str, company: str, title: str) -> dict:
    """Apply to a Greenhouse job using Wraith CDP."""
    # Convert custom career page URLs to standard Greenhouse embed URLs
    gh_jid_match = re.search(r'gh_jid=(\d+)', url)
    if gh_jid_match and 'greenhouse.io' not in url:
        jid = gh_jid_match.group(1)
        url = f"https://boards.greenhouse.io/embed/job_app?token={jid}"
        log(f"  Converted to embed URL: {url[:60]}")
    elif 'job-boards.greenhouse.io' in url:
        jid_match = re.search(r'/jobs/(\d+)', url)
        if jid_match:
            jid = jid_match.group(1)
            url = f"https://boards.greenhouse.io/embed/job_app?token={jid}"
    elif 'boards.greenhouse.io' in url and '/embed/' not in url:
        jid_match = re.search(r'/jobs/(\d+)', url)
        if jid_match:
            jid = jid_match.group(1)
            url = f"https://boards.greenhouse.io/embed/job_app?token={jid}"

    snap = wraith.navigate_cdp(url)
    if "not found" in snap.lower() or "no longer" in snap.lower():
        return {"success": False, "error": "Job no longer available"}

    time.sleep(2)
    snap = wraith.snapshot()
    elements = parse_snapshot_refs(snap)

    cover_letter = generate_cover_letter(company, title)

    # Fill all input fields
    for el in elements:
        if el["tag"] in ("input", "textarea"):
            answer = guess_field_answer(el["text"], company, title)
            if answer:
                wraith.fill(el["ref"], answer)
                time.sleep(0.3)

    # Upload resume
    for el in elements:
        if el["tag"] == "input" and "file" in el["text"].lower():
            wraith.upload_file(el["ref"], RESUME_PATH)
            time.sleep(1)
            break
    else:
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

    # Handle React Select custom dropdowns (combobox-like divs)
    for el in elements3:
        if el["tag"] in ("div", "span", "combobox") and any(x in el["text"].lower() for x in
                ["select...", "choose", "country", "authorized", "hear about", "source",
                 "sponsor", "visa", "gender", "race", "veteran", "disability"]):
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
            for el in parse_snapshot_refs(snap_final):
                if el["tag"] == "input" and any(x in el["text"].lower() for x in ["code", "verify"]):
                    wraith.fill(el["ref"], code)
                    time.sleep(0.5)
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

    # Check for validation errors
    if any(x in snap_lower for x in ["this field is required", "please fill", "validation"]):
        # Try to extract what failed
        errors = []
        for el in parse_snapshot_refs(snap_final):
            if any(x in el["text"].lower() for x in ["required", "please", "invalid", "error"]):
                errors.append(el["text"][:60])
        return {"success": False, "error": f"Validation: {'; '.join(errors[:3])}" if errors else "Validation error"}

    return {"success": False, "error": "No confirmation after submit"}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: APPLY — Ashby via Wraith CDP
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
# PHASE 3: APPLY — Lever via Wraith native
# ═══════════════════════════════════════════════════════════════════════

def apply_lever_native(wraith: WraithMCPClient, url: str, company: str, title: str) -> dict:
    """Apply to a Lever job using Wraith native renderer (server-rendered HTML)."""
    apply_url = url.rstrip("/") + "/apply"
    snap = wraith.navigate(apply_url)

    if "not found" in snap.lower() or "no longer" in snap.lower() or "page not found" in snap.lower():
        return {"success": False, "error": "Job no longer available"}

    time.sleep(2)
    snap = wraith.snapshot()
    elements = parse_snapshot_refs(snap)

    if not elements:
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

    verify = wraith.verify_submission()
    verify_lower = verify.lower()

    if "confirmed" in verify_lower or "success" in verify_lower or "likely" in verify_lower:
        return {"success": True, "msg": f"Wraith verified: {verify[:50]}"}

    snap_final = wraith.snapshot()
    snap_lower = snap_final.lower()

    if any(x in snap_lower for x in ["thank you", "submitted", "received", "confirmation",
                                      "successfully", "thanks for applying"]):
        return {"success": True, "msg": "Confirmation text detected"}

    if "already applied" in snap_lower or "already submitted" in snap_lower:
        return {"success": False, "error": "Already applied", "already": True}

    return {"success": False, "error": "No confirmation after submit"}


# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: APPLY — Main orchestrator (Wraith-only)
# ═══════════════════════════════════════════════════════════════════════

def run_apply(platform: str = None, min_score: float = 60.0, limit: int = 0,
              resume_from: int = 0, delay: float = 3.0, retry_failed: bool = False):
    log(f"\n{'='*70}")
    log(f"PHASE 3: APPLY {'(retry failed)' if retry_failed else ''} [Wraith CDP]")
    log(f"{'='*70}")
    start = time.time()

    status = "apply_failed" if retry_failed else "new"
    platforms = [platform] if platform else ["ashby", "greenhouse", "lever"]

    all_jobs = {}
    for p in platforms:
        jobs = get_viable_jobs(platform=p, min_score=min_score, status=status)
        if jobs:
            all_jobs[p] = jobs
            log(f"  {p}: {len(jobs)} jobs")

    if not all_jobs:
        log("No viable jobs to apply to.")
        return

    total_jobs = sum(len(v) for v in all_jobs.values())
    log(f"Total: {total_jobs} jobs across {len(all_jobs)} platforms")

    # Start Wraith
    log("Starting Wraith MCP client...")
    wraith = WraithMCPClient()
    wraith.start()
    time.sleep(2)

    engine = wraith.engine_status()
    log(f"Engine: {engine[:100]}")

    successes = 0
    failures = 0
    needs_code_count = 0
    job_num = 0

    # Interleave platforms for variety
    interleaved = []
    max_len = max(len(v) for v in all_jobs.values())
    for i in range(max_len):
        for plat in platforms:
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
            traceback.print_exc()
            failures += 1
            update_job_status(job["id"], "apply_failed")

        # Progress report every 10
        if job_num % 10 == 0:
            elapsed = time.time() - start
            log(f"--- Progress: {job_num} done | OK={successes} FAIL={failures} CODE={needs_code_count} | {elapsed/60:.1f}min ---")

        if i < len(batch) - 1:
            time.sleep(delay)

    # Shutdown Wraith
    wraith.stop()

    elapsed = time.time() - start
    log(f"\nAPPLY DONE in {elapsed/60:.1f}min")
    log(f"  Success: {successes}")
    log(f"  Failed: {failures}")
    log(f"  Needs code: {needs_code_count}")
    total_attempted = successes + failures + needs_code_count
    if elapsed > 0 and total_attempted > 0:
        log(f"  Rate: {total_attempted / (elapsed/60):.1f} apps/min")


# ═══════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════

def show_stats():
    conn = get_db()
    c = conn.cursor()

    print(f"\n{'='*60}")
    print(f"JOB HUNTER STATS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    rows = c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY COUNT(*) DESC").fetchall()
    print(f"\n  Status Distribution:")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")
    total = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"    {'TOTAL':20s} {total:>6d}")

    rows = c.execute("SELECT source, COUNT(*) FROM jobs WHERE status='applied' GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
    print(f"\n  Applied by Platform:")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")

    rows = c.execute("SELECT source, COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60 GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
    print(f"\n  Viable Unapplied (fit>=60):")
    for r in rows:
        print(f"    {r[0]:20s} {r[1]:>6d}")
    viable = c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60").fetchone()[0]
    print(f"    {'TOTAL':20s} {viable:>6d}")

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

    parser = argparse.ArgumentParser(description="Mega Pipeline — Scrape + Score + Apply (Wraith-Only)")
    parser.add_argument("--scrape", action="store_true", help="Run scrape phase")
    parser.add_argument("--rescore", action="store_true", help="Fetch descriptions + rescore")
    parser.add_argument("--apply", action="store_true", help="Run apply phase")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    parser.add_argument("--stats", action="store_true", help="Show current stats")
    parser.add_argument("--retry-failed", action="store_true", help="Retry apply_failed jobs")
    parser.add_argument("--platform", type=str, default=None, help="Filter apply to platform (ashby/greenhouse/lever)")
    parser.add_argument("--min-score", type=float, default=60.0, help="Minimum fit score")
    parser.add_argument("--limit", type=int, default=0, help="Max jobs to apply to (0=all)")
    parser.add_argument("--resume-from", type=int, default=0, help="Skip first N jobs")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between applies (seconds)")
    parser.add_argument("--workers", type=int, default=100, help="Max concurrent scrape workers")
    args = parser.parse_args()

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
