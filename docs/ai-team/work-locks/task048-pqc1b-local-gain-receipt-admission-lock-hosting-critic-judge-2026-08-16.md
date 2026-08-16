# TASK-048 / P-QC-1B Local Gain Receipt Admission Lock Hosting Evidence

- Date: 2026-08-16
- Fresh base: `main@dafcea762ca7ce4a6437033bf407695cccc9860d`
- Registry: revision `21 -> 22`
- Lock: `BVP-LOCK-TASK048-PQC1B-LOCAL-GAIN-ADMISSION`
- Owner lane: TASK-048 priority after canonical TASK-047 completion

## 1. Why this unit is next

TASK-047 dev.10は、OBSを起動したまま5秒のGAINチェックを実行し、Peak、RMS、clip count、sample-value countをbody-free receiptへ保存する。Owner技術Acceptanceではaudio body保存なし、hardware setting変更なし、clipping 0を確認した。

一方、そのlocal receiptはP-QC-1Aのcanonical `MeasurementReceipt`ではなく、次をまだ持たない。

- exact sample-rate / channel / sample-format mapping
- RAW / OBS post-filter / canonical converted processing class
- eight-stage `CaptureChainRevision`
- approved `QualityPolicyRevision`
- canonical `AnalyzerProfileRevision`
- staging/Asset range identityとcanonical mapping receipt

実測`480000 sample values`を、根拠なく`48000 Hz / mono / 10 seconds`または`5 seconds stereo`のどちらかへ決めてはならない。現local receiptだけで「適正GAIN」やP-QC PASSを発行するのはauthority driftである。

P-QC-1Bはこの境界を曖昧にせず、local receiptの測定factをstrictに検証し、P-QCへ進めるか、どのbindingが不足しているかをbody-free reportとして分類する最小adapterである。

## 2. Exact implementation reservation

Implementation branch:

`codex/task-048-pqc1b-local-gain-receipt-admission`

Allowed files exact 5:

1. `docs/ai-team/tasks/TASK-048/p-qc-1b-local-gain-receipt-admission-evidence-2026-08-16.md`
2. `schemas/voice-quality-gain-admission.schema.json`
3. `src/ai_video_production/schema_resources/voice-quality-gain-admission.schema.json`
4. `src/ai_video_production/voice_quality_gain_admission.py`
5. `tests/test_task048_voice_quality_gain_admission.py`

No fixture、`__init__.py`、TASK-047 source、P-QC-1A existing file、Registry、CHANGELOGまたはworkflowをimplementation branchへ含めない。

## 3. Adapter contract

Input is an in-memory mapping matching exact schema `bvp.task047.local-gain-check-receipt.v1`. The adapter itself does not open a file, read audio, run an analyzer or access OBS.

Required source facts:

- terminal reason and timestamps
- `sample_peak_dbfs` / `rms_dbfs` with explicit nullable semantics
- `clip_threshold_abs` and integer `clip_sample_count`
- integer `non_finite_sample_count`
- integer `measured_sample_values`
- packet / gap / HMAC / reconnect counts
- `audio_body_persisted=false`
- `hardware_setting_changed=false`
- `session_key_persisted=false`

The canonical JSON SHA-256 of the source receipt is included in the report. Private path, filename, device identity, credential and audio hash are neither accepted nor projected.

## 4. Fail-closed classification

- unknown/extra/missing field, invalid type, non-canonical numeric value: `REJECTED_INVALID_RECEIPT`
- non-finite sample count greater than zero: `INVALID_MEASUREMENT`
- clip count greater than zero: `RERECORD_RECOMMENDED_CLIPPING`
- sample format/channel/range/capture-chain/policy/analyzer binding absent: `MEASURED_FACTS_POLICY_OR_CHAIN_UNBOUND`
- binding digest mismatch: `MISMATCH`
- all external P-QC bindings exact: `READY_FOR_CANONICAL_PQC_EVALUATION`

The adapter never returns P-QC `PASS`; it only admits exact facts to a later canonical P-QC evaluation. It never issues `MeasurementReceipt` or `QualityEvaluationReceipt` and does not turn measured zero into unknown or unknown into zero.

## 5. Effect boundary

The implementation has no:

- filesystem API
- audio reader/writer or DSP/analyzer
- subprocess/network/CMake/native API
- OBS/RX/device/hardware API
- Asset/Dataset/Job/Training/Model/Production API
- canonical receipt issuer
- automatic gain change or Owner policy approval

Gain adjustment remains a proposal. P-QC-1B cannot modify preamp, OS level, OBS mixer/filter, +48V, PAD or HPF.

## 6. Release metadata policy

Product source changes must not reach a stale changelog-only CI blocker. The implementation Lock reserves an automatic CHANGELOG Integration sub-Gate that becomes effective only after implementation checks and only when the shared CHANGELOG lane is fresh and overlap-free. This reservation is not an ACTIVE Integration Lock and does not permit concurrent `CHANGELOG.md` writes.

## 7. Validation plan

- schema parse and public/mirror byte parity
- canonical JSON/source receipt hash stability
- strict known-field/type/numeric validation
- measured zero preserved
- missing/extra field rejection
- NaN/Infinity rejection
- clip/non-finite hard failure
- unbound format/channel/chain/policy remains UNKNOWN
- digest mismatch remains MISMATCH
- forged P-QC PASS rejection
- private-field and public-projection suppression
- static AST surface scan for filesystem/audio/subprocess/network/OBS/hardware effects
- focused Windows tests
- full Windows and WSL regression using existing environments only

## 8. Critic pass 1

Initial High: a converter could accidentally present the existing local receipt as a canonical P-QC `MeasurementReceipt`. Correction: the unit is explicitly an admission/classification adapter and cannot issue either canonical measurement or policy-decision receipt.

Initial High: `480000 sample values` could be silently interpreted as canonical mono duration. Correction: sample-rate/channel/sample-format/range mapping are mandatory external bindings; absent values stay `UNKNOWN`.

Initial Medium: clip=0 could be mislabeled quality PASS. Correction: clip=0 only clears the clipping hard failure; policy and chain remain required.

After correction: Critical / High / Medium = `0 / 0 / 0`.

## 9. Critic pass 2

Rechecked:

- exact5 path reservation and P-VS-3B overlap 0
- P-QC-1A and TASK-047 source remain read-only
- no second analyzer/Asset/Job/Consent truth
- no automatic hardware change or recording effect
- no universal peak/RMS threshold invented
- release-metadata gate planned before source mutation

Residual Critical / High / Medium = `0 / 0 / 0`.

## 10. Read-only Judge

- DOMAIN_BOUNDARY: PASS
- EXACT5_IMPLEMENTATION_RESERVATION: PASS
- CURRENT_PQC1A_BASELINE: `14 / 14 PASS`
- REAL_GAIN_POLICY_PASS: NOT_ESTABLISHED
- AUDIO_OR_HARDWARE_EFFECT_AUTHORIZED: NO
- LOCK_HOST_READINESS: PASS
- IMPLEMENTATION_READY_AFTER_MAIN_READ_BACK: PASS_CONDITIONAL
- Critical / High / Medium: `0 / 0 / 0`

The Lock becomes canonical only after an exact2 hosting PR merges to main, Registry revision 22 and the ACTIVE record are read back, and post-merge CI/Security are terminal SUCCESS.
