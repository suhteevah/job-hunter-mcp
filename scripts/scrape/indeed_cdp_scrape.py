"""
Indeed CDP Scraper
==================
Connects to Chrome via CDP (port 9222), loads Indeed cookies from JSON,
then scrapes Indeed job search results with random delays.

Uses Playwright to drive Chrome over CDP.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
COOKIES_PATH = r"J:\job-hunter-mcp\scripts\swarm\indeed_cookies.json"
CDP_URL = "http://localhost:9222"

SEARCH_QUERIES = [
    ("AI engineer remote", ""),
    ("LLM engineer remote", ""),
    ("machine learning engineer remote", ""),
    ("python developer AI remote", ""),
    ("devops engineer remote", ""),
    ("automation engineer remote", ""),
    ("defense software engineer remote", ""),
    ("CACI software engineer", ""),
    ("Leidos software engineer", ""),
    ("SAIC software engineer", ""),
]

TITLE_KEYWORDS = {
    "ai ": 20, "ml ": 20, "machine learning": 25, "llm": 25,
    "data scientist": 15, "data engineer": 15, "nlp": 20,
    "genai": 25, "gen ai": 25, "generative ai": 25,
    "python": 10, "backend": 10, "full stack": 10, "fullstack": 10,
    "infrastructure": 8, "platform": 8, "devops": 8, "sre": 8,
    "cloud": 8, "systems": 5, "automation": 10,
    "rust": 15, "agent": 15, "mcp": 20,
    "cleared": 5, "ts/sci": 5, "defense": 5,
}
NEGATIVE_KEYWORDS = ["manager", "director", "sales", "marketing", "recruiter", "intern"]


def score_job(title, description=""):
    text = (title + " " + description).lower()
    score = 30
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in text:
            score += pts
    for kw in NEGATIVE_KEYWORDS:
        if kw in title.lower():
            score -= 15
    if "remote" in text:
        score += 10
    return max(0, min(100, score))


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def insert_jobs(jobs):
    if not jobs:
        return 0
    conn = get_db()
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        jid = hashlib.sha256(job["url"].encode()).hexdigest()[:12]
        try:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE url = ? OR source_id = ?",
                (job["url"], job["job_key"])
            ).fetchone()
            if existing:
                continue
            conn.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  salary, description, date_found, fit_score, status)
                VALUES (?, 'indeed', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                jid, job["job_key"], job["title"], job["company"],
                job["url"], job.get("location", ""), job.get("salary", ""),
                job.get("description", ""),
                now, job["fit_score"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f"  DB error: {e}")
    conn.commit()
    conn.close()
    return inserted


def parse_job_cards(html):
    """Parse job cards from Indeed HTML."""
    jobs = []
    seen = set()

    for match in re.finditer(r'id="jobTitle-([a-f0-9]+)"[^>]*>([^<]+)<', html):
        jk = match.group(1)
        if jk in seen:
            continue
        seen.add(jk)
        title = match.group(2).strip().replace('&amp;', '&').replace('&#x27;', "'").replace('&#39;', "'")

        start = max(0, match.start() - 500)
        end = min(len(html), match.end() + 3000)
        card = html[start:end]

        company_m = re.search(r'data-testid="company-name"[^>]*>([^<]+)<', card)
        company = company_m.group(1).strip() if company_m else "Unknown"

        loc_m = re.search(r'data-testid="text-location"[^>]*>\s*<span>([^<]+)<', card)
        location = loc_m.group(1).strip() if loc_m else ""

        salary_m = re.search(r'data-testid="attribute_snippet_testid"[^>]*>([^<]*\$[^<]+)<', card)
        salary = salary_m.group(1).strip() if salary_m else ""

        snippet_m = re.search(r'<div[^>]*class="[^"]*css-[^"]*"[^>]*><ul[^>]*>(.*?)</ul>', card, re.DOTALL)
        snippet = ""
        if snippet_m:
            snippet = re.sub(r'<[^>]+>', ' ', snippet_m.group(1)).strip()[:500]

        url = f"https://www.indeed.com/viewjob?jk={jk}"
        fit = score_job(title, snippet)

        jobs.append({
            "title": title, "company": company, "url": url,
            "location": location, "salary": salary,
            "job_key": jk, "description": snippet, "fit_score": fit,
        })

    return jobs


def load_cookies_to_browser(context, cookies_path):
    """Load cookies from JSON file into Playwright browser context."""
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cookies = data.get('cookies', data) if isinstance(data, dict) else data

        playwright_cookies = []
        for c in cookies:
            if not isinstance(c, dict):
                continue
            cookie = {
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ".indeed.com"),
                "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
            }
            if "expires" in c and c["expires"]:
                cookie["expires"] = int(c["expires"])
            if "sameSite" in c:
                ss = c["sameSite"]
                if ss in ("Strict", "Lax", "None"):
                    cookie["sameSite"] = ss
            playwright_cookies.append(cookie)

        context.add_cookies(playwright_cookies)
        print(f"  Loaded {len(playwright_cookies)} cookies")
        return len(playwright_cookies)
    except Exception as e:
        print(f"  Cookie load error: {e}")
        return 0


def main():
    print(f"=== INDEED CDP SCRAPE — {len(SEARCH_QUERIES)} queries ===")
    print(f"CDP: {CDP_URL}")
    print(f"Cookies: {COOKIES_PATH}\n")

    total_found = 0
    total_inserted = 0

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            print(f"Connected to Chrome via CDP")
        except Exception as e:
            print(f"ERROR: Cannot connect to Chrome CDP at {CDP_URL}: {e}")
            sys.exit(1)

        ctx = browser.contexts[0] if browser.contexts else browser.new_context()

        # Load Indeed cookies
        print("Loading Indeed cookies...")
        num_cookies = load_cookies_to_browser(ctx, COOKIES_PATH)

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Navigate to Indeed first to set domain context
        print("Navigating to Indeed...")
        try:
            page.goto("https://www.indeed.com", timeout=30000)
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"  Initial navigation warning: {e}")

        for qi, (query, location) in enumerate(SEARCH_QUERIES):
            print(f"\n[{qi+1}/{len(SEARCH_QUERIES)}] Query: {query}")

            # Build URL
            q_enc = query.replace(' ', '+')
            url = f"https://www.indeed.com/jobs?q={q_enc}&sort=date&fromage=3&filter=0"
            if location:
                url += f"&l={location.replace(' ', '+')}"

            try:
                # Random pre-navigation delay
                pre_delay = random.uniform(3, 8)
                print(f"  Waiting {pre_delay:.1f}s (pre-nav delay)...")
                time.sleep(pre_delay)

                page.goto(url, timeout=30000)

                # Wait for job cards to load
                try:
                    page.wait_for_selector('[id^=jobTitle-]', timeout=12000)
                except Exception:
                    pass

                # Post-load delay (simulating reading)
                time.sleep(random.uniform(2, 4))

                # Get page HTML
                html = page.evaluate('() => document.documentElement.outerHTML')

                # Check for block page
                page_title = page.title()
                if "blocked" in page_title.lower() or "security" in page_title.lower() or "captcha" in page_title.lower():
                    print(f"  BLOCKED: Page title = '{page_title}' — skipping")
                    continue

                jobs = parse_job_cards(html)
                total_found += len(jobs)

                inserted = insert_jobs(jobs)
                total_inserted += inserted

                viable = sum(1 for j in jobs if j["fit_score"] >= 40)
                print(f"  Found: {len(jobs)}, New inserted: {inserted}, Viable (40+): {viable}, Page: '{page_title}'")

            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(random.uniform(5, 10))

        browser.close()

    print(f"\n{'='*60}")
    print(f"INDEED CDP SCRAPE COMPLETE")
    print(f"  Total jobs found: {total_found}")
    print(f"  New jobs inserted: {total_inserted}")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    main()
