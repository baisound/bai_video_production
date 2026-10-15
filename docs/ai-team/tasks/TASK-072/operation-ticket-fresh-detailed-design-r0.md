# TASK-072 Operation Ticket Fresh Detailed Design R0

Status: `DESIGN_ACCEPTED / RECOVERY_R3_ACCEPTED / HOSTED_CLOSURE_PENDING / DEV-4 / EFFECT_ZERO_PURE_I1_ONLY / LIVE_SOURCE_BLOCKED`

Design identity: `TASK072-OPERATION-TICKET-FRESH-DESIGN-R0`

Review parent: `main@4c68ad6d852a0c618eb35fe0b92649d9f8ac77df`

Owner allocation: `2026-10-12 / serialized BVP dependency-unblocking lane`

Recovery authority: `R3 = direct Owner-authorized one-finding correction after
the bounded R1/R2 review budget was exhausted`.

## 1. Decision

TASK-072 retains one coherent Product responsibility: create and consume one
live, one-shot, non-Human machine-operation capability and, where a child is
required, own its exact containment through a known or explicitly unknown
terminal.

Current main does not yet provide the producer/runtime set required to implement
that live responsibility safely. This design therefore admits only a pure,
fixture-only contract/state-machine slice:

```text
SOURCE_ADMISSION = ADMITTED_EFFECT_ZERO_PURE_CORE_I1
LIVE_SOURCE_ADMISSION = BLOCKED_DEPENDENCIES
NATIVE_SOURCE_ADMISSION = BLOCKED_DEPENDENCIES
```

I1 cannot mint authority, select current state, access the filesystem, start or
bind a process, create a channel or Job Object, or invoke any consumer. It gives
future producers and consumers one strict body-free fixture vocabulary that is
provably non-executable.

## 2. Responsibility boundary

TASK-072 owns:

- the closed execution-mode and fixture-transition vocabulary in this design;
- mode-specific ticket, start and vector budget validation;
- exact predecessor, proof-tag and terminal validation;
- body/path/secret-free fixture projection;
- future live broker/session/channel/child containment responsibility.

TASK-072 does not own immutable secure I/O, Project/Job currentness, installer
semantics, Human authorization, compute/network admission, consumer semantics,
private model/reference custody, Product release, or cleanup. A dependency type
listed below remains owned by its named Task. I1 validates fixture-shaped
references to it and never constructs or authenticates the live object.

## 3. Current producer ABI inventory

Classification is exact for this source gate:

- `CANONICAL_SOURCE_DEPENDENCY` means accepted source exists, but does not imply
  platform-native or live-composition readiness.
- `DESIGN_FIXTURE_ONLY` means the accepted/design-reviewed type is not a live
  producer.
- `DEPENDENCY_NOT_CURRENT` means TASK-072 must reject it as a live input.

