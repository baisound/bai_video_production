# TASK-027 Post-v0.21 Current-main Audit and Output Adoption Builder Design

Date: `2026-08-15`
Authority: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
Starting Source of Truth: exact clean main
`1956f6e04b0c6206f64333d719f41c567def0590`
Working branch: `feature/task-027-generation-output-adoption-design`
Selected unit: `BVP-TASK-027-P-ORCH-1 / GENERATION_OUTPUT_ADOPTION_DESIGN`
DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
Mode: `DESIGN_ONLY`

## 1. Fresh-main and release audit

- TASK-045 post-release Evidence PR #78 passed hosted `9 / 9` and merged at the
  exact current main above.
- Package and latest stable Release are `0.21.0 / v0.21.0`.
- The annotated Tag targets release-code main
  `c38187ed54e3601c44411d9b8a128348b0d8a7b7`; the later main commit contains
  Evidence/docs only.
- No Open PR or colliding TASK-027 remote branch exists at selection time.
- The fresh checkout is clean and no unknown local changes are present.
- The protected historical WIP checkout under
  `D:\BAI\bvp-task042-p-v6-4-autonomy` remains untouched.

TASK-013 Native H3 stays `PARKED_TO_SAFE_RUNTIME_REVIEW`. TASK-014 paid
narration execution, credentials and Production Deploy remain Human Gates.
Those task-local gates do not block this provider-free integration design.

## 2. Requirement adjudication against current main

| Owner Directive capability | Current truth | Decision |
|---|---|---|
| Start/End frame reference binding | TASK-042 Blueprint v2 and WORLD LOCK are hosted-closed | `ALREADY_IMPLEMENTED` |
| WORLD LOCK lifecycle | TASK-037 Candidate/Audit/ACCEPT/LOCK/STALE projection is hosted-closed | `ALREADY_IMPLEMENTED` |
| Visual Prompt Director | typed compiler, normalized Prompt and private body/hash boundary are hosted-closed | `ALREADY_IMPLEMENTED` |
| Provider -> compatible Model | TASK-028/032..034 projection and exact capability filtering exist | `ALREADY_IMPLEMENTED` |
| Production Timeline audio | TASK-042 P-V6-4 frame-authoritative Timeline Audio exists | `ALREADY_IMPLEMENTED` |
| Unified Editor / Export Queue | TASK-044 P-NLE-1..4 and packaged acceptance are hosted-closed | `ALREADY_IMPLEMENTED` |
| Approved Plan -> generation admission | TASK-027 durable Queue is hosted-closed | `ALREADY_IMPLEMENTED` |
| local/free execution control | TASK-013 durable no-replay execution and exact Comfy adapter exist | `PARTIALLY_IMPLEMENTED`; Native H3 remains parked |
| completed output -> canonical Product lifecycle | output Evidence stops before Asset/Candidate/Attempt/Audit entry | `NEW_CAPABILITY_REQUIRED` |
| full TASK-027 orchestration | Planning and Queue exist; later production handoffs remain incomplete | `PARTIALLY_IMPLEMENTED` |

The current execution store deliberately persists
`candidate_creation_authorized=false`. `GenerationOutputProductionBinding`
already validates an existing PASS Attempt and existing Candidate, but no
Application safely creates both from a verified completed local execution.
Direct Shell `production_register_candidate` accepts caller-supplied identities
and is not an execution-output adoption proof.

## 3. Problem and user outcome

After a future safe local generation succeeds, the Product must not leave the
operator with an opaque output reference or require manual identity copying.
It needs a bounded Human-confirmed adoption flow:

```text
exact COMPLETED local execution
  -> contained output bytes/hash/media revalidation
  -> canonical TASK-003 Asset ingest
  -> TASK-037 Candidate registration
  -> TASK-040 PASS Attempt + GENERATED_FROM lineage
  -> READY_FOR_AUDIT
  -> existing TASK-038 AI/Human Audit and separate ACCEPT/LOCK
```

