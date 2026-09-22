# TASK-098 — Universal WAV Review Staged BVP Integration

- Status: `A2-R1A_COMPLETE / A2-R1B_COMPLETE / A2-R1C_COMPLETE / A2-R2A_COMPLETE / A2-R2B1_COMPLETE / A2-R2B2_COMPLETE / A2-R2C_COMPLETE / A3-R0_COMPLETE / A3-R1_COMPLETE / A3-R2_COMPLETE / A3-R3_COMPLETE / A4-R0_COMPLETE / A4-R1_DESIGN_COMPLETE / A4-R1A_COMPLETE / A4-R1B_COMPLETE`
- Capability: `BVP-UNIVERSAL-WAV-REVIEW-INTEGRATION-001`
- Governance: `DEV-3 HIGH ASSURANCE`
- Owner authority: `2026-09-19` — proceed autonomously with staged Universal WAV Review integration while adapting cost and Context
- Additional Owner authority: `2026-09-20` — additional fixes approved for the four unresolved A2-R1b High findings
- Base: `origin/main` / `0.24.3` / `28ba61e5f01047a716c681a3584be22500fe53fc`
- Branch: `codex/task-098-a4-review-workspace`
- Completed Atomic Units: `TASK-098/A0 — authority and boundary reconnaissance`; `TASK-098/A1 — contract design and A2-R0 allocation`; `TASK-098/A2-R1 — runtime integration design and exact R1a allocation`; `TASK-098/A2-R1a — fake-only typed capability observation and deterministic resolver`; `TASK-098/A2-R1b Recovery R2 — persistent execution boundary`; `TASK-098/A2-R1c — trusted Python composition and public recovery presentation`; `TASK-098/A2-R2a — pure runtime transcription control contract and reducer`; `TASK-098/A2-R2b1 — durable control coordinator`; `TASK-098/A2-R2b2 — fake-only Provider / engine lifecycle integration`; `TASK-098/A2-R2c — trusted application/Shell projection and Human control`; `TASK-098/A3-R0 — pure local FasterWhisper model-directory inspection contract`; `TASK-098/A3-R1 — contained read-only model-directory inspector`; `TASK-098/A3-R2 — guarded private TASK-036 ASR model setting update and path-free Shell projection`; `TASK-098/A3-R3 — cache reuse/read-back and restart proof without model construction`; `TASK-098/A4-R0 — pure review-completion, timing projection and independent viewport contract`; `TASK-098/A4-R1 — exact-hash coordinator design`; `TASK-098/A4-R1a — pure body-free ephemeral exact-hash coordinator`; `TASK-098/A4-R1b — allowlisted unified Product/Shell projection`
- Completed recovery boundaries: `TASK-098/A2-R1b Recovery R2 — four preserved High findings closed`; `TASK-098/A2-R2c Recovery R1 — final-Judge H2/M1 corrections implemented and independently accepted, final Judge pending`
- Active Atomic Unit: `NONE — A4-R1b completed; A4-R2 playback/waveform runtime requires a fresh authority and architecture review`
- Next action: `design the injected external playback/waveform runtime boundary and native acceptance gate without executing private audio`

## Objective

Absorb the proven Universal WAV Review v1.0.5 capabilities into the unified
`BAI Video Production.exe` Product in bounded Atomic Units. The reference app is
Evidence, not Product authority. Integration must reuse existing BVP providers,
schemas, stores and Shell responsibilities rather than shipping a second app or
parallel canonical model.

## Authority and direct dependencies

| Source | Retained responsibility | TASK-098 rule |
|---|---|---|
| TASK-006 | canonical ASR request, Transcript, SRT publication and Subtitle Workspace foundations | extend through existing interfaces; never create a second Transcript/SRT authority |
| TASK-023 | canonical FasterWhisper provider identity and reconciliation | extend the existing `FasterWhisperProvider`; no duplicate backend |
| TASK-036 | unified Product Shell, local transcription operation and Subtitle Workspace integration | user-facing review belongs in the existing Product entrypoint |
| TASK-041 | canonical audio source/capability/range/review intent/external receipt/Human decision metadata | reuse from A1 forward; do not create a second durable audio-review store |
| TASK-046 | canonical Voice Dataset revision, Training, ModelCandidate and Owner approval | TASK-097 is a subordinate status/execution unit; TASK-098 performs no training or model selection |
| TASK-047 | Voice Capture provenance and candidate receipt ABI; production-recording gates | UWR receipts remain opaque foreign input until an exact TASK-047 ABI lands under fresh DEV-4 authority |
| TASK-048 | canonical voice-quality calibration and Dataset-eligibility decisions | TASK-098 may expose body-free observations only; it creates no quality score or eligibility decision |
| TASK-097 | local TASK-046 P-VS-3B/4A GPT-SoVITS iteration status | status-only dependency; no canonical Dataset/Training/ModelCandidate ownership |

TASK-096 remains an independent release-tooling unit and is not extended by this
Task. A1 promoted TASK-041 to a direct dependency after its existing audition,
waveform capability, sample-range intent and external-receipt boundary proved to
cover the durable review responsibility; A0 history remains unchanged.

## Reference Evidence

- Handoff bundle: `BAI_VIDEO_PRODUCTION_UWR_ASR_HANDOFF_V2_LOCAL_STATE_20260919.zip`
- Bundle SHA-256: `0a8d95fd6df91f50a8e443f2d51332f2a48cca77ec983e8e34e6c538979e3858`
- UWR reference version: `1.0.5`
- Review schema named by the prototype: `bvp.audio-review.v1`
- Foreign receipt name asserted by the prototype: `bvp.task047.local-voice-capture-receipt.v1`

The prototype's commands, paths, ports and architecture are not instructions.
Only bounded capability and test evidence may inform BVP design.

## Canonical integration boundary

