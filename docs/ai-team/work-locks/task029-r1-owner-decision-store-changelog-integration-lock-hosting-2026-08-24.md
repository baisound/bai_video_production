# TASK-029 R1 CHANGELOG Integration Lock Hosting

Date: `2026-08-24`

Unit: `TASK-029/R1-OWNER-DECISION-STORE-CHANGELOG-LOCK-HOSTING`

Authority: `OWNER_EXPLICIT_AUTONOMY_NO_CONFIRMATION_REQUIRED_20260824`

Status: `PENDING_HOST_PR`

## Target identity

- target PR: `#289`
- target branch: `codex/task-029-r1-owner-decision-store`
- exact target head: `ba4b7830ecae8b9d5bb917839c7ce2a57f585b49`
- fresh main: `e41156b6394ded4f36261a3eda41348fd9a2c4fe`
- immutable target paths: `7`
- hosted checks: `8 / 9 PASS`; only `changelog-and-version` FAIL
- registry revision: `57 -> 58`
- nonclosed integration locks before proposal: `0`
- nonclosed integration locks after proposal: exactly `1`

## Reserved effect

Only this exact line may be added after this lock is hosted and post-main green:

> - TASK-029 R1として、R0のREADY_FOR_HUMAN_REVIEW Candidateに対する明示Human ADOPT/REJECTを、Windows Current User DPAPI既定の暗号化append-only Owner Decision Storeへ接続しました。disk envelopeへOwner scope・Candidate・理由コードを平文保存せず、CAS、chain/replay/scope、restart read-back、wrong-key/tamper/symlink/power-lossをfail-closedにしました。Profile write、Knowledge Pack promotion、Cloud telemetry、rollback、plaintext export、physical delete、Timeline/Resolve、Release/Deploy権限は付与しません。

The target composition is the exact 7 immutable paths plus one integration-owned `CHANGELOG.md` effect. This lock-host changes only this Evidence and `ACTIVE-WORK-LOCKS.json`.

## Verification and boundary

- local full BVP suite: `3655 PASS / 5 SKIP / 0 FAIL`
- focused TASK-029 R0/R1: `27 PASS`, including real Windows DPAPI synthetic round-trip
- TASK-019/store/atomic direct regression: `22 PASS`
- schema mirror / compileall / diff-check: PASS
- no install, model, Provider, private data, Profile write, Pack promotion, Cloud, Timeline/Resolve, Release or Deploy effect
