# TASK-062 — Montage Consumer Runtime Desktop UX

- Status: `ALLOCATED / DEPENDENCY_BLOCKED / IMPLEMENTATION_NOT_AUTHORIZED`
- Capability: `BVP-MONTAGE-DESKTOP-UX-001`
- Roadmap: separate from TASK-058, TASK-029, and TASK-054
- Development profile: `DEV_4_FOUNDATION_CRITICAL`
- Runtime dependency: released, digest-pinned `bai-davinci-montage-skills` wheel
- Product dependency: current exact TASK-055 R0 schemas and admission

## Objective

Make the existing local `ConsumerRuntimeService` usable through the unified BVP
desktop product by adding Product-owned request compilation, durable background
job orchestration, verified TASK-055 proposal admission, and Human review UX.

This Task does not copy montage algorithms into BVP, approve a montage, create a
second Timeline, or apply changes to Resolve.

## Accepted design identity

- Git commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- `accepted_design_sha256`: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Allocation base: `e78699bc14f23abce995a46a9b059f826f9c2ef1`
- Registry revision at allocation preflight: `128`
- Reservation: `BVP-INTEGRATION-LOCK-TASK060-TASK062-AUTHORIZATION-METADATA-20260827`

## Atomic Units and dependency block

1. `UX-A` — pinned runtime package manifest and clean packaged load preflight.
2. `UX-B` — Product-local job application/worker and verified TASK-055 handoff.
3. `UX-C` — shell workspace, accessible UI, and installer integration.

Order: released wheel + exact TASK-055 identity, then `UX-A -> UX-B -> UX-C`.

`TASK-062` is `DEPENDENCY_BLOCKED` until a released wheel digest and current
TASK-055 schema/admission identity are frozen in an implementation Unit. This
metadata record neither downloads nor executes a runtime package.

## Current authorization state

Implementation, packaging, native Windows interaction, Product Project writes,
Timeline/Resolve effects, Release, Deploy, and Production are `NOT_AUTHORIZED`.

## Governing authorization

Closed Allowed Files—including the accepted trusted-launcher composition-root
amendment—and all acceptance/stop rules are fixed in
`task062-owner-allocation-and-implementation-authorization-2026-08-27.md`.
