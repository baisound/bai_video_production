# TASK-029 R3 Owner Profile Store — Design / Critic / Judge

- Date: 2026-08-25
- Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY
- Base: fresh main `6564ff9830156e1d46231b89d6e7bd54c22cbb18`
- Atomic Unit: explicit-Human-confirmed encrypted Owner Profile revision store
- Hosted state: LOCAL_IMPLEMENTED / HOSTING_PENDING

## Authority and scope

R3 continues TASK-029's Owner-local learning responsibility. It consumes the exact R2 materialization candidate only after a separate explicit Human confirmation and records the selected Profile in a local encrypted append-only history.

MAY MODIFY:

- one TASK-029 encrypted Owner Profile Store module;
- its public envelope schema and byte-identical package mirror;
- focused tests;
- TASK-029 task/index/design records.

MUST NOT MODIFY:

- TASK-029 Owner Decision Store/cipher/envelope;
- TASK-019 proposal/binding implementations;
- Model/Profile Registry or Knowledge Pack;
- Timeline, Resolve, media, Provider, Cloud, Release, Deploy, workflow, lock registry, or CHANGELOG before an exact hosted lock.

## Design

`OwnerProfileStore.append` accepts the exact TASK-019 proposal/binding, latest TASK-029 Owner Decision History, exact selections, candidate identity, and a distinct `OwnerProfileMaterializationConfirmation`.

Before any I/O it recompiles the R2 candidate from those sources. Only `READY_FOR_HUMAN_MATERIALIZATION` is accepted. The confirmation binds the exact candidate hash, Owner scope and proposed Profile hash. A false/missing, stale or different confirmation fails before write.

The Store then uses an exclusive cross-process file update lock, expected-revision CAS, append-only hash chain, atomic replace and post-write validation. Windows Current User DPAPI with a TASK-029 Owner Profile-specific entropy domain is the default cipher. The disk envelope exposes only cipher identity, ciphertext, ciphertext hash, document hash and `plaintext_fields_present: false`.

The encrypted history enforces one Owner scope, one Profile identity, contiguous revisions, previous-active-to-next-baseline continuity, and no candidate, confirmation or Profile-version replay.

## Authority boundary

The explicit Human confirmation authorizes only one encrypted Owner Profile Store append. It does not authorize:

- automatic materialization or promotion;
- Model/Profile Registry write;
- Knowledge Pack promotion;
- rollback execution or physical delete;
- Edit Plan/Timeline/Resolve mutation;
- Provider/Cloud/external effects;
- Release or Deploy.

R3 does not provide a runtime Profile resolver or apply the stored Profile to scoring. Registry metadata, runtime selection, staged promotion and rollback execution remain separate Atomic Units.

## Failure modes

| Failure | Required result |
|---|---|
| non-ready/rejected R2 sources | reject before confirmation/write |
| missing or false Human confirmation | reject before write |
| confirmation/candidate/source drift | reject before write |
| stale expected revision | `ERR_OWNER_PROFILE_STORE_CONFLICT` |
| Store/Owner scope mismatch | `ERR_OWNER_PROFILE_STORE_SCOPE` |
| candidate/confirmation/Profile version replay | reject |
| next baseline differs from current Profile | reject |
| wrong key, tamper, plaintext or symlink | `ERR_OWNER_PROFILE_STORE_INTEGRITY` |
| interruption before atomic replace | no partial publication |

## Critic review

- Finding: an R2 READY candidate could be mistaken for permission to persist.
  - Resolution: confirmation is a separate immutable record; `human_confirmed is True` and exact candidate/Profile bindings are mandatory.
- Finding: using the Owner Decision cipher domain would couple two privacy stores.
  - Resolution: R3 has its own cipher protocol, suite identity and DPAPI entropy domain.
- Finding: an encrypted envelope could still leak Profile or Owner identifiers.
  - Resolution: the envelope contains ciphertext and integrity metadata only; focused tests assert absence of candidate ID, confirmation ID and Owner scope.
- Finding: history append might silently make the Profile active in scoring.
  - Resolution: no resolver/application API is exported; Registry, runtime selection, Pack promotion and every external-effect flag remain false.
- Finding: authenticated ciphertext could contain structurally rehashed tampering.
  - Resolution: every confirmation, candidate/profile snapshot, revision and history hash is reconstructed and verified on load.

Unresolved Critical/High findings: 0 / 0.

## Tester evidence

- focused R3 plus direct dependencies: `36 PASS`;
- all TASK-019/TASK-029 regression: `61 PASS`;
- full Product regression: `3681 PASS / 6 SKIP / 0 FAIL`;
- compileall and diff-check: PASS;
- schema mirror byte identity: PASS;
- real Windows Current User DPAPI test: included and Windows-only;

## Judge decision

`ACCEPT_LOCAL_COMMIT_READY`.

Commit-ready requires compileall, schema validation/mirror, relevant TASK-019/TASK-029 regression, broader Product regression, bounded diff review and zero unresolved Critical/High findings. Hosted integration must use a fresh exact CHANGELOG lock transaction.
