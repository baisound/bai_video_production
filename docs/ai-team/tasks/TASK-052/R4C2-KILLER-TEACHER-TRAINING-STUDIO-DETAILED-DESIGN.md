# TASK-052 R4C2 — Killer-specific Teacher Training Studio

Status: `IMPLEMENTED / VERIFIED`
Profile: `DEV-3 HIGH ASSURANCE`
Depends on: `R2A`, `R2B`, `R4A`, `R4B`, `R4C1`

## Goal

Expose the R4C1 Killer-specific Teacher contract through the existing Safe Visual
Learning / Training Studio video-batch workflow without creating another dataset,
ROI model or capability catalog.

## Canonical boundaries

- `VisualTrainingManifest` remains the only visual Teacher manifest.
- `KillerCapabilityRegistry(initial_killer_capabilities(), {})` is the UI admission
  catalog and the required Killer-specific reference-index binding.
- Existing versioned Survivor portrait ROIs are reused for all currently registered
  starter capabilities; no duplicate Killer-specific crop geometry is introduced.
- The existing preview -> Human confirm -> batch commit -> one index rebuild/domain
  transaction remains the only R4C2 registration path.
- Real-media accuracy, Provider execution, Production mutation, release and deploy
  remain outside this Atomic Unit.

## Input contract

A Killer-specific batch target requires:

- an exact registered `killer_id / effect_id` pair;
- bounded `match_id` and one or more explicit Survivor slots `0..3`;
- `POSITIVE` or `HARD_NEGATIVE` Teacher role;
- the capability's exact positive namespace, or one of its registered cross-Killer
  hard-negative namespaces;
- `active` for positive samples, with optional bounded `stage` and
  `progress_milli`; hard negatives carry no positive state.

All fields are validated before FFmpeg extraction. Missing Registry binding,
unregistered targets/namespaces, ROI/slot mismatch, invalid role/state and stage
overflow fail closed.

## Persistence and review

`StagedTrainingSample`, `BatchVisualTarget` and receipt schema `1.2.0` preserve the
R4C1 fields through preview, receipt reload, commit and review-state transition.
Both batch and single confirmation preserve those fields in the canonical manifest.
Killer-specific index rebuilding always receives the exact Capability Registry.

The registered-data list exposes slot/Teacher role and searches the Killer/effect,
namespace and structured state fields. The legacy generic edit modal is intentionally
blocked for `KILLER_SPECIFIC_HUD`; operators delete and re-register through the
capability-bound workflow so a generic relabel cannot silently corrupt the namespace
or state contract.

## Acceptance

- positive and registered hard-negative samples round-trip through staging receipts;
- a confirmed pair builds the capability-bound Killer-specific reference index;
- missing Registry and foreign hard-negative namespace fail before extraction;
- four existing Survivor slot ROIs are reused exactly;
- Training Studio exposes registered capability/role/namespace/state controls and
  does not route this domain through generic Knowledge/Alias selection;
- existing Survivor Safe Visual Learning, batch transaction, Training Studio UI,
  transport/profile and packaged-source contracts remain green.

## Verification

- R4C2 focused plus R4C1/R2A/R2B/Safe Visual Learning: `30 PASS`.
- TASK-050/TASK-052 dependency regression: `161 PASS`.
- TASK-051 Training Studio / package-source affected regression: `125 PASS` after
  synchronizing the intentional accepted-source hash.
- Python compileall: `PASS`.
- unresolved Critical/High findings: `0 / 0`.
