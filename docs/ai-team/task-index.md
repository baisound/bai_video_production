# Consumer Task Index

| Task | Title | Status | Authorization | Governance | Notes |
|---|---|---|---|---|---|
| TASK-001 | Project Foundation / Domain Model | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 25 | Historical alias `VIDEO-TASK-001` |
| TASK-002 | Resolve Capability Spike | IMPLEMENTED_AWAITING_FINAL_LIVE_EVIDENCE | AUTHORIZED_FOR_IMPLEMENTATION | DEV-4 / score 22 | Attempt 02 read-only Resolve accepted; 0.2.3 runner corrective retry required for sandbox behavior + WSL2 IPC + final ADR |
| TASK-003..021 | Product roadmap tasks | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Canonical identities defined in project roadmap |
| TASK-022..026 | External-SKILL additions (collision-resolved) | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Prospective canonical re-numbering; historical documents unchanged |

## Roadmap authority

`docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` is the current Project-level roadmap. It is a planning authority, not Owner Authorization for later TASKs. Ver.1.1 applies Owner-directed editing-first prioritization while preserving dependency/Safety Floor gates.

## Route control

No later Consumer TASK is started or authorized while TASK-002 remains open. Current route: obtain sandbox behavioral Evidence and WSL2-to-Windows IPC Evidence, then close the Final IPC ADR and DEV-4 TASK-002 review.
