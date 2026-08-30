# TASK-060 through TASK-062 Authorization Metadata Integration Lock Hosting

Date: 2026-08-27
Unit: `TASK-060/TASK-061/TASK-062-AUTHORIZATION-METADATA-LOCK-HOSTING`
Authority: `OWNER_EXPLICIT_DESIGN_GO_AND_ALLOCATION_RESERVATION_20260827`
Checkpoint state: `LOCAL_CHECKPOINT_NOT_HOSTED`

## Canonical input identity

- Repository: `baisound/bai_video_production`
- Fresh remote main:
  `7591beb9a3f29212a938861e9ef8930e94c86ef7`
- Registry before this proposal: revision `126`, state `ACTIVE`, active
  nonclosed locks `0`
- Registry proposed by this local checkpoint: revision `127`, one exact
  `PENDING_HOST_PR` reservation-only record
- Exact open-PR overlap across the six target-owned Task paths and the one
  shared `task-index.md` effect: `0` across `16` open PRs
- `TASK-060`, `TASK-061` and `TASK-062` matches in the fresh main tree,
  task index, Registry and roadmap: `0`
- Matching remote hosting/target branch heads: `0`
- Matching open or closed GitHub pull requests for either branch: `0`

## Accepted design

- Design Git commit:
  `9f6c26ac5147b9a881ca037ae02ef020818db50a`
- Accepted design SHA-256:
  `sha256:c5c17aa92ab5f68daef315e4fc62a1fb7a46e3f80c2c8093adec1f073594db80`
- Final Design Judge: `GO / C/H/M/L 0/0/0/0`
- The accepted checksum covers the exact Git tree bytes of the six frozen
  design, work-order and proposal documents recorded by the Owner decision.
- Builder-supplied tests remain separate from the independent Critic's local
  execution status. BVP, Resolve and native runtime were not run by the
  design-only gate.

## Reserved Task identities

| Task | Capability | Allocation state | Implementation state |
|---|---|---|---|
| `TASK-060` | `BVP-MONTAGE-PREFERENCE-PROJECTION-001` | `OWNER_RESERVED_PENDING_CANONICAL_RECORD` | `NOT_AUTHORIZED` |
| `TASK-061` | `BVP-MONTAGE-CONNECTOR-ACTIVATION-001` | `OWNER_RESERVED_PENDING_CANONICAL_RECORD` | `NOT_AUTHORIZED` |
| `TASK-062` | `BVP-MONTAGE-DESKTOP-UX-001` | `OWNER_RESERVED_PENDING_CANONICAL_RECORD` | `NOT_AUTHORIZED` |

This Lock-host record reserves only the three Task identities, two branch
names and future exact metadata scope. Even after merged-main read-back it
does not authorize target Ready, target merge, the shared task-index effect or
implementation. A separate canonical activation amendment must bind the
target pull request, exact head, all six path/blob SHA-256 coordinates, hosted
checks, independent DEV-4 result and exact Owner Ready/merge authority before
any task-index effect is allowed.

## Immutable target-owned paths

These six new paths become immutable inputs to the one shared integration
effect after the target branch records their exact blobs:

1. `docs/ai-team/tasks/TASK-060/task.md`
2. `docs/ai-team/tasks/TASK-060/task060-owner-allocation-and-implementation-authorization-2026-08-27.md`
3. `docs/ai-team/tasks/TASK-061/task.md`
4. `docs/ai-team/tasks/TASK-061/task061-owner-allocation-and-implementation-authorization-2026-08-27.md`
5. `docs/ai-team/tasks/TASK-062/task.md`
6. `docs/ai-team/tasks/TASK-062/task062-owner-allocation-and-implementation-authorization-2026-08-27.md`

The only shared target effect is:

- `docs/ai-team/task-index.md`

`docs/ai-team/current-state.md`, the roadmap, `CHANGELOG.md`, package/version
metadata and every source, schema and test path are outside this Lock.

## Dependency and responsibility gates

- `TASK-060` owns Preference projection, Human confirmation,
  promotion/rollback records and the sealed read-only production source port.
  It does not own TASK-058 transport, TASK-055 semantics, Timeline or Resolve.
