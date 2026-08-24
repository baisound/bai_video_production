# TASK-054 R4C Dataset Split/Duplicate/Leakage Audit

R4C is a pure DEV-3 Evidence unit. It re-admits R4A/R4B records, audits source
group and Match split isolation, exact corrected-transcript duplicates and
32-character normalized cross-split phrase overlap. Findings retain IDs, split,
stable kind and a digest only; transcript bodies are not copied into the report.
PASS is Evidence only and state remains `EVIDENCE_ONLY_NO_ADOPTION`. Fewer than
two represented splits is NOT_CONFIRMED. No Dataset adoption, media I/O, training,
Provider execution or Product activation occurs.

## Canonical boundary

The auditor accepts only exact re-admitted R4A rights manifests and R4B narration
candidates. It uses bounded inverted indexes instead of pairwise segment scans,
with ceilings of 2,048 segments and 250,000 normalized transcript characters.
The canonical report binds the exact audited R4B candidate set by digest. Its
Schema is mirrored in Product resources and exact re-admission rejects checksum
tampering, unknown fields, invalid segment IDs,
same-split findings, invalid counts and non-canonical ordering.

## Result semantics

`FAIL` means one or more cross-split findings exist. `PASS` requires at least two
represented splits and no finding. One represented split is `NOT_CONFIRMED`.
None of these states grants Dataset adoption or training authority.

## Verification

R4C/R4B/R4A focused tests: `27 PASS`. TASK-054 plus direct TASK-049 and OSS
boundary regression: `610 PASS`. Compile and Schema mirror checks pass. Final
