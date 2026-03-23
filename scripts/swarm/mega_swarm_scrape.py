"""
MEGA SWARM SCRAPER — 200+ parallel workers scraping Greenhouse + Ashby job boards
==================================================================================
Phase 1: Scrape all known tech company job boards via public APIs
Phase 2: Score and insert into DB
No browser needed — pure HTTP with ThreadPoolExecutor.

Run: .venv\Scripts\python.exe mega_swarm_scrape.py [--workers N]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import re
import sqlite3
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
LOG_PATH = r"J:\job-hunter-mcp\mega_swarm_scrape_log.txt"

# ─── Company Lists ────────────────────────────────────────────────────
# Greenhouse companies (board token → company name)
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

# Ashby companies (slug → company name)
ASHBY_BOARDS = {
    # AI / ML
    "perplexity": "Perplexity AI", "openai": "OpenAI", "anthropic": "Anthropic",
    "cohere": "Cohere", "mistral": "Mistral AI", "together": "Together AI",
    "reka": "Reka", "adept": "Adept AI", "inflection": "Inflection AI",
    "characterai": "Character AI", "elevenlab": "ElevenLabs", "descript": "Descript",
    "deepgram": "Deepgram", "assemblyai": "AssemblyAI", "livekit": "LiveKit",
    "baseten": "Baseten", "modal": "Modal", "anyscale": "Anyscale",
    "replicate": "Replicate", "wandb": "Weights & Biases", "langchain": "LangChain",
    "pinecone": "Pinecone", "weaviate": "Weaviate", "qdrant": "Qdrant",
    "chroma": "Chroma", "lancedb": "LanceDB",
    # Infrastructure
    "render": "Render", "railway": "Railway", "vercel": "Vercel",
    "supabase": "Supabase", "netlify": "Netlify", "fly": "Fly.io",
    "neon": "Neon", "upstash": "Upstash", "cloudflare": "Cloudflare",
    "tailscale": "Tailscale", "temporal": "Temporal",
    # Dev tools
    "replit": "Replit", "sourcegraph": "Sourcegraph", "linear": "Linear",
    "retool": "Retool", "sentry": "Sentry", "posthog": "PostHog",
    "grafana": "Grafana Labs", "highlight": "Highlight", "axiom": "Axiom",
    # Fintech
    "stripe": "Stripe", "plaid": "Plaid", "mercury": "Mercury",
    "ramp": "Ramp", "brex": "Brex", "coinbase": "Coinbase",
    "phantom": "Phantom", "alchemy": "Alchemy",
    # Data
    "clickhouse": "ClickHouse", "cockroach": "Cockroach Labs",
    "planetscale": "PlanetScale", "timescale": "Timescale",
    "motherduck": "MotherDuck", "duckdb": "DuckDB",
    "fivetran": "Fivetran", "airbyte": "Airbyte",
    # Security
    "chainguard": "Chainguard", "wiz": "Wiz", "orca": "Orca Security",
    "bitwarden": "Bitwarden", "1password": "1Password",
    "snyk": "Snyk", "lacework": "Lacework", "vanta": "Vanta",
    # Consumer
    "notion": "Notion", "figma": "Figma", "coda": "Coda",
    "miro": "Miro", "airtable": "Airtable",
    "discord": "Discord", "reddit": "Reddit",
    # Enterprise
    "rippling": "Rippling", "gusto": "Gusto", "lattice": "Lattice",
    "ashby": "Ashby", "lever": "Lever",
    "zapier": "Zapier", "make": "Make",
    # Other
    "resend": "Resend", "clerk": "Clerk", "stytch": "Stytch",
    "turso": "Turso", "drizzle": "Drizzle",
    "cal": "Cal.com", "documenso": "Documenso",
    "harvey": "Harvey AI", "casetext": "Casetext",
    "cursor": "Cursor", "tabnine": "Tabnine", "codeium": "Codeium",
}

# ─── Scoring ──────────────────────────────────────────────────────────

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
    "api", "rest", "graphql", "fastapi",
]

NEGATIVE_KEYWORDS = [
    "senior staff", "principal", "director", "vp ",
    "phd required", "15+ years",
    "clearance required", "ts/sci",
    "java ", "c# ", ".net ", "angular", "php ",
]


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

    if "remote" in text:
        score += 5

    return max(0, min(100, score))


# ─── Greenhouse Scraper ──────────────────────────────────────────────

def scrape_greenhouse_board(board_token: str, company: str) -> list:
    """Scrape all jobs from a Greenhouse board via public API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 JobHunter/1.0"
        })
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs_data = data.get("jobs", [])

        results = []
        for j in jobs_data:
            title = j.get("title", "")
            jid = str(j.get("id", ""))
            location = j.get("location", {}).get("name", "Remote")
            url = j.get("absolute_url", f"https://boards.greenhouse.io/{board_token}/jobs/{jid}")
            updated = j.get("updated_at", "")

            # Generate stable ID
            stable_id = hashlib.md5(f"greenhouse:{board_token}:{jid}".encode()).hexdigest()[:8]

            results.append({
                "id": stable_id,
                "source": "greenhouse",
                "source_id": jid,
                "title": title,
                "company": company,
                "url": url,
                "location": location,
                "description": "",  # Don't fetch full descriptions to keep fast
                "date_posted": updated,
                "fit_score": score_job(title),
            })

        return results
    except Exception as e:
        return []


