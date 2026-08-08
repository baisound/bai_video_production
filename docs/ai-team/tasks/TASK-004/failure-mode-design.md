# TASK-004 — Failure Mode Design

| Failure | Required behavior |
|---|---|
| source checksum drift/tamper | fail before ffmpeg/AI runtime; no derived registration |
| malformed/zero frame-rate metadata | fail-safe unknown/explicit target; no float guess |
| ffprobe/ffmpeg missing | `EXTERNAL_DEPENDENCY` |
| ffprobe/ffmpeg timeout/nonzero | `TIMEOUT`/`EXTERNAL_DEPENDENCY`; staging not canonical |
| CFR-required output remains VFR | `DATA_INTEGRITY`; no registration |
| duration drift exceeds profile tolerance | QA failure; no registration |
| ComfyUI public/untrusted endpoint | `SECURITY` before request |
| ComfyUI stats cannot prove configured VRAM floor | `RESOURCE_EXHAUSTED`; `/prompt` not sent |
| workflow references unavailable class | `NOT_SUPPORTED` before queue |
| ComfyUI queue/history timeout | `TIMEOUT`; no canonical asset |
| ComfyUI history traversal/absolute/symlink output | `SECURITY` |
| ComfyUI output missing/non-video | `DATA_INTEGRITY`/`EXTERNAL_DEPENDENCY` |
| Audacity script pipe missing | `EXTERNAL_DEPENDENCY`; no project mutation |
| Audacity current project has tracks | `SECURITY`; fail closed before import/effect |
| OpenVINO effect not discoverable | `NOT_SUPPORTED`; no effect invocation |
| requested effect parameter not present in discovered contract | `VALIDATION`; no effect invocation |
| Audacity effect reports failure/timeout | `EXTERNAL_DEPENDENCY`/`TIMEOUT`; staging not canonical |
| Music Separation expected stem roles cannot be proven | `DATA_INTEGRITY`; no complete stem-set manifest |
| Audio export escapes Product staging | `SECURITY`; reject before publication |
| generated/processed media rights unknown | register conservatively and require review; never mark commercial-safe implicitly |
| crash after bytes promotion but before metadata completion | replay repairs metadata only if producer-bound canonical checksum still matches |
| canonical derived output missing/tampered during repair | `DATA_INTEGRITY`; do not recreate canonical truth silently |
