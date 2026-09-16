# TASK-094 — Windows Installer Existing-Install and Main Setup Repair

- Status: `HOSTED_CLOSED / MERGED / RELEASE_PENDING`
- Capability: `BVP-WINDOWS-INSTALLER-REPAIR-001`
- Development profile: `DEV-3 HIGH ASSURANCE`
- Owner instruction: `2026-09-16` — every published product installer must let
  the user select its destination and explicitly choose update/reinstall or
  uninstall-then-install when an existing copy is detected. The main installer
  failure observed after payload placement must also be corrected.

## Objective

Repair the five Inno Setup definitions that produce the six Windows installers:

1. always show the application destination page in interactive setup;
2. detect both a registered installation and an interrupted installation left
   in the selected directory;
3. present update/reinstall, uninstall-then-continue, and cancel choices;
4. preserve silent-install compatibility by defaulting it to in-place update;
5. stop the main installer from invoking the deliberately fail-closed TASK-063
   public mutation surface.
6. admit the repository-known Voice Capture locale revision as a safe prior
   exact3 input while continuing to reject every unknown OBS target hash.
7. align Owner Voice application-root validation with the installer by allowing
   a product-specific directory directly below a local drive while retaining
   the stricter nested-directory rule for private data, runtime, and model data.
8. apply the same application-root rule to the shared Training Studio / Trivia
   Editor installer while keeping drive roots, UNC paths, and reparse ancestors
   blocked before payload effects.

TASK-094 does not implement or activate the pending TASK-063 private montage
Bridge composition. Existing Bridge data is preserved. Release publication,
tagging, production activation, and deletion of the user's current partial
installation remain separate gates.

## Allowed files

- `packaging/task094_existing_install_choice.iss`
- `packaging/task063_main_installer.iss`
- `packaging/task092_dbd_utility_installer.iss`
- `packaging/task046_voice_model_builder_installer.iss`
- `packaging/task047_obs_voice_capture_installer.iss`
- `packaging/task093_owner_voice_runtime_installer.iss`
- `tools/windows/test-task063-main-installer.ps1`
- targeted installer contract tests under `tests/`
- `docs/ai-team/tasks/TASK-094/**`
- `docs/ai-team/current-state.md` at the integration checkpoint only

## Acceptance

- all five definitions explicitly set `DisableDirPage=no`;
- all five use the same bounded existing-install decision implementation;
- the registered installation is discovered independently of the newly selected
  target, while a partial selected-directory installation is also detected;
- update/reinstall is forced to the detected root; uninstall is user-selected,
  one-shot, and checked for a successful exit code;
- no unattended install launches an uninstaller;
- the main installer no longer calls `--bvp-installer-bridge` until its private
  composition has been completed and admitted by TASK-063;
- focused source contracts and real Inno compilation pass for all six outputs;
- native tests use one unique contained operation root and do not touch existing
  user installations.

## Prohibited effects

- no automatic removal of existing installations or user data;
- no mutation of the current partial installation during development tests;
- no TASK-063 Bridge activation or fabricated read-back;
- no tag, GitHub Release, deployment, paid-provider call, model download, or
  private-media access.

## Implementation checkpoint

- Exact implementation commit: `581b2e74714a71cba626a50195ecf01f6bb03308`
- Focused contract and canonical-state regression: `41 PASS / 1 intentionally deselected native
  legacy-asset test / 0 FAIL`.
- Inno Setup 7.1.0 compiled all six production-shaped outputs and all six
  isolated-AppId QA outputs.
- Isolated native install, same-location repair and uninstall: main Product,
  Training Studio, Trivia Editor and Voice Model Builder `PASS`.
- Fake-OBS native acceptance: install, repair, collision refusal, append-only
  journal, exact3 adoption/restoration and uninstall `PASS`; real OBS was not
  modified.
- The exact old `en-US.ini` and `ja-JP.ini` revisions observed on the Owner PC
  were accepted, updated and restored on uninstall in a separate fake-OBS run.
- Owner Voice bootstrap PlanOnly and root-policy test `PASS`. Full bootstrap was
  intentionally not executed because it can download/install Python packages
  and the pinned Qwen model; those effects remain outside this corrective unit.
- PR #557 exact head `7fbd101c41704f0393668062e9711138bf8c1b44`
  passed all nine required hosted checks and merged as
  `304d5f32ca7ba244fed4c15f22e1fe3727f0b4fd` at
  `2026-09-16T01:02:31Z`.
- Post-merge Security run `35042486504` passed. Post-merge CI run
  `35042486519` passed all six Linux/Windows Python 3.11/3.12/3.13 jobs,
  including the serial Windows native-installer contract.
- Tagging and GitHub Release publication remain a separate Owner gate.
