# TASK-042 — P-V6-0 Current-main Audit and Requirement Adjudication

## Audit identity

- Fresh clone: `D:\BAI\bvp-v6-product-integration`.
- Branch baseline: `main` at `8d055773f3966e301badff28e565ffcf26578721`.
- Remote/default: `baisound/bai_video_production / main`.
- Initial worktree: clean.
- Stable release: `v0.20.1`; current main contains later R2/R3/R4 development.
- Handoff ZIP SHA-256: `938565f5a73f1406addb1202f2904fd63233e0d4329ef914b9f5282af3a54b0c`.
- Additive patch SHA-256: `902469681bd5d6e8737c7f5a1e8bf097614ee3c89ef1ef4544675613c7204a71`; `git apply --check` PASS.

The older `D:\BAI\TASK007` checkout remains preserved with untracked native Evidence and was not used as Implementation Source of Truth.

## Source curation

| Source | Classification | Use |
|---|---|---|
| live repository and Product Canonicals | CURRENT PRODUCT AUTHORITY | implementation and status truth |
| Owner instruction in this task | OWNER AUTHORITY | maximum priority and roadmap insertion |
| V6 handoff / mandate / checklist | DESIGN INPUT | mandatory review coverage; no code authority by itself |
| V6.1.1 HTML mock | UX REFERENCE | layout/interaction intent only |
| P01-P15 Scene book | REAL-PRODUCTION EVIDENCE | Start/End, Identity, Space, UI, Continuity and brand gates |
| spatial/composition knowledge Ver.2.0 | REAL-PRODUCTION EVIDENCE | Task Axis, Visibility, Depth Order, Final Shot and failure escalation |
| 34-scene production document | REAL-PRODUCTION EVIDENCE | timeline-first audio, narration, BGM/SFX and long production workflow |
| implementation-impact audit | AUDIT INPUT | revalidated against current main |

No BAI Development OS runtime or historical mock state is imported as Product authority.

## Current-state corrections to the handoff

1. The pack snapshot stopped near TASK-013 readiness. Live main additionally contains TASK-041 PR #47/#48 closure.
2. TASK-041 is not unstarted: durable placement review and Human decision UI are hosted-closed at implementation merge `8dd6434a65115d88641d0942b08788a9eceda279`.
3. TASK-041 still does not provide Provider execution, media derivation, TASK-026 compile, Resolve/Cubase mutation or a Project-level Music Plan; those are genuine remaining surfaces.
4. Canonical roadmap body includes Addendum XXXVIII while its title remains Ver.1.42 and some current-position lines still say TASK-041 hosted pending. This is documentation drift requiring synchronization.
5. Current remote main is newer than the preserved TASK007 checkout and is the only implementation baseline.

## Requirement adjudication and coverage

| V6 requirement | Current implementation | Classification | Design action |
|---|---|---|---|
| one Desktop Product | TASK-036 shell/trusted launcher/native acceptance | ALREADY_IMPLEMENTED foundation | extend the same shell; no second app |
| Planning / Scene Contract | TASK-027 Blueprint/Proposal/GO | PARTIAL | versioned Blueprint v2 migration |
| Start/End Character 0..N, Space 0..1, Composition 0..1 | current Scene-level `reference_ids` and `locked_reference` | CONTRACT_MIGRATION_REQUIRED | frame-bound typed bindings |
| iterative WORLD LOCK | TASK-037 Candidate/LOCK/STALE + TASK-038 Audit + TASK-040 Attempt | PARTIAL | projection and new reference Slot roles, not a new lifecycle |
| exact continuity | TASK-039 exact Asset/hash | ALREADY_IMPLEMENTED invariant | bind frame specs and prevent override |
| Task Axis / Visibility / Depth Order / Final Shot | TASK-013 Shot Feasibility fields and gates | PARTIAL | make explicit v2 composition contract |
| immutable Prompt history | TASK-040 | ALREADY_IMPLEMENTED foundation | retain body-private hash/ref model |
| Visual Prompt Director and JA/JA/EN layers | no Product service | NEW_CAPABILITY_REQUIRED | new compiler/director connected to TASK-040 |
| audio toggles affect prompt hash | no compiler layer | NEW_CAPABILITY_REQUIRED | immutable compilation input/version |
| Provider -> compatible Model | TASK-028 route/capability and TASK-032..034 settings | PARTIAL | projection only; no second catalog |
| Quick Generate | plan-bound queue only | NEW_CAPABILITY_REQUIRED | explicit quick intent/session authority and adoption route |
| generated result as reference | Candidate/Asset identities exist | PARTIAL | allow internal Candidate identity independent of favorite |
| Project Timeline audio | TASK-041 placement review + TASK-026 plan + narration cue foundation | PARTIAL | one authoritative Timeline model; reuse review service |
| Master SRT timing | Subtitle/Narration cue foundations | OWNER_DECISION_REQUIRED resolved in design | Timeline is authority; SRT is projection/import proposal |
| NLE interactions / 2h scale | minimum editing shell | PARTIAL | real time scale, selection/seek split, dynamic tracks |
| Export Queue | render commands and BackgroundJobRegistry only | NEW_CAPABILITY_REQUIRED | stale-bound durable queue and per-job authority |
| native generation resume | parked attempt and readiness Evidence | SUPERSEDED_AS_NEXT_ACTION | remains parked until V6 acceptance |