# ─── Ashby Scraper ───────────────────────────────────────────────────

def scrape_ashby_board(slug: str, company: str) -> list:
    """Scrape all jobs from an Ashby board by fetching the HTML page."""
    url = f"https://jobs.ashbyhq.com/{slug}"
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return []

        # Ashby embeds job data as JSON in script tags
        # Look for __NEXT_DATA__ or similar
        json_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
        if not json_match:
            # Try alternate: look for job posting data in the page
            # Ashby uses a custom format — extract job links
            job_links = re.findall(
                rf'href="/{re.escape(slug)}/([a-f0-9-]{{36}})"[^>]*>([^<]+)',
                resp.text
            )
            results = []
            for job_id, title in job_links:
                title = title.strip()
                if not title or len(title) < 3:
                    continue
                stable_id = hashlib.md5(f"ashby:{slug}:{job_id}".encode()).hexdigest()[:8]
                results.append({
                    "id": stable_id,
                    "source": "ashby",
                    "source_id": job_id,
                    "title": title,
                    "company": company,
                    "url": f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                    "location": "Remote",
                    "description": "",
                    "date_posted": "",
                    "fit_score": score_job(title),
                })
            return results

        # Parse __NEXT_DATA__
        try:
            next_data = json.loads(json_match.group(1))
            # Navigate to job postings
            props = next_data.get("props", {}).get("pageProps", {})
            postings = props.get("jobPostings", props.get("jobs", []))

            results = []
            for p in postings:
                title = p.get("title", "")
                job_id = p.get("id", p.get("jobPostingId", ""))
                location = p.get("locationName", p.get("location", "Remote"))

                stable_id = hashlib.md5(f"ashby:{slug}:{job_id}".encode()).hexdigest()[:8]
                results.append({
                    "id": stable_id,
                    "source": "ashby",
                    "source_id": str(job_id),
                    "title": title,
                    "company": company,
                    "url": f"https://jobs.ashbyhq.com/{slug}/{job_id}",
                    "location": location or "Remote",
                    "description": "",
                    "date_posted": "",
                    "fit_score": score_job(title),
                })
            return results
        except json.JSONDecodeError:
            return []

    except Exception as e:
        return []


# ─── DB Operations ───────────────────────────────────────────────────

