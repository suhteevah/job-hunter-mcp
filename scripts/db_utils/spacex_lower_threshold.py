"""Apply to SpaceX and Anduril jobs with lowered threshold (score >= 50).
These are high-value companies worth applying to even for tangential roles."""
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA busy_timeout=60000")
c = db.cursor()

# Check what's available at lower threshold
for company in ['SpaceX', 'Anduril', 'Cloudflare', 'Palantir']:
    c.execute("""SELECT COUNT(*) FROM jobs
                 WHERE company=? AND fit_score >= 50 AND fit_score < 60 AND status='new'""", (company,))
    count = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM jobs WHERE company=? AND status='applied'""", (company,))
    applied = c.fetchone()[0]
    print(f"{company}: {count} jobs at 50-59 pts (already applied: {applied})")

    if count > 0:
        c.execute("""SELECT title, fit_score FROM jobs
                     WHERE company=? AND fit_score >= 50 AND fit_score < 60 AND status='new'
                     ORDER BY fit_score DESC LIMIT 10""", (company,))
        for r in c.fetchall():
            print(f"  {r[1]:.0f} | {r[0][:65]}")
