# TASK-006 — ASR / Transcript / Subtitle

- Status: `V0_16_4_RELEASED / SLICE_D_IMPLEMENTED / VALIDATION_PENDING`
- Initial local-ASR package: `0.14.0`
- Corrective package: `0.15.1`
- Review Workspace package: `0.16.0`
- Windows test-fixture corrective package: `0.16.1`
- Windows interaction corrective release: `0.16.4` (native Windows acceptance PASS)
- Next slice governance: `DEV-3` — resumable large-media state + downstream NLE handoff contract
- Slice D candidate package: `0.17.0`
- Authorization: Owner-directed editing-first continuation
- Dependencies: TASK-003 Asset identity, TASK-004 normalized media, TASK-022 Timeline Mapping

Slice A establishes the provider-neutral Transcript source of truth, cut-aware Subtitle Plan, and deterministic SRT output. It does not yet transcribe real media or write into DaVinci Resolve.

Slice B connects TASK-023 FasterWhisper as the first local ASR Provider and adds an end-user CLI/Windows launcher that writes `transcript.json`, `subtitles.srt`, and a text-free operational report. Model download requires an explicit flag and inference remains local. Native Windows Evidence confirmed successful local transcription and exposed a 1 ms SRT-render boundary overlap requiring correction.

Package `0.15.1` corrects non-overlapping SRT rendering. Package `0.16.0` adds Slice C's shared Subtitle Workspace for planned narration, ASR and imported SRT, preserving immutable source wording with revisioned row editing. The default-off `AI誤字・脱字チェック` stores permission only and cannot call a Provider, overwrite text or approve a revision. Dictionary correction, AI proposals, large-media chunk/checkpoint execution and Resolve placement remain separate bounded slices.

Package `0.16.1` changes only the cross-platform SRT test fixture. Python text-mode output translated embedded CRLF into CRCRLF on Windows, so the fixture now writes explicit UTF-8 BOM bytes. No production parser behavior changed.

Candidate package `0.16.2` corrects a usability defect discovered before broader Windows acceptance: SRT import/export no longer requires manual path typing. Explicit operator clicks can open Windows-native Open/Save dialogs through the loopback application; direct path entry remains available for advanced operation. Existing workspace replacement still requires an explicit confirmation in the browser. The dialog path does not upload media or authorize AI/provider execution.

Package `0.16.4` completes the Windows interaction corrective. Native Open/Save dialogs, strict relative insertion timing, visible export Evidence, bounded native-dialog error handling, CLIXML suppression and local-server-disconnected feedback passed the formal release gates and native Windows acceptance.

Slice D is the next authorized bounded continuation: resumable large-media chunk/checkpoint transcription plus a canonical Resolve subtitle-placement handoff. TASK-006 owns planning/publication only; actual DaVinci Resolve subtitle-track mutation remains TASK-010-owned.

Package `0.17.0` candidate implements deterministic bounded audio chunks, atomic text-free resume checkpoints, verified private partial reuse, source-mutation guards and a reused FasterWhisper model instance. It also publishes a deterministic private Resolve subtitle-placement handoff from the human Subtitle Workspace with an explicit timeline origin. Frame collisions fail closed and actual Resolve mutation remains TASK-010-owned. Focused/full validation remains required before release.
