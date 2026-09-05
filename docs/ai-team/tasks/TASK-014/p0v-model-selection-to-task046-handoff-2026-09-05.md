# TASK-014 P0V — Model Selection to TASK-046 Sealed Producer Boundary

## 1. Current bind

- Current main: `b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`
- Handoff branch: `codex/task-014-p0v-sealed-producer-boundary-handoff`
- Handoff worktree base: current main `b7b2f33`
- P0V synthetic worker preservation commit: `9d52e923a216bc11b7ecba4004dd63951657aab3`
- Existing zero-shot callable gap-audit commit: `28e21647b0a5375e5ba9d28b632e3922794c44ec`
- Existing zero-shot callable current-r1 candidate base: `6121ef2e9322501b391688998485918d10173f32`
- DEV profile: `DEV-3`

P0V worker branch is clean but `ahead 1 / behind 6` against current `origin/main`; Main Merge owns its current-main recovery. The callable candidates are also off-main and stale. This unit does not rebase, cherry-pick, merge, or modify any of those worktrees.

Real OBS input, raw audio, model loading, provider execution, GPU reservation, rendering, Dataset mutation, training, Asset publication, and profile adoption have effect `0` in this unit.

## 2. Existing assets and authority

| Existing symbol | Input | Output | Authority/effect |
| --- | --- | --- | --- |
| `ConnectionSettingsStore.load/save` | secret-free profile and expected revision | revisioned settings record | Configuration only. Save does not authorize generation. |
| `ConnectionSettingsFormBuilder.build` | profile, availability, settings preflight | user-facing workload form | Projection only; provider/model execution `0`. |
| `ConnectionSettingsEditor.apply` | complete workload modes and workload-owned route IDs | revised profile | Rejects unknown or cross-workload route selection. |
| `Task036ModelSelectionProjection.project` | bounded connection form and optional display snapshots | secret-free candidate projection | No persistence, runtime admission, model load, or provider call. |
| `AiConnectionSettingsService.preflight` | profile, availability, required capabilities | settings preflight report | Advisory readiness; not a sealed compute or inference capability. |
| `compile_local_primary_preflight` / `parse_local_primary_preflight` | exact text, VoiceProfile, engine, resource, rights, and exactly one route binding | body-free TASK-014 preflight | `READY_FOR_OWNER_HUMAN_GATE` is not execution authority; all effect flags remain false. |
| `compile_quick_clone_readback` / `public_projection` | Quick Clone flow plus optional preflight metadata | TASK-046 display/readback receipt | Current Product producer remains `NOT_BOUND`; execution, profile save, and publication remain false. |
| `compile_zero_shot_callable_envelope` / parser | render admission, preflight, VoiceProfile, plan, and three typed canonical-owner receipts | body-free callable envelope | Existing candidate permits only `BLOCKED` or `UNKNOWN`. It explicitly cannot claim dispatch authority. |
| `_bind_synthetic_operation` | exact ready preflight and in-memory compute admission | private synthetic operation | Module-private test token only; not durable and not production authority. |
| `LocalInferenceWorker.run_once` | exact private synthetic operation | synthetic worker receipt | Accepts only `FakeLocalInferenceChildBackend`; filesystem/network/process/model/audio effects `0`. |

## 3. Source-backed overlap finding

`task014_zero_shot_callable_contract.py` and its focused test already exist in two preserved worktrees:

1. `task-014-zero-shot-callable-gap-audit-r1` at `28e2164`;
2. `task-014-zero-shot-callable-current-r1` based at `6121ef2`, staged and behind current main.

Their source and test contents are logically identical when end-of-line differences are ignored. Neither is in current main. They are reuse candidates, not authority to copy blindly and not a reason to create a second callable-envelope contract.

The existing callable envelope fixes Qwen call-surface metadata, canonical coordinates, bounded preview limits, no automatic retry, hidden Windows runner intent, and body-free persistence flags. Even with internally constructed receipt objects, it ends in `UNKNOWN` because canonical authority, transcript authority, and trusted evaluation time are not confirmed. Its enum has no ready/dispatch decision.

This callable contract covers `ZERO_SHOT_LOCAL` preview only. It is not a generic local-inference envelope and must not be reused to authorize `FINE_TUNED_LOCAL`. The fine-tuned route remains `DEPENDENCY N.C.` until TASK-046 supplies its exact current Dataset/ModelCandidate/artifact receipt chain and a separately allocated TASK-014 callable/producer boundary consumes it.

