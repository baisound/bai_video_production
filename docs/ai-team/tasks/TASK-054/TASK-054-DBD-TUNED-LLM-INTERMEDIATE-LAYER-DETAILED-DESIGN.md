# TASK-054 — DbD Tuned LLM Intermediate Reasoning Layer Detailed Design

Status: `DESIGN COMPLETE / FUTURE IMPLEMENTATION GATED`

Date: `2026-08-21 JST`

Development profile: `DEV-3 HIGH ASSURANCE`

## 1. Placement decision

```text
Media
 -> detectors / ASR / OCR
 -> admitted Evidence
 -> deterministic Event Resolver
 -> Canonical Game Event Timeline (CGEL)
 -> compatible Game Knowledge + patch-aware RAG
 -> DbDReasoningContextEnvelope
 -> tuned LLM reasoning/style adapter             [TASK-054]
 -> strict DbDReasoningProposal parser
 -> deterministic Fact Validator
 -> deterministic Tactical/Policy Validator
 -> Commentary Candidate
 -> Human Approve / Correct / Reject
 -> existing explicit Production adoption
```

The tuned model is deliberately not placed between detector output and Event
confirmation. LLM output is never Evidence. It cannot promote an observation,
confirm an Event, write Knowledge, select credentials, mutate Timeline state or
approve its own output.

The current `CommentaryPlanner`, `CommentaryLlmService`,
`CommentaryFactValidator`, `CommentaryCandidateStore`, CGEL, Game Knowledge,
common RAG and canonical Provider boundaries remain authoritative.

## 2. Original-design reconciliation

The recovered original design separates these responsibilities:

- RAG: current patch facts, entity facts, tactical sources and provenance;
- tuning/LoRA: commentary structure, explanation order, DbD vocabulary, tempo,
  density, emotional intensity, prioritization and calibrated abstention;
- LLM reasoning: combine canonical facts, Events, tactical retrieval and style;
- deterministic validation: prevent invented numbers, activations, entities,
  patches, status effects and unsupported tactical certainty;
- Human Gate: decide whether a valid candidate is useful and adoptable.

Current Product source already has the safe outer loop `CommentaryPlan -> canonical
Provider -> strict JSON -> CommentaryFactValidator -> Candidate`. TASK-054 fills
the missing versioned tuned-model identity, structured intermediate reasoning,
offline evaluation, promotion/rollback and Human-comparison contracts.

## 3. Canonical ownership

| Concern | Canonical owner | Tuned model authority |
|---|---|---|
| Media/body/timebase | Asset/Evidence owners | bounded refs only |
| Observations | existing detectors | none |
| Event truth/state | CGEL + deterministic resolver | none |
| Game facts/revisions | Game Knowledge | none |
| Retrieval/index | common RAG Provider | none |
| Tactical interpretation | TASK-054 proposal | candidate only |
| Wording/style | TASK-054 proposal | candidate only |
| Factual/policy admission | deterministic validators | none |
| Commentary approval | Human Review | none |
| TTS/Timeline/publication | existing Product owners | none |

No second canonical Timeline, Knowledge Store, RAG Store, Candidate Store,
credential system or Provider stack is permitted.

## 4. Component decomposition

Future implementation uses the following bounded modules:

```text
dbd_reasoning_contracts.py
  TunedModelBinding
  DbDReasoningContextEnvelope
  DbDReasoningProposal
  DbDReasoningExecutionReceipt

dbd_reasoning_context.py
  DbDReasoningContextAssembler
  DbDContextCompatibilityValidator

dbd_tuned_model_registry.py
  DbDTunedModelRegistry
  DbDTunedModelResolver

dbd_reasoning_validation.py
  DbDReasoningProposalParser
  DbDTacticalPolicyValidator
  CommentaryFactValidator extension/bridge

dbd_reasoning_execution.py
  DbDTunedReasoningService
  canonical AiConnectionResolver / provider execution reuse

dbd_reasoning_evaluation.py
  DbDReasoningEvaluationHarness
  blind baseline/generic/tuned comparison

dbd_reasoning_review.py
  append-only correction/rejection/promotion decisions
```

