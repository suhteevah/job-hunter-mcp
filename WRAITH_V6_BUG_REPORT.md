# Wraith Browser V6 — Bug Report
## Tested: 2026-03-20 (session 2)
## Tester: Matt Gates + Claude
## Site: Greenhouse (Remote People Senior AI Engineer)

---

## EXECUTIVE SUMMARY

Wraith V5/V6 has **excellent navigation, fill, and file upload**. The `native_events` fill path works — DOM values persist and `browse_submit_form` correctly serializes all form data. However, **React form submission still does not work** via two distinct failure modes.

### Test Results

| Capability | Status | Evidence |
|-----------|--------|----------|
| `browse_navigate` | WORKS | Greenhouse job page loaded correctly |
| `browse_fill` (native_events) | WORKS | All 7 fields filled, DOM values confirmed via `eval_js` |
| `browse_upload_file` | WORKS | Resume (11403 bytes) and cover letter (2112 bytes) uploaded |
| `browse_submit_form` | PARTIAL | Serialized 7 fields correctly, but POSTed to wrong endpoint (HTTP 405) |
| `browse_click` (submit button) | PARTIAL | Click fires, but React's onClick handler doesn't execute |
| `eval_js` button.click() | PARTIAL | Click fires in QuickJS, but React's synthetic event system doesn't process it |
| React-aware fill via eval_js | WORKS | Native setter + `_valueTracker` invalidation + event dispatch all execute |
| **End-to-end submission** | **BROKEN** | Form cannot be submitted regardless of approach |

---

## BUG #1: `browse_submit_form` POSTs to wrong endpoint (HTTP 405)

### Reproduction
```
browse_submit_form @e89  (the "Submit application" button)
```

### Result
```
FORM_SERIALIZED: 7 fields collected, POST to https://job-boards.eu.greenhouse.io/remotepeople/jobs/4721961101 failed: HTTP 405
Fields: {"email":"ridgecellrepair@gmail.com","first_name":"Matt","last_name":"Gates","phone":"5307863655","question_7829852101":"120000","question_7829853101":"Chico, United States","question_7829854101":"4"}
```

### Analysis
- The **good news**: All 7 fields were correctly serialized with the right values. This proves `browse_fill` is working and Wraith can read the form state.
- The **bad news**: Greenhouse has NO `<form>` element (confirmed via `eval_js` — `document.querySelectorAll('form')` returns `[]`). Wraith's `browse_submit_form` fell back to constructing a manual POST to the page URL, which returns 405 Method Not Allowed.
- Greenhouse uses React state + `fetch()` API call on the submit button's onClick handler. The actual API endpoint is different from the page URL.

### Fix Needed
When `browse_submit_form` detects no `<form>` element:
1. Instead of constructing a manual POST, it should **click the submit button** and let React's own handler fire the request
2. Or, intercept the `fetch()`/`XMLHttpRequest` calls to discover the real API endpoint and replay them

---

## BUG #2: `browse_click` and `eval_js` button.click() don't trigger React event handlers

### Reproduction
```
browse_click @e89          -> CLICKED: Submit application
```
And via eval_js:
```javascript
var buttons = document.querySelectorAll('button');
for (var i = 0; i < buttons.length; i++) {
    if (buttons[i].textContent.indexOf('Submit') !== -1) {
        buttons[i].click();
    }
}
```

### Result
Both approaches: Page stays on same URL. No confirmation. No error. No network request. Form appears unchanged.

### Root Cause
This is a **fundamental QuickJS limitation**. React's event system uses event delegation — it attaches a single listener at the document root and routes synthetic events internally. QuickJS's `button.click()`:
1. Does dispatch a native `click` event
2. But React's root listener may not be properly initialized in QuickJS's DOM environment
3. React's synthetic event system relies on browser internals (event propagation, capture phase) that QuickJS may not fully implement

### Evidence
- `eval_js` can read/write DOM values correctly
- `eval_js` can call `.click()` and it returns successfully
- But the side effect (React handling the click) never occurs
- This matches the V5 bug report behavior exactly

### Fix Needed — Option A: Real Browser Engine
For React form submission, Wraith needs a **real browser rendering engine** (Chromium/WebKit) instead of QuickJS for the event dispatch. QuickJS is excellent for DOM reading/writing but cannot replicate the full browser event loop that React depends on.

### Fix Needed — Option B: Network Interception
Instead of trying to make React's event system work in QuickJS:
1. **Discover the API endpoint**: Intercept `fetch()` / `XMLHttpRequest` in the page context, then trigger the button click — capture where React tries to POST
2. **Replay the request**: Once the endpoint is known, construct and send the request directly using Wraith's HTTP client with the serialized form data
3. This is how headless testing frameworks (Cypress intercept, Playwright route) handle similar problems

### Fix Needed — Option C: React Fiber Tree Traversal
Access React's internal fiber tree to find the submit handler and call it directly:
```javascript
// Find React's internal instance
var btn = document.querySelector('button[type="submit"]') || submitButtonElement;
var reactKey = Object.keys(btn).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$'));
if (reactKey) {
    var fiber = btn[reactKey];
    // Walk up to find onClick handler
    var props = fiber.memoizedProps || fiber.pendingProps;
    if (props && props.onClick) {
        props.onClick({preventDefault: function(){}, stopPropagation: function(){}});
    }
}
```
This is hacky but would work without a real browser engine.

---

## WHAT WORKS GREAT

To be clear, Wraith has made massive progress:

1. **Navigation** is rock solid — Greenhouse pages load correctly every time
2. **`browse_fill` with `native_events`** correctly sets DOM values that persist
3. **`browse_upload_file`** handles resume and cover letter uploads perfectly
4. **`browse_submit_form` field serialization** correctly reads all form values — proving the fill is working
5. **`browse_eval_js`** can execute the React-aware fill technique (native setter + `_valueTracker` + event dispatch)
6. **`browse_snapshot`** correctly maps all interactive elements with @ref IDs

The ONLY remaining blocker is triggering React's submit handler. Everything else in the form-fill pipeline is working.

---

## RECOMMENDED FIX PRIORITY

1. **Option C (React Fiber traversal)** — Quickest to implement, no new dependencies. Try to find and invoke React's onClick handler directly via the fiber tree.
2. **Option B (Network interception)** — Medium effort. Monkey-patch `fetch()` in the page, trigger click, capture the request, replay it.
3. **Option A (Real browser engine)** — Highest effort but most robust. Would solve all React interaction issues permanently.

---

## TEST ENVIRONMENT

- Wraith: openclaw-browser (compiled 2026-03-20, V5/V6 with native_events)
- OS: Windows 10 Pro 10.0.19045
- Target: Greenhouse (job-boards.eu.greenhouse.io/remotepeople/jobs/4721961101)
- MCP transport: stdio via .mcp.json
- Fields tested: First Name, Last Name, Email, Phone, Salary, Location, Years of Experience
- Files tested: Resume (.docx, 11403 bytes), Cover Letter (.txt, 2112 bytes)
