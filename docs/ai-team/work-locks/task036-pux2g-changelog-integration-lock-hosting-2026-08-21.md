# TASK-036 P-UX-2G CHANGELOG Integration Lock Hosting

Date: 2026-08-21

Unit: `TASK-036/P-UX-2G-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_AUTONOMY_AND_ALL_GREEN_MERGE_DIRECTIVE_20260821`

Status: `DRAFT_PR_READY / JUDGE_ACCEPTED / PENDING_LOCK_HOST_PR`

## Scope

This exact two-file governance transaction proposes one shared
`CHANGELOG.md` integration effect required by the hosted release-metadata
check for target PR `#218`. It changes no Product implementation, runtime,
version, Tag, Release, Provider, native or audio state.

- fresh base main: `36275dce542e898c8bf57435b5dd451ccb818270`
- Registry revision: `30 -> 31`
- previous TASK-014 shared lock: `HOSTED_CLOSED_RELEASED`
- open PR shared-path overlap: `0`
- target branch: `codex/task-036-pux2g-canonical-native-vertical`
- expected target head: `4f08fd84c4ec5ddf3ff0d270e29ec2e737d25b92`
- immutable target paths: `15`
- target hosted checks before lock: `8 / 9 PASS`; only
  `changelog-and-version` requires `CHANGELOG.md`
- allowed shared effect after hosting merge: add the exact approved bullet
  below under `[Unreleased]`
- denied: target implementation/Evidence rewrite, workflow weakening,
  Provider/native/audio execution, version/Tag/Release/Deploy

## Approved CHANGELOG bullet

> - TASK-036 P-UX-2Gとして、canonical Human GO済みQueueからLOCAL_FREE_AIのComfyUI画像生成を別Human確認で実行し、構造検証済みPNGを別確認でTASK-003 IMAGE Asset/TASK-037 Candidate（READY_FOR_AUDIT）へ採用するtrusted Shell/CLI縦断と、再起動・排他・no-replay recovery境界を追加しました。実Windows/Comfy Provider実行、Human ACCEPT/LOCK、公開、Export、Release/Deployは引き続き別Gateです。

## Pre-host gates

- fresh main and previous-lock read-back: PASS
- target PR exact head and 15-file immutable scope: PASS
- target hosted Product/CI/Security checks: `8 / 9 PASS`
- only release-metadata check is failing for missing CHANGELOG: PASS
- exact two-file proposal and Registry JSON validation: PASS
- existing OSS readiness contract: `12 PASS`
- independent Tester/Critic/Judge: PASS (`C/H/M/L = 0/0/0/0`)
- hosted checks, merge and post-main read-back: PENDING

This proposal creates no effective CHANGELOG mutation authority until its
hosting PR is merged and the exact main Registry state is read back.
