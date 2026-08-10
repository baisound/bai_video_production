# Codex for OSS — Repository Readiness

Updated: 2026-08-10

## Purpose

This document separates repository readiness from application eligibility. A good README and license make participation safer, but they do not prove adoption or guarantee acceptance.

## Public-interest statement

BAI Video Production aims to make safe, auditable video automation available to people and small organizations that cannot assemble a costly stack of AI providers, media pipelines, and professional editing expertise. Its public contribution is a provider-neutral foundation where local and cloud models can be exchanged, human editors retain control, and rights, privacy, cost, provenance, recovery, and reproducibility are first-class constraints.

The project can reduce duplicated engineering across educational, cultural, accessibility, nonprofit, creator, and small-business workflows. It also offers a practical alternative to opaque one-click generation: outputs remain inspectable, replaceable, and editable in a professional NLE.

This is an intended impact, not a claim of demonstrated scale. Adoption and outcome metrics must be published as evidence becomes available.

## Application draft (Japanese, each under 500 characters)

### Project description and public benefit

BAI Video Productionは、企画、素材生成、音声・音楽、既存動画編集、DaVinci Resolve組立を安全に自動化する、Provider中立のOSS基盤です。高価で断片化した制作環境を個人、教育・文化・非営利、小規模事業にも開きます。人間の最終判断と素材差し替えを残し、権利、同意、費用、来歴、再現性、失敗復旧を制作工程の中心に置きます。特定AI企業へ固定せず、local/free/paidモデルを用途と条件に応じて選択できます。

### Maintainer contribution

私は主要Maintainerとして、製品構想、Canonical Manifest、Asset/rights管理、正確なtimebase、Provider/Model capability routing、Resolve・ComfyUI・Audacity/OpenVINO境界、安全設計、テスト、Windows実機検証、Release管理を継続しています。Issue/PRの判断基準、Security Policy、Governance、Roadmap、再現可能な検証手順を公開し、外部Contributorが安全に参加できる基盤を整えています。

### Why Codex support matters

動画制作OSSは、Windows/NLE、media処理、複数AI API、権利・Privacy、安全な再試行を横断し、実装と回帰検証の負担が大きい領域です。Codex支援により、Adapter追加、クロスプラットフォーム試験、Issue triage、文書化を速め、限られたMaintainer資源を利用者検証と品質判断へ集中できます。成果はProvider中立の実装、Test、Schema、設計資料として公開し、他の動画・Creator toolingにも再利用可能にします。

## Implemented repository baseline

- Public README with honest Alpha scope and impact statement
- MIT license, contribution guide, code of conduct, security policy, governance, support, changelog, citation and third-party notices
- Issue forms, pull request checklist and CODEOWNERS
- Linux/Windows/Python CI, dependency audit, secret scan and Dependabot
- Offline-first tests and explicit separation of live/paid provider probes

## Actions required on GitHub

- Make both the GitHub profile and repository public.
- Confirm the repository URL and default branch match README metadata.
- Push the complete Git history and annotated version tags; publish releases with changelog notes.
- Enable branch protection/rulesets with required CI and security checks.
- Enable private vulnerability reporting and review the security contact.
- Add repository description, topics, social preview and funding link if applicable.
- Triage issues and review pull requests publicly; document response cadence.
- Record only verifiable adoption: releases, users, dependent projects, contributors, issues resolved, and production outcomes.

## Suggested impact evidence

| Dimension | Evidence to publish |
|---|---|
| Access | Active installations, organizations, supported languages/platforms |
| Efficiency | Median human time and cost saved against a defined baseline |
| Safety | Rights metadata completion, secret leaks prevented, destructive writes blocked |
| Reliability | Job recovery rate, deterministic rerun rate, cross-platform pass rate |
| Human control | Asset replacements, accepted/rejected proposals, manual handoff success |
| Ecosystem | Contributors, merged PRs, downstream integrations, reusable adapters/schemas |

Never invent usage, stars, users, savings, or social benefit. Link raw methodology and anonymized aggregate Evidence when making quantitative claims.

## Eligibility boundary

The official application requires a public GitHub profile and public repository, and asks for evidence that the applicant is an active core maintainer and that the project is actively maintained and adopted or important to the ecosystem. Repository files alone do not satisfy those evidence requirements.

Official form: <https://openai.com/ja-JP/form/codex-for-oss/>
