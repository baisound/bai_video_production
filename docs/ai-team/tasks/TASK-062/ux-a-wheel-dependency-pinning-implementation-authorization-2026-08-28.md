# TASK-062 UX-A Wheel Dependency-Pinning Implementation Authorization Candidate

## Decision and activation boundary

- Task: `TASK-062`
- Capability: `BVP-MONTAGE-DESKTOP-UX-001`
- Atomic Unit: `UX-A / WHEEL-DEPENDENCY-PINNING`
- Development profile: `DEV_4_FOUNDATION_CRITICAL`
- Review/fix budget: maximum `2` cycles, then Owner escalation
- Candidate state: `OWNER_APPROVED_PENDING_CANONICAL_METADATA_HOSTING`
- Implementation state: `NOT_STARTED / DEPENDENCY_BLOCKED`

The Owner approved preparation of this bounded `UX-A` authorization candidate
on 2026-08-28. It becomes implementation authority only after this exact
metadata commit passes independent DEV-4 Critic/Tester/Judge with unresolved
Critical/High `0/0`, Hosted checks, an exact Owner Ready/merge decision,
canonical-main merge/read-back, and post-main CI/Security. The later
implementation start additionally requires every dependency gate in this
record to be satisfied by exact immutable evidence.

Before those gates, source, packaging, schema, test, runtime, native, Product
Project, Timeline, Resolve, Release, Deploy, and Production mutation remain
unauthorized. This candidate activates no `UX-B` or `UX-C` work and does not
amend the immutable Owner allocation record dated 2026-08-27.

## Bound coordinates

- Accepted design commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- Accepted design SHA-256: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Canonical BVP base: `c2cf2324650257d7dc7cc2e84883bdc1cc577e67`
- Registry revision at preflight: `132`
- Active nonclosed integration lock: `BVP-INTEGRATION-LOCK-TASK058-A2-CANONICAL-READBACK-LOOKUP-CHANGELOG-20260828`
- Active lock allowed shared effect: `CHANGELOG.md` only
- `UX-A` metadata and future implementation overlap with the active lock: `0`
- Metadata branch: `codex/task-062-uxa-wheel-dependency-pinning-authorization`
- Branch/PR collision and open-PR exact-path overlap at preflight: `0/0`

Drift in the accepted design, canonical main, Registry, released asset,
dependency set, TASK-055 authority, this exact scope, or Task identity requires
a new read-only audit before implementation.

## UX-A dependency-pinning objective

Implement the BVP-owned, fail-closed package manifest, runtime lock, verifier,
and clean packaged-load preflight for one released
`ConsumerRuntimeService` wheel. BVP must independently verify the package,
dependency, resource, Python/ABI, license, and current TASK-055 coordinates
before any import or Product job can be admitted.

This Unit does not copy montage algorithms into BVP, change the external
package, accept a package because its self-report is consistent, create a
Product job, admit a review item, change a Timeline, apply to Resolve, publish a
release, or enable Production.

## Released wheel identity

Only this published asset is an authority candidate:

```text
repository=https://github.com/baisound/bai-davinci-montage-skills
release_tag=v0.7.0
release_commit_git_sha1=2a7cb0794439004499e3b8de3178c694a72013c2
release_asset_id=531768280
filename=bai_davinci_montage_skills-0.7.0-py3-none-any.whl
distribution=bai-davinci-montage-skills==0.7.0
size_bytes=83241
sha256=sha256:b66773e2082fd0bf60a5a77bb763859646c7143186bb00fbf18c2c4625248d6f
wheel_tag=py3-none-any
requires_python=">=3.11"
```

Observed local evidence is limited to:

- wheel `RECORD` entries: `56/56` digest and size PASS, missing/extra `0/0`;
- packaged resources: `25` files (`16` schemas, `7` contracts, `2` profiles);
- packaged resource-tree SHA-256:
  `f87c0b067cf1bae55cbe5185fc079b1ef0412febab7ca9700785903ca24e0010`;
- exact dependency candidate: `9` dependency wheels plus the root wheel;
- offline `--no-index --only-binary=:all: --require-hashes` install PASS on
  Windows `win_amd64`, Python `3.12.13`;
