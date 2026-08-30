# TASK-029 R9B CHANGELOG Integration Lock Hosting

Date: 2026-08-26

Unit: TASK-029/R9B-OWNER-SIGNING-KEY-CUSTODY-CHANGELOG-LOCK-HOSTING

Authority: OWNER_EXPLICIT_TASK029_R9_SIGNATURE_AND_KEY_APPROVAL_20260826

Status: PENDING_HOST_PR

## Target identity

- target PR: #353
- target branch: codex/task-029-r9b-owner-key-custody
- exact target head: e8f9d11f263cd0be1c769422ac6e8a5d19e3f2fe
- fresh main: 85ddb70601898046826f869a9a9a1f2856ebdfb3
- immutable target paths: 8
- target hosted checks: 8 / 9 PASS; only changelog-and-version FAIL
- focused R9B: 13 PASS
- R8/R9A/R9B direct: 26 PASS
- TASK-029 regression: 94 PASS
- full Product regression: 3865 PASS / 6 SKIP / 0 FAIL
- registry revision: 86 -> 87
- nonclosed integration locks before proposal: 0
- nonclosed integration locks after proposal: exactly 1
- open pull requests: 17
- other open PR overlap with CHANGELOG.md or ACTIVE-WORK-LOCKS.json: 0

## Reserved effect

Only this exact line may be added after this lock-host is merged to main, read back exactly, and its post-main CI and Security are green:

> - TASK-029 R9Bとして、明示Human確認をexact custody/Owner scope/public-key IDへ束縛し、raw Ed25519 seedをWindows Current User DPAPIで一回限り暗号化保管するOwner signing-key custodyとbody-free receiptを追加しました。sign/export/replace/rotate、PuTTY PPK変換、real signing、Knowledge Pack write/promotion、Release/Deploy/Production authorityは生成しません。

The target composition is eight immutable TASK-029 R9B task/design/runbook/schema/source/test paths plus one integration-owned CHANGELOG.md effect. This lock-host changes only this Evidence document and ACTIVE-WORK-LOCKS.json.

Immutable pre-integration blob identities:

| Path | Blob |
|---|---|
| docs/ai-team/tasks/TASK-029/task.md | b93c2c93e381f64515ff7268b275a0a027078c10 |
| docs/ai-team/tasks/TASK-029/owner-signing-key-custody-r9b-design-critic-judge.md | e259ddbffdc49c303e07ddb08560896790c28f2d |
| docs/ai-team/tasks/TASK-029/r9b-puttygen-key-creation-and-custody-configuration-runbook-pre-execution.md | dbd205bea3761edab2874111400a79f3293485d7 |
| docs/ai-team/tasks/TASK-029/r9b-puttygen-key-creation-and-custody-native-execution-result.md | 8db560ba0180820f125b1042c8edf6f18ca5de91 |
| schemas/owner-signing-key-custody-store.schema.json | 22840a24dfae97a2a62a99b24e56971d4f784613 |
| src/ai_video_production/owner_signing_key_custody.py | c345396ebd5c226f6f1311f1184fb885c863dced |
| src/ai_video_production/schema_resources/owner-signing-key-custody-store.schema.json | 22840a24dfae97a2a62a99b24e56971d4f784613 |
| tests/test_task029_owner_signing_key_custody.py | b73126831b7449a5e162ac863d5312d92063c7c5 |

## Verification and boundary

- PR #353 exact head read-back: PASS
- PR #353 mergeable Draft read-back: PASS
- all eight non-CHANGELOG hosted checks: PASS
- dependency-audit and secret-scan: PASS
- fresh-main exact8 blob drift: 0 / 8
- schema mirror byte identity: PASS
- local focused/direct/TASK/full regression: PASS
- unresolved DEV-4 Critical/High/Medium findings: 0 / 0 / 0
- independent hosted CI matrix: PASS
- no real Owner key, PPK, passphrase, import, signing, or private export
- no Knowledge Pack write/promotion, Timeline/Resolve, provider, Release, Deploy, or Production effect

## Judge

ACCEPT_LOCK_PROPOSAL_PENDING_HOST_MAIN_READBACK.

The lock becomes authoritative only after this exact two-file proposal is merged to main and read back. Any main, registry, target-head, blob, or overlap drift expires the transaction. No retry, force update, workflow weakening, secret-bearing native action, Release, Deploy, or Production effect is authorized.
