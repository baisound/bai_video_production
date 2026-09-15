# SRTから本人声のMaster WAVを生成する手順

このページは、SRTの各字幕を本人の参照音声でローカル合成し、字幕時刻に合わせた
48 kHz・mono・PCM 24-bitのMaster WAVへまとめる実行手順です。

現在の入口はBAI Video Production本体EXEの画面ではなく、Python module CLIです。
音声Modelの学習は必須ではありません。承認済みの本人参照WAVとその正確な書き起こしを使う
Qwen3-TTS Base Modelのzero-shot voice cloneで生成できます。

## 事前準備

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

## 1. 作業パスを設定する

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

## 2. 参照WAVの情報を確認する

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

## 3. 生成前チェックを行う

```powershell
& $Python -m ai_video_production.task014_srt_owner_voice_wav preflight `
  --model-root $ModelRoot `
  --reference-wav $RefWav `
  --reference-text $RefText `
  --output (Join-Path $JobRoot 'preflight.json')
```

終了コード0で、`preflight.json`の`state`が`READY`であることを確認します。
`READY_WITH_WARNING`はCUDA未確認、`BLOCKED`は必須要素不足です。

## 4. SRTの配置計画を確認する

```powershell
& $Python -m ai_video_production.task014_srt_owner_voice_wav plan `
  --srt $Srt `
  --output (Join-Path $JobRoot 'srt-plan.json')
```

字幕が重複していないこと、各字幕の開始・終了位置と文章が意図どおりであることを確認します。

## 5. 本人声Master WAVを生成する

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

## 6. 出力を検証する

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
