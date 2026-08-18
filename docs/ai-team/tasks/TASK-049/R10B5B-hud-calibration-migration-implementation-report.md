# TASK-049 R10B5B — HUD Calibration / Data Migration Implementation Report

## Implemented

- Training Studio `HUD Calibration` tab with video/still input and exact frame preview;
- mouse-drag ROI registration for Survivor HUD/slots, upper-right text, Perk HUD/slots, optional Killer/Power;
- normalized coordinate persistence and versioned profile metadata;
- anchor clip persistence with dHash/SHA-256;
- calibrated profile registry and load/save;
- automatic profile resolution by geometry/UI Scale/game version plus anchor score;
- bounded micro-anchor alignment and parent->slot translation propagation;
- fail-closed unknown/ambiguous profile and low-confidence anchor behavior;
- optional profile resolver/alignment integration in `DbDRecordedVideoRecognizer`;
- Training Studio DbD Data Backup / Preview / Restore for PC migration;
- README/user/accuracy/slice documentation links.

## Safety boundaries

- Discovery default ROIs remain compatibility/testing defaults, not a Production accuracy claim.
- Auto profile resolution does not guess when candidates are absent/ambiguous.
- Anchor correction translates only within a bounded pixel window; it does not rescale geometry.
- Restore validates manifest and SHA-256 before writing and creates a safety backup before replacement.
- API keys/credentials/private keys and source DbD videos are excluded from the migration bundle.
- Production recognition accuracy remains NOT_CONFIRMED until real-media Human Gold KPI passes.

## Local verification

- TASK-049 focused suite after implementation: `164 PASS`.
- Additional broad regression is recorded separately in `broad-regression-evidence.md`.
