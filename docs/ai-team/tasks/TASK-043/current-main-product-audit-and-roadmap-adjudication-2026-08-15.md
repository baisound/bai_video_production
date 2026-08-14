# TASK-043 — Current-main Product Audit and Roadmap Adjudication

- Date: 2026-08-15
- Mode: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
- Audit baseline: `main@6784a44e6831daa2b3db8ff85e2abe7b197ba3de`
- Stable Release/Tag/package: `v0.20.1 / v0.20.1 / 0.20.1`
- Open Pull Requests at audit: `0`
- Latest main hosted checks: `Security=PASS / CI=PASS`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`

## 1. Source of Truth decision

Current GitHub `main` is the implementation Source of Truth. The prior handoff,
conversation state and old implementation checkout are evidence only.

| Input | Classification | Decision |
|---|---|---|
| main `6784a44` / PR #61 | `CONFIRMED_CURRENT` | P-V6-4 design is merged; documents saying `HOSTED_PENDING` are stale. |
| Release `v0.20.1` | `CONFIRMED_CURRENT` | Latest stable Product release. |
| TASK-036 W0/W1/W2 Evidence | `CONFIRMED_HISTORICAL` | Minimum editing Shell/native release remains accepted; it does not prove the full V6 NLE. |
| TASK-042 P-V6-1..3 | `ALREADY_IMPLEMENTED` | Blueprint v2, WORLD LOCK projection, Prompt compilation, Provider projection and Quick intent exist. |
| TASK-042 P-V6-4 design | `CONFIRMED_CURRENT` | Valid input to the rebuild, but not implementation authority under the replacement Directive. |
| two untracked Timeline Audio files in old checkout | `UNVERIFIED` | Preserve and isolate. Review only after the new Project contract. |
| former two-main-merge cadence instruction | `SUPERSEDED` | Replaced by this Owner Directive; repository PR protection still applies. |
| automatic Native H3 replay | `CONFLICTS_WITH_CURRENT_CANONICAL` | Existing recovery Evidence prohibits replay of the unknown-state attempt. |
| paid narration/Provider execution | `OWNER_DECISION_REQUIRED` | Parked Human Gate. |

No unknown change is discarded. The working branch was created from a clean
fresh clone; the old WIP remains in its original checkout.

## 2. Existing Product capability

### Confirmed implemented

- exact rational frame/time mapping, Asset ingest, rights and checksums;
- local transcription, subtitles, Cut Candidate review and approved Edit Plan;
- Resolve assembly/render QA and Cubase handoff native Evidence;
- Blueprint v2 and frame-bound Scene references;
- Candidate/Audit/LOCK/STALE and continuity propagation;
- Prompt/Attempt lineage, Provider/Model readiness projection and Quick intent;
- generation queue admission and local execution safety boundaries;
- Audio Workspace placement review foundation;
- single packaged Windows Shell and minimum editing route;
- atomic writes, checksums and CAS inside multiple individual domain stores;
- some cross-store bundles and task-specific recovery journals.

### Confirmed gaps or partial contracts

- the Product has many independent `1.0.0` JSON stores, but no unified Project
  Manifest that binds a reopenable set of child snapshot versions and hashes;
- most JSON stores reject any other version and have no general migrator;
- the Shell background-job registry is memory-only and intentionally excluded
  from current desktop checkpoints;
- the current UI has a fixed V1/S1/C1/A1/A2/A3 layout and fixed ruler/playhead;
- generic clips do not seek; only Cut Candidate review has a bounded click path;
- dynamic track add/remove, zoom, Fit Entire, scroll model, trim, snap and IN/OUT
  editing are absent or unverified;
- generic Undo/Redo, Autosave, user-visible Backup and crash-safe edit history are
  absent;
- no durable Product Export Queue with restart/idempotency/unknown-state recovery
  was found;
- the Shell `書き出し` workspace label is not evidence that export behavior exists;
- P-V6-4 Timeline Audio is design-only on main;
- TASK-013 Native H3 and paid TASK-014 remain parked.

## 3. Owner requirement reconciliation

| Requirement | Classification | Adjudication |
|---|---|---|
| Start/End frame binding | `PARTIALLY_IMPLEMENTED` | Blueprint v2 contracts exist; full variable Character 0..N / Space 0..1 / Composition 0..1 Product editing and migration acceptance remain. |
| WORLD LOCK lifecycle | `PARTIALLY_IMPLEMENTED` | Existing Candidate/Audit/LOCK/STALE is canonical; UI and project-wide repeated-generation flow need integration, not a second registry. |
| Visual Prompt Director | `PARTIALLY_IMPLEMENTED` | Compiler and immutable Prompt Evidence exist; full user-facing layered editor/proofreading path remains. |
| AI Video prompt switches | `PARTIALLY_IMPLEMENTED` | Intent contracts exist; BGM/SE/Ambience/Narration compilation into the visible workflow remains. |
| Provider -> Model selector | `PARTIALLY_IMPLEMENTED` | Catalog/capability projection exists; integrated two-stage selector and execution-state UX remain. |
| Timeline Audio | `NEW_CAPABILITY_REQUIRED` | Design is merged; implementation and Project persistence are not. |
| Unified Editor | `ARCHITECTURE_REFACTOR_REQUIRED` | Current minimum Shell is valid but not the requested practical NLE. |
| Export Queue | `NEW_CAPABILITY_REQUIRED` | Requires durable jobs, recovery and external NLE idempotency. |
| Quick Generate | `PARTIALLY_IMPLEMENTED` | Intent/CAS/read-only adoption exist; user-facing flow must remain Human/Provider gated. |

## 4. Major-refactor classification

| Concern | Classification | Evidence and required action |
|---|---|---|
| Architecture | `ARCHITECTURE_REFACTOR_REQUIRED` | Add a Product Project coordination layer; preserve domain owners. |
| Domain boundaries | `IMPROVEMENT_REQUIRED` | Formalize Project envelope vs child-store ownership and no-duplicate rules. |
| Schema/versioning | `CONTRACT_MIGRATION_REQUIRED` | Replace hard-coded single-version reopen assumptions with a registry. |
| Migration | `NEW_FEATURE_REQUIRED` | Read-only plan, copy-on-write apply, verification and rollback. |
| Project save | `ARCHITECTURE_REFACTOR_REQUIRED` | One manifest binds exact child snapshot hashes. |
| Recovery | `PARTIALLY_IMPLEMENTED` | Generalize task-local journals into a Project save coordinator. |
| STALE | `ALREADY_IMPLEMENTED` | Reuse TASK-037/039; add Project dependency projection only. |
| Undo/Redo | `NEW_FEATURE_REQUIRED` | Bounded compensating-command history; never delete Evidence. |
| Asset lifecycle | `ALREADY_IMPLEMENTED` | Reuse TASK-003/037. |
| Generated provenance | `ALREADY_IMPLEMENTED` | Reuse Prompt/Attempt/Candidate lineage. |
| Provider capability | `PARTIALLY_IMPLEMENTED` | Catalog exists; integrated state UX and snapshot compatibility remain. |
| Cost estimation | `PARTIALLY_IMPLEMENTED` | Budget ceiling exists; exact/unknown estimates need consistent projection. |
| Local/cloud execution | `PARTIALLY_IMPLEMENTED` | Local adapter exists; paid/cloud remains gated. |
| Background jobs | `ARCHITECTURE_REFACTOR_REQUIRED` | Memory-only Shell jobs must become durable records. |
| Queue | `PARTIALLY_IMPLEMENTED` | Generation queue exists; export/background queue does not. |
| Unknown-state timeout | `PARTIALLY_IMPLEMENTED` | Native H3 is safe; define a shared job terminal state model. |
| Idempotency | `PARTIALLY_IMPLEMENTED` | Resolve and stores have bounded guarantees; unify job operation identity. |
| Security | `ALREADY_IMPLEMENTED` | Preserve fail-closed paths, symlink checks and allowed roots. |
| Credential | `ALREADY_IMPLEMENTED` | OS-backed onboarding exists; never include secrets in Project files. |
| Prompt privacy | `ALREADY_IMPLEMENTED` | Private body references/hashes exist; extend export/redaction checks. |
| Performance | `IMPROVEMENT_REQUIRED` | Add bounded manifest loading, lazy child opening and long-project budgets. |
| 2h+ Timeline | `NEW_FEATURE_REQUIRED` | Virtualized tracks, viewport math and scale fixtures. |
| large Asset Library | `IMPROVEMENT_REQUIRED` | Add pagination/index projections; avoid full payload in Project manifest. |
| accessibility | `PARTIALLY_IMPLEMENTED` | Shell baseline passed; full timeline keyboard semantics remain. |
| multi-monitor / DPI | `ALREADY_IMPLEMENTED` | W1 accepted; rerun after the major UI refactor. |
| keyboard shortcuts | `NEW_FEATURE_REQUIRED` | Define command map and accessible alternatives. |
| Native file picker | `ALREADY_IMPLEMENTED` | Existing trusted native dialog is reusable. |
| crash recovery | `PARTIALLY_IMPLEMENTED` | Existing checkpoints exclude active jobs; add Project recovery. |
| autosave | `NEW_FEATURE_REQUIRED` | Add quiescent/debounced snapshot policy. |
| backup | `NEW_FEATURE_REQUIRED` | Add bounded rotation and explicit restore preview. |
| external NLE export | `PARTIALLY_IMPLEMENTED` | Resolve assembly exists; durable Export Queue is missing. |
| telemetry | `DEFER` | Local structured Evidence first; no new outbound telemetry. |
| Evidence | `ALREADY_IMPLEMENTED` | Extend with Project migration/recovery/job events. |
| learning | `DEFER` | TASK-029 remains later; no automatic learning from private projects. |
| regression prevention | `IMPROVEMENT_REQUIRED` | Add compatibility corpus and old-project round trips. |
| release engineering | `ALREADY_IMPLEMENTED` | Existing CI/tag/release process is valid; release only meaningful slices. |
| developer experience | `IMPROVEMENT_REQUIRED` | Central codec/migrator and fixture builder reduce store-specific repetition. |
| user experience | `ARCHITECTURE_REFACTOR_REQUIRED` | Replace static demonstration surfaces with real command/state projections. |

## 5. Roadmap adjudication

The old order put Timeline Audio directly before the full Shell/Export slice.
That order is unsafe because both would persist new mutable state on top of a
fragmented reopen/recovery contract. The canonical sequence becomes:

```text
TASK-043 Product Project / Migration / Recovery Foundation
    -> TASK-042 P-V6-4 Timeline Audio implementation
    -> TASK-044 Interactive Timeline / Unified NLE / Export Queue
    -> TASK-045 V6 Native Acceptance / Migration Corpus / Release
    -> TASK-013 Native H3 re-evaluation (separate Human Gate)
