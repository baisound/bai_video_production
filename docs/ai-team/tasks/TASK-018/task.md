# TASK-018 — Smart Reframe / Remotion

- Status: `R0 IMPLEMENTED / AUTOMATED VALIDATED`
- Governance: `DEV-3/4`
- Owner: `開発担当`
- Release status: `NOT RELEASED BY THIS WORK`

## Purpose

TASK-007 の承認済み Edit Plan と、current-valid な TASK-005/TASK-008/Human Review の行Evidenceを、決定論的な縦型crop proposalへ束縛する。R0はprovider-neutralなデータ契約であり、Remotionや他rendererの実行を含まない。

## R0 inputs

- canonical source Asset ID / SHA-256 / square-pixel geometry / exact frame rate / total frames
- TASK-007 Edit Plan SHA-256 とordered non-overlapping keep ranges
- portrait target profile、exact source-rate binding
- source keep rangesをexact partitionするbounded crop proposal
- exact manifest/row coordinatesを持つcurrent/UNKNOWN/stale/revoked Evidence

## R0 outputs

- ordered source/output frame ranges
- source-contained、target-aspect-exact crop windows
- deterministic target profile digest and non-self plan digest
- `READY_FOR_HUMAN_REVIEW | UNKNOWN_EVIDENCE | STALE_OR_REVOKED_EVIDENCE`
- Human review required / render・Timeline・external-write authority false

## Hard boundaries

R0はmedia/path/raw bytes、filesystem、subprocess、network、provider、detector、Remotion、Resolve、Timelineへのsurfaceを持たない。実media read、focus detection、OCR、render、Remotion execution、vertical artifact publication、Asset adoption、Timeline placementは別Gateである。UNKNOWNやstale/revoked Evidenceはreadyへ昇格しない。

## Next slices

1. bounded synthetic adapter fixture
2. exact Remotion dependency/license/runtime admission
3. no-media capability probe
4. synthetic-media render probe
5. real-media/Human acceptance and downstream adoption
