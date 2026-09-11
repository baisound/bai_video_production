# TASK-082 — Owner音声Private Media Custody

- Status: `PURE_CUSTODY_CORE_IMPLEMENTATION_CANDIDATE / WINDOWS_BACKEND_IMPLEMENTATION_CANDIDATE`
- Development Depth: `DEV-4 FOUNDATION CRITICAL`
- Execution coordinator: Owner指定の「OBS録音→学習→WAV最適化」統合Task
- Canonical responsibility: TASK-082（設計PR `#532`で確定。pure coreとWindows backendはPR `#534`のimplementation candidate）

## 目的

OBSで録音したOwner音声を、公開Evidenceへ本文、秘密値、speaker fingerprint、絶対host pathを出さず、`RAW_CAPTURE`、`CANONICAL_PCM`、`PROCESSED_SPEECH_CONTINUOUS`、`REVIEW_TRANSCRIPT`、`TRAINING_COPY` の各世代として暗号化保管する。TASK-047/048/046の各producerは出力をTASK-082へpublishし、後続consumerはbody-free custody receiptを用いて、同じOwnerSubject、Consent、purpose、media generation、logical object、physical identity/currentnessを検証する。

TASK-082は録音、品質判定、TASK-003 Asset採用、Dataset採用、学習、モデル評価、ナレーション生成、最終WAV採用を所有しない。現行TASK-068はstrict JSONのimmutable publication/readbackだけを提供し、binary media、directory tree、mutable CAS、currentness selectionを提供しないため、TASK-082のphysical custody backendとして扱わない。PR `#534`のTASK-082 Windows backend implementation candidateがvoice-private binary custodyとgeneration-currentnessを固有責任として実装し、TASK-003のcanonical Asset責任を複製しない。

## 現在のAuthority

- `PURE-CUSTODY-CORE-R0`は次のexact6だけを所有する。
  1. `src/ai_video_production/task082_owner_voice_private_media_custody.py`
  2. `schemas/task082-owner-voice-private-media-custody.schema.json`
  3. `src/ai_video_production/schema_resources/task082-owner-voice-private-media-custody.schema.json`
  4. `tests/test_task082_owner_voice_private_media_custody.py`
  5. `docs/ai-team/tasks/TASK-082/task.md`
  6. `docs/ai-team/tasks/TASK-082/voice-pipeline-execution-order.md`
- pure coreはbody-free metadata validation、event/currentness derivation、fixture-only admission/state/readbackだけを実装する候補であり、private body access、authority mint、Windows/backend/native effectを持たない。
- `WINDOWS-PRIVATE-CUSTODY-BACKEND-R0`は `src/ai_video_production/task082_owner_voice_private_media_custody_windows.py` と `tests/test_task082_owner_voice_private_media_custody_windows.py` のexact2だけを追加所有し、同じDraft PR `#534`へ統合されたimplementation candidateである。
- Owner CHANGELOG Rule（`2026-09-11`）に従い、Product versionを変更しない本ordinary implementation PRはshared `CHANGELOG.md`を変更・予約しない。Ready/mergeにはProduct version consistency、policy-current checkerによるexact candidate headのRelease metadata PASS、必要なregressionと独立review、fresh main・scopeの再確認を要する。実際にProduct versionを変更するPRだけは、そのexact release-version headingを含むCHANGELOG更新とserialized release/version-bump coordinationを別途要する。
- 実音声のimport/write/read/delete、暗号鍵・DACL設定、OBS/native操作は未実行である。candidateの存在やHuman Gateの承認状態だけでは、live lease、private body access、native/Production authorityを生成しない。

既存TASK-003/014/041/046/047/048/068 source、shared roadmap/current-state/task-indexは変更禁止。scope追加は別のexact amendmentを要する。

## Body-free contract

