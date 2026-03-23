# Wraith Browser — Open Bug Report
# Last updated: 2026-03-22 (full integration retest complete)
# Maintainer: Matt Gates (ridgecellrepair@gmail.com)
# Usage: Feed this file to Wraith dev for status updates. Delete resolved items.

---

## OPEN BUGS

(None — all blocking bugs resolved)

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

### FR-4: Engine context isolation / parallel sessions — SHIPPED
- **Implemented** in `pool.rs` with full `EnginePool` architecture: session-sticky routing, LRU idle selection, Draining state cleanup, health checks, and metrics.
- **Verified 2026-03-22**: Switched native (Indeed) → CDP (Ashby) without crash or stale state. Engine status correctly tracks active engine.

---

## PLATFORM CAPABILITY MATRIX (retested 2026-03-22, full integration test)

| Platform | Native Scrape | CDP Scrape | Native Click Nav | CDP Click Nav | CDP Apply Form | Playwright Apply |
|----------|--------------|------------|-----------------|---------------|---------------|-----------------|
| Greenhouse | Empty body | Board WORKS (437 jobs) | N/A | **WORKS** (full job+form) | **WORKS** (fill/upload/select) except React dropdowns (BUG-7) | WORKS (97%+) |
| Greenhouse embed | N/A | **WORKS** (56+ elements, BUG-2 FIXED) | N/A | N/A | Same as above | WORKS |
| Ashby | Empty body | Board WORKS (129 jobs) | N/A | **WORKS** (job detail + apply form) | **WORKS** (all fields rendered) | WORKS (97.5%) |
| Lever | WORKS (1090 elements, BUG-6 FIXED) | Not needed | **WORKS** (full detail + salary) | Not needed | Not needed | Not needed |
| Indeed | **WORKS** (54.8KB DOM, CF bypass) | N/A | Not tested | N/A | N/A | N/A |
