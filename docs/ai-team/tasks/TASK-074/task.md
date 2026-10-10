# TASK-074 — Owner Voice Authority, Route Selection and Private Reference

- Status: `DESIGN_ACCEPTED_R13 / R23_BRANCH_PREDICATE_REVIEW_PENDING / SOURCE_START0 / EFFECT0`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- Owner allocation: `成果V Voice/WAV primaryへ再編`
- Design owner: `Design A`
- Required independent review: `Design B security review / Montage Critic and Judge`
- Exact design base: `70ba9e369887d3d7ded59e7197d20d133b2b4d38`
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

The accepted design is the immutable R9 packet plus R10、R11、R12 and R13 addenda. R13 closes V2 terminal-current retirement/repeated-operation issuance and the legacy V1 `REVOKE_PENDING` terminal finalize-only recovery seam. Fresh independent DEV-4 review reproduced the exact frozen set、reported `Critical/High/Medium/Low = 0/0/0/0` and returned Judge `PASS`. TASK074-B pure contracts may therefore start after fresh Git/worktree/dirty/overlap verification. TASK074-C and TASK074-D retain their explicit producer、native and Human Gates; design acceptance does not authorize those gated effects.

R16 later identified the circular dependency between TASK-074 producer work and
TASK-014 D4 work, but independent review returned `FAIL / REVISE` with
unresolved High findings. R16 is superseded as a candidate and remains
`SOURCE_START0`. R17 is the current effect-zero correction candidate. It adds
separate TASK-014/TASK-074 owner contract acceptances, owner-specific nominal
completion layers, the full direct-transfer/recovery rules, a closed live
prerequisite table and the exclusive TASK-041-to-TASK-036 AUDIO_COMPLETION
boundary. R17 and both owner acceptance candidates require fresh exact-byte
Tester/Critic/Judge review with `Critical/High = 0/0` and Judge `PASS` before
either record may be marked accepted. No R17 source stage is allocated by this
Task record.

R17 failed that review: Tester `FAIL` `0/3/0/0`, Critic `REVISE` `0/4/2/0`,
Judge withheld. Its exact rejected bytes and findings are preserved in
`design-r17-independent-review-receipt.md`.

R18 is the current correction candidate. It keeps reviewed contract bodies
immutable and moves each owner's acceptance into a later, separate,
digest-stable envelope. It separates source eligibility from same-operation
live minting; restores the full TASK-076 V3 bootstrap/bind/preflight sequence;
corrects TASK-043/TASK-074 transaction ownership and LOCAL-only compute
admission; and makes TASK-041/TASK-036 ordering acyclic with a closed PASS input
table. R18 requires fresh exact-byte Tester/Critic/Judge review. No R18 owner
envelope or source stage is allocated by this Task record.

R18 failed review: Tester `FAIL` `0/2/0/0`, Critic `REVISE` `0/3/1/0`, Judge
withheld. Exact bytes and findings are preserved in
`design-r18-independent-review-receipt.md`.

R19 was the then-current correction candidate. It introduces distinct TASK-074
operation-ready, child-pair-ready and terminal-current types; restores the
TASK-014 one-use dispatch lease before TASK-076 arm; and moves TASK-075 result
to terminal/POST gating only. It normatively binds the exact current-main
TASK-076 V3 prepare/abort/release/containment failure graph and closes TASK-041
finishing with canonical REQUIRED/OPTIONAL/NOT_APPLICABLE policy plus a sealed
TASK-035 owner-issued optional-skip current result. R19 requires fresh
exact-byte Tester/Critic/Judge review. No owner envelope or source stage is
allocated by this Task record.

R19 failed review: Tester `FAIL` `0/3/0/0`, Critic `REVISE` `0/3/1/0`, Judge
withheld. Exact bytes and findings are preserved in
`design-r19-independent-review-receipt.md`. R19 remains immutable rejected
Evidence and cannot issue owner acceptance or source authority.

R20 is the current correction candidate. It replaces pre-arm TASK-014 call
dispatch with a metadata-only reservation consumed by a future separately
accepted TASK-014/072/075/076 adapter around the unchanged TASK-076 arm ABI.
Actual call/sink dispatch begins only after exact Artifact-prepare pending.
One second separately accepted four-owner adapter binds TASK-014 receipt-only
prepare/terminal truth into the existing TASK-076 inputs.
R20 separates SUCCESS, NONCURRENT, ABORTED and BURNED_UNKNOWN terminals,
defines full TASK-014 session/reply-loss closure, lists every exact
known-no-child result and preserves the canonical restart-safe unselected-orphan
exception. Its four immutable contracts and exact sixteen-key owner-envelope
schema require fresh exact-byte Tester/Critic/Judge review. This Task record
allocates no envelope, either adapter, source or runtime effect.

R20 failed review: Tester `FAIL` `0/2/2/0`, Critic `REVISE` `0/4/1/0`, Judge
withheld. Exact bytes and findings are preserved in
`design-r20-independent-review-receipt.md`. R20 is immutable rejected Evidence.

R21 was the then-current correction candidate. It adds durable pre-arm coordinator
and owner-query reconciliation, owner-issued prepare NEVER_ENTERED truth,
canonical receipt-only adapter outputs and ordinary AFTER_PREPARE abort. It
treats result/POST/role-close/lease facts as provisional until TASK-076 terminal
and TASK-074 retirement join; late uncertainty selects a containment branch
that preserves those facts. The complete canonical TASK-075 success predicate
gates POST, publication-current and downstream PASS. Exact owner contract paths
and TASK-041 forked handling are closed. Fresh exact-byte Tester/Critic/Judge
review was required; this Task record grants no envelope, amendment, source or
runtime effect.

