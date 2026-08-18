# TASK-050 Atomic Implementation Plan

## R1A Workspace identity/store
DEV-3
Files:
- new workspace model/store/schema/tests
Acceptance:
- user-selected path
- stable workspace_id
- no forced LocalAppData
- path rename does not change ID

## R1B Runtime Profile
DEV-3
Files:
- runtime profile model/store/detector/tests
Acceptance:
- FFmpeg/FFprobe/Tesseract/FasterWhisper effective paths visible in model
- user override
- version/health
- no secrets

## R1C Japanese catalog/navigation/help/error
DEV-2
Acceptance:
- normal user-facing strings Japanese
- ordered stage registry
- help metadata
- bare None prohibited

## R2A Calibration navigation
DEV-2
Acceptance:
- time seek and frame seek

## R2B Pixel ROI editor
DEV-3
Acceptance:
- 1px/5px move
- individual edges
- direct XYWH
- undo/redo
- normalized persistence

## R2C Heartbeat ROI
DEV-3
Acceptance:
- profile support
- observation contract
- active/intensity/trend

## R3A Safe video learning
DEV-3
Acceptance:
- no register before confirmation

## R3B Training data review
DEV-3
Acceptance:
- inspect/relabel/delete/approve/hard-negative

## R4A Alias/reading
DEV-3
Acceptance:
- generalized alias resolver

## R4B Trivia usability
DEV-2
Acceptance:
- Category/Event/Entity/Environment selectors and help

## R5 Observation/provenance/export
DEV-3

## R6 Human Gold/migration/backup/Windows closure
DEV-3
