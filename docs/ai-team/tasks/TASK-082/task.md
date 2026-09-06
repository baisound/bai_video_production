# TASK-082 — Owner音声Private Media Custody

- Status: `OWNER_DIRECTED_DESIGN_PROPOSAL / IMPLEMENTATION_NOT_STARTED`
- Development Depth: `DEV-4 FOUNDATION CRITICAL`
- Execution coordinator: Owner指定の「OBS録音→学習→WAV最適化」統合Task
- Canonical responsibility: TASK-082（本提案のreview/merge後に確定）

## 目的

OBSで録音したOwner音声を、公開Evidenceへ本文、秘密値、speaker fingerprint、絶対host pathを出さず、`RAW_CAPTURE`、`CANONICAL_PCM`、`PROCESSED_SPEECH_CONTINUOUS`、`REVIEW_TRANSCRIPT`、`TRAINING_COPY` の各世代として暗号化保管する。TASK-047/048/046の各producerは出力をTASK-082へpublishし、後続consumerはbody-free custody receiptを用いて、同じOwnerSubject、Consent、purpose、media generation、logical object、physical identity/currentnessを検証する。

TASK-082は録音、品質判定、TASK-003 Asset採用、Dataset採用、学習、モデル評価、ナレーション生成、最終WAV採用を所有しない。現行TASK-068はstrict JSONのimmutable publication/readbackだけを提供し、binary media、directory tree、mutable CAS、currentness selectionを提供しないため、TASK-082のphysical custody backendとして扱わない。将来のTASK-082 Windows backendがvoice-private binary custodyとgeneration-currentnessを固有責任として実装し、TASK-003のcanonical Asset責任を複製しない。

## 現在のAuthority

- 本Atomic Unitはこの文書、TASK-082 execution-order文書、TASK-083 task文書、TASK-084 task文書の設計・review・Evidence・commit/Draft PRに限定する。
- runtime source、Windows adapter、schema、mirror、test、`CHANGELOG.md` は本UnitのAllowed Filesではない。
- 以下の実装候補scopeは本設計が独立reviewされmainへmergeされた後、fresh currentness、sole-writer、専用clean worktree、exact Authorityを再確認して初めて有効になる。
- 実音声のimport/write/read/delete、暗号鍵・DACL設定、OBS/native操作はHuman Gate `H1 PRIVATE_CAPTURE` まで禁止する。

## 将来の実装候補Allowed Files

1. `src/ai_video_production/task082_owner_voice_private_media_custody.py`
2. `src/ai_video_production/task082_owner_voice_private_media_custody_windows.py`
3. `schemas/task082-owner-voice-private-media-custody.schema.json`
4. `src/ai_video_production/schema_resources/task082-owner-voice-private-media-custody.schema.json`
5. `tests/test_task082_owner_voice_private_media_custody.py`
6. `tests/test_task082_owner_voice_private_media_custody_windows.py`
7. `docs/ai-team/tasks/TASK-082/task.md`
8. `docs/ai-team/tasks/TASK-082/voice-pipeline-execution-order.md`
9. `CHANGELOG.md`（実装PRの最小Unreleased項目のみ）

既存TASK-003/014/041/046/047/048/068 source、shared roadmap/current-state/task-indexは変更禁止。scope追加は別のexact amendmentを要する。

## Body-free contract

