# TASK-099 JCV-D — Project / Job Currentness V2 Contract R0

## 1. Decision and responsibility boundary

- Baseline is main/origin/main `e41110c85ba4ab098c591378cb1b2eaae3cc3cb7`; design branch input HEAD before this unit is `23810f071c05a72f5992e5bcf4d673ae64f1b8f2`.
- Profile is DEV-4. This is a design-only unit. It authorizes no Project write, filesystem/native operation, private-media access, model/audio action, release, deployment or Production effect.
- TASK-099 is the successor producer for `PROJECT_JOB_CURRENTNESS_READBACK_V2`. It selects one exact TASK-076 immutable Job event through one secure successor revision of the canonical Product Project manifest.
- TASK-076 owns Job semantic keys, reservations, immutable events, transitions, candidate readbacks and orphan preservation. TASK-068 owns accepted immutable publication/readback only and never selects a winner. TASK-072 owns native child containment. TASK-099 does not recreate any of those owners.
- The legacy `ProductProjectManifestStore`, `_exclusive_project_lock`, path-based `load/save` and `AtomicJsonWriter` are evidence and compatibility surfaces only. They are not a V2 secure backend and are not modified by JCV-I.
- There is one canonical Project manifest. TASK-099 does not create a parallel Project store, a scan-selected head, a mutable `jobs.json`, or an independent winner pointer.

## 2. Canonical selection representation

The existing Project manifest remains the sole winner-selection coordinate. A V2 successor manifest contains exactly one TASK-099 child binding for an immutable `PROJECT_JOB_CURRENTNESS_INDEX_V2` generation. The binding uses the existing Project child-binding mechanism but a newly reviewed TASK-099 format identity. It points to a unique immutable generation, never a constant mutable path.

The index is a strict private canonical record with:

- `contract_version=PROJECT_JOB_CURRENTNESS_INDEX_V2` and `record_type=ProjectJobCurrentnessIndexV2`;
- `project_id`, positive `index_revision`, nullable `predecessor_index_sha256` and exact predecessor Project manifest SHA-256;
- `namespace_plan_set_sha256`;
- `task076_profile_id`, `task076_profile_version`, `consumer_operation_id`, `install_build_binding_sha256`, `security_reader_binding_sha256`, `producer_issuer_binding_sha256` and `evidence_source`;
- a sorted array of at most 4096 `heads`, with unique `job_semantic_key_sha256` values;
- each head containing exact TASK-076 profile/version, event coordinate, event SHA-256, event physical-identity reference, nullable predecessor event coordinate/SHA-256/physical-identity reference and positive event sequence;
- `index_sha256`, domain-separated over canonical JSON without itself.

Index domain:

```text
sha256(b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-INDEX:V2\0" + canonical_json(body_without_index_sha256))
```

The generation is published no-replace and pinned before the manifest commit. If manifest commit never selects it, it is an orphan and is preserved. A Project manifest may contain zero TASK-099 binding only before V2 initialization. It must never contain multiple V2 bindings, a mutable fixed-path binding, an unrecognized version, or a binding whose exact bytes/hash/physical identity cannot be re-read. JCV-N must amend/validate the existing Product manifest integration rather than relaxing the current strict parser ad hoc.

For initialization, a V2-capable Project manifest may already have any positive Project revision but has no TASK-099 binding. That prior readback is `index_state=UNINITIALIZED`, with both index SHA-256 and index physical identity null. Its successor index is exactly revision 1 with null predecessor index SHA-256. If a selected V2 index exists, `index_state=PRESENT`; a missing semantic key may still produce `ABSENT_JOB_HEAD`, but the successor index revision is prior index revision +1 and its predecessor is the exact prior index SHA-256. `UNINITIALIZED` is never inferred from an I/O failure, malformed binding or missing target.

Live selection starts only from an already accepted V2-capable Project manifest format. Any migration from the legacy manifest format is a separately reviewed JCV-N predecessor operation and cannot be combined with a Job-head selection transaction. A selection successor preserves `project_format_id`, `project_format_version`, `project_id`, `created_at`, `product_version`, `timebase`, authority fields, secret/media flags and every unrelated child binding exactly. Its only permitted differences are revision +1, predecessor-manifest binding, a trusted updated timestamp and replacement/addition of the single TASK-099 index binding.

An index is not current merely because it exists or has the expected content hash. It is current only when the securely opened canonical manifest selects its exact unique child binding and every manifest/index physical identity is pinned and revalidated.

## 3. Closed readback contract

`ProjectJobCurrentnessReadbackV2` is a private, strict, deeply immutable record with exactly:

