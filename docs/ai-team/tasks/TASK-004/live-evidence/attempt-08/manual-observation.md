# TASK-004 Behavioral Evidence Attempt 08

## Result

`FAIL / PRE-DISPATCH EXTERNAL DEPENDENCY`

The returned report contains `ERR_PROVIDER_FFPROBE_NOT_FOUND`. The runtime database shows only the first failed `ASSET_INGEST`; no Asset was published and no Audacity/OpenVINO operation was dispatched. This is not an OpenVINO behavioral failure.

## Root cause

Package 0.4.7 corrected Windows binary media I/O, but the behavioral runner still relied on the child Python process resolving the bare executable name `ffprobe` from inherited PATH. On the target machine that lookup failed.

## Corrective contract for package 0.4.8

The PowerShell runner resolves an existing `ffprobe.exe` from an explicit parameter, environment override, PATH, an `ffmpeg.exe` sibling or bounded standard Windows package locations. It passes the resolved absolute path to the behavioral CLI, which injects it into canonical Asset Ingest media inspection.

The correction does not download binaries, execute a shell command string or bypass structural validation. Absence still fails before any external AI mutation with actionable setup guidance.

## Remaining gate

Behavioral Evidence must be rerun with package `0.4.8`; the previously accepted capability Evidence remains valid.
