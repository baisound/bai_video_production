# TASK-050 R5 Observation / Provenance / Export Implementation Report

Status: IMPLEMENTED_IN_PACK
Prerequisites: R1 applied. R2 is required for `heartbeat_hud` calibration data.

## Implemented

### Common observation envelope
- observation type
- exact frame range
- visibility
- entity/state/intensity/trend
- confidence
- candidates
- evidence ref
- Workspace ID
- Runtime Profile ID
- HUD Profile ID/version
- ROI ID
- applied anchor X/Y pixel offsets
- detector version
- Knowledge revision refs

### Heartbeat
- ACTIVE / OFF / UNKNOWN state
- intensity_milli
- trend
- confidence
- no exact killer-distance claim

### Export
Existing Game Intelligence analysis export gains optional observations:
- `analysis.json` includes `observations`
- `observations.jsonl`
- `observations.csv`
- export manifest hashes both new artifacts

No Production Timeline, Resolve or publishing authority is added.

## Authority boundary

Observation != Canonical Game Event.
An Event resolver may later consume observations and Evidence, but the export
layer does not promote observations to canonical events.
