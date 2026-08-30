# TASK-066 GPU-First Desktop Execution Design

Date: `2026-08-31`
State: `DESIGN ACCEPTED / IMPLEMENTATION ALLOCATED BY DEPENDENCY / NATIVE PROOF PENDING`
Base: `75538cbf584c2807f02e0d3de51e3653d7e2baf0`

## Decision

BAI VIDEO PRODUCTION uses one startup-resolved compute profile for every user-facing Windows executable. Default mode is `AUTO_GPU_FIRST`; top-right Settings also offers explicit `GPU_REQUIRED` and `CPU_EXPLICIT` choices. The effective choice is workload-specific and must be read back from the loaded runtime.

The Product distinguishes UI renderer acceleration, the admitted AI/media compute backend, and an actual completed workload observation. None may be inferred from another. GPU hardware discovery or bundled DLL presence alone is not execution proof.

## Current source audit

- `task036_packaged_entry.py` provides the unified packaged entry and native/single-instance probes.
- `task036_shell_ui.py` starts WebView2 with the Edge Chromium engine. Production source did not show a GPU-disable flag.
- TASK-054 has an NVIDIA/CUDA-focused local reasoning runtime.
- Training Studio has FasterWhisper Auto/CPU/CUDA selection.
- current TASK-054 lock data is tied to an older CUDA/cuBLAS/cuDNN family and must not be treated as the Owner machine's loaded runtime.
- Training Studio, Trivia Editor and Voice Model Builder are Tk frontends. Capture Controller is a WinForms native controller (`CaptureForm : Form` and `Application.Run`); its app-drawing GPU acceleration remains `NOT_CONFIRMED`. Tk drawing has no supported switch that makes the whole window GPU-rendered.
- no common cross-EXE compute preference, DLL custody manifest, loaded-module read-back, or bounded common logging contract was found.

Conclusion: the Product is partially GPU-aware, but an all-desktop GPU-first claim is not currently established.

## Startup sequence

EXE entry -> single-instance ownership -> immutable `binary_root` -> TASK-063 descriptor read-back -> TASK-066 InstallLayout sidecar resolution -> writable `data_root` -> read preference -> enumerate adapters -> verify runtime compatibility -> choose backend per workload -> start required local companion service once -> readiness read-back -> open Shell -> execute admitted workload -> bounded result logging.

The Shell remains available when compute admission fails. A GPU-required workload is disabled rather than silently executed on CPU.

## Canonical profile and probe contract

`binary_root` is the immutable executable directory. The accepted TASK-063 descriptor supplies `install_instance_id` and its bridge-relative path only. A versioned TASK-066 `desktop-install-layout.json` sidecar beside the binaries binds that instance to install scope and writable `data_root`; the profile is `<data_root>\settings\desktop-compute-profile.json`. The main EXE Settings service is sole writer through an install-instance named mutex, same-directory temp, flush, atomic replace and exact read-back. Other EXEs read only. Missing/substituted layout or invalid/corrupt/unknown-version preference data is preserved and produces fail-closed startup plus a visible recovery reason; the preference may use in-memory Auto only after layout identity is valid.

Workload classes are `GPU_REQUIRED`, `GPU_PREFERRED_CPU_ALLOWED` and `CPU_ONLY`. Effective routes preserve stable Windows adapter identity (LUID, vendor/device/subsystem, driver-instance digest), backend, loaded runtime identity and public-safe reason. Auto and GPU-required use the same deterministic ranking: workload-supported discrete adapter, dedicated memory descending, then stable identity ascending. No preferred-adapter field or hidden saved-adapter authority exists.

Each adapter probe is shell-free and network-free, limited to `5 seconds`; all probes are limited to `20 seconds`. Product-private runtime admission requires a manifest-bound install-relative location resolved beneath `binary_root`, version/SHA-256 and compatibility. OS/display-driver runtime admission instead requires an approved system/vendor-signed location, signer, version and matching device/driver identity; these modules are never bundled. Actual workload success remains separate. Timeout/crash terminates only the owned probe and yields `NOT_CONFIRMED`.

