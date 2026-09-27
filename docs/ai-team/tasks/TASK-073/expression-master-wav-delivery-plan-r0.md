# Expression Master WAV delivery plan R0

## 1. Binding, authority and completion boundary

- Project: BAI VIDEO PRODUCTION; design coordinator: TASK-073.
- Atomic Unit: `EXPRESSION-MASTER-WAV-PLAN-R0`; date: 2026-09-27.
- Baseline: main/origin/main `e41110c85ba4ab098c591378cb1b2eaae3cc3cb7`.
- Owner request: formally determine remaining Tasks and settle detailed design for changing expression in the Owner's voice and producing one WAV.
- Additional Owner instruction: take over both unallocated connection contracts. TASK-099 and TASK-100 are owned end-to-end by this voice-integration thread (`01a054d9-2cf9-71e2-a486-351727c13150`), including design, implementation and verification. They are not waiting for reassignment. Implementation intent is accepted; exact implementation units/files must still be bound before mutation, and native gates remain unchanged.
- Depth: DEV-4, cross-owner contracts, private media and authority boundaries. Independent architecture audit, Critic and Tester are required. This unit is **design/documentation only**. Neither this plan nor its reviews authorize implementation, model loading, audio reads, inference, playback, installation, downloads or external repository changes.
- This is a new delivery overlay, not a replacement or retrospective alteration of the accepted TASK-073 D4-R4 bundle. Existing producer contracts remain authoritative until each proposed amendment is reviewed, merged and read back.
- Current Allowed Files: this document, `expression-master-wav-task-ledger-r0.json`, `expression-master-wav-plan-review-r0.md`, `evidence/expression-master-wav-plan-checkpoint-r0.md`, and new design-only `TASK-099/task.md`, `TASK-100/task.md`, `TASK-101/task.md`. TASK-101 is a review-required design allocation under the original design request, not an inferred implementation/native authorization. No shared current-state/task-index/roadmap/CHANGELOG, source, schema, tests, OS or external voice repository changes.

**Done means:** the normal BVP entrypoint lets the Human choose an admitted existing Owner model, assign at least two audibly distinct expressions within one approved script, generate ordered segments, save one technically passing `48 kHz / PCM24 integer / mono` Master WAV, play that exact output, and explicitly accept it. The saved artifact is a **private-staging narration WAV**, not a canonical Asset, publication or Production activation. Save/readback remains TASK-014/076 responsibility; TASK-073 does not write WAVs.

The proposed output coordinate is `PRIVATE_STAGING_NARRATION_MASTER_V1`: exact project/plan/candidate/Job/artifact digest and physical readback, format/sample count, QA and listening identities. Its closed schema must forbid `asset_id`, canonical Asset promotion/adoption and Timeline/Export fields. Here “persist” means private-staging persistence only; no canonical Asset publication is implied.

The first acceptance fixture uses one model pair and two styles, `CALM_EXPLAINER` and `EMPHATIC_NOTICE`, in a short 2–4-segment Japanese script. These are proposed test labels, not claims about engine capability. Exact approved script, reference material and acoustic profiles must be frozen at M1 before native work. An approximately 60–90-second example is a test target, not a forced duration or speech-compression rule. Broader styles, arbitrary-length performance and extra engines are subsequent scope.

Out of scope: new OBS recording, new Dataset/training, TASK-047 terminal capture, TASK-098 A5, canonical Asset adoption, Timeline/Resolve, Export, Release, Deploy, paid/cloud calls, Production. Existing TASK-097 second-training completion and model selection are retained as historical Evidence; no completed training is repeated.

## 2. Formal count and current reality

**Formal remaining count: 17 distinct Task responsibility lanes** at the bound baseline: 10 direct outcome owners + 5 shared platform owners + 2 connection successors. The direct outcome group contains 9 existing Tasks and one new existing-model-import custody successor, TASK-101: **14 existing + 3 new design allocations in total**. TASK-101 replaces, rather than adds to, TASK-084 on this no-training path; independent review rejected expanding training-terminal custody into imported-model custody. The Owner's explicit end-to-end takeover covers connection Tasks099/100; Task101 is design-only here. This counts only each lane's outstanding delivery obligation, not all historical work in that Task and not PRs, reviews or Atomic Units. Foundations already implemented are reused. A lane leaves the count only when its exact required completion/readback is verified; historical `HOSTED_CLOSED` alone is not live outcome completion. Canonical metadata allocation of TASK-099/100/101 must be serialized against a fresh Task-ID/lock audit before integration; this branch reserves their design definitions and grants no source authority.

