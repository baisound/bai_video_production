# Consumer Task Index

| Task | Title | Status | Authorization | Governance | Notes |
|---|---|---|---|---|---|
| TASK-001 | Project Foundation / Domain Model | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 25 | Historical alias `VIDEO-TASK-001` |
| TASK-002 | Resolve Capability Spike | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 22 | Resolve 21.0.2.4 sandbox mutation PASS; WSL2→Windows authenticated HTTP/restart PASS; Final IPC ADR accepted |
| TASK-003 | Asset Registry / Ingest / Path Resolver | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 33 | Package 0.3.0; secure canonical source ingest, rights/checksum, Path Resolver, source-manifest |
| TASK-004 | Media Normalization + Local Visual/Audio AI Runtime Foundation | CAPABILITY_VERIFIED_AWAITING_LIVE_BEHAVIORAL_EVIDENCE | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 / score 25 | Package 0.4.7; 250 tests; ComfyUI + Audacity/OpenVINO capability PASS; Attempt 07 failed before Audacity mutation because Windows low-level media ingest lacked `O_BINARY`; corrected and regression-pinned; Noise Suppression + 2-stem behavioral Evidence rerun pending; 4-stem fails closed on verified runtime because mode is UI-only |
| TASK-005,008,009,015..021 | Remaining product roadmap tasks | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Canonical identities defined in project roadmap |
| TASK-007 | Candidate Clip Graph / Cut Plan | IMPLEMENTED_AUTOMATED_VALIDATED_SHELL_INTEGRATED | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Deterministic candidate graph + human CUT/KEEP review + second-stage plan approval; TASK-036 W2 Edit Workspace PASS; no automatic external write |
| TASK-010 | Resolve Assembly MVP | NATIVE_VALIDATED_SHELL_INTEGRATED | OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | Real Resolve 21 assembly/linked A/V/idempotency/conflict/edit-aware subtitle semantics and TASK-036 W2 Shell route PASS |
| TASK-011 | Render QA / Loudness | NATIVE_VALIDATED_SHELL_INTEGRATED | OWNER_DIRECTED_IMPLEMENTATION | DEV-3/4 | Real Resolve render queue/artifact/video/audio/duration/LUFS/true-peak QA and TASK-036 W2 Shell route PASS; path-free report |
| TASK-012 | Manual Handoff / Cubase | NATIVE_VALIDATED_SHELL_INTEGRATED | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Real deterministic EDITOR_WORK, Cubase 13 48 kHz PCM return and TASK-036 W2 Shell route PASS; no automatic Cubase project conversion claim |
| TASK-013 | Shot Feasibility / Visual Compliance / Creative Orchestration | COMPLETE_R3_PRODUCT_PROMOTION | COMPLETED_WITH_OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | PR #30 passed 9/9 and merged at exact main be8ea573; durable Generation Safety and Visual Compliance -> TASK-038 Audit complete; no Provider/paid/NLE execution |
| TASK-006 | ASR / Transcript / Subtitle | SLICE_D_RELEASED_SHELL_INTEGRATED_V0.20.1 | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Native FasterWhisper, Subtitle Workspace, resumable transcription, Resolve subtitle handoff and TASK-036 W2 Shell route PASS |
| TASK-014 | Voice TTS / Owner Narration | DESIGN_RECORDED_ADAPTER_FOUNDATION_EXISTS | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Existing ElevenLabs Pro owner-trained voice; private Voice Profile; read-only ownership/capability probe; timed TTS and 48 kHz Asset flow planned; paid probe remains explicit |
| TASK-023 | FasterWhisper Fast Local Provider | COMPLETE_SHELL_INTEGRATED_V0.20.1 | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Existing TASK-006 provider is canonical; deterministic identity/diagnostic CLI retained; TASK-036 W2 local ASR Shell route PASS; no duplicate provider or ASR semantic change |
| TASK-024 | Silence / Filler / Disfluency Cut Candidate Worker | RELEASED_V0.18.0_SHELL_INTEGRATED_V0.20.1 | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Review-only cut candidates remain non-mutating; TASK-036 W2 Human Cut Review Shell route PASS |
| TASK-025..026 | Remaining External-SKILL additions (collision-resolved) | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Premiere adapter and Audio Placement remain later work |
| TASK-022 | Timeline Mapping Service | COMPLETED | COMPLETED_WITH_OWNER_VERIFICATION | DEV-4 | Package 0.5.0; exact affine/NTSC/end-exclusive mapping, speed/gap, deterministic Plan/schema; native Windows 263/263 PASS |
| TASK-027 | AI Video Creation Studio / New Production Orchestrator | R2_PLANNING_WORKSPACE_MINIMUM_COMPLETE_FUTURE_SLICES_REMAIN | OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | Bounded minimum: persisted Proposal/Scene Contract review, exact Human GO and separate Approved Plan -> TASK-037 Slot installation; PR #28 9/9 and exact main 91d76feb; Provider/NLE and Generation Queue slices remain |
| TASK-028 | AI Connection Provider / Model Routing | CAPABILITY_REGISTRY_IMPLEMENTED_AWAITING_NATIVE_WINDOWS_REGRESSION | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 | 0.6.2 external media 293/293 PASS; 0.6.3 removes provider-purpose locking and adds exact model capability catalog plus generic execution registry; 305-test Windows gate pending |
| TASK-029 | Human Edit Learning / Federated Knowledge Evolution | PROPOSED | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Human action Evidence → hypothesis/multi-metric evaluation → Owner-local learning; opt-in anonymized cloud aggregation; signed Git-versioned Knowledge Packs |
| TASK-030 | OSS Public Repository Readiness | IMPLEMENTED_AWAITING_GITHUB_CI | OWNER_DIRECTED_IMPLEMENTATION | DEV-2 | 0.6.6 fixed runner media dependencies; 0.6.7 removes global OS mutation after 5/6 matrix jobs passed |
| TASK-031 | OSS Adoption, Demonstration and Impact Evidence | FOUNDATION_IMPLEMENTED_CONTINUOUS_EXECUTION | OWNER_DIRECTED_IMPLEMENTATION | DEV-2 | 0.7.0 architecture/roadmap visuals, five-minute demo, release/PyPI workflows, contributor and real-impact Evidence gates |
| TASK-032 | AI Connection Settings UI Foundation | NATIVE_WINDOWS_PASS_USABILITY_PENDING | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.10.0 native save/reload/conflict Evidence accepted; 2–3-person usability review due 08/31 |
| TASK-033 | Provider and Model Catalog Editor | NATIVE_WINDOWS_PASS | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.11.0 safe add/edit/disable Evidence accepted 2026-08-10 |
| TASK-034 | OS-backed Credential Onboarding | NATIVE_WINDOWS_PASS | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.12.2 Catalog linkage, retained-key cleanup and per-Route password-manager lookup confirmed |
| TASK-035 | REAPER Audio Finishing Bridge / DaVinci Round-trip | PROPOSED | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Native ReaScript bridge first; iZotope Ozone/Nectar/Neutron capability levels; verified mix/stem Assets back to Resolve; optional MCP facade only after security review |
| TASK-036 | Unified Desktop Editing Shell / Minimum Editing Workflow Integration | COMPLETE_MINIMUM_EDITING_PRODUCT_MVP_PASS_RELEASED_0_20_1 | OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | W0 clean-profile/runtime/path, W1 display/accessibility and W2 packaged native route PASS; PR #22 9/9, exact main SHA, annotated v0.20.1 and stable GitHub Release complete |
| TASK-037 | Asset Registry 2 / Scene Asset Slot & Dependency Graph | COMPLETE_R2_PRODUCT_PROMOTION | COMPLETED_WITH_OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | PR #24 passed 9/9 and merged at exact main 045bd7ed; durable Application Service and Desktop Production Control workspace complete; no release at this checkpoint |
| TASK-038 | Audit Workspace / Candidate Quality Loop | COMPLETE_R2_PRODUCT_PROMOTION | COMPLETED_WITH_OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | PR #26 passed 9/9 and merged at exact main 9a999645; durable two-store Human decision/recovery and user-facing Audit history/actions complete; no release at this checkpoint |
| TASK-039 | Continuity Map / Boundary Integrity & Stale Propagation | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | DIRECT_CONTINUATION exact Asset/hash, End->Start graph, Character/Space continuity and Human-resolved Stale propagation |
| TASK-040 | Prompt Registry / Generation Evidence & Regeneration Routing | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | Prompt Entity/Version, provider profile, input/output identity, parent Candidate, Keep Conditions and failure-driven regeneration routes |
| TASK-041 | Audio Workspace / Embedded Audio Separation & Placement UX | PROPOSED | NOT_AUTHORIZED | DEV-3/4 candidate | VFX/generated-media audio policy, non-destructive strip derivative, review/lock lanes and TASK-026 placement-plan UX |

