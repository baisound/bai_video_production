# TASK-011 — Render QA / Loudness

- Status: `IMPLEMENTED / AUTOMATED_VALIDATED / INTEGRATION_DESIGNED`
- Governance: `DEV-3/4`
- Authorization: `OWNER_DIRECTED_IMPLEMENTATION`
- Wave: Technical MVP contiguous editing wave, 2026-08-12
- Release status: NOT RELEASED BY THIS WORK

## Purpose

Verify a rendered artifact before editor handoff using structural media checks, expected Timeline duration and configurable loudness/true-peak policy.

## Inputs

Rendered file, expected duration frames, exact Timeline frame rate, tolerance, media probe and optional loudness profile.

## Outputs

Path-free Render QA report containing artifact checksum/size, probe summary, loudness measurement/profile, individual checks and PASS/FAIL hash.

## Hard boundaries

Fixed-argv FFmpeg/ffprobe only; no shell. QA result persists no render absolute path. Structural provider failures raise; ordinary quality misses produce a deterministic FAIL report. -16 LUFS is a configurable default profile, not a universal delivery claim.

## Exit rule

Headless capability may reach `IMPLEMENTED`, but Product completion remains `INTEGRATION_DESIGNED` until Unified Desktop Shell wiring exists, and external Windows/Resolve/Cubase behavior may not be labeled `NATIVE_VALIDATED` until real-machine Evidence passes.