| Owner | Exact relevant type/version | Classification for I1/live |
|---|---|---|
| TASK-068 | `TASK068_IMMUTABLE_PLAN_V1`; `TASK068_IMMUTABLE_RECEIPT_V1` | `CANONICAL_SOURCE_DEPENDENCY`; platform-native remains `NOT_CONFIRMED`; never current-head authority |
| TASK-043 / TASK-099 | `PROJECT_JOB_CURRENTNESS_READBACK_V2` with `ABSENT_JOB_HEAD` or `SELECTED_JOB_HEAD` | pure parser/index/fake-port accepted; JCV-N/JCV-C live selection is `DEPENDENCY_NOT_CURRENT` |
| TASK-102 | PMST-N1 transaction feasibility and PMST-I2 writer migration | source dependency exists; `PRODUCT_ENROLLMENT_DISABLED`, so live Project transaction is `DEPENDENCY_NOT_CURRENT` |
| TASK-063 | `PRETERMINAL_SELECTED_INSTALL_PLAN_ABI_V1`; `INSTALLATION_READBACK_V2` | design/fixture contract; post-repair native installed terminal is absent, therefore live readback is `DEPENDENCY_NOT_CURRENT` |
| TASK-070 | `INSTALL_AUTHORITY_BASELINE_V1`; `INSTALL_OPERATION_LEASE_V1`; `INSTALL_DESCRIPTOR_PAIR_PLAN_V2`; `SUCCESSOR_RESERVATION_V1`; `PAIR_PREPARED_V2`; `PAIR_TERMINAL_V2`; `INSTALLATION_REVISION_V1`; `PORTABLE_REBIND_V1`; `INSTALLATION_PAIR_READBACK_V2` | `DESIGN_FIXTURE_ONLY / SOURCE_START0` |
| TASK-071 | `HUMAN_ACTION_ABI_V1`; `HUMAN_AUTHORIZATION_RESERVATION_V1`; `HUMAN_CHALLENGE_ISSUED_V1`; `HUMAN_DECISION_EVENT_V1`; `HUMAN_AUTHORIZATION_CAPABILITY_V1`; `HUMAN_AUTH_IN_FLIGHT_V1`; `HUMAN_AUTH_TERMINAL_V1`; `HUMAN_EFFECT_CURRENTNESS_ATTESTATION_V1`; `HUMAN_ACTION_REGISTRY_V2`; `OWNER_VOICE_REFERENCE_PREPARE_V1`; `OWNER_VOICE_LOCAL_INFERENCE_V1`; `OWNER_VOICE_LISTENING_DECISION_V1`; `OWNER_VOICE_REGENERATE_V1`; `OWNER_VOICE_REFERENCE_REVOKE_V1`; `OWNER_VOICE_REFERENCE_PURGE_V1` | `DESIGN_FIXTURE_ONLY / SOURCE_START0`; no live Human capability |
| TASK-066 / TASK-073 | current D4 allowlist `AUDIO_VOICE_COMPUTE_ADMISSION_V1`; proposed producer `LOCAL_VOICE_COMPUTE_ADMISSION_V1` | AUDIO is not an alias for local voice; LOCAL and exact child-network enforcement are `DEPENDENCY_NOT_CURRENT` |
| TASK-072 | proposed consumer reference `OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3` | not canonical source; this design does not admit it into I1 or live execution |
| TASK-075 | `TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1` | R6 bytes have a separate `PASS_DESIGN_ONLY` receipt but remain `SOURCE_START0`; live result is `DEPENDENCY_NOT_CURRENT` |
| TASK-041 | proposed `TASK041_OWNER_VOICE_LISTENING_DECISION_V2` used by TASK-075 R6 | owner producer/currentness remains `DEPENDENCY_NOT_CURRENT` for this gate |
| TASK-076 V2 | `JOB_DISPATCH_PLAN_V2`; `JOB_CHILD_ARMED_READBACK_V2`; `JOB_CHILD_REJECTED_READBACK_V2`; `JOB_CHILD_BURNED_UNKNOWN_READBACK_V2`; `JOB_CHILD_STARTED_READBACK_V2`; `JOB_CHILD_START_REJECTED_READBACK_V2`; `JOB_CHILD_ABORTED_READBACK_V2`; `JOB_CHILD_ORPHAN_ABORTED_READBACK_V2`; `JOB_CHILD_TERMINAL_READBACK_V2` | `DESIGN_FIXTURE_ONLY / SOURCE_START0` |
| TASK-076 V3 | `JOB_DISPATCH_PLAN_V3`; `TASK076_EXTERNAL_BINDING_SLOT_V1`; `JOB_CHILD_ARMED_READBACK_V3`; `JOB_CHILD_REJECTED_READBACK_V3`; `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`; `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3`; `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3`; `JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3`; `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3`; `JOB_CHILD_EXTERNAL_INPUT_BOUND_READBACK_V3`; `JOB_CHILD_EXTERNAL_BINDING_FAILED_CLOSED_READBACK_V3`; `JOB_CHILD_EXTERNAL_INPUT_VALIDATED_READBACK_V3`; `JOB_CHILD_EXTERNAL_INPUT_FAILED_CLOSED_READBACK_V3`; `JOB_CHILD_ARTIFACT_PREPARE_PENDING_READBACK_V3`; `JOB_CHILD_ARTIFACT_ABORT_WAIT_READBACK_V3`; `JOB_CHILD_ARTIFACT_PREPARED_READBACK_V3`; `JOB_CHILD_ARTIFACT_PREPARE_FAILED_ABORT_REQUIRED_READBACK_V3`; `JOB_CHILD_RELEASE_REJECTED_ABORT_REQUIRED_READBACK_V3`; `JOB_CHILD_ABORT_ARTIFACT_PHASE_V3`; `JOB_CHILD_ARTIFACT_NEVER_ENTERED_READBACK_V3`; `JOB_CHILD_ARTIFACT_ABORT_TRUTH_READBACK_V3`; `JOB_CHILD_ARTIFACT_PREPARE_COMMIT_CONTEXT_V3`; `JOB_CHILD_ABORT_PENDING_READBACK_V3`; `JOB_CHILD_TERMINATED_WAITED_READBACK_V3`; `JOB_CHILD_STARTED_READBACK_V3`; `JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3`; `JOB_CHILD_TERMINAL_READBACK_V3`; `TASK076_RECOVERY_CONTAINMENT_PROFILE_V1`; `JOB_CHILD_UNKNOWN_CONTAINMENT_READBACK_V3` | `DESIGN_FIXTURE_ONLY / SOURCE_START0` |
| named V3 producer/Artifact owners | `OWNER_EXTERNAL_INPUT_BOUND_READBACK_V1`; `OWNER_EXTERNAL_INPUT_BINDING_FAILED_READBACK_V1`; `OWNER_EXTERNAL_INPUT_CLOSED_READBACK_V1`; `OWNER_EXTERNAL_INPUT_RECOVERY_REVOKE_V1`; `FIXED_OWNER_PREFLIGHT_PROFILE_V1`; `JOB_ARTIFACT_HANDLE_PREPARED_READBACK_V1`; `JOB_ARTIFACT_KNOWN_NO_CREATE_READBACK_V1`; `JOB_ARTIFACT_RECEIPT_ONLY_PREPARED_READBACK_V1` | owner inputs consumed by the TASK-076 design; every live producer is `DEPENDENCY_NOT_CURRENT` |

Historical receipts, fixture records, equal hashes and public projections never
replace a live owner capability or currentness readback.

## 4. Closed execution modes and schema property sets

The root I1 object has exactly these common properties and rejects every other
property:

```text
message_type = BvpTask072OperationTicketFixture
schema_version = 1
fixture_id_sha256
mode
transition_kind
fixture_only = true
evaluation_effects
subject
```

`evaluation_effects` has exactly the following fixed fields, all `false`:

```text
authority_created
currentness_selected
filesystem_accessed
native_effect_executed
child_created
consumer_invoked
```

Those flags describe evaluation by I1. They never describe the historical or
hypothetical operation represented by `subject`.

`subject` is one and only one additional-properties-false tagged union:

