# TASK-014 — Qwen3-TTS Runtime Artifact Manifest Contract R0 Evidence

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / CONTRACT_FROZEN / COMMIT_READY / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Purpose and boundary

This Atomic Unit freezes a pure, no-I/O transport and semantic contract for a
future complete Windows runtime artifact manifest. It does not publish an
accepted production manifest, pin an accepted semantic digest, inspect `E:`,
start target Python, resolve/download/install packages, import Qwen/PyTorch,
load a model, read Owner audio or execute a native media tool.

The contract is fixed to `WINDOWS / win_amd64 / cp312 / Python 3.12.4`. It
represents the future trust chain:

```text
official or Owner-accepted retained artifact
→ exact artifact bytes and provenance
→ distribution metadata / RECORD / payload inventory
→ installed runtime file or explicit system prerequisite ownership
→ later diagnostic verifier
```

Installed-tree self-hashes, package version strings, pip reports and
`pip check` are not trust anchors. A manifest that satisfies this contract is
still not accepted merely because it is self-consistent.

## Contract

The strict manifest binds:

- bounded public artifact coordinates, source, size, SHA-256, provenance,
  provider-host allowlist, Windows-compatible wheel tags and closed kind/load
  policy;
- local-build wheels and native-tool archives only with source/build-matrix
  hashes and `same_machine_only=true`;
- exact distributions, dist-info/RECORD and payload-inventory digests;
- a bounded PEP 508 requirement subset (including legal internal whitespace)
  whose version grammar is deliberately limited to numeric releases plus an
  optional local suffix; prerelease/dev/post/epoch forms fail closed in R0;
  normalized dependency name, resolved-version satisfaction, case-sensitive
  non-version marker comparison, exact marker expression, fixed Windows/cp312
  marker-environment digest and recomputed active/inactive result; active edges
  have complete root reachability and an acyclic dependency graph;
- every runtime file to exactly one retained artifact or one named host
  OS/hardware-driver exclusion, with a domain-separated archive/RECORD member
  to installed-file mapping digest;
- Python/support/distribution/native/tool roles and exact ffmpeg/ffprobe/SoX
  ownership; exactly one `Scripts/python.exe`; and an ffmpeg/ffprobe pair from
  the same retained tool artifact;
- the exact merged Qwen locked-wheel diagnostic schema, official wheel
  filename/size/SHA-256 and trusted payload-inventory digest instead of
  duplicating its canonical member list; the referenced observation remains
  non-capability and cannot grant post-return authority;
- exact counts and a domain-separated canonical semantic digest;
- fixed no-effect and non-authority fields.

Absolute paths, private runtime roots, credentials, Owner media coordinates and
secret values are forbidden. URLs must be public HTTPS artifact coordinates
without userinfo, query or fragment data.

## Authority semantics

The manifest always records:

- `status=CONTRACT_ONLY_UNACCEPTED`;
- `diagnostic_only=true`;
- `persistent_manifest_is_capability=false`;
- `runtime_reuse_authorized=false`;
- `model_load_authorized=false`;
- `consumer_execution_authorized=false`;
- `post_return_state_guaranteed=false`;
- `consumer_revalidation_required=true`.

Its ordinary SHA-256 proves canonical-body consistency only. It does not prove
manifest origin, artifact authenticity, current installed state or execution
authority.

## Architecture result

The DEV-4 Architecture/Judge review selected this no-I/O contract as AU2C1 and
reported unresolved `Critical / High / Medium = 0 / 0 / 0` for the design.
Actual runtime or artifact observation remains `NO-GO` until a separate AU2C2
binds the full official/Owner-accepted direct and transitive artifact closure
and exact private roots without broad search.

## Implementation and verification

Allowed scope is exactly five files:

1. pure parser/compiler module;
2. public JSON Schema;
3. byte-identical packaged schema mirror;
4. focused tests;
5. this Evidence.

Observed verification:

- focused pytest: `63 / 63 PASS`;
- related TASK-014 runtime diagnostic regression: `161 / 161 PASS`;
- Python compile: `PASS`;
- Draft 2020-12 schema and byte mirror: `PASS`;
  - mirror SHA-256:
    `690c508b4f9fd6a6204edf8bfe4ae80b5dab42f0100f339e5d89b303c4162097`;
- diff/scope check: `PASS`;
- existing isolated pytest/jsonschema dependency was reused read-only; no package
  install or dependency resolution occurred;
- independent Tester: `PASS / Critical 0 / High 0 / Medium 0`;
- independent Critic/Judge: `PASS / Critical 0 / High 0 / Medium 0`.

## No-effect record

- filesystem/model/runtime artifact read: `false`;
- persistent filesystem write outside the five repository files: `false`;
  two transient self-created `py_compile` cache files were removed after the
  compile check;
- network/provider access: `false`;
- dependency resolution/download/install: `false`;
- target Python/package import: `false`;
- model load/inference/audio/native tool execution: `false`;
- Owner audio/private media access: `false`.

## Next gate

AU2C2 must capture and independently review the exact retained artifact
coordinates for CPython, every direct/transitive distribution, wheel-owned
native libraries and ffmpeg/ffprobe (plus SoX only if the admitted Qwen path
requires it). Missing artifacts produce `RETAINED_ARTIFACT_MISSING` and park a
separate acquisition AU; they do not authorize automatic download or install.
