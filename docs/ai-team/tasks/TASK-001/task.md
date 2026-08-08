# TASK-001 — Project Foundation / Domain Model

> Historical Alias: `VIDEO-TASK-001`

## Metadata

- Record Type: Task Definition
- Drafted By: Orchestrator
- Approved By: Owner
- Active Project: `ai-video-production`
- Project Root: `/home/baisound/projects/ai-video-production`
- Task ID: `TASK-001`
- Historical Alias: `VIDEO-TASK-001`
- Status: `ACTIVE`
- Current Phase: `DESIGN`
- Design Authorization: `AUTHORIZED`
- Implementation Authorization: `NOT_AUTHORIZED`
- Governance Profile: `DEV-3 HIGH ASSURANCE`
- Lifecycle Mode at Bootstrap: `DOCUMENT_GOVERNED_LEVEL_A`

## Objective

AI動画制作自動化システムの全後続Taskが依存するProject FoundationとProduct Domain Contractを、後続実装が追加の暗黙判断を必要としない水準まで確定し、DEV-3のDesign ReviewとAuthorizationを経て実装可能なFinal Planへ統合する。

## Background

既存Product Design Ver.0.6には、Asset、Production Job、Manifest、Timeline Mapping、Candidate Clip Graph、Resolve/Premiere連携、AI生成、Evidence等の詳細設計がある。

一方、開発Governance基盤はBAI Development OS 1.0.0 / Architecture Ver.2.27へ更新された。従って、旧AI Development OSのRole/Lifecycle/RegistryをConsumer側へ複製せず、BAI OSとProduct Domainを明確に分離したFoundationを確定する必要がある。

## Scope

### In Scope

1. Consumer Project directory/responsibility boundary
2. `.bai-os/project.json`の最終化
3. Product ID体系と不変性
4. Production Job State Machineと遷移契約
5. Canonical Manifest Envelope
6. Schema Version / compatibility / migration policy
7. Asset Registry minimum contract
8. Logical URI / Path Resolver contract
9. Atomic Write / Checksum / Idempotency contract
10. Product Error Envelope
11. Product Evidence / Checkpoint / Operation Record
12. Automation-owned / Human-owned / Shared ownership contract
13. Profile Snapshot / Product Profile Plugin boundary
14. Core / Worker / Adapter / Gateway dependency rules
15. Secret / PII / Rights / Voice Model data classification contract
16. External Skill / Reference Code intake boundary
17. Unit / Contract / Integration / Golden Fixture strategy
18. BAI Development OSとProduct Domainの責任分離
19. TASK-001でLevel B Runtime Assistedを導入するかの設計判断
20. 後続Taskが依存するPublic Product Contract一覧

### Out of Scope

- FFmpeg実素材変換
- VFR/CFR正規化実装
- Scene/VAD/ASR/WhisperX/話者分離/字幕生成
- Candidate Clip Graph最適化実装
- DaVinci Resolve実機API操作
- Premiere FCP7 XML出力実装
- AI SE/BGM/Video/TTS実装
- DBD Profile実装
- Product UI/Dashboard
- YouTube/TikTok等への公開処理
- BAI Development OS Coreの変更
- DistributedOSの有効化
- TASK-016未実装機能への依存

## Canonical / Required Inputs

### Development Governance Canonical

1. `/home/baisound/bai-development-os/registry/current-state.md`
2. `/home/baisound/bai-development-os/registry/ai-context-pack.md`
3. `/home/baisound/bai-development-os/registry/context-loading-rules.md`
4. `/home/baisound/bai-development-os/PROJECT.md`
5. BAI Development OS package 1.0.0 / Architecture Ver.2.27 current documentation

### Consumer Canonical

6. `/home/baisound/projects/ai-video-production/PROJECT.md`
7. `/home/baisound/projects/ai-video-production/.bai-os/project.json`
8. 本`task.md`

### Product Design Baseline

9. `AI動画制作自動化システム 基本・詳細統合設計書 Ver.0.6 外部SKILL統合版`

### Reference Only

10. 旧`VIDEO-TASK-001 正式起票パック Ver.1.0`
11. 旧AI Development OS Ver.1.3 Alpha / 差分設計書 Ver.2.1 Alpha
12. External Skill / corrected reference code

Referenceはcurrent BAI Development Governanceを上書きしない。

## DEV-3 Required Design Topics

Builderは少なくとも以下を詳細設計する。

### D-001 Project Boundary
- OS CoreとConsumerを分離
- Product RuntimeとDevelopment Toolingを分離
- allowed/protected paths

### D-002 Identifier Contract
最低限:
- Project ID
- Production Job ID
- Asset ID
- Segment ID
- Candidate ID
- Manifest ID
- Operation ID
- Evidence ID
- Checkpoint ID
- Profile Snapshot ID
- Schema ID / Version

各IDのformat、generation owner、uniqueness scope、immutability、validation、migrationを定義する。

### D-003 Production Job State Machine
- state list
- legal transition table
- entry/exit condition
- failure/retry/resume
- illegal transition
- optimistic concurrency/revision
- Product Job Serviceだけがmutationを行う

BAI LifecycleOSのTask Status/Phase/Gate/Authorizationと混同しない。

### D-004 Canonical Manifest Envelope
最低限:
- schema_id / schema_version
- manifest_id
- production_job_id
- created_at / producer
- source refs
- profile_snapshot_id
- content_checksum
- operation/idempotency reference
- payload

Secret値と環境依存raw pathをcanonical payloadへ保存しない。

### D-005 Schema Versioning
- semantic/version policy
- reader/writer compatibility
- unknown field
- migration responsibility
- breaking-change gate
- deprecation
- validation errors

