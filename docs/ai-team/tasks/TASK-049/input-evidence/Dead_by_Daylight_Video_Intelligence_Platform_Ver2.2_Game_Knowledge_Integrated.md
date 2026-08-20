# Dead by Daylight Video Intelligence Platform
# 解説・実況自動生成AIシステム 詳細設計書 Ver.2.0

> **統合元文書**
>
> 1. `Demucs_Video_To_Vocals_Guide.md`
> 2. `dbd_vision_ai_specification.md`
>
> **版**: Ver.2.0
> **作成日**: 2026-08-17
> **対象環境**: Windows / NVIDIA GPUを中心とするローカル実行環境
> **対象ゲーム**: Dead by Daylight（以下、DbD）
> **文書種別**: 構想仕様・詳細設計・運用設計・品質ゲート統合版

---

## 0. 文書の目的とVer.2.0の位置付け

本書は、YouTubeライブ配信、過去の大会動画、ユーザー自身が所有または適切な権利を有するDbDプレイ動画などから、実況・解説・ゲーム状況・戦術判断を構造化し、最終的に「実況のない動画へ高品質な解説・実況を自動付与する」ためのローカル中心AIシステムを設計するものである。

Ver.1系では、以下の2つの文書が独立して存在していた。

- NVIDIA GPU対応Demucsを用いた動画からの音声分離・一括抽出ガイド
- YouTubeライブ配信の文字おこしと動画解析を用いたDbD特化型「解説・実況」自動生成AIシステム仕様書

Ver.2.0では両者を一つの設計へ統合し、**動画取得 → 音声抽出 → 音源分離 → VAD → 文字おこし → 話者識別 → 映像解析 → Canonical Game Event Timeline → RAG/LoRA → 解説生成 → TTS → 自動編集 → 品質検査 → Human Gate → 出力**までを単一の責任境界として定義する。

また、Ver.1系文書を「漏れは存在する」という前提で、以下3者による3周監査を実施した。

1. 優秀なエンジニア視点
2. 日常運用者視点
3. システムエンジニア視点

その結果、Ver.2.0では特に次を正式仕様へ昇格する。

- **Fail-closed実行**
- **Job Manifest / Resume / Retry**
- **入力メディアの事前検査**
- **Source Separation Provider抽象化**
- **VAD・ASR・Diarization・Speaker Alignment**
- **Canonical Game Event Timeline**
- **Confidence / UNKNOWN / NEEDS_REVIEW**
- **DbD Patch Profile / HUD Profile**
- **時系列State Machine**
- **RAGのPatch-aware retrievalとProvenance**
- **Gold Dataset / 回帰試験 / KPI**
- **Human Gate**
- **Rights Registry / Voice Consent Gate**
- **AI生成・改変コンテンツ開示管理**
- **再処理可能性と監査証跡**

---

## 0.1 設計原則

本システムの中心はLLMでも、RAGでも、OpenCVでもない。

**中心データモデルは `Canonical Game Event Timeline` とする。**

すべての音声・映像・実況・解説・HUD・RAG・学習データは、最終的に同一の試合ID・イベントID・時間軸へ正規化する。

```text
Source Video
   │
   ├── Audio Pipeline ──────────┐
   │                            │
   ├── Vision Pipeline ─────────┼──> Canonical Game Event Timeline
   │                            │
   └── Metadata / Rights ───────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
                   RAG                         Training Dataset
                     │                               │
                     └──────────── LLM / LoRA ──────┘
                                     │
                              Commentary Planner
                                     │
                                Fact Validator
                                     │
                                  TTS / Mix
                                     │
                                   Render
                                     │
                                Quality Gate
                                     │
                                 Human Gate
                                     │
                                   Output
```

---

## 0.2 非目標

Ver.2.0では以下を保証しない。

- Demucsの `vocals` stemが「実況者・解説者の声だけ」になること
- OpenCVの単一テンプレートだけで全DbDパッチ・全解像度・全HUD設定を永続的に判定できること
- 生成AIが戦術判断を常に正しく断定できること
- 他者の声を無許可でクローンして公開できること
- YouTube等の第三者サービス上の動画を、権利確認なしに学習用途へ取り込めること
- 「30〜50試合集めれば必ず実用精度になる」といった固定的な品質到達保証

これらはすべて、評価結果・権利情報・ゲームバージョン・モデルバージョン・Human Reviewを通じて制御する。

---

# 第1章：システム概要とハイブリッドアプローチの設計思想

## 1.1 開発ビジョン

本システムは、YouTubeライブ配信および過去の大規模な大会動画等から「プロの解説者・実況者の癖、思考パターン、ゲーム内戦術知識」を学習可能な形へ構造化し、解説・実況のついていないプレイ動画や一般の試合動画に対して、高密度かつ高クオリティな解説実況音声を自動付与する動画コンテンツ生成システムを構築することを目的とする。

視聴者が「なるほど、そんな深い読み合いがあったのか」と理解できるような、エンタメ性と深い論理性を兼ね備えたコンテンツ生成を、個人PC環境を中心としたローカルAI基盤で実現する。

ただしVer.2.0では、「特定の実在人物が実際に実況しているように偽装すること」を目的にしない。実況スタイル、戦術知識、テンポ、説明密度などを学習対象とし、音声については後述するVoice Consent Gateを必須とする。

## 1.2 RAG＋ファインチューニングの併用

ゼロからAIモデルをフルスクラッチ学習するのではなく、高度な言語能力を持つ既存ベースモデルを利用し、以下を併用する。

### ファインチューニング（LoRA等）

**目的**

- 実況・解説らしい会話のテンポ
- DbD固有語彙の自然な使用
- 解説と実況の役割分担
- 「盤面を見て何を先に言うか」という出力スタイル
- 感情表現や説明密度

**重要なVer.2.0変更**

特定人物の口癖を100%複製すること自体を成功条件にしない。学習元の権利条件に従い、必要に応じて人物固有スタイルを一般化・匿名化する。

### RAG（検索拡張生成）

**目的**

- 最新パッチ知識
- パーク・アドオン性能
- マップ・固有建築・ジャングルジム等の知識
- 過去の類似盤面における戦術見解
- 出典付き戦術根拠
- ハルシネーション低減

RAGは「何でもベクトル検索」ではなく、以下の順で検索する。

```text
1. Structured Filter
   - game_version
   - mode
   - killer
   - map
   - survivor_count
   - generator_remaining
   - event_type

2. Semantic Retrieval
   - 盤面の意味的類似
   - 戦術概念
   - 過去見解

3. Freshness / Compatibility Check
   - 現パッチで有効か
   - 廃止済みパーク効果を参照していないか

4. Source Provenance Check
   - 出典不明データを強い根拠にしない
```

## 1.3 「なるほど」を生むナレッジ構造

Ver.1の思想を継承し、「盤面」を主軸として複数視点を紐付ける。

- **実況データ**: 画面で起きた出来事をリアルタイムに補強する。
- **解説データ**: 裏にある心理、戦術、リスク、代替手段を言語化する。
- **複数見解**: 同一盤面に対する複数の合理的見解を保持する。

ただしVer.2.0では、見解は「唯一の正解」として保存しない。

```json
{
  "event_id": "EVT-000123",
  "viewpoints": [
    {
      "speaker_id": "COMMENTATOR_A",
      "claim": "深追いせずタゲチェンすべき",
      "confidence": 0.88,
      "source_id": "SRC-001"
    },
    {
      "speaker_id": "COMMENTATOR_B",
      "claim": "このキラーなら窓枠読み合いを継続する価値がある",
      "confidence": 0.79,
      "source_id": "SRC-002"
    }
  ]
}
```

---

# 第2章：全体アーキテクチャと責任境界

## 2.1 End-to-End Pipeline

```text
[Rights / Source Gate]
        ↓
[Input / Media Probe]
        ↓
[Audio Extraction]
        ↓
[Source Separation Provider]
        ↓
[VAD]
        ↓
[ASR: Faster-Whisper]
        ↓
[Diarization: pyannote等]
        ↓
[ASR ↔ Speaker Alignment]
        ↓
────────────────────────────────
        ↓
[Vision Tier 1: HUD/OCR]
        ↓
[Vision Tier 2: Temporal State Machine]
        ↓
[Vision Tier 3: Object / Scene Recognition]
        ↓
[Vision Tier 4: Selective Vision AI]
        ↓
────────────────────────────────
        ↓
[Canonical Game Event Timeline]
        ↓
[Validation / Human Correction]
        ↓
 ┌──────┴────────┐
 ↓               ↓
[RAG]       [Training Dataset]
 ↓               ↓
 └──────┬────────┘
        ↓
[LLM / LoRA]
        ↓
[Commentary Planner]
        ↓
[Fact Validator]
        ↓
[Timing Planner]
        ↓
[TTS]
        ↓
[Audio Mixer / Renderer]
        ↓
[Automated Quality Gate]
        ↓
[Human Gate]
        ↓
[Final Output]
```

## 2.2 Job状態

すべての処理対象はJobとして管理する。

```text
READY
  ↓
PREFLIGHT
  ↓
PROCESSING
  ├── SUCCESS
  ├── WARNING
  ├── FAILED
  ├── SKIPPED
  ├── NEEDS_REVIEW
  └── RETRY_PENDING
```

Jobは最終成果物だけでなく、各Stageの状態を持つ。

```json
{
  "job_id": "JOB-20260817-0001",
  "match_id": "MATCH-0001",
  "source_id": "SRC-0001",
  "status": "PROCESSING",
  "current_stage": "ASR",
  "stages": {
    "media_probe": "SUCCESS",
    "audio_extract": "SUCCESS",
    "source_separation": "SUCCESS",
    "vad": "SUCCESS",
    "asr": "PROCESSING",
    "diarization": "READY",
    "vision": "READY"
  }
}
```

## 2.3 Fail-closed原則

以下のいずれかが成立する場合は、成功扱いにしない。

- FFmpegの終了コードが0以外
- Demucs/分離Providerの終了コードが0以外
- 期待成果物が存在しない
- 成果物サイズが0
- ffprobe等で読み取り不能
- ASR結果が空かつ音声が存在する
- Canonical Eventの必須フィールド欠落
- 権利情報が `UNKNOWN/PROHIBITED`
- Voice Consent Gateが未通過
- Unknown Patchで高リスクの自動生成を行おうとした

失敗時は原因を記録し、中間ファイルは原則保持する。

---

# 第3章：Rights / Source Gate と入力データ管理

## 3.1 入力元の種類

入力ソースを以下に分類する。

```text
OWNED
LICENSED
PERMITTED
PUBLIC_REFERENCE_ONLY
UNKNOWN
PROHIBITED
```

`UNKNOWN` と `PROHIBITED` は学習データへ投入しない。

## 3.2 Rights Registry

```json
{
  "source_id": "SRC-0001",
  "source_type": "video",
  "owner": "example",
  "source_url": null,
  "license": "owned",
  "permission_evidence": "records/rights/SRC-0001.pdf",
  "training_allowed": true,
  "voice_training_allowed": false,
  "redistribution_allowed": false,
  "commercial_use_allowed": true,
  "expires_at": null,
  "review_status": "APPROVED"
}
```

## 3.3 YouTube等からの取得

Ver.1では `yt-dlp` 等で取得する手順を一般化していたが、Ver.2.0では**権利確認済みソースに限定**する。

ソース取得ツールは技術機能と権利判断を分離する。

```text
Downloader available
≠
Download authorized
```

取得前にRights Registryを確認し、承認されていないSource IDは取得処理へ進ませない。

---

# 第4章：Audio Ingestion Subsystem
# NVIDIA GPU対応Demucs・FFmpeg・VAD・ASR・話者識別

## 4.1 Demucsの概要

DemucsはMeta/Facebook Research由来の音源分離AIで、入力音源を主として以下のstemへ分離する。

- `vocals`
- `drums`
- `bass`
- `other`

Ver.1文書では `vocals` を「人間の声だけ」と表現していたが、Ver.2.0では次のように定義する。

> `vocals` は**音源分離モデルがvocal成分として推定したstem**であり、「実況者だけ」「解説者だけ」「人間会話だけ」を意味しない。

ゲーム内キャラクターボイス、叫び声、残留BGM、分離アーティファクト等が混入する可能性があるため、後段のVAD・Diarization・ASR・品質検査を必須とする。

### 4.1.1 Demucsの保守状態とProvider化

2026-08-17時点の公式Meta側Demucsリポジトリはarchive/read-onlyであり、元READMEでも積極保守されていない旨が示されている。

したがってVer.2.0ではDemucsをシステム全体へ直結せず、`SourceSeparationProvider` の一実装として扱う。

```python
class SourceSeparationProvider:
    def separate(self, input_audio: str, output_dir: str) -> dict:
        raise NotImplementedError
```

想定Provider例:

```text
demucs
future_local_provider
future_api_provider
bypass
```

これにより将来別方式へ変更しても、ASR以降の設計を変更しない。

## 4.2 導入アプローチ

### アプローチA：Google Colaboratory等

検証・PoC用途として利用できる。ローカル環境構築を必要としないため初期比較に向く。

### アプローチB：ローカルWindows / NVIDIA GPU

本番候補。大量動画処理、ローカル保持、再処理、監査証跡の観点からこちらを主系統とする。

## 4.3 Windows / NVIDIA GPU環境

### 4.3.1 Python

Ver.2.0ではシステムPythonへ直接インストールせず、必ず仮想環境を利用する。

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
```

### 4.3.2 CUDA対応PyTorch

CUDA/PyTorchは固定値を文書へ永久記載するのではなく、**互換性を確認したLock Profile**として管理する。

例:

```text
profiles/runtime/windows-nvidia.json
```

```json
{
  "python": "3.11.x",
  "torch": "validated-version",
  "cuda_runtime": "validated-runtime",
  "demucs": "pinned-version-or-commit",
  "faster_whisper": "pinned-version",
  "pyannote_audio": "pinned-version"
}
```

GPU認識確認:

```bat
python -c "import torch; print(torch.cuda.is_available())"
```

`True` だけを確認して終了せず、GPU名・VRAMも記録する。

```bat
python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 4.4 Demucs基本実行

CPU:

```bat
demucs -d cpu "input.wav"
```

GPU:

```bat
demucs -d cuda "input.wav"
```

`htdemucs_ft`:

```bat
demucs -d cuda -n htdemucs_ft "input.wav"
```

### 4.4.1 モデル選定ルール

Ver.1では `htdemucs_ft` を「最高音質」として常時指定していた。Ver.2.0では**固定採用しない**。

モデルは以下で比較する。

- 分離後ASRのWER/CER
- 話者識別DER
- 会話区間の欠落率
- 残留ゲーム音による誤認識率
- 処理時間
- VRAM
- 失敗率

「音楽分離として良い音」ではなく、**DbD実況学習データとして後段精度が高いモデル**を採用する。

---

## 4.5 FFmpegによる動画からWAV抽出

### 4.5.1 Ver.1コード（保持）

以下は元文書のコードを記録として保持する。

```bat
@echo off
cd /d "%~dp0"
for %%f in (*.mp4 *.mkv *.avi *.mov) do (
    ffmpeg -i "%%f" -vn -acodec pcm_s16le -ar 44100 "output\%%~nf.wav"
)
pause
```

### 4.5.2 Ver.2.0で追加する事前検査

FFmpegの前に `ffprobe` を利用して以下を確認する。

- 動画が読み取り可能か
- 音声streamが存在するか
- 複数音声streamがあるか
- duration
- codec
- sample rate
- channel count
- stream language / title metadata

例:

```bat
ffprobe -v error -show_streams -show_format -of json "input.mp4"
```

複数音声トラックが存在する場合、暗黙にstream 0を選ばず、`MediaSelectionPolicy` に従う。

```json
{
  "audio_stream_policy": "prefer_japanese_then_default",
  "fallback": "first_audio_stream",
  "manual_review_if_multiple_unlabeled": true
}
```

### 4.5.3 出力名衝突

次のような入力は同一 `sample.wav` を生成し得る。

```text
sample.mp4
sample.mkv
```

Ver.2.0では `source_id` または拡張子を含むJob Directoryへ出力する。

```text
work/
└── JOB-0001/
    └── audio/
        └── source.wav
```

---

## 4.6 Demucs一括分離

### 4.6.1 Ver.1コード（保持・既知不具合あり）

以下の元コードには、`vocals.wav` のパス文字列が破損している既知不具合がある。Ver.2.0では**実行禁止のLegacy Reference**として保持する。

```bat
@echo off
cd /d "%~dp0"

:: 処理元のWAVフォルダと、声だけの出力先フォルダを指定
set "INPUT_DIR=output"
set "TARGET_DIR=vocals_only"

:: outputフォルダ内のすべてのWAVファイルをループ処理
for %%f in ("%INPUT_DIR%\*.wav") do (
    echo ----------------------------------------
    echo 処理中: %%~nxf
    echo ----------------------------------------

    :: Demucsを実行（GPU使用、最高音質モデル）
    demucs -d cuda -n htdemucs_ft "%%f"

    :: 生成されたボーカルファイルを、指定のvocals_onlyフォルダへ同名でコピー
    copy "separated\htdemucs_ft\%%~nf
ocals.wav" "%TARGET_DIR%\%%~nf.wav"
)

echo すべての処理が完了しました！
pause
```

### 4.6.2 既知不具合

元文書内の以下相当箇所:

```text
separated\htdemucs_ft\%%~nf<control-character>ocals.wav
```

は、

```text
separated\htdemucs_ft\%%~nf\vocals.wav
```

であるべきであり、Ver.2.0では修正する。

### 4.6.3 Ver.2.0安全版 `separate_vocals_v2.bat`