Each module is pure or provider-neutral until `DbDTunedReasoningService`. No
module may import BAI Development OS as a Product runtime dependency.

## 5. Contracts and schemas

### 5.1 `TunedModelBinding`

```json
{
  "schema_version": "1.0.0",
  "binding_id": "dbd-commentary-ja-v1",
  "revision": 1,
  "status": "DRAFT|EVALUATED|APPROVED|SUSPENDED|REVOKED",
  "purpose": "DBD_COMMENTARY_REASONING",
  "base_model_ref": "model://registry/base/version",
  "base_model_sha256": "sha256:...",
  "adapter_ref": "model-adapter://registry/dbd-ja/r1",
  "adapter_sha256": "sha256:...",
  "training_dataset_sha256": "sha256:...",
  "training_recipe_sha256": "sha256:...",
  "evaluation_report_sha256": "sha256:...",
  "rights_manifest_sha256": "sha256:...",
  "supported_locales": ["ja-JP"],
  "context_schema": "1.0.0",
  "output_schema": "1.0.0",
  "route_capability": "DBD_TUNED_COMMENTARY_REASONING",
  "approved_at": null,
  "approved_by_ref": null
}
```

Invariants:

- `APPROVED` requires all artifact/dataset/recipe/evaluation/rights digests and a
  `human://` approval ref;
- `SUSPENDED` and `REVOKED` never resolve;
- raw paths, model bodies, credentials and secrets are forbidden;
- base and adapter identities are separately pinned;
- unknown/future schema fails closed;
- binding content is canonical-json hashed and immutable by revision.

### 5.2 `DbDReasoningContextEnvelope`

```json
{
  "schema_version": "1.0.0",
  "context_id": "...",
  "match_id": "...",
  "event_id": "...",
  "event_revision": 3,
  "timeline_sha256": "sha256:...",
  "game_version": "...",
  "mode": "LIVE",
  "policy_version": "1.0.0",
  "observed_facts": [],
  "canonical_facts": [],
  "evidence_refs": [],
  "knowledge_ref_sha256s": [],
  "rag_chunks": [],
  "uncertainties": [],
  "forbidden_claims": [],
  "speech_budget_ms": 4200,
  "language": "ja-JP",
  "style_profile_ref": "style://generalized/dbd-ja-balanced/r1"
}
```

`observed_facts` and `canonical_facts` use exact typed key/value pairs.
`rag_chunks` contain only bounded content plus source ID/type, rights status,
patch interval, verification state and digest. Retrieved text is untrusted data,
never system instruction. Unknowns and contradictions remain explicit.

Hard limits are policy-controlled and checked before dispatch: total bytes/tokens,
facts, chunks, chars/chunk, refs, hypotheses requested and speech budget.

### 5.3 `DbDReasoningProposal`

```json
{
  "schema_version": "1.0.0",
  "disposition": "PROPOSE|REVIEW_REQUIRED|ABSTAIN",
  "observed_claims": [],
  "canonical_claims": [],
  "inferred_states": [],
  "tactical_interpretations": [],
  "commentary_outline": [],
  "commentary_text": "...",
  "citations": [],
  "uncertainty_codes": [],
  "style_metrics": {
    "density_milli": 0,
    "emotion_milli": 0,
    "tempo_milli": 0
  }
}
```

Observed/canonical claims must copy allowlisted keys and values exactly. Inferred
and tactical items require confidence, refs and `POSSIBLE|LIKELY`; `CONFIRMED` is
forbidden. Commentary may paraphrase validated structure but cannot introduce an
unlisted number, entity, activation, status, patch claim or tactic. `ABSTAIN` is a
successful safe result.

Hidden chain-of-thought is neither requested nor stored. Only bounded structured
claims, uncertainty/reason codes and supporting refs are persisted.

### 5.4 `DbDReasoningExecutionReceipt`

The receipt stores:

- context, binding, prompt-template and output-schema digests;
- route/provider/model/adapter refs and attempt ID;
- authorization decision and cost ceiling, never credential values;
- start/end, latency, token counts and bounded resource metrics;
- parser/fact/policy/stale/Human results;
- fallback/retry reason and final disposition.

