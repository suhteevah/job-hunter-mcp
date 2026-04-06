# Wraith Browser — Open Bug Report
# Last updated: 2026-03-31 (BUG-9 fixed — Indeed page 1 working via FlareSolverr)
# Maintainer: Matt Gates (ridgecellrepair@gmail.com)
# Usage: Feed this file to Wraith dev for status updates. Delete resolved items.

---

## OPEN BUGS

### BUG-12: FlareSolverr CORS error on second navigate — FIXED (2026-04-03)
- **Severity**: ~~P2~~ → **RESOLVED**
- **Root cause**: After FlareSolverr solves page 1, wraith stores `cf_clearance` cookies. On the second navigate, Tier 1 (direct fetch) replays those cookies, but Indeed sees a TLS fingerprint mismatch (wraith Firefox vs FlareSolverr Chrome) and returns "Invalid CORS request" or a fresh CF challenge.
- **Fix (attempt 1)**: Added `"Invalid CORS request"` to challenge signatures — didn't fully work because the MCP server's response varied.
- **Fix (attempt 2, WORKING)**: Added FlareSolverr domain memory. When FlareSolverr resolves a page, the domain is marked as "FlareSolverr-required" in a `HashSet`. Subsequent navigates to that domain **skip Tier 1 entirely** and go straight to FlareSolverr. No stale cookies, no CORS mismatch.
- **Binary rebuild + MCP server restart required**.
- **Performance note**: Each page costs ~8-10s (FlareSolverr Turnstile solve). For bulk pagination, the Google SSO login flow (`scripts/indeed-login.md`) is faster since authenticated cookies work directly without FlareSolverr.

### BUG-11: Indeed CF challenge escalation regression — RESOLVED (2026-04-02)
- **Severity**: ~~P1~~ → **RESOLVED** (was NOT a hydrator regression)
- **Root cause**: FlareSolverr's `maxTimeout` was 60s. After Docker restart with 410 Chrome zombie processes, FlareSolverr's cold Chrome took >60s to solve Indeed's Turnstile CAPTCHA, causing a timeout (status=0). The challenge detection and escalation chain worked correctly the entire time (`is_challenge=true` → Tier 2 → Tier 3).
- **Fix**: Bumped FlareSolverr `maxTimeout` from 60s to 120s in `try_flaresolverr_full_page()`.
- **Additional fix**: Killed 410 Chrome zombie processes and restarted FlareSolverr Docker container.
- **Verified working** (2026-04-02):
  ```
  WRAITH_FLARESOLVERR=http://localhost:8191 wraith-browser navigate "https://www.indeed.com/jobs?q=AI+engineer+remote&sort=date&filter=0"
  → Page: "Flexible Ai Engineer Remote Jobs – Apply Today to Work From Home (April 2, 2026) | Indeed"
  ```
- **Note for job-hunter**: If FlareSolverr starts hanging, check Chrome zombie count (`tasklist | grep -c chrome`). If >50, kill them all (`taskkill /F /IM chrome.exe`) and restart FlareSolverr (`docker restart flaresolverr`). The zombies accumulate from FlareSolverr's poor process cleanup.

### BUG-9: Indeed Cloudflare bypass regression — RESOLVED (2026-03-31)
- **Severity**: ~~P1~~ → **RESOLVED**
- **Fixed by**: Wraith dev session 2026-03-31. Two bugs were blocking the escalation to FlareSolverr:
  1. **Challenge detection size guard** — `is_cloudflare_challenge()` had a `>50KB → return false` heuristic. Indeed's CAPTCHA page is 61KB (bloated inline CSS), so it was never detected as a challenge. Fixed by checking definitive CF signatures (`CLOUDFLARE_STATIC_PAGE`, `cf-browser-verification`, `cf_chl_opt`) before the size guard.
  2. **CLI env var not wired** — `WRAITH_FLARESOLVERR` env var was only read by the MCP server, not the CLI binary. Added `env = "WRAITH_FLARESOLVERR"` to the clap arg. Also added `"env"` feature to clap in workspace Cargo.toml.
- **Verified working** (2026-03-31):
  ```
  WRAITH_FLARESOLVERR=http://localhost:8191 wraith-browser navigate "https://www.indeed.com/jobs?q=AI+engineer&l=remote&start=0&sort=date"
  → Challenge detected (is_challenge=true, 61KB page)
  → Tier 2 QuickJS solver (fails — expected, can't solve Turnstile)
  → Tier 3 FlareSolverr escalation (success — 2.2MB page returned)
  → Page: "Flexible Ai Engineer Jobs – Apply Today to Work From Home in Remote (March 31, 2026) | Indeed"
  ```
