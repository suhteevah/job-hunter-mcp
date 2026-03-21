# Wraith Bug Report: Cloudflare TLS Bypass & React SPA Rendering

**Date:** 2026-03-20
**Reporter:** Matt Gates (ridgecellrepair@gmail.com)
**Wraith Version:** Latest (FlareSolverr 3.4.6 configured)
**Platform:** Windows 10 Pro, Chrome 146

---

## Summary

Two critical blockers prevent Wraith from automating job applications on Indeed (Cloudflare) and Greenhouse/Ashby (React SPA). Detailed reproduction steps, root cause analysis, and proposed fixes below.

---

## Bug 1: Cloudflare Hard Block Despite Stealth TLS + Cookies + Chrome 146 Fingerprint

### Severity: Critical

### Environment
- Stealth TLS: ACTIVE (BoringSSL), 19 evasions
- Fingerprint: Chrome 146 Windows (custom-imported via `fingerprint_import`)
- Cookies: Loaded from Chrome via `cookie_load` (25 Indeed cookies including session tokens)
- IP: 174.182.244.155 (same IP that Chrome 146 uses successfully)

### Reproduction Steps

1. Verify stealth is active:
   ```
   stealth_status → "Stealth TLS: ACTIVE (BoringSSL), Evasions: 19"
   ```

2. Import Chrome 146 fingerprint (full schema with all required fields):
   ```
   fingerprint_import → "Imported: chrome_146_win (2560x1440, Win32)"
   ```

3. Export cookies from Chrome's live Indeed session (document.cookie → file → cookie_load):
   ```
   cookie_load → "Cookies loaded from C:\Users\Matt\.openclaw\cookies.json"
   ```

4. Navigate to Indeed:
   ```
   browse_navigate("https://www.indeed.com/jobs?q=software+engineer&l=remote")
   ```

### Expected Result
Indeed search results page (Chrome on the same IP, same cookies, loads fine)

### Actual Result
```
Page: "Attention Required! | Cloudflare"
@e8 [h1] "Sorry, you have been blocked"
Cloudflare Ray ID: 9df9563f8e306a01
```

### Root Cause Analysis

**The block happens at the TLS handshake level, before cookies or JS fingerprinting are evaluated.**

Evidence:
1. Chrome 146 on the same IP (174.182.244.155) loads Indeed with zero Cloudflare challenges — no `cf_clearance` cookie exists anywhere (`cookieStore.getAll()` returns zero `cf_` cookies)
2. This means Chrome passes Cloudflare purely on its **TLS fingerprint (JA3/JA4 hash)** — Cloudflare trusts real Chrome's handshake signature
3. Wraith's BoringSSL stealth produces a JA3 hash that **does not match** real Chrome 146's wire-level TLS handshake, even though the `tls_profiles` list shows Chrome 131 JA3 `cd08e31494f9531f560d64c695473da9`
4. We also tested: FlareSolverr solves the Cloudflare challenge and returns a valid `cf_clearance` cookie. Loading that cookie into Wraith and navigating **still gets blocked** — because Cloudflare ties `cf_clearance` to the solving browser's exact JA3 hash

**Key insight:** The `tls_profiles` and `fingerprint_import` features set the *declared* JA3 and User-Agent, but the *actual wire-level TLS ClientHello* produced by Wraith's Rust HTTP client doesn't match. Cloudflare validates the real handshake, not the declared fingerprint.

### Available TLS Profiles (all outdated)
```
Chrome 131 Windows — JA3: cd08e31494f9531f...
Chrome 131 macOS   — JA3: cd08e31494f9531f...
Firefox 132        — JA3: 579ccef312d18482...
Safari 18          — JA3: 773906b0efdefa24...
```
Real Chrome is at version 146. No Chrome 146 TLS profile exists, and importing one via `fingerprint_import` only affects JS-layer properties, not the actual TLS handshake.

### Workaround (working)
FlareSolverr persistent sessions bypass Cloudflare successfully:
```python
# Create session → search → fetch job descriptions
curl POST http://localhost:8191/v1 {"cmd":"request.get", "url":"https://www.indeed.com/...", "session":"<id>"}
# Returns: status 200, full HTML, all cookies including cf_clearance
```
But this is HTTP-only (fetch + parse), not interactive browsing.

