# TASK-004 — Verification Record

- Verification status: `LOCAL_IMPLEMENTATION_VERIFIED`
- Completion status: `COMPLETED`
- Package: `0.4.9`
- Governance: `DEV-4 FOUNDATION CRITICAL`

## Local verification

- `python -m pytest -q`: **250 / 250 PASS**
- `python -m compileall -q src tests`: PASS
- `git diff --check`: PASS
- wheel build with `pip wheel --no-deps --no-build-isolation`: PASS
- wheel SHA-256: `a87beed109e0ac6641fefb25d519b625eea1fa6507bfea04552edfe0e1e48366`
- installed-wheel package version: `0.4.9`
- packaged TASK-004 schema resources: PASS
- installed-wheel golden media ingest + forced CFR proxy (`30000/1001`) + 48 kHz PCM analysis-audio normalization using real `ffmpeg`/`ffprobe`: PASS
- installed-wheel unavailable-ComfyUI diagnostic: expected fail-closed `ERR_PROVIDER_COMFY_UNREACHABLE`, exit 2
- installed-wheel unavailable-Audacity diagnostic: expected fail-closed `ERR_PROVIDER_AUDACITY_PIPE_UNAVAILABLE`, exit 2
- installed-wheel new synthetic behavioral-probe CLI smoke: generated isolated 48 kHz probe inputs, failed closed on absent local Audacity pipe with exit 2, and retained structured partial Evidence rather than reporting PASS

## Covered contracts

### Media foundation

- exact rational NTSC-style rates;
- bounded timing inspection and VFR/CFR classification;
- fixed-argv ffmpeg/ffprobe execution;
- source checksum revalidation;
- complete-batch QA before canonical publication;
- CFR proxy and 48 kHz analysis-audio derived assets;
- normalization manifest/Evidence and downstream TASK-022 handoff.

### ComfyUI / Local Visual AI

- local/private endpoint boundary and untrusted endpoint refusal;
- workflow/object-class validation and typed placeholder substitution;
- minimum resource-admission floor;
- FLUX/Stable Diffusion family runtime-license profiles;
- MiniMax H3 T2V/I2V/First-Last/Reference request boundaries;
- same-Job canonical reference staging;
- Character Identity reference bundles;
- H3 Production Brief immutable reference order/role/retention contract;
- H3 SingleFrame external-node capability and frame-count normalization;
- Spectrum `NATIVE` default, approximate accelerator provenance and competing-cache rejection;
- H3 Foley/SFX standard/experimental acknowledgement gates;
- prompt-id persistence and replay reconciliation without blind duplicate external generation.

### Audacity / OpenVINO boundary

- external GPL runtime boundary with no copied plugin implementation;
- bounded targeted OpenVINO effect capability discovery through Audacity `Help`;
- empty/sandbox-project safety gate;
- Noise Suppression and complete 2-stem Music Separation contract; verified-runtime 4-stem request fails closed unless a scriptable mode parameter is exposed;
- output containment, media QA and batch-preflight publication;
- request-bound idempotency;
- ambiguous `IN_PROGRESS` external state fails closed instead of replaying Audacity work.

## Pending live Evidence

The build environment does not contain the Owner's actual ComfyUI/MiniMax/FLUX/SD/OpenVINO/Audacity runtime installation. Therefore this record does **not** assert:

- model-weight availability on the target PC;
- optional Spectrum/H3 SingleFrame custom-node installation;
- live MiniMax H3/FLUX/SD generation quality or speed;
- live Audacity OpenVINO Noise Suppression or Music Separation behavior on the target PC.

Target-machine capability Evidence is collected with `tools/windows/run-task004-local-ai-capability-probes.ps1`. These gates must be reviewed before TASK-004 can be marked `COMPLETED`.

## Live evidence corrective patch (0.4.1)

- User target runtime proved both `ToSrvPipe` and `FromSrvPipe` exist and Audacity UI exposes OpenVINO Music Separation, Noise Suppression and Super Resolution.
- Initial capability probe timed out at the former hard-coded 15-second discovery limit.
- Corrective implementation raised capability-only default to 120 seconds, exposed a 5-600 second CLI/PowerShell override, and recorded worker discovery progress for timeout diagnosis.
- Audio effect execution timeout remained separately controlled by `AudioAiRequest.timeout_seconds`; the patch did not silently lengthen or replay side-effecting effect executions.

## Live evidence corrective patch (0.4.2)

- Attempt 02 passed the former timeout boundary but returned `ERR_PROVIDER_AUDACITY_OPENVINO_WORKER_FAILED` with `Audacity response did not contain JSON`.
- Audacity's own reference `pipe_test.py` defines Windows command framing as `\r\n\0` and POSIX as `\n`. Product 0.4.1 incorrectly wrote plain LF to the Windows named pipe.
- Product 0.4.2 now preserves the exact Windows CRLF+NUL transport terminator while keeping the existing bounded reply limits and external supervisor timeout.
- Two regression tests pin the transport terminator contract and actual command write behavior.
- Full regression is **233 / 233 PASS**, compileall PASS, wheel build PASS, and installed-wheel protocol smoke PASS.
- Capability-only live evidence must be rerun on the target PC. No OpenVINO effect execution is yet claimed as live verified.