- artifact classは `RAW_CAPTURE`、`CANONICAL_PCM`、`PROCESSED_SPEECH_CONTINUOUS`、`REVIEW_TRANSCRIPT`、`TRAINING_COPY` のclosed unionとする。
- receiptのdiscriminatorは `record_type=Task082PrivateMediaCustodyReceiptV1`、`schema_version=1`、`canonical_owner_task=TASK-082`、`receipt_role=PRIVATE_MEDIA_CUSTODY` とし、wrong type/version/owner/roleを拒否する。
- receiptはopaque artifact ID、logical slot ref、generation revision、predecessor receipt digest、OwnerSubject revision digest、purpose、artifact class、content digest、bounded media metadata digest、opened physical identity digest、cipher/backend identity digest、Consent/rights revision digest、event/head digestをbindする。
- public projection、argv、stdout、log、exception、Evidenceへ音声、transcript本文、speaker fingerprint、鍵、token、秘密値、絶対host pathを保持・返却しない。
- security-relevant JSONはstrict UTF-8とし、unknown field、duplicate key、NaN/Infinity、BOM、trailing bytes、oversize、過剰depthを拒否する。
- state/currentnessはmutable `current=true` fieldやmtime/filenameから決めない。各logical slotのclosed immutable event unionは `GENERATION_PUBLISHED`、`GENERATION_REVOKED`、`GENERATION_QUARANTINED`、`GENERATION_EXPIRED` とする。最初のpublishはrevision 1/predecessor null、以後のeventは直前head digestとrevision+1を必須にする。新しい`GENERATION_PUBLISHED`は直前headをpredecessorとして新artifactをcurrentにし、直前generationのsuperseded状態はそこから導出する。tombstone eventは対象generationをnon-currentにし、後続publishはtombstone headをpredecessorにする。gap、fork、duplicate revision、rollback、unknown eventは`CURRENTNESS_NOT_CONFIRMED`とする。
- physical publish/readbackはTASK-082専用backendでsame-snapshot、nofollow、regular、`nlink=1`、pinned ancestor identity、no-replace、operation-owned temp、durable flush、post-publish pinned readbackを要求する。TASK-068 receiptやJSON file identityをbinary custody authorityへ昇格しない。
- receiptはauthorityのEvidenceであり、TASK-003 adoption、TASK-046 Dataset authority、TASK-048 QA authorityを生成しない。
- producer body ingressにはTASK-082-owned non-serializable `Task082PrivateMediaWriteLeaseV1`、consumer body accessには `Task082PrivateMediaReadLeaseV1` を使う。leaseはexact producer/consumer Task、artifact class/generation、purpose、operation、OwnerSubject、Consent/decision revision、custody receipt/head、expiry、one-use/replay policyをbindする。receiptだけ、logical refだけ、hashだけ、caller pathだけからleaseを発行しない。
- write leaseはproducer output identityとexpected logical-slot predecessor/headをbindする。まだ存在しないTASK-003 adoption/readbackを要求せず、publish/pinned readback receiptを後続TASK-003へ渡す。
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
- private bodyはtrusted in-process stream/OS handleで渡し、public surfaceへpath/body/keyを返さない。consumerはlease lifetime外へplaintextを保持せず、close時にhandleを閉じ、実装可能な一時bufferをzeroizeする。zeroization未確認、close failure、handle identity driftはsuccessにしない。
- delete/revokeは別の明示Human Gateを要する。logical refやpath名だけで対象を決めず、current physical identityを再検証する。

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
- wrong receipt type/version/owner/role、wrong subject/purpose/Consent、stale/revoked、generation gap/fork/rollback、cross-generation、path traversal、drive-root child、symlink/reparse/hardlink、ancestor swap、same-bytes/different-identity、concurrent publish、foreign temp、readback/durability failureをeffect 0で拒否する。
- private bodyがpublic surfaceへ漏れないことをnegative vectorで検証する。
- wrong producer/consumer/purpose/operation、stale Consent/decision/head、expired/double-open lease、receipt-as-capability、path-only access、close/zeroization/readback ambiguityを拒否する。
- TASK-047/048/046 consumer fixtureはexact receipt、purpose-bound lease、body-free completion readbackを別々に検証し、receiptだけをbody accessや別責任へ昇格させない。
- independent Critic/Tester/JudgeでCritical/High 0、focused/negative/Windows regression PASS、外部Evidence保存/readback、scope exact、non-force push、単一Draft PRを満たす。

## 禁止事項

実ユーザーデータ削除、未知dirty破棄、drive-root artifact、automatic Asset/Dataset adoption、automatic training、model/provider実行、Release、Deploy、Production Activation。
