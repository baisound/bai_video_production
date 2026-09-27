# TASK-102 PMST-D1 — Protocol, Journal and Migration Contract R0

Status: `DESIGN_R1 / DEV4_REREVIEW_REQUIRED / PURE_PROTOCOL_ONLY`

## 1. Decision

TASK-102 uses a **broker-owned generic transaction journal plus versioned participant protocol**. It does not move caller domain state machines into the service and does not keep the legacy interactive-user `save-journal.json` active beside a new witness. For an enrolled Project, the service owns all mutation beneath `.bai-project`; caller adapters prepare/verify domain objects through closed profiles and return bounded participant receipts. The service alone persists the transaction journal, terminal witness and protected objects.

The journal coordinates a transaction; it is not the Project selector. `.bai-project/project.json` remains the sole canonical Project head. Terminal witnesses are operation evidence and cannot choose currentness. TASK-043 parsers remain canonical for Project manifests. Every non-manifest object's semantic owner remains unchanged.

This design creates no source, runtime or native authority. All records are proposed pure contracts until a separately reviewed schema/source unit implements them.

## 2. Private IPC envelope

The client first constructs `PMST_OPERATION_INTENT_V1` with exactly `protocol_version`, `record_type`, `project_registration_id`, `operation_id`, `operation_kind`, `operation_profile_id`, `caller_task_id`, `caller_build_sha256`, `caller_policy_sha256`, `requested_at`, `expires_at`, one typed `payload`, and `intent_sha256`. The intent digest is `sha256(b"BAI:TASK-102:PMST-OPERATION-INTENT:V1\0" + canonical_json(intent_without_intent_sha256))`.

Only after mutual process admission does the broker mint a nonce bound internally to `intent_sha256`, both pinned process-instance identities, broker instance, session and registration. The client then sends `PMST_PRIVATE_REQUEST_V1` with exactly `protocol_version`, `record_type`, `broker_instance_id`, `session_id`, `request_nonce_id`, `intent`, and `request_sha256`. The request digest is `sha256(b"BAI:TASK-102:PMST-PRIVATE-REQUEST:V1\0" + canonical_json(request_without_request_sha256))`. This order removes nonce/request self-reference.

Every reply uses `PMST_PRIVATE_PHASE_RESULT_V1` with exactly `protocol_version`, `record_type`, `broker_instance_id`, `session_id`, `project_registration_id`, `operation_id`, `operation_kind`, `operation_profile_id`, `intent_sha256`, `request_sha256`, `phase`, `phase_status`, `manifest_commit_observation`, `effect_count`, `reason_code`, one typed `payload`, and `phase_result_sha256`. Its digest is `sha256(b"BAI:TASK-102:PMST-PRIVATE-PHASE-RESULT:V1\0" + canonical_json(result_without_phase_result_sha256))`.

The intent payload is a closed union:

| Operation kind | Exact payload fields |
|---|---|
| `MANIFEST_CREATE_V1` | `successor_manifest`, `successor_manifest_sha256`, `semantic_authorization_sha256` |
| `MANIFEST_TRANSITION_V1` | `prior_manifest_sha256`, `prior_manifest_physical_identity_ref`, `successor_manifest`, `successor_manifest_sha256`, `participant_plan_sha256`, `semantic_authorization_sha256` |
| `CONTROL_OBJECT_CAS_V1` | `predecessor_sha256`, `predecessor_physical_identity_ref`, `successor_document`, `successor_sha256`, `semantic_authorization_sha256` |
| `CONTROL_APPEND_CHAIN_V1` | `prior_terminal_revision`, `prior_terminal_sha256`, `successor_document`, `successor_sha256`, `semantic_authorization_sha256` |
| `CONTROL_RECOVERY_OBJECT_V1` | `recovery_action`, `predecessor_sha256`, `successor_document`, `successor_sha256`, `terminal_proof_sha256`, `semantic_authorization_sha256` |
| `CONTROL_SNAPSHOT_SET_V1` | ordered `create_set`, `retain_set`, `remove_set`, `retention_policy_sha256`, `semantic_authorization_sha256` |
| `PROJECT_READ_LEASE_V1` | `expected_manifest_sha256`, `expected_state_coordinate_sha256`, `observation_profile_id` |
| `QUERY_OPERATION_V1` | `queried_operation_id`, `queried_intent_sha256`, `queried_request_sha256` |

