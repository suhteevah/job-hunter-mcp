"""
Job Hunter MCP - API Integrations
Searches Remotive, Arbeitnow, and JSearch (RapidAPI) for remote jobs.
"""
import asyncio
import hashlib
import logging
import re
from typing import Optional
import httpx
from src.config import SCORING

logger = logging.getLogger("job_hunter.apis")
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _job_id(source: str, sid: str) -> str:
    return hashlib.md5(f"{source}:{sid}".encode()).hexdigest()[:16]


def _clean_html(html: str) -> str:
    if not html:
        return ""
    t = re.sub(r'<[^>]+>', ' ', html)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:4000]


def score_fit(title: str, description: str, category: str = "") -> tuple[float, str]:
    """Score job fit against Matt's profile."""
    text = f"{title} {description} {category}".lower()
    title_low = title.lower()
    reasons = []
    score = 0.0

    # Title matches
    for kw, pts in SCORING["title_keywords"].items():
        if kw in title_low:
            score += pts
            reasons.append(f"title:{kw}(+{pts})")

    # Primary skill matches
    pm = [s for s in SCORING["primary_skills"] if s in text]
    if pm:
        score += len(pm) * 5
        reasons.append(f"primary({len(pm)}): {','.join(pm[:4])}")

    # Secondary
    sm = [s for s in SCORING["secondary_skills"] if s in text]
    if sm:
        score += len(sm) * 2
        reasons.append(f"secondary({len(sm)})")

    # Negatives
    nm = [k for k in SCORING["negative_keywords"] if k in text]
    if nm:
        score -= len(nm) * 10
        reasons.append(f"neg: {','.join(nm[:3])}")

    # Bonuses
    for kw, pts in SCORING["bonus_keywords"].items():
        if kw in text:
            score += pts

    score = max(0, min(100, score))
    return round(score, 1), "; ".join(reasons) if reasons else "No strong matches"


async def search_remotive(query: str = "", category: str = "software-dev",
                          limit: int = 50) -> list[dict]:
    """Search Remotive's free API."""
    logger.info(f"[REMOTIVE] query='{query}' cat='{category}' limit={limit}")
    params = {"limit": limit}
    if query:
        params["search"] = query
    if category and category != "all":
        params["category"] = category

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get("https://remotive.com/api/remote-jobs", params=params)
            r.raise_for_status()
            data = r.json()

        jobs = []
        for j in data.get("jobs", []):
            desc = _clean_html(j.get("description", ""))
            fs, fr = score_fit(j.get("title", ""), desc, j.get("category", ""))
            sid = str(j["id"])
            jobs.append({
                "id": _job_id("remotive", sid), "source": "remotive", "source_id": sid,
                "title": j.get("title", ""), "company": j.get("company_name", ""),
                "url": j.get("url", ""),
                "location": j.get("candidate_required_location", "Worldwide"),
                "salary": j.get("salary", ""), "job_type": j.get("job_type", ""),
                "category": j.get("category", ""), "description": desc,
                "tags": j.get("tags", []), "date_posted": j.get("publication_date", ""),
                "fit_score": fs, "fit_reason": fr,
            })
        jobs.sort(key=lambda x: x["fit_score"], reverse=True)
        logger.info(f"[REMOTIVE] {len(jobs)} results, top={jobs[0]['fit_score'] if jobs else 0}")
        return jobs
    except Exception as e:
        logger.error(f"[REMOTIVE] Error: {e}")
        return []


async def search_arbeitnow(query: str = "", page: int = 1) -> list[dict]:
    """Search Arbeitnow's free API (remote jobs only)."""
    logger.info(f"[ARBEITNOW] query='{query}' page={page}")
    params = {"page": page}
    if query:
        params["search"] = query

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get("https://www.arbeitnow.com/api/job-board-api", params=params)
            r.raise_for_status()
            data = r.json()

        jobs = []
        for j in data.get("data", []):
            if not j.get("remote", False):
                continue
            desc = _clean_html(j.get("description", ""))
            fs, fr = score_fit(j.get("title", ""), desc)
            sid = str(j.get("slug", j.get("url", "")))
            jobs.append({
                "id": _job_id("arbeitnow", sid), "source": "arbeitnow", "source_id": sid,
                "title": j.get("title", ""), "company": j.get("company_name", ""),
                "url": j.get("url", ""), "location": j.get("location", "Remote"),
                "salary": "", "job_type": "", "category": ",".join(j.get("tags", [])),
                "description": desc, "tags": j.get("tags", []),
                "date_posted": str(j.get("created_at", "")),
                "fit_score": fs, "fit_reason": fr,
            })
        jobs.sort(key=lambda x: x["fit_score"], reverse=True)
        logger.info(f"[ARBEITNOW] {len(jobs)} remote results")
        return jobs
    except Exception as e:
        logger.error(f"[ARBEITNOW] Error: {e}")
        return []


