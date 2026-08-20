# TASK-051 R7P — Requirements Alignment Detailed Design

Status: `LOCAL_IMPLEMENTED / WINDOWS_HUMAN_ACCEPTANCE_PENDING`
Development depth: `DEV-3 HIGH ASSURANCE`

## Goal

Align the already implemented R7N Game Knowledge and video-analysis foundation with the Owner's 2026-08-20 requirements without creating duplicate runtime/configuration paths.

## Bounded scope

1. Reuse one shared Japanese Model / Device / Compute option provider.
2. Use Runtime Profile values as the defaults for video analysis.
3. Replace free-text video-analysis runtime settings with readonly selectors.
4. Split `動画を解析・編集情報を出力` into `解析` and `解析結果` tabs.
5. Keep the analysis surface two-stage: media + file controls on the first stage and settings/action below.
6. Remove images from the Game Knowledge list.
7. Add `種別` and `キーワード検索` filtering to the Game Knowledge result list.
8. Move image presentation to the edit/detail dialog and display the image path directly below it.
9. Show imported `details` fields in the edit/detail dialog so effects and other captured guide data are visible.

## Reuse / no-duplication contract

- `dbd_runtime_options.py` is the shared option source for the bounded DbD local analysis workflows.
- Existing `resolve_workspace_runtime_profile()` / `active_runtime` remains the default-value authority.
- R7N `DbDVideoAnalysisWorkspaceService` remains the analysis implementation. No second analysis service is introduced.
- R7N `GameKnowledgeReviewCatalog` remains the Game Knowledge store. No second catalog is introduced.

## Non-goals for this Atomic Unit

- DBD classification regression cases are not changed here.
- Fetch-stage timing/cache/delta/concurrency are not changed here.
- No schema migration.
- No Release / merge / packaged Windows acceptance claim.

## Acceptance

- New alignment tests pass.
- R7O startup safety remains represented after the layout refactor.
- R7N regression passes.
- TASK-049/050/051 regression passes except environment-only Tk display skip.
- Python compilation passes.
