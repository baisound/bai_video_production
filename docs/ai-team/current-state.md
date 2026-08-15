# AI Video Production — Current State

## Canonical project state

- Project: `ai-video-production`
- Mode: `BAI Development OS CONSUMER_PROJECT_MODE`
- Project Status: `V0_21_0_RELEASED / TASK_046_P_VS_0_ROADMAP_INTAKE_LOCAL_PASS / HOSTED_PENDING / NATIVE_RUNTIME_PARKED`
- Last Completed Release Unit: `TASK-045 P-RC-3 — v0.21.0`
- Last Completed Consumer Gate: `TASK-036 P-UX-1B implementation`; PR #89 passed hosted `9 / 9`, merged at exact main `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`, passed post-merge main CI/Security, and completed remote branch/dedicated-checkout cleanup
- Active Consumer Task: `TASK-046 / P-VS-0 VOICE STUDIO ROADMAP INTAKE / codex/task-046-voice-studio-roadmap-intake`; exact base main `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`; package integrity, audit, OR-01..32/Q1..44 Crosswalk, TASK-046/047/048 allocation, DEV-4, Architecture, Allowed Files, Builder design, two Critic passes and Judge pass locally; documentation-only hosted closure is pending
- TASK-004 Profile: `DEV-4 FOUNDATION CRITICAL` / score `25`
- TASK-004 Status: `COMPLETED`
- Package: `0.21.0`
- Release State: `FORMAL_RELEASE_COMPLETE`; stable GitHub Release `v0.21.0` targets exact release-code main SHA `c38187ed54e3601c44411d9b8a128348b0d8a7b7`
- Development Candidate: `NONE`; no post-0.21.0 candidate is selected
- Release commit: `c38187ed54e3601c44411d9b8a128348b0d8a7b7`
- Next Consumer Decision Gate: `P-VS-0 documentation PR -> hosted 9/9 -> exact main merge -> cleanup -> fresh-main TASK-036 P-UX-1C native parity closure -> successor canonical Voice mock -> TASK-046 P-VS-1 body-free foundation; Native Model/download/voice processing remains separately gated`

## TASK-007 / 010 / 011 / 012 Technical MVP candidate

- TASK-007: deterministic Candidate Graph, target-duration proposal ranking, explicit CUT/KEEP review, bounded override, protected Keep Blocks, second-stage plan approval and canonical Edit Plan hash. No automatic external-write authorization.
- TASK-010: approved Edit Plan -> TASK-022 exact mapping -> deterministic `BAI_AUTO_*` Resolve assembly, explicit external-write authorization, marker-based idempotency and partial/conflict fail-closed behavior. Source/normalized FPS is mandatory for source-frame conversion.
- TASK-011: render artifact checksum/media/duration verification plus configurable LUFS/true-peak QA; no absolute render path persisted in QA report.
- TASK-012: QA-gated deterministic `EDITOR_WORK_*` package, relative-path/checksum manifest and bounded 48 kHz PCM Cubase return. No automatic Cubase project conversion claim.
- Cross-task Application Service: `TechnicalMvpApplicationService` preserves the 007 -> 010 -> 011 -> 012 orchestration boundary for future Unified Desktop Shell wiring.
- Current integration state: TASK-010/011/012 are `NATIVE_VALIDATED / SHELL_INTEGRATED` through the accepted TASK-036 W2 route.
- Native PASS: real Resolve source-range/linked-A/V/idempotency/conflict semantics, edit-aware subtitle semantics, real Resolve render artifact QA and real Cubase 48 kHz PCM return.
- TASK-036 W2 PASS: the packaged trusted launcher completed real Windows `Media ingest -> local FasterWhisper -> Subtitle -> Cut Review/Approve -> Resolve apply -> TASK-011 native Render QA -> atomic EDITOR_WORK`; the final UI state was `NONE` and no host path was persisted in public status/Evidence.
- TASK-036 W0/W1 H2 closure: clean-profile packaged launch, isolated missing-WebView2 recovery, enforced long-path policy, actual three-monitor movement, increased-scale responsive layout and Windows Narrator/UI Automation semantics PASS. Overall TASK-036 and M3B reach `MINIMUM_EDITING_PRODUCT_MVP_PASS`.
- Phase G closure gates: post-W2 conversation-free restart PASS; final Pilot Context Cost `11,888` estimated tokens PASS; exact release decision `0.20.0 / v0.20.0 / stable` PASS; release integration PASS.
- Automated validation: final v0.20.1 WSL2 Ubuntu `810 / 810`; Windows clean-profile/three-monitor/Narrator/WebView2-recovery gates PASS; packaged Windows native W2 E2E remains accepted; PR #22 hosted checks `9 / 9 PASS`; Release workflow PASS.

