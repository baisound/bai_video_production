# TASK-051 — v0.22.0 Release Closure

Status: RELEASE_CANDIDATE
Profile: DEV-4 FOUNDATION CRITICAL
Depends on: merged main through TASK-036 P-UX-2D4/D5, TASK-049 and TASK-050
Authority: Owner-selected `0.22.0 / v0.22.0 / stable` on 2026-08-21

## Purpose

Publish the current integrated Product line as the exact stable `v0.22.0` release without reopening completed Task history or widening unfinished Product Gates.

## Responsibility boundary

TASK-051 owns version and citation consistency, CHANGELOG section promotion, release notes, regression/package verification, hosted checks, exact main merge, annotated Tag, repository Release workflow, published-asset read-back, Integration Lock closure and branch cleanup.

TASK-051 does not claim or authorize P-UX-2E packaged-native output read-back, per-Job dispatch/render, publication through external services, paid Provider execution, private credential use, native NLE mutation, model download/training, recording, Production Deploy or completion of separately parked Gates.

## Acceptance

1. all seven runtime/package version surfaces equal `0.22.0`;
2. CHANGELOG receives exact dated `0.22.0` promotion under the hosted Lock;
3. metadata checker, focused checks, full regression, compileall and distribution build pass;
4. release PR receives all hosted checks and merges at an exact read-back SHA;
5. annotated `v0.22.0` dereferences to that exact SHA;
6. Release workflow succeeds and published wheel/sdist metadata and hashes are read back;
7. post-release Evidence closes the Lock and cleanup removes task branches.