- `TASK-061` is blocked until TASK-058 is released and TASK-060 PP-C is
  complete. It owns security re-attestation, migration, exact readiness
  consumption and Human activation/deactivation only.
- `TASK-062` is blocked until the accepted runtime wheel and TASK-055 are
  released dependencies. It owns the Consumer job/review/desktop integration
  without changing TASK-055 algorithms or TASK-058 stores and receipts.
- Shared Registry, task index, CHANGELOG and other global metadata remain
  serialized even when later private implementation paths are disjoint.
- Existing TASK-058 A/B+C work is not paused or modified by this Lock.

## Lock record

- Lock ID:
  `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`
- Hosting branch:
  `codex/task-060-task062-authorization-metadata-lock-hosting`
- Target branch:
  `codex/task-060-task062-authorization-metadata`
- Status: `PENDING_HOST_PR`
- Activation after the Lock-host PR is merged and read back from fresh main is
  `RESERVATION_ONLY`. Revision `127` alone grants no task-index effect, target
  Ready state or merge authority.
- Target merge authority: `NOT_GRANTED_PENDING_SEPARATE_EXACT_OWNER_GATE`
- Target merge authority ID: `null`
- Integration effect authority: no effect until a separate canonical target
  activation amendment is hosted and read back from main.
- Automatic retry: `false`
- Automatic rollback or revert: `false`

## Required activation amendment binding

The later activation amendment must bind all of the following before the
shared task-index effect can begin:

1. exact target pull-request number and target branch;
2. exact target head Git SHA-1;
3. exact path, Git blob SHA-1 and file SHA-256 for all six Task records;
4. terminal-success hosted checks for that exact head;
5. independent DEV-4 Critic, Tester and Judge with unresolved Critical/High
   `0/0`;
6. exact Owner Ready and target merge authority; and
7. activation-amendment hosted main identity and Registry read-back.

Missing, null, stale, relabelled or mismatched coordinates keep the target
effect prohibited. The reservation record cannot be interpreted as that
amendment.

## Expiry and stop conditions

The proposal expires or stops on any of the following:

- main or Registry drift before the effect;
- any Task identity collision;
- any hosting or target branch-name collision;
- a new task-index, Registry or exact target-path overlap;
- accepted design commit or SHA-256 mismatch;
- target metadata blob drift;
- Allowed Files expansion;
- unresolved independent Critical or High finding;
- Owner authority revocation;
- target PR closure or merge before the expected transition;
- any forbidden effect or workflow-policy violation; or
- completed allocation integration and append-only Lock release.

## Explicit denials

This Lock grants no authority for:

- TASK-060, TASK-061 or TASK-062 source/schema/test/runtime implementation;
- mutation of TASK-058, TASK-055, TASK-029, TASK-019 or another Task;
- `current-state.md`, roadmap, CHANGELOG, PROJECT, package/version or
  `.github/**` changes;
- media, Profile body, credential, private data, paid/provider or network
  runtime effects;
- Timeline or Resolve mutation;
- Release, Deploy or Production Activation; or
- workflow weakening, force push, automatic retry, rollback or revert.

## Required continuation order

1. Validate and commit this exact two-path local reservation checkpoint.
2. Push and host it only under a separate explicit instruction.
3. Read back fresh main revision `127` as reservation-only with hosted CI and
   Security success and exact overlap `0`.
4. Under a separate exact Owner instruction, create a target draft from that
   fresh main and generate only the six Task records; do not change the task
   index yet.
5. Freeze the target pull request, exact head and all six path/blob SHA-256
   coordinates.
6. Obtain independent DEV-4 Critic, Tester and Judge with unresolved
   Critical/High `0/0` for that exact target.
7. Obtain a separate exact Owner Ready and target merge Gate.
8. Host and read back a canonical activation amendment containing every
   required coordinate and Gate above.
9. Only then perform the one shared task-index effect, merge the target under
   its exact authority and append the Lock closure.
10. Start implementation only in later per-Task Atomic Units after canonical
    allocation closure and each dependency Gate.

## Local validation record

This document records a local reservation proposal only. Even after it is
hosted and read back from canonical main, Registry revision `127` reserves
identity and future scope only. It grants no target Ready, merge, task-index
effect or implementation authority without the separate canonical activation
amendment defined above.
