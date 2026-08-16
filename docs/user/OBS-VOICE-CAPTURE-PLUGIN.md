# OBS Voice Capture Plugin 導入・利用・復旧ガイド

> **文書状態: LOCAL DRAFT / 実機未確認**
> `P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`: `NOT_ESTABLISHED`

この文書は、BAI Video ProductionのOBS Voice Capture Pluginを安全に導入し、
録音操作と異常復旧を確認するための公開マニュアル案です。

現在、公開・導入可能なPlugin package、Version、SHA-256、実機load結果は確認されて
いません。値が未確認の欄を推測で埋めたり、この文書だけを根拠にPluginを導入・起動・
録音したりしないでください。

## このPluginが行うこと

将来の正式版は、利用者がOBS上で明示的に選択した音声Sourceから、録音Sessionの
開始・一時停止・再開・停止を安全に扱うことを目的とします。

次の処理は別の判断・権限です。

- OBSの音声や配信信号を自動で変更すること
- 録音素材を自動でAssetやDatasetへ採用すること
- 学習、Fine-tuning、Model生成を自動で開始すること
- 録音、Dataset採用、学習、公開のHuman Gateを省略すること

## 現在の確認状況

| 項目 | 値 | 状態 |
|---|---|---|
| 対応OBS build | 未確認 | 未確認 |
| Plugin package名 | 未確認 | 未確認 |
| Plugin version | 未確認 | 未確認 |
| Package SHA-256 | 未確認 | 未確認 |
| Package manifest SHA-256 | 未確認 | 未確認 |
| Module ID | 未確認 | 未確認 |
| 対応architecture | 未確認 | 未確認 |
| 署名・配布元・provenance | 未確認 | 未確認 |
| License・Notice | 未確認 | 未確認 |
| Install先layout | 未確認 | 未確認 |
| Backup先 | 未確認 | 未確認 |
| Rollback結果 | 未確認 | 未確認 |
| OBS load結果 | 未確認 | 未確認 |
| START/PAUSE/RESUME/STOP | 未確認 | 未確認 |
| 保存・異常終了・復旧 | 未確認 | 未確認 |

この表は、実成果物と実機Evidenceを得た後にだけ更新します。

## 判定語

各チェックは次のいずれかで記録します。

| 判定 | 意味 |
|---|---|
| `PASS` | 対象VersionとEvidenceを固定して確認済み |
| `FAIL` | 既知の不一致または失敗を確認済み |
| `UNKNOWN` | 処理結果や外部状態を確定できない |
| `未確認` | まだ確認を開始していない |
| `NOT_APPLICABLE` | 承認済みPolicy上、その項目が対象外 |

`UNKNOWN`や`未確認`を`PASS`へ読み替えないでください。件数や音声欠損が不明な場合も
`0`として扱いません。

## 1. 導入前チェックリスト

次の全項目が`PASS`になるまで、PluginファイルをOBSのフォルダーへコピーしません。

### 1.1 Authorityと対象

- [ ] 導入作業に対する明示的な許可がある — 状態: `未確認`
- [ ] 対象PC、OBS build、architectureが許可内容と一致する — 状態: `未確認`
- [ ] OBSが停止し、対象OBS processが0件である — 状態: `未確認`
- [ ] Scene Collection、Profile、Source設定を変更しない範囲が明確 — 状態: `未確認`
- [ ] 録音・Source選択・device操作は導入作業と別Gateである — 状態: `未確認`

### 1.2 Package identity

- [ ] Package名、Version、SHA-256が正式な成果物Evidenceと一致する — 状態: `未確認`
- [ ] Manifestに全file、相対path、size、SHA-256がある — 状態: `未確認`
- [ ] Module ID、architecture、OBS互換範囲が固定されている — 状態: `未確認`
- [ ] 配布元、source revision、build Evidenceが固定されている — 状態: `未確認`
- [ ] License、Notice、source-offer等の必要事項を確認した — 状態: `未確認`
- [ ] Package内に絶対path、Credential、音声、個人情報がない — 状態: `未確認`

### 1.3 Install先とcollision