Nullable values are permitted only where a fixed profile explicitly represents absence. Successor documents are parsed canonical JSON objects under that profile, never arbitrary byte strings.

The phase/result union is exact:

| Phase | Allowed status | Exact payload fields |
|---|---|---|
| `ADMIT` | `ACCEPTED_NO_EFFECT`, `REJECTED_NO_EFFECT` | `admission_binding_sha256` or `rejection_class` |
| `OPEN` | `CURRENT_NO_EFFECT`, `BLOCKED_NO_EFFECT` | `manifest_sha256`, `manifest_physical_identity_ref`, `state_coordinate_sha256`, `security_binding_sha256` or `rejection_class` |
| `PREPARE` | `PREPARED`, `BLOCKED_NO_EFFECT` | `journal_sha256`, `intent_witness_sha256` or `rejection_class` |
| `PARTICIPANTS` | `PARTICIPANTS_PREPARED`, `PARTICIPANT_BLOCKED` | ordered `participant_receipt_sha256s` or `rejection_class` |
| `STAGE` | `OBJECTS_STAGED`, `STAGE_BLOCKED` | ordered `staged_identity_sha256s` or `rejection_class` |
| `COMMIT_OBJECTS` | `OBJECTS_COMMITTED`, `OBJECT_OUTCOME_UNKNOWN` | ordered `object_receipt_sha256s` |
| `COMMIT_MANIFEST` | `MANIFEST_COMMITTED`, `MANIFEST_NOT_COMMITTED`, `MANIFEST_OUTCOME_UNKNOWN` | `prior_manifest_sha256`, `successor_manifest_sha256`, `successor_physical_identity_ref`, `operation_witness_sha256` |
| `RECONCILE` | `RECONCILED`, `RECONCILIATION_REQUIRED` | ordered `participant_terminal_receipt_sha256s` |
| `TERMINAL` | `COMMITTED_WITH_READBACK`, `NOT_COMMITTED_PROVEN`, `BLOCKED_AFTER_PREPARE`, `COMMIT_OUTCOME_UNKNOWN` | non-null `operation_witness_sha256`, nullable `fresh_readback_sha256`, `admission_barrier_state` |
| `READ` | `READ_CURRENT_NO_EFFECT` | `manifest_sha256`, `state_coordinate_sha256`, `readback_sha256` |
| `READ` | `READ_BLOCKED_NO_EFFECT` | `read_failure_class`, `failure_observation_sha256` |
| `QUERY` | `COMMITTED_CURRENT`, `COMMITTED_SUPERSEDED`, `NOT_COMMITTED`, `UNKNOWN_WITH_WITNESS` | non-null `operation_witness_sha256`, nullable `fresh_readback_sha256` |
| `QUERY` | `WITNESS_NOT_FOUND_NO_EFFECT` | `queried_operation_id`, `queried_intent_sha256`, `absence_observation_sha256` |
| `QUERY` | `WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT` | `queried_operation_id`, `queried_intent_sha256`, `evidence_failure_class`, `failure_observation_sha256` |
| `QUERY` | `READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS` | `queried_operation_id`, `queried_intent_sha256`, non-null `operation_witness_sha256`, `evidence_failure_class`, `failure_observation_sha256` |
| `RELEASE` | `RELEASED`, `RELEASE_WARNING` | `release_warning_code` |

Fields from another payload variant, unknown phase/status, impossible status/manifest-observation pairs and undeclared nulls are rejected.

`manifest_commit_observation` is exactly `NOT_OBSERVED` through ADMIT/OPEN/PREPARE/PARTICIPANTS/STAGE/COMMIT_OBJECTS and for READ. At COMMIT_MANIFEST it maps one-to-one to `COMMITTED`, `NOT_COMMITTED` or `UNKNOWN`. RECONCILE/TERMINAL/QUERY preserve the proven witness observation; witness-not-found QUERY uses `NOT_OBSERVED`. RELEASE preserves the immediately preceding value. No phase may infer `NOT_COMMITTED` merely from missing evidence.

