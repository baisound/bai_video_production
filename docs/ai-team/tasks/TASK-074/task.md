# TASK-074 — Owner Voice Authority, Route Selection and Private Reference

- Status: `DESIGN_ACCEPTED_R14 / TASK074_B_IMPLEMENTATION_ELIGIBLE / TASK074_C_SOURCE_START_NC / EFFECT0`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Owner allocation: `成果V Voice/WAV primaryへ再編`
- Design owner: `Design A`
- Required independent review: `Design B security review / Montage Critic and Judge`
- Exact design base: `354ea2534ad5739a099d9eeaf0f1da9a7210ddb6`
- Product: `BAI VIDEO PRODUCTION`

## Goal

Owner自身の声を使うlocal/free narration routeについて、実行より前の次の境界を一つに閉じる。

1. current VoiceProfile、Consent、Project、installed routeへ結び付くroute selection revision;
2. route selectionのexact CAS/readback semantics;
3. private reference audioとexact reference transcriptのpaired import/in-place分類、暗号化保管、retention、revocation、purge eligibility;
4. TASK-071 Human action registryとTASK-072 consumer profileへ渡すversioned amendment contracts;
5. TASK-073が消費するbody-free projectionと、TASK-075がclosed one-ofで消費するdurable completion handoffまたはprivate live one-operation handoff。

TASK-074はmodel download/load、training、inference、playback、WAV生成、Asset採用、Timeline配置、Exportを行わない。

## Responsibility boundary

| Canonical responsibility | Owner | TASK-074 behavior |
|---|---|---|
| VoiceProfile / Consent / recording / reference-transcript semantic binding / Dataset / ModelCandidate | TASK-046 | exact current revisionをconsumeし、再定義しない。private transcript body custodyはTASK-074 brokerだけが所有する |
| local model catalog | TASK-013 | public route candidateをconsumeし、runtime availabilityを推測しない |
| narration plan / render / WAV publication | TASK-014 | output routeを選択するだけで、renderを行わない |
| Human authorization | TASK-071 | closed V2 amendment proposalを供給し、authorityをmintしない |
| one-shot operation ticket/config | TASK-072 | closed V2 consumer profile proposalを供給し、ticketをmint/consumeしない |
| secure immutable I/O primitives | TASK-068 | read/publish capabilityだけをconsumeし、mutable replace/deleteを推測しない |
| canonical Project/SQLite bootstrap, transaction and currentness | TASK-043 canonical Project store owner | private store portをconsumeし、新しいProject/store/path truthを作らない |
| installed startup composition | TASK-036 P0-E | fresh private contextをconsumeする。TASK-036はstore authorityを持たない |
| local execution/listening | TASK-075 / TASK-041 / TASK-048 | exact durable completionまたはlive one-operation handoffを渡し、実行・判定を所有しない |
| application composition | TASK-073 | public-safe completion projectionを渡し、TASK-073にauthorityを渡さない |
| shared Product UI/package | TASK-036 Outcome E | versioned receiptsのみhandoffし、TASK-036 sourceを変更しない |

## Atomic Units

### TASK074-A — Complete design and frozen ABI

- design packet、state machines、negative/fault matrices、Allowed Files、completion receiptを固定する;
- independent Criticでunresolved `Critical/High = 0/0`;
- independent Judge `PASS`;
- Product source change `0`。

The accepted design is the immutable R9 packet plus R10、R11、R12、R13 and R14 addenda. R13 closes V2 terminal-current retirement/repeated-operation issuance and the legacy V1 `REVOKE_PENDING` terminal finalize-only recovery seam. R14 freezes the exact TASK-074 owner-side producer profile for TASK-076 V3、pre-arm containment identity、bind/preflight/close/query/recovery ABIs and the non-circular TASK-075 V2 pre-close -> owner-close -> final-union seam. Fresh independent DEV-4 Tester、Critic and Judge reproduced the exact frozen set、reported `Critical/High/Medium/Low = 0/0/0/0` and returned `PASS`. TASK074-B pure contracts remain eligible after fresh Git/worktree/dirty/overlap verification. TASK074-C source start remains `NOT_CONFIRMED` until exact source/test Allowed Files、sole-writer、clean current-main worktree and all S1 dependency gates are separately established. TASK074-D retains its explicit native and Human Gates; design acceptance authorizes none of those gated effects.

### TASK074-B — Pure contracts and fixtures

TASK074-Aのaccept後に開始する。route selection、private-reference receipt、registry amendment、completion receiptのpure/body-free validatorsとfixturesを実装する。real Project store、real encryption、native picker、private audio、model runtimeは使わない。

### TASK074-C — Canonical producer binding