## Live evidence corrective patch (0.4.3)

- Attempt 03 on package 0.4.2 reached `DISCOVERING_COMMANDS` and again returned `Audacity response did not contain JSON`; therefore the CRLF+NUL write framing was no longer the blocking issue.
- Audacity's own `pipe_test.py` response loop does **not** terminate on an initial blank line. It terminates only when a blank line arrives after response content has already been accumulated.
- Product 0.4.2 incorrectly treated any leading blank line as end-of-response, so target runtimes that prefix `GetInfo` replies with a blank line discarded the subsequent JSON payload.
- Product 0.4.3 tracks whether nonblank content has been observed, skips leading blank lines, and terminates only on the post-content blank delimiter. Bounded byte/line limits and the external supervisor timeout remain unchanged.
- Two regression tests pin leading-blank tolerance and multi-response delimiter behavior.
- Full regression is **235 / 235 PASS** before target rerun. Live capability evidence remains pending; no OpenVINO effect execution is claimed by this patch.


## Live evidence corrective patch (0.4.4)

- Attempt 04 on package 0.4.3 reached `DISCOVERING_COMMANDS` and parsed JSON, but the value was not the top-level array required by the `GetInfo: Type=Commands Format=JSON` contract. This confirms the previous framing/delimiter fixes advanced transport but whole-inventory command discovery remained unreliable on the target runtime.
- Audacity source defines `GetInfo` Commands as a top-level array, but the command walks every enabled Effect/AudacityCommand and materializes each command definition. That work is unnecessary for TASK-004, which only needs a bounded OpenVINO capability set.
- Intel's OpenVINO effects declare stable internal symbols (`OpenVINO Noise Suppression`, `OpenVINO Music Separation`, `OpenVINO Whisper Transcription`, `OpenVINO Music Generation`, `OpenVINO Super Resolution`). Audacity derives script command identifiers from those symbols with its `GetSquashedName` rule.
- Product 0.4.4 therefore probes only `OpenvinoNoiseSuppression`, `OpenvinoMusicSeparation`, `OpenvinoWhisperTranscription`, `OpenvinoMusicGeneration`, and `OpenvinoSuperResolution` via Audacity's side-effect-free `Help` command. Missing optional effects are reported unavailable rather than failing the capability probe.
- `GetInfo: Type=Tracks Format=JSON` remains in use because the empty/sandbox-project safety gate requires current track state. The global `GetInfo: Type=Commands` query is retained only as a diagnostic helper and is no longer used by normal capability or execution discovery.
- JSON extraction is now contract-typed: array callers ignore unrelated JSON objects, and object callers ignore unrelated arrays. A mismatched `Help` descriptor ID fails closed.
- Full regression is **238 / 238 PASS**, compileall PASS, `git diff --check` PASS, wheel build PASS, and installed-wheel import/protocol-contract smoke PASS. Live target capability Evidence must still be rerun before TASK-004 can close.


## Live capability PASS — Attempt 05 / package 0.4.4

- Returned target Evidence reports `connected=true`, `ok=true`, `current_track_count=0`, and worker phase `EXECUTION_COMPLETE`.
- All five bounded OpenVINO commands are live-available: Noise Suppression, Music Separation, Whisper Transcription, Music Generation, and Super Resolution.
- Each live `Help` descriptor returned the expected command ID and OpenVINO name.
- The live descriptors expose `params: []`. This is now treated as a runtime contract fact, not as an invitation to invent parameter names.
- Capability discovery gate is closed. The remaining audio gate is behavioral execution of Noise Suppression and 2-stem Music Separation using synthetic probe media.

## Behavioral-probe corrective design — package 0.4.5

- Intel's Music Separation implementation initializes `m_separationModeSelectionChoice` to `0`, pushes `(2 Stem) Instrumental, Vocals` as choice 0 and `(4 Stem) Drums, Bass, Vocals, Others` as choice 1, but the verified Audacity `Help` descriptor exposes no scriptable mode parameter.
- Product 0.4.5 therefore records the exact no-parameter Intel path as `INTEL_RUNTIME_DEFAULT_2_STEM`; this is eligible for live behavioral proof.
- A 4-stem request on this verified runtime fails `ERR_PROVIDER_OPENVINO_4_STEM_NOT_SCRIPTABLE` instead of depending on mutable GUI state or inventing an unsupported script parameter.
- `tools/windows/run-task004-audacity-openvino-behavior-probe.ps1` generates deterministic local stereo 48 kHz probe WAVs, uses an isolated temporary Product job, requires the Audacity project to be empty, executes Noise Suppression then 2-stem Music Separation through the production adapter, and writes `audacity-openvino-behavior.json`.
- The behavioral probe uses no client/user media and makes no perceptual-quality claim; it proves only executable runtime behavior, output structure, Asset publication/manifest integration and fail-closed safety boundaries.
- Full regression after this change: **247 / 247 PASS**.
- DEV-4 replay Critic additionally pins worker execution phases. A timeout observed at or after `IMPORTING_SOURCE` is recorded as `PARTIAL`, so a repeated identical request fails `ERR_STATE_AUDACITY_RECONCILIATION_REQUIRED` instead of blindly replaying external AI work; a timeout proven to occur before the first Audacity mutation remains `FAILED`/retryable.

