# TASK-059 P0 — PPK Import Preflight Design / Critic / Judge

Date: `2026-08-26`

Status: `BOUND_AND_IMPLEMENTED_LOCAL`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Goal

Produce a body-free, deterministic preflight proving that one encrypted PuTTY
PPK Version 3 public coordinate, one separately stored RFC4716 public key and
one Owner-confirmed OpenSSH SHA-256 fingerprint identify the same Ed25519 key.
The unit must stop before receiving a passphrase or claiming PPK authenticity,
private-key access, R9B custody import or signing authority.

## Canonical boundary

- TASK-029 R9B remains the only raw seed validation and DPAPI custody owner.
- TASK-029 R9C remains the only exact local signing ceremony owner.
- TASK-029 R9A remains signature verification owner.
- TASK-059 P0 owns bounded PPK container/public metadata syntax inspection and
  body-free preflight construction only.

The API accepts in-memory bytes and never opens a path. File selection, Windows
secret entry, PPK decryption and custody execution belong to later adapters and
Human Gates.

## Input contract

P0 requires:

- a bounded ASCII PPK document;
- a bounded ASCII RFC4716 public key;
- an exact Owner-confirmed `SHA256:<OpenSSH fingerprint>`; and
- a positive observation time.

The PPK must use exact ordered Version 3 headers, `ssh-ed25519`, `aes256-cbc`,
`Argon2id`, canonical positive KDF values within ceilings, a 16-64-byte salt,
bounded public/private line counts, valid base64, AES-block-aligned encrypted
private bytes and a syntactically valid HMAC-SHA-256 field.

P0 does not execute Argon2, AES or HMAC verification. The PPK public section is
therefore treated as unauthenticated until the later passphrase/MAC Gate. Its
public SSH blob must nevertheless match both the separately stored RFC4716
blob and the exact Owner fingerprint before preflight can pass.

## Output contract

`PpkImportPreflight` contains only:

- PPK/public-file/public-blob/encrypted-private SHA-256 coordinates;
- raw-public-derived BVP signer key ID SHA-256;
- OpenSSH SHA-256 public fingerprint;
- bounded Argon2 numeric metadata;
- fixed format/algorithm/encryption/KDF identity; and
- fixed no-effect state.

The following are schema/runtime constants false:

- `passphrase_received`
- `private_mac_verified`
- `private_key_decrypted`
- `custody_import_authorized`
- `custody_import_started`
- `signing_authorized`
- `external_effect_authorized`

Raw path, comment, public body, encrypted private body, MAC, salt, passphrase,
seed and decrypted private material are never returned.

## Failure modes

| Failure | Required result |
|---|---|
| empty, oversized, NUL, non-ASCII or truncated input | reject |
| PPK v2/unknown version or non-Ed25519 | reject |
| unencrypted/non-AES-256-CBC PPK | reject |
| non-Argon2id or noncanonical/out-of-ceiling KDF metadata | reject |
| malformed salt/base64/MAC or non-block-aligned ciphertext | reject |
| malformed/trailing/duplicate/reordered header | reject |
| malformed SSH wire public blob | reject |
| PPK/RFC4716 public mismatch | reject |
| Owner fingerprint mismatch | reject |
| checksum/effect/unknown-field forgery on admission | reject |

No fallback, repair, conversion, decryption, retry or external process exists.

## Allowed files

- `src/ai_video_production/owner_signing_key_ppk_preflight.py`
- canonical schema and package mirror
- `tests/test_task059_owner_signing_key_ppk_preflight.py`
- TASK-059 design/task registration and bounded task index row

Must not modify TASK-029 source/schema/test/history, credentials, R9B custody,
R9C/R9D signing, Knowledge Pack storage/promotion, shared CHANGELOG/LOCK,
Release, Deploy or Production state.

## Critic

- Critical: P0 could be mistaken for authenticated PPK validation. Resolved by
  fixed `private_mac_verified=false`, explicit unauthenticated-public wording and
  a state that names the later passphrase/MAC Gate.
- High: two attacker-controlled public files could cross. Resolved by requiring
  a third, exact Owner-confirmed OpenSSH fingerprint.
- High: malicious KDF metadata could authorize future resource exhaustion.
  Resolved by canonical positive parsing and fixed ceilings; P0 executes no KDF.
- High: encrypted private or comment bodies could escape into Evidence. Resolved
  by returning only the required encrypted-container coordinates and testing
  body/effect exclusion.
- Medium: a low-entropy comment digest could expose a dictionary-guess surface.
  Resolved by omitting the individual digest; the whole-file digest retains binding.
- Medium: truncated headers initially raised `IndexError`. Resolved by bounded
  minimum-shape rejection before ordered parsing.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

## Tester

- P0 focused synthetic tests: `26 PASS`
- P0 plus direct R9A/R9B/R9C: `53 PASS, 1 intentional Windows DPAPI skip`
- TASK-029 plus TASK-059: `143 PASS, 4 intentional Windows DPAPI skips`
- format/schema mirror and Draft 2020-12 validation: `PASS`
- public crossing/fingerprint/tamper/size/KDF/header negatives: `PASS`
- secret-input/filesystem/subprocess/network/custody static boundary: `PASS`

No real Owner key or secret-bearing operation was used.

## Judge

Decision: `GO` for local P0 commit-ready integration. This GO authorizes only
the no-secret preflight contract. P1 design, implementation and native execution
remain separate Human/DEV-4 Gates.
