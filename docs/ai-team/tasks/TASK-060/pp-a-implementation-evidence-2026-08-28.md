# TASK-060 PP-A Implementation Evidence

## Identity and scope

- Atomic Unit: `PP-A`
- Capability: `BVP-MONTAGE-PREFERENCE-PROJECTION-001`
- Original implementation base: `dd0084a1d3ab03299f9611e7d5fe93860d7314b2`
- Fresh reconciliation base: `160c9569673fbf65a28b0f95eeb44c5b0111584f`
- Replayed feature commit: `f55b46b2b29c6d23b67dcecf5bbc774b6d0e83cb`
- Accepted design: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- Accepted design SHA-256: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Branch: `codex/task-060-ppa-fresh-main-reconciliation`
- Builder result: `LOCAL_CANDIDATE / INDEPENDENT_DEV4_PENDING`

The diff is limited to the exact six paths authorized by
`pp-a-implementation-authorization-2026-08-28.md`.  PP-B, PP-C, `__init__.py`,
TASK-055, TASK-058, Registry, task-index, current-state, CHANGELOG, runtime,
native, Timeline, Resolve, Release, Deploy, and Production were not changed.

## Implemented contract

- Closed, immutable and self-hashed projection policy with exact v1 schema and
  byte-identical package mirror.
- Exact typed TASK-019/TASK-029 source bundle with pre-serialization rejection
  of custom containers, hooks, and scalar subclasses.
- Independent in-memory reconstruction of Owner Profile Registry, Owner Profile,
  proposal, decision binding, and Owner Decision history coordinates.
- Multi-revision latest-change selection with one distinct current `ADOPTED`
  decision set per changed feature and replay rejection.
- Accepted integer-only sample, improvement, delta, confidence, effective
  strength, and signed bias formulas.
- Stable Owner-global profile and preference identities, deterministic payload
  hash, immutable candidate self-hash, and advisory-only SKILL v1 envelope.
- Closed body-free failure states for missing/stale/integrity/scope/mapping/
  confirmation/strength/no-active-preference outcomes.
- Automatic learning, promotion, canonical Timeline, Timeline mutation, Resolve
  write, and external-effect authority remain false.

## Builder validation

The following results are Builder Evidence only. They do not replace independent
Critic, Tester, or Judge Evidence.

```text
focused PP-A:
  11 passed

TASK-019/TASK-029 direct regression:
  72 passed, 3 intentionally skipped (Windows DPAPI runtime only)

compileall:
  PASS

schema/package mirror:
  PASS (byte-identical)

full BVP regression:
  NOT_CONFIRMED at collection because the available WSL environment lacks
  cryptography.hazmat.primitives.kdf.argon2 and referencing; 28 unrelated
  collection errors, with no test body executed and no dependency installed
```

Exact-scope, diff-check, and final Git identity results are appended to the
handoff after execution against the exact committed candidate. Full regression
must be rerun in the canonical Hosted environment and is not claimed as PASS.

## Fresh-main reconciliation read-back

The original feature commit was cherry-picked onto the fresh remote-main base
without the obsolete merge commit from PR #430.  The replay was conflict-free
and preserved the exact six authorized paths.  On the reconciled tree, focused
PP-A remains `11 passed`; direct TASK-019/TASK-029 regression remains
`72 passed, 3 skipped`; compileall and schema mirror identity pass.  No
CHANGELOG/shared-registry effect was taken, so the hosted release-metadata gate
is expected to remain separate from this immutable product diff.

## Authority denial and continuation

This candidate performs no persistence, Human confirmation, promotion,
rollback, transport, loading, publishing, automatic application, or Product
runtime mutation.  It creates no implementation authority for PP-B, PP-C, or
TASK-058.  Push and PR creation remain blocked until independent DEV-4 reports
unresolved Critical/High `0/0` for the exact immutable candidate.
