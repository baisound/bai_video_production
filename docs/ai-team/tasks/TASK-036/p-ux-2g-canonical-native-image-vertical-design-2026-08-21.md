# TASK-036 P-UX-2G canonical native image vertical design

Date: 2026-08-21

Status: `DEV-3 IMPLEMENTATION AUTHORIZED / NATIVE EXECUTION HUMAN GATE PENDING`

## Goal

Close one bounded Product vertical without recreating the rejected synthetic
Queue runner:

`current TASK-027 Human-GO Queue entry -> trusted Shell -> TASK-013 local IMAGE execution -> separate Human confirmation -> TASK-003 Asset + TASK-037 READY_FOR_AUDIT Candidate`.

The unit proves neither Candidate ACCEPT/LOCK nor NLE, Final Review, Export,
publication, deployment, release, or P-UX-2E completion.

## Canonical boundary

The CLI is a thin operator surface. It owns no Product truth and writes no
runner state or Evidence file. It may use only:

- a stable no-follow read of the launch-config bytes, parsed through
  `Task036LaunchConfiguration.from_dict` and bound by exact SHA-256;
- `ProductProjectManifestStore.load` for the expected Project identity;
- `build_trusted_launch` and the resulting live, leased public Shell bridge;
- canonical Product snapshots and mutations already exposed by that bridge.

It must not call a generation Queue application, execution port, adoption
application, database store, or private bridge member directly. It must not
create a Project, manifest, Product Job, Human GO, Queue entry, Prompt, or
connection profile. A missing or uninitialized Product Project fails closed
before trusted-launch composition. Existing Product database admission is
read-only and requires the complete current schema/migration/index contract
and configured Product Job from an isolated stable database-family copy. Exact
table/column/PK/FK/default/index semantics, integrity and foreign-key checks are
required. The validated database identity is pinned for later connections. It
must not bootstrap tables, directories, rows, or SQLite sidecars for an invalid
Project. Admission is bounded to a 512 MiB main database, a 256 MiB WAL, and a
30-second SQLite validation budget. On Linux/WSL, each later SQLite connection
must prove that its actual opened inode is the admitted pinned inode, including
against a pathname swap-and-restore race. The trusted launch releases the pin
when its runtime lease closes.

The removed synthetic runner and its bytecode are historical residue and must
not be restored or interpreted as source.

## Operations

The CLI has four exclusive operations and accepts one reviewed launch config,
its expected byte SHA-256, expected Project ID, and expected manifest SHA-256.
Every option is exact-once; abbreviations and last-value-wins duplicate options
are rejected.

### STATUS_EXECUTION

Read the canonical Queue and TASK-013 execution snapshots for one Queue entry.
If there is no execution history, validate the current Queue entry and run the
entry-scoped local runtime preflight. Preflight must report
`dispatch_performed=false`. Existing `DISPATCHING` is projected as
`RECOVERY_REQUIRED`; the CLI never retries it. Existing `COMPLETED` or `FAILED`
is rediscovered without Provider execution.

### EXECUTE

Require no prior execution history for the exact Queue entry. Read the current
Queue and execution snapshot, run entry-scoped preflight, then call Shell
prepare with both exact snapshot hashes. Display a body-free confirmation body
covering:

- launch-config SHA-256, Project ID, and manifest SHA-256;
- Queue entry, Queue snapshot, and execution snapshot;
- scene, slot, Prompt ID/version/SHA-256;
- route, Provider, model, capability, cost class, media kind;
- workflow SHA-256 and runtime policy.

The canonical JSON hash of that body defines the only accepted phrase:
`EXECUTE sha256:<64 lowercase hex>`. The Human must type it in the same process
after prepare. Any mismatch consumes/cancels the pending confirmation and
performs no dispatch. Immediately before apply, the manifest is re-read and
must still match. Shell apply also rechecks it while holding the canonical
Project manifest lock, then re-derives Queue/Prompt/Profile/runtime under the
execution CAS lock before writing `DISPATCHING` and before calling ComfyUI.
This locked recheck, not the CLI read, is the authority linearization point.
It also rejects a pending Project-save recovery transaction or any manifest
child whose bytes differ from the current binding.

