# TASK-042 Summary

- Name: Product Workflow V6 Integration / Frame-bound Reference & Production UX
- Priority: `OWNER_MAXIMUM / CURRENT_HIGHEST`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Current Phase: `P-V6-1B IMPLEMENTATION`
- Current Gate: `P-V6-1B IMPLEMENTATION_LOCAL_PASS / HOSTED_PENDING`
- Implementation: `P-V6-1A COMPLETE / P-V6-1B LOCAL_COMPLETE_HOSTED_PENDING`
- Current implementation baseline: `cbf27b29ddab08050df4804c160501ff4586bb11`
- TASK-013 Native H3: `PARKED / NO_REPLAY`
- TASK-041: `PRODUCT_PROMOTION_HOSTED_CLOSED / REUSE_FOUNDATION`
- Stable release: `v0.20.1`; no new version selected

TASK-042 is a new cross-cutting requirement set. It does not reopen completed TASK-036..041 history. Read the current-main audit, full detailed design and design/review/authorization record before any source change.

P-V6-0 merged through PR #49 at exact main `7be3de1a8b75dc6d88ec985ab49a2cd373f4549a`; its branch and dedicated clone were removed before a fresh P-V6-1A clone was created. P-V6-1A passed PR #50 `9 / 9` and merged at exact main `694e9933d93c2d0e320486d1afa81f85e7574940`; its branch and dedicated clone were also removed. Read the local evidence and hosted closure record before P-V6-1B review.

The BAI Development OS Autonomous Queue selected `BVP-TASK-042-P-V6-1B / DESIGN_ONLY` after Owner trigger merges PR #50 and #51. Design PR #52 head `f3d99fe07a74974d0e95a925f1c72b67054e86f3` passed `9 / 9` and merged at exact main `cbf27b29ddab08050df4804c160501ff4586bb11`; its branch and clone were removed. The Queue then selected the same unit with `IMPLEMENTATION` authority and checksum `sha256:6a44e3fee803b247d899278c8ad137a024a8f5aebd3b090022b4333eb4cc2f95` from a fresh clone.

P-V6-1B now locally passes exact v1/v2 Proposal, Human GO and crash-safe snapshot integration while keeping v2 Production Control/generation blocked until P-V6-2. The Owner-requested Windows EXE build batch, ignored `builds/` output, root Windows guide and README build/AUTONOMY examples are present and reuse `packaging/task036_shell.spec`. Focused tests pass `26 / 26`; full Windows regression passes `946 / 946` with one intentional skip; an isolated real Windows one-dir build produced the expected EXE with PyInstaller `6.22.0`. Hosted checks, exact main merge and cleanup remain. That merge is cadence merge `2 / 2`; return to AUTONOMY before selecting further work.