P-ORCH-1 stops at `READY_FOR_AUDIT`. It never records an Audit result, accepts
or locks a Candidate, publishes media, starts another Provider call, mutates an
NLE/DAW or widens paid/native authority.

## 4. Domain and persistence design

### 4.1 Exact adoption identity

Add a strict `GenerationOutputAdoption` transaction keyed deterministically by
the exact project, Queue entry, execution ID, Prompt ID/version, target Slot,
provider operation ID, output reference and output SHA-256. The transaction
stores no Prompt body, credential, absolute host path or media bytes.

State is append-only and limited to:

1. `PREPARED`;
2. `ASSET_REGISTERED`;
3. `CANDIDATE_REGISTERED`;
4. `ATTEMPT_BOUND`;
5. `READY_FOR_AUDIT`;
6. `FAILED_KNOWN`.

An unexpected interruption between side effects is `RECOVERY_REQUIRED`, never
automatic replay. Recovery re-reads each canonical store and permits only the
one exact missing suffix of the original transaction. A third-state identity
conflict has no automatic action.

### 4.2 Source and media proof

The launcher-private resolver converts only a current
`project-output://...` reference below the configured Product output root. It
rejects absolute/traversal/symlink paths, missing/non-regular files, extension
or media-kind mismatch and checksum drift. The existing TASK-003
`AssetIngestService` performs the canonical copy, media probe, checksum,
Source Manifest, SQLite record and Evidence write with a deterministic
idempotency key.

The generated Asset uses explicit Product-generation provenance containing
only execution/Queue/Prompt/provider operation identities and hashes. Rights
fields are conservative and cannot be promoted to publication-ready merely
because generation completed.

### 4.3 Candidate and Prompt Attempt

The Candidate ID is deterministic for the adoption identity. Registration
requires the exact current Slot, Scene, Queue entry and execution output hash;
it uses the newly ingested Asset ID/hash and exact generation job identity.

The PASS Attempt is recorded only after the Candidate exists. It binds the
same Prompt body hash, profile/version, provider/model, execution ID, output
Candidate and known cost/latency Evidence. The existing
`GenerationOutputProductionBinding` adds the Prompt -> Candidate dependency.
Exact duplicates are idempotent; any differing existing identity fails closed.

Finally, the Candidate advances only from `PROPOSED` to `READY_FOR_AUDIT`.
TASK-038 retains exclusive Human decision ownership. P-ORCH-1 never calls
`prepare_lock` or `apply_lock`.

### 4.4 Authority and UI

Preparation is read-only and returns a one-shot confirmation bound to the exact
execution, Queue, Production, Prompt and adoption snapshots. Apply consumes the
confirmation before revalidation. The Shell displays completed outputs eligible
for adoption, current transaction/recovery state and the resulting Candidate.

The action label is `検証して監査候補へ登録`; it must not say Publish,
Accept, Lock or Complete. Every result explicitly reports:

- `provider_execution_started=false` for the adoption action;
- `paid_execution_authorized=false`;
- `human_audit_required=true`;
- `candidate_accepted=false`;
- `candidate_locked=false`;
- `publication_started=false`;
- `resolve_mutation_started=false`.

## 5. Error, recovery and compatibility rules

- non-COMPLETED, uncertain `DISPATCHING`, failed or identity-drifted execution:
  not adoptable;
- Queue/Prompt/Profile/Slot or output bytes changed after prepare: confirmation
  consumed and rejected;
- Asset ingest known failure: `FAILED_KNOWN`, safe re-prepare only when no
  canonical Asset was created;
- Asset exists but Candidate is absent: exact recovery may continue from
  `ASSET_REGISTERED`;
- Candidate exists but Prompt Attempt/edge is absent: exact recovery may
  continue from `CANDIDATE_REGISTERED`;
