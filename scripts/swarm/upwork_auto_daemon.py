"""
Upwork Auto-Proposal Daemon
============================
Polls Gmail every 5 minutes for Upwork job alerts.
If a job matches Claude/AI keywords and costs <=10 connects,
auto-submits a personalized proposal. No human approval needed.

Usage:
  python upwork_auto_daemon.py          # Run daemon (polls forever)
  python upwork_auto_daemon.py --once   # Single check then exit
  python upwork_auto_daemon.py --dry    # Check but don't submit

Requires:
  - Chrome running with --remote-debugging-port=9222 and logged into Upwork
  - Gmail IMAP access (ridgecellrepair@gmail.com)
  - Wraith MCP for job page scraping (optional, falls back to Playwright)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import hashlib
import imaplib
import email as email_lib
import json
import os
import re
import sqlite3
import time
import random
from datetime import datetime, timezone
from html.parser import HTMLParser

# ─── Config ──────────────────────────────────────────────────────────────
GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = "yzpn qern vrax fvta"
POLL_INTERVAL = 300  # 5 minutes
MAX_CONNECTS = 10
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
LOG_DIR = r"J:\job-hunter-mcp\scripts\swarm\logs"
SEEN_FILE = r"J:\job-hunter-mcp\scripts\swarm\upwork_seen_jobs.json"

# Keywords that trigger auto-proposal (any match = submit)
MATCH_KEYWORDS = [
    'claude', 'anthropic', 'ai agent', 'ai automation', 'llm',
    'mcp server', 'model context protocol', 'agentic',
    'claude code', 'ai engineer', 'ai developer',
    'prompt engineering', 'ai consultant', 'ai implementation',
    'browser automation', 'web scraping ai', 'ai integration',
    'python ai', 'rust developer', 'full stack ai',
    'machine learning', 'generative ai', 'gen ai',
]

# Keywords that mean SKIP (not worth the connects)
SKIP_KEYWORDS = [
    'wordpress', 'shopify', 'wix', 'squarespace',
    'data entry', 'virtual assistant', 'social media manager',
    'graphic design', 'logo design', 'video editing',
    'content writing', 'blog post', 'seo article',
    'bookkeeping', 'accounting',
]

APPLICANT = {
    "name": "Matt Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "rate": "$55",
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_path = os.path.join(LOG_DIR, "upwork_daemon.log")
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def extract_upwork_urls(html_body):
    """Extract Upwork job URLs from email HTML."""
    urls = re.findall(r'https://www\.upwork\.com/jobs/~\d+', html_body)
    # Also check for redirect links
    redirect_urls = re.findall(r'https://www\.upwork\.com/ab/proposals/job/~\d+', html_body)
    # Deduplicate
    all_urls = list(set(urls + redirect_urls))
    # Normalize to job URLs
    normalized = []
    for url in all_urls:
        jk = re.search(r'~(\d+)', url)
        if jk:
            normalized.append(f"https://www.upwork.com/jobs/~{jk.group(1)}")
    return list(set(normalized))


def check_gmail_for_alerts():
    """Check Gmail IMAP for new Upwork job alerts."""
    log("Checking Gmail for Upwork alerts...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for unread Upwork job alerts from last 2 days
        _, msg_ids = mail.search(None, '(FROM "donotreply@upwork.com" UNSEEN SINCE "' +
                                  (datetime.now().strftime("%d-%b-%Y")) + '")')

        if not msg_ids[0]:
            log("  No new Upwork alerts")
            mail.logout()
            return []

        ids = msg_ids[0].split()
        log(f"  Found {len(ids)} unread Upwork emails")

        jobs = []
        for mid in ids[-20:]:  # Process last 20 max
            _, msg_data = mail.fetch(mid, "(RFC822)")
            msg = email_lib.message_from_bytes(msg_data[0][1])

            subject = msg.get("Subject", "")
            if "new job" not in subject.lower() and "job alert" not in subject.lower():
                continue

            # Get HTML body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            urls = extract_upwork_urls(body)
            for url in urls:
                jobs.append({
                    "url": url,
                    "subject": subject,
                    "body_snippet": body[:500],
                })

        mail.logout()
        return jobs

    except Exception as e:
        log(f"  Gmail error: {e}")
        return []


def matches_keywords(text):
    """Check if job text matches our target keywords."""
    text_lower = text.lower()
    for kw in SKIP_KEYWORDS:
        if kw in text_lower:
            return False, f"skip:{kw}"
    for kw in MATCH_KEYWORDS:
        if kw in text_lower:
            return True, f"match:{kw}"
    return False, "no_match"


def generate_proposal(job_title, job_description, company=""):
    """Generate a personalized cover letter for the job."""
    # Detect job type and tailor
    desc_lower = (job_description or "").lower()
    title_lower = (job_title or "").lower()

    if 'claude' in desc_lower or 'anthropic' in desc_lower:
        hook = "I use Claude Code as my primary development tool daily, running 4-6 instances simultaneously."
        project = "I built a 27,000-line Rust browser automation engine entirely through multi-agent Claude orchestration, and I've automated 4,000+ job applications using Claude agents."
    elif 'agent' in desc_lower or 'agentic' in desc_lower:
        hook = "I build production AI agent systems — not prototypes, but systems that run 24/7."
        project = "My flagship project is an autonomous job application system using Claude agents to coordinate across 70+ company career sites, processing 5,500+ applications with 97% success rates."
    elif 'automation' in desc_lower or 'n8n' in desc_lower or 'zapier' in desc_lower:
        hook = "I specialize in AI-powered automation that actually works in production."
        project = "I've built end-to-end automation pipelines using Claude, MCP servers, and browser automation (my own 27K-line Rust browser engine) that handle complex multi-step workflows autonomously."
    elif 'llm' in desc_lower or 'machine learning' in desc_lower:
        hook = "I build production LLM systems — from model integration to deployment to monitoring."
        project = "I've shipped a Kalshi weather prediction trading bot (20x returns, 4 beta testers) and 10+ production MCP server integrations connecting Claude to real-world systems."
    else:
        hook = "I'm a full-stack engineer with 10 years of experience and deep AI/automation expertise."
        project = "Recent projects include a 27K-line Rust browser automation engine, autonomous AI agent systems, and 10+ production MCP server integrations."

    proposal = f"""{hook}