## TASK-004 implemented scope

### Media foundation

- exact rational timebase including NTSC rates;
- bounded ffprobe timing/VFR inspection;
- fixed-argv ffmpeg normalization;
- 48 kHz PCM analysis audio;
- CFR proxy generation and complete-batch QA;
- source-checksum revalidation and derived-Asset publication;
- normalization manifest/Evidence and TASK-022 affine handoff.

### Local Visual AI

- local/private ComfyUI API boundary, class/resource admission and safe output containment;
- FLUX/Stable Diffusion family image runtime/license profiles;
- MiniMax H3 T2V/I2V/First-Last/Reference provider contracts;
- Character Identity profile + same-Job canonical reference bundle;
- H3 Production Brief structured compiler;
- H3 SingleFrame optional external-node provider;
- Spectrum optional approximate acceleration with Native default and cache-wrapper conflict prevention;
- H3 Foley/SFX standard and explicitly experimental FAST_32/extended-duration contracts;
- persisted ComfyUI `prompt_id` reconciliation to prevent blind duplicate generation after timeout/crash.

### Local Audio AI

- Audacity `mod-script-pipe` external Runtime boundary;
- Intel OpenVINO capability discovery without copying GPL plugin code;
- Noise Suppression and verified-runtime 2-stem Music Separation contract; 4-stem is fail-closed until scriptable mode is available;
- output containment, complete sibling QA before publication and derived AUDIO Asset registration;
- ambiguous external state fails closed instead of automatically replaying Audacity work.
- worker phase Evidence distinguishes pre-dispatch timeout from post-dispatch ambiguity; post-dispatch timeout is persisted as `PARTIAL` and blocks blind replay.

## Current verification

- TASK-006 Slice D package `0.17.0`: formal release complete; Windows full regression `415 passed, 1 intentional skip`, compileall/diff-check/fsck PASS, GitHub Actions all green. No Resolve mutation is implemented in TASK-006.
- TASK-024 Slice A package `0.18.0`: FORMAL RELEASE COMPLETE — PR #13 merged, annotated tag `v0.18.0` published, Windows/native validation and CI PASS.
- TASK-006 v0.16.4 formal release: `402 / 402 PASS`; `compileall` PASS; `git diff --check` PASS; `git fsck --full` PASS; native Windows Subtitle Workspace/Open/Save validation PASS.
- v0.17.0 development-governance baseline: BAI Development OS `1.0.0` / Architecture `Ver.2.28 CURRENT_CANONICAL`, Level A Governance Only, with no Product runtime dependency. Migration baseline is completed before TASK-006 Slice D feature code.
- Post-v0.20.1 R2-R4 governance provenance: BAI Development OS `v1.1.0` / Architecture `Ver.2.29` governed the later bounded Product work; the OS remains external development tooling and is not a Product runtime dependency.
- TASK-006 Windows interaction corrective `0.16.4`: native SRT dialog failure/CLIXML leakage corrected, strict relative insertion timing and visible export/server-disconnect feedback accepted on Windows
- TASK-006 corrective package `0.16.1`: Windows CRLF fixture writes exact bytes; production SRT behavior unchanged
- TASK-006 Slice C package `0.16.0`: planned narration/ASR/SRT intake, revisioned local review GUI, row editing and atomic SRT export implemented

