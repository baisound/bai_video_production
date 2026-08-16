# TASK-013 BGM Provider-Neutral Routing Compiler R0

日付: 2026-08-17

Authority: `BVP-AUTH-20260817-TASK013-BGM-ROUTING-COMPILER-R0-01`

Integration Lock: `BVP-ILOCK-20260817-TASK013-BGM-R0-CHANGELOG-01`

## A. 目的と境界

既存 `CreativeGenerationMode.MUSIC_GENERATION`、AI Connection Profile、Asset、rights、Evidence の正本座標だけを参照し、BGM Provider route の選択計画を決定論的にコンパイルする。Provider 呼出し、Credential 解決、media read/write、BGM生成、Asset公開、配置、Resolve、Release/Deployは行わない。

既存 `creative_generation.py`、`external_media_providers.py`、`h3_foley.py` は不変とし、provider-neutral orchestration と provider/media effect を分離する。

## B. Fresh Gate

- canonical base: `main@455b2bf73a9f7098b82ac23efabd412e4e34bf1a`
- Registry revision: `23`
- open PR: `0`
- active implementation Lock: `BVP-LOCK-TASK046-PVS3B` のみ
- exact4 path overlap: `0`
- local/remote target branch collision: `0`
- TASK-014 I1: PR #139 merge/postmerge green、CHANGELOG sub-Gate consumed/released

## C. 契約

### C1. 入力

- `CreativeGenerationIntentReference`: request/project/scene/slot、MUSIC_GENERATION、Prompt ID/revision/body digest、Creative Generation plan digest、exact provider-profile binding。Prompt bodyは保持しない。
- `BgmAssetReference`: canonical Asset ID/revision digest/content checksum と Evidence binding。Asset body/pathは保持しない。0件も許容する。
- `BgmRightsEvidenceReference`: secretを含まない `rights://` 座標と Evidence binding。
- `BgmRouteAdmissionEvidence`: route単位の capability/license/resource binding。
- `AiConnectionProfile` / `ConnectionAvailability`: 既存正本をread-onlyで利用する。

全binding stateは `CANONICAL_REF_NOT_PROVIDED | BOUND_VERIFIED | MISMATCH | UNKNOWN`。`BOUND_VERIFIED`はexact `evidence://` refとSHA-256を必須とし、未提供・UNKNOWN・MISMATCHをPASSへ変換しない。

### C2. route判定

MUSIC routeを `(priority, route_id)` で安定sortし、次を固定順で評価する。

1. global intent/rights/Asset binding
2. route enabled/availability
3. credential availability（Credential値は保存しない）
4. required capability
5. AI Connection selection mode
6. exact capability/license/resource Evidence

最初のeligible routeだけを `SELECTED` とし、後続eligible routeは `NOT_SELECTED_LOWER_PRIORITY`。全候補について除外理由を順序付きで残す。

### C3. 出力

`BgmRoutingPlan` は body-free immutable metadata。canonical JSONから `plan_sha256` を計算し、`provider_execution_admitted=false`、`provider_execution_started=false`、`bgm_generation_started=false`、`asset_publication_started=false`、`placement_started=false` を固定する。

状態:

- `ROUTE_SELECTED`: exact verified routeを1件選択
- `BLOCKED`: mismatch、disabled、またはknown exclusionのみ
- `UNKNOWN`: canonical ref、capability、license、resource等が未提供/観測不能

route選択はProvider execution authorizationではない。paid/credential/provider/network/media effectは別Gateである。

## D. Acceptance

| ID | Acceptance | Result |
|---|---|---|
| BGM-01 | highest-priority verified routeを一意選択 | PASS |
| BGM-02 | lower-priority eligible route理由を保持 | PASS |
| BGM-03 | canonical JSON/digest再現性 | PASS |
| BGM-04 | Prompt/Asset body、Credential、route settings非保持 | PASS |
| BGM-05 | rights UNKNOWN/未提供をUNKNOWN | PASS |
| BGM-06 | rights/Asset mismatchをBLOCKED | PASS |
| BGM-07 | capability/license/resource UNKNOWNをUNKNOWN | PASS |
| BGM-08 | missing route EvidenceをUNKNOWN | PASS |
| BGM-09 | disabled/unavailable/credential/capability/mode理由の固定順 | PASS |
| BGM-10 | MUSIC disabled / route0件をBLOCKED | PASS |
| BGM-11 | profile ID/version/hash mismatch拒否 | PASS |
| BGM-12 | non-MUSIC intent、duplicate Asset/route Evidence拒否 | PASS |
| BGM-13 | forged BOUND Evidence、secret-bearing ref拒否 | PASS |
| BGM-14 | Provider/BGM/Asset/placement effect flag false | PASS |

Validation:

- focused/compatibility: `36 passed`
- Windows full regression: `1440 passed / 1 intentional non-Windows skip`
- Ubuntu WSL2 full regression (existing offline runtime): `1440 passed / 1 Windows-only installer skip`
- `py_compile`: PASS
- `git diff --check`: PASS
- static no-effect scan: PASS

## E. Critic 1 — Builder

Finding: generic Creative Generation plannerを再実装すると既存authorityとdriftする危険。

Correction: inputは既存mode/profile/availabilityとimmutable coordinateへ限定し、provider adapter・Asset store・Prompt bodyを含めない。

Residual Critical/High/Medium: `0/0/0`。

## F. Critic 2 — Security / Privacy

Finding: persisted credential ref、route settings、Prompt/Asset body、pathをPlanへ漏らす危険。

Correction: outputはcredential presenceを理由判定にだけ使用し、Credential ref/settings/body/pathを一切serializeしない。Evidence refはallowlisted `evidence://`、rightsは `rights://`、digestはcanonical lowercase SHA-256に限定。

Residual Critical/High/Medium: `0/0/0`。

## G. Critic 3 — Compatibility / Fail-closed

Finding: UNKNOWNを単なるroute exclusionとしてBLOCKEDへ弱める、候補順がcaller順で変わる危険。

Correction: UNKNOWN provenanceをPlan stateへ伝播し、候補を `(priority, route_id)` sort、理由順を固定。profile exact hash mismatchとduplicate coordinatesをreject。

Residual Critical/High/Medium: `0/0/0`。

## H. Judge

- DOMAIN_CONTRACT: PASS
- PROVIDER_NEUTRAL_DETERMINISM: PASS
- UNKNOWN_FAIL_CLOSED: PASS
- BODY_FREE_PRIVACY: PASS
- PROVIDER_MEDIA_EFFECT: `0`
- Critical/High/Medium: `0/0/0`
- Judge: `PASS_FOR_DRAFT_PR_AND_HOSTED_CHECKS`

Ready/Mergeはexact4、full regression、hosted checks、fresh-main overlap0、postmerge CI/Securityをすべて満たす場合だけ進める。
