# TASK-073 P0-V Owner Voice Local WAV — Complete Design Packet

## 1. Design identity

- Task: `TASK-073`
- Atomic responsibility: `OWNER_VOICE_LOCAL_WAV_PRODUCT_VERTICAL_SLICE_V1`
- Design revision: `D1`
- Base: `origin/main@c27c24d6cb5f936e0549b743084bb9a9eaceb545`
- Profile: `DEV-4 FOUNDATION CRITICAL`
- State: `REVIEW_READY / SOURCE_START0`
- Product entry: the unified `BAI Video Production.exe`
- Primary route: local/free voice generation
- Default compute preference: `AUTO`
- Cloud/paid route: not runnable and not used as fallback

This packet is complete only as a technical design.  It grants no inference,
Owner-audio, training, Asset, Export, Release, Deploy or Production effect.

## 2. Owner outcome and definition of "optimal"

The Owner must be able to open the normal Product, select a currently admitted
local/free voice model, prepare the Owner's consented voice material, render an
approved script, compare technically valid candidates, listen, and retain one
accepted `48 kHz / 24-bit PCM / mono` WAV.

The Product must not label a candidate "optimal" solely because generation
finished, a hash validates, an engine reports success or one scalar score is
largest.  The winning candidate requires:

1. current VoiceProfile/Consent and subject binding;
2. current model/runtime/license/compute admission;
3. exact script, reference and operation identity;
4. successful pinned output readback;
5. technical QA whose unknown dimensions remain `UNKNOWN`;
6. an explicit Owner listening decision; and
7. no stale, replayed or cross-operation receipt.

The UI may say `技術QAに合格し、Ownerが選択したWAV`。It must not promise an
objective or universal best voice.

## 3. Existing facts and gaps

### 3.1 Existing canonical owners

- TASK-014 is the sole narration planning, render and publication owner.
- TASK-046 owns VoiceProfile/Dataset/training preparation/ModelCandidate and
  the Quick Clone lifecycle.
- TASK-048 owns calibration and technical voice-quality decisions.
- TASK-013 supplies local audio-model inventory Evidence.
- TASK-066 owns CPU/GPU/AUTO preference and live compute admission.
- TASK-036 owns Shell, startup, single-instance and packaged composition.

### 3.2 Existing implementation is not a real Product path

- Current TASK-014 Local Primary modules are no-effect preflight/admission
  contracts.  They do not load a model, render audio or publish an Asset.
- PR #470 adds a zero-shot callable envelope, but the envelope still records
  `model_loaded=false`, `audio_rendered=false` and `asset_published=false`.
- Current TASK-046 runtime assembles only explicitly synthetic non-Owner WAV.
- PR #476 adds Quick Clone lifecycle/readback, but real result binding, quality,
  playback and UI adoption remain outside it.
- Current TASK-036 Audio is an Asset/Placement workspace.  It has no Owner
  Voice Studio operation screen and does not generate narration.
- Ollama belongs to planning/LLM routes and is not a voice-runtime dependency.

TASK-073 therefore composes receipts; it does not pretend these no-effect
contracts already provide production execution.

## 4. Responsibility and trust boundaries

### 4.1 TASK-073 owns

- one operation plan and state machine for the Product vertical slice;
- late binding of actual typed receipts at the operation boundary;
- a public-safe Voice Studio view model;
- orchestration of separate preparation, inference, QA and listening effects;
- packaged synthetic E2E through the same UI and state machine;
- exact result correlation without becoming a second canonical store.

### 4.2 TASK-073 consumes but never mints

- VoiceProfile, Consent, Dataset and ModelCandidate authority;
- TASK-014 render authority and local runtime result;
- TASK-048 quality PASS;
- TASK-066 compute admission;
- installed layout, one-shot ticket and Human decision authority;
- Asset/Timeline/Export admission.

Serialized JSON, a dataclass, a self-hash, a module sentinel, a public receipt
or a caller-selected boolean never becomes effect authority.  Authoritative
capabilities are resolved in-process from current pinned durable state, are
single-operation and are burned on entry, success or exception.

### 4.3 Product process boundary

The normal packaged process acquires TASK-036's global single-instance lease
before voice context, private data, runtime probe or broker effect.  A second
launch performs no voice I/O, model load, child launch or log mutation beyond
the bounded existing-instance activation protocol.

Heavy runtime/model/GPU work is lazy and begins only for an admitted inference
operation.  Lightweight readiness composition may start with the Product.

## 5. One-direction dependency graph

