# TASK-023 — FasterWhisper Fast Local Provider Reconciliation Detailed Design Ver.1.1

- Date: `2026-08-12`
- Status: `IMPLEMENTATION_DESIGN / OWNER_DIRECTED`
- Candidate package: `0.19.0`
- Governance profile: `DEV-3`
- Canonical Product task: `TASK-023`
- Existing implementation origin: `TASK-006`
- Runtime dependency on BAI Development OS: `NONE / PROHIBITED`
- Route classification: `DIRECT_FORWARD`
- Canonical Product Architecture: `PRODUCT-ARCH-001`
- Integration state at start: `BACKEND_CAPABILITY_ONLY`
- Target integration state for this slice: `INTEGRATION_DESIGNED`

## 1. Objective

TASK-023 shall **not** create a second FasterWhisper implementation.

The Product already has a working `FasterWhisperProvider`, explicit model-download gating,
model cache directory support, process-local loaded-model reuse, one-shot transcription,
resumable large-media transcription, private checkpoint reuse, deterministic Transcript/SRT
publication and text-free operational reporting from TASK-006.

TASK-023 closes the historical “Fast Local Provider” task by formally reconciling those
capabilities, adding a provider-neutral deterministic execution identity/evidence surface, and
registering the final Unified Desktop Application integration path.

## 2. Historical source reconciliation

The historical external-skill reference asked for:

- FasterWhisper local execution;
- selectable model / language / device / compute settings;
- cache identity;
- model/download handling;
- atomic JSON output;
- word timestamps;
- `condition_on_previous_text`;
- stable output envelope.

Current Product implementation already supersedes most of that reference:

| Historical requirement | Current Product state | TASK-023 decision |
|---|---|---|
| FasterWhisper local inference | Implemented in TASK-006 | Reuse |
| model/device/compute/VAD/beam settings | Implemented | Reuse |
| explicit model-download gate | Implemented | Reuse |
| model cache directory | Implemented | Reuse |
| model reuse | Implemented in TASK-006 Slice D | Reuse |
| large-media cache/resume | Private verified chunk/checkpoint state implemented | Reuse |
| atomic Transcript/SRT/report publication | Implemented | Reuse |
| text-free operational report | Implemented | Reuse |
| deterministic cache/execution identity | Partial: chunk config hash exists | Add Product-level execution identity |
| final transcript result cache | Not canonical | Do not add in this slice |
| word-level timestamps | Not in canonical TranscriptManifest | Explicitly defer |
| condition_on_previous_text as Product contract | Not currently canonical | Explicitly defer; do not silently change ASR behavior |

The historical reference wrote raw `source_path` into output. The Product shall **not**
reintroduce that behavior because operational evidence must remain path-minimized.

## 3. Scope

### 3.1 Add `FasterWhisperExecutionIdentity`

A deterministic identity derived from:

- `source_sha256`;
- `requested_language`;
- provider id;
- model id;
- model name;
- device;
- compute type;
- beam size;
- VAD flag;
- model-download authorization;
- whether a custom cache directory is configured.

The identity does **not** contain:

- transcript text;
- subtitle text;
- media bytes;
- raw source path;
- cache directory path;
- credentials.

Two equal inputs produce the same identity. Any identity-relevant configuration change changes
the identity.

### 3.2 Add `TASK-023 Reconciliation Report`

A model-free, network-free structured report describing the already implemented capabilities:

- local inference capability exists;
- explicit model-download gate exists;
- model cache directory is supported;
- loaded model is reused in one provider process;
- resumable large-media private state exists;
- operational report remains text-free;
- final transcript result cache is intentionally not canonical;
- word-level timestamp output is deferred;
- actual Transcript/SRT authority remains TASK-006.

### 3.3 Add developer/diagnostic evidence CLI

New command:

`ai-video-faster-whisper-evidence`

It may:

- emit provider reconciliation evidence without loading a model;
- optionally hash a real source file and emit an execution identity;
- accept an already known `sha256:<hex>` source hash instead of a file;
- never print the source path;
- never download a model;
- never run ASR;
- never emit transcript text.

**PRODUCT-ARCH-001 classification:** `DEVELOPER_DIAGNOSTIC_INTERFACE`.

This CLI is not the final user-facing transcription workflow.

## 4. Unified Application Integration

