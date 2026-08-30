# TASK-061 — Montage Learning Connector Activation and Migration

- Status: `ALLOCATED / DEPENDENCY_BLOCKED / IMPLEMENTATION_NOT_AUTHORIZED`
- Capability: `BVP-MONTAGE-CONNECTOR-ACTIVATION-001`
- Development profile: `DEV_4_FOUNDATION_CRITICAL`
- Canonical activation bit: BVP-owned production connector config `enabled`
- Repository default: permanently `enabled:false`

## Objective

Re-attest the production Windows bridge security boundary, migrate compatible
legacy bridge evidence without automatic admission or deletion, consume the
released TASK-058 public readiness v1 contract, and support one explicit
Human-bound activation/deactivation switch with crash-safe history.  TASK-058's
v2 readiness object is a package-private diagnostic, not a public schema or
cross-process receipt.

This Task does not create a second readiness composer, admit learning, generate
or modify a Preference, change TASK-055, or set the repository default to true.

## Accepted design identity

- Git commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- `accepted_design_sha256`: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Allocation base: `e78699bc14f23abce995a46a9b059f826f9c2ef1`
- Registry revision at allocation preflight: `128`
- Reservation: `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`

## Atomic Units and dependency block

1. `CA-A` — Windows bridge security attestation and migration plan/executor.
2. `CA-B` — migration/source binding followed by exact TASK-058 public v1
   readiness validation; same-process v2 diagnostics may only be revalidated as
   an implementation detail of the exact pinned TASK-058 package.
3. `CA-C` — BVP-owned config plus explicit Human one-switch activation/deactivation.

Order: TASK-058 canonical release plus TASK-060 `PP-C`, then
`CA-A -> CA-B -> CA-C`.

TASK-058 v0.23.0 is released. `TASK-061` remains `DEPENDENCY_BLOCKED` because
TASK-060 `PP-C` does not yet exist.  No dependency requires or assumes a public
readiness v2 schema; metadata allocation does not waive the remaining PP-C
dependency.

## Current authorization state

Implementation, config writes, migration, DACL repair, adapter execution,
activation, Release, Deploy, and Production effects are `NOT_AUTHORIZED` until
the full authorization lifecycle is canonically closed.

## Governing authorization

Closed Allowed Files, acceptance, stop conditions, non-overlap, and DEV-4 roles
are fixed in
`task061-owner-allocation-and-implementation-authorization-2026-08-27.md`.
