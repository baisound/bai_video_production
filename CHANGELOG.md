# Changelog

??Project?Semantic Versioning????????????????????Git Tag?Commit log??????????

## [Unreleased]

- Registered `BVP-KNOWLEDGE-REFIMG-001` and the future TASK-013 Scene-Compatible Reference / Shot Feasibility Gate detailed design; documentation only, no runtime behavior change.

- Integrated end-user GUI and complete automatic editing workflow remain under development.

## [0.18.0] - 2026-08-12

- Added TASK-024 review-only silence/filler/disfluency cut-candidate analysis on normalized PCM audio and optional canonical Transcript input.
- Added fixed-argv FFmpeg `silencedetect`, transcript Keep Blocks, conservative filler-only and exact-adjacent-repeat candidates, and fail-closed overlap/integrity bounds.
- Added deterministic text-free Cut Candidate Manifest/report with explicit TASK-007 planning ownership, TASK-010 execution ownership, and `auto_apply_authorized=false`.
- Added `ai-video-cut-candidates`, canonical/package JSON Schema, user documentation, and focused privacy/integrity/CLI regression coverage.

## [0.17.0] - 2026-08-11

- Added resumable chunk/checkpoint transcription for large media with bounded overlap, explicit resume/restart semantics, source/config/plan integrity checks, and private local work state.
- Reused one FasterWhisper model instance across chunk calls while preserving the existing one-shot transcription path and explicit model-download gate.
- Added a deterministic, private Resolve subtitle-placement handoff plan with exact frame mapping, explicit timeline origin, approval readiness, collision fail-closed behavior, and TASK-010 execution ownership.
- Added focused regression coverage for resume integrity, private reports/checkpoints, model reuse, and Resolve handoff determinism.

## [0.16.4] - 2026-08-11

- Replaced the Windows native SRT dialog foreground-owner C# compilation path with a top-most cursor-monitor WinForms owner, avoiding the `System.Windows.Forms` `Add-Type -TypeDefinition` failure observed on native Windows.
- Added an ASCII/Base64 dialog result protocol and `-OutputFormat Text` boundary so PowerShell CLIXML and Windows code-page mojibake are never rendered into the browser status panel.
- Added regression coverage for Open/Save success, cancel, bounded PowerShell failure, malformed protocol data, and raw-CLIXML suppression.

## [0.16.3] - 2026-08-11

- Corrected Subtitle Workspace relative insertion so a cue placed between neighboring subtitles uses a strict 1 ms inner margin (for example `...300` / `...600` becomes `...301`–`...599`).
- Added prominent import/export/action feedback; successful SRT export now reports its resolved destination path and byte count.
- Added explicit local-server disconnect feedback so stale browser pages no longer make controls appear silently dead.
- Changed Windows Open/Save dialog launch to use the foreground window as the native owner with a top-most fallback for multi-monitor/fullscreen workflows.

## [0.16.2] - 2026-08-11

- Added Windows-native Open/Save dialogs to the Subtitle Workspace so operators can choose an SRT file and destination without typing filesystem paths.
- Kept manual path entry for advanced use, added a replacement confirmation before importing over an existing workspace, and preserved the loopback/CSRF boundary.
- Added deterministic dialog-service tests without opening a real native window during automated regression.

## [0.16.1] - 2026-08-10

- Corrected the SRT CRLF regression fixture to write exact UTF-8 BOM bytes on Windows, preventing text-mode newline translation from producing malformed `CRCRLF` test data.
- Confirmed that the production SRT parser was not the failure source; runtime behavior and the 0.16.0 Subtitle Workspace contract are unchanged.

## [0.16.0] - 2026-08-10

- Added a local Subtitle Workspace GUI for editing planned narration, ASR transcripts and imported SRT without provider execution.
- Added stable cue identity, immutable source wording, revisioned JSON persistence and insert/update/delete operations.
- Added bounded streaming SRT import, atomic SRT export and a default-off AI typo/omission permission gate that never calls an AI by itself.
- Added pull-request release-metadata checks requiring CHANGELOG updates for product changes and consistent package/GUI/citation versions.
- Documented truthful large-media limits: SRT text is streamed, while multi-GB media transcription still requires the future chunk/checkpoint slice.

