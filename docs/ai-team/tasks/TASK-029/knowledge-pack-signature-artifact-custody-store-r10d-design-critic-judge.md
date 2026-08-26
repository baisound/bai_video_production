# TASK-029 R10D Signature Artifact Custody Store — Design / Critic / Judge

Date: 2026-08-27

Status: HIGH_FINDINGS_REWORKED / INDEPENDENT_DEV4_REREVIEW_PENDING

DEV profile: DEV-4 FOUNDATION CRITICAL

## Atomic Unit

R10D consumes the exact R10C
`READY_FOR_EXPLICIT_HUMAN_CUSTODY_CONFIRMATION` candidate and performs one
non-authoritative encrypted signature-artifact staging transaction. It accepts a
transient raw 32-byte Ed25519 public key and 64-byte detached signature, but it
does not accept, retrieve, export, or store a private key.

The exact source Unit is six paths: this design, the TASK-029 task record, one
public receipt Schema and its byte-identical package mirror, one Product source
module, and one focused fault/boundary test module. `CHANGELOG.md`,
`ACTIVE-WORK-LOCKS.json`, TASK-059, UI, installer, Resolve, Timeline, runtime
Profile, Release, Deploy, and Production paths are excluded.

## Write algorithm

1. Require exact built-in security scalars, an exact R10C JSON snapshot and an
   exact R10B compile-argument object. Reject custom Mapping hooks before reads.
2. Re-run the trusted R10B compiler with the exact transient public-key and
   detached-signature bytes. R10B repeats Ed25519 verification and reconstructs
   the exact R6-R10A source graph.
3. Recompile R10C from the exact R9B custody receipt, the exact R9C ceremony
   snapshot used by R10B, and the newly recompiled R10B admission. Require the
   resulting candidate to equal the supplied R10C payload.
4. Bind a caller intent attestation to the exact candidate, logical
   artifact-store ID, Owner scope, request, signer and detached-signature
   digest. The attestation explicitly does not authenticate Human origin and
   does not authorize canonical custody.
5. Require public-key and detached-signature hashes to equal R10C and verify the
   detached signature again over the exact ASCII signature-message coordinate.
6. Under the existing cross-process file lock, reject symlink and existing
   destination paths, encrypt the full private store record with a dedicated
   R10D cipher domain, and use validated atomic replace. Production construction
   always instantiates the exact Windows DPAPI cipher; caller cipher injection
   is unavailable.
7. Decrypt and validate the replaced file before returning a body-free receipt.
   Any mismatch fails closed.

## Storage and public boundary

The production cipher is fixed to Windows Current User DPAPI with entropy domain
`TASK029_SIGNATURE_ARTIFACT_CUSTODY/V1`, distinct from the R9B private-key
custody domain. The disk envelope exposes only schema identity, cipher suite,
ciphertext, ciphertext checksum, a plaintext-absence flag, and document hash.

The encrypted record contains the exact R10C candidate, R10B admission,
non-authoritative caller intent attestation, public key and detached signature. It contains no
private key, passphrase, seed, credential, host path, media, or Project data.
The public receipt contains identifiers and hashes only.

Only an exact production DPAPI instance may set `encrypted_at_rest=true`.
Private test construction is labeled `test_only_cipher_used=true` and fixes
`encrypted_at_rest=false`, regardless of round-trip behavior or cipher-suite
text. The receipt may claim that the artifact was staged, read back, and
mathematically verified against the supplied signer policy at this write
boundary. Caller-supplied source-graph recompilation is
true, while canonical latest-source and canonical policy revalidation remain
false. Human confirmation origin, custody write authority, canonical custody
receipt, and custody completion are false. Owner-local path verification,
canonical Project/path binding, deletion
and alternate-path replay prevention are also false. It must not claim a
canonical Owner trust root, Owner-signer identity
authentication, canonical Knowledge Pack receipt, Pack write/promotion,
automatic promotion, runtime apply, rollback, Timeline/Resolve, Release,
Deploy, Production, or external effect.

## Filesystem assurance boundary

The path model is
`COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY`. Existing symlinks and non-regular
read targets are rejected. The current atomic writer fsyncs the file and tries
directory fsync, but an unsupported directory fsync is swallowed. Therefore
`directory_durability_confirmed=false` and
`power_loss_replay_prevention_confirmed=false`.

Path checks are not a hostile handle-bound ancestor/reparse defense.
`hostile_path_race_protection_confirmed=false`. A retained, intact file is
one-shot within this cooperative path; deletion, alternate paths, hostile
namespace replacement and physical recovery are outside this Unit.

