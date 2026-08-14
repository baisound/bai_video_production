# TASK-013 — R4 Local Comfy Native Failure / Recovery Evidence

- Date: `2026-08-14`
- Branch: `codex/task-013-r4-local-comfy-native-adapter`
- Owner: `TASK-013`
- Scope: contained local/free MiniMax H3 transport/runtime proof only
- Result: `NATIVE_RUNTIME_PARKED / RECOVERY_REQUIRED`

## Evidence boundary

Both attempts used loopback ComfyUI, the package-owned body-free workflow with canonical SHA-256 `sha256:1a1d2a6108c5fe94df006f3c9177832db51302d4135b1e502e2c71afef2194f8`, repository-ignored Product-owned runtime roots and a non-production private Prompt. Prompt content is not recorded here. No paid Provider, credential, production project, Candidate, Audit decision, Resolve/Cubase mutation or publish action was used.

## Attempt 01 — known native execution failure

- Execution: `EXEC-NATIVE-PROBE-20260814-01`
- Comfy prompt id: `91cb547f-1056-44a5-a2b5-9ddfd0c5621a`
- Durable journal state: `FAILED`
- Observable progress: GPU utilization reached the real execution path and the installed native MiniMax H3 models were loaded/staged.
- Failure: `SamplerCustomAdvanced` raised `RuntimeError: hostbuf_file_reader_read failed`.
- Output: none; no Product canonical output was published.

This is a known external runtime failure. It is not a generated-media PASS and does not authorize Candidate/TASK-040 Attempt binding.

## Attempt 02 — uncertain external interruption

- Execution: `EXEC-NATIVE-PROBE-20260814-02`
- Comfy prompt id: `f92c56e4-4fd8-44fc-b347-d7d4acdfed8b`
- Durable journal state: `QUEUED`
- Runtime flags included legacy low-VRAM operation: `--disable-dynamic-vram`, `--disable-async-offload`, `--disable-pinned-memory`, `--lowvram`.
- External event: Windows became unresponsive and the Owner confirmed a forced restart.
- Output: none observed; no Product canonical output was published.

The forced restart prevents a truthful terminal Product result. The journal therefore remains `QUEUED`; it must not be edited to `FAILED` merely to simplify state and it must never be automatically replayed. Any recovery decision must identify this exact prompt and inspect external state first.

## Corrective control and parking decision

The concrete adapter now verifies the live Comfy process arguments before reserving or dispatching an execution. It requires exact loopback listen/port, `--disable-auto-launch` and the configured Product-owned output root. It rejects `--disable-dynamic-vram`, `--lowvram`, `--highvram`, `--novram`, `--gpu-only` and `--cpu` before any queue side effect.

The current-machine legacy native route is `PARKED_TO_SAFE_RUNTIME_REVIEW`. No third native attempt is authorized from this Evidence. Resumption requires a separately reviewed runtime strategy that does not use the rejected flags, preserves isolated roots and proves sufficient host/GPU stability. Hosted review of the fail-closed adapter may continue independently.

## Claims explicitly not made

- no native MiniMax H3 completion PASS;
- no generated-video quality PASS;
- no Candidate, Prompt Attempt or Human Audit publication;
- no TASK-013 or R4 overall completion;
- no package version, Tag or GitHub Release decision.
