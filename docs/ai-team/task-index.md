# Consumer Task Index

| Task | Title | Status | Authorization | Governance | Notes |
|---|---|---|---|---|---|
| TASK-001 | Project Foundation / Domain Model | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 25 | Historical alias `VIDEO-TASK-001` |
| TASK-002 | Resolve Capability Spike | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 22 | Resolve 21.0.2.4 sandbox mutation PASS; WSL2→Windows authenticated HTTP/restart PASS; Final IPC ADR accepted |
| TASK-003 | Asset Registry / Ingest / Path Resolver | COMPLETED | COMPLETED WITH AUTHORIZED IMPLEMENTATION | DEV-4 / score 33 | Package 0.3.0; secure canonical source ingest, rights/checksum, Path Resolver, source-manifest |
| TASK-004 | Media Normalization + Local Visual/Audio AI Runtime Foundation | CAPABILITY_VERIFIED_AWAITING_LIVE_BEHAVIORAL_EVIDENCE | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 / score 25 | Package 0.4.7; 250 tests; ComfyUI + Audacity/OpenVINO capability PASS; Attempt 07 failed before Audacity mutation because Windows low-level media ingest lacked `O_BINARY`; corrected and regression-pinned; Noise Suppression + 2-stem behavioral Evidence rerun pending; 4-stem fails closed on verified runtime because mode is UI-only |
| TASK-005,008,009,013,015..021 | Remaining product roadmap tasks | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Canonical identities defined in project roadmap |
| TASK-007 | Candidate Clip Graph / Cut Plan | IMPLEMENTED_AUTOMATED_VALIDATED | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Deterministic candidate graph + human CUT/KEEP review + second-stage plan approval; PRODUCT-ARCH-001 target Edit Workspace; no automatic external write |
| TASK-010 | Resolve Assembly MVP | NATIVE_VALIDATED_INTEGRATION_DESIGNED | OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | Real Resolve 21 assembly/linked A/V/idempotency/conflict and edit-aware subtitle semantics PASS; Shell integration remains TASK-036 |
| TASK-011 | Render QA / Loudness | NATIVE_VALIDATED_INTEGRATION_DESIGNED | OWNER_DIRECTED_IMPLEMENTATION | DEV-3/4 | Real Resolve render queue/artifact/video/audio/duration/LUFS/true-peak QA PASS; path-free report |
| TASK-012 | Manual Handoff / Cubase | NATIVE_VALIDATED_INTEGRATION_DESIGNED | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Real deterministic EDITOR_WORK + Cubase 13 48 kHz PCM return PASS; no automatic Cubase project conversion claim |
| TASK-006 | ASR / Transcript / Subtitle | SLICE_D_RELEASED_V0.17.0 | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Native FasterWhisper, Subtitle Workspace, resumable large-media transcription and canonical Resolve subtitle handoff released; actual Resolve mutation remains TASK-010 |
| TASK-014 | Voice TTS / Owner Narration | DESIGN_RECORDED_ADAPTER_FOUNDATION_EXISTS | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Existing ElevenLabs Pro owner-trained voice; private Voice Profile; read-only ownership/capability probe; timed TTS and 48 kHz Asset flow planned; paid probe remains explicit |
| TASK-023 | FasterWhisper Fast Local Provider | COMPLETE | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | Existing TASK-006 provider is canonical; 0.19.0 adds deterministic identity + diagnostic evidence CLI; PRODUCT-ARCH-001 target Subtitle Workspace is INTEGRATION_DESIGNED; no duplicate provider or ASR semantic change |
| TASK-024 | Silence / Filler / Disfluency Cut Candidate Worker | RELEASED_V0.18.0 | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | v0.18.0 formal release complete: 433 pass + 1 intentional skip, real-WAV FFmpeg/CLI PASS, native GUI regression PASS; no auto cut |
| TASK-025..026 | Remaining External-SKILL additions (collision-resolved) | NOT_STARTED | NOT_AUTHORIZED | Re-evaluate at kickoff | Premiere adapter and Audio Placement remain later work |
| TASK-022 | Timeline Mapping Service | COMPLETED | COMPLETED_WITH_OWNER_VERIFICATION | DEV-4 | Package 0.5.0; exact affine/NTSC/end-exclusive mapping, speed/gap, deterministic Plan/schema; native Windows 263/263 PASS |
| TASK-027 | AI Video Creation Studio / New Production Orchestrator | SLICE_A1_PRODUCTION_BLUEPRINT_FOUNDATION_IMPLEMENTED | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 candidate | 0.15.0 validated Scene Ledger, Reference Registry, real-first strategy and text-risk gates; GUI proposal/GO next |
| TASK-028 | AI Connection Provider / Model Routing | CAPABILITY_REGISTRY_IMPLEMENTED_AWAITING_NATIVE_WINDOWS_REGRESSION | OWNER_AUTHORIZED_IMPLEMENTATION | DEV-4 | 0.6.2 external media 293/293 PASS; 0.6.3 removes provider-purpose locking and adds exact model capability catalog plus generic execution registry; 305-test Windows gate pending |
| TASK-029 | Human Edit Learning / Federated Knowledge Evolution | PROPOSED | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Human action Evidence → hypothesis/multi-metric evaluation → Owner-local learning; opt-in anonymized cloud aggregation; signed Git-versioned Knowledge Packs |
| TASK-030 | OSS Public Repository Readiness | IMPLEMENTED_AWAITING_GITHUB_CI | OWNER_DIRECTED_IMPLEMENTATION | DEV-2 | 0.6.6 fixed runner media dependencies; 0.6.7 removes global OS mutation after 5/6 matrix jobs passed |
| TASK-031 | OSS Adoption, Demonstration and Impact Evidence | FOUNDATION_IMPLEMENTED_CONTINUOUS_EXECUTION | OWNER_DIRECTED_IMPLEMENTATION | DEV-2 | 0.7.0 architecture/roadmap visuals, five-minute demo, release/PyPI workflows, contributor and real-impact Evidence gates |
| TASK-032 | AI Connection Settings UI Foundation | NATIVE_WINDOWS_PASS_USABILITY_PENDING | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.10.0 native save/reload/conflict Evidence accepted; 2–3-person usability review due 08/31 |
| TASK-033 | Provider and Model Catalog Editor | NATIVE_WINDOWS_PASS | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.11.0 safe add/edit/disable Evidence accepted 2026-08-10 |
| TASK-034 | OS-backed Credential Onboarding | NATIVE_WINDOWS_PASS | OWNER_DIRECTED_IMPLEMENTATION | DEV-3 | 0.12.2 Catalog linkage, retained-key cleanup and per-Route password-manager lookup confirmed |
| TASK-035 | REAPER Audio Finishing Bridge / DaVinci Round-trip | PROPOSED | OWNER_DIRECTED_DESIGN | DEV-4 candidate | Native ReaScript bridge first; iZotope Ozone/Nectar/Neutron capability levels; verified mix/stem Assets back to Resolve; optional MCP facade only after security review |
| TASK-036 | Unified Desktop Editing Shell / Minimum Editing Workflow Integration | W0_W1_PARTIAL_W2_PACKAGED_NATIVE_E2E_PASS | OWNER_DIRECTED_IMPLEMENTATION | DEV-4 | Trusted packaged launcher completed real Windows ingest/local ASR/subtitle/review/Resolve apply/native Render QA/atomic EDITOR_WORK with final UI `NONE`; clean-profile/runtime recovery/full DPI/accessibility/install-path acceptance, conversation-free restart and Pilot Context Cost remain |
| TASK-037 | Asset Registry 2 / Scene Asset Slot & Dependency Graph | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | Extends TASK-003 with Scene Asset Slot, Candidate Version, lifecycle, LOCK/STALE and dependency graph; does not reopen ingest authority |
| TASK-038 | Audit Workspace / Candidate Quality Loop | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | AI/Human separate review, dimension scores/findings, Failure Codes, alternate use, regeneration, compare/history and final lock |
| TASK-039 | Continuity Map / Boundary Integrity & Stale Propagation | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | DIRECT_CONTINUATION exact Asset/hash, End->Start graph, Character/Space continuity and Human-resolved Stale propagation |
| TASK-040 | Prompt Registry / Generation Evidence & Regeneration Routing | PROPOSED | NOT_AUTHORIZED | DEV-4 candidate | Prompt Entity/Version, provider profile, input/output identity, parent Candidate, Keep Conditions and failure-driven regeneration routes |
| TASK-041 | Audio Workspace / Embedded Audio Separation & Placement UX | PROPOSED | NOT_AUTHORIZED | DEV-3/4 candidate | VFX/generated-media audio policy, non-destructive strip derivative, review/lock lanes and TASK-026 placement-plan UX |

## Roadmap authority

`docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` is the current Project-level roadmap. Ver.1.5 records Owner-directed editing-first prioritization, production Blueprint intake and optional professional-audio expansion. The roadmap is planning authority, not Owner Authorization for later TASKs.

## Route control

TASK-004 is completed. Owner-directed continuation authorized TASK-027 through TASK-034 and the editing-first TASK-006 slices recorded above. Proposed later work remains unauthorized until Owner instruction; a configured credential or enabled AI proofreading setting never authorizes Provider execution, suggestion acceptance or GO.

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
