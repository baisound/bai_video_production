# TASK-102 PMST-I2 — Product Writer Migration Plan R0

Status: `PMST_I2_AUTHORIZED / PMST_I2A_I2B_I2C_COMMITTED / PMST_I2D_BUILDER_COMPLETE / PRODUCT_ENROLLMENT_DISABLED`

## 1. Bound outcome

PMST-I2 migrates the accepted D1 writer, recovery and protected-lock graph behind one Product-local PMST composition boundary. It does not enroll a Project. Source presence alone must preserve legacy behavior for an unenrolled root, while any enrolled state must make every legacy mutation and lock route fail closed. Read-only compatibility remains available unless a caller requires a broker read lease for integrity.

The accepted migration-matrix file SHA-256 is `ad7f4a22a560b84c8e317b2e450c3097110877e04f25f0352cc62651439a8dd5`; its PMST record value is `sha256:ad7f4a22a560b84c8e317b2e450c3097110877e04f25f0352cc62651439a8dd5` as required by the existing ABI. An ACTIVE enrollment with any other matrix digest is not executable. All 13 D1 routes are closed; there is no `UNKNOWN`, generic path, arbitrary byte sink, caller-selected validator, silent legacy fallback or partial enrollment.

## 2. Authority and prohibited effects

The Owner authorized PMST-I2 on 2026-09-29. This permits the source/test units in TASK-102's ordered I2 plan. It does not permit Product enrollment, service installation/update, ACL/owner mutation, real Project writes, native QA, private voice/media/model processing, Release, Deploy or Production.

All tests use pytest-owned temporary directories and injected fake resolvers/ports. No build, installer, runtime or native output is created by I2A.

## 3. I2A kernel contract

I2A supplies a closed route registry and a pure Product-facing router:

- the enrollment resolver sees the local Project root, but the port never receives a host path;
- no enrollment record means `UNENROLLED` and permits the unchanged legacy path;
- any valid `PREPARED`, `ACTIVE`, `SUSPENDED` or `REVOKED` enrollment blocks legacy mutation and lock creation;
- only `ACTIVE` with the exact accepted matrix digest admits a broker request;
- the private request must pass the accepted I1 parser and match enrollment registration, route operation kind and exact route profile;
- the broker response must pass the public-status parser and match the request's operation, kind, profile, intent and request digests;
- R013 and every unknown route are always rejected;
- read-only compatibility never creates mutation authority and is explicitly separate from a broker read lease.

The default composition has no enrollment resolver result and no live port. Therefore importing I2A changes no Product behavior and cannot produce a filesystem, service, ACL, socket, process or Project effect.

## 4. Ordered migration

I2B connects the central manifest/coordinator routes. I2C connects or blocks every protected object and lock route. I2D closes semantic callers and source policy. Until those units are complete, no composition may return an ACTIVE enrollment. I2E performs final review and integration; PMST-C alone may later propose enrollment UX and normal Product entrypoint activation.

### I2B central readback rule

Central source migration uses explicit dependency injection. A supplied PMST request never authorizes a legacy fallback. `COMMITTED_WITH_READBACK` is necessary but insufficient: the Product reparses the canonical manifest after the port returns, requires the exact requested successor digest, and for coordinated saves revalidates every selected child. Missing, stale or mismatched readback is `DATA_INTEGRITY`, not success. Until later units supply exact broker query/read-lease and participant recovery adapters, enrolled legacy recovery/status/integrity entrypoints return a deterministic unavailable error before lock/journal mutation.

### I2C protected-object order

I2C is executed as C1 (`R003/R004/R007` object stores), C2 (`R005/R006` snapshot sets), and C3 (`R008/R009/R010` recovery/read-lease/participant paths). A feature-block is a valid intermediate disposition only when it occurs before any legacy lock or protected-control mutation and no caller can bypass it through a package-private writer. The default composition remains unenrolled. Semantic request construction, readback and caller composition are completed in I2D before enrollment can be proposed.

C1 adds only injected legacy-route guards. All valid enrollment states reject Job, history and VoiceProfile legacy locks/writes before `.bai-project` creation. Direct Job/history internal writer calls are guarded separately. Unenrolled behavior remains unchanged, and C1 does not expose a broker write path that lacks semantic-owner request/readback validation.

C2 guards the mutating R005/R006 snapshot-set entrypoints. Enrolled Autosave mutation, Backup create and Backup restore stop before legacy locks, manifest save, snapshot reads or snapshot writes. Autosave's non-mutating timing skips and Backup's verified read-only preview remain compatible. Closed snapshot request/readback adapters remain I2D work, so enrolled snapshot mutation is unavailable rather than partially routed.

C3 guards R008 Timeline recovery and participant paths, all three R009 read-associated Project lock callers, and R010 TASK-029 constructor plus exact/generic public lock routes. Guards are evaluated before confirmation consumption, Project/control lock creation, recovery-object effects or TASK-029 authority-directory initialization. Long-lived TASK-029 instances recheck enrollment on every public lock route. Exact read-lease and participant request composition remains I2D work; there is no legacy fallback for an injected enrolled composition.

### I2D semantic and source-policy closure

R011 bootstrap/import and the remaining R012 semantic callers accept the same injected router used by their store/coordinator and deterministically reject an enrolled composition before consuming Human confirmation or starting a protected mutation. Callers already feature-blocked by R005/R006/R008/R010 retain that stronger closure. The source policy parses the accepted D1 matrix and Python ASTs, verifies every direct/delegated source closure, scans bounded protected mutation signals for files outside the matrix, and includes a synthetic unregistered-writer rejection test. The policy does not authorize Product enrollment or substitute a broad arbitrary-file scanner for the exact protected-control boundary.

## 5. I2A acceptance

I2A is commit-ready only when:

1. the registry contains exactly R001 through R013 and reproduces every accepted D1 disposition;
2. exact operation-kind/profile bindings are closed and immutable;
3. unknown, R013, partial/mismatched matrix, inactive enrollment, malformed request and mismatched response cases fail closed before a port effect;
4. enrolled legacy mutation/lock is rejected while unenrolled legacy and read-only compatibility remain unchanged;
5. the port receives no host path and only a strictly parsed PMST request plus enrollment;
6. focused tests and the existing PMST-I1 regression pass;
7. exact Allowed Files, diff, external Evidence and commit-ready state are verified.
