"""Upwork job-alert email hunter.

Scans unread Upwork "New job" emails, keyword-scores each against Matt's
profile, and shells out to upwork_apply.py for passing jobs.

upwork_apply.py handles the final gate (<=10 connects, already-applied,
Chrome CDP at localhost:9222 must be logged into Upwork).

Tracks processed email IDs in a local JSON file to avoid re-work across runs.
"""
import imaplib
import email
import os
import re
import sys
import json
import time
import sqlite3
import subprocess
from email.header import decode_header
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "yzpn qern vrax fvta")

STATE_FILE = Path(r"C:\Users\Matt\.job-hunter-mcp\upwork_email_state.json")
DB = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
APPLY_SCRIPT = Path(__file__).parent / "upwork_apply.py"
PYTHON = Path(r"J:\job-hunter-mcp\.venv\Scripts\python.exe")

SCORE_THRESHOLD = 70  # default shortlist cutoff — tune via --min-score
SHORTLIST_MODE = "--apply" not in sys.argv  # default: print shortlist, do NOT apply

# Keywords that strongly indicate a good fit — each adds 15
POSITIVE = [
    "claude", "anthropic", "llm", "gpt", "openai", "mcp", "model context protocol",
    "ai agent", "agentic", "agent", "automation", "rag", "vector", "embedding",
    "python", "rust", "fastapi", "langchain", "rag pipeline", "ai engineer",
    "ai consultant", "prompt engineer", "ai implementation", "workflow automation",
    "chatbot backend", "ai sdk", "sdk integration",
]
# Keywords that disqualify — each subtracts 25
NEGATIVE = [
    "shopify", "wordpress", "wix", "webflow", "squarespace", "bubble", "no-code",
    "no code", "nocode", "php", "laravel", "magento", "drupal", "wordpres",
    "unity game", "unreal engine", "3d modeling", "video editor", "voice over",
    "figma designer", "ui designer only", "illustrator", "photoshop",
    "translator", "virtual assistant", "data entry", "content writer",
    "seo expert", "seo specialist", "social media manager", "tiktok",
]


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_msg_ids": [], "applied_urls": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def decode(s):
    if not s:
        return ""
    parts = decode_header(s)
    return "".join(
        (p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else p)
        for p, enc in parts
    )


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                except Exception:
                    continue
    else:
        try:
            return msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
        except Exception:
            return ""
    return ""


def score_email(subject: str, body: str) -> tuple[int, list[str]]:
    """Keyword score 0-100. Returns (score, matched_terms)."""
    text = (subject + " " + body).lower()
    score = 40  # baseline
    matched = []
    for kw in POSITIVE:
        if kw in text:
            score += 15
            matched.append(f"+{kw}")
    for kw in NEGATIVE:
        if kw in text:
            score -= 25
            matched.append(f"-{kw}")
    return max(0, min(100, score)), matched


def extract_job_url(body: str) -> str | None:
    m = re.search(r"https://www\.upwork\.com/jobs/~\w+", body)
    return m.group(0) if m else None


def log_to_db(url: str, title: str, score: int, status: str, reason: str):
    try:
        db = sqlite3.connect(DB)
        db.execute(
            "INSERT OR IGNORE INTO jobs (id, source, source_id, title, company, url, "
            "fit_score, fit_reason, status, date_found) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                url.split("~")[-1][:16],
                "upwork_email",
                url.split("~")[-1],
                title,
                "Upwork",
                url,
                score,
                reason,
                status,
                time.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"  DB log failed: {e}")