- installed distribution/version, import, resource preflight, and local
  `READY -> REVIEW_REQUIRED` runtime path PASS;
- `codex_required=false`, `paid_ai_subscription_required=false`, and
  `automatic_resolve_write_authorized=false`.

The observed Windows `cp312/win_amd64` dependency candidate is closed by
requirements-lock SHA-256
`4e16e187338717986aaf9f34dd7f60a81ba474b6ad522c6fdff6be8a6c04925a`:

| Distribution | Version | Wheel SHA-256 |
|---|---:|---|
| `attrs` | `26.1.0` | `c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309` |
| `jsonschema` | `4.26.0` | `d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce` |
| `jsonschema-specifications` | `2025.9.1` | `98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe` |
| `numpy` | `2.5.2` | `28ac63476ec7651484215ee7fa15a1f78b57c14621f01e392afe17b9a1390ce4` |
| `pillow` | `12.3.0` | `a2b55dd6b2a4c4b7d87ffa56bdb33fdc5fdb9a462173861a7bc097f17d91cb09` |
| `PyYAML` | `6.0.3` | `5fcd34e47f6e0b794d17de1b4ff496c00986e1c83f7ab2fb8fcfe9616ff7477b` |
| `referencing` | `0.37.0` | `381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231` |
| `rpds-py` | `2026.6.3` | `2c958bf94822e9290a40aaf2a822d4bc5c88099093e3948ad6c571eca9272e5f` |
| `typing-extensions` | `4.16.0` | `481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8` |

These versions and digests are observed candidates, not Owner-accepted Product
dependencies. Their filenames, sizes, tags, dependency edges, and license
identities must be frozen and independently revalidated before activation.

Two fixed-epoch local builds both produced an `83241`-byte wheel with SHA-256
`d47ea70e051207eeabbbad8f9a3932fdf344832b352e1a81a8b1d1c0a60b7263`.
Their `56` entry payloads are byte-identical to the released wheel, but the ZIP
container digest differs. These rebuilds are reproducibility evidence only;
they are not alternate accepted artifacts and never replace the published
`b66773e...` identity. Unavailable or unobserved rebuild coordinates are not
recorded as evidence.

## Current TASK-055 compatibility gap

Wheel self-integrity PASS does not establish compatibility with current BVP.
The released wheel embeds these TASK-055 contract SHA-256 values:

| Contract | wheel `v0.7.0` SHA-256 | BVP `c2cf232` SHA-256 |
|---|---|---|
| `bvp-montage-skill-input.schema.json` | `8a0d4d535c57252e3430fa8a40b8e358e78e2c1cf452629f09677ffce9e539b5` | `511945f24cffaf37b6b0b158e16c9af8fbbfeb2b1f3d4cb48bb4ec49a064ef76` |
| `montage-approved-plan.schema.json` | `e44912442e5eac5a5983132507b1cb2fd575658da2ab7d582e779ef134949f38` | `4bce10cf3a29578bde6e0d1708a7c07179ca2da7626220da72fa85cdf0684fa3` |
| `montage-human-edit-evidence.schema.json` | `8489338e877f6a5ebba5fecace92cc2d6abd2a56658071f08c6c80101c38d152` | `112d557f0a5e377a9049bfd3625f636165b47c888fcdd8a21f6255f463f09307` |
| `montage-preference-profile.schema.json` | `cc810c3540536c719947d4b48418278f76cb622bd7b99c99c42efe15d6dedb80` | `7d89b0973ca69fef66aadb49f913332dc6df7928c95709c7fb05725364bbb412` |
| `montage-proposal.schema.json` | `6ff1425c8293977c1753e28ad732caea0b7a2829ffca180dcff8c95a96f655c9` | `1b7f33b1af464c7c6f6fb9ecee35c3674d6f5b81e4ec16b1488f6eb3d6a48137` |
| `montage-resolve-handoff.schema.json` | `95e7b0a92a58d565d135ec670e22016f9814e7b1e1c75a2134ef8591a9629f56` | `c06d6506bf8618c813ac2f8114b790d275205cf89def5103459f4d5814d00910` |

All six byte identities mismatch. Wheel-embedded contracts are
non-authoritative inside BVP. BVP may proceed only through one exact route:

1. independent clean packaged compatibility Evidence proves that the released
   wheel output is accepted by the current BVP TASK-055 parsers/admission while
   all wheel-embedded schema claims remain non-authoritative; or
2. a new released wheel contains the exact current TASK-055 contracts and is
   independently pinned through a fresh version, asset, digest, dependency,
   license, resource, and Windows package audit.

No automatic selection, compatibility waiver, or silent schema coercion is
allowed. Until one route passes, the package remains `DEPENDENCY_BLOCKED`.

The root wheel METADATA declares no license/SPDX expression, and no root
license file was observed in the released wheel or tagged source tree. This is
an unresolved rights identity, not an inferred proprietary or open-source
classification.

## Exact future UX-A implementation Allowed Files

Only these nine paths may change in the later implementation Unit:

```text
src/ai_video_production/montage_consumer_runtime_package.py
src/ai_video_production/task036_trusted_launcher.py
packaging/montage-runtime.lock.json
schemas/montage-consumer-runtime-package-manifest.schema.json
src/ai_video_production/schema_resources/montage-consumer-runtime-package-manifest.schema.json
tools/windows/verify-montage-runtime-package.ps1
tests/test_montage_consumer_runtime_package.py
tests/test_montage_windows_package_contract.py
docs/ai-team/tasks/TASK-062/task.md
```

`src/ai_video_production/task036_shell_cli.py` is intentionally excluded. The
trusted launcher is the accepted composition root and may only receive the
minimum package-preflight composition required by the accepted design. Any
other source, schema, test, packaging, task, shell, installer, or composition
root path is a stop condition and requires a new exact Owner Gate and, when
design responsibility changes, a design amendment.

## Dependency gates before implementation start

Every item must be exact and current:

- root wheel release/tag/asset/filename/size/SHA-256 and `RECORD` verification;
- all nine dependency wheel names, versions, platform tags, sizes, SHA-256,
  requirement edges, and an Owner dependency-set acceptance record;
- supported BVP Python version and ABI range, with incompatible interpreter and
  native wheel negatives;
- root package license/SPDX identity and license-file provenance; unknown,
  conflicting, or absent identity fails closed;
- all package resource paths, sizes, digests, tree digest, and required schema
  families;
- current BVP TASK-055 schema/parser/admission identity and one selected
  compatibility route from the preceding section;
- real packaged Windows clean-profile acceptance under the BVP application
  runtime, not a source checkout or developer environment;
- canonical-main metadata activation, exact Owner implementation-start Gate,
  and no path/lock/open-PR overlap.

The Product must not download or update packages. A retained Product-owned
artifact source and its installer/package custody boundary require exact
coordinates before implementation acceptance.

## Closed manifest and verifier contract

- public schema and package mirror are byte-identical, closed, versioned, and
  reject unknown versions and additional fields;
- `packaging/montage-runtime.lock.json` binds the root wheel, dependencies,
  Python/ABI/platform, complete resource inventory, license identity, current
  TASK-055 authority, compatibility evidence, and a domain-separated semantic
  digest;
- filenames, normalized distribution names, versions, dependency edges, wheel
  tags, sizes, and SHA-256 are recomputed from retained bytes and metadata;
- every `RECORD` member is verified, unlisted/duplicate/escaped/symlinked or
  case-colliding entries fail closed, and archive paths never become public
  runtime authority;
- clean packaged preflight uses a Product-controlled runtime root, disables
  network/package resolution, rejects source-checkout and import shadowing, and
  performs no runtime import before package and license admission;
- runtime import, resource access, and current TASK-055 compatibility are
  separate evidence stages; failure never falls back to another environment;
- the verifier emits body-free, path-free Evidence and grants no job, Review,
  Timeline, Resolve, installation, Release, Deploy, or Production authority;
- package self-hash, version text, rebuild similarity, or a successful import
  never substitutes for released-asset, dependency, license, or compatibility
  proof.

## Acceptance and tests

The future exact head must demonstrate:

- schema/mirror parity, deterministic semantic hash, unknown-version and
  additional-field rejection;
- release asset, filename, size, digest, wheel tag, METADATA, WHEEL, RECORD,
  dependency graph, and resource tree positive and negative fixtures;
