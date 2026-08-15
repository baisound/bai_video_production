# TASK-036 P-UX-1C CHANGELOG Integration Lock

Date: `2026-08-15`
Authority: `Delegated Owner Authorization (2026-08-15)`
Profile: `DEV-2 / docs-only governance integration`
Decision: `PASS_FOR_DOCS_ONLY_LOCK_HOSTING`

## Current-main audit

- fresh `main`: `841cda2e5f4eb4dbc5304d5f57afe49392723825`;
- target PR: `#94`, OPEN / READY / MERGEABLE;
- target branch: `codex/task-036-v611-packaged-native-closure`;
- exact pre-integration head:
  `dbccf1b1e6717a96d87440df1ebe8e707b3b8623`;
- CI result at audit: product/security checks `8 / 8 PASS`;
- only failure: `changelog-and-version` requires `CHANGELOG.md` for Product
  changes;
- `CHANGELOG.md` is outside `BVP-LOCK-TASK036-PUX1C` and is a shared
  Integration File;
- TASK-046 P-VS-1A files and PR #93 are not part of this unit.

No workflow exception or CI weakening is justified. The quality gate is valid;
the missing authority must be supplied through a narrow hosted Lock.

## Hosting Allowed Files

This docs-only Lock-hosting unit may change only:

- `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`;
- `docs/ai-team/work-locks/task036-pux1c-changelog-integration-lock-design-critic-judge-2026-08-15.md`.

It may not change `CHANGELOG.md` itself. The target PR may change that file only
after this Lock is merged exactly to main and post-merge CI/Security pass.

## Hosted target Lock

- owner: `開発担当 / Integration owner`;
- target PR: `#94`;
- target branch: `codex/task-036-v611-packaged-native-closure`;
- expected pre-integration head:
  `dbccf1b1e6717a96d87440df1ebe8e707b3b8623`;
- allowed file: `CHANGELOG.md` only;
- purpose: one exact P-UX-1C change-history entry required by
  `changelog-and-version` CI;
- denied: TASK-036 implementation/Evidence, TASK-046 P-VS-1A implementation,
  `.github/**`, every other shared file, version, Tag, Release and Deploy;
- expiry: target head mismatch, PR close/merge, or successful integration and
  Lock release;
- workflow policy: no exception and no weakening.

## Builder plan

1. Host this two-file docs-only Lock through a separate PR.
2. Require all hosted checks, exact main merge and post-merge CI/Security.
3. Re-read the Lock from main and verify PR #94 head equals the expected SHA.
4. If and only if it matches, add one exact Japanese P-UX-1C entry to
   `CHANGELOG.md` on PR #94 without touching any other file.
5. Rebase the target branch onto fresh main, verify Lock containment and
   TASK-046 overlap `0`, then run all hosted checks.
6. Merge PR #94 only when every check is green. Verify exact merge SHA and
   post-merge CI/Security before declaring P-UX-1C `HOSTED_CLOSED`.

## Critic pass 1

1. **High — bypass risk:** changing `.github` would hide the missing metadata.
   Resolution: `.github/**` is explicitly denied.
2. **High — shared-file overreach:** a broad shared-file grant could mix roadmap
   or Voice work into P-UX-1C. Resolution: target Allowed Files contains only
   `CHANGELOG.md`.
3. **High — stale-head write:** PR #94 could change during Lock hosting.
   Resolution: exact pre-integration head is mandatory; mismatch expires the
   Lock and requires Safe Stop.
4. **Medium — premature write:** adding CHANGELOG in the hosting PR would make
   authority self-effective. Resolution: this hosting unit cannot edit it.

Unresolved Critical/High: `0 / 0`.

## Critic pass 2

1. Target identity includes PR, branch and exact head.
2. Owner, one-file scope, purpose, denial and expiry are explicit.
3. TASK-036 remains first in merge order; PR #93 remains untouched until
   TASK-036 Hosted Closure.
4. Version, Tag, Release, Deploy, Provider, Credential, OBS, recording and Model
   execution remain outside authority.
5. The previous TASK-047 docs-only Lock is recorded as
   `HOSTED_CLOSED_RELEASED`, preventing two apparently active Integration Locks.

Unresolved Critical/High: `0 / 0`.

## Judge

Decision: `PASS_FOR_DOCS_ONLY_LOCK_HOSTING`.

The Lock becomes authoritative only after exact main merge. A main-hosted Lock,
exact target-head match and post-hosting checks are mandatory before the one-file
target integration starts.
