"""Score all 3,433 unscored/low-score jobs using rowid-based updates."""
import sys, sqlite3, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HIGH_MATCH = {
    'ai engineer': 30, 'ml engineer': 30, 'machine learning engineer': 30,
    'agentic': 35, 'llm': 30, 'generative ai': 30, 'gen ai': 30,
    'ai/ml': 30, 'applied ai': 30, 'ai platform': 25,
    'automation engineer': 20, 'devops': 15, 'infrastructure': 15,
    'full stack': 15, 'fullstack': 15, 'backend': 15, 'python': 20,
    'software engineer': 10, 'sre': 10, 'platform engineer': 15,
    'data engineer': 10, 'senior': 5, 'staff': 5, 'principal': 5,
    'rust': 15, 'golang': 10, 'typescript': 10, 'react': 10,
    'cloud': 10, 'aws': 10, 'kubernetes': 10, 'docker': 10,
    'systems engineer': 10, 'embedded': 10, 'firmware': 10,
    'security engineer': 10, 'network engineer': 5,
}
LOW_MATCH = {
    'manager': -20, 'director': -25, 'sales': -30, 'designer': -25,
    'product manager': -30, 'recruiter': -30, 'coordinator': -25,
    'account executive': -35, 'account manager': -30,
    'marketing': -25, 'legal counsel': -25, 'attorney': -25,
    'grafikdesigner': -40, 'vertrieb': -40,
    'werkstudent': -15, 'intern': -20, 'junior': -5,
    'content': -15, 'writer': -15, 'copywriter': -25,
    'analyst': -10, 'accountant': -25, 'finance': -20,
    'hr ': -25, 'people': -20, 'talent acquisition': -25,
}
REMOTE_KEYWORDS = {'remote', 'anywhere', 'distributed', 'usa', 'us-based'}

def score_job(title, location, description):
    title_lower = (title or '').lower()
    loc_lower = (location or '').lower()
    desc_lower = (description or '').lower()[:500]
    base = 50
    for kw, boost in HIGH_MATCH.items():
        if kw in title_lower or kw in desc_lower:
            base += boost
    for kw, penalty in LOW_MATCH.items():
        if kw in title_lower:
            base += penalty
    if any(kw in loc_lower or kw in title_lower for kw in REMOTE_KEYWORDS):
        base += 10
    return max(2, min(100, base))  # min 2 so they don't get re-scored

db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA busy_timeout=60000')

rows = db.execute('SELECT rowid, title, company, location, description FROM jobs WHERE fit_score <= 1 AND status = \'new\'').fetchall()
print(f"Scoring {len(rows)} jobs...")

high_count = 0
batch = []
for i, (rowid, title, company, location, desc) in enumerate(rows):
    score = score_job(title, location, desc)
    reason = f"auto-scored:{score}"
    batch.append((score, reason, rowid))
    if score >= 60:
        high_count += 1
        if score >= 80:
            print(f"  {score:3d} *** {company}: {title[:60]}")

    # Commit in batches of 200
    if len(batch) >= 200:
        for s, r, rid in batch:
            db.execute('UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE rowid = ?', (s, r, rid))
        db.commit()
        print(f"  ... committed {i+1}/{len(rows)} ({high_count} viable so far)")
        batch = []

# Final batch
if batch:
    for s, r, rid in batch:
        db.execute('UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE rowid = ?', (s, r, rid))
    db.commit()

print(f"\nDone. Scored {len(rows)} jobs. High-score (>=60): {high_count}")

# Show results
ready = db.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
print(f"\nReady to apply by source:")
total = 0
for r in ready:
    print(f"  {r[0]}: {r[1]}")
    total += r[1]
print(f"  TOTAL: {total}")

# Top companies
print(f"\nTop viable companies (score>=60, new):")
top = db.execute("""SELECT company, COUNT(*) as cnt FROM jobs
                    WHERE fit_score >= 60 AND status='new'
                    GROUP BY company HAVING cnt >= 3
                    ORDER BY cnt DESC LIMIT 20""").fetchall()
for r in top:
    print(f"  {r[0]}: {r[1]}")
