# TASK-052 R5C1 — Status Effect Teacher Backend

## Boundary

R5C1 extends the canonical Visual Training manifest and Safe Visual Learning
backend for positive/negative Status Effect icon samples. R5C2 owns operator UI,
Gold/review and R3C temporal wiring. No Provider, Production Timeline, Release or
Deploy effect is authorized.

## Contract

- domains are `STATUS_EFFECT_POSITIVE` and `STATUS_EFFECT_NEGATIVE`;
- labels use the R5B canonical codec;
- same-polarity identity/visibility samples are positive Teacher rows;
- `PERK_ICON/<perk_id>` and opposite-polarity identity rows require the explicit
  `hard-negative` group;
- opposite-polarity visibility and same-polarity hard-negative rows are rejected;
- identity labels must resolve to an R3C `StatusEffectDefinition` whose polarity
  agrees with the label;
- status samples do not carry Survivor-subject or Killer-specific Teacher fields.

Safe Visual Learning accepts only the matching positive/negative region or its
`/segment_<ordinal>` crop ROI, revalidates staged receipts at confirmation, and
normalizes hierarchical ROI IDs into a single safe preview filename. Index build
requires identity and hard-negative coverage and constructs an R5B recognizer
before publication, which also rejects unregistered identities, feature-label
conflicts and registry polarity contradictions.

## Verification

- R5B/R5C1/Safe Visual Learning focused: `16 PASS`;
- TASK-050/TASK-052 affected regression: `179 PASS`;
- TASK-051 compatibility/source-gate regression: `118 PASS`;
- compileall and diff-check: `PASS`;
- unresolved Critical/High findings: `0 / 0`.

Synthetic/reference evidence does not establish production accuracy. R5C2 and
R8/R9 retain Human Gold and packaged real-media gates.
