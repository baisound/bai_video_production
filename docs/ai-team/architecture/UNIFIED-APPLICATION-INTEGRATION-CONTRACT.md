# Unified Application Integration Contract Ver.1.0

- Parent architecture: `PRODUCT-ARCH-001`
- Applies to: all user-facing / operator-facing Product TASKs
- Status: `CANONICAL_DESIGN_CHECKLIST`

## Required Task Design Block

Copy this section into each relevant detailed design:

```markdown
## Unified Application Integration

- User-facing classification:
  - USER_FACING / OPERATOR_FACING / NOT_USER_FACING
- Integration state at start:
  - BACKEND_CAPABILITY_ONLY / INTEGRATION_DESIGNED / SHELL_INTEGRATED / NATIVE_VALIDATED
- Target integration state at exit:
- User Entry Point:
- Shell / Workspace Location:
- Project Context:
- Asset Context:
- Timeline/Edit Plan Context:
- Primary User Flow:
- Running/Progress UX:
- Success UX:
- Failure UX:
- Cancel/Retry/Recovery:
- Open/Save/Import/Export UX:
- Settings / Provider configuration:
- Background worker lifecycle:
- Review / Approval:
- External application interaction:
- CLI / localhost role:
- Native Windows acceptance:
```

## Design Gate

A user-facing Task cannot pass detailed-design Judge with `User Entry Point` and `Shell / Workspace Location` both undefined.

A backend-only slice may proceed before Shell implementation only if:

1. the future integration point is named;
2. the capability is marked `BACKEND_CAPABILITY_ONLY`;
3. CLI/browser surfaces are not described as final Product UX;
4. the headless boundary remains testable;
5. future Shell integration does not require breaking the canonical service contract without a new design review.

## UX Critic Questions

- Can a normal user discover the feature without reading documentation?
- Can input/output be selected without typing paths?
- Does the app show progress and completion?
- Are failures visible and actionable?
- Is there a recovery/retry path?
- Is Project/Asset context preserved across features?
- Is user approval required before destructive/external writes?
- Does Windows focus/foreground/dialog behavior work?
- Does the user need a terminal or browser for normal operation?
- Does the feature fit the common application navigation model?

## Exit Classification

`BACKEND_CAPABILITY_ONLY` means the internal engine is usable/testable but the final desktop workflow is not complete.

`INTEGRATION_DESIGNED` means the Shell connection and UX are fully specified.

`SHELL_INTEGRATED` means the capability is reachable and operable from the unified Product Shell.

`NATIVE_VALIDATED` means the integrated workflow passed real-machine acceptance.
