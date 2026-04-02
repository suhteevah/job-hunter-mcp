#!/usr/bin/env python3
"""Discover job boards for defense contractors, government IT, and large enterprises."""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
import urllib.request
import urllib.error

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

# ============================================================================
# COMPANIES TO PROBE — slug variations for each
# ============================================================================

DEFENSE_AEROSPACE = {
    "Raytheon": ["raytheon", "rtx", "raytheonmissiles", "raytheontechnologies"],
    "Lockheed Martin": ["lockheedmartin", "lockheed", "lmt"],
    "L3Harris": ["l3harris", "l3", "harris"],
    "Northrop Grumman": ["northropgrumman", "northrop", "ngc"],
    "General Dynamics": ["generaldynamics", "gd", "gdit"],
    "BAE Systems": ["baesystems", "bae"],
    "Leidos": ["leidos"],
    "SAIC": ["saic"],
    "Booz Allen Hamilton": ["boozallen", "boozallenhamilton", "bah"],
    "Palantir": ["palantir"],
    "Anduril": ["anduril", "andurilindustries"],
    "Shield AI": ["shieldai"],
    "SpaceX": ["spacex"],
    "Blue Origin": ["blueorigin"],
    "Honeywell": ["honeywell", "honeywellaerospace"],
    "Boeing": ["boeing"],
    "Collins Aerospace": ["collinsaerospace", "collins"],
    "Pratt Whitney": ["prattwhitney", "pratt-whitney"],
    "Textron": ["textron"],
}

GOV_IT_CLEARED = {
    "ManTech": ["mantech"],
    "Peraton": ["peraton"],
    "CACI": ["caci"],
    "ICF": ["icf"],
    "Maximus": ["maximus"],
    "CGI": ["cgi", "cgigroup"],
    "Accenture Federal": ["accenturefederal", "accenture"],
    "Deloitte": ["deloitte"],
    "MITRE": ["mitre"],
    "Johns Hopkins APL": ["jhuapl", "jhu-apl"],
}

LARGE_TECH_GOV = {
    "Microsoft": ["microsoft"],
    "Amazon": ["amazon", "aws"],
    "Google": ["google"],
    "Oracle": ["oracle"],
    "IBM": ["ibm"],
    "Cisco": ["cisco"],
    "Dell": ["dell", "delltechnologies"],
    "HP Enterprise": ["hpe", "hewlettpackardenterprise"],
    "Palo Alto Networks": ["paloaltonetworks"],
    "CrowdStrike": ["crowdstrike"],
    "Fortinet": ["fortinet"],
    "Splunk": ["splunk"],
    "Elastic": ["elastic"],
    "HashiCorp": ["hashicorp"],
    "Cloudflare": ["cloudflare"],
    "Akamai": ["akamai"],
}

# Merge all
ALL_COMPANIES = {}
ALL_COMPANIES.update(DEFENSE_AEROSPACE)
ALL_COMPANIES.update(GOV_IT_CLEARED)
ALL_COMPANIES.update(LARGE_TECH_GOV)

# ============================================================================
# SCORING
# ============================================================================

HIGH_KEYWORDS = [
    "ai", "ml", "machine learning", "software", "engineer", "python",
    "infrastructure", "devops", "automation", "cloud", "systems",
    "data", "backend", "full stack", "fullstack", "platform",
    "sre", "reliability", "security", "cyber", "network",
    "developer", "programmer", "architect", "deep learning",
    "nlp", "computer vision", "kubernetes", "docker", "terraform",
    "aws", "azure", "gcp", "linux", "api",
]

PENALTY_KEYWORDS = [
    "manager", "director", "sales", "intern", "internship",
    "recruiter", "coordinator", "administrative", "assistant",
    "vp", "vice president", "chief", "officer",
]

BONUS_KEYWORDS = ["remote", "work from home", "distributed", "anywhere"]


