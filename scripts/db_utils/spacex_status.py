import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

# SpaceX breakdown
c.execute("SELECT status, COUNT(*) FROM jobs WHERE company='SpaceX' GROUP BY status ORDER BY COUNT(*) DESC")
print("SpaceX by status:")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

c.execute("SELECT COUNT(*) FROM jobs WHERE company='SpaceX' AND fit_score >= 60 AND status='new'")
print(f"\nSpaceX ready to apply (score>=60, new): {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM jobs WHERE company='SpaceX' AND fit_score <= 1")
print(f"SpaceX unscored: {c.fetchone()[0]}")

# Top SpaceX scored jobs
c.execute("SELECT title, fit_score, status FROM jobs WHERE company='SpaceX' AND fit_score >= 60 ORDER BY fit_score DESC LIMIT 15")
print("\nSpaceX top scored:")
for r in c.fetchall():
    print(f"  {r[1]:.0f} | {r[2]} | {r[0][:60]}")

# What other platforms aren't covered
print("\n=== UNCOVERED PLATFORMS ===")
print("Workday: Raytheon, Lockheed, Boeing, Northrop, L3Harris, BAE, SAIC, Leidos")
print("Taleo: Some defense contractors")
print("iCIMS: Some enterprise companies")
print("Wellfound (AngelList): Startup jobs - has public API")
print("LinkedIn: Needs auth + anti-bot (hard)")
print("USAJobs: Federal government jobs - has public API")

# Check if any Anduril are still unapplied
c.execute("SELECT COUNT(*) FROM jobs WHERE company='Anduril' AND fit_score >= 60 AND status='new'")
print(f"\nAnduril ready to apply: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM jobs WHERE company='Anduril' AND status='applied'")
print(f"Anduril applied: {c.fetchone()[0]}")
