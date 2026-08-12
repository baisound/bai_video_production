# TASK-007 — Candidate Clip Graph / Cut Plan

- Status: `IMPLEMENTED / AUTOMATED_VALIDATED / INTEGRATION_DESIGNED`
- Governance: `DEV-3`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION`
- Wave: Technical MVP contiguous editing wave, 2026-08-12
- Release status: NOT RELEASED BY THIS WORK

## Purpose

Convert TASK-024 review-only cut candidates into a deterministic, explainable and human-approved Edit Plan without converting candidate strength into automatic destructive authority.

## Inputs

TASK-024 CutCandidateManifest; optional target duration; explicit per-candidate human CUT/KEEP decisions; optional bounded CUT override.

## Outputs

Candidate graph, proposed/final decisions, deterministic keep/cut ranges, projected duration, plan hash and explicit approval state.

## Hard boundaries

TASK-024 auto_apply=false is mandatory. Scores can rank proposals only. Every candidate stays REVIEW until a human decision exists. Plan approval is a second gate. Keep blocks cannot be cut. No external write authorization is ever serialized.

## Exit rule

Headless capability may reach `IMPLEMENTED`, but Product completion remains `INTEGRATION_DESIGNED` until Unified Desktop Shell wiring exists, and external Windows/Resolve/Cubase behavior may not be labeled `NATIVE_VALIDATED` until real-machine Evidence passes.
