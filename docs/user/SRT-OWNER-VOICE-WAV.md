# SRTから本人声のMaster WAVを作る

このページはエンドユーザー向けです。Python、PyTorch、Qwen、Model、ffmpegを手動で
準備する必要はありません。開発者がインストーラーを再構築する手順は
[開発者向けbuild guide](../windows/BUILDING-OWNER-VOICE-RUNTIME-INSTALLER.md)へ分けています。

## 最初の1回だけ: インストール

1. GitHub Releaseから`bai-owner-voice-runtime-0.24.2-windows-x64-setup.exe`を取得します。
2. インストーラーを起動します。
3. 本人声データの保存先を選びます。12 GB以上の空きが必要です。
4. 完了まで待ちます。初回は専用Python、CUDA版PyTorch、Qwen3-TTS、ffmpeg、約2.51 GBの
   Qwen Modelを準備して実際にModelをload確認するため、回線とPCによって時間がかかります。
5. 「完了」が出たら準備済みです。途中で失敗した場合は完了扱いになりません。同じ
   インストーラーをもう一度実行して修復できます。

インストーラーはsystem PythonやPATHを変更しません。専用環境とModelは選択したデータ
フォルダーで管理され、アンインストールしても録音、Dataset、Model、生成WAVは削除されません。

## WAV生成コマンド

以前に作った`voice-dataset`のmanifestを使う場合は、PowerShellで次を実行します。

```powershell
& "$env:LOCALAPPDATA\BAI Video Production\owner-voice\make-owner-voice-wav.ps1" `
  -Srt "E:\BAI_AI\private\owner-voice\input.srt" `
  -ReferenceManifest "E:\BAI_AI\private\owner-voice\voice-dataset\dataset\reference-manifest.json" `
  -ConfirmOwnerApproved
```

1本の見本WAVを直接指定する場合は次の形です。見本WAVは本人が3～15秒話した
48 kHz・mono・PCM 24-bit、`-ReferenceText`は実際の発話と一字一句同じ文章にします。

```powershell
& "$env:LOCALAPPDATA\BAI Video Production\owner-voice\make-owner-voice-wav.ps1" `
  -Srt "E:\BAI_AI\private\owner-voice\input.srt" `
  -ReferenceWav "E:\BAI_AI\private\owner-voice\owner-reference.wav" `
  -ReferenceText "この見本音声で実際に話している文章" `
  -ConfirmOwnerApproved
```

このコマンドの場所はアプリのインストール先を変更しても同じです。`-Python`、
`-ModelRoot`、`-JobsRoot`は指定不要で、インストーラーが検証済み設定を自動で読み取ります。
SRTや参照音声を選ぶ専用GUIも対話式質問もありません。`-ConfirmOwnerApproved`は、本人の声で
あること、使用権、見本音声の音質、文字起こしの一致を確認したという明示指定です。

## 生成物の場所

インストール時に選んだデータフォルダーの`jobs`に、実行ごとのフォルダーが作られます。

```text
<選択した本人声データフォルダー>\jobs\job-YYYYMMDD-HHMMSS-xxxxxxxx\
  output\master-owner-voice.wav
  output\master-owner-voice.report.json
  preflight.json
  srt-plan.json
```

成果物は`output\master-owner-voice.wav`です。48 kHz・mono・PCM 24-bitで、SRTの時刻に
合わせて1本にまとめられます。公開や動画利用の前に、本人が全編を試聴して発音、声、継ぎ目、
無音位置、字幕同期を確認してください。

## うまくいかない場合

- 「runtime設定が未完了」: 0.24.2インストーラーを再実行して修復します。
- 「GPU準備が完了していない」: `nvidia-smi`でNVIDIA GPU/driverを確認し、修復します。
- 「見本WAVの確認に失敗」: 3～15秒、48 kHz、mono、PCM 24-bitへ直します。
- 「字幕枠へ収まらない」: SRTの表示時間を長くするか文章を短くします。音声は途中で切りません。
- receipt: 選択データフォルダーの`receipts\owner-voice-0.24.2`を確認します。

## 学習との違い

今回の生成はQwen3-TTS 0.6B Baseのzero-shot voice cloneです。本人専用Modelのfine-tuningを
先に行う必要はありません。Voice Model Builderの学習工程は別機能で、現時点の公式0.6B
fine-tuning recipeには未解決制約があります。このインストーラーは学習成功を表示しません。
