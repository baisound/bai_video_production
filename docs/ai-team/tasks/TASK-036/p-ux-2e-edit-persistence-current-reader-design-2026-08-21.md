# TASK-036 P-UX-2E EDIT_PERSISTENCE Current Reader

Status: IMPLEMENTED LOCALLY / NATIVE CLOSURE STILL BLOCKED
Development depth: DEV-4

## Boundary

TASK-044 owns Timeline edit persistence. Its append-only edit history, exact
Product Manifest child binding and ProjectSave recovery state are the canonical
truth. This unit does not create a second receipt store and does not allow a
caller-supplied checksum document to become authority.

The TASK-044 application returns one typed current receipt only when all of the
following hold:

- the Product and Timeline Project identities match;
- no ProjectSave or Timeline command-history recovery is pending;
- every Product Manifest child binding passes current integrity validation;
- the TASK-044 child is bound, checksum-valid and version-consistent;
- at least one append-only edit revision exists;
- the revision chain applies to the exact base Timeline; and
- a second Manifest/integrity read confirms that evaluation did not cross a
  concurrent Project revision.

An empty history returns no receipt, so Final Review remains blocked by a
missing `EDIT_PERSISTENCE` Gate. Corrupt, foreign, stale or recovery-required
state fails closed.

TASK-036 may only wrap the typed TASK-044 receipt. When this canonical reader is
bound, a caller-supplied `EDIT_PERSISTENCE` wrapper is rejected as authority
substitution. The other four external Gate owners remain unchanged.

## Effects and gates

The reader performs no Project, Timeline, Asset, Provider, native, render,
Export, publication or Release mutation. It exposes no host path or edit body.
P-UX-2E remains blocked until all other owner receipts, packaged native render
and output QA read-back are current and separately authorized.

## Verification

- focused TASK-044 / Final Review / launcher: `66 PASS`;
- combined ProjectSave / NLE / Final Review / P-UX-2E impact regression:
  `171 PASS`;
- full repository regression: `3168 PASS / 2 platform skips / 0 FAIL`;
- changed Python compilation and `git diff --check`: PASS;
- self Critic/Judge result: `C/H/M/L = 0/0/0/0`.

No Provider, native runtime, render, Export, publication, installation or
Release operation was executed by this Atomic Unit.
