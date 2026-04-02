#!/usr/bin/env python
"""
probe_greenhouse_boards.py
Probe the public Greenhouse API for company job boards we haven't scraped yet.
Tries multiple slug variants per company. Inserts ALL jobs found (not just keyword-filtered).

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe probe_greenhouse_boards.py
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
DELAY_BETWEEN_REQUESTS = 0.3  # seconds — be polite

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("probe_greenhouse")

# ---------------------------------------------------------------------------
# Slugs to probe — multiple variants per company
# ---------------------------------------------------------------------------
SLUG_VARIANTS = [
    # HubSpot
    "hubspot", "hubspotproductandeng", "hubspotjobs",
    # Zapier
    "zapier", "zapierjobs",
    # Monday.com
    "mondaycom", "monday",
    # ClickUp
    "clickup", "clickupjobs",
    # Canva
    "canva", "canvajobs",
    # Miro
    "miro", "mirojobs",
    # Snyk
    "snyk", "snykjobs",
    # Wiz
    "wiz", "wizinc", "wizsecurity",
    # CrowdStrike
    "crowdstrike", "crowdstrikejobs",
    # SentinelOne
    "sentinelone", "sentineloneinc",
    # Palo Alto Networks
    "paloaltonetworks", "panw",
    # Zscaler
    "zscaler", "zscalerjobs",
    # Fortinet
    "fortinet", "fortinetjobs",
    # Rapid7
    "rapid7", "rapid7inc",
    # NerdWallet
    "nerdwallet", "nerdwalletjobs",
    # Peloton
    "peloton", "pelotoninteractive", "onepeloton",
    # Niantic
    "niantic", "nianticinc", "nianticlabs",
    # HashiCorp
    "hashicorp", "hashicorpjobs",
    # Confluent
    "confluent", "confluentinc",
    # Dropbox
    "dropbox", "dropboxjobs",
    # Box
    "box", "boxjobs", "boxinc",
    # Zendesk
    "zendesk", "zendeskjobs",
    # Freshworks
    "freshworks", "freshworksinc",
    # ServiceNow
    "servicenow", "servicenowjobs",
    # Splunk
    "splunk", "splunkjobs",
    # New Relic
    "newrelic", "newrelicjobs",
    # Sumo Logic
    "sumologic", "sumologicjobs",
    # Twilio
    "twilio", "twiliojobs",
    # GitLab
    "gitlab", "gitlabjobs",
    # GitHub
    "github", "githubjobs", "githubinc",
    # Uber
    "uber", "uberjobs", "ubercom",
    # Lyft
    "lyft", "lyftjobs",
    # Square / Block
    "square", "squarejobs", "squareinc", "block",
    # Stripe
    "stripe", "stripejobs",
    # Pinterest
    "pinterest", "pinterestjobs",
    # Snap
    "snap", "snapjobs", "snapinc", "snapchat",
    # Twitter / X
    "twitter", "twitterjobs", "x",
    # Meta
    "meta", "metajobs", "metacareers", "fabormetacareers",
    # Apple
    "apple", "applejobs",
    # Tesla
    "tesla", "teslajobs", "teslamotors",
    # NVIDIA
    "nvidia", "nvidiajobs",
    # AMD
    "amd", "amdjobs",
    # Intel
    "intel", "inteljobs",
    # Qualcomm
    "qualcomm", "qualcommjobs",
    # Broadcom
    "broadcom", "broadcomjobs",
    # VMware
    "vmware", "vmwarejobs",
    # Salesforce
    "salesforce", "salesforcejobs",
    # Oracle
    "oracle", "oraclejobs",
    # IBM
    "ibm", "ibmjobs",
    # Cisco
    "cisco", "ciscojobs",
    # Dell
    "dell", "delljobs",
    # HP / HPE
    "hp", "hpjobs", "hpe",
    # Databricks (already have but try alt slugs)
    "databricks",
    # Snowflake (already have - ashby)
    "snowflake", "snowflakejobs",
]

# ---------------------------------------------------------------------------
# DB helpers
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
    """Insert a job into the database. Returns True if inserted, False if duplicate."""
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

KEYWORD_PATTERNS = [
    re.compile(r'\bai\b', re.I),
    re.compile(r'\bartificial intelligence\b', re.I),
    re.compile(r'\bmachine learning\b', re.I),
    re.compile(r'\b(?:llm|nlp|ml)\b', re.I),
    re.compile(r'\bsoftware engineer', re.I),
    re.compile(r'\bsoftware developer', re.I),
    re.compile(r'\bbackend\b', re.I),
    re.compile(r'\bback-end\b', re.I),
    re.compile(r'\bfull.?stack\b', re.I),
    re.compile(r'\bdevops\b', re.I),
    re.compile(r'\bplatform engineer', re.I),
    re.compile(r'\binfrastructure engineer', re.I),
    re.compile(r'\bsre\b', re.I),
    re.compile(r'\bpython\b', re.I),
    re.compile(r'\bdata engineer', re.I),
    re.compile(r'\bcloud engineer', re.I),
    re.compile(r'\bsecurity engineer', re.I),
    re.compile(r'\bapplication engineer', re.I),
    re.compile(r'\bapi\b', re.I),
]

LOCATION_PATTERNS = [
    re.compile(r'\bremote\b', re.I),
    re.compile(r'\bunited states\b', re.I),
    re.compile(r'\b(?:us|usa)\b', re.I),
    re.compile(r'\bchico\b', re.I),
    re.compile(r'\bcalifornia\b', re.I),
    re.compile(r'\banywhere\b', re.I),
    re.compile(r'\bnorth america\b', re.I),
]


def score_job(title, location):
    score = 0
    t = (title or "").lower()
    if re.search(r'\bai\b|\bartificial intelligence\b|\bmachine learning\b|\b(?:llm|nlp)\b', t):
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
    loc = (location or "").lower()
    if re.search(r'\bremote\b', loc):
        score += 10
    return min(score, 100)

# ---------------------------------------------------------------------------
# Greenhouse API probe
# ---------------------------------------------------------------------------

def probe_slug(slug):
    """
    Hit the Greenhouse boards API for a slug.
    Returns (slug, job_count, jobs_list) or (slug, None, []) on 404/error.
    """
    url = GH_API.format(slug=slug)
    req = Request(url, headers={"User-Agent": "JobHunter/2.0 (probe)"})
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
    location_name = j.get("location", {}).get("name", "") if isinstance(j.get("location"), dict) else str(j.get("location", ""))
    job_url = j.get("absolute_url", "")
    if not job_url:
        job_url = f"https://boards.greenhouse.io/{slug}/jobs/{j.get('id', '')}"
    source_id = str(j.get("internal_job_id") or j.get("id", ""))
    return {
        "source": "greenhouse",
        "source_id": source_id,
        "title": title,
        "company": slug,
        "url": job_url,
        "location": location_name,
        "date_posted": j.get("updated_at", ""),
        "tags": ["greenhouse", slug, "probe"],
        "fit_score": score_job(title, location_name),
        "fit_reason": f"Probed from Greenhouse board: {slug}",
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 70)
    log.info("PROBE GREENHOUSE BOARDS — %d slug variants to try", len(SLUG_VARIANTS))
    log.info("DB: %s", DB_PATH)
    log.info("=" * 70)

    conn = get_db()

    # Track which slugs returned boards and how many jobs
    found_boards = {}   # slug -> job_count
    total_inserted = 0
    total_skipped = 0
    tried = 0

    for slug in SLUG_VARIANTS:
        tried += 1
        slug_lower = slug.lower()
        log.info("[%d/%d] Probing: %s", tried, len(SLUG_VARIANTS), slug)

        _, job_count, jobs_raw = probe_slug(slug_lower)

        if job_count is None or job_count == 0:
            log.info("  -> 404 or 0 jobs, skipping")
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

    if found_boards:
        log.info("")
        log.info("BOARDS WITH JOBS (sorted by count):")
        for slug, count in sorted(found_boards.items(), key=lambda x: -x[1]):
            log.info("  %-30s  %d jobs", slug, count)

    # Print final summary table for easy reading
    print("\n\n=== GREENHOUSE PROBE RESULTS ===")
    print(f"Slugs tried:   {tried}")
    print(f"Boards found:  {len(found_boards)}")
    print(f"Jobs inserted: {total_inserted}")
    print(f"Duplicates:    {total_skipped}")
    print("")
    if found_boards:
        print(f"{'SLUG':<30} {'TOTAL JOBS':>12}")
        print("-" * 44)
        for slug, count in sorted(found_boards.items(), key=lambda x: -x[1]):
            print(f"{slug:<30} {count:>12}")
    else:
        print("No new boards discovered.")


if __name__ == "__main__":
    main()
