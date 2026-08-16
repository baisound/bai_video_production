# TASK-047 P-OBS dev10 Runtime Lock Hosting Evidence

## 結論

- Task Unit: `TASK-047/P-OBS-DEV10-UX-RUNTIME-LH0`
- Audit base: `main@79975f6eb5a93ccea324d14a4612d24c847e2189`
- Registry: revision `18 -> 19`
- Proposed Lock: `BVP-LOCK-TASK047-POBS-DEV10-UX-RUNTIME`
- Changed files: このEvidenceと`ACTIVE-WORK-LOCKS.json`のexact 2件
- Implementation、OBS操作、録音、Release effect: このLock-host commitには含めない

## Owner要求の固定

本Lockは、OBS 32.2.1を起動したまま録音前GAIN確認、録音開始、一時停止、再開、停止を行えるController、常時見える入力レベル、録音中・一時停止中表示、自由に選べる保存先、installer、日英初心者ガイド、検証済みpublic prerelease候補を対象にする。一時停止・再開は同一OBS process IDと同一`obs64.exe`を必須とし、別processへの暗黙継続を拒否する。

## Fresh audit

- `origin/main`: `79975f6eb5a93ccea324d14a4612d24c847e2189`
- Registry blob: `7fe3dbd3cb71613f6bb911c79fcb8c347207c97d`
- Active Lock: `BVP-LOCK-TASK046-PVS3B` exact 1
- Open PR: 0
- 提案Allowed pathsとactive Lockのoverlap: 0
- `CHANGELOG.md`、`.github/**`、Registry自身はimplementation Allowed Filesから除外

## Effect boundary

このLockはRepository内のレビュー可能なsource、Controller、package/installer、tests、guides、Evidenceだけを予約する。Owner音声の追加録音は短い実機Acceptance時にOwnerへ知らせる。Dataset adoption、Training、Production admission、物理GAIN・phantom・PAD・HPF変更、破壊削除、有料Cloud・Credentialは許可しない。

## Critic pass 1

- Finding: 起動中OBS再利用だけではPause/Resume中のprocess同一性を証明できない。
- Correction: ControllerのPause、Resume、Stopでexact PIDとexecutable pathを再検証し、receiptに`VERIFIED_SAME_PROCESS`または`NOT_EXERCISED`を記録するAcceptanceを追加。
- Finding: 既存release assetsだけではsource reviewが困難。
- Correction: `native/task047_obs_voice_capture/**`をreviewable source正本候補としてLockへ追加。

## Critic pass 2

- Active Lock/Open PR overlap: 0
- Shared Registry serialization: 本H0 exact 2 filesのみ
- Authority inflation: 0。実録音、Dataset、Training、ProductionをLock-host successへ昇格しない。
- Critical/High unresolved: 0/0

## Read-only Judge

- `LOCK_RECORD_READY_FOR_HOST`: PASS
- `PURE_RUNTIME_SOURCE_IMPLEMENTATION_READY_AFTER_HOST`: PASS_CONDITIONAL
- `RUNNING_OBS_GAIN_PAUSE_RESUME_ACCEPTANCE`: PROBE_REQUIRED_ON_NEW_BUILD
- `PRODUCTION_RECORDING_ADMISSION`: BLOCKED
- `LOCK_HOST_NOW`: Owner autonomous TASK-047 directiveの範囲でDraft PRまで可。mergeはexact hosted checksとfresh read-back後のみ。
