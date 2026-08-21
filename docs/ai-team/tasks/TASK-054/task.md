# TASK-054 — DbD Tuned LLM Intermediate Reasoning Layer

Status: `R4A_DATASET_RIGHTS_MANIFEST_COMPLETE / COMMIT_READY / ADOPTION_HUMAN_GATED`

Development profile: `DEV-3 HIGH ASSURANCE`

Owner intent: exact instruction `実作業に戻って` on `2026-08-21`; bounded local implementation lane under the standing Atomic Unit rule

## Purpose

Define a DbD-specialized tuned language-model layer between canonical Game
Intelligence context assembly and commentary candidate generation. The model may
rank information, form bounded tactical hypotheses and express commentary, but it
never owns or confirms game facts, Events, Knowledge or Production decisions.

## Deliverables

- `TASK-054-DBD-TUNED-LLM-INTERMEDIATE-LAYER-DETAILED-DESIGN.md`
- `TASK-054-BASE-LLM-SETUP-TRAINING-TUNING-OPERATIONS-RUNBOOK.md`
- `TASK-054-OPERATOR-UX-DETAILED-DESIGN.md`
- `TASK-054-SALES-EXPLANATION-JA.md`
- `TASK-054-DESIGN-CRITIC-JUDGE-DECISION.md`

## R0 completion checkpoint

R0A-R0D Contracts/Threat Model are complete and commit-ready. The bounded
local implementation reuses existing `IdKind` and `CommentaryClaimKind` and
adds Binding/Context/Proposal/ExecutionReceipt contracts, immutable
`PREVIEW_NO_LEARNING` behavior, freshness and RAG-untrusted checks, bounded
size checks, secret/reference and runtime-admission guards, and the canonical
schema mirror. Focused Evidence is `32 PASS`; combined direct-dependency plus
schema/OSS Evidence is `75 PASS`. Critic/Judge unresolved Critical/High is
`0 / 0` and the decision is `GO`. R1 is the next bounded unit.

## R1 completion checkpoint

R1A-R1D Context Assembly is complete and commit-ready. The pure assembler
binds exact current Event, Timeline, Evidence, Knowledge, Trivia and RAG
snapshots; preserves LIVE/PTB environment and Evidence/RAG snapshot digests in
Context Schema 1.1; applies the existing Perk-exclusive and Killer/Power-inclusive
patch boundaries; isolates untrusted RAG; and requires exact Event/confirmed
Perk Activation facts. Direct oversized Contexts and stale or substituted
dependencies fail closed. Focused plus direct-dependency Evidence is `86 PASS`;
schema/OSS Evidence is `34 PASS`; compileall and schema-mirror checks pass.
Final independent Critic/Judge unresolved Critical/High is `0 / 0` and the
decision is `GO`. R2 Output Admission is the next bounded unit.

## R2 completion checkpoint

R2 Output Admission is merged on `main` through PR `#264`, with the shared
CHANGELOG lock closed through PR `#266`. The implementation structurally
quarantines raw LLM output, reuses the existing Commentary Fact Validator and
Candidate Store, applies deterministic Policy/DLP/reference admission, and
keeps Human approval/correction lineage append-only and approval-gated. Direct
R2 completion Evidence is `332 PASS`; final Critic/Judge unresolved
Critical/High is `0 / 0` and the decision is `GO`.

## R3A completion checkpoint

R3A Binding Registry lifecycle/revocation is complete and commit-ready. The
pure immutable registry reuses the existing `TunedModelBinding`, adds exact
canonical lifecycle records and schema mirror, enforces gap-free append-only
revision chains, one-shot body-free Human Evidence coordinates, immutable
evaluated artifact lineage, suspension/revocation latest-only resolution and
ambiguous-selection rejection. Resolution explicitly remains
`NOT_AUTHORIZED_R3B_REQUIRED`; no Provider, model/runtime, Dataset, training or
Product effect exists in this unit. Focused Evidence is `19 PASS`; TASK-054
R0-R3A plus TASK-049 direct regression is `351 PASS`; compileall, schema mirror
and diff-check pass. R3B route capability is next.

## R3B completion checkpoint

R3B route capability is complete and commit-ready. The pure resolver reuses the
existing `AiConnectionResolver`, requires the exact
`DBD_TUNED_COMMENTARY_REASONING` capability, and binds one latest APPROVED R3A
binding to an exact connection-profile route pin. The body-free decision records
Provider/model/cost and binding/profile/registry identities without credential or
endpoint references, settings, prompt or output bodies. It always remains
`NOT_AUTHORIZED_R3D_REQUIRED`; later consumers must re-resolve current
Registry/Profile/availability state instead of treating the checksum as an
authentication token. R3B focused Evidence is `27 PASS`; R3B + R3A + TASK-028
direct boundary Evidence is `57 PASS`; TASK-054 plus TASK-049 direct regression
is `380 PASS`; compileall, schema mirror and diff-check pass. R3C deterministic
fake adapter/fault tests are next.

## R3C completion checkpoint

R3C deterministic fake adapter/fault harness is complete and commit-ready. The
test-only in-memory harness revalidates the current R3B decision before every
emission, accepts only the canonical R2A strict parser and provides deterministic
SUCCESS, malformed, timeout, cancellation, runtime-unavailable and resource-limit
scenarios. Raw fixture bytes exist only while R2A parses them; the returned
Attempt retains only digests, stable fault codes, metrics and the structural
quarantine result. It cannot mint an ExecutionReceipt, Proposal, Candidate,
review, Dataset or execution authority, and fixed state remains
`TEST_ONLY_NO_PROVIDER_EXECUTION`. R3C focused Evidence is `18 PASS`; R3C + R3B
and R2A direct boundary Evidence is `160 PASS`; TASK-054 plus TASK-049 direct
regression is `398 PASS`; compileall and diff-check pass. R3D canonical
Provider/local adapter integration remains a separate Human Gate.

## R4A completion checkpoint

R4A Dataset rights/provenance manifest is complete and commit-ready. It binds
existing CAND-R2D and Game Match identities to opaque media, rights, Consent,
provenance and Human-review SHA references, fixes each source group to one split,
and derives disposition fail-closed. The body-free manifest is always
`CANDIDATE_ONLY_NO_ADOPTION`, performs no I/O and carries no transcript/media
body. Focused Evidence is `9 PASS`; R4A plus direct R0/R2D lineage Evidence is
`85 PASS`. Dataset adoption, narration intake and training remain Human-Gated.

## Authority boundary

This checkpoint closes the bounded local R3C deterministic fake adapter and R4A
Dataset rights/provenance manifest units. It does not adopt a Dataset or authorize training.
R3D is not eligible without its separate Human Gate. This checkpoint does not authorize Dataset adoption,
model/runtime download, local or paid training, Provider inference, TTS,
Timeline adoption, binding approval, Product Activation, release or deployment.
Those remain Human-Gated.

## Current decision

R3C deterministic fake adapter/fault harness and the independent R4A body-free
rights/provenance manifest are complete and commit-ready under the Owner's exact
bounded instruction. The tuned model design remains after CGEL + compatible
Knowledge/RAG and before deterministic Fact/Policy validation. R3D is Human-Gated;
all Dataset, runtime, training, Provider, TTS, Timeline, release and deploy
effects remain blocked by their Human Gates.
