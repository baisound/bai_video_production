# TASK-052 R9 Windows Packaged Acceptance Report

Date: `2026-08-21 JST`

Status: `AVAILABLE-SCOPE PASS / REAL-VIDEO AND HUMAN-GOLD DATA GATE`

## Scope and authority

The Owner authorized a real Windows build, launch and bounded operation of the
packaged Training Studio. This run did not call a Provider, purchase credits,
upload media, confirm training data, apply a migration, delete Owner data, or
perform release/deploy/Production Activation.

## Exact artifact

- command: `Python 3.12.4 -m PyInstaller --clean --noconfirm packaging/task049_training_studio.spec`
- PyInstaller: `6.22.0`
- artifact: `dist/BAI DbD Training Studio/BAI DbD Training Studio.exe`
- size: `15,098,447 bytes`
- SHA-256: `45ACB23BC17B1EA2A6BADEC99A8B037541D0021CF352F102948230971D35ED06`
- clean launch to accessible main window: `12,162 ms`
- startup exception: `NONE`

## Observed packaged workflows

| Workflow | Expected | Observed | Result |
|---|---|---|---|
| Startup/inventory | no prior `unhashable type: 'dict'` failure | main window opened; `1614 / 1614` records | PASS |
| Japanese search | bounded filtered inventory | `発電機` produced `231 / 1614` | PASS |
| HUD calibration | positive/negative effect regions available | both bottom-right positive and negative region choices visible | PASS |
| Image learning | video and Teacher controls render | both control groups visible and responsive | PASS |
| Unified review | current workspace counts remain readable | Game/Alias `1699`, crop `16`, notification `2`, commentary `1`, Human Gold/other `0`, total `1718` | PASS |
| Backup/restore screen | included/excluded scope is explicit | training workspace/global trivia included; credentials/private keys excluded | PASS |
| Map rotation | visible pixels rotate and orientation persists | cached `アザロフの休憩所` `PNG / PIL_BYTES` rendered at `0/90/180/270`; `90` persisted after reopen; final `0` persisted after EXE restart | PASS |
| Owner data restoration | temporary acceptance mutation is reversible | map orientation restored to its original `0°` and app closed | PASS |

The map acceptance exercised actual decoded pixels, not only a label or metadata
value. No packaged screenshots are committed because they can expose Owner-local
workspace content; the action/result receipt above is the retained repository
Evidence.

## Windows filesystem verification

The native Windows Python suite executed:

```text
tests/test_task049_dbd_data_migration.py
tests/test_task050_r6_backup_workspace_boundary.py
tests/test_task052_packaged_startup_failure_fix.py
8 passed in 1.25s
```

This verifies checksum-bound backup, separate-root restore, conflict/safety
backup, credential exclusion and the workspace boundary on real Windows
filesystem semantics. It does not claim that the Owner's live workspace was
backed up or migrated during this run.

## Human Gold and performance gate

R8 now requires real `media://` sources, `rights://` provenance, `human://`
labeler provenance, split isolation, complete required domains, validator
provenance and minimum quality thresholds before an explicitly authorized
production-accuracy claim can pass. Authority/credential/secret references are
rejected. The current workspace has no complete 5–10 match Human Gold corpus.

The following therefore remain `NOT_CONFIRMED` rather than being fabricated:

- real recorded-video analysis across multiple Killers, resolutions,
  compression levels and supported UI scales;
- the `発電機 残0` batch-registration performance/process-storm flow, because no
  authorized matching real video was available;
- packaged APPROVE/CORRECT/REJECT Gold operation against a complete real corpus;
- production recognition accuracy.

## Decision

The exact EXE build, startup, bounded navigation, Windows backup/restore contract
and available cached-map pixel rotation are `PASS`. TASK-052 implementation is
complete through R9 for available local Evidence. Closure remains gated only by
Owner-supplied/authorized real-video Human Gold data and the operations that
necessarily consume it; no production accuracy claim is made.

Final repository integration regression: `3106 passed / 2 platform-specific
skipped` in `102.26 s`; unresolved Critical/High review findings: `0 / 0`.
