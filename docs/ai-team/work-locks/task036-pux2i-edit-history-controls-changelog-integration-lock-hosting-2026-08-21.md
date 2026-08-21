# TASK-036 P-UX-2I CHANGELOG Integration Lock Hosting

Date: 2026-08-21

Unit: `TASK-036/P-UX-2I-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_AUTONOMY_AND_ALL_GREEN_MERGE_DIRECTIVE_20260821`

Status: `INDEPENDENT_REVIEW_ACCEPTED / COMMIT_READY / PENDING_LOCK_HOST_PR`

## Scope

This exact two-file governance transaction proposes one shared
`CHANGELOG.md` integration effect required by the hosted release-metadata
check for target PR `#257`. It changes no Product implementation, Timeline
schema, runtime, version, Tag, Release, Provider, native, Export or audio
state.

- fresh base main: `b130c778f266dc4b2692285ed46710b77711039b`
- Registry revision: `40 -> 41`
- previous TASK-041 R1A shared lock: `HOSTED_CLOSED_RELEASED`
- nonclosed integration locks before proposal: `0`
- open PR shared-path overlap: `0`; only target PR `#257` is open and it
  changes neither `CHANGELOG.md` nor the Registry
- target branch: `codex/task-036-pux2i-edit-history-controls`
- expected target head: `0ff1597458adafa3e41fc198305d4be33d2de25a`
- immutable target paths: `9`
- target hosted checks before lock: `8 / 9 PASS`; only
  `changelog-and-version` requires `CHANGELOG.md`
- target CI run: `32489329643` (`6 / 6 PASS`)
- target Security run: `32489329684` (`2 / 2 PASS`)
- target release-metadata run: `32489329852` (expected missing-CHANGELOG
  failure only)
- allowed shared effect after hosting merge: add the exact approved bullet
  below under `[Unreleased]`
- denied: target implementation/Evidence rewrite, workflow weakening,
  Timeline schema, Provider/native/audio/Resolve/Export execution,
  version/Tag/Release/Deploy

## Approved CHANGELOG bullet

> - TASK-036 P-UX-2Iとして、既存TASK-044のMOVE/TRIM/UNDO/REDOをV6.1.1 Edit画面へ接続し、Project履歴SHAのprepare/apply CAS、Timeline edit履歴とのcross-store exact binding、重複command ID拒否、Human確認拒否時cancel、runtime leaseを追加しました。Provider/Audio/Resolve/Export/公開/Release/Deployは引き続き別Gateです。

## Pre-host gates

- fresh main and previous-lock read-back: PASS
- target PR exact head and 9-file immutable scope: PASS
- target hosted Product/CI/Security checks: `8 / 9 PASS`
- only release-metadata check is failing for missing CHANGELOG: PASS
- exact two-file proposal and Registry JSON validation: PASS
- independent Tester/Judge: PASS (`C/H/M/L = 0/0/0/0`)
- hosted checks, merge and post-main read-back: PENDING

This proposal creates no effective CHANGELOG mutation authority until its
hosting PR is merged and the exact main Registry state is read back.
