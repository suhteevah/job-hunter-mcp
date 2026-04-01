import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

# Check what lever jobs look like
c.execute("SELECT COUNT(*) FROM jobs WHERE source='lever'")
print(f"Total lever jobs: {c.fetchone()[0]}")

c.execute("SELECT fit_score, COUNT(*) FROM jobs WHERE source='lever' GROUP BY fit_score ORDER BY fit_score DESC LIMIT 20")
print("\nLever score distribution:")
for r in c.fetchall():
    print(f"  score={r[0]}: {r[1]}")

# Check a specific Mistral Applied AI job
c.execute("SELECT id, fit_score, fit_reason, title FROM jobs WHERE title LIKE 'Applied AI%' AND source='lever' LIMIT 5")
print("\nMistral Applied AI jobs:")
for r in c.fetchall():
    print(f"  id={r[0]}, score={r[1]}, reason={r[2]}, title={r[3][:50]}")

# What does wraith_apply_swarm.py use as its query?
print("\nChecking swarm query pattern...")
c.execute("SELECT source, fit_score, status, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source, fit_score, status LIMIT 30")
for r in c.fetchall():
    print(f"  {r[0]} | score={r[1]} | {r[2]} | count={r[3]}")
