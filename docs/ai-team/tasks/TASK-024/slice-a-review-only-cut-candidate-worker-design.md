# TASK-024 Slice A — Review-only Silence / Filler / Disfluency Cut Candidate Worker 詳細設計

- Project: `ai-video-production`
- Task: `TASK-024`
- Slice: `A`
- Candidate Release: `0.18.0`
- Date: `2026-08-12`
- Governance: `DEV-3`
- Status: `IMPLEMENTED / WINDOWS RELEASE-CANDIDATE VALIDATION PASS`
- Runtime Boundary: `STANDALONE_APPLICATION_REQUIRED`

## 1. 目的

編集前処理として、TASK-004 が生成する正規化済み分析音声と TASK-006 の Canonical Transcript を使い、
「無音」「フィラーのみの発話」「近接した完全一致の言い直し候補」を決定論的に抽出する。

この Slice は **候補を作るだけ** であり、動画・音声・DaVinci Resolve Timelineを変更しない。

責務は次のように固定する。

- `TASK-024`: Cut Candidate / Keep Block / text-free Evidence の生成。
- `TASK-007`: Candidate を統合し Canonical Cut/Edit Plan を決定。
- `TASK-010`: 承認済み Plan を Resolve Automation-owned Timeline へ実行。

`TASK-024` 単独では `auto_apply_authorized=false` を変更できない。

## 2. 選定理由

Canonical Roadmap の Editing-first Critical Path は
`001 → 002 → 003 → 004 → 022 → (006 + 023 + 024) → 007 → 010 → 011 → 012`。

v0.17.0 で TASK-006 Slice D の長尺ASR/字幕Handoffが完了したため、
次に利用者が直接「編集が楽になった」と感じやすく、かつ TASK-007/010 の前提となる
無音・フィラー・言い直し候補を前倒しする。

## 3. In Scope

1. 正規化済み16-bit PCM WAVの検証。
2. FFmpeg `silencedetect` による無音区間抽出。
3. FFmpegは固定argv / `shell=False` / bounded timeout。
4. 無音Cut候補の前後保護幅。
5. Transcript発話のKeep Block化。
6. Transcript Keep Blockと無音候補の衝突除去。
7. 日本語フィラー「segment全体がフィラーのみ」の保守的検出。
8. 近接する完全一致発話のうち前側だけを言い直し候補化。
9. Candidate/Keep Blockのdeterministic ordering / IDs / hash。
10. Candidate Manifestとtext-free operational report。
11. Transcript manifest hash検証。
12. Audio SHA-256を解析前後で再検証。
13. CLI `ai-video-cut-candidates`。
14. JSON Schema root/package同梱。
15. Release metadata / Project state / Roadmap同期。

## 4. Out of Scope

- 実際のCut。
- Resolve API mutation。
- Candidateの自動承認。
- 意味解析による高度な言い直し判定。
- Scene Boundary。
- Multimodal/OCR。
- DBD固有編集判断。
- AI ProviderへのTranscript送信。
- 音声本文/字幕本文をEvidenceへ保存。
- TASK-007の最終Edit Plan。
- TASK-010のTimeline mutation。

## 5. Input Contract

### 5.1 Analysis Audio

TASK-004で生成された分析用WAVを想定する。

必須条件:

- regular file
- symlinkではない
- PCM / uncompressed
- sample width = 16-bit
- channels = 1..8
- sample rate = 8 kHz..192 kHz
- frame count > 0

TASK-024はAudio pathをCanonical Evidenceへ記録しない。

### 5.2 Transcript

Transcriptは任意。

指定時:

- canonical TASK-006 `TranscriptManifest`
- `source_asset_id` が解析対象と一致
- `manifest_sha256` が本文と一致
- Transcript終端がAudio duration + toleranceを越えない
- 読込上限 64 MiB
- symlink拒否

Transcript本文はCandidate Manifest/Reportへ出力しない。

## 6. Silence Detection

FFmpeg commandは概念上次の固定構造。

```text
ffmpeg
  -hide_banner
  -nostdin
  -v info
  -nostats
  -i <analysis.wav>
  -map 0:a:0
  -vn -sn -dn
  -af silencedetect=noise=<threshold>dB:d=<minimum>
  -f null -
```