- TASK-006 Slice A package `0.13.0`: Transcript/Subtitle schemas, cut-aware exact mapping and deterministic NTSC SRT tests PASS
- TASK-006 Slice B package `0.14.0`: optional FasterWhisper local ASR, explicit model-download gate, Transcript/SRT publication and text-free report tests PASS
- TASK-006 native Windows Evidence: `small` Japanese CPU/int8 produced 10 Segments locally; Native ASR PASS. One mistranscription and adjacent SRT 1 ms render overlaps require Slice C corrective/review work. Correction order is dictionary, GUI human review, default-off opt-in AI typo/omission proposal, then human approval.
- TASK-027 Slice A1 package `0.15.0`: real-production-evidence-derived Production Blueprint, Scene Ledger, Reference Registry, source-priority and dense-text generation gates implemented
- TASK-035 design intake: optional REAPER audio-finishing/Resolve round-trip recorded; native ReaScript Plan/QA bridge precedes any third-party MCP or iZotope Assistant automation
- TASK-014 design intake: owner's existing ElevenLabs Pro trained voice will be used through a private Voice Profile and timed TTS path; no retraining/upload or paid call is authorized by configuration alone
- TASK-013 R4 local generation execution control is hosted-closed: PR #38 final head `ff1cbed` passed `9 / 9` and merged at exact main `1614832b`; the subsequent exact local adapter target audit and fail-closed adapter implementation are also complete, while native generation and Candidate/Audit binding remain unclaimed
- TASK-013 exact target audit passed: loopback ComfyUI `0.31.0`, `837` node classes, RTX 4070 SUPER, all four native H3 model files/classes and isolated Product-owned runtime roots were verified; the operator Prompt/workflow remains private and no generation was queued
- TASK-013 concrete local adapter local gate passed: package-owned body-free workflow, exact `LOCAL_FREE_AI / TEXT_TO_VIDEO` authority, exact `127.0.0.1`/model/node/resource/runtime checks, durable prompt-id journal, exact output containment and opt-in trusted-launch composition pass `35 / 35` final focused and `919 / 919` full WSL2 regression
- TASK-013 adapter hosted closure passed: PR #41 exact head `ff481147080518f44865c88ad0a8caffadd96947` passed all `9 / 9` hosted checks and merged at exact main `74d6b5af0c6de66168f5ab6ab63a6a049b11acd4`; the implementation branch was deleted remotely and locally
- TASK-013 safe-runtime launch-flag hardening passes its bounded local gate: all four memory flags observed in the Owner-confirmed force-restart attempt, including assignment forms, are rejected before journal reservation or queue side effects; focused `39 / 39`, full WSL2 `923 / 923` and compileall PASS. Native H3 remains parked.
- TASK-013 safe-runtime readiness preflight passes its bounded local gate: explicit application/Shell invocation performs only body-free ComfyUI node/model, resource and exact runtime-identity inspection; focused `55 / 55` and full WSL2 `926 / 926` PASS. It queues nothing, creates no dispatch journal/output or execution Authority, and leaves Native H3 parked.
- TASK-013 safe-runtime readiness preflight hosted closure passed: PR #45 exact head `f0d3a95cd5f582f9a695ce46ecebf6955f52b046` passed all `9 / 9` checks and merged at exact main `fac1a2fb53c3c5c439c3b1cf6c55f10d4bbf3f57`; the remote branch and prior cycle clone were removed and a clean exact-main fresh clone was verified.
- TASK-041 Audio Workspace Product promotion is hosted-closed: project-scoped `audio-workspace.json`, exact Production/audio checksum binding, serialized CAS, one-shot Placement/Human decision confirmation, LOCK-only ACCEPT and unified Desktop/trusted-launch composition passed focused `64 / 64`, full WSL2 `932 / 932`, compileall and JavaScript syntax; PR #47 exact head `3785e44a211b8c4d81005060bc8a1faff161870d` then passed all `9 / 9` hosted checks and merged at exact main `8dd6434a65115d88641d0942b08788a9eceda279`. The remote branch and prior cycle clone were removed after a clean exact-main fresh clone was verified. Provider, paid execution, media derivation, TASK-026 compile and Resolve/Cubase mutation remain false.
- Native attempt 01 queued exact Comfy prompt `91cb547f-1056-44a5-a2b5-9ddfd0c5621a`, loaded the real native H3 model path and failed at `SamplerCustomAdvanced` with `hostbuf_file_reader_read failed`; no output was published
- Native attempt 02 queued exact Comfy prompt `f92c56e4-4fd8-44fc-b347-d7d4acdfed8b` under legacy low-VRAM flags and was externally interrupted by the Owner-confirmed Windows force restart after the host froze. Its journal remains `QUEUED`, the parent state is recovery-required, and automatic replay is prohibited
- Product runtime policy now rejects `--disable-dynamic-vram`, `--disable-async-offload`, `--disable-pinned-memory`, `--lowvram`, `--highvram`, `--novram`, `--gpu-only` and `--cpu`, including assignment forms, before dispatch. Native H3 completion is `PARKED_TO_SAFE_RUNTIME_REVIEW`, not PASS
- TASK-034 native Windows package `0.12.2`: Catalog/Credential lifecycle and per-row Password Manager behavior PASS
- TASK-034 package `0.12.2`: Catalog lifecycle linkage, retained-key cleanup, OS vault, per-Route password-manager lookup and secret-exclusion tests PASS
- TASK-033 native Windows: add `demo-video-route`, edit to `demo-model-v2`, disable and truthful adapter status display PASS
- TASK-033 package `0.11.0`: Catalog add/edit/disable, implementation status, API mutation and secret-exclusion tests PASS
- TASK-032 native Windows: save/reload PASS; stale revision 3 rejected after revision 4 save PASS; 2–3-person usability review pending
- TASK-032 package `0.10.0`: local GUI/API, CSRF, Host, conflict and secret-exclusion tests PASS
- TASK-032 package `0.9.0`: `330 / 330 PASS`, compileall PASS, diff-check PASS
- Settings persistence: atomic rollback, stale-write conflict, checksum tamper, 0.8 migration and secret-free bilingual form PASS
- `pytest`: `250 / 250 PASS`
- `compileall`: PASS
- `git diff --check`: PASS
- package `0.4.7` wheel build: PASS
- installed-wheel packaged schemas: PASS
- installed-wheel real ffmpeg/ffprobe golden normalization: PASS
- absent ComfyUI/Audacity runtimes: structured fail-closed diagnostics PASS
- wheel SHA-256: `a87beed109e0ac6641fefb25d519b625eea1fa6507bfea04552edfe0e1e48366`