```bat
@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "INPUT_DIR=output"
set "TARGET_DIR=vocals_only"
set "MODEL=htdemucs_ft"
set "FAILED=0"

if not exist "%INPUT_DIR%" (
    echo [ERROR] input directory not found: %INPUT_DIR%
    exit /b 10
)

if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

where demucs >nul 2>&1
if errorlevel 1 (
    echo [ERROR] demucs command not found.
    exit /b 11
)

for %%f in ("%INPUT_DIR%\*.wav") do (
    echo ========================================
    echo [INFO] Processing: %%~nxf

    demucs -d cuda -n "%MODEL%" "%%f"
    if errorlevel 1 (
        echo [ERROR] Demucs failed: %%~nxf
        set /a FAILED+=1
    ) else (
        set "VOCAL_PATH=separated\%MODEL%\%%~nf\vocals.wav"

        if not exist "!VOCAL_PATH!" (
            echo [ERROR] Expected output missing: !VOCAL_PATH!
            set /a FAILED+=1
        ) else (
            copy /y "!VOCAL_PATH!" "%TARGET_DIR%\%%~nf.wav" >nul
            if errorlevel 1 (
                echo [ERROR] Copy failed: %%~nxf
                set /a FAILED+=1
            ) else (
                echo [SUCCESS] %%~nxf
            )
        )
    )
)

if not "%FAILED%"=="0" (
    echo [FAILED] %FAILED% file(s) failed.
    exit /b 20
)

echo [SUCCESS] All files completed.
exit /b 0
```

---

## 4.7 動画→声抽出 完全統合バッチ

### 4.7.1 Ver.1コード（保持・実行非推奨）

```bat
@echo off
cd /d "%~dp0"

:: 自動作成するフォルダの名前を指定
set "TEMP_WAV_DIR=_temp_wav"
set "FINAL_OUT_DIR=vocals_only"

:: 必要なフォルダがなければ自動作成
if not exist "%TEMP_WAV_DIR%" mkdir "%TEMP_WAV_DIR%"
if not exist "%FINAL_OUT_DIR%" mkdir "%FINAL_OUT_DIR%"

:: 対象とする動画の拡張子を指定
for %%f in (*.mp4 *.mkv *.avi *.mov) do (
    echo ========================================
    echo  動画から音声を抽出中: %%~nxf
    echo ========================================

    :: ① 動画から一時的なWAVファイルを抽出
    ffmpeg -y -i "%%f" -vn -acodec pcm_s16le -ar 44100 "%TEMP_WAV_DIR%\%%~nf.wav" >nul 2>&1

    echo  Demucsで人の声（ボーカル）を抽出中...

    :: ② Demucsを実行（GPU使用、最高音質モデル）
    demucs -d cuda -n htdemucs_ft "%TEMP_WAV_DIR%\%%~nf.wav"

    :: ③ 抽出された声だけを、動画と同じ名前で「vocals_only」フォルダへ保存
    copy "separated\htdemucs_ft\%%~nf
ocals.wav" "%FINAL_OUT_DIR%\%%~nf.wav" >nul
)

:: 途中で作った一時的なWAVフォルダをクリーンアップ
echo ========================================
echo  一時ファイルを削除しています...
rmdir /s /q "%TEMP_WAV_DIR%"
if exist separated rmdir /s /q separated

echo すべての動画の処理が完了しました！
pause
```

### 4.7.2 Ver.1で発生し得る事故

- FFmpegのエラーを `>nul 2>&1` で捨てる
- FFmpeg失敗後もDemucsを実行する
- Demucs失敗後もcopyへ進む
- copy成功確認がない
- 全件成功確認前に一時フォルダを削除する
- 失敗件数を記録しない
- 最後に常に「完了」と表示し得る
- 再実行時のResume情報がない

### 4.7.3 Ver.2.0統合安全版

```bat
@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "WORK_ROOT=_work"
set "FINAL_OUT_DIR=vocals_only"
set "MODEL=htdemucs_ft"
set "LOG_DIR=logs"
set "FAILED=0"
set "SUCCESS=0"

if not exist "%WORK_ROOT%" mkdir "%WORK_ROOT%"
if not exist "%FINAL_OUT_DIR%" mkdir "%FINAL_OUT_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

where ffmpeg >nul 2>&1 || (
    echo [ERROR] ffmpeg not found.
    exit /b 10
)

where ffprobe >nul 2>&1 || (
    echo [ERROR] ffprobe not found.
    exit /b 11
)

where demucs >nul 2>&1 || (
    echo [ERROR] demucs not found.
    exit /b 12
)

for %%f in (*.mp4 *.mkv *.avi *.mov) do (
    set "BASENAME=%%~nf"
    set "JOB_DIR=%WORK_ROOT%\%%~nf_%%~xf"
    set "TEMP_WAV=!JOB_DIR!\source.wav"
    set "JOB_LOG=%LOG_DIR%\%%~nf_%%~xf.log"

    if not exist "!JOB_DIR!" mkdir "!JOB_DIR!"

    echo ======================================== >> "!JOB_LOG!"
    echo [START] %%f >> "!JOB_LOG!"

    ffprobe -v error -show_streams -show_format -of json "%%f" > "!JOB_DIR!\probe.json" 2>> "!JOB_LOG!"
    if errorlevel 1 (
        echo [ERROR] ffprobe failed: %%f
        echo [ERROR] ffprobe failed >> "!JOB_LOG!"
        set /a FAILED+=1
    ) else (
        ffmpeg -y -i "%%f" -map 0:a:0 -vn -acodec pcm_s16le -ar 44100 "!TEMP_WAV!" >> "!JOB_LOG!" 2>&1

        if errorlevel 1 (
            echo [ERROR] ffmpeg failed: %%f
            echo [ERROR] ffmpeg failed >> "!JOB_LOG!"
            set /a FAILED+=1
        ) else if not exist "!TEMP_WAV!" (
            echo [ERROR] WAV missing: %%f
            echo [ERROR] WAV missing >> "!JOB_LOG!"
            set /a FAILED+=1
        ) else (
            demucs -d cuda -n "%MODEL%" -o "!JOB_DIR!\separated" "!TEMP_WAV!" >> "!JOB_LOG!" 2>&1

            if errorlevel 1 (
                echo [ERROR] Demucs failed: %%f
                echo [ERROR] Demucs failed >> "!JOB_LOG!"
                set /a FAILED+=1
            ) else (
                set "VOCAL=!JOB_DIR!\separated\%MODEL%\source\vocals.wav"

                if not exist "!VOCAL!" (
                    echo [ERROR] vocals.wav missing: %%f
                    echo [ERROR] vocals.wav missing >> "!JOB_LOG!"
                    set /a FAILED+=1
                ) else (
                    copy /y "!VOCAL!" "%FINAL_OUT_DIR%\%%~nf.wav" >nul

                    if errorlevel 1 (
                        echo [ERROR] final copy failed: %%f
                        echo [ERROR] final copy failed >> "!JOB_LOG!"
                        set /a FAILED+=1
                    ) else (
                        echo [SUCCESS] %%f
                        echo [SUCCESS] completed >> "!JOB_LOG!"
                        set /a SUCCESS+=1

                        rem 成果物検証PASS後だけ、このJobの一時データを削除してよい。
                        rem 初期運用では監査のため保持を推奨。
                    )
                )
            )
        )
    )
)

echo ========================================
echo SUCCESS=%SUCCESS%
echo FAILED=%FAILED%

if not "%FAILED%"=="0" (
    echo [FAILED] One or more jobs failed. Work files are retained.
    exit /b 20
)

echo [SUCCESS] All jobs completed.
exit /b 0
```

このBATはPoC向けである。正式実装ではPython Job Runnerへ移行し、JSON Manifest、SHA-256、再開点、Stage Retryを持たせる。

---

## 4.8 VAD（Voice Activity Detection）

Demucs後の音声をそのままASRへ流さず、発話区間を検出する。

Faster-WhisperにはSilero VADを利用する `vad_filter` が存在するため、初期実装ではこれを利用できる。

```python
segments, info = model.transcribe(
    "vocals.wav",
    word_timestamps=True,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
)
```

VADの目的:

- 無音区間除去
- 心音や環境音のみの区間をASRへ送り続けるコスト低減
- Diarization対象区間の削減
- 誤文字起こし低減

---

## 4.9 高精度文字おこし Faster-Whisper

DbD固有語:

```text
デドバ
トンネル
ボロタイ
固有
タゲチェン
ノーワン
通電
ハッチ
ステイン
キャンプ
```

などをinitial prompt等で補助する。

### 4.9.1 必須出力

単なる全文テキストではなく、最低限以下を保持する。

```json
{
  "segment_id": "ASR-001",
  "start": 12.30,
  "end": 15.80,
  "text": "ここはタゲチェンしたいですね",
  "language": "ja",
  "words": [
    {"start": 12.30, "end": 12.62, "text": "ここは"},
    {"start": 12.63, "end": 13.10, "text": "タゲチェン"}
  ],
  "asr_confidence": 0.91
}
```

Word-level timestampを優先し、後段の話者アラインメントへ利用する。

---

## 4.10 Speaker Diarization

実況者・解説者が複数いる場合、PyAnnote等によるspeaker diarizationを行う。

出力例:

```json
[
  {"start": 12.10, "end": 13.95, "speaker": "SPEAKER_00"},
  {"start": 14.02, "end": 15.73, "speaker": "SPEAKER_01"}
]
```

`SPEAKER_00` を即座に実在人物名へ確定しない。

別途Speaker Registryを持つ。

```json
{
  "speaker_cluster_id": "SPEAKER_00",
  "resolved_identity": null,
  "role": "commentary",
  "identity_confidence": 0.0,
  "review_status": "UNRESOLVED"
}
```

---

## 4.11 ASR ↔ Speaker Alignment

Ver.1で欠落していた重要工程である。

ASR:

```text
12.30 - 15.80  「ここはタゲチェンしたいですね」
```

Diarization:

```text
12.10 - 13.95  SPEAKER_00
14.02 - 15.73  SPEAKER_01
```

この場合、単純にsegment単位で1話者へ決めると誤る。

Ver.2.0ではword timestampとspeaker segmentの重なりを計算する。

```python
def overlap(a_start, a_end, b_start, b_end):
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))

def assign_speaker(word, speaker_segments):
    candidates = []
    for seg in speaker_segments:
        ov = overlap(word["start"], word["end"], seg["start"], seg["end"])
        if ov > 0:
            candidates.append((ov, seg["speaker"]))
    if not candidates:
        return "UNKNOWN"
    candidates.sort(reverse=True)
    return candidates[0][1]
```

重複発話が検出された場合は、

```text
OVERLAPPED_SPEECH
```

として扱い、低信頼学習データへ自動投入しない。

---

## 4.12 音声パイプラインの最終フロー

```text
Video
 ↓
ffprobe
 ↓
Audio Stream Selection
 ↓
FFmpeg WAV
 ↓
Source Separation Provider
 ↓
Audio Quality Check
 ↓
VAD
 ↓
Faster-Whisper
 ↓
pyannote diarization
 ↓
Word ↔ Speaker Alignment
 ↓
Speaker Role Resolution
 ↓
Transcript Validation
 ↓
Canonical Timeline
```

---

# 第5章：ゲーム画面認識 Vision Pipeline

## 5.1 基本思想

全フレームを常時Vision LLMへ送るのではなく、低コストな認識で候補イベントを絞り込み、必要な箇所だけ高度な処理へ昇格する。

### Tier 1: HUD / OCR

- 発電機残数
- サバイバー状態
- フック状態
- UIベースチェイス兆候

### Tier 2: Temporal State Machine

- 1フレーム誤検出の除外
- debounce
- hysteresis
- 状態遷移整合

### Tier 3: Object / Scene Recognition

- 板
- 窓
- キラー/サバイバー
- マップ特徴
- 固有建築候補
- キラー能力の視覚的兆候

### Tier 4: Selective Vision AI

高価なVisionモデルを以下のような重要局面だけに使う。

- チェイス開始/終了
- ダウン直前
- 救助
- 通電
- 大きな戦術判断
- Tier 1〜3で矛盾が出た局面

---

## 5.2 チェイス検知

Ver.1の以下思想を保持する。

- サバイバーアイコン周囲の爪エフェクト
- 複数テンプレート
- `cv2.matchTemplate`
- 動体差分

Ver.2.0では単発しきい値では確定しない。

例:

```text
NOT_CHASE
  ↓ 3連続 positive
CHASE_CANDIDATE
  ↓ 2連続 positive
CHASE_ACTIVE
  ↓ 3連続 negative
CHASE_END_CANDIDATE
  ↓ 2連続 negative
NOT_CHASE
```

イベントにはconfidenceを持たせる。

```json
{
  "event_type": "CHASE_START",
  "timestamp": 331.42,
  "confidence": 0.87,
  "detectors": {
    "template": 0.91,
    "motion": 0.76,
    "state_machine": 0.94
  }
}
```

---

## 5.3 負傷・ダウン・フック

Ver.1のテンプレート/色判定思想を保持するが、「完全に判別できる」とは定義しない。

状態:

```text
HEALTHY
INJURED
DOWNED
HOOKED
DEAD
ESCAPED
UNKNOWN
```

不明な場合は `UNKNOWN` を許容する。

**誤った確定値よりUNKNOWNの方が正しい。**

---

## 5.4 発電機残数OCR

Ver.1の `allowlist='012345'` を保持する。

ただし単回OCR結果を確定しない。

```python
history = [5, 5, 5, 4, 5]

# 1回だけ4ならノイズの可能性。
# 複数フレームの多数決・遷移制約を利用する。
```

通常の試合進行で発電機残数が増加した場合は異常値候補として扱う。

---

## 5.5 DbD Patch Profile / HUD Profile

HUDはパッチ、解像度、UI Scale、配信レイアウト等で変化し得る。

```json
{
  "profile_id": "DBD-HUD-9.X-1080P-100",
  "game_version": "9.x",
  "resolution": [1920, 1080],
  "hud_scale": 100,
  "generator_roi": [0.05, 0.83, 0.10, 0.88],
  "survivor_roi": [0.01, 0.70, 0.12, 0.95],
  "templates_version": "2026-08-17"
}
```

未知パッチでは、

```text
PATCH_UNKNOWN
```

としてHuman Reviewへ回す。

---

## 5.6 初期実装 main.py（Ver.1コード保持）

以下は元仕様の初期PoCコードをそのまま保持する。

```python
import cv2
import easyocr
import os

def main():
    # 1. 保存用フォルダの自動生成
    output_dir = "templates"
    os.makedirs(output_dir, exist_ok=True)

    # 2. EasyOCRの初期化（英語・数字認識モードをメモリにロード）
    print("[INFO] OCRモデルを初期化中...")
    reader = easyocr.Reader(['en'], gpu=False) # GPUがある場合はTrueに設定可能

    # 3. 動画ファイルの読み込み
    video_path = 'videos/match_sample.mp4'
    if not os.path.exists(video_path):
        print(f"[ERROR] 動画ファイルが見つかりません: {video_path}")
        print("videos フォルダを作成し、match_sample.mp4 を配置してください。")
        return

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0:
        print("[ERROR] 動画の読み込みに失敗しました。ファイル破損かコーデックの問題の可能性があります。")
        return

    print(f"[INFO] 動画読み込み成功: {video_path}")
    print(f"[INFO] FPS: {fps} | 総フレーム数: {total_frames} | 動画長: {int(total_frames/fps)}秒")
    print("----------------------------------------------------------------")

    frame_count = 0
    previous_gen_num = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 処理軽量化のため、1秒（fpsフレーム）に1回だけサンプリング処理を実行
        if frame_count % int(fps) == 0:
            timestamp_sec = int(frame_count / fps)

            # --- 発電機残り台数OCR認識セクション ---
            # 【重要】以下の座標[y1:y2, x1:x2]は1920x1080(フルHD)を想定しています。
            # 動画の解像度やUIスケールに応じて、切り出し範囲の数値を適宜調整してください。
            h, w, _ = frame.shape

            # フルHD(1080p)時の画面左下・発電機アイコン付近の座標アタリ値
            y1, y2 = int(h * 0.83), int(h * 0.88)
            x1, x2 = int(w * 0.05), int(w * 0.10)

            gen_area = frame[y1:y2, x1:x2]

            # テスト用に最初の1枚だけトリミング画像を保存して目視確認できるようにする
            if timestamp_sec == 5:
                test_crop_path = os.path.join(output_dir, "debug_gen_crop.png")
                cv2.imwrite(test_crop_path, gen_area)
                print(f"[DEBUG] 5秒時点の発電機切り出し画像をデバッグ保存しました: {test_crop_path}")

            # EasyOCRで画像内のテキストを読み取る（0〜5の数字のみに限定）
            result = reader.readtext(gen_area, allowlist='012345')

            if result:
                # 認識結果から最も確信度の高いテキスト部分を抽出
                gen_num = result[0][1]

                # 数値が変化した瞬間だけイベントログとして強調表示
                if gen_num != previous_gen_num:
                    print(f"★【イベント発生】 {timestamp_sec}秒 | 発電機台数が変化: {gen_num}台")
                    previous_gen_num = gen_num
                else:
                    print(f"[{timestamp_sec}秒] 巡回監視中... 残り発電機: {gen_num}台")
            else:
                print(f"[{timestamp_sec}秒] 巡回監視中... 発電機数値の読み取り不鮮明")

            # --- テンプレート画像切り出しテスト（開発用コード） ---
            # 最初の10秒時点で、サバイバー1（一番下）のアイコンエリアを切り出して保存する例
            if timestamp_sec == 10:
                # サバイバーアイコン付近の座標アタリ値（解像度に応じて要微調整）
                sy1, sy2 = int(h * 0.70), int(h * 0.95)
                sx1, sx2 = int(w * 0.01), int(w * 0.12)
                sub_area = frame[sy1:sy2, sx1:sx2]

                template_path = os.path.join(output_dir, "sample_survivor_area.png")
                cv2.imwrite(template_path, sub_area)
                print(f"[DEBUG] 10秒時点のサバイバー全体エリアをテンプレート候補として保存しました: {template_path}")

        frame_count += 1

    cap.release()
    print("----------------------------------------------------------------")
    print("[INFO] 動画の全フレーム解析（前処理ビジョンタスク）が完了しました。")

if __name__ == '__main__':
    main()
```

### 5.6.1 Ver.2.0における位置付け

上記 `main.py` は**ROI/OCR確認用PoC**であり、本番解析器ではない。

不足点:

- EasyOCR confidenceを利用していない
- 一番高いconfidence結果を正しく選別していない
- State Machineがない
- Job Manifestがない
- Patch Profileがない
- JSON event出力がない
- 例外処理が限定的
- 動画ごとの解析結果保存がない
- UNKNOWN状態がない

正式実装では `vision_pipeline/` 配下へ分離する。

```text
vision_pipeline/
├── profiles/
├── detectors/
│   ├── generator_detector.py
│   ├── survivor_state_detector.py
│   └── chase_detector.py
├── state_machine.py
├── event_writer.py
└── pipeline.py
```