- missing/extra/duplicate/escaped/case-colliding members, truncated archive,
  same filename different bytes, relabel, hash/size drift, and rollback failure;
- Python/ABI/platform incompatibility and source-checkout/import-shadowing
  rejection before import;
- missing, unknown, conflicting, or unbound license/SPDX and license-file
  provenance rejection;
- all six current TASK-055 mismatches fail closed unless the selected clean
  packaged compatibility route is independently proven;
- a refreshed-wheel route rejects stale version, tag, release asset, digest,
  dependency, resource, license, or TASK-055 coordinates;
- offline hash-locked install, import, resource preflight, runtime preflight,
  BVP current TASK-055 admission, clean-profile packaged Windows operation, and
  restart/reopen verification;
- no network, automatic download/update, Provider, paid service, Product job,
  Review persistence, Timeline, Resolve, Release, Deploy, or Production effect;
- exact nine-path diff, compile, diff check, focused tests, TASK-055 direct
  regression, packaged Windows contract tests, and final full BVP regression.

Required command families:

```text
python -m pytest -q -p no:cacheprovider tests/test_montage_consumer_runtime_package.py tests/test_montage_windows_package_contract.py
python -m pytest -q -p no:cacheprovider tests/test_task055_montage_contract_recovery.py
python -m compileall -q src tests
python -m pytest -q -p no:cacheprovider
git diff --check
```

Future implementation files and focused tests do not exist in this metadata
Unit and are not executed or claimed here. Real packaged Windows acceptance is
separately authorized native Evidence and cannot be inferred from local wheel
inspection.

## DEV-4 role separation

- Builder implements only the exact nine-path Unit and supplies immutable
  exact-head, diff, manifest, lock, schema, artifact, and test Evidence.
- Critic independently reviews supply-chain, license, Python/ABI, TASK-055
  compatibility, package shadowing, privacy, authority, and failure modes.
- Tester independently verifies retained bytes, RECORD/resources, negative
  fixtures, clean packaged Windows behavior, focused/direct/full regression,
  and no-network/no-effect claims without promoting Builder results.
- Judge accepts only one exact head with unresolved Critical/High `0/0` and
  separately identifies local, Hosted, native, and post-main Evidence.

Maximum review/fix cycles are `2`. A third cycle, unresolved Critical/High,
runner inability, dependency ambiguity, or scope expansion returns to Owner.

## Prohibited effects and stop conditions

Prohibited: `UX-B` jobs/worker/review transaction; `UX-C` workspace/installer;
external package source changes; TASK-055 or TASK-058 changes; shell CLI edits;
Registry, task-index, current-state, CHANGELOG, roadmap, workflows, Product
Projects, real Owner data, Timeline, Resolve, Provider, network download,
package installation by the shipped Product, paid, native beyond an exact Gate,
Release, Deploy, Production, automatic retry, automatic rollback, automatic
dependency acceptance, or automatic compatibility waiver.

Stop on missing or changed release bytes; dependency or requirement drift;
unresolved/ambiguous license or SPDX identity; Python/ABI ambiguity; missing
Owner dependency acceptance; TASK-055 schema/parser/admission drift; unresolved
six-of-six wheel/BVP contract mismatch; compatibility test failure; source
checkout or import shadowing; arbitrary runtime path; unverified or non-owned
artifact custody; packaged Windows failure; private path/data leakage; dirty or
unknown ownership; branch/path/PR/lock overlap; Allowed Files expansion;
composition-root expansion; more than two review/fix cycles; or any request to
download, install, run a Product job, persist Review, mutate Timeline/Resolve,
or publish/activate a release.

## Completion and continuation

This metadata candidate is complete only after exact-scope documentation,
required independent DEV-4 review, Hosted checks, exact Owner merge
authorization, canonical-main merge/read-back, and post-main CI/Security.

`UX-A` implementation remains blocked after metadata hosting until license,
dependency acceptance, Python/ABI, TASK-055 compatibility, artifact custody,
and real packaged Windows start prerequisites are all exact and current. `UX-B`
and `UX-C` remain separately unauthorized. Completion creates no Release,
Deploy, Production, Timeline, Resolve, or automatic package authority.
