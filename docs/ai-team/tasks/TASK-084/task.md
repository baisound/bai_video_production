# TASK-084 — 音声モデルArtifact Custody

- Status: `PURE_CONTRACT_IMPLEMENTATION_CANDIDATE / WINDOWS_BACKEND_NOT_ADOPTED_NOT_CONFIRMED`
- Development Depth: `DEV-4 FOUNDATION CRITICAL`
- Execution coordinator: Owner指定の「OBS録音→学習→WAV最適化」統合Task
- Canonical responsibility: TASK-084（設計PR `#532`で確定。pure contractはDraft PR `#537`のimplementation candidate）

## 目的

voice trainingのcheckpointとterminal model artifactを暗号化されたrun固有destinationへimmutable/no-clobber file setとして保存し、content inventory、physical identity/currentness、model/runtime/recipe/license、Dataset snapshot、training Job/terminalを同じcustody receiptへbindする。

TASK-084はDataset採用、resource reservation、training実行、`ModelArtifactBinding`/`ModelCandidateRevision`生成、評価、モデル承認/選択、FineTunedModelBinding、inferenceを所有しない。現行TASK-068はJSON immutable publication/readbackだけを提供し、directory-tree commit、mutable phase CAS、model binary writeを明示的に提供しないため、TASK-084のphysical custody backendとして扱わない。

## 現在のAuthorityと依存

- 設計文書はPR `#532`でmainへmerge済みである。`PURE-CONTRACT-R0`のsource、canonical schema、package schema mirror、focused testsのexact4はcommit `e9d28ba686b3a2809c7f41ba6bea390beeca9943` / Draft PR `#537`の実装候補として存在する。Windows backendの受理済み実装・native実行は未確認である。
- 将来のcustody contractはTASK-046 training plan、TASK-043 current Job/head、TASK-083 planからeffect 0の `Task084OutputArtifactDestinationPlanV1` を作る。両plan digestをbindするTASK-046-owned `TrainingExecutionAuthorizationBindingV2` と `VoiceTrainingCompoundOperationV1` amendmentがlandした後だけH3 compound operationでdestinationをactivateし、TASK-046 engine terminalとTASK-083 consumed/consumption-started lineageを別々の入力として検証する。
- PR #536でmainへ統合されたTASK-083 pure planをcurrent-source依存とする。destination compilerはcaller-supplied digestだけを受け付けず、Mappingまたはexact `Task083ResourceReservationPlanV1` をcanonical parserで再検証し、project、Job ID/operation/revision/head/binding、snapshot ref/digest、Dataset、recipe ref/digest、runtime revision/digestをTASK-046入力と照合する。`run_id`はstableな`TrainingRunIntent.run_intent_id`へ固定し、`TrainingRunRevision.run_revision_id`を代用しない。`issued_at <= compiled_at < expires_at`を要求し、validated plan digestだけを出力へ保持する。
- TASK-083との接続は`PURE_CONTRACT_AVAILABLE_PRODUCTION_BLOCKED`であり、live reservationを意味しない。production/load admissionは`TASK083_PRODUCTION_RESERVATION_NOT_AVAILABLE_CURRENT_SOURCE`を含めて引き続き`BLOCKED`とする。compile時のcurrentnessはfuture H3/effect時の両plan・live bindingの再検証を代替しない。
- pure contract、synthetic artifact、fault testsは別の承認済み実装Unitでeffect 0として開始可能である。
- 実model/checkpoint write、cipher/key/DACL操作、retention/revoke/deleteはHuman Gate `H3 TRAINING_START` と該当する追加Gateまで禁止する。
- TASK-084はcheckpoint用 `Task084ModelCheckpointCustodyReceiptV1` とterminal用 `Task084ModelArtifactCustodyReceiptV1` だけを発行する。successful current terminalとpinned terminal custody readback後、TASK-046だけがterminal receiptを検証してnon-selectable `ModelArtifactBinding` を生成し、そこから`candidate_state=EVALUATION_PENDING`かつmodel/production use falseのpending candidateを登録できる。`EvaluationReceipt`はこのexact pending candidate digestを参照する。評価後のchildは、future/unlanded・TASK-046-owned `CandidateEvaluationAdmissionV2` とversioned candidate amendmentにより、exact pending parent digestとexact `EvaluationReceipt` digestを同時にbindして初めて`EVALUATED`になれる。
- pending→evaluated childで変更可能なclosed setは `revision`、`parent_candidate_sha256`、`candidate_state`、`evaluation_receipt_sha256`、`created_at`、`candidate_sha256` だけとする。artifact binding、run intent/terminal、Dataset snapshot、Consent/rights/license、model identityと全authoritative lineageはparentと完全一致を要求する。legacy current contract、digest読み替え、pending/evaluated混用、単純rehashでこのV2 admissionを代用しない。
- `CandidateEvaluationAdmissionV2`の設計、独立review、実装、merge、current readbackが完了するまでH4、promotion、selection、`FineTunedModelBinding`、model load/inferenceをfail closedで禁止する。checkpoint receiptやUNKNOWN/failed/cancelled/ambiguous terminalはbinding/candidate登録に使用不可とする。