---

# 第6章：Canonical Game Event Timeline

## 6.1 目的

Ver.2.0最大の設計変更である。

音声解析と映像解析を別々のログとして残すのではなく、同一時間軸へ統合する。

```json
{
  "event_id": "EVT-000123",
  "match_id": "MATCH-0001",
  "timestamp_start": 331.42,
  "timestamp_end": 342.81,
  "event_type": "CHASE",
  "game_version": "9.x",
  "mode": "1V4",
  "perspective": "SURVIVOR",
  "killer": "UNKNOWN",
  "survivor": "S2",
  "generator_remaining": 3,
  "confidence": 0.87,
  "evidence": [
    {
      "type": "HUD_CHASE",
      "ref": "vision/331.42.json",
      "confidence": 0.91
    },
    {
      "type": "TRANSCRIPT",
      "ref": "audio/segment-302.json",
      "confidence": 0.83
    }
  ],
  "source_video": "SRC-0001",
  "source_hash": "sha256:...",
  "review_status": "AUTO_ACCEPTED"
}
```

## 6.2 Event Type

初期候補:

```text
MATCH_START
GENERATOR_COMPLETE
CHASE_START
CHASE_END
INJURY
DOWN
HOOK
UNHOOK
HEAL
KILL
ESCAPE
GATE_POWERED
GATE_OPEN
HATCH_EVENT
KILLER_POWER_USE
PALLET_DROP
PALLET_BREAK
WINDOW_VAULT
TARGET_SWITCH
UNKNOWN_EVENT
```

## 6.3 Evidence-first

LLMの推論結果だけでイベントを作らない。

イベントには最低1つ以上のEvidenceを要求する。

強い戦術断定には複数Evidenceを推奨する。

---

# 第7章：文字おこし・映像・イベントの結合と学習データ生成

## 7.1 元仕様のQ&A形式（保持）

```json
[
  {
    "instruction": "DbDの試合状況: 残り発電機4台。サバイバー1人が固有建築でチェイス中。キラーはトラッパー。",
    "input": "キラーが固有の窓枠に罠を仕掛けたのを見たサバイバーの動きについて解説してください。",
    "output": "あー、ここはサバイバー側もしっかり見てますね！トラッパー相手の固有チェイスは窓枠の罠が一番怖いので、無理に中に入らずに外の板にターゲットを切り替えました。これは素晴らしい判断です。"
  },
  {
    "instruction": "DbDの試合状況: 残り発電機1台。通電間近。サバイバーが2人負傷状態。",
    "input": "この状況でのキラーとサバイバーの心理戦を解説してください。",
    "output": "ここが勝負の分かれ目ですね。サバイバーとしては何が何でも通電させたいですが、キラー側はここでダウンを取って『ノーワン（誰も死から逃れられない）』の発動まで繋げたい。チェイスに入っているサバイバーがいかに時間を稼げるかです！"
  }
]
```

## 7.2 Ver.2.0 Dataset Record

上記の単純Q&Aへ、出典・パッチ・confidence・eventを追加する。

```json
{
  "dataset_id": "DS-000001",
  "instruction": "この局面をDbD実況解説として説明してください。",
  "input": {
    "event_id": "EVT-000123",
    "game_version": "9.x",
    "generator_remaining": 4,
    "event_type": "CHASE",
    "killer": "TRAPPER"
  },
  "output": "あー、ここはサバイバー側もしっかり見ていますね…",
  "source": {
    "source_id": "SRC-0001",
    "speaker_id": "COMMENTATOR-A",
    "rights_status": "APPROVED"
  },
  "confidence": 0.94,
  "human_review": "APPROVED"
}
```

## 7.3 不要データの除外・成形

Ver.1ではパイプライン上で宣言されていたが詳細が欠落していた工程である。

除外候補:

- ASR confidenceが低い
- 複数話者が強く重複
- ゲーム音を発言として誤認識
- 盤面Evidenceが不足
- パッチ不明
- 権利不明
- 発言が戦術と無関係
- 個人情報を含む
- 差別・誹謗等の不要発言
- 学習目的と無関係な雑談
- 同一セグメントの重複

除外理由も記録する。

```json
{
  "record_id": "RAW-0091",
  "status": "REJECTED",
  "reasons": [
    "OVERLAPPED_SPEECH",
    "LOW_ASR_CONFIDENCE"
  ]
}
```

---

# 第8章：RAG設計

## 8.1 格納対象

```text
PATCH_NOTE
PERK
ADDON
KILLER
SURVIVOR
MAP
TILE
TACTIC
COMMENTARY_EXAMPLE
MATCH_EVENT
```

## 8.2 Patch-aware Retrieval

検索時:

```python
filters = {
    "game_version_compatible": current_game_version,
    "mode": current_mode,
}
```

古い情報を取得しても、現在パッチと非互換なら強い根拠にしない。

## 8.3 Provenance

RAGチャンク:

```json
{
  "chunk_id": "RAG-001",
  "content": "...",
  "source_id": "BHVR-PATCH-...",
  "source_type": "PATCH_NOTE",
  "game_version_from": "x",
  "game_version_to": null,
  "rights_status": "REFERENCE_ALLOWED",
  "verified_at": "2026-08-17"
}
```

## 8.4 Abstention

根拠が不足した場合、LLMは断定せず次の出力を許容する。

```text
「映像だけではこの判断の意図までは確定できません。」
```

この能力を品質低下ではなく**正しい安全動作**として評価する。

---

# 第9章：LoRA / ファインチューニング

## 9.1 学習目的

知識そのものをLoRAへ詰め込むのではなく、主として:

- 言い回し
- 実況構造
- 解説順序
- DbD語彙
- テンポ
- 感情量

を対象にする。

最新パッチ事実はRAGを優先する。

## 9.2 Train / Validation / Testの分離

同一Matchから切り出した複数Clipを別splitへ混ぜない。

禁止例:

```text
Match A / Clip 1 → Train
Match A / Clip 2 → Validation
```

推奨:

```text
Match A → Trainのみ
Match B → Validationのみ
Match C → Testのみ
```

可能であれば以下でも分布を監査する。

- killer
- map
- patch
- commentator
- tournament
- player

---

# 第10章：解説生成・Timing Planner・TTS・動画出力

## 10.1 Commentary Planner

1秒ごとに必ず発話を生成する設計にはしない。

実況の密度を制御する。

```json
{
  "event_id": "EVT-001",
  "speak": true,
  "priority": 0.92,
  "style": "EXCITED",
  "max_duration_sec": 4.2,
  "must_finish_before": 341.8
}
```

## 10.2 Fact Validator

生成した台本をそのままTTSへ渡さない。

チェック:

- 現在パッチと矛盾していないか
- Generator残数と矛盾しないか
- Evidenceにないプレイヤー意図を断定していないか
- パーク発動を推測で確定していないか
- RAG出典があるか
- 発話可能時間へ収まるか

## 10.3 TTS

候補:

- VOICEVOX
- AITalk
- ElevenLabs
- ローカルTTS
- ユーザー自身の音声モデル
- 許諾済み共有Voice

### Voice Mode

```text
ORIGINAL_SYNTHETIC
USER_OWN_VOICE
LICENSED_SHARED_VOICE
PROHIBITED_UNVERIFIED_CLONE
```

`PROHIBITED_UNVERIFIED_CLONE` はレンダリング禁止。

## 10.4 他者音声クローン

Ver.1では「解説者の声質をクローン」という表現があったが、Ver.2.0では無条件実行しない。

ElevenLabsのProfessional Voice Clone等、サービス側に本人確認・共有の仕組みがある場合はその正規フローに従う。

## 10.5 音声ミキシング

元動画へ生成音声を単純加算しない。

必要:

- game audio ducking
- commentary loudness target
- limiter
- clipping detection
- background BGMとの競合
- speech overlap制御

## 10.6 「なるほど演出」

重要局面で:

- slow motion
- freeze
- graphic overlay
- tactical annotation
- 3視点解説

等を挿入できる。

ただしイベントEvidenceのconfidenceが一定以上であることを条件とする。

---

# 第11章：Windows環境構築と依存関係管理

## 11.1 Ver.1の環境構築思想

PC全体を汚さないため `venv` を利用する思想は継承する。

```bat
mkdir dbd_vision_project
cd dbd_vision_project
python -m venv .venv
.venv\Scripts\activate
```

Ver.1では主として:

```bat
pip install opencv-python opencv-contrib-python easyocr numpy matplotlib Pillow
```

のみだった。

Ver.2.0ではシステム全体の依存を明示する。

## 11.2 Dependency Group

```text
core
media
audio
vision
asr
diarization
rag
llm
training
tts
render
test
```

例:

```text
requirements/
├── base.txt
├── audio.txt
├── vision.txt
├── training.txt
└── dev.txt
```

あるいは `pyproject.toml` / lock fileへ統合する。

## 11.3 バージョン固定

`pip install -U` を本番手順にしない。

```text
requirements.lock
runtime-profile.json
model-manifest.json
```

を使用する。

## 11.4 推奨ディレクトリ

```text
dbd_video_intelligence/
├── .venv/
├── config/
│   ├── runtime/
│   ├── hud_profiles/
│   └── policies/
├── input/
├── work/
│   └── JOB-*/
├── output/
├── models/
├── templates/
├── rights/
├── manifests/
├── logs/
├── datasets/
│   ├── raw/
│   ├── curated/
│   ├── train/
│   ├── validation/
│   └── test/
├── rag/
├── audio_pipeline/
├── vision_pipeline/
├── event_pipeline/
├── generation_pipeline/
├── renderer/
└── tests/
```

---

# 第12章：Job Manifest・Resume・Retry・クリーンアップ

## 12.1 Manifest

```json
{
  "job_id": "JOB-001",
  "input": {
    "path": "input/match01.mp4",
    "sha256": "..."
  },
  "runtime": {
    "profile": "windows-nvidia-v1",
    "gpu": "..."
  },
  "stages": {
    "probe": {
      "status": "SUCCESS",
      "started_at": "...",
      "finished_at": "..."
    },
    "audio": {
      "status": "SUCCESS"
    },
    "vision": {
      "status": "NEEDS_REVIEW"
    }
  }
}
```

## 12.2 Resume

再実行時は成功済みStageを再処理しない。

ただし以下なら無効化する。

- 入力hash変更
- model version変更
- config変更
- patch profile変更
- `--force`

## 12.3 Retry

```text
TRANSIENT
RESOURCE
INPUT
CONFIG
MODEL
RIGHTS
UNKNOWN
```

にエラー分類する。

`TRANSIENT` のみ自動retry候補。

## 12.4 Cleanup

Ver.1の「最後に全一時ファイル削除」を変更する。

```text
FAILED          → 保持
NEEDS_REVIEW    → 保持
SUCCESS          → retention policyに従う
ARCHIVED         → 削除可能
```

---

# 第13章：品質評価・Gold Dataset・回帰試験

## 13.1 KPI

| 領域 | 指標 |
|---|---|
| ASR | WER / CER |
| Diarization | DER |
| Event Detection | Precision / Recall / F1 |
| Timing | Timestamp Error |
| RAG | Recall@K / Precision@K |
| Tactical Fact | Factual Accuracy |
| Commentary | Human Tactical Score |
| Style | Human Style Score |
| TTS | MOS等 |
| Render | Sync Error / clipping |
| End-to-End | Human Acceptance Rate |

## 13.2 Gold Dataset

人間が正解を付けた少数の高品質データを作る。

最低:

- 5〜10試合のPilot
- 発電機変化
- chase
- injured/down/hook
- speaker
- transcript
- tactical notes

を人手で確定する。

自動処理精度はこのGold Datasetに対して測る。

## 13.3 回帰試験

新しい:

- OpenCV template
- HUD Profile
- Demucs/Provider
- Whisper model
- Diarization model
- LLM
- RAG embedding

を導入した際に過去Gold Datasetへ再実行し、品質低下を検出する。

---

# 第14章：学習データ量と段階的スケール

## 14.1 Ver.1の目安を継承するが「保証値」にはしない

| 段階 | 試合数の計画目安 | 主目的 |
|---|---:|---|
| Pipeline Pilot | 5〜10 | 前処理の成立確認 |
| 検証 | 10〜20 | 初期LoRA/RAG |
| 実用候補 | 30〜50 | バリエーション拡大 |
| 高品質候補 | 100+ | ロングテール拡大 |

30〜50試合という値はPlanning Estimateであり、品質判定は第13章KPIで行う。

## 14.2 特定シーン濃縮

索敵時間全体を無条件学習しない。

- chase start → down
- rescue
- generator completion
- endgame
- tactical switch

等の高情報密度区間を優先する。

---

# 第15章：Human Gate・運用UI・訂正フロー

## 15.1 Human Gate

```text
AI Analysis
 ↓
Automated Validation
 ↓
Human Review
 ↓
APPROVE / CORRECT / REJECT
 ↓
Render / Dataset Commit
```

## 15.2 自動停止条件

- confidence閾値未満
- unknown patch
- unknown HUD
- speaker unresolved
- rights unknown
- voice consent missing
- RAG根拠なしで強い戦術断定
- 複数Detectorが矛盾
- ASRと映像タイムラインが大きく矛盾

## 15.3 訂正履歴

人がAIイベントを修正した場合、上書きだけしない。

```json
{
  "event_id": "EVT-001",
  "original": {
    "event_type": "CHASE_START",
    "timestamp": 30.2
  },
  "corrected": {
    "event_type": "NOT_CHASE",
    "timestamp": 30.2
  },
  "reviewer": "USER",
  "reason": "HUD animation false positive"
}
```

この訂正を次回Detector改善へ利用する。

---

# 第16章：セキュリティ・モデル供給網・秘密情報

## 16.1 モデル取得

- model source URL
- revision / commit
- checksum
- license
- downloaded_at

をManifestへ記録する。

## 16.2 Secrets

API Keyをソースへ直書きしない。

```text
.env
Windows Credential Manager
secret store
```

等を利用し、ログへ出力しない。

## 16.3 入力ファイル

任意ファイルを扱うため:

- ファイルサイズ上限
- 許容拡張子
- ffprobe検証
- path traversal防止
- 実行ファイル混入防止

を行う。

---

# 第17章：AI音声・公開・権利ガバナンス

## 17.1 Voice Consent Gate

```json
{
  "voice_id": "VOICE-001",
  "owner": "USER",
  "mode": "USER_OWN_VOICE",
  "consent": true,
  "provider_verified": true,
  "public_use_allowed": true
}
```

## 17.2 AI生成・改変コンテンツ

公開先プラットフォームの最新ルールに従う。

現実的な他者音声のクローン等、公開時の開示が必要となるケースをPolicyとして管理する。

```json
{
  "publication_policy": {
    "ai_disclosure_required": true,
    "voice_clone_disclosure_required": true
  }
}
```

## 17.3 なりすまし防止

他人の声や名称を使い、

```text
本人が実況した
本人が承認した
本人公式コンテンツである
```

かのように誤認させない。

---

# 第18章：運用フロー

## 18.1 日常運用

```text
1. Input登録
2. Rights確認
3. Preflight
4. Job開始
5. Audio/Vision解析
6. Event統合
7. Low Confidence Review
8. Dataset/RAG登録
9. Commentary生成
10. TTS
11. Render
12. Quality Gate
13. Human Gate
14. Output
15. Manifest Archive
```

## 18.2 オペレータが見るべき情報

```text
Job ID
Source
Current Stage
Progress
Elapsed
GPU VRAM
Disk Free
Success Count
Warning Count
Failure Count
Needs Review Count
Last Error
Retry Action
```

## 18.3 失敗時

「もう一度最初から」ではなく、失敗Stageから再開する。

---

# 第19章：3周監査結果の正式反映

## 19.1 第1周

### 優秀なエンジニア

発見:

- `vocals.wav` パス破損
- FFmpeg/Demucsのexit code未確認
- 失敗時もcleanup
- dependency未固定
- `htdemucs_ft` 常時採用の根拠不足
- ファイル名衝突
- 音声stream選択欠落

是正:

- Legacy code保持＋V2安全版追加
- Provider化
- ffprobe
- Fail-closed
- Job directory

### 運用者

発見:

- 成功/失敗件数不明
- 再処理不可
- 途中経過不明
- 完了表示を信用できない

是正:

- Job State
- Manifest
- Retry
- Resume
- failed work retention

### システムエンジニア

発見:

- 音声パイプライン4工程のうち後半が未設計
- 環境構築がVision依存中心で全体を再現できない

是正:

- 第4・7・11章として詳細化
- dependency groups
- runtime profile

## 19.2 第2周

### 優秀なエンジニア

発見:

- Demucs vocals ≠ 実況者だけ
- diarizationとASRの時間結合欠落
- overlapped speech未設計

是正:

- VAD
- ASR word timestamps
- Speaker Alignment
- UNKNOWN / OVERLAPPED_SPEECH

### 運用者

発見:

- 誤判定を人間が直す仕組みがない

是正:

- Confidence
- NEEDS_REVIEW
- Human correction history

### システムエンジニア

発見:

- DbD Patch Version/HUD Versionがデータモデルにない
- OpenCV HUDのみでは戦術情報が不足

是正:

- Patch/HUD Profile
- Vision 4 Tier
- Canonical Game Event Timeline

## 19.3 第3周

### 優秀なエンジニア

発見:

- 学習精度の評価基準なし
- データリーク
- 試合数と品質の関係を固定値扱い

是正:

- Gold Dataset
- KPI
- Match単位Split
- Planning Estimate化

### 運用者

発見:

- AIが最後まで自動で公開可能
- 高リスク判断を止める場所がない

是正:

- Quality Gate
- Human Gate
- abstention

### システムエンジニア

発見:

- Source rights
- Voice consent
- AI disclosure
- provenance

是正:

- Rights Registry
- Voice Consent Gate
- Publication Policy
- Source provenance

---

# 第20章：開発ゲート

## P0：Execution Foundation

必須:

- [ ] Broken BAT path修正
- [ ] Fail-closed
- [ ] Exit code
- [ ] venv
- [ ] dependency lock
- [ ] ffprobe
- [ ] Job Manifest
- [ ] safe cleanup
- [ ] resume/retry

**P0 PASS → PoC開始可能**

## P1：Perception / Dataset Foundation

