"""
Ashby API-Native Application Submitter
=======================================
Bypasses the React SPA entirely. Uses Ashby's public GraphQL API to:
1. Fetch form definition (field IDs, types, paths, required flags, selectable values)
2. Get form render ID + definition ID + action identifier
3. Upload resume via presigned S3 URL (createFileUploadHandle → PUT to S3)
4. Attach resume to form (setFormValueToFile)
5. Submit application (submitSingleApplicationFormAction)

No browser needed. Pure HTTP. ~175 Ashby jobs unlocked.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import re
import sqlite3
import requests
import os
from datetime import datetime, timezone

# === Config ===
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
GRAPHQL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql"

# Form data from CLAUDE.md
APPLICANT = {
    "name": "Matt Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://linkedin.com/in/matt-michels-b836b260",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA",
    "work_auth": True,
    "pronouns": "he/him",
    "years_experience": "10",
}


import time as _time

def gql(operation_name: str, query: str, variables: dict, retries: int = 2) -> dict:
    """Execute a GraphQL request against Ashby's non-user API with rate limit handling."""
    for attempt in range(retries + 1):
        try:
            resp = requests.post(GRAPHQL_URL, json={
                "operationName": operation_name,
                "variables": variables,
                "query": query.strip(),
            }, timeout=30)
            if resp.status_code == 429:
                wait = min(2 ** (attempt + 1), 10)
                print(f"  [RATE LIMITED] Waiting {wait}s before retry...")
                _time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if attempt < retries and "429" in str(e):
                _time.sleep(2 ** (attempt + 1))
                continue
            raise
    return {"errors": [{"message": "Rate limited after retries"}]}