| Task | Outstanding obligation for this outcome | Current baseline assessment | Delivery owner |
|---|---|---|---|
| TASK-046 | Existing-model import reconciliation, current lineage/Consent/rights, H4 model approval and binding | Owner selection and training Evidence exist; current admitted import path not proved | VoiceProfile/model lineage |
| TASK-101 | Protected existing-model import custody/readback and bounded load lease | New design-only successor; TASK-084 remains training-terminal-only | Imported-model custody |
| TASK-014 | Expression plan, C04 render admission/adapter, Cue POST, assembly and private-staging persistence | Pure admission and Qwen CLI exist; this C04 Product render path not verified | Narration |
| TASK-074 | Current route selection and private reference/transcript custody | R13 design; live handoff/version closure pending | Selection/reference |
| TASK-075 | Trusted local inference, PCM handoff, playback/listening binding | R6 design review exists; exact live producer chain not confirmed | Execution/listening |
| TASK-076 | Durable Job/event/readback and restart/ambiguous recovery | V5 design; currentness producer missing | Durable Job |
| TASK-048 | Version-pinned real Cue and whole-Master QA | Metadata foundation closed; real QA profile/producer pending | Technical quality |
| TASK-041 | Exact-output Human listening decision | Foundation exists; live decision producer for this lane pending | Human review |
| TASK-073 | Updated receipt correlation/projection and synthetic outcome contract | D4-R4 accepted; tracked pure composition is not full integration | Composition only |
| TASK-036 | Normal Product Shell controls and packaged outcome connection | Separate P0-V mock check/integration/native closure pending | Shell |
| TASK-063 | Exact installed startup/runtime readback | Foundation/source exists; relevant live readback not confirmed | Installation identity |
| TASK-066 | Compute, CPU/GPU policy and network-egress enforcement/readback | Accepted design; native proof pending | Compute admission |
| TASK-068 | Secure immutable I/O and required native proof | Canonical R6 exists; foundation lane has pending native/successor work | Secure I/O |
| TASK-071 | Live Human action registry/receipts required by voice chain | Required V2 voice actions not confirmed | Human authority |
| TASK-072 | One-shot ticket/native child containment/playback authority | Required producer named by accepted 073/075/076 designs; dedicated Task record/source completion absent from bound main | Native broker |
| TASK-099 | `PROJECT_JOB_CURRENTNESS_READBACK_V2` and secure selected-head update | New successor of closed TASK-043; this thread owns delivery | Project currentness / this thread |
| TASK-100 | Body-free pinned local model/runtime catalog candidate | New successor of closed TASK-013 catalog responsibility; this thread owns delivery | Catalog admission / this thread |

Evidence anchors: TASK-076 complete-design-packet §7.7 explicitly rejects legacy Project store/generic lock as V2 currentness; TASK-043 is hosted-closed. TASK-074 assigns catalog to TASK-013; no current C04/stable2.0.1 route record was found in scoped canonical source/schema/tests. External installation is not Product catalog admission. If a fresh exact catalog readback later proves the obligation already satisfied, close TASK-100 by evidence/no source change: **do not silently rewrite this historical count to 16**. Record remaining count 16 in a new current revision. Any additional capability requires an explicit scope/count change, never an unlisted dependency hidden inside implementation.

External public model documentation reports Stable v2.0.1, unchanged weights from v2.0.0, and existing C04 standalone synthesis. BVP's older public-release-pending wording is stale Evidence and not a blocker to this route. It also does not prove BVP admission, expression support or end-to-end acceptance. Selected pair identities are SoVITS `76a492931f97cd349c6d7d6f04bab4f2442fa9890a5a40708a1d49f919f8e0ff` and GPT `4dd990db49d56bdaff6c4988635c46b58f73e1d719297570f0d361184fd60745`; no private path/body is published here.

TASK-047 is not a prerequisite for **reuse without new capture/training**. TASK-082/083/084/088/089/090 are not newly added to this critical path; if imported lineage cannot be established, block import and seek exact reconciliation rather than inventing training/capture receipts or enrolling their full pipelines. TASK-084's training-terminal/H3 branch is preserved and excluded, not silently amended into an import route. TASK-089's accepted role matrix excludes narration and cannot receive this final WAV. No generic server health result or file hash is a capability.