def main():
    state = load_state()
    processed = set(state["processed_msg_ids"])
    applied_urls = set(state["applied_urls"])

    mode = "SHORTLIST (read-only)" if SHORTLIST_MODE else "AUTO-APPLY"
    print(f"[upwork_email_hunt] mode={mode} threshold={SCORE_THRESHOLD}")
    print(f"[upwork_email_hunt] connecting to Gmail IMAP")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    # Search unread Upwork "New job" emails from last 3 days
    result, data = mail.search(
        None,
        '(UNSEEN FROM "donotreply@upwork.com" SUBJECT "New job")',
    )
    if result != "OK":
        print("  IMAP search failed")
        return
    ids = data[0].split()
    print(f"  {len(ids)} unread Upwork new-job emails")

    results = {"scanned": 0, "passed": 0, "applied": 0, "skipped": 0, "failed": 0}

    for mid in ids:
        msg_id_str = mid.decode()
        if msg_id_str in processed:
            continue

        try:
            res, raw = mail.fetch(mid, "(RFC822)")
            if res != "OK":
                continue
            msg = email.message_from_bytes(raw[0][1])
            subject = decode(msg["Subject"] or "")
            body = get_body(msg)
            results["scanned"] += 1

            title = re.sub(r"^(?:re:\s*)?new job:\s*", "", subject, flags=re.I).strip()
            url = extract_job_url(body)
            if not url:
                print(f"  [NO URL] {title[:70]}")
                processed.add(msg_id_str)
                continue

            if url in applied_urls:
                print(f"  [DUP] {title[:70]}")
                processed.add(msg_id_str)
                continue

            score, matched = score_email(subject, body)
            reason = " ".join(matched[:8])
            print(f"  [{score:3}] {title[:65]}")
            if matched:
                print(f"        {reason}")

            if score < SCORE_THRESHOLD:
                log_to_db(url, title, score, "skipped_low_score", reason)
                results["skipped"] += 1
                processed.add(msg_id_str)
                # Mark read so we don't rescan
                mail.store(mid, "+FLAGS", "\\Seen")
                continue

            results["passed"] += 1

            if SHORTLIST_MODE:
                # Shortlist mode: leave unread, log to DB only, do NOT apply
                log_to_db(url, title, score, "shortlist", reason)
                # Extract budget/type hints from body for context
                budget = ""
                for pat in (r"\$[\d,]+(?:\s*-\s*\$[\d,]+)?", r"\d+\s*(?:-\s*\d+)?\s*hr/wk", r"Hourly|Fixed\s*price"):
                    m = re.search(pat, body)
                    if m:
                        budget += " | " + m.group(0)
                print(f"        BUDGET/TYPE:{budget[:80]}")
                print(f"        URL: {url}")
                # Shortlist mode: do NOT mark processed/seen — stay visible for next run
                continue

            log_to_db(url, title, score, "applying", reason)

            # Shell out to upwork_apply.py
            print(f"        -> upwork_apply.py {url}")
            try:
                proc = subprocess.run(
                    [str(PYTHON), str(APPLY_SCRIPT), url],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                out = (proc.stdout or "") + (proc.stderr or "")
                print("        " + out.strip().replace("\n", "\n        ")[:500])
                applied_ok = (
                    proc.returncode == 0
                    and ("submitted" in out.lower() or "already applied" in out.lower())
                )
                if applied_ok:
                    results["applied"] += 1
                    applied_urls.add(url)
                    log_to_db(url, title, score, "applied", reason)
                else:
                    results["failed"] += 1
                    log_to_db(url, title, score, "apply_failed", reason)
            except subprocess.TimeoutExpired:
                print("        TIMEOUT")
                results["failed"] += 1
                log_to_db(url, title, score, "apply_failed", "timeout")

            mail.store(mid, "+FLAGS", "\\Seen")
            processed.add(msg_id_str)
            time.sleep(3)

        except Exception as e:
            print(f"  ERROR {msg_id_str}: {e}")
            continue

    mail.logout()

    state["processed_msg_ids"] = list(processed)[-500:]  # cap
    state["applied_urls"] = list(applied_urls)[-500:]
    save_state(state)

    print(f"\n[upwork_email_hunt] {results}")


if __name__ == "__main__":
    main()
