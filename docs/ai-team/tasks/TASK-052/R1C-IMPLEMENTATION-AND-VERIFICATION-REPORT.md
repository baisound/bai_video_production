# TASK-052 R1C — Implementation and Verification Report

Status: `PASS / COMMIT_READY`
Profile: `DEV-3 HIGH ASSURANCE`
Result: `R1C_COMPLETE / R2A_NEXT`

## Outcome

R1C introduces one content-sniffed image boundary for cached map assets and replaces
suffix-dispatched/generic preview failure in Training Studio.

- PNG, JPEG, GIF, WebP, BMP, TIFF and SVG are identified from bounded bytes;
- PNG/GIF/BMP/JPEG and SVG dimensions are inspected without trusting the suffix;
- unsafe SVG DTD/entity/active/external-reference input, unknown magic, oversized
  dimensions and pixel decode failure are bounded fail-visible results;
- raster preview opens bytes through Pillow and applies deterministic clockwise
  `0/90/180/270` view rotation;
- optional SVG rasterization is used only when a safe rasterizer is already available;
  no runtime was installed by R1C;
- collector cache suffix follows inspected content (`.svg`, `.png`, etc.); unsafe or
  unknown content stays `.img`;
- source assets are never destructively rewritten;
- a failed rotation keeps the last valid GUI image reference visible and adds detected
  format/code/reason;
- existing `MapRecord.orientation` continues to persist rotation across reopen/restart.

## Owner-data read-only evidence

The existing opaque asset family was inspected without mutation:

| Measure | Result |
|---|---:|
| `.img` files | 60 |
| detected format | SVG 60 |
| inspection result | OK 60 |
| dimensions | 330×90 for all 60 |
| preview on current WSL runtime | `SVG_RASTERIZER_UNAVAILABLE` (fail-visible) |

These current opaque files are same-sized SVG assets and are not evidence that a real
map diagram rendered successfully. Packaged Windows testing with a real cached map
asset remains mandatory in R9.

## Verification

- focused content-sniff/collector/map persistence regression: `37 PASS`;
- dependency-driven affected regression: `141 PASS` across 34 runnable files;
- Training Studio exact-source gate: `PASS`;
- changed Python `py_compile`: `PASS`;
- Windows packaged real-asset visual acceptance: `NOT_CONFIRMED`.

## Critic review

Resolved before closure:

1. suffix-independent decode reads bytes, not a filesystem-extension dispatcher;
2. SVG DTD/entity declarations, active content and external references fail closed
   before rasterization;
3. declared dimensions and decoded pixel counts are bounded before full pixel load;
4. unsafe/invalid content cannot receive a trusted image suffix;
5. SVG missing-rasterizer and Pillow missing/decoder failure are distinct diagnostics;
6. a failed transformed preview retains the last valid strong `PhotoImage` reference.

Unresolved Critical findings: `0`.
Unresolved High findings: `0`.

## Remaining gates

- R9 must test a real cached Kamigame map image at all four rotations in the packaged
  Windows Training Studio, close/reopen it, restart the app and verify pixels remain
  visible and orientation persists.
- R1C does not add or install an SVG runtime.
- R2A next owns Survivor-scoped hook/chase HUD and teacher-data identity.