| UWR capability | BVP target | Boundary decision |
|---|---|---|
| FasterWhisper ASR | existing TASK-006/023 Provider and Application Service | extend in place; keep TranscriptManifest canonical |
| CPU/CUDA preflight and auto fallback | ASR runtime capability service | `auto` may fall back only on preflight capability-unavailable before model load/inference; explicit `cuda`, post-start failures and partial output fail closed without retry |
| model folder picker and cache | existing Product settings/model-cache route | local path is private operational state, never canonical/public identity |
| Voice Capture receipt import | unsupported foreign input only | do not read, copy, persist, parse or admit its body; exact compatibility is deferred until the canonical ABI/parser lands and passes fresh DEV-4 review |
| waveform/segment review | TASK-041 48 kHz canonical Asset/Candidate plus TASK-036 Subtitle Workspace | non-destructive review session over `BOUND_VERIFIED` canonical media only; no duplicate media bytes or Timeline truth |
| `bvp.audio-review.v1` | foreign format label / optional future bounded importer | never persisted as a BVP store and never final Transcript authority |
| accepted clip export | later Dataset/Training boundary | candidate export only; never automatic Dataset adoption/training |
| HTTP range/port 8766 | existing Product media transport | preserve seek/cancel/error semantics; do not ship a resident standalone server |
| progress/cancel/single-flight | Product operation lifecycle | explicit state, bounded cancellation and truthful recovery; no silent retry; requested/effective device, preflight fallback reason and execution identity remain observable |

## Known gaps from A0

1. Current `main` has a candidate TASK-047 receipt design, but its exact
   schema/parser ABI is unallocated and not landed. The prototype's receipt name
   has no authority to fill that gap. A1 may define only the body-free
   `UNSUPPORTED_FOREIGN_RECEIPT` state and may not read, copy or persist the body;
   exact compatibility is deferred to a fresh
   DEV-4 TASK-047 allocation after its canonical prerequisites are satisfied.
2. `FasterWhisperConfig` already owns model/device/compute/cache/download settings,
   but it has no explicit runtime capability result or policy-aware auto fallback.
3. The provider retains lazy model reuse, but cancellation/progress and runtime
   failure classification are not a complete Product contract.
4. Subtitle Workspace is canonical for text review. Waveform and audio-region
   review are limited to TASK-041 48 kHz `BOUND_VERIFIED` canonical Asset/Candidate
   sources and require an ephemeral additive ViewModel rather than modification
   of Transcript or a second durable review store. Arbitrary or unregistered WAV
   input must first pass the existing ingest/normalization/Asset/Candidate route.
5. Prototype `preserve_receipt_verbatim_in_review_json=true` conflicts with BVP
   public Evidence minimization and cannot be adopted. A foreign receipt remains
   untrusted/opaque; BVP privacy and provenance policy wins.
6. TASK-047 transport/acoustic facts are observations only. SNR, noise, speech
   ratio, calibration and Dataset eligibility remain exclusively TASK-048-owned.
7. `auto` fallback requires a pre-inference capability-unavailable result. It is
   forbidden after model load/inference starts or any partial output exists, and
   the requested/effective mode plus reason must bind operation identity, receipt
   and UI status.

## Atomic Unit plan

### A0 — authority, dependency and boundary reconnaissance

Documentation-only allocation, current-state synchronization, integration map,
Human Gates, Context Scope and durable Evidence. No Product runtime changes.

### A1 — contract design and allocation checkpoint

Design additive runtime-capability/result and review-session/import contracts,
including preflight-only fallback identity, privacy and failure states. It may
define only the body-free `UNSUPPORTED_FOREIGN_RECEIPT` state for foreign UWR
receipts and cannot read, copy or persist their body. Before any
mutation, A1 must publish exact DEV depth, allowed files, acceptance and independent
review. It cannot define or admit a TASK-047-compatible schema/parser, issue a
TASK-048 quality decision or perform real Provider/model/audio execution.

### A2 — FasterWhisper runtime integration

Add CPU/CUDA preflight, policy-aware auto fallback, truthful failure reporting,
single-flight/cancel/progress semantics and fake-runtime tests through the existing
provider. No silent download or duplicate provider.

### A3 — model manager and Product settings

Integrate native model-folder selection, required-file validation, cache reuse and
private path handling with the existing settings route. Downloads remain explicit.

### A4 — review workspace

Add non-destructive waveform/segment review and independent scroll semantics
inside the unified Product, limited initially to TASK-041 48 kHz
`BOUND_VERIFIED` canonical Asset/Candidate sources. Transcript remains canonical,
the ViewModel is ephemeral and media bytes are not duplicated into review state.

### A5 — Voice Capture provenance adapter (dependency blocked)

Remain blocked until an exact canonical TASK-047 receipt ABI/parser lands under
fresh DEV-4 review. A later separately allocated Unit may admit only exact supported
versions, expose body-free observation/integrity facts, and consume TASK-048 quality
Evidence without recreating its decisions. Recording/Dataset/training gates remain
unchanged.

### A6 — packaging and native acceptance

Verify packaged discovery, CPU/CUDA behavior, cancel, cache reuse, review UI and
repair/update behavior. Native effects require exact later authorization and safe
contained output roots.

Each Unit completes `Design -> Implement -> Test -> Evidence/Diff Review ->
Commit-ready` before the next Unit begins.

## Context Scope

### Must read

- `AGENTS.md`
- `docs/ai-team/current-state.md`
- this Task, the accepted A1 contract, and TASK-046/TASK-097 status
- TASK-006, TASK-023, TASK-036 and TASK-041 exact task/contract sections
- the exact TASK-047 candidate-ABI and TASK-048 quality-boundary sections
- `faster_whisper_asr.py`, `faster_whisper_reconciliation.py`,
  `subtitle_workspace.py` and their focused tests
- the three exact UWR handoff/reference contracts used by A0

### Read if required

- TASK-036 Product port/application-service code for A2-A4
- packaging/install contracts for A6

### Do not read by default

