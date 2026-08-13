# TASK-037 — R2 Product Promotion Local Closure Evidence

- Date: `2026-08-14`
- Starting Source of Truth: `main` at `7873488c85cf1fd9e49b8061e4c201b6fec976d6`
- Working branch: `codex/task-037-r2-product-promotion`
- DEV Profile: `DEV-4 FOUNDATION CRITICAL`
- Local Gate: `PASS`
- Hosted PR Gate: `PENDING`
- Release decision: `NO_RELEASE_AT_TASK037_CHECKPOINT`

## Promoted Product capability

TASK-037 did not recreate the accepted R2 Foundation. It promoted it through a project-scoped Product Application Service and the existing unified Desktop Shell.

- the fixed project-owned `production-control.json` is the durable relationship Source of Truth;
- only an existing Human-approved Plan can install Scene Asset Slots; loose Slot creation is not exposed;
- Candidate versions append without overwriting prior Candidate history;
- Candidate lineage must reference an existing Candidate in the same Slot;
- CREATED -> READY_FOR_AUDIT is available without granting ACCEPT authority;
- TASK-038 remains the sole owner of Human ACCEPT/REJECT decisions;
- an ACCEPTED Candidate can be LOCKED from the Desktop `制作管理` workspace after an explicit confirmation displaying Slot, Candidate, Asset and exact SHA-256;
- lock confirmations are exact, stale-safe and one-shot even after a failed apply attempt;
- the cross-process checksum check and atomic replacement are serialized by a project-local file lock;
- the projection contains relationship metadata only: no host path, media bytes, physical delete, Provider execution, automatic regeneration or Resolve mutation.

## Bounded Critic result

- Critical findings after correction: `0`
- High findings after correction: `0`

Corrections applied during the bounded review:

1. removed loose Slot creation and bound installation to a Human-approved TASK-027 Plan;
2. reloaded the canonical snapshot for every durable command instead of treating long-lived memory as authority;
3. bound LOCK to project, snapshot checksum, Slot revision, Candidate identity and Asset checksum;
4. consumed LOCK confirmation before current-state validation so a stale failed attempt cannot be replayed;
5. serialized the CAS check plus atomic replacement across local Product processes;
6. kept TASK-038 ACCEPT/REJECT and all Provider/NLE operations outside TASK-037.

## Validation

- focused final Windows gate: `55 / 55 PASS` after Critic corrections;
- cross-process first-writer test: PASS; exactly one writer publishes and the competing writer fails closed with `ERR_PRODUCTION_SNAPSHOT_CAS_REQUIRED`;
- Windows full regression: `825 PASS / 1 intentional non-Windows skip / 0 FAIL`;
- Python `compileall`: PASS;
- `git diff --check`: PASS.

The first hosted metadata check correctly rejected the PR because Product code changed without an Unreleased changelog entry. The required `CHANGELOG.md` entry was added without changing package/version metadata. Initial Ubuntu 3.11/3.12/3.13 and both Security jobs passed. Initial Windows jobs stopped before Product tests because the GitHub runner's Chocolatey source could not provide or expose `ffmpeg`; this external runner failure is rerun after the changelog correction and is not recorded as a Product PASS.

The second hosted run reproduced the Chocolatey search-index failure on all three Windows jobs while all three Ubuntu, metadata and Security checks passed. The CI-only correction pins Chocolatey FFmpeg `8.1.2`, downloads the exact nupkg through its stable versioned endpoint, verifies SHA-256 `6c5746c8f0da8334d367131012ec1280bdd490651e108c35e19933587b06aed8`, then installs only from the runner-local directory. Unknown bytes fail closed before installation.

The first pinned-endpoint run showed that the Chocolatey API redirect returned `404` specifically from hosted Windows runners, while its package object was available. The source was narrowed to the immutable package-object URL `https://packages.chocolatey.org/ffmpeg.8.1.2.nupkg`; checksum enforcement is unchanged. The OSS-readiness contract test was updated from requiring the obsolete unpinned command text to requiring the exact package URL, SHA-256 and runner-local Chocolatey source.

WSL2 Ubuntu discovery found Python `3.12.3`, but the distribution has no installed pytest. Reusing Windows site-packages is invalid because the compiled `rpds` extension has no Linux binary, so WSL collection was not claimed as PASS. No dependency was installed or downloaded. The target Windows regression is the accepted local gate for this Windows Desktop Product unit.

The in-app browser visual harness could not initialize because its local kernel asset path was unavailable. Therefore no new native visual PASS is claimed. The Production Control markup, responsive drawer, keyboard-accessible controls, safe `textContent` rendering and exact lock interaction are covered by automated Shell tests. TASK-036's previously accepted native visual evidence is not rewritten.

## Claim and release boundary

The local implementation gate is complete. Formal TASK-037 closure still requires the dedicated PR to pass all hosted checks, merge into `main`, exact merge SHA verification and branch cleanup.

This checkpoint intentionally does not change package metadata and does not create a Tag or GitHub Release. TASK-037 is one step in the R2 wave; the stable Product release remains `v0.20.1`. After hosted closure, TASK-038 must start on a new dedicated branch and promote the existing Audit Foundation into the same user-facing Production Control flow.

Existing untracked raw native `evidence/` remains preserved and excluded from staging.