Invalid raw Provider output follows the existing private Evidence retention policy
and is never an admitted Candidate.

## 6. API-level design

```python
class DbDReasoningContextAssembler:
    def assemble(
        self,
        *,
        event: CanonicalGameEvent,
        evidence_by_id: Mapping[str, GameEvidence],
        knowledge_refs: Sequence[GameKnowledgeRef],
        rag_results: Sequence[RagChunk],
        policy: DbDReasoningContextPolicy,
        speech_budget_ms: int,
        style_profile_ref: str,
    ) -> DbDReasoningContextEnvelope: ...

class DbDTunedModelResolver:
    def resolve(
        self,
        *,
        binding_id: str,
        expected_revision: int,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        required_capability: str,
    ) -> ResolvedTunedModelRoute: ...

class DbDTunedReasoningService:
    def propose(
        self,
        *,
        context: DbDReasoningContextEnvelope,
        binding: TunedModelBinding,
        profile: AiConnectionProfile,
        availability: ConnectionAvailability,
        execution_authorized: bool,
        cost_ceiling: CostCeiling,
    ) -> DbDReasoningAttempt: ...

class DbDTacticalPolicyValidator:
    def validate(
        self,
        context: DbDReasoningContextEnvelope,
        proposal: DbDReasoningProposal,
    ) -> TacticalValidationResult: ...
```

`propose()` rechecks binding/context state before dispatch and again before return.
It never persists or adopts a Candidate. A separate Application Service composes
parser + Fact Validator + Policy Validator + append-only Candidate store.

## 7. Validation sequence

```text
1 schema/type/size
2 binding state/revision/digest
3 Event/Timeline/Knowledge/RAG freshness
4 exact observed/canonical claim membership
5 number/entity/status/activation membership
6 patch compatibility and provenance
7 citation completeness
8 tactical assertion and uncertainty policy
9 speech/style budget
10 stale-state recheck
11 Human Review
```

Validators reject; they do not silently rewrite. Human correction creates a new
Candidate linked to original/corrected values, reviewer, reason and provenance.

## 8. Runtime state machines

### Session mode contract

```text
PREVIEW_NO_LEARNING
LEARNING
```

`PREVIEW_NO_LEARNING` accepts an ordinary video, executes the currently selected
approved/baseline analysis and reasoning path, and renders a time-aligned preview
of what実況/解説 would be produced now. It cannot create/adopt Dataset examples,
start training, write model/adapters, change a binding or mine its own generated
text. Result receipts may be retained as evaluation Evidence, but carry
`training_eligible=false`.

`LEARNING` enables reviewed source narration, Operator-authored targets and Human
corrections to become Dataset candidates. Only Human-approved/corrected targets
may enter a Dataset revision; generated output never self-labels. The selected,
authorized training job then creates a new quarantined adapter revision and runs
evaluation. Learning never mutates the currently approved adapter in place.

Mode is fixed for the session/request, included in every receipt and visible in
the persistent UI header. Switching mode requires ending or safely cancelling the
current session; it cannot occur implicitly.

Inference:

```text
CONTEXT_PENDING -> CONTEXT_READY -> BINDING_RESOLVED
 -> EXECUTION_AUTHORIZED -> GENERATED -> SCHEMA_VALIDATED
 -> FACT_VALIDATED -> POLICY_VALIDATED -> HUMAN_REVIEW
 -> ADOPTED | REJECTED | ABSTAINED
```

Binding lifecycle:

```text
DRAFT -> EVALUATED -> APPROVED -> SUSPENDED -> APPROVED
                                      \-> REVOKED
EVALUATED -> REJECTED
```

Training lifecycle:

```text
DATASET_DRAFT -> RIGHTS_VERIFIED -> SPLIT_LOCKED -> TRAINING_AUTHORIZED
 -> TRAINING -> ARTIFACT_QUARANTINED -> OFFLINE_EVALUATED
 -> HUMAN_REVIEW -> EVALUATED_BINDING
```

Training completion never implies `APPROVED` or Product activation.

