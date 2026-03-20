# Wraith Browser — Native Engine Gaps for Full Form Automation
# Generated: 2026-03-20 (replaces WRAITH_GAPS.md)
# Updated: 2026-03-20 — confirmed all tool interfaces exist, engine is the gap
# Purpose: Build out Wraith's native engine to handle React forms without Chrome/Servo

## COMPLETED FEATURES (shipped since WRAITH_GAPS.md v1)

These tools now EXIST with correct interfaces — great work:
- [x] `browse_upload_file` — reads file from disk, base64-encodes, injects via JS
- [x] `browse_submit_form` — handles React forms, XHR/fetch submission
- [x] `browse_custom_dropdown` — React/Greenhouse-style dropdowns
- [x] `browse_type` — realistic keystroke delays for bot evasion
- [x] `browse_select` — native `<select>` dropdowns
- [x] `cookie_import_chrome` — import Chrome cookies

## ACTION REQUIRED — Test This Workflow

Before writing any new code, test if script execution already works.
Run this exact sequence and report what happens:

```
1. browse_navigate → https://job-boards.greenhouse.io/anthropic/jobs/5065894008
2. browse_fetch_scripts   (if this tool exists — execute page <script> tags)
3. browse_fill @e37 "Matt"
4. browse_eval_js → document.getElementById("first_name").value
5. browse_eval_js → typeof window.React
```

**What we need to see:**
- Step 4 returns `"Matt"` (not empty string)
- Step 5 returns `"object"` or `"function"` (not `"undefined"`)

**What we saw last time (broken):**
- Step 4 returned `""` (empty — React state not updated)
- Step 5 returned `"undefined"` (React never loaded)

If `browse_fetch_scripts` doesn't exist as a tool, that's the first
thing to build. The page has `<script>` tags with the React bundle —
they just need to be fetched and executed in QuickJS with DOM bindings.

## CONTEXT — What Wraith Does Amazingly Well

Wraith's native Rust engine + QuickJS is an absolute beast for scraping:
- Harvested 1,560+ jobs from 50+ companies via API scraping in ~3 minutes
- CF Turnstile bypass via rquest/BoringSSL TLS fingerprinting
- 80+ MCP tools, knowledge cache, entity graph, semantic search, swarm
- Pages render instantly, DOM snapshot is clean and actionable
- Greenhouse/Ashby/Lever API endpoints parsed perfectly
- Total DB now at 2,418 jobs from a single session

The scraping side is production-grade. Zero complaints.

---

## THE PROBLEM — React-Controlled Forms

When we tried to use Wraith for Greenhouse job applications (the actual
form-filling + submit flow), we hit a fundamental engine limitation:

### What Happens

1. `browse_navigate` loads the Greenhouse application page — HTML parses correctly
2. `browse_snapshot` shows all form fields with @ref IDs — looks perfect
3. `browse_fill` sets DOM `.value` on text inputs — appears to work
4. But **React never executes**. `window.React === undefined`.

### Why It Fails

Wraith uses **QuickJS** for JavaScript execution. QuickJS is fast and lightweight
but it's a standalone JS engine — it does NOT:
- Execute `<script>` tags from the page (React bundle never loads)
- Run React's reconciliation/render cycle
- Fire synthetic React events (onChange, onBlur, etc.)
- Process React-controlled input state updates
- Execute XHR/fetch for form submission

So when `browse_fill` sets `input.value = "Matt"`, the raw DOM value changes
but React's internal state stays empty. When the form submits, React sends
its state (empty) not the DOM values.

### Evidence

```
browse_eval_js: document.getElementById("first_name").value  → ""  (empty after fill)
browse_eval_js: typeof window.React                          → "undefined"
browse_eval_js: typeof window.__NEXT_DATA__                  → "undefined"
browse_upload_file: @e48 (file input)                        → "NOT_FOUND" (hidden, React-created)
```

### Affected Tools

These tools EXIST and have correct interfaces, but can't work without
a real JS runtime that executes page scripts:

| Tool | Status | Why |
|------|--------|-----|
| `browse_fill` | Partial | Sets DOM value but React state empty |
| `browse_upload_file` | Broken | File input is `visually-hidden`, no browser File API |
| `browse_submit_form` | Broken | React XHR submission needs React runtime |
| `browse_custom_dropdown` | Broken | React-Select components need React event system |
| `browse_type` | Partial | Types chars but React onChange never fires |
| `browse_click` | Works for links | Fails for React onClick handlers |

---

## THE SOLUTION — Native JS Engine Enhancement (NOT Chrome)

Chrome/CDP is NOT the answer. Wraith's value is being a native, fast,
self-contained browser. The solution is making the native engine capable
of running page JavaScript properly.

### Option 1: Full Page JS Execution in QuickJS (Recommended)

QuickJS CAN execute complex JavaScript including React — it just needs
the right environment setup:

**What's needed:**
1. **Execute `<script>` tags** — When a page loads, extract and execute all
   inline and external `<script>` tags in order. Currently Wraith parses
   HTML but doesn't execute scripts.

2. **DOM API bindings for QuickJS** — QuickJS needs bindings for:
   - `document.createElement`, `appendChild`, `removeChild` (React DOM manipulation)
   - `addEventListener`, `dispatchEvent` (event system)
   - `XMLHttpRequest` / `fetch` (network requests from JS)
   - `setTimeout`, `setInterval`, `requestAnimationFrame` (async scheduling)
   - `window.location`, `window.history` (navigation)
   - `FormData`, `File`, `Blob` (form/file handling)

