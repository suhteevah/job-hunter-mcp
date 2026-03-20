# Wraith Browser — Feature Gaps Blocking Full Job Hunter Automation
# Generated: 2026-03-20
# Purpose: Pass to Wraith dev to close gaps so we can stop using Chrome/Playwright

## CRITICAL: Why We Still Need Chrome

Wraith has 80+ MCP tools and can scrape, extract, search, cache, and navigate.
But for **applying to jobs** (form filling + file upload + submit), we're stuck
on Chrome because Wraith is missing these capabilities:

---

## 1. FILE UPLOAD (BLOCKER — #1 priority)

**What we need:** Upload `C:\Users\Matt\Downloads\matt_gates_resume_ai.docx` to
`<input type="file" id="resume">` on Greenhouse/Lever forms.

**What Wraith has:** `browse_fill` tool fills text/select fields by @ref ID.

**What's missing:** No file upload tool. `browse_fill` cannot set file inputs
(browser security prevents programmatic `value` setting on file inputs).
Need a dedicated `browse_file_upload` tool that:
- Takes a @ref ID (or CSS selector) of a `<input type="file">` element
- Takes a local file path
- Uses CDP `DOM.setFileInputFiles` or equivalent to set the file
- Returns success/failure + filename confirmation

**Impact:** Every single job application requires resume upload. This alone
forces us to Chrome for 100% of applications.

**Reference:** Playwright does this with `page.setInputFiles()`. CDP has
`DOM.setFileInputFiles(nodeId, files)`.

---

## 2. CLI `--flaresolverr` FLAG NOT WORKING (BLOCKER)

**What we need:** Pass `--flaresolverr http://localhost:8191` as a CLI flag
to enable Tier 3 CF Turnstile bypass for Indeed/Glassdoor scraping.

**What's happening:** The binary was compiled before the `--flaresolverr`
global arg was added to the Cli struct. Running:
```
openclaw-browser.exe --flaresolverr http://localhost:8191 extract "https://indeed.com/..."
```
Returns: `error: unexpected argument '--flaresolverr' found`

**Fix:** Rebuild the binary (`cargo build --release`). The code is already
correct in `crates/cli/src/main.rs:30-32` — just needs recompilation.

**Workaround for MCP mode:** The MCP server reads `WRAITH_FLARESOLVERR` env var
correctly, so this only blocks CLI usage.

---

## 3. FORM SUBMISSION (BLOCKER)

**What we need:** Click "Submit application" buttons that trigger form POST
with multipart/form-data (including file uploads).

**What Wraith has:** `browse_click` by @ref ID.

**What's uncertain:** Does `browse_click` actually trigger real browser click
events that fire form submission handlers? Or does it only work on simple
navigation links? Greenhouse forms use React-controlled state + XHR submission,
not native HTML form POST. Need confirmation that:
- Click triggers React synthetic events
- Form validation fires
- XHR/fetch submission executes
- Redirect after submission is followed

**If not working:** Need `browse_submit_form` tool that:
- Takes a form selector or @ref
- Serializes all form data (including files)
- Sends as multipart POST to the form action URL
- Returns response status + body

---

## 4. DROPDOWN/SELECT INTERACTION (IMPORTANT)

**What we need:** Select options from custom dropdown components (not native
`<select>` elements). Greenhouse uses custom React dropdowns for:
- Country selector (combobox with typeahead)
- Visa sponsorship (Yes/No dropdown)
- Gender, Race, Veteran status (EEO fields)

**What Wraith has:** `browse_fill` and `browse_select` tools.

**What's uncertain:** `browse_select` works on native `<select>` elements.
But Greenhouse uses custom combobox components (div/input with listbox role).
Need `browse_fill` + `browse_click` sequence to:
1. Click the combobox to open it
2. Type to filter options
3. Click the matching option

**Possible fix:** Could be handled by `browse_type_text` (character-by-character
with delay) + `browse_click` on the option. But needs testing.

---

## 5. VISIBLE BROWSER SESSION (NICE-TO-HAVE)

