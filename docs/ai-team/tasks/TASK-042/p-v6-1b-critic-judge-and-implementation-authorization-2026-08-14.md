# TASK-042 — P-V6-1B Critic, Judge and Implementation Authorization

## Critic cycle 1

1. `CRITICAL / CLOSED`: Human GO for v2 could be mistaken for verified Candidate LOCK and generation authority. The design separates exact Asset binding approval from P-V6-2 LOCK/CURRENT verification and explicitly blocks v2 compile/admission.
2. `HIGH / CLOSED`: replacing existing Proposal/Approved Plan versions would break historical snapshots. Existing record shapes and v1 output remain compatible; the integration widens accepted Blueprint identity only.
3. `HIGH / CLOSED`: flattening frame references without exact path rules could collide between Start/End or repeated Characters. Deterministic Scene/frame/role/index paths and exact Asset/checksum comparison are mandatory.
4. `HIGH / CLOSED`: a second PyInstaller spec could diverge from the native-validated shell. The root batch must reuse `packaging/task036_shell.spec`.
5. `HIGH / CLOSED`: a convenience batch that installs packages automatically would hide network/environment mutation. Dependency installation stays an explicit documented operator step.

## Critic cycle 2

1. `HIGH / CLOSED`: ignoring the whole `builds/` directory would prevent the requested source directory from existing after clone. Use `/builds/*` plus `!/builds/.gitkeep`.
2. `HIGH / CLOSED`: README AUTONOMY language could imply runtime self-operation. It must state that AUTONOMY is development governance and BVP runtime remains OS-independent.
3. `MEDIUM / CLOSED`: merge cadence could be counted before hosted completion. Count only exact all-green main merges after cleanup; failed/open PRs do not count.
4. `MEDIUM / CLOSED`: build success could be mistaken for release readiness. The guide distinguishes local unsigned build from Tag/GitHub Release/Deploy.

`CRITIC_PASS_AFTER_TWO_FIX_CYCLES`; unresolved Critical/High `0 / 0`.

## Implementation Allowed Files

- `.gitignore`
- `build-windows-exe.bat` (new)
- `builds/.gitkeep` (new)
- `docs/windows/BUILDING-WINDOWS-EXE.md` (new)
- `README.md`
- `pyproject.toml`
- `src/ai_video_production/production_proposal.py`
- `src/ai_video_production/production_proposal_store.py`
- `src/ai_video_production/approved_plan_orchestration.py`
- `tests/test_task042_blueprint_v2_proposal_integration.py` (new)
- `tests/test_task042_windows_exe_build_contract.py` (new)
- existing TASK-027 Proposal/store/orchestration/schema tests only if required for explicit compatibility coverage
- `docs/ai-team/tasks/TASK-042/**`
- bounded status synchronization: `PROJECT.md`, `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`, `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`, `CHANGELOG.md`

No new PyInstaller spec, application entry point, UI, Provider adapter, native generation, media mutation, release metadata or version is allowed.

## Required gates

- focused v1/v2 Proposal/GO/snapshot and build-contract tests;
- v1 Proposal/Approved Plan/snapshot byte and behavior compatibility;
- exact v2 binding path/Asset/checksum coverage;
- v2 compile/admission fail-closed until P-V6-2;
- batch syntax/contract validation and, when dependencies are available, actual local one-dir build plus EXE presence check;
- README Installation-adjacent build section and multiple plain-language AUTONOMY examples;
- full regression, compileall, diff check, Critic unresolved Critical/High `0 / 0` and hosted `9 / 9`.

## Judge

`P_V6_1B_DESIGN_LOCAL_PASS / HOSTED_DESIGN_PR_AUTHORIZED`

Implementation remains `NOT_STARTED`. After this exact design head passes GitHub and merges to main, verify the merge SHA, remove its branch/clone, create a fresh implementation clone, and rerun BAI Development OS Queue with `IMPLEMENTATION` authority. The design merge becomes current cadence merge `1 / 2`; no AUTONOMY reselection occurs until the implementation merge completes merge `2 / 2`.
