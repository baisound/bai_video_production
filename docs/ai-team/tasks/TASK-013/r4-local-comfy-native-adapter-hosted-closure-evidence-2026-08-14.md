# TASK-013 — R4 Local Comfy Native Adapter Hosted Closure Evidence

- Date: `2026-08-14`
- Pull request: `#41`
- Exact implementation head: `ff481147080518f44865c88ad0a8caffadd96947`
- Exact main merge: `74d6b5af0c6de66168f5ab6ab63a6a049b11acd4`
- Hosted result: `9 / 9 PASS`
- Adapter implementation: `HOSTED_CLOSED`
- Native completion: `PARKED_TO_SAFE_RUNTIME_REVIEW`

## Hosted checks

- CI: Ubuntu Python 3.11 / 3.12 / 3.13 PASS;
- CI: Windows Python 3.11 / 3.12 / 3.13 PASS;
- Release metadata check: PASS;
- dependency audit: PASS;
- secret scan: PASS.

PR #41 was Ready for review, mergeable and merged through the normal PR path. No direct push to main occurred. The exact implementation branch was deleted from origin and locally after main was fast-forwarded to the verified merge SHA.

## Closure boundary

This Evidence closes only the concrete fail-closed adapter implementation. It does not override the paired native failure/recovery Evidence:

- attempt 01: known `SamplerCustomAdvanced / hostbuf_file_reader_read failed`, no output;
- attempt 02: Owner-confirmed Windows force restart, durable `QUEUED / RECOVERY_REQUIRED`, no automatic replay;
- unsafe legacy low-VRAM runtime modes: rejected before dispatch;
- contained native generation: not PASS;
- Candidate, TASK-040 Attempt and Human Audit publication: not authorized;
- TASK-013 and R4 overall completion: not claimed.

The stable formal release remains `v0.20.1`. No package version change, Tag or GitHub Release is selected for this closure.
