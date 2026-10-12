# TASK-072 Operation Ticket Currentness Reconciliation R0

Status: `DESIGN_CURRENTNESS_CANDIDATE / DEV-4 / SOURCE_EFFECT_0 / SOURCE_ADMISSION_BLOCKED`

Design identity: `TASK072-ODCR-D0-R0`

Review parent: `main@7d1ae8a809c4e603b4e02cf701b5c71437e5fbdb`

Owner allocation: `2026-10-12 / serialized BVP dependency-unblocking lane`

## 1. Decision

TASK-072 retains one coherent Product responsibility: create and consume a live,
one-shot, non-Human machine-operation capability and own exact-child containment
through a known or explicitly unknown terminal. That responsibility remains
required by current TASK-063/066/070/071/075/076 contracts and is not owned by a
different Task.

Canonical main, however, contains no TASK-072 Task record, design packet,
broker/config source, schemas, fixtures or focused tests. References from other
Tasks are dependency expectations, not implementation or authority. This unit
therefore establishes canonical responsibility and currentness only. It does
not import a historical design or source tree.

Source admission is explicitly `BLOCKED_PENDING_FRESH_DETAILED_DESIGN`.

## 2. Exact scope

This unit changes exactly:

1. `docs/ai-team/tasks/TASK-072/task.md`;
2. `docs/ai-team/tasks/TASK-072/operation-ticket-currentness-reconciliation-r0.md`.

It changes no Product source, schema, test, fixture, package, installer,
CHANGELOG, shared current-state, roadmap, index, registry or historical worktree.
No native/build/install/Product/private/provider/download/Release/Deploy/
Production action is part of this unit.

## 3. Current-main responsibility boundary

TASK-072 owns:

- server-held, live, nonserializable one-use operation authority;
- closed action/profile selection from fixed Product composition;
- authenticated Product parent and exact-child channel binding;
- broker boot/session, exact user/session/build/process and invocation-budget
  binding;
- mode-specific immutable config creation/readback when required;
- serialized child create, Job containment, restricted handle transfer, start,
  abort and broker-close behavior;
- exact known terminal or completion-unknown classification;
- body-free audit/status projections that never recreate authority.

TASK-072 consumes but does not own:

| Owner | Canonical responsibility consumed by TASK-072 |
|---|---|
| TASK-068 | immutable secure I/O primitives and physical readback; never current-head selection |
| TASK-043 / TASK-076 | Project/Job currentness, durable Job events, generations and Artifact semantics |
| TASK-063 / TASK-070 | installer plan/pair/terminal semantics and current installed-instance handoff |
| TASK-071 | live Human authorization for Human-gated actions |
| TASK-066 | compute admission and enforceable network-isolation producer evidence |
| TASK-075 and other consumers | operation-specific semantic plan, result and reconciliation truth |

TASK-072 never owns private model/reference content, Dataset/Consent/rights,
consumer result meaning, Provider selection, downloads, release, deployment,
production activation or physical cleanup.

## 4. Current-main observations

At review parent `7d1ae8a809c4e603b4e02cf701b5c71437e5fbdb`:

- `docs/ai-team/tasks/TASK-072/` is absent before this candidate;
- no path matching TASK-072, product-operation or operation-ticket source,
  schema, fixture or test exists under `src/`, `schemas/` or `tests/`;
- TASK-076 requires TASK-072 exact child redemption/terminal proof and owns the
  current V2/V3 durable Job protocol;
- TASK-075 names TASK-072 ticket/begin/containment dependencies but also refers
  to historical R4. That reference does not make the unmerged R4/R7 packet
  canonical;
- TASK-071 expects mutual live broker/channel/profile binding but does not
  implement TASK-072;
- TASK-066 owns compute/network producer truth; TASK-072 may only consume an
  accepted producer receipt and bind it to the exact child;