- User-facing classification: `USER_FACING capability with developer diagnostic CLI`
- Integration state at start: `BACKEND_CAPABILITY_ONLY`
- Target integration state at exit: `INTEGRATION_DESIGNED`
- User Entry Point: `BAI Video Production.exe`
- Shell / Workspace Location: `Subtitle Workspace`
- Project Context: current BAI Video Production Project
- Asset Context: selected Media Asset from the Project Asset Browser
- Timeline/Edit Plan Context: transcript/subtitle output remains bound to canonical Asset identity; downstream timeline placement remains TASK-006/TASK-010 owned
- Primary User Flow:
  1. User selects media in the unified Project/Media surface.
  2. User enters Subtitle Workspace.
  3. User chooses Transcribe.
  4. Subtitle Application Service resolves FasterWhisper provider/settings.
  5. Background transcription runs with progress/status.
  6. Result opens in Subtitle Workspace for review.
  7. User approves/edits/export/handoff through unified workflow.
- Running/Progress UX:
  - queued/running/chunk progress;
  - elapsed progress where available;
  - resume state;
  - model availability/download authorization state.
- Success UX:
  - transcript/subtitle result appears in Subtitle Workspace;
  - result is attached to the selected Project/Asset;
  - no terminal interaction required.
- Failure UX:
  - actionable Product error in Shell;
  - retry/restart options when supported;
  - no silent localhost failure.
- Cancel/Retry/Recovery:
  - future Shell integration uses existing bounded resumable large-media state;
  - cancellation/retry semantics require the Shell integration slice before `SHELL_INTEGRATED`.
- Open/Save/Import/Export UX:
  - media selection comes from Project/Asset browser or native Open flow;
  - output location is Product-managed or selected with native file/folder UX;
  - raw path typing is not the final workflow.
- Settings / Provider configuration:
  - unified AI Connection / Provider Settings surface;
  - model/device/compute/VAD/download policy exposed there as product settings where appropriate.
- Background worker lifecycle:
  - owned by BAI Video Production Application Shell;
  - user does not manually start local worker/CLI.
- Review / Approval:
  - existing Subtitle Workspace review remains the approval surface.
- External application interaction:
  - none required for transcription;
  - downstream Resolve/Premiere/After Effects handoff is separate adapter ownership.
- CLI / localhost role:
  - CLI is `DEVELOPER_DIAGNOSTIC_INTERFACE`;
  - existing localhost Subtitle UI is `TRANSITIONAL_INTERNAL_UI` until embedded/replaced by unified Shell.
- Native Windows acceptance for this slice:
  - diagnostic CLI runs on a real local file;
  - no model load/download/inference;
  - no source path leakage.
- Native Windows acceptance for future `SHELL_INTEGRATED` state:
  - one EXE launch;
  - Subtitle Workspace reachable from Shell;
  - native file selection/focus;
  - visible progress/success/failure;
  - no terminal/browser startup.
- Integration state on Task exit: `INTEGRATION_DESIGNED` if all slice gates pass.

## 5. Non-goals

TASK-023 does not:

- create another FasterWhisper provider;
- create a second Transcript schema;
- modify Subtitle Workspace behavior in this slice;
- implement the unified Desktop Shell in this slice;
- add Resolve writes;
- add word-level Transcript schema;
- add WhisperX alignment or diarization;
- add a public/final transcript-result cache;
- change `condition_on_previous_text`;
- change recognition output;
- download models during evidence collection;
- add BAI Development OS runtime dependencies.

## 6. Ownership

| Concern | Owner |
|---|---|
| Transcript/SRT canonical contracts and actual ASR flow | TASK-006 |
| Formal FasterWhisper local-provider reconciliation/evidence | TASK-023 |
| Unified Subtitle Workspace integration target | PRODUCT-ARCH-001 + future Shell integration slice |
| Large-media resumable private work state | TASK-006 Slice D |
| Cut Candidate analysis | TASK-024 |
| Final Cut Plan | TASK-007 |
| Resolve mutation | TASK-010 |
| Development governance | external BAI Development OS only |

TASK-023 may describe TASK-006 capabilities but must not re-authorize or duplicate them.

## 7. Execution identity contract

Canonical payload before hashing:

```json
{
  "identity_version": "1.0.0",
  "source_sha256": "sha256:<64 hex>",
  "requested_language": "ja",
  "provider": {
    "provider_id": "...",
    "model_id": "...",
    "model": "small",
    "device": "cpu",
    "compute_type": "int8",
    "beam_size": 5,
    "vad_filter": true,
    "model_download_authorized": false,
    "custom_cache_directory_configured": false
  }
}
```

`config_sha256` hashes the provider subdocument.
`execution_sha256` hashes the complete identity input.