## Final TASK-004 Evidence

Target-machine capability Evidence is accepted for ComfyUI and Audacity/OpenVINO. The final package 0.4.9 behavioral run completed Noise Suppression and the provable Intel-default 2-stem Music Separation path. It published one noise-suppressed Asset and the complete `instrumental`/`vocals` pair with committed Manifests and verified checksums. All four probe database operations completed without error.

The first full native-Windows regression returned `251 passed, 2 failed`. Package 0.4.10 corrected the Windows-only test double so it preserves the real CRT `O_BINARY` bit, and normalized equivalent Win32/extended-length canonical paths before containment comparison. The final rerun passed `255 / 255` tests in 41.26 seconds; compileall also passed with no output.

4-stem Music Separation remains explicitly `NOT_SCRIPTABLE_ON_VERIFIED_RUNTIME`: the live descriptor exposes no separation-mode parameter, so the Product fails closed until a future runtime/provider exposes a scriptable mode.

## Roadmap

Canonical roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.85 Addendum LXXIX. TASK-036 P-UX-1B is hosted-closed by PR #89 at exact main `244e86aaa0ea65bdba2ca35176c422bcfc30d65f`, with post-merge CI/Security and cleanup complete. The Voice Studio Ver.1.2 intake is locally reconciled as TASK-046/047/048 plus bounded existing-Task extensions. P-UX-1C remains immediately before any Voice Shell change; a successor canonical mock must precede the Voice top-level destination. Then TASK-046/014 prioritize the Japanese owner-only local/free 60–90 second vertical slice before recording breadth, OBS, RX, broad Creative AI or locale expansion. Overall visual parity and native Voice completion remain unclaimed. Provider/paid/Cloud/Model download/private voice processing/external mutation/Production Deploy remain blocked at their recorded gates.

