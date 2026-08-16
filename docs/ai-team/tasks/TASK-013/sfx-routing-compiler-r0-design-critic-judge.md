# TASK-013 SFX Provider-Neutral Routing Compiler R0

Date: 2026-08-17
Authority: `BVP-AUTH-20260817-TASK013-SFX-ROUTING-COMPILER-R0-01`
Integration Lock: `BVP-ILOCK-20260817-TASK013-SFX-R0-CHANGELOG-01`

## 1. Outcome

既存 `CreativeGenerationMode.SFX`、AI Connection Profile、Asset、rights、
capability/license/resource Evidence の正本座標だけを参照し、SFX provider route の
除外と選択を決定論的にコンパイルする。Prompt、Asset、音声のbodyは保持しない。

本Unitはrouting planだけを生成する。Provider呼出し、Credential解決、H3 Foley、
SFX生成、Asset公開、Timeline配置、Resolve、Release/Deployを開始または許可しない。

## 2. Authority and ownership

| Concern | Canonical owner | This unit |
|---|---|---|
| Creative Generation intent/mode | existing TASK-013 | exact reference only |
| Provider profile/routes | existing AI Connection Profile | exact ID/version/hash binding |
| Provider adapters | `external_media_providers.py` | immutable, never called |
| Local H3 Foley generation | `h3_foley.py` | immutable, never called |
| Asset bytes/revision | Asset owner | body-free exact reference only |
| Rights/license/resource Evidence | their canonical owners | structured binding only |
| SFX route-plan metadata | this R0 unit | canonical JSON and digest |

Protected origin/main blobs at the operation Gate:

- `creative_generation.py`: `9b5b85b75b6c0d497cb940c3b933326e6d131351`
- `external_media_providers.py`: `877870ed21a174b546f8b9e0cbd6c06a8d495d5b`
- `h3_foley.py`: `8dc2b5655aee2ed888dce43d9f8fef6ac9fa567b`
- `bgm_generation_routing.py`: `7deac647cfe10c94e753aa5aa10fd7215c7aa000`

## 3. Domain contract

- `SfxCreativeGenerationIntentReference`: request/project/scene/slot、SFX、
  Prompt ID/revision/body digest、Creative plan digest、exact profile binding。
- `SfxAssetReference`: Asset ID/revision/checksumだけを保持し、bodyを保持しない。
- `SfxRightsEvidenceReference`: opaque `rights://` referenceとEvidence binding。
- `SfxRouteAdmissionEvidence`: route別 capability/license/resource binding。
- `SfxRoutingRequest`: compilation identityと上記のimmutable coordinates。
- `SfxRouteDecision`: provider profileが供給したroute座標、disposition、固定順reason。
- `SfxRoutingPlan`: ordered decisions、selected route、canonical digest、全effect flag false。

Binding stateは `CANONICAL_REF_NOT_PROVIDED / BOUND_VERIFIED / MISMATCH /
UNKNOWN`。未提供・UNKNOWNをzero/PASSへ変換しない。MISMATCHはfail closedする。
`BOUND_VERIFIED`はexact Evidence referenceとdigestの両方を要求する。

## 4. Deterministic compilation

1. Intentのprofile ID/version/hashをactive profileと照合する。
2. `AiWorkload.AUDIO` routeだけを `(priority, route_id)` で安定sortする。
3. global intent/rights/Asset bindingを評価する。
4. enabled、availability、credential availability、`SFX` capability、selection mode、
   capability/license/resource Evidenceを固定順で評価する。
5. 最初のeligible routeだけを選択し、残りは理由付きで除外する。
6. routeがない、または全routeが除外された場合もBLOCKED/UNKNOWNを明示する。
7. canonical JSON bytesからdigestを計算する。

Profile内のprovider/model値はdataとして転記するだけで、特定Providerやmodelを
compilerへ固定しない。Credential referenceやroute settingsはplanへ保存しない。

## 5. No-effect surface

