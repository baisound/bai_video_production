# TASK-005 R1C0 — Artifact / Probe / Output Receipt Contract

## Authority and immutable boundary

- Authorization: `BVP-AUTH-20260816-TASK005-R1C0-EVIDENCE-CONTRACT-01`
- Base: `0475b7c5ed270a1321d32e1883b2c145aab83714`
- Branch: `codex/task-005-real-detector-evidence-contract-r1c0`
- Integration Lock: `BVP-ILOCK-20260816-TASK005-R1C0-CHANGELOG-01`
- Scope: exact five files; schema, export, dependency, version, package and
  workflow changes `0`
- R1C-A acquisition, R1C-B materialization, R1C-C no-media process probe,
  R1C-D synthetic-media probe and R1C-E real-media/Human acceptance authority:
  `0`
- Native H3: `PARKED`

This unit defines only immutable in-memory records and pure validation. It
creates no canonical artifact identity, publisher authority, license
clearance, installation, capability, output, admission, runtime, or next-stage
authority.

## Closed contract

### Artifact identity and comparison

`ExpectedDetectorArtifact` preserves issuer-side identity separately from
`ObservedDetectorArtifact`. Both bind one real candidate family, exact R0
`DetectorProfile`, coordinate ID, artifact kind, basename, version, platform,
architecture, byte count, hashes, and current-valid state. Expected identity
also binds publisher and provenance receipts; observed identity binds its
independent observation receipt.

Signature state is a closed `REQUIRED | NOT_APPLICABLE | UNKNOWN` enum.
`REQUIRED` needs a signature digest, `NOT_APPLICABLE` requires null, and
`UNKNOWN` prevents a complete expected identity. A path-like filename, invalid
hash, unknown candidate, unbounded byte count, or cross-candidate/profile/
coordinate comparison rejects.

The evaluator alone creates `DetectorArtifactComparisonReceipt`:

- both sides current, complete, and identical: `MATCH`;
- both sides current and any identity field differs: `MISMATCH`;
- expected only: `NOT_OBSERVED`;
- observed only: `OBSERVED_ONLY_UNBOUND`;
- incomplete or non-current constituent: `UNKNOWN`;
- both null: unconditional reject and no placeholder receipt.

MISMATCH is a current comparison fact but cannot support identity admission.
Absence and UNKNOWN never become negative or positive authority.

### Constituent receipts

The license/provenance receipt directly contains the exact typed artifact
comparison, resolved SPDX identity, license-text digest, provenance receipt and
distribution-policy receipt. `CLEARED` requires a current exact artifact
`MATCH`, current-valid judged Evidence, and a resolved SPDX value; `NONE` and
`NOASSERTION` cannot be cleared.

The materialization receipt directly contains the comparison plus dependency,
platform/architecture and materialization receipts. `VERIFIED_CONTAINED`
requires a current exact artifact `MATCH`; it records future Evidence but does
not perform or authorize installation.

The probe plan directly contains the comparison and a canonical unique subset
of five probe kinds. `NO_MEDIA` requires a null source binding and cannot plan
output normalization; `SYNTHETIC_MEDIA` and `REAL_MEDIA` require the exact R0
Asset checksum/frame-rate/total-frame `SceneSourceBinding` metadata. This is a
body-free identity binding, not media-read authority. The plan bounds timeout to 300,000 ms, each text output to
16,777,216 bytes, retained memory to 1,073,741,824 bytes, and normalized events
to 512. It contains no executable, command, arguments, path, runner, callback,
filesystem handle or media input. Plan records fix `execution_authorized` and
`media_input_authorized` false.

The probe receipt requires one result for every planned kind in exact order. A
current-valid receipt requires every outcome `PASS`; FAIL, UNSUPPORTED, TIMEOUT
and UNKNOWN require an exact incident code and cannot be erased by absence. A
probe receipt authorizes neither runtime nor its next stage.

Normalized events are typed `SCENE_CANDIDATE | INCIDENT | END`, bound to one
exact probe receipt, contiguous from ordinal zero, bounded by the plan, and
terminated by one final END. Candidate frames strictly increase and remain
inside the bound R0 source frame count.
Cross-family, cross-profile, cross-probe and reordered event borrowing rejects.
An INCIDENT can be preserved as Evidence but cannot support the R1B1
`OUTPUT_NORMALIZATION` claim.

### Exact R1B1 projection

`project_detector_evidence_claim` is the only R1C0-to-R1B1 mapping:

