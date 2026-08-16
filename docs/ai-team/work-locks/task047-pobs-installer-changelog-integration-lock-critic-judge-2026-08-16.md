# TASK-047 P-OBS installer CHANGELOG Integration Lock hosting Evidence

## Outcome

TASK-047/P-OBS installer candidate PR #119 の実装7 fileを不変に保ったまま、
CIが要求するCHANGELOG 1行だけを別ownershipで統合する短期Lockを提案する。
本transactionはLock hostingだけであり、CHANGELOG、target PR、Plugin、installer、OBS、
録音、Dataset、Training、Production、ReleaseまたはDeployを変更しない。

## Fresh prestate

- base / origin main: `17ea08eb30cb7e728a2795fde66d26d54693e53d`
- Registry revision: `13 -> 14`
- Registry audit base: exact pre-host main
- target PR: `#119`, OPEN / Draft / MERGEABLE
- expected target head: `7450534b97bf1ad04f816aeeb19b4abfc3d85a5a`
- target changed paths: exact 7
- non-CHANGELOG hosted checks: running; only known early failure is
  `changelog-and-version`
- active Integration Lock before this transaction: `0`
- active implementation Lock overlap: `0`
- hosting changed paths: exact 2

## Exact hosting scope

1. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
2. `docs/ai-team/work-locks/task047-pobs-installer-changelog-integration-lock-critic-judge-2026-08-16.md`

Registry root changes are limited to revision `14`, fresh audit base and one ACTIVE
Integration Lock append. Existing Locks, history, roadmap, merge order and global policy
remain byte-semantically unchanged.

## Approved target composition

Approved CHANGELOG bullet:

> - Added TASK-047 P-OBS a bilingual local Windows installer candidate for BAI Voice Capture with selectable OBS 32.2.1 target, fail-closed process/version/path/reparse/disk/collision checks, exact3 backup/journal/read-back, Repair/Update/Uninstall recovery, reproducible Inno Setup build and beginner-friendly Japanese/English guidance from installation through destination, gain check, visible recording, stop and result verification. The candidate is unsigned and local-only; Owner voice recording, Dataset/Training/Production, Release and Deploy remain separate.

Final target composition must be the immutable 7 implementation files plus this one
physical CHANGELOG line. Baseline blobs at head `7450534...`:

| Path | Blob |
|---|---|
| `docs/ai-team/tasks/TASK-047/p-obs-installer-dev9-evidence-2026-08-16.md` | `421043e312500f72700df492e876ca95a135d108` |
| `docs/ai-team/tasks/TASK-047/task.md` | `8ca62f9e06a2e1309c683892e2d84fffef0840b6` |
| `docs/user/OBS-VOICE-CAPTURE-PLUGIN.md` | `7719599a0a0f704d27725ef93388fbdde86614ca` |
| `packaging/task047_obs_voice_capture_installer.iss` | `d80ec47e2974312a40ad7001d179aa78740afa7b` |
| `tests/test_task047_obs_installer_contract.py` | `595849d679b97ab6dc65f72e7afc25d4baae24df` |
| `tools/windows/build-task047-obs-installer.ps1` | `0c455406053a7a2c64c46507f75ff384f62a0885` |
| `tools/windows/test-task047-obs-installer.ps1` | `3b230d908c321bd317423ff173cf387312cc7c5c` |

## Required sequence

1. Host this exact2 Lock unit and obtain all hosted checks terminal SUCCESS.
2. Merge the Lock PR; read Registry revision 14 and ACTIVE record from canonical main.
3. Require post-merge CI and Security SUCCESS.
4. Re-audit main, Registry, target head, target worktree and overlap.
5. Merge fresh main normally into the target branch; no rebase or force.
6. Require conflict 0 and prove 7/7 baseline blobs unchanged.
7. Add the approved CHANGELOG bullet as a separate one-file Japanese commit.
8. Push normally; require final target diff exact 8 and fresh 9/9 SUCCESS.
9. Merge the target only after exact preflight; require post-merge CI/Security SUCCESS.
10. Close this Lock in a separate exact governance transaction and verify canonical main.

Main/target/Registry drift, conflict, unexpected path, blob mismatch, check non-success or
UNKNOWN stops the shared effect. There is no automatic retry, rollback, revert, reset,
force-push or workflow exception.

## Critic self-pass 1

Finding: direct CHANGELOG edit would violate target ownership and permit concurrent shared
file writers. Correction: exact one-file Integration Lock, exact2 host unit and serialized
main-into-target sequence were separated from implementation authority.

Finding: a textual file list alone would not prevent implementation drift. Correction:
all seven baseline blob IDs and the exact pre-integration head are fixed.

## Critic self-pass 2 / Judge

- Registry/source revision mismatch: 0
- active Integration Lock collision: 0
- target/open PR path overlap: 0
- implementation authority inflation: 0
- Plugin/OBS/recording/effect authority inflation: 0
- unresolved Critical/High/Medium: `0 / 0 / 0`

Judge: `PASS_EXACT2_LOCK_HOST_DRAFT_PR_READY`.