JSON is UTF-8 only, duplicate-key rejecting at every depth, bounded to 4 MiB for a manifest/object body envelope and 128 KiB otherwise, depth at most 16, no BOM/trailing data/nonfinite number/boolean-as-integer/unknown field. IDs are bounded ASCII and never paths. Digests use `sha256:` plus 64 lowercase hex. Timestamps are calendar-valid UTC `Z`; broker trusted time decides expiry.

Public projection is `PMST_PUBLIC_OPERATION_STATUS_V1` with exactly `record_type`, `protocol_version`, `operation_id`, `operation_kind`, `operation_profile_id`, `intent_sha256`, `request_sha256`, `status`, ordered `reason_codes`, `operation_witness_sha256`, `readback_sha256`, `retry_allowed=false`, `human_recovery_required`, `effect_count`, and `public_status_sha256`. Its digest domain is `BAI:TASK-102:PMST-PUBLIC-OPERATION-STATUS:V1\0`. The exact top-level/public status and nullability mapping is frozen in Section 8; no phase payload may create another combination. The projection contains no path, bytes, SID, ACL, handle, PID, process image, private identity reference, nonce, journal body or OS message.

## 3. Session and capability admission

Before parsing an operation body, both ends pin the other process instance and verify configured service SID, service/client image signature and digest, protocol/build/security-reader binding, logon/session policy and broker instance. The service issues the connection-local nonce only after validating the intent and binds it to `intent_sha256`, both pinned process instances, registration, operation/profile, broker instance and session. It is atomically consumed before the first filesystem callback and cannot be used on another connection, process, broker restart or operation.

Pipe names, server instance creation and security descriptors are fixed by installation configuration. First-instance protection and server-PID verification are mandatory. Same-user token or executable path alone is not admission. Arbitrary same-user peers, pipe squatters, PID reuse, early/copied/replayed nonce and stale broker instances fail with zero filesystem effects. Injection into an already admitted worker, administrator/backup privilege and kernel compromise are outside the live guarantee and force session invalidation/recovery.

## 4. Closed operation profiles

The broker compiles a registry of immutable operation profiles. A request supplies only `operation_profile_id`; the profile supplies the exact broker-derived target, parser/validator identity, maximum size/count, allowed predecessor/successor relation, durability class, semantic owner and permitted phases. No request carries a relative/absolute path, arbitrary validator, generic bytes sink, delete/rename target or reusable directory handle.

Closed operation kinds are:

1. `MANIFEST_CREATE_V1` — exact absent-to-revision-1 canonical Project creation.
2. `MANIFEST_TRANSITION_V1` — exact physical predecessor to revision+1 successor with invariant Project identity.
3. `CONTROL_OBJECT_CAS_V1` — one fixed singleton control object with exact predecessor digest/identity and owner parser/transition validator.
4. `CONTROL_APPEND_CHAIN_V1` — fixed append-only object whose next record binds prior terminal digest/revision.
5. `CONTROL_RECOVERY_OBJECT_V1` — owner-specific create/update/remove state machine; remove is permitted only in a terminal owner transition proved by the profile.
6. `CONTROL_SNAPSHOT_SET_V1` — bounded dynamic children derived only from broker operation digest and owner profile; create-new, fixed retention plan, no caller-selected deletion.
7. `PROJECT_READ_LEASE_V1` — no write; returns pinned manifest/control observations and replaces user-created lock files for read-integrity operations.
8. `QUERY_OPERATION_V1` — reads exact durable witness only; never retries or changes state.

Dynamic autosave/backup identifiers are broker-derived from accepted manifest/operation digests. Rotation is an explicit bounded ordered set in the request commitment and can remove only identities created and revalidated under the same owner profile. Unknown/foreign entries make rotation `UNKNOWN_QUARANTINED`; there is no recursive cleanup.