TASK-071/TASK-072とTASK-043-owned canonical Project transaction portがcanonicalかつoverlap-freeになった後だけ、同じTask/PR内でexact adaptersを実装する。R14のS1開始にはfresh source/test Allowed Files、sole-writer、clean current-main worktreeとimplementation Authorityが別途必要であり、下記candidate listはsource-start Authorityではない。TASK-075のtwo-stage V2 contracts、TASK-072 adapter、TASK-076 slotは各ownerのS2 compatibility実装・durable receiptが揃うまで`NOT_CONFIRMED`。TASK-036/P0-EはProject store authorityを持たないconsumer/integration ownerである。cross-owner file mutationは各ownerのexplicit lock/Allowed Filesが揃うまで`NOT_CONFIRMED`。

### TASK074-D — Private lifecycle native closure

non-biometric native fixtureでWindows custody、DACL、revocation、physical purgeのcontractを閉じる。real Owner audioを用いるproduction verificationは別状態`P0V_OWNER_REFERENCE_VERIFIED`と別Human Gateであり、`TASK074_IMPLEMENTATION_COMPLETE`の必須条件ではない。

## Design-phase Allowed Files

- `docs/ai-team/tasks/TASK-074/task.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r10-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r11-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r12-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r13-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r14-addendum.md`
- `docs/ai-team/tasks/TASK-074/design-r1-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r2-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r3-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r4-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r5-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r6-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r7-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r13-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r14-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-review-receipt.md`

## Candidate implementation Allowed Files

Design accept後にexact branch/lock/currentnessを再確認してから次だけを候補とする。

- `src/ai_video_production/owner_voice_authority.py`
- `src/ai_video_production/voice_profile_route_selection.py`
- `src/ai_video_production/owner_voice_private_reference.py`
- `src/ai_video_production/voice_profile_route_selection_store.py`
- `src/ai_video_production/owner_voice_private_reference_windows.py`
- `packaging/task074_owner_voice_private_reference_windows_entry.py`
- `schemas/owner_voice_authority.schema.json`
- `schemas/voice_profile_route_selection.schema.json`
- `schemas/owner_voice_private_reference.schema.json`
- `src/ai_video_production/schema_resources/owner_voice_authority.schema.json`
- `src/ai_video_production/schema_resources/voice_profile_route_selection.schema.json`
- `src/ai_video_production/schema_resources/owner_voice_private_reference.schema.json`
- `tests/test_task074_owner_voice_authority.py`
- `tests/test_task074_voice_profile_route_selection.py`
- `tests/test_task074_owner_voice_private_reference.py`
- `tests/test_task074_voice_profile_route_selection_store.py`
- `tests/test_task074_owner_voice_private_reference_windows.py`
- `tests/test_task074_owner_voice_private_reference_packaging.py`
- `tests/fixtures/task074/**`
- `docs/ai-team/tasks/TASK-074/implementation-completion-receipt.md`

TASK-071、TASK-072、Product Project storeへのadapter amendmentは、producer base implementation、exact owner lock、sole-writer、追加Allowed Filesが別途確認されるまで候補にも含めない。

## Must not modify

- `src/ai_video_production/task036_*`
- `docs/ai-team/current-state.md`
- roadmap、task-index、Registry、shared `CHANGELOG.md`
- TASK-014/TASK-046/TASK-068/TASK-071/TASK-072/TASK-073/TASK-075/TASK-076 owned source
- TASK-027 source/schema
- TASK-066 source/test
- unknown dirty/untracked paths in the root checkout

## Effect ceiling and Human Gates

Designとpure implementationのeffect ceilingは`0`。次は各exact Human Gateなしに禁止する。

- Owner audioを開く、読む、copy/importする;
- private root/DACL/key custodyを作成・変更する;
- reference derivativeを暗号化・復号する;
- referenceをrevokeまたは物理purgeする;
- model/runtimeをdownload、load、probe、train、inferする;
- playback、WAV書込み、OBS/native操作;
- provider/paid/cloud call、private upload;
- Release、Deploy、Production Activation。

## Definition of done

`TASK074_IMPLEMENTATION_COMPLETE`は、全design review、pure contracts、canonical producer bindings、synthetic/non-biometric Windows contract tests、independent Tester/Critic/Judge、C/H `0/0`を満たし、`TASK074_OWNER_VOICE_AUTHORITY_COMPLETION_RECEIPT_V1`のfixture/current contractをexact readbackできた時点で成立する。real Owner audioのimport/revoke/purge実行は要求しない。

`P0V_OWNER_REFERENCE_VERIFIED`は別のprivate/native Human Gateである。real Owner audio、custody readback、reference quality、revoke/purgeの実観測が未実行なら`NOT_CONFIRMED`のままでもimplementation completionをFAILにしない。blocked dependencyをPASSへ昇格しない。