TASK-072's count is backed by the existing producer responsibility in TASK-073 D2 §§7.3/8 and the accepted TASK-075 R6 review receipt, not by an observed `TASK-072/task.md` (absent on this baseline). M1 must obtain the owning lane's canonical Task/authority/profile/readback and resolve this metadata gap before any broker consumer implementation. The absence is recorded as `NOT_CONFIRMED`, never a completed native prerequisite or an additional new model/capture Task. Do not invent 072 authority locally or treat its reference in this ledger as an implementation allocation.

## 3. Milestones and critical dependency order

Task-level relations contain legitimate model/QA/approval feedback. The execution schedule is therefore an acyclic **Atomic Unit/milestone** graph, not a misleading acyclic Task graph.

| Milestone | Owner units / exit evidence | Predecessors |
|---|---|---|
| M0 | This exact count, owner boundaries, proposed amendments and independent design review | none |
| M1 | 046/101 existing-model import contract + H4 route; 100 catalog contract; 014 expression/assembly contract; 048 QA policy; 074/075/076/071/072/066/073 exact ABI matrix | M0 |
| M2 | 068 native I/O receipt; 063 installed readback; 066 compute/no-network receipt; 071 action registry; 072 broker; 099 currentness transaction; each independently tested and canonical | M1 |
| M3 | 046/101 imported model admitted; 100 catalog readback; 074 route and private reference admitted; 076 durable Job implementation/readback | M2, M4 |
| M4 | 014/075 synthetic adapter/sink/assembly integration, 048 real-QA producer contract implementation, 041 decision implementation; no private effects and no live admission claim | M1 |
| M5 | 073 versioned receipt projection; explicit Owner mock check; separate 036 scope, Shell and packaged synthetic test | M4 |
| M6 | Exact native effect authorization/preflight; real expression Cue renders; QA, Master assembly/save/readback and whole-output QA | M2, M3, M5 |
| M7 | 075 bounded playback of exact Master; 041 Human ACCEPT; restart/save readback; final 073 projection and independent integration review | M6 |

M1 design units can be reviewed independently; M2 foundation work can proceed in its existing owner lanes. M4 and M5 synthetic implementation do not wait for M2/M3 private/native admission: fake-port tests are allowed only under their own exact source allocations and cannot mint live authority. These milestone edges are completion barriers, not a prohibition on independent authorized per-lane design/pure-source work. This coordinator does not edit or silently take over other owners' sources. Dispatch is by verified owner completion receipt, not repeated polling, repeated context import or messages without Owner coordination authority. A blocked independent producer parks only its downstream branch. M6 may not use a standalone CLI to bypass M2–M5 and then claim a BVP outcome.

Each unit must carry exact Allowed Files, base/head, authority, inputs/ports, acceptance cases, independent roles, output roots and external checkpoint before implementation. No implementation starts on this plan alone. Foundation amendments are implemented once, with all consumers pinned to their merged version; no sequence of ad-hoc ABI aliases or repeated redesign of already accepted sections.

The dispatch-level prerequisite graph is recorded separately in the ledger. In particular: 099 pure work waits only for its own design; its native backend waits for068 transaction prerequisites. 100 pure work uses accepted046/101 fixtures and the existing inventory, not live private admission. 101 native import waits for its approved custody backend and046 reconciliation, not full076/Shell completion. 048 QA and041 decision pure contracts do not wait for model import. 074 live route waits for099/100/071/072;076 live Job waits for068/099/072. Only the real outcome waits for every required live receipt. These edges allow safe parallel owner work without parallel mutation of dependent slices by this Builder.

046 reconciliation must explicitly settle existing evaluation/approval Evidence before current H4. If fresh model evaluation is required,046/048 must bind its separate evaluation operation before H4; do not borrow a narration ticket or fabricate an EvaluationReceipt to solve that dependency. This is a named M1 readiness condition within those existing owners, not an unlisted new training Task.

## 4. Contract freeze inventory

The following is the required M1 freeze list. `PROPOSED` names are design coordinates, **not** accepted producer receipt types. All byte/hash/version changes need a new reviewed bundle/readback. Existing legacy consumers must reject new versions until explicitly amended.