| Mode | Exact allowed subject properties | Every foreign-mode property |
|---|---|---|
| `IN_PROCESS_INSTALLED_INSTANCE_BINDING_V1` | `profile_id=INSTALLED_INSTANCE_PROFILE_BINDING_V1`, `task063_installation_readback_sha256`, `task070_pair_readback_sha256`, `owner_currentness_fixture_sha256`, `owner_result_fixture_sha256`, `ticket_budget_before`, `ticket_budget_after`, `subject_effect_fact` | forbidden |
| `CHILD_V2_ORDINARY_V1` | `task076_dispatching_readback_sha256`, `job_dispatch_plan_v2_sha256`, `task076_in_flight_readback_sha256`, `job_child_armed_readback_v2_sha256`, `job_child_result_readback_v2_sha256`, `ticket_budget_before`, `ticket_budget_after`, `start_budget_before`, `start_budget_after`, `subject_child_fact`, `subject_consumer_effect_fact` | forbidden |
| `CHILD_V3_SENSITIVE_EXTERNAL_BINDING_V1` | `task076_dispatching_readback_sha256`, `job_dispatch_plan_v3_sha256`, `external_binding_slot_v1_sha256`, `task076_in_flight_readback_sha256`, `job_child_armed_readback_v3_sha256`, `phase_readback_v3_sha256`, `result_readback_v3_sha256`, `ticket_budget_before`, `ticket_budget_after`, `vector_before`, `vector_after`, `abort_context`, `subject_child_fact`, `subject_artifact_handle_fact`, `subject_artifact_body_fact`, `subject_model_effect_fact`, `subject_consumer_effect_fact` | forbidden |

Every SHA field is lowercase SHA-256 and is required or forbidden by the
transition tables below; it never authenticates the referenced object. Fact
fields use exactly `KNOWN_FALSE | KNOWN_TRUE | UNKNOWN`. `UNKNOWN` is an
explicit value, never an empty or omitted digest.

`mode` is exactly the three literals in the table above. `transition_kind` is
exactly one literal appearing in the first column of sections 6, 7, 8 or 8.1;
no alias, generic unknown, numeric index or caller extension is accepted. The
selected literal itself fixes the predecessor, result type, required fields,
forbidden fields and budget transition. The schema defines no separate
`predecessor_kind`, `result_kind` or `transition_index` that could disagree.

Mode selection follows actual input topology:

- installed-instance binding is the only admitted in-process profile;
- a non-sensitive ordinary child is V2;
- exactly one sensitive producer bound directly to an exact child is V3;
- zero-shot private reference topology may require V3;
- a fine-tuned route forbids reference field, role and handle, and does not
  become V3 merely because it is voice work;
- unsupported or mixed topology is rejected before any fixture transition.

## 5. Budget vocabularies

The ticket budget vocabulary is:

```text
NOT_CREATED
CONSUMED_IN_PROCESS
CONSUMED_ARMED
CONSUMED_REJECTED
CONSUMED_TERMINAL
BURNED_UNKNOWN
```

The V2 start budget vocabulary is:

```text
NOT_CREATED
OPEN
CONSUMED_STARTED
CONSUMED_REJECTED
CONSUMED_ABORTED
BURNED_UNKNOWN
```

The V3 vector has exactly five keys:
`process_create`, `external_bind`, `preflight`, `release`, `abort`. Each value
uses only the exact TASK-076 state token allowed by the row below. A ticket is
burned by the serialized `issue_and_arm` entry. V2 then owns a distinct start
budget. V3 then owns the five-budget vector. No single generic invocation
budget aliases these phases.

## 6. In-process transition matrix

The installed-instance profile has no child, Job, config, channel, external
slot, start budget or V3 vector.

| `transition_kind` | predecessor / result | ticket before -> after | Required proof fields | Terminal class |
|---|---|---|---|---|
| `INPROC_PRECHECK_REJECTED` | `PLANNED -> PRECHECK_REJECTED` | `NOT_CREATED -> NOT_CREATED` | task063 + task070 fixture digests; no owner currentness/result | no TASK-072 terminal |
| `INPROC_ENTER` | `RESERVED -> IN_FLIGHT` | `NOT_CREATED -> CONSUMED_IN_PROCESS` | task063 + task070 + owner currentness digests; no owner result | nonterminal |
| `INPROC_COMMITTED` | `IN_FLIGHT -> TERMINAL` | `CONSUMED_IN_PROCESS -> CONSUMED_TERMINAL` | all four digests; `subject_effect_fact=KNOWN_TRUE` | known committed |
| `INPROC_REJECTED_CONSUMED` | `IN_FLIGHT -> TERMINAL` | `CONSUMED_IN_PROCESS -> CONSUMED_TERMINAL` | all four digests; effect fact `KNOWN_FALSE` | known consumed rejection |
| `INPROC_BURNED_UNKNOWN` | `IN_FLIGHT -> TERMINAL` | `CONSUMED_IN_PROCESS -> BURNED_UNKNOWN` | owner currentness required; owner result forbidden; effect fact `UNKNOWN` | unknown, no replay |

No session-mismatch or cancellation spelling is admitted until its owner freezes
an exact terminal ABI. It maps neither to rejection nor to no effect.

## 7. V2 transition matrix

TASK-076 phase mapping is exact:

```text
selected DISPATCHING
  -> serialized issue_and_arm_job_child_v2
     (ticket issue/channel creation/ticket-budget burn)
  -> ARMED with separate start budget OPEN
  -> publish candidate TASK-076 IN_FLIGHT
  -> either orphan-abort while DISPATCHING stays current,
     or select exact TASK-076 IN_FLIGHT
  -> exactly one attach-and-start or same-session abort winner
  -> started child terminal, or known/unknown non-reusable closure
```

