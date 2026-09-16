# TASK-095 — v0.24.3 Corrective Windows Release

- Status: `ACTIVE / VERSION_BUMP_AND_RELEASE_PREPARATION`
- Capability: `BVP-V0.24.3-CORRECTIVE-RELEASE-001`
- Governance: `DEV-3 HIGH ASSURANCE`
- Owner authority: `2026-09-16` — 「公開しなおして」
- Base: TASK-094 hosted closure at main
  `61d73644d7834fe156a7c2560ab529f75338bee1`

## Objective

Publish the TASK-094 Windows installer corrections as a new immutable
`0.24.3 / v0.24.3` release. Preserve v0.24.2 and never move or replace its tag.
Build every distributed EXE/installer and ZIP again from the exact v0.24.3 tag,
publish Python wheel/sdist plus complete checksums, and read back every remote
asset identity.

## Required assets

- Python wheel and sdist
- BAI Video Production Windows ZIP and installer
- BAI DbD Training Studio Windows ZIP and installer
- BAI DbD Trivia Editor Windows ZIP and installer
- BAI Voice Model Builder Windows ZIP and installer
- BAI Voice Capture runtime/source ZIP and installer
- BAI Owner Voice Runtime installer
- complete checksum manifests

## Allowed files

- canonical version metadata and `CHANGELOG.md`
- Owner Voice Runtime version wiring, user/developer guides and exact tests
- Windows build/release metadata, release assets and exact contract tests needed
  for 0.24.3
- `docs/ai-team/current-state.md`
- `docs/ai-team/tasks/TASK-095/**`

## Acceptance

- version metadata is exactly `0.24.3` and release metadata checks pass;
- TASK-094 focused/native installer Evidence remains admitted;
- required focused, targeted and hosted checks are all green;
- PR is merged before tag creation;
- annotated `v0.24.3` points to exact merged main and is never moved;
- exact-tag Windows builds produce every required asset in a contained unique
  worktree output root;
- GitHub Release assets match local byte sizes and SHA-256 values;
- durable external Evidence is persisted and read back.

## Prohibited effects

- no overwrite, deletion or tag movement of v0.24.2;
- no force push or direct source push to protected main;
- no private Owner audio, real voice generation, training or model promotion;
- no user installation, OBS mutation, paid Provider call or Production
  Activation during build verification;
- no task-owned drive-root or direct-child output.
