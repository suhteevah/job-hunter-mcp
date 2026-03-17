"""
Job Hunter MCP - Gmail Integration
====================================
Full email automation using Gmail app password:
  - SMTP: Send approved emails from the queue
  - IMAP: Monitor inbox for recruiter replies
  - Auto-link: Match incoming emails to tracked jobs
  - Auto-draft: Generate reply drafts for approval

Reads credentials from secrets.json in project root.
"""
import email
import email.mime.text
import email.mime.multipart
import imaplib
import json
import logging
import re
import smtplib
import ssl
from datetime import datetime, timezone, timedelta
from email.header import decode_header
from pathlib import Path
from typing import Optional

from src import db
from src.config import GMAIL, EMAIL_TEMPLATES, USER_PROFILE, DATA_DIR

logger = logging.getLogger("job_hunter.gmail")

# ============================================================
# SECRETS LOADING
# ============================================================
SECRETS_FILE = Path(__file__).parent.parent / "secrets.json"

_cached_secrets = None

def _load_secrets() -> dict:
    """Load Gmail credentials from secrets.json."""
    global _cached_secrets
    if _cached_secrets:
        return _cached_secrets

    if not SECRETS_FILE.exists():
        logger.error(f"Secrets file not found: {SECRETS_FILE}")
        logger.error("Create secrets.json with: {\"gmail_address\": \"you@gmail.com\", \"gmail_app_password\": \"xxxx xxxx xxxx xxxx\"}")
        raise FileNotFoundError(f"Missing {SECRETS_FILE}")

    try:
        with open(SECRETS_FILE) as f:
            secrets = json.load(f)

        required = ["gmail_address", "gmail_app_password"]
        missing = [k for k in required if k not in secrets]
        if missing:
            raise ValueError(f"Missing keys in secrets.json: {missing}")

        _cached_secrets = secrets
        logger.info(f"Secrets loaded for: {secrets['gmail_address']}")
        return secrets
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in secrets.json: {e}")
        raise


def get_gmail_address() -> str:
    return _load_secrets()["gmail_address"]


def get_app_password() -> str:
    return _load_secrets()["gmail_app_password"]


# ============================================================
# SMTP - SENDING EMAILS
# ============================================================
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(to_address: str, subject: str, body: str,
               reply_to_message_id: Optional[str] = None,
               thread_id: Optional[str] = None) -> dict:
    """Send an email via Gmail SMTP with app password.

    Returns: {"success": bool, "message_id": str, "error": str}
    """
    logger.info(f"[SMTP] Sending email to: {to_address}")
    logger.info(f"[SMTP] Subject: {subject}")
    logger.debug(f"[SMTP] Body length: {len(body)} chars")

    try:
        secrets = _load_secrets()
        from_address = secrets["gmail_address"]
        app_password = secrets["gmail_app_password"]

        # Build message
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["From"] = f"{USER_PROFILE['name']} <{from_address}>"
        msg["To"] = to_address
        msg["Subject"] = subject

        # Thread headers for Gmail threading
        if reply_to_message_id:
            msg["In-Reply-To"] = reply_to_message_id
            msg["References"] = reply_to_message_id
            logger.debug(f"[SMTP] Threading reply to: {reply_to_message_id}")

        # Plain text body
        text_part = email.mime.text.MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        # HTML version (basic formatting)
        html_body = body.replace("\n", "<br>\n")
        html_part = email.mime.text.MIMEText(
            f"<html><body style='font-family: Arial, sans-serif; line-height: 1.6;'>"
            f"{html_body}</body></html>",
            "html", "utf-8"
        )
        msg.attach(html_part)

        # Connect and send
        logger.debug(f"[SMTP] Connecting to {SMTP_HOST}:{SMTP_PORT}...")
        context = ssl.create_default_context()

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.set_debuglevel(0)  # Set to 1 for raw SMTP debug
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            logger.debug("[SMTP] TLS established, authenticating...")
            server.login(from_address, app_password)
            logger.debug("[SMTP] Authenticated, sending...")
            server.sendmail(from_address, [to_address], msg.as_string())

        message_id = msg["Message-ID"] or ""
        logger.info(f"[SMTP] EMAIL SENT successfully to {to_address} (ID: {message_id})")

        return {"success": True, "message_id": message_id, "error": ""}

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[SMTP] Authentication failed: {e}")
        logger.error("[SMTP] Check your app password in secrets.json")
        return {"success": False, "message_id": "", "error": f"Auth failed: {e}"}
    except smtplib.SMTPException as e:
        logger.error(f"[SMTP] SMTP error: {e}")
        return {"success": False, "message_id": "", "error": f"SMTP error: {e}"}
    except Exception as e:
        logger.error(f"[SMTP] Unexpected error: {e}")
        return {"success": False, "message_id": "", "error": str(e)}


