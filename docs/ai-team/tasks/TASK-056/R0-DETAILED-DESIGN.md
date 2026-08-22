# TASK-056 R0 — Detailed Design

## 1. Contract evolution

### Transcript 1.0

Legacy callers keep `AsrRequest.include_word_timestamps == false` and the existing `TranscriptManifest 1.0.0` serialized shape. No `words` field is emitted.

### Transcript 1.1

Only explicit word-timestamp requests produce `TranscriptManifest 1.1.0`. Each segment may contain bounded `TranscriptWord` rows with canonical microsecond half-open ranges and nullable confidence. Invalid, reversed, overlapping or out-of-segment raw word timing is not repaired into precise evidence; it is dropped so detection can fall back to a REVIEW-only segment cue.

## 2. Keyword profile

`KeywordProfile` is local bounded configuration, not code-hardwired DBD logic. R0 supports only `EXACT` and `PHRASE`; no regex is accepted. Normalization is NFKC + casefold + punctuation/space normalization. Alias ownership conflicts fail closed.

Built-in profile `dbd-chase-call-ja-v1` contains `CHASE_CALL` aliases `チェイス`, `チェース`, `chase` and remains replaceable by a validated local profile.

## 3. Cue state

- `CONFIRMED`: exact WORD timing plus observed confidence >= profile threshold.
- `REVIEW`: missing word timing, missing confidence, or confidence below threshold.
- `REJECTED`: reserved for explicit downstream/Human rejection; R0 detector does not invent rejected hits.

A segment-timed fallback can never be `CONFIRMED`.

## 4. Duplicate semantics

Candidates are duplicate-merge eligible only when keyword and normalized match identity agree and their time ranges overlap, with shared provenance or sufficient deterministic IoU. Non-overlapping repeated calls remain separate even inside the same segment. Large-media core ownership prevents chunk-overlap replay; the detector still has a bounded duplicate merge as defense in depth.

## 5. Timebase

ASR times remain integer microseconds. Source frames use BVP `FrameRate.us_to_frame()` only:

- start: `FLOOR`
- end-exclusive: `CEIL`
- minimum one frame

No float FPS or millisecond re-rounding is canonical.

## 6. Identity and integrity

Manifest ID is deterministically derived from source asset, exact rational source rate, Transcript SHA and Profile SHA. Cue IDs are deterministically derived from Manifest identity plus semantic/timing/provenance fields. Same canonical input therefore yields byte-identical canonical JSON and SHA.

`SpeechCueManifest.from_dict()` and the Montage projection parser reject unknown fields, hash drift, count drift, malformed IDs/ranges, authority escalation and confirmed cues without WORD timing.

## 7. Privacy

Private Cue Manifest contains only opaque segment IDs plus keyword/timing metadata; no Transcript text, context text, media path or raw speaker. Montage projection removes segment provenance too. Operational report is written last as a text-free/path-free publication commit marker and binds both Manifest SHA and Projection SHA. `SpeechCuePublicationService.read_verified()` must re-bind the report, Manifest, projection, counts and each projected Cue before a consumer treats the set as complete.

CLI status prints only file basenames and counts, never absolute host paths.

## 8. Product/runtime boundary

R0 is local-only and reuses the existing FasterWhisper provider. The immediate Creator Application Service offers both a direct route and the existing bounded/resumable chunk route; resumability/checkpoint truth remains owned by `ResumableTranscriptionService`, not duplicated by TASK-056. `word_timestamps=True` is passed only when explicitly requested. Default model-download policy is unchanged. Tests use fake models only; they must not download a model or perform network access.

## 9. PR #269 coexistence

Current main is the PR #269 base. R0 avoids TASK-036 Product/Shell files. The one unavoidable overlap, `faster_whisper_asr.py`, is a narrow semantic extension around `transcribe()` / word parsing. Before TASK-056 merge, compare against the then-current PR #269/main and compose both changes explicitly.

## 10. Acceptance gates

- focused TASK-056 tests;
- existing TASK-006/023/large-media/timebase/TASK-022 regressions;
- schema mirror byte equality + meta-validation;
- compileall;
- `git diff --check`;
- no unresolved Critical/High Critic finding;
- real FasterWhisper/Windows runtime remains `NOT_RUN` unless actually executed.
