# TASK-036 P-UX-2J CHANGELOG Integration Lock Hosting

Date: 2026-08-22

Unit: `TASK-036/P-UX-2J-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_AUTONOMY_AND_ALL_GREEN_MERGE_DIRECTIVE_20260821`

Status: `INDEPENDENT_REVIEW_ACCEPTED / COMMIT_READY / PENDING_LOCK_HOST_PR`

## Scope

This exact two-file governance transaction proposes one shared
`CHANGELOG.md` integration effect required by the hosted release-metadata
check for target PR `#260`. It changes no Product implementation, TASK-003
schema, runtime, version, Tag, Release, Provider, native, Export or audio
state.

- fresh base main: `f76f3be65f8613006ad99e49873489c148ada8b4`
- Registry revision: `42 -> 43`
- previous TASK-036 P-UX-2I shared lock: `HOSTED_CLOSED_RELEASED`
- nonclosed integration locks before proposal: `0`
- open PR shared-path overlap: `0`; only target PR `#260` is open and it
  changes neither `CHANGELOG.md` nor the Registry
- target branch: `codex/task-036-pux2j-media-ingest-controls`
- expected target head: `7854bfb32512ccad984a0a316e5da88f8f383b8a`
- immutable target paths: `10`
- target hosted checks before lock: `8 / 9 PASS`; only
  `changelog-and-version` requires `CHANGELOG.md`
- target CI run: `32497625539` (`6 / 6 PASS`)
- target Security run: `32497625591` (`2 / 2 PASS`)
- target release-metadata run: `32497625696` (expected missing-CHANGELOG
  failure only)
- allowed shared effect after hosting merge: add the exact approved bullet
  below under `[Unreleased]`
- denied: target implementation/Evidence rewrite, workflow weakening,
  TASK-003 schema, Provider/native/audio/Resolve/Export execution,
  version/Tag/Release/Deploy

## Approved CHANGELOG bullet

> - TASK-036 P-UX-2Jとして、HomeとFileの動画読込操作を既存TASK-003 Asset ingestへ接続し、Asset ID/SHAだけのWebView返却、並行picker/ingestのsingle-flight、stage drift拒否、launch close中のin-flight完了待ちとold bridge拒否を追加しました。Provider/Audio/Resolve/Export/公開/Release/Deployは引き続き別Gateです。

## Pre-host gates

- fresh main and previous-lock read-back: PASS
- target PR exact head and 10-file immutable scope: PASS
- target hosted Product/CI/Security checks: `8 / 9 PASS`
- only release-metadata check is failing for missing CHANGELOG: PASS
- exact two-file proposal and Registry JSON validation: PASS
- independent Tester/Critic: PASS (`C/H/M/L = 0/0/0/0`)
- hosted checks, merge and post-main read-back: PENDING

This proposal creates no effective CHANGELOG mutation authority until its
hosting PR is merged and the exact main Registry state is read back.