## Behavioral Evidence Attempt 06 — package 0.4.5 returned / package 0.4.6 corrective

- Returned archive SHA-256: `4d777fdf1266031262353469a56223ff4722d93e79ffb9033807de6e3d3fde23`.
- Top-level report: `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST` / `DATA_INTEGRITY`.
- Runtime database contains exactly one operation: `ASSET_INGEST` for `task004-live-noise-source`, status `FAILED`; `assets` is empty. No Audacity/OpenVINO operation was dispatched, so this is not an OpenVINO behavioral failure.
- Root corrective: TASK-003 ingest previously treated any `mtime_ns` drift as content mutation. For freshly generated Windows media that is too strict as a content-identity signal.
- Package 0.4.6 keeps size drift as an immediate hard failure. Timestamp-only drift triggers a second complete SHA-256 pass over the **same open source handle**; only byte-identical content is accepted. Content/checksum/size disagreement still fails `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`.
- Regression adds a Windows-like timestamp-drift success case and a mismatch fail-closed case.
- Full local regression after corrective: **249 / 249 PASS**.
- Behavioral Evidence remains pending and must be rerun with package 0.4.6; capability Evidence remains accepted.

## Behavioral Evidence Attempt 07 — package 0.4.6 returned / package 0.4.7 corrective

- Returned report again failed before Audacity/OpenVINO dispatch: `ERR_INPUT_SOURCE_CHANGED_DURING_INGEST`, `reason=SIZE_CHANGED`, before/after size `576044`, copied size `143`.
- The returned synthetic noise WAV is actually `576044` bytes and its first byte `0x1A` occurs at zero-based offset `143`, exactly equal to the copied-size boundary.
- Root cause: TASK-003 low-level media ingest used `os.open`/`os.read` without `O_BINARY`. Python documents `O_BINARY` as required for binary mode on Windows; Microsoft CRT documents that translated text mode interprets CTRL+Z (`0x1A`) as EOF.
- Package 0.4.7 ORs `getattr(os, "O_BINARY", 0)` into both the source read descriptor and staging write descriptor. Existing `O_NOFOLLOW`, size/checksum, same-open-handle revalidation and atomic publication contracts remain intact.
- Regression adds a Windows-style injected `O_BINARY` flag and verifies both media descriptors receive it.
- Full local regression after corrective: **250 / 250 PASS**.
- Capability Evidence remains accepted. Behavioral Evidence must be rerun on package 0.4.7; no external effect was executed in Attempt 07.

## Behavioral Evidence Attempt 08 — package 0.4.7 returned / package 0.4.8 corrective

- `ERR_PROVIDER_FFPROBE_NOT_FOUND` occurred before Asset publication or Audacity dispatch.
- Package 0.4.8 adds bounded Windows ffprobe discovery and explicit executable overrides; mandatory validation remains fail-closed.

## Final Behavioral Evidence — package 0.4.9

- Returned archive: `task004-live-evidence-behavior(6).zip`.
- Top-level result: `ok=true`.
- Noise Suppression: `PASS`; operation `COMPLETED`; one validated derived AUDIO Asset and committed Manifest.
- Music Separation 2-stem: `PASS`; operation `COMPLETED`; complete `instrumental` and `vocals` Assets and committed Manifest.
- Database: four operations `COMPLETED`, zero failed; two source Assets, three derived Assets, four committed Manifests.
- Safety: deterministic synthetic inputs only, no user media, empty Audacity project required, isolated Product runtime paths.
- Decision: `ACCEPTED_FOR_TASK_COMPLETION`.

## Behavioral Evidence Attempts 09–10 — package 0.4.9 corrective

- Attempt 09 stalled at `IMPORTING_SOURCE` with a legacy-Windows-length repository path and was manually interrupted.
- Attempt 10 used `D:\BAI\ai-video-production`, completed the bounded runner, and returned a first-command Audacity failure.
- Package 0.4.9 converts Windows file arguments to forward-slash form for mod-script-pipe, rejects paths longer than 259 characters before dispatch, and records the failed command ID, precise phase, and sanitized reply SHA-256.
- Explicit-path integration reached the Audacity boundary; full local regression: **250 / 250 PASS**.