| `transition_kind` | predecessor -> result | ticket before -> after | start before -> after | Required fixture proof fields | Terminal class |
|---|---|---|---|---|---|
| `V2_PRE_ARM_REJECTED` | selected `DISPATCHING -> PRECHECK_REJECTED` before broker entry | `NOT_CREATED -> NOT_CREATED` | `NOT_CREATED -> NOT_CREATED` | dispatching + plan; every arm/in-flight/result digest forbidden | no TASK-072 terminal |
| `V2_ARMED` | selected `DISPATCHING -> JOB_CHILD_ARMED_READBACK_V2` | `NOT_CREATED -> CONSUMED_ARMED` | `NOT_CREATED -> OPEN` | dispatching + plan + armed; in-flight/result forbidden; child/effect `KNOWN_FALSE` | nonterminal |
| `V2_ARM_REJECTED` | selected `DISPATCHING -> JOB_CHILD_REJECTED_READBACK_V2` | `NOT_CREATED -> CONSUMED_REJECTED` | `NOT_CREATED -> NOT_CREATED` | dispatching + plan + exact result; armed/in-flight forbidden; child/effect `KNOWN_FALSE` | known arm rejection |
| `V2_ARM_BURNED_UNKNOWN` | selected `DISPATCHING -> JOB_CHILD_BURNED_UNKNOWN_READBACK_V2` | `NOT_CREATED -> BURNED_UNKNOWN` | `NOT_CREATED -> BURNED_UNKNOWN` | dispatching + plan + exact result; arm/in-flight forbidden; child/effect `UNKNOWN` | unknown, no replay |
| `V2_ORPHAN_ABORTED` | ARMED + unselected IN_FLIGHT candidate while DISPATCHING remains current -> `JOB_CHILD_ORPHAN_ABORTED_READBACK_V2` | `CONSUMED_ARMED -> CONSUMED_ARMED` | `OPEN -> CONSUMED_ABORTED` | dispatching + plan + armed + unselected candidate in in-flight field + result | known no-child orphan close |
| `V2_ABORTED` | exact current TASK-076 IN_FLIGHT + ARMED -> `JOB_CHILD_ABORTED_READBACK_V2` | unchanged `CONSUMED_ARMED` | `OPEN -> CONSUMED_ABORTED` | plan + armed + current in-flight + result; dispatching forbidden | known no-child same-session close |
| `V2_STARTED` | exact current TASK-076 IN_FLIGHT + ARMED -> `JOB_CHILD_STARTED_READBACK_V2` | unchanged `CONSUMED_ARMED` | `OPEN -> CONSUMED_STARTED` | plan + armed + current in-flight + result; child `KNOWN_TRUE` | known started, nonterminal |
| `V2_START_REJECTED` | exact current TASK-076 IN_FLIGHT + ARMED -> `JOB_CHILD_START_REJECTED_READBACK_V2` | unchanged `CONSUMED_ARMED` | `OPEN -> CONSUMED_REJECTED` | plan + armed + current in-flight + result; child/effect `KNOWN_FALSE` | known non-retryable rejection |
| `V2_ORPHAN_ABORT_BURNED_UNKNOWN` | ARMED + unselected IN_FLIGHT candidate while DISPATCHING remains current -> `JOB_CHILD_BURNED_UNKNOWN_READBACK_V2` | unchanged `CONSUMED_ARMED` | `OPEN -> BURNED_UNKNOWN` | dispatching + plan + armed + unselected candidate in in-flight field + result; child/effect `UNKNOWN` | unknown, query only |
| `V2_SELECTED_ABORT_BURNED_UNKNOWN` | exact current TASK-076 IN_FLIGHT + ARMED abort entry -> `JOB_CHILD_BURNED_UNKNOWN_READBACK_V2` | unchanged `CONSUMED_ARMED` | `OPEN -> BURNED_UNKNOWN` | plan + armed + selected in-flight + result; dispatching forbidden; child/effect `UNKNOWN` | unknown, query only |
| `V2_START_BURNED_UNKNOWN` | exact current TASK-076 IN_FLIGHT + ARMED start entry -> `JOB_CHILD_BURNED_UNKNOWN_READBACK_V2` | unchanged `CONSUMED_ARMED` | `OPEN -> BURNED_UNKNOWN` | plan + armed + selected in-flight + result; dispatching forbidden; child/effect `UNKNOWN` | unknown, containment/query only |
| `V2_CHILD_TERMINAL` | `JOB_CHILD_STARTED_READBACK_V2 -> JOB_CHILD_TERMINAL_READBACK_V2` | unchanged `CONSUMED_ARMED` | unchanged `CONSUMED_STARTED` | plan + armed + selected in-flight + started/terminal result chain | known started-child terminal |
| `V2_TERMINAL_READ_BURNED_UNKNOWN` | exact started readback terminal query -> `JOB_CHILD_BURNED_UNKNOWN_READBACK_V2` | unchanged `CONSUMED_ARMED` | unchanged `CONSUMED_STARTED` | plan + armed + selected in-flight + started readback + exact unknown result; effect `UNKNOWN` | unknown started-child terminal |

Every digest not named in a row is forbidden. A restart before start can return
only the exact same-operation `BURNED_UNKNOWN` classification; it cannot rebuild
ARMED, start, abort as known-no-effect, or restore either budget.

## 8. V3 transition and vector matrix

TASK-076 phase mapping is exact:

```text
selected DISPATCHING
  -> serialized issue_and_arm_job_child_v3
     (ticket burn + vector creation)
  -> ARMED_V3
  -> unselected-candidate orphan abort, or selected TASK-076 IN_FLIGHT
  -> prebootstrap abort or bootstrap create
  -> direct owner bind -> child preflight
  -> Artifact prepare claim/commit
  -> release/start winner or tagged abort winner
  -> exact V3 terminal, or vector-wide BURNED_UNKNOWN
```

The exact canonical vector rows are:

| `vector_after` phase | process-create | external-bind | preflight | release | abort |
|---|---|---|---|---|---|
| `V3_ARMED` | `OPEN` | `LOCKED` | `LOCKED` | `LOCKED` | `OPEN` |
| `V3_ORPHAN_ABORTED` / `V3_PREBOOTSTRAP_ABORTED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` |
| `V3_BOOTSTRAP_REJECTED` | `CONSUMED_REJECTED` | `CLOSED_REJECTED` | `CLOSED_REJECTED` | `CLOSED_REJECTED` | `CLOSED_REJECTED` |
| `V3_BOOTSTRAP_WAITING` | `CONSUMED_CREATED` | `OPEN` | `LOCKED` | `LOCKED` | `OPEN` |
| `V3_EXTERNAL_BOUND` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `OPEN` | `LOCKED` | `OPEN` |
| `V3_BIND_FAILED` | `CONSUMED_CREATED` | `CONSUMED_FAILED` | `LOCKED` | `LOCKED` | `OPEN` |
| `V3_EXTERNAL_VALIDATED` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `CONSUMED_VALIDATED` | `ARTIFACT_PREPARE_OPEN` | `OPEN` |
| `V3_PREFLIGHT_FAILED` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `CONSUMED_FAILED` | `LOCKED` | `OPEN` |
| `V3_ARTIFACT_PREPARE_PENDING` | preceding consumed bind/preflight | same | same | `ARTIFACT_PREPARE_PENDING` | `OPEN` |
| `V3_ABORT_WAITING_ARTIFACT_TRUTH` | preceding consumed bind/preflight | same | same | `ARTIFACT_PREPARE_PENDING` | `ABORT_WAITING_ARTIFACT_TRUTH` |
| `V3_ARTIFACT_PREPARED` | preceding consumed bind/preflight | same | same | `ARTIFACT_PREPARED` | `OPEN` |
| `V3_ARTIFACT_PREPARE_FAILED` | preceding consumed bind/preflight | same | same | `CONSUMED_REJECTED` | `OPEN` |
| `V3_RELEASE_REJECTED` | preceding consumed bind/preflight | same | same | `CONSUMED_REJECTED` | `OPEN` |
| `V3_STARTED` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `CONSUMED_VALIDATED` | `CONSUMED_STARTED` | `CLOSED_RELEASE_WON` |
| `V3_ABORT_PENDING_BEFORE_PREPARE` | `CONSUMED_CREATED` | preserve `CONSUMED_BOUND` or `CONSUMED_FAILED`; otherwise `CONSUMED_ABORTED` | preserve `CONSUMED_VALIDATED` or `CONSUMED_FAILED`; otherwise `CONSUMED_ABORTED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` |
| `V3_ABORT_PENDING_FROM_PREPARE_COMMIT` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `CONSUMED_VALIDATED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` |
| `V3_ABORT_PENDING_AFTER_PREPARED` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `CONSUMED_VALIDATED` | `CONSUMED_ABORTED` | `CONSUMED_ABORTED` |
| `V3_ABORT_PENDING_AFTER_PREPARE_FAILED` / `V3_ABORT_PENDING_AFTER_RELEASE_REJECTED` | `CONSUMED_CREATED` | `CONSUMED_BOUND` | `CONSUMED_VALIDATED` | preserve `CONSUMED_REJECTED` | `CONSUMED_ABORTED` |
| `V3_BOOTSTRAP_ABORTED` | byte-identical to the exact preceding `V3_ABORT_PENDING_*` vector | same | same | same | same |
| `V3_BURNED_UNKNOWN` | `BURNED_UNKNOWN` | `BURNED_UNKNOWN` | `BURNED_UNKNOWN` | `BURNED_UNKNOWN` | `BURNED_UNKNOWN` |
| `V3_TERMINAL` | identical to `V3_STARTED` | identical | identical | identical | identical |

The phrase `preceding consumed bind/preflight` means the exact previous row is
carried byte-for-byte; the caller cannot choose it. I1 accepts only a valid
adjacent pair. This is a derivation rule, not an open state wildcard.