### D-006 Asset Registry
- asset type
- owner
- rights
- checksum/fingerprint
- Logical URI
- media metadata
- generation provenance
- Human Lock
- retention class
- evidence refs

### D-007 Logical URI / Path Resolver
- Windows/WSL2/Object Storage mapping
- allowlist
- traversal/symlink escape
- unresolved path fail-closed
- execution-location ownership

### D-008 Integrity / Atomic Write
- temp write
- flush/fsync policy
- checksum
- atomic replace
- cross-filesystem fallback
- concurrent mutation/revision
- audit history

### D-009 Product Error Envelope
最低限分類:
- VALIDATION
- AUTHORIZATION
- NOT_SUPPORTED
- TRANSIENT
- RESOURCE_EXHAUSTED
- TIMEOUT
- EXTERNAL_DEPENDENCY
- DATA_INTEGRITY
- HUMAN_REVIEW_REQUIRED
- INTERNAL

ただしProduct AuthorizationとBAI Development Authorizationを区別する。

### D-010 Evidence / Checkpoint
- Product runtime evidence schema
- checkpoint unit
- input/output checksum
- component/model/version
- stdout/stderr扱い
- PII/secret masking
- retention

BAI Task Evidenceとはidentity namespaceを分離する。

### D-011 Ownership / Lock / Conflict
- AUTO_ASSEMBLY automation-owned
- EDITOR_WORK / FINAL_MASTER human-owned
- lock / revision / expected version
- conflict fail-closed

### D-012 Product Profile / Plugin Boundary
- Product Profile config
- DBD等のProfile Plugin
- capability/version/input/output/failure
- Core Schema/Job Stateへの直接mutation禁止

BAI ExtensionOSをProduct Plugin Runtimeへ自動流用しない。将来統合は別Task。

### D-013 Dependency Rules
最低限禁止:
- Worker → Product Job State direct mutation
- Candidate Engine → NLE direct operation
- Resolve Controller → AI Provider direct call
- Output Adapter → untracked Canonical Edit Plan mutation
- Storage Manager → LEGAL_HOLD/HUMAN_OWNED delete
- Plugin → Core DB schema direct mutation

### D-014 Security / Threat Model
- secret boundary
- path boundary
- arbitrary execution prevention
- PII / rights / voice model sensitivity
- Product runtime security vs BAI SecurityOS boundary

### D-015 External Skill Intake
- original/corrected version
- license declaration
- checksum
- static/runtime review
- adopted code / rewritten code / reference-only distinction

### D-016 Testability
最低限:
- ID validator unit
- state transition table
- JSON Schema contract
- old/new/unknown version
- atomic-write failure injection
- path traversal/symlink/allowlist
- ownership conflict
- idempotency duplicate
- error serialization
- checkpoint resume
- Golden Fixture versioning

### D-017 BAI OS Integration Decision
TASK-001 Final Planまでに以下を決定する。

- Level A継続かLevel Bへ移行か
- Level Bなら使用するBAI API/subpath
- BAI packageをProduct runtimeに入れずdevDependency/toolingへ限定できるか
- LifecycleStore導入範囲
- Context/Cost/Model/Security/Integrationの導入タイミング

## Constraints

- BAI Development OS CoreをConsumerへコピー/変更しない。
- OS upgradeとProduct featureを同一Taskへ混ぜない。
- DistributedOSは有効化しない。
- TASK-016機能を利用可能と仮定しない。
- Product Design Ver.0.6の意味を、Governance都合で勝手に変更しない。
- Scope外変更が必要ならDesign Gateへ戻る。
- Test PASS、Critic PASS、Judge recommendationをOwner Authorizationと誤認しない。

## Required Artifacts

起票時点では本Task Definition、Development Profile、Context Loading Planのみ。

DEV-3進行に応じて必要なArtifactをRoleが生成する。

- detailed design / builder-proposal
- critic design review
- builder response
- judge decision when gate requires
- final-plan
- final-plan consistency evidence
- implementation authorization evidence
- implementation report
- independent test report
- implementation review
- fix/retest if needed
- final judgment
- completion record / TASK-001.summary.md

空Artifactを先行作成しない。

## Acceptance Criteria — Design

- Product/BAI OS boundaryが一意である。
- Critical/High design finding = 0、またはOwnerが明示的に扱いを決定している。
- Product State Machine、Manifest、ID、Path、Integrity、Ownership、Error、Evidenceのcontractが実装可能な粒度で確定している。
- Level A/Bの採用判断と根拠が確定している。
- Scope/allowed/protected pathsが確定している。
- Test Matrixとrollback/recovery strategyが確定している。
- Final Planに未決定プレースホルダーが残っていない。
- Implementation Authorizationが独立したEvidenceとして成立するまで実装を開始しない。

## Acceptance Criteria — Implementation

Design/Authorization後にのみ適用。

- Final Planどおりのfoundation/schema/product contract codeが実装される。
- DEV-3 required testsがPASSする。
- Independent Testerがobserved evidenceを記録する。
- Blocking Critic finding = 0。
- Project/internal docs syncが完了する。
- Closure readinessが成立する。

## Stop Conditions

- BAI Development OS Core変更が必要
- Security/Authorization boundaryが想定より拡大
- Product StateとBAI Lifecycleを一意に分離できない
- 実機検証なしではContractを確定できず、別Taskへ切り出す必要がある
- Required Evidenceが観測不能
- DEV-4 Safety Floor条件が発生
- Scope外の外部side effectが必要

## Next Role

`Builder — DEV-3 Detailed Design`

Builderは実装を開始しない。