- `archive/**`, unrelated completed Task histories, full repository dumps,
  private audio/transcripts, and unrelated BAI Development OS documents

## A0 allowed files

- `docs/ai-team/current-state.md`
- `docs/ai-team/task-index.md`
- `docs/ai-team/tasks/TASK-097/task.md`
- `docs/ai-team/tasks/TASK-098/**`

Later Units must publish their own narrower allowed-file list before mutation.

## Prohibited effects

- no direct push to `main`, force push, tag, GitHub Release, Deploy or Production activation;
- no model/runtime download, paid/cloud Provider call or credential use;
- no real model inference, private audio processing, recording or transcript-body publication;
- no Dataset adoption, GPT-SoVITS/Whisper training, model promotion or final voice-pair selection;
- no Product installation/launch, OBS mutation, Resolve/Timeline write or destructive cleanup;
- no standalone UWR Product, second Transcript/store/provider, invented TASK-047 receipt ABI,
  TASK-048 quality decision, silent fallback/download or public raw path;
- no output at a drive root/direct child and no reuse of foreign/historical artifacts.

## A0 acceptance

- current main, authority, current Task, direct dependencies and overlap are recorded;
- TASK-097 optimization state is synchronized without exposing private bodies;
- integration boundaries and phased Units are explicit;
- independent DEV-3 Critic and Tester report zero unresolved Critical/High findings;
- documentation/static/diff checks pass;
- durable external Evidence is persisted and read back;
- A1 design/allocation is next; no A1 mutation is eligible until its exact DEV depth,
  allowed files, acceptance and required independent review are published and accepted.

## A0 completion

- Independent Critic first pass: `0 Critical / 3 High / 3 Medium / 0 Low`.
- Corrections: TASK-046 ownership restored; foreign receipt quarantined; TASK-047
  compatibility deferred to fresh DEV-4; TASK-048 quality authority restored; A1
  mutation denied; learning-run states separated; fallback limited to preflight.
- Independent Critic final: `0 Critical / 0 High / 0 Medium`.
- Independent Tester: `6 PASS` for Development OS consumer baseline and standalone
  Product contracts; diff, Markdown structure and ASCII filename checks PASS.
- Product/runtime/native/private effects: `NOT_EXECUTED`.
- Evidence: `evidence/a0-authority-boundary-20260919-r01.md`.

## A1 completion

- Design: `a1-contract-allocation-design-20260919.md`, accepted under
  `DEV-3 HIGH ASSURANCE`.
- Independent Critic: first `0/4/1/0`, second `0/1/2/0`, final `0/0/0/0 ACCEPT`.
- Independent Tester: design/diff/scope checks `PASS`; direct-dependency
  regression is `40 PASS`.
- Independent Judge: `ACCEPT`, unresolved `0 Critical / 0 High / 0 Medium / 0 Low`.
- A2-R0 is allocated only for the pure immutable request/decision contract,
  schema mirror, validation, public projection and focused tests. It cannot probe
  a runtime, construct a Provider, run inference, download a model or change UI.
- Product source/schema/runtime/native/private effects: `NOT_EXECUTED`.
- Evidence: `evidence/a1-contract-allocation-20260919-r01.md`.

## A2-R0 completion

- Implemented a pure immutable `FasterWhisperRuntimeRequestV1` and
  request-bound `FasterWhisperRuntimeDecisionV1` contract with exact schema and
  packaged mirror. No existing FasterWhisper config, Provider or TASK-036 state
  machine is connected by this Unit.
- The decision API requires one validated request object; raw request digest and
  device cannot be supplied as competing inputs. The schema and runtime both
  close the outcome/reason/effective device/compute/fallback matrix.
- Domain-separated digest, unknown/tamper rejection, direct-constructor
  validation, TTL `1..300`, `issued <= evaluated < expires`, body-free public
  projection and all-false authority/effect flags are covered.
- Independent Critic: first `0 Critical / 2 High / 1 Medium / 0 Low`; final
  `0 Critical / 0 High / 0 Medium / 0 Low`, `ACCEPT`.
- Independent Tester: `PASS`; focused tests `48 PASS`; direct-dependency suite
  `88 PASS`.
- Independent Judge: `ACCEPT / commit-ready`, unresolved `0/0/0/0`.
- Probe, Provider, inference, download, UI, persistence, native and private-media
  effects: `NOT_EXECUTED`.
- Evidence: `evidence/a2-r0-runtime-contract-20260919-r01.md`.

## A2-R1 design completion

- Accepted design: `a2-r1-runtime-integration-design-20260919.md`.
- Independent Critic: final `0 Critical / 0 High / 0 Medium / 0 Low / ACCEPT`.
- Independent Tester: `PASS`, final unresolved findings `0/0/0/0`.
- Independent Judge: `ACCEPT`; only A2-R1a is implementation-allocated.
- A2-R1a is limited to the typed fake capability observation, deterministic
  request-bound resolver, exact schema/mirror and focused tests. It cannot probe
  a real OS/GPU/DLL, construct a Provider, run inference or mutate TASK-036.
- R1b/R1c/A2-R2 and real/native activation require later fresh reviews and remain
  unallocated.
- Product source/schema/runtime/native/private effects: `NOT_EXECUTED`.
- Evidence: `evidence/a2-r1-design-allocation-20260919-r01.md`.

## A2-R1a completion

- Added the request-bound body-free
  `FasterWhisperRuntimeCapabilityObservationV1` with domain-separated digest,
  exact schema/mirror, closed request-specific matrix and TTL `1..300` seconds.
- Added an injected fake-only capability Protocol/coordinator. It probes only
  `cpu/int8` or `cuda/float16` in the accepted order and uniquely derives the
  existing A2-R0 decision; probe lookup/call errors and non-boolean values fail
  closed without auto fallback.
- Existing A2-R0 request/decision API and serialized behavior remain unchanged.
  No Provider, OS/GPU/DLL adapter, TASK-036, store, launcher or UI was connected.
