# TASK-046 P-VS-1A CHANGELOG Integration Lock

Date: `2026-08-15`
Authority: `Owner-approved PR #93 short Integration Lock / Delegated Owner Authorization`
Profile: `DEV-2 / docs-only governance integration`
Decision: `PASS_FOR_DOCS_ONLY_LOCK_HOSTING`

## Current-main and dependency audit

- fresh `main`: `0c171f3a7ffffdf0179ced7476664a16c9c444a7`;
- TASK-036 Track correction target PR `#94` exact head:
  `42cc0a933b51b2b56eea84682d7664b6d8b456ec`;
- TASK-036 exact merge: `0c171f3a7ffffdf0179ced7476664a16c9c444a7`;
- TASK-036 hosted checks: `9 / 9 PASS`;
- TASK-036 post-merge CI run `31879569752`: `PASS`;
- TASK-036 post-merge Security run `31879569750`: `PASS`;
- TASK-036 packaged Evidence SHA-256:
  `ee15487e237c630f750512322963eaed5e9632e4e79b4be6442464d2d134ac38`;
- whole-surface V6.1.1 parity remains a separate OPEN screen-by-screen
  follow-up and is not falsely closed by the Track unit.

Target audit:

- target PR: `#93`, OPEN / DRAFT / MERGEABLE;
- target branch: `codex/task-046-p-vs-1a-body-free-backend`;
- exact pre-integration head:
  `a87e741f9213a532e152fd01c1a243ae7837ef3e`;
- target implementation diff: the eight previously audited P-VS-1A Allowed
  Files only;
- product/security checks: `8 / 8 PASS`;
- only failure: `changelog-and-version` requires `CHANGELOG.md`;
- `CHANGELOG.md` is a shared Integration File outside P-VS-1A Allowed Files.

The quality gate is valid and remains unchanged.

## Hosting Allowed Files

This Lock-hosting unit may change only:

- `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`;
- `docs/ai-team/work-locks/task046-pvs1a-changelog-integration-lock-design-critic-judge-2026-08-15.md`.

It cannot change `CHANGELOG.md` or any P-VS-1A implementation file. The target
branch may receive one CHANGELOG entry only after this Lock is exactly hosted on
main and its post-merge checks pass.

## Hosted target Lock

- owner: `開発担当 / Integration owner`;
- target PR: `#93`;
- target branch: `codex/task-046-p-vs-1a-body-free-backend`;
- expected pre-integration head:
  `a87e741f9213a532e152fd01c1a243ae7837ef3e`;
- allowed file: `CHANGELOG.md` only;
- purpose: one exact P-VS-1A change-history entry required by CI;
- denied: all eight P-VS-1A implementation files, `.github/**`, every other
  shared file, version, Tag, Release and Deploy;
- expiry: target head mismatch, target PR close/merge, or completed integration
  and recorded Lock release;
- workflow policy: no exception and no weakening.

## Builder plan

1. Host this two-file docs-only Lock in its own PR.
2. Require all hosted checks, exact main merge and post-merge CI/Security.
3. Re-read the Lock from main and require PR #93 head to remain the exact
   expected SHA; mismatch is Safe Stop.
4. Add one exact P-VS-1A entry to `CHANGELOG.md` only. Do not touch the eight
   implementation files.
5. Integrate fresh main without force push, prove target diff containment and
   overlap `0`, and rerun every hosted check.
6. Move PR #93 from Draft to Ready only after all conditions pass, then merge,
   verify exact main SHA and post-merge CI/Security.
7. Record Lock `CLOSED/RELEASED`. Version, Tag, Release and Deploy remain a
   separate Human Gate.

## Critic pass 1

1. **High — CI bypass:** modifying workflow behavior would conceal missing
   release metadata. Resolution: `.github/**` denied; CI unchanged.
2. **High — implementation ownership:** Integration owner could accidentally
   absorb developer 2's eight files. Resolution: they are explicit read-only
   denials; only CHANGELOG may be added to the target branch.
3. **High — stale target:** another commit could invalidate the audit.
   Resolution: exact PR, branch and pre-integration head are mandatory; mismatch
   expires the Lock.
4. **High — TASK-036 ordering:** P-VS-1A must not merge before Consumer closure.
   Resolution: exact PR #94 merge plus post-merge CI/Security are recorded before
   this Lock is hosted.

Unresolved Critical/High: `0 / 0`.

## Critic pass 2

1. TASK-036 Track-unit Hosted Closure is recorded without expanding it into a
   false whole-surface parity claim.
2. The previous P-UX-1C CHANGELOG Lock is moved to immutable released history,
   leaving one active Integration Lock.
3. Target identity, owner, one-file scope, purpose, denial and expiry are exact.
4. No force push is authorized; fresh main is integrated without rewriting the
   published target history.
5. OBS, recording, Voice body persistence, Model execution, Cloud, paid,
   Credential, version, Tag, Release and Deploy remain outside authority.

Unresolved Critical/High: `0 / 0`.

## Judge

Decision: `PASS_FOR_DOCS_ONLY_LOCK_HOSTING`.

The Lock becomes authoritative only on exact main. Only then may the target
branch receive one CHANGELOG entry, and only an all-green exact target may leave
Draft and merge.