- artifact classは `RAW_CAPTURE`、`CANONICAL_PCM`、`PROCESSED_SPEECH_CONTINUOUS`、`REVIEW_TRANSCRIPT`、`TRAINING_COPY` のclosed unionとする。
- receiptのdiscriminatorは `record_type=Task082PrivateMediaCustodyReceiptV2`、`schema_version=2`、`canonical_owner_task=TASK-082`、`receipt_role=PRIVATE_MEDIA_CUSTODY` とし、wrong type/version/owner/roleを拒否する。final `receipt_sha256` は `TASK082_PRIVATE_MEDIA_CUSTODY_RECEIPT_V2\0` domainと`receipt_sha256` fieldを除外したcomplete canonical JSONから計算する。
- receiptはopaque artifact ID、logical slot ref、generation revision、predecessor receipt digest、OwnerSubject revision digest、purpose、artifact class、content digest、bounded media metadata digest、opened physical identity digest、cipher/backend identity digest、Consent/rights revision digest、event/head digestをbindする。V2 `custody_binding_sha256` はevent publication前に計算可能なstaged bindingであり、final receipt digestではない。
- public projection、argv、stdout、log、exception、Evidenceへ音声、transcript本文、speaker fingerprint、鍵、token、秘密値、絶対host pathを保持・返却しない。
- security-relevant JSONはstrict UTF-8とし、unknown field、duplicate key、NaN/Infinity、BOM、trailing bytes、oversize、過剰depthを拒否する。
- state/currentnessはmutable `current=true` fieldやmtime/filenameから決めない。各logical slotのclosed immutable event unionは `GENERATION_PUBLISHED`、`GENERATION_REVOKED`、`GENERATION_QUARANTINED`、`GENERATION_EXPIRED` とする。最初のpublishはrevision 1/predecessor null、以後のeventは直前head digestとrevision+1を必須にする。新しい`GENERATION_PUBLISHED`は直前headをpredecessorとして新artifactをcurrentにし、直前generationのsuperseded状態はそこから導出する。tombstone eventは対象generationをnon-currentにし、後続publishはtombstone headをpredecessorにする。gap、fork、duplicate revision、rollback、unknown eventは`CURRENTNESS_NOT_CONFIRMED`とする。
- generation eventのdiscriminatorは `record_type=Task082PrivateMediaGenerationEventV2`、`schema_version=2`、`canonical_owner_task=TASK-082`、`receipt_role=PRIVATE_MEDIA_GENERATION_EVENT` とする。共通closed fieldはdiscriminator、event kind、logical slot ref、artifact class、event revision、predecessor event digest、OwnerSubject revision digest、purpose、Consent/rights revision digest、created/observed/fresh-until、trusted-time binding digest、event digestだけとする。event digestは `TASK082_PRIVATE_MEDIA_GENERATION_EVENT_V2\0` domainとevent-digest fieldを除外したcanonical JSONから計算する。
- `GENERATION_PUBLISHED`だけが `published_generation_revision`、opaque artifact ID、V2 `custody_binding_sha256`、content/media-metadata/opened-physical-identity/cipher-backend digestを非nullで持ち、`target_generation_revision`、`target_publish_event_sha256`、tombstone decision digestをnullにする。`custody_binding_sha256` は `TASK082_PRIVATE_MEDIA_STAGED_CUSTODY_BINDING_V2\0` domainで、opaque artifact ID、logical slot、generation、OwnerSubject、purpose、artifact class、content/media metadata/opened physical/cipher backend、Consent/rights、observed/fresh-untilの共通preimageから計算し、event parserとreceipt parserの双方が再計算する。binding mismatchとfinal receipt digestへのaliasを拒否する。`GENERATION_REVOKED`、`GENERATION_QUARANTINED`、`GENERATION_EXPIRED` は逆に、exact current `target_generation_revision`、同じlogical slotの`target_publish_event_sha256`、event-kindに一致するseparate decision/policy digestだけを非nullで持ち、artifact/custody/content/physical/cipher fieldと新しいpublished generationをnullにする。published/tombstone field混用、別slot/別class target、non-current target、同じtargetへの再tombstoneを拒否する。publish generationは同じslot/classの直前publish+1とし、event revisionとは別に管理する。
- physical publish/readbackはTASK-082専用backendでsame-snapshot、nofollow、regular、`nlink=1`、pinned ancestor identity、no-replace、operation-owned temp、durable flush、post-publish pinned readbackを要求する。TASK-068 receiptやJSON file identityをbinary custody authorityへ昇格しない。
- receiptはauthorityのEvidenceであり、TASK-003 adoption、TASK-046 Dataset authority、TASK-048 QA authorityを生成しない。
- Windows backend implementation candidateによるproducer body ingressにはTASK-082-owned non-serializable `Task082PrivateMediaWriteLeaseV1`、consumer body accessには `Task082PrivateMediaReadLeaseV1` を使う。これらはV2 body-free decision recordとは別のunmerged production-capability candidateである。leaseはexact producer/consumer Task、artifact class/generation、purpose、operation、OwnerSubject、Consent/decision revision、custody receipt/head、expiry、one-use/replay policyをbindする。receiptだけ、logical refだけ、hashだけ、caller pathだけからleaseを発行しない。
- write leaseはproducer output identityとexpected logical-slot predecessor/headをbindする。まだ存在しないTASK-003 adoption/readbackを要求せず、publish/pinned readback receiptを後続TASK-003へ渡す。
- write leaseのpurpose matrixは次の5 tupleだけをclosed setとして許可する。`producer_output_role`はproducer-owned versioned output event/receiptのclosed roleであり、TASK-082がproducer結果を自己発行、relabel、rehashしてはならない。required欄以外のcross-row authority fieldは拒否する。

