"""
Job Hunter MCP Server
=====================
Full autonomous job hunting pipeline for Claude Code.

Tools:
  job_search          - Search all APIs for remote jobs
  job_search_preset   - Run pre-built targeted searches
  job_list            - List/filter tracked jobs
  job_detail          - Full details on a job
  job_update          - Update status/notes
  job_stats           - Dashboard statistics
  job_draft_letter    - Generate cover letter context for a job
  job_queue_email     - Queue an email draft (cover letter, follow-up, reply)
  job_email_queue     - View pending email drafts
  job_approve_email   - Approve a queued email for sending
  job_set_api_key     - Store API keys
  job_audit_log       - View system activity log
  job_export          - Export jobs as JSON
"""
import json
import logging
import sys
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# Ensure src is importable
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from src import db, apis
from src.config import (
    USER_PROFILE, SEARCH_PRESETS, SCHEDULER, DATA_DIR, LOG_FILE
)

# ============================================================
# LOGGING
# ============================================================
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), mode="a"),
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger("job_hunter.mcp")
logger.info("=" * 60)
logger.info("JOB HUNTER MCP SERVER STARTING")
logger.info(f"DB: {db.DB_PATH} | Log: {LOG_FILE}")
logger.info("=" * 60)

mcp = FastMCP("job_hunter_mcp")

# ============================================================
# INPUT MODELS
# ============================================================
class SearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(..., description="Search query e.g. 'AI automation engineer'", min_length=1)
    category: str = Field(default="software-dev", description="Remotive category: software-dev, qa, devops-sysadmin, sales, marketing, all")
    limit: int = Field(default=50, ge=1, le=100)
    save: bool = Field(default=True, description="Save results to tracking DB")

class PresetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    preset: str = Field(default="all", description="Preset: ai_automation, qa_engineering, devops, sales_tech, all")

class ListInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    status: Optional[str] = Field(default=None, description="Filter: new, saved, applied, interviewing, rejected, offer")
    source: Optional[str] = Field(default=None)
    min_score: float = Field(default=0.0, ge=0, le=100)
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class DetailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    job_id: str = Field(..., description="Job ID")

class UpdateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    job_id: str = Field(...)
    status: Optional[str] = Field(default=None, description="new, saved, applied, interviewing, rejected, offer")
    notes: Optional[str] = Field(default=None)
    cover_letter: Optional[str] = Field(default=None)

class CoverLetterInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    job_id: str = Field(...)
    tone: str = Field(default="professional", description="professional, enthusiastic, conversational")
    focus: Optional[str] = Field(default=None, description="Skills to emphasize")

class QueueEmailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    job_id: Optional[str] = Field(default=None)
    email_type: str = Field(..., description="cover_letter, follow_up, recruiter_reply, interview_confirm")
    to_address: str = Field(...)
    subject: str = Field(...)
    body: str = Field(...)
    thread_id: Optional[str] = Field(default=None, description="Gmail thread ID for replies")

class ApproveEmailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email_id: int = Field(..., description="Email queue ID to approve")

class ApiKeyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    service: str = Field(..., description="Service: rapidapi, adzuna")
    api_key: str = Field(..., min_length=5)

class ExportInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    status: Optional[str] = Field(default=None)
    min_score: float = Field(default=0.0, ge=0, le=100)
    limit: int = Field(default=100, ge=1, le=500)

# ============================================================
# TOOLS
# ============================================================

@mcp.tool(name="job_search", annotations={
    "title": "Search Jobs", "readOnlyHint": False,
    "destructiveHint": False, "openWorldHint": True,
})
async def job_search(params: SearchInput) -> str:
    """Search for remote jobs across Remotive, Arbeitnow, and JSearch.
    Scores each job for fit, deduplicates, and saves to tracking DB.
    """
    logger.info(f"TOOL: job_search('{params.query}', cat='{params.category}')")
    jsearch_key = db.get_api_key("rapidapi")
    result = await apis.search_all(params.query, jsearch_key, params.category, params.limit)

    new_count = 0
    if params.save:
        for job in result["jobs"]:
            if db.upsert_job(job):
                new_count += 1

    db.log_search(params.query, list(result["source_counts"].keys()),
                  result["total"], new_count)
    db.audit("job_search", f"query='{params.query}' found={result['total']} new={new_count}")

    # Format response
    top_jobs = result["jobs"][:15]
    lines = [
        f"## Search Results for '{params.query}'",
        f"**Total:** {result['total']} unique jobs | **New:** {new_count} | **Sources:** {result['source_counts']}",
        ""
    ]
    if result["errors"]:
        lines.append(f"**Errors:** {', '.join(result['errors'])}")

    lines.append("\n### Top Matches:")
    for i, j in enumerate(top_jobs, 1):
        sal = f" | {j['salary']}" if j['salary'] else ""
        lines.append(
            f"{i}. **{j['title']}** @ {j['company']} "
            f"(score: {j['fit_score']}{sal})\n"
            f"   ID: `{j['id']}` | {j['source']} | {j['location']}\n"
            f"   {j['url']}\n"
            f"   _Fit: {j['fit_reason']}_"
        )

    return "\n".join(lines)