### Proposed Fix

1. **Wire-level TLS spoofing**: The BoringSSL ClientHello must exactly replicate Chrome 146's cipher suite order, extensions, ALPN, supported groups, and signature algorithms — not just declare the JA3 hash
2. **Auto-update TLS profiles**: Ship profiles that match current Chrome stable (146+), not Chrome 131
3. **FlareSolverr integration in browse_navigate**: When Cloudflare is detected (title contains "Attention Required"), automatically route through FlareSolverr to solve the challenge, extract `cf_clearance` + User-Agent, and retry with those — but this only works if Wraith can match FlareSolverr's TLS fingerprint for the cookie to be valid
4. **Alternatively**: Allow Wraith to proxy requests through FlareSolverr's browser session (Selenium WebDriver) for Cloudflare-protected sites, preserving browse_click/browse_fill interactivity

---

## Bug 2: React SPA Pages Render as Empty (Greenhouse, Ashby)

### Severity: Critical

### Reproduction Steps

1. Navigate to a Greenhouse job board:
   ```
   browse_navigate("https://boards.greenhouse.io/anthropic")
   ```

2. Or a Greenhouse job application page:
   ```
   browse_navigate("https://job-boards.greenhouse.io/anthropic/jobs/4174081008")
   ```

3. Or an Ashby job board:
   ```
   browse_navigate("https://jobs.ashbyhq.com/anthropic")
   ```

### Expected Result
Rendered page with job listings, application form fields, file upload buttons

### Actual Result
```
Page: "" (https://boards.greenhouse.io/anthropic)
@e1 [html] ""
@e2 [body] ""
```
`browse_extract` returns:
```
# Untitled
---
0 links | ~0 tokens
```

### Root Cause
Greenhouse and Ashby are React Single Page Applications. The HTML contains only a `<div id="root"></div>` mount point — all content is rendered client-side by JavaScript.

Wraith's QuickJS engine handles basic JS but cannot execute React's virtual DOM rendering pipeline, which requires:
- `requestAnimationFrame` / `requestIdleCallback`
- Full DOM mutation observer support
- CSS-in-JS runtime (styled-components / emotion)
- Webpack/Vite chunk loading (dynamic imports)
- React 18 concurrent rendering APIs

### What DOES Work
The **Greenhouse REST API** works perfectly through Wraith:
```
browse_navigate("https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true")
→ 6.2MB JSON response with all jobs, descriptions, questions
```
But the **submit endpoint** (`POST .../candidates`) now returns 404 — Greenhouse has deprecated their public submission API in favor of their React frontend (with CSRF + reCAPTCHA).

### Workaround
Playwright headless Chromium (separate from Wraith) handles React SPAs with 97.5% success rate on Ashby, ~60% on Greenhouse.

### Proposed Fix

1. **Servo engine for SPA rendering**: Wraith reportedly has Servo integration. If Servo can execute React's JS bundle and produce a rendered DOM, `browse_navigate` should fall back to Servo when QuickJS returns an empty body
2. **Hybrid mode**: Detect empty `<body>` after QuickJS execution → re-render with Servo → return the Servo-rendered snapshot
3. **SPA detection heuristic**: If `<body>` has only a single `<div id="root">` or `<div id="app">`, the page is a SPA that needs a full browser engine

---

## Bug 3: `cookie_import_chrome` Looks in Wrong Path (Minor)

### Reproduction
```
cookie_import_chrome(domain="indeed.com")
→ "Chrome cookie DB not found at: C:\Users\Matt\AppData\Local\Google\Chrome\User Data\Default\Cookies"
```

### Root Cause
Modern Chrome (v96+) moved the cookie database from:
- Old: `<Profile>/Cookies`
- New: `<Profile>/Network/Cookies`

### Fix
Check both paths: `<Profile>/Cookies` and `<Profile>/Network/Cookies`

---

