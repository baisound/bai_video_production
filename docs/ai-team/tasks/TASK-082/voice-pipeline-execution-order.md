# Owner音声 OBS→学習→最適WAV 実行順

- TASK-082 Status: `PURE_CUSTODY_CORE_IMPLEMENTATION_CANDIDATE / WINDOWS_BACKEND_NOT_STARTED`
- Scope: TASK-082/083/084の責任境界と全voice pipelineの実行順
- Effect ceiling: 0（設計、readback、strict validationのみ）

## Current-source gap

既存実装を作り直さず、producer receiptとconsumer adoptionを同一視しない。

- TASK-047: OBS plugin、installer、selected-source transportの技術基盤は存在する。実音声のprivate custodyとcanonical Asset readbackは未成立。
- TASK-082: Draft PR `#534`にV2 pure custody core candidateが存在する。strict parser、immutable generation event/currentness、write/read admission、body-free completion、fixture-only one-use stateは実装候補として検証済みだが、Windows backend、private body access、production lease、暗号化media I/Oは未着手である。
- TASK-048: speech-continuous WAV、silence/fade、peak/clipping/dropout/room-tone、HVAC OFF/ON A/Bの契約とfixtureは存在する。実音声測定と正式QA receiptは未成立。
- TASK-046: recording、Dataset revision、training intent/admission、synthetic model-builder基盤は存在する。正式Dataset採用、実学習engine/worker、terminal model custodyは未成立。
- TASK-014/TASK-075: local narration preflight、render admission、body-free call/result境界は存在する。Owner承認済みfine-tuned model artifactを用いたactual WAVは未成立。
- TASK-068: strict JSON immutable publication/readbackは存在するが、binary media/model、directory-tree commit、mutable phase CAS、currentness selectionは意図的に提供しない。TASK-082/084のphysical custody backendとして昇格させない。
- TASK-046 current reservation consumer: legacy `ExecutionResourceReservationBinding` のclosed field setだけを受ける。TASK-083 V1を検証する別途許可されたbridge/amendmentがlandするまでtraining dispatchはBLOCKEDとする。

未割当だった責任を次の独立Taskへ分ける。

1. TASK-082: Owner voice private-media custody
2. TASK-083: training execution-resource reservation
3. TASK-084: encrypted voice-model artifact custody

本統合Taskは依存順と開発実行をcoordinateするが、各Taskのcanonical authority、state、receiptを統合・移転・aliasしない。

## TASK-082 V2 pure-core seam

| record / state | exact V2 boundary | source of truth |
|---|---|---|
| custody receipt | `Task082PrivateMediaCustodyReceiptV2` / schema `2` / role `PRIVATE_MEDIA_CUSTODY` | TASK-082 source + canonical schema + byte-identical package mirror |
| generation event | `Task082PrivateMediaGenerationEventV2` / schema `2` / role `PRIVATE_MEDIA_GENERATION_EVENT` | same exact3 |
| lease decision | `Task082PrivateMediaLeaseDecisionV2` / schema `2` / role `PRIVATE_MEDIA_LEASE_DECISION` | same exact3; fixture-only and body-free |
| completion readback | `Task082PrivateMediaLeaseCompletionReadbackV2` / schema `2` / role `PRIVATE_MEDIA_LEASE_COMPLETION_READBACK` | same exact3; write/read completion variant is closed |
| currentness / sentinel | sealed in-memory `GenerationCurrentness` and `Task082FixtureLeaseSentinel` | source + focused test only; neither is a production capability |

V2 eventの`custody_binding_sha256`はfinal custody receipt digestではない。`TASK082_PRIVATE_MEDIA_STAGED_CUSTODY_BINDING_V2\0` domainでevent/receipt共通media identityから計算し、両parserが再計算する。complete receiptは別の`receipt_sha256`を`TASK082_PRIVATE_MEDIA_CUSTODY_RECEIPT_V2\0` domainで持つ。V1 discriminator、`custody_receipt_sha256`名へのpartial binding格納、binding/final receipt alias、event/receipt media identity差替えは拒否する。

