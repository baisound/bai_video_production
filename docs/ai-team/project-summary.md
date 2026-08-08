# AI Video Production — Project Summary

`ai-video-production` is a Consumer Project built on BAI Development OS governance without copying OS Core into the repository.

The product analyzes video/audio/images/subtitles/AI-generated assets, produces auditable edit plans, automates safe deterministic assembly around DaVinci Resolve, and preserves human-controlled finishing surfaces.

## Completed foundation

TASK-001 completed Product IDs, state/recovery, manifests, schemas, assets/rights, logical paths, atomic persistence, errors/evidence, ownership, profiles/plugins, SQLite persistence and idempotency.

TASK-002 completed the Resolve capability and IPC foundation against the actual target topology. DaVinci Resolve Studio 21.0.2.4 was connected through the Windows PROGRAMDATA scripting bridge. The final isolated sandbox probe measured `15 SUPPORTED / 1 LIMITED / 7 PROBE_REQUIRED / 0 UNSUPPORTED`, including Project save/export, Media Pool/Bin access, WAV import, Timeline creation/append and marker placement.

WSL2 -> Windows authenticated HTTP/JSON was measured with unauthenticated rejection, authenticated round trips and same-endpoint restart/reconnect all passing. The final ADR selects authenticated HTTP/JSON as the primary WSL2 -> Windows transport while retaining Named Pipe as a Windows-local optimization candidate.

Package 0.2.4 additionally retains sandbox probe WAV/DRP assets under Evidence so a successfully imported Timeline item does not become offline merely because the probe process exits.

## Editing-first roadmap

The canonical roadmap prioritizes video-editing value as early as dependencies safely allow. The recommended next dependency route is `TASK-003 -> TASK-004 -> TASK-022`, after which SRT/subtitle creation and Resolve placement, filler/silence/disfluency cuts, SE/BGM generation and placement, and narration generation/placement are brought forward.

Roadmap recommendation does not authorize later TASKs.

## Current verification

- TASK-001: COMPLETED
- TASK-002: COMPLETED
- package: `0.2.4`
- `pytest`: `81 / 81 PASS`
- `compileall`: PASS
- wheel/installed-package verification: PASS
- active Consumer TASK: none
- recommended next: TASK-003, not authorized
