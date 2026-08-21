# TASK-036 P-UX-2E EDIT_PERSISTENCE Reader CHANGELOG Integration Lock Hosting

Date: 2026-08-21

Unit: `TASK-036/P-UX-2E-EDIT-READER-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_AUTONOMY_AND_ALL_GREEN_MERGE_DIRECTIVE_20260821`

Status: `DRAFT_PR_READY / SELF_REVIEW_ACCEPTED / PENDING_LOCK_HOST_PR`

## Scope

This exact two-file governance transaction proposes one shared
`CHANGELOG.md` integration effect required by the hosted release-metadata
check for target PR `#249`. It changes no Product implementation, runtime,
version, Tag, Release, Provider, native, export or Audio state.

- fresh base main: `311a623ae9ff63751bcb99439ca03bf03c90bc0c`
- fresh main CI: run `32477671405`, six-of-six matrix PASS
- fresh main Security: run `32477671398`, PASS
- Registry revision: `37 -> 38`
- previous TASK-041 shared lock: `HOSTED_CLOSED_RELEASED`
- nonclosed integration locks before proposal: `0`
- open PR shared-path overlap: `0`; only target PR `#249` is open
- target branch: `codex/task-036-pux2e-edit-persistence-reader`
- expected target head: `c5e778af7c57b13e790b7fc61d0eea75b4371400`
- immutable target paths: `11`
- target hosted checks before lock: `8 / 9 PASS`; only
  `changelog-and-version` requires `CHANGELOG.md`
- allowed shared effect after hosting merge: add the exact approved bullet
  below under `[Unreleased]`
- denied: target implementation/test/Evidence rewrite, workflow weakening,
  receipt minting, Provider/native/export execution, version/Tag/Release/Deploy

## Approved CHANGELOG bullet

> - TASK-036 P-UX-2Eとして、TASK-044のappend-only Timeline編集履歴とProject Manifest/ProjectSave整合性からcurrent EDIT_PERSISTENCE receiptをread-only投影し、空履歴、recovery、改ざん、stale Timeline、caller差替え、旧runtime leaseをfail-closedにしました。Audio/Privacy/Resource/Rightsのowner receipt、実Windows packaged render/output QA、公開、Release/Deployは引き続き別Gateです。

## Pre-host gates

- fresh main and previous-lock read-back: PASS
- target PR exact head and 11-file immutable scope: PASS
- target hosted Product/CI/Security checks: `8 / 9 PASS`
- only release-metadata check is failing for missing CHANGELOG: PASS
- exact two-file proposal and Registry JSON validation: PASS
- independent hosted checks, merge and post-main read-back: PENDING

This proposal creates no effective CHANGELOG mutation authority until its
hosting PR is merged and the exact main Registry state is read back.