- [ ] 対象rootが許可されたOBS install内に収まる — 状態: `未確認`
- [ ] `..`、絶対path、junction、symlink、reparse traversalがない — 状態: `未確認`
- [ ] 既存PluginとModule ID、filename、data/locale pathが衝突しない — 状態: `未確認`
- [ ] 同名で内容が異なる既存fileを検出した場合は停止する — 状態: `未確認`
- [ ] stagingとtargetが同一volumeである — 状態: `未確認`
- [ ] 必要disk容量とrollback用容量を確保した — 状態: `未確認`

## 2. Backupチェックリスト

Backupは導入前の状態を復元するためのものです。録音素材、Scene、Profileを無断で
収集する仕組みではありません。

- [ ] Backup operation IDを発行した — 状態: `未確認`
- [ ] 対象fileの存在・非存在を含む旧manifestを保存した — 状態: `未確認`
- [ ] 既存fileのsizeとSHA-256を記録した — 状態: `未確認`
- [ ] Backup先が対象root外かつ許可されたprivate領域である — 状態: `未確認`
- [ ] Backup先の空き容量と暗号化・retention方針を確認した — 状態: `未確認`
- [ ] Backup後に全fileをread-backし、manifestと一致した — 状態: `未確認`
- [ ] Backup EvidenceにCredential、host path、device fingerprintを公開しない — 状態: `未確認`

Backup manifestに最低限必要な項目:

```text
backup_operation_id
source_manifest_sha256
backup_manifest_sha256
relative_path
file_state = PRESENT | ABSENT
byte_size
sha256
created_at
retention_state
verification_state
```

## 3. 導入チェックリスト

正式なoperation手順とpackageが未確定のため、現在は実行しません。将来の導入では、
次の順序を崩さないでください。

1. Packageを許可されたstaging領域へ展開する。
2. 展開後manifest、file size、SHA-256、containmentを検証する。
3. OBS processが0件であることをもう一度確認する。
4. Backup Evidenceが`PASS`であることを確認する。
5. Journalを作成し、publish前状態を`PENDING_STAGED`として記録する。
6. 同一volume上の承認済みpublish操作を開始する。
7. targetの全fileをread-backし、manifestと照合する。
8. 全項目一致時だけ`VERIFIED_INSTALLED`と記録する。

許可される状態遷移:

```text
PENDING_STAGED
  -> PUBLISHING
  -> VERIFIED_INSTALLED | FAILED_KNOWN | UNKNOWN | CORRUPT_OR_INCOMPLETE
```

Timeout、crash、partial visibilityでは成功を主張しません。結果不明時に同じ導入を自動
retryしたり、別の導入effectを発行したりしません。

### 導入結果

| 項目 | 証跡 | 判定 |
|---|---|---|
| Package read-back | 未確認 | 未確認 |
| Target manifest一致 | 未確認 | 未確認 |
| Unexpected file 0件 | 未確認 | 未確認 |
| Journal terminal state | 未確認 | 未確認 |
| Install receipt | 未確認 | 未確認 |

## 4. Rollback・復元チェックリスト

Rollbackは導入失敗時の自動処理ではなく、別の明示的なRecovery operationです。

- [ ] Recovery操作の明示的な許可がある — 状態: `未確認`
- [ ] 導入結果を`FAILED_KNOWN`、`UNKNOWN`、`CORRUPT_OR_INCOMPLETE`から区別した — 状態: `未確認`
- [ ] 正しいBackup operation IDとmanifestを選択した — 状態: `未確認`
- [ ] OBS processが0件である — 状態: `未確認`
- [ ] 現target manifestを復元前Evidenceとして固定した — 状態: `未確認`
- [ ] 旧fileを復元し、導入前に存在しなかったfileだけを対象どおり除外した — 状態: `未確認`
- [ ] 復元後の全fileをread-backした — 状態: `未確認`
- [ ] 旧manifestと完全一致した場合だけ`ROLLBACK_VERIFIED`にした — 状態: `未確認`
- [ ] 以前の`UNKNOWN`履歴を成功へ書き換えていない — 状態: `未確認`

復元後も、OBS load確認は別に実施します。復元成功だけでPlugin利用可能とは判断しません。