```text
TASK-068 secure artifact I/O
TASK-070 installed roots/binding
TASK-071 trusted Human authorization
TASK-072 one-shot operation ticket/config
                    │
                    ▼
PR #470 TASK-014 callable + PR #476 TASK-046 Quick Clone
TASK-048 live quality + TASK-066 compute/settings + TASK-036 P0-E
                    │
                    ▼
TASK-073 body-free operation/projection and packaged synthetic E2E
                    │
                    ▼
TASK-014 real local invocation/result continuation
TASK-046 private-reference/Product binding continuation
                    │
                    ▼
TASK-073 real local E2–E5 verification
                    │
                    ▼
TASK-003 Asset adoption / TASK-044 Export (separate Human effects)
```

Fine-tuning is not on the zero-shot critical path.  The Product may prepare a
reviewable Dataset/training proposal, but P-VS-4A separately owns training
dispatch and ModelCandidate approval.

## 6. Effect levels

### E0 — design and no-effect contracts

- body-free documents, schema, states, typed ports and fixtures only;
- process, file, audio, model, network, GPU and private-data effect `0`.

### E1 — packaged synthetic Product E2E

- isolated synthetic fixture and test Project only;
- normal packaged EXE and shared UI/state machine;
- deterministic synthetic 48 kHz mono PCM24 WAV and pinned readback;
- Owner audio, model inference, network, Dataset/training and Asset effect `0`.

### E2 — installed readiness

- installed runtime/model/license/hash and live compute probe readback;
- no model download, model load, GPU reservation or audio processing.

### E3 — Owner intake and training preparation

- exact one-shot Human operation;
- pinned local Owner reference WAV and matching transcript;
- encrypted private derivative and reviewable Dataset/training proposal;
- Dataset adoption, training and inference remain `false`.

### E4 — local inference

- a separate one-shot Human operation;
- local-only admitted TTS process, one operation/one owned child;
- network and paid provider calls blocked;
- no automatic retry, backend switch or model reselection.

### E5 — technical QA and Owner listening

- pinned WAV readback, TASK-048 technical receipt and Owner decision;
- output remains private staging until accepted;
- Asset and Export effects remain `0`.

### E6 — adoption and export

- separate TASK-003/TASK-044 operation and Human confirmation;
- not authorized by TASK-073.

### ET — training

- separate TASK-046/P-VS-4A action/ticket;
- never implied by E3 preparation or E4 zero-shot inference.

## 7. Product state machine

```text
UNCONFIGURED
→ READINESS_BLOCKED | READY_FOR_REFERENCE
→ REFERENCE_REVIEW_REQUIRED
→ READY_FOR_MODEL_SELECTION
→ READY_FOR_RENDER_PLAN
→ OWNER_CONFIRMATION_REQUIRED
→ REGISTERED
→ RUNNING
→ RESULT_READBACK_REQUIRED
→ QA_REQUIRED
→ OWNER_LISTENING_REQUIRED
→ WAV_ACCEPTED | WAV_REJECTED
```

Recovery states are explicit:

- `RESUME_REQUIRED` — durable precommit state exists and no child is running;
- `UNKNOWN` — process/result ownership cannot be proven;
- `RECOVERY_REQUIRED` — ambiguous write/readback or state contradiction;
- `FAILED_KNOWN` — terminal typed failure with no success receipt;
- `CANCELLED_SAFE` — cancellation readback proves no accepted result.

`UNKNOWN` and `RECOVERY_REQUIRED` never auto-run inference.  A committed exact
result may be reopened as a duplicate readback without rerendering.  A stale
plan requires a new plan and Human action.

## 8. Voice model and runtime selection

### 8.1 User-facing catalog

The UI lists only currently installed, licensed and admitted local/free TTS
routes.  Each item shows a public-safe display name, version, route mode,
license state and readiness.  Internal model IDs/hashes appear only in a
technical disclosure and private evidence.

The current Qwen3-TTS candidate is Evidence, not a guaranteed winner.  Model
availability and quality are determined from current installed/runtime and QA
receipts, not product documentation or a static label.

### 8.2 Route modes

- `ZERO_SHOT_LOCAL` is the initial runnable route when the exact Owner
  reference/transcript and current engine are admitted.
- `FINE_TUNED_LOCAL` is selectable only with an Owner-approved current
  ModelCandidate and matching license/runtime receipt.
- Cloud/paid routes are absent from the default runnable set and are never an
  automatic fallback.

Saving a model selection is CAS/readback only.  It does not download, load,
train or infer.

### 8.3 CPU/GPU/AUTO

- `AUTO`: use a fresh admitted GPU route when eligible; otherwise a verified
  supported CPU route.  The effective backend is shown separately.
