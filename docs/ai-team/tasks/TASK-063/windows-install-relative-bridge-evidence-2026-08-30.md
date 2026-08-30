# TASK-063 Windows Install-Relative Bridge Evidence

## Result

- Technical result: `PASS`
- Execution: real Windows compile, Inno Setup compile and silent custom-path install
- Production connector activation: `NOT_EXECUTED / false`
- Release / Deploy: `NOT_EXECUTED`
- Resolve mutation: `NOT_EXECUTED`

## Exact source and environment

- Base: BVP `origin/main` at `772c8173d42c8312e8693bacc75934fbfd10bf3a`
- Branch: `codex/task063-installer-relative-bridge`
- Python: `3.12.13`
- PyInstaller: `6.22.0`
- Inno Setup: `6.7.3`
- Host: Windows 11 `10.0.26200`

## Build artifacts

- Main EXE: `builds/BAI Video Production/BAI Video Production.exe`
  - bytes: `15,179,034`
  - SHA-256: `3acddb0339f2982c623995464219b857e047d605dd745050aacccc512f1ade6a`
- Installer: `packaging/output/bai-video-production-0.23.0-task063-windows-x64-setup.exe`
  - bytes: `93,559,784`
  - SHA-256: `791381dcd11fb9785265cfc441435cfd753f23afd1bd8ed557d67db2a4207918`
- Installer payload tree:
  - files: `1,527`
  - SHA-256: `cb81582fa06fb507259d71be0e897d0cae3a00c25586165d025a2db97196e164`

## Native installation and read-back

- Selected install root:
  `D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install\BAI Video Production`
- Derived Bridge root:
  `D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install\BAI Video Production\data\montage-learning-bridge`
- Install instance:
  `bvp-install-a65cf0984a214bdab781912f56c7c88f`
- Descriptor SHA-256:
  `sha256:a51009d5d8fa509afd5f3528caf17f3bd0ce39d39d3d4bf2d605bebed0265ece`
- Owner manifest SHA-256:
  `sha256:e141c94c6ca751edba9e9345a1f8570c324b3d1601527bd0d06e5340172272e6`
- Discovery status: `READY_DISABLED_BY_DEFAULT`
- `bridge_relative_path`: `data/montage-learning-bridge`
- `connector_enabled`: `false`
- `activation_authorized`: `false`

The installed EXE performed both private provision and discovery. The acceptance
script then independently read `bridge-instance.json`, `bridge-owner.json`, the
complete required directory tree and
`migration/installer-readback.json`. The instance and digest bindings matched.

## Tests

- TASK-063 + packaged entry + existing file bridge: `41 PASS`
- TASK-058 admission store and Bridge contracts: `75 PASS`
- TASK-058 canonical preflight/promotion/durable staging/external anchor/receipt: `141 PASS`
- TASK-058 canonical admission transaction: `86 PASS / 2 environment-dependent SKIP`
- TASK-058 canonical SKILL adapter E2E: `38 PASS`
- Python `compileall`: `PASS`
- `git diff --check`: `PASS`

The two skips are the existing FIFO fixture-unavailable Windows cases. They are
not converted to PASS and do not affect the installer-relative coordinate.

## Failure found and corrected during acceptance

The first silent-install attempt did not preserve the quoted `/DIR` value with
spaces, so the bounded destination was not created. The acceptance tool was
corrected to quote both `/DIR` and `/LOG`, create only the exact bounded parent,
and treat a nonzero installer result or missing Bridge read-back as FAIL. The
second real installation passed. No ProgramData Bridge was created, migrated or
deleted.

## Remaining gates

- TASK-060 must supply the canonical production Preference source.
- TASK-061 must own Human activation/deactivation, legacy migration, production
  DACL attestation and final connector readiness.
- Therefore changing the connector switch to true remains unsafe and was not
  performed by TASK-063.
