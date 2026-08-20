# TASK-051 R7A — Accepted Source Gate Correction

Governance: `DEV-3 HIGH ASSURANCE`
Status: `BOUNDED_FIX_RETEST`

## Failure classification

The first R7 installer stopped before mutation because its accepted-source hash for
`src/ai_video_production/dbd_training_studio.py` was taken from the R4B candidate.

That was incorrect: R5 subsequently modified the same Product file, and R6 did not replace it.
Therefore the real accepted R6 worktree legitimately contains the R5 Training Studio source.

- stale R7 expected SHA-256: `36d1c1790ea1c1ec497109fc32ac048f89e3a2d19827baeb974187c5228cf02d`
- correct post-R5 accepted SHA-256: `07c2da313176cdac0f99a939166b43621aefb21f656cb57b6ed673c84cfd9f21`

## Corrective action

Only the R7 preflight hash expectation is corrected. No Product source is changed.

All other R7 behavior remains unchanged:
- accepted-source drift gate;
- focused lineage regression;
- full repository pytest;
- compileall;
- git diff --check;
- source import smoke;
- Windows PyInstaller build;
- packaged executable smoke.

No unresolved HIGH finding remains in R7A scope.