## Design Gap Register

| ID | Severity | Gap | Resolution route |
|---|---|---|---|
| V6-GAP-001 | CRITICAL | Scene-level references cannot express different Start/End people/space/composition | Blueprint v2 before UI |
| V6-GAP-002 | HIGH | legacy Blueprint migration could silently reinterpret Approved Plan hashes | explicit preview, Human review, new proposal revision/GO |
| V6-GAP-003 | HIGH | no typed reference roles for WORLD LOCK | evolve Production Control SlotKind compatibly |
| V6-GAP-004 | HIGH | Prompt layers and audio toggle compilation not durable | body-private compilation manifest + TASK-040 Prompt version |
| V6-GAP-005 | HIGH | Quick path could forge plan approval | independent quick intent authority; production adoption gated |
| V6-GAP-006 | HIGH | no single Project Timeline audio authority | Production Timeline authoritative; SRT derived/proposed |
| V6-GAP-007 | HIGH | Export queue could bypass per-job external mutation authority | exact hash binding, stale/reprepare and one-shot execution |
| V6-GAP-008 | MEDIUM | embedded shell UI is large and interaction semantics are coupled | bounded presentation modules and command-level tests |
| V6-GAP-009 | MEDIUM | long Timeline, large history and accessibility need real Evidence | P-V6-6 native acceptance matrix |
| V6-GAP-010 | MEDIUM | roadmap header/current-position drift | Ver.1.47 synchronization in this PR |

## Missing requirements discovered beyond the mock

- Legacy project migration preview must not write until explicit confirmation.
- Existing Approved Plans become stale; they are never silently rebound to v2.
- Frame reference availability change must stale dependent Prompt, Queue, Candidate and Export items.
- Same structural generation failure twice stops prompt micro-tuning and returns to Task Axis/layout/reference strategy.
- Source prompts and generated media require rights/provenance and retention identity.
- A two-hour Timeline needs bounded thumbnail/history loading and no full-DOM rendering.
- Project semantic data, UI layout profile and transient selection must remain separate.
- Provider timeout with unknown dispatch stays recovery-required and non-replayable.

## Task allocation decision

`TASK-042` is the next unused Product Task identity after live current-main inspection. It is allocated as one cross-cutting integration Task with sequential P-V6 slices. Completed TASK-036..041 records remain historical truth. TASK-041 supplies the hosted-closed placement-review foundation; TASK-042 owns the new Project Timeline Audio contract and integration so no competing timing model is created.

## Audit result

`CURRENT_MAIN_AUDIT_PASS / TASK_042_ALLOCATION_RECOMMENDED / ROADMAP_PROMOTION_REQUIRED_BEFORE_CODE`

Unresolved Critical/High design findings at this audit stage are routed into the full detailed design; implementation remains blocked until the design Critic/Judge closes them and the roadmap PR merges.
