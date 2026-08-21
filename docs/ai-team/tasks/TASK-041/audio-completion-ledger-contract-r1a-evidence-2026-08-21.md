# TASK-041 Audio Completion Ledger Contract R1A Evidence

Date: 2026-08-21

Atomic Unit: `TASK-041/AUDIO-COMPLETION-LEDGER-CONTRACT-R1A`

DEV profile: `DEV-4 FOUNDATION CRITICAL`

Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / COMMIT_READY / UNCOMMITTED`

Base main: `530ebb2c3186d0d4c127cc7d6e4342bd3e9e60f6`

## Result

R0の`SOURCE_REVALIDATION_REQUIRED / NOT_MINTED`候補を変更せず、callerから
供給されたimmutable entry chainだけをpureに検証するR1A contractを追加しました。
このUnitはfilesystemを観測せず、entryを永続化せず、native CASを実行せず、
canonical latest/current/PASSまたはTASK-036 Final Review wrapperを発行しません。

## Exact scope

1. `src/ai_video_production/audio_completion_ledger_contract.py`
2. `schemas/audio-completion-ledger-contract.schema.json`
3. `src/ai_video_production/schema_resources/audio-completion-ledger-contract.schema.json`
4. `tests/test_task041_audio_completion_ledger_contract.py`
5. `docs/ai-team/tasks/TASK-041/audio-completion-ledger-contract-r1a-evidence-2026-08-21.md`

既存R0、TASK-036、shared atomic writer、store/application/current-state/roadmap、
CHANGELOG、workflowは変更していません。

## Contract boundary

- ledger keyはproject/timeline revision+SHA、R0 scope binding SHA、receipt IDを
  domain-separated digestへ結合します。
- entry envelopeはexact R0 candidate、candidate receipt SHA、entry revision、
  parent entry SHA、prior/resulting chain SHAを結合します。
- entry stateは`PERSISTENCE_NOT_OBSERVED_BY_R1A`であり、R1Bが将来保存した
  bytesについてunpersistedとは主張しません。
- genesis、revision、parent、timestamp、R0 candidate transition、key、order、
  fork/replay/gapをfull supplied-chain validationでfail closedにします。
- CAS expectationはcaller expectationでありauthorityではありません。
- append evaluationは`CONTRACT_APPEND_ELIGIBLE_NOT_AUTHORIZED`等のpure判定のみで、
  COMMITTED/PERSISTED/RECOVEREDを返しません。
- exact latest replayはprefix CAS一致時のみ
  `IDEMPOTENT_LATEST_MATCH_NOT_AUTHORIZED`です。
- serialized observation名は`PROVIDED_CHAIN_DIAGNOSTIC`であり、filesystem/native/
  canonical latestを観測したとは主張しません。自己署名済みrecordからvalidation
  authorityを再発行しないため、private/publicとも
  `provided_chain_semantically_validated=false`、
  `consumer_revalidation_required=true`です。
- public projectionはproject/timeline/receipt/source coordinatesとprivate chain digestを
  除外し、state/countとfalse authorityだけを公開します。
- ordinary SHA-256はself-consistencyでありorigin authentication/capabilityではありません。
- chain inputはexact list/tupleだけを許し、truthiness判定前にentry countを閉じます。
  malformed first entryをclosed parserへ通し、entry単体4 MiB、chain総16 MiB、
  256 entries、aggregate evidence items 4096でfail closedにします。
- public APIはcaller key/CAS subtypeを受理せず、一度reparseしたexact sealed recordだけを
  validationとoutputに使用します。

## Authority and effects

次の値は全private recordでfalse固定です。

- native append authorization
- filesystem persistence verification
- storage origin authentication
- upstream owner revalidation
- canonical latest/PASS authorization
- Final Review gate issuance
- filesystem/network/provider/audio/model/process/release/deployment effects

R1B Windows native immutable store、R2 owner API revalidation/Application Reader、
TASK-036 composition adapterは別Atomic Unitです。

## Verification

WSL Ubuntu、repository既存dependencyのみ。install、network、E drive、audio/model/native
実行はありません。

Focused:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_task041_audio_completion_ledger_contract.py
25 passed in 3.82s
```

R0 + TASK-036 consumer boundary regression:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_task041_audio_completion_ledger_contract.py \
  tests/test_task041_audio_completion_receipt.py \
  tests/test_task036_final_review_gate.py
57 passed in 3.87s
```

- Draft 2020-12 schema check: PASS
- public/package schema byte equality: PASS
- Python AST/static no-I/O/no-owner-reader boundary: PASS
- `git diff --check`: PASS
- exact dirty scope: 5 untracked files

Current file SHA-256:

- module: `08a46bb69925d3e6b00037385176ba1b101733a250364d4c0f8c6fd3a746fb34`
- public schema: `ffb06475d2b37e6689589c21503b5f81e6f7b1cb6d482f55a71a8a08e8d6aba9`
- packaged schema mirror: `ffb06475d2b37e6689589c21503b5f81e6f7b1cb6d482f55a71a8a08e8d6aba9`
- focused test: `da524f1e45c86acbbffeb306e9f6adbdb915616af92fbfdd48ef167cd540d703`

Initial DEV-4 review found C0/H3/M3. The failure-fix closes false-empty admission,
serialized validation laundering, aggregate resource amplification, persistence wording,
malformed-first-entry normalization, decision/reason schema parity, caller key reuse,
public state/count schema parity, and the external-schema resolver scope defect. Independent
failure-fix Tester and Critic/Judge both returned C0/H0/M0. The branch was then fast-forwarded
to fresh main `530ebb2c3186d0d4c127cc7d6e4342bd3e9e60f6`; focused and related suites were
rerun with the results above. No exact5 drift or overlap occurred.

Independent Tester/Critic/Judge results are pending. The Unit is not commit-ready
until required DEV-4 review closes all Critical/High findings and fresh-main validation
is repeated.
