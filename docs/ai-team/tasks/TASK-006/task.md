# TASK-006 — ASR / Transcript / Subtitle

- Status: `SLICE_A_TRANSCRIPT_SRT_FOUNDATION_IMPLEMENTED`
- Package: `0.13.0`
- Authorization: Owner-directed editing-first continuation
- Dependencies: TASK-003 Asset identity, TASK-004 normalized media, TASK-022 Timeline Mapping

Slice A establishes the provider-neutral Transcript source of truth, cut-aware Subtitle Plan, and deterministic SRT output. It does not yet transcribe real media or write into DaVinci Resolve.

Next Slice B connects TASK-023 FasterWhisper as the first local ASR Provider. Slice C connects the resulting Subtitle Plan/SRT to TASK-010 Resolve Assembly.
