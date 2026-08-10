# Consumer Task Index

| Task | Title | Status | Authorization | Governance | Notes |
|---|---|---|---|---|---|
| TASK-001 | Project Foundation / Domain Model | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 25 | Historical alias `VIDEO-TASK-001` |
| TASK-002 | Resolve Capability Spike | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 22 | Resolve 21.0.2.4 sandbox mutation PASS; WSL2→Windows authenticated HTTP/restart PASS; Final IPC ADR accepted |
| TASK-003 | Asset Registry / Ingest / Path Resolver | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 33 | Package 0.3.0; secure canonical source ingest, rights/checksum, Path Resolver, source-manifest |
| TASK-004 | Media Normalization + Local Visual/Audio AI Runtime Foundation | CAPABILITY_VERIFIED_AWAITING_LIVE_BEHAVIORAL_EVIDENCE | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 / score 25 | Package 0.4.7; 250 tests; ComfyUI + Audacity/OpenVINO capability PASS; Attempt 07 failed before Audacity mutation because Windows low-level media ingest lacked `O_BINARY`; corrected and regression-pinned; Noise Suppression + 2-stem behavioral Evidence rerun pending; 4-stem fails closed on verified runtime because mode is UI-only |
| TASK-005..021 | Product roadmap tasks | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Canonical identities defined in project roadmap |
| TASK-023..026 | Remaining External-SKILL additions (collision-resolved) | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Prospective canonical re-numbering; historical documents unchanged |
| TASK-022 | Timeline Mapping Service | COMPLETED | COMPLETED_WITH_OWNER_VERIFICATION | DEV-4 | Package 0.5.0; exact affine/NTSC/end-exclusive mapping, speed/gap, deterministic Plan/schema; native Windows 263/263 PASS |
| TASK-027 | AI Video Creation Studio / New Production Orchestrator | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | GUI intent → AI proposal/revision → GO → generation/orchestration → replaceable Asset slots → Resolve assembly |
| TASK-028 | AI Connection Provider / Model Routing | ROUTING_CORE_IMPLEMENTED_AWAITING_NATIVE_WINDOWS_REGRESSION | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 | Package 0.6.0; per-workload AI/free/offline policy, exact provider/model/reasoning routing and secret-free persisted profiles; 273-test Windows gate pending |

## Roadmap authority

`docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` is the current Project-level roadmap. Ver.1.4 preserves Owner-directed editing-first prioritization while recording TASK-004's expanded runtime foundation. The roadmap is planning authority, not Owner Authorization for later TASKs.

## Route control

TASK-004 remains the only active authorized Consumer TASK until target local-runtime Evidence is reviewed and a final Judge decision closes it. No later Consumer TASK is started or authorized without Owner instruction.
