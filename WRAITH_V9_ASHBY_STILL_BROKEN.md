# Wraith Bug Report V9: Ashby SPA Still Not Rendering

## Summary
After reported fixes, Ashby (jobs.ashbyhq.com) still returns an empty DOM in Wraith. The React SPA does not hydrate — zero form elements, zero interactive refs. This is the same failure documented in V8.

## Reproduction Steps
```
1. mcp__wraith__browse_navigate({ url: "https://jobs.ashbyhq.com/pinecone/7ef089cb-a721-4ad8-a6d0-c390e64991d2/application" })
2. mcp__wraith__browse_wait({ ms: 5000 })
3. mcp__wraith__browse_snapshot()
4. mcp__wraith__browse_eval_js({ code: "document.querySelectorAll('input, button, form, label').length" })
```

## Observed Results
```
browse_navigate → Title loads: "Senior Software Engineer, Search & Retrieval Infrastructure @ Pinecone"
                  DOM: 7 nodes total — html, title, body, 4 empty divs
                  Interactive elements: 0

browse_snapshot (after 5s wait) → Same 7 nodes, still empty

browse_eval_js('input, button, form, label') → 0 elements
```

## Expected Results
The application form should render with ~20+ interactive elements:
- Text inputs (name, email, phone, LinkedIn)
- File upload (resume)
- Combobox (location)
- Radio buttons (pronouns, visa, demographics)
- Checkboxes (side businesses, EEO)
- Submit button

**Chrome renders all of these correctly on the same URL.**

## Wraith Config at Time of Test
```
JavaScript: true
Screenshots: None
Layout: true
Cookies: true
Stealth: true
Stealth TLS: INACTIVE (rustls)
Evasions: 19
FlareSolverr: not configured
Proxy: direct
```

## Root Cause (Unchanged from V8)
Ashby's HTML delivers an empty `<div id="root">` plus one inline `<script>` with a nonce attribute that:
1. Fetches a manifest from `https://cdn.ashbyprd.com/frontend_non_user/.../index.json`
2. Dynamically creates `<script type="module">` elements pointing to the React bundle on CDN
3. React mounts into `#root` and renders the application form

Wraith's QuickJS engine either:
- **Does not execute the inline `<script>`** at all (most likely — the nonce or inline detection fails)
- **Cannot handle `document.createElement("script")` with dynamic `src`** — no network fetch + execution pipeline for dynamically injected scripts
- **Cannot execute ES modules** (`type="module"`) which Ashby's React bundle requires

## Impact
- **175 jobs** in database (7% of all tracked jobs) are Ashby-hosted
- All are high-quality AI company roles (Pinecone, Cursor, Cohere, Perplexity, Deepgram, etc.)
- Current workaround: Chrome automation (works but non-parallelizable, no swarm support)

## Verification Command
Quick way to confirm the fix works — this should return > 0:
```
browse_navigate → https://jobs.ashbyhq.com/pinecone/7ef089cb-a721-4ad8-a6d0-c390e64991d2/application
browse_eval_js  → document.querySelectorAll('input[type="text"], input[type="email"]').length
```

## Date
2026-03-20