def insert_jobs(jobs: list) -> int:
    """Insert jobs into DB, skipping duplicates. Returns count of new jobs."""
    if not jobs:
        return 0

    conn = sqlite3.connect(DB_PATH, timeout=30)
    inserted = 0

    for job in jobs:
        try:
            # Check if exists by URL or source+source_id
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
                datetime.now(timezone.utc).isoformat(),
                job["fit_score"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    return inserted


# ─── Logging ─────────────────────────────────────────────────────────

log_lock = None

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── Main Swarm ──────────────────────────────────────────────────────

def scrape_worker(task: dict) -> dict:
    """Worker function for thread pool."""
    platform = task["platform"]
    slug = task["slug"]
    company = task["company"]

    try:
        if platform == "greenhouse":
            jobs = scrape_greenhouse_board(slug, company)
        elif platform == "ashby":
            jobs = scrape_ashby_board(slug, company)
        else:
            jobs = []

        if jobs:
            new_count = insert_jobs(jobs)
            return {"company": company, "platform": platform, "total": len(jobs), "new": new_count, "error": None}
        else:
            return {"company": company, "platform": platform, "total": 0, "new": 0, "error": None}
    except Exception as e:
        return {"company": company, "platform": platform, "total": 0, "new": 0, "error": str(e)}


def run_mega_swarm(max_workers: int = 100):
    start_time = datetime.now(timezone.utc)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"=== MEGA SWARM SCRAPE {start_time.isoformat()} ===\n")

    # Build task list
    tasks = []
    for slug, company in GREENHOUSE_BOARDS.items():
        tasks.append({"platform": "greenhouse", "slug": slug, "company": company})
    for slug, company in ASHBY_BOARDS.items():
        tasks.append({"platform": "ashby", "slug": slug, "company": company})

    log(f"{'='*70}")
    log(f"MEGA SWARM SCRAPE — {len(tasks)} company boards")
    log(f"  Greenhouse boards: {len(GREENHOUSE_BOARDS)}")
    log(f"  Ashby boards: {len(ASHBY_BOARDS)}")
    log(f"  Max workers: {max_workers}")
    log(f"{'='*70}")

    total_jobs_found = 0
    total_new_inserted = 0
    successes = 0
    failures = 0
    results_by_company = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(scrape_worker, task): task for task in tasks}

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result(timeout=30)
                results_by_company.append(result)

                if result["total"] > 0:
                    total_jobs_found += result["total"]
                    total_new_inserted += result["new"]
                    successes += 1
                    if result["new"] > 0:
                        log(f"  {result['company']} ({result['platform']}): {result['total']} jobs, {result['new']} NEW")
                else:
                    failures += 1

            except Exception as e:
                failures += 1

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Count viable new jobs
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60")
    viable = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60 AND source='ashby'")
    viable_ashby = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60 AND source='greenhouse'")
    viable_gh = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs")
    total_db = c.fetchone()[0]
    conn.close()

    log(f"\n{'='*70}")
    log(f"MEGA SWARM SCRAPE COMPLETE")
    log(f"{'='*70}")
    log(f"Duration: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    log(f"Boards scraped: {successes} success, {failures} empty/failed")
    log(f"Total jobs found: {total_jobs_found}")
    log(f"New jobs inserted: {total_new_inserted}")
    log(f"Viable (fit>=60): {viable} (Ashby: {viable_ashby}, Greenhouse: {viable_gh})")
    log(f"Total DB jobs: {total_db}")
    log(f"Rate: {total_jobs_found/(elapsed or 1)*60:.0f} jobs/min")
    log(f"{'='*70}")

    # Top companies by new jobs
    top = sorted([r for r in results_by_company if r["new"] > 0], key=lambda x: -x["new"])[:30]
    if top:
        log(f"\nTop companies by NEW jobs:")
        for r in top:
            log(f"  {r['company']} ({r['platform']}): +{r['new']} new ({r['total']} total)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=100, help="Max concurrent workers")
    args = parser.parse_args()
    run_mega_swarm(max_workers=args.workers)