V2の残りのdigest domainはgeneration event=`TASK082_PRIVATE_MEDIA_GENERATION_EVENT_V2\0`、currentness=`TASK082_PRIVATE_MEDIA_CURRENTNESS_V2\0`、lease decision=`TASK082_PRIVATE_MEDIA_LEASE_DECISION_V2\0`、completion readback=`TASK082_PRIVATE_MEDIA_LEASE_COMPLETION_READBACK_V2\0`とする。schema `$id` は `bai.task082.owner-voice-private-media-custody.v2` であり、canonical schemaとpackage mirrorのfield/version/domain説明がsource/testと一致しなければReadyにしない。

全currentness/decision/completionは `fixture_only=true`、`authority_created=false`、`body_access_granted=false`、`production_backend_invoked=false`、`private_media_effect_count=0` に固定する。このcandidateが返すREADYはsynthetic fixture stateだけであり、Windows/backend/native/private effectの実行可否を表さない。

## Canonical dependency DAG

次のDAGにあるTASK-082 one-use write/read lease、publish、open、burnは将来のWindows backend stageである。現行V2 pure core candidateはその手前のstrict validationとfixture-only decision/readbackで停止する。

```text
TASK-082 private custody plan/readiness
→ TASK-047 H1 PrivateCaptureExecutionAuthorizationBindingV1 candidate
→ H1 PRIVATE_CAPTURE
→ TASK-047 Q1 real RAW_CAPTURE/CANONICAL_PCM producer receipts
→ TASK-082 one-use write lease + raw/canonical custody publish + pinned readback
→ TASK-003 raw/canonical Asset adoption + readback
→ TASK-082 one-use quality-processing read lease for TASK-048
→ TASK-048 Q2 actual quality + speech-continuous finishing + HVAC A/B
→ TASK-048 PROCESSED_SPEECH_CONTINUOUS/TRAINING_COPY producer receipts
→ TASK-082 one-use write lease + processed/training-copy custody publish + pinned readback
→ TASK-003 processed/training-copy Asset adoption + readback
→ TASK-082 one-use Dataset-intake read lease for TASK-046
→ TASK-046 Q3a production intake + REVIEW_TRANSCRIPT producer receipt
→ TASK-082 one-use write lease + review-transcript custody publish + pinned readback
→ TASK-082 one-use Dataset-review read lease for TASK-046/Human review surface
→ TASK-046 Q3b Dataset proposal consuming exact transcript custody/read completion receipts
→ H2 DATASET_ADOPTION
→ TASK-046 Q4 Dataset revision + TrainingInputSnapshot
→ TASK-043 VOICE_MODEL_TRAINING durable Job/head
  + TASK-083 ResourceReservationPlanV1 (effect 0)
  + TASK-084 OutputArtifactDestinationPlanV1 (effect 0)
→ H3 TRAINING_START
→ one compound operation:
  TASK-083 live one-use reservation activation
  → TASK-084 encrypted destination activation
  → exact Job/snapshot/recipe/authorization/resource/destination revalidation
  → TASK-083 reservation consumption durable burn
  → TASK-082 one-use VOICE_MODEL_TRAINING read lease/open for TRAINING_COPY
  → TASK-046 training dispatch
→ TASK-046 checkpoint producer event (zero or more)
→ per checkpoint: TASK-084 checkpoint child write lease issue/open + immutable file-set seal + pinned readback
→ TASK-046 successful terminal producer event
→ TASK-084 terminal child write lease issue/open + immutable terminal file-set seal + pinned readback
→ TASK-046 non-selectable ModelArtifactBinding
→ TASK-046 ModelCandidateRevision(EVALUATION_PENDING, model/production use=false)
→ TASK-046 future ModelEvaluationAuthorizationBindingV1
→ TASK-084 one-use held-out-evaluation model load lease for TASK-046
→ TASK-046 EvaluationReceipt referencing the pending candidate
→ TASK-046 future/unlanded CandidateEvaluationAdmissionV2
→ TASK-046 evaluated child candidate binding exact pending parent + EvaluationReceipt
→ H4 MODEL_APPROVAL
→ TASK-014 FineTunedModelBinding
→ TASK-075 inference admission/operation
→ TASK-084 one-use approved-inference model load lease for TASK-014/TASK-075
→ TASK-075 local inference
→ TASK-014 durable staged/POST WAV
→ same script/seed/quality policyによるzero-shot対fine-tuned A/B
→ TASK-048 technical QA
→ TASK-041 Owner listening
→ H5 FINAL_WAV_ADOPTION
→ TASK-003 optimized WAV Asset adoption + readback
```