## 5. OBS読込確認チェックリスト

この章はOBS起動・Plugin loadの別Authorization取得後にだけ実行します。

- [ ] 対象OBS buildと実行architectureがmanifestに一致する — 状態: `未確認`
- [ ] 読み込まれたModule IDとVersionが成果物に一致する — 状態: `未確認`
- [ ] OBS logにload error、ABI mismatch、missing dependencyがない — 状態: `未確認`
- [ ] 想定外のPlugin、DLL search path、side-loadがない — 状態: `未確認`
- [ ] Scene、Profile、Source、Filter、Mixer設定に変更がない — 状態: `未確認`
- [ ] Pluginの状態表示が確認できる — 状態: `未確認`
- [ ] 未選択Sourceで録音開始できない — 状態: `未確認`
- [ ] OBS終了・再起動後もVersionとModule identityが一致する — 状態: `未確認`

Display nameだけをSource identityとして使いません。正式確認では、privateなProfile、
Scene Collection、Source UUID、graph digest、endpoint bindingを使用し、公開Evidenceでは
redactします。

## 6. 録音操作の受入チェックリスト

Owner voiceを含む実録音には、別のConsent、Owner GO、保存先・暗号化・retention Gateが
必要です。このdraftは録音を許可しません。

### 6.1 共通Preflight

- [ ] exact Session revisionとcommand hashを固定した — 状態: `未確認`
- [ ] VoiceProfile/Consentのcurrent評価が`PASS`である — 状態: `未確認`
- [ ] 選択Sourceのprivate identityとcurrent graphが一致する — 状態: `未確認`
- [ ] capture adapter revision/hashがload済みModuleと一致する — 状態: `未確認`
- [ ] target formatとmeasured formatが一致する — 状態: `未確認`
- [ ] encrypted staging、disk floor、recovery、retentionが`PASS`である — 状態: `未確認`
- [ ] recording-specific Human Gateが有効期限内である — 状態: `未確認`

### 6.2 START

- [ ] P-VSが発行したSession/Segment/Attempt identityを使用する — 状態: `未確認`
- [ ] Pluginがidentityを生成・置換しない — 状態: `未確認`
- [ ] `COMMAND_ACCEPTED`と`CAPTURE_STARTED`を別eventとして確認する — 状態: `未確認`
- [ ] ACKだけで録音成功を表示しない — 状態: `未確認`
- [ ] 可視状態が録音中へ遷移する — 状態: `未確認`

### 6.3 PAUSE

- [ ] `PAUSE_ACKNOWLEDGED`を確認する — 状態: `未確認`
- [ ] bounded drain、最後のsource frame/sample rangeを固定する — 状態: `未確認`
- [ ] 未完文・partial captureをEvidenceへ記録する — 状態: `未確認`
- [ ] PAUSE中にframeが暗黙追加されない — 状態: `未確認`
- [ ] PAUSEをSTOP成功として扱わない — 状態: `未確認`

### 6.4 RESUME

- [ ] 同じSegment、cue、sentence、text bindingを使用する — 状態: `未確認`
- [ ] P-VS発行の新Attempt identityを使用する — 状態: `未確認`
- [ ] `attempt_number = old + 1`とexact parent hashを確認する — 状態: `未確認`
- [ ] 未完文は文頭anchorから再録する — 状態: `未確認`
- [ ] Pluginが新SegmentやAttemptを勝手に作らない — 状態: `未確認`
- [ ] `RESUME_STARTED`を確認する — 状態: `未確認`

### 6.5 STOP

- [ ] `STOP_ACKNOWLEDGED`を確認する — 状態: `未確認`
- [ ] callback detach、in-flight zero、worker drainを確認する — 状態: `未確認`
- [ ] source frameとcanonical sample mappingを確定する — 状態: `未確認`
- [ ] staging receiptとretained Evidence ledgerを確認する — 状態: `未確認`
- [ ] 完全なCandidateと不完全・UNKNOWNを分離する — 状態: `未確認`
- [ ] Dataset採用や学習を自動開始しない — 状態: `未確認`

### 6.6 CANCEL

