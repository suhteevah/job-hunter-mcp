# Wraith → Chrome Parity Gap Analysis

**Goal:** Wraith should be able to do everything a real Chrome window can do — navigate, render, interact, and submit forms on any website — indistinguishable from a human using Chrome.

**Date:** 2026-03-20
**Tested against:** Chrome 146.0.0.0 on Windows 10 Pro
**Test targets:** Indeed.com (Cloudflare), Greenhouse (React SPA), Ashby (React SPA), Lever (server-rendered)

---

## Gap Summary

| # | Gap | Impact | Chrome Behavior | Wraith Behavior |
|---|-----|--------|----------------|-----------------|
| 1 | TLS fingerprint mismatch | Cloudflare blocks all requests | JA3 trusted by Cloudflare, zero challenges | Blocked at TLS handshake, before cookies/JS evaluated |
| 2 | React/SPA rendering | Can't see 60%+ of modern job sites | Full React 18 rendering | Empty `<body>`, zero DOM nodes |
| 3 | reCAPTCHA v3 | Can't submit forms on protected sites | Invisible score (0.7-0.9), auto-passes | No reCAPTCHA support, submit blocked |
| 4 | File input / upload | Can't attach resumes | Native file picker, drag-drop, FormData | No `<input type="file">` interaction |
| 5 | Cross-origin iframes | Can't interact with embedded apply forms | Full iframe rendering + postMessage | Iframes not rendered or accessible |
| 6 | OAuth / login flows | Can't use logged-in sessions | Full redirect chain, cookie persistence | Cookies load but can't complete OAuth |
| 7 | Cookie DB path outdated | Can't import Chrome sessions | N/A | Looks in old path, misses Network/Cookies |
| 8 | TLS profiles outdated | Fingerprint mismatch even with stealth | Chrome 146 | Profiles only go to Chrome 131 |
| 9 | Fingerprint import schema undocumented | 13 round-trips to import | N/A | Missing fields reported one at a time |
| 10 | CSS/layout rendering for form interaction | Can't identify visible form fields | Full CSS cascade, visibility, z-index | QuickJS has no CSS layout engine |

---

## Gap 1: Wire-Level TLS Fingerprint

### What Chrome does
Chrome 146 produces a TLS ClientHello with a specific cipher suite order, extensions, ALPN protocols, supported groups, key share, and signature algorithms. This creates a unique JA3/JA4 hash that Cloudflare whitelists. Chrome doesn't need `cf_clearance` cookies on Indeed — the TLS handshake alone passes.

### What Wraith does
Wraith's Rust HTTP client (reqwest/hyper + BoringSSL) produces a different ClientHello. Even with `stealth_status` showing "ACTIVE (BoringSSL), 19 evasions" and Chrome 131 TLS profiles loaded, the wire-level handshake doesn't match any real Chrome version. Cloudflare detects this and hard-blocks.

### Evidence
- Same IP (174.182.244.155): Chrome passes, Wraith blocked
- Zero `cf_clearance` cookies in Chrome — Cloudflare trusts the TLS alone
- Loading FlareSolverr's `cf_clearance` into Wraith still blocked (cookie tied to solver's JA3)

