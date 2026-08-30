# TASK-063 — Installer-Relative Montage Learning Bridge Foundation

- Status: `OWNER_AUTHORIZED / IMPLEMENTATION_ACTIVE`
- Capability: `BVP-INSTALL-RELATIVE-MONTAGE-BRIDGE-001`
- Development profile: `DEV-3 HIGH ASSURANCE`
- Owner instruction: `2026-08-30` — fixed machine-global Bridge paths are rejected; the Bridge must derive from the installer-selected destination, then be compiled, installed and tested without interrupting the three active development lanes.

## Objective

Add the missing unified BAI Video Production Windows installer foundation and
make the montage-learning Bridge discoverable only below the exact
installer-selected Product root:

```text
<installer-selected-root>\data\montage-learning-bridge
```

The installer provisions and reads back one stable installation instance. It
does not activate the production connector, migrate or delete legacy data,
admit learning, generate a Preference, mutate Resolve, publish a Release or
Deploy production state.

## Relationship to existing Tasks

- TASK-058 remains the released Bridge and SKILL interchange contract.
- TASK-060 remains the future canonical Preference source owner.
- TASK-061 remains the future Human activation/deactivation and legacy
  migration owner.
- TASK-063 owns only install-root derivation, instance descriptor, unified main
  installer packaging and bounded Windows installation/read-back Evidence.
- The old ProgramData location may be inspected later by TASK-061 as a
  read-only legacy source; it is not an active TASK-063 fallback.

## Atomic Units

1. `IR-A` — install-root resolver and instance descriptor.
2. `IR-B` — private installer provisioning/discovery command and negative tests.
3. `IR-C` — selectable-directory main EXE installer and build tooling.
4. `IR-D` — Windows compile, bounded custom-path install and read-back Evidence.

## Allowed files

- `src/ai_video_production/montage_learning_file_bridge.py`
- `src/ai_video_production/montage_learning_bridge_application.py`
- `src/ai_video_production/montage_learning_installation.py`
- `src/ai_video_production/montage_learning_installer_cli.py`
- `src/ai_video_production/task036_packaged_entry.py`
- `packaging/task063_main_installer.iss`
- `tools/windows/build-task063-main-installer.ps1`
- `tools/windows/test-task063-main-installer.ps1`
- `tests/test_task058_montage_learning_file_bridge.py`
- `tests/test_task063_install_relative_bridge.py`
- `tests/test_task063_main_installer_contract.py`
- `docs/ai-team/tasks/TASK-063/**`

Shared task index/current-state/roadmap files are intentionally excluded during
implementation so active developer lanes are not interrupted. They may be
updated only at an explicit integration checkpoint after overlap audit.

## Acceptance

- no active montage-learning source contains the old fixed ProgramData Bridge literal;
- an absolute custom root with spaces and Unicode resolves to the exact relative Bridge root;
- fresh provision creates the required directory tree and no fake current Profile;
- repair preserves `install_instance_id`;
- descriptor/owner mismatch, tamper, reparse or malformed identity fails closed;
- the packaged private command bypasses desktop/WebView startup and performs no activation;
- the main installer exposes destination selection, compiles from the exact one-dir EXE payload and binds a payload-tree digest;
- a real silent install under the bounded test root creates and reads back the descriptor and discovery receipt;
- the discovery receipt reports `connector_enabled:false` and `activation_authorized:false`;
- uninstall/data deletion, legacy migration, production activation, Release and Deploy remain outside this Task.

## Stop conditions

- unknown dirty overlap in the dedicated worktree;
- a different active installer architecture appears on fresh `main`;
- compilation would require unapproved credential/private-media access;
- installation target escapes the bounded test root;
- any test attempts automatic connector activation or legacy data deletion.