## [0.15.1] - 2026-08-10

- Corrected adjacent NTSC SRT cues so millisecond floor/ceil conversion cannot create a 1 ms overlap at a shared end-exclusive frame boundary.
- Preserved safe ceil-end behavior for isolated/final cues and added native-Evidence-shaped regression fixtures.
- Recorded the successful Windows FasterWhisper run and designed immutable Raw Transcript, prioritized dictionaries, GUI review and a default-off AI typo/omission suggestion gate.
- Added TASK-014 owner-trained ElevenLabs narration design and TASK-035 REAPER/iZotope/Resolve audio round-trip design.

## [0.15.0] - 2026-08-10

- Added TASK-027 Slice A1 Production Blueprint and validated Scene Ledger contracts derived from 11 real production design documents.
- Added stable PERSON/SPACE/PROMPT/ASSET/AUDIO reference registration with explicit planned/available/locked state.
- Added real-capture-first asset strategy and complete frame-range coverage validation.
- Added A/B/C visual-generation risk classification and fail-closed dense-UI rules requiring locked references, static cameras and post-composited text.
- Added scene-level narration, dialogue, SFX, BGM, sound-logo and final-hold planning.
- Routed narration timing, mix comparison, continuity QA and hypothesis-based learning findings into their canonical future Tasks without copying private source documents.

## [0.14.0] - 2026-08-10

- Added the optional FasterWhisper local ASR adapter and end-user Transcript/SRT CLI.
- Added explicit model-download authorization with local-files-only default behavior.
- Added atomic private Transcript/SRT publication and a schema-validated text-free operational report.
- Added NTSC adjacent-cue normalization and failure cleanup regression coverage.
- Separated the product version from the AI Connection Settings revision in the local GUI footer.

## [0.13.0] - 2026-08-10

- Added the TASK-006 transcript and subtitle foundation with provider-neutral ASR contracts and checksummed canonical Manifests.
- Added exact cut-aware subtitle mapping through TASK-022 Timeline placements, including deterministic splitting and retiming across kept source ranges.
- Added NTSC-safe SRT rendering using rational frame conversion with floor-start/ceil-end boundaries and normalized multiline text.
- Added packaged JSON Schemas and regression fixtures for validation, overlap rejection, cut removal, split cues, empty plans and deterministic hashes.

## [0.12.2] - 2026-08-10

- Linked the Catalog and Secure credentials projections explicitly: enabled credential-required routes appear in the active key list, while other routes do not.
- Added a retained-key cleanup section for disabled routes instead of silently deleting secrets or presenting disabled Models as active.
- Prevented removing `Credential required` while a key remains stored, avoiding an unreachable orphaned Windows credential.
- Added visible Catalog credential status and end-to-end add/disable/delete/unrequire regression coverage.

## [0.12.1] - 2026-08-10

- Fixed API-key re-registration suggestions so every credential row has an independent password-manager section, ID, and name instead of only the first row being recognized.
- Changed the credential input hint from new-password suppression to route-scoped current-password lookup while retaining password masking and post-operation clearing.

## [0.12.0] - 2026-08-10

- Added API-key onboarding from the loopback settings screen into the current user's Windows Credential Manager.
- Added opaque hashed credential targets, UTF-8/size validation, save/read/status/delete operations, and fail-closed non-Windows behavior.
- Exposed registration state only; secret values and internal credential references remain absent from settings JSON and browser responses.
- Added bilingual safety copy and regression tests proving that credential mutations never start Provider calls, billing, generation, or editing.

## [0.11.0] - 2026-08-10