Shell interpolationは禁止する。

Default:

- threshold: `-45 dBFS`
- minimum silence: `500 ms`
- timeout: `1800 sec`
- preserve leading: `80 ms`
- preserve trailing: `120 ms`
- minimum candidate cut: `180 ms`

`silence_start` / `silence_end` は Decimal でmicrosecondへ変換する。
nested start、end-without-start、duration外、overlap/out-of-orderはfail-closed。

末尾無音で `silence_end` が出ない場合はWAV header由来durationでcloseする。

## 7. Transcript Analysis

### 7.1 Filler

Unicode NFKC、casefold、空白・句読点除去後に判定する。

Default filler dictionary:

- えー
- えっと
- ええと
- えーと
- あの
- あのー
- うーん
- んー
- あー

**Segment全体が filler sequence のみ** で、duration <= 2500 msの場合だけ候補化する。

発話中の一部分に filler が含まれるだけではCut候補にしない。

### 7.2 Repeated Utterance

隣接Segmentについて、

- normalized text完全一致
- minimum 4 characters
- gap <= 1500 ms
- filler segmentではない

場合のみ、前側を `REPEATED_UTTERANCE` candidateにする。
後側をKeep側に残す。

意味的類似やLLM推定はこのSliceでは行わない。

## 8. Keep Block

候補化されなかったTranscript Segmentを保護区間とする。

Default guard:

- start - 80 ms
- end + 80 ms

0..audio durationでclipし、重なり/接触をmergeする。

Silence CandidateはKeep Blockを必ずsubtractする。

最終Manifest constructorでも Candidate と Keep Block の overlap を拒否する。

## 9. Candidate Contract

Kinds:

- `SILENCE`
- `FILLER`
- `REPEATED_UTTERANCE`

共通:

- deterministic `cut-000001` format
- source range in microseconds / end-exclusive
- bounded `strength_score` 0..100
- machine-readable evidence codes
- safe source segment IDs only
- `action=REVIEW_ONLY`
- `auto_apply_authorized=false`

Silence evidence:

- `FFMPEG_SILENCEDETECT`
- 1.5秒以上なら `LONG_PAUSE`

Filler evidence:

- `FILLER_ONLY_SEGMENT`

Repeat evidence:

- `EXACT_ADJACENT_REPEAT`
- `KEEP_LATER_OCCURRENCE`

## 10. Manifest Contract

`cut-candidates.json`

- manifest_version
- task_owner = TASK-024
- downstream_plan_owner = TASK-007
- downstream_execution_owner = TASK-010
- source_asset_id
- analysis_audio_sha256
- analysis_sample_rate
- source_duration_us
- config_sha256
- transcript_manifest_sha256 nullable
- transcript_text_in_manifest = false
- auto_apply_authorized = false
- candidates
- keep_blocks
- manifest_sha256

Manifestはtext-free。

## 11. Operational Report

`cut-candidate-report.json`

本文を保存せず次だけを記録する。

- success
- source_asset_id
- analysis audio SHA
- duration
- candidate count / type count
- keep block count
- transcript used flag
- transcript_text_in_report=false
- auto_apply_authorized=false
- TASK ownership

FFmpeg stderr/stdoutの生内容をreportへ転記しない。

## 12. Integrity / Security

1. Audio symlink拒否。
2. Transcript symlink拒否。
3. Output directory symlink拒否。
4. Audio SHA-256を解析前後に取得し不一致でfail。
5. size/mtimeも解析前後に比較。
6. Transcript manifest hashを再計算。
7. Transcript source Asset不一致を拒否。
8. Transcript duration mismatchを拒否。
9. fixed argv / shell=False。
10. FFmpeg timeout。
11. candidate / keep block count upper bounds。
12. malformed FFmpeg event orderをfail。
13. Candidate collisionをfail。
14. No secret/provider call。
15. No BAI Development OS runtime dependency。

## 13. Default Bounds