Preview invariants are tested by comparing before/after Dataset revision/digest,
base/adapter digests, binding revision/status and Training Job count: all must be
identical. Learning-mode acceptance requires a new Dataset/artifact revision and
lineage; overwrite is forbidden.

## 9. Fail-closed matrix

| Failure | Result | Retry |
|---|---|---|
| missing/revoked binding | `ABSTAINED` | no |
| authority/cost absent | `BLOCKED_AUTHORITY` | after new authority only |
| Provider/runtime unavailable | `BLOCKED_RUNTIME` | bounded policy only |
| context stale | `REJECTED_STALE_CONTEXT` | rebuild context |
| malformed/oversized output | `REJECTED_SCHEMA` | max one changed attempt |
| unsupported fact/citation | `REJECTED_VALIDATION` | new Candidate only |
| prompt injection detected | `REJECTED_INPUT_POLICY` | remove/review source |
| resource ceiling exceeded | `CANCELLED_RESOURCE_LIMIT` | explicit new budget |
| Human reject | `REJECTED_HUMAN` | corrected new version only |

Generic-model/template fallback is allowed only if explicitly configured and its
binding is separately approved. Route identity is visible; fallback is not silent.

## 10. Dataset and tuning boundary

Tune behavior, not current truth:

- prioritize what to say;
- explanation order and causal structure;
- DbD vocabulary, tempo, density, tone and educational level;
- calibrated uncertainty and abstention;
- observation/fact/hypothesis/expression separation.

Do not tune current Perk/Add-on/Killer values, patches, Event truth, private
identity, secrets or a real commentator's unique persona without separate rights
and consent.

Dataset rows retain context digest, redacted structured context, Human-approved
proposal, generalized style labels, speech budget, source-group/Match, patch,
Killer/Map/event/locale, rights/consent/provenance and review decision. Split is
locked by source group/Match. Near-duplicate and phrase-overlap audits prevent
cross-split leakage and memorized test answers.

### Narration/commentary video learning source

Videos containing narration—play-by-play実況 and analytical解説—are a first-class
intake source:

```text
rights-admitted video
 -> canonical audio extraction
 -> source separation / VAD
 -> timestamped ASR
 -> speaker diarization
 -> CGEL/Event temporal alignment
 -> commentary-role segmentation
 -> Human transcript/speaker/role/context review
 -> structured Dataset candidate
 -> Dataset revision adoption
```

Role labels are `PLAY_BY_PLAY`, `ANALYSIS`, `TACTICAL`, `REACTION`, `TRANSITION`,
`FILLER` and `UNCERTAIN`. The LLM learns text structure, timing, ordering,
vocabulary, density, uncertainty and the difference between実況 and解説. It does
not learn voice timbre, biometric speaker identity or an implicit voice clone.
Voice/audio-model learning stays under separate Voice Consent/Voice ownership.

Each segment retains source video/audio refs, exact source range, pseudonymous
speaker ref, ASR/diarization revisions, original and Human-corrected transcript,
role, aligned Event/context digest, rights/consent refs and reviewer provenance.
Public availability alone is not training permission.

Uncertain words/speakers/alignment, overlap, music bleed, unresolved proper nouns,
incompatible patches or unsupported tactical claims remain `NEEDS_REVIEW` or are
rejected. Automatic mining creates candidates only; it never adopts Dataset rows.

Negative data includes unknown patches/entities, missing revisions, conflicting
modalities, prompt-injection RAG, unsupported numbers/causes, congested speech
windows and rights-conflicting style requests.

## 11. Evaluation and promotion

Blind held-out comparison covers deterministic/template baseline, approved generic
model and tuned candidate. Reviewers do not see route identity.

| Metric | Minimum gate |
|---|---:|
| schema-valid output | `>= 995/1000` |
| unsupported admitted facts | `0` |
| patch-incompatible admitted claims | `0` |
| citation coverage | `1000/1000` |
| secret/PII leakage | `0` |
| source-group split leakage | `0` |
| replay stability | `>= 950/1000` |
| safe-negative abstention | `>= 950/1000` |
| Human factual acceptability | no baseline regression |
| Human style preference | justified improvement |
| latency/cost/resource | approved budget |