## 4. Required architecture

```text
Central Settings selection (configuration coordinate only)
  -> TASK-014 LocalPrimaryNarrationPreflight
  -> TASK-014 LocalPrimaryNarrationRenderAdmission
  -> zero-shot only: existing ZeroShotCallableEnvelope (BLOCKED/UNKNOWN, no dispatch)
     fine-tuned: separate canonical callable dependency, currently N.C.
  -> future private sealed producer resolver
       verifies canonical-owner receipts + trusted time + Human one-shot ticket
       verifies TASK-066 GF-C compute capability and current installed/runtime identity
       binds TASK-046 exact VoiceProfile/reference or model-candidate identity
       emits one private, non-serializable, one-use operation capability
  -> separately owned production executor (TASK-074/TASK-075 dependency)
  -> sealed result receipt and independent readback
```

The private producer must not accept a Settings projection, TASK-046 public readback, TASK-048 fixture, callable-envelope digest, or matching caller-supplied fields as authority. It must resolve the authoritative records in-process and bind their physical/current identity under the responsible owners' APIs. A zero-shot producer cannot silently branch to fine-tuned execution, and a fine-tuned producer cannot substitute a zero-shot reference.

The synthetic worker must remain synthetic. Do not inject a real backend into `LocalInferenceWorker`, expose `_SYNTHETIC_CAPABILITY`, or widen `_SyntheticInferenceOperation`. The existing worker is a behavioral test fixture for one-shot state and failure handling, not the production executor.

## 5. Reuse versus new implementation

### Reuse without redesign

- current central Settings store/editor/form/preflight;
- TASK-014 local-primary preflight and render-admission contracts;
- preserved zero-shot callable envelope contract after a designated current-main recovery;
- TASK-046 canonical VoiceProfile/reference/model-candidate read APIs and typed receipts;
- TASK-066 GF-C sealed compute broker receipt;
- TASK-071/TASK-072 Human one-shot authorization and ticket contracts;
- TASK-074/TASK-075 production custody/executor and terminal receipt boundaries;
- P0V synthetic worker tests as a no-effect behavioral oracle.

### Must not modify merely to bridge the gap

- `src/ai_video_production/task036_model_selection.py`
- `src/ai_video_production/connection_settings.py`
- `src/ai_video_production/connection_settings_store.py`
- `src/ai_video_production/owner_narration_local_primary.py`
- `src/ai_video_production/voice_studio_quick_clone.py`
- `src/ai_video_production/voice_studio_quick_clone_readback.py`
- `src/ai_video_production/task014_local_inference_worker.py`

### Candidate future Allowed Files

Exact allocation is still required. This handoff proposes the following ceiling and does not make the names canonical:

1. designated current-main recovery of existing `src/ai_video_production/task014_zero_shot_callable_contract.py`;
2. its existing focused test `tests/test_task014_zero_shot_callable_contract.py`;
3. one new TASK-014 private sealed producer/composition module;
4. one matching focused producer test module;
5. this task-local handoff only if evidence must be synchronized.

Schema, package-resource mirror, packaging, TASK-046 source, TASK-066 source, TASK-071/072 source, TASK-074/075 source, shared Shell/UI, Registry, current-state, CHANGELOG, release, install, and Production activation remain outside this candidate ceiling unless separately allocated.

## 6. Sealed producer state machine

```text
UNBOUND
  -> resolve authoritative current inputs
  -> ARMED
  -> atomically consume one Human/ticket capability
  -> IN_FLIGHT
  -> hand one private operation to the responsible executor
  -> TERMINAL_SUCCEEDED | TERMINAL_FAILED | TERMINAL_UNKNOWN
```

- Direct construction, public factory input, dataclass copy/replace, pickle, deserialization, or matching hashes cannot create `ARMED`.
- Entry into the effectful operation burns the one-use capability.
- Any exception after entry is terminal for that object; mode switching or silent retry is prohibited.
- Duplicate/concurrent use permits at most one executor call.
- Timeout/ambiguous child termination returns `TERMINAL_UNKNOWN`; it must not auto-retry.
- A result receipt does not authorize Asset publication, Dataset adoption, training, or profile promotion.

