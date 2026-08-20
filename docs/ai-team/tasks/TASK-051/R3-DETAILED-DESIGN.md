# TASK-051 R3 — HUD Profile Binding / Multi-slot Visual Learning

Governance: `DEV-3 HIGH ASSURANCE`

## Goals
1. Video Learning must resolve and visibly report the compatible workspace HUD profile.
2. Manual profile JSON becomes an advanced override and is still compatibility checked.
3. Crop ROI is derived from the same calibrated `DBDHudRoiProfile` used by calibration.
4. Pixel coordinates shown to the user are produced by `RoiPixelEditor`, the calibration editor's canonical conversion.
5. PERK_ICON supports four simultaneous slot/entity selections.
6. ADDON_ICON supports two simultaneous slot/entity selections.
7. Knowledge/Alias candidates are pre-populated; no CANDIDATE is silently promoted.
8. One preview displays all selected crops and one Human action registers the bounded batch.

## Failure behavior
- no compatible profile -> fail closed;
- ambiguous profiles -> fail closed and request explicit profile selection;
- uncalibrated optional item/add-on/killer-power ROI -> fail closed;
- no selected slots -> no extraction/registration side effect.

## R2 corrective
The R2 integration had overlapping row numbers in the video-learning lower section.
R3 reflows those rows while preserving the accepted shared transport contract.