WebView2 packaged verification uses DevTools Protocol `SystemInfo.getInfo` only as capability/inventory Evidence. Rendering PASS separately requires a validated per-WebView renderer/compositor observation tied to the packaged process, window and adapter. GF-B first tests route feasibility; WARP/software rendering, unavailable renderer Evidence or process/window mismatch is `NOT_CONFIRMED`.

Companion startup binds install instance, service kind, executable hash/version, PID and start time. It allows one automatic start attempt per application/session, waits at most `30 seconds` for identity-bound local readiness, never retries automatically, never kills unknown/stale ownership and terminates only an exact process owned by this session.

## Preference states

| Preference | Resolution | Failure behavior |
|---|---|---|
| `AUTO_GPU_FIRST` | GPU first; CPU only for a declared `GPU_PREFERRED_CPU_ALLOWED` workload | display effective CPU and fallback reason before execution; `GPU_REQUIRED` never falls back |
| `GPU_REQUIRED` | selected compatible GPU adapter only | fail closed; Shell stays available |
| `CPU_EXPLICIT` | implemented CPU adapter | explicit user choice only |

The Settings read-back includes adapter name, backend family, loaded runtime versions, compatibility status, selected workload and restart requirement. A saved preference is not proof that it took effect.

## Cross-hardware design

- NVIDIA workloads require driver/runtime/architecture and loaded-library compatibility checks.
- AMD/Intel are selectable only when the exact workload has an implemented, packaged and tested adapter.
- integrated and multiple-GPU systems are ranked by compatibility and policy, not device name alone.
- unsupported, remote and software adapters receive a truthful disabled state.

The Owner's RTX 4070 SUPER and possible CUDA 12, cuBLAS 12.9.2.10 and cuDNN 9.25.1.1 are a high-priority probe target, never a hard-coded PASS.

## UI convergence

WebView2 hardware acceleration remains enabled. Production packaging rejects a GPU-disable Chromium flag. Training Studio, Trivia Editor and Voice Model Builder may remain bounded migration tools, but all-window GPU rendering is not accepted until every user-facing Tk function is in the unified WebView2 Shell or a replacement frontend has independent rendering proof. Capture Controller is WinForms; GF-C audits its packaged/runtime rendering while GF-C2 remains the separately allocated mutation route if convergence is required.

## Packaging and licensing

Each bundled GPU component requires official artifact coordinates, hash, architecture, dependency closure, redistribution clause, notices, private destination, consuming workload and loaded-module read-back.

Official references:

- WebView2 performance: <https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/performance>
- WebView2 flags: <https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags>
- CUDA EULA: <https://docs.nvidia.com/cuda/eula/>
- cuDNN Windows installation: <https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html>
- cuDNN support matrix: <https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/support-matrix.html>
- cuDNN SLA/EULA: <https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/eula.html>
- NVIDIA acknowledgements: the exact shipped package's bundled acknowledgements file, version and hash are mandatory manifest fields

The Product must not redistribute the display driver, alter system CUDA, mutate global `PATH`, or source DLLs from an unverified machine. Vendor runtime files are install-relative and version-isolated. If redistribution is not proven, the component is not bundled.

No GPU DLL is selected for bundling by this design alone. Before GF-E creates an internal test payload, a separate immutable manifest row for every candidate DLL must provide: exact official URL/artifact ID, vendor version, architecture, bytes, SHA-256, vendor redistributable-manifest identity, EULA/SLA revision/date and exact Attachment/item or runtime clause, acknowledgements/notice filename and hash, every transitive DLL and its license, consuming workload, compatible driver/runtime range, manifest-bound install-relative destination, and secure loader flags/search order. GF-F then records the runtime-resolved absolute module path/version/hash and clean-machine workload Evidence. Only that sealed row may enter a later Release candidate; GF-E packaging alone is not final admission.

CUDA Attachment-A eligibility does not imply cuDNN eligibility; the exact cuDNN SLA and package acknowledgements are independently required. Missing legal or dependency evidence keeps that component unbundled. Download/acquisition remains behind its existing Human gate.