- **IMPORTANT for job-hunter**: Set `WRAITH_FLARESOLVERR=http://localhost:8191` in the environment when running the MCP server. The MCP server reads this env var and passes it to the engine config. Without it, Indeed will still fail (Tier 1 gets 403, no escalation path).
- **Binary rebuild required**: The fix is in the source. Run `cargo build --release` or use the pre-built binary from GitHub Releases v0.1.0 (uploaded 2026-03-31).
- **CDP path still blocked**: `browse_navigate_cdp` uses headless Chrome which Indeed blocks at the IP/fingerprint level. Use native engine + FlareSolverr instead.

### BUG-10: Indeed page 2+ requires authentication — SOLUTION AVAILABLE
- **Severity**: P2 → **HAS WORKAROUND** (login via CDP unlocks all pages)
- **Root cause**: Indeed requires login to view beyond page 1. This is an Indeed product decision.
- **Solution**: Use wraith CDP tools to log in, save cookies, then paginate with authenticated session. Full step-by-step at `J:\wraith-browser\scripts\indeed-login.md`.
- **Quick summary**:
  ```
  # 1. Login via CDP (two-step: email → password)
  browse_navigate_cdp url="https://secure.indeed.com/auth"
  browse_fill ref_id=<EMAIL_REF> text="your_email@example.com"
  browse_click ref_id=<CONTINUE_BTN>
  browse_snapshot   # React reveals password field
  browse_fill ref_id=<PASSWORD_REF> text="your_password"
  browse_click ref_id=<SIGNIN_BTN>

  # 2. Save cookies (~7 day lifespan)
  cookie_save path="~/.wraith/indeed_cookies.json"

  # 3. Use cookies for paginated search (page 2+)
  cookie_load path="~/.wraith/indeed_cookies.json"
  browse_navigate url="https://www.indeed.com/jobs?q=AI+engineer&l=remote&start=10&sort=date"
  ```
- **Requirements**: Indeed account via Google SSO or email+password. CDP mode for login (React SPA). Native engine + cookies for pagination. If Google 2FA is enabled, Matt needs to approve the phone prompt when the agent hits that step.
- **Cookie refresh**: Re-login weekly (~7 day expiry based on SURF cookie).
- **Caveat**: Indeed may show Turnstile CAPTCHA during login. CDP Chrome can handle basic challenges. If interactive Turnstile blocks, manually log in via browser → export cookies → `cookie_load`.
- **No Playwright needed**: Entire flow uses wraith CDP tools.

### BUG-8: Swarm playbooks use CSS selectors — fail on native engine and CDP @ref model
- **Severity**: P2 (playbooks run but all form steps fail)
- **Repro** (confirmed 2026-03-22):
  ```
  swarm_run_playbook playbook_yaml="greenhouse-apply" job_url="https://boards.greenhouse.io/anthropic/jobs/5098565008" variables={...}
  swarm_run_playbook playbook_yaml="lever-apply" job_url="https://jobs.lever.co/plaid/f09937a3-5edf-47c8-a9ba-69f9f5e39d86" variables={...}
  ```
- **Expected**: Playbook navigates, fills form, uploads resume, submits.
- **Actual**: Step 1 (navigate) uses native engine. For React sites (Greenhouse, Ashby), native returns 2 elements (empty React SPA). For Lever, native works but playbook uses CSS selectors like `input[name=name]`, `input[name=email]` which don't match the native engine's @ref-based DOM.
- **Root cause**: Playbooks are authored with real-browser CSS selectors (`input[name=first_name]`, `button[type=submit]`, `.postings-btn-wrapper`) but Wraith's tool model uses `@ref` IDs. The playbook engine needs to either:
  1. Use CDP for React sites (detect platform from URL and auto-switch), OR
  2. Map CSS selectors to @ref IDs using the snapshot, OR
  3. Use a hybrid approach where playbooks specify @ref-compatible patterns
- **Impact**: Playbooks are not usable as-is. Manual `browse_navigate_cdp` + `browse_fill` + `browse_click` workflow still works perfectly (proven in all tests above). The underlying Wraith apply pipeline is solid; only the playbook abstraction layer is broken.
- **Workaround**: Use direct MCP tool calls instead of playbooks. Works 100%.

