# Bug: `cookie_import_chrome` returns 0 cookies on Windows (DPAPI decryption failure)

## Summary

`cookie_import_chrome` silently returns "Imported 0 cookies" on Windows despite Chrome's cookie database containing 2,151 encrypted cookies. The tool reads the SQLite DB successfully but fails to decrypt any cookies.

## Environment

- **OS**: Windows 10 Pro 10.0.19045
- **Chrome**: User Data\Default profile, actively used
- **Wraith**: openclaw-browser (latest build as of 2026-03-20)
- **Cookie DB**: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies` (1.9 MB, 2,151 rows)

## Steps to Reproduce

1. Close Chrome (`taskkill /F /IM chrome.exe`)
2. Verify DB is readable: `sqlite3 "...Default/Network/Cookies" "SELECT COUNT(*) FROM cookies;"` → **2151**
3. Call `cookie_import_chrome` (no args, defaults to "Default" profile)
4. Result: `Imported 0 cookies from Chrome profile 'Default'`
5. Also tested with `profile: "Profile 1"` → same result (0 cookies)

## Expected Behavior

Should decrypt and import cookies using Windows DPAPI, returning a count >0.

## Root Cause (Suspected)

Chrome 80+ on Windows encrypts cookies with AES-256-GCM. The encryption key is stored in `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` under `os_crypt.encrypted_key`, itself protected by Windows DPAPI (`CryptUnprotectData`).

The decryption flow should be:
1. Read `Local State` → decode base64 `encrypted_key` → strip `DPAPI` prefix → call `CryptUnprotectData` to get AES key
2. For each cookie `encrypted_value`: strip `v10`/`v20` prefix → extract 12-byte nonce + ciphertext → AES-256-GCM decrypt with the key

Wraith appears to either:
- Fail silently on the DPAPI call (no error message returned)
- Not implement the v10/v20 decryption path for Windows
- Or be compiled without Windows crypto API bindings

## Verification

```sql
-- Cookies exist and are encrypted (non-empty encrypted_value)
sqlite3 "...Default/Network/Cookies" "SELECT host_key, name, LENGTH(encrypted_value) FROM cookies LIMIT 5;"

-- Output:
-- .autodesk.com|OPTOUTMULTI_REF|99
-- .www.autodesk.com|fingerprint_1739514841509|86
-- content.sheerid.com|thx_guid|95
-- content.sheerid.com|tmx_guid|157
-- .autodesk.com|AMCV_...|189
```

## Workaround

None currently. Chrome must be closed for DB access, but even with exclusive access Wraith can't decrypt. Manual cookie extraction with a Python script using `win32crypt.CryptUnprotectData` + `cryptography.hazmat` AES-GCM works.

## Impact

- Cannot reuse Chrome login sessions in Wraith (Indeed, LinkedIn, etc.)
- Must re-authenticate via `browse_login` for every session
- Blocks FlareSolverr cookie passthrough for CF-protected sites

## Related

- `fingerprint_list` works correctly (4 TLS profiles loaded)
- `cookie_set` / `cookie_get` work for manually-set cookies
- Only `cookie_import_chrome` is affected
