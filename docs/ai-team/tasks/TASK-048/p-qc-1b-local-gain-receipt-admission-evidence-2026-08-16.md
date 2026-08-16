# TASK-048 / P-QC-1B Local Gain Receipt Admission — Implementation Evidence

- Date: 2026-08-16
- Implementation start base: `main@7bb708dc42b135d9245a13ad4a6fd647f9b39d92`
- Branch: `codex/task-048-pqc1b-local-gain-receipt-admission`
- Active Lock: `BVP-LOCK-TASK048-PQC1B-LOCAL-GAIN-ADMISSION`
- Registry read-back: revision `22`
- Lock-host post-merge CI: `31950670844 = SUCCESS`
- Lock-host post-merge Security: `31950670878 = SUCCESS`

## Outcome

TASK-047 dev.10のlocal GAIN checkが出力するbody-free JSONをstrictに検証し、既存P-QC-1Aへ渡せる状態かを分類するpure metadata adapterを実装した。

このadapterは「クリップがなかった」という事実を「適正GAIN」や品質PASSへ昇格しない。exactなcanonical sample mapping、`MeasurementInputRangeBinding`、8段の`CaptureChainRevision`、`AnalyzerProfileRevision`、`QualityPolicyRevision`がすべて`BOUND_VERIFIED`の場合でも、結果は`READY_FOR_CANONICAL_PQC_EVALUATION`であり、最終品質は`UNKNOWN`のままである。canonical analyzer/policy evaluationは後続の別operationである。

## Exact five files

1. `docs/ai-team/tasks/TASK-048/p-qc-1b-local-gain-receipt-admission-evidence-2026-08-16.md`
2. `schemas/voice-quality-gain-admission.schema.json`
3. `src/ai_video_production/schema_resources/voice-quality-gain-admission.schema.json`
4. `src/ai_video_production/voice_quality_gain_admission.py`
5. `tests/test_task048_voice_quality_gain_admission.py`

`__init__.py`、fixture、既存P-QC-1A files、TASK-047 controller/native files、Registry、CHANGELOG、workflowは変更しない。

## Source contract read-back

Hosted controller `WriteGainReceipt`の実在fieldをsource truthとして再照合した。exact schemaは`bvp.task047.local-gain-check-receipt.v1`であり、次を持つ。

- terminal reason、start/end UTC
- measurement fact state、signal-integrity state、policy-unbound state、proposal-only recommendation
- nullable Peak/RMS dBFS
- clipping threshold/count、non-finite count、measured sample-value count、received byte count
- `audio_body_persisted=false`
- `hardware_setting_changed=false`
- `session_key_persisted=false`

Lock-host Evidenceのpre-implementation記述にあったpacket/gap/HMAC/reconnect countsは、このlocal GAIN receipt schemaには存在しない。実装は架空fieldを追加せず、hosted controllerのexact field setへ正規化した。unknown/extra/missing fieldは拒否する。

## Contract and classification

Canonical serialized rootは`GainReceiptAdmissionReport` 1型。source receiptと以下のstructured bindingはnested `$defs`としてstrict validationする。

- `CanonicalMeasurementBinding`: exact range、mapping receipt、48kHz/24-bit/mono、processing class
- `CanonicalRecordBinding`: CaptureChain / AnalyzerProfile / QualityPolicy exact ref/hash/Evidence
- `GainAdmissionContext`: 上記4 bindingの組

Classification:

- input不足: `INVALID_MEASUREMENT` + fact validity `UNKNOWN`
- non-finite sample: `INVALID_MEASUREMENT` + `FAIL`
- clipping: `RERECORD_RECOMMENDED_CLIPPING`
- canonical binding未提供/UNKNOWN: `MEASURED_FACTS_POLICY_OR_CHAIN_UNBOUND`
- binding mismatch: `MISMATCH`
- 全binding exact: `READY_FOR_CANONICAL_PQC_EVALUATION`

adapterが返せるquality stateは`FAIL / UNKNOWN / RERECORD_RECOMMENDED`のみ。`PASS`はschemaにもenumとして存在しない。

## Genuine zero and UNKNOWN

Hosted controllerはMEASUREDかつlinear peak/RMSが0の場合、dBFS値を`null`で出力する。adapterはこの組を`measured_linear_zero=true`として保持する。一方、`INSUFFICIENT_INPUT`のnullable値は`measured_linear_zero=false`であり、genuine zeroとUNKNOWNを混同しない。

`measured_sample_values`だけからsample rate、channel count、durationを推定しない。Owner Acceptanceで観測した`480000`も、mapping receiptなしに「mono 10秒」または「stereo 5秒」のどちらかへ決めない。