- `contract_version=PROJECT_JOB_CURRENTNESS_READBACK_V2`;
- `record_type=ProjectJobCurrentnessReadbackV2`;
- `project_id`;
- positive `manifest_revision`;
- `manifest_sha256`;
- nullable `predecessor_manifest_sha256`, null only for revision 1;
- `manifest_physical_identity_ref`;
- `project_root_identity_ref`;
- `job_semantic_key_sha256`;
- `head`, the closed union below;
- `namespace_plan_set_sha256`;
- `consumer_operation_id`;
- `install_build_binding_sha256`;
- `security_reader_binding_sha256`;
- `producer_issuer_binding_sha256`;
- `evidence_source=TRUSTED_BACKEND | FIXTURE_ONLY`;
- `currentness_capability=CURRENT | FIXTURE_ONLY`;
- `trusted_currentness_coordinate`;
- `readback_sha256`.

Readback domain:

```text
sha256(b"BAI:TASK-099:PROJECT-JOB-CURRENTNESS-READBACK:V2\0" + canonical_json(body_without_readback_sha256))
```

All SHA-256 values use `sha256:` plus 64 lowercase hex. Public/operation IDs are bounded ASCII opaque identifiers and reject path, drive and URI shapes. Physical identity references are opaque private trusted-port references; they are neither host paths nor caller-authenticated strings. No path, file body, Job body, media, text, secret, handle or OS identifier is admitted to a public projection.

### 3.1 Head union

`head` has exactly one of two variants.

`ABSENT_JOB_HEAD` contains:

- `variant=ABSENT_JOB_HEAD`;
- `index_state=UNINITIALIZED | PRESENT`;
- nullable `index_revision`, `index_sha256` and `index_physical_identity_ref`: all three null only for `UNINITIALIZED`; all three non-null and exact for `PRESENT`;
- `absence_proof_sha256` calculated by the trusted producer over the exact manifest revision/hash/physical identity, index bytes/hash/physical identity, semantic key and namespace plan-set digest.

`SELECTED_JOB_HEAD` contains:

- `variant=SELECTED_JOB_HEAD`;
- `index_state=PRESENT`, positive `index_revision`, exact selected `index_sha256` and `index_physical_identity_ref`;
- exact `event_coordinate` object: TASK-076 namespace/version, opaque operation ID, positive event sequence and coordinate SHA-256;
- exact `event_sha256` and `event_physical_identity_ref`;
- nullable `predecessor_event_coordinate`, `predecessor_event_sha256` and `predecessor_event_physical_identity_ref`, all null only for the first RESERVED event and otherwise all non-null;
- `selection_proof_sha256` over the same manifest/index binding plus the selected head.

Unknown, nullable or generic head variants are forbidden. `ABSENT_JOB_HEAD` means an authenticated absence in the complete bounded selected index, not a missing file, failed read, empty scan or caller assertion. `SELECTED_JOB_HEAD` is not satisfied by equal event IDs/hashes under a different physical identity.

### 3.2 Trusted currentness coordinate

`trusted_currentness_coordinate` separates committed state from observation freshness. It contains exactly `state` and `observation`.

`state` contains exactly:

- `authority_instance_id`, `epoch_id`, positive `manifest_generation_sequence`;
- `state_coordinate_sha256` under domain `BAI:TASK-099:PROJECT-CURRENTNESS-STATE-COORDINATE:V2\0`.

Its digest preimage is the exact three non-digest fields plus the readback's `project_id`, `project_root_identity_ref`, `manifest_revision`, `manifest_sha256` and `manifest_physical_identity_ref`. `manifest_generation_sequence` advances only on a committed canonical manifest successor and is stable across fresh observations of the same manifest.

`observation` contains exactly:

- positive `observation_sequence`;
- `observed_at`, `expires_at` using calendar-valid UTC seconds with optional 1–6 fractional digits and exact `Z`;
- `clock_binding_sha256` and `observation_sha256` under domain `BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2\0`.

`observation` binds the exact state-coordinate digest. `observed_at < expires_at`. Observation sequence may increase on a fresh re-read without creating a conflict; prior/reread comparison requires the same state coordinate while accepting a newer authenticated observation. Manifest commit creates state sequence +1 and a fresh observation. An epoch/authority change is not silently ordered against the old coordinate; it requires an authenticated backend `EPOCH_RECONCILIATION_REQUIRED` result and no selection write. A consumer must use trusted time and require `observed_at <= trusted_now < expires_at`; self-reported wall time is not authority.