- Focused R1a+A2-R0 tests: `129 PASS`.
- R1a plus TASK-006/023/036 direct-dependency regression: `168 PASS`.
- Independent Critic: first `0 Critical / 0 High / 1 Medium / 2 Low`, final
  `0 Critical / 0 High / 0 Medium / 0 Low / ACCEPT`.
- Independent Tester: `PASS / 129 PASS / 0/0/0/0`.
- Independent Judge: `ACCEPT / commit-ready / 0/0/0/0`.
- Real/native/private/provider/model/network/download effects: `NOT_EXECUTED`.
- R1b is review-eligible only and remains implementation-unauthorized until its
  fresh DEV-3 pre-mutation review closes exact files and acceptance.
- Evidence: `evidence/a2-r1a-runtime-preflight-20260919-r01.md`.

## A2-R1b pre-mutation review completion

- Accepted review: `a2-r1b-pre-mutation-review-20260919.md`.
- Independent Critic: first `0 Critical / 0 High / 2 Medium / 0 Low`, final
  `0 Critical / 0 High / 0 Medium / 0 Low / ACCEPT`.
- Independent Tester: first `0/0/1/0`, final `0/0/0/0 / PASS`.
- Independent Judge: `ACCEPT / implementation allocated / 0/0/0/0`.
- Allocation is limited to the exact 14-file ceiling and fake/synthetic tests in
  the review. R1c, A2-R2, real/native activation and old-binary writer shutdown
  are not authorized by this checkpoint.
- Technical implementation: `NOT_STARTED / NOT_CONFIRMED`.
- Product source/test/native/provider/model/private/training effects:
  `NOT_EXECUTED`.
- Evidence: `evidence/a2-r1b-pre-mutation-review-20260919-r01.md`.

## A2-R1b implementation recovery checkpoint

- Implementation was attempted only inside the accepted source/test boundary and
  remains uncommitted at HEAD `04c0f1e4eeb2b4267eabe2a0436f01266718dbc5`.
- Independent Tester: `PASS / 238 passed in 35.87s`; four-source `py_compile`
  and `git diff --check` also pass.
- Final independent Critic after the second bounded fix cycle: `REJECT / 0
  Critical / 4 High / 0 Medium / 0 Low`.
- Unresolved High findings: direct recovery repairs a missing permanent lease;
  recovery/publication lifecycle extraction is incomplete; foreign v2 audit can
  accept a consistent `BLOCKED` decision; required negative/golden tests remain
  incomplete.
- This is not an Atomic Unit completion, implementation acceptance, Judge
  acceptance or commit-ready state. DEV-3 review/fix budget is exhausted.
- No real probe, Provider/model execution, download, private media, native
  runtime, Dataset/training, Release, Deploy or Production effect occurred.
- Durable checkpoint: `evidence/a2-r1b-runtime-managed-transcription-20260919-r01.md`.

## A2-R1b Recovery R2 authorization

- Owner authorization date: `2026-09-20`.
- Responsibility remains A2-R1b. This is corrective completion of the accepted
  TASK-036 runtime-managed transcription boundary, not TASK-098/A2-R2 and not a
  new Product capability or canonical owner.
- Exact goals: require an existing immutable v2 lease before v2
  recovery/finalize while preserving the closed legacy v1 lease policy;
  centralize v1/v2 recovery, immutable publication access and final binding in
  the engine; reject foreign runtime decisions other than `READY_CPU` or
  `READY_CUDA`; add the four missing negative/golden test families.
- Existing 14-file ceiling remains the maximum. New code changes should be
  limited to `task036_product_ports.py` and the two TASK-036/TASK-098 operation
  test files unless independent review proves another existing allowed file is
  required.
- Recovery R2 receives a fresh maximum of two bounded review/fix cycles.
- R1c, A2-R2, real/native probe, model execution/download, private audio,
  training, Release, Deploy and Production Activation remain unauthorized.
- Design review: independent Critic `ACCEPT / 0/0/0/0`; independent Tester
  `PASS / 0/0/0/0` after two Medium clarifications were closed; independent
  Judge `ACCEPT / implementation allocated / 0/0/0/0`.
- Implementation completion:
  - exact seven-file direct regression: `269 PASS in 60.32s`;
  - final independent Critic: `ACCEPT / 0/0/0/0`;
  - independent Tester: `PASS`;
  - final independent Judge: `ACCEPT / COMMIT_READY / 0/0/0/0`;
  - `git diff --check`: `PASS`;
  - external Evidence read-back: `PASS`, SHA-256
    `f41e89fae8bf8b04d2acb75bd675fa6e95b47017fe8a139ab816f2d68a56366b`.
- A2-R1b status: `COMPLETE`; no native/model/private/training effect occurred.

## A2-R1c pre-mutation review

- Review document: `a2-r1c-pre-mutation-review-20260920.md`.
- Design review: independent Critic `ACCEPT / 0/0/0/0`; independent Tester
  `PASS / 0/0/0/0`; independent Judge `ACCEPT / implementation allocated /
  0/0/0/0`.
- Implementation status: `COMPLETE / COMMIT_READY`.
- Focused regression: `174 PASS / 0 FAIL`; `py_compile` and `git diff --check`
  are `PASS`. Ordinary Windows/WSL pytest remains `NOT_CONFIRMED` because the
  existing environments lack `jsonschema` or Argon2id respectively; no package
  installation occurred.
- Review closure: cycle 1 Critic `REJECT / 0/2/0/0`; cycle 2 Critic
  `ACCEPT / 0/0/0/0`; final independent Tester `PASS / 0/0/0/0`.
- Final independent Judge: `ACCEPT / COMMIT_READY / 0/0/0/0`.
- Evidence: `evidence/a2-r1c-trusted-composition-20260920-r01.md`; external
  checkpoint path, SHA-256 and successful read-back are recorded there.
