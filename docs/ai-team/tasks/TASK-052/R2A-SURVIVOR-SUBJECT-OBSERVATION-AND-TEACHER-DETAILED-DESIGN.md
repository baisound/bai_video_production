# TASK-052 R2A — Survivor-subject Observation and Teacher Detailed Design

Status: `DESIGN_BOUND`
Profile: `DEV-3 HIGH ASSURANCE`
Defect: `DBD-HA-052-007`
Matrix: `DBD-GAP-005 / 006 / 011 / 064`

## Boundary

R2A establishes the canonical subject identity consumed by later recognition and
temporal processing. It does not confirm hook/chase events and does not implement the
R3 temporal state machines.

`GENERATOR_REMAINING` remains match-scoped. `HOOK_COUNT`, `CHASE_STATE` and
`SURVIVOR_STATE` use:

```text
match_id
survivor_slot = 0..3 | unknown-abstention
signal_kind = HOOK_COUNT | CHASE_STATE | SURVIVOR_STATE
value
confidence
source_frame
hud_profile_id / roi_id / detector_version
```

An unknown slot may only carry `UNKNOWN`; it cannot be assigned to a guessed player.

## Canonical values

- `HOOK_COUNT`: `0 / 1 / 2 / UNKNOWN`;
- `CHASE_STATE`: `NOT_CHASE / CHASE_CANDIDATE / CHASE_ACTIVE /
  CHASE_END_CANDIDATE / UNKNOWN`;
- `SURVIVOR_STATE`: `HEALTHY / INJURED / DOWNED / HOOKED / DEAD / ESCAPED /
  UNKNOWN`.

R3 may consume the candidate states with profile-specific thresholds. R2A only
validates and preserves observations and teacher labels.

## Observation and Gold

The reusable observation envelope `1.1.0` adds survivor signal types and explicit
subject fields. JSONL and CSV retain the fields. Gold evaluation keys include
`observation_type + frame + match_id + survivor_slot`, so four observations at one
frame cannot overwrite each other.

## Teacher data and index

New non-Legacy `SURVIVOR_HUD` samples require `match_id`, `survivor_slot` and
`signal_kind`. Video batch, video single and manual UI paths collect and persist these
fields. ROI identity must equal `survivor_slot_<n>`.

The visual manifest adds explicit columns while reading older rows with missing
columns as Legacy. Reference Slice Index `1.1.0` retains the same subject metadata and
continues to read `1.0.0` indexes after checksum validation.

## Acceptance

1. four slots at the same frame serialize and evaluate independently;
2. unknown slot with a non-UNKNOWN value fails closed;
3. invalid hook/chase/Survivor values fail closed;
4. non-Legacy Survivor teacher data without exact subject identity is rejected;
5. preview receipt, manifest and reference index round-trip subject metadata;
6. existing non-Survivor and Legacy routes remain backward readable;
7. source/affected regression passes; packaged Windows interaction remains R9.
