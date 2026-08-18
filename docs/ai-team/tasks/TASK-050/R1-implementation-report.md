# TASK-050 R1 Foundation Implementation Report

Status: IMPLEMENTED_IN_PACK
Base reviewed: merged main after PR #185

## Implemented

### R1A Workspace Foundation
- stable workspace_id
- user-selected parent directory
- workspace display name
- workspace.json marker
- recent/default registry
- legacy fixed-path adoption without moving existing data
- rename while preserving identity/path
- non-mutating migration preflight
- required Workspace subdirectories

### R1B Runtime Environment Profile
- Python effective path
- FFmpeg / FFprobe / Tesseract auto detection
- FasterWhisper package version detection
- model cache path
- model/device/compute/OCR settings
- profile persistence
- credentials deliberately unsupported

### R1C Japanese-first foundation
- operational stage order
- Japanese stage labels
- Japanese structured error contract
- first-launch Workspace selector
- `はじめに`
- `実行環境を設定`
- `学習データを確認` read-only inventory
- existing major tabs renamed in Japanese by integration patch
- existing tabs reordered into operational sequence

## Explicitly deferred
- destructive/mutating Workspace relocation (R6; R1 is preflight only)
- HUD pixel editor/heartbeat (R2)
- Preview -> Confirm -> Register refactor (R3)
- relabel/delete/approve/hard-negative review operations (R3)
- generalized alias resolver (R4)
- observation/provenance export integration (R5)
- Human Gold visibility metrics (R6)

## Safety
- Existing fixed `%LOCALAPPDATA%` training directory remains supported only as a legacy adoption candidate.
- `--workspace` remains supported.
- No data is moved by R1.
- No secrets are serialized into Runtime Profiles.
