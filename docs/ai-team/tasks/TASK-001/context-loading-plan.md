# TASK-001 Context Loading Plan

## Purpose

BAI Development OSのContext Economy / Summary-first原則に従い、毎Roleで巨大な設計書と全OS資料を読み直さない。

## Mandatory First Read

1. `/home/baisound/bai-development-os/registry/current-state.md`
2. `/home/baisound/bai-development-os/registry/ai-context-pack.md`
3. `/home/baisound/bai-development-os/registry/context-loading-rules.md`
4. `/home/baisound/bai-development-os/PROJECT.md`
5. Consumer `PROJECT.md`
6. Consumer `.bai-os/project.json`
7. `docs/ai-team/tasks/TASK-001/task.md`
8. `development-profile.md`

## Product Design Read Strategy

`AI動画制作自動化システム Ver.0.6`は全文を毎回読まない。

TASK-001の設計対象に必要な章のみ:
- Project/Architecture boundary
- Job State
- Manifest/Schema
- Asset Registry
- Timeline/Path
- Error/Evidence/Checkpoint
- Ownership
- Profile/Plugin
- Security
- External Skill integration
- Test/Deployment foundation

## Read on Demand

- BAI Lifecycle details: Level B/LifecycleStore判断時のみ
- BAI Security/Integration: Secret/Egress/tooling判断時のみ
- BAI Cost/Model: external AI development tooling判断時のみ
- ExtensionOS: Product plugin統合を検討するときのみ
- DistributedOS: TASK-001では読まない

## Prohibited Context Expansion

- TASK-004〜015の全Detailed Design全文
- BAI Architecture全文の常時読込
- 全Public API 690 exportの無目的読込
- 旧AI Development OS全履歴
- 完了済みTask全Evidence

## Conflict Rule

同一identityのcurrent canonicalとreferenceで矛盾した場合、referenceを混ぜて平均化しない。current canonicalをAuthorityとして扱い、Product requirementとの衝突はDecision Itemとして記録する。
