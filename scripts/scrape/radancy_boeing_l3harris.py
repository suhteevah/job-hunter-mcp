"""
radancy_boeing_l3harris.py
===========================
Scrape Boeing and L3Harris jobs via the Radancy/TMP Worldwide job search API.
Both companies use the Radancy platform (jobs-search-analytics.prod.use1.radancy.net).

Boeing: https://jobs.boeing.com
L3Harris: https://careers.l3harris.com

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe radancy_boeing_l3harris.py
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

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("radancy_scraper")

# Company configurations
COMPANIES = [
    {
        "name": "Boeing",
        "source": "boeing",
        "base_url": "https://jobs.boeing.com",
        "search_url": "https://jobs.boeing.com/search-jobs/{query}/37341-30186/4",
        "api_url": "https://jobs.boeing.com/api/jobs",
        "tags": ["boeing", "aerospace", "defense"],
    },
    {
        "name": "L3Harris",
        "source": "l3harris",
        "base_url": "https://careers.l3harris.com",
        "search_url": "https://careers.l3harris.com/en/search/?q={query}&country=unitedstatesofamerica&pagesize=20&radiusunit=KM",
        "api_url": "https://careers.l3harris.com/en/api/jobs",
        "tags": ["l3harris", "defense", "aerospace"],
    },
    {
        "name": "Raytheon",
        "source": "raytheon",
        "base_url": "https://careers.rtx.com",
        "search_url": "https://careers.rtx.com/global/en/search/?q={query}&country=unitedstatesofamerica&pagesize=20",
        "tags": ["raytheon", "rtx", "defense"],
    },
    {
        "name": "Northrop Grumman",
        "source": "northrop_grumman",
        "base_url": "https://www.northropgrumman.com",
        "search_url": "https://www.northropgrumman.com/jobs#N=4294967149+4294967024",
        "tags": ["northrop_grumman", "defense", "aerospace"],
    },
]

SEARCH_TERMS = [
    "software engineer",
    "firmware engineer",
    "embedded software",
    "test engineer",
    "systems engineer",
    "AI engineer",
    "machine learning",
    "python developer",
    "cloud engineer",
    "devops",
    "cybersecurity",
    "automation engineer",
]

TITLE_KEYWORDS = {
    "software engineer": 30, "software developer": 25,
    "firmware": 40, "embedded": 35, "test engineer": 25,
    "ai ": 25, "machine learning": 30, "llm": 30,
    "python": 20, "backend": 15, "automation": 20,
    "systems engineer": 20, "devops": 15, "cloud": 15,
    "cybersecurity": 20, "security engineer": 20,
    "data engineer": 15, "data scientist": 15,
    "platform": 15, "infrastructure": 15,
}
NEGATIVE_KEYWORDS = ["manager", "director", "vp ", "sales", "marketing", "recruiter", "intern"]


def score_job(title, location=""):
    t = (title or "").lower()
    score = 20
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in t:
            score += pts
    for kw in NEGATIVE_KEYWORDS:
        if kw in t:
            score -= 20
    if re.search(r"\bremote\b", (location or "").lower()):
        score += 10
    return min(score, 100)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def url_exists(conn, url):
    return conn.execute("SELECT 1 FROM jobs WHERE url=?", (url,)).fetchone() is not None


def source_id_exists(conn, source, sid):
    return conn.execute(
        "SELECT 1 FROM jobs WHERE source=? AND source_id=?", (source, sid)
    ).fetchone() is not None


def insert_job(conn, jd):
    if url_exists(conn, jd["url"]):
        return False
    if source_id_exists(conn, jd["source"], jd["source_id"]):
        return False
    job_id = hashlib.sha256((jd["source"] + ":" + jd["source_id"]).encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO jobs (id, source, source_id, title, company, url, location,
           salary, job_type, category, description, tags, date_posted, date_found,
           fit_score, fit_reason, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job_id, jd["source"], jd["source_id"], jd["title"], jd["company"],
            jd["url"], jd["location"], None, None, "engineering",
            jd.get("description", ""),
            json.dumps(jd.get("tags", ["defense"])),
            jd.get("date_posted"), now,
            jd.get("fit_score", 0), jd.get("fit_reason", ""), "new"
        )
    )
    conn.commit()
    return True


def try_boeing_api(query, conn):
    """Try Boeing's Radancy-based job search."""
    inserted = 0
    skipped = 0

    # Boeing uses a structured URL: /search-jobs/{encoded-query}/{location-id}/{radius}
    # Also has a JSON API endpoint
    urls_to_try = [
        f"https://jobs.boeing.com/api/jobs?search={urllib.parse.quote(query)}&location=United+States&country=us&pagesize=20",
        f"https://jobs.boeing.com/search-jobs/{urllib.parse.quote(query, safe='')}/37341/4",
    ]

    for url in urls_to_try[:1]:  # Try first format
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/html",
        })
        try:
            with urlopen(req, timeout=15) as r:
                ct = r.headers.get("content-type", "")
                body = r.read()
                if "json" in ct:
                    data = json.loads(body)
                    jobs_raw = data.get("jobs", data.get("results", data.get("items", [])))
                    log.info("  Boeing API [%s]: %d jobs", query, len(jobs_raw))
                    for j in jobs_raw:
                        jid = str(j.get("id") or j.get("jobId") or j.get("reqId", ""))
                        title = j.get("title") or j.get("jobTitle", "")
                        loc = j.get("location") or j.get("city", "")
                        job_url = j.get("url") or j.get("applyUrl") or f"https://jobs.boeing.com/job/{jid}"
                        if not jid or not title:
                            continue
                        jd = {
                            "source": "boeing",
                            "source_id": jid,
                            "title": title,
                            "company": "Boeing",
                            "url": job_url,
                            "location": str(loc),
                            "fit_score": score_job(title, str(loc)),
                            "fit_reason": f"Boeing Radancy API: {query}",
                            "tags": ["boeing", "aerospace", "defense"],
                        }
                        if insert_job(conn, jd):
                            inserted += 1
                            log.info("    + %s | %s | score=%d", jid, title[:50], jd["fit_score"])
                        else:
                            skipped += 1
                else:
                    # HTML — try to extract job listings
                    html = body.decode("utf-8", errors="replace")
                    jobs_found = parse_radancy_html(html, "Boeing", "boeing",
                                                    "https://jobs.boeing.com", query)
                    for jd in jobs_found:
                        if insert_job(conn, jd):
                            inserted += 1
                            log.info("    + %s | %s | score=%d",
                                     jd["source_id"], jd["title"][:50], jd["fit_score"])
                        else:
                            skipped += 1
        except Exception as e:
            log.debug("Boeing API error [%s]: %s", query, e)

    return inserted, skipped


