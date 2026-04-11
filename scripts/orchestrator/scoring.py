"""Hyper-selective scoring for the orchestrator.

Applies the rules in `.pipeline/filters.yaml`. Two scorers:
  * `score_upwork(job, filters)`  — for IMAP-derived Upwork dicts
  * `score_ats(job, filters)`     — for SQLite-derived ATS dicts

Both return a `ScoreResult` with composite 0-100, a hit/miss flag, and a
list of human-readable reasons. Reasons matter — they go into the daily
report so the user can see WHY something was rejected (or surfaced).

Sniper-mode posture: when in doubt, REJECT. False negatives are cheap;
false positives waste connects or trigger bot flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ScoreResult:
    job: dict[str, Any]
    composite: float
    passed: bool
    reasons: list[str] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)


# ─── Helpers ───────────────────────────────────────────────────────────────


def _text_blob(job: dict[str, Any]) -> str:
    """Concatenate searchable text fields, lowercased."""
    parts = [
        str(job.get("title") or ""),
        str(job.get("description") or ""),
        str(job.get("tags") or ""),
        str(job.get("company") or ""),
    ]
    return " ".join(parts).lower()


def _contains_any(text: str, needles: list[str]) -> str | None:
    """Returns the first matching needle, or None."""
    for n in needles:
        if n.lower() in text:
            return n
    return None


def _hours_old(job: dict[str, Any]) -> float | None:
    """Returns age in hours from `posted_on` (Upwork) or `date_posted` (ATS).
    None if unparseable."""
    raw = job.get("posted_on") or job.get("date_posted") or job.get("date_found")
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw[:19], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - dt
            return delta.total_seconds() / 3600.0
        except ValueError:
            continue
    return None


# ─── Upwork scoring ────────────────────────────────────────────────────────


def score_upwork(job: dict[str, Any], filters: dict[str, Any]) -> ScoreResult:
    """Apply Upwork hyper-selective rules. Returns a ScoreResult.

    The composite is built additively but any HARD-REJECT reason short-
    circuits the pass flag to False — composite still computes for
    visibility in the report.
    """
    rules = filters["upwork"]
    blob = _text_blob(job)
    reasons: list[str] = []
    rejections: list[str] = []
    score = 0.0

    # Hard reject: blocked keywords.
    blocked = _contains_any(blob, rules["blocked_keywords"])
    if blocked:
        rejections.append(f"contains blocked keyword: {blocked!r}")

    # Hard reject: no required keyword present.
    matched_kw = _contains_any(blob, rules["required_keywords_any"])
    if not matched_kw:
        rejections.append("no required keyword (claude/mcp/agentic/openclaw/etc.)")
    else:
        reasons.append(f"keyword hit: {matched_kw!r}")
        score += 25  # heavy weight: this is the most important signal

    # Budget gate.
    hourly_high = job.get("hourly_high")
    fixed = job.get("fixed_budget")
    min_hourly = rules["min_hourly_usd"]
    min_fixed = rules["min_fixed_usd"]

    budget_ok = False
    if hourly_high is not None and hourly_high >= min_hourly:
        budget_ok = True
        reasons.append(f"hourly ${hourly_high:.0f}/hr ≥ ${min_hourly}")
        score += 15
    elif fixed is not None and fixed >= min_fixed:
        budget_ok = True
        reasons.append(f"fixed ${fixed:.0f} ≥ ${min_fixed}")
        score += 15
    elif hourly_high is None and fixed is None:
        rejections.append("no budget extracted (need manual review)")
    else:
        rejections.append(
            f"budget too low: hr=${hourly_high} fx=${fixed} "
            f"(min hr=${min_hourly}, fx=${min_fixed})"
        )

    # Client trust signals.
    spent = job.get("client_spent")
    rating = job.get("client_rating")
    verified = job.get("payment_verified")

    if rules.get("require_payment_verified") and not verified:
        rejections.append("payment not verified")
    elif verified:
        reasons.append("payment verified")
        score += 5

    if spent is not None:
        if spent >= rules["min_client_spent_usd"]:
            reasons.append(f"client spent ${spent:.0f} ≥ ${rules['min_client_spent_usd']}")
            score += 15
        else:
            rejections.append(
                f"client spent ${spent:.0f} < ${rules['min_client_spent_usd']}"
            )
    elif not rules.get("allow_new_unrated_if_payment_verified") or not verified:
        rejections.append("client spend unknown and not new+verified")

    if rating is not None:
        if rating >= rules["min_client_rating"]:
            reasons.append(f"rating {rating} ≥ {rules['min_client_rating']}")
            score += 10
        else:
            rejections.append(f"rating {rating} < {rules['min_client_rating']}")

    # Competition gate. None == unknown == fresh post == benefit of the doubt
    # (the whole point of polling every 30min is to beat the competition).
    proposals = job.get("proposals_count")
    if proposals is not None:
        if proposals < rules["max_proposals_on_job"]:
            reasons.append(f"proposals {proposals} < {rules['max_proposals_on_job']}")
            score += 10
            if proposals < rules["ideal_proposals_under"]:
                score += 5  # bonus for super-low competition
        else:
            rejections.append(
                f"proposals {proposals} ≥ {rules['max_proposals_on_job']}"
            )
    else:
        # Unknown but fresh — give it the benefit, modest score bump
        reasons.append("proposals unknown (fresh post, will verify on click)")
        score += 5

    # Recency.
    age_hr = _hours_old(job)
    if age_hr is not None:
        if age_hr <= rules["max_age_hours"]:
            reasons.append(f"posted {age_hr:.1f}h ago ≤ {rules['max_age_hours']}h")
            score += 10
        else:
            rejections.append(f"posted {age_hr:.1f}h ago > {rules['max_age_hours']}h")
    else:
        # Unknown age — modest penalty, not a hard reject
        reasons.append("age unknown (no posted_on field)")

    composite = min(100.0, score)
    passed = (
        not rejections
        and composite >= rules["min_composite_score"]
    )

    return ScoreResult(
        job=job,
        composite=composite,
        passed=passed,
        reasons=reasons,
        rejections=rejections,
    )


# ─── ATS scoring ───────────────────────────────────────────────────────────


def score_ats(job: dict[str, Any], filters: dict[str, Any]) -> ScoreResult:
    """Apply ATS hyper-selective rules to a SQLite-derived job dict.

    The ATS pool is fully drained and we are in sniper mode, so this scorer
    is harsher than Upwork's: composite must be ≥95 and all hard rejects
    must pass.
    """
    rules = filters["ats"]
    title_lower = str(job.get("title") or "").lower()
    blob = _text_blob(job)
    reasons: list[str] = []
    rejections: list[str] = []
    score = 0.0

    # Title gate (required).
    matched = _contains_any(title_lower, rules["required_title_any"])
    if not matched:
        rejections.append("title missing required IC keyword")
    else:
        reasons.append(f"title keyword: {matched!r}")
        score += 30

    # Title gate (blocked) with manager override.
    blocked = _contains_any(title_lower, rules["blocked_title_any"])
    if blocked:
        if blocked == "manager":
            override = _contains_any(
                title_lower, rules.get("allow_manager_if_title_contains", [])
            )
            if override:
                reasons.append(f"manager override: {override!r}")
            else:
                rejections.append("title contains 'manager' (no engineering override)")
        else:
            rejections.append(f"title contains blocked term: {blocked!r}")

    # Existing DB title score.
    fit = job.get("fit_score") or 0.0
    if fit >= rules["min_title_score"]:
        reasons.append(f"db fit_score {fit} ≥ {rules['min_title_score']}")
        score += 30
    else:
        rejections.append(f"db fit_score {fit} < {rules['min_title_score']}")

    # Recency.
    age_hr = _hours_old(job)
    if age_hr is not None:
        if age_hr <= rules["max_age_hours"]:
            reasons.append(f"age {age_hr:.0f}h ≤ {rules['max_age_hours']}h")
            score += 20
        else:
            rejections.append(f"age {age_hr:.0f}h > {rules['max_age_hours']}h")

    # Bonus: keywords in description that signal real Claude/agent work.
    desc_kw = _contains_any(
        blob,
        ["claude", "anthropic", "mcp", "agentic", "ai agent", "llm orchestration"],
    )
    if desc_kw:
        reasons.append(f"description matches: {desc_kw!r}")
        score += 20

    composite = min(100.0, score)
    passed = not rejections and composite >= rules["min_composite_score"]

    return ScoreResult(
        job=job,
        composite=composite,
        passed=passed,
        reasons=reasons,
        rejections=rejections,
    )


# ─── Smoke test ────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from boards import get_new_ats_jobs, scan_upwork_emails  # noqa: PLC0415
    from state import load_filters  # noqa: PLC0415

    filters = load_filters()

    print("=" * 72)
    print("UPWORK — full filter pass on all unread alerts")
    print("=" * 72)
    upwork_jobs, _ = scan_upwork_emails()
    upwork_results = [score_upwork(j, filters) for j in upwork_jobs]
    upwork_results.sort(key=lambda r: r.composite, reverse=True)

    passes = [r for r in upwork_results if r.passed]
    print(f"\n{len(upwork_jobs)} scanned, {len(passes)} passed hyper-selective filter\n")

    print("--- TOP 5 BY COMPOSITE (regardless of pass) ---")
    for r in upwork_results[:5]:
        flag = "PASS" if r.passed else "fail"
        print(f"  [{flag}] {r.composite:5.1f}  {r.job['title'][:65]}")
        if r.reasons:
            print(f"          + {'; '.join(r.reasons[:3])}")
        if r.rejections:
            print(f"          - {'; '.join(r.rejections[:3])}")

    if passes:
        print("\n*** SHORTLIST HITS ***")
        for r in passes:
            print(f"  {r.composite:.1f}  {r.job['title']}")
            print(f"        {r.job['url']}")

    print()
    print("=" * 72)
    print("ATS — sample scoring on 100 newest greenhouse jobs")
    print("=" * 72)
    ats_jobs = get_new_ats_jobs("greenhouse", None)[:100]
    ats_results = [score_ats(j, filters) for j in ats_jobs]
    ats_passes = [r for r in ats_results if r.passed]
    print(f"\n{len(ats_jobs)} scanned, {len(ats_passes)} passed hyper-selective filter")

    if ats_passes:
        print("\n*** ATS SHORTLIST HITS ***")
        for r in ats_passes[:10]:
            print(
                f"  {r.composite:.1f}  {r.job['company']} — {r.job['title']}"
            )
