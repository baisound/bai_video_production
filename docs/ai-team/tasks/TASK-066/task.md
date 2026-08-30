# TASK-066 - GPU-First Desktop Execution, Packaging and Diagnostics

- Status: `OWNER_AUTHORIZED / P0 DESIGN_ACCEPTED / IMPLEMENTATION_ALLOCATED_BY_DEPENDENCY / NATIVE_PROOF_PENDING`
- Capability: `BVP-GPU-FIRST-DESKTOP-EXECUTION-001`
- Development profile: `DEV-4 FOUNDATION CRITICAL`
- Canonical design base: `75538cbf584c2807f02e0d3de51e3653d7e2baf0`
- Owner instruction date: `2026-08-31`

## Objective

Create one cross-application compute policy decided at process startup, not by a mandatory first-run choice. The default is `AUTO_GPU_FIRST`:

1. inventory the executable and requested workload;
2. detect compatible graphics and compute backends;
3. select the highest-ranked compatible GPU backend;
4. keep GPU-backed UI rendering enabled where the UI technology supports it;
5. never silently fall back from a GPU-required AI workload to CPU;
6. expose Auto / GPU / CPU and detected backend under top-right Settings;
7. preserve an actionable, privacy-safe, bounded diagnostic log on failure.

Ordinary Python control flow, filesystem work and orchestration remain CPU work. Product truth means GPU-backed rendering where supported and GPU-backed AI/media compute whenever a compatible admitted backend exists.

## Current gap

Current source has isolated GPU-aware implementations: TASK-054 CUDA probing, `device=auto/cpu/cuda` FasterWhisper controls, and normal WebView2 hardware acceleration. It has no canonical cross-EXE startup policy, common Settings projection, all-EXE installer manifest, license-bound DLL manifest or bounded common diagnostic log. Training Studio, Trivia Editor and Voice Model Builder are Tk frontends and have no GPU-rendered UI guarantee. Capture Controller is confirmed as WinForms; its app-drawing acceleration and packaged runtime Evidence remain `NOT_CONFIRMED`.

## Product inventory

| Executable | Classification | Required result |
|---|---|---|
| `BAI Video Production.exe` | unified desktop | WebView2 renderer Evidence is separate from compute preference; Auto/GPU/CPU applies only to registry-listed admitted local Planning/Image/Video/Audio workloads; remote/cloud is not applicable and unproven adapters stay disabled; no silent CPU fallback |
| `BAI DbD Training Studio.exe` | user utility | GPU compute; common profile/logging; integrate into unified GPU Shell or replace Tk frontend before an all-window GPU claim |
| `BAI DbD Trivia Editor.exe` | user utility | common profile/logging; integrate into unified GPU Shell or replace Tk frontend before an all-window GPU claim |
| `bai-voice-model-builder.exe` | user-facing Tk technical preview | supported voice compute admission, common status/logging, and unified-Shell or replacement-frontend convergence before an all-window GPU claim; model/training gates remain |
| `bai-voice-capture-controller.exe` | native WinForms user controller | app-drawing GPU acceleration remains `NOT_CONFIRMED`; GF-C audits packaged/runtime behavior; OBS/plugin/recording gates remain |
| `BAI Video Production Key Helper.exe` | private non-UI helper | `NOT_APPLICABLE_PROVEN`; no GPU or Settings dependency |
| `BAI Video Production GPU Runtime Installer Helper.exe` | private non-UI installer helper | CPU-only provisioning entry; no GPU preference, Settings or user launch surface |
| OBS plugin/third-party EXEs | external component | no BVP GPU preference or driver mutation |

## Priority and dependencies

TASK-066 is a `P0 PACKAGED-DESKTOP PREREQUISITE` before:

- TASK-036 P-UX-2E packaged-native functional-export closure;
- TASK-049/TASK-052 packaged DbD and real-media acceptance;
- TASK-062 packaged Desktop UX acceptance;
- a new unified Windows installer/release candidate.

Independent non-native backend work continues in parallel. Completed Task history is not reopened.

## Allocated Atomic Units and assignees

