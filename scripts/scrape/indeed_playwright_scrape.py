"""
Indeed Playwright Scraper (with saved cookies)
================================================
Launches a fresh Playwright Chromium browser, loads Indeed cookies from JSON,
navigates to Indeed to establish session, then scrapes job listings.

Uses Playwright's bundled Chromium (no system Chrome needed).
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

SEARCH_QUERIES = [
    "AI engineer remote",
    "LLM engineer remote",
    "machine learning engineer remote",
    "python developer AI remote",
    "devops engineer remote",
    "automation engineer remote",
    "defense software engineer remote",
    "CACI software engineer",
    "Leidos software engineer",
    "SAIC software engineer",
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


def load_cookies(cookies_path):
    """Load and normalize cookies from JSON file."""
    with open(cookies_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    raw = data.get('cookies', data) if isinstance(data, dict) else data
    cookies = []
    for c in raw:
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
        if "expires" in c and c["expires"] and float(c["expires"]) > 0:
            cookie["expires"] = float(c["expires"])
        ss = c.get("sameSite", "")
        if ss in ("Strict", "Lax", "None"):
            cookie["sameSite"] = ss
        elif ss:
            cookie["sameSite"] = "None"
        cookies.append(cookie)
    return cookies


def main():
    print(f"=== INDEED PLAYWRIGHT SCRAPE — {len(SEARCH_QUERIES)} queries ===\n")

    cookies = load_cookies(COOKIES_PATH)
    print(f"Loaded {len(cookies)} cookies from file")

    total_found = 0
    total_inserted = 0

    with sync_playwright() as p:
        # Launch Playwright's own Chromium with stealth-like settings
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=1920,1080",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )

        # Add cookies
        try:
            context.add_cookies(cookies)
            print(f"Added {len(cookies)} cookies to context")
        except Exception as e:
            print(f"Cookie add error: {e}")

        # Remove automation detection signals
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()

        # Navigate to Indeed homepage first to warm up session
        print("\nWarming up session on Indeed homepage...")
        try:
            page.goto("https://www.indeed.com", timeout=30000, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))
            title = page.title()
            print(f"  Homepage: '{title}'")
        except Exception as e:
            print(f"  Homepage nav error: {e}")

        for qi, query in enumerate(SEARCH_QUERIES):
            print(f"\n[{qi+1}/{len(SEARCH_QUERIES)}] Query: {query}")

            q_enc = query.replace(' ', '+')
            url = f"https://www.indeed.com/jobs?q={q_enc}&sort=date&fromage=3&filter=0"

            try:
                pre_delay = random.uniform(3, 8)
                print(f"  Waiting {pre_delay:.1f}s...")
                time.sleep(pre_delay)

                page.goto(url, timeout=30000, wait_until="domcontentloaded")

                try:
                    page.wait_for_selector('[id^=jobTitle-]', timeout=10000)
                except Exception:
                    pass

                time.sleep(random.uniform(1.5, 3))

                page_title = page.title()

                if any(x in page_title.lower() for x in ["blocked", "security", "just a moment", "captcha", "403"]):
                    print(f"  BLOCKED: '{page_title}' — skipping")
                    continue

                html = page.content()
                jobs = parse_job_cards(html)
                total_found += len(jobs)

                inserted = insert_jobs(jobs)
                total_inserted += inserted

                viable = sum(1 for j in jobs if j["fit_score"] >= 40)
                print(f"  Found: {len(jobs)}, New: {inserted}, Viable: {viable} | '{page_title}'")

            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(random.uniform(5, 10))

        browser.close()

    print(f"\n{'='*60}")
    print(f"DONE: found={total_found}, inserted={total_inserted}")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    main()
