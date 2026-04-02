"""
indeed_defense_chrome_scrape.py
================================
Scrapes Indeed for defense/hardware/government jobs via logged-in Chrome CDP.
Targets the 10 specific queries requested.

Usage:
  python indeed_defense_chrome_scrape.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

SEARCH_QUERIES = [
    ("Honeywell engineer",                  ""),
    ("ERC engineer",                        ""),
    ("firmware engineer",                   "remote"),
    ("embedded systems engineer",           "remote"),
    ("PCB design engineer",                 ""),
    ("hardware test engineer",              ""),
    ("government software engineer",        "remote"),
    ("cleared software engineer",           "remote"),
    ("Booz Allen Hamilton engineer",        ""),
    ("Peraton engineer",                    ""),
]

TITLE_KEYWORDS = {
    "firmware": 25, "embedded": 25, "fpga": 25, "rtos": 25,
    "pcb": 20, "hardware": 20, "asic": 20, "verilog": 20, "vhdl": 20,
    "cleared": 15, "clearance": 15, "ts/sci": 20, "secret": 10,
    "defense": 15, "dod": 15, "government": 10, "federal": 10,
    "honeywell": 15, "booz": 15, "peraton": 15, "leidos": 15,
    "saic": 15, "caci": 15, "raytheon": 15, "northrop": 15,
    "python": 8, "c++": 8, "rust": 10, "automation": 10,
    "remote": 10, "engineer": 5, "developer": 5,
    "ai ": 10, "ml ": 10, "machine learning": 12,
    "sensor": 10, "signal": 10, "rf ": 15, "radio": 10,
    "test engineer": 12, "verification": 10,
}
NEGATIVE_KEYWORDS = ["manager", "director", "sales", "marketing", "recruiter", "intern", "vp "]


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
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def insert_jobs(jobs):
    if not jobs:
        return 0, 0
    conn = get_db()
    inserted = 0
    skipped = 0
    for job in jobs:
        jid = hashlib.sha256(job["url"].encode()).hexdigest()[:12]
        try:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE url = ? OR source_id = ?",
                (job["url"], job["job_key"])
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  salary, description, date_found, fit_score, status)
                VALUES (?, 'indeed', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                jid, job["job_key"], job["title"], job["company"],
                job["url"], job["location"], job.get("salary", ""),
                job.get("description", ""),
                datetime.now(timezone.utc).isoformat(), job["fit_score"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as e:
            print(f"  DB error: {e}")
    conn.commit()
    conn.close()
    return inserted, skipped


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


def main():
    MAX_PAGES = 3  # 3 pages per query = ~45 jobs each
    print(f"=== INDEED DEFENSE/HARDWARE CHROME SCRAPE ===")
    print(f"Queries: {len(SEARCH_QUERIES)} | Pages per query: {MAX_PAGES}")
    print(f"Connecting to Chrome on localhost:9222\n")

    total_found = 0
    total_inserted = 0
    total_skipped = 0

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp('http://localhost:9222')
        except Exception as e:
            print(f"ERROR: Cannot connect to Chrome CDP: {e}")
            print("Make sure Chrome is running with --remote-debugging-port=9222")
            sys.exit(1)

        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for qi, (query, location) in enumerate(SEARCH_QUERIES):
            loc_str = location if location else "nationwide"
            print(f"\n[{qi+1}/{len(SEARCH_QUERIES)}] '{query}' in {loc_str}")
            empty_streak = 0

            for pg_num in range(MAX_PAGES):
                start = pg_num * 10
                params = [
                    f"q={query.replace(' ', '+')}",
                    f"start={start}",
                    "sort=date",
                    "fromage=7",
                    "filter=0",
                ]
                if location:
                    params.append(f"l={location.replace(' ', '+')}")
                random.shuffle(params)
                url = f"https://www.indeed.com/jobs?{'&'.join(params)}"

                try:
                    pre_delay = random.uniform(3.0, 8.0)
                    print(f"  Page {pg_num+1}: waiting {pre_delay:.1f}s, fetching...")
                    time.sleep(pre_delay)

                    page.goto(url, timeout=30000)
                    try:
                        page.wait_for_selector('[id^=jobTitle-]', timeout=10000)
                    except:
                        pass
                    time.sleep(random.uniform(1.5, 3.0))

                    html = page.evaluate('() => document.documentElement.outerHTML')
                    jobs = parse_job_cards(html)

                    if not jobs:
                        empty_streak += 1
                        print(f"  Page {pg_num+1}: 0 jobs (empty)")
                        if empty_streak >= 2:
                            print(f"  Stopping (2 empty pages in a row)")
                            break
                        continue

                    empty_streak = 0
                    total_found += len(jobs)
                    inserted, skipped = insert_jobs(jobs)
                    total_inserted += inserted
                    total_skipped += skipped

                    viable = sum(1 for j in jobs if j["fit_score"] >= 40)
                    print(f"  Page {pg_num+1}: {len(jobs)} jobs | New: {inserted} | Dupes: {skipped} | Viable(40+): {viable}")
                    # Show top 2 jobs
                    for j in sorted(jobs, key=lambda x: -x["fit_score"])[:2]:
                        print(f"    [{j['fit_score']:3d}] {j['title']} @ {j['company']} ({j['location']})")

                except Exception as e:
                    print(f"  Page {pg_num+1}: ERROR — {e}")
                    time.sleep(5)

        browser.close()

    print(f"\n{'='*60}")
    print(f"SCRAPE COMPLETE")
    print(f"  Total jobs found    : {total_found}")
    print(f"  New inserted to DB  : {total_inserted}")
    print(f"  Dupes skipped       : {total_skipped}")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    main()