`TRUSTED_BACKEND` requires an admitted producer issuer and may carry `CURRENT`. `FIXTURE_ONLY` requires `currentness_capability=FIXTURE_ONLY` and can never be consumed as live Product currentness. A fake port may exercise a structurally successful commit path, but its readback/result always stays fixture-only and `live_currentness_eligible=false`.

## 4. Candidate and transaction request

TASK-099 receives a strict body-free `ProjectJobHeadCandidateV2` from the trusted TASK-076/TASK-068 boundary. It contains:

- `candidate_contract_version=PROJECT_JOB_HEAD_CANDIDATE_V2`, `record_type=ProjectJobHeadCandidateV2`;
- `project_id`, `job_semantic_key_sha256`, `namespace_plan_set_sha256`;
- `task076_profile_id`, `task076_profile_version`, `task076_event_contract_version`;
- exact `event_coordinate`, `event_sha256`, `event_physical_identity_ref`;
- nullable `predecessor_event_coordinate`, `predecessor_event_sha256`, `predecessor_event_physical_identity_ref`, all null only for the first RESERVED candidate and otherwise all non-null;
- `event_kind`, positive `event_sequence` and `task076_candidate_readback_sha256`;
- `task068_plan_sha256`, `task068_publish_receipt_sha256`, `task068_pinned_readback_sha256`;
- `consumer_operation_id`, `install_build_binding_sha256`, `security_reader_binding_sha256`;
- `producer_issuer_binding_sha256`, `evidence_source=TRUSTED_BACKEND | FIXTURE_ONLY`, `observed_at`, `expires_at`;
- `candidate_sha256` under domain `BAI:TASK-099:PROJECT-JOB-HEAD-CANDIDATE:V2\0`.

This R0 adapter accepts only `task076_profile_id=DURABLE_PRODUCT_JOB_EVENT_V2`, `task076_profile_version=2.0.0` and `task076_event_contract_version=DURABLE_PRODUCT_JOB_EVENT_V2`. Its closed `event_kind` values are `RESERVED`, `PREPARED`, `READY`, `DISPATCHING`, `IN_FLIGHT`, `SUCCEEDED`, `FAILED_KNOWN`, `BURNED_UNKNOWN`, `CANCELLED_SAFE` and `HUMAN_REQUIRED`. TASK-099 validates these exact values and predecessor bindings; it does not independently decide whether a TASK-076 transition is semantically allowed. Any TASK-076 successor profile requires a reviewed TASK-099 version amendment.

`ProjectJobCurrentnessTransactionRequestV2` contains exactly:

- version/type, `transaction_id`, `project_id`, `job_semantic_key_sha256`;
- exact `prior_readback_sha256` and prior trusted-coordinate SHA-256;
- exact `candidate_sha256` and candidate readback SHA-256;
- exact `manifest_successor_proposal_sha256`;
- proposed positive successor manifest/index revisions and proposed immutable index SHA-256;
- `namespace_plan_set_sha256`, `consumer_operation_id`;
- `install_build_binding_sha256`, `security_reader_binding_sha256`;
- `requested_at`, `expires_at`, and `request_sha256` under domain `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-TRANSACTION-REQUEST:V2\0`.

The request is valid only when all duplicated Project/semantic/namespace/operation/build/security bindings are equal, the prior coordinate is current, the successor manifest revision is prior +1, the successor index follows the explicit UNINITIALIZED/PRESENT rule in section 2, and the proposed index is the deterministic full-snapshot replacement described below. A self-hash authenticates no producer; the trusted backend verifies receipt issuers, currentness and physical identities.

`ProjectManifestSuccessorProposalV2` is the exact Project delta proof consumed by the request. It contains exactly: version/type; Project ID and format ID/version; prior manifest revision/SHA-256/physical identity; successor revision, predecessor-manifest SHA-256, successor canonical manifest SHA-256 and trusted `updated_at`; separate `prior_project_invariant_fields_sha256` and `successor_project_invariant_fields_sha256`; separate `prior_unrelated_child_bindings_sha256` and `successor_unrelated_child_bindings_sha256`; nullable exact prior TASK-099 child binding; exact successor TASK-099 child binding; evidence source/producer issuer; and `proposal_sha256` under `BAI:TASK-099:PROJECT-MANIFEST-SUCCESSOR-PROPOSAL:V2\0`.

The invariant digest covers `project_id`, `created_at`, `product_version`, `timebase`, authority object, secret/media flags and every other non-updatable manifest field. The unrelated-child digest covers the sorted complete set after removing the sole TASK-099 binding. Each prior/successor pair is computed independently from authenticated canonical bytes and must be equal. The proposal binds the exact successor canonical bytes digest, not just a revision/index hash. The backend phase result returns both authenticated full-manifest byte digests and all four recomputed preservation digests; JCV-I compares them to the request before index publication or manifest commit.