def process_approved_emails() -> dict:
    """Send all approved emails from the queue.

    Returns: {"sent": int, "failed": int, "errors": list}
    """
    logger.info("[SMTP] Processing approved email queue...")
    approved = db.get_email_queue("approved")

    if not approved:
        logger.info("[SMTP] No approved emails to send.")
        return {"sent": 0, "failed": 0, "errors": []}

    logger.info(f"[SMTP] Found {len(approved)} approved emails")
    sent = 0
    failed = 0
    errors = []

    for em in approved:
        logger.info(f"[SMTP] Processing email #{em['id']}: {em['email_type']} -> {em['to_address']}")

        result = send_email(
            to_address=em["to_address"],
            subject=em["subject"],
            body=em["body"],
            reply_to_message_id=em.get("gmail_message_id"),
            thread_id=em.get("gmail_thread_id"),
        )

        if result["success"]:
            db.mark_email_sent(em["id"], result["message_id"])
            db.audit("email_sent",
                     f"#{em['id']} to={em['to_address']} subj='{em['subject']}'",
                     "gmail_smtp")

            # Update job status if this was a cover letter / application
            if em.get("job_id") and em["email_type"] in ("cover_letter", "application"):
                db.update_job(em["job_id"], status="applied")
                logger.info(f"[SMTP] Job {em['job_id']} marked as applied")

            sent += 1
        else:
            errors.append(f"#{em['id']}: {result['error']}")
            db.audit("email_send_failed",
                     f"#{em['id']} error={result['error']}",
                     "gmail_smtp")
            failed += 1

    logger.info(f"[SMTP] Queue processing complete: {sent} sent, {failed} failed")
    return {"sent": sent, "failed": failed, "errors": errors}


# ============================================================
# IMAP - MONITORING INBOX
# ============================================================
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993


def _decode_header_value(raw) -> str:
    """Decode an email header value."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _extract_email_address(raw: str) -> str:
    """Extract email address from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', raw)
    return match.group(1) if match else raw.strip()


def _is_recruiter_email(subject: str, body: str, from_addr: str) -> bool:
    """Check if an email looks like a recruiter/job-related message."""
    text = f"{subject} {body} {from_addr}".lower()
    indicators = GMAIL["recruiter_indicators"]
    matches = sum(1 for ind in indicators if ind in text)
    # Need at least 2 indicator matches to flag as recruiter email
    is_match = matches >= 2
    if is_match:
        logger.debug(f"[IMAP] Recruiter email detected ({matches} indicators): {subject[:50]}")
    return is_match


def _match_to_job(subject: str, body: str, from_addr: str) -> Optional[str]:
    """Try to match an incoming email to a tracked job by company name."""
    jobs = db.get_jobs(limit=200)  # Get all tracked jobs
    text = f"{subject} {body} {from_addr}".lower()

    for job in jobs:
        company = job["company"].lower().strip()
        if len(company) > 2 and company in text:
            logger.info(f"[IMAP] Matched email to job: {job['title']} @ {job['company']} (ID: {job['id']})")
            return job["id"]

    return None


