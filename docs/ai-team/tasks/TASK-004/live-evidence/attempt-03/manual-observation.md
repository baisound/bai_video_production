# TASK-004 Live Evidence Attempt 03 — Audacity/OpenVINO

- Target package reported by user: `0.4.2`.
- Command: `run-task004-local-ai-capability-probes.ps1 -SkipComfyUI -AudacityTimeoutSeconds 120`.
- Result: `PENDING/FAILED (exit 2)`.
- Worker reached `DISCOVERING_COMMANDS`.
- Failure: `ERR_PROVIDER_AUDACITY_OPENVINO_WORKER_FAILED` / `Audacity response did not contain JSON`.
- Prior target evidence already proved `ToSrvPipe` and `FromSrvPipe` exist and Audacity UI exposes OpenVINO Music Separation, Noise Suppression and Super Resolution.
- Review conclusion: write-side CRLF+NUL framing was no longer the blocking issue. Product reply parsing incorrectly terminated on a leading blank line that Audacity may emit before the JSON payload.
- Corrective route: package 0.4.3 changes only response framing/parsing behavior and requires an Audacity capability-only rerun.