### BUG-4: Chrome v20 cookie import fails (App-Bound Encryption) — NOFIX
- **Severity**: CLOSED/NOFIX — this is a Chrome security design decision by Google, not a Wraith bug. No external tool can extract Chrome cookies since v127+ App-Bound Encryption (v20 prefix). This will never be fixable.
- **Workarounds**: `playwright_cookie_export.py` → `cookie_load`, or `browse_login`, or FlareSolverr.
- **Impact**: None for job hunting — all target platforms (Greenhouse, Ashby, Lever, Indeed) use public/anonymous access.

---

## RESOLVED (confirmed 2026-03-22 full integration retest)

### RESOLVED: BUG-7 — CDP `browse_custom_dropdown` reports success but value not retained
- **Fixed**: Confirmed working 2026-03-22. React custom dropdown value now persists in snapshot.
- **Verified**: `browse_custom_dropdown ref_id=10 value="United States"` on Greenhouse Anthropic apply form → snapshot shows `@e10 [combobox] "United States +1" value="United States +1"`. Previously showed empty string.
- **Impact**: CDP can now fully replace Playwright for ALL apply forms on Greenhouse and Ashby. No more React dropdown workaround needed.

### RESOLVED: BUG-2 — CDP embed/iframe URLs render empty
- **Fixed**: Confirmed working 2026-03-22. Embed URL now renders full apply form (56+ interactive elements).
- **Verified**: `browse_navigate_cdp url="https://boards.greenhouse.io/embed/job_app?for=anthropic&token=5098565008"` returns full form with text inputs, comboboxes, file upload, submit button. Previously returned only 2 elements.

### RESOLVED: BUG-6 — Native false positive overlay detection on dropdowns
- **Fixed**: Confirmed working 2026-03-22. Zero overlay warnings on Lever board.
- **Verified**: `browse_navigate url="https://jobs.lever.co/plaid"` returns 1090 elements, all jobs rendered, no `OVERLAY DETECTED` warnings. Previously showed 4 false positives for filter dropdown menus.

### RESOLVED: BUG-1 — CDP click navigation loses page state
- **Fixed**: 2026-03-21 (commit `2dfcda2`). CDP now reconnects to new page target after navigation.
- **Verified**: `browse_navigate_cdp` Greenhouse board → `browse_click` job link → `browse_snapshot` returns full job detail page with apply form (text inputs, file upload, submit button). Multi-page CDP flows fully working.

### RESOLVED: BUG-3 — Native browse_click on links doesn't navigate
- **Fixed**: 2026-03-21 (commit `2dfcda2`). Native engine now follows link navigation on click.
- **Verified**: `browse_navigate` Lever board → `browse_click` Apply link → page navigates to full job detail with description, qualifications, salary, and apply link. No more `CLICKED_LINK:` workaround needed.

### RESOLVED: BUG-5 — Cloudflare TLS fingerprint rejection
- **Fixed**: 2026-03-21 (rebuild from latest). Native engine now passes Cloudflare TLS checks.
- **Verified 2026-03-22**: `browse_navigate url="https://www.indeed.com/jobs?q=software+engineer+remote&fromage=3"` returns 54.8KB DOM with full job listings. Cloudflare bypass confirmed still working.

### RESOLVED: CDP — Page.enable wasn't found (JSON-RPC -32601)
- **Fixed**: 2026-03-21. Root cause was connecting to `/json/version` (browser-level WebSocket) instead of `/json` (page targets). Fix: poll `/json/version` for readiness, fetch `/json` for target list, find first `type: "page"` target, connect to its `webSocketDebuggerUrl`.

### RESOLVED: Feature request — CDP proxy mode for React SPAs
- **Shipped**: 2026-03-21. `browse_navigate_cdp` now auto-detects empty React SPA pages and falls back to headless Chrome via CDP. Board scraping works for Greenhouse and Ashby.

### RESOLVED: cookie_import_chrome wrong path on Windows
- **Superseded** by BUG-4 (v20 encryption). Even with correct path, decryption fails on v20 cookies.

---

## FEATURE REQUESTS

### FR-1: CDP navigation support (follow links) — SHIPPED
- Delivered in commit `2dfcda2`. Multi-page CDP flows work end-to-end.

### FR-2: CDP form interaction (fill, select, radio, checkbox, upload) — SHIPPED (except BUG-7)
- **Retested 2026-03-22** on Anthropic Greenhouse apply form via CDP.
- **ALL WORKING**: `browse_fill` (text, email, phone), `browse_upload_file` (resume), `browse_select` (native dropdowns), `browse_click` (navigation)
- **BLOCKED BY BUG-7**: `browse_custom_dropdown` on React comboboxes only. See BUG-7 for root cause and fix.
- **Verdict**: CDP can replace Playwright for ALL apply forms once BUG-7 is fixed. Currently Playwright is still needed for Greenhouse country/location dropdowns.

