# TASK-012 — Manual Handoff / Cubase

- Status: `IMPLEMENTED / AUTOMATED_VALIDATED / INTEGRATION_DESIGNED`
- Governance: `DEV-3`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION`
- Wave: Technical MVP contiguous editing wave, 2026-08-12
- Release status: NOT RELEASED BY THIS WORK

## Purpose

Create a deterministic EDITOR_WORK package only after approved Cut Plan, completed Resolve assembly and passing Render QA; support bounded professional audio round-trip without pretending to convert Cubase projects automatically.

## Inputs

Approved Edit Plan, completed Assembly result, PASS Render QA, unchanged render master; optional reviewed SRT, Resolve snapshot and PCM audio exports.

## Outputs

`EDITOR_WORK_*` relative-path handoff tree, checksummed manifest, optional 48 kHz PCM export/return workflow and return Evidence.

## Hard boundaries

Re-hash render at handoff to detect post-QA changes. Persist relative paths only. Existing deterministic destination is never overwritten. Cubase return must be regular PCM WAV, 48 kHz and duration-bounded. No automatic Cubase project conversion is promised.

## Exit rule

Headless capability may reach `IMPLEMENTED`, but Product completion remains `INTEGRATION_DESIGNED` until Unified Desktop Shell wiring exists, and external Windows/Resolve/Cubase behavior may not be labeled `NATIVE_VALIDATED` until real-machine Evidence passes.
