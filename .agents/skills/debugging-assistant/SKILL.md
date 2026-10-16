---
name: debugging-assistant
description: Structured, zero-guessing debugging workflows to isolate, root-cause, and fix frontend and backend issues.
---

# Debugging Assistant Protocol

## 1. Zero-Guessing Triage
- **Reproduce First**: Never attempt a fix without seeing the exact stack trace, error log, or HTTP status code.
- **Diff Comparison**: When behavior changes abruptly ("it worked yesterday"), compare against the last known working git commit (`git diff <commit>`).
- **3-Part Status Report**:
  - [확인한 것]: Exact command output, log line, or status code.
  - [추측한 것]: Hypotheses clearly marked as "추측:".
  - [확인 못한 것]: Blockers, missing files, or external dependency failures.

## 2. Root Cause Analysis (RCA) Process
1. **Trace Ingress**: Check what inputs (HTTP params, query args, JSON payloads) entered the failing function.
2. **State & Environment**: Verify file paths (e.g. `C:\jpro` vs `Desktop\제이프로젝트`), active virtualenv, and port availability.
3. **Isolate Component**:
   - If FastAPI: Test endpoint with `curl` or a scratch script.
   - If React: Check browser console logs, network tab payloads, and component props.
4. **Minimal Patching**: Fix only the root cause. Do not refactor unrelated code while resolving a bug.
5. **2-Attempt Limit**: If two consecutive fixes fail, stop, rollback, and re-examine assumptions.