| write purpose | exact producer | artifact class | required Consent scope | required producer output role | forbidden substitution |
|---|---|---|---|---|---|
| `CAPTURE_RAW_PUBLISH` | TASK-047 | `RAW_CAPTURE` | `OWNER_VOICE_CAPTURE` | `TASK047_RAW_CAPTURE_OUTPUT` | live callback/meter、canonical output、path/hashだけ |
| `CAPTURE_CANONICAL_PUBLISH` | TASK-047 | `CANONICAL_PCM` | `OWNER_VOICE_CAPTURE` | `TASK047_CANONICAL_PCM_OUTPUT` | raw float WAVE、暗黙48 kHz/mono、raw receipt再利用 |
| `QUALITY_SPEECH_CONTINUOUS_PUBLISH` | TASK-048 | `PROCESSED_SPEECH_CONTINUOUS` | `OWNER_VOICE_DATA_PREPARATION` | `TASK048_SPEECH_CONTINUOUS_OUTPUT` | capture Consent、QA decisionだけ、training-copy role |
| `QUALITY_TRAINING_COPY_PUBLISH` | TASK-048 | `TRAINING_COPY` | `OWNER_VOICE_DATA_PREPARATION` | `TASK048_TRAINING_COPY_OUTPUT` | speech-continuous role、Dataset/training authority |
| `DATASET_REVIEW_TRANSCRIPT_PUBLISH` | TASK-046 | `REVIEW_TRANSCRIPT` | `OWNER_VOICE_DATA_PREPARATION` | `TASK046_REVIEW_TRANSCRIPT_OUTPUT` | audio output、transcript本文、Dataset adoption decision |

同じcontent digestでもproducer、artifact class、purpose、Consent scope、producer output role、operation、expected slot/headのどれかが異なれば別tupleとして拒否する。TASK-003 adoptionはwrite前提ではなくpublish後consumerであり、write leaseへ偽装しない。
- read leaseのpurpose matrixは次のclosed setとする。required欄以外のcross-purpose authority fieldは拒否する。

