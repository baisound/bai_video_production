# TASK-092 — v0.24.1 Windows Installer Remediation

- Status: `OWNER_AUTHORIZED_IMPLEMENTATION_AND_RELEASE`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Owner authority: 2026-09-16に、v0.24.0 ReleaseでTraining Studio／Trivia Editorの個別インストーラーが欠落している指摘、OBS installer runtime errorの提示、SRTから本人声WAVを作る別リンク手順の作成依頼を受領
- Base: TASK-091のv0.24.0 release closure。TASK-091の履歴は変更せず、本補正を新Taskとして扱う

## Atomic Units

### R1 — DbD utility installers

- `BAI DbD Training Studio.exe` one-dir payload用per-user installer
- `BAI DbD Trivia Editor.exe` one-dir payload用per-user installer
- fresh contained build output、payload tree SHA-256、別AppId、bilingual UI、uninstaller

### R2 — OBS installer.2 remediation

- OBS rootと`bin\64bit`直指定を同一canonical rootへ正規化
- `FmtMessage`のopen-array引数を修正し、無効入力でRuntime `Type Mismatch`を発生させない
- 実機で確認したOBS 32.2.2を対応Versionへ追加
- installer.2を再buildし、release asset digestを更新

### R3 — SRT Owner Voice WAV guide and renderer correction

- SRT→本人声Master WAVの独立した公開実行ガイド
- READMEから別リンクで到達可能
- Qwen3-TTS `generate_voice_clone`が返す生成sample rateを正しく使用

### R4 — v0.24.1 release

- hosted checks all green
- annotated `v0.24.1` tag
- exact-tag Windows main、Training Studio、Trivia Editor builds
- main／Training Studio／Trivia Editor installer compilation
- OBS installer.2、wheel、sdist、Windows ZIP、全installerと完全なSHA256SUMSをReleaseへ公開しread-back

## Allowed files

- release metadata and current-state files
- `packaging/task047_obs_voice_capture_installer.iss`
- `packaging/task092_dbd_utility_installer.iss`
- `packaging/release-assets/task047/**`
- `tools/windows/build-task047-obs-installer.ps1`
- `tools/windows/test-task047-obs-installer.ps1`
- `tools/windows/build-task092-dbd-utility-installers.ps1`
- `src/ai_video_production/task014_srt_owner_voice_wav.py`
- `docs/user/OBS-VOICE-CAPTURE-PLUGIN.md`
- `docs/user/SRT-OWNER-VOICE-WAV.md`
- exact focused tests and TASK-092 Evidence

## Prohibited effects

- no direct push to `main`, force push or tag move
- no real OBS mutation/load/recording without a separate explicit native gate
- no real installer execution without a separate explicit native gate
- no Owner voice/model inference or private audio access
- no Production Deploy or Production Activation
- no task-owned drive-root direct-child output

## Completion

Completion requires exact PR/main/tag/workflow/release identities, all hosted checks green,
all exact-tag Windows payload and installer builds successful, remote asset digest read-back,
and durable external Evidence. Installer execution and real OBS plugin load remain separate gates.