後段は前段receiptを推測、relabel、rehash、自己発行してはならない。missing/stale/ambiguous receiptは当該effectだけをparkし、独立したdesign、strict parser、negative/fault fixture、disabled-state検証は継続できる。

## Responsibility matrix

| Phase | Canonical owner | Owns | Must not own |
|---|---|---|---|
| private-media custody | TASK-082 | encrypted binary media generations、immutable event chain、currentness receipt、purpose-bound write/read lease | capture、quality、Asset/Dataset adoption、training |
| OBS capture | TASK-047 | callback transport、session/segment、capture terminal | custody、Asset adoption、training |
| canonical media Asset | TASK-003 | AUDIO Asset adoption/readback | capture、quality判定、Dataset |
| quality/finishing | TASK-048 | technical QA、speech-continuous derived WAV、HVAC A/B | Dataset採否、training、final adoption |
| Dataset/training/evaluation | TASK-046 | intake、membership proposal、snapshot、worker、candidate/evaluation | custody、resource broker、final Asset |
| durable training Job | TASK-043 | Project/current Job CAS/readback | resource/model semantics |
| training resources | TASK-083 | resource plan、live CPU/GPU/RAM/VRAM/disk/thermal reservation、one-use burn/readback | training、model write、Dataset |
| model-artifact custody | TASK-084 | encrypted immutable checkpoint/terminal file-set custody receipt、purpose-bound write/load lease | ModelArtifactBinding、evaluation、approval、selection、inference |
| narration call/result | TASK-014/TASK-075 | admission、call、worker result、staged/POST WAV | Dataset/training/model approval |
| listening/final adoption | TASK-041/TASK-003 | Human decision、final Asset adoption/readback | technical QA、model approval |

責任行は将来のcanonical ownershipを示し、実装済み範囲を示さない。現在のTASK-082実装候補はpure V2 metadata coreだけで、encrypted binary mediaとproduction leaseは`WINDOWS_BACKEND_NOT_STARTED`である。

## Human Gates

各Gateのtarget versioned contractはclosed `record_type`/version、canonical owner、subject、purpose/scope、exact operation/run、bound input revision digests、issued/expires/revoked state、one-use/replay policy、previous decision/burn digestを持つ。H1/H5はfuture V1、H2/H3/H4はfuture V2 amendmentである。現行recordに存在しないfieldを「再利用」で補ったことにせず、versioned owner amendmentがlandするまで当該effectをBLOCKEDにする。receipt/hash/serialized bodyだけでauthorityを再生成せず、lost replyはdurable decision/readbackへ戻る。

