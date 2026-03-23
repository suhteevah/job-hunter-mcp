"""Harvest Lever jobs from search results and company pages via Wraith."""
import sys, sqlite3, hashlib, json, re
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

# Lever job URLs collected from Wraith searches
LEVER_JOBS = [
    # AI/ML focused
    ("https://jobs.lever.co/jobgether/242d33d3-ed16-471e-a84f-82486d441f7c", "Senior Engineer, Machine Learning", "Jobgether", "Remote"),
    ("https://jobs.lever.co/hsag/4e53ef1a-35c3-4103-a857-c86eaa1346d2", "AI Engineer (Copilot Studio / Azure AI)", "HSAG", "Remote"),
    ("https://jobs.lever.co/danti.ai/9c61d6b5-35b3-469b-8cbc-e6bdafaaa7a2", "Senior Machine Learning Engineer", "Danti", "Remote"),
    ("https://jobs.lever.co/spear-ai/e8994579-014e-4a11-a407-d50b843aac52", "Machine Learning Engineer", "Spear AI", "Remote"),
    ("https://jobs.lever.co/extremenetworks/3f97b5fc-cf53-4cc7-ac6d-39b8e721e885", "Senior Software Engineer (GenAI/ML)", "Extreme Networks", "San Jose / Toronto / Remote"),
    ("https://jobs.lever.co/jobgether/f26fc9bc-0d1f-420c-ace2-b79517649b61", "Remote AI Engineer", "Jobgether", "Remote"),
    ("https://jobs.lever.co/jobgether/9ef2b82c-2df6-494b-b228-3c1d546160b1", "Agentic AI Engineer", "Jobgether", "Remote"),
    ("https://jobs.lever.co/muttdata/8d40f420-1d29-4e94-a87a-6a271ebe3937", "Machine Learning Engineer", "Mutt Data", "Remote"),
    ("https://jobs.lever.co/bluelightconsulting/51e550b7-9800-4477-acd8-94edf35b77be", "Senior AI/ML Engineer", "Blue Light Consulting", "Remote"),
]

# Company pages to scrape for more jobs
LEVER_COMPANIES = [
    "https://jobs.lever.co/levelai",
    "https://jobs.lever.co/SymmetrySystems",
    "https://jobs.lever.co/danti.ai",
    "https://jobs.lever.co/hsag",
    "https://jobs.lever.co/spear-ai",
    "https://jobs.lever.co/extremenetworks",
    "https://jobs.lever.co/muttdata",
    "https://jobs.lever.co/bluelightconsulting",
]

def make_id(url):
    return hashlib.sha256(url.encode()).hexdigest()[:8]

def insert_job(db, url, title, company, location="Remote"):
    jid = make_id(url)
    try:
        db.execute('''INSERT OR IGNORE INTO jobs
            (id, source, source_id, title, company, url, location, status, date_found, fit_score)
            VALUES (?, 'lever', ?, ?, ?, ?, ?, 'new', ?, 0)''',
            (jid, jid, title, company, url, location, datetime.now(timezone.utc).isoformat()))
        return True
    except Exception as e:
        print(f"  SKIP {title}: {e}")
        return False

def main():
    db = sqlite3.connect(DB_PATH)
    inserted = 0
    dupes = 0

    # Insert known jobs from search
    print(f"Inserting {len(LEVER_JOBS)} jobs from search results...")
    for url, title, company, location in LEVER_JOBS:
        cur = db.execute("SELECT id FROM jobs WHERE url = ?", (url,))
        if cur.fetchone():
            dupes += 1
            print(f"  DUPE: {title} @ {company}")
        elif insert_job(db, url, title, company, location):
            inserted += 1
            print(f"  NEW: {title} @ {company}")

    db.commit()
    print(f"\nDone: {inserted} new, {dupes} dupes")
    print(f"Company pages to scrape via Wraith: {len(LEVER_COMPANIES)}")
    for c in LEVER_COMPANIES:
        print(f"  {c}")

if __name__ == "__main__":
    main()