- `GPU`: fail closed when the exact live GPU admission is absent.  Do not
  silently fall back to CPU.
- `CPU`: never initialize CUDA or reserve a GPU.

The operation receipt binds preference revision, effective backend, runtime,
probe and build identities.  The backend cannot change inside one operation.
An OOM, driver reset or device loss produces `UNKNOWN`/recovery, not a silent
backend switch.

### 8.4 Ollama separation

Voice readiness neither calls nor starts Ollama.  Ollama missing, stopped or
unhealthy cannot block the Voice route.  Planning retains its independent
Ollama lifecycle and UI state.

## 9. Owner voice intake and preparation

The UI derives an exact contained coordinate from a trusted picker and private
Product root.  Public argv/JSON never supplies an arbitrary root/path.

The intake reader uses full ancestor snapshots, `lstat`, no-follow handle open,
`fstat`, bounded read and post-identity verification.  Regular file, link count
one, non-reparse ancestors and exact opened bytes are required.  `ENOENT` is
the only absence.  Same bytes at a different physical identity are not the
same authority.

Required checks include:

- Owner subject, current Consent, rights, purpose and retention;
- one speaker and matching transcript identity;
- bounded duration/bytes/channels/rate/encoding;
- clipping, silence, dropout, non-finite and truncation checks;
- immutable raw input and separately hashed encrypted derivatives;
- preprocessing tool/build identity and sample mapping.

The raw input remains immutable.  Preprocessing creates a private derivative.
No reference is automatically adopted into a Dataset and no preparation starts
training.

## 10. Inference operation

The trusted one-shot capability binds:

- Project/install/session and Owner subject;
- script revision and language;
- VoiceProfile and Consent revisions;
- reference WAV/transcript or approved ModelCandidate;
- model/runtime/license/compute receipts;
- preprocessing and quality-policy revisions;
- output coordinate and operation idempotency;
- trusted time/currentness and expiry.

Execution rules:

1. late-bind the actual inputs at operation entry;
2. burn the capability to `IN_FLIGHT` before validation or child launch;
3. allow one owned child and one exact output namespace;
4. enforce local-files-only and network egress `0`;
5. bound text, reference, duration, memory, disk and timeout;
6. capture body-free reason codes and private bounded diagnostics;
7. never auto-retry or choose another model/backend;
8. after any exception, resolve a new capability from authoritative state.

The Product never passes a caller-selectable backend, security provider,
clock, output path, model loader or fault hook to Production composition.

## 11. WAV publication and QA

### 11.1 Publication

- write to an operation-owned exclusive temporary handle;
- preserve and verify the temporary physical identity;
- flush file data and required directory durability;
- publish with no-replace semantics for an absent target;
- use expected opened bytes+inode identity CAS for an approved replacement;
- reopen no-follow and bind exact published bytes/identity to the receipt;
- clean up only an exact operation-owned current temporary identity;
- never overwrite or delete a foreign replacement.

The admitted format is exactly:

- sample rate: `48000`;
- channels: `1`;
- sample representation: signed 24-bit integer PCM;
- finite bounded frame count and complete payload.

### 11.2 Technical QA

TASK-048 supplies the live technical receipt.  At minimum the Product displays
format, duration, clipping, silence/dropout, loudness/level consistency,
boundary artifact and identity/style continuity as separate facts.  Missing or
unsupported measurements remain `UNKNOWN`.

### 11.3 Owner listening

Technical PASS is not Owner acceptance.  The Owner may compare only candidates
whose exact WAV/readback/currentness match.  Accept, reject and regenerate are
separate operations.  Regeneration creates a new candidate revision and does
not overwrite an accepted or neighboring Cue.

Owner acceptance retains the private staging WAV.  It does not automatically
create an Asset, place narration, export a video or activate a model.

## 12. Product UI flow

The unified Product exposes one Voice Studio flow:

1. `モデル` — local/free route and CPU/GPU/AUTO;
2. `参照音声` — trusted selection, Consent and transcript status;
3. `学習準備` — Dataset/training proposal with `training_started=false`;
4. `原稿` — approved text and style segments;
5. `事前確認` — exact model/runtime/compute/privacy/output facts;
6. `生成確認` — one-shot Human confirmation;
7. `進行状況` — registered/running/recovery/cancel states;
8. `試聴・品質` — technical facts and Owner listening decision;
9. `WAV` — accepted private staging readback and next separate actions.

Every successful save is displayed only after fresh readback.  The UI never
asks the Owner to type an internal path, model hash, revision, store id or
authorization token.

## 13. Packaged verification

### 13.1 Synthetic installed E2E