## PURE-CONTRACT-R0 implementation checkpoint

- Candidate source: `src/ai_video_production/task084_voice_model_artifact_custody.py`。body-free metadata parser、destination plan、fixture inventory/event/lease/readbackとproduction/load admissionを実装する。productionとmodel loadのadmissionはcurrent sourceで`BLOCKED`に固定され、file I/O、暗号化、OS handle、model load、training/evaluation/inference authorityを生成しない。
- Canonical schema: `schemas/task084-voice-model-artifact-custody.schema.json`。package mirrorは`src/ai_video_production/schema_resources/task084-voice-model-artifact-custody.schema.json`で、両者はbyte-identicalである。
- Focused tests: `tests/test_task084_voice_model_artifact_custody.py`。上記commitの保存済みEvidenceはfocused `80 PASS`、直接依存regression `62 PASS`、独立Critic/Tester/JudgeのCritical/High `0`を記録する。これは既存の実行結果であり、本書の状態同期による再実行やnative確認を意味しない。
- Current-source統合修正の新しい検証はTASK-084 focused `113 PASS`、TASK-083 pure/Windows effect-zero `90 PASS`、TASK-043/046直接依存 `62 PASS`（合計`265 PASS / 0 FAIL / 0 SKIP`）、OSS readiness `12 PASS`である。schema mirror、Python compile、全5 ECMAScript patternのcompile/positiveと10 newline/CRLF negativeもPASS。新headのhosted Full regression・Security・metadataと最終独立reviewは別途確認する。
- 旧commitのhosted Ubuntu/Windows matrixとSecurityはPASS、旧`changelog-and-version`のFAILは履歴Evidenceとして保持する。現在のReady/merge判断は旧FAILの無条件免除ではなく、Owner CHANGELOG Rule（2026-09-11）に従うexact candidate headのmetadata、必要なFull regression、独立review、fresh main/scope/readbackを必須とする。
- 本checkpointは既存pure contractの実装事実だけを記録する。Windows backend、private model/checkpoint I/O、H3/H4、consumer統合、Release/Deploy/Productionの権限を追加しない。未追跡の実装ファイルは受理済みcandidateやnative Evidenceに含めない。

## 本pure contract統合PRのAllowed Files（exact5）

1. `src/ai_video_production/task084_voice_model_artifact_custody.py`
2. `schemas/task084-voice-model-artifact-custody.schema.json`
3. `src/ai_video_production/schema_resources/task084-voice-model-artifact-custody.schema.json`
4. `tests/test_task084_voice_model_artifact_custody.py`
5. `docs/ai-team/tasks/TASK-084/task.md`

Owner CHANGELOG Rule（`2026-09-11`）に従い、Product versionを変更しない本ordinary implementation PRはshared `CHANGELOG.md`を変更・予約しない。Product version consistency、policy-current checkerによるexact-head Release metadata PASS、必要なFull regressionと独立review、fresh main・scopeの再確認を経て通常Ready/mergeへ進める。実際にProduct versionを変更するPRだけは、そのexact release-version headingを含むCHANGELOG更新とserialized release/version-bump coordinationを別途要する。

