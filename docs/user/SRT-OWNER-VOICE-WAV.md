# SRTから本人声のMaster WAVを生成する手順

このページは、SRTの各字幕を本人の参照音声でローカル合成し、字幕時刻に合わせた
48 kHz・mono・PCM 24-bitのMaster WAVへまとめる実行手順です。

現在の入口はBAI Video Production本体EXEの画面ではなく、対話式PowerShell helperです。
helperの内部でPython module CLIを実行します。
音声Modelの学習は必須ではありません。承認済みの本人参照WAVとその正確な書き起こしを使う
Qwen3-TTS Base Modelのzero-shot voice cloneで生成できます。

## いちばん簡単な方法（初めての方はこちら）

用意するものは次の3つだけです。

1. 読ませたい字幕のSRTファイル
2. あなたが3～15秒話した、48 kHz・mono・PCM 24-bitの見本WAV
3. 見本WAVで話した内容を一字一句そのまま書いた文章

PowerShellを開き、BAI VIDEO PRODUCTIONのフォルダーで次の1行を実行します。

```powershell
.\tools\windows\make-owner-voice-wav.ps1
```

あとは画面の質問に答えます。SRTとWAVは、エクスプローラーからPowerShellの画面へ
ドラッグするとパスを入力できます。最後の確認で`YES`と入力すると生成が始まります。

すでに`run-owner-voice-recording-prepare.ps1`で`voice-dataset`を作っている場合は、その
フォルダーを質問画面へドラッグしてください。内部の承認済み3～15秒音声と書き起こしを
自動で使用するため、見本WAVと文章をもう一度指定する必要はありません。

質問を省略して1行で指定する場合は次の形です。

```powershell
.\tools\windows\make-owner-voice-wav.ps1 -Srt ".\input.srt" -ReferenceManifest ".\voice-dataset\dataset\reference-manifest.json"
```

スクリプト自身の使い方をPowerShellで表示することもできます。

```powershell
Get-Help .\tools\windows\make-owner-voice-wav.ps1 -Full
```

### `voice-dataset`はどこに作られるか

`run-owner-voice-recording-prepare.ps1`の`-OutputDir`で指定した場所です。固定のEドライブ
保存先はありません。たとえば、PowerShellの現在位置が`E:\BAI_AI`のときに
`-OutputDir ".\voice-dataset"`を指定すると、実際の保存先は
`E:\BAI_AI\voice-dataset`です。

現在のBAI Video Production、Voice Model Builder、OBS Voice Captureの各インストーラーは、
Owner Voice用の共通データルートを選択・保存しません。Voice Model Builderの現行版は
工程表示用Technical Previewであり、インストール先はアプリ本体の場所です。OBS installerで
選ぶフォルダーもOBS本体の場所であり、録音やDatasetの保存先ではありません。

現在位置によって保存先が変わるのを避けるには、Ownerが承認した暗号化保存領域を絶対パスで
指定してください。たとえば、その領域が`E:\BAI_AI\private\owner-voice`として準備・承認済み
の場合だけ、次のように指定します。

```powershell
.\tools\windows\run-owner-voice-recording-prepare.ps1 `
  -Input "E:\BAI_AI\private\owner-voice\recording.wav" `
  -OutputDir "E:\BAI_AI\private\owner-voice\voice-dataset" `
  -StyleId "NORMAL" `
  -EmotionId "NORMAL" `
  -OverallTargetSeconds 7200 `
  -ApproveDerivedSegments `
  -AcceptAsrTranscripts
```

この録音準備コマンドはSRTからWAVを生成するコマンドではありません。長い録音を3～15秒の
参照音声へ分割し、`reference-manifest.json`を作る一度きりの準備です。SRTからMaster WAVを
作るときは、その後に`make-owner-voice-wav.ps1`を実行します。

`-RecordingPreflightReport`はこの録音準備スクリプトの引数ではありません。
`recording-preflight.json`は録音開始前に別の`run-owner-voice-recording-preflight.ps1`で
作る確認記録であり、すでに存在する`recording.wav`の分割処理には渡しません。

完了時に表示される`master-owner-voice.wav`が成果物です。JSON作成、ハッシュ計算、
事前チェック、字幕配置計画、作業フォルダー作成はスクリプトが自動で行います。
既存の`voice-dataset`を指定した場合、生成ジョブはその中の`master-wav-jobs`へ保存されます。

初回だけ、Qwen3-TTS用Python環境とModelの準備が必要です。`本人声生成用Python環境が
見つかりません`または`Modelが見つかりません`と表示された場合は、下記のセットアップを
先に行います。

## 手動で実行する場合

ここから下は、保存先や生成条件を自分で管理したい方向けの詳細手順です。

### 事前準備

- Windows 10/11、NVIDIA GPUと利用可能なCUDA環境
- Python 3.12の隔離環境
- `ffmpeg`がPATHから実行可能
- ローカルへ準備済みの`Qwen/Qwen3-TTS-12Hz-0.6B-Base`
- 3～15秒、48 kHz、mono、PCM 24-bitの本人参照WAV
- 参照WAVで実際に話している内容と完全に一致するUTF-8テキスト
- 入力SRT

ModelとPython依存の準備は、先に
[Qwen3-TTS 0.6B Baseセットアップ](QWEN3-TTS-06B-BASE-SETUP.md)を完了してください。
本人音声は外部サービスへアップロードせず、暗号化されたOwner管理領域で扱ってください。

### 1. 作業パスを設定する

次の例では、ドライブルート直下を使わず、既存のBAI VIDEO PRODUCTIONフォルダー配下に
実行単位の専用フォルダーを置きます。実際のパスへ置き換えてください。

```powershell
$Repo = 'C:\home\baisound\projects\bai-video-production'
$Python = 'C:\path\to\qwen3-tts-venv\Scripts\python.exe'
$ModelRoot = 'D:\BAI\BAI_VIDEO_PRODUCTION_20260914\models\Qwen3-TTS-12Hz-0.6B-Base'
$JobRoot = 'D:\BAI\BAI_VIDEO_PRODUCTION_20260914\owner-voice-jobs\job-001'
$Srt = Join-Path $JobRoot 'input.srt'
$RefWav = Join-Path $JobRoot 'private\owner-reference.wav'
$RefText = Join-Path $JobRoot 'private\owner-reference.txt'
$References = Join-Path $JobRoot 'private\references.json'
$Work = Join-Path $JobRoot 'work'
$Output = Join-Path $JobRoot 'output\master-owner-voice.wav'
$Report = Join-Path $JobRoot 'output\master-owner-voice.report.json'

