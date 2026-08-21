# TASK-036 P-UX-2H H-B CHANGELOG Integration Lock Hosting Evidence

Date: 2026-08-21
State: PENDING_LOCK_HOST_PR

## Purpose

This docs-only proposal hosts one exact shared-path reservation for the
CHANGELOG effect required by TASK-036 P-UX-2H H-B pull request 243.

It does not modify the target implementation, grant Audio authority, start a
Provider or native execution, or authorize release/deploy.

## Fresh-main identity

- repository: `baisound/bai_video_production`
- hosting branch: `codex/task-036-pux2h-hb-changelog-lock-hosting`
- hosting base / audit base: `1abdc2fa80797915e4dbc5dbc573dc6bc75711f6`
- registry revision: `34 -> 35`
- open pull requests at proposal time: target PR 243 only
- CHANGELOG or registry overlap from another open PR: `0`
- intervening PR 242 changed TASK-054/current-state paths only and has no
  target, CHANGELOG or registry overlap

## Target identity

- target PR: 243
- target branch: `codex/task-036-pux2h-hb-shell-placement`
- expected pre-integration head: `ba2f33210b2cf66cbe59c32335e1a39eb3e78d35`
- target hosted state: `PENDING`
- immutable target path count: `14`

Immutable target paths:

1. `docs/ai-team/tasks/TASK-036/p-ux-2h-locked-visual-asset-edit-placement-design-2026-08-21.md`
2. `src/ai_video_production/final_review_readiness.py`
3. `src/ai_video_production/interactive_timeline_application.py`
4. `src/ai_video_production/task036_shell_ui.py`
5. `src/ai_video_production/task036_shell_v611.py`
6. `src/ai_video_production/task036_trusted_launcher.py`
7. `src/ai_video_production/task036_visual_asset_placement.py`
8. `src/ai_video_production/task044_nle_shell.py`
9. `tests/test_task036_final_review_readiness.py`
10. `tests/test_task036_trusted_launcher.py`
11. `tests/test_task036_v611_visual_contract.py`
12. `tests/test_task036_visual_asset_placement.py`
13. `tests/test_task044_nle_shell_ui.py`
14. `tests/test_task044_timeline_edit_history.py`

## Exact allowed effect

Allowed target file:

- `CHANGELOG.md`

Approved exact bullet:

> - TASK-036 P-UX-2H H-Bとして、Human LOCK済みのcanonical IMAGE AssetをTASK-044 TimelineへINSERT/REPLACEするplacement-only Shell/UIを追加し、Production/Candidate/Asset currentnessをapply・redo・ProjectSave回復時に再検証し、stale配置/回復待ちをFinal Review blockerへ接続しました。rights approval、Provider/native、Candidate ACCEPT/LOCK、Resolve、Export、公開、Release/Deployは引き続き別Gateです。

The effect is eligible only after this lock-host proposal has all hosted
checks green, is merged normally, and the merged main registry is read back
with the exact target head and no overlap.

## Denied during the effect

- mutation of any of the 14 immutable target paths
- mutation of this registry from the target implementation branch
- `.github/**` or workflow weakening
- Audio receipt/store/source changes
- paid/cloud/credential/Provider/native/Resolve/Export/publication execution
- version tag, Release, or Deploy
- rebase, force push, automatic retry, or automatic rollback

## Proposal verification

- registry JSON parse: required before commit
- exact lock count: one
- allowed file count: one (`CHANGELOG.md`)
- hosting diff scope: registry plus this ASCII-path Evidence only
- hosted checks / merge / post-main read-back: pending and not claimed