def check_inbox(since_hours: int = 24, max_messages: int = 50) -> dict:
    """Check Gmail inbox for recruiter/job-related emails.

    Returns: {"new_threads": int, "matched_to_jobs": int, "drafts_created": int, "errors": list}
    """
    logger.info(f"[IMAP] Checking inbox (last {since_hours}h, max {max_messages} msgs)...")

    try:
        secrets = _load_secrets()
        gmail_address = secrets["gmail_address"]
        app_password = secrets["gmail_app_password"]

        # Connect
        logger.debug(f"[IMAP] Connecting to {IMAP_HOST}:{IMAP_PORT}...")
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=context)
        mail.login(gmail_address, app_password)
        logger.debug("[IMAP] Authenticated")

        # Select inbox
        mail.select("INBOX")

        # Search for recent messages
        since_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{since_date}")'
        if GMAIL["check_unread_only"]:
            search_criteria = f'(UNSEEN SINCE "{since_date}")'

        logger.debug(f"[IMAP] Search: {search_criteria}")
        status, message_ids = mail.search(None, search_criteria)

        if status != "OK" or not message_ids[0]:
            logger.info("[IMAP] No matching messages found.")
            mail.logout()
            return {"new_threads": 0, "matched_to_jobs": 0, "drafts_created": 0, "errors": []}

        ids = message_ids[0].split()
        logger.info(f"[IMAP] Found {len(ids)} messages to check")

        # Limit
        ids = ids[-max_messages:]

        new_threads = 0
        matched = 0
        drafts = 0
        errors = []

        for msg_id in ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = _decode_header_value(msg["Subject"])
                from_raw = _decode_header_value(msg["From"])
                from_addr = _extract_email_address(from_raw)
                date_str = msg["Date"] or ""
                message_id = msg["Message-ID"] or ""
                thread_refs = msg.get("References", "")

                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="replace")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")

                body_preview = body[:500] if body else ""

                # Check if recruiter-related
                if not _is_recruiter_email(subject, body_preview, from_addr):
                    continue

                logger.info(f"[IMAP] RECRUITER EMAIL: From={from_addr} Subject='{subject[:60]}'")

                # Try to match to a tracked job
                job_id = _match_to_job(subject, body_preview, from_addr)
                if job_id:
                    matched += 1

                # Save thread
                thread_data = {
                    "thread_id": message_id,
                    "job_id": job_id,
                    "subject": subject,
                    "from_address": from_addr,
                    "last_message_date": date_str,
                    "status": "unread",
                    "category": "recruiter",
                    "summary": body_preview[:200],
                }
                is_new = db.upsert_gmail_thread(thread_data)
                if is_new:
                    new_threads += 1

                # Auto-draft a reply
                draft_body = _generate_reply_draft(subject, body_preview, from_addr, job_id)
                if draft_body:
                    reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject

                    db.queue_email(
                        job_id=job_id,
                        email_type="recruiter_reply",
                        to_address=from_addr,
                        subject=reply_subject,
                        body=draft_body,
                        thread_id=message_id,
                    )
                    drafts += 1
                    logger.info(f"[IMAP] Auto-drafted reply to {from_addr}")

                db.audit("inbox_recruiter_email",
                         f"from={from_addr} subject='{subject[:40]}' job_match={'yes' if job_id else 'no'}",
                         "gmail_imap")

            except Exception as e:
                logger.error(f"[IMAP] Error processing message {msg_id}: {e}")
                errors.append(str(e))

        mail.logout()

        logger.info(f"[IMAP] Inbox check complete: {new_threads} new threads, "
                    f"{matched} matched to jobs, {drafts} reply drafts created")

        return {
            "new_threads": new_threads,
            "matched_to_jobs": matched,
            "drafts_created": drafts,
            "errors": errors,
        }

    except imaplib.IMAP4.error as e:
        logger.error(f"[IMAP] IMAP error: {e}")
        logger.error("[IMAP] Check your app password and ensure IMAP is enabled in Gmail settings")
        return {"new_threads": 0, "matched_to_jobs": 0, "drafts_created": 0,
                "errors": [f"IMAP error: {e}"]}
    except Exception as e:
        logger.error(f"[IMAP] Unexpected error: {e}")
        return {"new_threads": 0, "matched_to_jobs": 0, "drafts_created": 0,
                "errors": [str(e)]}