## Bug 4: `fingerprint_import` Schema Undocumented (Minor)

### Issue
The `fingerprint_import` tool requires a very specific JSON schema with 30+ fields, but there's no documentation or error message showing the full schema. Each missing field produces a separate error:

```
Import failed: missing field `accept_language`
Import failed: missing field `language`
Import failed: missing field `vendor`
Import failed: missing field `screen_width`
Import failed: missing field `pixel_depth`
Import failed: missing field `device_pixel_ratio`
Import failed: missing field `timezone_offset`
Import failed: missing field `avail_width`
Import failed: missing field `plugins`
Import failed: missing field `automation_detected`
Import failed: missing field `captured_at`
Import failed: missing field `source_browser`
Import failed: missing field `raw_json`
```

It took 13 round-trips to discover the full schema.

### Fix
Either:
1. Return the full list of required fields in a single error message
2. Accept partial fingerprints and fill defaults for missing fields
3. Provide a `fingerprint_capture` tool that generates the JSON from the current browser session

### Complete Working Schema (discovered empirically)
```json
{
  "id": "string (required)",
  "name": "string",
  "user_agent": "string",
  "accept_language": "string",
  "accept_encoding": "string",
  "accept": "string",
  "ja3": "string",
  "ja4": "string",
  "http2_window_size": "number",
  "sec_ch_ua": "string",
  "sec_ch_ua_mobile": "string",
  "sec_ch_ua_platform": "string",
  "sec_fetch_dest": "string",
  "sec_fetch_mode": "string",
  "sec_fetch_site": "string",
  "sec_fetch_user": "string",
  "upgrade_insecure_requests": "string",
  "cache_control": "string",
  "language": "string",
  "languages": ["string"],
  "vendor": "string",
  "vendor_sub": "string",
  "platform": "string",
  "app_name": "string",
  "app_code_name": "string",
  "app_version": "string",
  "product": "string",
  "product_sub": "string",
  "screen_width": "number",
  "screen_height": "number",
  "avail_width": "number",
  "avail_height": "number",
  "inner_width": "number",
  "inner_height": "number",
  "outer_width": "number",
  "outer_height": "number",
  "color_depth": "number",
  "pixel_depth": "number",
  "pixel_ratio": "number",
  "device_pixel_ratio": "number",
  "timezone": "string",
  "timezone_offset": "number",
  "hardware_concurrency": "number",
  "device_memory": "number",
  "max_touch_points": "number",
  "do_not_track": "string",
  "cookie_enabled": "boolean",
  "java_enabled": "boolean",
  "pdf_viewer_enabled": "boolean",
  "online": "boolean",
  "webdriver": "boolean",
  "connection_type": "string",
  "plugins_length": "number",
  "plugins": ["string"],
  "mime_types_length": "number",
  "mime_types": ["string"],
  "automation_detected": "boolean",
  "chrome_app": "boolean",
  "chrome_runtime": "boolean",
  "permissions_query": "boolean",
  "notification_permission": "string",
  "canvas_hash": "string",
  "audio_hash": "string",
  "fonts": ["string"],
  "speech_synthesis_voices": ["string"],
  "media_devices": ["string"],
  "captured_at": "string (ISO 8601)",
  "source_url": "string",
  "source_browser": "string",
  "source_os": "string",
  "raw_json": "string",
  "webgl_vendor": "string",
  "webgl_renderer": "string"
}
```

---

## Environment Details

```
OS: Windows 10 Pro 10.0.19045
Chrome: 146.0.0.0
IP: 174.182.244.155
Screen: 2560x1440
GPU: NVIDIA GeForce RTX 3070 Ti
CPU Cores: 16
RAM: 8GB (reported to navigator)
FlareSolverr: 3.4.6 (localhost:8191)
```

## Files

- `J:/job-hunter-mcp/chrome146_fingerprint.json` — Complete Chrome 146 fingerprint (working import)
- `J:/job-hunter-mcp/flaresolverr_indeed.py` — FlareSolverr session proxy workaround for Indeed
- `C:\Users\Matt\.openclaw\cookies.json` — Indeed cookies exported from Chrome
