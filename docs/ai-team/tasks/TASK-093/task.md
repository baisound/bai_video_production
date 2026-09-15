# TASK-093 — Owner Voice Runtime Installer and v0.24.2 Release

- Status: `COMPLETED`
- Governance: `DEV-3 HIGH ASSURANCE`
- Owner authority: 2026-09-16に「インストーラーだけで保存先、Qwen用Python環境、Model準備、検証、SRTから本人声Master WAV生成まで完結させ、利用者向け文書を更新してReleaseへ含める」と明示承認を受領
- Base: TASK-092 / v0.24.1 closure。TASK-046とTASK-092の履歴は変更せず、本要件を新Taskとして扱う

## Responsibility boundary

本Taskは、承認済みの本人参照WAVを使用するQwen3-TTS 0.6B Base zero-shot voice cloneの
Windows runtime構築とSRTからMaster WAVを生成する入口を所有する。公式0.6B fine-tuning
recipeの未解決不整合、実Dataset学習、Model昇格、公開承認は所有しない。

## Atomic Units

### R1 — Installer-managed runtime and data root

- per-user installerでOwner Voice専用データrootを選択・安全検証・永続化
- 署名とSHA-256を固定したPython 3.12 runtimeを専用rootへ導入
- pinned CUDA PyTorch、Qwen-TTS、BAI Video Production wheel、ローカルffmpegを隔離導入
- Qwen Model exact revisionを取得またはexact file digestで既存Modelを再利用
- package、CUDA、ffmpeg、Model主要file、Model load-onlyを検証しreceiptを保存
- repairはexact identityを再検証し、uninstallは録音・Dataset・Model・生成WAVを削除しない

### R2 — Installed one-command SRT workflow

- installed runtime configを`make-owner-voice-wav.ps1`が自動検出
- SRT、参照音声、Owner確認はPowerShell引数で明示し、file pickerや対話式質問を設けない
- app install先に依存しない固定per-user pathから生成commandを実行可能
- source checkout、手動Python、手動Model path、system PATHをエンドユーザーに要求しない
- private audioをRelease、Git、外部サービスへ送信しない

### R3 — Audience-separated documentation

- エンドユーザー向けガイドはinstallerと生成操作だけに限定
- 開発者向けガイドへbuild、dependency pins、再構築、verification、Release手順を分離
- READMEとWindows build indexから適切なguideへ到達可能

### R4 — v0.24.2 release

- focused、integration、installer static/native verification、targeted regression
- Critical/High finding 0
- PR checks all green、merge、annotated tag、exact-tag build
- Owner Voice installer、wheel、sdist、Windows assets、SHA256SUMSをReleaseへ公開しread-back

## Allowed files

- `packaging/task093_owner_voice_runtime_installer.iss`
- `tools/windows/install-owner-voice-runtime.ps1`
- `tools/windows/make-owner-voice-wav.ps1`
- `tools/windows/build-task093-owner-voice-runtime-installer.ps1`
- `tools/windows/test-task093-owner-voice-runtime-installer.ps1`
- `src/ai_video_production/task014_srt_owner_voice_wav.py`
- exact TASK-093 tests
- `docs/user/SRT-OWNER-VOICE-WAV.md`
- `docs/windows/BUILDING-OWNER-VOICE-RUNTIME-INSTALLER.md`
- README/build index/release metadata/version/current-state/TASK-093 Evidence

## Prohibited effects

- no direct push to `main`, force push or tag move
- no private Owner audio read during installer/build verification
- no real voice generation or publication without separate input/quality approval
- no fine-tuning/training claim or automatic Model approval
- no global PATH mutation, system Python replacement or administrator-only install
- no removal of Owner recordings, Dataset, Model, checkpoint or generated WAV on uninstall
- no task-owned drive-root/direct-child output

## Completion

Completion requires exact source/PR/main/tag/Release identities, all required checks green,
an installer-managed fresh runtime or a truthful blocked receipt, successful config read-back,
exact Model revision/file validation, installed helper routing, separate end-user/developer docs,
remote asset digest read-back and durable external Evidence.

Completed on 2026-09-16 by PR #555, exact main/tag commit
`455c94c586b1c3fb72740b71cea7bd05a9a855fe`, Release workflow `35018509125`,
all 16 published asset identity read-back and durable external Evidence. Actual Owner voice
generation and listening-quality acceptance were not executed by the Release Unit.
