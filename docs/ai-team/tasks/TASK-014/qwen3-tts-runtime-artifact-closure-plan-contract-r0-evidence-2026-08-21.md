# TASK-014 — Runtime Artifact Closure Plan Contract R0 Evidence

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / COMMIT_READY / CONTRACT_ONLY / NETWORK_BLOCKED / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`
Base: `main@56337d343a2fc16ba76f9f0891261f4b369972c6`

## Atomic Unit

This is `AU2C2B1a`, the no-I/O closure-plan contract beneath the accepted
AU2C2B design. It freezes canonical request-observation, candidate-snapshot,
constraint, proposed-selection, digest and authority shapes before the actual
deterministic resolver engine is implemented.

This Unit does not claim to have solved dependency closure. Its strongest state
is `CONTRACT_ONLY_UNRESOLVED`. Candidate snapshots are unauthenticated,
selections are explicitly `CALLER_PROPOSED_UNVERIFIED`, and all of these fields
are parser/schema-enforced false:

- `candidate_snapshots_authenticated`;
- `deterministic_selection_verified`;
- `active_dependency_closure_verified`;
- `plan_review_accepted`;
- `acquisition_eligible`.

The next `AU2C2B1b` must bind an independently accepted exact `packaging`
parser artifact and implement the deterministic selection/closure algorithm.
Until then this contract cannot be used as a Stage A plan, acquisition input,
runtime gate or execution authority.

## Exact scope

Only these five new files belong to the Unit:

1. `src/ai_video_production/qwen3_tts_runtime_artifact_closure_plan.py`
2. `schemas/qwen3-tts-runtime-artifact-closure-plan.schema.json`
3. `src/ai_video_production/schema_resources/qwen3-tts-runtime-artifact-closure-plan.schema.json`
4. `tests/test_task014_qwen3_tts_runtime_artifact_closure_plan.py`
5. this Evidence file

No existing production source, dependency declaration, runbook, manifest,
runtime, model, Owner media or TASK-036 shared path was changed.
The PR additionally updates the existing `CHANGELOG.md` as required by the
repository release-metadata check; that mechanical release note is not part of
the five-file contract implementation boundary.

## Contract results

- semantic plan digest and volatile observation-receipt digest are domain
  separated;
- semantic projection excludes timestamp and volatile transport timing;
- observations, candidate records, snapshots, constraints and proposed
  selections use canonical ordering;
- observation provenance has exact observer id/revision/digest coordinates and
  closed `PROJECT_INDEX_GET`, `PROJECT_RELEASE_GET`,
  `METADATA_SIDECAR_GET`, `ARTIFACT_HEAD`, `CHECKSUM_ASSET_GET` and
  `UPSTREAM_REFERENCE_GET` provider/role/method/content/count contracts;
- B1a accepts synthetic observations only and requires
  `transport_policy_passed=false`; a Mapping caller cannot claim bound-network
  provenance or transport PASS;
- URLs are anonymous, query-free, fragment-free, port-free HTTPS coordinates
  from the closed provider host set;
- qwen and ordinary Python distribution candidates are owned by PyPI, torch
  and torchaudio are owned only by the PyTorch index, the exact Python runtime
  candidate is owned by Python.org, and the BtbN tool candidate is owned by its
  GitHub release project;
- the tagged union represents distribution wheels, the Python installer and a
  native-tool archive, with exact provider/kind/extension/metadata rules;
- each candidate separately binds its candidate-bearing index/release
  observation and artifact HEAD observation; wheels additionally bind the
  exact metadata observation/hash/byte count, while the BtbN archive binds a
  checksum observation, the exact BtbN repository/release/tag/asset shape,
  upstream FFmpeg version/commit observation, build-configuration digest and
  the unresolved exact `FFMPEG` + `FFPROBE` same-archive member requirement;
- yanked/prerelease/development values and version classification remain
  explicitly `CALLER_REPORTED_UNVERIFIED`; B1a does not claim that caller
  metadata has been semantically checked;
- candidate-set digest, exact all-candidate snapshot union, project/provider/
  index/observation/count binding, project closure and proposed-selection
  membership are revalidated by the strict parser; every request observation
  must be referenced by an exact candidate coordinate, so unrelated synthetic
  observations cannot enter the receipt;
- HEAD versus GET byte truth, the 4 MiB metadata-sidecar cap, lowercase-host
  ASCII/query-free URL canonicality and aggregate
  requirement/snapshot/canonical-body limits fail closed in the compiler,
  parser and public helper boundary;
- native SoX executable state is fixed to `UNKNOWN` for this metadata-only
  contract;
- all capability, network, download, install, runtime reuse, model, consumer
  execution and post-return authority fields remain false;
- all effect flags remain false;
- ordinary SHA-256 proves canonical self-consistency only, not provenance,
  authenticity, freshness or Authority.

## Executed verification

Existing isolated development runtime only; no new installation occurred.

- `py_compile` for module and focused test: `PASS`;
- schema JSON parse: `PASS`;
- public/resource schema byte mirror: `PASS`;
- `git diff --check`: `PASS`;
- first focused run: `34 PASS / 1 FAIL`; the failure was a test-order defect
  that attempted to hash an intentionally inadmissible candidate before
  asserting its rejection; production implementation was unchanged;
- final focused contract suite: `59 PASS / 0 FAIL` in `3.52s`;
- final focused plus merged AU2C1 manifest regression after both DEV-4
  failure-fix cycles: `122 PASS / 0 FAIL` in `4.03s`;
- closure plan plus the merged runtime manifest, pinned-snapshot verifier,
  installed-tree observer and locked-wheel session trust-chain regression:
  `215 PASS / 0 FAIL` in `10.51s`.

Current file hashes after the final run:

- module SHA-256:
  `099fc9a94324b32e731dbb34e710a7c02e70254c607e97e0b5425cc0a551e8f1`;
- public and packaged schema SHA-256:
  `f0c63bc91836e91591db95e79cdc989a676bba87088b9594959aeb6628f42d90`;
- focused test SHA-256:
  `eb308e54d538d9c083e6e7f0fd7dcec86779dc3e376e61c601fa535738c7afa3`.

Independent DEV-4 closeout:

- Tester: `PASS / C0 H0 M0`;
- Critic/Judge: `PASS / C0 H0 M0`;
- explicit five-file stage, commit and PR: `GO`;
- actual metadata network, artifact download, install, runtime, model, audio and
  E: access: `NO-GO / OUTSIDE THIS ATOMIC UNIT`.

## No-effect record

- metadata network access: `false`;
- artifact body download: `false`;
- E: filesystem access: `false`;
- file write outside this exact repository Unit: `false`;
- package install/update: `false`;
- target Python/package import: `false`;
- model body read/load: `false`;
- Owner audio read: `false`;
- inference: `false`;
- ffmpeg/ffprobe/SoX/native effect execution: `false`;
- TASK-043 dispatch or Product authority effect: `false`.

## Gates and next completion condition

This Unit is complete only after independent Tester and Critic/Judge report
`C0 / H0 / M0`, exact five-file scope remains clean, and commit/PR merge.

`AU2C2B1b` completes when the accepted parser coordinate, deterministic
PEP 508/440/tags resolver, candidate selection, active dependency closure and
negative matrix are implemented and merged. Actual metadata network observation
still requires a separately rebound exact network Authority. Artifact body
download, installation, target runtime execution, model load, Owner audio and
inference remain blocked.
