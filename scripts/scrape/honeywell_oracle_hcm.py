"""
honeywell_oracle_hcm.py
========================
Scrape Honeywell jobs via their Oracle Fusion HCM REST API.
Total available: ~1,703 jobs (507 in US).
Filters to engineering/tech roles and inserts into SQLite DB.

API: https://ibqbjb.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/
     recruitingCEJobRequisitions?finder=findReqs;siteNumber=CX_1&expand=requisitionList

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe honeywell_oracle_hcm.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import re
import sqlite3
import time
import logging
import urllib.parse
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
ORACLE_BASE = "https://ibqbjb.fa.ocs.oraclecloud.com"
SITE_NUMBER = "CX_1"
CAREERS_BASE = "https://careers.honeywell.com/en/sites/Honeywell/job"

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("honeywell_oracle")

# Matt's skills match keywords — firmware, PCB, test fixture, microsoldering
TITLE_KEYWORDS = {
    "software engineer": 30, "software developer": 25, "senior software": 30,
    "firmware": 40, "embedded": 35, "pcb": 30, "test engineer": 25,
    "hardware engineer": 25, "test fixture": 30, "microsoldering": 35,
    "ai ": 25, "machine learning": 30, "llm": 30, "ml engineer": 30,
    "python": 20, "backend": 15, "full stack": 15, "fullstack": 15,
    "automation": 20, "devops": 15, "cloud": 15, "platform": 15,
    "systems engineer": 20, "integration": 15, "avionics": 25,
    "aerospace": 20, "defense": 20, "iot": 20, "robotics": 20,
    "data engineer": 15, "data scientist": 15, "analyst": 5,
}
NEGATIVE_KEYWORDS = [
    "manager", "director", "vp ", "sales", "marketing", "recruiter",
    "hr ", "human resources", "finance", "accounting", "supply chain",
    "buyer", "procurement", "legal", "paralegal", "field service support",
    "ausbildung",  # German apprenticeship
    "praktikum", "internship",
]

# Category IDs from Oracle HCM (from the API response)
# Engineering category: 300000017425610
ENGINEERING_CATEGORY_ID = 300000017425610
US_LOCATION_ID = 300000000469866


def score_job(title, location="", workplace_type="", job_family=""):
    t = (title or "").lower()
    score = 15  # base score for being at Honeywell
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in t:
            score += pts
    for kw in NEGATIVE_KEYWORDS:
        if kw in t:
            score -= 25
    loc = (location or "").lower()
    wp = (workplace_type or "").lower()
    if re.search(r"\bremote\b", loc) or re.search(r"\bremote\b", wp) or "remote" in (workplace_type or "").lower():
        score += 15
    # Bonus for US locations
    if re.search(r"\bunited states\b|\busa\b|\b\, [a-z]{2}\b", loc, re.I):
        score += 5
    return min(score, 100)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def url_exists(conn, url):
    return conn.execute("SELECT 1 FROM jobs WHERE url=?", (url,)).fetchone() is not None


def source_id_exists(conn, sid):
    return conn.execute(
        "SELECT 1 FROM jobs WHERE source='honeywell' AND source_id=?", (sid,)
    ).fetchone() is not None


def insert_job(conn, jd):
    if url_exists(conn, jd["url"]):
        return False
    if source_id_exists(conn, jd["source_id"]):
        return False
    job_id = hashlib.sha256(("honeywell:" + jd["source_id"]).encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO jobs (id, source, source_id, title, company, url, location,
           salary, job_type, category, description, tags, date_posted, date_found,
           fit_score, fit_reason, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job_id, "honeywell", jd["source_id"], jd["title"], "Honeywell",
            jd["url"], jd["location"], None,
            jd.get("job_type"), "engineering",
            jd.get("description", ""),
            json.dumps(["honeywell", "oracle_hcm", "aerospace", "defense",
                        jd.get("workplace_type", "")]),
            jd.get("date_posted"), now,
            jd.get("fit_score", 0), jd.get("fit_reason", "Honeywell Oracle HCM"), "new"
        )
    )
    conn.commit()
    return True


def fetch_jobs_page(keyword="", offset=0, limit=25, location_id=None, category_id=None, workplace_type=None):
    """
    Fetch a page of Honeywell jobs from Oracle HCM API.
    Returns (list_of_job_dicts, total_count).
    """
    # Build finder string
    finder_parts = [f"siteNumber={SITE_NUMBER}"]
    if keyword:
        finder_parts.append(f"keyword={urllib.parse.quote(keyword)}")
    if location_id:
        finder_parts.append(f"selectedLocationsFacet={location_id}")
    if category_id:
        finder_parts.append(f"selectedCategoriesFacet={category_id}")
    if workplace_type:
        finder_parts.append(f"selectedWorkplaceTypesFacet={workplace_type}")

    finder = urllib.parse.quote("findReqs;" + ",".join(finder_parts))
    url = (
        f"{ORACLE_BASE}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        f"?finder={finder}&limit={limit}&offset={offset}"
        f"&totalResults=true&expand=requisitionList"
    )

    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "REST-Framework-Version": "2",
    })

    try:
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except (HTTPError, URLError, Exception) as e:
        log.warning("API error: %s", e)
        return [], 0

    items = data.get("items", [])
    if not items:
        return [], 0

    first = items[0]
    total = first.get("TotalJobsCount", 0)
    job_list = first.get("requisitionList", [])

    jobs = []
    for j in job_list:
        job_id = str(j.get("Id", ""))
        title = j.get("Title", "")
        location = j.get("PrimaryLocation", "")
        country = j.get("PrimaryLocationCountry", "")
        workplace = j.get("WorkplaceType", "") or j.get("WorkplaceTypeCode", "")
        job_family = j.get("JobFamily", "")
        job_type = j.get("JobType", "")
        posted = j.get("PostedDate", "")
        short_desc = j.get("ShortDescriptionStr", "")
        qualifications = j.get("ExternalQualificationsStr", "")
        responsibilities = j.get("ExternalResponsibilitiesStr", "")

        # Build URL — Oracle HCM job page
        job_url = f"https://careers.honeywell.com/en/sites/Honeywell/job/{job_id}"

        description = ""
        if short_desc:
            description += short_desc + "\n"
        if qualifications:
            description += "Qualifications: " + qualifications[:300] + "\n"
        if responsibilities:
            description += "Responsibilities: " + responsibilities[:300]

        fit_score = score_job(title, location + " " + country, workplace, job_family)
        fit_reason = f"Honeywell Oracle HCM | {job_family or 'Engineering'} | {workplace}"

        jobs.append({
            "source_id": job_id,
            "title": title,
            "location": f"{location}, {country}".strip(", "),
            "url": job_url,
            "date_posted": posted,
            "description": description[:800],
            "job_type": job_type,
            "workplace_type": workplace,
            "fit_score": fit_score,
            "fit_reason": fit_reason,
        })

    return jobs, total


def main():
    log.info("=" * 70)
    log.info("HONEYWELL ORACLE HCM SCRAPER")
    log.info("=" * 70)

    conn = get_db()
    total_inserted = 0
    total_skipped = 0
    total_fetched = 0

    # Strategy: search by keyword for engineering/tech terms
    # Also do a bulk US Engineering category pull
    search_configs = [
        # (keyword, location_id, category_id, workplace_type_filter, label)
        ("software engineer", US_LOCATION_ID, None, None, "SW Engineer US"),
        ("firmware", US_LOCATION_ID, None, None, "Firmware US"),
        ("embedded", US_LOCATION_ID, None, None, "Embedded US"),
        ("test engineer", US_LOCATION_ID, None, None, "Test Engineer US"),
        ("python", US_LOCATION_ID, None, None, "Python US"),
        ("AI", US_LOCATION_ID, None, None, "AI US"),
        ("machine learning", US_LOCATION_ID, None, None, "ML US"),
        ("hardware engineer", US_LOCATION_ID, None, None, "HW Engineer US"),
        ("automation", US_LOCATION_ID, None, None, "Automation US"),
        ("cloud", US_LOCATION_ID, None, None, "Cloud US"),
        ("devops", US_LOCATION_ID, None, None, "DevOps US"),
        ("systems engineer", US_LOCATION_ID, None, None, "Systems US"),
        # Remote worldwide
        ("software engineer", None, None, "ORA_REMOTE", "SW Engineer Remote"),
        ("firmware", None, None, "ORA_REMOTE", "Firmware Remote"),
        # Engineering category, US bulk
        ("", US_LOCATION_ID, ENGINEERING_CATEGORY_ID, None, "Engineering US (all)"),
    ]

    for kw, loc_id, cat_id, wp_type, label in search_configs:
        log.info("")
        log.info("Searching: %s", label)

        offset = 0
        page_num = 0
        max_pages = 10  # up to 250 jobs per search

        while True:
            jobs, total = fetch_jobs_page(
                keyword=kw,
                offset=offset,
                limit=25,
                location_id=loc_id,
                category_id=cat_id,
                workplace_type=wp_type
            )

            if not jobs:
                log.info("  No more jobs (offset=%d)", offset)
                break

            if page_num == 0:
                log.info("  Total available: %d", total)

            page_num += 1
            total_fetched += len(jobs)
            inserted = 0
            skipped = 0

            for jd in jobs:
                # Filter out obviously non-engineering/non-English roles
                skip = False
                title_lower = jd["title"].lower()
                for neg in NEGATIVE_KEYWORDS:
                    if neg in title_lower:
                        skip = True
                        break

                if skip:
                    skipped += 1
                    total_skipped += 1
                    continue

                if jd["fit_score"] < 20:
                    skipped += 1
                    total_skipped += 1
                    continue

                if insert_job(conn, jd):
                    inserted += 1
                    total_inserted += 1
                    log.info(
                        "  + [%s] %s | %s | score=%d",
                        jd["source_id"], jd["title"][:55],
                        jd["location"][:30], jd["fit_score"]
                    )
                else:
                    skipped += 1
                    total_skipped += 1

            log.info(
                "  Page %d (offset=%d): fetched=%d inserted=%d skipped=%d",
                page_num, offset, len(jobs), inserted, skipped
            )

            offset += 25
            if offset >= total or offset >= 250:  # cap at 250 per search
                break
            if page_num >= max_pages:
                log.info("  Reached max_pages limit")
                break

            time.sleep(0.5)

    conn.close()

    log.info("")
    log.info("=" * 70)
    log.info("HONEYWELL ORACLE HCM SCRAPE COMPLETE")
    log.info("  Total fetched:   %d", total_fetched)
    log.info("  Total inserted:  %d", total_inserted)
    log.info("  Total skipped:   %d", total_skipped)
    log.info("=" * 70)

    print("")
    print("=" * 70)
    print("HONEYWELL ORACLE HCM SCRAPE COMPLETE")
    print(f"Total fetched:   {total_fetched}")
    print(f"Total inserted:  {total_inserted}")
    print(f"Total skipped:   {total_skipped}")
    print("=" * 70)


if __name__ == "__main__":
    main()