def score_job(title: str, location: str = "") -> tuple[float, str]:
    t = title.lower()
    loc = (location or "").lower()
    combined = f"{t} {loc}"

    score = 0.3  # baseline
    reasons = []

    for kw in HIGH_KEYWORDS:
        if kw in t:
            score += 0.08
            reasons.append(f"+{kw}")

    for kw in PENALTY_KEYWORDS:
        if kw in t:
            score -= 0.15
            reasons.append(f"-{kw}")

    for kw in BONUS_KEYWORDS:
        if kw in combined:
            score += 0.1
            reasons.append(f"+remote")
            break

    score = max(0.0, min(1.0, score))
    return round(score, 3), "; ".join(reasons[:8]) if reasons else "baseline"


# ============================================================================
# API PROBES
# ============================================================================

def probe_greenhouse(slug: str) -> list[dict] | None:
    """Try Greenhouse boards API. Returns list of jobs or None."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            jobs = data.get("jobs", [])
            if jobs:
                return jobs
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        pass
    return None


def probe_ashby(slug: str) -> list[dict] | None:
    """Try Ashby GraphQL API. Returns list of job postings or None."""
    url = "https://jobs.ashbyhq.com/api/non-user-graphql"
    query = {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": slug},
        "query": (
            "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {"
            " jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {"
            " jobPostings { id title locationName } } }"
        ),
    }
    body = json.dumps(query).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            board = (data.get("data") or {}).get("jobBoard")
            if board:
                postings = board.get("jobPostings", [])
                if postings:
                    return postings
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        pass
    return None


def probe_lever(slug: str) -> list[dict] | None:
    """Try Lever postings API. Returns list of postings or None."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            if isinstance(data, list) and data:
                return data
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        pass
    return None


# ============================================================================
# DB INSERT
# ============================================================================

def make_id(source: str, source_id: str) -> str:
    return hashlib.md5(f"{source}:{source_id}".encode()).hexdigest()


