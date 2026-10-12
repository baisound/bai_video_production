# TASK-072 — Product Operation Ticket and Child Containment

- Status: `OWNER_ALLOCATED / FRESH_DETAILED_DESIGN_R0_ACCEPTED / SOURCE_I1_ADMITTED_AFTER_HOSTED_CLOSURE / HOSTED_CLOSURE_PENDING / LIVE_SOURCE_BLOCKED`.
- Atomic Unit: `OPERATION-TICKET-FRESH-DETAILED-DESIGN-R0`.
- Profile: `DEV-4 FOUNDATION CRITICAL`.
- Allocation: 2026-10-12 JST, direct Owner instruction `次へ` after the D0
  currentness gate reached hosted closure.
- Base: `4c68ad6d852a0c618eb35fe0b92649d9f8ac77df`, exact remote main verified
  before the dedicated worktree was created.
- Branch: `codex/task-072-fresh-detailed-design-owner-r0`.
- Product effects: source/schema/test/native/build/install/private/provider/
  download/Release/Deploy/Production effects are all `0` in this unit.

## Responsibility

TASK-072 owns the Product-private one-shot machine-operation authority boundary:

- live nonserializable operation/ticket state;
- authenticated Product-to-broker and exact-child channels;
- exact process, build, user/session and one-use budget binding;
- operation-specific immutable config only for a mode that requires it;
- serialized child create/contain/start/abort ownership;
- one dedicated non-inheritable Windows Job containment handle where a child is
  created;
- exact known/unknown terminal classification and body-free public projection.

TASK-072 does not own immutable secure I/O (TASK-068), Project/Job currentness
or durable Job events (TASK-043/TASK-099/TASK-076), installer authority or
terminal handoff (TASK-063/TASK-070), Human authorization (TASK-071), consumer
operation semantics (including TASK-075), compute/network admission policy
(TASK-066), private model/reference custody, Product release, or cleanup.

## D0 prerequisite closure

The prior [operation-ticket currentness reconciliation](operation-ticket-currentness-reconciliation-r0.md)
closed through PR #622 and normal merge commit
`4c68ad6d852a0c618eb35fe0b92649d9f8ac77df`. The exact PR head passed `9 / 9`
checks; post-main CI passed `6 / 6` and Security passed `2 / 2`. D0 preserved
the dirty R7 packet as `PARKED`, rejected historical A1 source adoption, and
required a fresh detailed design before any source admission.

This unit satisfies only that next design gate. It does not reopen, normalize,
copy, amend, reset, clean, or delete any historical branch, worktree, packet,
Evidence, or source candidate.

## Allowed Files — exactly two repository paths

1. `docs/ai-team/tasks/TASK-072/task.md`
2. `docs/ai-team/tasks/TASK-072/operation-ticket-fresh-detailed-design-r0.md`

