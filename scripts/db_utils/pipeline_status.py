import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

print("=== PIPELINE STATUS ===\n")

# Overall
c.execute("SELECT COUNT(*) FROM jobs")
print(f"Total jobs in DB: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
print(f"Applied: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM jobs WHERE status='apply_failed'")
print(f"Failed: {c.fetchone()[0]}")

# Ready to apply (score >= 60, new)
print("\n--- READY TO APPLY (score>=60, new) ---")
c.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC")
total_ready = 0
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
    total_ready += r[1]
print(f"  TOTAL: {total_ready}")

# Unscored
c.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score <= 1 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC")
print("\n--- UNSCORED / LOW-SCORE (<=1, new) ---")
total_unscored = 0
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
    total_unscored += r[1]
print(f"  TOTAL: {total_unscored}")

# Big unprocessed companies (Anduril, SpaceX, etc.)
print("\n--- LARGE UNPROCESSED COMPANIES (new, not applied) ---")
c.execute("""SELECT company, COUNT(*) as cnt,
             SUM(CASE WHEN fit_score >= 60 THEN 1 ELSE 0 END) as viable,
             SUM(CASE WHEN fit_score <= 1 THEN 1 ELSE 0 END) as unscored
             FROM jobs WHERE status='new'
             GROUP BY company HAVING cnt >= 20
             ORDER BY unscored DESC, cnt DESC LIMIT 25""")
print(f"  {'Company':<30} {'Total':>6} {'Viable':>7} {'Unscored':>9}")
for r in c.fetchall():
    print(f"  {r[0][:30]:<30} {r[1]:>6} {r[2]:>7} {r[3]:>9}")

# Failed apps that might be retryable
print("\n--- FAILED APPS BY SOURCE ---")
c.execute("SELECT source, COUNT(*) FROM jobs WHERE status='apply_failed' GROUP BY source ORDER BY COUNT(*) DESC")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Indeed jobs breakdown
print("\n--- INDEED JOBS (score>=60, new) - top 10 ---")
c.execute("SELECT company, title, fit_score FROM jobs WHERE source='indeed' AND fit_score >= 60 AND status='new' ORDER BY fit_score DESC LIMIT 10")
for r in c.fetchall():
    print(f"  {r[2]:.0f} | {r[0]} | {r[1][:50]}")
