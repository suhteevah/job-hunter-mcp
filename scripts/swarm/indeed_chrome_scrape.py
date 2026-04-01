"""
Indeed Scrape via Logged-In Chrome (CDP)
========================================
Connects to Chrome running with --remote-debugging-port=9222
where the user is logged into Indeed. Uses filter=0 for full pagination.

Usage:
  python indeed_chrome_scrape.py                 # All queries, 5 pages each
  python indeed_chrome_scrape.py --pages 10      # 10 pages per query
  python indeed_chrome_scrape.py --queries 5     # First 5 queries only
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import hashlib
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

SEARCH_QUERIES = [
    # AI / ML
    ("AI engineer", "remote"),
    ("machine learning engineer", "remote"),
    ("LLM engineer", "remote"),
    ("generative AI engineer", "remote"),
    ("AI platform engineer", "remote"),
    ("applied AI engineer", "remote"),
    ("MLOps engineer", "remote"),
    ("NLP engineer", "remote"),
    # Software Engineering
    ("python developer AI", "remote"),
    ("backend engineer python", "remote"),
    ("full stack engineer", "remote"),
    ("software engineer AI", "remote"),
    ("software engineer python", "remote"),
    ("rust developer", "remote"),
    # Infrastructure
    ("DevOps engineer", "remote"),
    ("platform engineer", "remote"),
    ("infrastructure engineer", "remote"),
    ("cloud engineer", "remote"),
    ("systems engineer", "remote"),
    ("SRE", "remote"),
    ("automation engineer", "remote"),
    # Data
    ("data engineer", "remote"),
    ("data scientist", "remote"),
    ("AI developer", "remote"),
    # Defense / Government
    ("software engineer cleared", "remote"),
    ("AI engineer defense", "remote"),
    ("software engineer TS/SCI", "remote"),
    ("cloud engineer government", "remote"),
    ("DevSecOps engineer", "remote"),
    ("cybersecurity engineer", "remote"),
    # Local
    ("software engineer", "Chico CA"),
    ("IT engineer", "Chico CA"),
    ("developer", "Chico CA"),
    ("data analyst", "Chico CA"),
    ("systems administrator", "Chico CA"),
]

# Scoring
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
    score = 30  # base
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
                job["url"], job["location"], job.get("salary", ""),
                job.get("description", ""),
                datetime.now(timezone.utc).isoformat(), job["fit_score"],
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=5, help="Pages per query")
    parser.add_argument("--queries", type=int, default=0, help="Limit queries (0=all)")
    args = parser.parse_args()

    queries = SEARCH_QUERIES[:args.queries] if args.queries > 0 else SEARCH_QUERIES
    # Shuffle query order to avoid predictable patterns
    queries = list(queries)
    random.shuffle(queries)
    print(f"=== INDEED CHROME SCRAPE — {len(queries)} queries x {args.pages} pages ===")
    print(f"Using logged-in Chrome via CDP (localhost:9222)")
    print(f"Query order randomized for anti-detection\n")

    total_found = 0
    total_inserted = 0
    total_viable = 0
    empty_pages = 0

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp('http://localhost:9222')
        except Exception as e:
            print(f"ERROR: Cannot connect to Chrome. Make sure Chrome is running with --remote-debugging-port=9222")
            print(f"  {e}")
            sys.exit(1)

        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for qi, (query, location) in enumerate(queries):
            print(f"\n[{qi+1}/{len(queries)}] Searching: \"{query}\" in {location}")

            for pg_num in range(args.pages):
                start = pg_num * 10
                # Randomize URL parameter order and add organic-looking params
                params = [
                    f"q={query.replace(' ', '+')}",
                    f"l={location.replace(' ', '+')}",
                    f"start={start}",
                    "filter=0",
                ]
                # Randomly include/exclude sort param (Indeed defaults to relevance)
                if random.random() > 0.3:
                    params.append("sort=date")
                # Shuffle param order
                random.shuffle(params)
                url = f"https://www.indeed.com/jobs?{'&'.join(params)}"

                try:
                    # Random pre-navigation delay (human-like)
                    time.sleep(random.uniform(1.0, 3.5))

                    page.goto(url, timeout=30000)
                    try:
                        page.wait_for_selector('[id^=jobTitle-]', timeout=10000)
                    except:
                        pass
                    # Random post-load delay (reading the page)
                    time.sleep(random.uniform(1.5, 4.0))

                    html = page.evaluate('() => document.documentElement.outerHTML')
                    jobs = parse_job_cards(html)

                    if not jobs:
                        empty_pages += 1
                        print(f"  Page {pg_num+1}: 0 jobs (empty)")
                        if empty_pages >= 2:
                            print(f"  Skipping rest of this query (2 empty pages)")
                            empty_pages = 0
                            break
                        continue

                    empty_pages = 0
                    total_found += len(jobs)
                    viable = sum(1 for j in jobs if j["fit_score"] >= 40)
                    total_viable += viable

                    inserted = insert_jobs(jobs)
                    total_inserted += inserted

                    print(f"  Page {pg_num+1}: {len(jobs)} jobs, {inserted} new, {viable} viable")

                    # Random inter-page delay (2-6s, varies)
                    time.sleep(random.uniform(2.0, 6.0))

                except Exception as e:
                    print(f"  Page {pg_num+1}: ERROR — {e}")
                    time.sleep(random.uniform(5, 10))

            # Random delay between queries (3-8s, like switching searches)
            time.sleep(random.uniform(3.0, 8.0))

        browser.close()

    print(f"\n{'='*60}")
    print(f"INDEED CHROME SCRAPE DONE")
    print(f"  Total found: {total_found}")
    print(f"  New inserted: {total_inserted}")
    print(f"  Viable (40+): {total_viable}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
