# TASK-052 R5B — Status Effect Identity, Polarity, Source and Visibility

## Decision

R5B owns the deterministic boundary from one R5A segmented icon crop to a
body-free status-effect recognition record. It does not own temporal
appearance/disappearance, Teacher UI mutation, Human Gold acceptance, CGEL
event creation, Provider execution or Production Timeline mutation.

## Canonical contracts

- R3C `StatusEffectDefinition` remains the canonical registry record for
  `effect_id`, polarity, source kind and Survivor scope. R5B does not create a
  second status-effect registry.
- Positive identity labels use
  `STATUS_EFFECT_POSITIVE/<effect_id>`; negative identity labels use
  `STATUS_EFFECT_NEGATIVE/<effect_id>`.
- Visibility labels use
  `STATUS_EFFECT_POSITIVE|NEGATIVE/VISIBILITY/<visibility>`.
- Perk hard negatives use `PERK_ICON/<perk_id>`. An opposite-polarity Status
  Effect match is a contradiction, not an identity result.
- Reference identities must exist in the R3C registry and their namespace
  polarity must agree with the registry. Source kind is resolved from the
  registry rather than trusted from a Teacher label.

## Recognition and Evidence

`StatusEffectIconRecognizer` applies the existing deterministic reference-slice
classifier to each R5A crop. The output separates:

- `IDENTIFIED`;
- `VISIBILITY_ONLY`;
- `HARD_NEGATIVE`;
- `ABSTAINED`;
- `CONTRADICTION`.

Only `IDENTIFIED` may carry `effect_id` and a non-UNKNOWN source. Only that
state may create an active `StatusEffectObservation` for the existing R3C
temporal machine. All other states retain Evidence and refuse temporal identity
projection.

Recorded-video integration preserves both the R5A region segmentation result
and the R5B recognition record. Recognition records contain no image body. The
region/polarity/ordinal must refer to an actual segmented candidate, and the
candidate crop SHA-256 is revalidated against the exact recrop before
classification.

## Fail-closed boundaries

- unknown or ambiguous reference match: `ABSTAINED`;
- Perk reference match: `HARD_NEGATIVE`;
- positive/negative namespace crossing: `CONTRADICTION`;
- unregistered effect or registry polarity mismatch: recognizer construction
  fails;
- identical feature with conflicting labels: recognizer construction fails;
- crop checksum mismatch: classification does not run;
- recognizer configured without R5A segmenter: recorded-video recognizer
  construction fails;
- recognition without a corresponding segmented candidate: frame contract
  construction fails.

## Verification

- R5A/R5B focused segmentation, label, registry, hard-negative, contradiction,
  checksum and recorded-video integration regression: `14 PASS`;
- TASK-049 DbD plus TASK-052 affected regression: `192 PASS`;
- TASK-050/TASK-051 compatibility regression: `186 PASS`;
- unresolved Critical/High Critic findings: `0 / 0`.

Production accuracy is not inferred from reference/synthetic tests. R5C owns
Teacher/Gold/review and R3C temporal wiring; R8/R9 retain held-out and packaged
real-media acceptance.