R21 failed review: Tester `FAIL` `0/1/0/0`, Critic `REVISE` `0/2/0/0`, Judge
withheld. Exact bytes and findings are preserved in
`design-r21-independent-review-receipt.md`. R21 remains immutable rejected
Evidence.

R22 was the then-current correction candidate. It makes exact terminal/retirement a
prerequisite only for known-closed global branches and makes partial-truth
containment reachable from explicit false/unknown late joins. It also separates
same-broker live-continuation interruption from Product/broker/worker/adapter/
coordinator restart or continuation loss. Only the live class may issue prepare
`NEVER_ENTERED` and finish abort-wait; restart-class state follows pinned
TASK-075 section 9.3.1 burned-unknown containment unless an exact pre-restart
abort-pending claim already exists. Fresh exact-byte Tester/Critic/Judge review
was required; this Task record grants no envelope, amendment, source or runtime
effect.

R22 failed review: Tester `FAIL` `0/2/0/0`, Critic `REVISE` `0/2/0/0`, Judge
withheld. Exact bytes and findings are preserved in
`design-r22-independent-review-receipt.md`. R22 remains immutable rejected
Evidence.

R23 is the current correction candidate. It derives one predecessor kind and
compares that kind with its complete expected POST/Job-terminal/retirement
vector, making the three known-closed branches and containment mutually
exclusive. It adds an exact no-prepare-recovery context for ordinary late
uncertainty. It also limits restart burned-unknown handling to explicit
pre-release states and preserves pinned post-release STARTED child terminal
recovery before fallback containment. Fresh exact-byte Tester/Critic/Judge
review is required; this Task record grants no envelope, amendment, source or
runtime effect.

### TASK074-B — Pure contracts and fixtures

TASK074-Aのaccept後に開始する。route selection、private-reference receipt、registry amendment、completion receiptのpure/body-free validatorsとfixturesを実装する。real Project store、real encryption、native picker、private audio、model runtimeは使わない。

### TASK074-C — Canonical producer binding

TASK-071/TASK-072とTASK-043-owned canonical Project transaction portがcanonicalかつoverlap-freeになった後だけ、同じTask/PR内でexact adaptersを実装する。TASK-036/P0-EはProject store authorityを持たないconsumer/integration ownerである。cross-owner file mutationは各ownerのexplicit lock/Allowed Filesが揃うまで`NOT_CONFIRMED`。

### TASK074-D — Private lifecycle native closure

non-biometric native fixtureでWindows custody、DACL、revocation、physical purgeのcontractを閉じる。real Owner audioを用いるproduction verificationは別状態`P0V_OWNER_REFERENCE_VERIFIED`と別Human Gateであり、`TASK074_IMPLEMENTATION_COMPLETE`の必須条件ではない。

## Design-phase Allowed Files

- `docs/ai-team/tasks/TASK-074/task.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r10-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r11-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r12-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r13-addendum.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r16-dependency-sequencing-amendment.md`
- `docs/ai-team/tasks/TASK-074/design-r16-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r17-dependency-sequencing-amendment.md`
- `docs/ai-team/tasks/TASK-074/r17-direct-transfer-producer-contract-acceptance-r0.md`
- `docs/ai-team/tasks/TASK-074/design-r17-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r18-stable-acceptance-split-gates.md`
- `docs/ai-team/tasks/TASK-074/r18-direct-transfer-producer-contract.md`
- `docs/ai-team/tasks/TASK-014/task.md`
- `docs/ai-team/tasks/TASK-014/d4-restricted-consumer-port-contract-r18.md`
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r18.md`
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r18.md`
- `docs/ai-team/tasks/TASK-074/design-r18-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r19-acyclic-runtime-exact-failure.md`
- `docs/ai-team/tasks/TASK-074/r19-direct-transfer-runtime-phases-contract.md`
- `docs/ai-team/tasks/TASK-014/d4-three-phase-runtime-contract-r19.md`
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r19.md`
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r19.md`
- `docs/ai-team/tasks/TASK-074/design-r19-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r20-reservation-tagged-terminal-closure.md`
- `docs/ai-team/tasks/TASK-074/r20-direct-transfer-tagged-terminal-contract.md`
- `docs/ai-team/tasks/TASK-014/d4-reservation-closed-terminal-contract-r20.md`
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r20.md`
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r20.md`
- `docs/ai-team/tasks/TASK-074/design-r20-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r21-coordinated-closure-late-truth.md`
- `docs/ai-team/tasks/TASK-074/r21-global-terminal-closure-contract.md`
- `docs/ai-team/tasks/TASK-014/d4-coordinated-closure-contract-r21.md`
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r21.md`
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r21.md`
- `docs/ai-team/tasks/TASK-074/design-r21-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r22-restart-split-reachable-containment.md`
- `docs/ai-team/tasks/TASK-074/r22-global-terminal-closure-contract.md`
- `docs/ai-team/tasks/TASK-014/d4-coordinated-closure-contract-r22.md`
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r22.md`
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r22.md`
- `docs/ai-team/tasks/TASK-074/design-r22-independent-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/complete-design-packet-r23-branch-predicate-post-release-recovery.md`
- `docs/ai-team/tasks/TASK-074/r23-global-terminal-closure-contract.md`
- `docs/ai-team/tasks/TASK-014/d4-coordinated-closure-contract-r23.md`
- `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r23.md`
- `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r23.md`
- `docs/ai-team/tasks/TASK-074/design-r1-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r2-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r3-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r4-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r5-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r6-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r7-review-receipt.md`
- `docs/ai-team/tasks/TASK-074/design-r13-review-receipt.md`
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