- [ ] Canonical Event Schema
- [ ] VAD
- [ ] ASR
- [ ] diarization
- [ ] speaker alignment
- [ ] confidence
- [ ] UNKNOWN
- [ ] Patch Profile
- [ ] Vision State Machine
- [ ] Gold Dataset
- [ ] KPI

**P0 + P1 PASS → 本格的な学習データ収集可能**

## P2：Generation / Governance Foundation

- [ ] RAG provenance
- [ ] Patch-aware retrieval
- [ ] Fact Validator
- [ ] Human Gate
- [ ] Rights Registry
- [ ] Voice Consent Gate
- [ ] AI disclosure policy
- [ ] Regression test
- [ ] Backup / restore

**P0 + P1 + P2 PASS → 本番運用候補**

---

# 第21章：上長最終判断

## 21.1 Ver.1評価

- 構想: **GO**
- PoC: **条件付きGO**
- 本番: **NO-GO**

理由は、アイデア不足ではなく、実装失敗・誤認識・再処理・権利・精度評価・ゲーム更新への耐性が不足していたためである。

## 21.2 Ver.2.0評価

本Ver.2.0は、監査で指摘された主要な設計欠落を**設計項目として統合済み**と判断する。

ただしこれは「実装完了」を意味しない。

上長判断:

> **詳細設計 Ver.2.0：承認候補 / IMPLEMENTATION AUTHORIZATIONはP0詳細化・テスト仕様確定後。**

すなわち、

```text
DESIGN: GO
P0 IMPLEMENTATION: GO
P1/P2: P0 Evidenceを見て段階承認
PRODUCTION: まだNO-GO
```

とする。

---

# 第22章：推奨実装順序

```text
TASK-001  Repository / Runtime Foundation
TASK-002  Job Manifest / Error Model
TASK-003  ffprobe / Audio Extraction
TASK-004  Source Separation Provider
TASK-005  VAD / Faster-Whisper
TASK-006  Diarization / Speaker Alignment
TASK-007  Vision HUD PoC
TASK-008  Patch Profile / State Machine
TASK-009  Canonical Event Timeline
TASK-010  Human Review Minimum UI
TASK-011  Gold Dataset / Benchmark
TASK-012  RAG
TASK-013  Dataset Curator
TASK-014  LoRA Pilot
TASK-015  Commentary Planner / Validator
TASK-016  TTS / Voice Gate
TASK-017  Renderer
TASK-018  End-to-End Quality Gate
TASK-019  Regression / Backup / Restore
TASK-020  Production Pilot
```

---

# 付録A：Ver.1から維持した重要思想

本Ver.2.0は元文書を否定するものではなく、次を明確に継承している。

- ローカルGPU中心
- Demucs/FFmpegによる前処理
- Faster-Whisper
- PyAnnote
- OpenCV/EasyOCR
- 低コスト検出→高度解析のハイブリッド思想
- RAG＋LoRA
- 盤面をキーにした複数解説者見解
- 「なるほど演出」
- 自動TTS
- 自動動画編集
- 5〜10試合から始めるスモールスタート
- 30〜50試合、100試合以上へ段階拡張する考え方

Ver.2.0はこれらへ「失敗した時に壊れないこと」「間違いを確定しないこと」「再現可能であること」「権利と出典を追えること」を追加したものである。

---

# 付録B：外部技術確認メモ（2026-08-17時点）

Ver.2.0作成時、以下の公式一次情報を設計判断の参考にした。実装開始時には再確認すること。

- Demucs公式/旧Metaリポジトリ
  https://github.com/facebookresearch/demucs
- Faster-Whisper公式GitHub
  https://github.com/SYSTRAN/faster-whisper
- pyannote.audio公式GitHub
  https://github.com/pyannote/pyannote-audio
- ElevenLabs Professional Voice Cloning Documentation
  https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning
- YouTube 利用規約
  https://jp.youtube.com/t/terms
- YouTube AI生成・改変コンテンツ開示
  https://support.google.com/youtube/answer/14328491

---

# 付録C：完成定義（Definition of Done）

システム全体としての「完成」は、動画が1本生成できることではない。

以下を満たすことを完成条件とする。

1. 同一入力・同一runtime profileから再現可能
2. 失敗したStageが特定できる
3. 失敗後に再開できる
4. 入力・モデル・設定・出力のhash/provenanceを追跡できる
5. Gold Datasetに対する回帰試験がある
6. UnknownをUnknownとして扱える
7. DbD Patch変更へProfile更新で対応できる
8. RAGの根拠を追跡できる
9. Human Gateで誤生成を止められる
10. 音声利用権限を確認できる
11. 出力公開時のAI開示要件を判定できる
12. バックアップ/再処理が可能
13. 日常運用者が成功・失敗・要確認を判断できる
14. 本番データを学習データへ昇格させる条件が明示されている

---

# 終章

Ver.1では、**「動画を解析してDbDの解説実況を自動生成する」**という目的と、Demucs・Faster-Whisper・PyAnnote・OpenCV・RAG・LoRA・TTS・MoviePy等を組み合わせる実現方向は明確だった。

Ver.2.0ではその思想を残したまま、システムの主軸を次のように再定義した。

> **動画 → AI** ではない。
> **動画 → 検証可能なEvidence → Canonical Game Event Timeline → AI → Validation → Human Gate → 成果物** である。

この構造にすることで、将来的には自動実況だけでなく、

- ハイライト抽出
- Shorts生成
- チェイス分析
- 「なぜ上手かったか」解説
- プレイヤーコーチング
- 大会分析
- 選手比較
- 実況スタイル比較
- 戦術ナレッジベース

へ同一基盤から拡張できる。

**本システムの本質は「DbD自動実況ツール」ではなく、DbD Video Intelligence Platformである。**


---

# Ver.2.1 追補：Perk Knowledge Intelligence Subsystem 統合設計

> **追補日**: 2026-08-17
> **対象**: `Dead by Daylight Video Intelligence Platform / 解説・実況自動生成AIシステム 詳細設計書 Ver.2.0`
> **統合対象**: パークアイコン、日本語名、英語名、正式効果、分かりやすい説明、構造化効果、タグ、バージョン、出典、アイコン認識、RAG
> **方針**: 既存Ver.2.0本文を削除・置換せず、本追補を追加仕様として適用する。矛盾する場合は本追補の責任境界定義を優先する。

---

## 23. 追補の目的

本追補は、Dead by Daylightのパーク知識基盤を、独立したLLM学習プロジェクトとしてではなく、既存の **DbD Video Intelligence Platform** の一部として正式統合するための設計である。

本プラットフォームでは、すでに以下が中核として定義されている。

```text
動画
 ↓
検証可能なEvidence
 ↓
Canonical Game Event Timeline
 ↓
RAG / Training Dataset
 ↓
LLM / LoRA
 ↓
Commentary Planner
 ↓
Fact Validator
 ↓
Human Gate
```

したがって、本追補で追加するPerk Knowledge Intelligence Subsystemは、

```text
独立した「DBDパークAI」
```

ではなく、

```text
DbD Video Intelligence Platform
    ├── Audio Pipeline
    ├── Vision Pipeline
    ├── Canonical Game Event Timeline
    ├── Perk Knowledge Intelligence Subsystem  ← 追加
    ├── RAG
    ├── Training Dataset
    ├── LLM / LoRA
    ├── Commentary Planner
    ├── Fact Validator
    └── Human Gate
```

という位置付けとする。

---

## 23.1 最重要変更点

単独設計時に想定していた、

```text
SQLite = System-wide Source of Truth
```

という表現は、本プラットフォームへ統合する場合は採用しない。

システム全体の中心データモデルは、Ver.2.0で定義済みの

```text
Canonical Game Event Timeline
```

を維持する。

Perk Knowledge BaseのSQLiteは、

```text
Perk Fact Canonical Store
```

すなわち、

> **パークというゲーム知識についてのCanonical Store**

と定義する。

責任境界は次の通り。

```text
Canonical Game Event Timeline
    = 試合中に何が観測されたか

Perk Knowledge Base
    = そのパークがそのゲームバージョンで何を意味するか

Vision Recognition
    = 画面に何が見えた可能性があるか

LLM
    = EvidenceとKnowledgeを基に何を説明すべきか
```

---

# 第24章：Perk Knowledge Intelligence Subsystem 全体構成

## 24.1 統合アーキテクチャ

```text
                     DbD VIDEO INTELLIGENCE PLATFORM

                               Source Video
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                │
                  ↓                ↓                ↓
             Audio Pipeline   Vision Pipeline   Rights / Metadata
                                   │
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ↓                             ↓
             Generic HUD/Event              Perk HUD Area
               Recognition                        │
                    │                             ↓
                    │                   Perk Icon Recognition
                    │                             │
                    │                       perk_id candidate
                    │                             │
                    │                             ↓
                    │                 ┌────────────────────────┐
                    │                 │ Perk Knowledge Base    │
                    │                 │                        │
                    │                 │ Identity               │
                    │                 │ Revision               │
                    │                 │ Official Effect        │
                    │                 │ Structured Effect      │
                    │                 │ Source Provenance      │
                    │                 │ Icon Assets            │
                    │                 │ Explanation            │
                    │                 └────────────┬───────────┘
                    │                              │
                    └──────────────┬───────────────┘
                                   ↓
                      Canonical Game Event Timeline
                                   │
                      ┌────────────┴─────────────┐
                      │                          │
                      ↓                          ↓
                     RAG                  Training Dataset
                      │                          │
                      └────────────┬─────────────┘
                                   ↓
                              LLM / LoRA
                                   │
                          Commentary Planner
                                   │
                             Fact Validator
                                   │
                              Human Gate
                                   │
                                  Output
```

---

## 24.2 役割分離

Perk Knowledge Intelligence Subsystemは、最低限以下の5層へ分離する。

```text
① FACT
公式・準公式根拠に基づくパーク情報

② STRUCTURE
機械可読化した発動条件・効果・数値・対象

③ INTERPRETATION
人間向けの分かりやすい説明

④ RECOGNITION
動画・スクリーンショット中のパークアイコン認識

⑤ MATCH REASONING
現在の試合状況でどう作用した可能性があるか
```

これらを同一モデルへ丸投げしない。

---

## 24.3 禁止する責任混同

以下を禁止する。

```text
Vision AIがperk_idを推定
    ↓
同じVision AIが効果を記憶だけで断定
```

正しくは、

```text
Vision
 ↓
perk_id candidate
 ↓
Perk Knowledge Base
 ↓
Patch-compatible Verified Revision
 ↓
Canonical Timeline / RAG
 ↓
LLM
```

とする。

---

# 第25章：Perk Canonical Data Model

## 25.1 基本エンティティ

```text
Perk
├── Identity
├── Localization
├── Revision
├── Official Effect
├── Structured Effect
├── Tags
├── Asset
├── Source Provenance
├── Explanation
├── Search Alias
├── Recognition Reference
└── Rights Metadata
```

---

## 25.2 Perk ID

表示名をPrimary Keyにしてはならない。

例:

```text
perk_survivor_dead_hard
perk_survivor_sprint_burst
perk_killer_hex_ruin
```

名称変更、翻訳変更、表記揺れがあっても `perk_id` は変更しない。

---

## 25.3 `perks`

概念スキーマ:

```sql
CREATE TABLE perks (
    perk_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('SURVIVOR', 'KILLER')),
    owner_character_id TEXT,
    perk_family TEXT,
    introduced_version TEXT,
    retired_version TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

`perk_family` 例:

```text
GENERAL
UNIQUE
HEX
BOON
SCOURGE_HOOK
OTHER
```

---

## 25.4 `perk_localizations`

```sql
CREATE TABLE perk_localizations (
    perk_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    name TEXT NOT NULL,
    official_text TEXT,
    short_official_summary TEXT,
    simple_text TEXT,
    beginner_text TEXT,
    short_text TEXT,
    PRIMARY KEY (perk_id, locale),
    FOREIGN KEY (perk_id) REFERENCES perks(perk_id)
);
```

推奨locale:

```text
ja-JP
en-US
```

必要に応じて他言語へ拡張する。

---

## 25.5 `perk_aliases`

プレイヤー俗称や検索用別名は正式名と分離する。

```sql
CREATE TABLE perk_aliases (
    alias_id TEXT PRIMARY KEY,
    perk_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (perk_id) REFERENCES perks(perk_id)
);
```

`alias_type`:

```text
COMMUNITY
ABBREVIATION
OLD_NAME
SEARCH_SYNONYM
ASR_VARIANT
MANUAL
```

ASR用の表記揺れもここで管理できる。

---

# 第26章：Perk Revision / Patch-aware Model

## 26.1 Revision必須化

パーク効果を現在値1つだけで保持してはならない。

```text
perk_id
    ├── revision 1
    ├── revision 2
    ├── revision 3
    └── current verified revision
```

---

## 26.2 `perk_revisions`

```sql
CREATE TABLE perk_revisions (
    revision_id TEXT PRIMARY KEY,
    perk_id TEXT NOT NULL,
    game_version_from TEXT NOT NULL,
    game_version_to TEXT,
    environment TEXT NOT NULL,
    status TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    source_confidence REAL,
    created_at TEXT NOT NULL,
    verified_at TEXT,
    FOREIGN KEY (perk_id) REFERENCES perks(perk_id)
);
```

`environment`:

```text
LIVE
PTB
ARCHIVE
UNKNOWN
```

`status`:

```text
DISCOVERED
PARSED
STRUCTURED
NEEDS_REVIEW
VERIFIED
SUPERSEDED
REJECTED
```

---

## 26.3 LIVE / PTB分離

PTBをLIVEへ自動昇格させてはならない。

```text
PTB Revision
 ↓
LIVE Patch Published
 ↓
Diff
 ↓
Compatibility Check
 ↓
Human Review
 ↓
VERIFIED LIVE Revision
```

---

## 26.4 Unknown Patch

現在動画の `game_version` が解決できない場合:

```text
PATCH_UNKNOWN
```

とする。

この場合、

```text
perk_id recognition
```

自体は継続してもよいが、

```text
「このパークの効果は○○だった」
```

というPatch依存の強い断定は原則停止する。

---

# 第27章：正式効果と分かりやすい説明の分離

## 27.1 Official Effect

正式効果はFact領域である。

```text
official_effect
```

には、

- 発動条件
- 数値
- 秒数
- 距離
- 対象
- 制限
- クールダウン
- トークン
- ティア値
- 例外

を、確認できる範囲で保持する。

---

## 27.2 Simple Explanation

分かりやすい説明はInterpretation領域である。

```text
simple_text
beginner_text
short_text
when_useful
limitations_text
```

として管理する。

---

## 27.3 生成ルール

LLMは分かりやすい説明を生成できる。

ただし、

```text
LLM Generated
    ↓
Rule Validator
    ↓
Fact Consistency Validator
    ↓
Human Review
    ↓
