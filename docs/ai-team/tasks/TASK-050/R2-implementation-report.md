# TASK-050 R2 HUD Calibration Implementation Report

Status: IMPLEMENTED_IN_PACK
Prerequisite: TASK-050 R1 applied; R1 verification may still be pending.

Implemented:
- source-frame pixel editor over normalized ROI persistence
- 1px / 5px ROI movement contract
- independent left/top/right/bottom edge editing
- direct X/Y/W/H contract
- undo / redo / reset
- parent ROI edits do not implicitly alter child ROI
- Japanese ROI labels
- perk orientation labels: up/right/down/left
- heartbeat_hud versioned ROI
- heartbeat observation/trend contract
- heartbeat remains Observation, not exact killer-distance fact

UI patch adds:
- Japanese calibration labels
- heartbeat target
- selected ROI emphasis
- exact source-pixel X/Y/W/H
- 1px/5px movement buttons
- edge buttons
- undo/redo/reset
- frame seek buttons

Note: coarse ±1s/±10s buttons use a temporary 30fps assumption. Exact frame index remains authoritative. Rational FPS wiring is a later refinement.
