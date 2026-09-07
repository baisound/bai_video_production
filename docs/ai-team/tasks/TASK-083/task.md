# TASK-083 — 音声学習Execution Resource Reservation

- Status: `PURE_CONTRACT_AND_EFFECT_ZERO_WINDOWS_BOUNDARY_CANDIDATE / NATIVE_RESERVATION_NOT_STARTED`
- Development Depth: `DEV-4 FOUNDATION CRITICAL`
- Execution coordinator: Owner指定の「OBS録音→学習→WAV最適化」統合Task
- Canonical responsibility: TASK-083

## 目的

local voice training開始前に、CPU、GPU、RAM、VRAM、disk、thermal、power、runtime/backendを同じproject/job/run/snapshot/recipeへbindしたone-use `ExecutionResourceReservationBinding` を発行、消費、readbackする。public hardware probe、policy dataclass、設定値、hash、tokenはadvisoryであり、live resource capabilityやtraining authorityではない。

TASK-083はDataset、training recipe、durable Job、worker、runtime/model acquisition、checkpoint/model write、評価、モデル承認を所有しない。

## 現在のAuthorityと依存

- 設計文書はPR #532でmainへmerge済みである。本Atomic Unitはeffect 0のpure contract/schema/fake backend/fault testsと、host inputを受け取らずnative effectをH3前に拒否するWindows composition boundaryだけを実装候補とする。Windows native reservationは未開始である。
- 将来のcontract実装は、TASK-046 current `TrainingInputSnapshot`、TASK-043 current `VOICE_MODEL_TRAINING` durable Jobからeffect 0の `Task083ResourceReservationPlanV1` を作る。OwnerはこのplanとTASK-084 destination planを確認し、両plan digest、Job/head、run、snapshot、recipe、compound operationをbindするTASK-046-owned `TrainingExecutionAuthorizationBindingV2` amendmentをH3で使用する。現行authorizationは両plan digestを持たないため代用不可とする。
- TASK-066 compute policy/probeはread-only advisory inputとし、TASK-083だけがlive reservation stateを所有する。
- current sourceではTASK-043 `_LOCAL_JOB_KINDS` に `VOICE_MODEL_TRAINING` がなく、TASK-066 `audio.voice.local` も `DISABLED_UNTIL_MAPPED` である。自己整合hashを持つbody-free `TrainingDurableJobBinding` はfixture入力には使えてもcanonical Job sourceやworkload mappingの代用にならない。pure production admissionは `DURABLE_JOB_SOURCE_NOT_AVAILABLE` と `VOICE_TRAINING_WORKLOAD_NOT_MAPPED` を含めて常に`BLOCKED`とする。
- pure contract、fake backend、fault testsは別の承認済み実装Unitでeffect 0として開始可能である。
- native resource observation/reservation、process/job assignment、training dispatchはHuman Gate `H3 TRAINING_START` まで禁止する。H3 V2とTASK-046-owned `VoiceTrainingCompoundOperationV1` amendmentがlandした後だけ、reservation activation、destination activation、exact revalidation、dispatchを一つのdurable operationとして順に行う。中間失敗でもauthorizationをburnし、同じauthorization/runを再利用しない。

## 将来の実装候補Allowed Files

1. `src/ai_video_production/task083_voice_training_resource_reservation.py`
2. `src/ai_video_production/task083_voice_training_resource_reservation_windows.py`
3. `schemas/task083-voice-training-resource-reservation.schema.json`
4. `src/ai_video_production/schema_resources/task083-voice-training-resource-reservation.schema.json`
5. `tests/test_task083_voice_training_resource_reservation.py`
6. `tests/test_task083_voice_training_resource_reservation_windows.py`
7. `docs/ai-team/tasks/TASK-083/task.md`
8. `CHANGELOG.md`（実装PRの最小Unreleased項目のみ）

既存TASK-043/046/066 sourceとshared roadmap/current-state/task-indexは変更禁止。候補scopeは設計merge、fresh currentness、sole-writer、clean dedicated worktree、exact Authority確認まで有効化しない。

## Body-free state machine and contract

- reservation stateのclosed transition matrixは次とする。

| source | allowed target |
|---|---|
| `PREPARED` | `RESERVED`、`EXPIRED`、`FAILED_CLOSED` |
| `RESERVED` | `CONSUMPTION_STARTED`、`EXPIRED`、`FAILED_CLOSED` |
| `CONSUMPTION_STARTED` | `CONSUMED`、`CONSUMPTION_UNKNOWN`、`FAILED_CLOSED` |
| `CONSUMED` / `EXPIRED` / `CONSUMPTION_UNKNOWN` / `FAILED_CLOSED` | none |

