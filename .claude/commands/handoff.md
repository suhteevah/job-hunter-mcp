# /handoff — End-of-session handoff routine

Perform the complete end-of-session handoff:

1. **Update HANDOFF.md** with:
   - Current state (what's working, what's broken)
   - What was completed this session (with specifics — scripts written, bugs fixed, apps submitted)
   - Active leads and their status
   - Key stats (apps submitted, DB size, connects remaining, etc.)
   - Known blockers and next steps
   - Any new patterns or findings discovered

2. **Update memory files** in `C:\Users\Matt\.claude\projects\J--job-hunter-mcp\memory\`:
   - Update `project_active_leads.md` if leads changed
   - Create/update feedback memories for any new user corrections
   - Update `MEMORY.md` index if new files were added

3. **Summarize** what was done in a short bullet list for the user.

Do NOT commit or push — Matt will review first.