VERIFIED Explanation
```

を必須とする。

---

## 27.4 禁止事項

LLMに以下を発明させない。

```text
存在しない数値
存在しない秒数
存在しない距離
存在しないStatus Effect
存在しない発動条件
存在しないクールダウン
存在しない対象
```

---

# 第28章：Structured Perk Effect Model

## 28.1 目的

自然言語の効果文のみでは、

- 正確な検索
- 発動判定
- Fact Validation
- パーク間比較
- Timelineとの照合
- 戦術推論

が不安定になる。

そのため、効果を機械可読化する。

---

## 28.2 基本形式

```json
{
  "trigger": {},
  "requirements": [],
  "effects": [],
  "limitations": [],
  "cooldown": null,
  "charges": null,
  "tokens": null
}
```

---

## 28.3 Trigger Enum

初期候補:

```text
FAST_VAULT
SLOW_VAULT
GENERATOR_START
GENERATOR_REPAIR
GENERATOR_COMPLETE
HEAL_START
HEAL_COMPLETE
UNHOOK
HOOK
DOWN
INJURE
CHASE_START
CHASE_END
TOTEM_CLEANSE
TOTEM_BLESS
PALLET_DROP
PALLET_STUN
PALLET_VAULT
WINDOW_VAULT
BLIND
LOCKER_ENTER
LOCKER_EXIT
EXIT_GATE_POWERED
EXIT_GATE_OPEN
OBSESSION_CHANGE
KILLER_POWER_USE
MATCH_START
MATCH_END
MANUAL_ACTIVATION
PASSIVE
UNKNOWN_TRIGGER
```

---

## 28.4 Effect Enum

```text
HASTE
HINDERED
EXHAUSTED
ENDURANCE
BROKEN
EXPOSED
OBLIVIOUS
UNDETECTABLE
AURA_REVEAL
OBJECT_BLOCK
PROGRESS_MODIFIER
REGRESSION_MODIFIER
HEAL_MODIFIER
ACTION_SPEED_MODIFIER
TOKEN_ADD
TOKEN_REMOVE
COOLDOWN
SCREAM
SCRATCH_MARK_MODIFIER
BLOOD_POOL_MODIFIER
NOISE_NOTIFICATION
TERROR_RADIUS_MODIFIER
RESET_OBJECT
HIDE_AURA
UNKNOWN_EFFECT
```

---

## 28.5 数値モデル

単一値ではなくティア・条件付き数値を表現できるようにする。

```json
{
  "value": {
    "tiers": [10, 12.5, 15],
    "unit": "PERCENT"
  }
}
```

単一値:

```json
{
  "value": {
    "fixed": 3,
    "unit": "SECONDS"
  }
}
```

---

## 28.6 条件式

```json
{
  "requirements": [
    {
      "field": "player_state.injured",
      "operator": "EQ",
      "value": true
    }
  ]
}
```

複雑な条件式は将来、

```text
AND
OR
NOT
```

を持つExpression Treeへ拡張する。

---

# 第29章：Tags / Search Taxonomy

## 29.1 Survivor初期タグ

```text
CHASE
GENERATOR
HEALING
UNHOOK
STEALTH
INFORMATION
AURA
EXHAUSTION
ANTI_TUNNEL
ANTI_CAMP
ENDGAME
TOTEM
TEAM_SUPPORT
ITEM
CHEST
MOVEMENT
PALLET
WINDOW
RECOVERY
SABOTAGE
BOON
```

---

## 29.2 Killer初期タグ

```text
GENERATOR_REGRESSION
GENERATOR_BLOCK
CHASE
TRACKING
AURA
STEALTH
TERROR_RADIUS
EXPOSED
HOOK
SCOURGE_HOOK
HEX
TOTEM
ENDGAME
ANTI_HEAL
ANTI_PALLET
ANTI_VAULT
OBSESSION
MOVEMENT
INFORMATION
ANTI_LOOP
```

---

## 29.3 タグの扱い

タグは、

```text
公式仕様
```

ではなく、

```text
検索・分類用メタデータ
```

である。

よって、Factと混同しない。

---

# 第30章：Source Provenance

## 30.1 出典の責任

各Revisionは必ずSourceへ接続する。

```sql
CREATE TABLE perk_sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    authority TEXT NOT NULL,
    environment TEXT,
    url TEXT,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    locale TEXT,
    content_hash TEXT,
    rights_status TEXT
);
```

---

## 30.2 Authority Class

```text
GAME_CLIENT
BHVR_OFFICIAL
OFFICIAL_CHARACTER_PAGE
OFFICIAL_PATCH_NOTE
OFFICIAL_WIKI
MANUAL_VERIFIED
COMMUNITY_REFERENCE
UNKNOWN
```

---

## 30.3 Revisionとの関係

```sql
CREATE TABLE perk_revision_sources (
    revision_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    PRIMARY KEY (revision_id, source_id, purpose)
);
```

`purpose`:

```text
NAME
ICON
OFFICIAL_EFFECT
CHANGE_HISTORY
STRUCTURE_EVIDENCE
VERIFICATION
```

---

## 30.4 Source優先順位

初期方針:

```text
S0 現行ゲーム内確認
S1 Behaviour LIVE Patch Notes
S2 Behaviour公式Character Page
S3 Official DbD Wiki
S4 Human Verified Manual Correction
S5 その他参考
```

ただし、単一優先順位だけではなく、情報項目ごとにSource Authorityを持つ。

---

# 第31章：Rights Registryとの統合

## 31.1 既存Rights Registryを拡張する

Ver.2.0のRights Registryは主に動画Sourceを想定していたが、本追補ではKnowledge Assetにも拡張する。

対象:

```text
video
audio
transcript
perk icon
screenshot
wiki image
patch note excerpt
generated derivative
```

---

## 31.2 Perk Asset Rights

```json
{
  "asset_id": "PERK-ASSET-001",
  "asset_type": "PERK_ICON",
  "source_id": "SRC-PERK-001",
  "copyright_owner": "UNKNOWN_OR_DECLARED_OWNER",
  "license_class": "REFERENCE_ONLY",
  "training_allowed": true,
  "redistribution_allowed": false,
  "commercial_use_allowed": false,
  "review_status": "APPROVED_FOR_INTERNAL_ANALYSIS"
}
```

---

## 31.3 内部利用と配布を分離

```text
Internal Analysis Asset
≠
Redistributable Asset
```

モデル学習・特徴量生成へ使用可能でも、パークアイコン原画像をアプリ配布物へ同梱できるとは限らない。

---

# 第32章：Perk Asset / Icon Reference Model

## 32.1 `perk_assets`

```sql
CREATE TABLE perk_assets (
    asset_id TEXT PRIMARY KEY,
    perk_id TEXT NOT NULL,
    revision_id TEXT,
    asset_type TEXT NOT NULL,
    source_id TEXT,
    local_path TEXT,
    sha256 TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    mime_type TEXT,
    visual_variant TEXT,
    rights_status TEXT,
    created_at TEXT NOT NULL
);
```

---

## 32.2 visual_variant

```text
MASTER
NORMALIZED
EDGE
BINARY
AUGMENTED
REAL_FRAME
ACTIVE_STATE
DISABLED_STATE
COOLDOWN_STATE
UNKNOWN_STATE
```

---

## 32.3 アイコンとパーク状態を分離

同じパークでもUI上の表示状態が変化する。

```json
{
  "perk_id": "perk_xxx",
  "visual_state": {
    "active": true,
    "disabled": false,
    "cooldown": false,
    "dimmed": false
  }
}
```

`perk_id classification` と `visual state classification` は別Detectorとして扱う。

---

# 第33章：Perk Icon Recognition Pipeline

## 33.1 位置付け

本機能は、既存第5章 Vision Pipeline の一部として追加する。

新規責任:

```text
Vision Tier 1.5:
Perk HUD Recognition
```

または実装上は `perk_detector.py` としてTier 1に含めてもよい。

---

## 33.2 処理フロー

```text
Frame
 ↓
HUD Profile Resolve
 ↓
Perk Area ROI
 ↓
Slot Detection
 ↓
P1 / P2 / P3 / P4 Crop
 ↓
Preprocess
 ↓
Fingerprint Match
 ↓
Template Match
 ↓
Image Embedding Match
 ↓
Top-K Fusion
 ↓
Temporal Voting
 ↓
perk_id / UNKNOWN
 ↓
Visual State Detector
 ↓
Canonical Timeline Observation
```

---

## 33.3 HUD Profile依存

パークROIを固定座標1種類へハードコードしない。

```json
{
  "profile_id": "DBD-HUD-PERK-EXAMPLE",
  "game_version": "x",
  "resolution": [1920, 1080],
  "hud_scale": 100,
  "perspective": "SURVIVOR",
  "perk_slots": [
    [0.01, 0.83, 0.05, 0.90],
    [0.05, 0.83, 0.09, 0.90],
    [0.09, 0.83, 0.13, 0.90],
    [0.13, 0.83, 0.17, 0.90]
  ]
}
```

上記座標は例示であり、Gold Datasetで確定する。

---

## 33.4 Preprocess

```text
resize
center normalize
grayscale
contrast normalize
background suppression
edge extraction
binary representation
```

Representation:

```text
RGB
GRAY
EDGE
BINARY
```

---

## 33.5 Stage A: Fast Fingerprint

```text
pHash
dHash
aHash
```

のいずれかまたは複数を使う。

高一致の場合のみ高速確定候補とする。

---

## 33.6 Stage B: Template Match

既存OpenCV資産と整合させる。

```text
cv2.matchTemplate
```

ただし、単一テンプレートのみでは確定しない。

---

## 33.7 Stage C: Image Embedding

```text
input crop
 ↓
Image Encoder
 ↓
embedding
 ↓
master icon embedding matrix
 ↓
cosine similarity
 ↓
Top-K
```

初期段階では、パーク数が数百規模であるため、大規模Vector Databaseは必須としない。

```text
NumPy Matrix
```

または既存のローカルEmbedding Indexへ格納する。

---

## 33.8 Fusion

例:

```text
final_score
 =
 fingerprint_score * w1
 + template_score * w2
 + embedding_score * w3
 + temporal_score * w4
```

実際の重みはGold Datasetで校正する。

---

## 33.9 Temporal Voting

動画では単一フレームを確定値にしない。

```text
Frame N     → perk_A 0.88
Frame N+1   → perk_A 0.96
Frame N+2   → perk_A 0.97
Frame N+3   → UNKNOWN
Frame N+4   → perk_A 0.95

        ↓

Temporal Aggregation

        ↓

perk_A confidence=0.978
```

---

## 33.10 Confidence State

初期論理:

```text
AUTO_ACCEPT
NEEDS_SECONDARY_CHECK
TOP_K_CANDIDATE
UNKNOWN
```

具体的閾値は固定値で決めず、Gold Dataset上で校正する。

---

## 33.11 Unknown優先

```text
誤ったperk_idを高信頼として確定する
```

より、

```text
UNKNOWN
```

を返す方を正しい動作とする。

---

# 第34章：Recognition Dataset

## 34.1 Dataset構成

```text
datasets/
└── perk_recognition/
    ├── master/
    ├── synthetic/
    ├── real_frames/
    ├── hard_negatives/
    ├── unknown/
    └── gold/
```

---

## 34.2 Synthetic Augmentation

```text
resize
blur
JPEG compression
video compression
brightness
contrast
noise
partial crop
color shift
darkening
scaling artifact
HUD overlay noise
stream overlay contamination
```

---

## 34.3 Real Frame

実動画から切り出した、

```text
720p
1080p
1440p
21:9
配信圧縮
録画圧縮
UI scale違い
```

を含める。

---

## 34.4 Hard Negative

似ているパーク同士を明示的に登録する。

```json
{
  "perk_id": "perk_A",
  "hard_negatives": [
    "perk_B",
    "perk_C"
  ]
}
```

---

# 第35章：Canonical Game Event Timelineへの統合

## 35.1 Perk情報はEvent Evidenceとして格納する

Perk Knowledge BaseをTimelineの代替にしない。

---

## 35.2 Loadout Observation

例:

```json
{
  "observation_id": "PERKOBS-0001",
  "match_id": "MATCH-0001",
  "timestamp": 12.43,
  "slot": 1,
  "perk_id": "perk_survivor_example",
  "recognition_confidence": 0.97,
  "visual_state": "NORMAL",
  "hud_profile_id": "DBD-HUD-...",
  "evidence_ref": "vision/perks/12.43-slot1.json",
  "review_status": "AUTO_ACCEPTED"
}
```

---

## 35.3 Knowledge Reference

Timeline側はEffect全文を複製しない。

```json
{
  "perk_ref": {
    "perk_id": "perk_survivor_example",
    "revision_id": "PERKREV-001",
    "game_version": "x.x.x",
    "knowledge_status": "VERIFIED"
  }
}
```

これによりFact修正時にTimeline全件を書き換える必要を減らす。

---

## 35.4 Perk Activation Event

十分なEvidenceがある場合のみ、

```text
PERK_ACTIVATION_CONFIRMED
```

とする。

Evidence不足時:

```text
PERK_ACTIVATION_CANDIDATE
```

---

## 35.5 Event Type拡張

第6章Event Typeへ以下を追加候補とする。

```text
PERK_LOADOUT_OBSERVED
PERK_STATE_CHANGED
PERK_ACTIVATION_CANDIDATE
PERK_ACTIVATION_CONFIRMED
PERK_COOLDOWN_CANDIDATE
PERK_COOLDOWN_CONFIRMED
PERK_DISABLED
PERK_REENABLED
PERK_UNKNOWN
```

ただし、Perkごとの複雑な状態をすべてEvent Typeへ平坦化しない。

詳細は `perk_state` と `structured_effect` へ保持する。

---

# 第36章：Perk Activation Reasoner

## 36.1 目的

単に「装備しているパーク」を認識するだけでなく、

```text
その瞬間に発動条件を満たしていたか
```

を評価する。

---

## 36.2 入力

```text
Canonical Timeline
+
Current Player State
+
Observed Perk Loadout
+
Verified Structured Effect
+
Game Version
```

---

## 36.3 出力

```json
{
  "perk_id": "perk_xxx",
  "timestamp": 331.42,
  "activation_state": "POSSIBLE",
  "confidence": 0.82,
  "requirements": [
    {
      "condition": "player_state.injured == true",
      "status": "SATISFIED"
    },
    {
      "condition": "cooldown == false",
      "status": "UNKNOWN"
    }
  ],
  "evidence": [
    "EVT-...",
    "PERKOBS-..."
  ]
}
```

---

## 36.4 Activation State

```text
CONFIRMED
LIKELY
POSSIBLE
UNLIKELY
NOT_AVAILABLE
UNKNOWN
```

---

## 36.5 Intent推定との分離

```text
パークが発動可能だった
```

と、

```text
プレイヤーがそのパークを意図的に狙った
```

は別である。

後者を強く断定しない。

---

# 第37章：RAGへの統合

## 37.1 Perk IDが既知の場合

Vector Searchを使わない。

```text
perk_id
 ↓
Exact Canonical Lookup
 ↓
Patch-compatible Verified Revision
```

を優先する。

---

## 37.2 自然言語質問の場合

例:

```text
発電機を触っている時にキラーが分かるパーク
```

フロー:

```text
Query
 ↓
Name / Alias Exact Match
 ↓
Structured Filter
 ↓
SQLite FTS
 ↓
Semantic Retrieval
 ↓
Rerank
 ↓
Verified Revision Check
```

---

## 37.3 Hybrid Retrieval

```text
Final Score
=
name score
+ alias score
+ lexical score
+ semantic score
+ tag score
+ structured effect score
+ patch compatibility
+ source authority
```

---

## 37.4 Vector Database方針

Perk単体が数百件規模の間は、専用Vector DBを必須としない。

ただし本プラットフォーム全体では、

```text
PERK
ADDON
MAP
TACTIC
COMMENTARY_EXAMPLE
MATCH_EVENT
PATCH_NOTE
```

などをRAG対象とする。

そのため、

> **Perk Subsystemが独自Vector DBを持つのではなく、プラットフォーム共通RAG Providerへ接続する**

ことを推奨する。

---

## 37.5 Repository Interface

```python
class PerkKnowledgeRepository:
    def get_current_verified_revision(
        self,
        perk_id: str,
        game_version: str
    ):
        ...

    def search(
        self,
        query: str,
        filters: dict
    ):
        ...
```

これによりSQLiteから将来別Backendへ変更可能。

---

# 第38章：LoRA / Fine-tuningとの関係

## 38.1 知識をLoRAへ詰め込まない

パークの、

```text
正式効果
数値
パッチ変更
```

は主としてKnowledge Base / RAGで扱う。

---

## 38.2 LoRA対象

既存方針を維持し、

```text
実況構造
説明順序
DbD語彙
テンポ
情報密度
感情量
盤面の優先順位付け
```

を中心にする。

---

## 38.3 Training DatasetへのPerk Fact埋め込み

学習レコードには、必要に応じて

```json
{
  "knowledge_refs": [
    {
      "type": "PERK_REVISION",
      "id": "PERKREV-001"
    }
  ]
}
```

を持たせる。

---

## 38.4 Patch Leak対策

古いパーク仕様を含むDatasetをそのまま現行Fact学習として扱わない。

```text
Style Training
```

と、

```text
Current Fact Grounding
```

を分離する。

---

# 第39章：Explanation Generator / Validator

## 39.1 生成入力

```text
perk_id
name
role
official_effect
structured_effect
game_terms
patch
```

---

## 39.2 出力

```json
{
  "simple": "...",
  "beginner": "...",
  "short": "...",
  "when_useful": "...",
  "limitations": "..."
}
```

---

## 39.3 Numeric Hallucination Validator

正式仕様に、

```text
15%
3秒
60秒
```

しか存在しない場合、説明文に

```text
20%
```

が出たら、

```text
HALLUCINATED_NUMBER
```

としてRejectする。

---

## 39.4 Fact Constraint

チェック対象:

```text
number
percent
seconds
meters
tokens
charges
target
status effect
trigger
cooldown
tier
```

---

## 39.5 Validator結果

```text
PASS
WARNING
FAIL
```

FAILの場合 `VERIFIED` へ昇格しない。

---

# 第40章：Fact Validatorへの統合

既存第10章Fact ValidatorへPerk検証を追加する。

チェック項目:

```text
現在PatchとRevisionが互換か
Timeline上のperk_idとKnowledge Revisionが対応しているか
装備未確認のパークを発動済みと断定していないか
Evidence不足のPerk Activationを確定していないか
古い効果を参照していないか
説明中の数値がCanonical Effectと一致するか
Cooldown/Token/Status条件を捏造していないか
PTB情報をLIVEとして使用していないか
```

---

# 第41章：Job Manifestへの追加

## 41.1 Stage追加

```text
perk_asset_prepare
perk_icon_recognition
perk_loadout_resolve
perk_knowledge_resolve
perk_activation_reasoning
perk_fact_validation
```

---

## 41.2 Manifest例

```json
{
  "stages": {
    "vision": "SUCCESS",
    "perk_icon_recognition": "SUCCESS",
    "perk_loadout_resolve": "SUCCESS",
    "perk_knowledge_resolve": "SUCCESS",
    "perk_activation_reasoning": "NEEDS_REVIEW",
    "perk_fact_validation": "READY"
  }
}
```

---

## 41.3 Resume Invalidation

以下変更時はPerk関連Stageを再実行する。

```text
HUD Profile変更
Perk Recognition Model変更
Perk Asset Hash変更
Perk Knowledge Revision変更
Game Version変更
Recognition Threshold変更
Structured Effect Parser変更
```

---

# 第42章：ディレクトリ構成追加

既存構成へ以下を追加する。

```text
dbd_video_intelligence/
├── config/
│   ├── runtime/
│   ├── hud_profiles/
│   ├── perk_profiles/
│   └── policies/
│
├── knowledge/
│   └── perks/
│       ├── db/
│       ├── migrations/
│       ├── collectors/
│       ├── parsers/
│       ├── normalize/
│       ├── explain/
│       ├── validators/
│       └── exports/
│
├── assets/
│   └── perks/
│       ├── master/
│       ├── normalized/
│       └── recognition/
│
├── vision_pipeline/
│   └── detectors/
│       ├── generator_detector.py
│       ├── survivor_state_detector.py
│       ├── chase_detector.py
│       ├── perk_slot_detector.py
│       ├── perk_icon_detector.py
│       └── perk_visual_state_detector.py
│
├── event_pipeline/
│   ├── perk_observation_writer.py
│   └── perk_activation_reasoner.py
│
├── rag/
│   ├── providers/
│   └── perk_retriever.py
│
├── datasets/
│   └── perk_recognition/
│       ├── master/
│       ├── synthetic/
│       ├── real_frames/
│       ├── hard_negatives/
│       └── gold/
│
└── tests/
    └── perks/
```

---

# 第43章：JSONL Export

## 43.1 用途

SQLiteをPerk Fact Canonical Storeとし、JSONLは、

```text
RAG
offline evaluation
dataset generation
debug
portable export
```

用途とする。

---

## 43.2 1行1Revision

```json
{
  "schema_version": "1.0",
  "perk_id": "perk_survivor_example",
  "revision_id": "PERKREV-001",
  "environment": "LIVE",
  "game_version_from": "x.x.x",
  "game_version_to": null,
  "status": "VERIFIED",
  "role": "SURVIVOR",
  "name": {
    "ja": "日本語名",
    "en": "English Name"
  },
  "effect": {
    "official_ja": "...",
    "official_en": "...",
    "structured": {
      "trigger": {},
      "requirements": [],
      "effects": [],
      "limitations": []
    }
  },
  "explanation": {
    "simple_ja": "...",
    "beginner_ja": "...",
    "short_ja": "..."
  },
  "tags": [
    "CHASE"
  ],
  "icon": {
    "asset_id": "PERK-ASSET-001",
    "sha256": "..."
  },
  "sources": [
    {
      "source_id": "SRC-...",
      "authority": "BHVR_OFFICIAL"
    }
  ]
}
```

---

# 第44章：Perk Knowledge Collector

## 44.1 Collector責任

Collectorは、

```text
取得
```

のみを責任とし、

```text
VERIFIED決定
```

をしない。

---

## 44.2 Collector種類

```text
BHVR Character Collector
BHVR Patch Note Collector
Official Wiki Collector
Manual Import Collector
Game Client Manual Verification Import
```

---

## 44.3 Raw Preservation

取得時は正規化前のRawを保存する。

```text
data/
└── perks/
    ├── raw/
    ├── staging/
    ├── verified/
    └── exports/