The cache directory’s actual filesystem path is excluded intentionally.

## 8. CLI contract

Examples:

```powershell
ai-video-faster-whisper-evidence

ai-video-faster-whisper-evidence `
  --source-file .\sample.wav `
  --language ja

ai-video-faster-whisper-evidence `
  --source-sha256 sha256:<64hex> `
  --language ja
```

`--source-file` and `--source-sha256` are mutually exclusive.

Successful output is one JSON object. It contains no media/transcript text and no source path.

## 9. Failure policy

Fail closed on:

- malformed SHA-256;
- missing/non-file source;
- unreadable source;
- unsupported invalid provider config (delegated to existing `FasterWhisperConfig`);
- mutually exclusive source arguments.

No evidence object may claim inference occurred.

## 10. Privacy / evidence policy

Allowed:

- checksums;
- provider/model identifiers;
- bounded runtime settings;
- boolean cache-directory-configured signal;
- capability/reconciliation statuses.

Disallowed:

- raw source path in JSON;
- raw cache directory path in JSON;
- transcript/subtitle body;
- secret values;
- model files.

## 11. Compatibility decision

This slice intentionally **does not modify `FasterWhisperProvider.transcribe()`**.

Reason:

1. TASK-006 native ASR is already released and verified.
2. TASK-023 is reconciliation, not a recognition-quality retuning task.
3. Adding word timestamps or changing `condition_on_previous_text` would alter recognition
   semantics and canonical schemas.
4. Those changes need separate measured quality evidence, not a bookkeeping reconciliation.

## 12. Acceptance tests

1. Reconciliation report can be built without loading the FasterWhisper model.
2. Report declares TASK-023 ownership and TASK-006 implementation origin.
3. Report contains no transcript text/source/cache path.
4. Execution identity is deterministic.
5. Changing source SHA changes execution identity.
6. Changing requested language changes execution identity.
7. Changing model/device/compute/beam/VAD/download/cache-configured state changes config identity.
8. Invalid SHA is rejected.
9. CLI with a real file hashes it without printing its path.
10. CLI with SHA only needs no media file.
11. CLI does not invoke the model factory.
12. Existing model-reuse test remains green.
13. Existing large-media resume tests remain green.
14. Full Product regression remains at or above the post-architecture baseline of 435 passed,
    except for understood test additions/skips.
15. `git diff --check` and `compileall` PASS.
16. Detailed design contains the complete `Unified Application Integration` block.
17. Task exit classification is not higher than `INTEGRATION_DESIGNED`.

## 13. Native Windows Gate

Because recognition behavior is unchanged, TASK-023 native Gate is:

1. install editable package;
2. run `ai-video-faster-whisper-evidence --source-file <real local media>`;
3. verify JSON `ok=true`;
4. verify `source_path_in_evidence=false`;
5. verify `transcript_text_in_evidence=false`;
6. verify `model_loaded=false`;
7. verify `inference_performed=false`;
8. verify no model download/network side effect.

Existing TASK-006 real-ASR evidence remains the behavioral proof for the provider itself.

This does **not** satisfy future `SHELL_INTEGRATED` or `NATIVE_VALIDATED` desktop state.

## 14. Critic review

### C-023-01 — Duplicate provider risk
Resolved. No second provider is created.

### C-023-02 — “cache” could accidentally become a transcript-text cache
Resolved. This slice adds deterministic identity only. Existing private resumable work state
remains the only result reuse mechanism.

### C-023-03 — Historical word timestamps could expand canonical schema
Resolved. Explicitly deferred.

### C-023-04 — Historical raw source path leaks privacy
Resolved. Evidence exposes only SHA-256; raw paths are prohibited.

### C-023-05 — Reconciliation might retune ASR under the guise of cleanup
Resolved. `FasterWhisperProvider.transcribe()` behavior is unchanged.

### C-023-06 — Diagnostic CLI could be mistaken for final UX
Resolved. PRODUCT-ARCH-001 classification is explicit: `DEVELOPER_DIAGNOSTIC_INTERFACE`.

### C-023-07 — Backend completion could be overstated as integrated application completion
Resolved. Slice exits at `INTEGRATION_DESIGNED`, not `SHELL_INTEGRATED`.

## 15. Judge design decision

`PASS FOR IMPLEMENTATION`

TASK-023 remains `DIRECT_FORWARD`.

The implementation is bounded to reconciliation/evidence + deterministic identity. It does not
reopen TASK-006, does not change ASR semantics, and does not pretend that the unified desktop
Subtitle Workspace integration is already implemented.
