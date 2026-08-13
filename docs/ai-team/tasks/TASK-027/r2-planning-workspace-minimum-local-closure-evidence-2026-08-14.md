# TASK-027 — R2 Planning Workspace Minimum Local Closure Evidence

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `12aa9a790e9c60705deaa13d0dcaf6b4e919c68c`
- Working branch: `codex/task-027-planning-workspace-minimum`
- DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
- Local Gate: `PASS`
- Hosted PR Gate: `PENDING`
- Release decision: `NO_RELEASE_AT_TASK027_MINIMUM_CHECKPOINT`

## Promoted Product capability

TASK-027 minimum promotes the accepted Planning Foundation into the trusted unified Desktop Shell.

- fixed project-owned `production-proposal.json` is reloaded for every command;
- persisted Proposal IDs, latest revision, Intent, section history/change and full Blueprint Scene Contract are visible in `企画`;
- each Scene displays exact frame range, narrative role, source strategy, generation risk, camera, references and audio intent;
- GO requires exact Proposal snapshot/revision, reference Asset bindings, cost ceiling, rights acknowledgement when applicable and explicit approver identity;
- GO confirmation is exact, stale-safe and one-shot, then the updated Proposal/Approved Plan snapshot is published through CAS;
- Proposal CAS check and atomic replacement are serialized across local Product processes;
- Human GO persists an immutable Approved Production Plan but starts no Provider, paid execution, Budget reservation, Resolve mutation or publishing;
- Approved Plan -> Production Control installation is a second one-shot confirmation bound to exact Proposal and Production snapshot identities;
- Plan installation reuses the accepted TASK-027/037 compiler and creates exact Plan -> Blueprint/Scene -> Asset Slot trace;
- restart detects an exactly installed Plan rather than duplicating Slots;
- no Candidate, Audit decision, LOCK, generation queue item or external mutation is created.

## Bounded Critic result

- Critical findings after correction: `0`
- High findings after correction: `0`

Corrections and verified controls:

1. separated Human GO from Approved Plan -> Production Control installation;
2. consumed both confirmations before current-state revalidation so a failed stale token cannot later become valid;
3. reloaded current Proposal/Production snapshots for every durable command;
4. serialized Proposal CAS publication across processes and proved that concurrent GO publication permits exactly one writer;
5. derived Scene/Slot state through existing canonical compilers rather than accepting caller-provided loose Slots;
6. kept Proposal provider creation, paid execution, Budget reservation, Resolve/Cubase mutation and publish outside this minimum.

## Validation

- final focused Planning / Production / Desktop Shell gate: `70 / 70 PASS` after Critic correction;
- Windows full regression: `842 PASS / 1 intentional non-Windows skip / 0 FAIL`;
- concurrent GO first-writer test: PASS; exactly one Approved Plan is published;
- stale/replayed GO, newer Proposal after prepare, project-scope mismatch and persisted restart: fail closed/PASS;
- separate Plan installation, exact trace and restart detection: PASS;
- Windows Python `compileall`: PASS;
- Ubuntu WSL2 `/mnt/d` Python `compileall`: PASS;
- `git diff --check`: PASS.

The Ubuntu distribution has no installed pytest, so no WSL pytest PASS is claimed and no dependency was installed or downloaded. Windows full regression is the local Product gate.

The in-app browser visual harness remained unavailable because its local kernel asset path could not be initialized earlier in this run. No new visual PASS is claimed. Safe DOM `textContent`, keyboard-focusable controls, complete Scene/authority text and strict bridge allowlisting are covered by automated tests; previously accepted TASK-036 native visual Evidence is not rewritten.

## Claim and release boundary

This completes the bounded R2 Planning Workspace minimum local gate, not all future TASK-027 slices. AI proposal generation, provider execution, production Budget mutation, generation queue integration and Resolve assembly remain separately owned/gated.

Formal closure requires a dedicated PR, all hosted checks, exact `main` merge verification and branch cleanup. Stable Product release remains `v0.20.1`; no package, Tag or GitHub Release is selected at this checkpoint.

Existing untracked raw native `evidence/` is preserved and excluded from staging.