terminalからの遷移、direct skip、self-transition、reissue/reconsumeを禁止する。
- plan/readbackはproject、durable Job/head、run、Dataset snapshot、recipe、backend/build、device profile、resource floors/ceilings、current policy revision、expiryをbindする。
- V1 receipt discriminatorは `record_type=Task083ExecutionResourceReservationReceiptV1`、`schema_version=1`、`canonical_owner_task=TASK-083`、`receipt_role=TRAINING_RESOURCE_RESERVATION` とし、wrong type/version/owner/roleを拒否する。
- `RESERVED` はcurrent in-process/OS-owned capabilityとTASK-083 durable event ledgerの一致を要する。receipt、hash、dataclass、serialized tokenだけからauthorityを復元しない。
- `RESERVED → CONSUMPTION_STARTED` の線形化点はexclusive live lease下でのexpected reservation revision/headに対するdurable burn-event appendであり、TASK-046 compound operationの `RESERVATION_CONSUMPTION_STARTED` stageへcross-bindする。その後はexception/cancel/restartでも`RESERVED`へ戻さない。dispatch acknowledgementのexact readbackだけを`CONSUMED`とし、crash/lost reply/ambiguous completionは`CONSUMPTION_UNKNOWN`へ閉じる。
- restart時にdurable `RESERVED` eventがあってもmatching live OS capabilityが無ければ`FAILED_CLOSED`とし、再生成や再利用をしない。同runのexact duplicate requestはstate readbackだけを返す。
- effect-0 fixtureでも全request IDをpayload digestへindexし、exact duplicateはhistorical receiptではなくcurrent head/state readbackだけを返す。same ID/different payloadは拒否する。
- production backend、clock、device discovery、process bindingはtrusted composition rootが内部固定し、caller injectionやmonkeypatchをauthority pathで許さない。
- security-relevant JSONはstrict UTF-8、closed schemaとし、unknown/duplicate key、NaN/Infinity、BOM、trailing bytes、oversize/depthを拒否する。
- public receiptへ秘密、OS handle、process token、private path、environment body、raw hardware dumpを含めない。
- effect-0 state machineはfixture専用receipt/readback discriminatorを使用し、serialized receipt/readbackを `fixture_only=true`、`authority_created=false`、`live_capability_present=false`、`production_backend_invoked=false`、`resource_effect_count=0`、`training_started=false` に固定する。fixture observationの`live_capability_present`は合成入力factにすぎずserialized authorityではない。production `Task083ExecutionResourceReservationReceiptV1` はparse-only contractとし、このpure moduleからmintしない。
- fixtureのburn後`FAILED_CLOSED`に使うnegative acknowledgementはsealed ledgerが`CONSUMPTION_STARTED` head/revisionへbindして発行し、そのledger内で一度だけ照合・消費する。plan/reservation/timeだけからcallerが生成したrecord、別ledger/別head/revisionのrecordはproofとして扱わない。
- production receipt/readbackはTASK-083 plan digest、TASK-046-owned H3 `TrainingExecutionAuthorizationBindingV2` digest、TASK-084 destination plan digest、compound operation identity/digest/stageを必須bindする。missing/legacy/stale/wrong-scope H3またはlineage欠落ではproduction `RESERVED`を認めない。
- resource unitはCPUを`LOGICAL_PROCESSOR`、RAM/VRAM/diskを`BYTES`とする。fixture observationはdigest-only device projection、trusted `observed_at`/`fresh_until`、floor ≤ grant ≤ ceilingをclosed validationし、raw device/environment bodyを保持しない。
- 現行TASK-046 `ExecutionResourceReservationBinding`はclosed legacy field setである。TASK-083 V1からは既存fieldsだけのlegacy projectionを作り、`receipt_ref`/`receipt_sha256`でV1へbindするが、projection単独はauthorityを生成しない。別途許可されたTASK-046 consumer amendmentがV1とmatching live capabilityを検証するまでdispatchは`BLOCKED`とする。
- TASK-083 receiptはTASK-046 dispatch admissionの一条件であり、training start、model write、successful terminalを意味しない。

## Acceptance

- fake backendで全state transition、resource floors/ceilings、one-use、expiry、failure/restart readbackをeffect 0で検証する。
- caller-forged probe/token/dataclass、custom backend/clock/device、stale Job/head/snapshot/recipe/policy、cross-run、double/concurrent consumption、exception reuseを拒否し、training processを0に保つ。
- resource drift、GPU disappearance、memory/disk/thermal/power breach、clock rollbackはdispatch前なら`FAILED_CLOSED`へ閉じる。burn後の`FAILED_CLOSED`はprocess未開始、Job head不変、live lease解放をdurable negative acknowledgementで証明できる場合だけとし、partial dispatch/crash/lost/ambiguous replyは`CONSUMPTION_UNKNOWN`へ決定的に閉じる。どちらも同じauthorization/runを再利用しない。
- legacy projectionのunknown-field injection、V1 digest mismatch、wrong type/version/owner/role、projection-only replayを拒否する。
- TASK-046 consumer fixtureはexact live reservationとseparate H3 admissionの両方を要求する。
- independent Critic/Tester/JudgeでCritical/High 0、focused/negative/Windows tests PASS、external Evidence readback、scope exact、non-force push、単一Draft PRを満たす。

## 禁止事項

native resource reservation、process start/stop、model/runtime download、training、artifact write、paid provider、Release、Deploy、Production Activation、未知dirty破棄。
