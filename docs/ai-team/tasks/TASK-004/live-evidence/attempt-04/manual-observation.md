# TASK-004 Live Evidence — Attempt 04

- Target package: `0.4.3`
- Probe: Audacity/OpenVINO capability only (`-SkipComfyUI -AudacityTimeoutSeconds 120`)
- Result: `PENDING/FAILED`
- Worker phase: `DISCOVERING_COMMANDS`
- Error: `GetInfo Commands did not return a JSON array`
- Existing target evidence already proves `ToSrvPipe` and `FromSrvPipe` are present and the Audacity UI exposes OpenVINO Music Separation, Noise Suppression and Super Resolution.
- Interpretation: Windows command framing and response-leading-blank fixes advanced the worker far enough to parse a JSON value, but whole-inventory `GetInfo: Type=Commands Format=JSON` did not yield the required top-level array on this plugin-heavy target runtime.
- Corrective route: package `0.4.4` no longer enumerates the complete Audacity command/effect inventory for TASK-004 capability discovery. It uses bounded, side-effect-free `Help` queries for the five known OpenVINO command identifiers and retains `GetInfo: Type=Tracks` only for the sandbox-project safety gate.
- Audacity/OpenVINO reinstallation is not required for this corrective route.
