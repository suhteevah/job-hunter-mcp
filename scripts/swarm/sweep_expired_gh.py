"""Sweep apply_failed Greenhouse jobs and reclassify expired ones as status=expired.

Uses cheap HTTP GET (with redirect follow) to detect ?error=true redirects.
Skips Wraith entirely — orders of magnitude faster than re-running apply swarm.
"""
import sqlite3
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
}


def check(job):
    job_id, url = job
    try:
        r = requests.get(url, headers=H, timeout=20, allow_redirects=True)
        final = r.url.lower()
        body = r.text.lower()
        expired = (
            "error=true" in final
            or "current openings at" in body
            or "current openings" in body and "jobs" in body and "apply" not in body[:2000]
        )
        return job_id, expired, final
    except Exception as e:
        return job_id, None, str(e)[:80]


def main():
    db = sqlite3.connect(DB)
    c = db.cursor()
    rows = c.execute(
        "SELECT id, url FROM jobs "
        "WHERE status='apply_failed' AND source='greenhouse' "
        "AND (url LIKE '%greenhouse.io%' OR url LIKE '%gh_jid=%')"
    ).fetchall()
    print(f"Checking {len(rows)} apply_failed GH jobs...")

    expired_ids = []
    errors = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(check, r): r for r in rows}
        for i, f in enumerate(as_completed(futs), 1):
            job_id, expired, info = f.result()
            if expired is True:
                expired_ids.append(job_id)
            elif expired is None:
                errors += 1
            if i % 25 == 0:
                print(f"  {i}/{len(rows)}  expired={len(expired_ids)}  err={errors}  "
                      f"({(time.time()-start):.0f}s)")

    print(f"\nTotal: {len(rows)}  Expired: {len(expired_ids)}  Errors: {errors}")
    if expired_ids:
        c.executemany(
            "UPDATE jobs SET status='expired', "
            "notes=COALESCE(notes,'')||' [auto-swept 2026-04-08]' WHERE id=?",
            [(i,) for i in expired_ids],
        )
        db.commit()
        print(f"Reclassified {len(expired_ids)} → expired")
    db.close()


if __name__ == "__main__":
    main()
