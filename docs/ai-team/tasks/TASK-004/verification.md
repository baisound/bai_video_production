# TASK-004 — Verification Record

- Verification status: `LOCAL_IMPLEMENTATION_VERIFIED`
- Completion status: `LIVE_CAPABILITY_EVIDENCE_PENDING`
- Package: `0.4.2`
- Governance: `DEV-4 FOUNDATION CRITICAL`

## Local verification

- `python -m pytest -q`: **233 / 233 PASS**
- `python -m compileall -q src tests`: PASS
- `git diff --check`: PASS
- wheel build with `pip wheel --no-deps --no-build-isolation`: PASS
- wheel SHA-256: `5f1e9a7c81de56b2ac8612272294c40e340d80434cd551cfa1867cf04dde63d6`
- installed-wheel package version: `0.4.2`
- packaged TASK-004 schema resources: PASS
- installed-wheel golden media ingest + forced CFR proxy + 48 kHz PCM analysis-audio normalization using real `ffmpeg`/`ffprobe`: PASS
- installed-wheel unavailable-ComfyUI diagnostic: expected fail-closed `ERR_PROVIDER_COMFY_UNREACHABLE`, exit 2
- installed-wheel unavailable-Audacity diagnostic: expected fail-closed `ERR_PROVIDER_AUDACITY_PIPE_UNAVAILABLE`, exit 2

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
- dynamic effect capability discovery;
- empty/sandbox-project safety gate;
- Noise Suppression and complete 2/4-stem Music Separation contracts;
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
