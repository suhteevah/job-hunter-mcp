"""
Re-score all jobs by fetching full descriptions from Greenhouse API.
Uses ThreadPoolExecutor for parallel fetching.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import requests

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

# ─── Scoring ──────────────────────────────────────────────────────────

TITLE_KEYWORDS = {
    "ai": 15, "automation": 15, "llm": 15, "prompt engineer": 20,
    "ai engineer": 20, "ml engineer": 15, "qa": 12, "quality": 10,
    "devops": 12, "infrastructure": 10, "backend": 10,
    "full stack": 12, "fullstack": 12, "python": 12, "rust": 15,
    "sales engineer": 12, "solutions engineer": 12,
    "technical consultant": 12, "developer advocate": 10,
    "platform": 10, "sre": 12, "data engineer": 10, "mcp": 20,
    "agent": 15, "software engineer": 8,
}

SKILL_KEYWORDS = [
    "ai", "automation", "llm", "claude", "anthropic", "openai",
    "python", "rust", "javascript", "typescript", "react", "next.js",
    "docker", "kubernetes", "devops", "ci/cd", "linux",
    "qa", "testing", "selenium", "playwright",
    "web scraping", "data pipeline", "mcp", "model context protocol",
    "api", "rest", "graphql", "fastapi", "flask", "django",
    "postgresql", "redis", "mongodb", "sqlite",
    "aws", "gcp", "azure", "cloud",
    "machine learning", "deep learning", "neural", "nlp",
    "rag", "vector", "embedding", "inference",
    "agent", "agentic", "autonomous",
    "n8n", "make.com", "zapier",
    "git", "github", "gitlab",
    "ollama", "gpu", "cuda",
]

NEGATIVE_KEYWORDS = [
    "senior staff", "principal", "director", "vp ",
    "phd required", "15+ years",
    "clearance required", "ts/sci", "security clearance",
    "java ", "c# ", ".net ", "angular", "php ",
    "ios ", "swift ", "kotlin ", "android ",
    "mandarin required", "japanese required", "korean required",
]

BONUS_KEYWORDS = {
    "remote": 5, "contractor": 3, "freelance": 3, "contract": 3,
    "startup": 3, "small team": 3,
}


def score_job(title: str, description: str = "") -> float:
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


# ─── Fetch descriptions ──────────────────────────────────────────────

def extract_board_and_id(url, company=""):
    """Extract board token and job ID from greenhouse URL."""
    m = re.search(r'boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'gh_jid=(\d+)', url)
    if m:
        return None, m.group(1)
    return None, None


def fetch_description(job_row):
    """Fetch full description from Greenhouse API."""
    job_id = job_row["id"]
    url = job_row["url"]
    source = job_row["source"]
    title = job_row["title"]

    if source != "greenhouse":
        # Can't fetch descriptions for non-greenhouse
        return job_id, title, "", score_job(title, "")

    board, gh_id = extract_board_and_id(url)
    if not board or not gh_id:
        return job_id, title, "", score_job(title, "")

    try:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{gh_id}"
        resp = requests.get(api_url, timeout=10, headers={"User-Agent": "JobHunter/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            # Description is HTML — strip tags for scoring
            desc_html = data.get("content", "")
            desc_text = re.sub(r'<[^>]+>', ' ', desc_html)
            desc_text = re.sub(r'\s+', ' ', desc_text).strip()
            new_score = score_job(title, desc_text)
            return job_id, title, desc_text[:2000], new_score
        else:
            return job_id, title, "", score_job(title, "")
    except Exception:
        return job_id, title, "", score_job(title, "")


def main(max_workers=100):
    start = datetime.now(timezone.utc)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all jobs that need rescoring (no description or short description)
    rows = conn.execute("""
        SELECT id, title, company, url, source, fit_score, description
        FROM jobs
        WHERE source = 'greenhouse'
        AND (description IS NULL OR description = '' OR length(description) < 50)
        AND status IN ('new', 'needs_code')
    """).fetchall()
    jobs = [dict(r) for r in rows]
    conn.close()

    print(f"Jobs to rescore: {len(jobs)}")
    if not jobs:
        print("Nothing to rescore.")
        return

    updated = 0
    high_score = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_description, j): j for j in jobs}

        batch = []
        for i, future in enumerate(as_completed(futures)):
            job_id, title, desc, new_score = future.result()
            batch.append((desc[:2000], new_score, job_id))

            if new_score >= 60:
                high_score += 1

            # Batch update every 200
            if len(batch) >= 200:
                conn2 = sqlite3.connect(DB_PATH, timeout=30)
                conn2.executemany(
                    "UPDATE jobs SET description = ?, fit_score = ? WHERE id = ?",
                    batch
                )
                conn2.commit()
                conn2.close()
                updated += len(batch)
                print(f"  Updated {updated}/{len(jobs)} ({high_score} viable)...")
                batch = []

        # Final batch
        if batch:
            conn2 = sqlite3.connect(DB_PATH, timeout=30)
            conn2.executemany(
                "UPDATE jobs SET description = ?, fit_score = ? WHERE id = ?",
                batch
            )
            conn2.commit()
            conn2.close()
            updated += len(batch)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    # Count results
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60")
    viable = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60 AND source='greenhouse'")
    viable_gh = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('new','needs_code') AND fit_score >= 40")
    viable40 = c.fetchone()[0]
    conn.close()

    print(f"\nRescoring complete in {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"Updated: {updated}")
    print(f"Viable (fit>=60): {viable} (Greenhouse: {viable_gh})")
    print(f"Viable (fit>=40): {viable40}")
    print(f"Rate: {updated/(elapsed or 1)*60:.0f} jobs/min")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=100)
    args = parser.parse_args()
    main(max_workers=args.workers)
