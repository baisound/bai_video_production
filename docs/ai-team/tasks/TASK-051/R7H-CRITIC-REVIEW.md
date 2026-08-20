# TASK-051 R7H — Critic Review

## Judgment

`PASS_WITH_WINDOWS_HUMAN_ACCEPTANCE_REQUIRED`

## Findings by severity

- Critical: `0`
- High: `0`
- Medium: `0`
- Low: `2 accepted operational notes`

## Review

### PASS — Shared architecture is preserved

R7H fixes the shared playback foundation rather than reintroducing per-tab video implementations. Five surfaces remain bound to `TkTrainingVideoPlayer` / `TkTrainingVideoSession` and one persistent decoder contract.

### PASS — Tk thread ownership is explicit

The decoder worker can only deposit Python objects into a bounded mailbox. Tk scheduling, image creation and widget update are confined to the UI-thread poll path. This removes the background-worker-to-`root.after` ambiguity that was invisible under fake-root tests.

### PASS — Renderer defect is independently reproduced

The pre-fix binary-PGM representation was tested against a real Tk interpreter and failed when transported as base64 plus `format="PGM"`. Raw binary PGM auto-detection PASSed. R7H therefore fixes an observed renderer defect instead of relying only on inferred threading behavior.

### PASS — Diagnostics are opt-in and non-authoritative

The marker file enables diagnostic Evidence only. Logs do not create execution Authority, mutate teacher-data decisions or become canonical Product state. Logging is background/bounded and may drop diagnostic events rather than block primary Product behavior.

### PASS — Privacy boundary

Credential-like keys are redacted. Local video/source paths are stored as basename plus truncated SHA-256 identity. Raw frame payloads and transcript/OCR bodies are not emitted by the playback diagnostics foundation.

### PASS — Packaging regression protection

The packaged acceptance launcher now requires real hidden-Tk image creation plus a diagnostics event written relative to the packaged EXE. This closes the prior gap where import-only smoke could PASS while the GUI renderer failed.

## Accepted low notes

1. The Linux/Xvfb real-Tk contract proves the renderer API/PGM representation, but the exact Windows Tk build still requires the packaged Windows gate.
2. Five sessions each maintain a lightweight UI mailbox poll; Human Acceptance should confirm this does not cause observable idle or playback UI degradation. If profiling later shows measurable overhead, a shared root-level pump can be a separate performance refinement without changing the R7H contract.

## Closure condition

R7H may advance only after the Owner's Windows worktree applies cleanly, automated focused gates pass, the rebuilt EXE visibly paints real DBD frames on all five surfaces, and `diagnostics/latest.jsonl` proves the decode -> mailbox -> Tk paint chain when diagnostics are enabled.