- Existing launch-config versions, first-run bootstrap, CLI and native entrypoints
  remain v1-only. No serialized v2 version or production adapter is allocated.
- Proposed R1c effects are fake/synthetic only and do not authorize real probe,
  model construction/inference/download, private audio, installation, Release,
  Deploy or Production Activation.

## A2-R2a completion

- Added six immutable durable control record types, a concrete immutable lease
  fact, immutable reducer facts, an exact schema/package mirror and a pure
  twelve-key phase-only public reducer.
- The reducer validates exact source-bound admission, operation status/attempt/
  ref, lease, slot, record family and predecessor digests before selecting a
  priority row. Foreign/corrupt/impossible facts fail closed without action,
  replay or release.
- Only an exact terminal closure commit plus exact barrier and generation-
  absence proof exposes `slot_release_allowed`. Only confirmed pre-Provider or
  cooperative cancellation reports technical Provider stop; Human attestation
  remains explicitly non-technical.
- Builder focused verification: `40 PASS / 0 FAIL`.
- Direct R1a/R1b/R1c dependency regression: `454 PASS / 0 FAIL`.
- Independent Tester: static/schema/fix review `0/0/0/0`; its agent-local pytest
  route was `NOT_CONFIRMED`. Independent Judge separately executed stub-free
  focused pytest with `40 PASS / 0 FAIL`.
- Final independent Critic: `ACCEPT / 0/0/0/0` after two bounded fix cycles.
- Final independent Judge: `ACCEPT / COMMIT_READY / 0/0/0/0`.
- External checkpoint read-back: `PASS`, SHA-256
  `b9966804d2df0f74c6e8fb74960b3fd4fb6d0b62924114ab9d9d476f210fd34d`.
- Evidence: `evidence/a2-r2a-runtime-control-20260920-r01.md`.
- R2b is review-eligible only. R2b/R2c implementation, store, Provider, engine,
  Shell, serialized v2/native, private media, model/training and release effects
  remain unallocated or gated.

## A2-R2b1 pre-mutation review

- Accepted review: `a2-r2b1-durable-coordinator-pre-mutation-review-20260920.md`.
- Responsibility: durable control-row CAS ordering, hash-addressed immutable
  control Evidence, atomic expected-attempt protection, generation-exclusion
  lock and crash-resumable terminal closure; no Provider/engine lifecycle or UI.
- Independent Critic: initial `0/3/2/0`; final `ACCEPT / 0/0/0/0`.
- Independent Tester: initial `0/2/1/0`; final `PASS / 0/0/0/0`.
- Independent Judge: `ACCEPT / R2b1 LIMITED IMPLEMENTATION ALLOCATED / 0/0/0/0`.
- Exact allocation: new coordinator and tests; optional default-off
  `expected_attempt` store CAS predicate and ABA tests; canonical v2 operation-
  key helper call and golden test; bounded TASK-098/current-state/task-index docs.
- R2b2 Provider/engine lifecycle integration, R2c Shell/Human application,
  FasterWhisper changes, native/private/model/training/release effects remain
  unallocated or gated.

## A2-R2b1 implementation and Recovery verification

- Exact implementation allocation: one durable coordinator, optional default-off
  ordinary-CAS `expected_attempt`, canonical TASK-036 v2 key-helper reuse and
  their three bounded test files; no Provider/engine/Shell/native effect.
- Final control-row refs are exact typed durable refs for cancel request, cancel
  outcome, commit barrier and terminal commit. Immutable Evidence remains
  canonical `sha256:` digest-addressed JSON.
- Immediately after the two generation-absence observations and their fault
  boundary, control is re-read as exact `PARTIAL / typed barrier / attempt 0`
  before any main terminal CAS. Post-main, pre-control and pre-slot checks remain.
- Recovery focused verification: `42 PASS` at
  `/tmp/bvp-task098-a2-r2b1-recovery-20260920T180000-r16`.
- Direct TASK-006/023/036/098 regression: `354 PASS` at
  `/tmp/bvp-task098-a2-r2b1-regression-20260920T181000-r17`.
- Final independent Critic: `ACCEPT / 0/0/0/0`.
- Final independent Tester after exact typed-barrier drift coverage:
  `PASS / 0/0/0/0`.
- Final independent Judge: `ACCEPT / COMMIT_READY / 0/0/0/0` after fresh
  external checkpoint read-back `PASS`.
- External checkpoint: `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2b1-durable-coordinator\20260920T184000+0900\checkpoint.md`, SHA-256
  `82484a0f1a9cb71ee5065ec9072f342f0a5d1063079f1a70a17e26c72365c2df`.
- Canonical tracked Evidence:
  `evidence/a2-r2b1-durable-coordinator-20260920-r01.md`.
- At R2b1 closure, R2b2 Provider/engine lifecycle and R2c Shell/Human work were
  still unallocated; the fresh R2b2 review outcome is recorded below.

## A2-R2b2 pre-mutation review

- Accepted review:
  `a2-r2b2-provider-engine-lifecycle-pre-mutation-review-20260920.md`.
- Responsibility: v2-only phase/cancel checkpoints, separate cooperative lazy-
  iterator path, exact iterator-close outcome, first-write publication barrier,
  main-before-control publication completion and Provider-zero reconciliation.
- Independent Critic: initial `0/4/1/0`; final `ACCEPT / 0/0/0/0`.
- Independent Tester: initial `0/3/1/0`; final `PASS / 0/0/0/0`.
- Independent Judge: `ACCEPT / R2b2 LIMITED IMPLEMENTATION ALLOCATED / 0/0/0/0`.
- Exact allocation: three source and four test files in the accepted review plus
  bounded TASK-098/current-state/task-index documentation.
- R2c, store/schema, Shell/launcher/CLI, serialized v2/native activation, real
  Provider/model/private media, voice learning and release effects remain
  unallocated or gated.

## A2-R2b2 implementation and verification

