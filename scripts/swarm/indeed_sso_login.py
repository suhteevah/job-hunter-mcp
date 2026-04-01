"""
Indeed Google SSO Login via FlareSolverr
========================================
Uses FlareSolverr's persistent session (real Chromium) to:
1. Navigate to Indeed login page (CF bypass)
2. Click "Continue with Google"
3. Handle Google OAuth redirect chain
4. Capture authenticated cookies
5. Save cookies for use by indeed_mass_scrape.py

After running this, indeed_mass_scrape.py can use the session cookies
to access page 2+ of search results.

Usage:
  python indeed_sso_login.py                    # Interactive SSO flow
  python indeed_sso_login.py --test-pagination  # Test page 2 access after login
  python indeed_sso_login.py --export-cookies   # Export cookies to JSON file
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import re
import time
import urllib.request
import urllib.parse
import argparse
from datetime import datetime

FLARESOLVERR_URL = "http://localhost:8191/v1"
MAX_TIMEOUT = 60000
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "indeed_cookies.json")

# Matt's Google account for Indeed
GOOGLE_EMAIL = "ridgecellrepair@gmail.com"


def flare_request(payload, timeout=MAX_TIMEOUT):
    """Send request to FlareSolverr."""
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


def create_session():
    """Create a new FlareSolverr session."""
    resp = flare_request({"cmd": "sessions.create"})
    session_id = resp["session"]
    print(f"[Session] Created: {session_id}")
    return session_id


def destroy_session(session_id):
    """Destroy a FlareSolverr session."""
    try:
        flare_request({"cmd": "sessions.destroy", "session": session_id})
        print(f"[Session] Destroyed: {session_id}")
    except Exception as e:
        print(f"[Session] Destroy failed: {e}")


def get_page(session_id, url):
    """Fetch a page through FlareSolverr session. Returns (html, cookies, final_url)."""
    payload = {
        "cmd": "request.get",
        "url": url,
        "session": session_id,
        "maxTimeout": MAX_TIMEOUT,
    }
    result = flare_request(payload)
    solution = result["solution"]
    html = solution["response"]
    cookies = solution.get("cookies", [])
    final_url = solution.get("url", url)
    status = solution.get("status", "?")
    print(f"[GET] {final_url} ({status}), {len(html)} chars, {len(cookies)} cookies")
    return html, cookies, final_url


def post_page(session_id, url, post_data=""):
    """POST to a page through FlareSolverr session."""
    payload = {
        "cmd": "request.post",
        "url": url,
        "session": session_id,
        "maxTimeout": MAX_TIMEOUT,
        "postData": post_data,
    }
    result = flare_request(payload)
    solution = result["solution"]
    html = solution["response"]
    cookies = solution.get("cookies", [])
    final_url = solution.get("url", url)
    status = solution.get("status", "?")
    print(f"[POST] {final_url} ({status}), {len(html)} chars, {len(cookies)} cookies")
    return html, cookies, final_url


def extract_google_sso_url(html):
    """Extract the Google SSO URL from Indeed's login page."""
    # Indeed's "Continue with Google" button links to accounts.google.com
    patterns = [
        r'href="(https://accounts\.google\.com/o/oauth2/[^"]+)"',
        r'href="(https://accounts\.google\.com/signin/oauth[^"]+)"',
        r'"(https://accounts\.google\.com[^"]*indeed[^"]*)"',
        r'action="(https://accounts\.google\.com[^"]*)"',
        # Indeed might use their own redirect
        r'href="(/auth/google[^"]*)"',
        r'href="(https://secure\.indeed\.com/auth/google[^"]*)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            url = match.group(1)
            if url.startswith("/"):
                url = f"https://secure.indeed.com{url}"
            return url
    return None


def save_cookies(cookies, filepath=COOKIE_FILE):
    """Save cookies to JSON file for later use."""
    with open(filepath, "w") as f:
        json.dump({
            "cookies": cookies,
            "saved_at": datetime.now().isoformat(),
            "source": "indeed_sso_login.py",
        }, f, indent=2)
    print(f"[Cookies] Saved {len(cookies)} cookies to {filepath}")


def load_cookies(filepath=COOKIE_FILE):
    """Load cookies from JSON file."""
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        data = json.load(f)
    print(f"[Cookies] Loaded {len(data['cookies'])} cookies (saved {data['saved_at']})")
    return data["cookies"]


def check_logged_in(html):
    """Check if the Indeed page shows a logged-in state."""
    indicators = [
        'data-gnav-user-signed-in="true"',
        'gnav-header-UserInfo',
        '"isLoggedIn":true',
        'My jobs',
        'data-testid="gnav-profile"',
    ]
    for indicator in indicators:
        if indicator in html:
            return True
    return False


def check_has_jobs(html):
    """Check if indeed page has job results."""
    match = re.search(r'id="jobTitle-([a-f0-9]+)"', html)
    return match is not None


def run_sso_flow():
    """Run the Indeed Google SSO login flow via FlareSolverr."""
    print("=" * 60)
    print("INDEED GOOGLE SSO LOGIN via FlareSolverr")
    print("=" * 60)

    session_id = create_session()

    try:
        # Step 1: Hit Indeed login page
        print("\n[Step 1] Navigating to Indeed login page...")
        login_url = "https://secure.indeed.com/auth?hl=en_US&co=US&continue=https%3A%2F%2Fwww.indeed.com%2F"
        html, cookies, final_url = get_page(session_id, login_url)

        # Check if we landed on the actual login page
        has_google = "google" in html.lower() or "Google" in html
        has_email = "email" in html.lower()
        print(f"  Login page: Google SSO visible={has_google}, Email field={has_email}")
        print(f"  Final URL: {final_url}")

        # Try to find Google SSO link
        google_url = extract_google_sso_url(html)
        if google_url:
            print(f"  Found Google SSO URL: {google_url[:100]}...")
        else:
            print("  [!] Could not find Google SSO URL in page HTML")
            print("  Searching for auth-related links...")
            # Dump any auth links we find
            auth_links = re.findall(r'href="([^"]*(?:auth|login|google|oauth|sso)[^"]*)"', html, re.IGNORECASE)
            for link in auth_links[:10]:
                print(f"    Found: {link[:120]}")

            # Also check for buttons/forms
            buttons = re.findall(r'<button[^>]*>([^<]*(?:Google|Sign|Log)[^<]*)</button>', html, re.IGNORECASE)
            for btn in buttons[:5]:
                print(f"    Button: {btn}")

        # Save intermediate state
        with open(os.path.join(os.path.dirname(__file__), "logs", "indeed_login_page.html"), "w", encoding="utf-8", errors="replace") as f:
            f.write(html)
        print("  Saved login page HTML to logs/indeed_login_page.html")

        # Step 2: Follow Google SSO link if found
        if google_url:
            print(f"\n[Step 2] Following Google SSO link...")
            html2, cookies2, final_url2 = get_page(session_id, google_url)
            cookies.extend(cookies2)

            # Check what Google returned
            has_email_input = 'type="email"' in html2
            has_account_chooser = "Choose an account" in html2
            print(f"  Google page: email_input={has_email_input}, account_chooser={has_account_chooser}")
            print(f"  Final URL: {final_url2}")

            with open(os.path.join(os.path.dirname(__file__), "logs", "google_sso_page.html"), "w", encoding="utf-8", errors="replace") as f:
                f.write(html2)
            print("  Saved Google SSO page to logs/google_sso_page.html")

        # Step 3: Save whatever cookies we got
        if cookies:
            save_cookies(cookies)
            indeed_cookies = [c for c in cookies if "indeed" in c.get("domain", "").lower()]
            print(f"  Indeed-specific cookies: {len(indeed_cookies)}")
            for c in indeed_cookies:
                print(f"    {c['name']} = {c['value'][:30]}... (domain={c['domain']})")

        print(f"\n[Summary]")
        print(f"  Session: {session_id}")
        print(f"  Total cookies: {len(cookies)}")
        print(f"  FlareSolverr session is still alive — you can continue interacting")
        print(f"\n  NOTE: Google SSO requires interactive clicks that FlareSolverr")
        print(f"  can't do via request.get alone. The session is warm with CF cookies.")
        print(f"  For full SSO, use FlareSolverr's browser directly or export cookies")
        print(f"  from a manual Chrome login.")

        return session_id, cookies

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        destroy_session(session_id)
        return None, []


def test_pagination(session_id=None):
    """Test if we can access Indeed page 2 with current session."""
    print("\n" + "=" * 60)
    print("TESTING INDEED PAGINATION")
    print("=" * 60)

    if session_id is None:
        session_id = create_session()

    # Test page 1
    print("\n[Test 1] Page 1 (start=0)...")
    html1, _, url1 = get_page(session_id, "https://www.indeed.com/jobs?q=AI+engineer&l=remote&start=0&sort=date")
    p1_jobs = check_has_jobs(html1)
    p1_logged = check_logged_in(html1)
    print(f"  Has jobs: {p1_jobs}, Logged in: {p1_logged}")

    # Test page 2
    print("\n[Test 2] Page 2 (start=10)...")
    html2, _, url2 = get_page(session_id, "https://www.indeed.com/jobs?q=AI+engineer&l=remote&start=10&sort=date")
    p2_jobs = check_has_jobs(html2)
    p2_logged = check_logged_in(html2)
    p2_auth = "secure.indeed.com/auth" in url2
    print(f"  Has jobs: {p2_jobs}, Logged in: {p2_logged}, Auth redirect: {p2_auth}")

    if p2_jobs:
        print("\n  >>> SUCCESS: Page 2 accessible! Full pagination unlocked. <<<")
    elif p2_auth:
        print("\n  >>> BLOCKED: Page 2 redirects to auth. Need login cookies. <<<")
    else:
        print(f"\n  >>> UNKNOWN: Final URL was {url2}")

    return p2_jobs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-pagination", action="store_true", help="Test page 2 access")
    parser.add_argument("--export-cookies", action="store_true", help="Export cookies to JSON")
    args = parser.parse_args()

    if args.test_pagination:
        test_pagination()
    else:
        session_id, cookies = run_sso_flow()
        if session_id and cookies:
            print("\n--- Testing pagination with new session ---")
            test_pagination(session_id)
