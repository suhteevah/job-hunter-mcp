# Wraith Browser — Issues & Gaps for Production Job Application Automation
## Version: 110 tools (compiled 2026-03-19)
## Tested: 2026-03-20 against Greenhouse (WITHIN AI Engineer)
## Author: Matt Gates + Claude

---

## EXECUTIVE SUMMARY

Wraith is **excellent for scraping, search, and reconnaissance** — CF bypass works, swarm fan-out works, caching/entity graph work, vault works. But **form filling and submission on real web apps (React/Greenhouse/Lever) does not work** because the QuickJS DOM bridge lacks critical browser APIs. This document catalogs every issue found during live testing.

---

## CRITICAL (Blocks job applications entirely)

### 1. `browse_fill` does not persist values to DOM
- **Symptom**: `browse_fill @e50 "Matt"` returns "Filled @e50" but `document.getElementById('first_name').value` is empty
- **Root cause**: `browse_fill` updates an internal tracking structure but does not call `.value =` on the actual DOM element in QuickJS
- **Impact**: Every form field appears filled from Wraith's perspective, but no data reaches the server on submit
- **Fix**: `browse_fill` must call `el.value = text` on the QuickJS DOM element AND dispatch synthetic events

### 2. No `Event` constructor in QuickJS
- **Symptom**: `typeof Event` → `undefined`
- **Root cause**: QuickJS DOM bridge doesn't implement the Web Events API
- **Impact**: Cannot dispatch `input`, `change`, `focus`, `blur` events — React-controlled forms (Greenhouse, Lever) will never see value changes even if `.value` is set
- **Needed**: `new Event('input', { bubbles: true })`, `new InputEvent()`, `new KeyboardEvent()`
- **Fix**: Implement `Event`, `InputEvent`, `KeyboardEvent`, `CustomEvent` constructors in the DOM bridge

### 3. No `dispatchEvent()` on DOM elements
- **Symptom**: `typeof el.dispatchEvent` → `undefined`
- **Root cause**: Missing from QuickJS DOM element prototype
- **Impact**: Even if `Event` existed, there's no way to fire it
- **Fix**: Implement `EventTarget.dispatchEvent()` on all DOM nodes

