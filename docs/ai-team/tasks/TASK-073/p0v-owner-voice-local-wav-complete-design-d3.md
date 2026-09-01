# TASK-073 P0-V Owner Voice Local WAV — Complete Design Packet D3

## 1. Identity and authority

- Task: `TASK-073`
- Atomic responsibility: `OWNER_VOICE_LOCAL_WAV_PRODUCT_COMPOSITION_V3`
- Design revision: `D3`
- Base: `origin/main@70ba9e369887d3d7ded59e7197d20d133b2b4d38`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- State: `DESIGN_REVIEW_PENDING / SOURCE_START0`
- Product entry: unified `BAI Video Production.exe`
- Runtime policy: installed local/free only; default compute preference `AUTO`
- Paid/cloud fallback: absent

D1 and D2 are immutable failed review inputs.  D3 supersedes only their
current design authority; it does not rewrite their bytes or findings.  No
producer implementation, packaged integration, native inference, playback or
Owner-audio effect is authorized by this document.

## 2. The three coequal P0 outcomes and the execution organization

The Owner has three coequal P0 outcomes:

1. `P0-V`: create the best currently accepted Owner-voice WAV locally;
2. `P0-L`: exchange privacy-safe learning data with Codex through the
   Canonical SKILL bridge;
3. `P0-E`: complete the normal UI path from model selection through planning,
   scene division, generation and export, then verify the installed EXE.

They use two design lines and three outcome lines:

| Line | Sole responsibility |
|---|---|
| Design A — Product Experience & AI | Product semantics, user flow, TASK-073/TASK-074 and the P0-E end-to-end UX contract. |
| Design B — Platform Trust & Delivery | TASK-075/TASK-076 and shared secure runtime, installer, operation and recovery contracts. |
| Outcome V — Voice/WAV | TASK-074 → TASK-075 → TASK-014 POST → TASK-048 → TASK-041/TASK-046; produces versioned receipts only. |
| Outcome L — Learning/SKILL | D2S → TASK-069 → TASK-060 → TASK-061-A → TASK-067 → TASK-036 handoff → TASK-061-B → TASK-065. |
| Outcome E — App/EXE | sole TASK-036 source integration, P0-E UI, packaging, installer, native QA and final export-path verification. |

Montage is the independent Critic/Judge and Main Merge is the task-complete
merge service.  A dependency parks only the exact gated effect.  ABI, UI,
fixtures, negative tests and unrelated accepted units continue.  A Task starts
source implementation when that Task's complete design has `C/H=0` and Judge
`PASS`; it does not wait for every other design line.

## 3. Three distinct completion results

The following results are never collapsed:

### 3.1 `TASK073_IMPLEMENTATION_COMPLETE`

Requires:

- accepted D3 and successor mock design;
- TASK-073-owned closed schema, composition, application and projection;
- application-level synthetic fixtures and all focused/negative/regression
  tests;
- independent Critic/Tester/Judge, `Critical=0`, `High=0`;
- changed-file scope readback, one coherent TASK-073 PR and canonical merge.

It excludes TASK-036 source changes, installed EXE execution and real Owner
audio.  Packaged synthetic E2E is not a TASK-073 completion requirement.

### 3.2 `TASK036_P0V_INTEGRATION_COMPLETE`

Requires a separately authorized TASK-036 P0-V amendment after:

- exact D3/mock/manifest are merged to canonical main;
- hosted checks succeed and fresh-main readback matches the accepted hashes;
- producer contracts and TASK-073 completion receipt are canonical;
- GF-B/P0-E overlapping branches are merged or explicitly disposed and their
  locks released;
- the new TASK-036 Task/Atomic Unit, exact Allowed Files and lock are recorded;
- the Owner has checked the exact mock revision.

Outcome E then owns UI wiring, packaged entry, build and installed synthetic
E2E.  No other line edits TASK-036 source.

### 3.3 `P0V_OWNER_OUTCOME_VERIFIED`

Requires one separate explicit native Human Gate and a real private E3–E5
run through the installed EXE.  Exact-current reference, runtime, output,
technical QA, full listening and TASK-046 lifecycle readbacks must all be
`PASS`.  Synthetic data, fixture data, code presence and `NOT_CONFIRMED` can
never create this result.

## 4. TASK-073 boundary

TASK-073 owns only:

- a closed non-authoritative composition document;
- deterministic request-to-receipt correlation;
- currentness/conflict evaluation over verified public-safe projections;
- Product view-model labels and actionable Japanese guidance;
- synthetic fixtures whose taint cannot be removed.

TASK-073 never owns:

- a canonical transition, selector, store, Job, Asset or Export state;
- filesystem or OS-handle I/O;
- authority mint/deserialize/burn;
- model/runtime load, child execution, network isolation or playback;
- reference processing, synthesis, WAV publication, QA or recovery;
- TASK-036 source, packaging or installer files.

## 5. Producer responsibility and authority status

| Unit | Responsibility | D3 authority status |
|---|---|---|
| TASK-074 | TASK-046-owned route selection plus Owner private-reference lifecycle and Voice action/profile amendments. | `PROPOSED / AUTHORITY0 / SOURCE_START0` until its own complete packet has C/H=0 and Judge PASS. |
| TASK-075 | Local voice inference, zero-network native boundary, private playback and runtime observations. | `PROPOSED / AUTHORITY0 / SOURCE_START0` until its own complete packet has C/H=0 and Judge PASS. |
| TASK-076 | Limited TASK-020/TASK-043 immutable-generation durable Job correction. | `PROPOSED / AUTHORITY0 / SOURCE_START0` until its own complete packet has C/H=0 and Judge PASS. |
| TASK-014 amendment | PRE callable plan, private output sink and POST WAV publication/alignment. | Separate TASK-014 owner amendment; TASK-073/TASK-075 cannot edit it. |
| TASK-041/TASK-046 amendment | Listening decision becomes one canonical Quick Clone transition/readback. | Separate owner amendment; no direct projection from raw TASK-041 decision. |

The labels above are allocation proposals, not implementation authority.  Each
Task must publish exact Allowed Files, prohibitions, acceptance and negative
tests before source mutation.

## 6. One-direction graph

```text
TASK-068 ───────────────→ TASK-076 durable Job correction

TASK-070 → TASK-063 → TASK-072 installed binding → TASK-036 P0-E context

TASK-071/072 base + TASK-013 + TASK-046
                         → TASK-074 authority/reference/selection

TASK-074 TASK-072 registry V2 canonical merge
                         → fresh-main TASK-075 TASK-072 registry V3

PR #470 canonical + TASK-014 PRE amendment
+ TASK-066 Voice admission + TASK-071 + TASK-072 V3
+ TASK-074 + TASK-076
                         → TASK-075 native inference
                         → TASK-014 POST publication/alignment
                         → TASK-048 technical QA
                         → TASK-075 private playback
                         → TASK-071 + TASK-041 decision
                         → TASK-046 lifecycle transition/readback
                         → TASK-075 exact QA/listening join

P0-E context + canonical producer completions
                         → TASK-073 composition/application receipt
                         → TASK073_IMPLEMENTATION_COMPLETE
                         → separate TASK-036 P0-V amendment
                         → TASK036_P0V_INTEGRATION_COMPLETE
                         → explicit private Owner native Gate
                         → P0V_OWNER_OUTCOME_VERIFIED
```

TASK-074 changes the TASK-072 registry first.  TASK-075 begins its registry
amendment only from fresh main after TASK-074 merge and lock release.  The two
Tasks never concurrently edit the registry.  A future single TASK-072-owner
amendment may replace this sequence only through a separately reviewed design
change.

## 7. TASK-014 PRE/POST implementation ABI

TASK-014 retains narration semantics and WAV publication ownership.  TASK-075
is only the executor.  The amendment must define these closed types.

### 7.1 `LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2`

Exact fields:

- `schema`, `record_type`, `task_owner="TASK-014"`, `profile_version=2`;
- `project_id`, `project_manifest_revision`,
  `project_manifest_sha256`;
- `operation_plan_id`, `operation_plan_sha256`, `intended_usage`;
- `quick_clone_flow_id`, `quick_clone_revision`,
  `quick_clone_revision_sha256`;
- `source_kind="TASK046_PRIVATE_REFERENCE"`,
  `private_reference_revision_sha256`;
- `voice_profile_revision_sha256`, `route_selection_revision_sha256`;
- `script_text_revision_sha256`, `style_direction_sha256`,
  `language_code`, `speaker_mode="ZERO_SHOT_LOCAL"`;
