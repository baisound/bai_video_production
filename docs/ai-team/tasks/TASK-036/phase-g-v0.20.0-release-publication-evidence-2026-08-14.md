# TASK-036 — Phase G v0.20.0 Release Publication Evidence

- Date: `2026-08-14`
- Result: `V0_20_0_RELEASE_PUBLICATION_VERIFIED`
- Repository: `baisound/bai_video_production`
- PR: `#20 / MERGED / https://github.com/baisound/bai_video_production/pull/20`
- Exact PR head: `3e43b550ad3eb1db9c6b51843c0051d692c1732c`
- Exact main release SHA: `1fc8bae6ee5bf0c63c1c7d92e21e1eb6dd966c88`
- Annotated tag: `v0.20.0`
- Tag object: `398ff06c938044c28c588a2faa2f68fc5109ee73`
- Tag dereference: `1fc8bae6ee5bf0c63c1c7d92e21e1eb6dd966c88`
- GitHub Release: `BAI Video Production v0.20.0`
- Release URL: `https://github.com/baisound/bai_video_production/releases/tag/v0.20.0`
- Channel: `stable` (`draft=false / prerelease=false`)
- Published at: `2026-08-13T18:23:11Z`
- Formal Release workflow: `31730365365 / SUCCESS`

## Published assets

- Wheel: `ai_video_production-0.20.0-py3-none-any.whl`
  - SHA-256: `beb861614a89e13836506ec7ff02c8ae5a4c24bb6f04420f266f9705e0e4205d`
- Source distribution: `ai_video_production-0.20.0.tar.gz`
  - SHA-256: `63188c2c011ce1335d3bcde9a89e0ca06938c36084e016fd114299e765a94984`

## Ordered gate verification

1. TASK-010/011/012 real native gates passed.
2. TASK-036 W2 packaged native E2E passed; W0/W1 was formally parked with bounded release limitations.
3. Isolated WSL2 regression passed `805 / 805` and PR #20 passed all `9 / 9` hosted checks.
4. PR #20 merged without direct main push; the exact main merge SHA was verified before Tag creation.
5. The annotated Tag dereferences to that exact SHA.
6. The formal stable GitHub Release published the verified wheel and source distribution.
7. The release feature branch was deleted locally/remotely; raw local `evidence/` remained untracked and preserved.

This release does not claim overall TASK-036 `NATIVE_VALIDATED`, `DESKTOP_SHELL_NATIVE_UX_PASS`, `MINIMUM_EDITING_PRODUCT_MVP_PASS` or M3B completion. W0/W1 clean-profile, missing-WebView2, long-path, full DPI/mixed-monitor and screen-reader cases remain `PARTIAL / PARKED_TO_PHASE_H2`.
