"""Database connection helper. All scripts import from here.
Supports PostgreSQL (primary) with SQLite fallback.
PostgreSQL has NO file locking — unlimited parallel workers."""
import os

# Set this to 'sqlite' to fall back to SQLite
DB_BACKEND = os.environ.get("JOB_HUNTER_DB", "postgres")

PG_DSN = "host=localhost port=5432 dbname=jobs user=postgres password=jobhunter"
SQLITE_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"


def get_db():
    """Get a database connection. Works with both Postgres and SQLite."""
    if DB_BACKEND == "postgres":
        import psycopg2
        conn = psycopg2.connect(PG_DSN)
        conn.autocommit = False
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_PATH, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
        conn.row_factory = sqlite3.Row
        return conn


def execute(conn, query, params=None):
    """Execute a query, handling placeholder differences (%s vs ?)."""
    if DB_BACKEND == "postgres":
        # Postgres uses %s placeholders
        query = query.replace("?", "%s")
        # Handle INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
        query = query.replace("INSERT OR IGNORE", "INSERT")
        if "INSERT" in query and "ON CONFLICT" not in query:
            query += " ON CONFLICT DO NOTHING"
    cur = conn.cursor()
    if params:
        cur.execute(query, params)
    else:
        cur.execute(query)
    return cur


def fetchone(conn, query, params=None):
    cur = execute(conn, query, params)
    return cur.fetchone()


def fetchall(conn, query, params=None):
    cur = execute(conn, query, params)
    return cur.fetchall()
