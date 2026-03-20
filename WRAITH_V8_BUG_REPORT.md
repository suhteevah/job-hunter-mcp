# Wraith Bug Report V8: Ashby SPA Rendering Failure

## Summary
Ashby (jobs.ashbyhq.com) returns an empty DOM snapshot — 0 interactive elements, 1 node total (just `<title>`). This blocks automation of 175 jobs in our database (7% of all jobs).

## Root Cause: Two Cascading Failures

### Failure 1: Script Tag Not Parsed
Ashby's HTML has a single inline `<script>` in `<body>` that bootstraps the entire SPA:

```html
<body>
  <div id="root">
  <script nonce="7Roc4p3n5zh5GOy6rfyVNgisrpoFzDWTn5fmldULPYg">
    // Inline JS that:
    // 1. Fetches manifest from CDN
    // 2. Dynamically creates <link> tags for CSS
    // 3. Dynamically creates <script type="module"> for the React bundle
    // 4. Bundle URL: https://cdn.ashbyprd.com/frontend_non_user/{hash}/{file}
  </script>
</body>
```

**Problem**: Wraith's HTML parser produces only 1 node (`<title>`). The `<script>` tag in `<body>` is either:
- Not being parsed as a DOM node at all, OR
- Being parsed but filtered out before reaching `build_node_json()`

Either way, `browse_fetch_scripts` reports "No external scripts found" because the script inventory is empty.

### Failure 2: Dynamic Script Loading Pattern
Even if wraith captured the `<script>` tag, Ashby uses a **two-stage dynamic loading pattern**:

```
Stage 1 (inline script): fetch("/api/ashby/non_user/index.json")
  → Returns manifest with CSS filenames and JS entry point

Stage 2 (dynamic): document.createElement("script")
  script.type = "module"
  script.src = "https://cdn.ashbyprd.com/frontend_non_user/{hash}/{entry}.js"
  → This is the actual React bundle that renders the application form
```

The inline script doesn't have a `src` attribute — it's inline JS. And it uses `document.createElement("script")` to dynamically inject the real bundle. So even if `browse_fetch_scripts` found it, it can't execute an inline script that itself dynamically loads more scripts.

## Evidence

```
browse_navigate → Page title: "Technical Account Manager @ Vultr", 0 elements
browse_snapshot → Empty (no @e refs)
browse_extract → "# Technical Account Manager\n\n---\n0 links | ~0 tokens"
browse_eval_js(__wraith_nodes.length) → 1 (only <title>)
browse_fetch_scripts → "No external scripts found or fetchable"
curl raw HTML → Confirms <div id="root"> is empty, single inline <script> with nonce
```

## What Ashby's HTML Actually Contains
1. `<head>`: meta tags, `<title>`, `<script type="application/ld+json">` (structured data with full job description!)
2. `<body>`: empty `<div id="root">`, one inline `<script>` that bootstraps everything

## Proposed Fixes (Pick One or Both)

### Fix A: Parse ld+json for Job Data (Quick Win)
The `<script type="application/ld+json">` in `<head>` contains the **complete job description** as structured data (JSON-LD). Wraith could:
1. Detect `<script type="application/ld+json">` during HTML parsing
2. Extract the JSON payload
3. Surface it in `browse_extract` output or a new `browse_structured_data` tool

This won't give us the application form, but it gives us all job details without needing React.

### Fix B: Support Inline Script Execution + Dynamic Script Loading (Full Fix)
1. **Parse `<script>` tags** in the HTML parser (currently they seem to be dropped)
2. **Execute inline scripts** in QuickJS after DOM bridge setup
3. **Intercept `document.createElement("script")`** — when inline JS creates a new script element with a `src`, fetch that URL and execute it
4. This is essentially a mini module loader. The chain would be:
   - Parse HTML → find inline `<script>` → execute in QuickJS
   - Inline script calls fetch("/api/ashby/non_user/index.json") → wraith HTTP client fetches it
   - Inline script creates `<script src="bundle.js">` → wraith fetches and executes bundle.js
   - React renders into `<div id="root">` → DOM snapshot now has form elements

### Fix C: SSR/Prerender API Detection (Alternative)
Some SPAs have server-side rendering for bots. Check if Ashby responds differently with:
- `User-Agent: Googlebot`
- `Accept: text/html` with bot-like headers
- Or an API endpoint like `https://jobs.ashbyhq.com/api/posting/Vultr/69a7aae9-a5eb-4939-bee3-df9e6a47183c`

## Affected Sites
This same pattern likely affects any SPA-only job board:
- **Ashby** (175 jobs) — confirmed broken
- **Workable** — likely same issue (apply.workable.com)
- **SmartRecruiters** — potentially
- Any site using client-side rendering without SSR fallback

## Priority
High — 175 jobs blocked, and the pattern will recur as more ATS platforms move to SPA architecture.

## Workaround (Current)
Use Chrome browser automation (Claude in Chrome) for Ashby applications. Works but is slower and can't be parallelized via swarm.
