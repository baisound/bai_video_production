# TASK-006 Slice D — Large-Media Resume + Resolve Subtitle Handoff Detailed Design

## Status

`IMPLEMENTATION_PREPARED / VALIDATION_PENDING`

- Product development branch baseline: PR #10 merged main
- Base commit: `a098f881b095e3290d2562efe3846d9e2384806a`
- Governance profile: `DEV-3`
- Candidate package: `0.17.0`
- Handoff owner: `TASK-006`
- Actual DaVinci Resolve write owner: `TASK-010`

## Objectives

Slice D closes two bounded gaps without crossing the TASK-010 execution boundary:

1. make local FasterWhisper transcription practical for very large/long media through deterministic bounded audio chunks, atomic text-free checkpoints and explicit resume/restart;
2. compile the human Subtitle Workspace into a deterministic private Resolve subtitle-placement JSON plan with exact frame conversion.

The slice does not write, create or mutate a Resolve timeline or subtitle track.

## Large-media architecture

```text
source media
  -> ffprobe structural duration/audio validation
  -> streaming SHA-256 source fingerprint
  -> deterministic non-overlapping core chunk plan
  -> overlap-expanded bounded extraction window
  -> fixed-argv ffmpeg mono PCM extraction
  -> one reused FasterWhisper model instance
  -> midpoint ownership + core clipping
  -> private partial chunk JSON
  -> atomic text-free checkpoint
  -> deterministic final merge
  -> transcript.json / subtitles.srt / transcription-report.json
```

Defaults: 900-second core chunks, 2-second overlap, mono PCM WAV 16 kHz, 10,000 chunk cap, bounded ffmpeg/ffprobe timeouts. Existing one-shot CLI behavior remains the default unless `--chunk-seconds` is supplied.

## Chunk ownership

Overlap provides ASR context only. Each segment is mapped to absolute source time, retained only when its midpoint belongs to the chunk's non-overlapping core interval, then clipped to that core. Equal text is never blindly deduplicated, because repeated speech can be legitimate.

## Resume/checkpoint contract

Work state is `<output>/.bai-transcription-work/` and is Git-ignored.

`checkpoint.json` is text-free and contains source Asset ID, streaming source SHA-256, size, duration, Provider/safe Model identity, safe config hash, chunk-plan hash, detected language, and completed chunk IDs mapped to partial SHA-256 values. It stores no transcript text and no source/model filesystem path.

Private `partials/chunk-NNNNNN.json` files contain transcript text. A partial is atomically written before its checksum is atomically published into the checkpoint. Resume verifies all canonical fingerprints and every referenced partial before any new inference.

An unfinished work directory requires explicit `--resume`; explicit `--restart` deletes only that bounded work directory and recomputes. Symlinked work/checkpoint/partial state fails closed. Input size/mtime is checked around every chunk and the complete source SHA-256 is revalidated before final publication.

## FasterWhisper lifecycle

The Provider becomes lazy per-instance cached: one model construction per Provider instance, reused for all chunk calls. No global singleton is introduced and model download remains behind the existing explicit authorization flag.

## Resolve handoff

`SubtitleWorkspace` is the source of truth. Start time uses exact FLOOR ms-to-frame conversion; end-exclusive uses CEIL, both offset by an explicit non-negative `timeline_origin_frame`. Any cue collapse or frame-level overlap fails closed. No silent timing clamp/reorder is permitted.

The private plan contains workspace ID/revision/hash, rational Timeline rate, 1-based track index, cue IDs, end-exclusive frame ranges, subtitle text, review state, readiness, `handoff_owner=TASK-006`, `execution_owner=TASK-010`, and deterministic plan hash.

`ready_for_resolve_write` is true only when at least one placement exists and all cues are APPROVED. It is not execution authorization.

## Privacy/safety floor

- checkpoint/report text-free;
- partials and Resolve handoff private;
- raw ffmpeg stderr not persisted into ProductError details;
- fixed argv + `shell=False`;
- no BAI Development OS Product runtime dependency;
- no Resolve API import/mutation in TASK-006;
- no auto model download;
- no blind resume after drift.

## CLI

Large-media additions to `ai-video-transcribe`:
`--chunk-seconds`, `--chunk-overlap-seconds`, `--resume`, `--restart`, `--ffmpeg-executable`, `--ffprobe-executable`.

New handoff:
`ai-video-resolve-subtitle-handoff WORKSPACE --timeline-rate 30000/1001 --timeline-origin-frame 0 --track-index 1`

If `--output` is omitted, the private plan is written beside the Workspace under `.bai-resolve-handoff/`, which is Git-ignored.

## Validation

Focused tests cover deterministic planning, interruption/resume, source mismatch, privacy, restart, model reuse, deterministic Resolve plan hashing, approval gating, frame collision failure and atomic publication. Full Product regression, compileall, diff-check and git fsck remain release gates.