# ============================================================
# AUTO-REPLY DRAFTING
# ============================================================
def _generate_reply_draft(subject: str, body: str, from_addr: str,
                          job_id: Optional[str] = None) -> Optional[str]:
    """Generate a reply draft based on email content and context."""

    # Extract recruiter name (guess from email)
    name_part = from_addr.split("@")[0]
    # Clean up: remove dots, numbers, underscores
    recruiter_name = name_part.replace(".", " ").replace("_", " ")
    recruiter_name = re.sub(r'\d+', '', recruiter_name).strip().title()
    if len(recruiter_name) < 2:
        recruiter_name = "there"

    # Get job info if matched
    job_title = "the position"
    company = "your company"
    if job_id:
        job = db.get_job(job_id)
        if job:
            job_title = f"the {job['title']} position"
            company = job["company"]

    # Determine email type and pick template
    body_lower = body.lower()
    subject_lower = subject.lower()

    if any(w in subject_lower + body_lower for w in ["interview", "schedule", "meet", "call", "zoom"]):
        # Interview invitation
        template = EMAIL_TEMPLATES["interview_confirm"]
        personalized = template.format(
            recruiter_name=recruiter_name,
            interview_details="the proposed time",
        )
    elif any(w in subject_lower + body_lower for w in ["follow up", "checking in", "status", "update"]):
        # Status check / follow up
        personalized = (
            f"Hi {recruiter_name},\n\n"
            f"Thank you for the update regarding {job_title} at {company}. "
            f"I appreciate you keeping me informed.\n\n"
            f"Please don't hesitate to reach out if you need any additional "
            f"information from me.\n\n"
            f"Best regards,\n"
            f"Matt Gates\n"
            f"(530) 786-3655"
        )
    else:
        # General recruiter outreach
        template = EMAIL_TEMPLATES["recruiter_reply"]
        personalized = template.format(
            recruiter_name=recruiter_name,
            job_title=job_title,
            company=company,
            personalized_body=(
                f"My background in AI/LLM infrastructure, automation, and full-stack development "
                f"aligns well with what you're looking for. I've built production AI agent systems, "
                f"deployed GPU inference infrastructure, and have strong experience with Python, "
                f"Rust, and modern cloud tooling."
            ),
        )

    return personalized


# ============================================================
# COMBINED CYCLE (called by scheduler)
# ============================================================
def run_email_cycle() -> dict:
    """Run full email cycle: send approved + check inbox.

    Returns combined results.
    """
    logger.info("=" * 40)
    logger.info("EMAIL CYCLE STARTING")
    logger.info("=" * 40)

    # 1. Send approved emails
    send_results = process_approved_emails()

    # 2. Check inbox for recruiter emails
    inbox_results = check_inbox(since_hours=24)

    combined = {
        "sent": send_results["sent"],
        "send_failed": send_results["failed"],
        "new_recruiter_threads": inbox_results["new_threads"],
        "matched_to_jobs": inbox_results["matched_to_jobs"],
        "reply_drafts_created": inbox_results["drafts_created"],
        "errors": send_results["errors"] + inbox_results["errors"],
    }

    db.audit("email_cycle_complete",
             f"sent={combined['sent']} inbox_new={combined['new_recruiter_threads']} "
             f"drafts={combined['reply_drafts_created']}",
             "gmail")

    logger.info(f"EMAIL CYCLE COMPLETE: {json.dumps(combined)}")
    return combined
