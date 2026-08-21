# TASK-036 P-UX-2E Export Dispatch Vertical — Detailed Design

Date: `2026-08-21`
Execution owner: `開発2` (`BAI Development OS: 開発担当`)
Development depth: `DEV-4`
State: `IMPLEMENTATION_CHECKPOINT / E1 DISPATCH PARKED ON CANONICAL OWNER RECEIPT SOURCES`

## 1. Goal

P-UX-2E Atomic Unit E1 connects the existing P-UX-2D5 durable Export Job to
the existing TASK-011 render/QA runtime. It does not create another renderer,
Timeline, Job store, Final Review authority, or output-publishing authority.

The supported flow is:

```text
current typed Final Review approval
  -> exact private ExportPreparation
  -> exactly one TASK-044 durable EXPORT Job
  -> READY
  -> individual one-shot dispatch confirmation
  -> DISPATCHING persisted before the side effect
  -> existing TASK-011 render + Render QA
  -> exact artifact bytes/hash and media contract validation
  -> same durable Job SUCCEEDED
```

## 2. Authority boundary

- The browser receives only logical IDs, state versions, confirmation IDs and
  safe result identities. It never receives a host destination or adapter.
- Queue insertion and dispatch remain separate Human confirmations.
- The dispatch confirmation replaces no Final Review, rights, privacy,
  resource, audio-completion, Resolve-apply or publication authority.
- The private launcher owns the destination and dispatcher bindings.
- A dispatcher failure after `DISPATCHING` is not replayed. Startup recovery
  converts the interrupted Export to `UNKNOWN` for explicit reconciliation.
- Actual Resolve/real-media execution remains a separate Owner/native gate.

## 3. Canonical boundaries

| Concern | Existing owner used by E1 |
|---|---|
| Final approval | TASK-036 P-UX-2D3/D4 |
| Approval to queue | TASK-036 P-UX-2D5 |
| Durable Job/CAS/recovery | TASK-043/TASK-044 |
| Timeline and Export preparation | TASK-044 |
| Resolve assembly/render/QA | TASK-010/TASK-011 |
| Unified Shell composition | TASK-036 |

`ExportPreparation` is reconstructed only on an explicit dispatch preparation
request. A stale Final Review screen may still display the durable Job without
calling the private preparation provider. Reconstruction must match the exact
stored Job inputs and current Project Manifest before a confirmation is issued.

## 4. Atomic Unit E1

### May modify

- `src/ai_video_production/export_queue_application.py`
- `src/ai_video_production/export_queue.py` (additive execution-profile digest only)
- `src/ai_video_production/final_review_export_application.py`
- `src/ai_video_production/task044_nle_shell.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_shell_v611.py`
- `src/ai_video_production/task036_workflow_runtime.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- directly related TASK-036/TASK-044 tests
- this design/Evidence record

### Must not modify

- audio/voice domain implementations or receipts;
- Project/Timeline/Durable Job schema formats (the additive private
  `ExportPreparation.export_profile_sha256` digest does not add a host path,
  authority token, or Durable Job field);
- provider, rights, privacy or resource decisions;
- release, deployment or publication state.

### Acceptance

1. restart-safe private re-preparation binds the exact approval and Job;
2. UI can prepare, explicitly confirm, apply or cancel one dispatch;
3. the browser cannot inject a path, preparation, renderer or QA result;
4. confirmation storage is bounded and concurrent replay has exactly one
   admitted caller;
5. `DISPATCHING` is durable before the renderer is called;
6. synthetic output bytes are re-hashed and match the TASK-011 QA report;
7. output width/height/rate/container/video/audio contract is validated;
8. success updates the same Job and exposes no host path;
9. crash/restart becomes `UNKNOWN` and never auto-renders;
10. focused tests, adjacent integration tests, syntax and diff checks pass.

## 5. Independent review checkpoint

The first implementation pass is not commit-ready as a completed E1 and mints
no completion marker. Independent review found three material boundaries:

- dispatch apply must reconstruct the private preparation again and byte-match
  every confirmation-bound coordinate;
- TASK-011 Evidence/output roots must be isolated by durable Job identity;
- the packaged launcher must not turn a project-local self-checksummed JSON file
  into authority for the five externally owned Final Review Gates.

The first two findings are corrected in the local checkpoint. Export execution
semantics are additionally bound to a canonical `export_profile_sha256` in the
durable Job inputs. The third remains parked: packaged execution stays unbound
until each owner exposes an append-only/latest-invalidating canonical reader.
In particular, this lane consumes but never mints or rewrites the
`AUDIO_COMPLETION` receipt owned by the audio lane.

Safe parked behavior is:

```text
missing owner canonical reader
  -> Final Review Gate MISSING/UNKNOWN
  -> no Final Approval or dispatch authority
  -> existing durable Job unchanged
  -> provider/renderer call count 0
```

The owner-reader dependency is not replaced by a hand-authored PASS fixture,
launch-time cached tuple, self-hashed registry, or default/dummy provider.

## 6. Deferred P-UX-2E closure gates

E1 does not mint either
`MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_PASS` or
`TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE`.

Those remain blocked on the later packaged E2/E3 gates: clean-profile Windows,
F0..F10 restart matrix, supported viewport/DPI screenshots, keyboard/Narrator/
UIA/focus/error persistence, and one Owner-authorized real-media/native run with
durable output read-back.
