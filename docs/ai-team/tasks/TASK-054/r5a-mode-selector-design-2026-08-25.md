# TASK-054 R5A Mode Selector and Immutable Receipt Design

Date: `2026-08-25`
Development depth: `DEV-3 HIGH ASSURANCE`
State: `IMPLEMENTED / LOCAL EVIDENCE`

## Atomic Unit

Provide an always-visible Japanese Operator control for choosing
`確認モード（学習しない）` or `学習モード`, and persist each explicit choice as
an immutable, checksum-bound receipt. This unit records mode intent only.

## Canonical boundary

- `ReasoningSessionMode` in `dbd_reasoning_contracts.py` remains canonical.
- R5A does not create a second inference mode or redefine
  `training_eligible`.
- A mode-selection receipt is not an execution receipt and grants no
  authorization.
- `LEARNING` means preparation eligibility only. Dataset mutation, training,
  Provider execution and Binding mutation all remain false until their separate
  gates are satisfied.
- `PREVIEW_NO_LEARNING` remains the default when no selection receipt exists.

## Operator flow

The compact selector is placed above the Training Studio notebook so the active
mode remains visible on every tab. Text, not color, communicates the safety
boundary:

- confirmation: model unchanged, learning material unchanged, no automatic
  learning;
- learning: candidate preparation only, with no learning, external send or
  model change from selection alone.

No `学習する` action exists in this control. Raw SHA-256 is hidden under
`詳細`. While an analysis/training operation is active the control rejects a
mode change and restores its prior visual selection.

## Receipt and store

Each explicit selection creates one canonical JSON receipt under
`control/dbd-reasoning-mode-receipts/` in the selected Workspace. Files use
exclusive creation and are never replaced. The receipt binds Workspace,
previous/selected mode, UTC time, mode effect, training eligibility and four
explicitly false authority flags. Its SHA-256 covers the complete body.

Loading is fail-closed. Unknown fields, invalid enum/boolean/timestamp values,
foreign Workspace identity, checksum mismatch, duplicate ordering keys or a
corrupt JSON file stop mode mutation rather than silently resetting state.

## Allowed files

- R5A mode-selection domain/application module and Tk panel
- Training Studio composition root
- canonical and packaged schema mirror
- TASK-054 tests and current task documentation

## Prohibited effects

- Dataset adoption or mutation
- model/runtime download
- local or paid training
- Provider inference or private-media upload
- active Binding mutation/promotion
- Timeline/Resolve mutation
- release, deploy or Production Activation

## Acceptance

- default is confirmation mode without a startup write;
- confirmation and learning selections produce schema-valid immutable receipts;
- neither selection grants execution or mutation authority;
- an active operation prevents switching without writing a receipt;
- tampering or Workspace crossing fails closed;
- canonical and packaged schemas are byte-identical;
- selector is integrated globally in the unified Training Studio entrypoint;
- TASK-054/TASK-049/OSS targeted regression, compileall and diff checks pass.
