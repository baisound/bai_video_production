# TASK-006 — ASR / Transcript / Subtitle

- Status: `NATIVE_ASR_PASS / SUBTITLE_WORKSPACE_IMPLEMENTED / RESOLVE_PLACEMENT_PLANNED`
- Initial local-ASR package: `0.14.0`
- Corrective package: `0.15.1`
- Review Workspace package: `0.16.0`
- Authorization: Owner-directed editing-first continuation
- Dependencies: TASK-003 Asset identity, TASK-004 normalized media, TASK-022 Timeline Mapping

Slice A establishes the provider-neutral Transcript source of truth, cut-aware Subtitle Plan, and deterministic SRT output. It does not yet transcribe real media or write into DaVinci Resolve.

Slice B connects TASK-023 FasterWhisper as the first local ASR Provider and adds an end-user CLI/Windows launcher that writes `transcript.json`, `subtitles.srt`, and a text-free operational report. Model download requires an explicit flag and inference remains local. Native Windows Evidence confirmed successful local transcription and exposed a 1 ms SRT-render boundary overlap requiring correction.

Package `0.15.1` corrects non-overlapping SRT rendering. Package `0.16.0` adds Slice C's shared Subtitle Workspace for planned narration, ASR and imported SRT, preserving immutable source wording with revisioned row editing. The default-off `AI誤字・脱字チェック` stores permission only and cannot call a Provider, overwrite text or approve a revision. Dictionary correction, AI proposals, large-media chunk/checkpoint execution and Resolve placement remain separate bounded slices.
