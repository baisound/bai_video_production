# TASK-014 Packaging Parser Artifact Verifier R0 Evidence

Status: JUDGE_ACCEPTED / COMMIT_READY / PROPOSED_PIN_NOT_ACCEPTED / ARTIFACT_BODY_NOT_OBSERVED / PARSER_USE_BLOCKED / UNCOMMITTED

## Atomic Unit

- Unit: AU2C2B1b0-A, pure immutable-bytes verifier contract.
- DEV depth: DEV-4.
- Exact scope: module, public schema, packaged mirror, focused test, this Evidence.
- Prohibited in this Unit: artifact download, install, import of `packaging`, target runtime execution, E: access, model/audio read, resolver implementation.

## Proposed official coordinate

The contract records a proposed PyPI release coordinate from a feasibility lookup on 2026-08-21:

- project/version: `packaging 25.0`;
- filename: `packaging-25.0-py3-none-any.whl`;
- bytes: `66,469`;
- SHA-256: `29572ef2b1f17581046b3a2227d5c611fb25ec70ca1ba8554b24b0e69331a484`;
- core-metadata SHA-256: `5b611a609c38fefc3d616bf45d20aec98fb7d53f245daca9e2c30fc85c7ac282`;
- Requires-Python: `>=3.8`;
- yanked: false;
- canonical files.pythonhosted.org URL is embedded in the schema/module.

This lookup has no accepted observer identity/request receipt/response digest in
the repository. Therefore the coordinate remains `NOT_CONFIRMED` and is not an
independently accepted trust anchor. It is a proposed byte-verifier input only,
not proof that the wheel is retained locally. PyPI upload metadata is not
substituted for same-byte ZIP/RECORD verification.

## Contract

`parse_pinned_packaging_250_wheel(raw)` accepts only immutable `bytes` with the exact official size and SHA-256. From that same byte sequence it validates:

- bounded ZIP member count and expanded size;
- ASCII canonical member paths, case-fold uniqueness and Windows reserved-name rejection;
- no encrypted, unsupported-compression, link/device, executable/native, `.pth`, or unexpected top-level member;
- exact `packaging-25.0.dist-info` METADATA/WHEEL/RECORD presence;
- exact RECORD member set, self row and every payload hash/size;
- METADATA digest, name `packaging`, version `25.0`, Requires-Python `>=3.8`, and no runtime Requires-Dist;
- pure `py3-none-any` wheel identity;
- a domain-separated payload-inventory digest and receipt self-consistency digest.

## Authority boundary

Even after successful byte verification, the persisted receipt forces:

- `diagnostic_only=true`;
- `official_metadata_observation_accepted=false`;
- `pin_acceptance_authorized=false`;
- `persistent_receipt_is_capability=false`;
- `parser_import_authorized=false`;
- `resolver_use_authorized=false`;
- `install_authorized=false`;
- `post_return_state_guaranteed=false`;
- `consumer_revalidation_required=true`;
- every verifier-scoped network/download/install/import/runtime/model/audio effect flag false.

Those effect fields describe this pure verifier invocation only. They do not
claim that a future caller did not acquire the supplied bytes earlier; a later
acquisition Unit must persist its own truthful effect receipt.

The self-hash detects accidental/tampered serialization changes; it does not authenticate origin. AU2C2B1b remains blocked until later Units accept the exact pin, obtain the body under bounded network authority, and bind same-call verification to a live trusted parser-use boundary. The serialized receipt remains diagnostic and is never sufficient by itself. No installed or transitive `packaging` import may stand in for that chain.

## Verification

- focused pytest: `57 PASS`;
- focused plus closure-plan, runtime-manifest and locked-wheel trust-chain regression: `201 PASS` in `4.74s`;
- schema mirror/Draft 2020-12: PASS;
- compile/static/diff check: PASS;
- current module SHA-256: `119a1bccf4882c7600cd0d4d19d1708d45d14b282de4d4301814dd25514a026e`;
- current public/mirror schema SHA-256: `d43081e62d08255da4fb0567b10aad9344c94667394f8cce869994a0d34be298`;
- current focused-test SHA-256: `59b44bf29f467273db0ecee291d4bb81c048adf71500bafc14c0a3f42a700670`;
- independent Tester: `C0 / H0 / M0`, PASS. An independent pytest rerun was
  attempted with the existing isolated dependency path but was `NOT_CONFIRMED`
  because that environment lacked `pytest.__main__`; no dependency was installed;
- independent Critic/Judge: `C0 / H0 / M0`, PASS. Contract-only proposed
  verifier stage/commit/PR is GO; pin acceptance, body acquisition, parser import,
  resolver use and install remain separate NO-GO gates.

## No-effect record

- official release metadata was read only to establish the public coordinate;
- artifact body downloaded: false;
- package installed/imported: false;
- E:/target runtime/model/audio accessed: false;
- filesystem mutation outside this worktree: false.