| Unit | Responsibility | Assignee |
|---|---|---|
| `GF-A` | common policy/schema, startup probe, backend ranking, safe read-back and negative tests | Development 4 |
| `GF-B` | main EXE, WebView2 GPU, top-right Settings, Planning/Image/Video UI and disabled states | Development 2 |
| `GF-C` | audio/voice/FasterWhisper/TTS capability mapping and no-silent-CPU tests | Development |
| `GF-D` | DbD EXEs, GPU compute, unified-Shell or GPU-rendered-UI closure | Development 3 |
| `GF-E` | installer/build payload, per-EXE preference, DLL/license manifest and log provisioning | Production Linkage Setup |
| `GF-F` | clean build/install/launch/operator verification and unsupported-machine matrix | Development 4 |

The main-integration task integrates eligible frozen PR heads only and owns no implementation.

Design Critic reports Critical/High `0/0` and the Design Judge returns `ACCEPT`. Each allocation is now effective only after its own upstream boundary plus fresh main, clean/owned worktree, open-PR overlap and work-lock evidence are satisfied. Allocation never bypasses a dependency or side-effect Gate.

## Dependency and file-ownership matrix

All units consume TASK-066 common contracts from base `75538cbf584c2807f02e0d3de51e3653d7e2baf0` and must rebind fresh main before mutation.

| Unit | Required upstream boundary | MAY MODIFY after allocation | MUST NOT MODIFY | Shared owner/lock |
|---|---|---|---|---|
| GF-A | accepted immutable TASK-063 descriptor revision/head on fresh main supplies `install_instance_id` only; GF-A defines a TASK-066 InstallLayout sidecar/resolver and frozen workload registry; no installer mutation | new `desktop_install_layout.py`, `desktop_compute_policy.py`, `desktop_compute_probe.py`, `desktop_compute_diagnostics.py`; schemas/mirrors; `tests/test_task066_desktop_*.py` | Shell, voice, DbD, installer, existing Task backends | TASK-066 policy Builder; new paths only |
| GF-B | accepted GF-A schema/read API; TASK-036 current Shell contract; active TASK-063 packaged-entry work must be terminal and read back before any entrypoint integration | `task036_shell_ui.py`, `task036_shell_v611.py`, focused TASK-066/TASK-036 tests | `task036_packaged_entry.py` until a separately frozen TASK-063 handoff, PyInstaller specs, TASK-013/027 producer backends, voice/DbD source, TASK-063 installer | Development 2 is sole Shell writer under exact lock |
| GF-C | accepted GF-A schema/read API; TASK-046/047 authority remains unchanged | `faster_whisper_asr.py`, `voice_model_builder_beginner_client.py`, `voice_model_builder_engine_capability_probe.py`, a new TASK-066 audio adapter, focused tests; read-only Capture Controller classification against its exact native entry/UI source | recording, Consent, Dataset, training, Owner voice processing, Shell and installer | Development owns audio files; no new voice authority. If the audit requires Capture Controller UI change, `GF-C2` is separately allocated to Development before mutation |
| GF-D | accepted GF-A schema/read API; current TASK-049/052/054 boundaries | `dbd_reasoning_local_runtime.py`, `dbd_training_studio.py`, `dbd_trivia_editor.py`, TASK-049 Windows entries, focused tests | PyInstaller specs, inference truth, Dataset/training gates, TASK-036 Shell, installer | Development 3 owns DbD paths; exact per-file lock |
| GF-E | accepted GF-A manifest/API; active TASK-063 main-installer work must be terminal and read back | new TASK-066 packaging manifest/validator/private helper entry+spec/tests; `task063_main_installer.iss` and existing EXE specs only after TASK-063 handoff and exact lock | `task036_packaged_entry.py`, TASK-063 CLI/bridge semantics, Product backends, display driver, system CUDA/PATH | Production Linkage Setup is sole packaging writer; TASK-063 handoff required; dedicated TASK-066 helper follows the existing TASK-063 dispatch |
| GF-F | GF-A through GF-E accepted frozen heads and separate native authority | TASK-066 runbook/evidence and bounded native fixtures only | Product source, producer receipts, Release/Deploy | Development 4 operator; no source write during observation |

Each handoff records base/head, changed paths, tests, Critic result, effect ledger and rollback point. Shared files have one writer; another unit waits on that file only and continues non-conflicting work.

### Exact candidate Allowed Files

