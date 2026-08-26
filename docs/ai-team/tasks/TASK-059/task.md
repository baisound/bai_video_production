# TASK-059 — Owner Signing Key PPK Import Bridge

Status: `P0_PREFLIGHT_IMPLEMENTED_COMMIT_READY`

Authority: Owner exact instruction `続きを開発して` on `2026-08-26`, following
the requested TASK-029 BVP signing-key import procedure.

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Responsibility

TASK-059 owns the separately gated bridge from an Owner-held encrypted PuTTY
PPK Version 3 Ed25519 key to the existing TASK-029 R9B Owner-local DPAPI custody
boundary. It does not reopen or rewrite the hosted-closed TASK-029 R9B/R9C/R9D
history.

TASK-029 remains owner of:

- R9B one-shot raw 32-byte Ed25519 seed validation and Windows Current User
  DPAPI custody;
- R9C exact local signing and immediate R9A verification; and
- R9D durable signing journal semantics.

TASK-059 must not create a second custody store, signer registry, signing
protocol, Knowledge Pack store, promotion service or Product entrypoint.

## P0 checkpoint

P0 implements a pure, body-free encrypted-PPK public-coordinate preflight. It
strictly parses bounded PPK Version 3 metadata, requires Ed25519, AES-256-CBC and
Argon2id, validates bounded KDF metadata and encrypted private-block syntax, and
matches the PPK public blob against a separate RFC4716 public key and an exact
Owner-confirmed OpenSSH SHA-256 fingerprint.

The result exposes only digests, public fingerprint, KDF numeric metadata and
fixed false effect flags. It accepts no passphrase, performs no MAC verification
or private-key decryption, imports no custody, writes no file, starts no signing
and invokes no subprocess/network/DPAPI boundary. Fixed state is
`READY_FOR_PASSPHRASE_MAC_GATE_NO_CUSTODY_IMPORT`.

P0 synthetic Evidence is `26 PASS`; P0 plus direct R9A/R9B/R9C is `53 PASS,
1 intentional Windows DPAPI skip`; full TASK-029 plus TASK-059 regression is
`143 PASS, 4 intentional Windows DPAPI skips`. Schema/mirror, compileall, exact
admission and diff checks pass. No real PPK, private key, seed, passphrase or
Owner custody was read, created, imported, logged or persisted.

## Next gated unit

P1 may implement a short-lived Windows-only secret-bearing helper only after a
separate detailed design/Critic/Judge gate. It must use masked direct Owner
passphrase entry, authenticate PPK MAC before trusting decrypted material,
derive and cross-check the exact Ed25519 public key, require explicit Human
confirmation, call the existing R9B confirmation/provision boundary once, emit
only a body-free receipt and terminate without secret persistence.

Real PPK selection, passphrase entry, private-key decryption, DPAPI custody,
real signing, Knowledge Pack mutation/promotion, runtime apply, Release, Deploy
and Production remain separate Human Gates and are not authorized by P0.
