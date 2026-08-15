# TASK-047 / P-OBS-1A Canonical Contract Lock Closure — Builder / Critic / Judge

- Date: 2026-08-15
- Unit: `TASK-047/P-OBS-1A H2 LOCK CLOSURE`
- Authority: `BVP-AUTH-20260815-TASK047-POBS1A-H2-LOCK-CLOSURE`
- Branch: `codex/task-047-pobs1a-contract-lock-closure`
- Audit base: `00e1c75f186b0ba0240d75a96c5bf33fde224e19`
- Entry Registry: revision `8`, blob `dd0d2ce40cf11b7e3a1f3fba2b09de8c88f525db`
- Exit Registry proposal: revision `9`
- Authority boundary: docs-only exact two-file closure; implementation, build, install, load, OBS launch, configuration, capture, release, and deploy are not authorized.

## 1. Builder decision

The canonical P-OBS-1A Rev.2.1 contract was hosted by PR #102 and read back from exact main. This unit closes only `BVP-LOCK-TASK047-POBS1A-CONTRACT-HOST`; it does not authorize or start native implementation.

The closure becomes authoritative only when this exact two-file unit is merged into `main`, because the Registry activation scope remains `AUTHORITATIVE_ONLY_WHEN_READ_FROM_MAIN`. Pre-merge hosted checks are a merge gate. Post-merge CI and Security for this closure PR are mandatory operational verification and branch-cleanup gates; a later failure must create a separate incident/correction unit and must not rewrite the recorded PR #102 history.

## 2. Serialized dependency state

- Fresh main: `00e1c75f186b0ba0240d75a96c5bf33fde224e19`
- P-VS-3A implementation Lock: `HOSTED_CLOSED_RELEASED`
- P-VS-3A CHANGELOG Integration Lock: `HOSTED_CLOSED_RELEASED`
- P-QC-1A Lock: `ACTIVE`; no P-QC implementation completion is claimed.
- P-OBS-1A contract-hosting Lock before this unit: `ACTIVE`
- P-OBS-1A implementation authority: `NOT_AUTHORIZED`
- P-OBS-1A implementation state: `NOT_STARTED`
- Open pull requests at the pre-commit audit: `0`; authorized-path overlap: `0`
- P-OBS-0 T0 trust validation remains parked with the exact catalog mismatch; installed toolchain or host observations do not rewrite that receipt.

## 3. PR #102 immutable hosting receipt

- PR: `#102`
- Base: `a7690917b2c05c44372a1c7ea6dd81d422b1aa88`
- Reviewed head: `898555e4998173f6d77c6679ae151ba3d6ed5ff9`
- Merge/main: `1c94fac10f2c4beb9c31b2eccb85f97d531fabde`
- Merge parents: exact base plus exact reviewed head
- Changed files: exactly `4`
- Pre-merge hosted checks: `9 / 9 SUCCESS`
- Pre-merge CI: `31890071504`
- Pre-merge Release metadata check: `31890071652`
- Pre-merge Security: `31890071633`
- Post-merge CI: `31890287294`, `SUCCESS`
- Post-merge Security: `31890287319`, `SUCCESS`

| Artifact | Git blob | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Rev.2.1 contract | `82a84898e4cc738e158acd3f77c36ac772cc387f` | 20,234 | `5ec78a4aeaafd921b0a5f81b483a176ac99a54cbf0cce02a1db4443cf2f65362` |
| Provenance | `c773f7e044ab967cbba3d3edc1fc648e0692fa30` | 8,650 | `aa18f51f069c2857a02a6a63f79556b2dd9096a787d6c16e178593c4c01244a5` |
| Hosting Evidence | `579c9532ff645eb94cbecd579fde6cbc5c33d988` | 4,443 | `b32d6dc7b2cbbe7477cbfb9e6b455d16df27d4c7874c7d7c453717488ba2cbf9` |
| TASK-047 pointer | `10bdf7ce7515b90a8edce947d3b072a3d46a76f3` | 5,654 | `c41f21b7b65fcf0f2a4a6285a2b1ebac644f78fc3c7300dfa721188add31df81` |