| purpose | artifact / consumer | required binding | forbidden substitution |
|---|---|---|---|
| `QUALITY_PROCESSING` | Q1 `RAW_CAPTURE`/`CANONICAL_PCM` → TASK-048 | TASK-082 custody/head + matching current TASK-003 Asset adoption/readback + Q1 producer receipt | custody receiptだけ、未採用/別Asset revision |
| `DATASET_INTAKE` | Q2 `PROCESSED_SPEECH_CONTINUOUS`/`TRAINING_COPY` → TASK-046 Q3 | TASK-082 custody/head + matching current TASK-003 Asset adoption/readback + Q2 receipt | Dataset/training authority、別purpose lease |
| `DATASET_REVIEW` | `REVIEW_TRANSCRIPT` → TASK-046/Human review surface | TASK-082 transcript custody/head + Q3 transcript/proposal operation | TASK-003 Asset fields（このroleでは禁止）、audio/body receiptの代用 |
| `VOICE_MODEL_TRAINING` | `TRAINING_COPY` → TASK-046 training worker | TASK-082 custody/head + matching current TASK-003 adoption/readback + Q4 Dataset revision/`TrainingInputSnapshot` + TASK-043 Job/head + run/recipe + H3 V2 + compound operation | Q3 intake lease、receipt/path/hash単独、別run/purpose replay |

- write/read leaseのclosed transition matrixは次とする。

| source | allowed target |
|---|---|
| `PREPARED` | `ISSUED`、`EXPIRED`、`FAILED_CLOSED` |
| `ISSUED` | `OPEN_STARTED`、`EXPIRED`、`FAILED_CLOSED` |
| `OPEN_STARTED` | `CONSUMED`、`COMPLETION_UNKNOWN`、`FAILED_CLOSED` |
| `CONSUMED` / `EXPIRED` / `COMPLETION_UNKNOWN` / `FAILED_CLOSED` | none |

`OPEN_STARTED`のdurable burnをbody accessの線形化点にし、terminalからの遷移、direct skip、self-transition、reissue/reopenを禁止する。burn後のcrash/lost replyは`COMPLETION_UNKNOWN`でnon-replayableとし、exact duplicateはbody/capabilityを再送せずstate readbackだけを返す。write leaseの`CONSUMED`はpublish+pinned readback後、read leaseの`CONSUMED`はclose+handle identity+completion readback後だけ許可する。
- pure core candidateはstrict parser、event/currentness derivation、write/read admission compiler、body-free decision/completion readbackとfixture-only state machineを実装する。serialized decisionのdiscriminatorは `record_type=Task082PrivateMediaLeaseDecisionV2`、`schema_version=2`、`receipt_role=PRIVATE_MEDIA_LEASE_DECISION`、completionは `record_type=Task082PrivateMediaLeaseCompletionReadbackV2`、`schema_version=2`、`receipt_role=PRIVATE_MEDIA_LEASE_COMPLETION_READBACK` とする。decision/state/reasonはsourceが生成できるclosed unionだけをschema-validとし、`READY_FIXTURE_ONLY`、`BLOCKED`、`COMPLETION_UNKNOWN`の組合せを自由に読み替えない。
- `GenerationCurrentness`、`LeaseDecision`、`LeaseCompletionReadback`とnon-serializable `Task082FixtureLeaseSentinel`はsubclass、pickle、typed-object tamper、通常のstate rewindを拒否し、untrusted Mapping/Sequenceを一度だけbounded snapshot化してから検証する。全decision/currentness/readbackは `fixture_only=true`、`authority_created=false`、`body_access_granted=false`、`production_backend_invoked=false`、`private_media_effect_count=0` を固定する。
- pure core candidateはproduction `Task082PrivateMediaWriteLeaseV1` / `Task082PrivateMediaReadLeaseV1`、OS handle、stream、backend callを発行しない。Windows backend implementation candidateはfixture sentinelを必ず拒否し、live lease mint/open/burn前にexact grant/receipt、trusted time、Consent/currentness、root/DACL/cipher bindingを再検証する。候補実装の存在はH1/H2/H3該当Gate、native/private effect、Production authorityを代替しない。
- private bodyはtrusted in-process stream/OS handleで渡し、public surfaceへpath/body/keyを返さない。consumerはlease lifetime外へplaintextを保持せず、close時にhandleを閉じ、実装可能な一時bufferをzeroizeする。zeroization未確認、close failure、handle identity driftはsuccessにしない。
- delete/revokeは別の明示Human Gateを要する。logical refやpath名だけで対象を決めず、current physical identityを再検証する。

