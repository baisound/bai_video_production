# TASK-046 / P-VS-3A 実装・検証・Critic・Judge Evidence

- Date: `2026-08-15`
- Authorization: `BVP-AUTH-20260815-TASK046-PVS3A-IMPL-I1`
- Limited rebase authorization: `BVP-AUTH-20260815-TASK046-PVS3A-IMPL-I1-REBASE-9013249`
- Authority: `IMPLEMENT_AND_VALIDATE_WITHIN_EXACT_ACTIVE_LOCK_ONLY`
- Fresh base: `origin/main@24d43daa201808fa2da11c0f6d8e61bbc1ffb45c`
- Pre-push target after governance-only drift: `origin/main@901324902242724a9f441a26339392b62b07e3a4`
- Branch: `codex/task-046-p-vs-3a-recording-session-contract`
- Lock: `BVP-LOCK-TASK046-PVS3A / ACTIVE`
- Implementation state at intake: `NOT_STARTED`
- Production execution: `NOT_AUTHORIZED / BLOCKED`

## 1. Fresh-main / Governance Audit

実装開始前に、fresh `origin/main` と merged-main Registryを再読した。

- Registry revision: `5`
- `BVP-LOCK-TASK046-PVS3A.status`: `ACTIVE`
- Registry Allowed Filesと本Unitの5 files: exact一致
- open PR: `0`
- target branch remote collision: `0`
- proposed 5 pathsとのopen PR overlap: `0`
- P-VS-1A module blob: `c30e1bba7d8418ef5bfc2661fe1f6d855ef53ddd`
- P-VS-1A public/mirror schema blob: `4901237b59243ac195da6f6b92ff878d68288d42 / 4901237b59243ac195da6f6b92ff878d68288d42`
- user WIP、既存checkout、Registry、CHANGELOG、`.github/**`: 非接触

実装完了後のprecommit auditでPR #100によるmain進行を検出した。incomingはRegistryとP-OBS-1A Lock-host Evidenceのexact 2 governance files、実装Allowed Files overlapは0だった。自動rebaseせず設計担当へ報告し、上記child authorizationによりatomic commit後のexact target mainへの限定rebaseが認可された。

## 2. Exact Changed Files

1. `docs/ai-team/tasks/TASK-046/p-vs-3a-implementation-readiness-and-evidence-2026-08-15.md`
2. `schemas/voice-recording-session.schema.json`
3. `src/ai_video_production/schema_resources/voice-recording-session.schema.json`
4. `src/ai_video_production/voice_recording_session.py`
5. `tests/test_task046_voice_recording_session_contract.py`

Fixture、`__init__.py`、shared integration file、audio body、filesystem store、adapter、Job/Queueは追加していない。

## 3. Canonical Domain Surface

Schema root `oneOf` とPython public record typeは、承認済みの次の5 typesへ固定した。

1. `VoiceRecordingSessionRevision`
2. `VoiceSegmentAttemptRevision`
3. `TeleprompterCheckpointRevision`
4. `DatasetCandidateRevision`
5. `DatasetCandidateReviewDecision`

`RecordingSegmentRevision`、`SemanticSessionCheckpoint`等のalias/rename rootは受け付けない。全recordはcanonical JSONから決定論的SHA-256を計算し、parse時にunknown field、missing field、hash tamperを拒否する。

## 4. Binding / Authority Invariants

### P-VS-1A exact binding

`VoiceProfileRevisionBinding`は現行P-VS-1Aの名前を変えず、次を保持する。

- `voice_profile_id`
- `canonical_narration_profile_sha256`
- `revision`
- `parent_revision_sha256`
- `voice_profile_revision_sha256`
- nested `ConsentReference` exact fields

`consent_evidence_id`、`consent_revision_id`等の架空aliasはない。

### Structured unresolved upstream

TASK-003/020/043/047/048の未提供面は`CANONICAL_REF_NOT_PROVIDED`で全canonical fieldをnullにし、receipt/APIを捏造しない。

- TASK-003: `UNBOUND_PENDING_TASK003 | BOUND`
- TASK-020: Resource Admission binding
- TASK-043: Capture Durable Job binding。`PROJECT_MAINTENANCE`流用拒否
- TASK-047/P-OBS-1: Capture Adapter / Capture Evidence binding
- TASK-048/P-QC-1A: Calibration binding

