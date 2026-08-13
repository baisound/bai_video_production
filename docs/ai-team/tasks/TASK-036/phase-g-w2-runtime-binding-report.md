# TASK-036 Phase G W2 Runtime Binding Report

- Date: 2026-08-14
- Status: `W2_PACKAGED_NATIVE_E2E_PASS`
- Product completion claim: **NOT MADE**

## Implemented boundary

The native pywebview Shell can now continue from Human-approved Cut Review through the existing TASK-010/011/012 Application Services without accepting adapters, host paths, Resolve targets or external-write authority from JavaScript.

- a trusted pre-edit runtime composes TASK-003 ingest, TASK-006 local transcription, Subtitle Workspace creation and TASK-024 Cut Candidate generation;
- completed Cut Candidates dynamically promote the same coordinator into the Human Cut Review application without replacing Project/source/transcript identity;
- existing Product Service ports receive rights, local model, output directories and normalized analysis-audio bindings only from Python at launch;
- JavaScript cannot supply a source path, provider/model setting, analysis WAV, Product port or paid/download authorization;
- the trusted desktop composition root binds the exact Resolve adapter, source binding, frame rate, sandbox Project and runtime-only render/handoff inputs before launch;
- the bridge exposes only fixed allowlisted operations;
- Resolve compile is non-mutating;
- Resolve apply uses the existing Shell one-shot confirmation bound to the exact Project, Timeline, Edit Plan and Assembly identities;
- TASK-011 native render now has a second exact one-shot confirmation bound to the applied Assembly, sandbox Project, Automation Timeline, expected duration/rate and a Python-only Evidence destination;
- only the trusted native-render port can authorize the existing TASK-011 runner, and successful execution binds the exact Render QA identity and runtime-only artifact path back into the same desktop session;
- JavaScript passes only the one-shot `confirmation_id` for apply and cannot replace the target, adapter or source path;
- Render QA and EDITOR_WORK creation consume only trusted objects/paths already bound in the Python runtime;
- no host path is returned by workflow status.

## Native UI

The Shell now has one stage-aware `Continue` action. It displays the exact `next_recommended_action` and invokes only the corresponding allowlisted bridge operation. External Resolve apply still presents the exact Python-created target confirmation before consuming the one-shot token.

## Packaged native E2E acceptance

- the packaged CLI selects a private trusted launch configuration from an explicit argument or host environment; the WebView never receives it;
- nested configuration keys and types are exact, explicit symlinks are rejected, all durable outputs remain under the private Project root, and only `BAI_CAPABILITY_PROBE_*` Resolve targets are accepted;
- FasterWhisper/CTranslate2/ONNX/PyAV are frozen into the Windows bundle; the accepted run used a cached local model with network use and model download both false;
- the accepted 30fps source was reviewed and mapped to the real 24fps Resolve Project, producing Automation-owned Timeline `BAI_AUTO_A9AD30E48C30` with the exact assembly marker;
- TASK-011 wrote a new native render and returned PASS QA for video, audio, duration, loudness and true peak;
- empty 0-cue subtitle output was truthfully omitted from handoff rather than treated as a non-empty Asset;
- EDITOR_WORK is now preflighted and published atomically from a private staging directory, preventing a failed optional source from exposing a partial canonical handoff;
- final packaged UI state was `NONE` after atomic `EDITOR_WORK_4E36CD0D60C6` publication.

The W2 workflow gate is `SHELL_INTEGRATED / PACKAGED_NATIVE_E2E_PASS`. Overall TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS` and `MINIMUM_EDITING_PRODUCT_MVP_PASS` remain unclaimed because W0/W1 acceptance, conversation-free restart, Pilot Context Cost and exact release decision remain.

## Verification

- focused atomic handoff/launcher/runtime tests: `25 passed`;
- WSL2 Ubuntu full regression: `805 passed`;
- corrected one-dir package built with PyInstaller `6.22.0` and the project virtual environment;
- updated packaged EXE SHA-256: `2978e9f4ff649566b072ae8c3803924d11da22a597c0585c19521fb4cf4bcf84`;
- package: `461` files / `250926594` bytes; packaged native top-level window launch, real W2 E2E and normal close: `PASS`;
- the frozen module graph contains the trusted launcher, FasterWhisper runtime, pre-edit/Product ports, workflow/native-render runtime, TASK-011 runner and pywebview hooks.

Machine-readable Evidence:

- `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-runtime-binding.json`;
- `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-pre-edit-composition.json`;
- `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-render-authority-integration.json`.
- `evidence/native/phase-g-task036-w2-runtime-20260813-01/task036-w2-packaged-native-e2e.json`.