- Implementation stays within the accepted ceiling: three allocated source
  files and three allocated test files changed; the fourth allowed legacy v1
  regression file remains unchanged.
- Legacy `transcribe(request)` remains exact. V2 alone uses cooperative lazy-
  iterator checks, exact single `close()` confirmation, and closed cancellation
  outcomes without adding a callback to the generic Provider Protocol.
- Publication now binds main digest before exact control completion, revalidates
  lease/main attempt/slot/control at observable boundaries, and requires exact
  publication control in both recoverable and verification-only Provider-zero
  recovery. Missing or foreign completed control fails closed and retains the
  slot.
- Final direct spawn-mode TASK-006/023/036/098 regression: `488 PASS / 0 FAIL`
  at `/tmp/bvp-task098-r2b2-spawn-regression-20260920T235000-r11`.
- Judge-specific completed-control and verification-only negative matrix:
  `3 PASS / 0 FAIL` at
  `/tmp/bvp-task098-r2b2-judge-high-fixes-20260920T234000-r10`.
- `py_compile` and `git diff --check`: `PASS`.
- Final independent Critic: `ACCEPT / 0/0/0/0`.
- Final independent Tester: `PASS / 0/0/0/0`; independent pytest remained
  `NOT_CONFIRMED` only because of its known WSL2 `E_ACCESSDENIED` route, without
  conflict with the main isolated spawn result.
- Final independent Judge: `ACCEPT / COMMIT_READY / 0/0/0/0` after external
  checkpoint hash/read-back and all eleven path hashes were verified.
- Accepted external checkpoint:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2b2-provider-engine-lifecycle\20260920T235500+0900\checkpoint.md`, SHA-256
  `1e8432890ffa6e697e960ee137cce4f0fa39d8dd8774328e213b13d74b2d96d0`.
- Canonical tracked Evidence:
  `evidence/a2-r2b2-provider-engine-lifecycle-20260920-r01.md`.
- R2c Shell/Human application, store/schema, launcher/CLI, serialized v2/native,
  real Provider/model/private media, voice learning, installation and release
  remain unallocated or gated.

## A2-R2c pre-mutation review

- Accepted review:
  `a2-r2c-shell-human-pre-mutation-review-20260920.md`.
- Proposed responsibility: exact read-only R2a projection, process-local phase,
  bounded server-held Human confirmation and fake-only Shell control routing.
- Proposed ceiling: four source and five focused test files plus bounded docs.
- Independent Critic: initial `0/3/1/0`; final `ACCEPT / 0/0/0/0`.
- Independent Tester: initial `0/2/2/0`; final `PASS / 0/0/0/0`.
- Independent Judge: `ACCEPT / IMPLEMENTATION_ALLOCATED / 0/0/0/0`.
- Exact implementation allocation: four source and five test files in the
  accepted review plus bounded docs.
- Canonical design Evidence:
  `evidence/a2-r2c-design-allocation-20260920-r01.md`.
- Store/schema/reducer, launcher/first-run/CLI, serialized/native v2, real
  Provider/model/private media, voice learning and release effects remain
  read-only, unallocated or gated.

## A2-R2c implementation checkpoint

- Pre-commit HEAD: `4b0ddc3ba9ebf3509ab97fd63412c35f799f4f38`;
  base/current local main: `28ba61e5f01047a716c681a3584be22500fe53fc`.
- Implemented only the allocated four source and four changed test paths; the
  fifth allowed launcher regression file remained unchanged.
- Added read-only control-chain capture without row/Evidence creation or
  repair; exact main/lease/slot/publication/terminal-chain validation; and
  conservative orphan/corrupt-state blocking.
- Added exact process-local forward-only phase and active-worker coordinates,
  closed twelve-key R2a projection composition, private frozen snapshots and
  exact revalidation before cancel/Human mutation.
- Added bounded 300-second server-local single-use confirmations, separate
  prepare/apply/cancel Bridge endpoints and v2 START-only in-flight Shell
  cancellation presentation. JavaScript receives only public projection and
  opaque confirmation identity.
- Direct six-file R2a/R2b1/R2b2/R2c/R1c/TASK-036 regression:
  `413 PASS / 0 FAIL` in `108.79s`; Python compile and Git diff check: `PASS`.
- Final independent Critic: `ACCEPT / 0/0/0/0` after two bounded fix cycles.
- Final independent Tester: `PASS / 0/0/0/0`; independent dynamic pytest is
  `NOT_CONFIRMED` because of intermittent WSL service access, while the main
  isolated WSL route and spawn-specific test passed.
- Real Provider/model, private media/audio, native/packaged Shell, recording,
  Dataset adoption, voice training, installation, Release, Deploy and
  Production Activation were not executed.
- Final Judge and commit remain pending. Serialized
  v2/native activation is not allocated; the next safe action after commit is
  a fresh bounded design/authority review for the next staged integration unit.
- External pre-commit checkpoint:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2c-shell-human-control\20260920T082311+0900\checkpoint.md`, SHA-256
  `39d48dc57a601df2a27036ef2168bcf1d84135b2d74129497223fd9519fd36b4`,
  read-back `PASS`.

## A2-R2c Recovery R1 checkpoint

- The first final Judge rejected the pre-recovery checkpoint with
  `0 Critical / 2 High / 1 Medium / 0 Low`; no rejected-state commit occurred.
- Recovery design `a2-r2c-recovery-r1-review-20260920.md` received independent
  Critic `ACCEPT / 0/0/0/0`, Tester `PASS / 0/0/0/0`, and Judge
  `ACCEPT / IMPLEMENTATION_ALLOCATED / 0/0/0/0`.
- The legacy `RuntimeTranscriptionCoordinatesV1` again requires its complete
  validated request/decision pair. Detached R2c application uses a distinct
  frozen durable-control coordinate and exactly two dedicated coordinator
  entrypoints; Provider/worker paths exact-reject that type.