- `H1 PRIVATE_CAPTURE`: TASK-047-owned future `PrivateCaptureExecutionAuthorizationBindingV1` がexact safe-root readiness digest、capture Consent/rights、OwnerSubject、current principal/DACL/cipher/key、retention、OBS source/session、capture operationをbindする。one-use burn後のreplayは拒否する。
- `H2 DATASET_ADOPTION`: 現行 `DatasetCandidateReviewDecision` はそのままEvidenceとして保持するが、H2 effectにはTASK-046-owned versioned `DatasetCandidateReviewDecisionBindingV2` amendmentを要求する。V2はQ1/Q2 Asset、review transcript custody/read completion、proposal revision、adoption operation、expiry/revocation、one-use/replayをbindする。V2とDataset ownerのadoption transaction/readbackがlandするまでmembershipはBLOCKEDとし、decisionだけではmembershipを作らない。
- `H3 TRAINING_START`: 現行 `TrainingExecutionAuthorizationBinding` はTASK-083/TASK-084 plan digestを持たないため単独使用しない。TASK-046-owned `TrainingExecutionAuthorizationBindingV2` amendmentがcurrent snapshot、recipe、durable Job/head、run、compound operation、TASK-083 reservation plan digest、TASK-084 destination plan digest、expiry/revocation、one-use/replayを直接bindするまでH3をBLOCKEDとする。V2消費後だけ同じcompound operation内でlive reservation/destinationをactivateし、全binding再検証後にdispatchする。runtime/model acquisitionは別の明示Gateとする。
- `H4 MODEL_APPROVAL`: 現行 `OwnerModelApprovalDecisionBinding` はそのままEvidenceとして保持するが、H4 effectにはTASK-046-owned `OwnerModelApprovalDecisionBindingV2` amendmentを要求する。V2はterminal custody receipt、`ModelArtifactBinding`、held-out evaluation、`CandidateEvaluationAdmissionV2`で成立したexact evaluated child candidate digest、model/voice identity、安全性、operation/run、expiry/revocation、one-use/replayをbindする。pending parent digest、legacy current candidate、digest読み替え、単純rehashは代用不可とする。両amendmentの設計、独立review、実装、merge、current readbackまでH4、promotion、selection、`FineTunedModelBinding`、inferenceをBLOCKEDとする。
- `H5 FINAL_WAV_ADOPTION`: TASK-041-owned future `OwnerNarrationListeningDecisionBindingV1` がsame-condition pair、TASK-048 QA、listening decisionをbindし、TASK-003の別final Asset adoption transaction/readbackがoptimized WAVをexact 1回採用する。listening decisionだけではAssetを作らない。

自動Dataset採用、自動学習、自動resource consumption、自動モデル昇格、自動最終WAV採用は禁止する。

## H3 compound operation and recovery

TASK-046は別途許可されたconsumer/coordinator amendmentで `VoiceTrainingCompoundOperationV1` を所有する。全stage recordは同じ `compound_operation_id`、Job/head、run、snapshot、recipe、H3 V2、TASK-083/TASK-084 plan、monotonic revision、predecessor digestをbindする。

```text
PREPARED
→ AUTHORIZATION_BURNED
→ RESERVATION_ACTIVE
→ DESTINATION_ACTIVE
→ REVALIDATED
→ RESERVATION_CONSUMPTION_STARTED
→ TRAINING_COPY_OPEN_STARTED
→ DISPATCH_STARTED
→ DISPATCH_ACKNOWLEDGED
```

- `AUTHORIZATION_BURNED`より前の失敗はeffect 0の`FAILED_CLOSED`、burn後かつdispatch前の失敗はnon-replayable `FAILED_CLOSED` とし、新attemptにはnew run/plans/authorizationを要求する。
- `RESERVATION_CONSUMPTION_STARTED`はTASK-083 durable burn eventとmatching live capability、`TRAINING_COPY_OPEN_STARTED`はTASK-082 training read lease burnをcross-bindする。destination activationはreadinessだけであり、TASK-084 write lease/body accessを作らない。各burn後は同run/authorization/leaseを再利用せず、新attemptにnew run/plans/authorizationを要求する。
- `DISPATCH_STARTED`のdurable appendをdispatch線形化点とする。以後のcrash/lost reply/ambiguous resultは`COMPLETION_UNKNOWN`へ閉じ、TASK-043 current JobとTASK-046 worker terminalをreadback/reconcileするまで二回目のdispatchを禁止する。
- exact duplicateはstage readbackだけを返し、activation、body access、dispatchをreplayしない。TASK-046 amendmentがlandするまでcompound operation全体を`BLOCKED`とする。