`PMST_ENROLLMENT_V1` has exactly `record_type`, `protocol_version`, `project_registration_id`, `project_id`, `root_physical_identity_ref`, `control_physical_identity_ref`, `manifest_physical_identity_ref`, `volume_binding_sha256`, `owner_dacl_binding_sha256`, `writer_migration_matrix_sha256`, `broker_install_binding_sha256`, `enrollment_epoch`, `created_at`, `status`, and `enrollment_sha256`. `status` is `PREPARED | ACTIVE | SUSPENDED | REVOKED`; only ACTIVE admits operations. Its digest domain is `BAI:TASK-102:PMST-ENROLLMENT:V1\0`. Enrollment carries no host path and cannot be created or repaired by an ordinary operation request.

## 5. Broker-owned journal and participant protocol

The service stores one create-new `PMST_TRANSACTION_JOURNAL_V1` per operation below its protected transaction namespace. It has exactly `record_type`, `protocol_version`, `project_registration_id`, `operation_id`, `operation_kind`, `operation_profile_id`, `intent_sha256`, `request_sha256`, `caller_task_id`, `caller_build_sha256`, `caller_policy_sha256`, `prior_observation_sha256`, `intended_successor_set_sha256`, `participant_plan_sha256s`, `broker_instance_id`, `enrollment_epoch`, `expires_at`, `phase`, `phase_sequence`, `phase_evidence_sha256s`, `journal_sha256`. Its digest domain is `BAI:TASK-102:PMST-TRANSACTION-JOURNAL:V1\0`. Its monotonic phase is one of:

```text
PREPARED
PARTICIPANTS_PREPARED
OBJECTS_STAGED
OBJECTS_COMMITTED
MANIFEST_COMMITTING
MANIFEST_COMMITTED
PARTICIPANTS_RECONCILED
TERMINAL
UNKNOWN_QUARANTINED
```

Each transition is same-operation CAS, durably flushed and exactly read back. Regression, skip, duplicate with different bytes, unknown phase or foreign physical identity quarantines the root.

`PMST_PARTICIPANT_PLAN_V1` has exactly `record_type`, `protocol_version`, `operation_id`, `participant_id`, `participant_profile_id`, `semantic_owner_task_id`, ordered `object_commitments`, `prepare_supported`, `commit_supported`, `reconcile_supported`, `abort_before_commit_supported`, and `plan_sha256`, under domain `BAI:TASK-102:PMST-PARTICIPANT-PLAN:V1\0`.

`PMST_PARTICIPANT_RECEIPT_V1` has exactly `record_type`, `protocol_version`, `operation_id`, `participant_id`, `plan_sha256`, `participant_phase`, `participant_status`, ordered `object_observations`, `effect_observation`, `receipt_sequence`, and `receipt_sha256`, under domain `BAI:TASK-102:PMST-PARTICIPANT-RECEIPT:V1\0`. Its allowed `(participant_phase, participant_status, effect_observation)` tuples are exactly the following rows; independently choosing values from columns is forbidden:

| Participant phase | Participant status | Effect observation |
|---|---|---|
| `PREPARE` | `PREPARED_NO_COMMIT` | `NO_EFFECT` |
| `PREPARE` | `PREPARE_BLOCKED_NO_EFFECT` | `NO_EFFECT` |
| `PREPARE` | `PREPARE_OUTCOME_UNKNOWN` | `UNKNOWN` |
| `COMMIT` | `OBJECTS_COMMITTED` | `COMMITTED` |
| `COMMIT` | `OBJECTS_NOT_COMMITTED_PROVEN` | `NOT_COMMITTED` |
| `COMMIT` | `OBJECT_COMMIT_OUTCOME_UNKNOWN` | `UNKNOWN` |
| `RECONCILE` | `RECONCILED_COMMITTED` | `COMMITTED` |
| `RECONCILE` | `RECONCILED_NOT_COMMITTED` | `NOT_COMMITTED` |
| `RECONCILE` | `RECONCILIATION_REQUIRED_COMMITTED` | `COMMITTED` |
| `RECONCILE` | `RECONCILIATION_REQUIRED_NOT_COMMITTED` | `NOT_COMMITTED` |
| `RECONCILE` | `RECONCILIATION_REQUIRED_UNKNOWN` | `UNKNOWN` |
| `ABORT` | `ABORTED_OWNED_PREPARE` | `NOT_COMMITTED` |
| `ABORT` | `ABORT_NOT_PROVEN` | `UNKNOWN` |

