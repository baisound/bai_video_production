# TASK-029 R5 Owner Profile Registry Store — Design / Critic / Judge

Date: 2026-08-25

Governance: DEV-4 PRIVACY, LEARNING AND RELEASE INTEGRITY

## Atomic Unit

Persist one exact TASK-029 R4 Owner Profile Registry candidate only after a separate explicit Human registry confirmation. The destination is an encrypted Owner-local Model/Profile Registry history. This Unit does not apply the registered Profile at runtime and does not promote it into a Knowledge Pack.

## Inputs and authority

- source: current encrypted R3 `OwnerProfileStore`
- candidate: R4 `OwnerProfileRegistryCandidate`, recompiled inside the write transaction
- confirmation: separate `OwnerProfileRegistryConfirmation`
- destination: R5 encrypted `OwnerProfileRegistryStore`
- authority: Owner priority/autonomy direction of 2026-08-24, bounded to local implementation and ordinary Git/PR integration

The confirmation is data consumed by one append. It is not Release, Deploy, Production, automatic promotion, runtime apply, rollback, Provider, Cloud, Timeline, or Resolve authority.

## Transaction design

1. Reject identical source and destination paths.
2. Acquire source and destination cross-process locks in deterministic normalized path order.
3. Reload and decrypt the source Owner Profile Store while both locks are held.
4. Require exact `expected_source_history_revision` and recompile the R4 candidate from the latest source revision.
5. Require the separate Human confirmation to bind candidate hash, Owner scope, source history revision/hash, source Profile revision hash, and proposed Profile hash.
6. Load or create the destination registry history and enforce exact `expected_registry_revision` CAS.
7. Enforce append-only chain, strictly advancing source revision, fixed Owner/source store/Profile identity, active-Profile baseline continuity, and candidate/confirmation/source-revision/Profile-version anti-replay.
8. Encrypt the complete registry history with Windows Current User DPAPI using a registry-specific entropy domain distinct from the R1 Decision Store and R3 Owner Profile Store.
9. Atomically replace the envelope and validate by decrypting and reconstructing all domain records before commit.

## Persisted boundary

The plaintext JSON envelope contains only:

- schema and record identity
- cipher-suite identity
- ciphertext
- ciphertext checksum
- document checksum
- `plaintext_fields_present=false`

Owner scope, candidate/confirmation identities, Profile snapshot, lineage, and history are ciphertext-only. No raw media, transcript/prompt body, host path, credential, Provider payload, or private project body is accepted.

Every decrypted history and revision fixes these flags:

- `runtime_profile_apply_authorized=false`
- `knowledge_pack_promotion_authorized=false`
- `automatic_promotion_authorized=false`
- `rollback_execution_authorized=false`
- `edit_plan_mutation_authorized=false`
- `external_effect_authorized=false`

## Failure matrix

| Failure | Required result |
|---|---|
| Human confirmation absent/false | fail before I/O |
| confirmation/candidate/source/Profile mismatch | fail before destination write |
| source Owner Profile revision changed | fail closed |
| destination expected revision stale | state conflict; no retry |
| Owner/source store/Profile identity drift | authorization/data-integrity failure |
| candidate, confirmation, source revision, or Profile version replay | fail closed |
| broken chain or baseline discontinuity | fail closed |
| wrong cipher/DPAPI user, ciphertext or envelope tamper | integrity failure |
| plaintext history supplied as envelope | integrity failure |
| source/destination symlink or same path | fail closed |
| interruption before atomic replace | original file preserved or no first file |
| non-Windows default cipher | NOT_SUPPORTED |

## Verification plan

- strict R4 candidate round-trip and unknown/derived-field rejection
- explicit confirmation positive/negative and exact binding
- encrypted save/load and schema validation
- source revalidation, registry CAS, scope, continuity, replay matrix
- authenticated envelope/ciphertext tamper and wrong-key rejection
- same-path, symlink, plaintext, and power-loss rejection
- schema mirror byte identity
- real Windows Current User DPAPI synthetic round-trip
- R2/R3/R4 direct dependency regression
- TASK-019/029 chain regression
- full Product regression before commit-ready checkpoint

## Critic review

Initial findings:

- High: loading the source before taking the destination lock could admit a stale source revision during a concurrent update.
  - Resolution: source and destination locks are acquired together in deterministic path order before source reload and candidate recompilation.
- High: accepting a caller-supplied R4 object without reconstruction could admit derived-field or semantic drift.
  - Resolution: add strict `OwnerProfileRegistryCandidate.from_dict`, and recompile from the locked source at append time.
- Medium: reusing the R3 DPAPI entropy would collapse storage domains.
  - Resolution: use `TASK029_OWNER_PROFILE_REGISTRY_STORE` entropy and a distinct cipher-suite identity.
- Medium: a second registration could diverge from the active registry Profile.
  - Resolution: require the next candidate baseline hash to equal the current registered Profile hash and keep Profile identity fixed.
- Medium: a frozen registry revision retaining a mutable candidate mapping could drift after validation.
  - Resolution: revisions retain the immutable R4 candidate object and serialize a fresh canonical projection; an immutability regression test is required.

Residual Critical / High / Medium: 0 / 0 / 0.

## Judge

Decision: ACCEPT IMPLEMENTATION AND VERIFICATION PLAN.

Conditions:

- no runtime Profile application in R5;
- no Knowledge Pack promotion or automatic promotion;
- no rollback execution;
- no plaintext Owner data in the envelope;
- no shared CHANGELOG mutation until a separate exact integration lock is hosted from fresh main.
