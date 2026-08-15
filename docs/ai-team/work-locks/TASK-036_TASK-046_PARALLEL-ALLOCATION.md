# TASK-036／TASK-046 Parallel Allocation

Status: `ACTIVE_ON_MAIN / OWNER_AUTHORIZED / REGISTRY_REVISION_1`

Machine-readable authority:
`docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`.

## Hosted state entering this allocation

- GitHub main audited at
  `25e2e04fb3360af77017a4a42e868fc95b15ec80`.
- PR #90 exact head `664722d0fac8cc0e79f7c424c6911f4651ceb303`
  passed `9 / 9`, merged to that exact main, and post-merge CI/Security passed.
- P-VS-0 is `HOSTED_CLOSED`.
- TASK-036 P-UX-1C is the active Consumer Task.
- TASK-046 P-VS-1A is a parallel reserved Backend unit; P-VS-1B remains gated
  by a successor canonical mock and separate Authorization.

## `BVP-LOCK-TASK036-PUX1C` — 開発担当

TASK-036 P-UX-1C exclusively owns the existing Timeline, Track, Shell and
packaged Native-closure files enumerated in the Registry. Its uncommitted WIP,
Evidence and branch remain in the original checkout and may not be copied,
stash-relocated, reset, cleaned or prematurely committed by another unit.

Implementation remains paused until the Registry-hosting PR is on main and
every entry in the Owner-provided `WIP_FILE_SHA256.txt` matches. The current
Native Evidence predates the latest Track changes and cannot prove closure.

## `BVP-LOCK-TASK046-PVS1A` — 開発担当2

TASK-046 P-VS-1A exclusively owns the new body-free VoiceProfile Backend files
enumerated in the Registry. It may start only from fresh main after its own
Current Main Audit, DEV-4 reconfirmation, exact Allowed Files, Builder Design,
two Critic correction cycles and Judge decision are recorded.

P-VS-1A is limited to immutable `VoiceProfileRevision` metadata,
Consent/License references, public/private projection, atomic/CAS persistence,
tamper/restart and a non-executing capability description/preflight. The
existing `owner_narration.py::VoiceProfile` remains the canonical narration
identity and is read-only; P-VS-1A may not create a second `VoiceProfile` class
or narration planner. It must not store audio/voice bodies or download, load or
invoke a Model. Its main merge waits for P-UX-1C hosted closure, fresh-main
rebase, overlap `0`, full regression and hosted checks.

## P-VS-1B remains separate

P-VS-1B owns the future Voice destination, Shell and TASK-014 integration. It
is not part of the P-VS-1A Lock and cannot start before a reviewed successor
canonical mock and separate Authorization. P-VS-1A Backend existence never
authorizes P-VS-1B or native Voice execution.

## Shared Integration Lock

Global current-state, roadmap, architecture, package export, version, release
and `.github` files cannot be changed from either implementation Lock. A
dedicated Integration Lock and docs-only or closure PR is required first.

An Agent must stop before touching any file outside its hosted Allowed Files.
File/glob overlap, an unknown local change or a stale base is a fail-closed
condition; it is not permission to resolve or overwrite another Agent's work.

## Denied operations

Neither Lock authorizes Model download/load/inference, recording, training,
voice/audio body persistence, Credential, paid/Cloud Provider, ambiguous
external application mutation, Human ACCEPT/LOCK, version, Tag, Release or
Deploy.

## Merge order

1. Host this Lock/Roadmap coordination unit.
2. Verify P-UX-1C WIP hashes and complete P-UX-1C Native/full closure.
3. Rebase and merge P-VS-1A only after P-UX-1C hosted closure.
4. Host the successor canonical Voice mock.
5. Authorize P-VS-1B separately.

P-VS-1A branch development may occur in parallel between steps 1 and 2; this
does not change the main-merge order.