## Roadmap authority

`docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` is the current Project-level roadmap. Ver.1.5 records Owner-directed editing-first prioritization, production Blueprint intake and optional professional-audio expansion. The roadmap is planning authority, not Owner Authorization for later TASKs.

## Route control

TASK-004, TASK-036, TASK-037, TASK-038, TASK-013 R3 Product promotion and the bounded TASK-027 Planning Workspace minimum are completed. TASK-039 Continuity Map / STALE propagation is next on a dedicated branch. A configured credential or enabled AI setting never authorizes Provider execution, suggestion acceptance or GO.

## Registered Future Design / Knowledge Intake

| Knowledge / Design | Future Owner | Status | Contract |
|---|---|---|---|
| `BVP-KNOWLEDGE-REFIMG-001` Scene-Compatible Reference Image Rule | TASK-013 | DESIGN_REGISTERED / IMPLEMENTATION_NOT_AUTHORIZED | Character identity, Room master and Scene Shot composition remain separate reference roles; Shot Feasibility must PASS before Start/End generation; DIRECT_CONTINUATION reuses exact previous End Asset |
| `PRODUCT-CONTROL-001` Production Control Plane | TASK-036..041 + existing owners | DESIGN_REGISTERED / ROADMAP_CANONICAL | Plan -> Scene -> Asset Slot -> Candidate -> Audit -> Human Decision -> Lock traceability; no silent overwrite; Reject != Delete; LOCK/STALE; regeneration Evidence |

This registration does not change editing-first execution order and does not reopen TASK-004.

## Cross-Cutting Product Architecture Contracts

| Contract | Status | Applies To | Requirement |
|---|---|---|---|
| `PRODUCT-ARCH-001` Unified Desktop Application | CANONICAL | All Product TASKs | Final Product is one BAI Video Production Desktop Application entrypoint; user-facing capabilities must define Shell integration |
| Unified Application Integration Contract | CANONICAL | User/Operator-facing TASKs | Detailed design must define entrypoint, workspace, context, progress/error/recovery, file UX, worker lifecycle and native acceptance |
| `PRODUCT-CONTROL-001` Production Control Plane | CANONICAL | Planning/Generation/Asset/Audit/Continuity/Audio/Knowledge flows | Human Final Authority; Plan-to-Asset traceability; Evidence by default; version-not-overwrite; Reject != Delete; LOCK/STALE; no silent auto-fix |

These contracts do not allocate a new TASK number and do not change existing TASK ownership.