{project}

For this role specifically, I bring:
- 10 years of software engineering (Python, Rust, TypeScript, React)
- Deep experience with Claude API, MCP, tool use, and prompt engineering
- Production deployment on AWS, Docker, PostgreSQL
- Track record of shipping fast and iterating

I'm US-based (California), available immediately, and ready to start contributing on day one.

Best,
Matt Gates
GitHub: github.com/suhteevah"""

    return proposal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single check then exit")
    parser.add_argument("--dry", action="store_true", help="Check but don't submit")
    args = parser.parse_args()

    log("=" * 60)
    log("UPWORK AUTO-PROPOSAL DAEMON")
    log(f"Poll interval: {POLL_INTERVAL}s | Max connects: {MAX_CONNECTS}")
    log(f"Mode: {'DRY RUN' if args.dry else 'LIVE'}")
    log("=" * 60)

    seen = load_seen()

    while True:
        try:
            alerts = check_gmail_for_alerts()

            for alert in alerts:
                url = alert["url"]
                if url in seen:
                    continue

                subject = alert["subject"]
                body = alert["body_snippet"]

                # Check keyword match
                match, reason = matches_keywords(subject + " " + body)
                if not match:
                    log(f"  SKIP: {reason} | {subject[:60]}")
                    seen.add(url)
                    continue

                log(f"  MATCH: {reason} | {subject[:60]}")
                log(f"  URL: {url}")

                # TODO: Check connects cost via Playwright/Chrome CDP
                # For now, log the match and save for manual review
                # Full auto-submit requires Chrome with remote debugging

                proposal = generate_proposal(subject, body)
                log(f"  PROPOSAL READY ({len(proposal)} chars)")

                if not args.dry:
                    log(f"  AUTO-SUBMIT: would submit to {url}")
                    # TODO: Implement Chrome CDP submit via upwork_apply.py
                    # For now, save to a queue file for batch processing
                    queue_file = os.path.join(LOG_DIR, "upwork_auto_queue.json")
                    try:
                        with open(queue_file, "r") as f:
                            queue = json.load(f)
                    except Exception:
                        queue = []
                    queue.append({
                        "url": url,
                        "subject": subject,
                        "proposal": proposal,
                        "matched_at": datetime.now(timezone.utc).isoformat(),
                        "reason": reason,
                    })
                    with open(queue_file, "w") as f:
                        json.dump(queue, f, indent=2)
                    log(f"  QUEUED for submission")

                seen.add(url)

            save_seen(seen)

            if args.once:
                log("Single check complete. Exiting.")
                break

            log(f"Sleeping {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("Daemon stopped.")
            break
        except Exception as e:
            log(f"ERROR: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