- A validated `terminal-commit.json` discovered while control remains
  `PARTIAL` stays in the private chain identity but is withheld from the reducer.
  The actual `after_terminal_commit_write` fault test proves main `FAILED`,
  control `PARTIAL`, slot `IN_PROGRESS`, public `BLOCKED`, and release false;
  resume commits control before exact slot release.
- Shell JavaScript now validates the exact three-key apply response and the
  Python-derived closed twelve-key R2a row set. A fake Node harness proves valid
  notify/refresh `1/1` and malformed/throw notify/refresh `0/1` for null, array,
  top/nested missing or extra/private keys, wrong type and invalid row.
- Direct recovery tests: `3 PASS`, Medium corrections: `2 PASS`, focused
  three-file regression: `220 PASS`, final six-file regression:
  `416 PASS / 0 FAIL` in `110.24s`; Python compile and Git diff check: `PASS`.
- Recovery implementation Critic cycle 1: initial `0/0/1/0`, final
  `ACCEPT / 0/0/0/0`. Independent Tester cycle 1: initial `FAIL / 0/0/1/0`,
  final `PASS / 0/0/0/0`; its Windows pytest route is `NOT_CONFIRMED` only
  because that interpreter lacks `jsonschema`, while the Builder's WSL2 route
  executed the Node harness and all six files.
