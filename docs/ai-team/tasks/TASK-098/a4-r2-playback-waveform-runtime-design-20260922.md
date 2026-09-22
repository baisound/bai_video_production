# TASK-098 A4-R2 Playback/Waveform Runtime Boundary Design

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A4-R2 DESIGN`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `5fcc9e0ff56deea25f45f332a38c88ce58557569`
- Base/current-main identity: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Branch: `codex/task-098-a4-review-workspace`
- Result: `DESIGN_ACCEPTED / A4-R2A_FAKE_ONLY_CONTRACT_ALLOCATED / A4-R2B_HUMAN_GATED`

## Authority and capability routing

Owner autonomy authorizes this architecture review and a pure, injected,
fake-only A4-R2a contract. It does not authorize reading private audio, starting
OS playback, generating a real waveform, launching a native Product, or writing
a TASK-041 receipt. Those effects are parked at A4-R2b until a specific native
acceptance authority and bounded test asset are established.

- High-Reasoning: Asset/locator/security ownership, execution/observation split,
  completion non-claim, Critic and final integration review.
- Implementation: pure typed request/result/reducer and disabled-by-default
  injected Port composition.
- Bulk/Mechanical: fake fixtures, negative tests, documentation and Evidence.

## Existing boundary evidence

- No current general BVP playback/waveform engine owns this review use case.
  DbD Training playback is a separate Product surface and must not be reused as
  review authority merely because it can play media.
- TASK-041 owns source/capability/intent/external-receipt and Human review facts,
  but deliberately performs no audio read or waveform/playback effect.
- The canonical Asset Registry and `LogicalPathResolver` can resolve an Asset's
  logical URI inside an allowlisted Product root. A later concrete runtime must
  obtain the Asset by exact Asset ID, verify checksum/rights/identity, then
  resolve internally. No caller or Shell may supply a host path.
- A4-R1a/R1b own only ephemeral exact joins and body-free projection.

## Unit split

### A4-R2a — pure injected runtime contract and fake-only coordinator

A4-R2a may define:

- an immutable request built internally from exact TASK-041 source/capability/
  intent plus A4-R1a identity and the requested half-open sample range;
- a runtime Port protocol with no concrete filesystem/audio implementation;
- closed capability/operation/result states and bounded fake waveform metadata;
- a reducer that distinguishes `NOT_BOUND`, `READY`, `RUNNING`, `SUCCEEDED`,
  `FAILED_KNOWN`, `CANCELLED_SAFE` and `UNKNOWN_AFTER_DISCONNECT`;
- effect truth supplied only by the injected fake observation, never inferred
  from a request or capability record; and
- a body-free Shell-safe status projection which still exposes no amplitude
  samples, paths, digests or private identifiers.

A4-R2a tests use deterministic fakes only. The default composition has no Port
and remains `NOT_BOUND`. It may not open files, decode media, allocate audio
devices, create waveform arrays, call TASK-041 stores or add Shell actions.

### A4-R2b — concrete runtime and native acceptance (parked Human Gate)

A4-R2b requires a fresh implementation review plus explicit Human authority for
one bounded real private-audio/native acceptance run. Its concrete Port must:

1. load the Asset by the exact Product Asset ID from the canonical registry;
2. require checksum and rights agreement with the exact TASK-041 source;
3. resolve its logical URI internally with `LogicalPathResolver` and recheck
   canonical containment, symlink/regular-file identity and operation scope;
4. decode only the exact requested 48 kHz half-open range;
5. cap waveform points/bytes and keep derived amplitude data process-local;
6. own stop/cancel/device cleanup and report disconnect as unknown, not success;
7. avoid logs/Evidence containing path, audio samples or waveform bodies; and
8. return an observation only. TASK-041 separately owns any external review
   receipt and A4-R0 separately classifies completion after canonical persistence.

No playback or waveform result may mutate Asset, Candidate, Timeline, Subtitle
Workspace, placement or Human decision state.

## A4-R2a Allowed Files

- `src/ai_video_production/task098_review_media_runtime_contract.py`
- `tests/test_task098_review_media_runtime_contract.py`
- bounded TASK-098 task/design/Evidence/current-state/task-index documentation

TASK-041/TASK-006 stores/contracts, Asset Registry/path resolver, Shell/UI,
concrete audio/media libraries, dependencies, private media, package/installer
and Product version must not change in A4-R2a.

## A4-R2a acceptance

- request construction proves exact TASK-041 source/capability/intent and A4-R1a
  source/range identity without accepting a path;
- direct constructors reject identity/range/state/effect forgery;
- no Port produces `NOT_BOUND`; fake observations alone drive closed states;
- success requires exact request identity plus explicit playback/waveform
  observation flags for the operations requested;
- failure/cancel/disconnect cannot be completion and returns no partial waveform;
- status projection contains no path/digest/private ID/text/audio/waveform body;
- no TASK-041 receipt, completion, persistence or Human decision is created;
- focused and relevant A4/TASK-041 regression and durable Evidence pass.

## Critic / Tester / Judge

- Critical: treating playback/waveform observation as a TASK-041 persisted
  receipt would collapse execution and canonical Evidence. Corrected by making
  A4-R2 observations non-canonical and keeping receipt/completion separate.
- High: accepting a path from Shell/caller would bypass Asset Registry and
  logical-root containment. Corrected by forbidding paths and reserving internal
  exact Asset resolution for A4-R2b.
- High: reusing DbD Training playback would cross Product responsibility and
  bring unrelated persistence/diagnostics behavior. Corrected by a dedicated
  injected Port protocol with no concrete implementation in A4-R2a.
- High: capability support could be mistaken for executed playback/waveform.
  Corrected with explicit observation flags and closed lifecycle state.
- High: disconnect could be reported as stopped/completed. Corrected with
  `UNKNOWN_AFTER_DISCONNECT` and no completion claim.
- Medium: waveform arrays could leak private audio-derived body. Corrected by
  forbidding real arrays in A4-R2a and capping/process-localizing them in R2b.
- Medium: default Product composition might activate effects accidentally.
  Corrected with no-Port `NOT_BOUND` and no Shell action in A4-R2a.
- Final findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Tester: `PASS / A4-R2A_TEST_PLAN_ACCEPTED`.
- Judge: `ACCEPT A4-R2A / PARK A4-R2B AT HUMAN GATE`.
