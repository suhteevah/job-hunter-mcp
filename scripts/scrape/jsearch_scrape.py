"""Scrape JSearch API (RapidAPI) for remote tech jobs."""
import sys, json, sqlite3, hashlib, time, random, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
API_KEY = "845423ab1emshdc9d0de9746fcdbp175051jsnde0ca0fd970f"
API_HOST = "jsearch.p.rapidapi.com"

QUERIES = [
    "AI engineer remote",
    "machine learning engineer remote",
    "software engineer remote",
    "python developer remote",
    "devops engineer remote",
    "full stack developer remote",
    "backend engineer remote",
    "cloud engineer remote",
    "automation engineer remote",
    "firmware engineer remote",
    "embedded engineer remote",
    "SRE remote",
    "platform engineer remote",
    "Honeywell engineer",
    "defense software engineer",
]

def search_jsearch(query, page=1):
    url = f"https://jsearch.p.rapidapi.com/search?query={urllib.request.quote(query)}&page={page}&num_pages=1&date_posted=week&remote_jobs_only=true"
    req = urllib.request.Request(url, headers={
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('data', [])
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  Rate limited! Waiting 30s...")
            time.sleep(30)
            return []
        elif e.code == 403:
            print(f"  API key expired or quota exceeded")
            return None  # Signal to stop
        else:
            print(f"  HTTP {e.code}: {e.reason}")
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []

def main():
    print("=== JSEARCH SCRAPE ===")
    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=60000")

    total_found = 0
    total_inserted = 0

    for qi, query in enumerate(QUERIES):
        print(f"\n[{qi+1}/{len(QUERIES)}] '{query}'...")
        time.sleep(random.uniform(1, 3))

        jobs = search_jsearch(query)
        if jobs is None:
            print("API quota exceeded — stopping")
            break
        if not jobs:
            continue

        print(f"  Found {len(jobs)} jobs")
        total_found += len(jobs)

        for j in jobs:
            url = j.get('job_apply_link', '') or j.get('job_google_link', '')
            if not url:
                continue
            title = j.get('job_title', 'Unknown')
            company = j.get('employer_name', 'Unknown')
            location = j.get('job_city', '') or 'Remote'
            salary_min = j.get('job_min_salary', '')
            salary_max = j.get('job_max_salary', '')
            salary = f"${salary_min}-${salary_max}" if salary_min and salary_max else ''
            desc = j.get('job_description', '')[:500]

            jid = hashlib.md5(url.encode()).hexdigest()[:16]
            try:
                db.execute("""INSERT OR IGNORE INTO jobs
                    (id, source, source_id, title, company, url, location, salary, description, date_found, status, fit_score)
                    VALUES (?, 'jsearch', ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'new', 0)""",
                    (jid, jid, title, company, url, location, salary, desc))
                if db.total_changes:
                    total_inserted += 1
            except sqlite3.IntegrityError:
                pass

        db.commit()

    print(f"\n=== DONE ===")
    print(f"Total found: {total_found}")
    print(f"New inserted: {total_inserted}")
    print(f"Total DB: {db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]}")

if __name__ == "__main__":
    main()