def try_l3harris_api(query, conn):
    """Try L3Harris job search via their SAP-based URL pattern."""
    inserted = 0
    skipped = 0

    url = (
        f"https://careers.l3harris.com/en/search/"
        f"?q={urllib.parse.quote(query)}"
        f"&country=unitedstatesofamerica&pagesize=20&radiusunit=KM"
    )
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html,application/json",
    })
    try:
        with urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
            jobs_found = parse_radancy_html(html, "L3Harris", "l3harris",
                                            "https://careers.l3harris.com", query)
            log.info("  L3Harris [%s]: %d jobs parsed", query, len(jobs_found))
            for jd in jobs_found:
                if insert_job(conn, jd):
                    inserted += 1
                    log.info("    + %s | %s | score=%d",
                             jd["source_id"], jd["title"][:50], jd["fit_score"])
                else:
                    skipped += 1
    except Exception as e:
        log.debug("L3Harris error [%s]: %s", query, e)

    return inserted, skipped


def try_raytheon_api(query, conn):
    """Try Raytheon/RTX job search."""
    inserted = 0
    skipped = 0

    url = (
        f"https://careers.rtx.com/global/en/search/"
        f"?q={urllib.parse.quote(query)}"
        f"&country=unitedstatesofamerica&pagesize=20&radiusunit=KM"
    )
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/json",
    })
    try:
        with urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
            jobs_found = parse_radancy_html(html, "Raytheon/RTX", "raytheon",
                                            "https://careers.rtx.com", query)
            log.info("  Raytheon [%s]: %d jobs parsed", query, len(jobs_found))
            for jd in jobs_found:
                if insert_job(conn, jd):
                    inserted += 1
                else:
                    skipped += 1
    except Exception as e:
        log.debug("Raytheon error [%s]: %s", query, e)

    return inserted, skipped


def try_northrop_api(query, conn):
    """Try Northrop Grumman's job search."""
    inserted = 0
    skipped = 0

    # Northrop uses a custom search
    url = f"https://www.northropgrumman.com/jobs?search_query={urllib.parse.quote(query)}&country=United+States"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/json"})
    try:
        with urlopen(req, timeout=15) as r:
            ct = r.headers.get("content-type", "")
            body = r.read()
            if "json" in ct:
                data = json.loads(body)
                jobs_raw = data.get("jobs", data.get("results", []))
                log.info("  Northrop JSON [%s]: %d jobs", query, len(jobs_raw))
                for j in jobs_raw:
                    jid = str(j.get("id") or j.get("reqId", ""))
                    title = j.get("title") or j.get("jobTitle", "")
                    loc = j.get("location") or j.get("primaryLocation", "")
                    job_url = j.get("url") or f"https://www.northropgrumman.com/jobs/job/{jid}"
                    if not jid or not title:
                        continue
                    jd = {
                        "source": "northrop_grumman",
                        "source_id": jid,
                        "title": title,
                        "company": "Northrop Grumman",
                        "url": job_url,
                        "location": str(loc),
                        "fit_score": score_job(title, str(loc)),
                        "fit_reason": f"Northrop Grumman: {query}",
                        "tags": ["northrop_grumman", "defense", "aerospace"],
                    }
                    if insert_job(conn, jd):
                        inserted += 1
                        log.info("    + %s | %s | score=%d", jid, title[:50], jd["fit_score"])
                    else:
                        skipped += 1
            else:
                html = body.decode("utf-8", errors="replace")
                jobs_found = parse_radancy_html(html, "Northrop Grumman", "northrop_grumman",
                                                "https://www.northropgrumman.com", query)
                log.info("  Northrop HTML [%s]: %d jobs", query, len(jobs_found))
                for jd in jobs_found:
                    if insert_job(conn, jd):
                        inserted += 1
                    else:
                        skipped += 1
    except Exception as e:
        log.debug("Northrop error [%s]: %s", query, e)

    return inserted, skipped


