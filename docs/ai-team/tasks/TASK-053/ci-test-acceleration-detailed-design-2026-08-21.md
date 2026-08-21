# TASK-053 CI Test Acceleration Detailed Design

Date: 2026-08-21
Status: IMPLEMENTED / HOSTED VALIDATION PENDING
Development depth: DEV-2 STANDARD

## 1. Goal and authority

GitHub Actions の Python test wall-clock timeを短縮し、Windows固有の停止を無期限に待たず診断可能にする。変更対象はCI test executionのみであり、Product runtime、Provider、native media、Release、Deploy、Audio authorityを変更しない。

## 2. Current-state assessment

- pip cacheは既に `actions/setup-python` で有効。
- Linux/WindowsとPython 3.11/3.12/3.13のmatrixは既に並列。
- Product testはfake/local transport中心で、実cloud Provider呼出しを高速化対象にしない。
- 通常main CIは約4〜9分で完了する一方、TASK-036 PRのWindows 3 jobは同時にpytest工程で15分を超えた。したがって単純な全体性能問題ではなく、Windows固有の長時間testまたはhangも診断対象に含める。
- repository全体をDB in-memory方式へ変更する根拠はない。

## 3. Selected design

1. `pytest-xdist==3.8.0` をGitHub-hosted test jobへpinして導入する。
2. worker数はrunner CPU数任せの `auto` ではなく固定2とし、標準2-core runnerでresource oversubscriptionを避ける。
3. `--dist loadfile` で同一test fileを同じworkerへ載せ、module-level fixtureと順序依存露出の範囲を抑える。
4. `pytest-timeout==2.4.0` と `--timeout=120` で1 test itemの停止を検出する。Windowsではportable thread timeoutが使われ、stack dumpをEvidenceとして残す。
5. `--max-worker-restart=0` により、timeoutで終了したworkerを自動replayしない。Provider/native replayとは無関係だが、診断の重複と待ち時間を抑える。
6. `--durations=20` で遅い上位20件を各runのログに残す。
7. job全体に `timeout-minutes: 20` を設定し、collection/session teardownなどper-item timeout外の停止も最大20分でfail closedにする。

## 4. Rejected alternatives

- `-n auto`: runner差でworker数が変わり、I/O競合と再現性低下を招くため不採用。
- test matrixの追加shard: wall-clock短縮は可能だがjob数を6から12へ増やし、setup/FFmpeg download costを倍増するため先に採用しない。
- DB一括in-memory化: current bottleneckとの直接Evidenceがなく、Product storage test semanticsを弱めるため不採用。
- timeoutだけ:停止診断は改善するが通常runの短縮にならないため、bounded parallelismと組み合わせる。

## 5. Safety and compatibility

- full suiteのtest selectionは変更しない。
- OS/Python matrix、FFmpeg verification、compileallを維持する。
- Product packageのruntime dependencyへpytest pluginを追加しない。pluginはephemeral CI job内だけに入れる。
- timeout/worker crashはjob FAILであり、PASSへ変換しない。
- hosted comparisonは全9 checks PASSに加え、Windows/Linuxのpytest durationとslowest-20をread-backする。

## 6. Files and acceptance

Allowed files:

- `.github/workflows/ci.yml`
- `tests/test_oss_readiness.py`
- `docs/ai-team/tasks/TASK-053/ci-test-acceleration-detailed-design-2026-08-21.md`
- `docs/ai-team/tasks/TASK-053/ci-pytest-parallel-installation-procedure-2026-08-21.md`

Acceptance:

- workflow contract focused test PASS
- YAML parse/static read PASS
- `git diff --check` PASS
- hosted Linux/Windows × Python 3.11/3.12/3.13 PASS
- no product source/schema/version/CHANGELOG change
- measured wall-clock and any timeout finding reported truthfully

## 7. Local implementation evidence

- focused workflow contract with the exact plugin options: `12 passed in 3.03s`
- non-Tk WSL full regression with fixed 2 workers: `2652 passed, 2 skipped in 60.10s`
- slowest 20 durations were emitted; slowest item was 3.40 seconds
- no per-item timeout, worker crash or replay occurred
- unfiltered WSL run's only residuals were the environment's missing `tkinter` module (1 failure, 3 collection errors); this is kept separate from the parallel-run technical result
- hosted Linux/Windows matrix remains the final acceptance authority
