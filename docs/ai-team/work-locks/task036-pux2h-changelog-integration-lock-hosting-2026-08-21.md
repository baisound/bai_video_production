# TASK-036 P-UX-2H H-A CHANGELOG Integration Lock Hosting Evidence

Date: 2026-08-21
State: PENDING_LOCK_HOST_PR

## Purpose

This docs-only proposal hosts one exact shared-path reservation for the
CHANGELOG effect required by TASK-036 P-UX-2H H-A pull request 232.

It does not modify the target implementation, grant H-B implementation
authority, start Provider or native execution, or authorize release/deploy.

## Fresh-main identity

- repository: `baisound/bai_video_production`
- hosting branch: `codex/task-036-pux2h-changelog-lock-hosting`
- hosting base / audit base: `40d511a2de77ef4bbf0314c576a1268521b8b614`
- registry revision: `32 -> 33`
- open pull requests at proposal time: target PR 232 only
- CHANGELOG or registry overlap from another open PR: `0`

## Target identity

- target PR: 232
- target branch: `codex/task-036-pux2h-asset-edit-placement`
- expected pre-integration head: `078791f7dc8de27d07747e25c71dff70fd539aba`
- target hosted state: `8_OF_9_PASS_CHANGELOG_ONLY_FAILURE`
- immutable target path count: `9`

Immutable target paths:

1. `docs/ai-team/tasks/TASK-036/p-ux-2h-locked-visual-asset-edit-placement-design-2026-08-21.md`
2. `schemas/project-save-journal.schema.json`
3. `src/ai_video_production/interactive_timeline_edit.py`
4. `src/ai_video_production/interactive_timeline_store.py`
5. `src/ai_video_production/project_history.py`
6. `src/ai_video_production/project_save.py`
7. `src/ai_video_production/schema_resources/project-save-journal.schema.json`
8. `tests/test_task043_project_save_recovery.py`
9. `tests/test_task044_timeline_edit_history.py`

## Exact allowed effect

Allowed target file:

- `CHANGELOG.md`

Approved exact bullet:

> - TASK-036 P-UX-2H H-Aとして、Timeline編集v1.1の可逆source bindingとProjectSave participant transactionを追加し、INSERT/REMOVE/REPLACEのUNDO/REDO、COMPLETE/ROLLBACK、再起動・pre-journal orphan回復をv1.0互換を保ってfail-closedにしました。Task036 Shellへのplacement統合（H-B）、Provider/native、Asset mutation、Export、公開、Release/Deployは引き続き別Gateです。

The effect is eligible only after this lock-host proposal has all hosted
checks green, is merged normally, and the merged main registry is read back
with the exact target head and no overlap.

## Denied during the effect

- mutation of any of the 9 immutable target paths
- mutation of this registry from the target implementation branch
- `.github/**` or workflow weakening
- TASK-026 audio-domain changes
- TASK-036 P-UX-2H H-B Shell/placement implementation
- paid/cloud/credential/Provider/native execution
- Asset mutation, Export, publication, version tag, Release, or Deploy
- rebase, force push, automatic retry, or automatic rollback

## Proposal verification

- registry JSON parse: required before commit
- exact lock count: one
- allowed file count: one (`CHANGELOG.md`)
- hosting diff scope: registry plus this ASCII-path Evidence only
- hosted checks / merge / post-main read-back: pending and not claimed
