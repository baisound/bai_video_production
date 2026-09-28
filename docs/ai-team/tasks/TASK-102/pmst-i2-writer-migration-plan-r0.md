# TASK-102 PMST-I2 — Product Writer Migration Plan R0

Status: `PMST_I2_AUTHORIZED / PMST_I2A_IN_PROGRESS / PRODUCT_ENROLLMENT_DISABLED`

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

## 5. I2A acceptance

I2A is commit-ready only when:

1. the registry contains exactly R001 through R013 and reproduces every accepted D1 disposition;
2. exact operation-kind/profile bindings are closed and immutable;
3. unknown, R013, partial/mismatched matrix, inactive enrollment, malformed request and mismatched response cases fail closed before a port effect;
4. enrolled legacy mutation/lock is rejected while unenrolled legacy and read-only compatibility remain unchanged;
5. the port receives no host path and only a strictly parsed PMST request plus enrollment;
6. focused tests and the existing PMST-I1 regression pass;
7. exact Allowed Files, diff, external Evidence and commit-ready state are verified.