async def search_jsearch(query: str, api_key: str, remote_only: bool = True,
                         page: int = 1) -> list[dict]:
    """Search JSearch via RapidAPI (aggregates Indeed/LinkedIn/Glassdoor)."""
    logger.info(f"[JSEARCH] query='{query}' remote={remote_only} page={page}")
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {
        "query": query, "page": str(page), "num_pages": "1",
        "date_posted": "week",
    }
    if remote_only:
        params["remote_jobs_only"] = "true"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get("https://jsearch.p.rapidapi.com/search",
                           headers=headers, params=params)
            r.raise_for_status()
            data = r.json()

        jobs = []
        for j in data.get("data", []):
            desc = j.get("job_description", "")[:4000]
            fs, fr = score_fit(j.get("job_title", ""), desc)
            sid = j.get("job_id", "")

            # Format salary
            sal = ""
            mn, mx = j.get("job_min_salary"), j.get("job_max_salary")
            per = j.get("job_salary_period", "")
            if mn and mx:
                sal = f"${mn:,.0f}-${mx:,.0f} {per}"
            elif mn:
                sal = f"${mn:,.0f}+ {per}"

            jobs.append({
                "id": _job_id("jsearch", sid), "source": "jsearch", "source_id": sid,
                "title": j.get("job_title", ""), "company": j.get("employer_name", ""),
                "url": j.get("job_apply_link", "") or j.get("job_google_link", ""),
                "location": j.get("job_city", "Remote"), "salary": sal,
                "job_type": j.get("job_employment_type", ""),
                "category": "", "description": desc, "tags": [],
                "date_posted": j.get("job_posted_at_datetime_utc", ""),
                "fit_score": fs, "fit_reason": fr,
            })
        jobs.sort(key=lambda x: x["fit_score"], reverse=True)
        logger.info(f"[JSEARCH] {len(jobs)} results, top={jobs[0]['fit_score'] if jobs else 0}")
        return jobs
    except Exception as e:
        logger.error(f"[JSEARCH] Error: {e}")
        return []


async def search_all(query: str, jsearch_key: Optional[str] = None,
                     category: str = "software-dev", limit: int = 50) -> dict:
    """Search all APIs, deduplicate, sort by fit."""
    logger.info(f"=== MULTI-SEARCH: '{query}' ===")

    tasks = [
        search_remotive(query, category, limit),
        search_arbeitnow(query),
    ]
    names = ["remotive", "arbeitnow"]

    if jsearch_key:
        tasks.append(search_jsearch(f"{query} remote", jsearch_key))
        names.append("jsearch")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    counts = {}
    errors = []
    for name, res in zip(names, results):
        if isinstance(res, Exception):
            logger.error(f"[{name}] FAILED: {res}")
            errors.append(f"{name}: {res}")
            counts[name] = 0
        else:
            counts[name] = len(res)
            all_jobs.extend(res)

    # Dedupe by title+company
    seen = set()
    unique = []
    for j in all_jobs:
        key = f"{j['title'].lower().strip()}:{j['company'].lower().strip()}"
        if key not in seen:
            seen.add(key)
            unique.append(j)

    unique.sort(key=lambda x: x["fit_score"], reverse=True)
    logger.info(f"=== SEARCH DONE: {len(unique)} unique from {len(names)} sources ===")

    return {
        "jobs": unique, "source_counts": counts,
        "total": len(unique), "dupes_removed": len(all_jobs) - len(unique),
        "errors": errors,
    }
