# TASK-060 — Montage Preference Projection and Production Source

- Status: `PP_A_IMPLEMENTATION_AUTHORIZATION_CANDIDATE / IMPLEMENTATION_NOT_STARTED`
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

The allocation package is canonical and the Owner has approved a bounded PP-A
implementation-authorization candidate. This metadata branch does not mutate
implementation files and does not itself prove that the authorization is
canonical.

PP-A implementation becomes eligible only after the exact metadata candidate
passes independent DEV-4 review with unresolved Critical/High `0/0`, Hosted
checks, an exact Owner Ready/merge decision, canonical-main merge/read-back,
and post-main CI/Security. At that point only the six paths frozen in
`pp-a-implementation-authorization-2026-08-28.md` may change. PP-B and PP-C
remain `IMPLEMENTATION_NOT_AUTHORIZED`.

Current candidate effect is source `0`, schema `0`, test `0`, Registry `0`,
task-index `0`, CHANGELOG `0`, runtime/native/paid/external `0`, and
Release/Deploy/Production `0`.

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