@mcp.tool(name="job_search_preset", annotations={
    "title": "Run Preset Job Searches", "readOnlyHint": False,
    "openWorldHint": True,
})
async def job_search_preset(params: PresetInput) -> str:
    """Run pre-built targeted searches for Matt's top job categories.
    Preset 'all' runs all categories. Each preset has optimized queries.
    """
    logger.info(f"TOOL: job_search_preset('{params.preset}')")

    presets = SEARCH_PRESETS if params.preset == "all" else {
        params.preset: SEARCH_PRESETS.get(params.preset, {})
    }

    if not any(presets.values()):
        return f"Unknown preset: {params.preset}. Available: {', '.join(SEARCH_PRESETS.keys())}, all"

    jsearch_key = db.get_api_key("rapidapi")
    total_new = 0
    total_found = 0
    summaries = []

    for name, preset in presets.items():
        if not preset:
            continue
        logger.info(f"Running preset: {name}")
        for query in preset.get("queries", []):
            cat = preset.get("categories", ["software-dev"])[0]
            result = await apis.search_all(query, jsearch_key, cat, 30)
            new_count = 0
            for job in result["jobs"]:
                if db.upsert_job(job):
                    new_count += 1
            total_new += new_count
            total_found += result["total"]
            db.log_search(query, list(result["source_counts"].keys()),
                         result["total"], new_count)

        summaries.append(f"- **{name}**: {len(preset.get('queries', []))} queries run")

    db.audit("preset_search", f"preset='{params.preset}' found={total_found} new={total_new}")

    return (
        f"## Preset Search Complete: '{params.preset}'\n\n"
        f"**Total found:** {total_found} | **New jobs saved:** {total_new}\n\n"
        + "\n".join(summaries)
        + f"\n\nUse `job_list` with min_score to see top matches."
    )


@mcp.tool(name="job_list", annotations={
    "title": "List Tracked Jobs", "readOnlyHint": True,
})
async def job_list(params: ListInput) -> str:
    """List jobs from the tracking database with optional filters."""
    logger.info(f"TOOL: job_list(status={params.status}, min={params.min_score})")
    jobs = db.get_jobs(params.status, params.source, params.min_score,
                       params.limit, params.offset)

    if not jobs:
        return "No jobs found matching filters."

    lines = [f"## Tracked Jobs ({len(jobs)} results)\n"]
    for j in jobs:
        sal = f" | {j['salary']}" if j.get('salary') else ""
        lines.append(
            f"- **{j['title']}** @ {j['company']} "
            f"[{j['status']}] score={j['fit_score']}{sal}\n"
            f"  ID: `{j['id']}` | {j['source']} | {j['url']}"
        )
    return "\n".join(lines)


@mcp.tool(name="job_detail", annotations={
    "title": "Job Details", "readOnlyHint": True,
})
async def job_detail(params: DetailInput) -> str:
    """Get full details on a specific job including description and fit analysis."""
    job = db.get_job(params.job_id)
    if not job:
        return f"Job not found: {params.job_id}"

    return json.dumps({
        "id": job["id"], "title": job["title"], "company": job["company"],
        "url": job["url"], "location": job["location"], "salary": job["salary"],
        "job_type": job["job_type"], "category": job["category"],
        "status": job["status"], "fit_score": job["fit_score"],
        "fit_reason": job["fit_reason"], "date_posted": job["date_posted"],
        "date_found": job["date_found"], "notes": job["notes"],
        "has_cover_letter": bool(job.get("cover_letter")),
        "applied_date": job["applied_date"],
        "description": job["description"][:2000],
        "source": job["source"],
    }, indent=2)