`ProjectJobCurrentnessSnapshotV2`, returned by `open_prior` and `reread_under_lease`, contains exactly: the full strict readback; full parsed current index or authenticated `UNINITIALIZED`; exact canonical prior manifest bytes SHA-256 and physical identity; invariant/unrelated-child digests; sole TASK-099 binding state; producer issuer/evidence source; and snapshot SHA-256. JCV-I derives the successor index from this full snapshot. A digest-only, partial-head or caller-selected snapshot is rejected.

### 4.1 Head transition

- Prior `ABSENT_JOB_HEAD` accepts only the first TASK-076 `RESERVED` event with sequence 1 and null predecessor.
- Prior `SELECTED_JOB_HEAD` requires candidate sequence exactly prior +1 and candidate predecessor SHA-256 exactly the selected event SHA-256. The candidate's predecessor coordinate and physical-identity binding must also equal the selected predecessor readback supplied by TASK-076.
- The next index preserves every unrelated sorted head byte-for-byte and adds/replaces only the requested semantic key. Removing, reordering semantically unequal data, changing another key, duplicate keys or exceeding the bound rejects before commit.
- Candidate and index must bind the same Project, namespace plan-set, install/build/security reader and consumer operation.
- Candidate TASK-076 profile/version/event-contract version and every predecessor coordinate/hash/physical identity must equal the authenticated TASK-076 candidate readback; each field is compared independently, never represented only by a caller-provided aggregate hash.
- A terminal, equal-body or equal-hash event is not a duplicate success unless the canonical manifest already selects that exact event and the backend returns a fresh exact readback for the same operation recovery.

## 5. Pure JCV-I orchestration port

JCV-I may implement strict parsers, canonical hashes, deterministic transition/index compilation and a side-effect-injected orchestration state machine. It contains no `Path`, filesystem, OS lock, network, clock, process or native API. Tests use fake ports only.

The injected `ProjectJobCurrentnessBackendV2` exposes these logical phases:

1. `open_prior(request)` returns an authenticated, pinned prior Project/readback snapshot.
2. `pin_candidate(request, candidate)` returns exact TASK-076/TASK-068 candidate authentication and pinned physical identity.
3. `acquire_exclusive(request)` returns an opaque one-operation lease or a no-write blocked/conflict result.
4. `reread_under_lease(lease, request)` returns the exact current Project/readback; JCV-I compares every expected identity and coordinate.
5. `validate_successor_proposal(lease, request, compiled_index, proposal)` authenticates the exact proposed canonical successor manifest, independently recomputes all four prior/successor preservation digests and returns `PROPOSAL_ACCEPTED_NO_WRITE` or a no-write rejection. It performs no publication/commit.
6. `publish_index_generation(lease, compiled_index)` publishes/pins the exact immutable successor index, or returns no-write/block/unknown. Publication alone never selects currentness.
7. `commit_manifest_successor(lease, request, index_readback)` performs one predecessor CAS and durable commit classification.
8. `read_successor(lease, request)` reopens and authenticates the exact committed manifest/index/head and returns a fresh V2 readback.
9. `query_operation(transaction_id, request_sha256)` is the only recovery entry after uncertainty. It returns exact prior, exact intended successor, conflicting successor or unknown; it never retries a write by itself.
10. `release(lease)` releases only this operation's lease and never cleans an index/event/foreign path.

Every phase result is a strict tagged record with operation/request digest and `NO_WRITE_CONFIRMED`, `INDEX_ORPHAN_PRESERVED`, `MANIFEST_COMMIT_DURABLE` or `OUTCOME_UNKNOWN` classification as applicable. Generic exceptions cannot be translated to success. The pure orchestrator calls no later mutation phase after conflict, security stop or unknown outcome.

The common phase-result envelope has exactly: `phase_result_version=PROJECT_JOB_CURRENTNESS_PHASE_RESULT_V2`, `record_type`, closed `phase`, `transaction_id`, `request_sha256`, `backend_operation_witness_sha256`, `evidence_source`, `producer_issuer_binding_sha256`, `issuer_admission=ACCEPTED | NOT_ACCEPTED`, closed `phase_status`, `no_manifest_write_proven`, `manifest_commit_observation`, `reason_code`, one phase-specific `payload`, and `phase_result_sha256`. The digest domain is `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-PHASE-RESULT:V2\0`.