External public-safe Evidence only:
`C:\home\baisound\evidence\bai-video-production\TASK-072\operation-ticket-fresh-detailed-design\<unique-run-id>\`.

No shared current-state, roadmap, index, lock registry, CHANGELOG, source,
schema, test, fixture, packaging, installer, historical branch/worktree, or
foreign Task path is writable under this unit. Documentation paths are ASCII.

## Detailed-design decision

The linked [fresh detailed design](operation-ticket-fresh-detailed-design-r0.md)
keeps every live/native route blocked and admits only, after this exact design
reaches hosted closure:

`SOURCE_ADMISSION = ADMITTED_EFFECT_ZERO_PURE_CORE_I1`.

That candidate is a pure, fixture-only parser/state-machine/public-projection
slice. It creates no machine authority, selects no current record, opens no
path, creates no process/channel/Job Object, and composes no live producer.

The future I1 candidate may modify exactly:

1. `src/ai_video_production/task072_operation_ticket.py`
2. `schemas/task072-operation-ticket.schema.json`
3. `src/ai_video_production/schema_resources/task072-operation-ticket.schema.json`
4. `tests/test_task072_operation_ticket.py`
5. `tests/test_task072_operation_ticket_faults.py`
6. `docs/ai-team/tasks/TASK-072/task.md`

This list is a bounded future source allocation only after this design receives
final DEV-4 acceptance and hosted closure. It is not source authority in this
design unit. `CHANGELOG.md` remains excluded.

## Live dependency status

Live broker, Product integration, native child containment, installer/profile
binding, Owner-voice execution, compute/network admission, and Production
effects remain blocked. Current dependencies include source/native gaps in
TASK-063/070/071/075/076, TASK-099 JCV-N/canonical-consumer integration,
TASK-102 Product enrollment, accepted exact-child network isolation and the
owner amendments required for local-voice route admission.

No old design reference, public receipt, equal hash, fixture PASS, or historical
test may satisfy those live dependencies.

## Context scope

MUST READ: this Task record; D0 reconciliation; the fresh detailed design;
current TASK-043/063/066/068/070/071/075/076 and TASK-099/102 exact dependency
sections named by the design. READ IF REQUIRED: one exact owner contract needed
to resolve a contradiction. DO NOT READ BY DEFAULT: private media/model bodies,
unrelated completed Tasks, all repository history, full OS Architecture, or
native runtime state. MAY MODIFY: exact-two only. MUST NOT MODIFY: every other
path, especially historical worktrees and implementation candidates.

Escalate an unexpected main/head change, exact-two overlap, unknown dirty state,
new Critical/High design finding after two bounded correction cycles, or any
request to start source/native/build effects.

## Design verification and completion

1. Verify fresh remote main, dedicated worktree, branch and clean pre-edit state.
2. Resolve every D0 section 6 contradiction against current owner contracts.
3. Freeze disjoint execution modes, exhaustive predecessor/terminal rules,
   authority-zero fixture fields, and exact future I1 Allowed Files.
4. Obtain independent Critic and Tester results on the same candidate hashes.
5. Apply at most two bounded exact-two correction cycles, then obtain a separate
   Judge decision on the final hashes.
6. Run exact-two, ASCII-path, relative-link, secret-text, whitespace and OSS
   documentation-readiness checks.
7. Persist and read back external Evidence; commit exact-two, push the task
   branch, open a Japanese PR, and merge normally only after exact-head hosted
   checks are green.

Completion of this unit admits at most the separately implemented pure I1
candidate. It does not complete TASK-072 and does not admit a live broker.

## Recovery R3 final review receipt

The direct Owner-authorized one-finding Recovery R3 added exactly one missing
`OWNER_EXTERNAL_INPUT_RECOVERY_REVOKE_V1` inventory entry and did not reopen any
other contract. The contract candidate reviewed by all three independent roles
had these frozen hashes:

- `task.md`: `55190C52E519CD63FE5AC567BECDE38C06FD9AA60F4E869CE60092F5E949DE42`
- detailed design: `708C3FD413EB85E3C1BEF6614A770B51090D5D87E42E2EA876DC7D8EB70FE3E0`

Final results on those identical bytes were:

- Critic: `ACCEPT`, Critical/High/Medium/Low `0/0/0/0`;
- Tester: `ACCEPT`, Critical/High/Medium/Low `0/0/0/0`, OSS readiness
  `12 passed`, exact-two/scope/link/secret/whitespace/ABI-count checks `PASS`;
- Judge: `ACCEPT`, Critical/High/Medium/Low `0/0/0/0`, with
  `ADMITTED_EFFECT_ZERO_PURE_CORE_I1` established and every live/native route
  still blocked.

This paragraph and the accepted/pending status are administrative closure only.
They do not change the reviewed contract or authorize I1 before exact-head
hosted closure.

## Prohibited effects and next action

No broker source/schema/test mutation in this unit; no native preflight retry,
build, install, Product launch, private data access, provider call, dependency
or model download, Release, Deploy, Production, historical cleanup, branch
deletion, force push, or direct-main push.

The next action is external Evidence readback, exact-two commit/publication, and
exact-head hosted closure. Only the accepted design after that hosted closure
may allocate I1 implementation.
