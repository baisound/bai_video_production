# TASK-063 U5 lifecycle implementation evidence

Date: 2026-09-03

## Binding

- Base chain: `origin/main@f46179ec2c32d1d81635ff9eaf1ff9c6a1efeee8`
- Prior TASK-063 U4 commit: `515801926246e7f2a01774a370c3942724e224e2`
- Branch: `codex/task-063-r01-readonly-lc01-r0`
- Design unit: `U5 LIFECYCLE`

## Result

An internal, fixture-only pure lifecycle model now covers:

- first provision at revision one;
- read-only verify/repair with exact instance, pair, terminal and package
  preservation;
- one revision successor with the same immutable pair and revision `+1`;
- predecessor-bound adoption without pair or instance replacement;
- destination-specific portable rebind with a new root and pair generation,
  while preserving instance, revision and package commitments;
- static uninstall preservation with delete count zero and no ProgramData
  fallback.

The model rejects cross-instance, stale/mixed pair, changed repair/adoption
package, same-terminal successor, same-root/same-pair rebind, changed-package
rebind, and first provision over an existing state. Its projection contains no
raw install instance or filesystem path and fixes authority/native effects
false.

The fixture state and planner are absent from `__all__`; the state is
noncopyable and nonserializable. This is a pure transition oracle only. It is
not an operation ticket, TASK-070 reservation, installer effect, or recovery
authority.

## Verification and effects

- focused lifecycle/negative/uninstall cases: 12 PASS
- coherent U1-U5 focused regression: 67 PASS / 19 deselected
- `python -m py_compile`: PASS
- `git diff --check`: PASS
- directory/descriptor/owner/readback mutation: 0
- automatic old-data delete: 0
- cross-instance adoption: 0
- fixed ProgramData fallback: 0
- native installer effect: 0
- real TASK-070/TASK-072 binding: 0
- Release/Deploy/Production Activation: 0

U6 real binding and U7 native evidence remain parked. No TASK-063 corrective
completion or Production-linkage PASS is claimed.