| `transition_kind` | Exact predecessor -> result readback | Ticket before -> after | Required fixture proof and fact rules | Terminal class |
|---|---|---|---|---|
| `V3_PRE_ARM_REJECTED` | selected DISPATCHING -> precheck rejection before broker entry | `NOT_CREATED -> NOT_CREATED` | dispatching + plan + slot; arm/vector/result forbidden; all subject facts `KNOWN_FALSE` | no TASK-072 terminal |
| `V3_ARMED` | selected DISPATCHING -> `JOB_CHILD_ARMED_READBACK_V3` | `NOT_CREATED -> CONSUMED_ARMED` | dispatching + plan + slot + armed; vector `absent -> V3_ARMED`; all facts false | nonterminal |
| `V3_ARM_REJECTED` | selected DISPATCHING -> `JOB_CHILD_REJECTED_READBACK_V3` | `NOT_CREATED -> CONSUMED_REJECTED` | dispatching + plan + slot + result; vector absent; all facts false | known pre-vector rejection |
| `V3_ARM_BURNED_UNKNOWN` | selected DISPATCHING -> `JOB_CHILD_BURNED_UNKNOWN_READBACK_V3` | `NOT_CREATED -> BURNED_UNKNOWN` | dispatching + plan + slot + result; vector-after `V3_BURNED_UNKNOWN`; every uncertain subject fact explicit `UNKNOWN` | unknown, no replay |
| `V3_ORPHAN_ABORTED` | ARMED + unselected IN_FLIGHT candidate while DISPATCHING current -> `JOB_CHILD_ORPHAN_ABORTED_READBACK_V3` | unchanged `CONSUMED_ARMED` | dispatching + plan + slot + armed + unselected candidate in in-flight field + result; `V3_ARMED -> V3_ORPHAN_ABORTED`; all facts false | known zero-effect orphan close |
| `V3_PREBOOTSTRAP_ABORTED` | selected TASK-076 IN_FLIGHT + ARMED -> `JOB_CHILD_PREBOOTSTRAP_ABORTED_READBACK_V3` | unchanged | plan + slot + armed + selected in-flight + result; `V3_ARMED -> V3_PREBOOTSTRAP_ABORTED`; all facts false | known zero-effect selected close |
| `V3_BOOTSTRAP_WAITING` | selected IN_FLIGHT + ARMED -> `JOB_CHILD_BOOTSTRAP_WAITING_READBACK_V3` | unchanged | exact selected chain + phase result; `V3_ARMED -> V3_BOOTSTRAP_WAITING`; child true, every other fact false | nonterminal contained child |
| `V3_BOOTSTRAP_REJECTED` | selected IN_FLIGHT + ARMED create entry -> `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3` | unchanged | exact selected chain + result; `V3_ARMED -> V3_BOOTSTRAP_REJECTED`; all facts false | known no-process rejection |
| `V3_EXTERNAL_BOUND` / `V3_BIND_FAILED` | BOOTSTRAP_WAITING -> exact bound or failed-closed readback | unchanged | prior phase + result; exact adjacent vector row; child true; other facts false | nonterminal / abort-required |
| `V3_EXTERNAL_VALIDATED` / `V3_PREFLIGHT_FAILED` | exact BOUND -> exact validated or failed-closed readback | unchanged | prior phase + result; exact adjacent vector row; Artifact/model/consumer facts false | nonterminal / abort-required |
| `V3_ARTIFACT_PREPARE_PENDING` | VALIDATED -> exact pending readback | unchanged | exact selected lineage + pending readback; vector adjacent; Artifact fact remains false | nonterminal exclusive lease |
| `V3_ARTIFACT_ABORT_WAIT` | PREPARE_PENDING abort claim -> exact abort-wait readback | unchanged | pending + abort-wait result; `abort_context=PREPARE_IN_PROGRESS`; vector `V3_ARTIFACT_PREPARE_PENDING -> V3_ABORT_WAITING_ARTIFACT_TRUTH`; Artifact fact `UNKNOWN` | nonterminal, release winner closed |
| `V3_ARTIFACT_PREPARED` / `V3_ARTIFACT_PREPARE_FAILED` | `PREPARE_ONLY` pending commit -> exact prepared or failure readback | unchanged | exact pending context + result; Artifact handle fact follows exact result; body/model/consumer false | release-open or abort-required |
| `V3_RELEASE_REJECTED` | PREPARED -> exact release-rejected readback | unchanged | complete lineage + result; exact vector row; consumer fact false | abort-required |
| `V3_STARTED` | PREPARED -> `JOB_CHILD_STARTED_READBACK_V3` | unchanged | complete lineage + result; vector `V3_STARTED`; child true; Artifact fact exact; body/model/consumer may be explicit `UNKNOWN` but never omitted | known started, nonterminal |
| `V3_ABORT_PENDING_BEFORE_PREPARE` | exact `BEFORE_PREPARE` claim -> `JOB_CHILD_ABORT_PENDING_READBACK_V3` | unchanged | `abort_context=BEFORE_PREPARE` + exact never-entered truth + phase result; exact corresponding vector row | owner-close/terminate pending |
| `V3_ABORT_PENDING_FROM_PREPARE_COMMIT` | exact abort-wait + matching `PREPARE_WITH_ABORT_WAIT` commit -> `JOB_CHILD_ABORT_PENDING_READBACK_V3` | unchanged | `abort_context=PREPARE_IN_PROGRESS` + pending + abort-wait + commit result; release and abort both become `CONSUMED_ABORTED` | owner-close/terminate pending |
| `V3_ABORT_PENDING_AFTER_PREPARED` | exact `AFTER_PREPARE` claim from PREPARED -> `JOB_CHILD_ABORT_PENDING_READBACK_V3` | unchanged | `abort_context=AFTER_PREPARE` + prepared truth + result; release becomes `CONSUMED_ABORTED` | owner-close/terminate pending |
| `V3_ABORT_PENDING_AFTER_PREPARE_FAILED` | exact `AFTER_PREPARE` claim from PREPARE_FAILED -> `JOB_CHILD_ABORT_PENDING_READBACK_V3` | unchanged | `abort_context=AFTER_PREPARE` + prepare-failed truth + result; release remains `CONSUMED_REJECTED` | owner-close/terminate pending |
| `V3_ABORT_PENDING_AFTER_RELEASE_REJECTED` | exact `AFTER_RELEASE_REJECTED` claim -> `JOB_CHILD_ABORT_PENDING_READBACK_V3` | unchanged | matching release-rejected truth + result; release remains `CONSUMED_REJECTED` | owner-close/terminate pending |
| `V3_BOOTSTRAP_ABORTED` | ABORT_PENDING + exact owner-close/no-role-transfer + terminated/waited proofs -> `JOB_CHILD_BOOTSTRAP_ABORTED_READBACK_V3` | unchanged | pending phase + exact terminal result; facts retain truthful child/Artifact values; body/model/consumer false | known contained abort |
| `V3_UNKNOWN_CONTAINMENT` | BURNED_UNKNOWN -> `JOB_CHILD_UNKNOWN_CONTAINMENT_READBACK_V3` | unchanged | exact original operation coordinate + containment profile + result; vector remains burned; cannot change terminal class | recovery containment only |
| `V3_CHILD_TERMINAL` | STARTED -> `JOB_CHILD_TERMINAL_READBACK_V3` | unchanged | complete ARMED/bootstrap/bind/validated/prepared/started lineage plus owner lease terminal and Artifact/result truth | known started-child terminal |