- TASK-063 post-repair native terminal handoff remains not confirmed, and the
  separately accepted TASK-066 GF-E source/build paths are absent. Those facts
  blocked the preceding native build lane with `build_count=0` and
  `launch_count=0`; they do not authorize a TASK-072 build or source import.

## 5. Historical inventory and exact classification

### 5.1 Closed draft PR #475 and clean historical design

- PR: `https://github.com/baisound/bai_video_production/pull/475`
- state: `CLOSED`, draft, never merged;
- closed at: `2026-09-02T09:30:43Z`;
- head: `52203bc9962340016f4b7ac494ea02d25202484d`;
- design path blob OID:
  `1987213495cf3f42b19440f31f1cfcabb5a49398`.

Classification: `HISTORICAL_INPUT_ONLY`. The responsibility concept may inform
this reconciliation, but no text, ABI or source authority is adopted merely
because the draft once existed.

The later clean design branch head is
`fef5bf8469ad26eb1d18e39190bbdf303150dacb`, with design blob OID
`a9726c5e328b6ec5bc1f319f555302a6fd7a5156`. It also never reached canonical
main and is not an accepted source gate.

### 5.2 User-owned dirty R7 worktree

- worktree:
  `C:\home\baisound\projects\bai-video-production\.worktrees\task-072-operation-ticket-design-r6`;
- branch: `codex/task-072-operation-ticket-design-r6`;
- clean HEAD: `fef5bf8469ad26eb1d18e39190bbdf303150dacb`;
- dirty path:
  `docs/ai-team/tasks/TASK-072/complete-design-packet.md`;
- raw working-file bytes: `93201`;
- raw working-file lines observed by PowerShell: `1552`;
- raw working-file SHA-256:
  `76BF8925DC1E8CA41243F028456CD8D67CFDA78B63947AF90F98964850E9FD5E`.

Classification: **`PARKED`**.

The working file's own administrative receipt records Critic
`FAIL_R7_C0_H3_M1_L0`, Tester `FAIL_R7_C0_H1_M0_L0`, Judge not run and
`design_frozen=false`. Its open High clusters concern:

1. TASK-076 V3 issue/arm timing and a not-yet-created vector identity;
2. wrong external-slot bind/preflight/recovery ABI mapping;
3. fine-tuned routing incorrectly inheriting zero-shot reference/V3
   requirements;
4. uncertain arm publication without one unambiguous terminal predecessor.

The worktree and bytes are preserved. This candidate does not copy, normalize,
amend, stage, reset, commit or clean that file. The parked content is rejected
as implementation or canonical-design authority while remaining historical
evidence.

### 5.3 Closed draft PR #515 and historical A1 source

- PR: `https://github.com/baisound/bai_video_production/pull/515`
- state: `CLOSED`, draft, never merged;
- closed at: `2026-09-05T14:53:38Z`;
- head: `6a0d11ac985c7cb4b420cf1a8980b083379dfec6`;
- current-main merge base: `b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`;
- detailed-design blob OID:
  `a3c12feb120dd66d4e7982e6f4acfb06a23ecbd5`.

The branch contains historical broker/config source, three root schemas and
package mirrors, two focused tests, two fixtures, evidence, design and an
obsolete `CHANGELOG.md` edit. Its own evidence reports exact historical
SHA-256 values and focused results, but the branch predates the current
TASK-076 V2/V3 contract and the rejected R7 findings.

Classification: `REJECTED_FOR_ADOPTION`. The commit and its existing clean
worktree remain preserved. No cherry-pick, copy, merge, rebase, source test,
CHANGELOG edit or cleanup is allowed in D0.

## 6. Currentness contradictions to resolve before source

A future detailed design must close all of the following against the current
main versions, without treating an old consumer reference as canonical source:

1. **V2/V3 phase ownership.** TASK-072 must define exactly where its one-use
   budget is consumed relative to TASK-076 DISPATCHING, IN_FLIGHT, arm,
   bootstrap create, external bind, preflight, release, abort and terminal
   publication.
