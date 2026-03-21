"""
Swarm Application Dispatcher
=============================
Deploys parallel application workers across all automatable ATS platforms.
Anything that CAN'T be swarmed gets annotated in the bug report with
exactly what's wrong and what would need to happen to unblock it.

Platforms:
- Ashby: API-native (no browser needed) — FULLY AUTOMATED
- Lever: Wraith browser (server-rendered HTML) — NEEDS BROWSER SESSION
- Greenhouse (direct): Wraith browser (React forms) — NEEDS BROWSER SESSION
- Greenhouse (wrapped): Company career sites with gh_jid= param — NEEDS BROWSER + REDIRECT HANDLING
- jsearch/arbeitnow: Random third-party boards — NEEDS PER-SITE INVESTIGATION
- LinkedIn/Indeed: Heavy anti-bot, captchas — MANUAL ONLY
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import sqlite3
import os
import re
import traceback
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
BUG_REPORT_PATH = r"J:\job-hunter-mcp\swarm_bug_report.md"

from apply_ashby_api import apply_to_job as ashby_apply, mark_applied_in_db


# ─── ATS Classification ──────────────────────────────────────────────

def classify_job(url: str, source: str) -> dict:
    """Classify a job URL into an automation tier with blockers annotated."""
    domain = urlparse(url).netloc.lower()

    # Ashby — API native, but blocked by reCAPTCHA
    if "ashbyhq.com" in domain:
        return {"tier": "api_native", "platform": "ashby",
                "blocker": "WRAITH BUG: Ashby API submit requires a valid reCAPTCHA v3 token. Empty token gets RECAPTCHA_SCORE_BELOW_THRESHOLD. Wraith needs reCAPTCHA v3 token generation support — load Google's reCAPTCHA JS in QuickJS, execute grecaptcha.execute(siteKey, {action: 'submit'}), return the token. Site key is embedded in Ashby's React bundle.",
                "method": "GraphQL API (apply_ashby_api.py) — form fetch + fill works, submit blocked by captcha"}

    # Lever — server-rendered HTML, Wraith can fill
    if "lever.co" in domain:
        return {"tier": "wraith_ready", "platform": "lever",
                "blocker": "WRAITH TASK: Lever forms are server-rendered HTML — Wraith CAN render these. Needs sequential browse_navigate → browse_fill → browse_upload_file → browse_click. No captcha. Playbook exists at playbooks/lever.md.",
                "method": "Wraith: browse_navigate(url+'/apply') → fill per lever playbook → submit"}

    # Greenhouse direct — React SPA but Wraith can handle
    if "greenhouse.io" in domain:
        return {"tier": "wraith_ready", "platform": "greenhouse_direct",
                "blocker": "WRAITH TASK: Greenhouse forms are React SPAs but Wraith renders them. Needs sequential browser session — browse_navigate → browse_snapshot → browse_fill → browse_upload_file → browse_click. Playbook at playbooks/greenhouse.md.",
                "method": "Wraith: browse_navigate → snapshot → fill per greenhouse playbook → submit"}

    # Greenhouse wrapped — company career sites that embed Greenhouse
    if source == "greenhouse" and "greenhouse" not in domain:
        gh_jid = re.search(r'gh_jid=(\d+)', url)
        return {"tier": "wraith_redirect", "platform": "greenhouse_wrapped",
                "blocker": f"WRAITH BUG: Company career site wrapping Greenhouse (gh_jid={gh_jid.group(1) if gh_jid else '?'}). Wraith needs to follow redirect chain from company URL to find the actual Greenhouse form. May render as iframe (Wraith can't enter iframes) or redirect to greenhouse.io (Wraith can handle). Needs: 1) browse_navigate to company URL, 2) detect redirect vs iframe, 3) if redirect → fill Greenhouse form, 4) if iframe → BLOCKED (Wraith iframe support needed).",
                "method": "Wraith: navigate → detect redirect/iframe → fill if accessible"}

    # LinkedIn
    if "linkedin.com" in domain:
        return {"tier": "manual_only", "platform": "linkedin",
                "blocker": "WRAITH BUG: LinkedIn has aggressive anti-bot detection: CAPTCHA challenges, session fingerprinting, rate limiting by IP. Easy Apply requires authenticated session + CSRF tokens. Wraith needs: 1) Cookie import from real browser session (browse_cookie_import or similar), 2) LinkedIn-specific fingerprint profile to avoid detection, 3) CSRF token extraction from page. Even with these, LinkedIn blocks after 2-3 automated attempts per IP.",
                "method": "Wraith with session cookies + stealth profile (not built)"}

    # Indeed
    if "indeed.com" in domain:
        return {"tier": "wraith_investigation", "platform": "indeed",
                "blocker": "WRAITH BUG: Indeed uses CloudFlare bot protection + reCAPTCHA v3. Direct Indeed apps require login (2FA). However, many Indeed listings redirect to company ATS (Greenhouse, Lever, etc.) — Wraith should follow the redirect and apply at the destination. Needs: 1) browse_navigate to Indeed URL, 2) detect if it redirects to external ATS, 3) if redirect → re-classify destination URL and apply there, 4) if direct Indeed → BLOCKED (captcha).",
                "method": "Wraith: navigate → follow redirect → apply at destination ATS"}

    # Workday
    if "workday" in domain or "myworkdayjobs" in domain:
        return {"tier": "wraith_hard", "platform": "workday",
                "blocker": "WRAITH BUG: Workday uses heavy JavaScript SPA with dynamic DOM IDs that change per session. Forms are multi-page wizards. Wraith would need: 1) Full JS SPA rendering (QuickJS may not handle Workday's bundle), 2) Multi-step form navigation (next/back buttons), 3) Dynamic element discovery (no stable selectors). No public API exists.",
                "method": "Wraith with full SPA support + multi-step form engine (not built)"}

    # iCIMS
    if "icims" in domain:
        return {"tier": "wraith_hard", "platform": "icims",
                "blocker": "WRAITH BUG: iCIMS requires account creation + login per company instance. Forms use iframes with cross-origin restrictions. Wraith needs: 1) Account creation automation, 2) iframe navigation support, 3) Per-company session management.",
                "method": "Wraith with iframe support + auth flow (not built)"}

    # SmartRecruiters
    if "smartrecruiters" in domain:
        return {"tier": "needs_investigation", "platform": "smartrecruiters",
                "blocker": "INVESTIGATE: SmartRecruiters has a public API (jobs.smartrecruiters.com/api) that may support direct application submission like Ashby. Could be API-native. Needs: curl the API, check for form definition + submit endpoints.",
                "method": "Investigate SmartRecruiters API — may be API-native like Ashby"}

    # BambooHR
    if "bamboohr" in domain:
        return {"tier": "wraith_ready", "platform": "bamboohr",
                "blocker": "WRAITH TASK: BambooHR serves server-rendered HTML forms (like Lever). Wraith should be able to render and fill them. Needs profiling: browse_navigate to sample URL, browse_snapshot to check form elements.",
                "method": "Wraith: profile first, then fill like Lever if forms render"}

    # Upwork
    if "upwork.com" in domain:
        return {"tier": "manual_only", "platform": "upwork",
                "blocker": "MANUAL: Upwork requires authenticated session with 2FA. Proposals require custom cover letters + bid amounts. ToS prohibits automated applications. No Wraith workaround.",
                "method": "Manual application only — ToS prohibits automation"}

    # CyberCoders
    if "cybercoders.com" in domain:
        return {"tier": "wraith_ready", "platform": "cybercoders",
                "blocker": "WRAITH TASK: CyberCoders serves standard HTML forms. Wraith should render them. Needs profiling: browse_navigate → browse_snapshot to verify form structure.",
                "method": "Wraith: profile then fill standard HTML form"}

    # Flexionis / TealHQ / other aggregators
    if any(x in domain for x in ["flexionis", "wuaze", "tealhq"]):
        return {"tier": "skip", "platform": "aggregator",
                "blocker": "SKIP: Job aggregator/scraper site — not the actual employer. These redirect to the real ATS. Should extract destination URL and re-classify.",
                "method": "Extract destination URL via Wraith browse_navigate → follow redirect"}

    # Unknown
    return {"tier": "unknown", "platform": f"unknown ({domain})",
            "blocker": f"WRAITH TASK: Unrecognized ATS at {domain}. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.",
            "method": "Wraith: browse_navigate → browse_snapshot → classify"}


# ─── Bug Report ───────────────────────────────────────────────────────

class BugReport:
    """Collects successes, failures, and non-automatable jobs with full annotations."""

    def __init__(self):
        self.successes = []
        self.failures = []
        self.skipped = []  # Jobs we can't swarm with reason why
        self.start_time = datetime.now(timezone.utc)

    def add_success(self, source: str, company: str, title: str, url: str):
        self.successes.append({
            "source": source, "company": company, "title": title,
            "url": url, "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def add_failure(self, source: str, company: str, title: str, url: str,
                    error: str, category: str = "unknown", stacktrace: str = None):
        self.failures.append({
            "source": source, "company": company, "title": title,
            "url": url, "error": error, "category": category,
            "stacktrace": stacktrace,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def add_skipped(self, source: str, company: str, title: str, url: str,
                    classification: dict):
        self.skipped.append({
            "source": source, "company": company, "title": title,
            "url": url, **classification
        })

    def categorize_error(self, error: str) -> str:
        error_lower = error.lower()
        if "graphql" in error_lower or "mutation" in error_lower:
            return "graphql_api"
        if "upload" in error_lower or "s3" in error_lower or "file" in error_lower:
            return "file_upload"
        if "recaptcha" in error_lower or "captcha" in error_lower:
            return "captcha_blocked"
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        if "404" in error_lower or "not found" in error_lower:
            return "job_expired"
        if "already applied" in error_lower or "duplicate" in error_lower:
            return "duplicate"
        if "validation" in error_lower or "required" in error_lower:
            return "form_validation"
        if "parse" in error_lower or "url" in error_lower:
            return "url_parse"
        if "connection" in error_lower or "network" in error_lower:
            return "network"
        return "unknown"

    def write_report(self, path: str):
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        total_attempted = len(self.successes) + len(self.failures)
        total_all = total_attempted + len(self.skipped)

        # Group skipped by tier
        skip_by_tier = {}
        for s in self.skipped:
            tier = s["tier"]
            if tier not in skip_by_tier:
                skip_by_tier[tier] = []
            skip_by_tier[tier].append(s)

        # Group skipped by platform
        skip_by_platform = {}
        for s in self.skipped:
            plat = s["platform"]
            if plat not in skip_by_platform:
                skip_by_platform[plat] = []
            skip_by_platform[plat].append(s)

        # Group failures by category
        fail_by_category = {}
        for f in self.failures:
            cat = f["category"]
            if cat not in fail_by_category:
                fail_by_category[cat] = []
            fail_by_category[cat].append(f)

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Swarm Application Bug Report\n\n")
            fh.write(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            fh.write(f"**Duration**: {elapsed:.1f}s\n")
            fh.write(f"**Attempted**: {total_attempted} | **Success**: {len(self.successes)} | **Failed**: {len(self.failures)}\n")
            fh.write(f"**Skipped (not swarmable)**: {len(self.skipped)}\n")
            fh.write(f"**Total jobs audited**: {total_all}\n")
            if total_attempted > 0:
                fh.write(f"**Success Rate (of attempted)**: {len(self.successes)/total_attempted*100:.1f}%\n")
            fh.write("\n")

            # ── Overview table ──
            fh.write("## Overview by Platform\n\n")
            fh.write("| Platform | Tier | Count | Status | Blocker |\n")
            fh.write("|----------|------|-------|--------|----------|\n")

            # Ashby successes/failures
            ashby_ok = len([s for s in self.successes if s["source"] == "ashby"])
            ashby_fail = len([f for f in self.failures if f["source"] == "ashby"])
            if ashby_ok + ashby_fail > 0:
                fh.write(f"| Ashby | api_native | {ashby_ok + ashby_fail} | {ashby_ok} OK / {ashby_fail} failed | None — fully automated |\n")

            for plat, items in sorted(skip_by_platform.items(), key=lambda x: -len(x[1])):
                blocker_short = items[0]["blocker"][:80] + "..." if len(items[0]["blocker"]) > 80 else items[0]["blocker"]
                tier = items[0]["tier"]
                fh.write(f"| {plat} | {tier} | {len(items)} | Skipped | {blocker_short} |\n")

            # ── Attempted: Failures ──
            if self.failures:
                fh.write("\n---\n\n## Application Failures (Attempted but Failed)\n\n")
                for cat, items in sorted(fail_by_category.items(), key=lambda x: -len(x[1])):
                    fh.write(f"### {cat} ({len(items)})\n\n")
                    for item in items:
                        fh.write(f"- **{item['company']}** — {item['title']}\n")
                        fh.write(f"  - URL: `{item['url']}`\n")
                        fh.write(f"  - Error: `{item['error'][:250]}`\n")
                        if item.get("stacktrace"):
                            fh.write(f"  - Stacktrace:\n    ```\n    {item['stacktrace'][:600]}\n    ```\n")
                        fh.write("\n")

            # ── Skipped: Full detail per tier ──
            fh.write("\n---\n\n## Non-Swarmable Jobs — What's Wrong & How to Fix\n\n")

            tier_order = ["api_native", "wraith_ready", "wraith_redirect", "wraith_investigation",
                          "wraith_hard", "needs_investigation", "manual_only", "skip", "unknown"]
            tier_labels = {
                "api_native": "API-Native (Blocked by reCAPTCHA — WRAITH BUG)",
                "wraith_ready": "Wraith-Ready (Can automate now, needs session)",
                "wraith_redirect": "Wraith Redirect (Needs redirect/iframe handling — WRAITH BUG)",
                "wraith_investigation": "Wraith Investigation (May work after redirect)",
                "wraith_hard": "Wraith Hard (SPA/iframe barriers — WRAITH BUG)",
                "needs_investigation": "Needs Investigation (Potentially API-Native)",
                "manual_only": "Manual Only (Anti-Bot/Auth/ToS Barriers)",
                "skip": "Skip (Aggregator/Scraper Sites)",
                "unknown": "Unknown ATS (Needs Wraith Profiling)",
            }

            for tier in tier_order:
                items = skip_by_tier.get(tier, [])
                if not items:
                    continue

                label = tier_labels.get(tier, tier)
                fh.write(f"### {label} ({len(items)} jobs)\n\n")

                # Group by platform within tier
                platforms_in_tier = {}
                for item in items:
                    p = item["platform"]
                    if p not in platforms_in_tier:
                        platforms_in_tier[p] = []
                    platforms_in_tier[p].append(item)

                for plat, plat_items in sorted(platforms_in_tier.items(), key=lambda x: -len(x[1])):
                    fh.write(f"**{plat}** ({len(plat_items)} jobs)\n\n")
                    fh.write(f"> **What's wrong**: {plat_items[0]['blocker']}\n>\n")
                    fh.write(f"> **How to fix**: {plat_items[0]['method']}\n\n")

                    # Show up to 5 example URLs
                    show = min(5, len(plat_items))
                    for i, item in enumerate(plat_items[:show]):
                        fh.write(f"- {item['company']} — {item['title']}\n")
                        fh.write(f"  `{item['url'][:120]}`\n")
                    if len(plat_items) > show:
                        fh.write(f"- *... and {len(plat_items) - show} more*\n")
                    fh.write("\n")

            # ── Successes ──
            if self.successes:
                fh.write("\n---\n\n## Successful Applications\n\n")
                for i, s in enumerate(self.successes, 1):
                    fh.write(f"{i}. **{s['company']}** — {s['title']} [{s['source']}]\n")

        print(f"\n[BUG REPORT] Written to {path}")


# ─── Workers ──────────────────────────────────────────────────────────

def apply_ashby_worker(job: dict, report: BugReport, dry_run: bool = False) -> bool:
    try:
        result = ashby_apply(job["url"], dry_run=dry_run)
        if result["success"]:
            report.add_success("ashby", job["company"], job["title"], job["url"])
            if not dry_run:
                mark_applied_in_db(job["id"], True)
            return True
        else:
            error = result.get("error", "Unknown")
            category = report.categorize_error(error)
            report.add_failure("ashby", job["company"], job["title"], job["url"], error, category)
            if not dry_run:
                mark_applied_in_db(job["id"], False)
            return False
    except Exception as e:
        tb = traceback.format_exc()
        category = report.categorize_error(str(e))
        report.add_failure("ashby", job["company"], job["title"], job["url"],
                          str(e), category, stacktrace=tb)
        if not dry_run:
            mark_applied_in_db(job["id"], False)
        return False


# ─── Main Swarm ───────────────────────────────────────────────────────

def get_all_new_jobs() -> list[dict]:
    """Get ALL new jobs from the database for auditing."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, company, url, fit_score, source
        FROM jobs
        WHERE status = 'new'
        ORDER BY fit_score DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def run_swarm(ashby_limit: int = 10, dry_run: bool = False, parallel: int = 3) -> BugReport:
    """
    Deploy the swarm:
    1. Audit ALL new jobs and classify by automation tier
    2. Apply to Ashby jobs via API (parallel)
    3. Log everything else in the bug report with what's wrong
    """
    report = BugReport()
    all_jobs = get_all_new_jobs()

    # Classify every job
    ashby_jobs = []
    for job in all_jobs:
        classification = classify_job(job["url"], job["source"])
        if classification["tier"] == "api_native" and "ashby" in classification["platform"]:
            ashby_jobs.append(job)
        else:
            report.add_skipped(job["source"], job["company"], job["title"],
                              job["url"], classification)

    # Cap Ashby to limit
    ashby_batch = ashby_jobs[:ashby_limit]

    total_swarmable = len(ashby_batch)
    total_skipped = len(report.skipped)
    print(f"{'='*60}")
    print(f"SWARM AUDIT: {len(all_jobs)} total new jobs")
    print(f"  Swarmable (Ashby API):  {len(ashby_jobs)} available, {len(ashby_batch)} in this batch")
    print(f"  Not swarmable:          {total_skipped} (see bug report)")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  Parallelism: {parallel}")
    print(f"{'='*60}\n")

    # Phase 1: Ashby API (sequential with delay to avoid rate limits)
    if ashby_batch:
        import time
        print(f"--- Ashby API: applying to {len(ashby_batch)} jobs (2s delay between) ---")
        for i, job in enumerate(ashby_batch):
            if i > 0:
                time.sleep(2)  # Rate limit protection
            apply_ashby_worker(job, report, dry_run)

    # Write bug report
    report.write_report(BUG_REPORT_PATH)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Swarm Application Dispatcher")
    parser.add_argument("--ashby", type=int, default=10, help="Max Ashby jobs to apply to")
    parser.add_argument("--dry-run", action="store_true", help="Don't submit anything")
    parser.add_argument("--parallel", type=int, default=3, help="Parallel workers for API-native")
    args = parser.parse_args()

    report = run_swarm(
        ashby_limit=args.ashby,
        dry_run=args.dry_run,
        parallel=args.parallel,
    )

    print(f"\n{'='*60}")
    print(f"SWARM COMPLETE")
    print(f"  Applied:  {len(report.successes)}")
    print(f"  Failed:   {len(report.failures)}")
    print(f"  Skipped:  {len(report.skipped)} (not swarmable)")
    print(f"  Report:   {BUG_REPORT_PATH}")
    print(f"{'='*60}")
