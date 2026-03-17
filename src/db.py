"""
Job Hunter MCP - Database Layer
SQLite-backed storage for jobs, applications, email drafts, and audit log.
"""
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from src.config import DB_PATH

logger = logging.getLogger("job_hunter.db")


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    logger.info(f"Initializing database at {DB_PATH}")
    conn = get_conn()
    conn.executescript("""
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
            applied_date TEXT,
            UNIQUE(source, source_id)
        );

        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            email_type TEXT NOT NULL,
            to_address TEXT,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            gmail_thread_id TEXT,
            gmail_message_id TEXT,
            created_at TEXT NOT NULL,
            sent_at TEXT,
            approved_at TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS gmail_threads (
            thread_id TEXT PRIMARY KEY,
            job_id TEXT,
            subject TEXT,
            from_address TEXT,
            last_message_date TEXT,
            status TEXT DEFAULT 'unread',
            category TEXT,
            summary TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            source TEXT DEFAULT 'system'
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            sources TEXT NOT NULL,
            result_count INTEGER DEFAULT 0,
            new_jobs INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            service TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            added_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scheduler_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_fit ON jobs(fit_score DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_date ON jobs(date_found DESC);
        CREATE INDEX IF NOT EXISTS idx_email_status ON email_queue(status);
        CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp DESC);
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# JOBS
# ============================================================
def upsert_job(job: dict) -> bool:
    """Insert or skip a job. Returns True if new."""
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM jobs WHERE source=? AND source_id=?",
            (job["source"], job.get("source_id", job["id"]))
        ).fetchone()
        if existing:
            return False

        conn.execute("""
            INSERT INTO jobs (id, source, source_id, title, company, url, location,
                            salary, job_type, category, description, tags,
                            date_posted, date_found, fit_score, fit_reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
        """, (
            job["id"], job["source"], job.get("source_id", job["id"]),
            job["title"], job["company"], job["url"],
            job.get("location", "Remote"), job.get("salary"),
            job.get("job_type"), job.get("category"),
            job.get("description"), json.dumps(job.get("tags", [])),
            job.get("date_posted"), _now(),
            job.get("fit_score", 0.0), job.get("fit_reason"),
        ))
        conn.commit()
        logger.info(f"NEW JOB: [{job['source']}] {job['title']} @ {job['company']} (score={job.get('fit_score', 0)})")
        return True
    except Exception as e:
        logger.error(f"upsert_job error: {e}")
        return False
    finally:
        conn.close()


def update_job(job_id: str, **kwargs) -> bool:
    conn = get_conn()
    try:
        sets = []
        params = []
        for k, v in kwargs.items():
            if k in ("status", "notes", "cover_letter", "applied_date", "fit_score", "fit_reason"):
                sets.append(f"{k}=?")
                params.append(v)
        if not sets:
            return False
        if "status" in kwargs and kwargs["status"] == "applied" and "applied_date" not in kwargs:
            sets.append("applied_date=?")
            params.append(_now())
        params.append(job_id)
        cursor = conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", params)
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Job {job_id} updated: {kwargs}")
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_jobs(status=None, source=None, min_score=0.0, limit=50, offset=0) -> list:
    conn = get_conn()
    try:
        conds = ["fit_score >= ?"]
        params: list = [min_score]
        if status:
            conds.append("status=?")
            params.append(status)
        if source:
            conds.append("source=?")
            params.append(source)
        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE {' AND '.join(conds)} ORDER BY fit_score DESC, date_found DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[dict]:
    conn = get_conn()
    try:
        r = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_conn()
    try:
        stats = {}
        for s in ("new", "saved", "applied", "interviewing", "rejected", "offer"):
            stats[s] = conn.execute("SELECT COUNT(*) FROM jobs WHERE status=?", (s,)).fetchone()[0]
        stats["total"] = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        stats["avg_score"] = round(conn.execute(
            "SELECT COALESCE(AVG(fit_score), 0) FROM jobs WHERE fit_score > 0"
        ).fetchone()[0], 1)
        stats["top_score"] = conn.execute(
            "SELECT COALESCE(MAX(fit_score), 0) FROM jobs"
        ).fetchone()[0]
        sources = conn.execute("SELECT source, COUNT(*) c FROM jobs GROUP BY source").fetchall()
        stats["by_source"] = {r["source"]: r["c"] for r in sources}
        stats["pending_emails"] = conn.execute(
            "SELECT COUNT(*) FROM email_queue WHERE status='draft'"
        ).fetchone()[0]
        stats["sent_emails"] = conn.execute(
            "SELECT COUNT(*) FROM email_queue WHERE status='sent'"
        ).fetchone()[0]
        return stats
    finally:
        conn.close()


# ============================================================
# EMAIL QUEUE
# ============================================================
def queue_email(job_id: Optional[str], email_type: str, to_address: str,
                subject: str, body: str, thread_id: Optional[str] = None) -> int:
    conn = get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO email_queue (job_id, email_type, to_address, subject, body,
                                    status, gmail_thread_id, created_at)
            VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)
        """, (job_id, email_type, to_address, subject, body, thread_id, _now()))
        conn.commit()
        eid = cursor.lastrowid
        logger.info(f"EMAIL QUEUED #{eid}: [{email_type}] {subject} -> {to_address}")
        return eid
    finally:
        conn.close()


def get_email_queue(status="draft", limit=20) -> list:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM email_queue WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def approve_email(email_id: int) -> bool:
    conn = get_conn()
    try:
        cursor = conn.execute(
            "UPDATE email_queue SET status='approved', approved_at=? WHERE id=? AND status='draft'",
            (_now(), email_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def mark_email_sent(email_id: int, message_id: str = None) -> bool:
    conn = get_conn()
    try:
        cursor = conn.execute(
            "UPDATE email_queue SET status='sent', sent_at=?, gmail_message_id=? WHERE id=?",
            (_now(), message_id, email_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================
# GMAIL THREADS
# ============================================================
def upsert_gmail_thread(thread: dict) -> bool:
    conn = get_conn()
    try:
        existing = conn.execute("SELECT thread_id FROM gmail_threads WHERE thread_id=?",
                               (thread["thread_id"],)).fetchone()
        if existing:
            conn.execute("""
                UPDATE gmail_threads SET last_message_date=?, status=?, summary=?
                WHERE thread_id=?
            """, (thread.get("last_message_date"), thread.get("status", "unread"),
                  thread.get("summary"), thread["thread_id"]))
        else:
            conn.execute("""
                INSERT INTO gmail_threads (thread_id, job_id, subject, from_address,
                                          last_message_date, status, category, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (thread["thread_id"], thread.get("job_id"), thread.get("subject"),
                  thread.get("from_address"), thread.get("last_message_date"),
                  thread.get("status", "unread"), thread.get("category"),
                  thread.get("summary")))
        conn.commit()
        return not existing
    finally:
        conn.close()


# ============================================================
# AUDIT LOG
# ============================================================
def audit(action: str, details: str = "", source: str = "system"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO audit_log (timestamp, action, details, source) VALUES (?, ?, ?, ?)",
            (_now(), action, details, source)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    finally:
        conn.close()


def get_audit_log(limit=50) -> list:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# SCHEDULER STATE
# ============================================================
def set_state(key: str, value: str):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO scheduler_state (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, _now())
        )
        conn.commit()
    finally:
        conn.close()


def get_state(key: str) -> Optional[str]:
    conn = get_conn()
    try:
        r = conn.execute("SELECT value FROM scheduler_state WHERE key=?", (key,)).fetchone()
        return r["value"] if r else None
    finally:
        conn.close()


# ============================================================
# API KEYS
# ============================================================
def save_api_key(service: str, key: str):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO api_keys (service, api_key, added_date) VALUES (?, ?, ?)",
            (service, key, _now())
        )
        conn.commit()
        logger.info(f"API key saved: {service}")
    finally:
        conn.close()


def get_api_key(service: str) -> Optional[str]:
    conn = get_conn()
    try:
        r = conn.execute("SELECT api_key FROM api_keys WHERE service=?", (service,)).fetchone()
        return r["api_key"] if r else None
    finally:
        conn.close()


# ============================================================
# SEARCH HISTORY
# ============================================================
def log_search(query: str, sources: list, result_count: int, new_jobs: int):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO search_history (query, sources, result_count, new_jobs, timestamp) VALUES (?, ?, ?, ?, ?)",
            (query, json.dumps(sources), result_count, new_jobs, _now())
        )
        conn.commit()
    finally:
        conn.close()


# Initialize
init_db()