Safety failures are non-compensating. Aggregate preference cannot offset one
admitted unsupported fact, leakage or provenance violation.

## 12. Security and rights

- RAG/transcript/import content is untrusted data and structurally isolated from
  system policy;
- data cannot choose tools, routes, credentials or binding;
- artifact/adapter files require immutable digest verification;
- local loaders cannot execute arbitrary remote repository code;
- prompts/receipts never persist credential values;
- private Dataset adoption requires encrypted-storage and rights/consent gates;
- generalized style is default; specific-person imitation is separately gated;
- revocation prevents future resolution while preserving historical receipts.

## 13. Unified Product UX

No standalone DbD product is created. The existing Game Intelligence Commentary
panel will show binding status/revision, baseline/tuned identity, route/cost before
execution, source summary, separated Observed/Canonical/Inferred/Tactical/
Commentary sections, validation errors, blind comparison, Approve/Correct/Reject,
stale warnings and versioned regeneration.

Training Studio may manage Dataset examples/evaluation reports, but cannot train,
download or activate merely because examples are approved.

## 14. Two-level implementation decomposition

### R0 Contracts and threat model

- R0A enums/dataclasses/canonical serialization;
- R0B JSON Schemas and checksum verification;
- R0C unsafe-ref/secret/prompt-injection/size/stale negative fixtures;
- R0D Critic/Judge contract review; no model execution.

### R1 Context assembly

- R1A exact CGEL/Evidence adapter;
- R1B Knowledge revision/patch adapter;
- R1C common RAG result adapter and injection isolation;
- R1D deterministic limits/digest/replay tests.

### R2 Output admission

- R2A strict parser;
- R2B existing Fact Validator extension;
- R2C tactical assertion/citation/style validator;
- R2D append-only Candidate/receipt/correction lineage.

### R3 Binding and execution

- R3A registry lifecycle/revocation;
- R3B `DBD_TUNED_COMMENTARY_REASONING` route capability;
- R3C fake deterministic adapter and fault tests;
- R3D gated canonical Provider/local adapter integration.

### R4 Dataset and evaluation

- R4A rights/provenance Dataset manifest;
- R4B narration transcript/diarization/role/CGEL-alignment intake;
- R4C split/duplicate/leakage audit;
- R4D offline baseline/generic/tuned evaluator;
- R4E blind Human review and promotion report.

### R5 UX

- R5A explicit `確認モード（学習しない）` / `学習モード` selector and immutable
  mode receipt;
- R5B ordinary-video current-commentary preview with time-aligned output;
- R5C Commentary model status/execute/review panel;
- R5D Training Studio Dataset/evaluation view;
- R5E accessible Japanese progress/cancel/error/recovery;
- R5F no-console bounded worker lifecycle.

### R6 Gated pilot

- R6A exact environment/runtime probe;
- R6B authorized training or adapter acquisition;
- R6C quarantined artifact hash/evaluation;
- R6D `EVALUATED` binding only.

### R7 Windows packaged acceptance

- R7A exact EXE hash/build;
- R7B offline fixture, cancellation and missing runtime;
- R7C authorized route, restart/replay and stale context;
- R7D process/latency/memory/cost Evidence.

### R8 promotion

- R8A independent Gold/security/rights review;
- R8B rollback/revocation drill;
- R8C Owner activation decision;
- R8D separately authorized release/Production gate.

## 15. Human Gates

Separate explicit authority is required for Dataset adoption, model/runtime or
adapter download, local/paid training, external Provider inference/upload,
binding approval, default-route activation, Commentary/TTS/Timeline adoption and
release/deployment/Production Activation. Design approval grants none.

## 16. Definition of Done

The future capability is complete only when the tuned model cannot confirm or
mutate canonical state; all admitted statements are traceable or explicitly
bounded hypotheses; all revisions are immutable/replayable; unsafe state abstains;
existing canonical owners are reused; held-out evaluation meets every safety gate;
Human review/rollback/revocation work; packaged Windows acceptance passes; and no
private body, secret, copyrighted body or hidden chain-of-thought leaks.
