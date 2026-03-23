#!/usr/bin/env python3
"""
CDP Cookie Bridge — Extracts decrypted cookies from Chrome via DevTools Protocol.

Chrome v20 App-Bound Encryption prevents external tools from decrypting cookies.
This script launches Chrome with CDP enabled using a COPIED profile directory
(Chrome refuses --remote-debugging-port on the default user-data-dir), extracts
all cookies via Network.getAllCookies, and outputs them as JSON.

Usage:
    python cdp_cookie_bridge.py                     # All cookies
    python cdp_cookie_bridge.py --domain indeed.com # Filter by domain
    python cdp_cookie_bridge.py --inject-wraith     # Extract + inject into Wraith via cookie_set
    python cdp_cookie_bridge.py --output cookies.json

Requires: Chrome installed, no other Chrome instances running with debug port 9222.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import websocket  # pip install websocket-client


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
CDP_PORT = 9222
CDP_TIMEOUT = 15  # seconds to wait for Chrome CDP


def find_chrome():
    """Locate Chrome executable."""
    if os.path.exists(CHROME_PATH):
        return CHROME_PATH
    # Try alternate locations
    for path in [
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Chrome not found. Install Chrome or set CHROME_PATH env var.")


def copy_profile(profile_name="Default"):
    """
    Copy Chrome profile to a temp directory.
    Chrome won't enable CDP on the default user-data-dir, so we copy it.
    We only need the cookie-related files, not the full profile.
    """
    src_profile = os.path.join(CHROME_USER_DATA, profile_name)
    if not os.path.exists(src_profile):
        raise FileNotFoundError(f"Chrome profile not found: {src_profile}")

    temp_dir = tempfile.mkdtemp(prefix="cdp_cookie_bridge_")
    temp_user_data = os.path.join(temp_dir, "chrome_data")
    temp_profile = os.path.join(temp_user_data, profile_name)
    os.makedirs(temp_profile, exist_ok=True)

    # Copy Local State (contains encryption keys)
    local_state_src = os.path.join(CHROME_USER_DATA, "Local State")
    if os.path.exists(local_state_src):
        shutil.copy2(local_state_src, os.path.join(temp_user_data, "Local State"))

    # Copy cookie database
    network_dir = os.path.join(src_profile, "Network")
    if os.path.exists(network_dir):
        shutil.copytree(network_dir, os.path.join(temp_profile, "Network"))

    # Copy Preferences (needed for Chrome to recognize the profile)
    for f in ["Preferences", "Secure Preferences"]:
        src = os.path.join(src_profile, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(temp_profile, f))

    print(f"[bridge] Profile copied to {temp_user_data}", file=sys.stderr)
    return temp_dir, temp_user_data


def launch_chrome_cdp(chrome_path, user_data_dir, profile_name="Default"):
    """Launch Chrome with CDP enabled."""
    cmd = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_name}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--remote-allow-origins=*",
    ]
    print(f"[bridge] Launching Chrome CDP on port {CDP_PORT}...", file=sys.stderr)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    return proc


def wait_for_cdp(timeout=CDP_TIMEOUT):
    """Wait for Chrome CDP to be ready."""
    url = f"http://127.0.0.1:{CDP_PORT}/json/version"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            data = json.loads(resp.read())
            ws_url = data.get("webSocketDebuggerUrl")
            print(f"[bridge] CDP ready: {data.get('Browser', 'unknown')}", file=sys.stderr)
            return ws_url
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Chrome CDP did not start within {timeout}s")


def get_all_cookies(ws_url):
    """Fetch all cookies via CDP Network.getAllCookies."""
    ws = websocket.create_connection(ws_url, timeout=10)
    try:
        msg = json.dumps({"id": 1, "method": "Network.getAllCookies"})
        ws.send(msg)
        result = json.loads(ws.recv())
        cookies = result.get("result", {}).get("cookies", [])
        print(f"[bridge] Retrieved {len(cookies)} cookies from Chrome", file=sys.stderr)
        return cookies
    finally:
        ws.close()


def filter_cookies(cookies, domain=None):
    """Filter cookies by domain."""
    if not domain:
        return cookies
    # Match domain and subdomains
    filtered = []
    for c in cookies:
        cookie_domain = c.get("domain", "").lstrip(".")
        if cookie_domain == domain or cookie_domain.endswith(f".{domain}"):
            filtered.append(c)
    print(f"[bridge] Filtered to {len(filtered)} cookies for {domain}", file=sys.stderr)
    return filtered


def cleanup(proc, temp_dir):
    """Kill Chrome and clean up temp directory."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    print("[bridge] Cleaned up", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Extract Chrome cookies via CDP")
    parser.add_argument("--domain", help="Filter by domain (e.g., indeed.com)")
    parser.add_argument("--profile", default="Default", help="Chrome profile name")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    parser.add_argument("--inject-wraith", action="store_true",
                        help="Output as Wraith cookie_set commands (one per line)")
    args = parser.parse_args()

    chrome_path = find_chrome()
    temp_dir = None
    proc = None

    try:
        # Step 1: Copy profile
        temp_dir, temp_user_data = copy_profile(args.profile)

        # Step 2: Launch Chrome with CDP
        proc = launch_chrome_cdp(chrome_path, temp_user_data, args.profile)

        # Step 3: Wait for CDP
        ws_url = wait_for_cdp()

        # Step 4: Get cookies
        cookies = get_all_cookies(ws_url)
        cookies = filter_cookies(cookies, args.domain)

        # Step 5: Output
        if args.inject_wraith:
            # Output as Wraith-compatible cookie_set JSON lines
            for c in cookies:
                wraith_cookie = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c["domain"],
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                    "http_only": c.get("httpOnly", False),
                    "same_site": c.get("sameSite", "Lax"),
                }
                if c.get("expires", -1) > 0:
                    wraith_cookie["expires"] = int(c["expires"])
                print(json.dumps(wraith_cookie))
        else:
            output = json.dumps(cookies, indent=2, ensure_ascii=False)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"[bridge] Wrote {len(cookies)} cookies to {args.output}", file=sys.stderr)
            else:
                print(output)

    except Exception as e:
        print(f"[bridge] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cleanup(proc, temp_dir)


if __name__ == "__main__":
    main()
