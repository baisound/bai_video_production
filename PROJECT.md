# AI動画制作自動化システム

## Project ID

`ai-video-production`

## Project Status

`TASK-006_SLICE_A_TRANSCRIPT_SRT_FOUNDATION_IMPLEMENTED`

## Purpose

元動画・音声・画像・字幕・AI生成素材を解析・計画・編集・検査し、DaVinci Resolveを中心に人間が安全に仕上げられる動画制作自動化基盤を構築する。

## Active Project Root

Consumer Project Repository root. Machine-specific absolute paths are not canonical project metadata.

## Source / Test / Documentation

- Source: `src/`
- Tests: `tests/`
- Schemas: `schemas/`
- Profiles: `profiles/`
- Documentation: `docs/`
- Project Task Evidence: `docs/ai-team/tasks/`

## BAI Development OS Integration

- OS Version Baseline: `1.0.0`
- Architecture Baseline: `Ver.2.27 CURRENT_CANONICAL`
- Planned development-governance baseline from Product `0.17.0`: `BAI Development OS 1.0.0 / Architecture Ver.2.28 CURRENT_CANONICAL`
- Adapter: `.bai-os/project.json`
- Bootstrap Governance Level: `Level A — Governance Only`
- TASK-001 decision: remain `Level A — Governance Only`; runtime-assisted BAI dependency is not justified for the product foundation
- BAI OS Core / shared Roles / OS-owned Tasks / Registry are not copied into this repository
- BAI Development OS is a development-time governance/tooling foundation only. It is not a Product runtime dependency.

### Repository Ownership Boundary — Must Read

Canonical invariant: `PROJECT_OS_OWNERSHIP_BOUNDARY`

このRepository内のProduct固有ファイルはBAI Video Production自身が所有する。パス名に`ai-team`を含むことだけを理由にBAI Development OS所有と判断してはならない。変更可否はパス名ではなくOwnershipで判断する。

- `PROJECT.md`、`src/`、`tests/`、`schemas/`、`profiles/`、`docs/`、および`docs/ai-team/`配下のBAI Video Production固有Task / Design / Evidence / Current StateはProduct-ownedであり、実装結果と同期するため必要に応じて更新する。
- BAI Development OS repository側のCore、Registry、shared Roles、OS-owned Tasks、OS-owned Evidence、Governance canonical documentsはOS-ownedであり、Consumer Project開発から勝手に変更しない。
- BAI Development OS CoreやOS-owned文書をこのRepositoryへ丸ごとコピーしてProduct-ownedとして扱わない。
- `docs/ai-team/`を一律READ ONLYとする運用は禁止する。個々の文書のOwnershipを確認して扱う。
- Ownershipが不明な文書は変更前に由来・役割・参照関係を確認し、推測でOS-owned / Product-ownedを決めない。

## Non-Negotiable Product Goal — Standalone Application

Canonical invariant: `STANDALONE_APPLICATION_REQUIRED`

BAI Video Productionの最終成果物は、BAI Development OSから独立してインストール・起動・実行・更新・利用できる単体アプリケーションでなければならない。BAI Development OSは開発時に設計、Critic/Judge、Knowledge、Context/Cost Guard、Integration/Security/Release等の能力を必要に応じて利用するための共通開発基盤であり、完成Productの実行環境ではない。

- Product runtimeはBAI Development OS repository、package、Registry、Role、OS-owned Task、Evidence store、Context PackまたはOS内部Serviceの存在を要求してはならない。
- 開発中にBAI Development OSのSubsystemを利用しても、Product実行時に必要なCapabilityはProduct所有の実装・Adapter・明示的なProduct dependencyとして成立させる。
- BAI Development OSの更新・停止・削除・未接続によって、完成したBAI Video Productionの通常利用が停止してはならない。
- 0.17.0以降のOS差し替えは「開発方法の更新」であり、「Product runtimeへのOS組込み」ではない。
- 将来の設計、Refactor、Provider統合、配布方式の判断は、このStandalone Application要件を弱めてはならない。
- この要件と衝突する提案は、TASK認可の有無にかかわらず最終Product設計として採用しない。

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

- TASK-001: `DEV-4 FOUNDATION CRITICAL` / score 25 / COMPLETED
- TASK-002: `DEV-4 FOUNDATION CRITICAL` / score 22 / COMPLETED
- TASK-003: `DEV-4 FOUNDATION CRITICAL` / score 33 / COMPLETED
- TASK-004: `DEV-4 FOUNDATION CRITICAL` / score 25 / completed on package 0.4.10 with accepted target behavioral Evidence and `255 / 255` native-Windows regression PASS

