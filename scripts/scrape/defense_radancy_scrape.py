#!/usr/bin/env python3
"""
Defense contractor job scraper — Radancy (TalentBrew) and Phenom sites.

Uses Wraith MCP client (CDP mode) to navigate, extract, and paginate:
  - Boeing         (Radancy/TalentBrew)  — jobs.boeing.com/search-jobs
  - Lockheed Martin(Radancy/TalentBrew)  — lockheedmartinjobs.com/search-jobs
  - L3Harris       (Radancy/TalentBrew)  — careers.l3harris.com/en/search-jobs
  - MITRE          (Phenom)              — careers.mitre.org/us/en/search-results
  - RTX/Raytheon   (Phenom/CF)           — careers.rtx.com (FlareSolverr if needed)

All jobs are inserted into the SQLite DB.
After scraping, score_all_unscored.py is run.

Snapshot format used:
  - Radancy (TalentBrew): extract('markdown') produces job lines like:
      - [Job Title](/job/city/slug/company_id/job_id) City, State Date
  - Phenom: extract('markdown') produces:
      - [Job Title](https://careers.site/us/en/job/RXXXXXX/Job-Title-Slug) Location info
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import os
import re
import sqlite3
import subprocess
import time
import random
from datetime import datetime, timezone

# ─── Paths ──────────────────────────────────────────────────────────────────
DB_PATH    = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
VENV_PY    = r"J:\job-hunter-mcp\.venv\Scripts\python.exe"
SCORER     = r"J:\job-hunter-mcp\scripts\db_utils\score_all_unscored.py"
CLIENT_DIR = r"J:\job-hunter-mcp\scripts\swarm"

sys.path.insert(0, CLIENT_DIR)
from wraith_mcp_client import WraithMCPClient  # noqa: E402

# ─── Scoring keywords ────────────────────────────────────────────────────────
HIGH_KEYWORDS = [
    "ai", "ml", "machine learning", "software", "engineer", "python",
    "devops", "automation", "cloud", "systems", "data", "backend",
    "full stack", "fullstack", "platform", "sre", "reliability",
    "security", "cyber", "network", "developer", "programmer", "architect",
    "kubernetes", "docker", "terraform", "aws", "azure", "gcp", "linux",
    "api", "embedded", "firmware", "rust", "golang", "typescript",
    "information technology", "it ", "cybersecurity", "agentic", "llm",
]
PENALTY_KEYWORDS = [
    "manager", "director", "sales", "intern", "internship",
    "recruiter", "coordinator", "administrative", "assistant",
    "vp", "vice president", "chief", "officer", "analyst",
    "manufacturing", "machinist", "machining", "welder", "technician",
    "logistics", "supply chain", "quality assurance", "accountant",
    "human resources", "public relations", "legal counsel", "attorney",
    "pilot", "flight operations", "program management",
]
BONUS_KEYWORDS = ["remote", "work from home", "distributed", "anywhere"]


def score_job(title: str, location: str = "") -> tuple[float, str]:
    t   = title.lower()
    loc = (location or "").lower()
    combined = f"{t} {loc}"
    score = 0.3
    reasons = []
    for kw in HIGH_KEYWORDS:
        if kw in t:
            score += 0.08
            reasons.append(f"+{kw}")
    for kw in PENALTY_KEYWORDS:
        if kw in t:
            score -= 0.12
            reasons.append(f"-{kw}")
    for kw in BONUS_KEYWORDS:
        if kw in combined:
            score += 0.1
            reasons.append("+remote")
            break
    return round(max(0.0, min(1.0, score)), 3), "; ".join(reasons[:8]) or "baseline"


def make_id(source: str, source_id: str) -> str:
    return hashlib.md5(f"{source}:{source_id}".encode()).hexdigest()


# ─── DB helpers ──────────────────────────────────────────────────────────────

def insert_jobs(jobs_to_insert: list[dict]) -> int:
    """Upsert jobs into DB. Returns count of newly inserted rows."""
    if not jobs_to_insert:
        return 0
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur  = conn.cursor()
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inserted = 0
    for j in jobs_to_insert:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO jobs
                   (id, source, source_id, title, company, url, location,
                    salary, job_type, category, description, tags,
                    date_posted, date_found, fit_score, fit_reason,
                    status, notes, cover_letter, applied_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    j["id"], j["source"], j["source_id"], j["title"],
                    j["company"], j["url"], j.get("location", ""),
                    "", "", j.get("category", "defense"), "", "",
                    j.get("date_posted", ""), now,
                    j.get("fit_score", 0.0), j.get("fit_reason", ""),
                    "new", "", "", "",
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"  [DB ERROR] {e}")
    conn.commit()
    conn.close()
    return inserted


# ─── Markdown parsers ─────────────────────────────────────────────────────────

# Category prefixes used in L3Harris link text (appear before the city/state)
_L3_CATEGORIES = [
    "Engineering, Services", "Engineering Services", "Engineering Leadership",
    "Engineering", "Manufacturing", "Finance", "Legal", "Contracts",
    "Supply, Chain", "Supply Chain", "Information Technology", "Human Resources",
    "Program Management", "Quality", "Security", "Business", "Communications",
    "Operations", "Research", "Co-Op", "New, Grads", "New Grads",
    "Flight Operations", "Business Development",
]


def _strip_l3_category(part: str) -> str:
    """Strip L3Harris category prefix from the category+location string."""
    p = part.strip()
    for cat in _L3_CATEGORIES:
        if p.startswith(cat):
            loc = p[len(cat):].strip().lstrip('|').strip()
            if loc:
                return loc
    # Fallback: find first city/state or "Multiple Locations" pattern
    loc_m = re.search(
        r'(?:Multiple Locations|[A-Z][a-zA-Z\s\-]+,\s*[A-Z][a-zA-Z]+)',
        p,
    )
    if loc_m:
        return p[loc_m.start():].strip()
    return p


def parse_radancy_markdown(markdown: str, company_name: str, source: str,
                            base_domain: str) -> list[dict]:
    """
    Parse a Radancy/TalentBrew extract(markdown) response.

    Two formats seen in the wild:

    Boeing / Lockheed (single-line):
      - [Job Title](/job/city/slug/company_id/job_id) City, State Date

    L3Harris (multiline — h2 inside link):
      - [ \n\n## Job Title\n\n Category City, State ](/en/job/city/slug/id/job_id)
    """
    jobs = []
    seen_ids: set[str] = set()

    # For Lockheed/Boeing: only parse the "Search Results" section to avoid
    # duplicate Featured Jobs entries (which lack location data).
    # If the heading isn't found, fall back to full markdown.
    search_section = markdown
    for heading in ("# Search Results", "## Search Results", "# Search our Job"):
        idx = markdown.find(heading)
        if idx >= 0:
            search_section = markdown[idx:]
            break

    # Multiline-aware pattern: captures everything between [ and ]( URL )
    # We use re.DOTALL so . matches newlines inside the bracket group.
    # IMPORTANT: use [^\S\n]* (horizontal space only) after ) to avoid consuming
    # the newline that separates list items.
    pattern = re.compile(
        r'-\s+\[([^\]]*?)\]\((/(?:en/)?job/[^\)]+)\)[^\S\n]*([^\n]{0,150})',
        re.DOTALL,
    )

    for m in pattern.finditer(search_section):
        raw_title = m.group(1)
        rel_url   = m.group(2).strip()
        rest      = m.group(3).strip()

        # Build full URL
        url = f"https://{base_domain}{rel_url}"

        # ── Title extraction ─────────────────────────────────────────────────
        # Two formats:
        #   A) Lockheed/Boeing: [Job Title](/job/...) Location Date
        #      → raw_title is clean
        #   B) L3Harris: [ \n\n## Job Title\n\n Category City, ST ]
        #      → raw_title has ##heading + category/location inside the link

        # Split on double-newlines to find the heading part
        nl_parts = [p.strip() for p in re.split(r'\n\n+', raw_title) if p.strip()]

        if nl_parts and any('##' in p for p in nl_parts):
            # ── L3Harris format: [ \n\n## Title\n\n Category Location ]
            title = ""
            inline_location = ""
            for part in nl_parts:
                if part.startswith('#'):
                    title = part.lstrip('#').strip()
                elif title and not inline_location:
                    inline_location = _strip_l3_category(part)
            location    = inline_location
            date_posted = ""

        elif re.search(r'Date\s+Posted:', raw_title):
            # ── Lockheed format: [ Title City, State Date Posted: MM/DD/YYYY Job ID: XXXXX ]
            # Everything is inside the brackets; nothing useful in `rest`
            inner = re.sub(r'\s+', ' ', raw_title).strip()
            # Extract date
            date_m = re.search(r'Date\s+Posted:\s*(\d{2}/\d{2}/\d{4})', inner)
            date_posted = date_m.group(1) if date_m else ""
            # Strip from "Date Posted:" onward
            inner_clean = inner[:date_m.start()].strip() if date_m else inner
            # Strip "Job ID: XXXXX" if present
            inner_clean = re.sub(r'\s*Job\s+ID:.*$', '', inner_clean, flags=re.IGNORECASE).strip()
            # Now inner_clean = "Title City, State" or "Title Multiple Locations"
            # Strategy: use the city from the URL slug to anchor the split.
            city_slug = re.match(r'/(?:en/)?job/([^/]+)/', rel_url)
            city_from_slug = city_slug.group(1).replace('-', ' ').title() if city_slug else ""
            if city_from_slug and city_from_slug.lower() in inner_clean.lower():
                # Find where city appears in inner_clean
                city_pos = inner_clean.lower().find(city_from_slug.lower())
                if city_pos > 3:
                    title    = inner_clean[:city_pos].strip()
                    location = inner_clean[city_pos:].strip()
                else:
                    # City is at the start — title must come from the URL slug
                    job_slug_m = re.match(r'/(?:en/)?job/[^/]+/([^/]+)/', rel_url)
                    if job_slug_m:
                        title = job_slug_m.group(1).replace('-', ' ').title()
                    else:
                        title = inner_clean
                    location = inner_clean
            elif "Multiple Locations" in inner_clean:
                loc_start = inner_clean.index("Multiple Locations")
                title    = inner_clean[:loc_start].strip()
                location = "Multiple Locations"
            else:
                # Fallback: no location found
                title    = inner_clean
                location = ""

        else:
            # ── Boeing format: [Title](/job/...) City, State Date (title only inside brackets)
            title = re.sub(r'\s+', ' ', raw_title).strip()
            location    = rest.strip()
            date_posted = ""

            date_m = re.search(r'Date\s+Posted:\s*(\d{2}/\d{2}/\d{4})', rest)
            if date_m:
                date_posted = date_m.group(1)
                location    = rest[:date_m.start()].strip()
            else:
                date_m2 = re.search(r'\d{2}/\d{2}/\d{4}', rest)
                if date_m2:
                    date_posted = date_m2.group(0)
                    location    = rest[:date_m2.start()].strip().rstrip(',').strip()
                else:
                    date_m3 = re.search(
                        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s*\d{4}',
                        rest, re.IGNORECASE,
                    )
                    if date_m3:
                        date_posted = date_m3.group(0)
                        location    = rest[:date_m3.start()].strip()

        # Strip badge/image markup and "Pin" suffix from location
        location = re.sub(r'!\[.*?\].*$', '', location).strip()
        location = re.sub(r'\s+Pin\s*$', '', location).strip()
        location = re.sub(r'Date\s+Posted:.*$', '', location, flags=re.IGNORECASE).strip()

        # Skip obviously non-job links
        lower = title.lower()
        if any(skip in lower for skip in [
            "next", "previous", "prev", "download transcript", "view all",
            "join our talent", "sign up", "talent community", "find u.s.",
            "search", "careers at", "we're hiring!", "job alert",
        ]):
            continue
        if len(title) < 4:
            continue

        # Source ID: last numeric segment in the URL path
        parts    = rel_url.rstrip('/').split('/')
        id_parts = [p for p in parts if p.isdigit()]
        source_id = id_parts[-1] if id_parts else hashlib.md5(url.encode()).hexdigest()[:12]

        uid = make_id(source, source_id)
        if uid in seen_ids:
            continue
        seen_ids.add(uid)

        sc, reason = score_job(title, location)
        jobs.append({
            "id":          uid,
            "source":      source,
            "source_id":   source_id,
            "title":       title,
            "company":     company_name,
            "url":         url,
            "location":    location,
            "date_posted": date_posted,
            "fit_score":   sc,
            "fit_reason":  reason,
            "category":    "defense",
        })

    return jobs


def parse_phenom_markdown(markdown: str, company_name: str, source: str,
                           domain: str) -> list[dict]:
    """
    Parse a Phenom career page extract(markdown) response.

    Job lines look like:
      - [Job Title](https://careers.site/us/en/job/RXXXXXX/Job-Title-Slug) ...
    """
    jobs = []
    seen_ids: set[str] = set()

    # Match: - [title](https://domain/...job/ID/slug)
    pattern = re.compile(
        r'-\s+\[([^\]]{4,150})\]\((https?://' + re.escape(domain) + r'/[^)]+/job/[^)]+)\)',
        re.MULTILINE,
    )

    for m in pattern.finditer(markdown):
        title = m.group(1).strip()
        url   = m.group(2).strip()

        # Skip save/alert links
        lower = title.lower()
        if any(skip in lower for skip in ["save ", "prev", "next", "join", "sign up", "subscribe"]):
            continue

        # Source ID from URL
        parts = url.rstrip('/').split('/')
        # Phenom job IDs look like R116302
        id_parts = [p for p in parts if re.match(r'^R\d{5,}$', p, re.IGNORECASE)]
        source_id = id_parts[0] if id_parts else hashlib.md5(url.encode()).hexdigest()[:12]

        uid = make_id(source, source_id)
        if uid in seen_ids:
            continue
        seen_ids.add(uid)

        # Location: appears in lines after the job link
        location = ""

        sc, reason = score_job(title, location)
        jobs.append({
            "id":          uid,
            "source":      source,
            "source_id":   source_id,
            "title":       title,
            "company":     company_name,
            "url":         url,
            "location":    location,
            "date_posted": "",
            "fit_score":   sc,
            "fit_reason":  reason,
            "category":    "defense",
        })

    return jobs


def extract_total_pages_radancy(markdown: str) -> int | None:
    """Parse 'Pageof 95Go' from Radancy markdown."""
    m = re.search(r'[Pp]age\s*of\s*(\d+)\s*Go', markdown)
    if m:
        return int(m.group(1))
    return None


def extract_total_pages_phenom(markdown: str) -> int | None:
    """Parse 'Showing 1 - 10 of 79 jobs' from Phenom markdown."""
    m = re.search(r'Showing\s+\d+\s+-\s+(\d+)\s+of\s+(\d+)\s+jobs', markdown, re.IGNORECASE)
    if m:
        per_page = int(m.group(1))
        total    = int(m.group(2))
        return max(1, (total + per_page - 1) // per_page)
    return None


# ─── Cookie consent helper ───────────────────────────────────────────────────

def dismiss_cookie_consent(client: WraithMCPClient, snap: str) -> str:
    """Try to find and click a cookie accept button. Returns updated snapshot."""
    patterns = [
        r'@(e\d+)\s+\[button\]\s+.*Accept All Cookies',
        r'@(e\d+)\s+\[button\]\s+.*Accept Non-Essential',
        r'@(e\d+)\s+\[button\]\s+.*Accept All',
        r'@(e\d+)\s+\[link\]\s+\"Accept\"',
        r'@(e\d+)\s+\[button\]\s+.*[Aa]ccept',
    ]
    for pat in patterns:
        m = re.search(pat, snap)
        if m:
            client.click(m.group(1))
            time.sleep(2)
            return client.snapshot()
    return snap


# ─── Radancy scraper ─────────────────────────────────────────────────────────

def scrape_radancy(client: WraithMCPClient, start_url: str, company_name: str,
                   source: str, base_domain: str, max_pages: int = 100) -> list[dict]:
    """
    Scrape a Radancy/TalentBrew career site.
    Pagination via `<base>&p=N` appended to the search-jobs URL.
    Uses extract(markdown) to get job links with URLs.
    """
    all_jobs: list[dict] = []
    seen_ids: set[str]   = set()
    # Base URL for pagination (strip existing p= param)
    paginate_base = re.sub(r'[&?]p=\d+', '', start_url)
    # Determine separator: use ? if no existing query string, else &
    # Boeing/Lockheed/L3Harris use ?p=N (no other query params on their all-jobs URL)
    page_sep = "?" if "?" not in paginate_base else "&"

    print(f"\n  [{source.upper()}] {company_name} — {start_url}")

    # Page 1
    snap = client.navigate_cdp(start_url)
    time.sleep(random.uniform(4, 6))
    snap = client.snapshot()
    snap = dismiss_cookie_consent(client, snap)
    if "OVERLAY DETECTED" in snap:
        # One more try after another wait
        time.sleep(2)
        snap = client.snapshot()
        snap = dismiss_cookie_consent(client, snap)

    md = client.extract("markdown")
    total_pages = extract_total_pages_radancy(md)
    if total_pages:
        pages = min(max_pages, total_pages)
        print(f"    Total pages detected: {total_pages} (scraping {pages})")
    else:
        pages = max_pages
        print(f"    Total pages not detected. Scraping up to {pages}.")

    def _harvest(markdown: str, page_num: int) -> int:
        found = parse_radancy_markdown(markdown, company_name, source, base_domain)
        new = 0
        for j in found:
            if j["id"] not in seen_ids:
                seen_ids.add(j["id"])
                all_jobs.append(j)
                new += 1
        print(f"    Page {page_num:>3}: {len(found):>3} parsed, {new:>3} new "
              f"(total so far: {len(all_jobs)})")
        return new

    _harvest(md, 1)

    consecutive_empty = 0
    for page in range(2, pages + 1):
        # Radancy pagination: ?p=N for clean URLs, &p=N if query string already present
        page_url = f"{paginate_base}{page_sep}p={page}"
        client.navigate_cdp(page_url)
        time.sleep(random.uniform(3, 5))
        md = client.extract("markdown")
        new = _harvest(md, page)
        if new == 0:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                print(f"    3 consecutive empty pages, stopping early.")
                break
        else:
            consecutive_empty = 0

    print(f"  [{source.upper()}] Done: {len(all_jobs)} unique jobs")
    return all_jobs


# ─── Phenom scraper ───────────────────────────────────────────────────────────

def scrape_phenom(client: WraithMCPClient, start_url: str, company_name: str,
                  source: str, domain: str, max_pages: int = 50) -> list[dict]:
    """
    Scrape a Phenom career site.
    Pagination via `&from=N&s=1` (10 results per page).
    """
    all_jobs: list[dict] = []
    seen_ids: set[str]   = set()

    # Strip existing from= param
    base_url = re.sub(r'[&?]from=\d+', '', start_url)
    base_url = re.sub(r'[&?]s=\d+', '', base_url)
    sep = "&" if "?" in base_url else "?"

    print(f"\n  [{source.upper()}] {company_name} (Phenom) — {start_url}")

    snap = client.navigate_cdp(start_url)
    time.sleep(random.uniform(4, 6))

    # Check for Cloudflare challenge
    snap_text = client.snapshot()
    if "security verification" in snap_text.lower() or "just a moment" in snap_text.lower():
        print(f"    [CF] Cloudflare challenge detected — waiting for FlareSolverr bypass...")
        time.sleep(10)
        snap_text = client.snapshot()
        if "security verification" in snap_text.lower():
            print(f"    [CF] Still blocked after wait. Skipping {source}.")
            return []

    md = client.extract("markdown")
    total_pages = extract_total_pages_phenom(md)
    if total_pages:
        pages = min(max_pages, total_pages)
        print(f"    Total pages detected: {total_pages} (scraping {pages})")
    else:
        pages = max_pages
        print(f"    Total pages not detected. Scraping up to {pages}.")

    def _harvest(markdown: str, page_num: int) -> int:
        found = parse_phenom_markdown(markdown, company_name, source, domain)
        new = 0
        for j in found:
            if j["id"] not in seen_ids:
                seen_ids.add(j["id"])
                all_jobs.append(j)
                new += 1
        print(f"    Page {page_num:>3}: {len(found):>3} parsed, {new:>3} new "
              f"(total so far: {len(all_jobs)})")
        return new

    _harvest(md, 1)

    for page in range(2, pages + 1):
        offset   = (page - 1) * 10
        page_url = f"{base_url}{sep}from={offset}&s=1"
        client.navigate_cdp(page_url)
        time.sleep(random.uniform(3, 5))
        md = client.extract("markdown")
        new = _harvest(md, page)
        if new == 0:
            print(f"    No new jobs on page {page}, stopping.")
            break

    print(f"  [{source.upper()}] Done: {len(all_jobs)} unique jobs")
    return all_jobs


# ─── Site definitions ─────────────────────────────────────────────────────────

RADANCY_SITES = [
    {
        "company":    "Boeing",
        "source":     "boeing",
        "url":        "https://jobs.boeing.com/search-jobs",
        "domain":     "jobs.boeing.com",
        "max_pages":  100,
    },
    {
        "company":    "Lockheed Martin",
        "source":     "lockheed",
        "url":        "https://www.lockheedmartinjobs.com/search-jobs",
        "domain":     "www.lockheedmartinjobs.com",
        "max_pages":  250,  # ~3,366 jobs / 15 per page = 225 pages
    },
    {
        "company":    "L3Harris",
        "source":     "l3harris",
        "url":        "https://careers.l3harris.com/en/search-jobs",
        "domain":     "careers.l3harris.com",
        "max_pages":  120,
    },
]

PHENOM_SITES = [
    {
        "company":   "MITRE",
        "source":    "mitre",
        "queries": [
            "https://careers.mitre.org/us/en/search-results?keywords=software+engineer",
            "https://careers.mitre.org/us/en/search-results?keywords=cybersecurity+engineer",
            "https://careers.mitre.org/us/en/search-results?keywords=AI+engineer",
            "https://careers.mitre.org/us/en/search-results?keywords=data+engineer",
            "https://careers.mitre.org/us/en/search-results?keywords=systems+engineer",
        ],
        "domain":    "careers.mitre.org",
        "max_pages": 20,
    },
    {
        "company":   "Raytheon/RTX",
        "source":    "raytheon",
        "queries": [
            "https://careers.rtx.com/en/search-jobs",
        ],
        "domain":    "careers.rtx.com",
        "max_pages": 50,
    },
]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("  DEFENSE CONTRACTOR SCRAPER — Radancy (TalentBrew) + Phenom")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    client = WraithMCPClient(
        binary_path=r"J:\wraith-browser\target\release\wraith-browser.exe"
    )
    print("\nStarting Wraith MCP client...")
    client.start()
    print(f"  Engine: {client.engine_status()}")

    company_totals: dict[str, dict]  = {}
    grand_found    = 0
    grand_inserted = 0

    # ── Radancy sites (TalentBrew) ────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("  RADANCY / TALENTBREW SITES")
    print("─" * 72)

    for site in RADANCY_SITES:
        company    = site["company"]
        source     = site["source"]
        url        = site["url"]
        domain     = site["domain"]
        max_pages  = site["max_pages"]

        jobs     = scrape_radancy(client, url, company, source, domain, max_pages)
        inserted = insert_jobs(jobs)
        company_totals[company] = {"found": len(jobs), "inserted": inserted}
        grand_found    += len(jobs)
        grand_inserted += inserted
        print(f"  [{source.upper()}] {company}: {len(jobs):,} found, {inserted:,} new in DB")
        time.sleep(random.uniform(2, 4))

    # ── Phenom sites ──────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("  PHENOM SITES")
    print("─" * 72)

    for site in PHENOM_SITES:
        company    = site["company"]
        source     = site["source"]
        queries    = site["queries"]
        domain     = site["domain"]
        max_pages  = site["max_pages"]

        site_jobs: list[dict] = []
        seen_ids:  set[str]   = set()

        for q_url in queries:
            kw = re.search(r'keywords?=([^&]+)', q_url)
            kw_str = kw.group(1).replace("+", " ") if kw else q_url
            print(f"\n  Query: {kw_str}")
            batch = scrape_phenom(client, q_url, company, source, domain, max_pages)
            for j in batch:
                if j["id"] not in seen_ids:
                    seen_ids.add(j["id"])
                    site_jobs.append(j)
            time.sleep(random.uniform(2, 4))

        inserted = insert_jobs(site_jobs)
        company_totals[company] = {"found": len(site_jobs), "inserted": inserted}
        grand_found    += len(site_jobs)
        grand_inserted += inserted
        print(f"  [{source.upper()}] {company}: {len(site_jobs):,} found, {inserted:,} new in DB")

    # ── Stop Wraith ───────────────────────────────────────────────────────────
    client.stop()
    print("\nWraith stopped.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  SCRAPE SUMMARY")
    print("=" * 72)
    print(f"  {'Company':<25} {'Jobs Found':>12} {'New in DB':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    for company, stats in sorted(company_totals.items(), key=lambda x: -x[1]["found"]):
        print(f"  {company:<25} {stats['found']:>12,} {stats['inserted']:>12,}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'TOTAL':<25} {grand_found:>12,} {grand_inserted:>12,}")

    # ── Run scorer ────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  RUNNING SCORER — score_all_unscored.py")
    print("=" * 72)
    try:
        result = subprocess.run(
            [VENV_PY, SCORER],
            capture_output=False,
            timeout=600,
        )
        if result.returncode != 0:
            print(f"  [WARN] Scorer exited with code {result.returncode}")
        else:
            print("  Scorer completed OK.")
    except subprocess.TimeoutExpired:
        print("  [WARN] Scorer timed out after 10 minutes.")
    except Exception as e:
        print(f"  [ERROR] Could not run scorer: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