```

---

## 44.4 Content Hash

各取得物にHashを付与する。

```text
SHA-256
```

同一Sourceの内容変更を検出する。

---

# 第45章：Patch Update Pipeline

```text
Patch Source Discovery
 ↓
New Version Detection
 ↓
LIVE / PTB Classification
 ↓
Perk Change Candidate Extraction
 ↓
Existing Revision Match
 ↓
Diff
 ↓
Structured Effect Reparse
 ↓
Explanation Revalidation
 ↓
Recognition Asset Impact Check
 ↓
Human Review
 ↓
New VERIFIED Revision
 ↓
RAG Index Update
 ↓
Regression Test
```

---

## 45.1 Icon変更検出

Patch変更時は効果文だけではなく、

```text
icon hash
```

も比較する。

アイコンが変更された場合、

```text
Recognition Reference Rebuild Required
```

とする。

---

# 第46章：Perk Gold Dataset / KPI

## 46.1 Vision KPI

```text
Top-1 Accuracy
Top-3 Accuracy
False Positive Rate
False Negative Rate
Unknown Detection Rate
Calibration Error
Temporal Stability
Per-slot Accuracy
```

---

## 46.2 Knowledge KPI

```text
Source Coverage
Verified Revision Coverage
Patch Compatibility Accuracy
Structured Effect Accuracy
Numeric Extraction Accuracy
Localization Match Accuracy
```

---

## 46.3 RAG KPI

```text
Exact Perk Lookup Accuracy
Alias Resolution Accuracy
Recall@K
Precision@K
Patch-compatible Retrieval Rate
Source Provenance Coverage
```

---

## 46.4 Commentary KPI

```text
Perk Fact Accuracy
Activation Claim Accuracy
Abstention Correctness
Human Tactical Score
Human Acceptance Rate
```

---

# 第47章：Perk-specific Test Suite

## 47.1 Database

```text
perk_id unique
slug unique
role valid
revision source required
LIVE VERIFIED revision consistency
no overlapping invalid revision ranges
asset hash required
localization key unique
```

---

## 47.2 Structured Effect

```text
unknown enum rejection
negative duration rejection
invalid percentage rejection
invalid tier cardinality rejection
unknown target rejection
condition schema validation
```

---

## 47.3 Explanation

```text
hallucinated number = 0
hallucinated status effect = 0
trigger mutation = 0
LIVE/PTB confusion = 0
```

---

## 47.4 Vision

以下を含むGold Datasetを作る。

```text
低解像度
高圧縮
一部欠損
暗転
グレー化
発動中
UI Scale違い
21:9
配信Overlay
Hard Negative
Unknown icon
```

---

## 47.5 Timeline Integration

```text
perk observation timestamp consistency
perk revision resolution consistency
event evidence exists
unknown patch fail-closed
activation candidate does not become confirmed without evidence
```

---

# 第48章：Human Gate追加項目

Human Review UIへ最低限追加する。

```text
Frame Preview
Perk Slot Crop
Top-3 Perk Candidate
Confidence
Selected Perk
Visual State
Game Version
Resolved Revision
Official Effect
Structured Effect
Explanation
Source
Activation Candidate
Evidence
Approve / Correct / Reject
```

---

## 48.1 Correction Learning

人が修正した場合:

```json
{
  "review_type": "PERK_RECOGNITION",
  "original_perk_id": "perk_A",
  "corrected_perk_id": "perk_B",
  "frame_ref": "...",
  "reason": "hard_negative_confusion"
}
```

Hard Negative Datasetへ追加候補とする。

---

# 第49章：Fail-closed追加条件

以下を成功扱いにしない。

```text
perk_id未解決なのに確定パークとして出力
Patch不明なのに現行効果として断定
Revisionなし
Sourceなし
PTBしかない情報をLIVE扱い
Recognition confidence不足
Perk asset hash不整合
Structured Effect parse fail
Explanation validator fail
Knowledge RevisionとTimeline game_version不整合
```

---

# 第50章：RAG / LLMプロンプト制約

LLM System Ruleへ以下を追加する。

```text
Perk Knowledge Baseに存在しない効果を推測しない。

数値を推測しない。

LIVEとPTBを混同しない。

perk_idがUNKNOWNの場合、
候補を断定しない。

game_versionと互換なVERIFIED Revisionを優先する。

Timeline EvidenceにないPerk Activationを確定しない。

「発動可能」と「実際に発動した」を区別する。

「発動した」と「プレイヤーが意図して使用した」を区別する。

根拠不足時はUNKNOWNまたはNEEDS_REVIEWを許容する。
```

---

# 第51章：Commentary Plannerとの接続

## 51.1 発話価値

すべてのパーク状態を実況しない。

Commentary Plannerは、

```text
event significance
perk tactical relevance
novelty
viewer educational value
time available
speech congestion
confidence
```

を基に発話するか決定する。

---

## 51.2 例

```text
単に常時装備しているパーク
→ 原則発話不要

重要チェイス中に発動したパーク
→ 高Priority

勝敗へ大きく影響したパークシナジー
→ 高Priority

Evidenceが弱い推定
→ 発話しないか不確実性を明示
```

---

# 第52章：Perk Interaction / Synergy Model

## 52.1 V1

V1ではシナジーをLLMだけに自由推論させず、

```text
Structured Effect
+
Tag
+
Trigger
+
Timeline
```

を根拠にする。

---

## 52.2 Interaction Record

将来:

```json
{
  "interaction_id": "INT-001",
  "perk_a": "perk_A",
  "perk_b": "perk_B",
  "interaction_type": "SYNERGY",
  "conditions": [],
  "patch_from": "x.x.x",
  "patch_to": null,
  "source_type": "ANALYTICAL",
  "confidence": 0.81,
  "review_status": "VERIFIED"
}
```

---

## 52.3 唯一解禁止

戦術的シナジーや強弱は、

```text
FACT
```

ではなく、

```text
TACTICAL INTERPRETATION
```

として分離する。

---

# 第53章：ASRとの接続

実況・解説中にパーク名が発話された場合、

```text
ASR text
 ↓
Perk Alias Resolver
 ↓
perk_id candidate
 ↓
Vision EvidenceとのCross-check
```

を可能にする。

---

## 53.1 ASR Alias

例:

```text
正式名
略称
俗称
旧名
誤認識候補
```

を `perk_aliases` に保持する。

---

## 53.2 Cross-modal Evidence

```text
Visionでperk_A 0.82
+
ASRでperk_A名称を発話
+
Timeline上で効果条件一致
```

の場合、総合confidenceを上げられる。

ただし、発話が一般論である可能性もあるため、単純一致で確定しない。

---

# 第54章：Cross-modal Perk Evidence

Perk判定は将来的に以下を統合できる。

```text
HUD icon
ASR mention
on-screen effect
status icon
animation
game event
commentator statement
```

---

## 54.1 Evidence Record

```json
{
  "evidence_id": "PEV-001",
  "perk_id": "perk_xxx",
  "timestamp": 331.42,
  "evidence_type": "HUD_ICON",
  "confidence": 0.96,
  "source_ref": "vision/perk-slot-1.json"
}
```

---

## 54.2 Evidence Type

```text
HUD_ICON
ASR_MENTION
VISUAL_EFFECT
STATUS_CHANGE
TIMELINE_CONDITION
COMMENTATOR_CLAIM
MANUAL_REVIEW
```

---

# 第55章：Knowledge BaseとCanonical Timelineの二重管理防止

以下を禁止する。

```text
Perk Effect全文をTimeline全イベントへコピー
```

理由:

- Patch修正時の更新困難
- 同一情報の不整合
- Dataset肥大化
- Provenance複雑化

Timelineは、

```text
perk_id
revision_id
knowledge_ref
```

を保持する。

---

# 第56章：データ更新時の再処理範囲

## 56.1 Official Effectのみ変更

```text
Perk KB Revision
RAG Index
Fact Validator
必要なCommentary再生成
```

を再実行。

Icon Recognition自体は再実行不要な場合がある。

---

## 56.2 Icon変更

```text
Perk Asset
Embedding
Recognition Regression
必要に応じて過去Frame再判定
```

を再実行。

---

## 56.3 HUD変更

```text
HUD Profile
Slot Detector
Vision Gold Dataset
Recognition Pipeline
```

を再検証。

---

## 56.4 Structured Effect Parser変更

```text
全Verified Revisionを再parse候補
Explanation Validator
Activation Reasoner Regression
```

を再実行する。

---

# 第57章：Artifact Version Manifest

```json
{
  "perk_kb_schema_version": "1.0",
  "perk_kb_data_version": "2026-08-17",
  "icon_reference_version": "1",
  "structured_effect_schema_version": "1.0",
  "recognizer_model_version": "1",
  "hud_profile_version": "1",
  "embedding_model_version": "1",
  "rag_index_version": "1"
}
```

Job Manifestへ記録する。

---

# 第58章：バックアップ / Restore

既存P2のBackup / RestoreへPerk KBを含める。

対象:

```text
SQLite DB
Migration files
Raw source snapshots
Verified JSONL export
Asset hashes
Master icon assets
Embedding index
Tag taxonomy
Structured Effect schema
Human corrections
Gold Dataset labels
```

---

# 第59章：開発タスクへの正式挿入

既存TASK-001〜TASK-020を壊さず、以下をサブタスクとして割り込ませる。

```text
TASK-007   Vision HUD PoC
   └── TASK-007A Perk HUD ROI / Slot Detection PoC

TASK-008   Patch Profile / State Machine
   ├── TASK-008A Perk Canonical Schema / Revision Model
   ├── TASK-008B Perk Source / Collector / Baseline Import
   └── TASK-008C Perk Icon Recognition Reference Build

TASK-009   Canonical Event Timeline
   └── TASK-009A Perk Observation / Knowledge Ref / Activation Candidate

TASK-010   Human Review Minimum UI
   └── TASK-010A Perk Recognition / Effect Review UI

TASK-011   Gold Dataset / Benchmark
   └── TASK-011A Perk Icon Recognition Gold Dataset / KPI

TASK-012   RAG
   └── TASK-012A Perk Exact Lookup / Patch-aware Retrieval / Alias Search

TASK-013   Dataset Curator
   └── TASK-013A Perk Fact / Explanation Dataset Curator

TASK-015   Commentary Planner / Validator
   └── TASK-015A Perk Fact Validator / Activation Explanation

TASK-019   Regression / Backup / Restore
   └── TASK-019A Perk KB / Icon / Patch Regression

TASK-020   Production Pilot
   └── TASK-020A Perk Intelligence End-to-End Pilot
```

---

## 59.1 実装順序

推奨順:

```text
TASK-007A
 ↓
TASK-008A
 ↓
TASK-008B
 ↓
TASK-008C
 ↓
TASK-011A
 ↓
TASK-009A
 ↓
TASK-010A
 ↓
TASK-012A
 ↓
TASK-013A
 ↓
TASK-015A
 ↓
TASK-019A
 ↓
TASK-020A
```

ただし、

```text
TASK-008A Perk Canonical Schema
```

はVision認識の前倒し実装に必要となる場合があるため、TASK-007Aと並行開始を許容する。

---

# 第60章：開発ゲートへの追加

## P1追加条件

```text
[ ] Perk Canonical Schema
[ ] Perk Revision Model
[ ] Source Provenance
[ ] LIVE / PTB Separation
[ ] Perk HUD Slot Detection
[ ] Icon Recognition UNKNOWN handling
[ ] Perk Gold Dataset
[ ] Recognition KPI
[ ] Timeline Perk Observation Schema
```

---

## P2追加条件

```text
[ ] Patch-aware Perk Retrieval
[ ] Perk Fact Validator
[ ] Explanation Hallucination Validator
[ ] Perk Human Review
[ ] Rights Metadata
[ ] Regression Test
[ ] Backup / Restore
```

---

# 第61章：Perk Acceptance Gate

## 61.1 Canonical Knowledge

```text
100% perk_id unique
100% VERIFIED RevisionにSourceが存在
100% VERIFIED Revisionにgame_version/environmentが存在
100% RAG Fact回答は互換Revisionを優先
PTBをLIVEとして返す件数 = 0
```

---

## 61.2 Explanation

```text
幻覚数値 = 0
発動条件改変 = 0
存在しないStatus Effect = 0
```

---

## 61.3 Vision

目標値はGold Datasetで確定するが、

```text
Top-1 Accuracy
Top-3 Accuracy
False Positive Rate
Unknown Detection Rate
Calibration Error
```

を必須測定する。

高精度目標を設定する場合も、

```text
誤認識よりUNKNOWNを優先
```

する。

---

## 61.4 End-to-End

以下のケースを再現できること。

```text
動画
 ↓
Perk HUD抽出
 ↓
perk_id
 ↓
Patch-compatible Revision
 ↓
Timeline Knowledge Ref
 ↓
RAG
 ↓
Commentary
 ↓
Fact Validator
 ↓
Human Gate
```

---

# 第62章：例：Timeline + Perk Knowledge統合レコード

```json
{
  "event_id": "EVT-000123",
  "match_id": "MATCH-0001",
  "timestamp_start": 331.42,
  "timestamp_end": 334.10,
  "event_type": "WINDOW_VAULT",
  "game_version": "x.x.x",
  "perspective": "SURVIVOR",
  "generator_remaining": 3,

  "perk_context": {
    "loadout": [
      {
        "slot": 1,
        "perk_id": "perk_survivor_example",
        "recognition_confidence": 0.97,
        "revision_id": "PERKREV-001",
        "knowledge_status": "VERIFIED"
      }
    ],

    "activation_candidates": [
      {
        "perk_id": "perk_survivor_example",
        "state": "POSSIBLE",
        "confidence": 0.82,
        "requirements": [
          {
            "condition": "example_condition",
            "status": "SATISFIED"
          }
        ]
      }
    ]
  },

  "evidence": [
    {
      "type": "PERK_HUD_ICON",
      "ref": "vision/perks/331.42-slot1.json",
      "confidence": 0.97
    },
    {
      "type": "VISION_EVENT",
      "ref": "vision/window-vault-331.42.json",
      "confidence": 0.91
    }
  ],

  "review_status": "AUTO_ACCEPTED"
}
```

---

# 第63章：最終的な学習・推論責任境界

## 63.1 Perk Knowledge Base

覚えるもの:

```text
正式名
翻訳
効果
数値
発動条件
Patch履歴
構造化仕様
出典
```

---

## 63.2 Vision

覚えるもの:

```text
アイコン外観
HUD位置
表示状態
映像上の特徴
```

---

## 63.3 RAG

担当:

```text
現在Patchに適合する事実取得
自然言語検索
戦術知識検索
過去類似Event検索
Source Provenance
```

---

## 63.4 LoRA

担当:

```text
実況構造
説明順序
語彙
テンポ
感情量
説明密度
```

---

## 63.5 LLM Reasoning

担当:

```text
何が起きたか
なぜ重要か
どのパークが関係するか
何が確定で何が推定か
視聴者へどう説明するか
```

---

# 第64章：この統合で得られる最終機能

Perk Knowledge Intelligence Subsystemを統合すると、同一プラットフォームで以下が可能になる。

```text
動画から装備4パークを自動認識
```

```text
その試合バージョンに対応する正式効果を取得
```

```text
パークが発動可能だった局面を抽出
```

```text
発動候補と確定発動を区別
```

```text
実況者がパークへ言及した箇所と盤面を結合
```

```text
「なぜこの場面でこのパークが強かったか」を説明
```

```text
同一パークのパッチ差分を考慮して過去大会動画を分析
```

```text
プレイヤーのパーク構成傾向を統計化
```

```text
チェイス中のパーク活用分析
```

```text
パークシナジーの解説
```

```text
古いパーク仕様を現行仕様として誤って実況する事故を防止
```

---

# 第65章：統合後の完成像

```text
VIDEO
 │
 ├── Audio
 │     ├── VAD
 │     ├── ASR
 │     └── Speaker
 │
 ├── Vision
 │     ├── Generator
 │     ├── Survivor State
 │     ├── Chase
 │     ├── Objects
 │     └── Perk HUD
 │            ↓
 │       perk_id candidate
 │            ↓
 │     Perk Knowledge Base
 │            ├── Current Revision
 │            ├── Structured Effect
 │            ├── Source
 │            └── Explanation
 │
 └──────────────┬──────────────────────
                ↓
       Canonical Game Event Timeline
                │
      ┌─────────┴──────────┐
      ↓                    ↓
     RAG              Training Dataset
      │                    │
      └─────────┬──────────┘
                ↓
            LLM / LoRA
                ↓
       Commentary Planner
                ↓
          Fact Validator
                ↓
            Human Gate
                ↓
              Output
```

---

# 第66章：統合判断

本追補による正式判断は以下とする。

```text
Perk Knowledge Base:
    独立プロジェクトとして扱わない

Perk Icon Recognition:
    Vision Pipelineの正式サブシステム

Perk Canonical Store:
    Game KnowledgeのCanonical Fact Store

Canonical Game Event Timeline:
    引き続きシステム全体の中心

RAG:
    Perk Factと最新Patchを取得する主経路

LoRA:
    Perk Fact暗記ではなく実況・説明スタイル学習

LLM:
    Evidence + Canonical Knowledgeを基に説明

Human Gate:
    認識・Revision・説明・発動推定の最終訂正点