On success the CLI prints only the durable execution ID, Queue entry ID,
logical `project-output://` reference, output SHA-256, media kind, state, and
snapshot SHA-256. It does not adopt the output.

### STATUS_ADOPTION

In a fresh trusted launch, read the canonical completed execution and require
the operator-supplied expected output SHA-256 to match. Read Queue, production,
Prompt, and adoption snapshots and project the exact adoption eligibility.
This operation must make zero ComfyUI calls.

### ADOPT

In a separate process from EXECUTE, require the exact completed execution ID
and output SHA-256. Read all canonical snapshots and call Shell adoption
prepare. Display a second confirmation body covering Project/manifest,
execution/Queue/output/media/slot/Candidate, and all five CAS snapshot hashes.
The only accepted phrase is `ADOPT sha256:<64 lowercase hex>` computed from
that body. Immediately before apply, re-read the manifest and completed
execution identity. Shell adoption apply rechecks the manifest under the
canonical Project lock, then performs the canonical CAS checks and stable
output verification. Pending Project-save recovery and manifest-child drift
are rejected before the first adoption mutation. Success requires:

- adoption state `READY_FOR_AUDIT`;
- exact TASK-003 Asset SHA-256 and IMAGE media identity;
- exact TASK-037 Candidate in `READY_FOR_AUDIT`;
- no Candidate ACCEPT or LOCK;
- no publication, NLE, Export, paid, cloud, or Provider replay authority.

ADOPT makes zero ComfyUI calls and cannot call TASK-013 execute.

## Crash, restart, and concurrency

- Before execution apply, process loss discards only an in-memory confirmation.
- After durable `DISPATCHING`, EXECUTE must not be called again. The operator
  uses the existing Product Shell Human recovery action, which reconciles the
  exact port journal/history without queue replay.
- After durable `COMPLETED`, STATUS_EXECUTION redisplays the output identity if
  stdout was lost. ADOPT may then be started separately.
- If adoption is active after a crash, the existing Product Shell adoption
  recovery is the only continuation. The CLI neither restarts nor repairs it.
- Concurrent EXECUTE and ADOPT processes rely on the existing runtime lease and
  Product CAS. At most one process obtains mutation authority.
- Every path closes the trusted launch in `finally`; a retained old bridge is
  unusable after close.

## Privacy and side-effect policy

Command output is closed-schema JSON containing only logical Product IDs,
SHA-256 values, enum states, and booleans. ProductError messages/details,
Prompt text, config path, host paths, secrets, workflow bodies, Provider
payloads, confirmation tokens, and traceback text are never printed.

`tmp/**` is user-owned and outside this Atomic Unit. It is not read, changed,
staged, or used as Evidence.

Only the reviewed local IMAGE route is eligible: fixed loopback ComfyUI,
`LOCAL_FREE_AI`, no credential, no endpoint override, no settings, no fallback,
no model/runtime download, and no cloud or paid call.

## Verification and native gate

Automated verification must cover exact argument schemas, wrong Project or
manifest, missing initialization, stale/foreign Queue entries, preflight with
zero dispatch, confirmation mismatch, state drift, existing DISPATCHING and
COMPLETED rediscovery, uncertain execution with no replay, separate adoption,
ADOPT Provider-call zero, output/candidate exact identity, trusted-launch close,
and recursive stdout privacy.

The integration gate uses a canonical initialized Product fixture and the real
CLI, trusted-launch composition, public Shell bridge, production local IMAGE
port, TASK-013 store, TASK-003 Asset ingest, and TASK-037 Candidate adoption.
Only the Comfy transport is fake. It must show one Queue dispatch, a durable
structurally verified PNG/output digest, a fresh trusted launch for ADOPT, zero
additional Comfy dispatch, and an exact `READY_FOR_AUDIT` Candidate with no
ACCEPT, LOCK, or publication authority.

Fake clients validate logic only. After focused/integration regression and
independent Critic/Judge reach C/H/M=0, a real Windows native run remains a
separate Human Gate. The order is STATUS_EXECUTION, review, one EXECUTE phrase,
read back durable output SHA-256, process exit, STATUS_ADOPTION, review, and one
ADOPT phrase. Never retry an uncertain dispatch or use an alternate Project.