- [ ] `CANCEL_ACKNOWLEDGED`を確認する — 状態: `未確認`
- [ ] 外部work、staging、retained bytesの有無を確認する — 状態: `未確認`
- [ ] retained Evidenceがある場合にplain `CANCELLED`へ隠さない — 状態: `未確認`
- [ ] ACKや外部状態が不明なら`UNKNOWN`にする — 状態: `未確認`
- [ ] delete、Dataset review、adoptionを自動実行しない — 状態: `未確認`

## 7. 保存・Staging受入チェックリスト

- [ ] Callback内ではbounded copyと最小metadata以外を行わない — 状態: `未確認`
- [ ] Disk I/O、JSON、network、analysis、RX、encryptionはcallback外で行う — 状態: `未確認`
- [ ] Native rangeとcanonical `48 kHz / 24-bit integer PCM / mono` rangeの対応を保持する — 状態: `未確認`
- [ ] Conversion profile、delay、tail、remainderをEvidenceへ記録する — 状態: `未確認`
- [ ] Byte checksum、sample count、range hashをprivate Evidenceへ保存する — 状態: `未確認`
- [ ] Drop、overrun、discontinuityのknown flagとcountを保持する — 状態: `未確認`
- [ ] 不明なcountを`0`へ変換しない — 状態: `未確認`
- [ ] Stagingは暗号化され、recovery/retention policyへbindingされる — 状態: `未確認`
- [ ] Stagingを同一objectのstate変更でAssetへ昇格しない — 状態: `未確認`
- [ ] Asset化、Dataset採用、Training開始は別receipt/Human Gateである — 状態: `未確認`

## 8. 異常終了・Recovery受入チェックリスト

| Scenario | 必須結果 | 状態 |
|---|---|---|
| Source切断 | `SOURCE_LOST`、capture停止、UNKNOWN範囲の隔離 | 未確認 |
| Profile/Scene/graph変更 | `SOURCE_SCOPE_CHANGED`、自動rebind禁止 | 未確認 |
| Format変更 | `FORMAT_MISMATCH`、成功禁止 | 未確認 |
| Ring full/overrun | 既知drop facts、discontinuity、成功禁止 | 未確認 |
| Oversized callback | callback unit全体をdrop、partial publish禁止 | 未確認 |
| Reentrant callback | copy 0、`CAPTURE_UNKNOWN` | 未確認 |
| Disk不足 | write停止、partial staging隔離、状態UNKNOWN/FAILED | 未確認 |
| IPC切断 | command/event reconciliation、duplicate effect禁止 | 未確認 |
| Worker crash | journal/staging read-back、no auto replay | 未確認 |
| Plugin crash | OBS/process/moduleとreceiptをread-reconcile | 未確認 |
| OBS crash/restart | old Sessionを自動継続せず、fresh preflight | 未確認 |
| Detach timeout | memory解放・成功claim禁止 | 未確認 |
| Receipt timeout | authoritative read/reconcile、retry禁止 | 未確認 |

Recoveryでは次を守ります。

1. `FAILED_KNOWN`と`UNKNOWN`を区別する。
2. Processの有無だけで成功・失敗を決めない。
3. 同じoperation/idempotency identityのcanonical receiptを照合する。
4. 外部状態が不明なまま新しいSTARTや保存effectを発行しない。
5. Partial stagingをCandidate、Asset、Datasetへ自動昇格しない。
6. 完全性を確認できない範囲は隔離し、Owner reviewへ送らない。

## 9. Evidence記録テンプレート

実機確認では、公開Evidenceとprivate Evidenceを分離します。

```text
test_case_id:
tested_at:
operator_kind:
authorization_ref:
obs_build:
plugin_package_id:
plugin_version:
package_sha256:
manifest_sha256:
module_id:
operation_id:
expected_result:
actual_result:
result: PASS | FAIL | UNKNOWN | 未確認 | NOT_APPLICABLE
public_evidence_digest:
private_evidence_ref:
notes:
```

公開Evidenceへ次を含めません。

- 音声body、音声に直接結びつくhash
- Script、Transcript、Reference Audio
- Device fingerprint、Source UUID、Profile、Scene Collection、graph detail
- Host absolute path、Credential、key reference
- Consent subject、private scope、private Evidence ID