### 8.1 Closed V3 unknown-origin transitions

Every row below returns the exact same-operation
`JOB_CHILD_BURNED_UNKNOWN_READBACK_V3`, changes the vector to
`V3_BURNED_UNKNOWN`, keeps `ticket_budget_after=CONSUMED_ARMED`, and requires
every subject fact to be explicit `KNOWN_FALSE | KNOWN_TRUE | UNKNOWN`. The
distinct tag fixes the sole legal predecessor and proof set:

| `transition_kind` | Sole predecessor / attempted entry | Required proof fields before the exact unknown result |
|---|---|---|
| `V3_ORPHAN_ABORT_BURNED_UNKNOWN` | ARMED + unselected IN_FLIGHT candidate while DISPATCHING remains current / orphan abort | dispatching + plan + slot + armed + unselected candidate |
| `V3_PREBOOTSTRAP_ABORT_BURNED_UNKNOWN` | ARMED + exact selected TASK-076 IN_FLIGHT / prebootstrap abort | plan + slot + armed + selected in-flight |
| `V3_BOOTSTRAP_CREATE_BURNED_UNKNOWN` | ARMED + exact selected TASK-076 IN_FLIGHT / bootstrap create | plan + slot + armed + selected in-flight |
| `V3_EXTERNAL_BIND_BURNED_UNKNOWN` | BOOTSTRAP_WAITING / owner bind record | complete selected lineage + bootstrap-waiting phase readback |
| `V3_PREFLIGHT_BURNED_UNKNOWN` | EXTERNAL_BOUND / child preflight | complete selected lineage + bound phase readback |
| `V3_ARTIFACT_PREPARE_CLAIM_BURNED_UNKNOWN` | EXTERNAL_VALIDATED / prepare claim | complete selected lineage + validated phase readback |
| `V3_ARTIFACT_PREPARE_COMMIT_BURNED_UNKNOWN` | ARTIFACT_PREPARE_PENDING / `PREPARE_ONLY` commit | complete lineage + pending phase readback; `abort_context` forbidden |
| `V3_ABORT_WAIT_PREPARE_COMMIT_BURNED_UNKNOWN` | ABORT_WAITING_ARTIFACT_TRUTH / `PREPARE_WITH_ABORT_WAIT` commit | complete lineage + pending + abort-wait readbacks; `abort_context=PREPARE_IN_PROGRESS` |
| `V3_RELEASE_BURNED_UNKNOWN` | ARTIFACT_PREPARED / release entry | complete lineage + prepared phase readback |
| `V3_ABORT_CLAIM_BEFORE_PREPARE_BURNED_UNKNOWN` | exact BEFORE_PREPARE phase / abort claim | complete lineage + exact never-entered truth; `abort_context=BEFORE_PREPARE` |
| `V3_ABORT_CLAIM_PREPARE_IN_PROGRESS_BURNED_UNKNOWN` | ARTIFACT_PREPARE_PENDING / abort claim | complete lineage + pending phase readback; `abort_context=PREPARE_IN_PROGRESS` |
| `V3_ABORT_CLAIM_AFTER_PREPARE_BURNED_UNKNOWN` | exact ARTIFACT_PREPARED or PREPARE_FAILED phase / abort claim | complete lineage + exact phase readback; `abort_context=AFTER_PREPARE` |
| `V3_ABORT_CLAIM_AFTER_RELEASE_REJECTED_BURNED_UNKNOWN` | RELEASE_REJECTED / abort claim | complete lineage + release-rejected phase readback; `abort_context=AFTER_RELEASE_REJECTED` |
| `V3_ABORT_COMMIT_BURNED_UNKNOWN` | ABORT_PENDING / owner close + terminate/wait commit | exact abort-pending, owner-close/no-role-transfer and terminated/waited proofs |
| `V3_TERMINAL_READ_BURNED_UNKNOWN` | STARTED / terminal read | complete started lineage + exact owner lease and Artifact/result query inputs |

Every digest not named in a transition row is forbidden. `abort_context` is
required only for `V3_ARTIFACT_ABORT_WAIT`, the matching
`V3_ABORT_PENDING_*` row and its exact unknown counterpart. It is exactly
`BEFORE_PREPARE | PREPARE_IN_PROGRESS | AFTER_PREPARE |
AFTER_RELEASE_REJECTED` and is forbidden elsewhere.

## 9. Fixture subject facts and public projection

The modeled `subject_*_fact` values describe fixture evidence, not effects
performed by I1. Their closed rules are:

- pre-arm, arm rejection, ARMED, orphan abort and prebootstrap abort require all
  applicable facts `KNOWN_FALSE`;