- `model_recipe_sha256`, `runtime_recipe_sha256`;
- `sample_rate_hz=48000`, `channels=1`, `sample_format="PCM_S24LE"`;
- `max_frames`, `created_at`, `expires_at`;
- `fixture_only`, `authority_created`, `production_eligible`;
- `call_profile_sha256`.

The profile carries no script body, raw path, OS handle, model path, clock,
backend choice or capability.  For a real operation its project, Quick Clone,
reference, profile, selection and script revisions must be exact-current in a
single trusted resolver observation.  The current V1 TASK-003 Asset contract
is not reinterpreted; V2 is the explicit private-reference bridge.

### 7.2 `NARRATION_OUTPUT_SINK_CAPABILITY_V1`

This is a private, in-process, non-serializable one-use capability minted by
the TASK-014 trusted operation.  It binds:

- exact call-profile, operation plan, Project and installed session;
- artifact class `STAGED_NARRATION_PCM_WAV_48000_MONO`;
- expected format and maximum frame count;
- expected predecessor/output generation and private staging policy;
- a pinned TASK-014-owned output handle and currentness lease;
- state `READY → IN_FLIGHT → CONSUMED | FAILED_CLOSED`.

No public dataclass, mapping, module token, path or receipt can recreate it.
TASK-075 receives the live capability, writes once through the owned handle and
cannot publish, reopen, choose or clean the destination.

### 7.3 `TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1`

TASK-075 returns a private typed result bound to the call profile and sink:

- operation/plan/profile digests;
- exact admitted model, runtime, engine and effective backend identities;
- offline/native-isolation and one-child/one-generation receipt digests;
- waveform digest, frame count and observed format;
- output-handle identity digest and terminal execution outcome;
- fixture lineage and body/path-free public projection.

It is execution evidence only and cannot claim WAV publication or alignment.

### 7.4 `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1`

TASK-014 consumes the exact result and already consumed sink capability, then
publishes/read-backs:

- all PRE/operation/Project/Quick Clone bindings;
- TASK-075 result and output-handle identities;
- immutable staged WAV reference/hash;
- exact `48000 Hz`, mono, signed PCM24, sample count and duration;
- script/alignment result and boundary evidence;
- publication generation/predecessor/currentness;
- terminal status and fixture lineage.

Fault seams are required before sink acquisition, after acquisition, before
first write, after body write, before sink consume, after consume, before
publication, after publication and before readback.  Unknown state causes no
automatic retry, cleanup, backend switch or re-publication.

## 8. The only listening-to-lifecycle path

TASK-041 owns the listening decision semantics; TASK-046 owns the canonical
Quick Clone lifecycle.  D3 requires this one path:

```text
TASK-075 full/partial playback observation
+ TASK-048 exact QA
+ TASK-071 Human decision receipt
→ TASK-041 OWNER_VOICE_LISTENING_DECISION_V2
→ TASK-046 apply_owner_listening_decision amendment
→ QUICK_CLONE_FLOW_READBACK_V2
→ TASK-075 QA_LISTENING_JOIN_V1
→ TASK-073 projection
```

`OWNER_VOICE_LISTENING_DECISION_V2.decision` is closed to
`ACCEPT | REJECT | RETEST`.  TASK-046 V2 adds the corresponding lifecycle
states `ACCEPTED | REJECTED | RETEST_REQUIRED` while preserving historical V1
read compatibility.  The transition binds the TASK-041 decision receipt,
TASK-071 Human receipt, exact QA, WAV and playback candidate.  Only the
TASK-046 readback may yield `WAV_ACCEPTED`, `WAV_REJECTED` or
`WAV_RETEST_REQUIRED` in TASK-073.

`RETEST` replays the same candidate through a new bounded playback session and
does not generate audio.  `REGENERATE` is a separate TASK-071/TASK-014 action
that creates a new operation plan and candidate generation.  Neither action
may substitute for or replay the other.

## 9. Closed TASK-073 composition schema

`OWNER_VOICE_LOCAL_WAV_PRODUCT_COMPOSITION_V3` has exactly these top-level
fields:

```text
schema
record_type
task_owner
composition_id
composition_revision
project_binding
installed_session_binding
operation_plan_binding
quick_clone_binding
selection_binding
reference_binding
job_binding
inference_binding
wav_binding
qa_binding
listening_binding
producer_receipts
derived_state
reason_codes
fixture_lineage
observed_at
composition_sha256
```

Every `*_binding` is a closed object with:

```text
owner_task
receipt_type
schema_version
opaque_ref
receipt_sha256
producer_build_sha256
project_binding_sha256
installed_session_sha256
operation_plan_sha256
revision
head_sha256
observed_at
expires_at
current
fixture_only
authority_created
production_eligible
```

Only the following producer versions are accepted in V3:

- `INSTALLED_STARTUP_CONTEXT_V1`;
- `QUICK_CLONE_FLOW_READBACK_V2`;
- `TASK074_OWNER_VOICE_AUTHORITY_COMPLETION_RECEIPT_V1` and its exact
  selection/reference projections;
- `TASK076_DURABLE_PRODUCT_JOB_READBACK_V1`;
- `TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1`;
- `TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1`;
- `TASK048_OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1`;
- `TASK075_VOICE_PLAYBACK_OBSERVATION_V1` and
  `TASK075_VOICE_QA_LISTENING_JOIN_V1`.

Unknown fields, versions or owners are rejected.  The resolver accepts one
exact-current receipt per slot.  Repeated byte-identical/hash-identical
observations collapse to one; two different receipts for the same coordinate
produce `BLOCKED/MULTIPLE_CURRENT_RECEIPTS`.  All non-null Project, installed
session, Product build, operation plan and Quick Clone heads must match.  Every
required `current` must be true and every expiry must be after the trusted
observation time.  Missing, stale, mismatched or ambiguous input produces a
stable body-free reason and no success state.  TASK-073 never chooses the
newest timestamp, highest revision or first file.

### 9.1 Fixture taint

`fixture_lineage` contains:

```text
fixture_only
authority_created
production_eligible
fixture_set_sha256
producer_fixture_count
```

The composition calculates, rather than accepts, these values.  If any input
is fixture-only, lacks real authority or is production-ineligible, output must
be `fixture_only=true`, `authority_created=false`,
`production_eligible=false`.  The fixture-set digest binds every tainted
producer receipt.  Dropping, relabelling, mixing or rehashing a marker is a
closed failure.  Fixture-tainted output can produce only synthetic UI states,
never Task036 real integration or Owner outcome authority.

## 10. Derived UI states

TASK-073 stores none of these labels:

| UI state | Sole exact evidence |
|---|---|
| `SETUP_REQUIRED` | Missing installed session or accepted producer version. |
| `REFERENCE_REQUIRED` | Current TASK-046/TASK-074 private reference absent. |
| `MODEL_SELECTION_REQUIRED` | Current TASK-074 selection absent. |
| `READY_TO_RENDER` | Current PRE profile, reference, selection, Task066 admission and operation plan. |
| `CONFIRMATION_REQUIRED` | TASK-071 plan current and ticket not consumed. |
| `QUEUED/RUNNING/RECOVERY_REQUIRED/UNKNOWN` | TASK-076/TASK-075 exact Job/runtime readback. |
| `QA_REQUIRED` | Current Task014 POST, Task048 QA absent. |
| `LISTENING_REQUIRED` | QA PASS, TASK-046 listening transition absent. |
| `WAV_ACCEPTED/WAV_REJECTED/WAV_RETEST_REQUIRED` | Exact current TASK-046 V2 readback plus Task075 join. |

## 11. Successor mock and scoped Owner Gate

The D3 mock preserves the canonical V6.1.1 stage bar exactly:

`H, 1..11, A, Q`, with `音声制作` remaining stage `7`.

Its Voice Signal Rail uses one consistent order:

`参照 → モデル → 生成 → QA → 試聴`.

It visibly separates Play, Stop, Accept, Reject, Retest and Regenerate.
Retest does not create a new candidate; Regenerate does.  All mock operations
are in-memory and carry `MOCK ONLY`.

The Owner Gate blocks only the new P0-V Voice Studio successor/P-VS-1B
TASK-036 amendment.  It does not block unrelated TASK-036 work.  That
amendment remains `START0` until the exact D3/mock/manifest are canonical with
hosted checks and fresh-main hash readback, the Owner checks the exact mock,
and the separate TASK-036 authority/Allowed Files/lock exists.

## 12. Acceptance

1. Three completion results remain distinct and independently reportable.
2. TASK-073 has no authority, I/O, process, playback, QA or recovery effect.
3. TASK-036 remains the sole Shell/package source owner.
4. TASK-014 PRE/POST and sink/result ABIs are exact and private-reference
   compatible without changing V1 semantics.
