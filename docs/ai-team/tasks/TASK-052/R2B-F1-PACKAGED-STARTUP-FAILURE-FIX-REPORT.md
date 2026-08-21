# TASK-052 R2B-F1 — Packaged Startup Failure Fix Report

Status: `PASS / COMMIT_READY`
Profile: `DEV-3 HIGH ASSURANCE`
Result: `PACKAGED_STARTUP_AND_BOUNDED_INTERACTION_PASS / R3_NEXT`

## Failure and root cause

The Windows one-dir EXE failed during initial Owner-workspace inventory refresh with
`TypeError: unhashable type: 'dict'`. The inventory search-text builder tested every
Knowledge detail value with set membership (`value not in {None, ""}`). Valid nested
JSON dictionaries and lists are unhashable, so one nested detail aborted startup
before `mainloop`.

## Correction

- added a pure JSON-like Knowledge detail search formatter;
- excluded only top-level `None` and empty-string values by direct comparison;
- retained nested dictionaries/lists as searchable text;
- routed initial inventory refresh through the formatter;
- added a regression fixture containing nested dictionaries, lists, Japanese text,
  `None`, and an empty string;
- advanced the exact Training Studio source gate to the corrected source.

No catalog schema, canonical store, Owner record, or external-provider contract was
changed.

## Verification

- focused failure-fix, R2B, source-gate and package-contract tests: `13 PASS`;
- all TASK-052 plus source/package gate tests: `38 PASS`;
- Training Studio dependency-driven affected regression: `161 PASS` across `44`
  files;
- changed source `compileall`: `PASS`;
- `git diff --check`: `PASS`;
- Windows PyInstaller 6.22.0 / Python 3.12.4 clean one-dir build: `PASS`;
- rebuilt EXE SHA-256:
  `b6a70c25486a012abc57cf23009a014c0388e8baaa48d04b9a5a84a40452f9bd`.

## Real-machine interaction evidence

The rebuilt `BAI DbD Training Studio.exe` opened the default Owner workspace without
an exception and completed these bounded checks:

- initial game-information inventory: `1614 / 1614` displayed;
- Japanese keyword search: `発電機` narrowed the inventory to `231` rows without
  an exception;
- video batch learning tab rendered and switched from Perk to Survivor HUD;
- Survivor HUD displayed four subject slots;
- registered image-learning list rendered existing `VIDEO_BATCH` rows;
- unified training review rendered `1718` registrations;
- application closed normally and left no Training Studio EXE window running.

No fetch, delete, edit, confirm, restore, learning commit, paid-provider, Release,
Deploy, or Production action was executed during this acceptance check.

## Review

The fix is bounded to the failing presentation/search boundary and preserves the
existing JSON-like detail contract. Unresolved Critical findings: `0`. Unresolved
High findings: `0`. Overall TASK-052 real-media packaged acceptance remains open;
this unit confirms startup and bounded non-destructive interaction only.
