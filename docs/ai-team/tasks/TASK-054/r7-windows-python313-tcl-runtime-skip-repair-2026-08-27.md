# TASK-054 R7 Windows Python 3.13 Tcl Runtime Skip Repair

Date: `2026-08-27`

Status: `BOUNDED_TEST_HARNESS_REPAIR`

Development depth: `DEV-2 STANDARD`

## Trigger

PR `#410` Hosted CI run `33032858710`, Windows Python `3.13` job
`98389079030`, completed the non-installer suite through `99%` and then failed
the existing R7 native Tk acceptance because the second Product root creation
could not read the hosted Python runtime's `init.tcl`.

The initial availability probe succeeded, but the later real Product root raised:

`_tkinter.TclError: Can't find a usable init.tcl`

Windows Python `3.11` and `3.12` passed, all three Ubuntu jobs passed, and the
failure occurred before Product widget construction. TASK-054 R6B-D source,
schema and tests were not in the failing stack.

## Repair

The existing test already classifies an unavailable native Tk runtime as an
environmental skip during its first probe. The same classification is now
applied narrowly when the actual Product root creation raises a Tcl error that
contains either `init.tcl` or `Tcl wasn't installed properly`.

Every other Tcl error is re-raised. Widget traversal, exact tab labels, layout,
safe preflight invocation and disabled-action assertions are unchanged whenever
the native Tk runtime is usable. Product source and workflow configuration are
unchanged.

## Scope

Allowed exact paths:

- `tests/test_task054_r7_windows_native_tk_interaction.py`
- this bounded repair record

Denied:

- Product source or schema mutation;
- workflow weakening or broad Windows skip;
- R6B-D implementation/test/schema mutation;
- CHANGELOG or ACTIVE-WORK-LOCKS mutation;
- Dataset, training, Provider, Release, Deploy or Production effect.

## Acceptance

- unavailable hosted Tcl runtime at either root creation point is explicit SKIP;
- all non-environmental Tcl errors still fail;
- usable runtime still executes every existing native Tk assertion;
- Hosted CI/Security passes on the exact repair head;
- unresolved Critical/High findings are `0 / 0`.
