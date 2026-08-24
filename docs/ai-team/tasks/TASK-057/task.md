# TASK-057 Windows Snapshot Lock Initialization Race Hardening

- Status: `R0 IMPLEMENTED LOCAL HOSTING PENDING`
- Owner: 開発担当
- Trigger: TASK-019 lock-host PR #293 Windows 3.12 hosted CI
- Dependency: existing TASK-037 `production_control_store._exclusive_snapshot_lock`
- Governance: DEV-4 because the shared cross-process CAS lock is used by multiple Product applications

## Objective

既存snapshot lock fileが空の初回に複数Windows callerが同時進入した場合、byte初期化の`write/flush`がexclusive lock取得前に競合して`PermissionError`になるraceを除去する。

## R0 scope

- OS lock取得後のexclusive region内でのみempty lock byteを初期化する。
- Windows `msvcrt.locking`がempty fileのbyte rangeをlock可能である実機probeを前提Evidenceとして保持する。
- POSIX `flock`、CAS check、atomic replace、symlink/regular-file拒否、lock releaseを変更しない。
- fresh empty lockへの8-thread同時進入と8回の4-thread反復raceを検証する。

## Boundaries

- TASK-037のSnapshot/Registry schemaとProduct責任は変更しない。
- lock path、retry policy、timeout、file deletion、data migrationを変更しない。
- Workflow、Provider、media、Timeline/Resolve、Release/Deploy authorityを変更しない。
