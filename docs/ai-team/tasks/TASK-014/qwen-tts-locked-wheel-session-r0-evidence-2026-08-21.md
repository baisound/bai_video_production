# TASK-014 — Qwen-TTS Locked Wheel Session R0 Evidence

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / COMMIT_READY / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Why the design changed

The prior clean-leaf materialization and ACL design was rejected before any
actual `E:` execution. Its path-based sequence could not prove that every read
and later use remained bound to the same source object, and an owner-changeable
ACL was not adversarial immutability. Those draft files were removed. This
redesign performs no materialization or other filesystem mutation.

## Capability boundary

The public factory accepts only an RFC3339 UTC evaluation time. The production
wheel path is a private exact constant; a caller cannot provide or authorize an
alternate path.

The private Windows adapter:

1. requires `E:\` to report a fixed local drive;
2. opens `E:\`, `BAI_AI`, `downloads` and `TASK-014` in top-down order with
   `OPEN_REPARSE_POINT | BACKUP_SEMANTICS`, read/attribute access, read/write
   sharing and no delete sharing;
3. validates non-reparse type, final canonical path and stable file ID from
   each held handle;
4. opens the exact wheel with `GENERIC_READ`, read sharing only, no write/delete
   sharing and `OPEN_REPARSE_POINT`;
5. reads exactly 113,529 bytes from that same wheel handle and validates the
   exact SHA-256, 24 ZIP/RECORD rows and 23 authenticated payload bodies;
6. rechecks the wheel and all ancestor identities while every handle remains
   held;
7. closes wheel then ancestor handles in reverse order on failure or context
   exit.

Every handle is explicitly non-inheritable. The context-managed session is a
one-shot, non-serializable capability and rejects reads after exit. A second
verified read is permitted only through the same live wheel handle.

Non-inheritance is applied and then read back with `GetHandleInformation`. If
that safety step and its immediate close both fail, an internal-only exception
returns the opaque handle to the session cleanup list. Reverse cleanup removes
only handles whose close was confirmed, retains failed handles for bounded
retry, and never serializes their values. A live revalidation failure performs
reverse close immediately rather than waiting for context exit.

## Persistent receipt boundary

The receipt is diagnostic Evidence, never the live capability. It persists no
absolute path, canonical path, volume serial, file ID, handle, SID or security
descriptor. It always fixes these claims to false:

- persistent receipt is capability;
- runtime reuse authorized;
- post-return state guaranteed;
- consumer execution authorized;
- dependency installation, target Python execution and package import;
- model load, Owner audio read and inference;
- network, subprocess, archive extraction and filesystem modification.

The receipt records actual phase effects even on failure: how many directory
handles were opened, whether the wheel handle opened, whether its exact bytes
and payload were verified, whether handle release is confirmed, and the count
of opaque handles not confirmed released. An active successful session reports
five unreleased handles and `handle_release_confirmed: false`; normal context
exit refreshes the same diagnostic receipt to zero and `true`. A persistent
close failure remains `BLOCKED / HANDLE_CLOSE_FAILED` with a nonzero count.

## Builder verification

- focused synthetic parser/session tests: `22 PASS`
- focused session plus prior observer regression: `59 PASS`
- exact top-down open order: `PASS`
- fixed-local/reparse/final-path/file-ID/swap failures: `PASS`
- pre-existing writer-compatible open denial simulation: `PASS`
- same-handle second verified read: `PASS`
- reverse closure and closure-failure invalidation: `PASS`
- failed-close retention, bounded retry and unreleased-count reporting: `PASS`
- non-inheritance native readback and readback-fault closure: `PASS`
- non-serialization and use-after-exit rejection: `PASS`
- schema/resource mirror, Draft 2020-12 and receipt tamper/privacy checks:
  `PASS`
- runtime/schema parity for partial phase facts and all-or-none source
  verification flags: `PASS`
- static no write/delete/rename/install/import/model/audio/network surface:
  `PASS`
- pre-actual independent Tester and Critic: `ACCEPT / C0 H0 M0`

## Actual fixed-wheel diagnostic

After the independent DEV-4 reviews reached zero unresolved Critical, High and
Medium findings, one bounded Windows diagnostic session was executed against
the fixed production wheel coordinate. The development Python used only this
module and did not import the target qwen package.

- evaluated at: `2026-08-20T19:52:17.044652Z`
- in-session decision: `LOCKED_SOURCE_VERIFIED_DIAGNOSTIC`
- in-session reasons: none
- authenticated payload files: `23`
- live held handles: `5`
- in-session release confirmed: `false`
- post-context decision: `LOCKED_SOURCE_VERIFIED_DIAGNOSTIC`
- post-context reasons: none
- post-context unreleased handles: `0`
- post-context release confirmed: `true`
- final receipt SHA-256:
  `sha256:4b7ecd8bd505084c5ddc47a365253af2cff2b6f348a2d099c87174943da1641b`

The final receipt records `false` for persistent-capability authority, runtime
reuse, consumer execution, target Python execution, target-package import,
model load, Owner-audio read, inference, network access, subprocess start and
filesystem modification. No automatic retry was required or performed.

This result is diagnostic supporting Evidence only. It does not satisfy the
full runtime receipt, offline load-only, alignment, private staging, dispatch,
Owner-voice inference, publication, REAPER or iZotope gates.

## Post-actual review and fresh-main integration

- post-actual independent Acceptance: `PASS / C0 H0 M0`
- post-actual independent Judge: `ACCEPT / C0 H0 M0`
- actual `E:` reread during review: `NO`
- fresh main: `9951f428b51e32b7b86d91959fd18cb008fc5886`
- rebased dependency commit:
  `16b4479090f27553cc913b8e5cf5edf47e8856b4`
- fresh-main locked-session plus prior-observer regression: `59 PASS`
- Python no-bytecode compile: `PASS`
- Draft 2020-12 schema and byte-identical packaged mirror: `PASS`
- AU2B5 uncommitted scope: exact six authorized files
- dependency commit scope: exact five accepted AU2B4 files
- `git diff --check`: `PASS`

The Atomic Unit is commit-ready. This acceptance does not authorize runtime
reuse, model load, Owner voice use, inference, REAPER or iZotope execution.
