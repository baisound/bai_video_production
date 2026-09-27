# SRTから本人声のMaster WAVを作る

このページはエンドユーザー向けです。現在の最短ローカル経路は、WSLで起動済みの
GPT-SoVITS APIとOwner選択済みV2_FRESH e4/e15 Modelを使います。従来のQwen3-TTS経路も
`-Backend qwen3`で残しています。開発者がインストーラーを再構築する手順は
[開発者向けbuild guide](../windows/BUILDING-OWNER-VOICE-RUNTIME-INSTALLER.md)へ分けています。

## GPT-SoVITS利用前提

既定経路では、WSL上のGPT-SoVITS `api_v2.py`、Owner選択済みV2_FRESH e4 SoVITS +
e15 GPT、ffmpeg、BVPをimportできるWindows Pythonが必要です。APIは外部公開せず
`127.0.0.1:9880`で起動します。このコマンドはserverやModelをインストールせず、学習もしません。

## Qwen3互換経路を使う場合の初回インストール

1. GitHub Releaseから`bai-owner-voice-runtime-0.24.3-windows-x64-setup.exe`を取得します。
2. インストーラーを起動します。
3. 本人声データの保存先を選びます。12 GB以上の空きが必要です。
4. 完了まで待ちます。初回は専用Python、CUDA版PyTorch、Qwen3-TTS、ffmpeg、約2.51 GBの
   Qwen Modelを準備して実際にModelをload確認するため、回線とPCによって時間がかかります。
5. 「完了」が出たら`-Backend qwen3`の準備済みです。途中で失敗した場合は完了扱いになりません。同じ
   インストーラーをもう一度実行して修復できます。

インストーラーはsystem PythonやPATHを変更しません。専用環境とModelは選択したデータ
フォルダーで管理され、アンインストールしても録音、Dataset、Model、生成WAVは削除されません。

## WAV生成コマンド

以前に作った`voice-dataset`のmanifestを使う場合は、PowerShellで次を実行します。

```powershell
& "$env:LOCALAPPDATA\BAI Video Production\owner-voice\make-owner-voice-wav.ps1" `
  -Srt "E:\BAI_AI\private\owner-voice\input.srt" `
  -ReferenceManifest "E:\BAI_AI\private\owner-voice\voice-dataset\dataset\reference-manifest.json" `
  -Backend gpt-sovits `
  -GptWeights "/home/<user>/BAI_AI/task097_gptsovits/GPT-SoVITS/GPT_weights_v2Pro/BAISOUND_TASK097_V2_FRESH-e15.ckpt" `
  -SoVitsWeights "/home/<user>/BAI_AI/task097_gptsovits/GPT-SoVITS/SoVITS_weights_v2Pro/BAISOUND_TASK097_V2_FRESH_e4_s192.pth" `
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

GPT-SoVITS APIはloopbackの`http://127.0.0.1:9880`で先に起動してください。コマンドは生成前に
Owner選択済みweightをAPIへ明示設定します。`-GptWeights`と`-SoVitsWeights`はWSL内の実パスを
指定するか、同じ値を`BAISOUND_GPT_SOVITS_GPT_WEIGHTS`と
`BAISOUND_GPT_SOVITS_SOVITS_WEIGHTS`環境変数に設定します。外部hostのURLは受け付けません。

Cueごとに表情を変える場合は、次のようなJSONを`-CueOverrides`へ渡します。manifestには各
`style_id`/`emotion_id`に対応する、本人が承認済みの参照WAVと一致Transcriptが必要です。

```json
{
  "cue-000001": {"style_id": "NORMAL", "emotion_id": "NORMAL"},
  "cue-000002": {"style_id": "SPORTS_COMMENTARY", "emotion_id": "EXCITED", "speaking_rate": 1.1}
}
```

```powershell
& "$env:LOCALAPPDATA\BAI Video Production\owner-voice\make-owner-voice-wav.ps1" `
  -Srt "E:\BAI_AI\private\owner-voice\input.srt" `
  -ReferenceManifest "E:\BAI_AI\private\owner-voice\voice-dataset\dataset\reference-manifest.json" `
  -CueOverrides "E:\BAI_AI\private\owner-voice\cue-overrides.json" `
  -ConfirmOwnerApproved
```

このコマンドの場所はアプリのインストール先を変更しても同じです。GPT-SoVITS経路では
`-ModelRoot`は不要です。`-JobsRoot`はmanifestから安全な既定位置を選べます。
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

- 「server_contract」がfalse: WSLのGPT-SoVITS `api_v2.py`をloopback:9880で起動します。
- 「selected weights」が拒否された: `-GptWeights`/`-SoVitsWeights`のWSLパスを確認します。
- 「runtime設定が未完了」: Qwen3を選んだ場合は0.24.3インストーラーを再実行します。
- 「GPU準備が完了していない」: `nvidia-smi`でNVIDIA GPU/driverを確認し、修復します。
- 「見本WAVの確認に失敗」: 3～15秒、48 kHz、mono、PCM 24-bitへ直します。
- 「字幕枠へ収まらない」: SRTの表示時間を長くするか文章を短くします。音声は途中で切りません。
- receipt: 選択データフォルダーの`receipts\owner-voice-0.24.3`を確認します。

## 学習との違い

既定のGPT-SoVITS経路は、既に完了した本人専用Model学習からOwnerが選択したV2_FRESH e4
SoVITS + e15 GPTを使います。このコマンド自体は学習を行いません。Qwen3-TTS 0.6B Baseの
zero-shot経路は互換用の別backendです。
