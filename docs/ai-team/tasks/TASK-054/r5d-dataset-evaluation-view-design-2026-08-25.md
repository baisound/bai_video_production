# TASK-054 R5D Dataset / Evaluation View Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `IMPLEMENTED / COMMIT_READY`

## Goal

Training Studioに、R4A-R4E-Bで作られたDataset・漏洩監査・offline評価・blind review・昇格候補Evidenceを、Operatorが安全に確認できる日本語の読み取り専用画面として接続する。

## Canonical boundary

R5Dは新しいDataset、評価、昇格、Timeline、モデルのcanonical sourceを所有しない。入力は各R4 moduleのpublic admissionで再検証し、画面用のimmutable snapshotへ投影するだけである。Dataset/split変更、TEST期待文表示、評価・training・Provider実行、Binding承認、モデル昇格は行わない。

## Inputs and projection

1. R4A manifestを再admitし、TRAIN / VALIDATION / TESTの件数、候補、要確認を集計する。
2. TESTは常に`target_text_visible=false`かつ`editable=false`とする。
3. R4C leakage reportはexact manifest digestを要求する。
4. R4D offline reportはexact manifest/leakage digestを要求し、BASELINE / GENERIC / TUNEDをcanonical orderで表示する。
5. R4E-A blind presentationはexact offline report digestとexact TEST sample-set digestを要求する。
6. R4E-B promotion candidateはexact offline report、presentation、TEST sample-setを要求する。

Evidence未入力は`NOT_AVAILABLE`とし、未確認をPASSにしない。digestまたはsample-setが交差した場合はfail closedとする。

## Operator flow

- `Dataset監査`: split別の件数、候補、要確認、編集可否。TEST固定と期待文非表示を常時説明する。
- `モデル比較`: arm別の状態、件数、JSON schema、引用、replay、話さない判断を1000分率で比較する。
- `Evidence詳細`: manifest digest、漏洩finding数、blind sample数を必要時だけ表示する。
- footer: `Dataset採用: 不可 / モデル昇格: Owner判断が必要 / この画面はEvidence閲覧専用`を常時表示する。

通常導線では長いdigestを隠し、詳細だけで参照できる。画面にはmutation callbackを持たせない。

## Failure modes

- noncanonical input、Evidence交差: public admissionとdigest照合で拒否
- AVAILABLEなのに対象が空: snapshot invariantで拒否
- metric範囲外、負の件数、split順不一致: view invariantで拒否
- adoption/promotion flag forge: immutable snapshot生成時に拒否

## Verification

Focused tests cover split counts, TEST lock/target hiding, matching/crossed leakage Evidence, stage consistency, metric bounds, fixed no-authority flags and required Japanese UI copy. R4 canonical contracts remain covered by targeted TASK-054 regression.

## Human Gates preserved

Dataset adoption、実データ取込、model/runtime download、training、Provider inference、TTS、binding approval、promotion、Timeline/Resolve mutation、Product Activation、release、deployは引き続きHuman-Gatedである。
