# TASK-004 — Local AI Live Capability Evidence Instructions

Status: `IMPLEMENTATION VERIFICATION SUPPORT`

This procedure collects **capability Evidence only**. It does not auto-install ComfyUI, MiniMax H3, FLUX/Stable Diffusion models, Spectrum, H3 SingleFrame, Audacity or Intel OpenVINO plugins, and it does not download model weights.

## Preconditions

1. Install the current package from the repository: `python -m pip install -e .`
2. For ComfyUI Evidence, start the user's local ComfyUI server. Default endpoint is `http://127.0.0.1:8188`.
3. For Audacity/OpenVINO Evidence, start Audacity with `mod-script-pipe` enabled and the OpenVINO AI plugins installed. Use an empty/sandbox Audacity project.
4. Do not open client/production audio projects while running the Audacity capability probe.

## One-command Windows probe

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task004-local-ai-capability-probes.ps1
```

Optional switches:

```powershell
# ComfyUI only
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task004-local-ai-capability-probes.ps1 -SkipAudacity

# Audacity/OpenVINO only
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task004-local-ai-capability-probes.ps1 -SkipComfyUI

# Alternate local ComfyUI endpoint
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task004-local-ai-capability-probes.ps1 -ComfyEndpoint http://127.0.0.1:8189
```

## Output

The runner writes only to `task004-live-evidence/`:

- `comfyui-capability.json`
- `audacity-openvino-capability.json`
- `_runtime/` temporary capability DB/root used by the Audacity Adapter

A failed probe is retained as diagnostic Evidence and is **not** converted into a support PASS.

## Interpretation

### ComfyUI

A successful capability response proves that the configured local ComfyUI endpoint is reachable and reports `/system_stats` + `/object_info`. The report identifies whether optional node classes such as Spectrum and H3 SingleFrame are present. It does **not** claim that MiniMax H3/FLUX/SDXL model weights are installed or that generation quality/performance has been verified.

### Audacity/OpenVINO

A successful report proves that the external Audacity scripting boundary can be reached and reports discovered OpenVINO feature commands. It does not mutate a production project and does not claim output quality until a separately authorized behavioral run is executed.

## Evidence handoff

Zip the `task004-live-evidence/` directory and return it for final DEV-4 live-evidence review. Missing optional providers may remain `NOT_VERIFIED` rather than being treated as implementation failure; required runtime claims are never fabricated.

## Audacity/OpenVINO capability timeout

The live capability probe uses a dedicated Audacity discovery timeout of **120 seconds** by default because `GetInfo: Type=Commands Format=JSON` may enumerate a large installed effect set. The timeout is configurable without changing Product execution timeouts:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task004-local-ai-capability-probes.ps1 -SkipComfyUI -AudacityTimeoutSeconds 120
```

If discovery still times out, `task004-live-evidence/_runtime/audacity/work/progress.json` records the last completed discovery phase (`OPENING_PIPE`, `PIPE_CONNECTED`, `DISCOVERING_COMMANDS`, `COMMANDS_DISCOVERED`, `DISCOVERING_TRACKS`, `TRACKS_DISCOVERED`). This is diagnostic Evidence only and does not authorize or execute an OpenVINO audio effect.

## Windows transport note for package 0.4.2

Package 0.4.2 corrects the Windows `mod-script-pipe` command terminator to Audacity's required `CRLF + NUL` framing. If package 0.4.1 produced `Audacity response did not contain JSON`, install/use 0.4.2 and rerun the Audacity-only probe; do not reinstall Audacity or OpenVINO solely for that error.