- GF-A: `src/ai_video_production/desktop_install_layout.py`, `src/ai_video_production/desktop_compute_policy.py`, `src/ai_video_production/desktop_compute_probe.py`, `src/ai_video_production/desktop_compute_diagnostics.py`, `schemas/desktop-install-layout.schema.json`, `src/ai_video_production/schema_resources/desktop-install-layout.schema.json`, `schemas/desktop-compute-profile.schema.json`, `src/ai_video_production/schema_resources/desktop-compute-profile.schema.json`, `schemas/desktop-compute-workload-registry.schema.json`, `src/ai_video_production/schema_resources/desktop-compute-workload-registry.schema.json`, `schemas/desktop-renderer-evidence.schema.json`, `src/ai_video_production/schema_resources/desktop-renderer-evidence.schema.json`, `tests/test_task066_desktop_install_layout.py`, `tests/test_task066_desktop_compute_policy.py`, `tests/test_task066_desktop_compute_probe.py`, `tests/test_task066_desktop_compute_diagnostics.py`, `tests/test_task066_desktop_renderer_evidence.py`.
- GF-B: `src/ai_video_production/task036_shell_ui.py`, `src/ai_video_production/task036_shell_v611.py`, `tests/test_task036_shell_ui.py`, `tests/test_task066_shell_compute_settings.py`. `src/ai_video_production/task036_packaged_entry.py` and its test remain excluded until a later exact TASK-063 terminal handoff is reviewed and separately allocated.
- GF-C: `src/ai_video_production/faster_whisper_asr.py`, `src/ai_video_production/voice_model_builder_beginner_client.py`, `src/ai_video_production/voice_model_builder_engine_capability_probe.py`, `src/ai_video_production/task066_audio_compute_adapter.py`, `tests/test_task066_audio_compute_adapter.py`, `tests/test_task046_voice_model_builder_engine_capability_probe.py`.
- GF-C Capture Controller audit is read-only against `native/task047_obs_voice_capture/controller/BaiVoiceCaptureController.cs`, `packaging/task047_obs_voice_capture_installer.iss`, and `tests/test_task047_obs_runtime_source_contract.py`. If change is necessary, a separate `GF-C2` allocation names Development as Builder and may add only those exact paths after fresh TASK-047 historical-boundary, overlap and lock checks.
- GF-D: `src/ai_video_production/dbd_reasoning_local_runtime.py`, `src/ai_video_production/dbd_training_studio.py`, `src/ai_video_production/dbd_trivia_editor.py`, `packaging/task049_training_studio_windows_entry.py`, `packaging/task049_trivia_editor_windows_entry.py`, `tests/test_task054_dbd_reasoning_local_runtime.py`, `tests/test_task049_dbd_training_studio_packaging.py`, `tests/test_task049_dbd_trivia_editor_packaging.py`, `tests/test_task066_dbd_compute_profile.py`.
- GF-E: `packaging/task066_gpu_runtime_manifest.json`, `schemas/task066-gpu-runtime-manifest.schema.json`, `src/ai_video_production/schema_resources/task066-gpu-runtime-manifest.schema.json`, `src/ai_video_production/task066_gpu_runtime_installer.py`, `packaging/task066_gpu_runtime_installer_windows_entry.py`, `packaging/task066_gpu_runtime_installer.spec`, `tests/test_task066_gpu_runtime_installer.py`, `tests/test_task066_gpu_runtime_installer_entry.py`, `tests/test_task066_main_installer_contract.py`; after TASK-063 handoff and exact lock only, `packaging/task063_main_installer.iss`, `packaging/task036_shell.spec`, `packaging/task049_training_studio.spec`, `packaging/task049_trivia_editor.spec`. `src/ai_video_production/task036_packaged_entry.py` and `src/ai_video_production/montage_learning_installer_cli.py` remain prohibited.
- GF-F: `docs/ai-team/tasks/TASK-066/gpu-first-desktop-native-runbook.md`, `docs/ai-team/tasks/TASK-066/gpu-first-desktop-native-evidence.md`, `tests/native/task066_gpu_first_desktop/` only after exact native-fixture path admission.

An Allowed File entry does not authorize mutation before the design and unit gates. Any path outside this list requires a new bounded allocation; no wildcard expands source ownership.

## Candidate implementation files

Exact paths require each assignee's fresh main/branch/dirty/overlap/lock bind. The proposed responsibility map is:

