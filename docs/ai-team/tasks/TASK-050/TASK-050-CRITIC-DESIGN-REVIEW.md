# TASK-050 Critic Design Review

Decision: APPROVE WITH REQUIRED CORRECTIONS INCORPORATED
Risk profile: DEV-3

## Review summary

The requirements are valid, but treating them only as UI cleanup would be architecturally incorrect. The design is accepted only if the following corrections remain binding.

## Required corrections

### 1. UI labels must not become serialized authority

Japanese display text is presentation. Stable internal IDs/enums remain canonical.

### 2. Workspace path must not become workspace identity

Use stable `workspace_id`. Display name and physical location are mutable metadata.

### 3. Workspace relocation must be journaled migration

Never update the path first. Copy, checksum, verify, activate, then optionally remove the old location.

### 4. Runtime tool path and effective runtime are separate

Store configured path plus actual detected version/health at execution time.

### 5. Runtime Profiles must not contain secrets

No API keys, tokens, passwords, private keys, raw credential material.

### 6. External dependency errors need stable codes

A bare `None`, raw exception, `Error`, or `Failed` dialog is prohibited.

### 7. Training extraction cannot mutate before preview

Interactive video learning must be Preview -> Confirm -> Register.

### 8. Hidden is a presentation state, not absence

For Perk/Item/Add-on:
`HIDDEN != EMPTY`
`HIDDEN != UNKNOWN identity`

### 9. Heartbeat must remain observation before inference

Heartbeat intensity/trend can support killer proximity inference but must not encode an exact distance without evidence/knowledge support.

### 10. ROI pixel editing requires source geometry

Pixel edits are allowed only when the source frame dimensions are known. Persistence remains normalized.

### 11. Parent ROI must not silently overwrite child ROI

Moving a parent may optionally translate children when explicitly selected; resizing a parent must not implicitly distort child calibration.

### 12. Alias model must be generalized

Readings/aliases are not Perk-only. Use a shared entity-alias contract.

### 13. Training dataset review is mandatory

A registration pipeline without review/removal/relabel risks poisoning recognition references.

### 14. Human Gold must separate identity and visibility metrics

Hidden/occluded samples must not reduce identity accuracy.

### 15. Provenance must reach exports

Output should be able to identify Workspace/Runtime/HUD profile/detector versions that produced the observation.

## Residual risks

- Windows DPI scaling may make screen-pixel and source-frame-pixel coordinates diverge.
- Runtime Profile auto-detection order may vary by machine.
- Workspace moves across volumes can be interrupted.
- Tournament overlays may change layout during a match.
- Heartbeat UI can be disabled and should support disabled/not-observed distinction.

These risks are addressed in the implementation plan and tests.