| Parameter | Default |
|---|---:|
| silence_threshold_dbfs | -45.0 |
| min_silence_ms | 500 |
| min_cut_ms | 180 |
| preserve_leading_ms | 80 |
| preserve_trailing_ms | 120 |
| transcript_guard_ms | 80 |
| max_filler_ms | 2500 |
| repeat_max_gap_ms | 1500 |
| repeat_min_chars | 4 |
| transcript_duration_tolerance_ms | 500 |
| max_candidates | 100000 |
| max_keep_blocks | 100000 |
| ffmpeg_timeout_seconds | 1800 |

## 14. CLI

```powershell
ai-video-cut-candidates .\analysis.wav `
  --output-dir .\cut-analysis `
  --source-asset-id ASSET-... `
  --transcript .\transcript.json
```

主なoverride:

- `--silence-threshold-dbfs`
- `--min-silence-ms`
- `--min-cut-ms`
- `--preserve-leading-ms`
- `--preserve-trailing-ms`
- `--transcript-guard-ms`
- `--max-filler-ms`
- `--repeat-max-gap-ms`
- `--repeat-min-chars`
- `--ffmpeg-executable`
- `--ffmpeg-timeout-seconds`
- repeated `--filler-term`

## 15. Acceptance Gate

Focused:

- deterministic silence range
- keep-block subtraction
- filler-only detection
- exact-repeat earlier-only candidate
- short repetition not flagged
- no Transcript text leakage
- publication review-only contract
- transcript hash tamper detection
- source mutation fail-closed
- unsupported WAV fail-closed
- config hash stability
- fixed argv FFmpeg parser
- malformed event order fail-closed
- FFmpeg failure structured/no stderr leak
- transcript/audio duration mismatch
- CLI publication
- schema validation/package parity

Final Windows gate:

```text
python -m pytest -q
python -m compileall -q src tests
git diff --check
git fsck --full
```

Baseline v0.17.0 = 415 passed + 1 intentional skip.
This Slice adds 18 focused tests in the implementation pack, so nominal full-suite target is
433 passed + 1 intentional skip only if no additional concurrent test changes exist.
The actual pytest result is authoritative.

## 16. Critic Review

### Finding C1 — Pure Python sample-by-sample RMS would be too slow for long media
Rejected.
Production path uses existing FFmpeg silencedetect.

### Finding C2 — Filler substring auto-cut risks deleting meaningful speech
Rejected.
Only filler-only entire segments become review candidates.

### Finding C3 — Similarity-based rephrase detection is semantically unsafe
Deferred.
Slice A only flags exact normalized adjacent repetitions.

### Finding C4 — Silence may overlap speech because ASR timestamps are imperfect
Mitigated.
Transcript guard creates protected Keep Blocks and silence candidates subtract them.

### Finding C5 — Evidence can leak transcript text
Blocked by contract and regression.
Only segment IDs/reason codes/hash/counts are persisted.

### Finding C6 — Candidate generation could accidentally become an execution authority
Blocked.
Manifest hard-codes REVIEW_ONLY / auto_apply_authorized=false and records downstream TASK-007/TASK-010 ownership.

### Finding C7 — Large malformed input can exhaust resources
Mitigated.
Transcript size, candidate count, keep block count, FFmpeg timeout are bounded.

## 17. Judge Decision

`PASS FOR RELEASE-CANDIDATE COMMIT / PR`

No Product runtime dependency on BAI Development OS is introduced.
No Resolve mutation or paid Provider execution is introduced.

## 18. Final Windows Validation Evidence

- Full pytest: `433 passed, 1 intentional skip`
- compileall: PASS
- `git diff --check`: PASS
- `git fsck --full`: PASS (dangling historical local tags are informational and unrelated to TASK-024 content)
- Installed `ai-video-cut-candidates` CLI: PASS on a real 16-bit PCM WAV
- Real FFmpeg `silencedetect`: PASS; 5 review-only SILENCE candidates generated
- Manifest/report: text-free, `auto_apply_authorized=false`, TASK-024/TASK-007/TASK-010 ownership PASS
- Subtitle Workspace launch / Windows Open dialog / Cancel: PASS
- AI Connection Settings launch: PASS

Formal public release is not yet declared; protected-branch PR, CI, merge and v0.18.0 tag remain.
