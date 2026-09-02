# TASK-036 Current Main Build and User Flow QA Matrix

Date: 2026-09-03 JST

Role: Development 4 / Owner-perspective integration build and QA

DEV profile: DEV-2 STANDARD (integration/package/user-flow contract); native observation remains a separate gate

## Bound identity

- Repository: `baisound/bai_video_production`
- Canonical source: `origin/main`
- Exact source commit: `d1c41e2f57600caef5668f19e5e6040c90601cc6`
- Worktree: `C:\Users\user\.codex\visualizations\2026\08\30\01a051d0-03e9-74b0-af5c-13e37836926c\bvp-owner-qa-main-20260903`
- Branch: `codex/task-036-owner-main-qa-20260903`
- Source state before build: clean
- Root checkout dirty state: pre-existing untracked worktrees and TASK-036 task-local material only; preserved and not modified by this unit

## Reproducible Windows package build

- Python: `C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe`
- Python version: `3.12.4`
- PyInstaller: `6.22.0`
- pywebview: `6.2.1`
- Build command: process-local `BVP_BUILD_PYTHON=<Python312>` followed by `cmd.exe /d /c build-windows-exe.bat`
- Build result: `PASS`
- Main EXE: `builds\BAI Video Production\BAI Video Production.exe`
- Main EXE size: `16,659,375` bytes
- Main EXE SHA-256: `cc7696412867b7431177896b0b537fa87c57af0a17453ddb6372b87a1d15d364`
- Bundled helper size: `17,277,065` bytes
- Bundled helper SHA-256: `65f9fe0c1064c865d7efa35a0ce0192948bbaae0ecbf04081478d25161c6ecfb`
- Staged helper SHA-256: `65f9fe0c1064c865d7efa35a0ce0192948bbaae0ecbf04081478d25161c6ecfb`
- Package: `1,560` files / `308,390,030` bytes
- Helper staged/bundled identity: exact match
- Secret-free helper protocol smoke: `PASS`
- Source contamination check: `Analysis-00.toc` and xref contain no `task-050` source; sampled packaged resources resolve to this exact QA worktree.
- Warnings: optional Android webview hook, pycparser generated tables, and `pkg_resources` deprecation only. No build failure.

No install, model/runtime download, Provider call, paid action, Release, Deploy, or Production activation occurred.

## Focused and negative verification

### Unit 1 — package entry, first run, central model settings, planning, final review/export

- Result: `186 passed in 16.18s`
- Includes package and entry contracts, TASK-059 helper packaging, installer contract, first-run bootstrap, model selection persistence/restart read-back, planning application, shell/element/interaction contracts, final review/export, and P0E synthetic vertical/native-QA contracts.
- An earlier run reported `116 passed / 70 errors`; one representative error proved the common cause was a missing parent directory for the explicitly supplied pytest `--basetemp`. After creating the test-only parent and rerunning unchanged product tests, all 186 passed. This was a harness invocation error, not a Product logic result.

### Unit 2 — WORLD LOCK, visual generation, Quick, narration/WAV admission, DbD Training Studio

- Result: `213 passed, 2 skipped in 10.17s`
- The two skips are POSIX-only directory-fsync crash injection cases on Windows.
- Includes V6.1.1 visual contract, visual handoff/placement, WORLD LOCK, image/video/Quick route and application contracts, local Comfy ports, local narration preflight/render admission, DbD reasoning model panel, Training Studio integration, and Windows Tk interaction contract.

Combined executed result: `399 PASS / 0 FAIL / 2 platform SKIP`.

These results prove static/synthetic/package contracts only. They are not native UI observation, real generated media, or persistence read-back from an actually launched packaged process.

## Owner-approved R3 comparison

The Owner explicitly approved the full R3 mock in the controlling conversation. The corresponding local task material is preserved in the root checkout but is not present in canonical main:

- R3 design: `v1-owner-exe-ai-model-settings-gap-and-r3-design-2026-08-31.md`
  - bytes: `8,290`
  - SHA-256: `5ccac1a59fc4805a0bc10099728047eff4954a92ad289faa3af112deb697ccb8`
- Interactive R3 candidate: `v1-next-mock-candidate-owner-preview.html`
  - bytes: `31,531`
  - SHA-256: `ecf41d39c9536b52d93bdeb7c4d9868f6a2c121ff5b242a04466171f9bc24b27`

The older R3 design file still says `OWNER_VISUAL_REVIEW_PENDING`; that text is historical/stale relative to the later explicit Owner acceptance. Development 4 did not rewrite or stage the unknown untracked source material.

R3 requires:

1. model selection only at top-right `設定` → `AIモデル`;
2. baseline roles plus game-analysis/commentary/training roles in the central settings surface;
3. no model selector or save button in production screens or DbD Training Studio;
4. an unset warning only on the affected screen, with the exact settings route;
5. loading, empty/no-candidate reason, saving, success, failure/conflict, and restart-restored feedback;
6. Japanese product-facing wording, including `ゲームAI`, `対戦分析`, and `DbD学習スタジオ` rather than unexplained English product labels.

## Current main comparison findings

### Central model settings — baseline production roles

Technical result: `PASS` for static/synthetic behavior; native result: `NOT_CONFIRMED`.

- `task036_shell_v611.py:147-155` projects planning, image, video, audio/music, and Quick readiness from the central settings snapshot.
- Each production screen states that the model is not changed there.
- When unset/unavailable it directs the user to `右上の［設定］→［AIモデル］`.
- `tests/test_task036_v611_interaction_contract.py:58-101` rejects page-local audio/Quick selectors and proves central setting copy/disabled reasons.
- `tests/test_task036_shell_ui.py:172-276,380-420` proves central save, persisted restart read-back, Quick inheritance, and absence of planning/image/video/audio/Quick page-local selectors without Provider execution.

