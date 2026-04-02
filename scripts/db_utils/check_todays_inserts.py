import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
today_indeed = conn.execute("SELECT COUNT(*) FROM jobs WHERE date_found > datetime('now','-3 hours') AND source='indeed'").fetchone()[0]
today_scored = conn.execute("SELECT COUNT(*) FROM jobs WHERE date_found > datetime('now','-3 hours') AND source='indeed' AND fit_score > 0").fetchone()[0]
high_score = conn.execute("SELECT COUNT(*) FROM jobs WHERE date_found > datetime('now','-3 hours') AND source='indeed' AND fit_score >= 60").fetchone()[0]
status_new = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new'").fetchone()[0]

print(f"Total jobs in DB: {total}")
print(f"New indeed jobs (last 3h): {today_indeed}")
print(f"Scored (fit_score>0, last 3h): {today_scored}")
print(f"High score (>=60, last 3h): {high_score}")
print(f"Status=new (all): {status_new}")

# Show top 10 from today's scrape
print("\nTop 10 from today's defense/hardware scrape:")
rows = conn.execute("""
    SELECT title, company, location, fit_score
    FROM jobs
    WHERE date_found > datetime('now','-3 hours') AND source='indeed'
    ORDER BY fit_score DESC
    LIMIT 10
""").fetchall()
for r in rows:
    print(f"  [{int(r[3]):3d}] {r[0]} @ {r[1]} ({r[2]})")
conn.close()
