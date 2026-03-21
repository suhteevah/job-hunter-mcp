"""
FlareSolverr Session Proxy for Indeed
=====================================
Wraith can't bypass Cloudflare's TLS fingerprinting on Indeed.
This module uses FlareSolverr (real Chromium) as a persistent session proxy.

Usage:
    from flaresolverr_indeed import IndeedSession
    session = IndeedSession()
    jobs = session.search("AI engineer python", "remote")
    html = session.get_page("https://www.indeed.com/viewjob?jk=abc123")
    session.close()
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import re
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional


FLARESOLVERR_URL = "http://localhost:8191/v1"
MAX_TIMEOUT = 60000


@dataclass
class IndeedJob:
    title: str
    company: str
    location: str
    job_key: str
    url: str
    snippet: str = ""
    salary: str = ""
    date_posted: str = ""


class IndeedSession:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._create_session()
        self.user_agent = None
        self.cookies = []
        print(f"[IndeedSession] Session: {self.session_id}")

    def _create_session(self) -> str:
        resp = self._flare_request({"cmd": "sessions.create"})
        session_id = resp["session"]
        print(f"[IndeedSession] Created session: {session_id}")
        return session_id

    def _flare_request(self, payload: dict, timeout: int = MAX_TIMEOUT) -> dict:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            FLARESOLVERR_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout // 1000 + 30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        if result.get("status") != "ok":
            raise RuntimeError(f"FlareSolverr error: {result.get('message', 'unknown')}")
        return result

    def get_page(self, url: str) -> str:
        """Fetch a page through the FlareSolverr session. Returns HTML."""
        payload = {
            "cmd": "request.get",
            "url": url,
            "session": self.session_id,
            "maxTimeout": MAX_TIMEOUT,
        }
        result = self._flare_request(payload)
        solution = result["solution"]
        self.user_agent = solution.get("userAgent")
        self.cookies = solution.get("cookies", [])
        print(f"[IndeedSession] Fetched {solution['url']} ({solution['status']}), {len(solution['response'])} chars")
        return solution["response"]

    def post_page(self, url: str, post_data: str) -> str:
        """POST to a page through the FlareSolverr session. Returns HTML."""
        payload = {
            "cmd": "request.post",
            "url": url,
            "session": self.session_id,
            "maxTimeout": MAX_TIMEOUT,
            "postData": post_data,
        }
        result = self._flare_request(payload)
        solution = result["solution"]
        self.user_agent = solution.get("userAgent")
        self.cookies = solution.get("cookies", [])
        print(f"[IndeedSession] POST {solution['url']} ({solution['status']}), {len(solution['response'])} chars")
        return solution["response"]

    def search(self, query: str, location: str = "remote", start: int = 0) -> list[IndeedJob]:
        """Search Indeed for jobs. Returns list of IndeedJob."""
        params = urllib.parse.urlencode({
            "q": query,
            "l": location,
            "start": start,
            "sort": "date",
        })
        url = f"https://www.indeed.com/jobs?{params}"
        html = self.get_page(url)
        return self._parse_job_cards(html)

    def get_job_description(self, job_key: str) -> str:
        """Fetch full job description for a job key."""
        url = f"https://www.indeed.com/viewjob?jk={job_key}&from=serp&vjs=3"
        html = self.get_page(url)
        return self._extract_description(html)

    def _parse_job_cards(self, html: str) -> list[IndeedJob]:
        """Parse job cards from Indeed search results HTML."""
        jobs = []
        seen_jks = set()

        # Indeed 2026 layout: each card has class="resultContent" and
        # a link with data-jk="<hex>" containing the job key.
        # Title: <span id="jobTitle-{jk}">{title}</span>
        # Company: <span data-testid="company-name">{company}</span>
        # Location: <div data-testid="text-location"><span>{location}</span></div>

        # Find all job title spans with their job keys
        title_pattern = re.compile(
            r'id="jobTitle-([a-f0-9]+)"[^>]*>([^<]+)<',
        )
        for match in title_pattern.finditer(html):
            jk = match.group(1)
            if jk in seen_jks:
                continue
            seen_jks.add(jk)
            title = match.group(2).strip()
            title = title.replace('&amp;', '&').replace('&#x27;', "'")

            # Get the surrounding card HTML (search forward from title)
            start = max(0, match.start() - 500)
            end = min(len(html), match.end() + 3000)
            card_html = html[start:end]

            # Company
            company_match = re.search(
                r'data-testid="company-name"[^>]*>([^<]+)<', card_html
            )
            company = company_match.group(1).strip() if company_match else "Unknown"

            # Location
            loc_match = re.search(
                r'data-testid="text-location"[^>]*>\s*<span>([^<]+)<', card_html
            )
            loc = loc_match.group(1).strip() if loc_match else ""

            # Salary (in metadata section)
            salary_match = re.search(
                r'(?:salary-snippet|salaryText|metadata salary-snippet-container|jobMetaDataGroup)[^>]*>[^<]*?(\$[\d,]+(?:\.\d{2})?\s*[-–]\s*\$[\d,]+(?:\.\d{2})?[^<]*)',
                card_html
            )
            salary = salary_match.group(1).strip() if salary_match else ""

            jobs.append(IndeedJob(
                title=title,
                company=company,
                location=loc,
                job_key=jk,
                url=f"https://www.indeed.com/viewjob?jk={jk}",
                snippet="",
                salary=salary,
            ))

        print(f"[IndeedSession] Parsed {len(jobs)} job cards")
        return jobs

    def _extract_description(self, html: str) -> str:
        """Extract job description text from viewjob page."""
        # Main description div
        desc_match = re.search(
            r'id="jobDescriptionText"[^>]*>(.*?)</div>',
            html,
            re.DOTALL
        )
        if desc_match:
            desc = desc_match.group(1)
            # Strip HTML tags, keep text
            desc = re.sub(r'<br\s*/?>', '\n', desc)
            desc = re.sub(r'<li[^>]*>', '\n- ', desc)
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = re.sub(r'&nbsp;', ' ', desc)
            desc = re.sub(r'&amp;', '&', desc)
            desc = re.sub(r'&lt;', '<', desc)
            desc = re.sub(r'&gt;', '>', desc)
            desc = re.sub(r'\n{3,}', '\n\n', desc)
            return desc.strip()
        return ""

    def close(self):
        """Destroy the FlareSolverr session."""
        try:
            self._flare_request({
                "cmd": "sessions.destroy",
                "session": self.session_id,
            })
            print(f"[IndeedSession] Session {self.session_id} destroyed")
        except Exception as e:
            print(f"[IndeedSession] Warning: session destroy failed: {e}")


if __name__ == "__main__":
    session = IndeedSession()
    try:
        print("\n=== Searching: AI engineer python, remote ===")
        jobs = session.search("AI engineer python", "remote")
        for i, job in enumerate(jobs):
            print(f"\n[{i+1}] {job.title}")
            print(f"    Company: {job.company}")
            print(f"    Location: {job.location}")
            print(f"    Salary: {job.salary or 'N/A'}")
            print(f"    URL: {job.url}")
            if job.snippet:
                print(f"    Snippet: {job.snippet[:120]}...")

        if jobs:
            print(f"\n=== Fetching description for: {jobs[0].title} ===")
            desc = session.get_job_description(jobs[0].job_key)
            print(desc[:500] if desc else "No description found")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()
