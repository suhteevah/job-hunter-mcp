# Wraith Browser V5 — Bug Report
## Tested: 2026-03-20
## Tester: Matt Gates + Claude
## Sites: Greenhouse (Remote People, Anthropic)

---

## EXECUTIVE SUMMARY

Wraith V5 has made **massive progress** over V3/V4. The two biggest blockers from previous versions — `browse_fill` not persisting values and `browse_upload_file` returning NOT_FOUND — are **both fixed**. The new `native_events` fill path correctly sets `.value` on DOM elements and the upload tool successfully injects files via base64.

However, **React-controlled form submission still does not work**. Greenhouse (and likely Lever, Ashby, and other modern ATS platforms) use React's internal state management, which means DOM-level `.value` changes are invisible to React. The submit button clicks fire, but React's handler sees empty fields and silently does nothing.

### Bottom Line
- **Navigation**: EXCELLENT
- **Form filling (DOM)**: FIXED — `native_events` path works, values persist in DOM
- **File upload**: FIXED — resume and cover letter upload correctly
- **React form submission**: BROKEN — React ignores DOM-set values, submit silently fails
- **Non-React form submission**: UNTESTED (likely works)
- **Net assessment**: Can prep everything, cannot submit on React-based ATS platforms

---

## WHAT'S FIXED SINCE V3/V4

| Issue | V3/V4 Status | V5 Status | Evidence |
|-------|-------------|-----------|----------|
| `browse_fill` value persistence | Values did not persist to DOM | **FIXED** — `FILLED (native_events)` | `eval_js` confirms `.value` = filled text |
| `browse_upload_file` | NOT_FOUND on @ref IDs | **FIXED** — `OK: uploaded` | Resume (11403 bytes) and cover letter (1788 bytes) both uploaded |
| `browse_click` on links | ref mismatch issues | **WORKS** | Navigated from job listing to job detail via click |
| `browse_submit_form` | untested (blocked by fill) | **PARTIALLY WORKS** — fires click, but React ignores it | See Critical Bug #1 |
| `browse_navigate` | worked | **WORKS** | Greenhouse pages load correctly |
| `browse_snapshot` | worked | **WORKS** | All form elements visible with @ref IDs |
| `browse_eval_js` | worked | **WORKS** | Can read/write DOM values |

**This is real, significant progress.** The two hardest bugs from V3/V4 are resolved.

---

## CRITICAL BUG: React Form Submission Silently Fails

### Reproduction Steps

1. Navigate to a Greenhouse job application:
   ```
   browse_navigate https://job-boards.eu.greenhouse.io/remotepeople/jobs/4721961101
   ```

2. Fill all required fields (all return `FILLED (native_events)`):
   ```
   browse_fill @e58 "Matt"        -> FILLED (native_events): Matt
   browse_fill @e60 "Gates"       -> FILLED (native_events): Gates
   browse_fill @e62 "ridgecellrepair@gmail.com" -> FILLED (native_events)
   browse_fill @e66 "5307863655"  -> FILLED (native_events)
   browse_fill @e84 "120000"      -> FILLED (native_events)
   browse_fill @e86 "Chico, United States" -> FILLED (native_events)
   browse_fill @e88 "4"           -> FILLED (native_events)
   ```

3. Upload resume and cover letter (both succeed):
   ```
   browse_upload_file @e69 resume.docx -> OK: uploaded (11403 bytes)
   browse_upload_file @e77 cover.txt   -> OK: uploaded (1788 bytes)
   ```

4. Verify values are in DOM via eval_js:
   ```js
   document.querySelectorAll('input')[0].value  // -> "Matt" ✓
   ```

5. Submit the form:
   ```
   browse_submit_form @e89  -> CLICKED_SUBMIT: Submit application
   browse_click @e89        -> CLICKED: Submit application
   ```

6. **Result**: Page stays on the same URL. No confirmation message. No error message. No network request fired. Form appears to reset in snapshot but values still present in DOM.

### Root Cause

Greenhouse uses **React-controlled form inputs**. React maintains its own internal state tree — it does NOT read from `element.value` on the DOM. When React's submit handler fires, it reads from its internal state (which is empty because no React-recognized events updated it).

The `native_events` fill path sets `.value` on the DOM element directly and may dispatch native DOM events, but React uses a **synthetic event system** that intercepts events at the root level. For React to recognize a value change, one of these must happen:

1. **React's internal value setter must be called** — specifically, the native input value setter must be invoked AND a React-compatible `input` event must be dispatched:
   ```js
   var nativeSetter = Object.getOwnPropertyDescriptor(
     window.HTMLInputElement.prototype, 'value'
   ).set;
   nativeSetter.call(element, 'new value');
   element.dispatchEvent(new Event('input', { bubbles: true }));
   ```

2. **Or** the `_valueTracker` on the input element must be invalidated before dispatching the event:
   ```js
   element.value = 'new value';
   var tracker = element._valueTracker;
   if (tracker) tracker.setValue('');  // force React to see a "change"
   element.dispatchEvent(new Event('input', { bubbles: true }));
   ```

### What's Needed in Wraith

The `browse_fill` tool needs a **React-aware fill mode** that:

1. Checks if `window.HTMLInputElement.prototype` has a native value setter (it does now in V5!)
2. Uses `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, text)` to set the value through the native setter
3. Invalidates React's `_valueTracker` if present: `el._valueTracker && el._valueTracker.setValue('')`
4. Dispatches a **bubbling** `input` event: `el.dispatchEvent(new Event('input', { bubbles: true }))`
5. Optionally dispatches `change`, `focus`, `blur` events for completeness

**The prototype infrastructure is already there** (V5 has `HTMLInputElement` as a function). The missing piece is using the native setter path + `_valueTracker` invalidation in the fill tool.

### Severity

**CRITICAL** — This blocks all job applications on:
- Greenhouse (used by Anthropic, Reddit, Scale AI, ZipRecruiter, AssemblyAI, PlanetScale, etc.)
- Lever (used by many startups)
- Ashby (used by Ramp, etc.)
- Any React/Vue/Angular-based application form

These platforms represent ~80% of tech job applications.

---

## MINOR ISSUES

### 1. Snapshot shows empty values after fill
- **Symptom**: After `browse_fill` succeeds, `browse_snapshot` shows fields as `""` even though `eval_js` confirms values are present
- **Impact**: Low — cosmetic only, values ARE in the DOM
- **Likely cause**: Snapshot reads from internal element state, not DOM `.value`

### 2. eval_js crashes on complex expressions
- **Symptom**: `Array.from(x).map().filter().join()` chains crash with "Exception generated by QuickJS"
- **Workaround**: Use simple for-loops instead of functional chains
- **Impact**: Low — workaround exists

### 3. Input elements have no `name` or `id` attributes in Greenhouse
- **Symptom**: `document.querySelectorAll('input')` returns elements with `undefined` name/type
- **Impact**: Low — can still access by index, @ref IDs work fine
- **Likely cause**: Greenhouse generates inputs dynamically without standard HTML attributes; Wraith's DOM bridge may not parse `name`/`id` from the real page

---

## SUGGESTED FIX PRIORITY

1. **React-aware fill** (Critical) — Add `_valueTracker` invalidation + native setter path to `browse_fill`. This one fix would unlock all React-based job applications.
2. **Snapshot value display** (Low) — Show filled values in snapshot output for better debugging.
3. **eval_js stability** (Low) — Support functional array chains in QuickJS.

---

## TEST ENVIRONMENT

- Wraith: openclaw-browser (compiled 2026-03-20, V5 with V3 fixes)
- OS: Windows 10 Pro 10.0.19045
- Targets: Greenhouse (job-boards.eu.greenhouse.io, job-boards.greenhouse.io)
- MCP transport: stdio via .mcp.json

---

## APPENDIX: Proposed React-Aware Fill Implementation

```javascript
// This is the standard technique used by Selenium, Puppeteer, and Playwright
// to fill React-controlled inputs. Wraith's browse_fill should implement this.

function reactAwareFill(element, value) {
    // Step 1: Focus the element
    element.focus();

    // Step 2: Use native setter to bypass React's synthetic wrapper
    var nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value'
    ).set;
    nativeSetter.call(element, value);

    // Step 3: Invalidate React's value tracker
    var tracker = element._valueTracker;
    if (tracker) {
        tracker.setValue(''); // Force React to see this as a "change"
    }

    // Step 4: Dispatch events that React listens for
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));

    // Step 5: Blur to trigger any onBlur validation
    element.dispatchEvent(new Event('blur', { bubbles: true }));
}
```

If `browse_fill` implements this logic, Wraith will be able to fill AND submit React forms — completing the full autonomous application chain without any browser GUI dependency.