### What parity looks like
Wraith's TLS ClientHello must be byte-for-byte identical to Chrome 146's. This means:
- Exact cipher suite ordering (not just the same ciphers in different order)
- Exact extension ordering and values
- Exact ALPN protocol list
- Exact supported groups and key share
- Exact signature algorithms
- Correct GREASE values (Chrome randomizes these per-session)
- Correct PSK and early data behavior
- HTTP/2 SETTINGS frame matching (HEADER_TABLE_SIZE, ENABLE_PUSH, MAX_CONCURRENT_STREAMS, INITIAL_WINDOW_SIZE, MAX_FRAME_SIZE, MAX_HEADER_LIST_SIZE must match Chrome's values)
- HTTP/2 WINDOW_UPDATE and PRIORITY frames matching Chrome's patterns

### Verification method
Use a TLS fingerprinting service (e.g., `https://tls.browserleaks.com/json` or `https://ja3er.com/json`) from both Chrome and Wraith — the JA3 and JA4 hashes must match exactly.

---

## Gap 2: JavaScript SPA Rendering (React, Vue, Angular)

### What Chrome does
Chrome's V8 engine + Blink renderer executes the full JavaScript bundle:
1. Parses and executes the webpack/vite chunk loader
2. Boots React 18 with `createRoot()` or `hydrateRoot()`
3. Runs the virtual DOM reconciler
4. Mounts components into the `<div id="root">` mount point
5. Fires `useEffect` hooks, fetches data via `fetch()`/`XMLHttpRequest`
6. Re-renders with fetched data
7. Produces a fully populated DOM with interactive elements

### What Wraith does
Wraith's QuickJS engine executes inline `<script>` tags but cannot:
- Load external JS bundles (webpack chunks, dynamic imports)
- Execute `requestAnimationFrame` / `requestIdleCallback` (React scheduler depends on these)
- Run CSS-in-JS runtimes (styled-components, emotion, Tailwind runtime)
- Handle `MutationObserver` (React uses this internally)
- Process `IntersectionObserver` (lazy loading)
- Execute Web Workers / Service Workers
- Handle `import()` dynamic imports
- Process ES modules (`<script type="module">`)

Result: Any React/Vue/Angular SPA returns empty `<body>`.

### Sites affected
- **Greenhouse** (boards.greenhouse.io, job-boards.greenhouse.io) — React
- **Ashby** (jobs.ashbyhq.com) — React
- **Lever** application forms — React (listings page is server-rendered)
- **Workday** — Angular
- **LinkedIn** — React
- **Most modern career pages** — SPA frameworks

### What parity looks like
A full browser engine (V8 + Blink, or Servo) that can:
- Execute arbitrary JS including ES modules, dynamic imports, Web Workers
- Produce a complete rendered DOM accessible via `browse_snapshot`
- Support `requestAnimationFrame`, `MutationObserver`, `IntersectionObserver`
- Handle `fetch()` and `XMLHttpRequest` for data loading
- Wait for React's commit phase before snapshotting (not just initial script execution)

---

## Gap 3: reCAPTCHA v3 (Invisible)

### What Chrome does
Google's reCAPTCHA v3 runs in the background:
1. Loads `https://www.google.com/recaptcha/api.js?render=<site_key>`
2. Monitors mouse movements, scroll patterns, click timing, keystroke cadence
3. Checks browser environment (plugins, canvas fingerprint, WebGL, audio context)
4. Calls `grecaptcha.execute(siteKey, {action: 'submit'})` on form submission
5. Returns a token with a score (0.0 = bot, 1.0 = human)
6. Score 0.7+ typically passes

### What Wraith does
No reCAPTCHA support. The `grecaptcha` object never loads because:
- External script loading doesn't work (Gap 2)
- Even if it did, behavioral signals (mouse/scroll/keystroke patterns) are absent
- Canvas/WebGL/audio fingerprinting APIs may not be fully implemented

### Sites affected
- **Ashby** — GraphQL submit endpoint requires reCAPTCHA v3 token
- **Greenhouse** — Many boards have reCAPTCHA on the application form
- **Indeed** — Cloudflare Turnstile (similar concept)
- **Most modern forms** — reCAPTCHA v3 or hCaptcha or Cloudflare Turnstile

### What parity looks like
Option A: Full browser engine renders reCAPTCHA and generates behavioral signals (mouse movement simulation, realistic timing)

Option B: reCAPTCHA token relay — intercept the `grecaptcha.execute()` call, request a token from a real Chrome session (via extension or API), and inject it back

Option C: Use `2captcha` or similar service API to solve reCAPTCHA v3 programmatically (returns tokens with 0.7+ scores)

---

## Gap 4: File Input / Upload

### What Chrome does
- `<input type="file">` opens native file picker on click
- JavaScript: `input.files = new DataTransfer().files` sets files programmatically
- Drag-and-drop: `drop` event with `DataTransfer` containing `File` objects
- `FormData.append('file', blob, 'filename.pdf')` for programmatic upload
- XHR/fetch with `multipart/form-data` body

### What Wraith does
- `browse_fill` works for text inputs but not file inputs
- No `browse_upload_file` tool exists (there IS a `browse_upload_file` tool, but unclear if it handles `<input type="file">` or React dropzone components)
- React file upload components (react-dropzone, Material-UI Upload) may not respond to standard file input events

### What parity looks like
- A `browse_upload` tool that accepts a local file path and a `@ref` ID
- Handles both native `<input type="file">` and JS-based dropzone components
- Sets `input.files` via `DataTransfer` API
- Fires `change`, `input`, and `drop` events as Chrome would
- Supports multiple files and drag-drop zones

---

## Gap 5: Cross-Origin Iframes

### What Chrome does
- Renders `<iframe>` content in a separate browsing context
- Each iframe gets its own JS execution environment
- Cross-origin iframes are sandboxed but rendered
- `postMessage` enables parent↔iframe communication
- Indeed Easy Apply uses an iframe from `smartapply.indeed.com`

### What Wraith does
- Iframes are not rendered
- `browse_snapshot` shows the `<iframe>` tag but not its contents
- Cannot `browse_click` or `browse_fill` elements inside iframes
- No tool to switch browsing context into an iframe

### What parity looks like
- `browse_snapshot` includes iframe contents (nested snapshot)
- `@ref` IDs work across iframe boundaries
- `browse_fill` and `browse_click` can target elements inside iframes
- Or: a `browse_enter_iframe(ref_id)` tool that switches context into the iframe

---

## Gap 6: OAuth / Login Flow Support

### What Chrome does
Full redirect chain handling:
1. Click "Sign in with Google" → redirect to `accounts.google.com`
2. Google auth → redirect back to `indeed.com/auth/callback?code=...`
3. Indeed sets session cookies (`JSESSIONID`, auth tokens)
4. All subsequent requests carry auth cookies

### What Wraith does
- Can navigate to login pages
- Can fill username/password fields (if rendered — see Gap 2)
- But: OAuth redirect chains may break (each redirect is a new navigation)
- Cookie persistence across redirects is untested for OAuth flows
- 2FA/MFA (TOTP, SMS, push) requires external interaction
- Indeed specifically requires login for Easy Apply and page 2+ results

### What parity looks like
- Redirect chains work end-to-end (302 → 302 → 302 → 200)
- Cookies set during redirects persist
- `Set-Cookie` headers with `Secure`, `SameSite`, `HttpOnly` flags are respected
- Or: `cookie_import_chrome` works (Bug 3 fix) to import existing logged-in sessions

---

## Gap 7: Cookie Import Path (Bug)

### Current behavior
```
cookie_import_chrome(domain="indeed.com")
→ "Chrome cookie DB not found at: C:\...\Default\Cookies"
```

### Fix needed
Chrome 96+ stores cookies at `<Profile>/Network/Cookies`, not `<Profile>/Cookies`. Check both paths.

---

## Gap 8: Outdated TLS Profiles

### Current profiles
```
Chrome 131 Windows — JA3: cd08e31494f9531f...
Chrome 131 macOS   — JA3: cd08e31494f9531f...
Firefox 132        — JA3: 579ccef312d18482...
Safari 18          — JA3: 773906b0efdefa24...
```

### Current Chrome
Chrome 146 (stable as of 2026-03-20). The TLS handshake has evolved since Chrome 131 — cipher suites, extension order, and GREASE behavior change between versions.

### Fix needed
Ship TLS profiles matching the current Chrome stable release. Ideally auto-update or derive from Chrome's BoringSSL source.

---

## Gap 9: Fingerprint Import Schema

### Current behavior
`fingerprint_import` requires 60+ fields but reports missing fields one at a time. Took 13 attempts to discover the full schema.

### Fix needed
Either:
- Report all missing fields in a single error
- Accept partial fingerprints with sensible defaults
- Provide a `fingerprint_capture` tool that generates the complete JSON from a live browser session
- Publish the schema in documentation

Full schema documented in `wraith_bug_greenhouse_indeed.md`.

---

## Gap 10: CSS Layout Awareness

### What Chrome does
Chrome's Blink renderer computes the full CSS cascade:
- Element visibility (`display: none`, `visibility: hidden`, `opacity: 0`)
- Element position (`position: absolute/fixed`, `z-index`)
- Element size (actual rendered dimensions)
- Scroll position and overflow
- Media queries and responsive breakpoints
- `pointer-events: none` elements are not clickable

### What Wraith does
- `browse_snapshot` shows all DOM elements regardless of visibility
- `browse_click` may click hidden or overlapped elements
- No concept of viewport scroll position
- React portals (modals, dropdowns) may not be positioned correctly
- Form fields hidden by CSS conditional logic are still listed

### What parity looks like
- `browse_snapshot` filters out invisible elements (or marks them)
- `browse_click` respects `pointer-events`, visibility, z-index stacking
- `browse_scroll` scrolls to bring elements into viewport before interaction
- Elements behind modals/overlays are not clickable

---

## Priority Order for Chrome Parity

| Priority | Gap | Unlocks |
|----------|-----|---------|
| **P0** | Gap 2: SPA rendering (Servo) | Greenhouse, Ashby, Lever, LinkedIn, Workday — the entire modern web |
| **P0** | Gap 1: TLS fingerprint | Indeed, any Cloudflare-protected site |
| **P1** | Gap 4: File upload | Resume/CV attachment on all platforms |
| **P1** | Gap 3: reCAPTCHA v3 | Form submission on protected sites |
| **P1** | Gap 5: Iframe support | Indeed Easy Apply, embedded application forms |
| **P2** | Gap 6: OAuth flows | Logged-in sessions, page 2+ results, premium features |
| **P2** | Gap 10: CSS layout | Correct element targeting, avoiding hidden element clicks |
| **P3** | Gap 8: TLS profiles | Keeps up with Chrome releases |
| **P3** | Gap 7: Cookie path | Quality of life |
| **P3** | Gap 9: Fingerprint schema | Developer experience |

**Fixing P0 + P1 (gaps 1-5) gives Wraith full Chrome parity for 95% of job application workflows.**

---

## Test Matrix: Verification Checklist

Once fixes land, validate against these real-world scenarios:

```
[ ] Indeed: browse_navigate to search page returns job listings (not Cloudflare block)
[ ] Indeed: browse_click on a job card shows job description
[ ] Indeed: Easy Apply iframe renders and browse_fill works inside it
[ ] Indeed: File upload attaches resume
[ ] Indeed: reCAPTCHA passes and application submits
[ ] Greenhouse: browse_navigate to board shows job listings (React rendered)
[ ] Greenhouse: browse_navigate to job page shows application form
[ ] Greenhouse: browse_fill populates all form fields
[ ] Greenhouse: File upload attaches resume
[ ] Greenhouse: reCAPTCHA passes and application submits
[ ] Ashby: browse_navigate to board shows job listings (React rendered)
[ ] Ashby: browse_click opens application form
[ ] Ashby: browse_fill handles React controlled inputs
[ ] Ashby: File upload attaches resume
[ ] Ashby: reCAPTCHA v3 passes and GraphQL mutation succeeds
[ ] Lever: browse_navigate shows job page with form
[ ] Lever: browse_fill + browse_upload + submit works
[ ] cookie_import_chrome imports from Network/Cookies path
[ ] fingerprint_import accepts Chrome 146 profile on first attempt
[ ] TLS fingerprint matches Chrome 146 (verified via ja3er.com)
```