## PURE-CUSTODY-CORE-R0 V2 candidate checkpoint

- Canonical source candidate: `src/ai_video_production/task082_owner_voice_private_media_custody.py`
- Canonical schema: `schemas/task082-owner-voice-private-media-custody.schema.json`。`$id=bai.task082.owner-voice-private-media-custody.v2` とする。
- Package mirror: `src/ai_video_production/schema_resources/task082-owner-voice-private-media-custody.schema.json`。canonical schemaとbyte-identicalでなければfailとする。
- Focused contract tests: `tests/test_task082_owner_voice_private_media_custody.py`
- Single review surface: Draft PR `#534`。source/schema/testと本2文書を同じPR headでread backする。
- Digest domains are exact: `TASK082_PRIVATE_MEDIA_STAGED_CUSTODY_BINDING_V2\0`、`TASK082_PRIVATE_MEDIA_CUSTODY_RECEIPT_V2\0`、`TASK082_PRIVATE_MEDIA_GENERATION_EVENT_V2\0`、`TASK082_PRIVATE_MEDIA_CURRENTNESS_V2\0`、`TASK082_PRIVATE_MEDIA_LEASE_DECISION_V2\0`、`TASK082_PRIVATE_MEDIA_LEASE_COMPLETION_READBACK_V2\0`。V1 domainとの混用を許可しない。
- Candidate verification at the V2 implementation checkpoint: focused `84 PASS`、TASK-082/074/048/046 targeted regression `469 PASS`、independent Critic/Tester/JudgeでCritical/High `0`。これはprivate audio、Windows backend、native runtime、Production readinessの実行Evidenceではない。
- Current product state is `PURE_CUSTODY_CORE_IMPLEMENTATION_CANDIDATE / WINDOWS_BACKEND_IMPLEMENTATION_CANDIDATE`。private body、H1 effect、native runtime、Release metadata、Production Activationは未実行である。

## WINDOWS-PRIVATE-CUSTODY-BACKEND-R0 candidate checkpoint

- Canonical source candidate: `src/ai_video_production/task082_owner_voice_private_media_custody_windows.py`
- Focused tests: `tests/test_task082_owner_voice_private_media_custody_windows.py`
- CandidateはWindows Current User DPAPI、digest-only root/authorization verifier、root-pinned/no-replace/durable publication、generation CAS、one-use write/read lease、durable burn/completion/recovery readbackを境界とし、host path、plaintext body、key、reusable capabilityをpublic resultへ返さない。
- trusted-time freshnessはlease issuance時だけでなくopen時にも再検証し、write grantの`fresh_until`またはread custody receiptの`fresh_until`がstaleならprivate effect/body access前に拒否する。
- Synthetic/current-hash verification: focused freshness `2 PASS`、TASK-082/TASK-068 Windows/core targeted regression `300 PASS / 88 Windows-only skip`、hosted Windows Python 3.11/3.12/3.13 checks `PASS`、independent Critic/TesterでCritical/High `0`、Judgeはcommit/non-force pushを承認した。
- Windows local testは既存Pythonに`jsonschema`がなく`NOT_CONFIRMED`のままとし、install/PATH変更を行っていない。hosted Windows checkのPASSはcurrent PR headの実行Evidenceだが、実Owner音声、private root、DPAPI/DACL、OBS、native Product、Productionの実行Evidenceではない。