- Real Provider/model, private media/audio, native/packaged Shell, recording,
  Dataset adoption, voice training, installation, Release, Deploy and
  Production Activation were not executed. Unique Recovery checkpoint:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2c-shell-human-control\20260920T085346+0900\checkpoint.md`, SHA-256
  `cee6507b2fa9338c8daad5c916cc80d37c80262ba489dca1222a061fa89713c2`,
  size `6474`, read-back `PASS`. Final Judge:
  `ACCEPT / COMMIT_READY / 0/0/0/0`. Implementation commit:
  `92bd4592a6754bf65fe252c9258a930f3cbb7852`. External post-commit receipt:
  `C:\home\baisound\evidence\bai-video-production\TASK-098\a2-r2c-shell-human-control\20260920T085346+0900\post-commit-receipt.md`, SHA-256
  `055f17c33403f57408e02b7c5f7d2b0df0ab178c0f15b6e2eaf5612c30b38ea3`,
  size `2003`, read-back `PASS`.

## A3-R0 model-directory contract completion

- Design/review:
  `a3-r0-model-directory-contract-pre-mutation-review-20260922.md`.
- Added a pure, body-free model file observation and model-directory inspection
  contract plus exact canonical/package schema mirrors. No filesystem, model,
  network, download, Provider or inference behavior is present.
- READY requires `config.json`, `model.bin`, `tokenizer.json` and exactly one of
  `vocabulary.txt` / `vocabulary.json`; `preprocessor_config.json` is optional.
  Per-file sizes, checksums, manifest/record digests and closed state/reason
  matrices fail closed.
- The public projection omits private locator/file/manifest/record digests and
  every file observation while fixing download, model-load, inference, network
  and execution flags to false.
- Critic corrections closed schema-only semantic gaps for file-specific size
  bounds, complete READY files and public READY/BLOCKED cross-products. Final
  finding count: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Focused A3-R0 plus direct A2 runtime-contract regression:
  `87 PASS / 0 FAIL`; Python compile, JSON parse, schema mirror and Git diff
  checks: `PASS`.
- Real directory inspection, launch-config/settings mutation, native picker,
  model load/inference/download and private audio processing were not executed.
- Evidence:
  `evidence/a3-r0-model-directory-contract-20260922-r01.md`.
- Next Unit: fresh A3-R1 review for the contained read-only filesystem inspector.

## A3-R1 read-only model-directory inspector completion

- Design/review:
  `a3-r1-model-directory-inspector-pre-mutation-review-20260922.md`.
- Added a contained inspector that accepts one explicit absolute local path,
  rejects symlink/reparse ancestry, scans at most 64 top-level entries and reads
  only the six A3-R0 allowlisted filenames.
- Each admitted file must remain a single-link regular file across pre-open,
  opened-handle, post-read-handle and post-read path identity checks. SHA-256 is
  streamed in bounded chunks; present JSON files must be valid UTF-8 JSON.
- BLOCKED output contains only closed reason codes and no partial observation,
  host path, exception text or file body. READY binds only a private digest of
  the canonical locator; the A3-R0 public projection remains path/digest-free.
- The Product dependency is a `>=1.2.1,<2` range, so this Unit does not claim
  installed-runtime or model execution compatibility.
- Initial test cycle: `102 PASS / 1 FAIL`; the sole failure found non-regular
  entries classified by link count before file type. Classification order was
  corrected to alias, regular-file type, then hardlink count.
- Final A3-R1, A3-R0 and direct A2 contract regression:
  `106 PASS / 0 FAIL`; Python compile and Git diff check: `PASS`.
- Final Critic findings: `Critical 0 / High 0 / Medium 0 / Low 0`; Tester:
  `PASS`; Judge: `ACCEPT / COMMIT_READY`.
- Settings, native picker, model construction/inference, download/network,
  private audio, recording, Dataset adoption, training, installation, Release,
  Deploy and Production Activation were not executed.
- Evidence:
  `evidence/a3-r1-model-directory-inspector-20260922-r01.md`.
- Next Unit: fresh A3-R2 review for expected-digest guarded settings update.

## A3-R2 guarded private model-settings completion

- Design/review:
  `a3-r2-guarded-model-settings-pre-mutation-review-20260922.md`.
- Added a prepare/apply coordinator over the existing private TASK-036 launch
  config. Prepare is read-only, requires an exact config digest before invoking
  the injected picker, validates Project containment and stores a selected model
  path only in an expiring process-local one-use confirmation.
- Apply consumes the confirmation, revalidates config and the exact A3-R1 model
  record, preserves cache and `allow_model_download=false`, proves a semantic
  one-field diff, and uses atomic write plus replacement-time CAS/read-back.
- TASK-036 gained an internal model-folder dialog purpose and fixed Windows
  folder-dialog method. No real native dialog was opened. Shell exposes only
  closed path-free prepare/apply projections when the service is injected;
  existing Product composition does not auto-activate it.
- Initial direct pytest collection was `NOT_CONFIRMED` because the WSL
  `cryptography` build lacks unused Argon2id. No dependency changed; a
  process-local unused import stub enabled the existing Shell test route.
- Focused A3 settings/picker/contracts: `131 PASS`; TASK-036 Shell and trusted
  launcher regression: `113 PASS`; final combined regression:
  `245 PASS / 0 FAIL` in `30.30s`. Python compile and Git diff check: `PASS`.
- Design Critic findings `0/4/1/0` plus implementation Critic findings
  `0/2/0/0` were corrected; final findings:
  `Critical 0 / High 0 / Medium 0 / Low 0`. Tester: `PASS`; Judge:
  `ACCEPT / COMMIT_READY`.
- Only pytest-owned temporary configs/models were written/read. Real Product
  settings, native picker, model load/inference, Provider, download/network,
  private audio, recording, Dataset/training, installation, Release, Deploy and
  Production Activation were not executed.
- Remote branch push is parked because destination ownership was not approved
  by the external safety reviewer; local commits and durable Evidence remain.
- Evidence:
  `evidence/a3-r2-guarded-model-settings-20260922-r01.md`.
- Next Unit: fresh A3-R3 review for cache reuse/read-back and restart tests.

## A3-R3 cache/restart read-back completion

- Design/review:
  `a3-r3-cache-restart-readback-pre-mutation-review-20260922.md`.
- Added a read-only snapshot over the existing TASK-036 launch configuration.
  It requires the exact current config digest, validates the existing cache
  directory and re-runs the A3-R1 local-model inspection without constructing
  a FasterWhisper model.
- A newly constructed service reads back an A3-R2 selection by the same
  path-free model ID. A symbolic model returns
  `LOCAL_MODEL_NOT_CONFIGURED`; stale config identity, unsafe cache ancestry
  and missing/invalid model contents fail closed.
- The projection distinguishes safe cache configuration from actual execution:
  `cache_reuse_available` may be true, while `cache_hit_observed`,
  `model_manifest_continuity_confirmed` and
  `runtime_compatibility_confirmed` remain false. A3-R3 therefore makes no
  cache-hit, persisted-manifest-continuity or runtime/model-compatibility claim.
- A3-R2 confirmation state remains process-local and cannot be applied through
  a reconstructed service. Shell request shape is exact and all public output
  remains path-free.
- Direct pytest collection was `NOT_CONFIRMED` because the WSL cryptography
  build lacks unused Argon2id. No dependency changed; a process-local unused
  import stub enabled the existing Shell graph.
- Final A3-R3 through A3-R0, settings, Shell, trusted-launch and direct A2
  regression: `234 PASS / 0 FAIL` in `41.43s`. Python compile and Git diff
  check: `PASS`.
- Critic design findings `0/2/2/0` were corrected; final findings:
  `Critical 0 / High 0 / Medium 0 / Low 0`. Tester: `PASS`; Judge:
  `ACCEPT / COMMIT_READY`.
- Only pytest-owned temporary configs/models/cache directories were touched.
  Real Product settings, native picker, model load/inference, Provider,
  download/network, private audio, recording, Dataset/training, installation,
  Release, Deploy and Production Activation were not executed.
- Remote branch push remains parked because destination ownership was not
  approved by the external safety reviewer; no retry or workaround occurred.
- Evidence:
  `evidence/a3-r3-cache-restart-readback-20260922-r01.md`.
- Next Unit: fresh A4 design/authority review for the review workspace.

## A4-R0 review-completion / viewport contract completion

- Design/review:
  `a4-r0-review-completion-viewport-contract-pre-mutation-review-20260922.md`.
- Added a separate A4 completion classifier over the existing TASK-041
  inclusion proof. `COMPLETE` requires exact inclusion, `BOUND_VERIFIED`,
  `COMPLETED`, canonical persistence and the exact requested audition/waveform
  result flags; every missing, false, unknown, failed, cancelled or mismatched
  condition remains `INCOMPLETE` with closed reason codes.
- Added exact integer half-open projection from Transcript microseconds and
  Subtitle Workspace milliseconds to 48 kHz samples. Start is floored, exclusive
  end is ceiled, and there is no reverse/write-back path.
- Added an immutable serialization-free viewport with independent waveform
  horizontal and segment-list vertical scroll axes. Each reducer preserves the
  other axis and clamps only to its own bounds.
- Implementation Critic found directly constructible result/range values could
  forge completion/effect or timing claims. Constructor-level closed reason,
  digest, fixed-false effect and exact projection invariants corrected the High
  finding. Final findings: `Critical 0 / High 0 / Medium 0 / Low 0`.
- Direct A4-R0/TASK-041/TASK-006 regression: `57 PASS / 0 FAIL` in `3.04s`.
  Final TASK-098 plus TASK-041/TASK-006 targeted regression:
  `462 PASS / 0 FAIL` in `151.62s`. Python compile and Git diff check: `PASS`.
- Windows fixed-Python collection was `NOT_CONFIRMED` because that interpreter
  lacks `jsonschema`. No dependency changed; WSL used the same process-local
  unused Argon2id import stub as A3. Its two pytest-cache permission warnings
  did not affect collection, execution or results and created no cache output.
- No media/text/path body, persistence, audio read/playback, waveform render,
  Subtitle Workspace mutation, Human decision authorization, Product UI,
  Provider/native/private effect, installation, Release, Deploy or Production
  Activation occurred.
- Evidence:
  `evidence/a4-r0-review-completion-viewport-20260922-r01.md`.
- Next Unit: fresh A4-R1 review for the ephemeral exact-hash coordinator; A4-R0
  completion does not allocate its implementation.