def parse_radancy_html(html, company_name, source, base_url, query):
    """
    Parse Radancy/TMP job listing HTML.
    Common patterns: data-jobid, JSON-LD, structured data.
    """
    jobs = []

    # JSON-LD JobPosting
    json_ld = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )
    for block in json_ld:
        try:
            data = json.loads(block.strip())
            postings = []
            if isinstance(data, list):
                postings = [d for d in data if d.get("@type") == "JobPosting"]
            elif data.get("@type") == "JobPosting":
                postings = [data]
            elif data.get("@type") == "ItemList":
                postings = [item for item in data.get("itemListElement", [])
                            if isinstance(item, dict) and item.get("@type") == "JobPosting"]
            for post in postings:
                jid = str(post.get("identifier", {}).get("value", "")) if isinstance(post.get("identifier"), dict) else str(hash(post.get("title", "")))
                title = post.get("title", "")
                loc_data = post.get("jobLocation", {})
                if isinstance(loc_data, list):
                    loc_data = loc_data[0] if loc_data else {}
                location = ""
                if isinstance(loc_data, dict):
                    addr = loc_data.get("address", {})
                    if isinstance(addr, dict):
                        location = f"{addr.get('addressLocality','')}, {addr.get('addressRegion','')}".strip(", ")
                job_url = post.get("url", post.get("@id", ""))
                if not job_url.startswith("http"):
                    job_url = base_url + job_url
                if title:
                    jobs.append({
                        "source": source,
                        "source_id": jid or hashlib.sha256(job_url.encode()).hexdigest()[:12],
                        "title": title,
                        "company": company_name,
                        "url": job_url,
                        "location": location,
                        "fit_score": score_job(title, location),
                        "fit_reason": f"{company_name}: {query}",
                        "tags": [source, "defense"],
                    })
        except Exception:
            pass

    if jobs:
        return jobs

    # Fallback: look for data-jobid attributes
    job_ids = re.findall(r'data-jobid=["\']([^"\']+)["\']', html)
    titles = re.findall(r'class=["\'][^"\']*job-title[^"\']*["\'][^>]*>([^<]+)<', html)
    locations_raw = re.findall(r'class=["\'][^"\']*job-location[^"\']*["\'][^>]*>([^<]+)<', html)

    for i, jid in enumerate(job_ids):
        title = titles[i].strip() if i < len(titles) else f"{company_name} Position"
        location = locations_raw[i].strip() if i < len(locations_raw) else "United States"
        job_url = f"{base_url}/job/{jid}"
        jobs.append({
            "source": source,
            "source_id": jid,
            "title": title,
            "company": company_name,
            "url": job_url,
            "location": location,
            "fit_score": score_job(title, location),
            "fit_reason": f"{company_name}: {query}",
            "tags": [source, "defense"],
        })

    return jobs


import hashlib  # ensure available


def main():
    log.info("=" * 70)
    log.info("RADANCY / DEFENSE COMPANY SCRAPER")
    log.info("Companies: Boeing, L3Harris, Raytheon, Northrop Grumman")
    log.info("=" * 70)

    conn = get_db()
    grand_total_ins = 0
    grand_total_skp = 0

    for term in SEARCH_TERMS:
        log.info("\nTerm: '%s'", term)

        ins, skp = try_boeing_api(term, conn)
        grand_total_ins += ins
        grand_total_skp += skp
        log.info("  Boeing: +%d inserted, %d skipped", ins, skp)
        time.sleep(1)

        ins, skp = try_l3harris_api(term, conn)
        grand_total_ins += ins
        grand_total_skp += skp
        log.info("  L3Harris: +%d inserted, %d skipped", ins, skp)
        time.sleep(1)

        ins, skp = try_raytheon_api(term, conn)
        grand_total_ins += ins
        grand_total_skp += skp
        log.info("  Raytheon: +%d inserted, %d skipped", ins, skp)
        time.sleep(1)

        ins, skp = try_northrop_api(term, conn)
        grand_total_ins += ins
        grand_total_skp += skp
        log.info("  Northrop: +%d inserted, %d skipped", ins, skp)
        time.sleep(2)

    conn.close()

    print("")
    print("=" * 70)
    print("RADANCY / DEFENSE SCRAPE COMPLETE")
    print(f"Total inserted: {grand_total_ins}")
    print(f"Total skipped:  {grand_total_skp}")
    print("=" * 70)


if __name__ == "__main__":
    main()