### 4. No `HTMLInputElement.prototype` / `HTMLElement.prototype`
- **Symptom**: `typeof window.HTMLInputElement` → `undefined`
- **Root cause**: QuickJS DOM bridge creates generic elements, not typed HTML element subclasses
- **Impact**: Cannot use native value setters (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set`) — the standard technique for React form filling
- **Fix**: Implement typed element classes with proper prototype chains

### 5. `browse_upload_file` fails with NOT_FOUND
- **Symptom**: `browse_upload_file` on @e61 (a `[file]` input visible in snapshot) returns "NOT_FOUND: no element at @e61"
- **Root cause**: Likely a mismatch between snapshot @ref IDs and the internal element registry, OR file inputs are excluded from the fillable element map
- **Fix**: Ensure file inputs are in the @ref registry and that the upload handler can find them

### 6. Form submission would send empty data
- **Symptom**: Not tested (blocked by issues 1-5)
- **Root cause**: Since values aren't in the DOM, any POST/fetch to Greenhouse's API would send empty fields
- **Impact**: Even if `browse_submit_form` "works", the application would be rejected/empty
- **Fix**: Depends on fixes 1-4. Once values persist in DOM with events dispatched, form submission should work.

---

## HIGH (Significantly limits functionality)

### 7. No JavaScript execution environment (React never boots)
- **Symptom**: `typeof window.React` → `undefined`; no React fiber tree, no component state
- **Root cause**: QuickJS parses HTML and builds a DOM tree, but doesn't execute `<script>` tags or load external JS bundles
- **Impact**: Any site that renders content via JavaScript (React, Vue, Angular) will show only the server-rendered HTML shell. SPAs are invisible.
- **Note**: `browse_fetch_scripts` (tool #110) was added to address this, but it needs to actually execute the fetched scripts in the QuickJS context
- **Fix**: Either execute `<script>` tags in QuickJS (hard, many Web APIs missing) OR switch to a real browser engine for form interactions

### 8. No `document.forms` collection
- **Symptom**: `typeof document.forms` → `undefined`
- **Impact**: Cannot enumerate or access forms by index/name — a standard DOM API
- **Fix**: Implement `document.forms` HTMLCollection

### 9. `browse_eval_js` values don't flow to `browse_fill`/`browse_submit_form`
- **Symptom**: Setting `el.value = 'Matt'` via eval_js works and persists within eval_js, but it's unclear if `browse_submit_form` reads from eval_js DOM state or from its own internal tracking
- **Impact**: Even the eval_js workaround may not help with form submission
- **Fix**: Ensure `browse_submit_form` serializes the actual DOM element values, not an internal map

---

## MEDIUM (Limits advanced use cases)

### 10. No `window.fetch` / `XMLHttpRequest`
- **Symptom**: Not tested explicitly, but likely missing given the API surface
- **Impact**: Cannot intercept or make API calls from within eval_js (e.g., direct Greenhouse API submission)
- **Fix**: Implement `fetch()` backed by Wraith's native HTTP client (rquest)

### 11. No `MutationObserver`
- **Impact**: Cannot watch for dynamic DOM changes (e.g., React re-renders, dropdown population)
- **Fix**: Implement `MutationObserver` in QuickJS DOM bridge

### 12. No `window.location` mutations
- **Impact**: Cannot programmatically navigate via `window.location.href = ...`
- **Fix**: Hook `location` property setters to trigger Wraith navigation

### 13. Dropdown/select handling unclear
- **Symptom**: `browse_fill` on dropdown fields (Country, Gender, etc.) returns success but likely has same persistence issue
- **Impact**: Greenhouse uses both native `<select>` and custom React dropdown components — neither would work reliably
- **Fix**: `browse_select` and `browse_custom_dropdown` need to interact with actual DOM state + dispatch events

---

## LOW (Nice to have)

### 14. No `localStorage` / `sessionStorage`
- **Impact**: Some sites check storage for auth tokens, preferences, or anti-bot flags
- **Fix**: Implement in-memory Storage API backed by Wraith's cache

### 15. No `navigator` properties
- **Impact**: Bot detection scripts check `navigator.userAgent`, `navigator.webdriver`, `navigator.plugins`, etc.
- **Fix**: Populate `navigator` with realistic Chrome-like values (already done for TLS fingerprint — extend to JS)

### 16. No `getComputedStyle` / `getBoundingClientRect`
- **Impact**: Some forms use visibility checks or position-based logic
- **Fix**: Return reasonable defaults or compute from parsed CSS

---

## WHAT WORKS PERFECTLY

These are solid and production-ready:

| Feature | Status | Notes |
|---------|--------|-------|
| `browse_navigate` | PASS | Pages load, full HTML parsed, CF bypass works |
| `browse_snapshot` | PASS | All elements get @ref IDs, labels visible |
| `browse_search` | PASS | DuckDuckGo metasearch returns results |
| `browse_extract` | PASS | Clean markdown extraction |
| `browse_eval_js` (read) | PASS | Can query DOM, read values, get element counts |
| `browse_eval_js` (write) | PARTIAL | `.value =` works but no events, so React-blind |
| `swarm_fan_out` | PASS | Parallel URL fetching works |
| `cache_*` tools | PASS | Knowledge store, search, tagging all work |
| `entity_*` tools | PASS | Entity graph tracking works |
| `vault_*` tools | PASS | Encrypted credential storage works |
| `cookie_*` tools | PASS | Cookie management works |
| CF/Turnstile bypass | PASS | TLS fingerprint + FlareSolverr stack works |
| `browse_click` (links) | PASS | Navigation via link clicks works |
| `browse_task` | UNTESTED | Autonomous agent loop — depends on fill working |
| `workflow_*` tools | UNTESTED | Record/replay — depends on fill working |

---

## RECOMMENDED FIX PRIORITY

### Phase 1: Make `browse_fill` actually work (unblocks 90% of job apps)
1. **`browse_fill` → set `el.value` in QuickJS DOM** (not just internal map)
2. **Implement `Event` + `InputEvent` constructors** in QuickJS
3. **Implement `el.dispatchEvent()`** on all DOM nodes
4. **`browse_fill` → auto-dispatch `focus`, `input`, `change`, `blur` events** after setting value
5. **Fix `browse_upload_file` @ref lookup** for file inputs

### Phase 2: React compatibility (unblocks Greenhouse/Lever specifically)
6. **Implement `HTMLInputElement.prototype.value` setter** that dispatches React-compatible events
7. **Execute inline `<script>` tags** or at least the Greenhouse form validation scripts
8. **Implement `document.forms`**
9. **Ensure `browse_submit_form` reads actual DOM values** for POST serialization

### Phase 3: Full browser parity (unblocks SPAs, LinkedIn, complex sites)
10. **Implement `fetch()` / `XMLHttpRequest`** backed by rquest
11. **Implement `MutationObserver`**
12. **Implement `localStorage` / `sessionStorage`**
13. **Populate `navigator` object** with Chrome-like values
14. **Execute external `<script src="...">` bundles** (this is what `browse_fetch_scripts` should do)

---

## CURRENT WORKAROUND

Until these fixes ship, the optimal architecture is:

```
WRAITH (scraping layer)          CHROME (apply layer)
├─ browse_search → find jobs     ├─ find() → locate fields
├─ swarm_fan_out → batch scrape  ├─ form_input() → fill fields
├─ browse_extract → get details  ├─ file upload → resume
├─ cache → knowledge store       ├─ computer(click) → submit
├─ entity graph → track cos      └─ javascript_tool → verify
├─ CF bypass → Indeed/Glassdoor
└─ vault → store credentials
```

Wraith handles discovery + Intel. Chrome handles the last mile (form fill + submit).

---

## TEST REPRODUCTION

```
# Navigate to Greenhouse form
browse_navigate → https://job-boards.greenhouse.io/agencywithin/jobs/5056863007

# Fill a field (appears to succeed)
browse_fill @e50 "Matt"  → "Filled @e50"

# Verify via eval_js (value is empty)
browse_eval_js → document.getElementById('first_name').value  → ""

# Set via eval_js directly (works)
browse_eval_js → document.getElementById('first_name').value = 'Matt'  → "Matt"

# Verify persistence (works within eval_js)
browse_eval_js → document.getElementById('first_name').value  → "Matt"

# But no events = React-blind
browse_eval_js → typeof Event  → "undefined"
browse_eval_js → typeof el.dispatchEvent  → "undefined"

# Upload file (fails)
browse_upload_file @e61 "C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"  → "NOT_FOUND"
```
