# TASK-110 — Stable AI Model Identity Labels

Status: `ACTIVE / IMPLEMENTATION_VALIDATED / COMMIT_READY`

Governance: `DEV-2 STANDARD`

## Authority and responsibility

During the authorized TASK-106 packaged-native acceptance on 2026-10-11, the
Owner observed that the central AI-model selector displayed ordinal aliases
instead of actual model names and requested that the real names be visible.
After the implementation boundary was clarified, the Owner explicitly
authorized this TASK-110 implementation on 2026-10-11.

The same acceptance showed that selecting ordinal `2` changed the preferred
route, after which the selected model was relabeled as ordinal `1` because the
routes are sorted by priority. This made a successful save look like a reset
and could cause the Owner to select the other route on a subsequent save.

This is a new model-identity presentation responsibility. It does not reopen
TASK-106 Planning readiness, TASK-107 Settings reachability or TASK-108 save
handler execution. The separately proposed TASK-109 identity is reserved by
another lane and is not reused.

## Start identity and overlap decision

- base / HEAD / observed `origin/main`:
  `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04`;
- branch: `codex/task-110-model-identity-labels-20261011`;
- worktree:
  `C:\Users\user\.codex\worktrees\task110-model-identity-labels\bai-video-production`;
- initial dirty state: clean;
- the TASK-106 native-QA worktree and its external Evidence are preserved and
  must not be modified, cleaned or used as this Task's source;
- the previously launched TASK-106 Product process was absent at TASK-110
  start; no native process is owned by this unit.

## Root cause

`ConnectionSettingsFormBuilder` returns routes sorted by
`(priority, route_id)`. `Task036ShellBridge._connection_settings_projection()`
then overwrites every route display name with an ordinal label derived from
that current list position. Saving another preferred route changes its
priority to zero, so the same route receives a different ordinal after
readback even though persistence succeeded.

The canonical form already contains `model_id`. The Shell also has an existing
public-label validator that rejects control characters, non-normalized or
oversized text, paths, URLs, account-like values and common secret tokens, but
the model projection did not use it.

## Atomic Unit A contract

Goal: present a stable, public-safe model identity in the central selector and
selected-model readback without changing route persistence or execution
authority.

The implementation must:

1. derive `display_name_ja` from the canonical `model_id` only when it passes
   the existing public-label validator;
2. retain the generic `登録済みローカルAIモデル` fallback for unsafe or
   missing identities;
3. make `selected_model_display_name` match the preferred route's projected
   stable label;
4. keep the same route-to-label mapping before save, after priority reorder and
   after restart readback;
5. preserve secret, endpoint, credential, Provider-execution, billing and
   generation boundaries;
6. change no connection-settings schema, route identity or selection logic.

## Allowed Files

- `docs/ai-team/tasks/TASK-110/**`
- `src/ai_video_production/task036_shell_ui.py`
- `tests/test_task036_shell_ui.py`
- `tests/test_task036_v611_interaction_contract.py`

## Prohibited changes and effects

- no TASK-106/107/108 historical rewrite or TASK-109 reuse;
- no connection-settings schema/store mutation semantics change;
- no Provider, inference, model download, billing or generation;
- no build/package/installer or native Product launch;
- no Resolve, Cubase, Release, Deploy or Production Activation;
- no cleanup or mutation of foreign worktrees, QA roots or Evidence.

## Acceptance

- safe model IDs such as `qwen3:8b` are visible as their stable actual name;
- unsafe display values fall back without entering the rendered label;
- selecting another preferred route and the resulting priority reorder do not
  rename either model;
- restart readback retains the selected model's real name;
- existing missing-label fallback behavior remains valid;
- focused Shell, model-selection and interaction tests pass;
- diff/scope review contains only Allowed Files;
- no prohibited effect occurs.

## Next action

Atomic Unit A now projects safe canonical model identities without ordinal
renaming, keeps the generic fallback for unsafe values and derives the selected
model display from the preferred projected route. The focused red case was
`3 FAIL / 1 PASS`; the corrected focused gate is `4 PASS`, the related
Settings/model-selection/Shell/Node regression is `102 PASS`, compileall and
diff checks pass, and prohibited effects remain zero. Detailed validation is
recorded in `evidence/atomic-unit-a-implementation-validation-20261011.md`.

The unit is commit-ready. Commit/push/PR and replacement package/native
confirmation remain later actions; they are not implied by source validation.
