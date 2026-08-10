# Governance

## Roles

- **Lead Maintainer:** `baisound`。Release、Security、Roadmap、最終Mergeを管理します。
- **Contributor:** Issue、設計提案、Code、Test、Documentationを提供します。
- **Reviewer:** 技術領域ごとに変更の正確性、安全性、互換性を確認します。

## Decision making

通常変更はIssue／Pull Request上の根拠、Test、Reviewで決定します。合意できない場合はLead MaintainerがProject目的、安全性、後方互換性、保守負担を基準に決定し、理由を記録します。

Security、Credential、権利、Privacy、外部費用、Human-owned artifact、Canonical Schemaの変更は、速度より安全性を優先します。緊急Security fixは限定的に先行Mergeし、後からEvidenceと説明を補完できます。

## Releases

- Semantic Versioningを基本とします。
- Release Commitへ注釈付き`vX.Y.Z` Tagを付けます。
- CHANGELOG、Package Version、Test結果、既知制約を同期します。
- Release ZIPはGit履歴とTagを含む形でも提供できます。

## Project independence

BAI Development OSは開発Governanceとして利用できますが、Product runtimeの必須依存ではありません。公開Contributorは特定のAI Toolや有料Serviceを使う必要はありません。