Main read-back at both `1c94fac10f2c4beb9c31b2eccb85f97d531fabde` and fresh main `00e1c75f186b0ba0240d75a96c5bf33fde224e19` matched all four Git blobs, byte lengths, and SHA-256 values.

## 4. Registry delta

Only these semantic changes are permitted:

1. `registry_revision`: `8` to `9`.
2. `audit_base_main_sha`: exact fresh main.
3. `last_completed_gate`: exact PR #102 contract-hosting closure.
4. `BVP-LOCK-TASK047-POBS1A-CONTRACT-HOST.status`: `ACTIVE` to `HOSTED_CLOSED_RELEASED`.
5. Append the closure authority and exact PR #102 hosted receipt.

All original immutable P-OBS Lock fields remain present. `implementation_authority_state=NOT_AUTHORIZED` and `implementation_state=NOT_STARTED` remain unchanged. P-QC, P-VS-3A, integration history, shared files, roadmap dependency gates, merge order, and global denied operations remain unchanged.

## 5. Acceptance and failure handling

- Changed paths must be exactly the two authorized paths.
- Registry JSON must parse, remain revision `9`, and name exact audit base `00e1c75f...`.
- The P-OBS terminal record must preserve every original field and add only terminal Evidence.
- A/B/C/D must remain outside the diff and match all four receipts.
- P-QC and P-VS-3A records must be byte-semantically unchanged.
- No workflow, CHANGELOG, code, schema, test, native, package, version, tag, release, or deploy change is allowed.
- Any main, Registry blob, PR #102 receipt, path-scope, or active-Lock drift before push or merge requires safe stop.
- A failed or unknown hosted check is not retried, bypassed, or converted to PASS.
- No automatic rollback, rebase, force-push, reset, cleanup, or branch deletion is allowed.

## 6. Critic review 1 — Evidence preservation

Initial risk: reducing the terminal Lock to only status and result fields would discard the authority, scope, denial, prerequisite, expiry, and release history required for an append-only canonical record.

Correction: retain the entire original P-OBS Lock object, keep the original implementation boundary unchanged, and append an exact `hosted_closure` receipt plus the closure authority.

Result: Critical `0`, High `0`, Medium `0`.

## 7. Critic review 2 — Closure-cycle and authority escalation

Initial risk: making this closure PR's own post-merge checks a recorded prerequisite would create a circular closure, while the word “closed” could be misread as implementation admission.

Correction: the release record becomes effective when the exact two-file closure is merged and thereby hosted on main after all pre-merge checks pass. Its post-merge checks are operational verification and cleanup gates. The Registry explicitly retains `NOT_AUTHORIZED` and `NOT_STARTED` for implementation.

Result: Critical `0`, High `0`, Medium `0`.

## 8. Read-only Judge proposal

- Exact two-file diff: `PASS`
- Registry JSON parse and revision `8` to `9`: `PASS`
- Original P-OBS Lock fields preserved: `22 / 22 PASS`; only the authorized status transition changed an original value
- P-VS-3A and P-QC Lock records: `UNCHANGED PASS`
- Shared files, integration history, roadmap dependency gates, merge order, and global policies: `UNCHANGED PASS`
- A/B/C/D Git blob receipts: `4 / 4 PASS`
- Hosted checks: pending Draft PR
- Critical / High / Medium: `0 / 0 / 0`
- Proposed decision: `PASS_FOR_DRAFT_PR_AND_HOSTED_CHECKS`
- Ready / Merge: `NOT_AUTHORIZED_PENDING_FRESH_DESIGN_JUDGE`
- Native implementation / build / install / load / OBS launch / capture: `NOT_AUTHORIZED`