### FR-3: CDP iframe/embed content extraction — SHIPPED
- **Implemented** in `engine_cdp.rs` lines 539-688. Uses `Page.getFrameTree()` + isolated worlds to extract iframe DOM and merge into parent snapshot.
- **Also**: BUG-2 is now resolved — embed URLs render full forms directly, making iframe extraction less critical.

### FR-5: JS-rendered enterprise career sites — SHIPPED + VERIFIED (2026-04-02)
- **Status**: **ALL 5 WORKING** via native engine. Three hydrators added + detection logic fixed.
- **Hydrators added**:
  1. `try_radancy_api_hydration` — `GET /search-jobs/results` + `X-Requested-With: XMLHttpRequest`. Extracts tenant ID from meta tags.
  2. `try_phenom_api_hydration` — `POST /widgets` with JSON. Returns structured jobs with ML skills.
  3. `try_workday_api_hydration` — `POST /wday/cxs/{company}/{site}/jobs`. Needs PLAY_SESSION cookie.
- **Detection fix**: Platform hydrators now trigger regardless of element count. Previously nav chrome (>5 elements) skipped hydration.
- **Verified results (2026-04-02)**:
  | Site | Platform | Elements | FlareSolverr? | Page Title |
  |------|----------|----------|---------------|------------|
  | Boeing | Radancy | 198 | No | "Job Search Results" |
  | L3Harris | Radancy | 145 | No | "Job Search Results" |
  | Lockheed | Radancy | 194 | No | "Job Search Results" |
  | MITRE | Phenom | 180 | No | "25 Jobs - Search Results" |
  | RTX/Raytheon | Phenom+CF | 246 | Yes | "Search results \| Available job openings at Raytheon" |
- **RTX note**: Behind Cloudflare — requires `WRAITH_FLARESOLVERR=http://localhost:8191`
- **Honeywell/Workday**: Intermittent (Workday maintenance windows). When up, needs PLAY_SESSION cookie from initial page load.
- **Northrop Grumman** (Eightfold.ai): NOT supported — requires session + CSRF + reCAPTCHA. Use CDP fallback.

### FR-4: Engine context isolation / parallel sessions — SHIPPED
- **Implemented** in `pool.rs` with full `EnginePool` architecture: session-sticky routing, LRU idle selection, Draining state cleanup, health checks, and metrics.
- **Verified 2026-03-22**: Switched native (Indeed) → CDP (Ashby) without crash or stale state. Engine status correctly tracks active engine.

---

## PLATFORM CAPABILITY MATRIX (updated 2026-04-02)

| Platform | Native Scrape | CDP Scrape | Native Click Nav | CDP Click Nav | CDP Apply Form | Playwright Apply |
|----------|--------------|------------|-----------------|---------------|---------------|-----------------|
| Greenhouse | Empty body | Board WORKS (437 jobs) | N/A | **WORKS** (full job+form) | **WORKS** (fill/upload/select) except React dropdowns (BUG-7) | WORKS (97%+) |
| Greenhouse embed | N/A | **WORKS** (56+ elements, BUG-2 FIXED) | N/A | N/A | Same as above | WORKS |
| Ashby | Empty body | Board WORKS (129 jobs) | N/A | **WORKS** (job detail + apply form) | **WORKS** (all fields rendered) | WORKS (97.5%) |
| Lever | WORKS (1090 elements, BUG-6 FIXED) | Not needed | **WORKS** (full detail + salary) | Not needed | Not needed | Not needed |
| Indeed | **WORKS** (page 1 via FlareSolverr, BUG-9 FIXED) | **BLOCKED** (CF "Request Blocked") | N/A | N/A | N/A | N/A |
| Boeing | **WORKS** (198 elements, Radancy hydrator) | Not needed | N/A | N/A | N/A | N/A |
| L3Harris | **WORKS** (145 elements, Radancy hydrator) | Not needed | N/A | N/A | N/A | N/A |
| Lockheed Martin | **WORKS** (194 elements, Radancy hydrator) | Not needed | N/A | N/A | N/A | N/A |
| RTX/Raytheon | **WORKS** (246 elements, FlareSolverr+Phenom) | Not tested | N/A | N/A | N/A | N/A |
| MITRE | **WORKS** (180 elements, Phenom hydrator) | Not needed | N/A | N/A | N/A | N/A |
| Northrop Grumman | NOT SUPPORTED (Eightfold+reCAPTCHA) | Not tested | N/A | N/A | N/A | N/A |