- `src/ai_video_production/desktop_compute_policy.py` - pure preference and ranking policy;
- `src/ai_video_production/desktop_compute_probe.py` - capability discovery and loaded-runtime read-back;
- `src/ai_video_production/desktop_compute_diagnostics.py` - bounded structured diagnostics;
- `schemas/desktop-compute-profile.schema.json` and the package mirror;
- focused policy, packaging, startup, Settings, redaction, rotation and recovery tests;
- existing EXE entrypoints, PyInstaller specs and installer sources only within the assigned unit.

No unit may edit another product owner's backend or claim runtime success from package presence.

## Startup and Settings contract

- Startup resolves the preference before workload initialization. Default is `AUTO_GPU_FIRST`.
- `AUTO_GPU_FIRST` selects the best compatible admitted GPU backend. For `GPU_PREFERRED_CPU_ALLOWED` workloads only, it may select an implemented CPU adapter when no compatible GPU exists, but Settings and the action screen must display the CPU choice and exact fallback reason before execution.
- `GPU_REQUIRED` workloads never admit CPU in Auto mode.
- explicit `GPU_REQUIRED` mode rejects an unsupported or incompatible workload with a clear disabled reason.
- `CPU_ONLY` workloads use CPU and are labelled not GPU-applicable.
- `CPU_EXPLICIT` is an Owner/user-selected diagnostic or compatibility mode. It is never selected silently after a GPU failure.
- Top-right Settings exposes Auto/GPU/CPU, detected adapter, effective backend, runtime versions, compatibility result and restart requirement.
- A preference change is validated and persisted, then takes effect at the next safe workload boundary or process restart. The UI must not claim a switch before read-back.
- `BAI Video Production.exe` starts required bundled/local companion services exactly once when a selected workload needs them, with single-instance ownership and durable readiness read-back. It does not start paid/cloud providers.
- WebView2 hardware acceleration remains enabled. A Chromium process flag that disables GPU rendering is prohibited in production.
- Tkinter drawing is not GPU-rendered by configuration. Training Studio, Trivia Editor and Voice Model Builder must converge into the unified WebView2 Shell or receive an independently proven GPU-rendered frontend before the Product claims all-window GPU rendering. Capture Controller is confirmed from exact source as WinForms; its app-drawing acceleration remains `NOT_CONFIRMED`, and classification alone does not authorize a rewrite.

The Owner machine's RTX 4070 SUPER and a possible CUDA 12 / cuBLAS 12.9.2.10 / cuDNN 9.25.1.1 stack are probe candidates, not hard-coded truth. The actual loaded DLL/runtime identity and workload compatibility decide admission.

Other machines use the same capability contract. NVIDIA, AMD and Intel are reported truthfully; only an implemented and tested workload adapter is selectable. Hardware detection alone never creates compute support.

## Canonical profile, writable roots and probe trust

`binary_root` is derived from the running executable, never the current directory, and is immutable after installation. The accepted TASK-063 descriptor supplies only `install_instance_id` and its own bridge-relative path. TASK-066 therefore defines an immutable, versioned `desktop-install-layout.json` sidecar beside the binaries. It binds `install_instance_id`, install scope and the writable `data_root`: per-user `<selected-root>\data`, or `%ProgramData%\BAI Video Production\instances\<install_instance_id>` for a system-wide Program Files install. GF-A owns schema/read-only resolution; GF-E may write the sidecar only after the TASK-063 installer handoff. Missing, stale, substituted or mismatched sidecars fail closed without guessing from the current directory.

The installer creates a protected DACL: the installing user for per-user data, or SYSTEM/Administrators plus explicitly admitted Product users for a system-wide instance. No broad inherited write ACE is accepted. `settings`, `logs` and `runtime-cache` are the only new TASK-066 operational leaves. Existing canonical Project, Asset, media input, output and Export owners remain unchanged.

The versioned profile path is `<data_root>\settings\desktop-compute-profile.json`. The main EXE Settings service is the sole writer; other EXEs consume a read-only projection. Writes use a named mutex derived from `install_instance_id` with a `2 second` timeout, temp file in the same directory, flush, atomic replace and exact read-back. Unknown version, invalid schema or corrupt digest fails closed to default in-memory Auto state without overwriting the rejected file; migration requires a later schema-defined unit.

