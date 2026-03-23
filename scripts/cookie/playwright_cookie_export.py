#!/usr/bin/env python3
"""
Playwright Cookie Exporter — Logs into Indeed, exports cookies for Wraith cookie_load.

Usage:
    python playwright_cookie_export.py                    # Indeed login + export
    python playwright_cookie_export.py --site linkedin    # LinkedIn login + export
    python playwright_cookie_export.py --output cookies.json

Outputs Wraith-compatible JSON cookie array.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import asyncio
import json
import os

from playwright.async_api import async_playwright


SITES = {
    "indeed": {
        "login_url": "https://secure.indeed.com/auth",
        "check_url": "https://www.indeed.com/",
        "domain": "indeed.com",
    },
    "linkedin": {
        "login_url": "https://www.linkedin.com/login",
        "check_url": "https://www.linkedin.com/feed/",
        "domain": "linkedin.com",
    },
    "glassdoor": {
        "login_url": "https://www.glassdoor.com/profile/login_input.htm",
        "check_url": "https://www.glassdoor.com/",
        "domain": "glassdoor.com",
    },
}

DEFAULT_OUTPUT = "J:/job-hunter-mcp/wraith_cookies.json"


async def login_and_export(site_key: str, output_path: str, headed: bool = True):
    site = SITES[site_key]
    print(f"[export] Launching browser for {site_key} login...", file=sys.stderr)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not headed,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )

        page = await context.new_page()

        # Navigate to login page
        print(f"[export] Navigating to {site['login_url']}...", file=sys.stderr)
        await page.goto(site["login_url"], wait_until="domcontentloaded", timeout=30000)

        # Wait for user to log in manually
        print(f"[export] >>> LOG IN MANUALLY in the browser window <<<", file=sys.stderr)
        print(f"[export] Waiting for navigation to {site['check_url']} (up to 5 min)...", file=sys.stderr)

        try:
            # Wait until we detect the user is logged in
            # Check every 2 seconds if we're on a post-login page
            for _ in range(150):  # 5 minutes
                current_url = page.url
                cookies = await context.cookies()
                domain_cookies = [c for c in cookies if site["domain"] in c.get("domain", "")]

                # Check if we have meaningful session cookies
                if len(domain_cookies) > 5 and any(
                    c["name"] in ("JSESSIONID", "indeed_rcc", "CTK", "li_at", "JSESSIONID_SEL")
                    for c in domain_cookies
                ):
                    print(f"[export] Login detected! Found {len(domain_cookies)} cookies for {site['domain']}", file=sys.stderr)
                    break

                await asyncio.sleep(2)
            else:
                print(f"[export] Timeout waiting for login. Exporting whatever cookies we have.", file=sys.stderr)

        except Exception as e:
            print(f"[export] Error during login wait: {e}", file=sys.stderr)

        # Get ALL cookies from the browser context
        all_cookies = await context.cookies()
        print(f"[export] Total cookies from browser: {len(all_cookies)}", file=sys.stderr)

        # Filter to target domain
        domain_cookies = [c for c in all_cookies if site["domain"] in c.get("domain", "")]
        print(f"[export] Cookies for {site['domain']}: {len(domain_cookies)}", file=sys.stderr)

        # Convert to Wraith cookie_load format
        wraith_cookies = []
        for c in all_cookies:  # Export ALL cookies, not just domain-filtered
            wraith_cookie = {
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
                "sameSite": c.get("sameSite", "Lax"),
            }
            if c.get("expires", -1) > 0:
                wraith_cookie["expires"] = int(c["expires"])
            wraith_cookies.append(wraith_cookie)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(wraith_cookies, f, indent=2, ensure_ascii=False)

        print(f"[export] Wrote {len(wraith_cookies)} cookies to {output_path}", file=sys.stderr)
        print(f"[export] Load into Wraith with: cookie_load(path=\"{output_path}\")", file=sys.stderr)

        await browser.close()

    return wraith_cookies


def main():
    parser = argparse.ArgumentParser(description="Export browser cookies for Wraith")
    parser.add_argument("--site", default="indeed", choices=SITES.keys(),
                        help="Site to log into (default: indeed)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Output JSON file (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--headless", action="store_true",
                        help="Run headless (you won't be able to log in manually)")
    args = parser.parse_args()

    cookies = asyncio.run(login_and_export(args.site, args.output, headed=not args.headless))
    print(f"\nExported {len(cookies)} cookies to {args.output}")


if __name__ == "__main__":
    main()