New-Item -ItemType Directory -Path $Work, (Split-Path -Parent $Output) -Force | Out-Null
Set-Location $Repo
```

対象環境へBAI VIDEO PRODUCTIONをまだ導入していない場合だけ、同じ隔離Pythonで
Release wheelを入れるか、source checkoutから次を実行します。

```powershell
& $Python -m pip install -e .
```

### 2. 参照WAVの情報を確認する

```powershell
& $Python -c "from pathlib import Path; from ai_video_production.owner_voice_wav import read_pcm_wav_info; from ai_video_production.voice_reference_selector import sha256_file; p=Path(r'$RefWav'); i=read_pcm_wav_info(p, require_canonical=True); print('duration_samples=', i.sample_count); print('sha256=', sha256_file(p))"
```

`duration_samples`が144000～720000（3～15秒）であることを確認します。表示された
`duration_samples`と`sha256:`値を使い、`references.json`を次の形で作成します。

```json
{
  "candidates": [
    {
      "candidate_id": "OWNER_NORMAL_001",
      "wav_path": "D:\\BAI\\BAI_VIDEO_PRODUCTION_20260914\\owner-voice-jobs\\job-001\\private\\owner-reference.wav",
      "transcript_path": "D:\\BAI\\BAI_VIDEO_PRODUCTION_20260914\\owner-voice-jobs\\job-001\\private\\owner-reference.txt",
      "content_sha256": "sha256:ここを表示値へ置換",
      "duration_samples": 384000,
      "style_id": "NORMAL",
      "emotion_id": "NORMAL",
      "quality_pass": true,
      "owner_approved": true,
      "transcript_verified": true
    }
  ]
}
```

`true`は実際に確認した項目だけに設定します。参照文が音声と一致しない、権利・同意がない、
品質を確認していない場合は生成へ進めません。

### 3. 生成前チェックを行う

```powershell
& $Python -m ai_video_production.task014_srt_owner_voice_wav preflight `
  --model-root $ModelRoot `
  --reference-wav $RefWav `
  --reference-text $RefText `
  --output (Join-Path $JobRoot 'preflight.json')
```

終了コード0で、`preflight.json`の`state`が`READY`であることを確認します。
`READY_WITH_WARNING`はCUDA未確認、`BLOCKED`は必須要素不足です。

### 4. SRTの配置計画を確認する

```powershell
& $Python -m ai_video_production.task014_srt_owner_voice_wav plan `
  --srt $Srt `
  --output (Join-Path $JobRoot 'srt-plan.json')
```

字幕が重複していないこと、各字幕の開始・終了位置と文章が意図どおりであることを確認します。

### 5. 本人声Master WAVを生成する

```powershell
& $Python -m ai_video_production.task014_srt_owner_voice_wav render `
  --srt $Srt `
  --model-root $ModelRoot `
  --references $References `
  --work-dir $Work `
  --output $Output `
  --report $Report `
  --style NORMAL `
  --emotion NORMAL `
  --speaking-rate 1.0
```

各字幕は個別に生成され、長すぎる場合だけピッチを保つ`ffmpeg atempo`で最大1.35倍まで
短縮されます。それでも字幕枠へ収まらない音声は切断せず、処理全体が失敗します。字幕間は
無音で埋め、SRT終端までを1本のWAVにします。

### 6. 出力を検証する

```powershell
& $Python -c "from ai_video_production.owner_voice_wav import read_pcm_wav_info; print(read_pcm_wav_info(r'$Output', require_canonical=True))"
Get-FileHash -Algorithm SHA256 -LiteralPath $Output
Get-Content -Raw -LiteralPath $Report
```

最後に必ず本人が全編を試聴し、発音、声の類似性、不自然な継ぎ目、無音位置、字幕との同期を
確認してください。コマンド成功は聴感品質の承認を意味しません。問題があるCueはSRTの時間枠や
文章、参照音声を見直して再生成します。

## 現在の制約

- 本体EXEからのone-click操作はまだありません。
- 実行にはローカルQwen3-TTS/CUDA環境が必要です。
- 学習済み本人専用Modelは不要ですが、使用する場合のModel承認は別Gateです。
- 本人音声、生成WAV、参照文、作業CueはReleaseやGitへ追加しません。
- 自動生成された音声は、本人の試聴承認前に公開・配信へ使用しません。
