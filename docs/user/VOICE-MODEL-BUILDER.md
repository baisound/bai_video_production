# BAI Voice Model Builder — beginner guide / 初心者向けガイド

**日本語** | [English](#english-guide)

## このアプリは何ですか

BAI Voice Model Builderは、OBSで録音した学習用WAVから、将来のDataset確認、Model学習、品質評価、style別音声、一本の自然なMaster WAVまでの流れを迷わず進めるためのWindowsクライアントです。

現在の`0.1.0-dev.1-installer.2`は、**12工程を確認し、既存のworkflow JSONを実行せず検証・表示するTechnical Preview**です。インストールしても、録音を読み取らず、Modelをdownloadせず、学習・音声生成・公開を開始しません。

## インストール前の確認

1. Windows 10または11の64-bit環境を使います。
2. Releaseの`bai-voice-model-builder-0.1.0-dev.1-installer.2-windows-x64-setup.exe`と`SHA256SUMS`を同じ場所へ保存します。
3. PowerShellで次を実行し、表示されたSHA-256がReleaseの値と一致することを確認します。

```powershell
Get-FileHash -Algorithm SHA256 .\bai-voice-model-builder-0.1.0-dev.1-installer.2-windows-x64-setup.exe
```

一致しない場合は実行しないでください。開発版インストーラーは未署名のため、Windowsが警告する場合があります。出所とSHA-256を確認できない場合は中止してください。

## インストールする

1. インストーラーをダブルクリックします。
2. 表示言語を選び、内容を読みながら進めます。
3. 通常は既定のユーザー専用フォルダーを使います。管理者権限は不要です。
4. 必要ならデスクトップショートカットを選びます。
5. 完了画面が出たら閉じます。インストーラーがアプリを勝手に起動することはありません。

インストール中にModel取得、GPU処理、録音、学習、音声生成、外部送信は行いません。

## 起動して確認する

1. スタートメニューから「BAI Voice Model Builder」を開きます。
2. 「この画面だけでは学習・音声生成を開始しません」と表示されることを確認します。
3. 12工程を上から確認します。最初は「録音を選ぶ」が次の作業です。
4. 既存の`VerticalSliceWorkflowRevision` JSONを確認する場合だけ「workflow JSONを選ぶ」を押します。最大1 MiBのUTF-8 JSONを読み、型・revision・digest・effect flagを検証して表示します。
5. 不正・改変・未対応のJSONはfail closedで拒否し、元ファイルを書き換えません。選択したpathやJSON本文を公開metadataへ保存しません。
6. JSONを選ばなければ合成Demoのままです。Owner音声やprivateな保存先を指定する必要はありません。
7. 英語表示を確認する場合は、コマンドプロンプトでインストール先のEXEへ`--locale en`を付けて起動します。

## 将来の完成形

今後の各Gateが実装・実機承認されると、同じ案内の中で次を安全に行える構成になります。

- OBS録音を選び、48 kHz・24-bit mono、clip、noise、GAINを確認する。
- Ownerが学習対象を確認し、Datasetを確定する。
- 12 GB環境で利用できる学習recipeとresourceを確認する。
- Owner確認後だけ学習を開始し、停止・checkpoint・復旧状況を監視する。
- Model候補を別に評価・承認する。
- normal、shout、whisper等のstyle音声を作り、自然につないだMaster WAVを確認する。
- 承認済みMaster WAVだけをナレーション工程へ渡す。

前工程の成功が後工程の許可を自動で意味することはありません。Owner音声が必要になるのは、合成Demoではなく正式な録音Acceptance Gateです。その時点でアプリが明示し、勝手に録音は始めません。

## アンインストールとデータ

Windowsの「インストールされているアプリ」からBAI Voice Model Builderをアンインストールできます。アプリ本体とショートカットは削除されますが、録音、Dataset、checkpoint、Model、生成WAVは自動削除しません。現在の合成Demoはそれらのデータを作成しません。

## 困ったとき

- SHA-256が一致しない: 実行せず、Releaseから再取得します。
- 内容の異なる既存ファイルで停止する: 上書きせず停止する安全動作です。既存版をアンインストールしてから再確認します。
- 画面が出ない: タスクマネージャーで重複起動を確認し、残っていれば終了後に一度だけ再試行します。
- 学習や音声生成ができない: 現版は表示専用です。未実装機能を成功として表示しません。

## 開発者向け: `E:\BAI_AI`でインストーラーをbuildする

次は一例です。既存PATHは変更せず、すべて絶対pathで実行します。

```powershell
E:\BAI_AI\runtimes\Python31314\python.exe -m venv E:\BAI_AI\envs\task046-voice-model-builder-package-py31314
E:\BAI_AI\envs\task046-voice-model-builder-package-py31314\Scripts\python.exe -m pip install "jsonschema>=4.20,<5" pyinstaller==6.22.0

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows\build-task046-voice-model-builder-installer.ps1 `
  -PythonExe E:\BAI_AI\envs\task046-voice-model-builder-package-py31314\Scripts\python.exe `
  -InnoCompiler E:\BAI_AI\runtimes\InnoSetup\7.1.0\ISCC.exe `
  -WorkRoot E:\BAI_AI\build\task046-voice-model-builder-installer `
  -OutputDirectory E:\BAI_AI\artifacts\task046-voice-model-builder-installer
```

build scriptはPython、project runtime dependencyのjsonschema、PyInstaller 6.22.0、Inno Setup compilerのidentityを検証し、EXE・guide・license・manifestのSHA-256をInstallerへ固定します。出力をReleaseへ公開する行為はbuildとは別のGateです。

Installerにはprojectの`LICENSE.md`に加え、実際にbundleしたCPython、Tcl/Tk、PyInstaller、jsonschema、attrs、jsonschema-specifications、referencing、rpds-pyの完全なlicense本文を`THIRD-PARTY-NOTICES.txt`として同梱します。build環境でlicense fileが欠落・増減した場合はfail closedで停止します。

---

<a id="english-guide"></a>

## English guide

### What this app is

BAI Voice Model Builder is the future Windows client for moving from OBS training WAV recordings through Dataset review, model training, evaluation, style clips, and one naturally joined Master WAV.

Version `0.1.0-dev.1-installer.2` is a **Technical Preview that shows the twelve-step flow and validates an existing workflow JSON without executing it**. Installing it does not read recordings, download a model, start training, generate audio, or publish anything.

### Before installation

1. Use 64-bit Windows 10 or 11.
2. Download the installer and `SHA256SUMS` from the same Release.
3. Run `Get-FileHash -Algorithm SHA256` and compare the result with the Release value.
4. Stop if the values differ. This development installer is unsigned, so Windows may warn you; continue only when the source and digest are verified.

### Install and open

1. Double-click the installer and choose a language.
2. Keep the default per-user folder unless you have a reason to change it. Administrator rights are not required.
3. Optionally create a desktop shortcut.
4. Close the completion page. Installation never launches the app automatically.
5. Open “BAI Voice Model Builder” from the Start menu.
6. Confirm that the window says it does not start training or audio generation.
7. Read the twelve steps from top to bottom. The synthetic demo begins at “Choose recordings”.
8. To inspect an existing `VerticalSliceWorkflowRevision`, choose “Choose workflow JSON”. The app accepts at most 1 MiB of strict UTF-8 JSON, validates its exact contract and digest, and never changes the selected file.
9. Invalid, tampered or unsupported input is rejected. The local path and JSON body are not copied to public metadata.

### Safety and future workflow

The completed product is intended to check OBS recording format, clipping, noise and gain; obtain Owner Dataset approval; admit a measured training recipe; start training only after a separate Owner gate; evaluate and approve a Model candidate; generate style clips; and review a naturally joined Master WAV. Each effect remains a separate gate. Owner voice is requested only at the formal real-recording acceptance stage, never by this synthetic demo.

### Uninstall and troubleshooting

Uninstall through Windows Installed apps. Application files and shortcuts are removed, while recordings, Datasets, checkpoints, Models and generated WAVs are never automatically deleted. If a digest differs, stop. If an unexpected existing file blocks installation, uninstall or reconcile the prior copy instead of forcing an overwrite. If the app does not appear, check for a duplicate process and retry once. Training and generation are not available in this display-only version.

### Build from source

Use the `E:\BAI_AI` commands in the Japanese build section above. They intentionally use absolute executable paths and do not modify PATH. The build creates a local candidate; publishing it as a GitHub Release is a separate operation.

The installer also includes `THIRD-PARTY-NOTICES.txt`, generated from the exact CPython, Tcl/Tk, PyInstaller, jsonschema, attrs, jsonschema-specifications, referencing and rpds-py license files used by the build. Missing or ambiguous license input stops the build.
