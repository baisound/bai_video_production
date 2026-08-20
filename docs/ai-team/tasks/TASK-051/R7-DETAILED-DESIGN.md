# TASK-051 R7 — Integration / Windows Packaged Acceptance

Governance: `DEV-3 HIGH ASSURANCE`

R7 is the final automated acceptance unit for R1–R6 and adds no Product feature.

Required gates:
- TASK-051 focused lineage regression;
- full repository pytest;
- compileall;
- git diff --check;
- source import smoke;
- real Windows PyInstaller onedir build;
- packaged executable import smoke.

The packaged acceptance launcher supports `BAI_TRAINING_STUDIO_SMOKE_EXIT=1`; this proves that
the packaged executable can load the Training Studio dependency graph without starting Tk.

R7 intentionally does not auto-install missing dependencies. PyInstaller absence fails with an
actionable command rather than causing an unapproved network side effect.

Human Acceptance remains separate for real GUI layout, real DBD media, OCR, FasterWhisper,
and visually confirming HUD Profile -> Crop equality.
