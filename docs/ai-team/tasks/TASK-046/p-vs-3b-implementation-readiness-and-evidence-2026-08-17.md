# TASK-046 / P-VS-3B implementation evidence — 2026-08-17

## Authority and scope

This unit implements the previously approved P-VS-3B body-free metadata
contract so the Owner-requested OBS-WAV Model Builder can later consume a
canonical `TrainingInputSnapshot`.  It performs no Dataset, Asset, store, Job,
Training, Model or publication effect.

Implementation base: `origin/main@d99d0bc038a16dd03d14ef1489570f9ba46f8645`.

Exact files:

1. this Evidence document;
2. `schemas/voice-dataset-revision.schema.json`;
3. the byte-identical schema-resource mirror;
4. `src/ai_video_production/voice_dataset_revision.py`;
5. `tests/test_task046_voice_dataset_revision_contract.py`.

The open TASK-036 proposal-revision PR has zero path overlap.  `CHANGELOG.md`,
Registry, roadmap, workflow, `__init__.py` and existing dependency files are
unchanged in this implementation commit.

## Canonical serialized types

- `VoiceDatasetStore`
- `VoiceDatasetCommitIntent`
- `VoiceDatasetRevision`
- `VoiceDatasetMembershipEntry`
- `DatasetMemberExclusion`
- `DatasetCandidateReviewBinding`
- `DatasetAdoptionReceipt`
- `VoiceDatasetCommitEnvelope`
- `DatasetStorePersistenceCapabilityBinding`
- `StoreCommitBinding`
- `DurableDatasetAdoptionJobBinding`
- `DatasetReadinessCoverageIndicator`
- `TrainingInputSnapshot`

The public Python types freeze their validated nested metadata.  The schema and
runtime validators both reject unknown root fields.  Digests use the existing
repository `sha256:<64 lowercase hex>` convention and canonical JSON helper.

## Correctness boundaries

- `VoiceDatasetStore` is restored as the authoritative root metadata shape.
  `store_generation` is the only CAS generation counter; `store_revision` is
  rejected.
- Revision 1 binds a recomputed, context-complete empty-store digest and exact
  generation/head/latest/count preimage.
- Revision 2 and later require generation, head, latest, count and full-store
  digest expectations together.
- the acyclic order is Intent → Revision → Receipt → Envelope.  Receipt has no
  Envelope reverse reference.
- `VERIFIED_COMMITTED` requires atomic CAS plus matching authoritative
  read-back.
- an unobservable timeout is `UNKNOWN`; a mismatch or invalid graph that was
  actually read is `CORRUPT_OR_INCOMPLETE` and is not weakened to UNKNOWN.
- existing success is accepted only when the exact valid Envelope is the head
  or a valid ancestor of the current canonical head.  An orphan/fork is
  `CONFLICT`.
- `StoreCommitBinding` has only `BOUND_VERIFIED | MISMATCH | UNKNOWN`.
  Pre-persistence capability is represented separately by
  `DatasetStorePersistenceCapabilityBinding`.
- the pure module validates externally supplied facts.  It has no API that
  writes a store or issues an authoritative committed Receipt/Binding.
- TASK-003 unresolved Asset mapping cannot carry invented Asset fields.
- Dataset adoption Job identity cannot be reused as PROJECT_MAINTENANCE or a
  Training Job identity.
- `TrainingInputSnapshot` stores no body and grants no Dataset mutation or
  Training authority.

## Validation

Validation results at the current checkpoint:

- focused contract tests: `13 passed`;
- Windows full regression: `1736 passed, 1 skipped`;
- WSL2 full regression using the existing offline venv:
  `1736 passed, 1 Windows-only installer skip`;
- public/schema-resource mirror: byte exact;
- Python 3.12 compile: PASS.

The focused set covers empty/normal CAS, body-free records, TASK-003 unresolved
binding, immutable TrainingInputSnapshot, UNKNOWN versus observed corruption,
atomic read-back, canonical ancestor inclusion, orphan conflict, Receipt DAG,
Job identity separation, digest tamper and schema-mirror parity.  The JSON
Schema validates representative canonical records through its 13-type union.

Hosted checks remain required before merge.  A product source change also
requires the repository's serialized CHANGELOG integration policy; no shared
CHANGELOG write is attempted while the TASK-036 PR is open.

## Critic pass 1 — Builder and domain

Initial findings:

1. **High — repository checksum convention mismatch.** Test vectors initially
   used bare 64-hex strings while the canonical helper requires the
   `sha256:` prefix.  Corrected in runtime tests and public schema.
2. **Medium — frozen dataclass still exposed a mutable dictionary.** Corrected
   with recursive frozen mappings/tuples plus thawed copies from `to_dict()`.
3. **Medium — non-empty store generation could diverge from revision count.**
   Corrected by requiring exact equality and matching head/latest/index.

Post-correction residual Critical/High/Medium: `0 / 0 / 0`.

## Critic pass 2 — Security and compatibility

- raw audio/text/path/credential fields: absent;
- filesystem/network/process/subprocess/store mutation surface: absent;
- Dataset/Training authorization flags: exact false;
- unknown fields and reverse Envelope reference: rejected;
- observed corruption cannot be mislabeled UNKNOWN;
- idempotency success cannot be inferred from cache/preimage/orphan history;
- existing P-VS-1A/P-VS-3A/P-QC/TASK-003/TASK-043 files: unchanged;
- schema mirror: byte exact at validation time.

Residual Critical/High/Medium: `0 / 0 / 0`.

## Judge

- DOMAIN_READINESS: `PASS`.
- PURE_METADATA_IMPLEMENTATION: `PASS_LOCAL_WINDOWS_AND_WSL`.
- DATASET_STORE_RECEIPT_JOB_TRAINING_EFFECT: `BLOCKED / NOT_AUTHORIZED`.
- OBS-WAV Model Builder dependency: P-VS-3B layer is implemented locally;
  P-VS-4A and P-VS-4B remain later, separate units.
- Merge readiness: conditional on fresh-main integration, exact-five diff,
  full regressions, serialized CHANGELOG, hosted checks and post-merge checks.
- Residual Critical/High/Medium: `0 / 0 / 0`.