Each per-workload route binds class (`GPU_REQUIRED`, `GPU_PREFERRED_CPU_ALLOWED` or `CPU_ONLY`), effective backend, public-safe reason and stable adapter identity. Windows adapter identity uses LUID plus vendor/device/subsystem and driver-instance digest. Both Auto and GPU-required resolution rank workload-supported discrete adapters by dedicated memory descending, then stable identity ascending. TASK-066 defines no preferred-adapter selection field or hidden saved-adapter authority. An absent/tied/changed coordinate is re-evaluated and displayed, never guessed.

Capability admission separates three trust classes. Product-private runtime modules require a manifest-bound install-relative destination resolved beneath immutable `binary_root`, exact version/SHA-256 and secure loader read-back. OS/display-driver modules are never bundled and require an approved system/vendor-signed location, signer, version and matching device/driver identity. Actual workload observation is a third, separate Evidence cell. A private DLL is loaded only from the resolved Product runtime directory using an absolute secure loader call; current directory and ambient PATH are excluded.

Every probe runs without shell/network, with `5 seconds` per adapter and `20 seconds` total. Timeout or crash terminates only the exact owned probe and yields `NOT_CONFIRMED`. Device name or package presence never admits a backend.

WebView2 native verification uses the exact packaged CoreWebView2 runtime. DevTools Protocol `SystemInfo.getInfo` is capability/inventory Evidence only. GPU-rendering PASS additionally requires a separately validated per-WebView renderer/compositor observation tied to the packaged process, window and adapter; GF-B must first prove that observation route is feasible. WARP/software rendering, unavailable renderer evidence or a mismatched process/window yields `NOT_CONFIRMED`, not GPU PASS.

## Frozen renderer Evidence and workload registries

UI rendering is not a compute workload and is not affected by Auto/GPU/CPU. A separate renderer-Evidence registry fixes `shell.webview2.renderer` to `preference_applies=false` and `hardware_acceleration_policy=ENABLED_WHEN_SUPPORTED`; CPU_EXPLICIT never adds a WebView2 GPU-disable flag. It records capability inventory and the separate packaged process/window/adapter renderer observation. Tk/WinForms frontends remain independently classified and cannot inherit a compute PASS.

GF-A publishes a versioned, schema-validated registry before GF-B/GF-C/GF-D implementation. These IDs and ownership/class ceilings are frozen; `CURRENT_BIND_REQUIRED` means source must be freshly bound before an adapter is enabled.

| Workload ID | Owner | Class | Current adapter status |
|---|---|---|---|
| `planning.local.ollama` | Development 2 | `GPU_PREFERRED_CPU_ALLOWED` | current local route bind required; CPU fallback must be explicit |
| `image.local.comfyui` | Development 2 | `GPU_REQUIRED` | current local route bind required |
| `video.local.generation` | Development 2 | `GPU_REQUIRED` | adapter/runtime remains disabled until implemented and proven |
| `audio.asr.faster_whisper` | Development | `GPU_PREFERRED_CPU_ALLOWED` | current CUDA/CPU adapters require fresh bind |
| `audio.voice.local` | Development | `GPU_PREFERRED_CPU_ALLOWED` | exact TTS/voice adapter remains disabled until mapped and proven |
| `dbd.reasoning.qwen3_8b` | Development 3 | `GPU_REQUIRED` | current TASK-054 route bind required |
| `dbd.training` | Development 3 | `GPU_REQUIRED` | Dataset/training Human Gates remain unchanged |
| `dbd.trivia.editor` | Development 3 | `CPU_ONLY` | no GPU compute claim; UI convergence remains separate |
| `voice.capture.controller` | Development | `CPU_ONLY` control plane | WinForms confirmed; app-drawing acceleration and packaged runtime Evidence pending; recording/OBS authority unchanged |
| `key.helper` | Production Linkage Setup | `CPU_ONLY` | private non-UI helper; Settings-independent |

Remote/cloud providers are `NOT_APPLICABLE` to local GPU admission and remain behind their existing provider/credential/paid gates. A new workload ID, class change or CPU-fallback eligibility change requires a versioned registry revision and focused review; runtime discovery cannot invent one.

