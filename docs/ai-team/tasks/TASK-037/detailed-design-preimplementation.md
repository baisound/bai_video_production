# TASK-037 — Asset Registry 2 / Scene Asset Slot & Dependency Graph
## Pre-implementation Detailed Design Ver.0.9

- Date: 2026-08-13
- Status: `DESIGN_AHEAD / IMPLEMENTATION_NOT_AUTHORIZED_BY_THIS_DOCUMENT`
- Parent: TASK-003 Asset Registry, TASK-027 Production Blueprint foundation, PRODUCT-CONTROL-001

## Objective

Extend the existing Asset Registry without reopening secure ingest ownership so production intent can address a stable Scene Asset Slot while generated/imported outputs remain immutable Candidate versions.

Canonical trace:

`Plan -> Scene -> Asset Slot -> Candidate -> Audit -> Human Decision -> Locked Asset`.

## Core entities

### SceneAssetSlot

- `slot_id`
- `project_id`
- `scene_id`
- `slot_kind` (`START_FRAME`, `END_FRAME`, `VIDEO`, `VFX`, `SE`, `BGM`, `NARRATION`, extensible)
- `required`
- `status`
- `locked_candidate_id`
- `stale_state`
- `created_at`
- `revision`

### AssetCandidate

- `candidate_id`
- `slot_id`
- `asset_id` (TASK-003 canonical Asset)
- `generation_job_id` nullable
- `parent_candidate_id` nullable
- `candidate_version`
- `lifecycle_state`
- `created_at`
- `supersedes` nullable

### DependencyEdge

- `from_entity_type/id/hash`
- `to_entity_type/id`
- `dependency_kind`
- `continuity_boundary` nullable
- `created_at`

## Lifecycle

Candidate states:

`CREATED -> READY_FOR_AUDIT -> ACCEPTED | REJECTED | ALTERNATE_USE`

A Human lock is separate:

`ACCEPTED -> LOCKED`

Rules:

- regeneration creates a new Candidate;
- Reject != physical delete;
- LOCKED bytes/asset identity are immutable;
- changing upstream dependency marks dependent slots/candidates `STALE`;
- STALE never silently unlocks/replaces/regenerates;
- Human explicitly resolves STALE.

## TASK-003 boundary

TASK-037 stores production relationship metadata and references TASK-003 `asset_id`/checksum. It must not duplicate raw file storage, rights evidence, secure ingest or canonical path resolution.

## Concurrency

- optimistic revision on slot mutation;
- lock requires expected revision;
- two agents cannot lock different candidates into one slot silently;
- conflicting lock -> structured state conflict.

## Deletion

Logical reject/retention belongs here; physical purge policy remains separately governed (TASK-017 per roadmap). No cascade filesystem delete from dependency graph.

## Shell integration target

- Project/Scene asset panel;
- current locked asset and candidate history;
- `STALE` visible with upstream cause;
- compare/audit delegated to TASK-038;
- no standalone final app.

## Acceptance draft

- exact reverse trace from locked Asset to Scene/Plan;
- Candidate version never overwrites previous bytes;
- repeated regeneration produces new identity;
- upstream hash change propagates STALE transitively and deterministically;
- human lock/unlock authority explicit;
- no physical delete side effect;
- schema and store crash-safe;
- existing TASK-003 ingest regression unchanged.

## Addendum — crash-safe relationship-state persistence foundation (2026-08-13)

A bounded JSON snapshot store is now designed/implemented for TASK-037 relationship state only. It uses the existing atomic fsync/replace writer, deterministic SHA-256 identity and exact compare-and-swap replacement for an existing snapshot. The store does not embed media bytes or gain physical-delete authority.

Load rejects checksum tampering, orphan Candidates, inconsistent Slot locks, duplicate IDs, dependency cycles, symlink targets and oversized files. Existing snapshots cannot be blindly overwritten: a writer must present the exact previous snapshot hash.

Cross-process file locking, database migration and cloud persistence remain later integration concerns; this slice establishes deterministic local durability without choosing a final database prematurely.