## Failure model

| Threat | Result |
|---|---|
| no exact caller intent attestation | reject before staging |
| public boolean used as Human authority | records intent only; Human origin/write authority/custody remain false |
| caller-provided production cipher | production constructor rejects the argument |
| prefix, rotation, unauthenticated or DPAPI-name-spoof cipher | cannot enter production construction or mint encryption/custody claims |
| custom/stateful public Mapping | reject before hook read |
| derived security scalar or bytes type | reject |
| stale/tampered R10B source graph | R10B direct recompile rejects |
| stale/tampered R10C candidate | exact R10C recompile rejects |
| public key or detached signature mismatch | reject |
| intent-attestation coordinate/time mismatch | reject |
| store time before candidate/admission/attestation | reject |
| destination exists or is symlink | reject without overwrite |
| encryption, temp validation, replace or read-back failure | fail closed |
| wrong cipher, tampered ciphertext or plaintext file | integrity error |
| public receipt authority tamper | strict parser rejects |

## Verification plan

- exact R10B and R10C write-boundary recompilation;
- Ed25519 artifact digest and mathematical verification;
- caller intent binding, false Human-origin/authority claims and causality negatives;
- production cipher injection rejection, DPAPI-suite spoof rejection, and
  prefix/rotation/unauthenticated test-cipher downscope;
- one-shot overwrite, symlink, tamper, wrong-cipher, plaintext and atomic
  failure/retry coverage;
- no-body/no-private-key public and disk-envelope checks;
- strict receipt Schema and byte-identical package mirror;
- exact scalar/custom Mapping barriers;
- Windows DPAPI synthetic artifact round-trip where available;
- focused R10D, direct R9B-R10D, TASK-029 and relevant Product regression;
- exact6 diff/scope review and DEV-4 Critic/Tester/Judge.

## Builder Critic

Initial self-review C/H/M/L: `0/0/2/0`.

- M1: reusing the R9B DPAPI entropy domain would conflate key and artifact
  custody. Closed by a dedicated R10D cipher class and entropy domain.
- M2: atomic replace alone would not justify post-write read-back or directory
  durability claims. Closed by an in-lock decrypt/validate comparison after
  replace and explicit false directory/power-loss flags.
- M3: a dependency-injected cipher could make an encrypted-at-rest receipt
  false even when ciphertext differs from plaintext. The first mitigation was
  insufficient and independent review elevated this to High. Closed by
  removing cipher injection from production construction. Private test cipher
  construction cannot claim DPAPI, encryption at rest, Owner-local custody, or
  standalone authority. A direct post-replace decrypt corruption fixture also
  proves that no receipt is returned after failed read-back.

Independent review found `0/2/1/0`: arbitrary cipher injection, boolean Human
authority self-mint, and unverified Owner-local path overclaim. The bounded
rework removed cipher injection from the production constructor, made test
cipher construction private and permanently non-authoritative, replaced the
confirmation API with a caller intent attestation, and changed the terminal
state to `SIGNATURE_ARTIFACT_STAGED_AWAITING_TRUSTED_HUMAN_CONFIRMATION`.
Owner-local path/store, Human confirmation origin, custody write authority,
custody completion, and canonical receipt claims are all false. Independent
Critic and Tester rereview remain required.

Builder Evidence:

- focused R10D after bounded security rework: `18 PASS / 1 Windows-only DPAPI SKIP` on WSL;
- R9B-R10D direct chain: `101 PASS / 2 Windows-only DPAPI SKIP`;
- TASK-029 complete: `179 PASS / 5 Windows-only DPAPI SKIP`;
- public/package receipt Schema byte identity and strict Draft 2020-12
  validation: PASS; final SHA-256
  `D552EF8611183B3C9366A67C31C8FA8BEA4688A8345CAE9C480356F11DED139F`;
- Windows source `py_compile`, WSL focused/schema tests and `git diff --check`:
  PASS;
- full Product regression: NOT_CONFIRMED. The fresh-main TASK-059 source now
  requires Argon2 support from cryptography >=46 and `referencing`; the existing
  WSL environment has cryptography 41.0.7 and no `referencing`, so collection
  stopped on 28 dependency import errors before Product tests ran. No package
  was installed or Product failure claimed. Hosted CI remains the full Product
  confirmation route.

## Judge

Decision: `PENDING_INDEPENDENT_DEV4_REVIEW_AND_HOSTED_FULL_PRODUCT`.
