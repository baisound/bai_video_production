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
| TASK-028 | AI Connection Provider / Model Routing | CAPABILITY_REGISTRY_IMPLEMENTED_AWAITING_NATIVE_WINDOWS_REGRESSION | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 | 0.6.2 external media 293/293 PASS; 0.6.3 removes provider-purpose locking and adds exact model capability catalog plus generic execution registry; 305-test Windows gate pending |
| TASK-029 | Human Edit Learning / Federated Knowledge Evolution | PROPOSED | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Human action Evidence → hypothesis/multi-metric evaluation → Owner-local learning; opt-in anonymized cloud aggregation; signed Git-versioned Knowledge Packs |
| TASK-030 | OSS Public Repository Readiness | IMPLEMENTED_AWAITING_GITHUB_CI | OWNER_DIRECTED_IMPLEMENTATION | DEV-2 | 0.6.6 fixed runner media dependencies; 0.6.7 removes global OS mutation after 5/6 matrix jobs passed |
| TASK-031 | OSS Adoption, Demonstration and Impact Evidence | FOUNDATION_IMPLEMENTED_CONTINUOUS_EXECUTION | OWNER_DIRECTED_IMPLEMENTATION | DEV-2 | 0.7.0 architecture/roadmap visuals, five-minute demo, release/PyPI workflows, contributor and real-impact Evidence gates |
| TASK-032 | AI Connection Settings UI Foundation | NATIVE_WINDOWS_PASS_USABILITY_PENDING | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.10.0 native save/reload/conflict Evidence accepted; 2–3-person usability review due 08/31 |
| TASK-033 | Provider and Model Catalog Editor | CATALOG_EDITOR_IMPLEMENTED_AWAITING_NATIVE_EVIDENCE | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.11.0 safe add/edit/disable UI with truthful adapter status; native Evidence due 08/24 |

## Roadmap authority

`docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` is the current Project-level roadmap. Ver.1.4 preserves Owner-directed editing-first prioritization while recording TASK-004's expanded runtime foundation. The roadmap is planning authority, not Owner Authorization for later TASKs.

## Route control

TASK-004 is completed. Owner-directed continuation authorized TASK-027 through TASK-033 design/implementation slices recorded above. Proposed later work remains unauthorized until Owner instruction; a Catalog entry alone never authorizes its Provider adapter or execution.
