# TASK-045 P-RC-3 Release Finalization Evidence

Date: 2026-08-15
Authority: `BVP-TASK-045-P-RC-3 / RELEASE_FINALIZATION`
State: `LOCAL_PASS / HOSTED_PENDING / TAG_NOT_CREATED / RELEASE_NOT_CREATED`

## Fresh-main selection

- P-RC-2 PR: `#76`;
- final P-RC-2 head: `76644790b8e154014af7e46b5efeef49b3d58789`;
- hosted checks: `9 / 9 PASS`;
- exact fresh main: `84837e34a42234e23a544f54c8fe0c49aab8cacb`;
- remote branch and dedicated checkout cleanup: `PASS`;
- active branch: `release/0.21.0`;
- collision recheck before P-RC-2 closure: `v0.21.0 NONE`;
- exact decision: `0.21.0 / v0.21.0 / stable`.

P-RC-1 and P-RC-2 are hosted-closed. This satisfies the conditional Owner
authorization for P-RC-3. Production Deploy is not part of this authority.

## Version and documentation truth

The release candidate synchronizes these runtime/package truths to `0.21.0`:

- `pyproject.toml`;
- `CITATION.cff` with release date `2026-08-15`;
- `src/ai_video_production/__init__.py`;
- AI Connection and Subtitle Workspace `PRODUCT_VERSION` constants;
- trusted Desktop launcher and native layout-spike default Product versions.

`CHANGELOG.md` receives the dated `0.21.0` section. Japanese and English README
installation sections document the annotated tag and fail-closed v0.20.1/legacy
Project migration boundary. Tests that explicitly construct v0.20.1 fixtures
remain unchanged because they are compatibility Evidence, not Product defaults.

The first focused governance check rejected `Development Candidate: 0.21.0`
after the Package field had also become `0.21.0`: that field represents only a
strictly later development version. Both canonical surfaces now use
`Development Candidate: NONE`; the current `0.21.0 / v0.21.0 / stable` identity
remains explicit in Release State and release-decision text. No next release is
invented by P-RC-3.

## Sequential gates

| Gate | State |
|---|---|
| Version constants and canonical status synchronization | PASS |
| Local release-metadata consistency | PASS (`0.21.0`) |
| Full Windows and WSL2 regression / compileall | PASS |
| Wheel and source distribution build | PASS |
| Clean isolated install and `pip check` | PASS |
| Windows one-dir EXE build and packaged acceptance | PASS |
| Pull request and all hosted checks | PENDING |
| Exact main merge SHA verification | PENDING |
| Annotated `v0.21.0` creation/push | PENDING |
| Repository Release workflow and published-asset verification | PENDING |

## Local release gate Evidence

- focused governance/launcher/Shell after Candidate-field corrective:
  `43 / 43 PASS`;
- full Windows native Python 3.12: `1123 passed, 1 expected platform skip` in
  `67.46 s`;
- full WSL2 Ubuntu: `1124 / 1124 PASS` in `57.81 s`;
- Windows and WSL2 compileall: `PASS`;
- wheel: `ai_video_production-0.21.0-py3-none-any.whl`, SHA-256
  `45841a129c564b06c5a475526ddbc5e04b6af6e655d2c90efa057f1aca6d2327`;
- source distribution: `ai_video_production-0.21.0.tar.gz`, SHA-256
  `f9c9c2700f1742f0a97a52ba6a7c74017e823a46b43d068e305d49664f9301db`;
- fresh Windows wheel install, installed distribution/package version `0.21.0`
  and `pip check`: `PASS`;
- Windows one-dir EXE SHA-256:
  `aa33bb07580997f45eb0a1e69d1e1926206ca13119bfdf6dc05868826f265109`;
- isolated default packaged acceptance: semantic buttons `36`, unnamed `0`,
  Timeline zoom/scroll, native picker cancellation and same-profile restart with
  `84` entries: `PASS`;
- owned synthetic v0.20.1 Project packaged open/reopen: semantic buttons `31`,
  unnamed `0`, same-profile restart with `50` entries: `PASS`;
- synthetic Manifest file SHA-256 before/after:
  `9c090377a055d28d726338410a18bd56a35f6d41a5c86bef8dd48fb5c306313e` /
  exact same value;
- Provider/paid/Resolve/Cubase execution: `false / false / false / false`.

The distribution build emitted non-blocking setuptools warnings that the current
license table/classifier form will require future PEP 639 modernization before
2027-02-18. Packaging and clean install succeeded; this release does not widen
metadata scope solely to silence a future warning.

## Release order and recovery

The immutable order is release metadata branch, regression/build/install, PR,
all-green hosted checks, main merge, exact main SHA verification, annotated Tag,
then GitHub Release workflow. A failed pre-merge gate is corrected on this
branch. A published Tag is never moved or overwritten; a post-publication notes
correction may narrow claims but may not widen them beyond Evidence.

Credential input, paid Provider execution, ambiguous or destructive Human-owned
Project migration, TASK-013 Native H3 replay and Production Deploy remain
blocked. No Tag or GitHub Release exists at this checkpoint.

## Critic checkpoint

- broad replacement of historical v0.20.1 fixtures/Evidence: prohibited;
- version truth mismatch: fail closed through the repository metadata checker;
- premature Tag or Release: blocked until exact merged main SHA;
- release-note overclaim: bounded by the checked-in release notes and P-RC1/2
  Evidence;
- unresolved Critical/High: `0 / 0`.