## 7. Focused negative matrix

| ID | Negative input/state | Required result |
| --- | --- | --- |
| `N1` | selected `LOCAL_FREE_AI` route without exact engine/resource/rights/reference authority | blocked before producer mint; executor/child call `0` |
| `N2` | TASK-046 public Quick Clone projection or readback passed as operation authority | type/seal rejection; child call `0`; producer remains `NOT_BOUND` |
| `N3` | self-created callable receipts/envelope, copied fields, or caller digest | callable remains `UNKNOWN`/rejected; private capability `0` |
| `N4` | TASK-048 calibration projection/fixture used as producer authority | reject; model load/provider/Asset/profile effects `0` |
| `N5` | zero-shot/fine-tuned route or callable-envelope substitution | exact route rejection before executor call; fine-tuned remains N.C. without its own canonical chain |
| `N6` | expired/stale/wrong Project, plan, VoiceProfile, reference, model, runtime, compute, Human ticket, or trusted time | fail closed; no automatic recompute/retry |
| `N7` | direct/copy/replace/pickle/deserialized capability or same fields without the trusted resolver operation | reject; executor call `0` |
| `N8` | double or concurrent use, or reuse after executor exception | exact one call maximum; old capability terminal/burned |
| `N9` | public input containing raw script/audio/transcript body, private voice ID, credential, or host path | reject without logging/persisting the value |
| `N10` | executor success without sealed result plus independent current readback | no Product PASS, Asset publication, or TASK-046 adoption |

The first four cases are the minimum focused suite. `N5` through `N10` are required for the DEV-3 producer implementation.

## 8. Evidence

- TASK-046 synthetic OBS intake focused suite: `68 passed`.
- Central Settings + TASK-014 preflight + TASK-046 readback regression: `112 passed`.
- Existing zero-shot callable contract focused suite: `129 passed`.
- One-shot boundary probe: current TASK-046 public projection was rejected by P0V worker as not a sealed synthetic operation; child-call count `0`; producer state `NOT_BOUND`.
- Existing zero-shot callable candidates: source and test logical diff `0` after ignoring end-of-line differences.
- Main, P0V worker, callable candidates, and TASK-046 OBS intake received no source mutation from this unit.

These are contract and design checks. They are not evidence of native audio, real model execution, Dataset mutation, training, publication, release, or Production activation.

## 9. Dependency receipt ABI and implementation allocation (current-main audit)

This section freezes the dependency boundary discovered at main
`b7b2f33f9acca95b5bf0d727361f0e794a2d5f82`.  It does not introduce a public
receipt type, a compatibility wrapper, or a substitute authority.  A named
design artifact is not a completion receipt, and a public data object remains
Evidence with `authority_created=false`.