## Installer-selected layout

A clean machine is assumed to have no `E:\BAI_AI`. Immutable `binary_root` comes from the executable. TASK-063's descriptor binds only `install_instance_id` and its bridge-relative path. TASK-066's versioned InstallLayout sidecar binds install scope and writable `data_root`: per-user `<selected-root>\data`, or `%ProgramData%\BAI Video Production\instances\<install_instance_id>` for a system-wide Program Files install. GF-A defines and resolves it; GF-E writes it only after the TASK-063 handoff. TASK-066 creates only protected `settings`, `logs` and `runtime-cache` leaves and verifies DACL, system-wide/per-user identity, upgrade/backward read-back and substitution failure. Canonical Project, Asset, media input/output and Export paths remain with their existing owners.

Current main has only the TASK-063 `--bvp-installer-bridge` dispatch in `task036_packaged_entry.py`; it is fixed to `montage_learning_installer_cli`. TASK-066 must not extend that dispatch or duplicate its descriptor semantics in Inno Setup. GF-E therefore packages a private non-UI `BAI Video Production GPU Runtime Installer Helper.exe` from `packaging/task066_gpu_runtime_installer_windows_entry.py` and `packaging/task066_gpu_runtime_installer.spec`.

The main installer sequence is fixed: (1) execute and verify the existing TASK-063 provision/read-back once; (2) execute the TASK-066 helper once; (3) the helper invokes the accepted GF-A InstallLayout resolver/validator, consumes the exact TASK-063 `install_instance_id`, provisions the sidecar and protected writable leaves, writes `<data_root>\runtime-cache\installation\task066-installer-readback.json`, and completes its own exact read-back before success; (4) Inno Setup consumes only the helper exit status. The receipt write is containment-checked, ancestor-reparse-safe, regular-file-only, hardlink-rejecting, atomic and no-clobber unless an exact prior Product receipt is validated for repair. Inno Setup never parses the descriptor/receipt or reimplements root/DACL/sidecar rules. Each outer provision or repair operation launches the helper once, waits at most `30 seconds`, never retries automatically and may terminate only the exact helper process it owns; unknown ownership is not killed. The helper permits only bounded provision/read-back, repair/read-back and uninstall-preservation operations and has no network, provider, model, UI, GPU execution, physical user-data deletion or TASK-063 mutation authority.

Focused tests cover TASK-063 failure preventing helper launch, exactly one invocation, timeout/no-retry/owned-process termination, helper nonzero/read-back mismatch, exact-receipt idempotent repair, foreign/substituted/partial/reparse/hardlink rejection, uninstall preservation and absence of Inno JSON parsing.

## Bounded diagnostics

Default location is `<data_root>\logs`. Frozen limits are `16 KiB/record`, one `4 MiB` active file per application/process family, active plus `4` generations per family, `32 MiB` shared all-EXE cap, `14 days`, per-process `2 events/s` sustained and burst `20`, all-EXE `10 events/s` and burst `50`, `60 second` dedupe, queue `512 records/4 MiB`, writer lock `2 seconds`, cleanup startup/rotation/every `15 minutes`, nonessential suspension below `max(512 MiB, 5% free)`, and one terminal guard event per application/session. One install-instance-scoped coordinator owns global accounting. It removes expired closed generations, then oldest closed generations by creation sequence and stable family name; foreign and active files are never deleted. If active files alone meet the cap, nonessential writes suspend. DEBUG/INFO drop first; WARN/ERROR duplicates aggregate; partial temp records never count as complete; recursive logger failures are suppressed. Concurrency, crash, deterministic eviction and active-only-cap tests are required.

## Frozen renderer Evidence and workload registries

UI rendering is governed separately from AI/media compute. The renderer-Evidence registry fixes `shell.webview2.renderer` to `preference_applies=false` and `hardware_acceleration_policy=ENABLED_WHEN_SUPPORTED`. CPU_EXPLICIT does not disable WebView2 acceleration. Its records distinguish capability inventory from the packaged process/window/adapter renderer observation; no compute route or workload result may satisfy renderer Evidence.