5. TASK-041 decision changes TASK-046 before TASK-073 may project acceptance.
6. TASK-074/075 registry changes are serialized V2 then V3 on fresh main.
7. Every composition field, producer version, coordinate and conflict rule is
   closed and deterministic.
8. Fixture taint is calculated, preserved and cannot produce real authority.
9. UI model preference and effective backend are separate.
10. Ollama state neither blocks nor authorizes Voice.
11. Local runtime has no paid/cloud fallback and no automatic retry.
12. WAV is exactly 48 kHz, mono, signed PCM24 and Task014-owned.
13. Accept/Reject/Retest/Regenerate are separate and non-replayable.
14. The mock retains all V6.1.1 destinations, Play/Stop and the exact flow.
15. Private audio/text/path/token/identity never enters public UI/log/Evidence.
16. WAV acceptance does not adopt Dataset, train, adopt Asset, place Timeline
    media or Export.
17. Real Owner data remains behind a separate private native Human Gate.

## 13. Required negative and fault coverage

- direct/copy/pickle/deserialize/subclass/rehashed public authority objects;
- unknown producer/version/field, missing slot, stale/expired projection;
- identical duplicate versus conflicting multiple-current receipts;
- cross-Project/install/session/build/operation/Quick Clone head;
- fixture marker removal, real/fixture mixing and tainted output promotion;
- TASK-041 ACCEPT with TASK-046 `REQUIRED`, wrong WAV/QA/playback receipt;
- RETEST used as REGENERATE or vice versa;
- V1 Task003 Asset call profile supplied to the V2 private-reference path;
- sink capability copy, second/concurrent use, exception reuse and path
  substitution;
- result without offline/native receipt, wrong backend/model/runtime or more
  than one generation;
- POST publication without exact sink/result, wrong format/alignment,
  publication/readback ambiguity;
- raw path/UNC/reparse/hardlink/ancestor/inode change;
- GPU failure fallback, CPU CUDA initialization, Ollama coupling;
- mock without 14 canonical destinations, Stop, Retest or separate Regenerate;
- public audio, transcript, path, Voice ID, SID/PID, token, secret or OS error.

Every negative asserts Project, Bridge, private reference, Job, WAV,
VoiceProfile, Asset, Timeline, Export and unrelated sentinel deltas separately.
Required fault seams include resolver read races, TASK-014 PRE/sink/POST seams,
TASK-075 child/result/playback seams, TASK-041→TASK-046 commit/readback seams
and UI projection between producer revisions.  Unknown state is preserved for
the producer owner; TASK-073 never repairs or retries.

## 14. Implementation and PR order

1. Freeze D3/mock/manifest and obtain independent C/H=0 Judge PASS.
2. Canonicalize each TASK-074/075/076 complete design; Task074 registry
   amendment precedes Task075 registry amendment.
3. Implement TASK-073 closed schema/composition/projection with synthetic
   fixtures; missing producer receipts keep only affected states blocked.
4. Complete producer Task implementations in their outcome lines.
5. Rebind TASK-073 to canonical producer completion versions and close one
   coherent TASK-073 PR.
6. After canonical Task073 receipt and exact Owner mock check, Outcome E opens
   one separate TASK-036 P0-V integration Task/PR and runs packaged synthetic
   E2E.
7. Run real Owner E3–E5 only through the separate explicit private native Gate.

No design PR is fragmented into small partial PRs.  A Task creates its design
PR only after its full assigned design is complete.  A completed design line
may assist another line only through a non-overlapping, explicitly owned design
unit; it cannot overwrite another Task's responsibility.

## 15. Prohibitions and review gate

- no Product source until D3 has independent `Critical=0`, `High=0`, Judge
  `PASS`;
- no TASK-036 P0-V mutation until the narrower canonical/mock/Owner/authority
  Gate in section 11 passes;
- no paid/cloud provider, model download, Release, Deploy or Production
  Activation;
- no Owner audio/transcript/embedding/model weight in Git, PR, logs or public
  Evidence;
- no Dataset adoption, training dispatch, ModelCandidate approval, Asset
  adoption, Timeline placement or Export;
- no direct TASK-070 state, raw path/backend/clock/security-hook input;
- no force push, unknown dirty discard or shared-state mutation outside the
  sole-Builder lock workflow.

`SOURCE_START0` remains until this exact D3 identity completes review.  Owner
approval cannot convert unresolved Critical/High findings into PASS.