The installed EXE uses an isolated test profile and synthetic non-Owner audio
through the same UI/state machine.  It must prove:

- normal packaged launch and one visible Product window;
- second launch has voice process/data effect `0`;
- model and compute selection save/readback without download or load;
- Ollama absence does not block the Voice route;
- deterministic synthetic fixture reaches pinned 48 kHz mono PCM24 output;
- screen/UI automation and public-safe state match the operation receipt;
- logs are bounded, rotated and contain no fixture body or private path.

Synthetic PASS never creates Production voice authority.

### 13.2 Real local native E2–E5

Real validation uses an explicit Owner operation in a private test Project.
It runs one admitted local operation and records exact result WAV/hash, QA and
listening decision.  `NOT_EXECUTED` is never presented as PASS.  No voice data,
transcript, embedding, private Voice ID or absolute path enters Git, CI, public
logs or public Evidence.

## 14. Acceptance matrix

| ID | Acceptance |
|---|---|
| A01 | TASK-073 composes existing typed receipts and creates no second canonical store/type. |
| A02 | The normal EXE owns one global instance; a losing launch starts no voice effect. |
| A03 | Lightweight readiness may start with the EXE; model/GPU load starts only at E4. |
| A04 | Ollama state cannot block or authorize Voice. |
| A05 | Model UI shows only installed/admitted local-free routes and saves by CAS/readback. |
| A06 | Zero-shot and fine-tuned routes enforce their distinct source prerequisites. |
| A07 | CPU/GPU/AUTO bind both preference and effective backend; no silent fallback. |
| A08 | Owner input is current, consented, pinned, contained and private. |
| A09 | Training preparation has `training_started=false`. |
| A10 | Preprocessing is bounded, reproducible by receipt and preserves raw input. |
| A11 | A private one-shot capability binds every operation input/currentness fact. |
| A12 | Inference is local-only, one child/one output, bounded and non-retrying. |
| A13 | WAV publication is durable, identity-bound and foreign-artifact safe. |
| A14 | Technical QA and Owner listening are separate and both exact-current. |
| A15 | The nine-step Voice Studio UI is operable without raw paths/internal IDs. |
| A16 | Packaged synthetic E2E uses the Production UI/state machine with no Owner data. |
| A17 | Real native Evidence remains PASS/FAIL/NOT_CONFIRMED and private. |
| A18 | Public UI/log/receipt leaks no raw audio/text/transcript/path/Voice ID/secret. |
| A19 | Crash/restart never auto-runs and can read back an exact committed duplicate. |
| A20 | WAV acceptance does not imply Asset, placement, Export or Production Activation. |

## 15. Negative matrix

| ID | Input/failure | Required result |
|---|---|---|
| N01 | Unknown, unlicensed, uninstalled or hash-drifted model | Runnable `false`; model process `0`. |
| N02 | Paid/cloud credential or route present | No local fallback to cloud and network `0`. |
| N03 | Ollama missing, running or tampered | Voice state/effect unchanged. |
| N04 | Raw path, UNC, symlink, reparse, hardlink, ancestor swap or same-bytes/new-inode | Intake/output effect `0`. |
| N05 | Transcript mismatch, multi-speaker, clipped/noisy/empty/truncated/oversize reference | Inference `0`. |
| N06 | Revoked/expired/wrong-subject/purpose Consent | Private read/model load `0`. |
| N07 | Forged, copied, rehashed or deserialized public receipt/object | Capability `0`. |
| N08 | Stale/replayed/cross-action ticket or caller clock/backend injection | Effect `0`. |
| N09 | GPU requested without live admission, OOM or driver reset | No CPU fallback; recovery required. |
| N10 | CPU initializes CUDA or GPU silently runs CPU | Hard fail; no success receipt. |
| N11 | Second Product/process or concurrent same operation | Single winner; second effect `0`. |
| N12 | Config/model/reference/output changes after precheck | Capability burned; success/adoption `0`. |
| N13 | Target appears, temp is replaced, fsync/readback fails | Foreign overwrite/delete `0`; receipt `0` or UNKNOWN. |
| N14 | QA missing/forged/stale/UNKNOWN | Owner acceptance/adoption `0`. |
| N15 | Synthetic marker removed or fixture copied to Product profile | Production authority `0`. |
| N16 | Preparation accidentally dispatches training/GPU work | Hard fail; `training_started=false`. |
| N17 | UI value differs from saved canonical readback | Success display `0`; recovery required. |
| N18 | Error/UI/log contains private body/path/Voice ID/token/account | Test FAIL. |
| N19 | Restart auto-downloads or auto-runs inference | Test FAIL. |
| N20 | Owner accepts WAV and Asset/Export/placement runs automatically | Test FAIL. |