GF-A implements a versioned compute registry with these fixed IDs and ceilings before downstream units: `planning.local.ollama` (Development 2, GPU preferred/CPU allowed), `image.local.comfyui` (Development 2, GPU required), `video.local.generation` (Development 2, GPU required but disabled until implemented), `audio.asr.faster_whisper` (Development, GPU preferred/CPU allowed), `audio.voice.local` (Development, GPU preferred/CPU allowed but disabled until mapped), `dbd.reasoning.qwen3_8b` (Development 3, GPU required), `dbd.training` (Development 3, GPU required with unchanged Human Gates), `dbd.trivia.editor` (Development 3, CPU only), `voice.capture.controller` (Development, CPU-only control plane; WinForms rendering Evidence remains separate), and `key.helper` (Production Linkage Setup, CPU only). Remote/cloud routes are outside local GPU admission and retain provider/credential/paid gates. Any registry change is versioned and reviewed.

Credentials, secrets, full environment dumps, raw prompts, transcripts, media, provider bodies and private absolute paths are prohibited.

## Failure and recovery

| Condition | Result | Recovery boundary |
|---|---|---|
| no compatible GPU adapter | GPU_REQUIRED disabled; Auto uses CPU only for declared CPU-allowed workload and displays reason | admit an adapter or explicitly choose supported CPU |
| missing/incompatible DLL | fail closed | repair exact Product component; no system DLL copy |
| companion service absent | one bounded start and read-back | no repeated launch storm |
| multiple process owner | attach/read back or reject | no duplicate service/EXE |
| GPU fails after admission | preserve failure; no silent CPU retry | explicit decision or bounded recovery |
| log guard fails | suspend nonessential logging | preserve one bounded terminal indication |
| unknown runtime identity | `NOT_CONFIRMED` | fresh loaded-module probe |

## Verification layers

Pure policy/schema tests -> backend negative tests -> per-EXE Settings/startup/single-instance tests -> installer/license/layout tests -> logging fault tests -> packaged build/launch -> real Windows rendering/runtime/workload read-back -> independent Critic and Judge.

Full completion requires observed evidence for every user-facing EXE. One RTX 4070 SUPER PASS is evidence for that machine, not all hardware.

## Governance gate sequence

1. Design Critic unresolved Critical/High `0/0`;
2. Design Judge `ACCEPT` and exact numeric/ownership freeze;
3. implementation allocation per GF unit after fresh currentness/lock checks;
4. focused Tester and required implementation Critic for each unit;
5. integration of eligible frozen heads only;
6. GF-F real Windows clean install/startup/read-back;
7. final independent Critic Critical/High `0/0`;
8. final package Judge.

Download, native execution, Release, Deploy and Production remain separate effects and are not granted by design acceptance.

## Accepted review result

- Independent Design Critic: `ACCEPT`, `C/H/M/L = 0/0/0/0`.
- Independent Design Judge: `ACCEPT`.
- Final design currentness: recorded base, `HEAD` and `origin/main` all equal `75538cbf584c2807f02e0d3de51e3653d7e2baf0`; commit object read-back passed.
- The numeric diagnostics profile in this document is Judge-frozen. Implementation must retain the global coordinator, deterministic closed-generation eviction, active-only-cap suspension, and concurrency/crash tests.
- Allocation is dependency-scoped. It does not authorize download/acquisition, native execution, GF-F observation, final DLL package admission, Release, Deploy or Production.
- Post-acceptance Critical delta: the original GF-E Allowed Files lacked a callable packaged provisioner entry. The dedicated private-helper entry, spec, tests and exact installer ordering were independently reviewed: delta Critic `C/H/M/L = 0/0/0/0`; delta Judge `ACCEPT`. `task036_packaged_entry.py` and the TASK-063 CLI remain prohibited, and GF-E mutation still requires TASK-063 terminal handoff/read-back plus fresh currentness, overlap and exact lock.
