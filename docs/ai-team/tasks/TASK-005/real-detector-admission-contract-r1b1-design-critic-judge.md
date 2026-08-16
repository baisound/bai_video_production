# TASK-005 R1B1 — Real Detector Admission Contract

## Authority and binding

- Authorization: `BVP-AUTH-20260816-TASK005-R1B1-REAL-DETECTOR-ADMISSION-CONTRACT-01`
- Base: `dafcea762ca7ce4a6437033bf407695cccc9860d`
- Branch: `codex/task-005-real-detector-admission-contract-r1b1`
- Integration Lock: `BVP-ILOCK-20260816-TASK005-R1B1-CHANGELOG-01`
- Scope: exact five files; dependency, schema, export, version and package changes `0`
- Runtime candidate: `NONE`; Native H3: `PARKED`

## Design

The contract separates seven candidate families, seven admission states,
twelve Evidence kinds and five current-valid states. A real-detector Evidence
claim immutably binds one candidate family, exact R0 `DetectorProfile`, Evidence
kind, finalized receipt digest, authority-scope digest and validity. Claims are
bounded to twelve, unique by kind, and supplied in canonical enum order.

The pure evaluator derives the exact missing-Evidence set. License and
distribution gaps yield `LICENSE_REVIEW_REQUIRED`; identity, version, artifact,
provenance, dependency, platform or offline-materialization gaps yield
`ACQUISITION_GATE_REQUIRED`; runtime-capability, resource-bound or normalized
output gaps yield `CAPABILITY_EVIDENCE_REQUIRED`. A stale, revoked, conflicted
or unknown constituent yields `UNKNOWN`. Only the complete exact twelve-row
`CURRENT_VALID_JUDGED` set can yield `ADMITTED`.

`DetectorAdmissionDecision` cannot be directly constructed by a caller; an
internal construction token forces all decisions through the evaluator. The
decision digest covers canonical JSON excluding only its own digest. The R0
profile vector binds the canonical configuration
`{"filter":"scene","frame_mapping":"integer_index_v1","threshold_milli":400}`
to `sha256:73b87e3c9ac24f183b12944ca57733e324994ca989042f4c2242fe57725a3162`.

## Candidate and authority boundary

`FFMPEG_SCENE_FILTER_PROFILE_FAMILY` is the selected contract family only.
`selected_runtime_candidate` is always null; runtime authorization, media read
and external effect are always false. FFprobe metadata and FFmpeg silence
detection are explicitly not Scene detectors. PySceneDetect and OpenCV remain
unselected families requiring the same exact Evidence closure. UNKNOWN cannot
carry placeholder Evidence.

Names, executable paths, PATH presence, package names, observed hashes or local
availability cannot substitute for artifact identity, provenance, license,
distribution permission, capability or current-valid Judge Evidence. This unit
does not accept a path, raw bytes, runner, callback or filesystem handle and has
no filesystem, subprocess, network, media, Provider, model or native-runtime
surface. R0 range/hash/schema compilation and R1A synthetic behavior are reused
unchanged and are not duplicated.

## Builder / Completeness Critic

- closed enums and exact Evidence ordering make missing-set classification total;
- the claim maximum equals the twelve-kind registry and max+1 rejects;
- source profile, candidate and authority scope cannot be borrowed across claims;
- direct decision construction is rejected, so `ADMITTED` requires evaluator closure;
- canonical JSON and non-self digest are deterministic.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Security / Authority / License Critic

- contract admission never grants runtime, acquisition, install, media-read or execution authority;
- license and distribution Evidence remain distinct from provenance and capability;
- stale, revoked, conflicted and unknown Evidence fail closed;
- receipt and scope digests are bindings, not proof of bytes or issuing authority;
- Human license acceptance, Provider choice and Native H3 are not inferred.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Operations / Compatibility Critic

- Python 3.11–3.13 compatible standard-library implementation;
- new dependency, package export, schema, workflow and runtime integration changes `0`;
- retained state is a bounded immutable twelve-row tuple plus canonical projections;
- R0/R1A public APIs and blobs remain unchanged;
- all runtime, acquisition, platform-capability and real-media checks remain separate Gates.

Result: `PASS`; residual Critical/High/Medium `0/0/0`.

## Verification and independent Judge

Promotion requires focused R1B1 plus R0/R1A tests, deterministic digest,
missing-set precedence, stale/revoked/conflicted/unknown, cross-binding,
max/max+1, direct-construction and forbidden-surface negatives, compileall,
proportionate Windows/WSL2 full regression, exact five-file scope, `git diff
--check`, terminal hosted checks and fresh base/head/Lock/overlap closure.

Local verification result:

- focused R1B1 + R0/R1A regression: `57 passed`;
- Ubuntu/WSL2 full regression using the existing offline test environment:
  `1339 passed, 1 skipped` (the Windows-only Inno Setup contract skip);
- Windows and WSL2 compileall: `PASS`;
- the bundled Windows Python runtime has no pytest package, so no dependency was
  installed; hosted Windows checks remain the required platform Gate;
- exact five-file scope and R0/R1A blob immutability: `PASS`;
- dependency install/download, media read, runtime and external effect: `0`.

The independent Judge may return PASS only with unresolved Critic
Critical/High/Medium `0/0/0`. Passing R1B1 establishes only a no-effect
admission contract; acquisition, install, execution, real media, Human license
acceptance, downstream editing/generation, Release and Deploy remain separate
authorization Gates.

Current pre-hosting result:
`PASS_LOCAL_READY_FOR_ATOMIC_COMMIT_AND_DRAFT_PR`.