@mcp.tool(name="job_update", annotations={
    "title": "Update Job", "readOnlyHint": False, "destructiveHint": False,
})
async def job_update(params: UpdateInput) -> str:
    """Update a job's status, notes, or cover letter."""
    kwargs = {}
    if params.status:
        kwargs["status"] = params.status
    if params.notes is not None:
        kwargs["notes"] = params.notes
    if params.cover_letter is not None:
        kwargs["cover_letter"] = params.cover_letter

    if not kwargs:
        return "Nothing to update."

    ok = db.update_job(params.job_id, **kwargs)
    if ok:
        db.audit("job_update", f"id={params.job_id} {kwargs}", "claude_code")
        return f"Job {params.job_id} updated: {kwargs}"
    return f"Job not found: {params.job_id}"


@mcp.tool(name="job_stats", annotations={
    "title": "Dashboard Statistics", "readOnlyHint": True,
})
async def job_stats() -> str:
    """Get comprehensive dashboard statistics."""
    s = db.get_stats()
    return json.dumps(s, indent=2)


@mcp.tool(name="job_draft_letter", annotations={
    "title": "Draft Cover Letter Context", "readOnlyHint": True,
})
async def job_draft_letter(params: CoverLetterInput) -> str:
    """Get all context needed to draft a cover letter for a job.
    Returns job details + Matt's profile so Claude Code can write the letter.
    """
    job = db.get_job(params.job_id)
    if not job:
        return f"Job not found: {params.job_id}"

    return json.dumps({
        "instruction": (
            f"Draft a {params.tone} cover letter for this job. "
            f"{'Focus on: ' + params.focus if params.focus else 'Match the strongest skills.'} "
            "Keep it under 400 words. Be specific about matching experience."
        ),
        "job": {
            "title": job["title"], "company": job["company"],
            "description": job["description"][:2500],
            "fit_reason": job["fit_reason"], "fit_score": job["fit_score"],
        },
        "applicant": USER_PROFILE,
    }, indent=2)


@mcp.tool(name="job_queue_email", annotations={
    "title": "Queue Email Draft", "readOnlyHint": False,
})
async def job_queue_email(params: QueueEmailInput) -> str:
    """Queue an email draft for review. Emails stay in 'draft' until approved."""
    eid = db.queue_email(
        params.job_id, params.email_type, params.to_address,
        params.subject, params.body, params.thread_id
    )
    db.audit("email_queued", f"#{eid} type={params.email_type} to={params.to_address}")
    return f"Email #{eid} queued as draft. Use job_approve_email to approve for sending."


@mcp.tool(name="job_email_queue", annotations={
    "title": "View Email Queue", "readOnlyHint": True,
})
async def job_email_queue() -> str:
    """View all pending email drafts waiting for approval."""
    drafts = db.get_email_queue("draft")
    if not drafts:
        return "No pending email drafts."

    lines = [f"## Email Queue ({len(drafts)} drafts)\n"]
    for d in drafts:
        lines.append(
            f"- **#{d['id']}** [{d['email_type']}] To: {d['to_address']}\n"
            f"  Subject: {d['subject']}\n"
            f"  Created: {d['created_at']}\n"
            f"  Preview: {d['body'][:150]}..."
        )
    return "\n".join(lines)


@mcp.tool(name="job_approve_email", annotations={
    "title": "Approve Email", "readOnlyHint": False,
})
async def job_approve_email(params: ApproveEmailInput) -> str:
    """Approve a queued email draft for sending."""
    ok = db.approve_email(params.email_id)
    if ok:
        db.audit("email_approved", f"#{params.email_id}", "user")
        return f"Email #{params.email_id} approved. Scheduler will send on next cycle."
    return f"Email #{params.email_id} not found or already processed."


@mcp.tool(name="job_set_api_key", annotations={
    "title": "Set API Key", "readOnlyHint": False,
})
async def job_set_api_key(params: ApiKeyInput) -> str:
    """Store an API key for a service (e.g. 'rapidapi' for JSearch)."""
    db.save_api_key(params.service, params.api_key)
    db.audit("api_key_set", f"service={params.service}")
    return f"API key saved for {params.service}."


@mcp.tool(name="job_audit_log", annotations={
    "title": "View Audit Log", "readOnlyHint": True,
})
async def job_audit_log() -> str:
    """View recent system activity."""
    log = db.get_audit_log(30)
    if not log:
        return "No audit entries."

    lines = ["## Recent Activity\n"]
    for e in log:
        lines.append(f"- [{e['timestamp'][:19]}] **{e['action']}** ({e['source']}) {e['details']}")
    return "\n".join(lines)


