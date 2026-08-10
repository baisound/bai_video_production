# Contributing to BAI Video Production

ご協力ありがとうございます。本ProjectはAlpha段階で、Windows、外部Runtime、生成AI、NLE、権利・費用境界を扱います。

## Before starting

1. 既存IssueとPull Requestを検索してください。
2. 大きな変更、外部通信、Schema変更、Resolve mutationは実装前にIssueで提案してください。
3. 1 Pull Requestを1目的へ限定してください。
4. 公開API・正規のSDK・許可されたRuntime境界を使用し、規約回避や不正アクセスを提案しないでください。

## Development

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src tests
```

通常テストは外部通信、課金API、Resolve mutation、GUI自動起動を必要としない形にしてください。実機確認が必要な変更は、合成素材、空Project、明示的Timeout、Evidence保存先、復旧方法を文書化してください。

## Engineering rules

- Canonical data、Evidence、Job stateの決定論と後方互換性を守る。
- 元素材とHuman-owned Timelineを変更しない。
- Provider名からCapabilityを推測せず、正確なModel Capabilityを検証する。
- 秘密値をManifest、Profile、Prompt、log、test fixtureへ保存しない。
- 外部Processは固定argv、Timeout、出力上限、allowlistを使用する。
- 不明値を推測値や`0`で埋めない。
- 新しい依存関係は目的、License、Security、保守性を説明する。
- 無関係な整形変更を機能変更へ混ぜない。

## Pull Request requirements

- 変更目的と関連Issue
- 変更した契約、Schema、API
- 実行したテストと結果
- 外部通信、課金、権利、Privacyへの影響
- Windows／Python／Runtime互換性
- 文書とCHANGELOG更新
- 未解決事項とRollback方法

## Secrets, media and personal data

API Key、Token、Cookie、Authorization Header、署名URL、実在人物の音声・顔・個人情報、非公開動画をCommit、Issue、PR、ログ、スクリーンショットへ含めないでください。漏えいしたCredentialは履歴から削除するだけでなく失効・再発行してください。

## Contributor license

Pull Requestを提出することで、提供した変更を本RepositoryのMIT Licenseで公開する権利があることを表明します。第三者コードや生成素材を含める場合は、出典と再配布条件を明示してください。
