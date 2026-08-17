# TASK-046 / P-VS-4B Gate 4 — Bounded Runtime Adapter R0

## Outcome

Gate 4 R0 implements the smallest safe runtime step after the body-free Gate 3
workflow contract.  It can inspect and deterministically assemble only approved
synthetic, non-Owner WAV fixtures.  It cannot train a model, run inference,
adopt a Dataset/Asset, use Owner audio, or publish a Master.

## Exact implementation boundary

- `WavInspectionReceipt` records bytes, SHA-256, exact sample count and the
  canonical 48 kHz / mono / PCM 24-bit facts without an absolute path or body.
- `SyntheticMasterAssemblyRequest` binds the Gate 3 workflow/model/profile/
  assembly-policy hashes, ordered unique Cue hashes, inspection receipt hashes,
  bounded pause samples and one contained logical output reference.
- `SyntheticMasterAssemblyReceipt` proves atomic output read-back and exact
  frame arithmetic.  Boundary, loudness and style analysis remain `UNKNOWN`;
  the adapter never invents their PASS.
- Runtime roots are passed out of band.  Relative containment, existing-target
  rejection, symlink/reparse rejection, source hash read-back and bounded frame
  caps are mandatory.
- The only authority accepted by R0 is
  `APPROVED_SYNTHETIC_TEST_AUTHORITY`.  `owner_audio_used` and every Dataset,
  training, inference, Asset adoption and publication effect flag remain false.

## Explicit exclusions and next Gates

Dataset preparation, P-VS-3B adoption, P-VS-4A Training dispatch, an admitted
engine recipe, model inference, real style analysis, Owner listening acceptance,
TASK-014 production narration and installer/Release are not implemented here.
Owner recordings must not enter this adapter until a separate exact authority
and current Consent/rights/quality bindings are supplied.

The R0 pause policy is an exact integer number of silence samples after each
non-final Cue.  Crossfade, loudness normalization and boundary repair are not
silently approximated.  Their analyzer/policy states stay `UNKNOWN`.

## Acceptance inventory

- canonical WAV inspection and integer-sample duration;
- 44.1 kHz, stereo and 16-bit rejection;
- ordered Cue and inspection receipt binding;
- deterministic 48 kHz / mono / PCM 24-bit Master assembly;
- exact pause insertion and total-frame cap;
- source mutation after inspection rejection;
- receipt swap, duplicate Cue/source and non-contiguous order rejection;
- absolute, parent traversal, missing parent, existing output and symlink
  rejection;
- schema/runtime/mirror parity, digest tamper and unknown-field rejection;
- public projection excludes paths and hashes;
- static no-network/no-process/no-model-training surface.

## Critic pass 1 — Builder and compatibility

The adapter uses the Python standard library `wave` container reader/writer and
the repository canonical serialization helpers.  It adds no package import or
`__init__` surface.  Gate 3 types remain immutable.  WAV bodies exist only
during a bounded synthetic runtime call and are never serialized.  Finding:
the final Cue must not add trailing silence; enforced in validation.

## Critic pass 2 — Security and authority

Absolute/private paths are absent from records.  Caller roots must already
exist, parents are resolved under the root, existing outputs and symlink/reparse
components fail closed, and the output is published with a same-directory
temporary file plus atomic replace.  Only a new target is allowed.  No network,
subprocess, model, Dataset, training, Owner-audio or publication authority is
exposed.  Analyzer results remain `UNKNOWN`.  Residual Critical/High/Medium:
`0 / 0 / 0` after tests.

## Readiness Judge

- BOUNDED_SYNTHETIC_WAV_RUNTIME: PASS after focused and full validation.
- OWNER_AUDIO / DATASET / TRAINING / MODEL_INFERENCE: BLOCKED, separate Gate.
- MASTER_NATURALNESS / STYLE / LOUDNESS ACCEPTANCE: UNKNOWN, analyzer and Owner
  listening Gate not executed.
- RELEASE / DEPLOY / PRODUCTION: NOT AUTHORIZED.