| Interface | Producer -> consumer | Required reconciliation |
|---|---|---|
| Existing-model reconciliation / protected import (PROPOSED V1) | 046 + 101 -> 014/100/075 | Preserve historical Dataset/run/model identities as verified lineage, not current training authority. Strict tagged producer union: `TRAINING_TERMINAL` accepts084 contracts only on its separate training route; `EXISTING_MODEL_IMPORT` accepts101 contracts only on this route. No rehash/alias/cross-variant fields; 084 source/history unchanged. Bind pair, custody, current Consent/rights/license/runtime/operation |
| FineTunedModelBinding / current H4 | 046 -> 014 | Handoff selection is not current H4. Exact parent/import receipt and evaluation/approval identity, expiry/revocation checked at use |
| LocalVoiceCatalogCandidate (PROPOSED V1) | 100 -> 074/014/073 | Body-free engine/runtime/model/capability/rights candidate; no private handles, load authority or parallel inventory |
| PROJECT_JOB_CURRENTNESS_READBACK_V2 | 099 -> 076/074/072 | Exact manifest physical identity, revision/predecessor, ABSENT or SELECTED Job head, namespace digest, install/security/time and consumer operation; legacy 043 not an alias |
| LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2 / POST | 014 -> 075 -> 014 | Exact input plan, model/reference/compute/ticket/Job/sink and operation; fresh per-Cue admission; Master assembly is separately bound operation |
| Private reference / JobChildArmed | 074 <-> 072/076/075 | R13/R14 and V2/V3 proposals must resolve into one accepted version matrix before coding; older V2 receipt cannot be rehashed as V3 |
| Compute admission | 066 -> 014/075/073 | Reconcile 073 `AUDIO_VOICE_COMPUTE_ADMISSION_V1` versus 075 `LOCAL_VOICE_COMPUTE_ADMISSION_V1` by explicit versioned amendment; no string alias |
| Human plan / ticket | 071 -> 072 -> 075 | Required V2 action registry and one-shot ticket V3/current accepted successor; reference, inference, listening, regenerate, revoke, purge kept distinct; no chat approval treated as live receipt |
| Job artifact | 076 -> 014/048/073 | Immutable event + pinned selected-head readback; NOT legacy mutable jobs.json; 072 solely owns native child containment |
| QA / listening | 048 -> 075 + 041 -> 046/073 | Technical pass does not mean Human accept; playback observation and exact-output decision are separately bound |
| Shell projection | 073 -> 036 | Original D4-R4 bundle remains immutable; amendment for actual producer versions and staging artifact coordinate; no canonical Asset requirement introduced |

M1 finishes only with all proposed interfaces reviewed, closed unknown-field/enum sets, canonical schema + package mirror equality, digest preimages and accepted same-head test fixtures. No raw media/text/path/key in public receipts. Private text/reference enters only trusted owning ports. Absence of an exact contract is a named blocked M1 item, not an invitation to improvise during native execution.

## 5. Expression plan and engine adapter

TASK-014 owns the plan and private text. An immutable plan revision binds:

- project/request ID, ordered unique segment IDs, approved script revision and text digest;
- separate subtitle, normalized, TTS and alignment text revisions (do not use subtitle blocks as automatic speech fragments);
- semantic direction ID/revision, style/emotion, approved speaking-rate range, intended before/after pause in integer samples, pronunciation revision;
- exact model/runtime/catalog/capability receipt, reference role/version, inference parameter/seed policy and operation identities;
- closed per-field capability map: `SUPPORTED`, `REFERENCE_CONDITIONED`, `UNSUPPORTED`, `UNKNOWN`, plus explicit DirectionLoss reasons. This is a PROPOSED plan amendment, not current parser support.

The pinned GPT-SoVITS C04 route is the first adapter. Existing normal route uses fixed reference and sampling settings; no claim that an emotion label, pitch shift or speed knob produces a real expression. Two styles require consented role-specific references or a verified runtime mechanism, current capability Evidence and Human audition. `UNSUPPORTED/UNKNOWN` requested expression blocks execution; neutral fallback is disabled. Changing model, reference, text, direction or parameter policy creates a new candidate/revision and invalidates dependent admission.