Companion services bind `install_instance_id`, service kind, executable hash, version, PID and process start time. Startup timeout is `30 seconds`, with at most one automatic start attempt per application/session and no automatic retry. Readiness must return the matching identity over the bounded local protocol. Unknown/stale ownership is parked without kill; only an exact process started and owned by this session may be terminated.

## Installer and runtime-library contract

A GPU runtime component may be bundled only when the packaging manifest binds all of:

1. official source and immutable version;
2. filename, architecture, size and SHA-256;
3. license/EULA identity and exact redistribution basis;
4. required notices and redistributable dependency closure;
5. consuming workload and compatible driver/runtime range;
6. isolated install-relative destination and loader search order;
7. pre-package legal/provenance/hash/dependency admission for an internal test payload, followed by final clean-machine load/read-back sealing before Release;
8. bounded upgrade, repair and uninstall behavior.

The installer must not bundle or install a display driver, copy DLLs from an unknown developer machine, overwrite system CUDA, mutate global `PATH`, or depend on pre-existing `E:\BAI_AI`. Product-private immutable runtime files live beneath `binary_root`; writable settings, logs and runtime-cache live beneath the sidecar-bound `data_root`. Missing writable leaves are created by the installer or first authorized startup using the canonical layout, protected DACL and exact post-create read-back.

Runtime DLLs are private to the Product and versioned. Package presence is not runtime use: the loaded module identity, backend probe, compatibility result and a focused workload observation are separate evidence cells.

### Dedicated GF-E installer entry

GF-E does not extend `--bvp-installer-bridge`, parse the TASK-063 descriptor in Inno Setup, or reuse TASK-063 CLI semantics. It packages the private non-UI `BAI Video Production GPU Runtime Installer Helper.exe` from the dedicated TASK-066 Windows entry and spec listed above.

After the existing TASK-063 post-install dispatch has successfully provisioned and read back its descriptor, the main installer invokes the TASK-066 helper exactly once. The helper calls the accepted GF-A InstallLayout resolver/validator, consumes the existing descriptor's exact `install_instance_id`, provisions `desktop-install-layout.json` plus the protected `settings`, `logs` and `runtime-cache` leaves, writes the fixed `<data_root>\runtime-cache\installation\task066-installer-readback.json` receipt, and performs its own exact sidecar/leaf/receipt read-back before returning success. Receipt creation is containment-checked, ancestor-reparse-safe, regular-file-only, hardlink-rejecting, atomic and no-clobber unless the exact prior Product receipt is validated for repair. Inno Setup consumes only the helper's exit status; it never parses or independently validates JSON, DACL, root or sidecar meaning.

The helper is not a general CLI and accepts only bounded provision/read-back, repair/read-back and uninstall-preservation operations. Each outer installer operation may launch it once, waits at most `30 seconds`, and never retries automatically. Timeout may terminate only the exact helper process started and owned by that operation; unknown ownership is not killed. It has no network, model, provider, UI, GPU execution, TASK-063 bridge mutation, physical user-data deletion or Release authority. A timeout or helper/receipt mismatch returns nonzero and fails installation or repair closed without claiming success; recovery preserves pre-existing user data and exact TASK-063 state.

Focused tests must prove: TASK-063 failure launches no TASK-066 helper; exact one helper launch for provision or repair; `30 second` timeout/no retry/owned-process-only termination; helper nonzero or read-back mismatch fails closed; exact Product receipt repair is idempotent while foreign/substituted/partial/reparse/hardlink receipt cases reject; uninstall preserves physical data; and Inno Setup contains no descriptor/receipt JSON parser.

## Diagnostic logging contract

The default Product log root is `<data_root>\logs`, created with the Product layout. Each record is structured and public-safe:

- timestamp, application/version, session and event category;
- selected preference, detected adapter and effective backend;
- public-safe runtime/version compatibility result;
- failure stage, stable reason code and one actionable next step;
- bounded exception category and correlation identity.

Logs must never contain credentials, secrets, raw prompts, transcripts, media bytes, provider payloads, private absolute media paths, or full environment dumps.