### DbD / game-analysis model setting

Technical result: `FAIL` against Owner-approved R3 interaction rule.

Classification: `POST_MOCK_EXTENSION_PARTIAL_OR_NONFUNCTIONAL` / High UX-responsibility gap.

- The central settings workload set is limited to `PLANNING`, `IMAGE`, `VIDEO`, `AUDIO`, and `MUSIC`; it does not include game analysis, commentary, explanation, or DbD learning support.
- `dbd_training_studio.py:291-332` adds `実況・解説AI` with a `モデルと事前チェック` subpage.
- `dbd_reasoning_model_panel_ui.py:56-72` renders `使用するModel`, a combobox, and `選択を保存` inside the Training Studio.
- `dbd_reasoning_model_panel_ui.py:148-245` loads, enables/disables, and persists that local selection.
- `tests/test_task054_dbd_reasoning_model_panel.py:267-292` and `tests/test_task054_training_studio_ui_integration.py:11-56` explicitly preserve this duplicate selection UI.

The model panel is functionally guarded and its tests pass, but its responsibility/placement is wrong for the Owner interaction rule. Passing tests do not make the UX acceptance pass.

Expected correction:

- add admitted game-analysis/commentary/explanation/DbD-learning model roles to top-right `設定` → `AIモデル`;
- Training Studio and commentary/game-analysis screens show only the selected identity and readiness/preflight state;
- if unset, show a warning and an `AIモデル設定を開く` navigation action, without embedding another selector;
- save, same-screen canonical read-back, restart restoration, and failure feedback remain owned by central settings.

### Japanese product wording

Technical result: `FAIL` against the Owner language requirement.

User-facing current-main HTML still contains mixed internal terminology, including:

- `Game Intelligence / DbD解析`
- `Game Intelligenceを開く`
- `Scene一覧 / Timeline Contract`
- `WORLD LOCK Registries`
- `Recent`, `Direct`, `Project`, `Provider`, `Model`, `Route`, `Track`, `Prompt`, and `Secret` in primary-facing copy

Internal identifiers may stay English, but primary user labels and instructions need plain Japanese. The R3 mock already demonstrates better labels such as `ゲームAI制作の流れ`, `対戦分析`, `実況・解説案`, and `接続・認証情報`.

## Screen-flow QA matrix

| User flow | Static/synthetic | Native packaged UI | Current conclusion |
|---|---:|---:|---|
| Installer/package entry | PASS | NOT_EXECUTED | Reproducible one-dir EXE exists; install/first launch not observed in this unit. |
| First run/project bootstrap | PASS | NOT_EXECUTED | Trusted bootstrap and fail-closed contracts pass. |
| Settings → AI model | PARTIAL | NOT_EXECUTED | Baseline central settings are wired; game/DbD roles are absent from central settings. |
| Planning | PASS | NOT_EXECUTED | Central model readiness, unset guidance, save/restart binding contracts pass. |
| Scene split / WORLD LOCK / Scene design / Start-End | PASS | NOT_EXECUTED | Screen and application contracts pass; real operator usability remains unobserved. |
| AI image / AI video / Quick generation | PASS | NOT_EXECUTED | Route/admission/handoff contracts pass; no Provider or real media generation executed. |
| Voice/narration WAV | PASS for admission contracts | NOT_EXECUTED | Preflight/render admission is covered; no real WAV was generated or heard. |
| Material review / management | PASS for shell contracts | NOT_EXECUTED | No native populated-data interaction performed. |
| Edit / final review / export | PASS | NOT_EXECUTED | P0E synthetic queue/persistence contracts pass; no native dispatch or exported file produced. |
| Game analysis / DbD Training Studio / commentary | FAIL for R3 placement, PASS for current panel mechanics | NOT_EXECUTED | Duplicate model selection remains in Training Studio; central role inventory and Japanese flow are incomplete. |

## Root-cause and routing

- Primary root cause: canonical UI responsibility split. Baseline roles were centralized in TASK-036, while the later TASK-054 consumer retained a separate model-selection store/UI.
- Secondary root cause: extension naming and operator copy retain implementation terminology rather than the approved Japanese product vocabulary.
- Responsible implementation owner: unified Shell/TASK-036 consumer with TASK-054 contract consumer coordination. Development 4 records integration acceptance and does not mutate those shared source paths in this unit.
- Dependency class: shared consumer paths.
- Severity: High for the duplicate model-selection responsibility and absent central DbD roles; Medium for remaining English-heavy operator copy.

Acceptance for the repair:

1. `設定` → `AIモデル` is the only model-selection/save surface for every admitted role.
2. DbD/実況/解説/対戦分析 roles are visible in that central inventory with truthful availability and disabled reasons.
3. Training Studio/model-dependent screens are read-only for model identity/readiness and never save a selection.
4. Unset warnings appear only when needed and link to the exact central settings location.
5. Configured screens do not nag or duplicate settings controls.
6. Save success is shown only after canonical read-back; failure/conflict remains visible; restart restores the same selection.
7. Primary product labels and instructions are understandable Japanese; English remains only where it is a necessary proper noun or technical detail.
8. Packaged-native evidence at the repair head proves visible populated content, interaction, save, navigation, restart restoration, and no duplicate process.

## Parked gates and next action

- Native packaged launch and GUI observation: `NOT_EXECUTED` in this unit; parked until the already-authorized native gate is actively used with duplicate-process preflight.
- Real Ollama process start/stop/probe: not performed.
- Real Provider, real user data, install/download, and release effects: not performed.
- Next independent action: hand off the two consolidated source gaps (central DbD model responsibility and Japanese operator copy), then rebuild the accepted repair head and execute the same matrix plus packaged-native observation.
