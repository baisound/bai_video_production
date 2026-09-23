# TASK-098 A6-R1 Product/Shell Review Runtime Design

Date: `2026-09-22`
Status: `APPROVED FOR IMPLEMENTATION`
Development depth: `DEV-3 HIGH ASSURANCE`

## Authority and bounded goal

Owner authorization permits this unit to connect the already verified A4 WAV
review runtime to the normal BAI Video Production Product/Shell and to perform
bounded Windows-native verification.  Execution is allowed only after an
explicit Human action and only for the exact canonical Asset already bound by
the A4 contracts.

This unit does not authorize Asset ingest or automatic selection, TASK-041
completion/receipt creation, ASR or model activation, training, Release,
Deploy, Production activation, or a second canonical media/review store.

## Current boundary and dependency decision

- TASK-036 remains the single Product/Shell entrypoint and confirmation UI.
- The existing Product `SQLiteProductStore` and `LogicalPathResolver` remain the
  only Asset lookup and locator authorities used by the concrete runtime.
- A caller may provide an in-memory exact A4 binding provider. It may not
  provide a host path, media body, Asset selector, or runtime implementation.
- The launcher constructs the concrete registry-bound Windows runtime itself.
- When no binding provider is supplied, the feature is absent and no Asset is
  selected automatically. This is the safe default for the shipped launcher.
- A5 and the missing canonical TASK-047 receipt ABI are not dependencies for
  this non-persistent review action and remain separately blocked.

## Private/public split

The bound policy, source, capability, intent, canonical Asset ID/digests and
private workspace ViewModel remain inside Python. The ordinary Shell ViewModel
continues to expose only the A4 body-free timing projection.

One explicit Human-confirmed action may return a bounded ephemeral waveform
envelope to the local embedded Shell solely for canvas rendering. The envelope:

- is derived only after exact Asset/checksum/rights/job/range revalidation;
- contains at most 2,048 normalized integer peaks and no PCM samples;
- contains no path, Asset ID, digest, transcript/subtitle text or receipt;
- is not stored, logged, written to Evidence or added to canonical state; and
- is returned only when the runtime reports successful waveform observation.

This is a deliberate A6 local-display allowance. It does not change the A4
body-free snapshot contract or authorize a general/public waveform API.

## Human action protocol

1. Effect-zero `prepare` obtains the current private binding, builds the exact
   A4 request and creates a bounded, expiring, process-local one-use token.
2. JavaScript displays a native Shell confirmation explaining that private
   local audio playback and ephemeral waveform rendering will occur.
3. Cancel consumes the token without media effects.
4. Apply consumes the token before execution, re-reads the current binding and
   requires the exact request identity to remain unchanged.
5. The registry-bound runtime performs the already verified bounded WAV read,
   waveform generation, playback and cleanup.
6. Shell receives only the closed public runtime status plus the bounded local
   display envelope. Success never means TASK-041 review completion.

No view refresh, Project open, workspace navigation or launcher construction
may start playback or waveform generation.

## Atomic Unit and allowed files

Goal: implement and verify the Human-only Product/Shell connection.

May modify:

- `src/ai_video_production/task098_review_shell_application.py` (new)
- `src/ai_video_production/task098_review_media_runtime_windows.py`
- `src/ai_video_production/task098_review_workspace_shell_projection.py`
- `src/ai_video_production/task036_shell_ui.py`
- `src/ai_video_production/task036_trusted_launcher.py`
- exact TASK-098/TASK-036 tests for this connection
- TASK-098 current-state, task and bounded Evidence/Handoff documents

Must not modify schemas, stores, Asset ingest, TASK-041 decision/completion,
ASR/provider/model settings, packaging/installer/version, Release/Deploy, or
Production configuration.

## Acceptance criteria

1. Default/unbound Product behavior is byte-shape compatible and effect-zero.
2. The normal trusted launcher can bind the application only from an explicit
   private A4 binding provider and constructs the registry runtime itself.
3. Shell prepare/apply/cancel requests are exact; confirmation is one-use,
   expiring, capacity-bounded and stale-binding-safe.
4. No path, canonical identity, digest, text, PCM body or exception detail is
   returned to JavaScript.
5. Waveform envelope is bounded, normalized, success-only and non-persistent.
6. UI performs no media effect during refresh and requires `window.confirm`.
7. Runtime failure, cancellation, disconnect or forged output cannot claim
   playback, waveform, completion, persistence or mutation success.
8. Focused unit/integration regression passes, followed by a contained Windows
   native Product/Shell acceptance using a canonical test Asset under an
   OS-allocated temporary directory.
9. Native output/temp paths and all residual artifacts are recorded; no task
   artifact is created at or directly beneath a drive root.

## Risk review

- Critical: auto-selecting an Asset would create unauthorized ingest/ownership
  behavior. The launcher requires an explicit exact binding provider and stays
  unbound by default.
- High: stale confirmation could replay against a changed Asset. Apply consumes
  first and requires the rebuilt request to equal the prepared request.
- High: arbitrary paths could bypass Registry controls. No Shell/application
  request contains a path; only the concrete runtime resolves the Asset URI.
- High: private audio-derived data could escape. Only a capped normalized
  envelope crosses the local bridge; it is never persisted or evidenced.
- High: playback observation could be mistaken for review completion. All
  result flags keep completion, receipt, persistence, Human decision and media
  mutation false.
- Medium: refresh could accidentally execute the runtime. Snapshot and ViewModel
  routes have no Port invocation; tests assert this.
- Medium: a failed playback could leave waveform data visible. Failed results
  return an empty envelope and the UI clears the canvas before execution.
