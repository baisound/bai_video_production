# TASK-056 — Creator Route Usage (R0)

## Purpose

This is the temporary local creator route used before TASK-036 Product GUI integration is safe to land. It is not the intended final consumer UX. Final users should reach the same Application Service through BVP, without Codex, ChatGPT, API keys, JSON authoring, or a paid AI subscription.

## Preconditions

- use an existing BVP `ASSET-*` identity for the source media;
- FasterWhisper and the selected model are already installed/cached unless the operator explicitly allows a model download;
- use the exact rational source frame rate (`60000/1001`, not `59.94`);
- `ffmpeg` / `ffprobe` are required only for the resumable long-media route.

## Short/local media

```powershell
ai-video-speech-cues `
  --media "D:\capture\match.mp4" `
  --source-asset-id "ASSET-..." `
  --source-frame-rate "60000/1001" `
  --output-dir ".\speech-cue-job"
```

The built-in `dbd-chase-call-ja-v1` profile is used by default. Model download remains disabled by default.

## Long gameplay / resumable route

```powershell
ai-video-speech-cues `
  --media "D:\capture\long-match.mp4" `
  --source-asset-id "ASSET-..." `
  --source-frame-rate "60000/1001" `
  --resumable `
  --chunk-seconds 900 `
  --overlap-seconds 2 `
  --output-dir ".\speech-cue-job"
```

If execution is interrupted after at least one completed chunk, rerun the same canonical inputs with:

```powershell
ai-video-speech-cues ... --resumable --resume
```

If the source/configuration intentionally changed, use explicit `--restart`; do not silently reuse an incompatible checkpoint.

## Outputs

`semantic-cues/` contains:

- `speech-cues.json` — private deterministic Cue Manifest;
- `montage-semantic-audio-cues.json` — text-free, non-canonical SKILL sidecar;
- `speech-cue-report.json` — path/text-free commit marker written last.

Consumers must validate the complete set with `SpeechCuePublicationService.read_verified()` or equivalent binding checks. The presence of `speech-cues.json` alone is not publication completion.

## Meaning of a cue

A `CHASE_CALL` cue means only: **the speaker said a configured chase keyword at this source time**. It does not prove that gameplay video contains a chase. Montage automation must combine this audio evidence with independent video/game-event evidence before proposing chase-specific edits.

## Human / authority boundary

- `CONFIRMED` requires precise word timing plus observed confidence meeting the profile threshold.
- low-confidence or segment-only matches are `REVIEW`.
- the sidecar has `canonical_timeline=false` and `auto_apply_authorized=false`.
- no cue authorizes Timeline mutation, Resolve writes, render, release, or deploy.
