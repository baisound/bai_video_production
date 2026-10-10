# TASK-107 source validation evidence — 2026-10-11 R01

## Identity and scope

- Active Project: `BAI VIDEO PRODUCTION`
- Task: `TASK-107`
- Atomic Unit: `A — Settings modal reachability repair`
- Run identity: `source-validation-20261011-r01`
- Worktree:
  `C:\Users\user\.codex\worktrees\task036-settings-scroll-fix\bai-video-production`
- Branch: `codex/task-107-settings-modal-reachability-20261011`
- Base / initial HEAD / initial `origin/main`:
  `79701a2e3f888cf85f22abb7a6d94d385cf4881f`
- Initial tracked state: clean

Changed paths are contained by the frozen Allowed Files:

- `src/ai_video_production/task036_shell_v611.py`
- `tests/test_task036_v611_visual_contract.py`
- `docs/ai-team/tasks/TASK-107/**`

No shared lock registry, task index, current-state file, CHANGELOG, Provider,
store, queue, Timeline, Resolve or Export path changed.

## Candidate identity

- `src/ai_video_production/task036_shell_v611.py` SHA-256:
  `90c8cb3c675fd4d9f7c4ab2ca3a0b32e7067338cd9485a2a8ba2d98512dd977a`
- `tests/test_task036_v611_visual_contract.py` SHA-256:
  `7b9e14b64b02a35212094f796622c2aaa0d3420641084c742307f2159f37f572`

## Verification

Pre-fix reproduction:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_task036_v611_visual_contract.py::test_settings_modal_routes_bounded_height_to_scrollable_panes
1 failed
```

Post-fix focused contract:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_task036_v611_visual_contract.py::test_settings_modal_routes_bounded_height_to_scrollable_panes
1 passed
```

V6.1.1 regression:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_task036_v611_visual_contract.py \
  tests/test_task036_v611_interaction_contract.py
70 passed
```

Related Shell regression:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_task036_desktop_shell.py \
  tests/test_task036_final_review_shell.py \
  tests/test_task036_shell_cli.py \
  tests/test_task036_shell_ui.py
86 passed
```

Additional checks:

- `git diff --check`: `PASS`
- Allowed Files scope: `PASS`
- source review: Critical `0`, High `0`

## Effect and residual boundary

- No Product or packaged EXE was launched.
- No Windows package/build/compiler/installer ran.
- No Provider, model download, paid call, Resolve, Cubase, release, deploy or
  Production effect occurred.
- Pytest cache was disabled; no task-owned build, runtime or output root was
  created.
- Intentional residuals are the uncommitted Allowed Files changes in the
  dedicated TASK-107 worktree pending Evidence persistence and commit.
- Fresh integrated packaged-native verification is explicitly
  `NOT_CONFIRMED` and remains a separate post-integration Human Gate.