| Dependency | Current source/design fact | TASK-014 consumer rule | Implementation allocation / status |
| --- | --- | --- | --- |
| TASK-046 voice route | `VoiceProfileRouteSelection` and `QuickCloneReadbackReceipt` are revision/readback contracts. `QuickCloneReadbackReceipt` keeps the producer state `NOT_BOUND`; its public `__all__` exposes no live owner port. `owner_voice_private_reference.py` likewise states that none of its classes is a live reference capability. | A future zero-shot producer must obtain a TASK-046-owned current private reference/transcript binding; fine-tuned must obtain the separate Dataset/ModelCandidate/artifact chain. Neither public readback nor a matching revision/hash is accepted. | TASK-046 owns the future sealed production binding/read API. It is **DEPENDENCY N.C.** for this handoff; TASK-014 must not add a parallel VoiceProfile, Dataset, ModelCandidate, transcript, or store reader. |
| TASK-066 compute | `CapabilityAdmissionReceipt` and `capability_from_probe_result(...)` are public current-source policy/probe data. The frozen probe registry is unsealed in the current product and the public conversion path must not be treated as a producer capability. | Require a TASK-066-owned private one-use compute admission bound to the exact workload, installed runtime/process identity, profile currentness, and result readback. A probe, adapter identity, helper hash, or CPU/GPU preference alone is insufficient. | TASK-066 GF-C / its cross-owner corrective allocation owns this broker boundary. No sealed TASK-014-consumable compute receipt is currently available: **DEPENDENCY N.C.** |
| TASK-071 Human authorization | The documented V1 action matrix has no owner-voice inference action. The future V2 packet names `OWNER_VOICE_LOCAL_INFERENCE_V1`, but its live broker capability is explicitly nonserializable and its implementation/completion state is not current. | Consume only the live, exact-action capability over the authenticated broker channel; never consume a JSON receipt, confirmation text, display projection, timestamp, or copied ticket field. | TASK-071 owns the V2 producer ABI, reservation, consume/burn and terminal audit. Until its exact completion receipt exists, TASK-014 has no Human-ticket input: **DEPENDENCY N.C.** |
| TASK-072 consumer ticket | The TASK-075 design names `OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3` and `TASK072_OWNER_VOICE_WORKER_BEGIN_READBACK_V1`, but records their implementation/completion receipts as N.C. | Bind a private producer operation only to the exact ticket/profile supplied through the TASK-071 authenticated channel. Do not parse, reconstruct, or serialize the ticket. | TASK-072 owns ticket/profile issuance and worker-begin readback. No current TASK-014 integration source is allocated: **DEPENDENCY N.C.** |
| TASK-074 route/reference producer | TASK-074 is design accepted; it owns route/reference custody and states that TASK-075 receives a durable completion handoff or private live one-operation handoff. | Receive only the owner-provided sealed zero-shot route/reference handoff. It must remain route-specific and cannot be converted into a fine-tuned authority. | TASK-074 owns producer/custody completion. Its native producer binding is still separately gated; no TASK-014 bridge implementation is authorized. |
| TASK-075 executor | TASK-075 is `DESIGN_CANDIDATE_R6 / SOURCE_START0`. Its chain explicitly requires a TASK-014 call profile/capability and a TASK-014 output-sink capability before native execution. | TASK-014 will hand one private operation to the executor only after every preceding dependency resolves. Executor output must return through its sealed result and independent readback; it cannot create Asset, Dataset, training, or profile-promotion authority. | TASK-075 owns native execution/listening composition. There is no executable consumer ABI to call today: **DEPENDENCY N.C.** |

### 9.1 Frozen direction and minimum private bindings

The producer resolver may be allocated only after all six rows above have
exact completion identities.  Its private input must bind, in one in-process
resolution operation, the following already-owned coordinates:

1. exact Project and narration-plan identity/currentness from TASK-014;
2. either the zero-shot reference/transcript binding **or** the fine-tuned
   Dataset/ModelCandidate/artifact chain from TASK-046, never both;
3. exact TASK-066 workload/runtime/process admission and readback;
4. exact TASK-071 action capability plus its TASK-072 consumer ticket/profile;
5. exact TASK-074 custody/route handoff and the TASK-075 executor contract;
6. trusted current time and one-shot budget at the same consume seam.

The current handoff deliberately does not freeze field names or a serialized
wire shape for those private bindings.  The individual owners must publish
their immutable, versioned completion identities first.  TASK-014 may then
freeze an adapter only by consuming those identities through private owner
ports; it may not recover the ABI by inspecting files, public projections, or
matching caller fields.

### 9.2 Implementation sequence and no-change boundary

1. Main Merge first recovers the preserved zero-shot callable contract onto
   current main under its existing owner/disposition gate.  That recovery stays
   body-free and `BLOCKED`/`UNKNOWN` only.
2. TASK-046, TASK-066, TASK-071, TASK-072, TASK-074 and TASK-075 each deliver
   their own exact completion receipt/owner port.  A design document, test
   fixture, package presence, or public preflight is not delivery.
3. Only then may a separately allocated TASK-014 implementation use the
   existing two callable files plus one private producer/composition module and
   one focused test module already listed in Section 5.  No additional file
   is approved by this handoff.
4. The first implementation test must prove all dependency inputs are absent
   or public-only today and that the resolver produces no private operation,
   executor call, child process, model load, audio read/write, or persistence
   delta.  After dependencies arrive, it must add the Section 7 matrix before
   any native-execution gate is requested.

Accordingly, no source implementation is presently eligible from this ABI
audit.  The current safe result is a closed dependency allocation, not a
claim that local narration execution is available.

Validation for this documentation delta: `git diff --check` passed.  The
targeted current-source regression was not executed in this worktree because
the available Python runtime lacks the required `jsonschema` package; no
runtime installation or other environment mutation was performed.
