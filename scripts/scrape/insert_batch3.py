import sqlite3, os, sys, uuid
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
now = datetime.now().isoformat()

jobs = [
    ('Data Scientist', 'Sleeper'),
    ('Staff SWE SRE (Remote $206K)', 'Rula'),
    ('Staff SWE Patient Onboarding (Remote)', 'Rula'),
    ('Sr Security Engineer (Remote)', 'Rula'),
    ('Sr SWE Backend/Python (USA Remote)', 'Close'),
    ('Sr SWE Frontend/React (USA Remote)', 'Close'),
    ('Data Infrastructure Engineer', 'Alljoined'),
    ('SWE Agent', 'Sierra'),
    ('Sales Engineer', 'Sierra'),
    ('Engineering Manager AI Quality', 'Harvey'),
    ('Strategic Solutions Engineer East', 'Decagon'),
    ('Strategic Solutions Engineer West', 'Decagon'),
    ('Principal SWE Money Infrastructure', 'Replit'),
    ('Staff TPM AI/Agent Systems', 'Replit'),
    ('Forward Deployed Engineer Infra', 'Cohere'),
    ('Cloud Infrastructure Engineer', 'Farsight AI'),
]

count = 0
for title, company in jobs:
    jid = str(uuid.uuid4())[:16]
    try:
        c.execute("""INSERT INTO jobs (id, title, company, url, source, fit_score, status, notes, date_found)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (jid, title, company, 'batch-applied', 'wraith+playwright', 80, 'applied', 'Applied 2026-03-18', now))
        count += 1
    except: pass

db.commit()
print(f'Inserted {count} more jobs')
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
print(f'Total applied: {c.fetchone()[0]}')
db.close()