## Human Gate H1

Ownerは実行直前に、公開文書へ値を記載せず次を確認する。

1. exact private rootが既存のauthorized root配下であり、drive root/direct child、foreign/unknown pathでないこと
2. `OWNER_VOICE_CAPTURE` Consent/use-rightsとOwnerSubject revisionがcurrentであること
3. cipher backend、current Windows principal/SID、DACL、key scope/currentness
4. retention/revocation/delete policy
5. exact OBS source/sessionとTASK-047 capture operation
6. TASK-047が発行するfuture `PrivateCaptureExecutionAuthorizationBindingV1` のrecord type/version、OwnerSubject、Consent、custody readiness、capture operation、scope、issued/expires/revoked、one-use/replay policyが一致すること

設計承認、receipt hash、設定値の存在だけではH1を満たさない。

## Acceptance

- synthetic bytesのみで全artifact classのgeneration chainとbody-free receiptを検証する。
- eventはinitial event revision 1/predecessor null、publish generation 1、publish後tombstone、tombstone後republishをpositiveで固定する。wrong event type/version/owner/role、unknown event、event/generation revision gap・duplicate・fork・rollback、cross-slot/class replay、published/tombstone field混用、wrong/non-current target、同一target再tombstoneを拒否する。
- wrong receipt type/version/owner/role、wrong subject/purpose/Consent、stale/revoked、generation gap/fork/rollback、cross-generation、path traversal、drive-root child、symlink/reparse/hardlink、ancestor swap、same-bytes/different-identity、concurrent publish、foreign temp、readback/durability failureをeffect 0で拒否する。
- private bodyがpublic surfaceへ漏れないことをnegative vectorで検証する。
- wrong producer/consumer/artifact/output-role/purpose/operation、stale Consent/decision/head、TASK-003 adoption/currentness差替え、expired/double-open lease、direct skip/self-transition/reissue、receipt-as-capability、path-only access、close/handle identity/zeroization/readback ambiguityを拒否する。burn後lost replyは必ず`COMPLETION_UNKNOWN`、exact duplicateはstate readback-onlyで、body/capability再送を0にする。
- boundary fixtureは (1) TASK-047 RAW/CANONICAL write→TASK-048 `QUALITY_PROCESSING`、(2) TASK-048 PROCESSED/TRAINING_COPY write→TASK-046 `DATASET_INTAKE`、(3) TASK-046 REVIEW_TRANSCRIPT write→`DATASET_REVIEW`、(4) TASK-046 TRAINING_COPY→`VOICE_MODEL_TRAINING` の4 familyに限定する。各positiveにsame digest/wrong owner・artifact・generation・purpose・consumer、stale TASK-003 readback、receipt-as-capability negativeを表駆動で対応させる。TASK-014はFineTunedModelBindingがTASK-082 receipt/leaseを代用できないnegativeだけを持ち、model consumer positiveはTASK-084へ残す。
- invalid UTF-8、BOM、duplicate key、NaN/Infinity、trailing bytes、oversize/depth、bool-as-int、wrong scalar type、digest tamperを拒否し、canonical schemaとpackage resource mirrorのbyte parity/hash一致を検証する。
- TASK-047/048/046 fixtureはexact receipt、purpose-bound admission、fixture-only false-authority decision、body-free completion readbackを別々に検証し、receiptだけをbody accessや別責任へ昇格させない。
- independent Critic/Tester/JudgeでCritical/High 0、focused/negative/Windows regression PASS、外部Evidence保存/readback、scope exact、non-force push、単一Draft PRを満たす。

## 禁止事項

実ユーザーデータ削除、未知dirty破棄、drive-root artifact、automatic Asset/Dataset adoption、automatic training、model/provider実行、Release、Deploy、Production Activation。