`provider_execution_admitted`、`provider_execution_started`、
`sfx_generation_started`、`h3_foley_started`、`asset_publication_started`、
`placement_started` は常にfalseである。raw `execution_authorized` boolean、network、
filesystem、audio、provider SDK、process、paid/credential API surfaceを持たない。

## 6. Acceptance matrix

| ID | Case | Result |
|---|---|---|
| SFX-01 | highest-priority verified AUDIO/SFX route | selected |
| SFX-02 | lower-priority eligible route | excluded with stable reason |
| SFX-03 | input Asset order variation | identical canonical digest |
| SFX-04 | Prompt/Asset body、Credential、route settings | not persisted |
| SFX-05 | rights UNKNOWN/unprovided | UNKNOWN |
| SFX-06 | rights/Asset mismatch | BLOCKED |
| SFX-07 | capability/license/resource UNKNOWN | UNKNOWN |
| SFX-08 | missing route Evidence | UNKNOWN |
| SFX-09 | disabled/unavailable/credential/capability/mode | fixed ordered reasons |
| SFX-10 | AUDIO workload disabled / no AUDIO route | BLOCKED |
| SFX-11 | profile ID/version/hash mismatch | rejected |
| SFX-12 | non-SFX intent / duplicate coordinates | rejected |
| SFX-13 | forged BOUND / secret-bearing Evidence ref | rejected |
| SFX-14 | MUSIC route | never used for SFX |
| SFX-15 | Provider/SFX/Foley/Asset/placement flags | all false |
| SFX-16 | protected existing files | blobs unchanged |
| SFX-17 | paid/cloud/local route | metadata parity, no execution authority |
| SFX-18 | focused/full/hosted/postmerge gates | required before closure |

Local validation:

- SFX + BGM focused compatibility: `33 passed`
- Ubuntu WSL2 full regression using the existing offline runtime:
  `1457 passed / 1 Windows-only installer skip`
- Windows bundled Python AST parse: PASS
- `git diff --check`: PASS
- static no-effect/security scan: PASS
- protected existing blobs: `4_OF_4_PASS`

Windows bundled Pythonにはpytestが含まれないため、Windows full regressionはhosted
Windows 3.11/3.12/3.13 checksで必ず確認する。未実行をlocal PASSへ読み替えない。

## 7. Critics

### Builder Critic

Finding: BGM compilerのprivate helper再利用やshared refactorはAllowed Filesを越える。

Correction: SFX-specific closed typesとvalidatorを新規module内に限定し、schema、
`__init__.py`、既存consumerを変更しない。Residual Critical/High/Medium = 0/0/0。

### Security Critic

Finding: route profileにはCredential referenceが含まれ得る。

Correction: availability判定にのみ使用し、planにはpersistしない。Evidenceは
`evidence://`、rightsは`rights://`だけを許容し、body/effect flagsを固定する。
Residual Critical/High/Medium = 0/0/0。

### Compatibility Critic

Finding: SFX routingをH3 Foleyまたはexternal adapterとして実装すると既存正本を
重複し、routing successをgeneration successへ誤昇格させる。

Correction: compilerは`CreativeGenerationMode.SFX`と`AiWorkload.AUDIO`の公開契約だけを
参照し、既存Foley/provider/BGM filesを不変にする。
Residual Critical/High/Medium = 0/0/0。

## 8. Judge

- DOMAIN_READINESS: PASS
- DETERMINISTIC_BODY_FREE_ROUTING: PASS
- PROVIDER_NEUTRALITY: PASS
- EFFECT_BOUNDARY: PASS_FAIL_CLOSED
- Critical/High/Medium: 0/0/0
- Provider/network/paid/credential/H3 Foley/audio/Asset/placement/Release/Deploy: NOT AUTHORIZED

Canonical completion requires exact four-file diff, focused and full Windows/WSL regression,
hosted checks terminal SUCCESS, canonical merge, postmerge CI/Security SUCCESS and serialized
CHANGELOG Lock release.
