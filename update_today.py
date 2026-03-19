import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()

# Today's confirmed submissions
apps = [
    ("Glass Health", "Founding AI/Data Engineer", "lever"),
    ("Atmosera", "Collaborative Engineer GitHub Copilot", "lever"),
    ("Censys", "Sr SWE AI/LLM", "greenhouse"),
    ("NearForm", "Sr AI Python SWE", "greenhouse"),
    ("Covey", "Sr SWE Remote AI", "greenhouse"),
    ("Qwiet AI", "Sr SWE Remote", "greenhouse"),
    ("Collectly", "Sr SWE USA Remote", "lever"),
    ("Upbound", "Sr SWE REMOTE", "greenhouse"),
    ("Openly", "Sr Backend Engineer Remote US", "greenhouse"),
    ("Alvys", "Sr SWE", "greenhouse"),
    ("RapidSOS", "Sr SWE Full-Stack", "greenhouse"),
]

for company, title, source in apps:
    c.execute("SELECT id FROM jobs WHERE company=? AND title LIKE ?", (company, f'%{title.split()[0]}%'))
    row = c.fetchone()
    if row:
        c.execute("UPDATE jobs SET status='applied', applied_date='2026-03-18' WHERE id=?", (row[0],))
        print(f"  Updated: {title} @ {company}")
    else:
        c.execute("""INSERT INTO jobs (source, title, company, url, status, applied_date, date_found)
                     VALUES (?, ?, ?, ?, 'applied', '2026-03-18', '2026-03-18')""",
                  (source, title, company, f'applied-via-chrome-{source}'))
        print(f"  Inserted: {title} @ {company}")

conn.commit()
c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
print('\n=== UPDATED COUNTS ===')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')
conn.close()