3. **Event dispatch on fill** — When `browse_fill` sets a value, it must
   also dispatch: `input`, `change`, `blur` events on the element so
   React's synthetic event system picks up the change.

4. **Script fetching** — External `<script src="...">` tags need their
   JS fetched and executed. React bundles are typically 200-500KB.

**Effort estimate:** 2-4 weeks for a solid implementation.
Could be incremental — start with event dispatch (#3) which alone
might fix `browse_fill` for many React forms.

**Quick win — Event dispatch only (~1 day):**
Even without full script execution, if `browse_fill` dispatches
native DOM events (`new Event('input', {bubbles: true})`,
`new Event('change', {bubbles: true})`), AND the page's React bundle
has been executed, the forms would work. The question is whether
QuickJS can load React's bundle.

### Option 2: Servo Integration (WebView-like)

Mozilla's Servo engine is written in Rust and designed for embedding:
- Full HTML/CSS rendering
- SpiderMonkey JS engine (full ES2024+, runs React)
- Composable as a library (`servo_embedder`)
- Already has DOM bindings, event system, fetch API
- Rust-native — fits Wraith's architecture perfectly

**Trade-offs:**
- Much larger binary (Servo is ~50MB+)
- More complex build
- Full browser capabilities out of the box
- Could run in "headless webview" mode for form flows

**Effort estimate:** 1-2 weeks to integrate as an alternative renderer.

### Option 3: Headless WebKitGTK / WebView2

- WebKitGTK (Linux) or WebView2 (Windows) as a rendering backend
- Full JS execution, DOM, file handling
- Lighter than full Chrome
- Still native, no external process dependency

### Option 4: Minimal React Shim (~2 days, experimental)

Instead of running the full page JS, inject a minimal shim that:
1. Intercepts `browse_fill` calls
2. Finds the React fiber node for the target element
3. Calls React's internal `onChange` handler directly
4. Sets React state programmatically

```javascript
// React fiber access pattern
function setReactValue(element, value) {
  var fiber = element[Object.keys(element).find(function(k) {
    return k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$');
  })];
  if (fiber && fiber.memoizedProps && fiber.memoizedProps.onChange) {
    element.value = value;
    fiber.memoizedProps.onChange({ target: element, currentTarget: element });
  }
}
```

This is hacky but has been proven to work in Selenium/Playwright for
React-controlled forms.

---

## RECOMMENDED APPROACH — Incremental

### Phase 1 (Quick Win — 1-2 days)
Modify `browse_fill` to:
1. Set the DOM value
2. Dispatch native DOM events (`input`, `change`, `focus`, `blur`)
3. Try the React fiber shim pattern above

This alone might fix form filling for Greenhouse/Lever/most React forms.

### Phase 2 (Script Execution — 1-2 weeks)
Add `<script>` tag execution to the page load pipeline:
1. After HTML parse, collect all `<script>` elements
2. Fetch external scripts
3. Execute in QuickJS with DOM bindings
4. React mounts, controls inputs, handles state

### Phase 3 (Full Native Engine — 2-4 weeks)
Either build out QuickJS DOM bindings fully OR integrate Servo
as an optional rendering backend for complex pages.

---

## FILE UPLOAD — Specific Fix Needed

The `browse_upload_file` tool exists but fails because:
1. Greenhouse's file input has class `visually-hidden` (CSS hidden)
2. No real browser File API in QuickJS

**Fix for Phase 1:**
```javascript
// After setting file via DataTransfer, dispatch change event
var input = document.querySelector('input[type="file"]#resume');
// OR find by: document.querySelector('.visually-hidden[type="file"]');
var dt = new DataTransfer();
dt.items.add(new File([fileBytes], 'resume.docx', {type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}));
input.files = dt.files;
input.dispatchEvent(new Event('change', {bubbles: true}));
```

This requires `DataTransfer`, `File`, and `Blob` constructors in QuickJS.

---

## WHAT THIS UNLOCKS

If form filling works natively in Wraith:
- **Apply to any Greenhouse/Lever job** without Chrome/Playwright
- **Batch apply via `swarm_fan_out`** — 15 applications in parallel
- **Workflow record/replay** — record one apply flow, replay with variables
- **Full stealth** — TLS fingerprinting + behavioral simulation on applies
- **Zero external dependencies** — no Chrome, no Playwright, no Node.js

This makes Wraith a complete autonomous job hunting engine, which is
the entire point of this project.

---

## SUMMARY

| Phase | Fix | Effort | Unlocks |
|-------|-----|--------|---------|
| 1 | Event dispatch + React fiber shim | 1-2 days | Form filling on most React sites |
| 1 | File upload via DataTransfer API | 1 day | Resume upload |
| 2 | Script tag execution | 1-2 weeks | Full React app support |
| 3 | Servo or full DOM bindings | 2-4 weeks | Any website, any form |

**Priority: Phase 1 first.** The React fiber shim + event dispatch is
a 1-2 day fix that would immediately unlock Greenhouse/Lever applications
entirely through Wraith. That alone covers ~60% of all job applications.