```

---

# 第67章：追補後のDefinition of Done追加

既存付録Cへ以下を追加条件とする。

15. パークアイコン認識が `perk_id / UNKNOWN` として出力される
16. `perk_id` から対象パッチ互換のRevisionを解決できる
17. LIVEとPTBを分離できる
18. パーク効果にSource Provenanceが存在する
19. パーク効果とLLM説明の数値矛盾を検出できる
20. Perk ObservationをCanonical TimelineへEvidence付きで格納できる
21. 発動可能・発動候補・発動確定を区別できる
22. アイコン誤認識をHuman Gateで訂正できる
23. 訂正結果をGold Dataset / Hard Negativeへ戻せる
24. Patch変更後に影響範囲をDiffできる
25. 古いRevisionが現行実況へ混入しない
26. Asset Rightsを追跡できる
27. Perk KnowledgeをRAGから出典付きで取得できる
28. Perk関連変更後にRegression Testを実行できる

---

# 第68章：本追補による設計変更サマリー

単独のPerk KB設計から、本プラットフォーム統合時に変更した点を明示する。

| 項目 | 単独設計時 | 統合後 |
|---|---|---|
| システム中心 | SQLite KB | Canonical Game Event Timeline |
| SQLite | 全体Source of Truth | Perk Fact Canonical Store |
| Vision | 独立Perk認識 | 既存Vision Pipeline配下 |
| RAG | Perk専用 | Platform共通RAGへ統合 |
| Vector DB | Perk側で判断 | 共通RAG Provider方針に従う |
| Patch Profile | Perk独自 | 既存DbD Patch Profileと共有 |
| HUD Profile | Perk独自 | 既存HUD Profileへ拡張 |
| Human Gate | Perk専用 | Platform Human Gateへ統合 |
| Rights | Perk Asset単独管理 | 既存Rights Registryへ統合 |
| Job | 独立Pipeline | 既存Job ManifestへStage追加 |
| Gold Dataset | Perk単独 | Platform Gold Dataset配下 |
| LoRA | 説明学習 | 既存方針どおりStyle中心 |
| Fact | KB | KB + Timeline Evidence |
| Activation | LLM推論 | Structured Effect + Timeline + Evidence |
| 出力 | パーク説明 | 実況・解説・分析へ利用 |

---

# 追補終章

本追補で追加したPerk Knowledge Intelligence Subsystemは、単なるパーク辞書でも、アイコン分類器でもない。

その役割は、

> **動画内で観測されたパーク情報を、Patch互換・出典付き・検証可能なゲーム知識へ接続し、Canonical Game Event Timeline上のEvidenceとして扱えるようにすること**

である。

これにより、本プラットフォームは、

```text
「画面左下にこのパークがある」
```

という画像認識だけで終わらず、

```text
このパークは何か
↓
この試合バージョンでは何をするか
↓
この局面で発動条件を満たしていたか
↓
実際に発動したEvidenceがあるか
↓
その結果、盤面へどのような意味を持ったか
↓
実況として何を、どの程度の確信度で説明すべきか
```

までを一つの追跡可能な処理系として扱える。

したがって、統合後の本システムの本質は引き続き、

> **DbD Video Intelligence Platform**

であり、Perk Knowledge Intelligence Subsystemはその中の重要な **Game Knowledge / Vision / RAG Bridge** として正式採用する。

---

**End of Ver.2.1 Addendum**


---

# Ver.2.2 追補：DbD Game Knowledge Intelligence Subsystem 一般化設計

> **追補日**: 2026-08-17
> **対象**: `Dead by Daylight Video Intelligence Platform / 解説・実況自動生成AIシステム`
> **前提**: Ver.2.0本文およびVer.2.1 Perk Knowledge Intelligence追補を全文保持する。
> **変更目的**: Ver.2.1でパーク中心に定義したCanonical Knowledgeを、マップ、キラー、キラー能力、アドオン、サバイバー、アイテム、オファリング、タイル、ゲームメカニクス、ステータス効果等へ一般化する。
> **優先規則**: Ver.2.1の「Perk Knowledge Intelligence Subsystem」という名称・責任境界は、本追補以降、より上位概念である `DbD Game Knowledge Intelligence Subsystem` の配下サブドメインとして解釈する。

---

# 第69章：設計変更の結論

本システムが蓄積すべき対象はパークだけではない。

最終的なKnowledge Domainは次のように定義する。

```text
DbD Game Knowledge Intelligence Subsystem
│
├── Perk Knowledge
├── Killer Knowledge
│   ├── Killer Identity
│   ├── Power
│   ├── Power State
│   ├── Killer-specific Mechanics
│   └── Counterplay Knowledge
│
├── Survivor Knowledge
├── Map Knowledge
│   ├── Realm
│   ├── Map
│   ├── Main Building
│   ├── Landmark
│   ├── Tile / Jungle Gym
│   ├── Shack
│   └── Generation Constraints
│
├── Add-on Knowledge
├── Item Knowledge
├── Offering Knowledge
├── Status Effect Knowledge
├── Game Mechanic Knowledge
├── Object Knowledge
├── Interaction Knowledge
├── Patch Knowledge
├── Terminology / Alias Knowledge
└── Tactical Interpretation Knowledge
```

Ver.2.1のPerk Knowledge Baseはこの中の、

```text
Game Knowledge
└── Perk Knowledge
```

へ位置付けを変更する。

---

# 第70章：システム全体の中心は引き続きCanonical Game Event Timeline

Game Knowledgeを大規模化しても、システム全体の中心データモデルは変更しない。

```text
Canonical Game Event Timeline
```

が、

> **その試合で何が起きたか**

を保持する。

Game Knowledge Storeは、

> **そのゲーム要素が、そのパッチにおいて何であり、どのような仕様・特徴・関係を持つか**

を保持する。

責任境界:

```text
Canonical Game Event Timeline
    = Match-specific Truth / Observation

Game Knowledge Intelligence
    = Game-wide Canonical Knowledge

Vision / Audio
    = Evidence Acquisition

RAG
    = Knowledge Retrieval

LLM / LoRA
    = Explanation / Reasoning / Style

Human Gate
    = Correction / Approval
```

---

# 第71章：Knowledge Entity共通モデル

## 71.1 すべてのゲーム知識を共通Entityとして扱う

共通識別子:

```text
entity_id
entity_type
canonical_slug
introduced_version
retired_version
active_status
```

`entity_type` 初期候補:

```text
PERK
KILLER
KILLER_POWER
KILLER_POWER_STATE
SURVIVOR
MAP
REALM
MAP_FEATURE
LANDMARK
MAIN_BUILDING
TILE
OBJECT
ADDON
ITEM
OFFERING
STATUS_EFFECT
GAME_MECHANIC
ACTION
INTERACTION
PATCH
TACTIC
TERM
```

---

## 71.2 `game_entities`

概念スキーマ:

```sql
CREATE TABLE game_entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    canonical_slug TEXT NOT NULL,
    introduced_version TEXT,
    retired_version TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(entity_type, canonical_slug)
);
```

Perk専用テーブルは残してよいが、上位共通Entityへ接続する。

---

# 第72章：Localization / Alias共通化

## 72.1 `entity_localizations`

```sql
CREATE TABLE entity_localizations (
    entity_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    name TEXT NOT NULL,
    short_description TEXT,
    official_description TEXT,
    PRIMARY KEY (entity_id, locale)
);
```

---

## 72.2 `entity_aliases`

```sql
CREATE TABLE entity_aliases (
    alias_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0
);
```

Alias Type:

```text
COMMUNITY
ABBREVIATION
OLD_NAME
TRANSLITERATION
ASR_VARIANT
OCR_VARIANT
SEARCH_SYNONYM
MANUAL
```

これにより、

```text
パーク俗称
キラー略称
マップ略称
実況者固有の呼び方
ASR誤認識
```

を同じ仕組みで解決できる。

---

# 第73章：Knowledge Revision共通化

## 73.1 パーク以外もPatchで変わる

Revision対象:

```text
Perk
Killer Power
Killer Base Stat
Add-on
Map
Tile Rule
Object Placement Rule
Status Effect
Core Mechanic
```

---

## 73.2 `entity_revisions`

```sql
CREATE TABLE entity_revisions (
    revision_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    game_version_from TEXT NOT NULL,
    game_version_to TEXT,
    environment TEXT NOT NULL,
    status TEXT NOT NULL,
    structured_payload_json TEXT,
    content_hash TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    created_at TEXT NOT NULL,
    verified_at TEXT
);
```

`environment`:

```text
LIVE
PTB
ARCHIVE
UNKNOWN
```

---

# 第74章：Killer Knowledge Model

## 74.1 Killer Identity

保持対象:

```text
killer_id
name_ja
name_en
canonical_name
aliases
chapter
release_version
base_movement_speed
terror_radius
height_class
power_id
official_description
source
revision
```

ただし、数値や分類はRevision管理し、固定値として埋め込まない。

---

## 74.2 Killer Power

```text
Killer
  ↓ HAS_POWER
Killer Power
  ├── activation
  ├── resource
  ├── state
  ├── cooldown
  ├── range
  ├── movement modifier
  ├── attack interaction
  ├── survivor interaction
  ├── map object interaction
  └── visual/audio cues
```

---

## 74.3 Power Structured Model

例示スキーマ:

```json
{
  "activation": {
    "action": "POWER_ACTIVATE"
  },
  "resources": [],
  "states": [],
  "effects": [],
  "limitations": [],
  "cooldowns": [],
  "visual_cues": [],
  "audio_cues": []
}
```

---

## 74.4 Killer Power State

動画解析に重要なため、能力そのものと現在状態を分離する。

```text
READY
CHARGING
ACTIVE
COOLDOWN
RESOURCE_EMPTY
DISABLED
UNKNOWN
```

キラー固有に別Stateが必要な場合は、汎用State＋固有Substateを持つ。

---

## 74.5 Killer-specific Mechanics

例:

```text
特殊移動
設置物
感染/蓄積
マーク
テレポート
罠
能力ゲージ
召喚物
固有オブジェクト
特殊攻撃
変身
ステルス
探知
```

これらは自由文章だけでなく、可能な範囲で構造化する。

---

# 第75章：Killer Visual / Audio Recognition

## 75.1 Recognition対象

```text
Killer Model
Killer Weapon
Power Object
Power VFX
Power HUD
Unique Prop
Audio Cue
Animation
```

---

## 75.2 Killer Recognition出力

```json
{
  "killer_id": "killer_xxx",
  "confidence": 0.93,
  "evidence": [
    {
      "type": "VISUAL_MODEL",
      "confidence": 0.91
    },
    {
      "type": "POWER_OBJECT",
      "confidence": 0.87
    }
  ],
  "review_status": "AUTO_ACCEPTED"
}
```

---

## 75.3 単一特徴依存禁止

```text
一瞬映った武器だけ
```

など、単一Evidenceで確定しない。

複数Evidenceを統合できる設計とする。

---

# 第76章：Killer Counterplay Knowledge

## 76.1 FactとTacticを分離

```text
Killer Powerの仕様
```

はFact。

```text
その能力に対する一般的な対策
```

はTactical Interpretation。

---

## 76.2 Tactical Record

```json
{
  "tactic_id": "TACTIC-...",
  "subject_entity_id": "killer_xxx",
  "situation": {},
  "recommendation": "...",
  "patch_from": "x.x.x",
  "patch_to": null,
  "source_refs": [],
  "confidence": 0.84,
  "review_status": "VERIFIED"
}
```

複数見解を許容する。

---

# 第77章：Map Knowledge Model

## 77.1 重要原則

DbDマップは、

```text
「マップ名を覚える」
```

だけでは不十分。

最低限、

```text
Realm
Map
Map Variant
Main Building
Landmark
Killer Shack
Tile
Jungle Gym
Window
Pallet
Generator Area
Exit Gate Area
Basement Candidate
Special Object
Generation Rule
```

を分離する。

---

## 77.2 Mapと実試合Layoutを分離

Canonical Map Knowledge:

```text
このマップ一般にどのような特徴があるか
```

Match Layout Observation:

```text
この試合ではどこに何が生成されたか
```

両者を混同しない。

---

## 77.3 `maps`

```sql
CREATE TABLE maps (
    map_id TEXT PRIMARY KEY,
    realm_id TEXT,
    entity_id TEXT NOT NULL,
    indoor_class TEXT,
    base_environment TEXT,
    created_at TEXT NOT NULL
);
```

詳細はRevision側に保持する。

---

## 77.4 Map Structured Features

```json
{
  "realm_id": "realm_xxx",
  "environment": "OUTDOOR",
  "main_building": {
    "present": true,
    "type": "..."
  },
  "killer_shack": {
    "possible": true
  },
  "landmarks": [],
  "tile_families": [],
  "special_objects": [],
  "generation_constraints": []
}
```

---

# 第78章：Map Feature / Landmark

## 78.1 Map Feature Entity

```text
MAP_FEATURE
LANDMARK
MAIN_BUILDING
```

を独立Entityとして持てるようにする。

例:

```text
大きな中央建築
固有窓
階段
高低差
屋内通路
長い壁
特殊ゲート
視認性の高いランドマーク
```

---

## 78.2 Relation

```text
MAP
 ├── HAS_LANDMARK
 ├── HAS_MAIN_BUILDING
 ├── MAY_GENERATE_TILE
 ├── HAS_SPECIAL_OBJECT
 └── BELONGS_TO_REALM
```

---

# 第79章：Tile / Jungle Gym Knowledge

## 79.1 Tileはマップと別Entity

```text
Tile Family
Tile Variant
Observed Tile Instance
```

に分ける。

---

## 79.2 Tile Knowledge

保持候補:

```text
tile_id
tile_family
window_candidates
pallet_candidates
wall_structure
entry_points
loop_direction_characteristics
visibility_characteristics
common_connections
patch_revision
```

---

## 79.3 Observed Tile Instance

Timeline/Match Spatial Model側:

```json
{
  "tile_instance_id": "TILEINST-001",
  "match_id": "MATCH-001",
  "tile_id": "tile_xxx",
  "position": null,
  "orientation": "UNKNOWN",
  "confidence": 0.81,
  "evidence": []
}
```

位置が正確に取れない場合は推測座標を作らない。

---

# 第80章：Map Vision Recognition

## 80.1 目的

Vision Tier 3を拡張し、

```text
Map Identification
Landmark Recognition
Main Building Recognition
Tile Candidate Recognition
```

を行う。

---

## 80.2 Map Recognition Evidence

```text
Loading Screen Metadata
Visual Landmark
Architecture
Color / Lighting
Ground Texture
Unique Object
Main Building
HUD / Text if available
```

複数Evidenceで統合する。

---

## 80.3 Map Confidence

```text
CONFIRMED
LIKELY
CANDIDATE
UNKNOWN
```

マップ類似環境では断定しない。

---

# 第81章：Map-specific Tactical Knowledge

以下はFactと分離して保存する。

```text
強いチェイスエリア
弱いチェイスエリア
見通し
巡回しやすさ
発電機防衛傾向
固有建築の使い方
キラーごとの相性
サバイバーごとの判断
```

---

## 81.1 Context-dependent Tactic

```json
{
  "tactic_id": "TACTIC-MAP-001",
  "subject_entity_id": "map_xxx",
  "related_entities": [
    "killer_xxx"
  ],
  "conditions": {
    "perspective": "SURVIVOR"
  },
  "claim": "...",
  "confidence": 0.79,
  "source_refs": []
}
```

---

# 第82章：Add-on Knowledge

## 82.1 Add-on Entity

```text
addon_id
owner_type
owner_entity_id
rarity
name
official_effect
structured_effect
revision
source
```

---

## 82.2 Killer Powerとの接続

```text
KILLER
 ↓ HAS_POWER
KILLER_POWER
 ↓ MODIFIED_BY
ADDON
```

---

## 82.3 Add-on Recognition

ロードアウト画面等から認識可能な場合は、

```text
ADDON_LOADOUT_OBSERVED
```

としてTimelineへ接続する。

認識不能な映像では推測しない。

---

# 第83章：Survivor / Item / Offering Knowledge

## 83.1 Survivor

最低限:

```text
survivor_id
name
aliases
chapter
release_version
unique_perks
source
```

サバイバー本体の基本性能が共通である場合、不要な差分を捏造しない。

---

## 83.2 Item

```text
ITEM
├── type
├── charges
├── interaction
├── addon compatibility
├── revision
└── source
```

---

## 83.3 Offering

```text
OFFERING
├── category
├── effect
├── target
├── map influence
├── revision
└── source
```

---

# 第84章：Status Effect Knowledge

## 84.1 独立Entity化

```text
HASTE
HINDERED
EXHAUSTED
ENDURANCE
BROKEN
EXPOSED
OBLIVIOUS
UNDETECTABLE
...
```

を文字列EnumだけでなくEntityとしても保持できる。

---

## 84.2 Relation

```text
PERK
 └── APPLIES_STATUS → STATUS_EFFECT

KILLER_POWER
 └── APPLIES_STATUS → STATUS_EFFECT

ADDON
 └── MODIFIES_STATUS → STATUS_EFFECT
