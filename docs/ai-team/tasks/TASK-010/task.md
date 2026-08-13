# TASK-010 — Resolve Assembly MVP

- Status: `IMPLEMENTED / AUTOMATED_VALIDATED / NATIVE_VALIDATED / INTEGRATION_DESIGNED`
- Governance: `DEV-4`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION`
- Wave: Technical MVP contiguous editing wave, 2026-08-12
- Release status: NOT RELEASED BY THIS WORK

## Purpose

Compile an approved TASK-007 Edit Plan through TASK-022 timing into an Automation-owned Resolve assembly and execute only after an explicit external-write authorization.

## Inputs

Approved Edit Plan, exact rational timeline rate/origin, optional approved TASK-006 subtitle plan, optional generic audio placement contracts, source/normalized media bindings and its probed frame rate.

## Outputs

Deterministic `BAI_AUTO_*` assembly plan/hash, exact timeline mapping, optional subtitle/audio execution state, and idempotent assembly result.

## Hard boundaries

Never mutate a human Timeline. Only `BAI_AUTO_*` Timeline names are allowed. Real write requires explicit runtime authorization. Existing matching marker => no-op; conflicting/partial deterministic Timeline => fail closed. Source frame rate is mandatory and may never be substituted with timeline FPS. Subtitle/audio scripting semantics remain native validation gates.

## Exit rule

Headless capability may reach `IMPLEMENTED`, but Product completion remains `INTEGRATION_DESIGNED` until Unified Desktop Shell wiring exists, and external Windows/Resolve/Cubase behavior may not be labeled `NATIVE_VALIDATED` until real-machine Evidence passes.

## Phase G native acceptance — 2026-08-13

Real DaVinci Resolve Studio `21.0.2.4` Evidence passes source-rate-aware trim assembly, linked video/audio preservation, Timeline-start-relative record placement, idempotent replay, partial/conflict rejection and edit-aware subtitle text/timing semantics. TASK-010 backend is `NATIVE_VALIDATED`; Product-facing completion remains blocked on TASK-036 W2.