将来のWindows backend source/testは本exact5に含めず、別の明示scopeとnative Gateを要する。foreign worktreeのunknown/untracked backendは`NOT_ADOPTED / NOT_CONFIRMED`とし、コピー・統合・実行しない。既存TASK-014/043/046/068/083 sourceとshared roadmap/current-state/task-indexは変更禁止。fresh currentness、sole-writer、clean dedicated worktree、exact Authorityを継続確認する。

## Body-free state machine and contract

- artifact phaseは `PREPARED → DESTINATION_ACTIVE → CHECKPOINT_PUBLISHED* → TERMINAL_SEALED | FAILED_CLOSED` のclosed transitionとする。phaseはmutable same-path journalで更新せず、operation/run、monotonic revision、predecessor digestを持つimmutable event chainから導出する。gap/fork/rollback/duplicate revisionは`FAILED_CLOSED`とする。
- destinationはopaque coordinateとし、public argv/receipt/log/Evidenceへabsolute host pathを出さない。
- checkpoint receipt discriminatorは `record_type=Task084ModelCheckpointCustodyReceiptV1`、`schema_version=1`、`canonical_owner_task=TASK-084`、`receipt_role=MODEL_CHECKPOINT_CUSTODY` とし、checkpoint index、training step/progress、checkpoint event predecessorを必須、terminal result/model terminal digestを禁止する。
- terminal receipt discriminatorは `record_type=Task084ModelArtifactCustodyReceiptV1`、`schema_version=1`、`canonical_owner_task=TASK-084`、`receipt_role=MODEL_ARTIFACT_CUSTODY` とし、successful terminal result、TASK-046 terminal digest、last checkpoint/event headを必須にする。wrong type/version/owner/role、cross-variant field、null/extra fieldをstrict schemaで拒否する。
- 両receiptはproject、Job/head、run、Dataset snapshot、recipe、engine/model/runtime/build/license、reservation identity/state digest、content inventory digest、各fileのopened physical identity digest、cipher/backend/principal/key-scope digestを共通bindする。
- TASK-084専用backendは各fileをoperation-owned temp handleからimmutable no-replaceでpublishし、durable flushとpinned readbackを行う。全fileを検証後、closed inventory manifestを最後にno-replace publishし、そのmanifestが存在するfile setだけをvisibleとする。directory-tree rename/commit、same-path mutable phase CAS、TASK-068のunsupported operationを要求しない。
- inventoryはclosed relative-file allowlist、bounded bytes/count/depth、regular、`nlink=1`、no reparseを要求する。同run以外のartifactやforeign/unknown tempを上書き、削除、repairしない。crashで未sealed file setが残ってもvisible/currentにせず、新operationは別identityを使う。
- security-relevant JSONはstrict UTF-8、closed schemaとし、unknown/duplicate key、NaN/Infinity、BOM、trailing bytes、oversize/depthを拒否する。
- public receipt/hash/dataclassはauthorityを生成せず、TASK-046 `ModelArtifactBinding`/evaluationとH4、TASK-014/TASK-075 inference admissionを別に要する。
- H3 pre-dispatchはdestination planのactivation/readinessとpinned destination identity確認だけを行い、body-capable write leaseを発行・open・burnしない。TASK-046 workerが各output producer eventを発行した後、そのeventを親にTASK-084-owned non-serializable `Task084ModelArtifactWriteLeaseV1` childをexact 1回発行する。checkpoint variantはcheckpoint receipt type/index/progress/event predecessor、terminal variantはsuccessful TASK-046 terminal digestとlast checkpoint/event headをbindし、cross-variant fieldを拒否する。private model accessにはpurpose-discriminated `Task084ModelLoadLeaseV1` を使う。
- load leaseのclosed purpose matrixは次とする。required欄以外のcross-purpose authority fieldは拒否する。

