# Security Policy

## Supported versions

Alpha期間中は、既定Branchの最新版のみをSecurity update対象とします。過去Tagは再現・監査用であり、原則としてSecurity patchを受けません。

## Reporting a vulnerability

脆弱性の詳細を公開Issueへ投稿しないでください。GitHubのPrivate vulnerability reportingを有効化し、Repositoryの**Security → Report a vulnerability**から報告してください。利用できない場合は、攻撃手順や秘密値を書かず「非公開連絡が必要」とだけIssueで知らせてください。

報告には影響機能、最小再現条件、影響範囲、検証環境、修正案、希望公開時期を含めてください。

## Prohibited content

API Key、Token、Cookie、Authorization Header、署名URL、Provider response body、実在人物の個人情報・音声・顔、非公開素材を報告へ含めないでください。Credential漏えい時は直ちに失効・再発行してください。

## Security boundaries

- Credentialは`credential://`参照として保持し、実行時Storeから解決する。
- Endpointはallowlist、HTTPS／local policy、Timeout、response sizeで制限する。
- 通常CIは有料API、外部Provider、Resolve、ComfyUI、Audacityを実行しない。
- Human-owned Timelineと元素材をAutomationが直接変更しない。
- 外部生成は権利承認、費用上限、idempotency、provenanceを必要とする。

## Automated checks

CIはoffline-first regressionとcompileallを実行します。Security workflowはdependency auditとGit履歴のsecret scanを実行します。除外を追加する場合は対象と理由を最小限に限定してください。

OpenAI、Anthropic、Google、ElevenLabs、SunoAPI.org、各Model、DaVinci Resolve、ComfyUI、Audacity、FFmpegなど外部製品自体の脆弱性は各公式窓口へ報告してください。
