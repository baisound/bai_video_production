# TASK-029 R9B — PuTTYgen Key Creation and Owner Custody Configuration Runbook

State: PRE-EXECUTION
Date: 2026-08-26
Authority: current Owner sleep window only; expires immediately when Owner says "おはよう"

## Secret rule

Never paste, print, screenshot, commit, upload, or send a private key, PPK body, seed, or passphrase to Codex, ChatGPT, Git, PR, CI, logs, or documentation. Only public-key material and body-free SHA-256 identifiers may be recorded.

## Preconditions

1. Confirm the sleep-window authority is still active.
2. Confirm PuTTYgen is installed from an approved source using the R9A installation runbook.
3. Confirm the R9B custody source and tests are present and green.
4. Use only an Owner-local fixed NTFS directory with private ACLs. Do not use the repository, visualizations directory, OneDrive, network storage, removable media, or project/media directories.
5. Close screen recording, clipboard history capture, terminal logging, and unrelated remote-control tools.
6. A strong passphrase must be entered directly into PuTTYgen by the Owner or through an Owner-approved secret-custody mechanism. It must never be supplied through a prompt or automation transcript.

## PuTTYgen creation procedure

1. Launch PuTTYgen.
2. Select EdDSA and Ed25519.
3. Choose Generate and move the pointer only inside the PuTTYgen window until generation completes.
4. Verify the public key is shown and the fingerprint identifies an Ed25519 key.
5. Enter and confirm a strong unique key passphrase locally.
6. Save the private key as an encrypted PPK in the approved Owner-private directory.
7. Export or copy only the public key into a separate public-only file if required.
8. Do not use Conversions or export an OpenSSH private key in this Unit.
9. Close PuTTYgen, reopen the encrypted PPK, and verify that its passphrase is required. Do not record the passphrase.

## BVP boundary

PuTTYgen PPK and OpenSSH formats are not the BVP R9B raw 32-byte seed contract. No PPK conversion or BVP import may occur until a separately verified converter/loader and exact native import procedure exist. R9B source exposes no signing or private-key export API. Therefore key generation may be evidenced independently, but BVP custody must remain NOT EXECUTED unless the exact format bridge and passphrase-safe import gate are available.

## Evidence to record without secrets

- PuTTYgen version and executable SHA-256
- execution timestamp and current Windows user scope (body-free)
- algorithm: Ed25519
- private key path represented only as a body-free SHA-256 coordinate
- public-key-derived signer key ID SHA-256
- encrypted PPK created: YES/NO
- passphrase required on reopen: PASS/FAIL/NOT_EXECUTED
- BVP custody import: PASS/FAIL/NOT_EXECUTED
- real signing: NOT_EXECUTED
- document bytes, SHA-256, Git commit/blob identity

## Stop conditions

Stop immediately if the Owner says "おはよう", the target directory or ACL is uncertain, a secret would enter logs/clipboard/chat, the passphrase cannot be entered safely, the installed binary identity is uncertain, or PPK-to-BVP conversion would be required. Preserve no secret in temporary files.

## Post-execution result version

After any native action, create a separate result document. Do not overwrite this pre-execution runbook. The result must list each step as PASS/FAIL/NOT_EXECUTED, any created artifact only by safe identity, exact cleanup, and all unexecuted boundaries.