| purpose | required binding | expressly forbidden |
|---|---|---|
| `TRAINING_RESUME` | checkpoint custody receipt/head、same TASK-043 Job/head・run・snapshot・recipe、TASK-043 recovery readback、current TASK-083 reservation、future/unlanded TASK-046 H3 V2 `scope=RESUME`、resume compound operation | terminal `ModelArtifactBinding`、H4 approval、inference admission |
| `HELD_OUT_EVALUATION` | sealed terminal custody/readback、TASK-046-created non-selectable `ModelArtifactBinding`、exact `EVALUATION_PENDING` candidate digest、future/unlanded TASK-046 `ModelEvaluationAuthorizationBindingV1`、evaluation operation/run | H4 approval、FineTunedModelBinding、inference admission |
| `LOCAL_NARRATION_INFERENCE` | sealed terminal custody/readback、`ModelArtifactBinding`、current H4 V2 approval、TASK-014 `FineTunedModelBinding`、TASK-075 admission/operation、current Consent/rights | checkpoint receipt、approval前access、evaluation/resume authority |

- write/load leaseのclosed transition matrixは次とする。

| source | allowed target |
|---|---|
| `PREPARED` | `ISSUED`、`EXPIRED`、`FAILED_CLOSED` |
| `ISSUED` | `OPEN_STARTED`、`EXPIRED`、`FAILED_CLOSED` |
| `OPEN_STARTED` | `CONSUMED`、`COMPLETION_UNKNOWN`、`FAILED_CLOSED` |
| `CONSUMED` / `EXPIRED` / `COMPLETION_UNKNOWN` / `FAILED_CLOSED` | none |

durable `OPEN_STARTED` burn後は再openしない。terminalからの遷移、direct skip、self-transition、reissue/reopenを禁止し、exact duplicateはbody/capabilityを再送せずstate readbackだけを返す。write leaseの`CONSUMED`はmanifest-last seal+pinned readback後、load leaseの`CONSUMED`はclose+handle identity+completion readback後だけ許可する。private bytes/path/keyをpublic surfaceへ返さず、trusted stream/OS handleだけをlease lifetime中に渡す。close/identity/readback/zeroizationがNOT_CONFIRMEDならsuccessにしない。

## Acceptance

- synthetic immutable file setだけでcheckpoint/restart/terminal/duplicate/idempotent readbackを検証する。
- destination readinessからwrite body accessが得られないこと、producer event前のchild lease発行、同一producer eventの二重child発行/open、checkpoint/terminal cross-variantを拒否する。
- pending/evaluated candidate digest混用、wrong parent/evaluation receipt、closed set外のfield変更、legacy rehashによるV2代用、admission未landingでのH4/promotion/inferenceを拒否する。
- wrong type/version/owner/role、symlink/reparse/hardlink、ancestor swap、same-bytes/different-identity、target appears、temp replacement、partial/unsealed set、unexpected file、event-chain gap/fork/rollback、manifest swap、flush/readback failure、wrong Job/head/run/snapshot/recipe/reservation/terminalをfail closedで拒否する。
- foreign/unknown fileのoverwrite/deleteを0、failed/cancelled/ambiguous terminalからModelArtifactBindingを0、public path/secret/private model bytes leakageを0に保つ。
- wrong consumer/purpose/operation、cross-purpose field、checkpoint-as-terminal、approval前inference、missing resume/evaluation/inference authority、stale head、expired/double-open load lease、receipt-as-capability、path-only load、close/zeroization ambiguityを拒否する。
- TASK-046 evaluation consumerはexact terminal custody readbackとseparate evaluation/H4 authorityを要求する。
- independent Critic/Tester/JudgeでCritical/High 0、focused/negative/Windows tests PASS、external Evidence readback、scope exact、non-force push、単一Draft PRを満たす。

## 禁止事項

実学習、real checkpoint/model write、model/runtime download、automatic ModelCandidate registration/approval/select、inference、Release、Deploy、Production Activation、unknown cleanup。