2. **Terminal predecessor truth.** Every known/unknown terminal requires one
   legal predecessor and mode-specific proof. Missing fields cannot be promoted
   to no-effect truth, and an unknown result cannot be fabricated as a digest.
3. **Mode separation.** Child-channel, in-process owner transaction and
   sensitive V3 child paths require closed, disjoint fields and transitions.
   One mode cannot borrow another mode's config, child, channel or Job fields.
4. **Current producer ABI versions.** TASK-063/066/068/070/071/075/076 inputs
   must be named by exact accepted type/version/owner and classified as
   canonical, fixture-only or dependency-not-current.
5. **Fine-tuned versus zero-shot routing.** Private references, model custody,
   external binding and V3 requirements must follow the exact selected consumer
   route rather than an overbroad owner-voice category.
6. **Containment and recovery.** The sole Job containment handle, child kill on
   broker close, recovery-only query, no replay, and public authority-zero
   projection must be explicit and testable.
7. **Source scope.** New source/schema/test files must be freshly allocated.
   Historical A1 bytes are not a baseline and CHANGELOG remains excluded unless
   an actual Product version change is separately authorized.

## 7. Source-admission gate

This D0 gate returns:

```text
responsibility_owner: TASK-072
responsibility_current: true
canonical_task_record_before_D0: absent
historical_R7_classification: PARKED
historical_A1_source_adoption: REJECTED
source_admission: BLOCKED_PENDING_FRESH_DETAILED_DESIGN
source_effect: 0
schema_effect: 0
test_effect: 0
native_effect: 0
build_count: 0
launch_count: 0
release_deploy_production_effect: 0
```

Source may be admitted only by a later separately allocated detailed-design
unit that:

- starts from then-current remote main;
- names exact dependency versions and resolves section 6;
- freezes exact source/schema/test Allowed Files without CHANGELOG by default;
- receives independent DEV-4 Critic and Tester results with unresolved
  Critical/High `0/0` and a Judge `ACCEPT`;
- persists and reads back canonical external Evidence;
- explicitly changes `source_admission` to an admitted bounded source unit.

No standing implementation rule may bypass those conditions because D0 records
an explicit source gate.

## 8. D0 verification and acceptance

Required checks:

- exact base/branch/worktree and clean pre-edit state;
- exact-two diff and Allowed-Files match;
- ASCII documentation path names;
- local relative-link resolution;
- current main has no preexisting TASK-072 canonical files/source;
- historical commit/PR/worktree identities and R7 raw hash read back;
- no copied block from the dirty R7 or old A1 source/design beyond bounded
  identity/finding summaries;
- no source/schema/test/fixture/CHANGELOG change;
- no secret, private path body, credential or authority-bearing value;
- independent Critic, Tester and Judge on the same frozen candidate;
- canonical external Evidence write and readback;
- Japanese PR and all hosted checks green before normal merge.

Acceptance of D0 canonicalizes only responsibility, historical classification,
currentness gaps and the source gate. It does not accept R7, adopt A1, create a
ticket, admit a child, satisfy TASK-063/066 native prerequisites, or authorize
build/install/Product/private/provider/download/Release/Deploy/Production work.

## 9. Failure and recovery

- If current main changes any exact-two path or a dependency contradicts this
  boundary, stop and re-reconcile; do not overwrite.
- If the dirty R7 worktree identity/hash changes, record the new observation
  without modifying it and re-run classification.
- If a reviewer finds a Critical/High issue, correct only exact-two and re-run
  all independent roles. After two bounded cycles, stop and escalate.
- If publication head changes after review, reviews and hashes are stale.
- Hosted failure permits a bounded docs-only fix only when it stays exact-two;
  otherwise return to design review.
- Never repair by importing old source, weakening current owner contracts,
  deleting historical worktrees or retrying a native/build lane.
