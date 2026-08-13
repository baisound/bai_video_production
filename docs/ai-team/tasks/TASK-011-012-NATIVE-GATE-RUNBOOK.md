# TASK-011 / TASK-012 Native Gate Runbook

- Date: 2026-08-13
- Purpose: minimize Owner/operator steps for the remaining R0 native gates
- Scope: Windows + DaVinci Resolve + Cubase acceptance only

## Preconditions

- Work from the current `feature/task-007-012-native-validation` checkout or its successor branch.
- Keep existing `evidence/` untracked unless a separate Evidence publication decision is made.
- Do not run the Resolve render gate while a human production Project is current.
- Use a dedicated `BAI_CAPABILITY_PROBE_*` Resolve Project.
- The target Timeline must be the exact TASK-010 deterministic `BAI_AUTO_<12HEX>` Timeline.
- No release/tag/version change is part of this runbook.

## Gate 1 — TASK-011 real Resolve render

Preferred path: pass the persisted TASK-010 assembly plan so timeline identity and expected duration are not typed manually.

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task011-native-render-gate.ps1 `
  -SandboxProject "BAI_CAPABILITY_PROBE_TASK011_20260813" `
  -EvidenceRoot ".\evidence\native\task011-final" `
  -Output ".\evidence\native\task011-final\task011-native-render-qa.json" `
  -AssemblyPlan ".\path\to\resolve-assembly-plan.json" `
  -AuthorizeResolveRender
```

If a saved assembly plan is not available, use the exact Timeline name and expected duration frames from TASK-010 Evidence:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task011-native-render-gate.ps1 `
  -SandboxProject "BAI_CAPABILITY_PROBE_TASK011_20260813" `
  -EvidenceRoot ".\evidence\native\task011-final" `
  -Output ".\evidence\native\task011-final\task011-native-render-qa.json" `
  -TimelineName "BAI_AUTO_XXXXXXXXXXXX" `
  -ExpectedDurationFrames 123 `
  -AuthorizeResolveRender
```

The Product default loudness profile is `-16 LUFS ±2 LU`, max true peak `-1 dBTP`. If the native fixture has a deliberately different delivery target, pass the intended policy explicitly; do not silently loosen the product default just to obtain PASS.

### TASK-011 PASS evidence

The JSON must show:

- `gate=NATIVE_RESOLVE_RENDER_QA`
- `status=PASS`
- `qa_report.status=PASS`
- expected exact Project timeline rate
- one render artifact
- `render_artifact.path_persisted=false`
- `render_job.id_persisted=false`

## Gate 2 — TASK-012 EDITOR_WORK integrity

Before Cubase, package integrity can be checked without claiming final native close:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task012-native-handoff-gate.ps1 `
  -EditorWorkRoot ".\path\to\EDITOR_WORK_XXXXXXXXXXXX" `
  -Output ".\evidence\native\task012\task012-editor-work-pre-cubase.json"
```

This may PASS with `cubase_roundtrip.status=NOT_PRESENT`.

## Gate 3 — real Cubase round-trip

Use the documented TASK-012 human/editor workflow:

1. Open the handoff's audio export in Cubase.
2. Perform the intended bounded audio finishing work.
3. Export a PCM WAV at exactly 48 kHz.
4. Register the return through the existing `EditorHandoffService.register_cubase_return` route used by the product/diagnostic tooling.
5. Run the final gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-task012-native-handoff-gate.ps1 `
  -EditorWorkRoot ".\path\to\EDITOR_WORK_XXXXXXXXXXXX" `
  -Output ".\evidence\native\task012\task012-native-cubase-final.json" `
  -RequireCubaseReturn
```

### TASK-012 PASS evidence

The JSON must show:

- `gate=NATIVE_EDITOR_WORK_HANDOFF`
- `status=PASS`
- `cubase_roundtrip.status=PASS`
- `sample_rate=48000`
- `editor_work_root_persisted=false`

## R0 exit

Only after TASK-010, TASK-011 and TASK-012 native Evidence are all accepted may the backend editing milestone be recorded as:

`BACKEND_NATIVE_EDITING_MVP_PASS`

This does **not** mean the normal-user product flow is complete. TASK-036 unified Desktop E2E remains required for `MINIMUM_EDITING_PRODUCT_MVP_PASS`.
