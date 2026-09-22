# TASK-098 A4-R1b Unified Product/Shell Projection Design

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R1b DESIGN`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `a2689bf507d9821a4ba5a991a192943bff30767b`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Branch: `codex/task-098-a4-review-workspace`
- Result: `DESIGN_ACCEPTED / A4-R1B_IMPLEMENTATION_ALLOCATED`

## Capability routing

- High-Reasoning: unified Shell boundary, private/public projection split,
  failure behavior, Critic and final integration review.
- Implementation: pure projector and optional trusted Shell-provider wiring.
- Bulk/Mechanical: projection/bridge tests, documentation and Evidence.

## Goal and canonical boundary

A4-R1b may expose an already validated A4-R1a in-memory ViewModel through the
unified `Task036ShellBridge.view_model()` response. It does not reopen canonical
inputs and does not create a second Transcript, Subtitle Workspace, review store
or playback authority.

The bridge receives an optional trusted Python provider. It invokes that
provider once per `view_model()` request and projects the returned exact
`ReviewWorkspaceViewModel`; it does not retain or persist the private ViewModel.
Both the integrated-application and projection-only view-model paths pass
through one additive projection helper.

When no provider is injected, existing view-model output remains byte-for-byte
shape compatible: no new key is added and no existing Product behavior changes.

## Public allowlist

The additive key is `universal_wav_review`. Its exact projection may contain:

- projection version, `TASK-098` owner and `available=true`;
- fixed sample rate and source duration in samples;
- transcript segment ID plus original microsecond and projected sample ranges;
- subtitle cue ID plus original millisecond and projected sample ranges;
- workspace revision and the fixed-false lineage confirmation;
- current immutable waveform/segment viewport coordinates; and
- closed capability flags showing that local scrolling is representable while
  audition, waveform rendering, subtitle mutation, completion, persistence and
  Human decision are unavailable.

It must omit source/candidate/intent/workspace identity, every digest, text/raw
text, speaker/confidence/word bodies, path/locator, media/audio bytes, receipt,
canonical objects, Provider/model/store/service objects and exception bodies.
The pure Shell projection has a serializer; the private A4-R1a ViewModel still
does not.

## Failure and effect boundary

- Provider absence preserves the existing response shape.
- Provider exception, wrong return type or projection invariant failure raises
  one closed `ProductError` without returning a partial view model or embedding
  the underlying exception text.
- A4-R1b adds no JavaScript renderer or new Shell mutation/action method.
- It does not scroll state itself, read media, start playback, render a waveform,
  edit/save Subtitle Workspace state, classify completion, persist review state,
  make Provider/model/network calls or authorize Human decisions.
- A4-R2 remains the fresh review point for injected playback/waveform runtime,
  interactive controls and native acceptance.

## Allowed Files

- `src/ai_video_production/task098_review_workspace_shell_projection.py`
- `src/ai_video_production/task036_shell_ui.py`
- `tests/test_task098_review_workspace_shell_projection.py`
- `tests/test_task036_shell_ui.py` only if an existing bridge fixture requires
  direct coverage; otherwise the dedicated test owns the integration coverage
- bounded TASK-098 task/design/Evidence/current-state/task-index documentation

TASK-006/TASK-041 contracts/stores, A4-R1a internal shape, TASK-036 canonical
editing/application state, HTML/JavaScript, providers/models, media, package,
installer and Product version must not change.

## Acceptance

- exact A4-R1a input produces only the public allowlist and fixed disabled
  effect capabilities;
- all private digests/source identities and all text/body/path values are absent;
- direct projection construction rejects forged keys, rows, sample rate,
  lineage/effect claims and viewport/count disagreement;
- provider is invoked once per view-model request on both Task036 bridge paths;
- missing provider preserves the exact legacy view-model response;
- provider/projection failure becomes one closed Product error with no partial
  response or underlying exception body;
- no Shell action, JavaScript or runtime/native effect is added;
- focused and relevant TASK-098/TASK-036 regression, diff/scope/privacy scan and
  durable Evidence read-back pass.

## Critic / Tester / Judge

- High: passing the private A4-R1a ViewModel directly to JavaScript would expose
  exact source identities/digests. Corrected with an independent allowlisted
  public projection.
- High: adding an unavailable key to every legacy response could break exact
  consumers. Corrected by preserving response shape when no provider is bound.
- High: integrated-application and projection-only paths could diverge.
  Corrected by requiring one additive projection helper after either base path.
- High: provider exceptions could leak private details or return partial state.
  Corrected with a closed Product error and all-or-nothing response.
- Medium: duplicating subtitle/transcript text would create a competing body
  projection. Corrected by body-free timing rows only; existing TASK-036/TASK-006
  presentation keeps text ownership.
- Medium: exposing actions could imply playback/waveform authority. Corrected by
  snapshot-only integration with explicit unavailable effect capabilities.
- Medium: retaining the private ViewModel in the bridge could become stale.
  Corrected with one provider read per request and no bridge retention.
- Final findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.
- Judge: `ACCEPT / A4-R1B_IMPLEMENTATION_ALLOCATED`.