## Effect and privacy boundary

Moduleはin-memory mappingだけを扱い、次を行わない。

- file/path/audio bodyのread/write
- DSP/analyzer、OBS/RX/device/hardware操作
- preamp/OS/OBS gainの自動変更
- canonical P-QC `MeasurementReceipt` / `QualityEvaluationReceipt`発行
- staging/Asset/Dataset/Job/Training/Model/Production effect
- subprocess/network/CMake/native/download/install/build

全reportでcanonical P-QC receipt issuance、audio read、analyzer execution、hardware/OBS setting change、gain authorization、Dataset/Training/Production authorizationは`false`固定。Public projectionからtimestamp、received bytes、canonical refs、range/mapping refs、Evidence digestを抑制する。

## Validation inventory

- unbound measurementはVALID factでもquality UNKNOWN
- all-exact bindingはlater P-QC evaluation readyまで
- clipping/non-finite/input不足のfail-closed分類
- genuine measured zeroとUNKNOWNの分離
- missing/extra field拒否
- NaN/Infinity拒否
- body/hardware/session-key flag偽装拒否
- source policy PASS偽装拒否
- inconsistent clipping/recommendation、Peak/RMS関係拒否
- timestamp逆転、clip threshold drift、anomaly count超過、measured-with-zero-bytes拒否
- `CANONICAL_REF_NOT_PROVIDED`へのref混入拒否
- SHA単体を`BOUND_VERIFIED`にしない
- 48kHz/24-bit/mono mismatch拒否
- MISMATCH precedence
- deterministic source/report hash
- parser tamper、classification tamper、effect flag偽装拒否
- schema validation、unknown property、forged PASS拒否
- public/private suppression
- public schema / packaged mirror byte parity
- AST static no-effect surface

Focused result: `39 / 39 PASS`（初期33件からclassification再計算、hosted controller cross-field negative casesを追加）。

## Critic pass 1

Initial High: serialized report parserが受領済みclassificationを再計算せず、outer hashを再計算した改ざんを受け入れる余地があった。

Correction: parserはsource receiptとstructured contextからclassification/validity/qualityを必ず再計算し、serialized document全体とexact比較する。classificationとouter hashを同時に改ざんするnegative testを追加した。

Initial Medium: Lock-host Evidenceにhosted sourceに存在しないtransport counterが列挙されていた。

Correction: implementationと本Evidenceはhosted `WriteGainReceipt` exact 18 fieldsへ固定し、架空fieldを拒否する。

Residual Critical / High / Medium: `0 / 0 / 0`。

## Critic pass 2

再監査:

- P-QC PASS/receipt issuer authorityの重複なし
- 48kHz/mono/durationの推定なし
- clipping=0をpolicy PASSへ昇格しない
- structured unprovided/bound/mismatch/unknown state rules維持
- source controllerおよび既存P-QC-1Aはread-only
- exact5以外のproduct/shared file変更なし
- filesystem/audio/process/network/native effect surfaceなし
- public projectionにprivate path/device/session key/range refなし
- timestamp、constant threshold、sample/byte counter cross-field整合

Residual Critical / High / Medium: `0 / 0 / 0`。

## Judge

- DOMAIN_CONTRACT: PASS
- HOSTED_SOURCE_FIELD_PARITY: PASS_WITH_PREIMPLEMENTATION_EVIDENCE_CORRECTION
- BODY_FREE_NO_EFFECT_SURFACE: PASS
- SCHEMA_MIRROR_PARITY: PASS
- FOCUSED_TESTS: PASS
- WINDOWS_FULL_REGRESSION: `1357 PASS / 1 SKIP`（隔離tempで`1356 PASS / 1 SKIP / 1 DESELECT`後、sandboxが拒否した既存installer acceptance 1件をOwner standing install authority下で別実行しPASS）
- WSL_FULL_REGRESSION: `1357 PASS / 1 SKIP`
- REAL_GAIN_POLICY_PASS: NOT_ESTABLISHED
- CANONICAL_PQC_RECEIPT_ISSUANCE: NOT_AUTHORIZED / NOT_IMPLEMENTED
- REAL_CALIBRATION_OR_HARDWARE_EFFECT: NOT_AUTHORIZED / NOT_IMPLEMENTED
- Critical / High / Medium: `0 / 0 / 0`

Product sourceをmainへ統合する前に、focused/full regression、hosted checks、shared CHANGELOG serialization、post-merge CI/Security、append-only Lock closureを別Gateで完了する。