def insert_jobs(jobs_to_insert: list[dict]) -> int:
    """Insert jobs into DB. Returns count of newly inserted."""
    if not jobs_to_insert:
        return 0
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inserted = 0
    for j in jobs_to_insert:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO jobs
                   (id, source, source_id, title, company, url, location,
                    salary, job_type, category, description, tags,
                    date_posted, date_found, fit_score, fit_reason,
                    status, notes, cover_letter, applied_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    j["id"], j["source"], j["source_id"], j["title"],
                    j["company"], j["url"], j["location"],
                    "", "", j.get("category", ""), "", "",
                    j.get("date_posted", ""), now,
                    j["fit_score"], j["fit_reason"],
                    "new", "", "", "",
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"  DB error: {e}")
    conn.commit()
    conn.close()
    return inserted


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 72)
    print("  DEFENSE / GOV / ENTERPRISE JOB BOARD DISCOVERY")
    print("=" * 72)
    print()

    discovered = []  # (company_name, platform, slug, job_count)
    all_jobs = []

    total_slugs = sum(len(slugs) for slugs in ALL_COMPANIES.values()) * 3  # 3 platforms
    checked = 0

    for company_name, slugs in ALL_COMPANIES.items():
        found_for_company = {}

        for slug in slugs:
            # --- Greenhouse ---
            checked += 1
            gh_jobs = probe_greenhouse(slug)
            if gh_jobs and "greenhouse" not in found_for_company:
                count = len(gh_jobs)
                print(f"  [GH]  {company_name} => '{slug}' => {count} jobs")
                found_for_company["greenhouse"] = (slug, count, gh_jobs)
                discovered.append((company_name, "Greenhouse", slug, count))
                # Parse jobs
                for j in gh_jobs:
                    jid = str(j.get("id", ""))
                    title = j.get("title", "")
                    loc_obj = j.get("location", {})
                    location = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj)
                    url = j.get("absolute_url", f"https://boards.greenhouse.io/{slug}/jobs/{jid}")
                    sc, reason = score_job(title, location)
                    all_jobs.append({
                        "id": make_id("greenhouse", jid),
                        "source": "greenhouse",
                        "source_id": jid,
                        "title": title,
                        "company": company_name,
                        "url": url,
                        "location": location,
                        "fit_score": sc,
                        "fit_reason": reason,
                        "category": "defense-enterprise",
                        "date_posted": "",
                    })
            time.sleep(0.15)

            # --- Ashby ---
            checked += 1
            ab_jobs = probe_ashby(slug)
            if ab_jobs and "ashby" not in found_for_company:
                count = len(ab_jobs)
                print(f"  [AB]  {company_name} => '{slug}' => {count} jobs")
                found_for_company["ashby"] = (slug, count, ab_jobs)
                discovered.append((company_name, "Ashby", slug, count))
                for j in ab_jobs:
                    jid = str(j.get("id", ""))
                    title = j.get("title", "")
                    location = j.get("locationName", "")
                    url = f"https://jobs.ashbyhq.com/{slug}/{jid}"
                    sc, reason = score_job(title, location)
                    all_jobs.append({
                        "id": make_id("ashby", jid),
                        "source": "ashby",
                        "source_id": jid,
                        "title": title,
                        "company": company_name,
                        "url": url,
                        "location": location,
                        "fit_score": sc,
                        "fit_reason": reason,
                        "category": "defense-enterprise",
                        "date_posted": "",
                    })
            time.sleep(0.15)

            # --- Lever ---
            checked += 1
            lv_jobs = probe_lever(slug)
            if lv_jobs and "lever" not in found_for_company:
                count = len(lv_jobs)
                print(f"  [LV]  {company_name} => '{slug}' => {count} jobs")
                found_for_company["lever"] = (slug, count, lv_jobs)
                discovered.append((company_name, "Lever", slug, count))
                for j in lv_jobs:
                    jid = str(j.get("id", ""))
                    title = j.get("text", "")
                    cats = j.get("categories", {})
                    location = cats.get("location", "") if isinstance(cats, dict) else ""
                    url = j.get("hostedUrl", f"https://jobs.lever.co/{slug}/{jid}")
                    sc, reason = score_job(title, location)
                    all_jobs.append({
                        "id": make_id("lever", jid),
                        "source": "lever",
                        "source_id": jid,
                        "title": title,
                        "company": company_name,
                        "url": url,
                        "location": location,
                        "fit_score": sc,
                        "fit_reason": reason,
                        "category": "defense-enterprise",
                        "date_posted": "",
                    })
            time.sleep(0.15)

        if not found_for_company:
            print(f"  [--]  {company_name} => no boards found")

    # ============================================================================
    # INSERT INTO DB
    # ============================================================================
    print()
    print("=" * 72)
    print(f"  INSERTING {len(all_jobs)} JOBS INTO DATABASE")
    print("=" * 72)

    new_count = insert_jobs(all_jobs)
    print(f"  New jobs inserted: {new_count}")
    print(f"  Already existed:   {len(all_jobs) - new_count}")

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print()
    print("=" * 72)
    print("  DISCOVERY SUMMARY")
    print("=" * 72)
    print(f"  {'Company':<30} {'Platform':<12} {'Slug':<30} {'Jobs':>6}")
    print(f"  {'-'*30} {'-'*12} {'-'*30} {'-'*6}")

    total_jobs = 0
    for company_name, platform, slug, count in sorted(discovered, key=lambda x: (-x[3], x[0])):
        print(f"  {company_name:<30} {platform:<12} {slug:<30} {count:>6}")
        total_jobs += count

    print(f"  {'-'*30} {'-'*12} {'-'*30} {'-'*6}")
    print(f"  {'TOTAL':<30} {'':<12} {'':<30} {total_jobs:>6}")
    print()
    print(f"  Boards discovered: {len(discovered)}")
    print(f"  Companies with boards: {len(set(d[0] for d in discovered))}")
    print(f"  Total jobs found: {total_jobs}")
    print(f"  New jobs inserted to DB: {new_count}")

    # Show top-scored jobs
    top = sorted(all_jobs, key=lambda x: -x["fit_score"])[:25]
    if top:
        print()
        print("=" * 72)
        print("  TOP 25 HIGHEST-SCORED JOBS")
        print("=" * 72)
        for j in top:
            print(f"  [{j['fit_score']:.2f}] {j['company']} — {j['title']}")
            print(f"         {j['location']}  |  {j['source']}")
            print()


if __name__ == "__main__":
    main()
