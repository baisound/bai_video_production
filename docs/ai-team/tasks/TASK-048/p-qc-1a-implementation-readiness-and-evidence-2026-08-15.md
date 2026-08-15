# TASK-048 / P-QC-1A Implementation Readiness and Evidence — 2026-08-15

## Authority and immutable source of truth

- Authorization: `BVP-AUTH-20260815-TASK048-PQC1A-IMPL-I1`
- Authority: `IMPLEMENT_AND_VALIDATE_WITHIN_EXACT_ACTIVE_LOCK_ONLY`
- Exact implementation base:
  `a7c9f0c7276249dd93b32508fe920007e7074c80`
- Branch: `codex/task-048-p-qc-1a-voice-quality-calibration-contract`
- Registry: revision `9`
- P-QC Lock: `BVP-LOCK-TASK048-PQC1A = ACTIVE`
- P-OBS contract Lock: `HOSTED_CLOSED_RELEASED`
- Pre-start open PR / target branch / exact path overlap: `0 / 0 / 0`

The earlier Lock base is historical path-reservation Evidence, not the
implementation start base.  Fresh P-OBS H2 merge/read-back and post-merge CI
and Security were all verified before this unit started.

## Exact allowed files

1. `docs/ai-team/tasks/TASK-048/p-qc-1a-implementation-readiness-and-evidence-2026-08-15.md`
2. `schemas/voice-quality-calibration.schema.json`
3. `src/ai_video_production/schema_resources/voice-quality-calibration.schema.json`
4. `src/ai_video_production/voice_quality_calibration.py`
5. `tests/test_task048_voice_quality_calibration_contract.py`

No fixture, `__init__.py`, Registry, CHANGELOG, workflow, shared integration,
native helper or second module/schema was added.

## Dependency read-back

Hosted canonical and exact blobs at implementation start:

- P-VS-1A public/mirror schema:
  `4901237b59243ac195da6f6b92ff878d68288d42`
- P-VS-1A revision module:
  `c30e1bba7d8418ef5bfc2661fe1f6d855ef53ddd`
- P-VS-1A store:
  `9bfccfef566ef64fd0acdde3eaf715a37648c241`
- P-VS-3A public/mirror schema:
  `0515957d580571a09c12b80d9d93af32df94014a`
- P-VS-3A module:
  `6951f404d49dee4779a8ac540adb07c432c4831d`
- P-VS-3A focused test:
  `ecbd74de21064e05201dec42b1efa9b809430089`
- TASK-003 public/mirror AssetRecord schema:
  `d6016ed2eec9e00c3bd828f7466fa3ea55c78f61`
- TASK-003 Asset module:
  `7fd5340923c4844bed6eeef8c8e92ef409ef49ff`
- TASK-043 public/mirror durable job schema:
  `0443588a0087981ddb59217cd9467ee444587c66`
- TASK-043 module:
  `028896468851a5267c95443b94b186910580f32b`
- TASK-048 task definition:
  `71371c5cb532c76715248c2d732693438e11cfe8`

P-VS-1A, P-VS-3A, TASK-003 AssetRecord and TASK-043 durable product job are
hosted.  Formal TASK-003 AssetRevision mapping, P-OBS capture/staging effect
receipt, exact endpoint capability, canonical privacy decision and RX effect
owner remain structured unresolved dependencies.  `PROJECT_MAINTENANCE` is not
used as a P-QC Job type.

## Implemented pure contract

The public schema and packaged mirror expose exactly the 23 Lock-owned
canonical serialized types:

1. `CaptureChainRevision`
2. `CalibrationProfileRevision`
3. `QualityPolicyRevision`
4. `AnalyzerProfileRevision`
5. `CalibrationSessionRevision`
6. `MeasurementInputRangeBinding`
7. `StagingToTask003AssetPromotionBinding`
8. `MetricInputSetBinding`
9. `MetricFact`
10. `MeasurementReceipt`
11. `QualityEvaluationReceipt`
12. `CaptureEvidenceBinding`
13. `RXDerivedQualityBinding`
14. `PrivacyPolicyBinding`
15. `HumanInputBinding`
16. `GainRecommendationRevision`
17. `AdditionalRecordingRecommendationRevision`
18. `DriftComparisonReceipt`
19. `DurationCoverageIndicator`
20. `ApprovedStyleLanguageEmotionCoverageIndicator`
21. `RawAcousticQualityCoverageIndicator`
22. `DatasetReadinessIndicator`
23. `ModelEvaluationReadinessIndicator`

The module implements deterministic canonical JSON/hash verification,
append-only revision/CAS guards, exact eight-stage chain validation, strict
staging-versus-TASK-003 range binding, Metric input role/compatibility checks,
fact-versus-policy decision separation, half-open integer interval union,
integer-rational coverage, five independent readiness axes, privacy
projection and the exact hosted P-VS-3A `calibration_binding` projection.

## Calibration and signal-integrity invariants

- Canonical format is `48000 Hz / 24-bit integer PCM / mono` metadata.
- The chain order is exact:
  mic PAD/HPF; interface analogue preamp; driver/OS endpoint; OBS source;
  OBS filters; OBS mixer; Plugin/capture tap; non-real-time canonical
  conversion.
- +48V, PAD, HPF and interface preamp states distinguish declared, measured,
  observed, unknown and not-applicable Evidence.  Unknown hardware state does
  not pass raw calibration.
- Endpoint display name never replaces stable private endpoint identity.
- Unknown processing, hidden AGC/filter/limiter or duplicate primary gain does
  not pass raw calibration.
