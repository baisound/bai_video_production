# TASK-002 — Independent Critic Implementation Review

## Decision

`PASS_WITH_LIVE_EVIDENCE_GATE`

Blocking code/design findings discovered during review were corrected. No unresolved local blocking defect remains. TASK completion is still withheld because the declared target-machine Evidence gate is unmet.

## Findings and corrections

| ID | Finding | Severity | Correction | Status |
|---|---|---|---|---|
| C-001 | Supervisor timeout wrote an ad-hoc JSON shape outside canonical report schemas | BLOCKING | Timeout and worker failure now emit schema-valid capability/IPC reports with a typed `supervision` envelope | RESOLVED |
| C-002 | CLI schema lookup depended on repository-relative `schemas/`, risking installed-wheel failure | BLOCKING | Canonical schemas are mirrored as package resources; equality is contract-tested; wheel is run outside checkout | RESOLVED |
| C-003 | Missing candidate methods could be classified `UNSUPPORTED` without semantic/live proof | BLOCKING | Absence remains `PROBE_REQUIRED`; `UNSUPPORTED` requires explicit target evidence | RESOLVED |
| C-004 | HTTP recovery restarted on a new random port, which did not prove configured endpoint recovery | BLOCKING | Restart now rebinds the exact same loopback address/port | RESOLVED |
| C-005 | Windows core-candidate completion flag could be true from platform measurement even when the candidate failed | HIGH | Flag now requires target-platform measurement **and** `MEASURED` status for both HTTP and Named Pipe | RESOLVED |
| C-006 | Resolve bridge dependency import errors could be hidden as simple module absence | HIGH | Internal import/OSError failures are normalized as `ERR_RESOLVE_SCRIPT_MODULE_IMPORT_FAILED` | RESOLVED |

## Safety review

Default execution calls only the safe-read allowlist. Mutation authorization is fail-closed and sandbox-prefixed, while actual mutation sequences remain disabled in this implementation. Deletion, forced Resolve termination and existing non-sandbox/human Timeline writes remain prohibited.

## Remaining non-defect gate

Windows/Resolve and WSL2 evidence is not reproducible inside this Linux build environment. This is an environmental completion dependency, not permission to infer support.
