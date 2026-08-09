# AI Video Production — Project Summary

`ai-video-production` is a Consumer Project built on BAI Development OS governance without copying OS Core into the repository.

The product analyzes source media, creates auditable edit intelligence and safely assembles human-finishable timelines around DaVinci Resolve.

## Completed foundation

**TASK-001** completed IDs, Product Job state/recovery, manifests, schemas, base Asset/rights, Logical URI, atomic persistence, Evidence/Checkpoint, ownership, profiles/plugins, SQLite and idempotency.

**TASK-002** completed DaVinci Resolve Studio 21.0.2.4 capability verification and the WSL2→Windows authenticated HTTP/JSON IPC architecture.

**TASK-003** completed secure source Asset ingestion: allowlisted source boundary, ffprobe/SHA-256, rights metadata, immutable `asset://` promotion, SQLite v2, concurrency-safe source manifests and crash/idempotency recovery.

## Active TASK-004 checkpoint

TASK-004 package `0.4.8` has accepted target-runtime ComfyUI and Audacity/OpenVINO capability Evidence and now awaits bounded OpenVINO behavioral Evidence. It establishes:

- exact timebase/proxy/48 kHz media normalization;
- shared safe derived-Asset publication;
- ComfyUI local Image/Video AI boundary for FLUX/Stable Diffusion/MiniMax H3;
- Character Identity and H3 Production Brief foundations;
- optional H3 SingleFrame and Spectrum contracts;
- H3 Foley/SFX generation contract with community-experimental modes clearly separated;
- Audacity/OpenVINO external local Audio AI boundary for Noise Suppression and Music Separation;
- minimum resource/license/admission Evidence and crash-safe external dispatch rules.

These are prerequisites for the editing-first SRT/subtitle, filler/cut, SE/BGM/narration and Resolve placement route.

## Current verification

- TASK-001: COMPLETED
- TASK-002: COMPLETED
- TASK-003: COMPLETED / DEV-4 score 33
- TASK-004: `CAPABILITY_VERIFIED_AWAITING_LIVE_BEHAVIORAL_EVIDENCE` / DEV-4 score 25
- package: `0.4.8`
- `pytest`: `250 / 250 PASS`
- wheel + installed-wheel golden normalization: PASS
- target ComfyUI/Audacity live capability Evidence: ACCEPTED; Attempt 07 stopped before Audacity mutation because Windows low-level media descriptors were not opened with `O_BINARY`; package 0.4.7 corrective implemented and regression-pinned; synthetic OpenVINO behavioral Evidence: RERUN PENDING