TASK-004はTimebaseだけでなく、ComfyUI画像/動画生成、Character Identity、MiniMax H3 Production Brief/SingleFrame/Spectrum/Foley、Audacity OpenVINO外部Runtime境界を含むためSafety Floorを下げない。

## Security / Privacy Constraints

- Secret値をManifest、prompt、log、evidenceへ保存しない。
- Product Path ResolverはAllowlist外Pathを拒否する。
- External inputから任意Shell/Pythonを直接実行しない。
- PII、Voice Model、Rights metadataはSensitivity/Retentionを定義する。
- External providerはlocal/private endpoint、explicit authorization、request-bound idempotency、output containmentを満たす。
- 外部GPL実装（Audacity OpenVINO / Spectrum等）はBAI CoreへコピーせずRuntime境界で扱う。

## Current Consumer Task State

- Last Completed: `TASK-004 — Media Normalization + Local Visual/Audio AI Runtime Foundation`
- Active Task: `TASK-006 — ASR / Transcript / Subtitle`
- TASK-004: `COMPLETED`
- Package: `0.13.0`
- Local verification: `250 / 250 PASS`, compileall PASS; capability Evidence accepted; Windows timestamp, binary-I/O and ffprobe discovery correctives covered
- Target-machine Gate: synthetic OpenVINO Noise Suppression + 2-stem Music Separation behavioral Evidence + final DEV-4 Judge review
- Project Roadmap: `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md` Ver.1.4
- TASK-022: `COMPLETED`; package 0.5.0 native-Windows regression `263 / 263 PASS` and compileall PASS
- AI routing: package 0.6.2 native-Windows `293 / 293 PASS`; TASK-028 package 0.6.3 uses exact model capabilities rather than provider-purpose locking; GUI settings and remaining adapters are subsequent slices
- OSS readiness: package 0.6.4 adds public documentation, governance/community health files, cross-platform CI, dependency/secret scanning, packaging metadata and evidence-based impact guidance; the Repository is now public and hosted CI remains the final external gate
- Repository URL corrective: package 0.6.5 binds all public metadata and GitHub community links to `https://github.com/baisound/bai_video_production`; the first push and Security workflow succeeded
- CI corrective: package 0.6.6 provisions FFmpeg/ffprobe on every Ubuntu and Windows matrix runner before executing the media-dependent regression suite
- Python 3.11 CI corrective: package 0.6.7 replaces process-global OS mutation with explicit Audacity path-platform injection; five other matrix jobs already passed
- OSS adoption: package 0.7.0 adds truthful architecture/roadmap visuals, five-minute offline demo, guarded release/PyPI automation and Evidence gates for real video pilots, early adopters and contributors
- Connection settings: package 0.8.0 adds a secret-free five-workload preflight projection for the future low-literacy GUI; persistence and interactive UI have dated completion gates
- Settings persistence: package 0.9.0 adds atomic checksummed storage, revision-conflict protection, 0.8 migration and a bilingual GUI-neutral form; interactive UI remains due 2026-08-24
- Interactive settings: package 0.10.0 adds a loopback-only bilingual screen for five workload modes and preferred configured Models; native Windows screenshot and usability Evidence remain
- Native settings Evidence: package 0.10.0 Windows save/reload and stale revision 3 versus saved revision 4 conflict behavior accepted; multi-user usability review remains
- Catalog editor: package 0.11.0 adds safe Provider/Model candidate add/edit/disable with truthful implementation status and no Provider execution path
- Native Catalog Evidence: package 0.11.0 add/edit/disable behavior accepted on Windows
- Credential onboarding: package 0.12.2 links enabled credential-required Catalog candidates to active key rows, retains disabled-route keys in an explicit cleanup section, prevents orphaning, and provides per-Route password-manager lookup; Provider connectivity is not executed
- Native Credential Evidence: package 0.12.2 Catalog linkage, retained-key cleanup and per-row Password Manager behavior accepted on Windows
- Subtitle foundation: package 0.13.0 adds provider-neutral Transcript and Subtitle contracts, cut-aware exact frame mapping and deterministic SRT; real ASR and Resolve placement remain subsequent slices
- New-production route: `TASK-027 PROPOSED / NOT AUTHORIZED`; GUI intent → AI production proposal/revision → explicit GO → generated/supplied replaceable Asset slots → automated Resolve assembly
- OS-internal TASK-016 remains unrelated and untouched.

## Completion Rule

Taskは、選択DEV Profileの要求、実装、必要Test、blocking finding解消、内部文書同期、Completion Evidenceが揃った場合のみ完了する。

Local Test PASSやCapability PASSを、まだ未実施のBehavioral EvidenceまたはOwner Authorization for later TASKへ読み替えない。