- BOOTSTRAP_WAITING and later known phases require child `KNOWN_TRUE`;
- Artifact handle becomes `KNOWN_TRUE` only from the exact prepared readback;
  a known-no-create/receipt-only result remains `KNOWN_FALSE`;
- Artifact body/model/consumer remain `KNOWN_FALSE` before release;
- after release they must be explicit `KNOWN_TRUE | KNOWN_FALSE | UNKNOWN` as
  bound by the exact phase/terminal proof;
- BURNED_UNKNOWN never converts an unknown fact to false;
- containment may refine containment facts only and cannot change the operation
  terminal or consumer result.

The public projection is additional-properties-false and exposes exactly:

```text
message_type = BvpTask072OperationTicketFixtureProjection
schema_version = 1
fixture_only = true
mode
transition_kind
evaluation_effects (all false)
```

It exposes no path, command, environment, handle, SID, PID, body, URI, private
payload, error text, owner capability, currentness coordinate, proof digest,
modeled fact, budget or completion claim. `mode` and `transition_kind` retain
their exact root enums and are fixture metadata, never Product success or
currentness receipts.

## 10. Future I1 source allocation

After final acceptance and hosted closure of this design, a separate I1 unit may
change exactly:

1. `src/ai_video_production/task072_operation_ticket.py`
2. `schemas/task072-operation-ticket.schema.json`
3. `src/ai_video_production/schema_resources/task072-operation-ticket.schema.json`
4. `tests/test_task072_operation_ticket.py`
5. `tests/test_task072_operation_ticket_faults.py`
6. `docs/ai-team/tasks/TASK-072/task.md`

I1 may implement only strict bounded parsing/canonicalization, the exact tagged
unions and adjacent transitions above, deterministic immutable budget
validation, body/path/secret-free fixture projection, byte-identical schema
mirrors, and test fixtures. It has no live port.

I1 must not import or call `os`, `subprocess`, `socket`, `ctypes`, Windows/native
APIs, Project/store/currentness backends, installer/Product entrypoints, private
media/model/provider/network code, or live TASK-063/066/070/071/075/076 ports.

## 11. Explicit live/native blocks

Live/native work remains blocked on separate owner acceptance and implementation
for at least:

- TASK-099 JCV-N secure backend and JCV-C canonical consumer integration;
- TASK-102 Product enrollment;
- TASK-063/TASK-070 live implementation and installed-terminal readback;
- TASK-071 live Human broker and required owner-voice amendments;
- TASK-066 accepted local-voice compute plus enforceable exact-child network
  isolation producer and TASK-073 no-alias amendment;
- TASK-014/TASK-074 parent-reference/direct-child compatibility and exact V3
  bind/preflight/recovery adapters;
- TASK-075 accepted source allocation and consumer terminal contracts;
- TASK-076 source/runtime producer;
- Windows restricted channel, process, Job Object and kill-on-close feasibility;
- native/private-data Human Gate;
- Product composition, build/install, Release, Deploy and Production.

## 12. D0 contradiction closure

This design resolves the seven D0 requirements as follows:

1. Sections 5, 7 and 8 separate ticket burn, V2 start budget and V3 five-budget
   vector relative to selected DISPATCHING, arm, selected IN_FLIGHT, bootstrap,
   bind, preflight, prepare, release, abort and terminal.
2. Sections 6 through 8 give every admitted terminal one named predecessor,
   exact result type, budget transition and required/forbidden proof set.
3. Section 4 fixes three additional-properties-false property sets; no mode may
   borrow another mode's config, child, channel, external slot or budget.
4. Section 3 names exact owner type/version and classifies live currentness.
5. Section 4 separates zero-shot sensitive topology from fine-tuned routing.
6. V3 keeps sole non-inheritable kill-on-close custody, recovery-only
   containment, no replay and authority-zero evaluation/public projection.
7. Section 10 allocates a fresh exact-six I1 scope without historical A1 bytes
   or CHANGELOG.

## 13. Verification, failure and recovery

Acceptance requires:

- exact-two diff, ASCII paths, valid relative links and secret-safe prose;
- matrix exhaustiveness and schema implementability without invented meaning;
- exact-six future scope and prohibited-import/static-test plan;
- independent Critic and Tester on identical hashes with unresolved
  Critical/High `0/0`, followed by an independent Judge;
- external Evidence write/readback;
- Japanese PR and exact-head hosted checks green before normal merge.

If remote main or either exact-two path changes, stop and re-reconcile. If an
owner contract contradicts this design, keep the affected mode blocked rather
than weakening or locally redefining it. Stop after at most two bounded
correction cycles with any unresolved blocker.

Never recover by copying dirty R7/historical A1 source, deleting worktrees,
broadening scope, starting a native/build lane, or treating fixture PASS as live
authority.

## 14. Recovery R3 closure

The direct Owner-authorized Recovery R3 corrected only the omitted TASK-076
recovery-revoke owner ABI inventory entry. Independent Critic, Tester and Judge
each returned `ACCEPT` with Critical/High/Medium/Low
`0/0/0/0`; the Tester also recorded OSS readiness `12 passed` and all bounded
mechanical checks `PASS`. The Judge established
`ADMITTED_EFFECT_ZERO_PURE_CORE_I1` while preserving every live/native block.

These results applied to the frozen pre-administrative-closure hashes recorded
in `task.md`. This final status paragraph changes no contract bytes reviewed by
those roles. Commit, PR and exact-head hosted closure remain pending, and no I1,
live, native, build, provider, Release, Deploy or Production effect is thereby
authorized.
