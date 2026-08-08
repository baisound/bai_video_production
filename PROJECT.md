# AI動画制作自動化システム

## Project ID

`ai-video-production`

## Project Status

`FOUNDATION_READY`

## Purpose

元動画・音声・画像・字幕・AI生成素材を解析・計画・編集・検査し、DaVinci Resolveを中心に人間が安全に仕上げられる動画制作自動化基盤を構築する。

## Active Project Root

`/home/baisound/projects/ai-video-production`

## Source / Test / Documentation

- Source: `src/`
- Tests: `tests/`
- Schemas: `schemas/`
- Profiles: `profiles/`
- Documentation: `docs/`
- Project Task Evidence: `docs/ai-team/tasks/`

## BAI Development OS Integration

- OS Root: `/home/baisound/bai-development-os`
- OS Version Baseline: `1.0.0`
- Architecture Baseline: `Ver.2.27 CURRENT_CANONICAL`
- Adapter: `.bai-os/project.json`
- Bootstrap Governance Level: `Level A — Governance Only`
- TASK-001 decision: remain `Level A — Governance Only`; runtime-assisted BAI dependency is not justified for the product foundation
- BAI OS Core / shared Roles / OS-owned Tasks / Registry are not copied into this repository
- Product runtime does not depend on BAI OS unless an authorized Task explicitly approves that dependency

## Product Design Baseline

`AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`

この設計書はProduct仕様のBaselineである。BAI Development OSの開発Governanceとは責任を分離する。

## Core Product Principles

1. Canonical ManifestをProduct Domainの正本とし、NLE Projectだけを正本にしない。
2. AI判断と決定論的実行を分離する。
3. 元素材を破壊せず、再生成可能・監査可能にする。
4. Automation-ownedとHuman-owned Timelineを分離する。
5. Windows/WSL2/Object StorageのPath差異をLogical URI/Path Resolverで吸収する。
6. Production Job StateはProduct Domain専用Serviceのみが変更する。
7. External Provider / NLE / AI ModelはAdapter境界を持つ。
8. Product JobはCheckpoint/Evidence/Idempotencyにより安全に再開可能にする。
9. 権利、プライバシー、費用、公開安全性をProduct要件として扱う。
10. 開発TaskのAuthorizationとProduct Jobの状態を混同しない。

## BAI OS / Product Domain Separation

- BAI LifecycleOS: 開発TASK用。
- Product Job State Machine: 動画制作案件用。
- BAI Lifecycle Recovery: 開発作業のSafe Stop/Resume用。
- Product Job Recovery: 動画処理の途中再開用。
- BAI Cost Guard: AI支援開発/Tooling予算用。
- Product Cost Ledger: 動画生成ジョブの費用用。
- BAI SecurityOS: 開発Tooling/Secret/Egress/Sandbox用。
- Product Privacy Guard: 動画内容のPII/権利/NG表現用。

## Adaptive Governance

各TASKをDEV-0〜DEV-4へ分類する。すべての変更へ固定の最大手続きを強制しない。

`TASK-001`は`DEV-4 FOUNDATION CRITICAL`（score 25）として完了した。`TASK-002`はResolve Gatewayという外部統合境界、Security、External Side Effect、New Architectureを含むため`DEV-4 FOUNDATION CRITICAL`（score 22）として起票・認可されている。Safety Floorは下げていない。

## Security / Privacy Constraints

- Secret値をManifest、prompt、log、evidenceへ保存しない。
- Product Path ResolverはAllowlist外Pathを拒否する。
- External inputから任意Shell/Pythonを直接実行しない。
- PII、Voice Model、Rights metadataはSensitivity/Retentionを定義する。
- External serviceのCredential/Egressを開発Toolingから扱う場合はBAI SecurityOS / IntegrationOS境界を優先する。

## Current Consumer Task State

- Last Completed: `TASK-002 — Resolve Capability Spike`
- Active Task: `NONE`
- TASK-002: `COMPLETED` / package `0.2.4`
- Target Resolve: `DaVinci Resolve Studio 21.0.2.4`; final sandbox matrix `15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED`
- Final IPC ADR: WSL2→Windows primary transport = authenticated HTTP/JSON over the Windows host/default-gateway endpoint; Windows Named Pipe retained as Windows-local optimization candidate
- Project Roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.2 — Owner-directed editing-first priority (Cut/SRT/字幕/SE/BGM/ナレーションの生成・配置を前倒し)
- Recommended next Consumer Task: `TASK-003 — Asset Registry / Ingest / Path Resolver` (NOT_STARTED / NOT_AUTHORIZED)
- OS-internal TASK-016 remains unrelated and untouched.

## Completion Rule

Taskは、選択DEV Profileの要求、実装、必要Test、blocking finding解消、内部文書同期、Completion Evidenceが揃った場合のみ完了する。

Test PASSやNEXTをOwner Authorizationへ読み替えない。