- Added a local Provider/Model Catalog editor for safe add, edit, and disable operations without JSON editing.
- Added truthful `IMPLEMENTED`, `LOCAL_RUNTIME`, and `PLANNED_ADAPTER` labels so configuration never implies execution support.
- Added generated internal credential references while excluding keys, tokens, references, endpoints, headers, and arbitrary settings from the browser contract.
- Reused atomic revision storage, CSRF, Host, CSP, and bounded-request protections and added Catalog regression coverage.

## [0.10.0] - 2026-08-10

- Added a responsive bilingual AI Connection settings screen served exclusively on local loopback.
- Added interactive mode and preferred configured-model selection across planning, video, image, audio, and music.
- Added a narrow mutation contract with revision conflict checks, random CSRF protection, Host validation, restrictive CSP, JSON/size limits, and no Provider execution path.
- Added a Windows launcher plus beginner and developer guides with diagrams, safety explanations, and truthful remaining gates.

## [0.9.0] - 2026-08-10

- Added atomic, checksummed AI Connection settings persistence with optimistic revision checks.
- Added safe migration from the 0.8 raw profile document and fail-closed handling for damaged or unsupported data.
- Added a bilingual GUI-neutral form contract with five workloads, plain-language mode/status help, exact safe model metadata, and no credential or endpoint references.
- Added power-loss rollback, stale-write, migration, integrity, schema-packaging, and secret-exclusion regression tests.

## [0.8.0] - 2026-08-10

- Added a GUI-safe, secret-free AI Connection settings preflight across planning, video, image, audio, and music.
- Reports selected exact model metadata, cost/locality class, credential readiness, disabled/blocked state, normalized errors, and a deterministic hash without executing a provider.
- Added a dated detailed design for persistence, interactive settings UI, and low-literacy usability review.

## [0.7.0] - 2026-08-10

- Added GitHub-rendered architecture and roadmap visuals plus a credential-free five-minute demo.
- Added complete Japanese/English public README navigation and equivalent English project, impact, safety and contribution guidance.
- Added guarded GitHub Release and PyPI Trusted Publishing workflows.
- Added monthly release-readiness automation, good-first-issue intake and measurable adoption/impact protocols.

## [0.6.7] - 2026-08-10

- Removed process-global `os.name` mutation from the Audacity Windows import regression test.
- Added an explicit OS-name seam so Linux/Python 3.11 pytest never attempts to instantiate `WindowsPath`.

## [0.6.6] - 2026-08-10

- Provisioned and verified FFmpeg/ffprobe on Linux and Windows GitHub-hosted CI runners.
- Corrected the six-job CI failure caused by missing media executables rather than a product regression.

## [0.6.5] - 2026-08-10

- Corrected every public repository URL to `baisound/bai_video_production`.
- Added a regression check that prevents the former repository URL from returning.

## [0.6.4] - 2026-08-10

- Added OSS public documentation, MIT license, governance, security and contribution policies.
- Added GitHub CI, security scanning, Dependabot, Issue forms and Pull Request template.
- Added public-package metadata and repository structure regression checks.

## [0.6.3] - 2026-08-10

- Replaced provider-purpose assumptions with exact model capability routing.

## [0.6.2] - 2026-08-10

- Added ElevenLabs TTS/SFX/music and SunoAPI.org asynchronous music adapters.

## [0.6.1] - 2026-08-10

- Added OpenAI, Anthropic and Google text execution adapters.

## [0.6.0] - 2026-08-10

- Added unified AI connection profiles and deterministic route resolution.

## [0.5.0] - 2026-08-10

- Added exact rational Timeline Mapping Service.

## [0.4.10] - 2026-08-09

- Completed Media Normalization and Local Visual/Audio AI Runtime foundation after native-Windows regression.

## [0.3.0] - 2026-08-08

- Added secure Asset ingest, rights/checksum and Logical Path Resolver.

## [0.2.4] - 2026-08-08

- Completed DaVinci Resolve capability spike.

## [0.1.0] - 2026-08-08

- Added Product domain, canonical manifest, state, evidence and persistence foundation.
