# TASK-058 P1C-D External Monotonic Anchor Candidate Contract

Date: `2026-08-27`
Profile: `DEV-4 FOUNDATION CRITICAL`
Atomic Unit: `P1C-D / pure external monotonic anchor candidate contract`
Execution class: `NO_EXTERNAL_OR_MUTABLE_I/O`

## 1. Decision

P1C-D fixes the body-free structural contract that a later canonical Product
Project writer must use when it establishes an external monotonic anchor. The
Unit does not read, write, own, authenticate, or durably observe an anchor. Its
public records remain caller-constructible candidates with
`EXTERNAL_ANCHOR_REVALIDATION_REQUIRED / NOT_ESTABLISHED`.

P1C-D is separated from the writer so rollback/fork classification, exact
scope, anchor chaining, CAS coordinates, and false-authority serialization are
reviewed independently from filesystem, ProjectSave, recovery, and receipt
minting failure modes.

## 2. Inputs and records

### Anchor candidate

One candidate binds only:

- `project_id + canonical_store_id + owner_scope_hash + ledger_key_sha256`;
- sequential anchor revision and previous candidate digest;
- exact non-empty P1C-C ledger revision/latest-entry/chain/ledger digests;
- false observation/origin/commit/rollback authority fields;
- exact false authority and effect maps;
- a domain-separated candidate digest.

Anchor revision one has no predecessor. Later revisions require the previous
anchor digest. An anchor revision cannot exceed the anchored ledger revision.
This is structural consistency, not proof that an external store committed the
candidate.

### Anchor expectation

An absent expectation binds one P1C-C ledger key and requires revision zero
with all current-anchor and current-ledger coordinates null. An existing
expectation binds anchor revision/hash plus anchored ledger revision/chain/hash.
`expectation_is_authority=false` is fixed.

### Evaluation

Evaluation stores only observed/proposed coordinates, one closed decision, the
expectation digest, an optional proposed anchor candidate, false authority and
effect maps, and its own domain-separated digest. It embeds no full ledger,
source delivery, Human edit, media, path, actor, account, secret, or receipt
body.

## 3. Exact typed transition boundary

The evaluator accepts:

```text
current anchor candidate or None
exact anchor expectation
current exact P1C-C ledger or None
proposed exact non-empty P1C-C ledger
```

Current anchor and current ledger are an atomic pair. The evaluator reparses
all supplied exact typed records. A mapping or scalar/container subclass is not
a capability and is rejected.

For an existing anchor, the anchor must bind the complete supplied current
ledger. An advance requires the proposed ledger to preserve the entire current
entry prefix exactly and increase the ledger revision. Comparing only revision,
latest entry, chain, or self-hash is insufficient.

## 4. Closed decisions

| Decision | Meaning |
|---|---|
| `BOOTSTRAP_CANDIDATE` | Absent expectation matches and a non-empty ledger yields anchor candidate revision one. |
| `ADVANCE_CANDIDATE` | Existing anchor/CAS matches and the proposed ledger is an exact higher-revision extension. |
| `UNCHANGED_CANDIDATE` | The exact currently anchored ledger is supplied again; no candidate is emitted. |
| `ROLLBACK_REJECTED` | Proposed ledger revision is below the anchored current ledger. |
| `FORK_REJECTED` | Same-revision content differs or a higher ledger does not preserve the full current prefix. |
| `SCOPE_MISMATCH_REJECTED` | Project/store/Owner-scope/ledger-key coordinates differ. |
| `STALE_ANCHOR_REJECTED` | Any expected anchor/CAS coordinate differs from the supplied current anchor. |

None of these decisions proves an external latest value or creates rollback
detection authority. Duplicate/unchanged classification is local to the
supplied candidate graph.

## 5. Authority and effect boundary

Every candidate and evaluation fixes these statements false:

- raw source revalidated under canonical Product Project transaction;
- canonical Product Project transaction held;
- canonical store commit verified;
- external monotonic anchor verified or origin authenticated;
- rollback detection authority created;
- public v2 receipt mint authorized;
- canonical admission or automatic learning promotion authorized;
- filesystem/canonical-ledger/external-anchor/Project manifest writes;
- receipt, Timeline, Resolve, Provider, network, process, Release, Deploy, or
  Production effects.

The later writer must rerun raw P1C-B verification internally, hold the
canonical Product Project transaction boundary, read and authenticate the real
external anchor, persist and recover the canonical ledger and anchor, perform
durable commit read-back, and only then mint a public v2 receipt. A P1C-D
mapping, self-hash, typed instance, or GO review cannot replace those steps.

## 6. API

```text
MontageLearningExternalMonotonicAnchorExpectation.for_absent_anchor(ledger)
MontageLearningExternalMonotonicAnchorExpectation.for_anchor(anchor)
MontageLearningExternalMonotonicAnchorExpectation.from_dict(mapping)
MontageLearningExternalMonotonicAnchorCandidate.from_dict(mapping)
evaluate_montage_learning_external_monotonic_anchor(
    current_anchor, expectation, current_ledger, proposed_ledger
)
MontageLearningExternalMonotonicAnchorEvaluation.from_dict(mapping)
```

There is no open/load/save/write/replace/recover/get-latest/mint/receipt API.

## 7. Exact scope and acceptance

Exact six paths:

1. `docs/ai-team/tasks/TASK-058/task.md`;
2. this design;
3. `schemas/montage-learning-external-monotonic-anchor-candidate.schema.json`;
4. byte-identical packaged Schema mirror;
5. `src/ai_video_production/montage_learning_external_monotonic_anchor_contract.py`;
6. `tests/test_task058_montage_learning_external_monotonic_anchor_contract.py`.

Acceptance requires Schema Draft 2020-12 and mirror parity; deterministic
bootstrap/advance; unchanged, rollback, same-revision fork, higher-prefix fork,
scope mismatch and stale expectation fixtures; exact anchor/current-ledger
binding; absent-sentinel and non-empty-ledger rules; exact built-in scalar and
container rejection; proposed-anchor parser cross-binding; immutable detached
records; false authority/effect matrices; pure/no-I/O source surface; focused
and P1C-A through P1C-D direct regression; exact diff scope; and independent
Critic/Tester/Judge with unresolved C/H/M/L zero.