Reuse the external engine implementation behind TASK-075's reviewed trusted boundary; do not duplicate voice training/server code in BVP. External `127.0.0.1` server presence, permissive CORS, text-only API or health probe is insufficient operation authentication. Adapter must identify exact runtime build/model/license and support bounded operation, no-network enforcement, child containment and result correlation. No external source mutation is included here. If the engine lacks the required guarded API, define a BVP-owned child adapter under 075 or obtain a separately owned versioned external interface; never weaken receipts to fit the old server.

Each Cue obtains fresh 014 admission, 071 Human action, 072 one-shot ticket, 076 Job and 101 model-load/074 reference leases for its exact operation. No consumed ticket/lease is reused. If batch Human confirmation is desired, its exact bounded per-Cue issuance must be accepted by 071/072 first; this plan grants no batch authority. Cancellation, expiry/revocation and UNKNOWN dispatch invalidate unstarted Cues and prohibit blind retries. Failed Cue replacement gets a new candidate; unchanged current QA-passing Cues may be reused only after fresh assembly admission/readback.

## 6. WAV, Master and save semantics

1. 075 supplies PCM through an operation-bound child/sink handoff; it does not return an arbitrary file path to the Shell.
2. 014 validates format, complete nonempty frames, exact requested text/direction correlation and bounded duration policy. Resample/quantize once into 48 kHz mono signed PCM24 under a pinned converter; never truncate speech or accelerate merely to fit SRT slots.
3. 048 issues exact Cue QA receipts, including corrupt/silent/clipped/critical-term-loss/speech-end-overflow negatives, actual duration and analyzer/profile identity. Missing/inapplicable metrics remain NOT_CONFIRMED; aggregate score cannot override a hard failure.
4. 014's separate `MASTER_ASSEMBLY` operation admits a complete ordered set of current Cue POST/QA receipts. Output samples are the exact concatenation of admitted Cue sample ranges plus approved integer-sample pauses. No hidden crossfade, overlap, trimming, gain change, time stretch or reordering. If processing is needed, freeze a new explicit plan and re-QA the changed audio.
5. 014 persists/selects the whole private-staging output via076's secure immutable artifact/readback using `PRIVATE_STAGING_NARRATION_MASTER_V1`. Expected sample count is `sum(cue_frame_count) + sum(explicit_pause_samples)`, measured duration is samples/48000. Exact digest, size, format and receipt inventory bind the Master. Partial assembly is not a success; no Asset publication occurs.
6. 048 runs whole-Master QA, checks complete plan coverage and joins. Join clicks, unnatural pauses, audible level discontinuity and expression difference require Human listening in addition to measured QA. No new invented numeric quality percentage or auto-accept.
7. 075 plays only the admitted exact Master under a fresh playback operation; 041 records ACCEPT/REJECT/RETEST against exact output/plan/QA/playback identities. ACCEPT cannot be inherited from the model/reference or an earlier WAV.
8. BVP Save means confirmed persistence of this private-staging artifact to an admitted destination, plus restart readback. User-copy/export outside the protected staging root requires a separately authorized destination/disclosure operation; it is not implied here. No overwrite. Public UI shows opaque identity/status, not private path/text.

At M1, 048 must freeze a versioned narration QA profile including format/sample-count consistency, duration bounds, corrupt/silent/clipping/critical-term-loss/speech-end tests, supported measurements and exact numeric thresholds from accepted policy. Those audio-policy values cannot be guessed by this documentation unit. `QA_POLICY_NOT_FROZEN` blocks M6. Human acceptance remains mandatory, automatic calibration/promotion remains OFF.

## 7. Recovery, gates and tests

States are derived from owner receipts, not a new 073 state store: SETUP_BLOCKED -> READY -> HUMAN_CONFIRMED -> QUEUED/RUNNING -> QA_REQUIRED -> LISTEN_REQUIRED -> ACCEPTED_PRIVATE_STAGING, or REJECT/RETEST. Post-dispatch uncertainty is UNKNOWN, not FAILED-with-safe-retry. Restart loads selected immutable owner events/currentness; filesystem scan/latest filename is never winner selection. A saved artifact with no verified current head is not accepted. New plan/ref/model/Consent revision marks affected descendants STALE.

Human/native gates:

- H0: exact script, styles/reference rights, frozen QA/parameter policy and 036 successor mock check.
- H4: exact imported model approval under 046; earlier model selection is Evidence, not automatic live admission.
- Effect-specific reference load, inference, assembly/save, playback and destination admission: exact 071/072 accepted actions, current Consent, leases and installed/compute/I/O readbacks. Do not reinterpret TASK-098 private canonical-Asset playback approval as synthesis permission.
- New training, acquisition, external storage disclosure, installation, Release/Deploy/Production remain prohibited unless separately authorized.

Focused test acceptance is assigned before implementation:

| Layer | Required tests |
|---|---|
| Import/catalog | correct historical pair; foreign/truncated/hash-mismatched model; expired Consent/license; missing evaluation/H4; copied/hash-only custody; wrong runtime; unsupported style; strict084/101 tagged-union cross-variant rejection; no model-body access in pure tests |
| Currentness/Job | absent/selected heads; two concurrent writers; stale predecessor; manifest tamper; physical replacement/reparse; crash before/after commit; ABA; forged time; wrong operation; no stale event promoted |
| Broker/reference | wrong issuer/version; replay; expiry/revocation; crossed Cue/Job/reference/sink; child containment violation; egress attempt; denied CPU fallback; parent plaintext exclusion; output overrun; cancel and ambiguous dispatch |
| Render/assembly | missing/duplicate/reordered segment; text/direction mismatch; zero/partial/non-PCM24 output; deterministic sample count; explicit pauses; full speech ends; no SRT-slot truncation; stale QA/digest; atomic no-clobber/save restart |
| QA/listening | corrupt/silent/clipping/term loss/overflow negatives; NOT_CONFIRMED handling; wrong-output playback/decision; technical pass != Human ACCEPT; REJECT != delete; retest new candidate |
| Product | effect-zero before Human action; only current receipt projections; unavailable/unsupported Japanese reasons; packaged entry; no private path/log leakage; two visibly selectable styles and real distinct-expression Human check |

No full repository/native suite on each doc edit. For implementation use source/schema static, exact owner unit tests, boundary/fault integration, targeted regression, required independent DEV-4 Critic/Tester/Judge, same-head hosted checks and final integration review. No PASS for unexecuted native work.

## 8. Delay prevention and progress accounting

- Named unknowns are M1 contract amendments, model import/rights evidence, QA policy, style-reference support, 036 mock check, and M2 native producer completion. Close them before costly live runs. A design review PASS does not erase them.
- No new Task for tests, fixture, review cycle or ordinary correction. Task099/100 cover missing connection responsibilities; Task101 owns the genuinely different imported-model custody entrypoint and replaces084 in this path. Completed043/013 and existing084 training history are not repurposed.
- An actual Task reassignment needs explicit ownership/Allowed Files, fresh canonical main and lock audit. This plan does not authorize messaging other threads, copying foreign worktrees or using their unmerged branches.
- High-reasoning capability: import/currentness/canonical schema, Critic, hard faults and final integration. Implementation capability: approved adapters/stores/UI. Bulk/mechanical capability: bounded docs/fixtures/tests. Minimum sufficient available model; DEV floors never reduced. This unit uses high reasoning for architecture/Critic and mechanical validation for ledger/docs.
- Track 17 lane exits and seven post-design milestones independently. Equal Task count is **not** effort/time progress; do not infer 60% completion from prior rough conversation. Current verified real BVP expression-Master outcome: NOT_CONFIRMED. Report future progress with completed milestone/17-lane evidence and separate estimated engineering progress.
- No automatic monitoring of training or other unchanged activity. No guaranteed zero delays: owner/native/quality failures can still block execution; exact named resume conditions prevent unexplained stalls.

## 9. Minimal continuation context

M1 reads this plan + ledger; exact046 model and101 import contracts (084 only to check the strict alternative branch boundary); 014 local render admission; 074/075 accepted amendment receipts; 076 §7.7; 099/100/101 design definitions; exact048 profile and073 R4 bundle. Read each owning source/schema/test only for its allocated unit. Do not preload all completed Tasks, OS Architecture, raw model/audio or full historical packs.

Before canonical integration, verify main/Task IDs/locks again; publish this overlay and new design allocations through normal review. Shared state synchronization is a separate serialized exact-files unit, not authorized by 073's source allocation. Persist/read back external Evidence before stopping or cleanup. Do not delete/reuse residual foreign directories.