## 16. Fault seams

| ID | Seam | Required durable state |
|---|---|---|
| F0 | Lightweight broker startup unavailable | Shell remains usable; Voice degraded; heavy process `0`. |
| F1 | Ticket durable before job registration | Unconsumed/reconcilable ticket; process `0`. |
| F2 | Job registered before child spawn | `RESUME_REQUIRED`; automatic spawn `0`. |
| F3 | Child/model-load started before load receipt | `UNKNOWN`; old capability burned; output `0`. |
| F4 | GPU reserved/model loaded before inference | Release owned lease; no backend switch/retry. |
| F5 | Waveform returned before temp write | Receipt/output `0`; new explicit operation required. |
| F6 | Temp fsynced before publish | Only exact owned temp may be reconciled/cleaned. |
| F7 | Publish completed before pinned readback | UNKNOWN; QA/adoption `0`; exact restart readback may avoid rerender. |
| F8 | WAV readback before technical QA | Output retained private; `QA_REQUIRED`. |
| F9 | QA PASS before listening | `OWNER_LISTENING_REQUIRED`; Asset/Export `0`. |
| F10 | Owner acceptance before Asset adoption | Accepted staging preserved; inference not repeated. |
| F11 | Correlation/receipt publication crash | Exact result lookup/duplicate readback; rerender `0`. |
| F12 | App/Windows closes mid-operation | Preserve bounded job state; kill only exact owned child identity. |

## 17. Implementation sequence

### V1 — TASK-073 owned no-effect contract

Implement new schema, operation types, late-bound port interfaces, public-safe
projection and strict JSON/privacy/capability tests.  No existing owner file is
modified.

### V2 — packaged synthetic composition

After TASK-068/070/071/072 producer acceptance, connect an isolated synthetic
fixture to the new application.  Owner data/model/network effects remain zero.

### V3 — existing owner receipt composition

After PR #470/#476 and TASK-048/TASK-066 accepted receipts, bind their exact
public-safe/read-only projections.  Missing producers remain visible and
non-runnable; TASK-073 never manufactures a PASS.

### V4 — GF-B UI amendment

After GF-B exact4 acceptance and fresh overlap/lock, add the Voice Studio view
and bridge methods within the exact limited TASK-036 UI amendment.  Preserve
the central model/compute settings authority and do not add a feature-local
durable selector.

### V5 — P0-E packaged amendment

After TASK-036 P0-E/TASK-063/TASK-070/TASK-072 terminal handoff, bind the
application into the normal trusted launcher.  Global single-instance remains
before all voice/private/runtime effects.

### V6 — real local runtime and readback

Consume the separately completed TASK-014/TASK-046/TASK-048 owner
continuations.  Perform one private Owner-authorized E2–E5 validation.  No
Release, Deploy, Production Activation, Asset adoption or Export.

## 18. Verification and evidence

Required before commit-ready:

1. schema/static/compile checks;
2. focused operation/application/projection tests;
3. strict JSON, privacy, capability, physical I/O and all N/F matrices;
4. relevant TASK-014/046/048/036/066 regressions;
5. independent implementation Critic and Tester;
6. Judge PASS with unresolved `Critical/High = 0/0`;
7. changed-files/Allowed-Files and secret/path leakage review;
8. hosted Windows and Ubuntu Python 3.11–3.13 checks;
9. installed packaged synthetic UI/single-instance/readback Evidence;
10. real Owner-audio Evidence recorded separately and privately.

One coherent TASK-073 implementation PR is created only after the entire Task
implementation scope is complete.  CHANGELOG is added to that same PR only by
the Main Merge sole-writer after the functional head is frozen.

## 19. Explicit prohibitions

- no paid provider, Cloud fallback or model download by configuration save;
- no training dispatch from preparation;
- no automatic Dataset adoption or ModelCandidate approval;
- no arbitrary caller path, output, clock, backend or security provider;
- no second VoiceProfile/Dataset/Asset/Job/compute/settings store;
- no raw private data in tests, Git, public Evidence, UI errors or logs;
- no foreign-file overwrite/delete or unknown-state repair;
- no automatic inference retry after crash or ambiguity;
- no Release, Deploy, Production Activation, Asset adoption, placement or
  Export under TASK-073 authority.

## 20. Review gate

This D1 packet must be hashed and independently reviewed without mutation.
Any finding produces a new design revision and hash while preserving D1 as
immutable failed history.  Product source remains `START0` until the accepted
revision has `Critical=0`, `High=0` and Judge `PASS`.