TASK-022 is `COMPLETED` with exact rational source/normalized-to-Timeline mapping, deterministic Plan hashing and canonical/package schemas; native-Windows full regression and compileall passed (`263 / 263`).

## Safety boundaries

- BAI Development OS Core and OS-internal TASK-016 remain untouched.
- DistributedOS remains disabled.
- no third-party runtime/model/custom-node is auto-installed or auto-updated;
- external GPL custom/runtime source is not copied into Product Core;
- generated/processed media is not canonically published until Product-side containment/media/checksum QA passes;
- downstream public-use/licensing decisions remain explicit policy gates;
- Character Identity / SingleFrame / Spectrum / H3 Foley are bounded capabilities, not claims of guaranteed identity fidelity or quality.

## Registered Design Knowledge

- `BVP-KNOWLEDGE-REFIMG-001` imported from the 2026-08-12 Product Promotion workflow.
- Remaining detailed implementation design: `docs/ai-team/tasks/TASK-013/scene-compatible-reference-gate-detailed-design.md`.
- The separate R3 Shot Feasibility / Visual Compliance Product promotion is complete. Unimplemented Scene-Compatible Reference slices remain design-only and require their own authorization.
- This Knowledge registration does not authorize a native retry, Candidate/Audit binding or another R4 slice.

## Cross-cutting Product Architecture — Unified Desktop Application

- `PRODUCT-ARCH-001` registered as canonical Product architecture.
- Final user-facing Product: one BAI Video Production Desktop Application entrypoint.
- CLI / localhost Web UI remain internal/transitional/diagnostic unless explicitly integrated.
- Existing backend capabilities are not automatically classified as `SHELL_INTEGRATED`.
- Every future relevant detailed design must include `Unified Application Integration`.
- No runtime/package change is created by this architecture registration.
- TASK-023 resumes only after this architecture change is merged; its design must name Subtitle Workspace as the final user-facing integration location.

## TASK-023 reconciliation completed

- Existing TASK-006 FasterWhisper local provider/cache/download-gate/model-reuse/resumable-transcription capabilities are reused.
- New 0.19.0 candidate adds deterministic execution identity and a model-free/network-free evidence CLI.
- PRODUCT-ARCH-001 target: `BAI Video Production.exe -> Subtitle Workspace`.
- Historical 0.19.0 slice state was `INTEGRATION_DESIGNED`; TASK-036 v0.20.1 now integrates the accepted local ASR route into the Shell.
- CLI classification: `DEVELOPER_DIAGNOSTIC_INTERFACE`.
- No second provider, no recognition-semantic change, no word-level schema expansion and no public transcript-result cache.
- Validation complete: `444 passed, 1 intentional skip`; compileall/diff-check PASS; native Windows evidence CLI PASS on a real local source.
- Final TASK-023 capability state remains `COMPLETE`; its accepted local ASR route is now `SHELL_INTEGRATED / NATIVE_VALIDATED` through TASK-036 W2.
