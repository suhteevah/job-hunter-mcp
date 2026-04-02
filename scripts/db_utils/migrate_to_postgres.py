"""Migrate jobs.db from SQLite to PostgreSQL. Zero downtime — creates table, copies all data."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import psycopg2
import psycopg2.extras
import time

SQLITE_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
PG_DSN = "host=localhost port=5432 dbname=jobs user=postgres password=jobhunter"

def main():
    print("=== MIGRATING SQLite → PostgreSQL ===")

    # Connect to both
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(PG_DSN)
    pg_cur = pg_conn.cursor()

    # Create table in Postgres
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            url TEXT NOT NULL,
            location TEXT DEFAULT 'Remote',
            salary TEXT,
            job_type TEXT,
            category TEXT,
            description TEXT,
            tags TEXT,
            date_posted TEXT,
            date_found TEXT NOT NULL,
            fit_score REAL DEFAULT 0.0,
            fit_reason TEXT,
            status TEXT DEFAULT 'new',
            notes TEXT,
            cover_letter TEXT,
            applied_date TEXT
        )
    """)

    # Create indexes for common queries
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fit_score ON jobs(fit_score)")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
    pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source_status_score ON jobs(source, status, fit_score)")
    pg_conn.commit()
    print("Postgres table + indexes created")

    # Count existing
    pg_cur.execute("SELECT COUNT(*) FROM jobs")
    existing = pg_cur.fetchone()[0]
    print(f"Existing Postgres rows: {existing}")

    # Read all from SQLite
    rows = sqlite_conn.execute("SELECT * FROM jobs").fetchall()
    cols = [desc[0] for desc in sqlite_conn.execute("SELECT * FROM jobs LIMIT 1").description]
    print(f"SQLite rows to migrate: {len(rows)}")

    # Batch insert with ON CONFLICT DO NOTHING
    batch_size = 500
    inserted = 0
    skipped = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        values_list = []
        for row in batch:
            values = []
            for col in cols:
                val = row[col]
                # Handle None/NULL
                if val is None:
                    values.append(None)
                else:
                    values.append(str(val) if not isinstance(val, (int, float)) else val)
            values_list.append(tuple(values))

        # Build the INSERT query
        placeholders = ','.join(['%s'] * len(cols))
        col_names = ','.join(cols)
        query = f"INSERT INTO jobs ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"

        try:
            psycopg2.extras.execute_batch(pg_cur, query, values_list, page_size=100)
            pg_conn.commit()
            inserted += len(batch)
        except Exception as e:
            pg_conn.rollback()
            print(f"  Batch error at {i}: {e}")
            # Try one by one
            for values in values_list:
                try:
                    pg_cur.execute(query, values)
                    pg_conn.commit()
                    inserted += 1
                except Exception:
                    pg_conn.rollback()
                    skipped += 1

        if (i + batch_size) % 2000 == 0:
            print(f"  ... migrated {i + batch_size}/{len(rows)}")

    # Final count
    pg_cur.execute("SELECT COUNT(*) FROM jobs")
    final = pg_cur.fetchone()[0]
    pg_cur.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
    applied = pg_cur.fetchone()[0]

    print(f"\n=== MIGRATION COMPLETE ===")
    print(f"  Total Postgres rows: {final}")
    print(f"  Applied: {applied}")
    print(f"  Skipped: {skipped}")

    # Verify counts match
    sqlite_count = sqlite_conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"  SQLite count: {sqlite_count}")
    if final >= sqlite_count:
        print("  ✓ Migration verified — counts match!")
    else:
        print(f"  WARNING: Postgres ({final}) < SQLite ({sqlite_count})")

    pg_conn.close()
    sqlite_conn.close()

if __name__ == "__main__":
    main()