```

これにより横断検索が可能になる。

---

# 第85章：Game Mechanic Knowledge

## 85.1 パーク・キラーとは独立した基礎ルール

例:

```text
CHASE
HOOK_STATE
GENERATOR_REPAIR
HEALING
VAULT
PALLET
AURA
TERROR_RADIUS
OBSESSION
TOTEM
HEX
BOON
SCOURGE_HOOK
ENDGAME
HATCH
EXIT_GATE
BASIC_ATTACK
SPECIAL_ATTACK
```

---

## 85.2 Mechanic Revision

ゲーム本体ルールが変更された場合もRevision管理する。

---

# 第86章：Object Knowledge

Visionとの接続のため、ゲーム内オブジェクトをEntity化する。

```text
GENERATOR
PALLET
WINDOW
LOCKER
HOOK
SCOURGE_HOOK
TOTEM
CHEST
EXIT_GATE
HATCH
BASEMENT
KILLER_SHACK
POWER_OBJECT
SPECIAL_MAP_OBJECT
```

---

# 第87章：Knowledge Graph Relation Model

## 87.1 Relation Table

```sql
CREATE TABLE entity_relations (
    relation_id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    object_entity_id TEXT NOT NULL,
    revision_id TEXT,
    confidence REAL,
    source_id TEXT,
    review_status TEXT
);
```

---

## 87.2 Relation Type初期候補

```text
BELONGS_TO
HAS_PERK
HAS_POWER
MODIFIED_BY
APPLIES_STATUS
TRIGGERS_ON
INTERACTS_WITH
COUNTERS
SYNERGIZES_WITH
WEAK_AGAINST
STRONG_AGAINST
APPEARS_ON
HAS_LANDMARK
HAS_TILE
MAY_GENERATE
USES_OBJECT
AFFECTS_ACTION
CHANGED_BY_PATCH
RELATED_TACTIC
```

---

## 87.3 Fact RelationとAnalytical Relationを分離

```text
HAS_POWER
BELONGS_TO
```

はFact。

```text
COUNTERS
SYNERGIZES_WITH
STRONG_AGAINST
```

はAnalytical/Tactical Relation。

`relation_class` を持たせてもよい。

---

# 第88章：Canonical Game Event Timeline拡張

## 88.1 Knowledge References

イベントは必要に応じて複数Knowledge Entityを参照する。

```json
{
  "knowledge_refs": [
    {
      "entity_type": "KILLER",
      "entity_id": "killer_xxx",
      "revision_id": "REV-KILLER-001"
    },
    {
      "entity_type": "MAP",
      "entity_id": "map_xxx",
      "revision_id": "REV-MAP-001"
    },
    {
      "entity_type": "PERK",
      "entity_id": "perk_xxx",
      "revision_id": "REV-PERK-001"
    }
  ]
}
```

---

## 88.2 Match Context

Timelineとは別に、Match Context Snapshotを持つ。

```json
{
  "match_id": "MATCH-001",
  "game_version": "x.x.x",
  "map": {
    "map_id": "map_xxx",
    "confidence": 0.94
  },
  "killer": {
    "killer_id": "killer_xxx",
    "confidence": 0.98
  },
  "survivor_loadout": [],
  "observed_addons": [],
  "observed_offerings": []
}
```

---

# 第89章：Spatial Match Model

マップ知識を実戦解析へ利用するため、将来 `Canonical Match Spatial Model` を追加可能とする。

```text
Canonical Game Event Timeline
    = 時間軸

Canonical Match Spatial Model
    = 空間構造
```

---

## 89.1 初期段階

位置推定精度が不十分な段階では、

```text
AREA_A
MAIN_BUILDING
SHACK_SIDE
GEN_CLUSTER
UNKNOWN_AREA
```

などの論理領域でよい。

---

## 89.2 将来

十分なEvidenceが得られる場合、

```text
Observed Tile Graph
Landmark Graph
Player Route
Generator Cluster
Hook Distribution Observation
```

へ拡張できる。

---

# 第90章：RAGのGame Knowledge一般化

## 90.1 Search Domain

RAG対象を正式に以下へ拡張する。

```text
PATCH_NOTE
PERK
ADDON
KILLER
KILLER_POWER
SURVIVOR
ITEM
OFFERING
MAP
REALM
MAP_FEATURE
TILE
STATUS_EFFECT
GAME_MECHANIC
OBJECT
TACTIC
COMMENTARY_EXAMPLE
MATCH_EVENT
```

---

## 90.2 Retrieval Route

```text
1. Entity Resolution
   - exact ID
   - name
   - alias
   - ASR variant

2. Structured Filter
   - game_version
   - mode
   - killer
   - map
   - entity_type
   - event_type

3. Canonical Fact Lookup

4. Semantic Retrieval

5. Tactical / Historical Retrieval

6. Patch Compatibility

7. Source Provenance

8. Confidence / Abstention
```

---

## 90.3 Exact Lookup優先

Entity IDが判明している場合:

```text
Vector Search
```

より、

```text
Canonical Exact Lookup
```

を優先する。

---

# 第91章：LLMへ渡すGame Context

例:

```json
{
  "query": "このチェイスでなぜ板を温存したのか説明してください",
  "match_context": {
    "game_version": "x.x.x",
    "killer_id": "killer_xxx",
    "map_id": "map_xxx"
  },
  "event": {
    "event_id": "EVT-001",
    "event_type": "CHASE"
  },
  "knowledge": {
    "killer_power": {},
    "map_features": [],
    "tile": {},
    "perks": []
  },
  "tactical_viewpoints": []
}
```

---

# 第92章：LLMの事実と推論の分離

LLM出力内部モデル:

```text
OBSERVED FACT
CANONICAL FACT
INFERRED STATE
TACTICAL INTERPRETATION
COMMENTARY EXPRESSION
```

を概念的に分離する。

---

## 92.1 例

```text
OBSERVED:
キラーが板付近へ接近した。

CANONICAL:
このキラー能力には○○という仕様がある。

INFERRED:
能力使用を警戒していた可能性がある。

TACTICAL:
板を即倒ししない選択には合理性がある。

COMMENTARY:
「ここ、すぐ板を倒さず能力を見ていますね。」
```

断定レベルを階層化する。

---

# 第93章：Cross-modal Entity Resolution

## 93.1 Killer

```text
Visual Model
+
Power VFX
+
Audio Cue
+
ASR Mention
+
Unique Object
=
killer_id confidence
```

---

## 93.2 Map

```text
Landmark
+
Architecture
+
Lighting
+
Main Building
+
ASR Mention
=
map_id confidence
```

---

## 93.3 Perk

```text
HUD Icon
+
ASR Mention
+
Effect Observation
=
perk_id confidence
```

---

# 第94章：Game Knowledge Collector一般化

## 94.1 Collector Interface

```python
class KnowledgeCollector:
    def collect(self) -> list:
        raise NotImplementedError
```

---

## 94.2 Domain Collectors

```text
PerkCollector
KillerCollector
KillerPowerCollector
AddonCollector
MapCollector
TileCollector
MechanicCollector
PatchCollector
ManualVerifiedCollector
```

---

## 94.3 CollectorはFact確定しない

```text
COLLECTED
 ↓
PARSED
 ↓
NORMALIZED
 ↓
STRUCTURED
 ↓
VALIDATED
 ↓
HUMAN_REVIEW
 ↓
VERIFIED
```

---

# 第95章：Game Knowledge JSONL

共通Export形式:

```json
{
  "schema_version": "2.0",
  "entity_id": "killer_xxx",
  "entity_type": "KILLER",
  "revision_id": "REV-...",
  "environment": "LIVE",
  "game_version_from": "x.x.x",
  "game_version_to": null,
  "status": "VERIFIED",
  "names": {
    "ja-JP": "...",
    "en-US": "..."
  },
  "structured": {},
  "tags": [],
  "relations": [],
  "assets": [],
  "sources": []
}
```

Perk専用JSONLは互換Exportとして残してよい。

---

# 第96章：SQLite構成方針

V1ではSQLiteを継続採用する。

ただし構造は、

```text
Common Entity Tables
+
Domain-specific Tables
```

のハイブリッドとする。

---

## 96.1 Common

```text
game_entities
entity_localizations
entity_aliases
entity_revisions
entity_sources
entity_assets
entity_relations
```

---

## 96.2 Domain-specific

```text
perks
perk_effect_nodes

killers
killer_powers
killer_power_states

maps
map_features
tiles

addons
items
offerings

status_effects
game_mechanics
```

---

# 第97章：Game Knowledge StoreとRAG Storeの分離

```text
Canonical Game Knowledge Store
```

は事実の正本。

```text
RAG Index
```

は検索用派生物。

RAG indexを正本にしてはならない。

---

## 97.1 Rebuild可能性

```text
Canonical DB
 ↓
Deterministic Export
 ↓
Chunking
 ↓
Embedding
 ↓
RAG Index
```

RAG Indexは再生成可能であること。

---

# 第98章：Map / Killer Gold Dataset

## 98.1 Killer

```text
killer visual identity
power activation
power object
power visual cue
power audio cue
hard negative
unknown
```

---

## 98.2 Map

```text
map identity
main building
landmark
tile candidate
indoor/outdoor
hard negative
unknown
```

---

## 98.3 Metrics

```text
Top-1 Accuracy
Top-3 Accuracy
Unknown Detection Rate
False Positive Rate
Calibration Error
Temporal Stability
Cross-modal Resolution Accuracy
```

---

# 第99章：Human Review UI一般化

既存Perk ReviewをGame Knowledge Reviewへ拡張する。

最低表示:

```text
Frame / Clip
Detected Entity Type
Top Candidates
Confidence
Current Patch
Resolved Entity
Revision
Canonical Facts
Structured Data
Relations
Source
Cross-modal Evidence
Approve
Correct
Reject
Mark Unknown
```

---

# 第100章：Fact Validator一般化

チェック対象:

```text
Perk Effect
Killer Power
Killer Identity
Map Identity
Map Feature
Tile Claim
Add-on Effect
Status Effect
Game Mechanic
Patch Compatibility
Source Provenance
```

---

## 100.1 Map Fact Validator

禁止例:

```text
この試合では必ずこの位置に板がある
```

を、Canonical Map Knowledgeだけから断定しない。

手続き生成要素はMatch Observation Evidenceが必要。

---

## 100.2 Killer Fact Validator

```text
Killer-specific Power Fact
```

と、

```text
プレイヤーがその能力を使おうとした意図
```

を分離する。

---

# 第101章：Tactical Knowledge Layer

## 101.1 Tactical KnowledgeはCanonical Factと別Store/Classification

```text
FACT
TACTIC
VIEWPOINT
HEURISTIC
STATISTICAL_PATTERN
```

を区別する。

---

## 101.2 例

Fact:

```text
この能力は○○条件で発動する。
```

Tactic:

```text
このマップでは能力を○○に使うと強い場合が多い。
```

Viewpoint:

```text
解説者Aはこの場面でタゲチェンを推奨した。
```

同一階層へ混ぜない。

---

# 第102章：将来の戦術Knowledge Graph

```text
KILLER
 ├── HAS_POWER → POWER
 ├── MODIFIED_BY → ADDON
 ├── STRONG_AGAINST → TACTIC / OBJECT
 └── RELATED_TO → MAP

MAP
 ├── HAS_FEATURE → LANDMARK
 ├── MAY_GENERATE → TILE
 ├── RELATED_TACTIC → TACTIC
 └── MATCH_OBSERVATION → TILE_INSTANCE

PERK
 ├── APPLIES_STATUS → STATUS_EFFECT
 ├── TRIGGERS_ON → ACTION
 └── SYNERGIZES_WITH → PERK

MATCH_EVENT
 ├── OBSERVED_ENTITY → KILLER / MAP / PERK
 ├── OCCURS_AT → MAP_AREA
 └── SUPPORTED_BY → EVIDENCE
```

---

# 第103章：開発タスク再編

Ver.2.1のPerkサブタスクを残しつつ、Game Knowledgeへ拡張する。

```text
TASK-008A  Game Knowledge Common Schema
TASK-008B  Perk Domain Schema / Import
TASK-008C  Killer / Power Domain Schema / Import
TASK-008D  Map / Feature / Tile Domain Schema / Import
TASK-008E  Add-on / Item / Offering / Mechanic Schema
TASK-008F  Source Provenance / Revision / LIVE-PTB Governance
```

Vision:

```text
TASK-007A  Perk HUD Recognition
TASK-007B  Killer Identity / Power Cue PoC
TASK-007C  Map / Landmark Recognition PoC
```

Timeline:

```text
TASK-009A  Perk Observation
TASK-009B  Killer / Power Observation
TASK-009C  Map / Tile Observation
TASK-009D  Knowledge Ref Integration
```

RAG:

```text
TASK-012A  Common Entity Resolver
TASK-012B  Exact Canonical Lookup
TASK-012C  Patch-aware Hybrid Retrieval
TASK-012D  Tactical / Match Retrieval
```

Validation:

```text
TASK-015A  Perk Fact Validator
TASK-015B  Killer Power Fact Validator
TASK-015C  Map / Procedural Claim Validator
TASK-015D  Cross-domain Commentary Validator
```

---

# 第104章：推奨実装順序 Ver.2.2

```text
1. Common Game Knowledge Schema
2. Revision / Provenance / Rights
3. Perk Domain
4. Killer / Power Domain
5. Map / Feature / Tile Domain
6. Status Effect / Mechanic Domain
7. Add-on / Item / Offering Domain
8. Common Entity Resolver
9. Vision Perk Recognition
10. Vision Killer Recognition
11. Vision Map / Landmark Recognition
12. Canonical Timeline Knowledge References
13. RAG Integration
14. Fact Validators
15. Human Review UI
16. Gold Dataset / Regression
17. Tactical Knowledge Layer
18. End-to-End Commentary Pilot
```

---

# 第105章：Definition of Done追加 Ver.2.2

既存DoDに加え、以下を満たすこと。

29. パーク以外も共通 `entity_id` で管理できる
30. キラーとキラー能力を別Entityとして管理できる
31. キラー能力のRevisionをPatch-awareに解決できる
32. マップとRealmを分離できる
33. マップ一般知識と実試合生成Layoutを分離できる
34. Map Feature / Landmark / Tileを別Entityとして扱える
35. Add-onをPowerへRelationで接続できる
36. Status Effectを横断Entityとして参照できる
37. Game MechanicをPerk/Killerから独立管理できる
38. Timeline Eventから複数Knowledge Entityを参照できる
39. Killer Recognitionが `killer_id / UNKNOWN` を返せる
40. Map Recognitionが `map_id / UNKNOWN` を返せる
41. Procedural Map FactをEvidenceなしでMatch-specific Factへ昇格しない
42. RAGが共通Entity Resolverを経由する
43. Fact / Tactic / Viewpointを区別できる
44. Game Knowledge RAG IndexをCanonical DBから再構築できる
45. Killer / Map / Perk変更後に回帰試験できる
46. Cross-modal EvidenceでEntity confidenceを統合できる
47. Human GateでEntity誤認識・Revision誤解決を訂正できる

---

# 第106章：最終アーキテクチャ Ver.2.2

```text
                            SOURCE VIDEO
                                 │
             ┌───────────────────┼────────────────────┐
             │                   │                    │
             ↓                   ↓                    ↓
       AUDIO PIPELINE      VISION PIPELINE      RIGHTS/METADATA
             │                   │
             │          ┌────────┼────────┬──────────┐
             │          │        │        │          │
             │          ↓        ↓        ↓          ↓
             │        Perk     Killer    Map      Generic
             │        Vision    Vision   Vision      HUD
             │          │        │        │
             └──────────┴────┬───┴────────┘
                             ↓
                      EVIDENCE LAYER
                             │
                             ↓
                 ENTITY / STATE RESOLUTION
                             │
                             ↓
             ┌──────────────────────────────┐
             │ DbD GAME KNOWLEDGE STORE     │
             │                              │
             │ Perk                         │
             │ Killer / Power               │
             │ Map / Realm / Tile           │
             │ Add-on / Item / Offering     │
             │ Status / Mechanic            │
             │ Source / Revision / Rights   │
             └──────────────┬───────────────┘
                            │
                            ↓
                 CANONICAL GAME EVENT TIMELINE
                            │
                 ┌──────────┴───────────┐
                 │                      │
                 ↓                      ↓
                RAG              TRAINING DATASET
                 │                      │
                 └──────────┬───────────┘
                            ↓
                        LLM / LoRA
                            ↓
                   COMMENTARY PLANNER
                            ↓
                      FACT VALIDATOR
                            ↓
                       HUMAN GATE
                            ↓
                           OUTPUT
```

---

# 第107章：具体的に蓄積できる知識の例

## パーク

```text
何というパークか
誰のパークか
何をすると発動するか
何秒続くか
どのStatusを付与するか
現Patchではどうなっているか
過去Patchではどうだったか
俗称は何か
```

---

## キラー

```text
何というキラーか
能力は何か
能力の発動条件
能力のリソース
特殊攻撃
特殊オブジェクト
視覚的兆候
音響的兆候
アドオンによる変更
一般的な対策
マップとの相性に関する見解
```

---

## マップ

```text
Realm
正式マップ名
屋内/屋外
固有建築
ランドマーク
キラー小屋候補
生成され得るTile
特徴的な窓
特徴的な高低差
視認性
特殊オブジェクト
一般的なチェイス特徴
```

ただし、

```text
この試合の板・窓・発電機の正確な配置
```

はMatch Observationとして別管理する。

---

## タイル

```text
Tile Family
窓候補
板候補
壁構造
Loopの特徴
接続方向
Observed Instance
```

---

## 戦術

```text
このキラー相手に何を警戒するか
このMap Featureで何を優先するか
このPerk構成なら何が狙いか
複数解説者がどう評価したか
```

---

# 第108章：この一般化によるLLMの役割

LLMへ「DbD全部を記憶させる」ことは目的にしない。

LLMは、

```text
Canonical Game Knowledge
+
Canonical Game Event Timeline
+
Retrieved Tactical Knowledge
+
Commentary Style
```

を組み合わせ、

```text
この試合で何が起きたか
なぜ重要だったか
どのゲーム仕様が関係したか
何が確定で何が推測か
視聴者へどう説明するか
```

を生成する。

---

# 第109章：最終判断 Ver.2.2

今後の名称は、

```text
Perk Knowledge Intelligence Subsystem
```

ではなく、

> **DbD Game Knowledge Intelligence Subsystem**

を上位正式名称とする。

その配下に、

```text
Perk Intelligence
Killer Intelligence
Map Intelligence
Mechanic Intelligence
Tactical Intelligence
```

を置く。

これにより将来、

```text
パークだけに強いAI
```

ではなく、

> **DbDというゲーム世界の仕様・盤面・映像・戦術・解説を同じEntity/Revision/Evidence体系で理解するVideo Intelligence Platform**

へ拡張できる。

---

# Ver.2.2 追補終章

本変更によって、Knowledge Architectureの中心単位は、

```text
perk_id
```

から、

```text
entity_id
```

へ一般化される。

ただし、試合解析の中心はこれまでどおり、

```text
Canonical Game Event Timeline
```

である。

最終的なデータフローは、

```text
映像・音声
 ↓
Evidence
 ↓
Entity / State Resolution
 ↓
Patch-aware Canonical Game Knowledge
 ↓
Canonical Game Event Timeline
 ↓
RAG / Training Dataset
 ↓
LLM / LoRA
 ↓
Fact Validation
 ↓
Human Gate
 ↓
実況・解説・分析
```

とする。

この構造であれば、

- パーク
- キラー
- キラー能力
- アドオン
- マップ
- Realm
- 固有建築
- タイル
- Status Effect
- ゲームルール
- 戦術
- 過去試合の見解

を、個別に別システム化せず、同一のDbD Video Intelligence Platformへ継続的に蓄積できる。

---

**End of Ver.2.2 Addendum**