Synthetic contract testは未host upstreamをunresolvedのまま表現できるが、Production admissionへ昇格しない。

### Capture mode / readiness

- `capture_mode`:
  - `SYNTHETIC_CONTRACT_TEST`
  - `OWNER_APPROVED_NON_DATASET_TECHNICAL_PROBE`
  - `PRODUCTION_RECORDING`
- `readiness_evaluation_state`:
  - `NOT_EVALUATED | TEST_READY | TECHNICAL_PROBE_READY | PRODUCTION_READY | BLOCKED | UNKNOWN`

`production_admission=true`はProduction mode/readyと、P-OBS、TASK-020、TASK-048、TASK-043、Consent、selected source、encryption/recovery、disk floor、Owner GOのexact PASSがそろう場合だけ表現できる。現在の未host bindingsではfail closedする。

## 5. State / CAS / Resume

- 全record: revision `>=1`、first parent null、successorはexact parent hash
- `validate_append_only_revision`: stale expected parent、identity drift、revision gapを拒否
- Session/Attempt/Candidate/Checkpoint: allow-list state transition
- `UNKNOWN`: 自動replay/outgoing transitionなし
- capture mode変更: new revision + full preflight、prior readiness/production admission継承禁止
- `CANCELLED`: exact ACK + external/staging/candidate/retained workなし
- `CANCELLED_WITH_RETAINED_EVIDENCE`: retained ledger + retention + encryption/recoveryを必須化
- complete Candidateをcancel terminalへ隠す経路なし

`RESUME`はsame segment/cue/sentence/text/start anchor、new attempt ID、`attempt_number+1`、exact parent attempt hash、prior `INCOMPLETE`、new `PLANNED`を要求する。Adapter生成identityや文中anchorを拒否する。

## 6. Execution Authorization Boundary

raw `execution_authorized=true`をauthority入力として受け付けない。`ExecutionAuthorizationBinding`は次へexact bindする。

- authorization ID/revision/hash/Evidence
- authority kind
- project/session/session revision
- capture mode/readiness digest
- selected source
- current Consent evaluation
- approved text
- `START | RESUME` scope
- issued/expiry/one-shot/replay policy

Binding hash tamper、expired/not-yet-valid、wrong session/mode/source/text/Consent/scope、one-shot replayを拒否する。`CaptureCommandAdmissionReport`はmetadata admissibilityのみを返し、常に以下をfalseに保つ。

- `dispatch_authorized`
- `dispatch_started`
- `runtime_probe_started`

OBS/process/runtime probeを呼ぶAPIは存在しない。

## 7. Candidate / Review / Adoption Separation

- CaptureされたCandidateとOwner ReviewDecisionは別record
- `APPROVED_FOR_ADOPTION`はexact Owner Review/Asset/Consent/quality bindingを要求
- proposal labelをapproved labelとして自動採用しない
- `REJECTED` / `RERECORD`もexact Owner ReviewDecisionを要求
- `ADOPTED_TO_DATASET`はexternal `DatasetAdoptionReceiptBinding=BOUND_VERIFIED`がなければ拒否
- ReviewDecisionは`training_start_authorized=false`固定
- Owner approvalはDataset mutation successやTraining startを意味しない

本moduleはDataset receiptを発行せず、Dataset/Asset/storeを変更しない。

## 8. Privacy / Body-free Projection

全root recordにbody/effect flagsを持ち、audio/script/transcript/credential/absolute path/device fingerprint public/Dataset mutation/Training/Capture dispatchをfalse固定した。

Public projectionから次を除外する。

- Consent subject/scope/usage/Evidence
- private source ref/revision digest
- approved text ref/digestとsource text digest
- Asset private ref/checksum/mapping
- human review Evidence
- label proposal/approved label detail

Public projectionはredacted bodyとprojection digestのみを返す。raw audio、script/transcript body、device fingerprint、host path、credentialを入力・保存するfield/APIはない。

## 9. Validation Evidence

### Focused