Phase payload is a closed union: OPEN/REREAD carries one full `ProjectJobCurrentnessSnapshotV2`; PIN_CANDIDATE carries the authenticated candidate and exact event/predecessor physical readbacks; ACQUIRE carries an opaque lease reference plus exact root/manifest/state-coordinate bindings; VALIDATE_PROPOSAL carries the exact proposal, authenticated proposed-manifest canonical SHA-256, all four independently recomputed preservation digests and `PROPOSAL_ACCEPTED_NO_WRITE | PROPOSAL_REJECTED_NO_WRITE`; PUBLISH_INDEX carries exact index SHA-256/physical readback and `PUBLISHED_ORPHAN_SAFE | NOT_PUBLISHED | UNKNOWN`; COMMIT carries prior/successor canonical manifest SHA-256, successor physical identity and `COMMITTED_DURABLE | NOT_COMMITTED_PROVEN | UNKNOWN`; READ_SUCCESSOR carries a fresh exact readback; QUERY_OPERATION carries the same-operation witness union defined in section 7; RELEASE carries only `RELEASED | RELEASE_WARNING`. Fields from another phase, null payloads outside their conditional variant, unknown issuer or `FIXTURE_ONLY` with `currentness_capability=CURRENT` are rejected.

Live `COMMITTED_WITH_READBACK` additionally requires every phase evidence source `TRUSTED_BACKEND`, the same accepted issuer binding and `currentness_capability=CURRENT`. A structurally successful fake-port flow returns fixture-only evidence and can be asserted as orchestration success in unit tests, but its Product/public live projection is always ineligible.

## 6. Transaction result

`ProjectJobCurrentnessTransactionResultV2` has one state:

- `COMMITTED_WITH_READBACK`: exact successor manifest commit is durable and the fresh readback selects the candidate.
- `CONFLICT_NO_WRITE`: authenticated re-read proves a different predecessor/head/currentness before this operation wrote the manifest.
- `BLOCKED_NO_WRITE`: validation/security/expiry/backend eligibility failure with explicit no-manifest-write proof.
- `COMMIT_OUTCOME_UNKNOWN`: the operation may have crossed the manifest commit seam or durable/readback status is not proven.

The strict result binds request/candidate/prior readback, nullable successor readback, outcome evidence SHA-256, evidence source/producer issuer/currentness capability, `live_currentness_eligible`, manifest observation `COMMITTED | NOT_COMMITTED | UNKNOWN`, index disposition `SELECTED | SUPERSEDED_PRESERVED | ORPHAN_PRESERVED | NOT_PUBLISHED | UNKNOWN`, ordered reason codes, and fixed authority flags:

- `retry_authorized=false`;
- `blind_replay_authorized=false`;
- `job_effect_authorized=false`;
- `cleanup_authorized=false`;
- `release_deploy_production_authorized=false`.

`COMMITTED_WITH_READBACK` requires successor readback present, manifest observation COMMITTED and index SELECTED. It is live-eligible only for admitted trusted-backend evidence; fixture success remains `live_currentness_eligible=false`. Conflict/blocked require successor null, manifest NOT_COMMITTED and an exact same-operation no-manifest-write proof. UNKNOWN requires no success projection and permits manifest observation COMMITTED or UNKNOWN, including a known earlier same-operation commit that is now superseded; any published index is preserved. UNKNOWN can never carry NOT_COMMITTED without the same-operation no-commit proof that would justify a no-write result. Result digest domain is `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-TRANSACTION-RESULT:V2\0`.

Public projection contains only Project ID, semantic-key digest, transaction/result state, evidence source, live-currentness eligibility, current head/event digests when confirmed, reason codes and result/readback digests. It excludes physical identity refs, operation internals, paths, lease, clock bodies and private Project structure. `COMMITTED_WITH_READBACK` means currentness selection only; it does not authorize TASK-076's next effect.

## 7. Commit and recovery algorithm

```text
strict-parse request/prior/candidate
→ authenticate and pin Project + candidate
→ validate current coordinate and transition
→ acquire exact one-operation exclusive lease
→ re-read/revalidate Project root, manifest bytes/identity, index and head
→ deterministically compile full successor index and exact Project successor
→ authenticate successor canonical bytes and validate the sole allowed manifest delta with no write
→ publish/pin immutable index generation (orphan-safe)
→ predecessor-CAS one canonical Project manifest successor
→ classify durable commit
→ reopen exact canonical manifest/index/head
→ issue fresh current readback
→ release lease
```

The backend must fail closed before every effect if the resolved destination is outside its exact authorized Project root, is a drive root/direct child, or has foreign/unknown ownership. JCV-N records resolved roots and residual index generations in Evidence.

Recovery uses the same `transaction_id` and `request_sha256` only. The backend maintains an operation-bound durable witness independent of the currently selected head. `query_operation` returns exactly one of:

