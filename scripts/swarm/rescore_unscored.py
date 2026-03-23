"""Re-score unscored/low-scored jobs using the real scoring engine."""
import sys, sqlite3
sys.path.insert(0, r"J:\job-hunter-mcp")
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.apis import score_fit

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

def main():
    db = sqlite3.connect(DB_PATH)
    # Get jobs that were auto-scored by the quick script (fit_reason starts with 'auto-scored')
    # or have fit_score = 0
    rows = db.execute('''
        SELECT id, title, company, description, fit_score, fit_reason
        FROM jobs
        WHERE fit_reason LIKE 'auto-scored%' OR fit_score = 0
    ''').fetchall()

    print(f"Re-scoring {len(rows)} jobs with real scorer...")
    upgraded = 0
    for jid, title, company, desc, old_score, old_reason in rows:
        desc = desc or ""
        new_score, new_reason = score_fit(title, desc)
        if new_score != old_score:
            db.execute('UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE id = ?',
                       (new_score, new_reason, jid))
            marker = " ***" if new_score >= 85 else ""
            if new_score != old_score:
                print(f"  {old_score:5.1f} -> {new_score:5.1f}{marker} | {title[:50]} @ {company}")
                upgraded += 1

    db.commit()
    print(f"\nRe-scored {upgraded} jobs")

    # Show new top scores
    print("\n=== NEW 85+ JOBS ===")
    for r in db.execute('''
        SELECT fit_score, title, company, status, fit_reason
        FROM jobs WHERE fit_score >= 85
        ORDER BY fit_score DESC
    ''').fetchall():
        print(f"  {r[0]}pts [{r[3]}] {r[1][:55]} @ {r[2]}")
        print(f"    reason: {r[4][:80]}")

if __name__ == "__main__":
    main()
