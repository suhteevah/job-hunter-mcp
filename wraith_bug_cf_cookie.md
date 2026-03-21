# Wraith Bug: cookie_set Cookies Not Used by browse_navigate for CF Bypass

**Severity**: High — blocks all CF-protected sites (Indeed, Glassdoor, LinkedIn)
**Filed**: 2026-03-21
**Component**: Cookie jar + TLS fingerprint

## Summary

`cookie_set` successfully stores cookies (including `cf_clearance` from FlareSolverr),
but `browse_navigate` still gets blocked by Cloudflare. The cookies are either not sent
with requests, or CF rejects them due to TLS fingerprint mismatch.

## Reproduction

```
1. FlareSolverr (localhost:8191) solves CF challenge for indeed.com — returns 20 cookies including cf_clearance
2. Inject cookies into Wraith via cookie_set:
   - cf_clearance ✓ (confirmed stored)
   - __cf_bm ✓
   - _cfuvid ✓
   - SURF ✓
   - CSRF ✓
3. browse_navigate("https://www.indeed.com/jobs?q=software+engineer&l=remote")
4. Result: Page: "Authenticating..." — still blocked
```

## Root Cause Analysis

`stealth_status` returns:
```
Stealth TLS: INACTIVE (rustls)
Evasions: 19
```

Cloudflare validates `cf_clearance` cookies against the TLS fingerprint (JA3/JA4 hash)
that was used when the cookie was issued. FlareSolverr uses real Chromium with native
OpenSSL TLS stack → Chrome-like JA3. Wraith uses rustls → completely different JA3
fingerprint. CF sees the mismatch and rejects the cookie, serving the challenge page again.

This is a **two-part bug**:

1. **Stealth TLS should be ACTIVE when FlareSolverr env var is set.** The `.mcp.json`
   config has `WRAITH_FLARESOLVERR=http://localhost:8191` — Wraith should automatically
   use FlareSolverr's TLS profile or proxy through it for CF sites.

2. **cookie_set cookies may not be sent on browse_navigate requests.** Even if TLS
   fingerprint matched, it's unclear if the native HTTP client attaches cookies from
   the cookie jar to outgoing requests. Need confirmation.

## Expected Behavior

Either:
- **Option A (best)**: When `WRAITH_FLARESOLVERR` is set and a CF challenge is detected,
  Wraith should automatically proxy the request through FlareSolverr, cache the result,
  and return the page normally. Transparent to the caller.
- **Option B**: Wraith activates stealth TLS (Chrome-like JA3/JA4) so cookies obtained
  from FlareSolverr are accepted by CF on subsequent Wraith requests.
- **Option C (minimum)**: Document that `cookie_set` does NOT work for CF bypass due to
  TLS fingerprint binding, and provide a `browse_navigate_via_flaresolverr` tool.

## Impact

- **Indeed**: ~500K+ job listings, completely blocked
- **Glassdoor**: Reviews + jobs, completely blocked
- **LinkedIn**: Jobs section, blocked (also has other anti-bot)
- **Any CF-protected site**: Cannot use Wraith's cache/entity/swarm features

## Current Workaround

Using FlareSolverr directly via curl + Python for HTML parsing. Works but loses all
Wraith benefits (caching, entity graph, swarm fan-out, knowledge store).

## Environment

- Wraith: openclaw-browser (latest binary)
- FlareSolverr: Docker on localhost:8191
- OS: Windows 10 Pro
- MCP config: `.mcp.json` with `WRAITH_FLARESOLVERR=http://localhost:8191`