- `SAME_OPERATION_COMMITTED_CURRENT`: durable same-operation commit witness plus the exact intended successor still current and freshly read back;
- `SAME_OPERATION_COMMITTED_SUPERSEDED`: durable same-operation commit witness plus a later authenticated canonical successor;
- `SAME_OPERATION_NOT_COMMITTED`: durable same-operation no-commit witness covering the commit seam;
- `SAME_OPERATION_UNKNOWN`: absent, ambiguous, physically unequal or incomplete history.

Only CURRENT returns `COMMITTED_WITH_READBACK`. COMMITTED_SUPERSEDED returns fail-closed `COMMIT_OUTCOME_UNKNOWN` with manifest observation COMMITTED, index `SUPERSEDED_PRESERVED` and reason `SAME_OPERATION_COMMIT_SUPERSEDED`; it never claims no-write. NOT_COMMITTED may return conflict/blocked only after a fresh authenticated readback determines the present cause. UNKNOWN stays UNKNOWN. Seeing a different current successor without the same-operation witness proves neither commit nor no-write. A new write always requires a newly compiled request under a fresh current readback; query never retries. No scan, mtime, filename, maximum revision, content equality or automatic replay chooses the answer.

## 8. Failure and crash matrix

| Seam | Result | Required preservation / prohibition |
|---|---|---|
| malformed, expired, wrong issuer/version/binding | BLOCKED_NO_WRITE | manifest/index/event delta zero |
| root/manifest/index link, reparse, hardlink, DACL or ancestor drift | BLOCKED_NO_WRITE security reason | no commit; preserve all |
| candidate missing/foreign/ambiguous or TASK-068 receipt mismatch | BLOCKED_NO_WRITE | no manifest/index mutation |
| stale prior, ABA coordinate, epoch change, equal hash different identity | CONFLICT_NO_WRITE | no manifest/index mutation |
| two writers with same prior | exactly one may COMMIT; other CONFLICT | loser never overwrites winner |
| crash before index publish | BLOCKED or UNKNOWN only with evidence | manifest unchanged |
| index publish succeeds, crash before manifest commit | COMMIT_OUTCOME_UNKNOWN | orphan index preserved; grants nothing |
| manifest CAS rejection | CONFLICT_NO_WRITE | orphan index preserved |
| replace/flush/directory-durability uncertainty | COMMIT_OUTCOME_UNKNOWN | no retry/cleanup; exact operation query only |
| durable manifest commit, response/readback loss | COMMIT_OUTCOME_UNKNOWN | recovery may prove exact successor; no blind replay |
| post-commit manifest/index/event physical replacement | COMMIT_OUTCOME_UNKNOWN only | never claim no-write; preserve and escalate |
| same operation committed, later writer advances current head | COMMIT_OUTCOME_UNKNOWN / COMMITTED+SUPERSEDED_PRESERVED | never downgrade the earlier operation to CONFLICT_NO_WRITE |
| successor readback mismatch or expired coordinate | COMMIT_OUTCOME_UNKNOWN | no downstream currentness projection |
| release failure after confirmed readback | committed result plus stable warning only if commit/readback remain exact | no cleanup or second commit |
| unrelated head changes in compiled index | BLOCKED_NO_WRITE | all prior canonical state preserved |
| orphan TASK-076 event | not selected | event preserved; TASK-076 cannot advance from it |

## 9. Security, parser and schema requirements