RECONCILE must preserve the most recent proven COMMIT/terminal effect: a known `COMMITTED` or `NOT_COMMITTED` observation cannot change or become `UNKNOWN`. `RECONCILIATION_REQUIRED_UNKNOWN` is valid only when the preceding participant outcome is already unknown; it keeps `admission_barrier_state=CLOSED` and can never be followed by a `RECONCILED_*` receipt until recovery proves one exact known outcome. Every tuple not listed above, including `RECONCILED_* / UNKNOWN`, is rejected before state transition.

A participant cannot claim manifest commit; only the service witness can. Neither record carries a path or reusable capability.

For existing coordinated save semantics:

1. broker authenticates and pins the exact current manifest/control state;
2. broker writes PREPARED journal plus an intent witness that binds only facts already known: intent/request/profile, exact prior observations, intended successor/object commitments and participant-plan digests;
3. admitted owner adapters prepare bounded external child changes; the broker appends their exact prepare receipts and advances `PARTICIPANTS_PREPARED`;
4. service stages protected-control objects itself, observes their new stage identities, appends those observations and advances `OBJECTS_STAGED`;
5. owner adapters commit external child objects under operation-bound capabilities, then the service commits its staged protected objects, reopens all of them, appends exact commit receipts/physical identities and advances `OBJECTS_COMMITTED`;
6. service revalidates all committed participant/object receipts, protected identities and exact predecessor exclusion, then advances `MANIFEST_COMMITTING`;
7. service performs the one manifest namespace effect, fresh exact readback, and advances `MANIFEST_COMMITTED`; it durably terminalizes the manifest outcome witness immediately, but the root admission barrier remains closed;
8. participant reconciliation completes and advances `PARTICIPANTS_RECONCILED`; warning/failure cannot erase the manifest outcome;
9. service advances the journal to `TERMINAL`, records `admission_barrier_state=OPEN`, and only then admits a later manifest transaction.

`PROJECT_READ_LEASE_V1` follows only `ADMIT -> OPEN -> READ -> RELEASE` and performs zero writes or witness creation. `QUERY_OPERATION_V1` follows `ADMIT -> QUERY -> RELEASE` and performs zero writes; `WITNESS_NOT_FOUND_NO_EFFECT` carries an authenticated absence observation, not a fabricated witness. A read failure carries no readback. A query witness lookup that cannot prove either a valid witness or authenticated absence uses `WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT`; a valid witness followed by failed/corrupt current-state readback uses `READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS`. Neither failure variant claims absence, currentness or mutation authority. `REJECTED_NO_EFFECT` at ADMIT and `BLOCKED_NO_EFFECT` at OPEN end directly at RELEASE and never enter PREPARE/TERMINAL. A non-manifest control-object operation follows `ADMIT -> OPEN -> PREPARE -> STAGE -> COMMIT_OBJECTS -> TERMINAL -> RELEASE`; it never enters manifest or participant phases unless its fixed profile declares a participant.

If failure occurs before manifest effect, rollback/abort is allowed only where every owner profile proves exact same-operation ownership and unchanged physical identity. After manifest commit, rollback of the canonical head is forbidden; recovery completes/reconciles forward. A terminal commit witness is queryable even while reconciliation is pending, but the root admission barrier stays closed. Ambiguous participant/object/manifest effect, unresolved reconciliation or nonterminal journal becomes UNKNOWN/recovery-required and blocks later manifest writes. No automatic deletion or reset occurs.

The legacy `.bai-project/save-journal.json` is accepted only for **pre-enrollment migration inspection**. Enrollment requires it absent or terminal and exactly reconciled. It is never written after enrollment and is not copied into the new journal as authority.

## 6. Witness and restart recovery

