# TASK-018 R0 Smart Reframe Contract — Design / Critic / Judge

## Decision

`TASK018_R0_PROVIDER_NEUTRAL_SMART_REFRAME_CONTRACT = PASS`

This unit adds only an immutable, deterministic, in-memory reframe-plan compiler. It neither selects nor executes a renderer.

## Contract design

### Ownership and reuse

- TASK-007 owns Edit Plan approval and keep/cut semantics. R0 binds its exact plan digest and receives already-authored keep ranges; it does not recompute cut decisions.
- TASK-005 owns scene boundaries and TASK-008 owns multimodal scores. R0 consumes exact row receipt coordinates and validity only; it does not rerun detection/scoring.
- TASK-010/044 own Resolve/Timeline/export effects. R0 emits no execution authority.

### Deterministic invariants

- source Asset ID/SHA, geometry, square-pixel state, rational frame rate and total-frame bound are immutable
- target is portrait, bounded and rate-equal to the source
- every crop is source-contained and has exact target aspect by integer cross multiplication
- keep ranges are ordered and non-overlapping
- proposal source ranges form an exact partition of the complete keep-range set; cut gaps may not be silently filled
- output ranges are rebuilt contiguously from source durations
- Evidence coordinates are unique and canonically sorted
- canonical JSON produces target-profile and plan SHA-256 digests under non-self formulas

### State boundary

`CURRENT_VALID only -> READY_FOR_HUMAN_REVIEW`

`any UNKNOWN -> UNKNOWN_EVIDENCE`

`any STALE or REVOKED -> STALE_OR_REVOKED_EVIDENCE`

All states retain `human_review_required=true` and render/Timeline/external-write false. A digest or state cannot substitute for constituent rows.

### Caps

- dimensions: 1..32768
- frames: 1..2^63-1
- keep ranges: 1..100000
- crop segments: 1..100000
- Evidence rows per segment: 1..32

The maxima are schema/contract bounds only, not memory or runtime admission.

## Negative matrix

- weak Asset name or digest-only checksum
- bool/zero/oversized dimensions or frames
- non-portrait target or source/target frame-rate mismatch
- crop outside source or aspect mismatch
- keep range overlap/out-of-source
- missing/extra/gapped/overlapping proposal partition
- duplicate/unsorted/malformed Evidence row
- string laundering into closed enum fields
- UNKNOWN/stale/revoked Evidence promoted ready
- tampered plan body retaining old hash
- max+1 ranges/segments/Evidence
- path/raw bytes/runner/callback/filesystem/process/network/provider/renderer surface
- Remotion compatibility treated installed/executable
- plan treated Human approval, render, Timeline mutation or publication authority

## Builder / Completeness Critic

Finding: source gaps created by TASK-007 cuts must not be rejected as ordinary discontinuity, but must also never disappear from closure accounting.

Correction: serialize the exact keep-range set, require ordered non-overlap, and require proposals to partition every keep range exactly. Rebuild a separate contiguous output range projection.

Residual C/H/M: `0/0/0`.

## Security / Authority Critic

Finding: a symbolic `REMOTION` target can be mistaken for dependency availability or execution authority.

Correction: the target is `PROVIDER_NEUTRAL`; `remotion_compatibility=CONTRACT_ONLY_UNPROVEN`, with explicit false execution/write predicates and no effect-capable API surface.

Residual C/H/M: `0/0/0`.

## Operations / Compatibility Critic

Finding: float crop ratios and independent output frame rates create cross-platform drift.

Correction: validate ratios by integer cross multiplication and require exact canonical `FrameRate` equality. R0 supports square-pixel sources only; non-square-pixel admission remains a later versioned Gate.

Residual C/H/M: `0/0/0`.

## Independent Judge

- exact source/Edit Plan/target/Evidence binding: PASS
- deterministic partition/crop/output projection: PASS
- schema mirror and non-self digest design: PASS
- provider-neutral/no-effect boundary: PASS
- downstream Human/render/Timeline authority isolation: PASS
- focused + affected regression: `75 PASS`
- full WSL2 regression: `1560 PASS / 1 intentional Windows-only skip`
- compileall / schema mirror / git diff check: PASS
- unresolved C/H/M: `0/0/0`

`JUDGE=PASS_LOCAL_PENDING_HOSTED_EVIDENCE`
