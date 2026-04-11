"""Curated shortlist writer.

Writes `.pipeline/shortlist/current.md` — the human-readable list of jobs
that survived the hyper-selective filter and are awaiting Matt's manual
review. The current.md file is overwritten on every orchestrator run; the
previous version is rotated into `.pipeline/shortlist/archive/` first so
nothing gets lost.

This file is the ONLY apply-side surface in the entire orchestrator. There
is no script that auto-submits anything. Sniper-mode posture: surface, do
not act.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[2] / ".pipeline"
SHORTLIST_DIR = PIPELINE_DIR / "shortlist"
CURRENT_PATH = SHORTLIST_DIR / "current.md"
ARCHIVE_DIR = SHORTLIST_DIR / "archive"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _archive_current() -> None:
    """Rotate current.md into archive/ before overwriting."""
    if not CURRENT_PATH.exists():
        return
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    shutil.copy2(CURRENT_PATH, ARCHIVE_DIR / f"shortlist-{stamp}.md")


def _format_upwork_job(result: Any, idx: int) -> str:
    j = result.job
    lines: list[str] = []
    lines.append(f"### {idx}. {j.get('title', '(no title)')}")
    lines.append("")
    lines.append(f"- **URL:** {j.get('url', '(no url)')}")
    lines.append(f"- **Composite score:** {result.composite:.0f}/100")
    lines.append(f"- **Posted:** {j.get('posted_on') or j.get('date_posted_raw') or 'unknown'}")

    hr_low = j.get("hourly_low")
    hr_high = j.get("hourly_high")
    fixed = j.get("fixed_budget")
    if fixed:
        lines.append(f"- **Budget:** Fixed ${fixed:,.0f}")
    elif hr_low and hr_high:
        lines.append(f"- **Budget:** ${hr_low:.0f}–${hr_high:.0f}/hr")
    elif hr_high:
        lines.append(f"- **Budget:** ${hr_high:.0f}/hr")
    else:
        lines.append("- **Budget:** unknown (verify on click)")

    spent = j.get("client_spent")
    rating = j.get("client_rating")
    country = j.get("client_country")
    verified = j.get("payment_verified")
    client_bits = []
    if spent:
        client_bits.append(f"${spent:,.0f} spent")
    if rating:
        client_bits.append(f"{rating}★")
    if country:
        client_bits.append(country)
    if verified:
        client_bits.append("payment verified")
    lines.append(f"- **Client:** {', '.join(client_bits) if client_bits else 'unknown'}")

    if j.get("experience_level"):
        lines.append(f"- **Experience:** {j['experience_level']}")
    if j.get("duration"):
        lines.append(f"- **Duration:** {j['duration']}")
    if j.get("weekly_hours"):
        lines.append(f"- **Hours:** {j['weekly_hours']}")
    if j.get("proposals_count") is not None:
        lines.append(f"- **Proposals:** {j['proposals_count']}")
    else:
        lines.append("- **Proposals:** unknown (fresh post — verify before applying)")

    if result.reasons:
        lines.append("- **Why surfaced:**")
        for r in result.reasons:
            lines.append(f"  - {r}")

    desc = (j.get("description") or "").strip()
    if desc:
        lines.append("")
        lines.append("> " + desc[:400].replace("\n", " ").replace(">", "&gt;"))

    lines.append("")
    return "\n".join(lines)


def _format_ats_job(result: Any, idx: int) -> str:
    j = result.job
    lines: list[str] = []
    lines.append(f"### {idx}. {j.get('company', '?')} — {j.get('title', '(no title)')}")
    lines.append("")
    lines.append(f"- **URL:** {j.get('url', '(no url)')}")
    lines.append(f"- **Composite score:** {result.composite:.0f}/100")
    lines.append(f"- **Source:** {j.get('source')}")
    lines.append(f"- **Posted:** {j.get('date_posted') or j.get('date_found') or 'unknown'}")
    lines.append(f"- **Location:** {j.get('location') or 'Remote'}")
    if j.get("salary"):
        lines.append(f"- **Salary:** {j['salary']}")
    lines.append(f"- **DB fit_score:** {j.get('fit_score')}")
    if result.reasons:
        lines.append("- **Why surfaced:**")
        for r in result.reasons:
            lines.append(f"  - {r}")
    desc = (j.get("description") or "").strip()
    if desc:
        lines.append("")
        lines.append("> " + desc[:400].replace("\n", " ").replace(">", "&gt;"))
    lines.append("")
    return "\n".join(lines)


def write_shortlist(
    upwork_passes: list[Any],
    ats_passes: list[Any],
    near_misses: list[Any] | None = None,
    upwork_connects_remaining: int = 18,
) -> Path:
    """Write the shortlist markdown. Returns the path written.

    `near_misses` is an optional list of ScoreResults that scored ≥80 but
    didn't pass — useful context, kept under a separate header.
    """
    SHORTLIST_DIR.mkdir(parents=True, exist_ok=True)
    _archive_current()

    out: list[str] = []
    out.append("# Curated Shortlist — Sniper Mode")
    out.append("")
    out.append(f"_Generated {_utcnow()}_")
    out.append("")
    out.append(f"**Upwork connects remaining: {upwork_connects_remaining}**")
    out.append("")

    total_passes = len(upwork_passes) + len(ats_passes)
    if total_passes == 0:
        out.append("## Nothing passed the filter this run.")
        out.append("")
        out.append(
            "That is the expected outcome most of the time. Hyper-selective "
            "means quiet days are normal. The orchestrator will keep polling."
        )
    else:
        out.append(f"## {total_passes} job{'s' if total_passes != 1 else ''} surfaced")
        out.append("")
        out.append(
            "**Sniper protocol:** review each, click through to verify "
            "proposal count and full description, then decide manually whether "
            "to spend connects. Do NOT batch-apply."
        )
        out.append("")

    if upwork_passes:
        out.append("---")
        out.append("")
        out.append(f"## Upwork ({len(upwork_passes)})")
        out.append("")
        # Sort by composite descending
        upwork_passes_sorted = sorted(
            upwork_passes, key=lambda r: r.composite, reverse=True
        )
        for i, r in enumerate(upwork_passes_sorted, 1):
            out.append(_format_upwork_job(r, i))

    if ats_passes:
        out.append("---")
        out.append("")
        out.append(f"## ATS — Greenhouse / Ashby / Lever ({len(ats_passes)})")
        out.append("")
        ats_passes_sorted = sorted(ats_passes, key=lambda r: r.composite, reverse=True)
        for i, r in enumerate(ats_passes_sorted, 1):
            out.append(_format_ats_job(r, i))

    if near_misses:
        out.append("---")
        out.append("")
        out.append(f"## Near misses (composite ≥80, did not pass) — {len(near_misses)}")
        out.append("")
        out.append(
            "_These scored well on some axes but failed at least one hard gate. "
            "Listed for visibility, not for action._"
        )
        out.append("")
        for r in sorted(near_misses, key=lambda r: r.composite, reverse=True)[:10]:
            j = r.job
            label = (
                f"{j.get('company') or 'Upwork'} — {j.get('title', '?')[:70]}"
            )
            out.append(f"- **{r.composite:.0f}/100** · {label}")
            if j.get("url"):
                out.append(f"  - {j['url']}")
            for rej in r.rejections[:2]:
                out.append(f"  - rejected: {rej}")

    CURRENT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    return CURRENT_PATH


if __name__ == "__main__":
    # Smoke test: write an empty shortlist and a populated one.
    p = write_shortlist([], [], near_misses=None, upwork_connects_remaining=18)
    print(f"Wrote empty shortlist to {p}")