@mcp.tool(name="job_export", annotations={
    "title": "Export Jobs", "readOnlyHint": True,
})
async def job_export(params: ExportInput) -> str:
    """Export tracked jobs as JSON for the dashboard."""
    jobs = db.get_jobs(params.status, None, params.min_score, params.limit)
    stats = db.get_stats()
    emails = db.get_email_queue("draft")

    return json.dumps({
        "jobs": jobs, "stats": stats,
        "email_queue": emails,
        "exported_at": __import__("datetime").datetime.now().isoformat(),
    }, indent=2, default=str)


# ============================================================
# GMAIL AUTOMATION TOOLS
# ============================================================

class GmailSendInput(BaseModel):
    """Input for sending a specific email directly (bypasses queue)."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    to_address: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body text")
    job_id: Optional[str] = Field(default=None, description="Associated job ID to mark as applied")

class GmailCheckInput(BaseModel):
    """Input for checking inbox."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    since_hours: int = Field(default=24, description="Check emails from last N hours", ge=1, le=168)
    max_messages: int = Field(default=50, ge=1, le=200)

class GmailFlushInput(BaseModel):
    """Input for flushing the send queue."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    confirm: bool = Field(default=False, description="Must be True to send all approved emails")


@mcp.tool(name="gmail_send_now", annotations={
    "title": "Send Email Now", "readOnlyHint": False, "destructiveHint": False,
    "openWorldHint": True,
})
async def gmail_send_now(params: GmailSendInput) -> str:
    """Send an email immediately via Gmail SMTP. Use for urgent applications or replies.
    For tracked/queued workflow, use job_queue_email + job_approve_email instead.
    """
    logger.info(f"TOOL: gmail_send_now(to={params.to_address}, subj='{params.subject}')")

    try:
        from src.gmail import send_email as gmail_send
        result = gmail_send(params.to_address, params.subject, params.body)

        if result["success"]:
            db.audit("email_sent_direct",
                     f"to={params.to_address} subj='{params.subject}'",
                     "claude_code")
            if params.job_id:
                db.update_job(params.job_id, status="applied")

            return (f"Email sent successfully to {params.to_address}\n"
                    f"Message ID: {result['message_id']}"
                    f"{' | Job marked as applied' if params.job_id else ''}")
        else:
            return f"SEND FAILED: {result['error']}"

    except FileNotFoundError:
        return ("Error: secrets.json not found. Create it with:\n"
                '{"gmail_address": "you@gmail.com", "gmail_app_password": "xxxx xxxx xxxx xxxx"}')
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="gmail_check_inbox", annotations={
    "title": "Check Inbox for Recruiter Emails", "readOnlyHint": False,
    "openWorldHint": True,
})
async def gmail_check_inbox(params: GmailCheckInput) -> str:
    """Scan Gmail inbox for recruiter/job-related emails.
    Auto-matches to tracked jobs and drafts replies for approval.
    """
    logger.info(f"TOOL: gmail_check_inbox(hours={params.since_hours})")

    try:
        from src.gmail import check_inbox
        result = check_inbox(params.since_hours, params.max_messages)

        lines = [
            f"## Inbox Check Results",
            f"**New recruiter threads:** {result['new_threads']}",
            f"**Matched to tracked jobs:** {result['matched_to_jobs']}",
            f"**Reply drafts created:** {result['drafts_created']}",
        ]
        if result["errors"]:
            lines.append(f"**Errors:** {', '.join(result['errors'])}")
        if result["drafts_created"] > 0:
            lines.append(f"\nUse `job_email_queue` to review and approve the drafted replies.")

        return "\n".join(lines)

    except FileNotFoundError:
        return "Error: secrets.json not found."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="gmail_flush_queue", annotations={
    "title": "Send All Approved Emails", "readOnlyHint": False,
    "openWorldHint": True,
})
async def gmail_flush_queue(params: GmailFlushInput) -> str:
    """Send all approved emails in the queue via Gmail SMTP.
    Set confirm=True to actually send.
    """
    if not params.confirm:
        queue = db.get_email_queue("approved")
        if not queue:
            return "No approved emails in queue."
        lines = [f"**{len(queue)} approved emails ready to send:**\n"]
        for em in queue:
            lines.append(f"- #{em['id']} → {em['to_address']}: {em['subject']}")
        lines.append(f"\nCall again with confirm=True to send all.")
        return "\n".join(lines)

    try:
        from src.gmail import process_approved_emails
        result = process_approved_emails()
        return (f"Queue flushed: {result['sent']} sent, {result['failed']} failed"
                f"{' | Errors: ' + ', '.join(result['errors']) if result['errors'] else ''}")
    except FileNotFoundError:
        return "Error: secrets.json not found."
    except Exception as e:
        return f"Error: {e}"


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    logger.info("Starting MCP server via stdio...")
    mcp.run()