```

- TASK-042 P-V6-1..3 and the P-V6-4 design remain valid history.
- P-V6-5 responsibility is split into TASK-044.
- P-V6-6 responsibility is split into TASK-045.
- TASK-043 is a prerequisite, not a claim that the Product currently has these
  capabilities.
- Foundation-only checkpoints are not releases. The next SemVer is decided from
  the actual integrated user-facing slice and compatibility result.

## 6. Human Gates and parked work

| Work | State | Resume condition |
|---|---|---|
| TASK-013 real Native H3 attempt | `READY_FOR_HUMAN_GATE / NO_REPLAY` | safe runtime review and explicit fresh execution identity |
| TASK-014 paid narration | `READY_FOR_HUMAN_GATE` | explicit paid execution and credential authorization |
| destructive migration of a human project | `READY_FOR_HUMAN_GATE` | backup, preview and explicit target approval |
| Production Deploy | `READY_FOR_HUMAN_GATE` | separate Owner authorization |

These parked Tasks do not block the local, deterministic TASK-043 design and
implementation route.

## 7. Audit conclusion

The Repository is healthy and its completed foundations remain valuable, but
the roadmap status and Product persistence architecture are not ready for the
requested full V6 editor. TASK-043 is therefore the highest-priority runnable
unit. Its design may proceed; implementation requires the Critic/Judge gate in
the companion detailed design record.