Before any protected or manifest effect, the service writes `PMST_OPERATION_WITNESS_V1` in `PREPARED`. It has exactly `record_type`, `protocol_version`, `project_registration_id`, `operation_id`, `operation_kind`, `operation_profile_id`, `intent_sha256`, `request_sha256`, `prior_observation_sha256`, `intended_successor_set_sha256`, `participant_plan_sha256s`, ordered `observed_participant_receipt_sha256s`, ordered `observed_object_identity_sha256s`, `journal_sha256`, `broker_instance_id`, `enrollment_epoch`, `witness_state`, `manifest_commit_observation`, `committed_manifest_sha256`, `committed_manifest_physical_identity_ref`, `created_at`, `terminalized_at`, and `witness_sha256`, under domain `BAI:TASK-102:PMST-OPERATION-WITNESS:V1\0`. At PREPARED, observed receipt/identity arrays are empty and committed fields are null. Later observations are appended through journal-bound monotonic witness revisions; no future observation is claimed in the pre-effect record.

Terminal witness state is exactly `COMMITTED_DURABLE`, `NOT_COMMITTED_PROVEN` or `UNKNOWN_QUARANTINED`. A committed witness is durable before participant reconciliation, but a later manifest transaction requires both a terminal witness and a TERMINAL journal with every required participant reconciled or independently proved safe. On restart, the service admits no mutating client for the root until it reacquires barriers and reconciles all nonterminal journals/witnesses. Exact successor current proves commit; exact predecessor proves no-commit only with independent continuous commit-seam exclusion; anything else is UNKNOWN. Terminal knowledge is monotonic and queryable after a later successor.

Non-manifest protected-object operations receive separate witnesses and coordinates. They do not advance Project revision or reuse the manifest witness. Serialization policy is profile-defined: an object operation that can invalidate a manifest-bound child cannot overlap a manifest transaction selecting it.

## 7. Migration matrix contract

The companion JSON is the complete D1 design inventory at bound source HEAD `2051f002f9f7d5c71e9cd0d237934ba07a2740d2`. Every route has a stable ID, source symbols, physical target class, mutation/lock type, semantic owner, proposed profile/disposition and enrollment condition.

D1 acceptance requires:

- every current source hit from `.bai-project`, `_manifest_path(...).with_name`, `ProductProjectManifestStore.path(...).with_name`, `_exclusive_project_lock`, control-directory helpers and sibling lock helpers maps to at least one route;
- every manifest semantic caller maps to the central manifest/coordinator route;
- no `UNKNOWN` disposition;
- old binary/plugin/CLI routes are explicitly blocked, not assumed absent;
- source-policy tests are specified to reject future unregistered physical mutation imports/calls;
- owner-specific schema/transition details remain later owner-adapter work, not invented by TASK-102.

Proposed source-policy test inputs are Python AST plus bounded literal/symbol scanning. False negatives fail the check; suppression requires an exact route ID and reviewed reason. Generated/build/vendor trees are excluded; Product `src/ai_video_production` entrypoints are not.

## 8. Failure and result contract

The top-level result is closed and maps one-to-one to `PMST_PUBLIC_OPERATION_STATUS_V1.status`. No unlisted status or nullability combination is valid:

| Top-level/public status | Witness | Readback | Effect count | Human recovery |
|---|---|---|---:|---|
| `COMMITTED_WITH_READBACK` | non-null | non-null | broker-observed positive | false unless reconciliation warning |
| `NOT_COMMITTED_PROVEN` | non-null | nullable | broker-observed | false unless reconciliation warning |
| `BLOCKED_NO_WRITE` | null | null | `0` | false |
| `COMMIT_OUTCOME_UNKNOWN` | non-null | nullable | broker-observed | true |
| `READ_CURRENT_NO_EFFECT` | null | non-null | `0` | false |
| `READ_BLOCKED_NO_EFFECT` | null | null | `0` | false |
| `QUERY_COMMITTED_CURRENT` | non-null | non-null | `0` | false |
| `QUERY_COMMITTED_SUPERSEDED` | non-null | non-null | `0` | false |
| `QUERY_NOT_COMMITTED` | non-null | non-null | `0` | false |
| `QUERY_UNKNOWN_WITH_WITNESS` | non-null | non-null | `0` | true |
| `QUERY_WITNESS_NOT_FOUND_NO_EFFECT` | null | null | `0` | false |
| `QUERY_WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT` | null | null | `0` | true |
| `QUERY_READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS` | non-null | null | `0` | true |

