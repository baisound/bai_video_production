# TASK-047 P-OBS Release installer Integration Lock closure Evidence

## Outcome

PR #123でhostした短期Integration Lockは、PR #125でRelease workflow、CHANGELOG、
日英README、hash固定したinstaller/runtime/source一式とcontract testがcanonical mergeされ、
target post-merge CI/SecurityもSUCCESSとなったため`HOSTED_CLOSED_RELEASED`へ移す。

## Exact receipts

- closure base/main: `f7f55ec3f14842452a71a564b21b718ef282a830`
- Registry: `17 -> 18`
- Lock host PR/head/merge: `#123` / `e41b9fcb410ad181d278ed0397e7cd4d0801a45e` / `034c986eee90433d72cfc47a03ac7d6ac25c2d4b`
- Lock host checks: pre-merge `9 / 9 PASS`
- Lock host post-merge CI/Security: `31938259077 / 31938259076`, SUCCESS
- target PR/base/head/merge: `#125` / `5d9e18a59a08923e917f846505136fb09ebf52ad` / `eef852526bfb983a5e1826a44b2c8939014eb241` / `f7f55ec3f14842452a71a564b21b718ef282a830`
- target first-parent diff: exact 10
- installer/runtime/source SHA-256: `3 / 3 PASS`
- Japanese/English README build guide and beginner-guide route: `PASS`
- focused/Windows/WSL2: `4 PASS` / `1273 PASS, 1 SKIP` / `1274 PASS`
- target pre-merge CI/Release metadata/Security: `31938813518 / 31938813498 / 31938813482`
- target post-merge CI/Security: `31938971179 / 31938971144`, SUCCESS

## Closure invariants

- original Lock identity, ownership, base, target, allowed/denied scope, task-owned files,
  prerequisites and failure policy are preserved;
- the ACTIVE record leaves `locks` and the complete append-only receipt enters
  `integration_lock_history` exactly once;
- all unrelated Locks/history, roadmap, merge order and global policy are unchanged;
- closure authorizes no Tag, GitHub Release, Deploy, OBS, capture, recording, Dataset,
  Training, Production or Owner voice effect;
- branch/worktree cleanup is separate and only after merged-tip/clean/no-active-Lock proof.

## Critic self-pass 1

Finding: Release assets could be merged while leaving the shared `.github/**` slot ACTIVE.
Correction: close and release the exact Lock in the same Registry transaction after exact
post-merge read-back.

## Critic self-pass 2 / Judge

- receipt/run/head mismatch: 0
- asset or README drift: 0
- Release workflow omission path: 0
- unrelated Registry/root/policy mutation: 0
- Tag/Release/Deploy authority inflation: 0
- unresolved Critical/High/Medium: `0 / 0 / 0`

Judge: `PASS_EXACT2_INTEGRATION_LOCK_CLOSURE_DRAFT_PR_READY`.