- `RAW_PRE_FILTER`, `OBS_POST_FILTER`, `CANONICAL_CONVERTED_RAW` and
  `RX_DERIVED` remain distinct.
- Single-range facts, ordered SIGNAL/NOISE SNR and paired BEFORE/AFTER facts
  have distinct arity and roles.
- `MetricFact.value_state` preserves `DECLARED`, genuine-zero `MEASURED`,
  `NOT_SUPPORTED`, `INSUFFICIENT_INPUT`, `ERROR` and `UNKNOWN`.  Only
  `MEASURED` carries a numeric value.
- Receipt validity and Quality policy decisions are separate.
- Coverage uses a unique half-open interval union per source, processing class
  and policy scope.  Retry/overlap cannot double-count or exceed 100 percent.
- An unhosted percentage policy yields `percentage=null` and `UNKNOWN`; no
  0/95/100 value is invented.
- Duration, approved style/language/emotion, raw acoustic, Dataset readiness
  and Model-evaluation readiness are separate axes and are never averaged.

## External-effect and privacy boundary

The module has no filesystem store, network, subprocess, CMake, audio reader,
analyzer, OBS, RX, device/hardware, Asset, Job/Queue, Dataset, Training, Model
or production dispatcher surface.  All body/effect authority flags are fixed
false.

Calibration staging is not a permanent Asset and cannot be used for Dataset,
Training or publication.  Promotion is a separate external TASK-003/Owner
effect.  RX output is a separate derived Asset candidate; raw overwrite,
delete and automatic Dataset adoption remain false.  Gain and additional
recording results are proposals only.

When canonical privacy policy binding is absent, public projection suppresses
range, receipt, source, Asset/staging, device, metric, sample-count, duration,
percentage and low-count coverage detail.  No fixed privacy `k` is invented.

P-QC I1 is pure Python and adds no CMake dependency or invocation.  A future
native Evidence procedure must use the exact approved absolute CMake 3.30.5
path; bare `cmake`, PATH ordering and an existing CMake installation remain
out of scope.

## Validation Evidence

- Focused schema/module/negative suite:
  `14 passed`
- JSON Schema Draft 2020-12 meta-validation: `PASS`
- Public/package schema mirror byte parity: `PASS`
- WSL2 compileall: `PASS`
- WSL2 existing environment full regression:
  `1229 passed in 71.07s`
- Windows repository Python runtime: `NOT_AVAILABLE`
- Windows workspace-runtime discovery: `NO_RESULT`; it was stopped without
  install/download/environment mutation
- Windows regression: `NOT_RUN_NO_EXISTING_RUNTIME`

Focused test groups map the Blueprint acceptance inventory:

- `PQC-SCH/SEC`: 23 roots, alias/additional-field rejection, mirror/body flags
- `PQC-MET`: genuine zero and all non-measured states
- `PQC-CHN`: exact chain, endpoint, hidden processing, duplicate gain,
  +48V/PAD/HPF/preamp and auto-change denial
- `PQC-INP`: staging/Asset discriminator, expiry, use denial and promotion
- `PQC-SET`: single, SNR and before/after role/compatibility
- `PQC-COV/AXS`: interval union, retry/conflict, rational coverage and five axes
- `PQC-REC/RX/PRI`: proposal-only, immutable raw lineage and suppression
- `PQC-CAS/PVS/SRF`: append/CAS, exact P-VS-3A mapping and no-effect surface

## Critic pass 1 — domain, naming and state

Initial findings and corrections:

1. Hardware +48V/PAD/HPF/preamp state was initially represented only by a
   settings digest.  Exact declared/measured/observed/unknown state fields were
   added, and raw PASS now rejects relevant UNKNOWN states.
2. Structured unresolved bindings initially relied more heavily on Python
   validators.  Schema state-dependent nullability was synchronized for
   staging, TASK-003 Asset, promotion, capture Evidence, RX, privacy and Human
   input bindings.
3. SNR and paired metrics could be shape-valid without schema role order.
   Schema arity/prefix role rules and Python cross-range checks are both fixed.
4. Low-count projection initially retained current receipt/index digests.
   These details are now suppressed while privacy policy is unresolved.

Residual Critical / High / Medium: `0 / 0 / 0`.

## Critic pass 2 — authority, security and regression

- Canonical type rename/omission: `0`
- Schema/module mirror drift: `0`
- Hosted P-VS-3A projection field drift: `0`
- Raw/derived or processing/policy coverage collapse: `0`
- Unknown-to-zero/percentage/PASS conversion: `0`
- Audio/private body or credential/path exposure: `0`
- External effect or hardware setting authority escalation: `0`
- CMake/native/install/download surface: `0`
- Allowed-file expansion: `0`
- WSL regression failure: `0`

Residual Critical / High / Medium: `0 / 0 / 0`.

## Builder Judge

- Domain and canonical 23 types: `PASS`
- Exact five-file implementation scope: `PASS`
- Pure metadata implementation: `PASS`
- Focused/schema/mirror/compile/full WSL validation: `PASS`
- Windows validation: `NOT_RUN_NO_EXISTING_RUNTIME`, not represented as PASS
- Real calibration/recording/OBS/RX/device/Asset/Dataset/Training/Model or
  production execution: `BLOCKED / NOT_AUTHORIZED`
- Ready for atomic commit, push and Draft PR: `PASS_CONDITIONAL_ON_FINAL_DIFF`
- Ready/Merge: `NOT_AUTHORIZED`
