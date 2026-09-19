# TASK-098 — Universal WAV Review Staged BVP Integration

- Status: `A0_COMPLETE / CRITIC_TESTER_PASS / A1_DESIGN_ALLOCATION_NEXT`
- Capability: `BVP-UNIVERSAL-WAV-REVIEW-INTEGRATION-001`
- Governance: `DEV-3 HIGH ASSURANCE`
- Owner authority: `2026-09-19` — proceed autonomously with staged Universal WAV Review integration while adapting cost and Context
- Base: `origin/main` / `0.24.3` / `28ba61e5f01047a716c681a3584be22500fe53fc`
- Branch: `codex/task-098-universal-wav-review-integration`
- Completed Atomic Unit: `TASK-098/A0 — authority, direct dependencies, canonical boundaries and staged integration map`
- Next Atomic Unit: `TASK-098/A1 — contract design and allocation checkpoint; mutation not yet authorized`

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
| TASK-046 | canonical Voice Dataset revision, Training, ModelCandidate and Owner approval | TASK-097 is a subordinate status/execution unit; TASK-098 performs no training or model selection |
| TASK-047 | Voice Capture provenance and candidate receipt ABI; production-recording gates | UWR receipts remain opaque foreign input until an exact TASK-047 ABI lands under fresh DEV-4 authority |
| TASK-048 | canonical voice-quality calibration and Dataset-eligibility decisions | TASK-098 may expose body-free observations only; it creates no quality score or eligibility decision |
| TASK-097 | local TASK-046 P-VS-3B/4A GPT-SoVITS iteration status | status-only dependency; no canonical Dataset/Training/ModelCandidate ownership |

TASK-096 remains an independent release-tooling unit and is not extended by this
Task. TASK-041 Audio Workspace may be read later if the review UI needs its
audition contract, but it is not an A0/A1 direct dependency.

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
| Voice Capture receipt import | opaque foreign-input quarantine boundary | do not parse or admit it as TASK-047; exact compatibility is deferred until the canonical ABI/parser lands and passes fresh DEV-4 review |
| waveform/segment review | TASK-036 Subtitle/Audio Review workspace | non-destructive review session; no duplicate media bytes or Timeline truth |
| `bvp.audio-review.v1` | versioned review-session/import adapter | never final Transcript authority |
| accepted clip export | later Dataset/Training boundary | candidate export only; never automatic Dataset adoption/training |
| HTTP range/port 8766 | existing Product media transport | preserve seek/cancel/error semantics; do not ship a resident standalone server |
| progress/cancel/single-flight | Product operation lifecycle | explicit state, bounded cancellation and truthful recovery; no silent retry; requested/effective device, preflight fallback reason and execution identity remain observable |

## Known gaps from A0

1. Current `main` has a candidate TASK-047 receipt design, but its exact
   schema/parser ABI is unallocated and not landed. The prototype's receipt name
   has no authority to fill that gap. A1 may define only an opaque unsupported/
   quarantined foreign-input state; exact compatibility is deferred to a fresh
   DEV-4 TASK-047 allocation after its canonical prerequisites are satisfied.
2. `FasterWhisperConfig` already owns model/device/compute/cache/download settings,
   but it has no explicit runtime capability result or policy-aware auto fallback.
3. The provider retains lazy model reuse, but cancellation/progress and runtime
   failure classification are not a complete Product contract.
4. Subtitle Workspace is canonical for text review; waveform and audio-region
   review require an additive session model rather than modification of Transcript.
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
define only an unsupported/quarantined state for foreign UWR receipts. Before any
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

Add non-destructive whole-media waveform/segment review and independent scroll
semantics inside the unified Product. Transcript remains canonical and media bytes
are not duplicated into review state.

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

## A0 Context Scope

### Must read

- `AGENTS.md`
- `docs/ai-team/current-state.md`
- this Task, TASK-046 and TASK-097 status
- TASK-006, TASK-023 and TASK-036 task/contract summaries
- the exact TASK-047 candidate-ABI and TASK-048 quality-boundary sections
- `faster_whisper_asr.py`, `faster_whisper_reconciliation.py`,
  `subtitle_workspace.py` and their focused tests
- the three exact UWR handoff/reference contracts used by A0

### Read if required

- TASK-041 audio audition contract for A4
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
