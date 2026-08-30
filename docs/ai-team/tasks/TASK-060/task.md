# TASK-060 — Montage Preference Projection and Production Source

- Status: `PP_B_IMPLEMENTATION_CANDIDATE / INDEPENDENT_DEV4_PENDING`
- Capability: `BVP-MONTAGE-PREFERENCE-PROJECTION-001`
- Development profile: `DEV_4_FOUNDATION_CRITICAL`
- Owner boundary: TASK-029 source semantics and TASK-019 evaluation, promotion, and rollback semantics
- Transport consumer: TASK-058 Profile transport after canonical release

## Objective

Create a deterministic, SKILL-compatible, advisory-only Preference projection
from already-authoritative TASK-029 and TASK-019 records, require an explicit
Human confirmation before promotion, persist an append-only promotion/rollback
history, and expose one exact promoted envelope through a read-only production
source port.

This Task does not import generic observations, transport the envelope, approve
a montage, derive meaning from TASK-055 timing preferences, mutate a Timeline,
write Resolve state, or apply a Profile automatically.

## Accepted design identity

- Git commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- `accepted_design_sha256`: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Allocation base: `e78699bc14f23abce995a46a9b059f826f9c2ef1`
- Registry revision at allocation preflight: `128`
- Reservation: `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`
- Collision and exact-path overlap at preflight: `0`

## Atomic Units

1. `PP-A` — freeze the typed projection policy and implement the pure candidate compiler.
2. `PP-B` — implement explicit Human confirmation and the append-only promotion/rollback store.
3. `PP-C` — implement the read-only production source port returning one exact promoted envelope.

Dependency order is `PP-A -> PP-B -> PP-C`. Each Unit requires a separately
frozen exact file subset and completion Evidence before the next Unit starts.

## Current authorization state

The PP-A authorization metadata is canonical at main
`dd0084a1d3ab03299f9611e7d5fe93860d7314b2`.  The Owner authorized the exact
six-path PP-A implementation Unit, and a local implementation candidate now
exists for independent DEV-4 review.  This status does not claim Hosted or
canonical completion.

The fresh-main PP-A candidate remains the exact stacked input to a bounded PP-B
implementation candidate. The Owner continuity/takeover instruction authorized
the unfinished dependency to proceed instead of remaining idle. PP-B adds only
explicit Human confirmation plus the encrypted append-only promotion/rollback
store and its closed schema/tests. PP-C remains unimplemented. Registry,
task-index, CHANGELOG, runtime/native/paid/external, Timeline/Resolve, and
Release/Deploy/Production effects remain `0`.

The stale PR #430 implementation commit was replayed without its historical
merge commit onto canonical remote main
`160c9569673fbf65a28b0f95eeb44c5b0111584f`.  The fresh-main candidate retains
the exact six-path scope and remains a Draft/noncanonical result; it does not
create canonical PP-B or PP-C completion. PP-B exact Builder validation is
Windows focused `24 passed`, WSL2 focused `23 passed / 1 Windows-only skipped`,
Windows TASK-019/029 direct regression `75 passed`, and WSL2 direct regression
`72 passed / 3 Windows-only skipped`. Its five implementation/schema/test paths
plus this existing task checkpoint are the exact candidate scope.

## Responsibility non-overlap

- TASK-029 remains the owner of Human learning decisions and Owner Profile source semantics.
- TASK-019 remains the owner of evaluation, promotion decision, and rollback semantics.
- TASK-058 remains the owner of transport, receipt, bridge, and readiness behavior.
- TASK-055 timing profiles are not inputs and are not modified.
- Existing BVP Timeline and Human Gates remain canonical; no second Timeline is created.

## Governing authorization

The closed Allowed Files, tests, stop conditions, expiry conditions, role
separation, and prohibited effects are fixed in
`task060-owner-allocation-and-implementation-authorization-2026-08-27.md`.

The bounded PP-A activation conditions, exact six-path implementation scope,
dependency read set, required tests, stop conditions, and denied effects are
fixed in `pp-a-implementation-authorization-2026-08-28.md`. The original Owner
allocation record remains immutable.