- Command: existing WSL venv Python 3.12 / `pytest -q tests/test_task046_voice_recording_session_contract.py`
- Result: `25 passed`

Coverage:

- schema validity / byte-exact mirror
- canonical 5 types / root alias rejection
- deterministic hash / tamper / round-trip
- exact P-VS-1A names / alias rejection
- synthetic vs technical vs Production readiness
- stale CAS / forbidden transitions / UNKNOWN no replay
- retained Evidence cancellation guards
- exact resume attempt lineage
- structured authorization forgery/expiry/scope/replay/tamper
- Candidate/Review/Adoption/Training separation
- revoked Consent / unresolved quality
- public redaction
- PROJECT_MAINTENANCE流用拒否

### Windows available checks

PATH上にPython/pytestはなく、workspace同梱Pythonにもpytestは未導入だった。Owner ruleに従いdownload/install/PATH変更は行っていない。

- bundled Python `compileall src tests`: `PASS`
- schema JSON parse: `PASS`
- public/mirror byte hash: `016EE5A4B3E0310A1EACC59CF39F5910D3DECDC1C1059DB3854ED7940D794B80 / MATCH`
- Windows full pytest: `NOT_RUN_NO_EXISTING_PYTEST_RUNTIME`

Draft PR hosted CIのWindows 3.11/3.12/3.13をmerge前の必須Gateとする。これはlocal Windows PASSの捏造ではない。

### WSL2 full regression

- Existing venv: `/home/baisound/bvp-phaseg-w2-venv`
- No install/download/update performed
- Command: `python -m pytest -q`
- Final result after Critic corrections: `1215 passed in 73.87s`

## 10. Critic Self-pass 1

Initial findings:

1. **High**: approved Candidateからexact ReviewDecisionへのbindingが不足。
2. **High**: reserved `ADOPTED_TO_DATASET`をexternal adoption receiptなしで表現できる余地。
3. **Medium**: Session以外のrecordに共通CAS validatorとtyped transition validatorが不足。

Corrections:

- `review_decision_binding`を追加し、approval/reject/rerecordをexact decisionへbind
- Session/CandidateのADOPTED stateにverified external receiptを必須化
- generic append-only CAS、Attempt/Candidate/Checkpoint transition validatorsを追加
- focused/full regression再実行

Resolved: `Critical/High/Medium = 0/0/0`

## 11. Critic Self-pass 2

Reviewed:

- exact 5 paths / shared file drift
- canonical type rename/omission
- P-VS-1A field aliases
- authority boolean forgery / authorization hash tamper
- UNKNOWN auto replay
- complete Candidate cancellation concealment
- Owner reviewとDataset effect混同
- unbound Asset/quality/Consent adoption
- public biometric/text/Asset/label leakage
- filesystem/network/process/OBS/audio/Job/store mutation surface
- schema mirror parity and canonical JSON hash

Findings:

- Critical: `0`
- High: `0`
- Medium: `0`

`voice_recording_session.py`は1-file contractとして大きいが、Lockがshared/module splitを認可していないため、pure validatorsとtyped recordsを同一owner fileへ保持した。effect adapter/storageを混在させておらず、現在のfunctional/security blockerではない。将来分割は別Lock/compatibility proposalを要求する。

## 12. Read-only Judge Before Publish

- Exact Active Lock: `PASS`
- Exact 5 Allowed Files: `PASS`
- Canonical five root types: `PASS`
- Schema mirror parity: `PASS`
- Body-free / pure metadata: `PASS`
- CAS/state/UNKNOWN/cancel/resume: `PASS`
- Authorization fail-closed: `PASS`
- Candidate/Review/Adoption separation: `PASS`
- Focused tests: `PASS (25)`
- Windows available checks: `PASS`; full pytest availabilityは正直に`NOT_RUN`
- WSL2 full regression: `PASS (1215)`
- Critical/High/Medium: `0/0/0`
- Production/recording/Dataset/Training authority: `BLOCKED / NOT_AUTHORIZED`

判定: `READY_FOR_ATOMIC_COMMIT_AND_DRAFT_PR`

Ready/Mergeは本判定に含まない。exact PR head/diff/hosted checksを設計Judgeへ提出し、明示ProceedまでDraftを維持する。