- unknown mixed stores or different existing IDs/hashes: Human Gate;
- legacy Product Project with no adoption store: empty compatible state;
- unknown version, checksum failure, symlink or oversized store: fail closed;
- existing execution/Queue/Production/Prompt/Audit formats are unchanged.

## 6. Performance, observability and cost

Projection and recovery use indexed IDs and bounded recent rows; no unbounded
Asset or Attempt load is added to the Shell. Media bytes are streamed once by
the existing ingest path and never embedded in JSON. Evidence records phase,
exact hashes, elapsed time and whether recovery was used. Provider/cached/
output/billed token fields remain unavailable unless measured; they are not
invented. No paid Provider call or credit operation is in scope.

## 7. Exact proposed Allowed Files

- `src/ai_video_production/generation_output_adoption_application.py` (new)
- `src/ai_video_production/generation_output_adoption_store.py` (new if a
  separate strict store is required after implementation audit)
- `src/ai_video_production/schema_resources/generation-output-adoption.schema.json` (new)
- `schemas/generation-output-adoption.schema.json` (new)
- `src/ai_video_production/creative_generation_execution_application.py`
  only for a bounded exact completed-event accessor;
- `src/ai_video_production/production_control_application.py` only for exact
  idempotent Candidate registration needed by recovery;
- `src/ai_video_production/prompt_evidence_application.py` only for exact
  idempotent PASS Attempt/lineage application needed by recovery;
- `src/ai_video_production/generation_output_binding.py` only if current exact
  idempotency is insufficient;
- `src/ai_video_production/task036_shell_ui.py`;
- `src/ai_video_production/task036_trusted_launcher.py`;
- `src/ai_video_production/desktop_shell.py` only for new command categories;
- focused new TASK-027 tests and exact existing compatibility tests;
- TASK-027 Evidence plus `PROJECT.md`, `CHANGELOG.md`, current-state,
  project-summary, task-index and canonical roadmap.

SQLite/schema migration, package version, Release metadata, Provider adapter,
Credential vault, TASK-013 native workflow, Resolve/Cubase and Production Deploy
files are not allowed. A newly proven need outside this list returns to Builder
and Critic before editing.

## 8. Required tests and gates

- exact current completed execution is the only eligible source;
- containment/symlink/traversal/checksum/media-kind tests;
- deterministic idempotent Asset/Candidate/Attempt/edge identity;
- stale confirmation consumed before any adoption write;
- crash injection and restart recovery at every phase boundary;
- third-state/mixed-store conflict parks without automatic repair;
- Candidate ends only at `READY_FOR_AUDIT`;
- no automatic Audit/ACCEPT/LOCK/publish/Provider/NLE operation;
- Prompt bodies, credentials and host paths absent from snapshots/errors/UI;
- legacy no-store compatibility and strict unknown-version rejection;
- Shell command allowlist and accessible bounded UI tests;
- focused tests, required full Windows/WSL2 regression, compileall, JavaScript,
  schema, release-metadata and diff checks;
- implementation Critic unresolved Critical/High `0 / 0`;
- hosted `9 / 9`, exact main merge and cleanup before closure.

## 9. Implementation order

1. strict transaction model/store and compatibility/recovery tests;
2. exact execution/Queue/output resolver and canonical Asset-ingest port;
3. idempotent Candidate and Prompt Attempt/lineage adoption;
4. `READY_FOR_AUDIT` transition and bounded Shell integration;
5. failure injection, security, privacy and restart tests;
6. focused/full/static/native-packaged tests as applicable;
7. Evidence/current-state/roadmap synchronization;
8. PR, all hosted checks, exact main merge and branch/checkout cleanup;
9. fresh-main AUTONOMY reselection.

## 10. Release impact

This design and its first implementation checkpoint do not preselect a version.
A later release decision depends on actual user-facing completion and required
Native acceptance. Stable formal Release remains `v0.21.0`.
