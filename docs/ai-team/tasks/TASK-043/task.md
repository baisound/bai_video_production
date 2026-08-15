# TASK-043 — Unified Product Project / Migration / Recovery Foundation

## Identity

- Product: `BAI VIDEO PRODUCTION`
- Priority: `OWNER_MAXIMUM / MAJOR_REFACTOR_FOUNDATION`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Status: `HOSTED_CLOSED / P-FND-4_DURABLE_PRODUCT_JOB_HOSTED_CLOSED`
- Authority: Owner Directive `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
- Current main baseline: `19febe3e00de92b18948e93740a0e3080b63d1b1`

## Problem

The Product already has strong domain-specific stores, hashes, CAS checks and
recovery paths, but it has no single versioned Product Project envelope that can
prove which child snapshots form one reopenable project. Most JSON stores reject
any version other than `1.0.0`; background Shell jobs are memory-only; generic
Undo/Redo, Autosave and user-visible Backup are absent. Building the full V6
Timeline and Export Queue on this boundary would multiply migration and recovery
risk.

## Goal

Add a compatibility-preserving Product Project foundation that coordinates the
existing canonical domain stores without replacing their ownership:

1. versioned Project Manifest and child-store bindings;
2. explicit compatibility and migration planning;
3. atomic save journal and deterministic crash recovery;
4. bounded command history for Undo/Redo;
5. Autosave and rotating Backup policy;
6. durable background-job and Export Queue contracts;
7. exact Evidence and rollback boundaries.

## Slices

1. `P-FND-1` Project Manifest, compatibility reader and read-only migration plan.
2. `P-FND-2` save coordinator, journal, recovery and cross-store validation.
3. `P-FND-3` command history, Autosave and Backup.
4. `P-FND-4` durable job/Export Queue foundation and Shell projection.

## Reused ownership

- SQLite Asset/Production Job truth remains TASK-001/003.
- Blueprint v2 truth remains TASK-042.
- Candidate/LOCK/STALE remains TASK-037.
- Audit remains TASK-038; Continuity remains TASK-039; Prompt/Attempt remains TASK-040.
- Audio placement review remains TASK-041.
- Shell command authority remains TASK-036.
- Resolve mutation/render remains TASK-010/011 and is not authorized by this Task.
- OBS capture ownership remains TASK-047. TASK-043 supplies only durable
  session/job/checkpoint/recovery primitives and never converts a recovered
  segment into Dataset adoption or training authority.

## Permanent boundaries

- The Project Manifest references child truth by relative path, schema version
  and checksum; it does not duplicate domain payloads.
- Migration preview is read-only. Applying an incompatible or destructive
  migration remains a Human Gate.
- Undo is a new compensating command, never historical Evidence deletion.
- Autosave never captures credentials, confirmation tokens, media bytes or
  arbitrary host paths.
- Recovery never replays external, Provider, paid, Resolve/Cubase or unknown-state
  operations automatically.
- P-OBS-1 capture recovery must persist session/segment identity, incomplete or
  UNKNOWN state, exact sample/drop counts and explicit reconciliation. Restart
  never resumes recording, adopts a Dataset segment or starts training without
  the applicable explicit authority.
- Production Deploy, paid Provider execution, new credential input and destructive
  external operations remain unauthorized.

## Exit gate

- Two Critic rounds and Final Judge have unresolved Critical/High `0 / 0`.
- Migration and rollback fixtures pass for supported source versions.
- Interrupted-save and checksum-conflict recovery tests pass.
- Undo/Redo, Autosave and Backup retention tests pass.
- Full regression and static checks pass.
- Current State, Roadmap and Task Registry are synchronized.