- Security JSON accepts UTF-8 bytes only and rejects BOM, duplicate keys at every depth, nonfinite numbers, unknown fields, invalid nulls, booleans as integers, trailing data and depth over 16. Index, snapshot and manifest-proposal records are individually 1..4,194,304 bytes. A phase-result envelope containing one of those large payloads is 1..4,718,592 bytes while the nested payload must also pass its own 4,194,304-byte limit. Every other TASK-099 top-level or nested record is 1..131,072 bytes.
- All returned records are deeply immutable and detached from caller input. Public constructors cannot bypass validation; typed inputs are revalidated at orchestration boundaries.
- JSON Schema draft 2020-12 is a byte-identical canonical/package mirror and an interchange check, not the sole security parser. Conditional variants and result-state fields are encoded with `oneOf`/`if`/`then` and negative fixtures.
- Timestamp grammar is calendar-valid without relying only on an optional format checker. `observed <= trusted_now < expires`; equality at expiry rejects.
- Public/operation/profile/epoch IDs are 1..128 ASCII characters matching `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. Physical/lease identity refs are 1..192 matching `^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$`. Both additionally reject slash, backslash, drive prefix, URI scheme and parent components. Arrays have their explicit design bounds; no unconstrained string exceeds 512 UTF-8 bytes.
- Canonical JSON is the repository `canonical_json_bytes`: UTF-8, keys sorted lexicographically, separators `,` and `:`, no whitespace/BOM/nonfinite number or alternate Unicode transformation. Every digest excludes only its own digest field and prepends the exact domain bytes shown in this design.
- Ordered reason codes are unique, maximum 24, and closed to: `MALFORMED_INPUT`, `EXPIRED_CURRENTNESS`, `FIXTURE_ONLY_EVIDENCE`, `PRODUCER_NOT_AUTHENTICATED`, `PROJECT_BINDING_MISMATCH`, `SEMANTIC_KEY_MISMATCH`, `NAMESPACE_MISMATCH`, `OPERATION_MISMATCH`, `BUILD_SECURITY_MISMATCH`, `CANDIDATE_PREDECESSOR_MISMATCH`, `STALE_PRIOR_READBACK`, `CURRENTNESS_EPOCH_CHANGED`, `PHYSICAL_IDENTITY_CHANGED`, `SECURITY_IDENTITY_DRIFT`, `INDEX_PROPOSAL_MISMATCH`, `MANIFEST_PROPOSAL_MISMATCH`, `CONCURRENT_SUCCESSOR`, `INDEX_PUBLISH_UNKNOWN`, `MANIFEST_COMMIT_UNKNOWN`, `SUCCESSOR_READBACK_FAILED`, `SAME_OPERATION_HISTORY_UNKNOWN`, `SAME_OPERATION_COMMIT_SUPERSEDED`, `BACKEND_BLOCKED`, `LEASE_RELEASE_WARNING`.

### 9.1 Frozen digest vector

The state-coordinate vector body is:

```json
{"authority_instance_id":"task099-fixture","epoch_id":"epoch-1","manifest_generation_sequence":1,"manifest_physical_identity_ref":"manifest-fixture","manifest_revision":3,"manifest_sha256":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","project_id":"project-fixture","project_root_identity_ref":"root-fixture"}
```

With domain `BAI:TASK-099:PROJECT-CURRENTNESS-STATE-COORDINATE:V2\0`, expected digest is `sha256:a61a3a828ae786bfaa42c62ebb1442fdb2c408d99d55555eab0c58f209ec9045`.

The observation vector body is:

```json
{"clock_binding_sha256":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","expires_at":"2026-09-27T00:05:00Z","observation_sequence":7,"observed_at":"2026-09-27T00:00:00Z","state_coordinate_sha256":"sha256:a61a3a828ae786bfaa42c62ebb1442fdb2c408d99d55555eab0c58f209ec9045"}
```

With domain `BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2\0`, expected digest is `sha256:99fa406c81dacccb2500a297bd6eda92713397f6ee4891feb5bde0a2fe4cdb05`.

### 9.2 Normative digest registry

Every domain suffix `\0` in this document means one byte `0x00`, never the two ASCII characters backslash and zero. The algorithm is always `sha256(ASCII(domain_without_suffix) + 0x00 + canonical_json(preimage))`.

For Index, Readback, Candidate, TransactionRequest, ManifestSuccessorProposal, Snapshot, PhaseResult and TransactionResult, the preimage is the exact closed record with only its own `*_sha256` field removed. Their domains are respectively:

- `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-INDEX:V2`
- `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-READBACK:V2`
- `BAI:TASK-099:PROJECT-JOB-HEAD-CANDIDATE:V2`
- `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-TRANSACTION-REQUEST:V2`
- `BAI:TASK-099:PROJECT-MANIFEST-SUCCESSOR-PROPOSAL:V2`
- `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-SNAPSHOT:V2`
- `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-PHASE-RESULT:V2`
- `BAI:TASK-099:PROJECT-JOB-CURRENTNESS-TRANSACTION-RESULT:V2`

The remaining derived digests use these exact preimages:

- Event coordinate, domain `BAI:TASK-099:TASK076-EVENT-COORDINATE:V2`: `{task076_namespace, task076_event_contract_version, operation_id, event_sequence}`.
- Project invariant, domain `BAI:TASK-099:PROJECT-MANIFEST-INVARIANTS:V2`: exactly `{project_format_id, project_format_version, project_id, created_at, product_version, timebase, authority, secrets_embedded, media_bytes_embedded}`. An unknown field/version rejects and requires a new reviewed contract version.
- Unrelated child bindings, domain `BAI:TASK-099:PROJECT-UNRELATED-CHILD-BINDINGS:V2`: the complete canonical array of existing Project child-binding objects after removing the sole TASK-099 currentness binding, sorted by the existing Product identity order.
- Absence proof, domain `BAI:TASK-099:ABSENT-JOB-HEAD-PROOF:V2`: `{project_id, project_root_identity_ref, manifest_revision, manifest_sha256, manifest_physical_identity_ref, index_state, index_revision, index_sha256, index_physical_identity_ref, job_semantic_key_sha256, namespace_plan_set_sha256, state_coordinate_sha256}` with the three index values null only for UNINITIALIZED.
- Selection proof, domain `BAI:TASK-099:SELECTED-JOB-HEAD-PROOF:V2`: the same manifest/index/Project/semantic/namespace/state-coordinate fields as absence plus `{event_coordinate, event_sha256, event_physical_identity_ref, predecessor_event_coordinate, predecessor_event_sha256, predecessor_event_physical_identity_ref}`.
- State coordinate, domain `BAI:TASK-099:PROJECT-CURRENTNESS-STATE-COORDINATE:V2`: the exact eight-field vector shape shown in §9.1.
- Observation, domain `BAI:TASK-099:PROJECT-CURRENTNESS-OBSERVATION:V2`: the exact five-field vector shape shown in §9.1.
- Backend operation witness, domain `BAI:TASK-099:BACKEND-OPERATION-WITNESS:V2`: `{transaction_id, request_sha256, producer_issuer_binding_sha256, evidence_source, witness_state, manifest_commit_observation, committed_manifest_revision, committed_manifest_sha256, committed_manifest_physical_identity_ref}`; the three committed fields are all non-null only for a committed witness and all null for NOT_COMMITTED/UNKNOWN.

No generic hash field may substitute for one of these typed digests. Each prior/successor invariant or unrelated-child digest is recomputed from its own exact canonical source before equality comparison.

Mandatory schema fixtures cover: UNINITIALIZED/PRESENT absence; selected first/later predecessor; TRUSTED/CURRENT and FIXTURE_ONLY pairings; all four result states; UNKNOWN with COMMITTED/superseded; no-write results without a no-commit witness; every phase payload used in the common envelope; invalid calendar/leap dates; field-by-field candidate/profile/predecessor/operation/build/security tampering; and the two frozen digests above.

## 10. Atomic units and exact allocation

### JCV-I — pure contracts and fake-port orchestration

After independent acceptance of this design and fresh main/ID audit, JCV-I may modify exactly:

1. `src/ai_video_production/task099_project_job_currentness.py`
2. `schemas/task099-project-job-currentness.schema.json`
3. `src/ai_video_production/schema_resources/task099-project-job-currentness.schema.json`
4. `tests/test_task099_project_job_currentness.py`
5. `docs/ai-team/tasks/TASK-099/task.md` only as completion Evidence/status carrier

No existing Product manifest/store/TASK-068/TASK-076 source changes. Tests use deterministic fake ports and system temporary directories only when pytest owns them; the pure implementation itself writes nothing.

JCV-I acceptance covers strict parse/hash/schema, both head variants, deterministic index replacement, absence proof, first/later transition, stale/cross-Project/issuer/version/operation/namespace/currentness negatives, constructor bypass, two-writer fake-port serialization, all crash seams, UNKNOWN recovery, public redaction, fixed false authorities, schema mirror and direct Project-contract regression. Independent Tester/Critic/Judge and final C/H zero are mandatory.

### JCV-N — secure native backend

JCV-N is separately authorized only after TASK-068 transaction prerequisites and an exact backend design/review. It owns physical handles, Project manifest format migration/extension, secure lock/lease, no-replace index generation, predecessor CAS, durable replacement/readback, trusted clock/coordinate and Windows native race/fault tests. It must use a dedicated worktree or OS unique temp root and the canonical external Evidence root; no direct drive-root child. JCV-I acceptance does not authorize JCV-N.

### JCV-C — consumers

TASK-076/074/072 consumers receive an exact accepted version amendment and reject V1/legacy/hash-only aliases. They use only fresh readbacks and retain their own authority. No canonical owner transfer occurs.

## 11. Exit and non-goals

JCV-D exits when this contract receives independent DEV-4 Critic/Tester/Judge acceptance and the exact JCV-I scope is bound. JCV-I completion is pure/fake-port only. TASK-099 as a whole remains incomplete until JCV-N and JCV-C native/consumer evidence are confirmed and canonical integration is merged/read back.

Forbidden in this design/unit: native Project writes, legacy manifest repair, deleting orphan index/events, inferring latest by scan, modifying TASK-043 history, model/audio/private-media work, inference/playback/training, canonical Asset adoption, Release, Deploy or Production.