| R1C0 receipt | Supported R1B1 Evidence kinds |
|---|---|
| exact artifact MATCH | ARTIFACT_IDENTITY, VERSION_PIN, ARTIFACT_SHA256, PLATFORM_ARCH |
| cleared license/provenance | PROVENANCE, LICENSE, DISTRIBUTION_POLICY |
| verified contained materialization | DEPENDENCY_GRAPH, OFFLINE_MATERIALIZATION |
| exact PASS probe | RUNTIME_CAPABILITY, RESOURCE_BOUNDS |
| incident-free normalized output | OUTPUT_NORMALIZATION |

Every projection is one claim occurrence with the support receipt digest and
explicit authority-scope digest. Unsupported strengthening, non-current
support, missing probe kind, artifact MISMATCH, unresolved license, unverified
materialization, failed probe, or incident-bearing normalization rejects. The
existing R1B1 evaluator remains the sole missing-set/admission classifier; R0
ranges, manifest hash/schema validation, and R1A synthetic behavior are not
duplicated.

## Dependency and effect DAG

`expected + observed -> comparison -> license/materialization/probe plan ->
probe receipt -> normalized events -> typed R1B1 claim -> R1B1 admission`

Every arrow is data validation only. R1C-A through R1C-E each needs separate
future authority and a receipt never authorizes the next stage. Current actual
artifact, comparison, license, materialization, probe, event and claim rows are
all zero.

## Builder / Completeness Critic

- finding: downstream receipts initially accepted only a digest for the
  artifact comparison, allowing an unrelated digest to be asserted without
  typed lineage;
- correction: license, materialization and probe plans now contain the exact
  typed comparison and validate candidate/profile equality;
- finding: null signature initially conflated “not applicable” and “unknown”;
- correction: the closed signature-requirement enum and branch predicates make
  the distinction machine-checkable;
- finding: normalized event ordinals were initially probe-bound but not
  source-checksum/frame-domain bound;
- correction: media-mode branches now reuse the exact R0 `SceneSourceBinding`
  and cap every candidate frame to its total-frame domain;
- exact result/null partitions, caps/max+1, constituent ordering, terminal END,
  event lineage and all twelve R1B1 mappings are covered by negative tests.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Security / Authority / License / Privacy Critic

- expected metadata never overwrites observed identity and observation never
  creates publisher, signer, consent, license or expected identity;
- `CLEARED` is a typed received state, not inferred legal acceptance, and an
  unresolved SPDX value cannot be promoted;
- receipt digests bind metadata but do not substitute for artifact bytes or
  issuer authority;
- all runtime/effect flags remain false and the API exposes no path, raw bytes,
  process, filesystem, network, Provider, model, credential or media surface;
- stale, revoked, conflicted, unknown, missing, extra, mismatched and incident
  Evidence fails closed without auto-retry or next-stage authority.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Operations / Compatibility / Recovery Critic

- standard-library-only implementation targets Python 3.11–3.13;
- bounded tuples and byte/time/memory/event caps prevent unbounded contract
  populations; cap+1 rejects;
- canonical JSON uses the existing repository serializer and every receipt SHA
  excludes only its own digest;
- append-only receipt identities preserve mismatch, incident and nonterminal
  outcomes instead of repairing them downstream;
- package exports, schemas, dependencies, workflows, R0/R1A/R1B1 blobs and
  runtime integration remain unchanged.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Verification and independent Judge

Required gates are focused R1C0 plus R1B1/R1A/R0 regression, full repository
regression proportional to risk, Windows/WSL2 syntax/compile checks,
deterministic receipt hashes, null/mismatch/current-valid/license/cap/event/
strengthening negative tests, exact five-file scope, immutable predecessor
blobs, `git diff --check`, terminal hosted checks and fresh base/head/Lock/
overlap closure.

Local verification result:

- focused R1C0 plus R1B1/R1A/R0 regression: `74 passed`;
- full Windows regression: `1356 passed, 1 expected non-Windows skip`;
- Windows and WSL2 all-source/all-test syntax compilation: `382 / 382 PASS`;
- exact five-file scope, predecessor blob immutability and `git diff --check`:
  `PASS`;
- dependency install/download, artifact/materialization/process/media/runtime
  and external effect: `0`.

The first sandboxed full-test attempt could not access pytest's host temporary
directory and produced setup-only permission errors. The authoritative rerun
used the same existing offline test environment outside that sandbox, changed
no Product tree, and produced the full PASS above; no workflow exception or
test weakening was used.

The provisional independent Judge returns `PASS_READ_ONLY_CONTRACT` only when
all three Critic residual counts are `0/0/0`. That PASS establishes a no-effect
receipt contract only. It does not establish an actual artifact identity,
license clearance, installation, capability, normalized detector output,
runtime admission, process/media authority, Native H3 recovery, downstream
generation/editing, Release or Deploy.
