# TASK-038 — R2 Audit Product Promotion Local Closure Evidence

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `66446cf01ad5210ce196bc2803a5ffb18a37139c`
- Working branch: `codex/task-038-audit-product-promotion`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Local Gate: `PASS`
- Hosted PR Gate: `PENDING`
- Release decision: `NO_RELEASE_AT_TASK038_CHECKPOINT`

## Promoted Product capability

TASK-038 promotes the accepted immutable Audit/Human-decision Foundation rather than duplicating it.

- project-owned `candidate-audit.json` and `production-control.json` remain the durable stores;
- a bounded `task038-decision-transaction.json` records the exact intended Human transition before either store changes;
- every operation reloads current snapshots and checks exact project, Candidate, Asset SHA-256 and Audit-set identity;
- a Candidate must be explicitly `READY_FOR_AUDIT` before the Application accepts an immutable Audit;
- ACCEPT / REJECT / ALTERNATE_USE / NEEDS_REGENERATION use an exact one-shot Human confirmation;
- Audit is saved first and Production lifecycle second under a project-local transaction lock;
- interruption exposes explicit `OLD_OLD`, `AUDIT_NEW_PRODUCTION_OLD`, `AUDIT_OLD_PRODUCTION_NEW` or `NEW_NEW` recovery; an unknown mixture has no action and fails closed;
- the unified Desktop `制作管理` drawer shows Auditor kind/identity, scores, findings, Failure Codes, Critical state and alternate-use proposals;
- Human decision buttons require actor identity and show Candidate, Asset checksum, Audit refs, Critical state and selected decision before apply;
- Candidate decision and TASK-037 LOCK remain separate Human actions;
- Reject never deletes an Asset, and NEEDS_REGENERATION never starts a Provider.

## Bounded Critic result

- Critical findings after correction: `0`
- High findings after correction: `0`

Corrections and verified controls:

1. replaced naive two-file save with a prepared exact transaction and explicit restart recovery;
2. consumed Application confirmation before reload/current-state validation, preventing a failed stale token from becoming valid later;
3. blocked all ordinary Audit actions while a prepared transaction requires recovery;
4. restricted automatic recovery to exact old/new snapshot combinations and provided no action for unknown mixtures;
5. retained full immutable Audit history in the projection instead of presenting only an aggregate score;
6. used DOM `textContent` for Candidate/Audit fields and kept ACCEPT separate from LOCK;
7. kept physical deletion, automatic regeneration, paid Provider execution and Resolve/Cubase mutation outside TASK-038.

## Validation

- focused TASK-038 / TASK-037 / Desktop Shell gate: `86 / 86 PASS`;
- Windows full regression: `833 PASS / 1 intentional non-Windows skip / 0 FAIL`;
- interruption after transaction prepare: explicit `OLD_OLD` recovery/abandon PASS;
- interruption after Audit save: explicit exact completion PASS;
- interruption after both stores: explicit finalization PASS;
- unknown mixed state: no automatic recovery action PASS;
- transaction checksum tamper, stale snapshots, replay and cross-project state: fail closed PASS;
- Windows Python `compileall`: PASS;
- Ubuntu WSL2 `/mnt/d` Python `compileall`: PASS;
- `git diff --check`: PASS.

The Ubuntu distribution still has no installed pytest, so no new WSL pytest PASS is claimed and no dependency was installed or downloaded. The Windows full regression is the local Product gate.

The in-app browser visual harness again failed before page creation because its local kernel asset path was unavailable. No new visual PASS is claimed. Safe DOM construction, responsive Audit markup, exact confirmation text and bridge allowlisting are covered by automated tests; previously accepted TASK-036 native visual Evidence is not rewritten.

The first hosted CI run found one canonical-document contract error, not a Product-code failure: `Development Candidate` had been populated with a TASK label even though that field accepts only a semantic release version or `NONE`. Because this checkpoint selects no release, `PROJECT.md` and `current-state.md` now consistently retain `NONE`. The exact contract test and the full Windows regression then passed locally again.

## Claim and release boundary

The local implementation gate passes. Formal TASK-038 completion still requires a dedicated PR, all hosted checks, exact `main` merge verification and branch cleanup.

This checkpoint does not change package/version metadata and does not create a Tag or GitHub Release. Stable Product release remains `v0.20.1`. After hosted closure, the Owner-routed R2 sequence advances to TASK-027 Planning Workspace minimum on a new dedicated branch.

Existing untracked raw native `evidence/` is preserved and excluded from staging.