## 10. 誤完了表示scan

公開前に、文書、UI、Evidenceを次の観点で確認します。
この節の`PASS`はdraft本文の静的scan結果だけを示し、Pluginの実装・導入・load・録音の
成功を示しません。

- [ ] `P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`は最終Judge前に`NOT_ESTABLISHED` — 状態: `PASS`
- [ ] 未確認のPackage/Version/SHAを具体値で表示していない — 状態: `PASS`
- [ ] Design完成をPlugin実装・導入・利用可能と表示していない — 状態: `PASS`
- [ ] Package展開成功をOBS load成功と表示していない — 状態: `PASS`
- [ ] OBS load成功を録音成功・Production Readyと表示していない — 状態: `PASS`
- [ ] Command ACKをcapture/save成功と表示していない — 状態: `PASS`
- [ ] Synthetic test成功を実機互換・Production Readyと表示していない — 状態: `PASS`
- [ ] Backup作成をRollback成功と表示していない — 状態: `PASS`
- [ ] `UNKNOWN`、未計測count、未確認を`0`や`PASS`に変換していない — 状態: `PASS`
- [ ] Dataset採用・Training開始・公開を自動化済みと表示していない — 状態: `PASS`

次の表現は、exact Evidenceと最終Judgeが揃うまで使用しません。

```text
導入済み
動作確認済み
利用可能
録音できます
復旧確認済み
Production Ready
P_OBS_PLUGIN_DEVELOPMENT_COMPLETEの値をPASSとする表現
```

## 11. 最終受入Gate

Plugin開発完了を主張するには、少なくとも次のGateがすべて必要です。

1. Exact source、toolchain、build、package、manifest、SHA-256のEvidence
2. License・Notice・配布境界の確認
3. Backup、containment、collision、journaled install、read-backのPASS
4. Separate rollback operationとread-backのPASS
5. Exact OBS buildでのModule/ABI/load PASS
6. START/PAUSE/RESUME/STOP/CANCELのcommand/event/Evidence PASS
7. Save、drop/overrun/discontinuity、crash/restart/recoveryのPASS
8. Public/private redactionとtamper確認のPASS
9. Production Recording、Consent、storage、Owner GOが別Gateのままであること
10. Criticで未解決Critical/Highが0、最終Judgeが明示的にPASS

いずれかが`未確認`、`UNKNOWN`、`FAIL`なら、
`P_OBS_PLUGIN_DEVELOPMENT_COMPLETE`は`NOT_ESTABLISHED`のままです。

## 12. 成果物確定後に更新する欄

Lead担当から実成果物を受領した後、次をEvidence付きで更新します。

| Field | 確定値 | Evidence |
|---|---|---|
| Package ID | 未確認 | 未確認 |
| Version | 未確認 | 未確認 |
| SHA-256 | 未確認 | 未確認 |
| Manifest SHA-256 | 未確認 | 未確認 |
| Source revision | 未確認 | 未確認 |
| Build profile | 未確認 | 未確認 |
| Module ID | 未確認 | 未確認 |
| Supported OBS build | 未確認 | 未確認 |
| Install receipt | 未確認 | 未確認 |
| Load receipt | 未確認 | 未確認 |

値はLead担当のcanonical成果物とreceiptから転記し、チャット、filename、family名、手入力だけを
根拠に確定しません。

## 困ったとき

- PackageやSHAが不明: 導入しない
- 既存fileとのcollisionを検出: 上書きせず停止する
- OBSが起動中: 導入・復元を開始しない
- 導入結果が不明: retryや自動rollbackを行わずread/reconcileする
- Source、Profile、Scene、deviceが変わった: 録音を止めfresh preflightを行う
- 音声欠損、drop、overrunが不明: `0`にせず`UNKNOWN`として隔離する
- Stagingが残った: 自動削除・Asset化・Dataset採用を行わない
- Public Evidenceにprivate情報が疑われる: 公開せずSecurity/Privacy reviewへ送る

このdraftの存在は、Pluginの実装、導入、OBS起動、録音、ReleaseまたはDeployを許可する
ものではありません。