Post-dispatch output custodyはcompound start stageのpre-issued leaseを使わない。各TASK-046 producer eventごとに、same compound/run/destination、event type、checkpoint index/progressまたはsuccessful terminal digest、current event predecessorをbindしたTASK-084 child write leaseを発行し、`CHECKPOINT_WRITE_OPEN_STARTED → CHECKPOINT_SEALED` を0回以上、最後に `TERMINAL_WRITE_OPEN_STARTED → TERMINAL_SEALED` をexact 1回進める。各`OPEN_STARTED`がそのchild leaseのdurable burnであり、duplicate/lost replyはstate readbackだけ、別variant/別event/double-openはfail closedとする。

## Safe parallel work

1. TASK-082/083/084のdesign、pure contract、strict schema、versioned receipt discriminator、synthetic negative/fault fixturesは相互にauthorityを生成しない範囲で並行可能。
2. TASK-047/048はH1待ちでもsynthetic harness、format/quality/fault matrix、consumer compatibilityを進められる。
3. TASK-046はH2/H3待ちでもQ3/Q4 strict consumer、worker protocol、checkpoint/terminal parser、fake-backend representative stepを進められる。
4. TASK-014/075はH4待ちでもfine-tuned route disabled state、reference-read-zero、same-condition A/B planを進められる。
5. 一つのHuman Gateやdependency failureは該当effectだけをparkし、別責任のauthorityへ越境しない独立Unitを止めない。

TASK-083 V1はcurrent TASK-046 legacy reservation fieldsへbody-free projectionできるが、projection単独ではauthorityを作らない。TASK-046がV1 receipt/current live capabilityを検証するconsumer amendmentと、H3 V2/compound coordinator amendmentが別途review/mergeされるまでtraining dispatchは必ずBLOCKEDとする。

Training resumeはstart pathを再利用しない。checkpoint custody/head、TASK-043 recovery readback、new current TASK-083 reservation、H3 V2 `scope=RESUME`、new compound operationを要求する。resumeのclosed pre-dispatch tailは `REVALIDATED → RESERVATION_CONSUMPTION_STARTED → TRAINING_COPY_OPEN_STARTED → MODEL_RESUME_LOAD_OPEN_STARTED → DISPATCH_STARTED` とし、`MODEL_RESUME_LOAD_OPEN_STARTED`でTASK-084 `TRAINING_RESUME` leaseをdurably burnする。terminal binding、H4、inference authorityはresume authorityとして使用禁止とする。

Candidate evaluation promotionはTASK-046だけが所有する。future `CandidateEvaluationAdmissionV2` はpending parent digestとEvaluationReceipt digestをbindし、childで変更可能なfieldをrevision/parent/state/evaluation-receipt/created-at/self-digestのclosed setへ限定する。それ以外のartifact、run、snapshot、Consent/rights/license、model identity lineageは不変であり、TASK-084はcandidate生成、評価、promotion、approvalを行わない。

## Evidence and PR policy

- 各Taskは一つの責任境界をAtomic Unitとしてcommit-readyまで閉じる。
- external Evidenceはcanonical Task Evidence rootの `TASK-###/<atomic-unit>/<run-id>/` に保存し、停止・handoff前にread backする。
- public Evidence、PR、log、receiptへ実音声、transcript本文、秘密値、speaker fingerprint、private absolute pathを含めない。
- exact head、required checks SUCCESS、Critical/High 0、independent review、overlap/conflict 0をReady/merge前に再確認する。
- 本coordination laneはcommit、non-force push、Draft PRまでを行い、Ready/mergeはPR統合/main管理へhandoffする。
