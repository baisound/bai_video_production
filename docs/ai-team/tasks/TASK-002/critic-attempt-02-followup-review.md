# TASK-002 — Critic Attempt 02 Follow-up Review

## Decision

`NO_BLOCKING_CODE_FINDINGS / FINAL_LIVE_EVIDENCE_REQUIRED`

## Findings resolved

### C-02-01 — Unknown current Project identity could weaken sandbox protection — BLOCKING / RESOLVED

A non-null current Project whose name could not be read was previously represented as `None` name, which could pass the same guard path as no current Project. Fixed by refusing mutation unless the identity of every existing current Project is positively known.

### C-02-02 — Created/reloaded sandbox identity needed re-verification — BLOCKING / RESOLVED

The probe now verifies that the Project returned by CreateProject/LoadProject exactly matches the requested `BAI_CAPABILITY_PROBE_*` name before subsequent save/media/timeline writes.

### C-02-03 — Worker refusal Evidence was overwritten by generic supervisor failure — MAJOR / RESOLVED

A Schema-valid worker Evidence file is now preserved even when the worker exits non-zero. Exact `mutation_error` remains available for audit while the caller still receives failure status.

### C-02-04 — WSL authentication isolation was recorded but not mandatory — MAJOR / RESOLVED

The WSL client now fails if unauthenticated access does not return HTTP 401. Final report construction also requires successful auth rejection, authenticated round trips and same endpoint identity across restart.

### C-02-05 — Temporary WSL probe server could survive a phase failure — MAJOR / RESOLVED

PowerShell runner tracks both temporary server processes and terminates either remaining process in `finally`.

## Remaining non-code dependency

No local code finding can substitute for the two target-machine Evidence gates. TASK-002 must stay open until sandbox behavior and WSL2-to-Windows reachability/restart are measured and reviewed.
