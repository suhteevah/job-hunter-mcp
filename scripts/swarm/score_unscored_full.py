"""
Score unscored jobs with FULL descriptions fetched from APIs.
Rule: ALWAYS fetch full job descriptions for scoring — never score title-only.

Sources handled:
- Lever: fetch via https://api.lever.co/v0/postings/<company>/<id>
- Greenhouse: fetch via https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>
- Ashby: fetch via https://jobs.ashbyhq.com/api/non-user-graphql (public GraphQL)
- Indeed/arbeitnow: score from existing description in DB
"""
import sys
import re
import sqlite3
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, r"J:\job-hunter-mcp")
from src.apis import score_fit

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
WORKERS = 20
REQUEST_TIMEOUT = 15


def clean_html(html_text):
    if not html_text:
        return ""
    t = re.sub(r'<[^>]+>', ' ', html_text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def fetch_lever_description(url):
    """
    Fetch full description from Lever API.
    URL pattern: https://jobs.lever.co/<company>/<job_id>/apply
    API: https://api.lever.co/v0/postings/<company>/<job_id>
    """
    m = re.search(r'jobs\.lever\.co/([^/]+)/([a-f0-9-]+)', url)
    if not m:
        return None
    company, job_id = m.group(1), m.group(2)
    api_url = f"https://api.lever.co/v0/postings/{company}/{job_id}"
    try:
        resp = requests.get(api_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "JobHunter/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            desc_parts = []
            for field in data.get("descriptionBody", ""):
                if isinstance(field, str):
                    desc_parts.append(field)
            # Try plain text description
            if data.get("descriptionPlain"):
                return clean_html(data["descriptionPlain"])
            if data.get("description"):
                return clean_html(data["description"])
            # lists format
            lists = data.get("lists", [])
            for lst in lists:
                desc_parts.append(lst.get("text", "") + " " + " ".join(lst.get("content", [])))
            text = " ".join(desc_parts).strip()
            if text:
                return text
    except Exception as e:
        pass
    return None


def fetch_greenhouse_description(url, company=""):
    """
    Fetch full description from Greenhouse API.
    URL patterns:
    - https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>
    - https://<company>.com/...?gh_jid=<id>
    - https://job-boards.greenhouse.io/<board>/jobs/<id>
    """
    # Try to extract from boards-api URL
    m = re.search(r'boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([^/]+)/jobs/(\d+)', url)
    if m:
        board, job_id = m.group(1), m.group(2)
        return _gh_fetch(board, job_id)

    # Try job-boards URL
    m = re.search(r'job-boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        board, job_id = m.group(1), m.group(2)
        return _gh_fetch(board, job_id)

    # Try gh_jid parameter with company name
    m = re.search(r'gh_jid=(\d+)', url)
    if m:
        job_id = m.group(1)
        # Derive board token from company name (lowercase, no spaces/punctuation)
        if company:
            board = re.sub(r'[^a-z0-9]', '', company.lower().replace(' ', ''))
            result = _gh_fetch(board, job_id)
            if result:
                return result
            # Also try with just alphanumeric
            board2 = re.sub(r'[^a-z0-9]', '-', company.lower().strip()).strip('-')
            result = _gh_fetch(board2, job_id)
            if result:
                return result
    return None


def _gh_fetch(board, job_id):
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
    try:
        resp = requests.get(api_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "JobHunter/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "") or data.get("description", "")
            if content:
                return clean_html(content)
    except Exception:
        pass
    return None


def fetch_ashby_description(url):
    """
    Fetch full description from Ashby public GraphQL API.
    URL pattern: https://jobs.ashbyhq.com/<company>/<job_id>
    """
    m = re.search(r'jobs\.ashbyhq\.com/([^/]+)/([a-f0-9-]+)', url)
    if not m:
        return None
    company, job_id = m.group(1), m.group(2)

    graphql_url = "https://jobs.ashbyhq.com/api/non-user-graphql"
    query = """
    query JobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
        jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) {
            id
            title
            descriptionHtml
            descriptionSections { descriptionHtml }
        }
    }
    """
    payload = {
        "operationName": "JobPosting",
        "query": query,
        "variables": {
            "organizationHostedJobsPageName": company,
            "jobPostingId": job_id
        }
    }
    try:
        resp = requests.post(
            graphql_url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "JobHunter/1.0",
                "Content-Type": "application/json",
                "Apollo-Require-Preflight": "true",
            }
        )
        if resp.status_code == 200:
            data = resp.json()
            posting = data.get("data", {}).get("jobPosting", {})
            if posting:
                desc_html = posting.get("descriptionHtml", "")
                sections = posting.get("descriptionSections", []) or []
                for s in sections:
                    desc_html += " " + (s.get("descriptionHtml", "") or "")
                if desc_html.strip():
                    return clean_html(desc_html)
    except Exception:
        pass
    return None


def fetch_and_score(job):
    job_id, title, company, url, source, existing_desc = job

    desc = existing_desc or ""
    fetched = False

    if source == "lever" and url and "lever.co" in url:
        fetched_desc = fetch_lever_description(url)
        if fetched_desc and len(fetched_desc) > len(desc):
            desc = fetched_desc
            fetched = True

    elif source == "greenhouse":
        fetched_desc = fetch_greenhouse_description(url or "", company)
        if fetched_desc and len(fetched_desc) > len(desc):
            desc = fetched_desc
            fetched = True

    elif source == "ashby" and url and "ashbyhq.com" in url:
        fetched_desc = fetch_ashby_description(url)
        if fetched_desc and len(fetched_desc) > len(desc):
            desc = fetched_desc
            fetched = True

    # Score with full description
    new_score, new_reason = score_fit(title, desc)

    return {
        "id": job_id,
        "title": title,
        "company": company,
        "source": source,
        "score": new_score,
        "reason": new_reason,
        "desc": desc[:4000] if fetched else None,  # Only save if we fetched new desc
        "fetched": fetched,
        "desc_len": len(desc),
    }


def main():
    start = datetime.now()
    print(f"=== FULL DESCRIPTION SCORING PIPELINE ===")
    print(f"Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    db = sqlite3.connect(DB_PATH)
    rows = db.execute("""
        SELECT id, title, company, url, source, description
        FROM jobs
        WHERE fit_score = 0
        ORDER BY source, company
    """).fetchall()
    db.close()

    print(f"Total unscored jobs to process: {len(rows)}")
    by_source = {}
    for r in rows:
        src = r[4]
        by_source[src] = by_source.get(src, 0) + 1
    for src, cnt in sorted(by_source.items()):
        print(f"  {src}: {cnt}")
    print()

    results = []
    errors = []

    print(f"Fetching descriptions and scoring with {WORKERS} workers...")
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(fetch_and_score, r): r for r in rows}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                result = future.result()
                results.append(result)
                if done % 50 == 0:
                    print(f"  Progress: {done}/{len(rows)}...")
            except Exception as e:
                job = futures[future]
                errors.append(f"  ERROR {job[1]}: {e}")

    print(f"\nDone fetching. Saving to DB...")

    # Write results to DB
    db = sqlite3.connect(DB_PATH, timeout=30)
    updated = 0
    desc_fetched = 0

    for r in results:
        if r["desc"] is not None:
            # We fetched a new description — save both desc and score
            db.execute(
                "UPDATE jobs SET fit_score = ?, fit_reason = ?, description = ? WHERE id = ?",
                (r["score"], r["reason"], r["desc"], r["id"])
            )
            desc_fetched += 1
        else:
            # Score only from existing data
            db.execute(
                "UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE id = ?",
                (r["score"], r["reason"], r["id"])
            )
        updated += 1

    db.commit()

    # Summary stats
    total_viable_60 = db.execute("SELECT COUNT(*) FROM jobs WHERE fit_score >= 60 AND status IN ('new','needs_code')").fetchone()[0]
    total_viable_80 = db.execute("SELECT COUNT(*) FROM jobs WHERE fit_score >= 80 AND status IN ('new','needs_code')").fetchone()[0]
    db.close()

    elapsed = (datetime.now() - start).total_seconds()

    print(f"\n{'='*50}")
    print(f"SCORING COMPLETE in {elapsed:.0f}s")
    print(f"{'='*50}")
    print(f"Total scored:        {updated}")
    print(f"Full descs fetched:  {desc_fetched}")
    print(f"Errors:              {len(errors)}")
    print()

    # Score distribution
    score_buckets = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "40-59": 0, "0-39": 0}
    for r in results:
        s = r["score"]
        if s >= 90: score_buckets["90-100"] += 1
        elif s >= 80: score_buckets["80-89"] += 1
        elif s >= 70: score_buckets["70-79"] += 1
        elif s >= 60: score_buckets["60-69"] += 1
        elif s >= 40: score_buckets["40-59"] += 1
        else: score_buckets["0-39"] += 1

    print("Score distribution (this batch):")
    for bucket, cnt in score_buckets.items():
        print(f"  {bucket}: {cnt}")

    print()
    print(f"Viable jobs in DB (score>=60, status=new/needs_code): {total_viable_60}")
    print(f"High priority (score>=80, status=new/needs_code):      {total_viable_80}")

    print()
    print("=== TOP SCORING JOBS (>= 60) ===")
    top = sorted([r for r in results if r["score"] >= 60], key=lambda x: -x["score"])
    for r in top[:30]:
        fetch_marker = "[FETCHED]" if r["fetched"] else "[existing]"
        print(f"  {r['score']:5.1f}  {fetch_marker}  {r['title'][:55]} @ {r['company']} ({r['source']})")
        print(f"         reason: {r['reason'][:80]}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors[:10]:
            print(e)

    print()
    print("Done!")


if __name__ == "__main__":
    main()
