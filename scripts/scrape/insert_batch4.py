import sqlite3, os, sys, uuid
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
now = datetime.now().isoformat()

jobs = [
    ('Growth Engineer', 'Warp'),
    ('Product Engineer', 'Warp'),
    ('Engineering Manager AI Quality', 'Harvey'),
    ('Strategic Solutions Engineer', 'Decagon'),
    ('Principal SWE Money Infrastructure', 'Replit'),
    ('Staff TPM AI/Agent Systems', 'Replit'),
    ('Forward Deployed Engineer Infra', 'Cohere'),
    ('Data Scientist', 'Sleeper'),
    ('Staff SWE SRE ($206K Remote)', 'Rula'),
    ('Staff SWE Patient Onboarding', 'Rula'),
    ('Sr Security Engineer', 'Rula'),
    ('Sr SWE Backend/Python (USA Remote)', 'Close'),
    ('Sr SWE Frontend/React (USA Remote)', 'Close'),
    ('Data Infrastructure Engineer', 'Alljoined'),
    ('SWE Agent', 'Sierra'),
    ('Sales Engineer', 'Sierra'),
]

count = 0
for title, company in jobs:
    jid = str(uuid.uuid4())[:16]
    try:
        c.execute("""INSERT INTO jobs (id, title, company, url, source, fit_score, status, notes, date_found)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (jid, title, company, 'batch-applied-v4', 'wraith+playwright', 80, 'applied', 'Applied 2026-03-18', now))
        count += 1
    except: pass

db.commit()
print(f'Inserted {count} more jobs')
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
total = c.fetchone()[0]
print(f'Total applied in DB: {total}')
print(f'\nCompanies applied to:')
c.execute("SELECT DISTINCT company FROM jobs WHERE status = 'applied' ORDER BY company")
for r in c.fetchall():
    print(f'  - {r[0]}')
db.close()
