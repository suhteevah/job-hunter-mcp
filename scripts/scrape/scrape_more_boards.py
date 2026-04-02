#!/usr/bin/env python
"""
scrape_more_boards.py
Scrapes 15+ new job boards + additional Greenhouse slugs.
Writes all found jobs to JSON, then inserts into SQLite DB.

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe scrape_more_boards.py
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
import random
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
OUTPUT_JSON = r"J:\job-hunter-mcp\scripts\swarm\logs\more_boards_20260401.json"
REQUEST_TIMEOUT = 15
DELAY_MIN = 3
DELAY_MAX = 6

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_json(url, timeout=REQUEST_TIMEOUT):
    try:
        req = Request(url, headers={**HEADERS, "Accept": "application/json"})
        with urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw.decode('utf-8', errors='replace'))
    except HTTPError as e:
        log.warning(f"HTTP {e.code} for {url}")
        return None
    except Exception as e:
        log.warning(f"Error fetching {url}: {e}")
        return None

def fetch_text(url, timeout=REQUEST_TIMEOUT):
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        log.warning(f"Error fetching text {url}: {e}")
        return None

def delay():
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    log.info(f"  Sleeping {t:.1f}s...")
    time.sleep(t)

# ---------------------------------------------------------------------------
# Dedup helper
# ---------------------------------------------------------------------------
def make_uid(title, company, url):
    s = f"{title}|{company}|{url}".lower()
    return hashlib.sha1(s.encode()).hexdigest()

# ---------------------------------------------------------------------------
# Greenhouse helper
# ---------------------------------------------------------------------------
def scrape_greenhouse(slug, source_name=None):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    log.info(f"Greenhouse: {slug}")
    data = fetch_json(url)
    if not data:
        return []
    jobs = data.get("jobs", [])
    results = []
    for j in jobs:
        title = j.get("title", "")
        loc = j.get("location", {}).get("name", "") if isinstance(j.get("location"), dict) else ""
        job_url = j.get("absolute_url", "")
        company = source_name or slug
        results.append({
            "title": title,
            "company": company,
            "url": job_url,
            "location": loc,
            "source": f"greenhouse_{slug}",
            "description": j.get("content", "")[:2000] if j.get("content") else "",
        })
    log.info(f"  -> {len(results)} jobs from greenhouse/{slug}")
    return results

# ---------------------------------------------------------------------------
# Working Nomads RSS/JSON
# ---------------------------------------------------------------------------
def scrape_working_nomads():
    log.info("Working Nomads...")
    results = []
    # Try JSON API
    categories = ["software-dev", "programming", "devops-sysadmin", "product"]
    for cat in categories:
        url = f"https://www.workingnomads.com/api/exposed_jobs/?category={cat}&limit=100"
        data = fetch_json(url)
        if data and isinstance(data, list):
            for j in data:
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "url": j.get("url", "") or f"https://www.workingnomads.com/jobs/{j.get('slug','')}",
                    "location": j.get("region", "Remote"),
                    "source": "workingnomads",
                    "description": j.get("description", "")[:2000],
                })
            log.info(f"  -> Working Nomads cat={cat}: {len(data)} jobs")
        elif data and isinstance(data, dict):
            items = data.get("results", data.get("jobs", []))
            for j in items:
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "url": j.get("url", "") or j.get("job_url", ""),
                    "location": j.get("region", "Remote"),
                    "source": "workingnomads",
                    "description": j.get("description", "")[:2000],
                })
        delay()
    log.info(f"  -> Working Nomads total: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Remotive (already have but try new categories)
# ---------------------------------------------------------------------------
def scrape_remotive_extra():
    log.info("Remotive extra categories...")
    results = []
    cats = ["all"]
    for cat in cats:
        url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=200"
        data = fetch_json(url)
        if data and "jobs" in data:
            for j in data["jobs"]:
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "url": j.get("url", ""),
                    "location": j.get("candidate_required_location", "Remote"),
                    "source": "remotive",
                    "description": j.get("description", "")[:2000],
                })
        delay()
    log.info(f"  -> Remotive extra: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Remote.co scrape
# ---------------------------------------------------------------------------
def scrape_remote_co():
    log.info("Remote.co...")
    results = []
    # Try their jobs JSON feed
    urls = [
        "https://remote.co/remote-jobs/developer/",
        "https://remote.co/remote-jobs/programmer/",
    ]
    for url in urls:
        html = fetch_text(url)
        if not html:
            delay()
            continue
        # Parse job listings from HTML
        # Look for job title patterns
        pattern = r'<a[^>]+href="(/remote-jobs/[^"]+)"[^>]*>\s*<[^>]+>\s*([^<]+)</[^>]+>\s*</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for m in matches[:50]:
            job_url = f"https://remote.co{m[0]}"
            title = m[1].strip()
            if title and len(title) > 3:
                results.append({
                    "title": title,
                    "company": "Remote.co listing",
                    "url": job_url,
                    "location": "Remote",
                    "source": "remote_co",
                    "description": "",
                })
        # Also try card pattern
        card_pattern = r'<h2[^>]*class="[^"]*job[^"]*"[^>]*>(.*?)</h2>'
        cards = re.findall(card_pattern, html, re.DOTALL | re.IGNORECASE)
        for c in cards[:30]:
            clean = re.sub(r'<[^>]+>', '', c).strip()
            if clean:
                results.append({
                    "title": clean,
                    "company": "Remote.co",
                    "url": url,
                    "location": "Remote",
                    "source": "remote_co",
                    "description": "",
                })
        delay()
    # Try their API/RSS
    rss_url = "https://remote.co/remote-jobs/feed/"
    rss_html = fetch_text(rss_url)
    if rss_html:
        items = re.findall(r'<item>(.*?)</item>', rss_html, re.DOTALL)
        for item in items[:100]:
            title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
            title = title_m.group(1).strip() if title_m else ""
            link = link_m.group(1).strip() if link_m else ""
            if title:
                results.append({
                    "title": title,
                    "company": "Remote.co",
                    "url": link,
                    "location": "Remote",
                    "source": "remote_co",
                    "description": "",
                })
    log.info(f"  -> Remote.co: {len(results)} jobs")
    return results

# ---------------------------------------------------------------------------
# JustRemote
# ---------------------------------------------------------------------------
def scrape_justremote():
    log.info("JustRemote...")
    results = []
    # Try their API
    url = "https://justremote.co/api/jobs/?category=developer&remote_type=full_remote&page_size=100"
    data = fetch_json(url)
    if data:
        items = data.get("results", data.get("jobs", []))
        if isinstance(data, list):
            items = data
        for j in items:
            results.append({
                "title": j.get("title", j.get("name", "")),
                "company": j.get("company", j.get("company_name", "")),
                "url": j.get("url", j.get("job_url", f"https://justremote.co/remote-jobs/{j.get('slug','')}")),
                "location": j.get("location", "Remote"),
                "source": "justremote",
                "description": j.get("description", "")[:2000],
            })
    delay()
    # Also try the main categories
    for cat in ["developer", "software-engineer", "devops"]:
        url2 = f"https://justremote.co/api/jobs/?search={cat}&page_size=100"
        data2 = fetch_json(url2)
        if data2:
            items2 = data2.get("results", []) if isinstance(data2, dict) else data2
            for j in items2:
                results.append({
                    "title": j.get("title", j.get("name", "")),
                    "company": j.get("company", j.get("company_name", "")),
                    "url": j.get("url", j.get("job_url", "")),
                    "location": j.get("location", "Remote"),
                    "source": "justremote",
                    "description": j.get("description", "")[:2000],
                })
        delay()
    log.info(f"  -> JustRemote: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Hacker News Who's Hiring (Algolia API)
# ---------------------------------------------------------------------------
def scrape_hn_hiring():
    log.info("HN Who's Hiring (Algolia)...")
    results = []
    # Get the latest "Who is hiring" thread
    url = "https://hn.algolia.com/api/v1/search?query=Ask+HN+Who+is+hiring&tags=ask_hn&hitsPerPage=5"
    data = fetch_json(url)
    if not data:
        log.warning("HN: Could not fetch thread list")
        return results

    hits = data.get("hits", [])
    # Find most recent "who is hiring" post
    thread_id = None
    for h in hits:
        title = h.get("title", "")
        if "who is hiring" in title.lower():
            thread_id = h.get("objectID")
            log.info(f"  HN thread: {title} (id={thread_id})")
            break

    if not thread_id:
        log.warning("HN: No 'who is hiring' thread found")
        return results

    delay()
    # Fetch comments from that thread
    comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{thread_id}&hitsPerPage=200"
    cdata = fetch_json(comments_url)
    if not cdata:
        return results

    for hit in cdata.get("hits", []):
        text = hit.get("comment_text", "")
        if not text:
            continue
        # Skip very short ones
        if len(text) < 30:
            continue
        # Parse company | title | location pattern
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        if not lines:
            continue
        first_line = lines[0]
        # Try to extract company and title from first line
        parts = re.split(r'\s*[\|/]\s*', first_line)
        company = parts[0].strip() if parts else "HN Hiring"
        title = parts[1].strip() if len(parts) > 1 else "See description"
        location = "Remote" if "remote" in clean_text.lower() else parts[2].strip() if len(parts) > 2 else "Unknown"
        job_url = f"https://news.ycombinator.com/item?id={hit.get('objectID','')}"
        results.append({
            "title": title[:200],
            "company": company[:200],
            "url": job_url,
            "location": location[:100],
            "source": "hn_hiring",
            "description": clean_text[:2000],
        })

    log.info(f"  -> HN Who's Hiring: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# YCombinator Work at a Startup
# ---------------------------------------------------------------------------
def scrape_workatastartup():
    log.info("YC Work at a Startup...")
    results = []
    # Try their API
    url = "https://www.workatastartup.com/companies/filters?companySize=any&demographic=any&hasSalary=false&industry=any&interestInDesignTools=any&investedIn=any&jobType=any&layout=list-compact&sortBy=created_at&tab=any&usVisaNotRequired=false&query="
    data = fetch_json(url)
    if data and isinstance(data, dict):
        companies = data.get("companies", [])
        for co in companies[:100]:
            co_name = co.get("name", "")
            for job in co.get("jobs", []):
                results.append({
                    "title": job.get("title", ""),
                    "company": co_name,
                    "url": f"https://www.workatastartup.com/jobs/{job.get('id','')}",
                    "location": job.get("location_or_remote", "Remote"),
                    "source": "workatastartup",
                    "description": job.get("description", "")[:2000],
                })
    delay()
    # Also try direct jobs API
    jobs_url = "https://www.workatastartup.com/jobs?remote=true&role=engineer"
    data2 = fetch_json(jobs_url)
    if data2 and isinstance(data2, dict):
        for j in data2.get("jobs", []):
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else "",
                "url": f"https://www.workatastartup.com/jobs/{j.get('id','')}",
                "location": j.get("location_or_remote", "Remote"),
                "source": "workatastartup",
                "description": j.get("description", "")[:2000],
            })
    log.info(f"  -> WorkAtAStartup: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Dice.com API
# ---------------------------------------------------------------------------
def scrape_dice():
    log.info("Dice.com...")
    results = []
    # Dice has a public API
    queries = ["software engineer remote", "python developer remote", "devops remote", "automation engineer remote"]
    for q in queries:
        import urllib.parse
        q_enc = urllib.parse.quote(q)
        url = f"https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search?q={q_enc}&countryCode2=US&radius=30&radiusUnit=mi&page=1&pageSize=50&filters.workplaceTypes=Remote&language=en"
        data = fetch_json(url)
        if data:
            for j in data.get("data", []):
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("advertiser", {}).get("name", "") if isinstance(j.get("advertiser"), dict) else j.get("companyName", ""),
                    "url": j.get("applyDataLink", j.get("apply_url", f"https://www.dice.com/job-detail/{j.get('id','')}")),
                    "location": j.get("location", "Remote"),
                    "source": "dice",
                    "description": j.get("summary", "")[:2000],
                })
        delay()
    log.info(f"  -> Dice: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# BuiltIn
# ---------------------------------------------------------------------------
def scrape_builtin():
    log.info("BuiltIn...")
    results = []
    # BuiltIn has a GraphQL/REST API
    url = "https://api.builtin.com/jobs/search?role=Software+Engineer&remote=true&page=1&perPage=100"
    data = fetch_json(url)
    if data:
        for j in data.get("jobs", data.get("results", [])):
            results.append({
                "title": j.get("title", j.get("name", "")),
                "company": j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else j.get("companyName", ""),
                "url": j.get("url", j.get("canonical", "")),
                "location": j.get("remote", j.get("locations", "Remote")),
                "source": "builtin",
                "description": j.get("description", "")[:2000],
            })
    delay()
    # Also try builtin.com's job listing endpoint
    url2 = "https://builtin.com/api/jobs?remote=true&title=engineer&page=1"
    data2 = fetch_json(url2)
    if data2:
        for j in data2.get("jobs", []):
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "url": j.get("url", ""),
                "location": "Remote",
                "source": "builtin",
                "description": "",
            })
    log.info(f"  -> BuiltIn: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Startup.jobs
# ---------------------------------------------------------------------------
def scrape_startup_jobs():
    log.info("Startup.jobs...")
    results = []
    url = "https://startup.jobs/api/jobs?remote=true&page=1&per_page=100"
    data = fetch_json(url)
    if data:
        jobs_list = data.get("jobs", data.get("data", []))
        if isinstance(data, list):
            jobs_list = data
        for j in jobs_list:
            results.append({
                "title": j.get("title", j.get("name", "")),
                "company": j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else j.get("company_name", ""),
                "url": j.get("url", j.get("job_url", f"https://startup.jobs/{j.get('slug','')}")),
                "location": j.get("location", "Remote"),
                "source": "startup_jobs",
                "description": j.get("description", "")[:2000],
            })
    delay()
    log.info(f"  -> Startup.jobs: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Otta (via their public jobs feed)
# ---------------------------------------------------------------------------
def scrape_otta():
    log.info("Otta.com...")
    results = []
    # Try their API endpoint
    url = "https://api.otta.com/graphql"
    # GraphQL - try a simple REST endpoint first
    rest_url = "https://api.otta.com/jobs?limit=100&remote=true"
    data = fetch_json(rest_url)
    if data:
        for j in data.get("results", data.get("jobs", [])):
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else "",
                "url": j.get("url", f"https://app.otta.com/jobs/{j.get('id','')}"),
                "location": j.get("remote_status", "Remote"),
                "source": "otta",
                "description": j.get("description", "")[:2000],
            })
    delay()
    log.info(f"  -> Otta: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Nodesk (remote job aggregator)
# ---------------------------------------------------------------------------
def scrape_nodesk():
    log.info("Nodesk...")
    results = []
    # Nodesk aggregates from other boards - try their RSS
    url = "https://nodesk.co/remote-jobs/feed/"
    rss = fetch_text(url)
    if rss:
        items = re.findall(r'<item>(.*?)</item>', rss, re.DOTALL)
        for item in items[:100]:
            title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item, re.DOTALL)
            if not title_m:
                title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
            company_m = re.search(r'<company>(.*?)</company>', item, re.DOTALL)
            title = title_m.group(1).strip() if title_m else ""
            link = link_m.group(1).strip() if link_m else ""
            company = company_m.group(1).strip() if company_m else "Nodesk"
            if title:
                results.append({
                    "title": title,
                    "company": company,
                    "url": link,
                    "location": "Remote",
                    "source": "nodesk",
                    "description": "",
                })
    delay()
    log.info(f"  -> Nodesk: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Pangian
# ---------------------------------------------------------------------------
def scrape_pangian():
    log.info("Pangian...")
    results = []
    url = "https://pangian.com/job-travel-remote/?s=&category=&type=remote"
    data = fetch_json(url)
    if data:
        for j in (data.get("jobs", []) if isinstance(data, dict) else data):
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "url": j.get("url", ""),
                "location": "Remote",
                "source": "pangian",
                "description": "",
            })
    delay()
    # Try RSS
    rss_url = "https://pangian.com/feed/"
    rss = fetch_text(rss_url)
    if rss:
        items = re.findall(r'<item>(.*?)</item>', rss, re.DOTALL)
        for item in items[:50]:
            title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item, re.DOTALL)
            if not title_m:
                title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
            title = title_m.group(1).strip() if title_m else ""
            link = link_m.group(1).strip() if link_m else ""
            if title and ("job" in link.lower() or "career" in link.lower() or "remote" in link.lower()):
                results.append({
                    "title": title,
                    "company": "Pangian",
                    "url": link,
                    "location": "Remote",
                    "source": "pangian",
                    "description": "",
                })
    log.info(f"  -> Pangian: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# PowerToFly
# ---------------------------------------------------------------------------
def scrape_powertofly():
    log.info("PowerToFly...")
    results = []
    # Try their API
    url = "https://powertofly.com/api/v1/job_postings/?remote=true&page=1&per_page=100"
    data = fetch_json(url)
    if data:
        for j in data.get("results", data.get("jobs", [])):
            results.append({
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("name", "") if isinstance(j.get("company"), dict) else j.get("company_name", ""),
                "url": j.get("url", j.get("job_url", "")),
                "location": j.get("location", "Remote"),
                "source": "powertofly",
                "description": j.get("description", "")[:2000],
            })
    delay()
    log.info(f"  -> PowerToFly: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Authentic Jobs
# ---------------------------------------------------------------------------
def scrape_authentic_jobs():
    log.info("Authentic Jobs...")
    results = []
    # Try their RSS feed
    url = "https://www.authenticjobs.com/feed/"
    rss = fetch_text(url)
    if rss:
        items = re.findall(r'<item>(.*?)</item>', rss, re.DOTALL)
        for item in items[:100]:
            title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item, re.DOTALL)
            if not title_m:
                title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(https?://[^<]+)</link>', item, re.DOTALL)
            company_m = re.search(r'<company>(.*?)</company>', item, re.DOTALL)
            loc_m = re.search(r'<location>(.*?)</location>', item, re.DOTALL)
            title = title_m.group(1).strip() if title_m else ""
            link = link_m.group(1).strip() if link_m else ""
            company = company_m.group(1).strip() if company_m else "Authentic Jobs"
            loc = loc_m.group(1).strip() if loc_m else "Remote"
            if title:
                results.append({
                    "title": re.sub(r'<[^>]+>', '', title),
                    "company": re.sub(r'<[^>]+>', '', company),
                    "url": link,
                    "location": loc,
                    "source": "authenticjobs",
                    "description": "",
                })
    delay()
    log.info(f"  -> Authentic Jobs: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Gun.io
# ---------------------------------------------------------------------------
def scrape_gun_io():
    log.info("Gun.io...")
    results = []
    url = "https://gun.io/api/v1/jobs/?remote=true&page=1"
    data = fetch_json(url)
    if data:
        for j in data.get("results", data.get("jobs", [])):
            results.append({
                "title": j.get("title", j.get("name", "")),
                "company": j.get("company", j.get("client_name", "")),
                "url": j.get("url", f"https://gun.io/jobs/{j.get('id','')}"),
                "location": j.get("location", "Remote"),
                "source": "gun_io",
                "description": j.get("description", "")[:2000],
            })
    delay()
    log.info(f"  -> Gun.io: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Jobicy (JSON API)
# ---------------------------------------------------------------------------
def scrape_jobicy_extra():
    log.info("Jobicy extra...")
    results = []
    url = "https://jobicy.com/api/v2/remote-jobs?count=100&geo=anywhere&industry=tech"
    data = fetch_json(url)
    if data and "jobs" in data:
        for j in data["jobs"]:
            results.append({
                "title": j.get("jobTitle", ""),
                "company": j.get("companyName", ""),
                "url": j.get("url", ""),
                "location": j.get("jobGeo", "Remote"),
                "source": "jobicy",
                "description": j.get("jobDescription", "")[:2000],
            })
    delay()
    log.info(f"  -> Jobicy extra: {len(results)}")
    return results

# ---------------------------------------------------------------------------
# Main collection
# ---------------------------------------------------------------------------
def collect_all():
    all_jobs = []
    stats = {}

    # === GREENHOUSE SLUGS ===
    gh_slugs = [
        "hubspot", "asana", "zapier", "monday", "clickup",
        "canva", "miro", "snyk", "wiz", "crowdstrike",
        "sentinelone", "paloaltonetworks", "zscaler", "fortinet",
        "rapid7", "nerdwallet", "peloton", "niantic", "hashicorp",
        "confluent", "dropbox", "box", "zendesk", "freshworks",
        "servicenow", "workday", "splunk", "newrelic", "sumologic",
        "elasticcloud",
    ]

    gh_results = {}
    for slug in gh_slugs:
        jobs = scrape_greenhouse(slug)
        gh_results[slug] = len(jobs)
        all_jobs.extend(jobs)
        delay()

    stats["greenhouse"] = gh_results
    log.info(f"Greenhouse total: {sum(gh_results.values())} from {len(gh_results)} boards")

    # === OTHER SOURCES ===
    sources = [
        ("working_nomads", scrape_working_nomads),
        ("remote_co", scrape_remote_co),
        ("justremote", scrape_justremote),
        ("hn_hiring", scrape_hn_hiring),
        ("workatastartup", scrape_workatastartup),
        ("dice", scrape_dice),
        ("builtin", scrape_builtin),
        ("startup_jobs", scrape_startup_jobs),
        ("otta", scrape_otta),
        ("nodesk", scrape_nodesk),
        ("pangian", scrape_pangian),
        ("powertofly", scrape_powertofly),
        ("authenticjobs", scrape_authentic_jobs),
        ("gun_io", scrape_gun_io),
        ("jobicy", scrape_jobicy_extra),
        ("remotive", scrape_remotive_extra),
    ]

    for name, fn in sources:
        try:
            jobs = fn()
            stats[name] = len(jobs)
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"Error in {name}: {e}")
            stats[name] = 0

    return all_jobs, stats

# ---------------------------------------------------------------------------
# DB Insert
# ---------------------------------------------------------------------------
def insert_to_db(jobs):
    log.info(f"Inserting {len(jobs)} jobs into DB...")
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()

    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            title TEXT,
            company TEXT,
            url TEXT,
            location TEXT,
            source TEXT,
            description TEXT,
            scored INTEGER DEFAULT 0,
            score REAL,
            applied INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    inserted = 0
    skipped = 0
    for j in jobs:
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "").strip()
        url = (j.get("url") or "").strip()
        if not title:
            skipped += 1
            continue
        uid = make_uid(title, company, url)
        try:
            cur.execute("""
                INSERT OR IGNORE INTO jobs (uid, title, company, url, location, source, description)
                VALUES (?,?,?,?,?,?,?)
            """, (uid, title[:500], company[:300], url[:1000], (j.get("location") or "Remote")[:200],
                  j.get("source","unknown")[:100], (j.get("description") or "")[:3000]))
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            log.warning(f"Insert error: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    log.info(f"  -> Inserted: {inserted}, Skipped/dupe: {skipped}")
    return inserted

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log.info("=" * 60)
    log.info("MORE BOARDS SCRAPER - 2026-04-01")
    log.info("=" * 60)

    all_jobs, stats = collect_all()

    # Save JSON
    import os
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)
    log.info(f"Saved {len(all_jobs)} jobs to {OUTPUT_JSON}")

    # Insert to DB
    inserted = insert_to_db(all_jobs)

    # Print summary
    log.info("\n" + "=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)
    total = 0
    for k, v in stats.items():
        if isinstance(v, dict):
            sub = sum(v.values())
            log.info(f"  greenhouse combined: {sub} jobs")
            for slug, cnt in v.items():
                if cnt > 0:
                    log.info(f"    -> {slug}: {cnt}")
            total += sub
        else:
            log.info(f"  {k}: {v}")
            total += v
    log.info(f"\nTOTAL COLLECTED: {total}")
    log.info(f"TOTAL INSERTED (new): {inserted}")