The frozen logging profile is: maximum UTF-8 record `16 KiB`; one active file per application/process family, `4 MiB` each; active plus `4` retained generations per family; one install-instance-scoped coordinator/lock namespace and one shared all-EXE directory cap `32 MiB`; retention `14 days`; per-process sustained rate `2 events/second` with burst `20`; all-EXE writer rate `10 events/second` with burst `50`; duplicate aggregation window `60 seconds`; queue maximum `512 records` and `4 MiB`; cross-process writer-lock timeout `2 seconds`; cleanup at startup, after rotation and every `15 minutes`; suspend nonessential logging below `max(512 MiB, 5% free space)`; one terminal guard record per application/session.

Under the coordinator lock, cleanup removes expired Product-owned closed generations first, then the oldest closed generation by creation sequence and stable family name until within the shared cap. It never removes foreign or active files. If active files alone reach the cap or the lock/cap cannot be recovered, nonessential writes are suspended; DEBUG then INFO are dropped first, repeated WARN/ERROR records aggregate by stable reason and count, and the queue never grows. A writer-lock timeout permits only the session's single terminal guard record when it can be written safely. Partial `.tmp` records are never parsed as complete and only exact Product-owned partials are recovered or removed. Logger failures are not recursively logged. Concurrent-process, writer-crash, active-only-cap and deterministic-eviction tests are mandatory. These numbers are Judge-frozen only after the global accounting algorithm is accepted.

The Owner's request for useful logs is a requirement, not proof that selected limits are correct.

## Acceptance

TASK-066 is complete only when:

1. every user-facing BVP EXE is classified and bound to the common startup policy;
2. default startup is automatic and GPU-first without silent workload fallback;
3. Settings can show and safely persist Auto/GPU/CPU with truthful effective-state read-back;
4. the main EXE keeps WebView2 GPU acceleration enabled;
5. each GPU-capable AI/media workload has backend-specific compatibility and negative tests;
6. incompatible/missing GPU, DLL, driver, companion service and runtime cases keep the Shell usable and explain the next action;
7. bundled GPU components pass license, hash, architecture and dependency admission;
8. clean installer-selected-root build/install/launch evidence proves no pre-existing `E:\BAI_AI` dependency;
9. single-instance and companion-process ownership are verified;
10. bounded log rotation, rate limiting, redaction, disk guard and recovery tests pass;
11. independent Critic reports unresolved Critical/High `0/0`; independent Judge accepts the final package gate;
12. real Windows read-back distinguishes UI rendering, compute backend selection and actual workload execution.

## Non-goals and gates

- no driver installation or update;
- no unsupported claim that Python orchestration or Tk rendering executes on GPU;
- no paid/cloud provider call, model download or credential mutation;
- no Release, Deploy or Production authority;
- no forced removal of CPU mode;
- no claim for hardware/runtime combinations that were not observed.

After this accepted Design Critic/Judge gate and dependency-scoped allocation, a blocked backend, installer or native observation parks only that effect; other authorized units continue without waiting for routine design ACK.

## Design review record

- Base/currentness: `75538cbf584c2807f02e0d3de51e3653d7e2baf0`; commit object exists; `HEAD == origin/main == recorded base` at final design read-back.
- Independent Design Critic: `ACCEPT`, unresolved `Critical / High / Medium / Low = 0 / 0 / 0 / 0`.
- Independent Design Judge: `ACCEPT`.
- Judge-frozen diagnostics: `16 KiB/record`; one `4 MiB` active file per application/process family; active plus `4` generations per family; shared `32 MiB`; `14 days`; process `2/s` burst `20`; global `10/s` burst `50`; dedupe `60s`; queue `512 records/4 MiB`; writer lock `2s`; cleanup startup/rotation/every `15m`; disk guard `max(512 MiB, 5% free)`; one terminal guard per application/session.
- Separate Gates retained: TASK-063 terminal handoff where named; downloads/acquisition; native execution/GF-F; final DLL package seal; Release/Deploy/Production.
- Post-acceptance delta: GF-E reported that current main exposes only the TASK-063 `--bvp-installer-bridge` dispatch and that the accepted Allowed Files had no TASK-066 provisioner entry. The dedicated private-helper design above closes that gap without extending `task036_packaged_entry.py` or TASK-063 CLI semantics. Independent delta Critic `C/H/M/L = 0/0/0/0`; independent delta Judge `ACCEPT`. GF-E mutation still requires the TASK-063 terminal handoff/read-back plus fresh currentness, overlap and exact-lock binding.
