"""
Indeed Mass Scrape via FlareSolverr — Search multiple queries, score, insert to DB.
Usage:
  python indeed_mass_scrape.py              # Run all queries
  python indeed_mass_scrape.py --pages 3    # Scrape 3 pages per query
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import sqlite3
import time
import argparse
from datetime import datetime, timezone

# Import from siblings
from flaresolverr_indeed import IndeedSession

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

SEARCH_QUERIES = [
    ("AI engineer", "remote"),
    ("machine learning engineer", "remote"),
    ("python developer AI", "remote"),
    ("data engineer", "remote"),
    ("backend engineer python", "remote"),
    ("MLOps engineer", "remote"),
    ("LLM engineer", "remote"),
    ("software engineer AI", "remote"),
    ("full stack engineer", "remote"),
    ("DevOps engineer", "remote"),
    ("platform engineer", "remote"),
    ("infrastructure engineer", "remote"),
    ("data scientist", "remote"),
    ("AI developer", "remote"),
    ("automation engineer", "remote"),
    ("systems engineer", "remote"),
    ("rust developer", "remote"),
    ("cloud engineer", "remote"),
    ("software engineer python", "Chico CA"),
    ("IT engineer", "Chico CA"),
    ("developer", "Chico CA"),
    ("data analyst", "Chico CA"),
]

# ─── Scoring (same as mega_pipeline.py) ────────────────────────────
TITLE_KEYWORDS = {
    "ai ": 20, "ml ": 20, "machine learning": 25, "llm": 25,
    "data scientist": 15, "data engineer": 15, "nlp": 20,
    "genai": 25, "gen ai": 25, "generative ai": 25,
    "python": 10, "backend": 10, "full stack": 10, "fullstack": 10,
    "infrastructure": 8, "platform": 8, "devops": 8, "sre": 8,
    "cloud": 8, "systems": 5, "automation": 10,
    "rust": 15, "agent": 15, "mcp": 20,
}

SKILL_KEYWORDS = [
    "python", "rust", "typescript", "react", "fastapi", "docker",
    "kubernetes", "aws", "gcp", "azure", "pytorch", "tensorflow",
    "langchain", "openai", "anthropic", "llm", "rag", "vector",
    "postgresql", "redis", "elasticsearch", "kafka", "airflow",
    "ci/cd", "github actions", "terraform", "mcp",
]

NEGATIVE_KEYWORDS = [
    "senior director", "vp of", "vice president", "chief",
    "head of sales", "account executive", "sales rep",
    "nurse", "medical", "clinical", "pharmaceutical",
    "mandarin required", "japanese required", "korean required",
    "clearance required", "ts/sci", "polygraph",
    "intern ", "internship",
]

BONUS_KEYWORDS = {
    "remote": 5, "work from home": 5, "distributed": 3,
    "startup": 3, "series a": 3, "series b": 3,
    "$150": 5, "$160": 5, "$170": 5, "$180": 8, "$200": 10,
}


def score_job(title, description=""):
    score = 0.0
    tl = title.lower()
    dl = (description or "").lower()
    text = tl + " " + dl
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in tl:
            score += pts
    for kw in SKILL_KEYWORDS:
        if kw in dl:
            score += 3
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score -= 10
    for kw, pts in BONUS_KEYWORDS.items():
        if kw in text:
            score += pts
    return max(0, min(100, score))


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def insert_indeed_jobs(jobs):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=2, help="Pages per query (10 results/page)")
    args = parser.parse_args()

    print(f"=== INDEED MASS SCRAPE — {len(SEARCH_QUERIES)} queries x {args.pages} pages ===\n")

    total_found = 0
    total_inserted = 0
    total_viable = 0

    session = None
    try:
        session = IndeedSession()

        for qi, (query, location) in enumerate(SEARCH_QUERIES):
            print(f"\n[{qi+1}/{len(SEARCH_QUERIES)}] Searching: \"{query}\" in {location}")

            for page in range(args.pages):
                start = page * 10
                try:
                    jobs = session.search(query, location, start=start)
                    print(f"  Page {page+1}: {len(jobs)} jobs found")

                    if not jobs:
                        break

                    scored_jobs = []
                    for job in jobs:
                        fit = score_job(job.title, job.snippet)
                        scored_jobs.append({
                            "title": job.title,
                            "company": job.company,
                            "url": job.url,
                            "location": job.location,
                            "salary": job.salary,
                            "job_key": job.job_key,
                            "description": job.snippet,
                            "fit_score": fit,
                        })
                        total_found += 1
                        if fit >= 40:
                            total_viable += 1

                    inserted = insert_indeed_jobs(scored_jobs)
                    total_inserted += inserted
                    print(f"  Inserted: {inserted} new | Viable (40+): {sum(1 for j in scored_jobs if j['fit_score'] >= 40)}")

                    time.sleep(3)  # Be nice to FlareSolverr

                except Exception as e:
                    print(f"  Error on page {page+1}: {e}")
                    # Recreate session on error
                    try:
                        session.close()
                    except Exception:
                        pass
                    time.sleep(5)
                    try:
                        session = IndeedSession()
                    except Exception as e2:
                        print(f"  Session recreation failed: {e2}")
                        break

            time.sleep(2)  # Delay between queries

    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass

    print(f"\n{'='*60}")
    print(f"INDEED SCRAPE DONE")
    print(f"  Total found: {total_found}")
    print(f"  New inserted: {total_inserted}")
    print(f"  Viable (40+): {total_viable}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
