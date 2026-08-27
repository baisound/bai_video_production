# TASK-029 R10E — Signature Artifact Custody Confirmation Request

## Governance and Atomic Unit

- Governance: `DEV-4 FOUNDATION CRITICAL`
- Unit: `R10E_SIGNATURE_ARTIFACT_CUSTODY_CONFIRMATION_REQUEST`
- Goal: turn an exact R10D encrypted-staging receipt into a short-lived,
  body-free request for a later trusted Human interaction.
- Source scope: exact six paths: this design, TASK-029 task record, public
  schema, package schema mirror, source contract and focused test.
- Shared scope excluded: `CHANGELOG.md` and `ACTIVE-WORK-LOCKS.json`.

## Responsibility boundary

The R10E compiler consumes one exact built-in JSON snapshot of the public R10D
receipt. It revalidates that receipt's self-hash and requires its production-DPAPI claim,
completed encrypted staging, completed post-write read-back, and explicit
absence of custody confirmation. The output preserves only stable identifiers,
hashes and three bounded timestamps. Its maximum lifetime is fifteen minutes.

The source R10D receipt and the R10E request are publicly constructible. The
serialized request records that receipt self-hash validation is a compiler
requirement but fixes standalone revalidation to false. R10E therefore does not
authenticate the store or DPAPI operation that allegedly produced it. It does
not read encrypted storage, re-run a DPAPI decrypt, verify a trusted clock, or
decide whether a serialized request is currently fresh. Those facts require a
later trusted interaction/store boundary.

## Threat model and fail-closed rules

- Stateful or hostile Mapping inputs must be rejected before any hook read.
- Exact built-in scalar types are required; subclasses cannot override time or
  equality behavior.
- Request creation cannot predate R10D staging, expiry must follow creation,
  and the TTL cannot exceed fifteen minutes.
- Fixed state and authority/effect fields are part of the self-hash and typed
  reconstruction. Relabeling or changing any false authority flag remains
  invalid even after an attacker recomputes the outer hash. Stable coordinates
  are intentionally constructible when detached from the compiler; their
  reconstruction never authenticates source or grants standalone authority.
- Test-only cipher receipts cannot be used to create a production confirmation
  request.
- Signature bytes, public/private key material, host paths, credentials and
  media are prohibited from the request.

## Authority and effect denial

The request is non-authoritative and does not prove that a Human saw, accepted
or originated anything. Human confirmation received/origin authentication,
one-shot enforcement, custody promotion, staging deletion, canonical custody
write/receipt, trust root, Owner-signer binding, Knowledge Pack write/promotion,
runtime apply, rollback, Timeline/Resolve, Release, Deploy, Production and all
external effects are fixed false.

## Acceptance and review gates

1. Public schema and package mirror are byte-exact Draft 2020-12 schemas.
2. Positive compile/serialize/parse round-trip preserves the exact R10D
   lineage without body or path data.
3. Receipt tamper, test cipher, time inversion, excessive TTL, authority
   relabel, custom Mapping and scalar-subclass attacks fail closed.
4. Focused, relevant TASK-029 and applicable Product regressions pass.
5. Independent DEV-4 Critic, Tester and Final Judge responsibilities report no
   unresolved Critical or High finding before integration.

## Review state

- Builder: `COMMIT_READY`
- Builder focused test: `15 PASS`
- R10D + R10E direct test: `34 PASS / 3 platform SKIP`
- TASK-029 regression: `195 PASS / 7 platform SKIP`
- Schema: Draft 2020-12 valid; public/package mirror byte-exact; 72 required
  fields equal 72 declared properties; SHA-256
  `6307D88BE43617A30502654D61B6AF3FCC4F12F50246E31D4339F7B211D3BB3E`.
- Full Product: `NOT_CONFIRMED`; the existing WSL environment stopped during
  collection because it lacks TASK-059's Argon2-capable cryptography and the
  `referencing` package. No dependency was installed.
- Builder Critic finding: one High authority-overclaim found and closed. A
  publicly constructible request no longer claims standalone source-receipt
  revalidation; it records the compiler requirement and fixes standalone
  revalidation/source origin to false.
- Independent Critic/Tester: `PENDING`
- Final Judge: `PENDING`
- Shared CHANGELOG integration: `NOT_STARTED`
