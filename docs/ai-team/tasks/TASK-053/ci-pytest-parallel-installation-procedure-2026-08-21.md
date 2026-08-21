# CI Pytest Parallel Tooling Installation Procedure

Date: 2026-08-21
Scope: GitHub-hosted ephemeral CI runners only

## Purpose

BAI VIDEO PRODUCTIONのfull Python regressionを固定2 workerで実行し、Windows固有hangをbounded timeoutで診断するためのCI専用tooling手順。

## Installed packages

- `pytest-xdist==3.8.0`
- `pytest-timeout==2.4.0`

いずれもtest toolingであり、Product runtime dependency、packaged EXE、ComfyUI、Ollama、音声runtimeには導入しない。

## CI installation

既存のeditable development install後、各GitHub-hosted runnerで次を実行する。

```text
python -m pip install --disable-pip-version-check --no-input pytest-xdist==3.8.0 pytest-timeout==2.4.0
```

runnerはjob終了時に破棄されるため、永続PC環境、PATH、registry、system Pythonを変更しない。

## Test command

```text
python -m pytest -q -n 2 --dist loadfile --timeout=120 --max-worker-restart=0 --durations=20
```

## Verification

1. install stepが全OS/Python matrixで成功すること。
2. test logが2 workerを開始すること。
3. full suiteのselected test countが意図せず減っていないこと。
4. 全testとcompileallがPASSすること。
5. timeout時はstack dumpを保存し、rerunやtimeout延長の前に原因testを修正すること。

## Rollback

Hosted validationでparallel-only failureが出た場合、test isolation defectを修正する。緊急rollbackが必要な場合はCI workflowのplugin install stepとparallel/timeout optionsを同じcommitで戻す。Product runtimeのuninstall作業はない。