For QUERY, phase statuses `COMMITTED_CURRENT`, `COMMITTED_SUPERSEDED`, `NOT_COMMITTED`, `UNKNOWN_WITH_WITNESS`, `WITNESS_NOT_FOUND_NO_EFFECT`, `WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT`, and `READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS` map respectively to the seven `QUERY_*` top-level/public statuses above. `read_failure_class` and `evidence_failure_class` are closed enums: `IO_FAILURE`, `CORRUPT_RECORD`, `DIGEST_MISMATCH`, `AUTHENTICITY_UNPROVEN`, `SECURITY_BINDING_DRIFT`, or `AMBIGUOUS_DUPLICATE`. `failure_observation_sha256` authenticates only the attempted bound operation and stable failure class; it is not a witness, readback or absence proof. UNKNOWN/evidence-unavailable results never authorize replay. `effect_count` is broker-observed and cannot be caller supplied. Stable reasons include admission/profile/predecessor/identity/security/expiry/participant/durability/witness/quarantine classes; raw OS details remain private and are cleared before projection.

| Failure/cut | Required state/result | Later admission |
|---|---|---|
| admission/open rejection before PREPARED | `BLOCKED_NO_WRITE`, effect 0 | allowed after fresh request |
| PREPARED lost response, no later evidence | query exact witness/journal; otherwise UNKNOWN | blocked until reconciled |
| participant prepare blocked with no effect | abort only exact prepared participants, `NOT_COMMITTED_PROVEN` | after terminal journal |
| protected stage failure | preserve owned stages and record identity; no manifest effect | blocked until exact abort/recovery |
| external or protected object commit ambiguous | `COMMIT_OUTCOME_UNKNOWN` | blocked/quarantined |
| objects committed, before manifest effect | exact recovery may continue or prove no-commit; no blind new request | blocked |
| exception during manifest effect | query exact manifest/witness, UNKNOWN until proved | blocked |
| successor manifest exact and durable | witness `COMMITTED_DURABLE`; reconcile forward | blocked until journal TERMINAL |
| predecessor exact with continuous exclusion | witness `NOT_COMMITTED_PROVEN`; exact abort/recovery | blocked until journal TERMINAL |
| missing/other manifest or security drift | `UNKNOWN_QUARANTINED` | blocked for Human recovery |
| participant reconcile warning after known commit | preserve commit plus `RECONCILIATION_REQUIRED` | blocked until proved safe |
| release warning after TERMINAL | preserve determined result plus warning | later admission allowed only if barrier OPEN |
| read failure before authenticated readback | `READ_BLOCKED_NO_EFFECT`, witness/readback null, effect 0 | no mutation authority created |
| query witness lookup I/O/corrupt/ambiguous | `QUERY_WITNESS_EVIDENCE_UNAVAILABLE_NO_EFFECT`, witness/readback null, effect 0 | no mutation authority created; recovery required |
| query has valid witness but current readback fails | `QUERY_READBACK_EVIDENCE_UNAVAILABLE_WITH_WITNESS`, witness non-null/readback null, effect 0 | no mutation authority created; recovery required |

Known commit is never downgraded. Release/reconcile warnings attach to the determined result without changing it. Retry is false for every returned operation; a new write requires a new request compiled from a fresh authenticated readback. Query is read-only.

## 9. D1 exit and later gates

D1 is design-complete only after the exact3 documents pass JSON/count/reference checks and independent DEV-4 Critic/Tester/Judge with unresolved Critical/High findings zero. Acceptance authorizes a later exact schema/pure fake-port implementation allocation only. It does not authorize source mutation under this unit, service installation, ACL/owner mutation, enrollment, native QA, Project/control/child writes, private voice/model effects, Release, Deploy or Production.
