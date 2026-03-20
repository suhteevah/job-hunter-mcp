"""Check if any Wave 2 targets have already been applied to."""
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

WAVE2_URLS = [
    ("Anthropic", "Sr/Staff+ SWE Autonomous Agent Infra", "https://job-boards.greenhouse.io/anthropic/jobs/5065894008"),
    ("Anthropic", "Staff SWE Claude Dev Platform (FS)", "https://job-boards.greenhouse.io/anthropic/jobs/4561282008"),
    ("Scale AI", "Sr SWE Agentic Data Products", "https://job-boards.greenhouse.io/scaleai/jobs/4653827005"),
    ("Scale AI", "Sr/Staff ML Eng General Agents", "https://job-boards.greenhouse.io/scaleai/jobs/4658162005"),
    ("WITHIN", "AI Engineer", "https://job-boards.greenhouse.io/agencywithin/jobs/5056863007"),
    ("Anthropic", "Sr Staff SWE API", "https://job-boards.greenhouse.io/anthropic/jobs/5134895008"),
    ("Anthropic", "Staff SWE Claude Dev Platform (BE)", "https://job-boards.greenhouse.io/anthropic/jobs/4988878008"),
]

print("=== WAVE 2 DUPLICATE CHECK ===\n")
clean = []
for company, short_title, url in WAVE2_URLS:
    # Check by URL
    c.execute("SELECT status, applied_date FROM jobs WHERE url = ?", (url,))
    row = c.fetchone()
    if row and row[0] == 'applied':
        print(f"  ALREADY APPLIED: {short_title} @ {company} (applied {row[1]})")
    elif row:
        print(f"  IN DB (status={row[0]}): {short_title} @ {company} — OK to apply")
        clean.append(url)
    else:
        print(f"  NOT IN DB: {short_title} @ {company} — OK to apply")
        clean.append(url)

    # Also check by company name for any applied Anthropic/Scale jobs
    if company in ('Anthropic', 'Scale AI'):
        c.execute("SELECT title FROM jobs WHERE company = ? AND status = 'applied'", (company,))
        applied = c.fetchall()
        if applied:
            for a in applied:
                print(f"    (already applied to: {a[0]} @ {company})")

print(f"\n{len(clean)}/{len(WAVE2_URLS)} are safe to apply")

# Also check if we applied to any of these companies at all
print("\n=== ALL APPLIED JOBS BY COMPANY ===")
c.execute("""
    SELECT company, COUNT(*) FROM jobs WHERE status = 'applied'
    GROUP BY company ORDER BY COUNT(*) DESC
""")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} applied")
