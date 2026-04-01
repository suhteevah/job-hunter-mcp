import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HIGH_MATCH = {
    'ai engineer': 30, 'ml engineer': 30, 'machine learning engineer': 30,
    'agentic': 35, 'llm': 30, 'generative ai': 30, 'gen ai': 30,
    'ai/ml': 30, 'applied ai': 30, 'ai platform': 25,
    'automation engineer': 20, 'devops': 15, 'infrastructure': 15,
    'full stack': 15, 'backend': 15, 'python': 20,
    'software engineer': 10, 'sre': 10, 'platform engineer': 15,
    'data engineer': 10, 'senior': 5, 'staff': 5,
}
LOW_MATCH = {
    'manager': -20, 'director': -25, 'sales': -30, 'designer': -25,
    'product manager': -30, 'grafikdesigner': -40, 'vertrieb': -40,
    'werkstudent': -15, 'intern': -20, 'junior': -5,
}
REMOTE_KEYWORDS = {'remote', 'anywhere', 'distributed'}

def score_job(title, location, description):
    title_lower = (title or '').lower()
    loc_lower = (location or '').lower()
    desc_lower = (description or '').lower()
    base = 50
    for kw, boost in HIGH_MATCH.items():
        if kw in title_lower or kw in desc_lower[:200]:
            base += boost
    for kw, penalty in LOW_MATCH.items():
        if kw in title_lower:
            base += penalty
    if any(kw in loc_lower or kw in title_lower for kw in REMOTE_KEYWORDS):
        base += 10
    return max(1, min(100, base))  # min 1 so they don't get re-scored

db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA busy_timeout=60000')

# Use rowid for the update
rows = db.execute('SELECT rowid, title, company, location, description FROM jobs WHERE fit_score = 0').fetchall()
print(f"Scoring {len(rows)} jobs using rowid...")

high_count = 0
for rowid, title, company, location, desc in rows:
    score = score_job(title, location, desc)
    reason = f"auto-scored:{score}"
    db.execute('UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE rowid = ?', (score, reason, rowid))
    if score >= 60:
        high_count += 1
        print(f"  {score:3d} *** {company}: {title[:55]}")

db.commit()

# Also fix NULL ids — generate them from source + url
null_ids = db.execute("SELECT rowid, source, url FROM jobs WHERE id IS NULL").fetchall()
if null_ids:
    print(f"\nFixing {len(null_ids)} NULL IDs...")
    import hashlib
    for rowid, source, url in null_ids:
        new_id = hashlib.md5(f"{source}:{url}".encode()).hexdigest()[:16]
        db.execute('UPDATE jobs SET id = ? WHERE rowid = ?', (new_id, rowid))
    db.commit()
    print("IDs fixed.")

# Verify
remaining = db.execute('SELECT COUNT(*) FROM jobs WHERE fit_score = 0 OR fit_score IS NULL').fetchone()[0]
print(f"\nRemaining unscored: {remaining}")

ready = db.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
print(f"\nReady to apply by source:")
total = 0
for r in ready:
    print(f"  {r[0]}: {r[1]}")
    total += r[1]
print(f"  TOTAL: {total}")
