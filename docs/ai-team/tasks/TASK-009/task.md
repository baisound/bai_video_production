# TASK-009 — DBDProfilePlugin

- Status: `R0 IMPLEMENTED / AUTOMATED VALIDATED`
- Governance: `DEV-3`
- Owner: `開発担当`
- Dependency: `TASK-008 Multimodal Scoring`
- Release status: `NOT RELEASED BY THIS WORK`

## Purpose

DBD固有のHUD・chase・event taxonomyを、TASK-008のprovider-neutral FeatureRule/ScoringProfileへ決定論的に投影するProduct Profile Plugin契約を提供する。

## R0 boundary

R0は、作者が既に選んだcanonical feature source selectorとruleを束縛するdata-only snapshotである。HUD_STATE/CHASE/EVENTの全family、signal kindとfamilyのclosed mapping、TASK-008 rule projection exact equality、plugin descriptor/capability/input/output/failure boundary、canonical digestを固定する。

feature producer、runtime、HUD detector、OCR、game process、media、path、raw bytes、filesystem、network、subprocess、Providerを選択・実行しない。出力はHuman review必須で、Edit Plan、Timeline、external effect authorityを持たない。

## Next Gates

1. exact DBD feature producer / detector Evidence contract
2. no-media capability admission
3. bounded synthetic fixture
4. real-media/Human accuracy review
5. TASK-008 score consumption and Human-reviewed downstream proposal
