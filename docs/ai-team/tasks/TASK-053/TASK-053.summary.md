# TASK-053 — CI Test Acceleration and Hang Diagnostics

Status: ACTIVE / IMPLEMENTATION COMPLETE / HOSTED VALIDATION PENDING
Owner lane: Development 2
Development depth: DEV-2 STANDARD
Allocated: 2026-08-21 by direct Owner request

## Objective

添付されたPython test speedup guideをcurrent repositoryへ照合し、既存full regression coverageを減らさずGitHub Actionsのwall-clockを短縮する。同時に、Windows test hangをbounded time内で原因testとして観測可能にする。

## Scope

- GitHub Actions test jobの固定2-worker parallel execution
- file-scoped distribution
- per-test timeout、worker no-replay、job timeout
- slowest-test duration Evidence
- workflow contract test
- CI-only installation procedure

## Exclusions

- Product runtime dependency
- Product source/schema/version/CHANGELOG
- testのskip/deselect
- DB semantics変更
- paid/cloud/native Provider
- Release/Deploy
- BAI Development OS変更

## Completion gate

- detailed designとinstallation procedureが存在
- focused static contract PASS
- hosted 6-platform matrix PASS
- pre/post wall-clock比較を記録
- Critical/High unresolved finding 0

## Local verification

- exact parallel focused contract: `12 passed in 3.03s`
- WSL non-Tk full regression: `2652 passed, 2 skipped in 60.10s`
- unfiltered WSL observation: `2657 passed, 2 skipped`; remaining 1 failure and 3 collection errors are exact `tkinter` absence, not xdist/timeout failures
- compileall: PASS
- diff check: PASS
- paid/cloud/native Provider calls: 0
