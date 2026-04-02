#!/usr/bin/env python
"""
probe_more_gh_boards.py
Probe NEW Greenhouse board slugs we haven't checked yet.
Analytics, internal tools, cloud platforms, legal tech, AI/ML, defense, etc.
Inserts ALL jobs found. Runs scorer afterward if requested.

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe probe_more_gh_boards.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import hashlib
import json
import re
import logging
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
GH_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
REQUEST_TIMEOUT = 12
DELAY_BETWEEN_REQUESTS = 0.25  # seconds

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("probe_more_gh")

# ---------------------------------------------------------------------------
# NEW slugs to probe — all the ones not in probe_greenhouse_boards.py
# ---------------------------------------------------------------------------
SLUG_VARIANTS = [
    # Analytics
    "amplitude", "amplitudeinc",
    "segment", "segmentio",
    "rudderstack",
    "mparticle",

    # Internal tools
    "retool", "retooljobs",
    "airplane",
    "superblocks",

    # Cloud platforms
    "render", "renderinc",
    "railway",
    "fly", "flydotio",

    # Hosting / Vercel / Netlify variants
    "vercel", "verceljobs",
    "netlify", "netlifyjobs",

    # Fintech
    "navan", "navanjobs",
    "brex", "brexjobs",

    # Legal tech
    "relativity", "relativiteinc",
    "clio", "cliojobs",
    "ironclad", "ironcladinc",

    # HR / payroll
    "justworks", "justworksjobs",
    "rippling", "ripplingjobs",

    # Product analytics / onboarding
    "pendo", "pendoio",
    "chameleon", "chameleonio",
    "appcues",

    # Data / analytics infra
    "dbtlabs", "dbt-labs", "getdbt",
    "fivetran", "fifetran",

    # Distributed SQL / time-series
    "yugabyte", "yugabyteinc",
    "timescaledb", "timescale",

    # Observability
    "observeinc", "observe",
    "chronosphere",
    "lightstep",

    # Cloud security
    "lacework", "laceworkinc",
    "orcasecurity", "orca",
    "snyk", "snykjobs",

    # Streaming / real-time DB
    "materialize", "materializeinc",
    "readyset",
    "neon", "neonjobs",

    # Mobile / cross-platform
    "expo", "expojobs",
    "ionic", "ionicjobs",

    # BaaS / open source BaaS
    "supabase", "supabasejobs",
    "appwrite",
    "convex", "convexinc",

    # MLOps / experiment tracking
    "weightsandbiases", "wandb",
    "cometml", "cometai",
    "neptuneai", "neptune",

    # AI labs
    "openai", "openaijobs",
    "google-deepmind", "googledeepmind", "deepmind",
    "xai", "xaijobs",
    "mistralai", "mistral",
    "cohere", "cohereinc",
    "inflectionai", "inflection",

    # Autonomous / robotics
    "cruise", "cruisejobs",
    "waymo", "waymojobs",
    "aurora", "aurorajobs",
    "applied-intuition", "appliedintuition",
    "anyscale", "anyscalejobs",

    # Chips / AI hardware
    "cerebras", "cerebrassystems",
    "sambanova", "sambanovajobs",
    "groq", "groqjobs",

    # AI inference / cloud
    "togetherai", "together",
    "fireworksai", "fireworks",

    # Browser automation / scraping
    "browserbase",
    "apify", "apifyjobs",
    "scrapfly",

    # Dev tools / IDEs
    "replit", "replitjobs",
    "gitpod", "gitpodjobs",

    # Design tools
    "framer", "framerjobs",

    # Project management
    "shortcut", "shortcutinc",
    "height", "heightapp",

    # ATS companies themselves (meta!)
    "beamery",
    "lever", "leverjobs",
    "ashby", "ashbyjobs",
    "greenhouse", "greenhouserh",

    # More SaaS
    "asana", "asanajobs",
    "notion", "notionjobs",
    "airtable", "airtablejobs",
    "loom", "loomvideo",
    "miro", "mirojobs",
    "coda", "codajobs",
    "figma", "figmajobs",
    "webflow", "webflowjobs",
    "framer",
    "linear", "linearapp",

    # Security
    "wiz", "wizinc",
    "orca", "orcasecurity",
    "lacework",
    "snyk",
    "datadoghq", "datadog",
    "crowdstrike",
    "sentinelone",

    # Fintech / crypto
    "coinbase", "coinbasejobs",
    "chainalysis",
    "plaid", "plaidinc",
    "marqeta",
    "chime", "chimejobs",
    "stytch",
    "unit21",

    # Health tech
    "openloop",
    "commure", "commureinc",
    "nomi-health", "nomihealth",
    "medallion", "medallioninc",

    # Infrastructure
    "coreweave", "coreweavejobs",
    "lambdalabs", "lambda",
    "vast", "vastdata",
    "crusoe", "crusoejobs",

    # More startups
    "descript",
    "watershed", "watershedjobs",
    "arcadia", "arcadiajobs",
    "axiom", "axiomdatajobs",
    "planetscale",
    "grafana", "grafanajobs",
    "sentry", "sentryjobs",
    "posthog", "posthogjobs",
    "cal",  # cal.com
    "turso",
    "novu",
    "trigger",
    "inngest",
    "temporal", "temporalio",
    "restack",
    "modal",
    "prefect", "prefectio",
    "dagster", "dagsterjobs",
    "airbyte", "airbytejobs",
    "hightouch", "hightouchjobs",
    "census", "censusjobs",
    "rudderstack",
    "mixpanel", "mixpaneljobs",
    "heap", "heapjobs",
    "fullstory", "fullstoryjobs",
    "logrocket",
    "smartlook",
    "glassbox",
    "contentsquare",
    "hotjar",

    # Enterprise / B2B
    "rippling",
    "deel", "deeljobs",
    "remote", "remotejobs",
    "papaya-global", "papayaglobal",
    "globalhr", "globalhrjobs",
]

# ---------------------------------------------------------------------------
# DB helpers (copied from probe_greenhouse_boards.py)
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    return conn


def job_exists(conn, source, source_id):
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE source = ? AND source_id = ?",
        (source, source_id),
    ).fetchone()
    return row is not None


def url_exists(conn, url):
    row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
    return row is not None


def insert_job(conn, job_dict):
    source = job_dict.get("source", "greenhouse")
    source_id = str(job_dict.get("source_id", ""))

    if job_exists(conn, source, source_id):
        return False
    if url_exists(conn, job_dict["url"]):
        return False

    job_id = hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO jobs
           (id, source, source_id, title, company, url, location, salary,
            job_type, category, description, tags, date_posted, date_found,
            fit_score, fit_reason, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            source,
            source_id,
            job_dict.get("title", "Unknown"),
            job_dict.get("company", "Unknown"),
            job_dict["url"],
            job_dict.get("location", ""),
            job_dict.get("salary"),
            job_dict.get("job_type"),
            job_dict.get("category", "engineering"),
            job_dict.get("description", ""),
            json.dumps(job_dict.get("tags", [])),
            job_dict.get("date_posted"),
            now,
            job_dict.get("fit_score", 0.0),
            job_dict.get("fit_reason", ""),
            "new",
        ),
    )
    conn.commit()
    return True

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_job(title, location):
    score = 0
    t = (title or "").lower()
    if re.search(r'\bai\b|\bartificial intelligence\b|\bmachine learning\b|\b(?:llm|nlp|ml)\b', t):
        score += 40
    if re.search(r'\bpython\b', t):
        score += 20
    if re.search(r'\bbackend\b|\bback-end\b', t):
        score += 15
    if re.search(r'\bsoftware engineer\b', t):
        score += 15
    if re.search(r'\bdevops\b|\bsre\b|\bplatform\b|\binfrastructure\b', t):
        score += 15
    if re.search(r'\bfull.?stack\b', t):
        score += 10
    if re.search(r'\bsenior\b|\bstaff\b|\blead\b', t):
        score += 10
    if re.search(r'\bsecurity\b|\bcloud\b|\bdata\b', t):
        score += 10
    if re.search(r'\bfirmware\b|\bembedded\b|\bhardware\b|\bpcb\b|\btest\b', t):
        score += 15  # Matt has this experience
    loc = (location or "").lower()
    if re.search(r'\bremote\b', loc):
        score += 10
    return min(score, 100)

# ---------------------------------------------------------------------------
# Greenhouse API probe
# ---------------------------------------------------------------------------

def probe_slug(slug):
    url = GH_API.format(slug=slug)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; JobHunter/2.0)"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status != 200:
                return slug, None, []
            raw = resp.read()
            data = json.loads(raw)
            jobs = data.get("jobs", [])
            return slug, len(jobs), jobs
    except HTTPError as e:
        if e.code == 404:
            return slug, None, []
        log.debug("HTTP %s for slug %s", e.code, slug)
        return slug, None, []
    except (URLError, Exception) as e:
        log.debug("Error probing %s: %s", slug, e)
        return slug, None, []


def build_job_dict(j, slug):
    title = j.get("title", "")
    location_raw = j.get("location", {})
    if isinstance(location_raw, dict):
        location_name = location_raw.get("name", "")
    else:
        location_name = str(location_raw or "")
    job_url = j.get("absolute_url", "")
    if not job_url:
        job_url = f"https://boards.greenhouse.io/{slug}/jobs/{j.get('id', '')}"
    source_id = str(j.get("internal_job_id") or j.get("id", ""))

    # Try to get company name from metadata
    company = j.get("company", {})
    if isinstance(company, dict):
        company_name = company.get("name", slug)
    else:
        company_name = str(company) if company else slug

    return {
        "source": f"greenhouse_{slug}",
        "source_id": source_id,
        "title": title,
        "company": company_name,
        "url": job_url,
        "location": location_name,
        "date_posted": j.get("updated_at", ""),
        "tags": ["greenhouse", slug, "probe_more"],
        "fit_score": score_job(title, location_name),
        "fit_reason": f"Probed from Greenhouse board: {slug}",
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Deduplicate slugs preserving order
    seen = set()
    unique_slugs = []
    for s in SLUG_VARIANTS:
        sl = s.lower()
        if sl not in seen:
            seen.add(sl)
            unique_slugs.append(sl)

    log.info("=" * 70)
    log.info("PROBE MORE GREENHOUSE BOARDS — %d unique slugs to try", len(unique_slugs))
    log.info("DB: %s", DB_PATH)
    log.info("=" * 70)

    conn = get_db()

    found_boards = {}
    total_inserted = 0
    total_skipped = 0
    tried = 0

    for slug in unique_slugs:
        tried += 1
        log.info("[%d/%d] Probing: %s", tried, len(unique_slugs), slug)

        _, job_count, jobs_raw = probe_slug(slug)

        if job_count is None or job_count == 0:
            log.info("  -> 404 or 0 jobs")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue

        log.info("  -> FOUND %d jobs on board '%s'", job_count, slug)
        found_boards[slug] = job_count

        inserted_this = 0
        dup_this = 0
        for j in jobs_raw:
            jd = build_job_dict(j, slug)
            if insert_job(conn, jd):
                inserted_this += 1
                total_inserted += 1
            else:
                dup_this += 1
                total_skipped += 1

        log.info("  -> Inserted: %d  |  Duplicates: %d", inserted_this, dup_this)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    conn.close()

    # Summary
    log.info("")
    log.info("=" * 70)
    log.info("PROBE COMPLETE")
    log.info("  Slugs tried:    %d", tried)
    log.info("  Boards found:   %d", len(found_boards))
    log.info("  Jobs inserted:  %d", total_inserted)
    log.info("  Duplicates:     %d", total_skipped)
    log.info("=" * 70)

    print("\n\n=== GREENHOUSE PROBE RESULTS ===")
    print(f"Slugs tried:   {tried}")
    print(f"Boards found:  {len(found_boards)}")
    print(f"Jobs inserted: {total_inserted}")
    print(f"Duplicates:    {total_skipped}")
    print("")
    if found_boards:
        print(f"{'SLUG':<35} {'TOTAL JOBS':>12}")
        print("-" * 49)
        for slug, count in sorted(found_boards.items(), key=lambda x: -x[1]):
            print(f"{slug:<35} {count:>12}")


if __name__ == "__main__":
    main()
