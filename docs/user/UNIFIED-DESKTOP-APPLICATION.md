# BAI Video Production は最終的に1つの統合アプリです

BAI Video Productionの最終形は、機能ごとに別々のツールを起動する製品ではありません。

ユーザーは **BAI Video Production.exe** を起動し、同じProjectの中で次の機能を横断して使います。

- Media / Asset
- Edit / Cut Candidate
- Subtitle / FasterWhisper
- Audio / BGM / SE / Narration
- Generative AI
- Review / QA
- Export
- DaVinci Resolve連携
- Premiere Pro連携
- After Effects連携

現在存在するCLIやlocalhost Web UIは、開発・単体検証・診断のための内部Interfaceです。

最終ユーザーにPowerShell、localhost URL、worker processの手動管理を通常操作として要求しません。

内部では複数ServiceやWorkerが動作しても構いませんが、起動・終了・状態・エラー・設定はBAI Video Productionの統合Desktop Shellから扱います。

## 開発中の表示

内部機能が完成していても統合GUIへ未接続の場合は、最終完成とは区別します。

- `BACKEND_CAPABILITY_ONLY`
- `INTEGRATION_DESIGNED`
- `SHELL_INTEGRATED`
- `NATIVE_VALIDATED`

この区別により、「機能は存在するがユーザーが使いにくい」状態を完成扱いしません。