**What we need:** Some job sites (LinkedIn Easy Apply, iCIMS portals) require
a visible browser window because:
- LinkedIn shadow DOM blocks all programmatic interaction
- iCIMS uses iframes that don't respond to CDP
- Some CAPTCHAs need human solving (user must see the window)

**What Wraith has:** Headless Chrome via CDP.

**What's missing:** Option to launch in headed (visible) mode. Even if Wraith
is headless-first, a `--headed` or `--visible` flag would let us:
- Debug form filling visually
- Let user solve CAPTCHAs when they appear
- Handle sites that detect headless mode

**Current workaround:** Use Claude in Chrome (user's visible browser).

---

## 6. SESSION PERSISTENCE ACROSS CLI INVOCATIONS (IMPORTANT)

**What we need:** Keep a browser session alive across multiple CLI commands.
Currently each CLI invocation (`navigate`, `extract`, `search`) launches a
new Chrome session, navigates, does its thing, then shuts down.

**Impact:**
- Can't fill a form across multiple CLI calls (session dies between calls)
- Can't maintain login state (cookies lost)
- Each invocation has ~400ms Chrome launch overhead

**What's needed:** Either:
- A daemon mode (`openclaw-browser daemon start`) that keeps Chrome alive
- Or the MCP server mode (which already persists sessions) — but this requires
  Claude Code restart to activate as MCP, and can't be used via Bash tool

**Workaround:** Use MCP server mode (`.mcp.json` configured, needs session restart).

---

## 7. COOKIE/SESSION IMPORT FROM EXISTING CHROME PROFILE (NICE-TO-HAVE)

**What we need:** Import cookies from the user's actual Chrome profile so we
can reuse existing logins (Indeed, LinkedIn, Greenhouse).

**What Wraith has:** `cookie_set`, `cookie_save`, `cookie_load` tools.

**What's missing:** No way to import from Chrome's cookie database
(`%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies`). Would need:
- `cookie_import_chrome --profile "Default"` command
- Decrypt Chrome cookies (DPAPI on Windows)
- Load into Wraith's cookie jar

**Impact:** Without this, we need to log in fresh to Indeed/LinkedIn every
session, which triggers bot detection.

---

## 8. SEARCH PROVIDER RELIABILITY (MINOR)

**What we see:** DuckDuckGo `site:` searches work for simple queries but
return 0 results for complex queries with OR operators:
```
WORKS:    "site:greenhouse.io AI engineer remote 2026" → 12 results
FAILS:    "site:greenhouse.io QA automation engineer OR SDET remote" → 0
FAILS:    "site:lever.co AI engineer OR ML engineer remote 2026" → 0
```

**What's needed:** Either:
- Better query preprocessing (split OR into multiple queries, merge results)
- Additional search providers (Google Custom Search, Bing API)
- SearXNG self-hosted instance (free, supports OR queries properly)

---

## SUMMARY — Priority Order

| # | Gap | Severity | Fix Effort | Impact |
|---|-----|----------|-----------|--------|
| 1 | File upload tool | BLOCKER | 2-4 hours | Unlocks ALL job applications |
| 2 | Rebuild binary (--flaresolverr) | BLOCKER | 5 minutes | Unlocks Indeed/Glassdoor scraping |
| 3 | Form submission validation | BLOCKER | 2-4 hours | Confirms apply flow works end-to-end |
| 4 | Custom dropdown interaction | IMPORTANT | 1-2 hours | Required for Greenhouse EEO fields |
| 5 | Headed browser mode | NICE-TO-HAVE | 1 hour | Debug + CAPTCHA solving |
| 6 | Session persistence (CLI) | IMPORTANT | 2-4 hours | Multi-step form flows |
| 7 | Chrome cookie import | NICE-TO-HAVE | 4-8 hours | Reuse existing logins |
| 8 | Search OR query handling | MINOR | 1-2 hours | More job discovery |

**If only ONE thing gets fixed:** File upload (#1). That single feature would
let us apply to every Greenhouse/Lever job entirely through Wraith, which is
~60% of all our applications.

**If TWO things:** File upload + rebuild binary. That covers applications +
Indeed/Glassdoor scraping = ~90% of workflow.