def parse_ashby_url(url: str) -> tuple[str, str] | None:
    """Extract (company_slug, job_id) from an Ashby URL."""
    # Strip /application suffix
    url = re.sub(r'/application/?$', '', url)
    patterns = [
        r"jobs\.ashbyhq\.com/([^/]+)/([0-9a-f\-]{36})",
        r"jobs\.ashbyhq\.com/([^/]+)/([^/\?#]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1), m.group(2)
    return None


def fetch_form_with_identifiers(company_slug: str, job_id: str) -> dict | None:
    """Fetch form structure + render/definition IDs + action identifiers."""
    query = """
    query FormDef(
        $organizationHostedJobsPageName: String!,
        $jobPostingId: String!
    ) {
        jobPosting(
            organizationHostedJobsPageName: $organizationHostedJobsPageName,
            jobPostingId: $jobPostingId
        ) {
            id
            title
            applicationForm {
                id
                sourceFormDefinitionId
                formControls { identifier title }
                sections {
                    title
                    fieldEntries {
                        ... on FormFieldEntry {
                            descriptionHtml
                            field
                        }
                    }
                }
            }
        }
    }
    """
    data = gql("FormDef", query, {
        "organizationHostedJobsPageName": company_slug,
        "jobPostingId": job_id,
    })
    if "errors" in data:
        print(f"[ERROR] GraphQL errors: {json.dumps(data['errors'], indent=2)}")
        return None
    return data.get("data", {}).get("jobPosting")


def create_upload_handle(company_slug: str, filename: str, content_type: str, content_length: int) -> dict | None:
    """Get a presigned S3 upload URL from Ashby."""
    mutation = """
    mutation CreateFileUploadHandle(
        $organizationHostedJobsPageName: String!,
        $fileUploadContext: FileUploadContext!,
        $filename: String!,
        $contentType: String!,
        $contentLength: Int!
    ) {
        createFileUploadHandle(
            organizationHostedJobsPageName: $organizationHostedJobsPageName,
            fileUploadContext: $fileUploadContext,
            filename: $filename,
            contentType: $contentType,
            contentLength: $contentLength
        ) {
            handle
            url
            fields
        }
    }
    """
    data = gql("CreateFileUploadHandle", mutation, {
        "organizationHostedJobsPageName": company_slug,
        "fileUploadContext": "NonUserFormEngine",
        "filename": filename,
        "contentType": content_type,
        "contentLength": content_length,
    })
    if "errors" in data:
        print(f"[ERROR] Upload handle errors: {json.dumps(data['errors'], indent=2)}")
        return None
    return data.get("data", {}).get("createFileUploadHandle")


def upload_file_to_s3(upload_handle: dict, file_path: str, content_type: str) -> bool:
    """Upload file to the presigned S3 URL using multipart form POST.
    S3 presigned POST requires Content-Type as a form field AND exact match in the file part.
    The Content-Type field MUST appear before the file field in the multipart body.
    """
    url = upload_handle["url"]
    fields = dict(upload_handle["fields"])

    # S3 policy enforces Content-Type — must include as form field
    fields["Content-Type"] = content_type

    with open(file_path, "rb") as f:
        # requests sends form fields first, then the file — which is what S3 expects
        files = {"file": (os.path.basename(file_path), f, content_type)}
        resp = requests.post(url, data=fields, files=files, timeout=60)

    if resp.status_code in (200, 201, 204):
        print(f"[OK] File uploaded to S3 (status {resp.status_code})")
        return True
    else:
        print(f"[ERROR] S3 upload failed: {resp.status_code} {resp.text[:300]}")
        return False


def attach_file_to_form(company_slug: str, form_render_id: str, form_def_id: str,
                        field_path: str, file_handle: str) -> bool:
    """Attach an uploaded file to a form field."""
    mutation = """
    mutation SetFormValueToFile(
        $organizationHostedJobsPageName: String!,
        $formRenderIdentifier: String!,
        $path: String!,
        $fileHandle: String!,
        $formDefinitionIdentifier: String!
    ) {
        setFormValueToFile(
            organizationHostedJobsPageName: $organizationHostedJobsPageName,
            formRenderIdentifier: $formRenderIdentifier,
            path: $path,
            fileHandle: $fileHandle,
            formDefinitionIdentifier: $formDefinitionIdentifier
        ) {
            id
        }
    }
    """
    data = gql("SetFormValueToFile", mutation, {
        "organizationHostedJobsPageName": company_slug,
        "formRenderIdentifier": form_render_id,
        "path": field_path,
        "fileHandle": file_handle,
        "formDefinitionIdentifier": form_def_id,
    })
    if "errors" in data:
        print(f"[ERROR] Attach file errors: {json.dumps(data['errors'], indent=2)}")
        return False
    print(f"[OK] Resume attached to form field '{field_path}'")
    return True


def set_form_field_value(company_slug: str, form_render_id: str, form_def_id: str,
                         field_path: str, value) -> bool:
    """Set a single form field value via GraphQL."""
    # Ashby uses setFormValue for text/select fields
    mutation = """
    mutation SetFormValue(
        $organizationHostedJobsPageName: String!,
        $formRenderIdentifier: String!,
        $path: String!,
        $value: JSON!,
        $formDefinitionIdentifier: String!
    ) {
        setFormValue(
            organizationHostedJobsPageName: $organizationHostedJobsPageName,
            formRenderIdentifier: $formRenderIdentifier,
            path: $path,
            value: $value,
            formDefinitionIdentifier: $formDefinitionIdentifier
        ) {
            id
        }
    }
    """
    data = gql("SetFormValue", mutation, {
        "organizationHostedJobsPageName": company_slug,
        "formRenderIdentifier": form_render_id,
        "path": field_path,
        "value": value,
        "formDefinitionIdentifier": form_def_id,
    })
    if "errors" in data:
        print(f"  [ERROR] setFormValue({field_path}): {json.dumps(data['errors'])[:200]}")
        return False
    return True


def submit_form(company_slug: str, job_id: str, form_render_id: str,
                form_def_id: str, action_id: str) -> dict | None:
    """Submit the completed application form.
    Returns: {applicationFormResult: FormRender|FormSubmitSuccess, messages: {blockMessageForCandidateHtml}}
    - FormSubmitSuccess = success
    - FormRender = validation errors (form returned with errorMessages)
    """
    mutation = """
    mutation SubmitApplication(
        $organizationHostedJobsPageName: String!,
        $jobPostingId: String!,
        $formRenderIdentifier: String!,
        $formDefinitionIdentifier: String!,
        $actionIdentifier: String!
    ) {
        submitSingleApplicationFormAction(
            organizationHostedJobsPageName: $organizationHostedJobsPageName,
            jobPostingId: $jobPostingId,
            formRenderIdentifier: $formRenderIdentifier,
            formDefinitionIdentifier: $formDefinitionIdentifier,
            actionIdentifier: $actionIdentifier,
            recaptchaToken: "",
            sourceAttributionCode: "",
            viewedAutomatedProcessingLegalNoticeRuleId: "",
            deviceFingerprint: "",
            applicationRequestId: ""
        ) {
            applicationFormResult {
                ... on FormSubmitSuccess {
                    __typename
                }
                ... on FormRender {
                    __typename
                    id
                    errorMessages
                }
            }
            messages {
                blockMessageForCandidateHtml
            }
        }
    }
    """
    data = gql("SubmitApplication", mutation, {
        "organizationHostedJobsPageName": company_slug,
        "jobPostingId": job_id,
        "formRenderIdentifier": form_render_id,
        "formDefinitionIdentifier": form_def_id,
        "actionIdentifier": action_id,
    })
    if "errors" in data:
        print(f"[ERROR] Submit errors: {json.dumps(data['errors'], indent=2)}")
        return None
    return data.get("data", {}).get("submitSingleApplicationFormAction")


def resolve_field_value(field: dict) -> object:
    """Map a form field to the appropriate value from APPLICANT data."""
    path = field.get("path", "")
    ftype = field.get("type", "")
    title = field.get("title", "").lower()

    # System fields
    if path == "_systemfield_name":
        return APPLICANT["name"]
    if path == "_systemfield_email":
        return APPLICANT["email"]
    if path == "_systemfield_resume":
        return "__FILE__"  # Sentinel — handled separately
    if path == "_systemfield_location":
        return APPLICANT["location"]

    # By type + title heuristics
    if ftype == "Phone" or "phone" in title:
        return APPLICANT["phone"]
    if ftype == "Email" or "email" in title:
        return APPLICANT["email"]

    # LinkedIn
    if "linkedin" in title:
        return APPLICANT["linkedin"]
    if "github" in title:
        return APPLICANT["github"]
    if "portfolio" in title or "website" in title:
        return APPLICANT["github"]

    # Pronouns
    if "pronoun" in title:
        return APPLICANT["pronouns"]

    # Work authorization / sponsorship
    # Two question patterns:
    # A) "Are you legally authorized to work in the US?" → answer YES
    # B) "Will you require sponsorship?" → answer NO
    if any(kw in title for kw in ["sponsorship", "sponsor", "sponor", "visa", "authorized", "work auth", "legally work"]):
        selectable = field.get("selectableValues", [])
        is_sponsorship_question = "sponsor" in title or "sponor" in title or "visa" in title  # "Need sponsorship?" → No
        is_auth_question = ("authorized" in title or "legally" in title) and not is_sponsorship_question

        if is_sponsorship_question:
            # We do NOT need sponsorship → select the "No" option
            for sv in selectable:
                val = sv["value"].lower().strip()
                label = sv["label"].lower().strip()
                if val == "no" or val.startswith("no,") or val.startswith("no ") or label.startswith("no"):
                    return sv["value"]
                if "will not" in val or "do not" in val or "don't" in val or "not require" in val:
                    return sv["value"]
        if is_auth_question:
            # We ARE authorized → select Yes
            for sv in selectable:
                val = sv["value"].lower().strip()
                label = sv["label"].lower().strip()
                if val == "yes" or val.startswith("yes,") or val.startswith("yes ") or label.startswith("yes"):
                    return sv["value"]
        # Fallback
        return selectable[0]["value"] if selectable else "Yes"

    # Years of experience
    if "year" in title and "experience" in title:
        return APPLICANT["years_experience"]

    # Side business / obligations / non-compete
    if any(kw in title for kw in ["side business", "obligation", "board position", "non-compete"]):
        selectable = field.get("selectableValues", [])
        for sv in selectable:
            if sv["value"].lower() == "no":
                return sv["value"]
        return "No"

    # Location / relocation
    if any(kw in title for kw in ["location", "where do you", "city", "reside"]):
        return APPLICANT["location"]

    # Remote work
    if "remote" in title:
        selectable = field.get("selectableValues", [])
        for sv in selectable:
            if "yes" in sv["label"].lower():
                return sv["value"]
        return "Yes"

    # Salary / compensation
    if any(kw in title for kw in ["salary", "compensation", "pay"]):
        return "Open to discussion"

    # How did you hear
    if "how did you" in title or "hear about" in title or "find this" in title:
        selectable = field.get("selectableValues", [])
        for sv in selectable:
            if any(kw in sv["label"].lower() for kw in ["other", "internet", "job board", "online"]):
                return sv["value"]
        return selectable[0]["value"] if selectable else "Job board"

    # Start date / availability
    if "start" in title or "available" in title or "begin" in title:
        return "Immediately"

    # Boolean fields — common yes/no questions
    if ftype == "Boolean":
        # Sponsorship/visa booleans → False (we do NOT need sponsorship)
        if any(kw in title for kw in ["sponsor", "sponor", "visa", "h1b", "h-1b"]):
            return False
        # "Are you located in the United States?" → True
        if "united states" in title or "located in" in title:
            return True
        # "Are you authorized to work?" → True
        if "authorized" in title or "legally" in title:
            return True
        # "Do you have experience with X?" → True
        if "experience" in title or "hands-on" in title:
            return True
        # "Are you able to work from office?" → True (willing to consider)
        if "office" in title or "work from" in title or "on-site" in title:
            return True
        # "Are you 18 or older?" → True
        if "18" in title or "age" in title:
            return True
        # Default boolean: True (optimistic)
        return True

    # Legal name / alternate name
    if "legal" in title and "name" in title:
        return APPLICANT["name"]

    # "Tell us about yourself" / essay questions
    if ftype == "LongText" or ftype == "RichText":
        if "about you" in title or "excited" in title or "why" in title:
            return ("I'm a full-stack engineer with 10 years of experience spanning AI/ML systems, "
                    "browser automation, and infrastructure. I've built production MCP servers, "
                    "autonomous agent systems, and GPU inference pipelines. I'm excited about this "
                    "role because it aligns with my passion for building reliable, scalable systems.")
        if "project" in title or "proud" in title or "accomplishment" in title:
            return ("I built a 27K-line Rust browser automation engine with MCTS action planning, "
                    "knowledge graphs, and multi-step agent orchestration. It processes thousands of "
                    "web interactions daily with sub-50ms page loads. I also built an autonomous "
                    "trading system using ML prediction models that achieved 20x returns.")
        return "__COVER_LETTER__"

    # Generic select — pick first value if required
    if ftype in ("ValueSelect", "MultiValueSelect") and field.get("selectableValues"):
        if not field.get("isNullable", True):
            print(f"  [WARN] Unknown required select '{field['title']}' — picking first value")
            return field["selectableValues"][0]["value"]
        return None

    # Cover letter / additional info — caller overrides
    if any(kw in title for kw in ["cover", "additional", "anything else", "message"]):
        return "__COVER_LETTER__"

    # URL fields
    if ftype == "Url" or "url" in title or "link" in title:
        if "linkedin" in title:
            return APPLICANT["linkedin"]
        if "github" in title:
            return APPLICANT["github"]
        # Generic "shared URL" / "portfolio" / "website"
        return APPLICANT["github"]

    # "Referred by" / "How did you hear" with text input
    if "refer" in title and ftype == "String":
        return ""  # No referral

    # Catch-all for sponsorship detail follow-ups
    if "sponsorship" in title and ("detail" in title or "additional" in title):
        return "N/A - US citizen, no sponsorship needed"

    print(f"  [WARN] No mapping for: {field['title']} (type={ftype}, path={path})")
    return None


def apply_to_job(url: str, cover_letter: str = None, dry_run: bool = False) -> dict:
    """
    Full pipeline: parse URL -> fetch form -> upload resume -> fill fields -> submit.
    Returns dict with {success: bool, error: str|None, job_title: str, company: str}.
    """
    result = {"success": False, "error": None, "job_title": "", "company": "", "url": url}

    print(f"\n{'='*60}")
    print(f"[ASHBY API] Applying to: {url}")
    print(f"{'='*60}")

    # 1. Parse URL
    parsed = parse_ashby_url(url)
    if not parsed:
        result["error"] = f"Cannot parse Ashby URL: {url}"
        print(f"[ERROR] {result['error']}")
        return result
    company_slug, job_id = parsed
    result["company"] = company_slug
    print(f"[OK] Company: {company_slug}, Job ID: {job_id}")

    # 2. Fetch form definition with identifiers
    print("[...] Fetching form definition...")
    posting = fetch_form_with_identifiers(company_slug, job_id)
    if not posting:
        result["error"] = "Failed to fetch form definition"
        print(f"[ERROR] {result['error']}")
        return result

    result["job_title"] = posting.get("title", "Unknown")
    print(f"[OK] Job: {result['job_title']}")

    form = posting.get("applicationForm", {})
    form_render_id = form.get("id")
    form_def_id = form.get("sourceFormDefinitionId")
    controls = form.get("formControls", [])
    action_id = controls[0]["identifier"] if controls else None

    if not all([form_render_id, form_def_id, action_id]):
        result["error"] = f"Missing form identifiers: render={form_render_id}, def={form_def_id}, action={action_id}"
        print(f"[ERROR] {result['error']}")
        return result

    print(f"[OK] Form: render={form_render_id[:12]}... def={form_def_id[:12]}... action={action_id[:12]}...")

    # Collect all fields
    all_fields = []
    for section in form.get("sections", []):
        for entry in section.get("fieldEntries", []):
            if "field" in entry:
                all_fields.append(entry["field"])
    print(f"[OK] Found {len(all_fields)} form fields")

    # 3. Upload resume if needed
    resume_field = None
    for f in all_fields:
        if f.get("path") == "_systemfield_resume" or f.get("type") == "File":
            resume_field = f
            break

    if resume_field and os.path.exists(RESUME_PATH):
        print("[...] Uploading resume...")
        file_size = os.path.getsize(RESUME_PATH)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        upload = create_upload_handle(company_slug, os.path.basename(RESUME_PATH), content_type, file_size)
        if upload:
            file_handle = upload["handle"]
            if not dry_run:
                s3_ok = upload_file_to_s3(upload, RESUME_PATH, content_type)
                if s3_ok:
                    attach_file_to_form(company_slug, form_render_id, form_def_id,
                                        resume_field["path"], file_handle)
                else:
                    print("[WARN] S3 upload failed — continuing without resume")
            else:
                print(f"[DRY RUN] Would upload resume ({file_size} bytes) to S3")
        else:
            print("[WARN] Could not create upload handle — continuing without resume")

    # 4. Fill form fields
    print("[...] Filling form fields...")
    field_errors = []
    for field in all_fields:
        fpath = field["path"]
        ftype = field.get("type", "")

        # Skip file fields (handled above)
        if ftype == "File" or fpath == "_systemfield_resume":
            continue

        value = resolve_field_value(field)

        # Cover letter override
        if value == "__COVER_LETTER__":
            if cover_letter:
                value = cover_letter
            else:
                continue  # Skip if no cover letter provided

        if value is None or value == "__FILE__":
            if not field.get("isNullable", True):
                field_errors.append(f"Required field has no value: {field['title']}")
            continue

        display = str(value)[:60]
        print(f"  {field['title']}: {display}")

        if not dry_run:
            ok = set_form_field_value(company_slug, form_render_id, form_def_id, fpath, value)
            if not ok:
                field_errors.append(f"Failed to set: {field['title']}")

    if field_errors:
        print(f"[WARN] {len(field_errors)} field issues:")
        for e in field_errors:
            print(f"  - {e}")

    if dry_run:
        print(f"\n[DRY RUN] Would submit form {form_render_id[:12]}... with action {action_id[:12]}...")
        result["success"] = True
        return result

    # 5. Submit
    print("[...] Submitting application...")
    submit_result = submit_form(company_slug, job_id, form_render_id, form_def_id, action_id)
    if submit_result:
        form_result = submit_result.get("applicationFormResult", {})
        typename = form_result.get("__typename", "")

        if typename == "FormSubmitSuccess":
            print(f"[SUCCESS] Application submitted to {company_slug} — {result['job_title']}!")
            result["success"] = True
        elif typename == "FormRender":
            error_msgs = form_result.get("errorMessages", [])
            result["error"] = f"Form validation errors: {error_msgs}"
            print(f"[FAILED] {result['error']}")
        else:
            # Check for block message
            block_msg = submit_result.get("messages", {}).get("blockMessageForCandidateHtml")
            if block_msg:
                result["error"] = f"Blocked: {block_msg}"
                print(f"[BLOCKED] {block_msg}")
            else:
                result["error"] = f"Unknown response type: {typename}"
                print(f"[WARN] {result['error']}: {json.dumps(submit_result)[:300]}")
    else:
        result["error"] = "Submit returned no data"
        print(f"[FAILED] {result['error']}")

    return result


def get_ashby_jobs_from_db(status: str = "new", limit: int = 10) -> list[dict]:
    """Get unapplied Ashby jobs from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score
        FROM jobs
        WHERE source = 'ashby'
          AND status = ?
          AND url LIKE '%ashbyhq.com%'
        ORDER BY fit_score DESC
        LIMIT ?
    """, (status, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_applied_in_db(job_id: int, success: bool):
    """Update job status in the database."""
    conn = sqlite3.connect(DB_PATH)
    status = "applied" if success else "apply_failed"
    conn.execute(
        "UPDATE jobs SET status = ?, applied_date = ? WHERE id = ?",
        (status, datetime.now(timezone.utc).isoformat(), job_id)
    )
    conn.commit()
    conn.close()


def run_batch(limit: int, cover_letter: str = None, dry_run: bool = False) -> list[dict]:
    """Apply to multiple Ashby jobs from the database. Returns list of results."""
    jobs = get_ashby_jobs_from_db(limit=limit)
    print(f"Found {len(jobs)} Ashby jobs to apply to\n")

    results = []
    for job in jobs:
        res = apply_to_job(job["url"], cover_letter=cover_letter, dry_run=dry_run)
        res["db_id"] = job["id"]
        res["db_score"] = job.get("score", 0)
        results.append(res)

        if not dry_run:
            mark_applied_in_db(job["id"], res["success"])

    # Summary
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {len(successes)}/{len(results)} successful")
    if failures:
        print(f"\nFailed ({len(failures)}):")
        for r in failures:
            print(f"  - {r['company']}: {r['job_title']} — {r['error']}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ashby API-Native Application Submitter")
    parser.add_argument("--url", help="Apply to a specific Ashby URL")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually submit")
    parser.add_argument("--batch", type=int, default=0, help="Apply to N top-scored Ashby jobs from DB")
    parser.add_argument("--cover-letter", help="Cover letter text")
    args = parser.parse_args()

    if args.url:
        apply_to_job(args.url, cover_letter=args.cover_letter, dry_run=args.dry_run)
    elif args.batch > 0:
        run_batch(args.batch, cover_letter=args.cover_letter, dry_run=args.dry_run)
    else:
        print("Usage: python apply_ashby_api.py --url <URL> [--dry-run]")
        print("       python apply_ashby_api.py --batch 5 [--dry-run]")
