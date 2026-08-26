# TASK-059 P1C-J2 - Trusted Runtime Configuration Design, Critic and Judge

Date: `2026-08-27`

Identity: `TASK-059-P1CJ2-TRUSTED-RUNTIME-CONFIGURATION-DESIGN-V1`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

Decision: `GO_IMPLEMENTED_SYNTHETIC_ONLY_NATIVE_MANUAL_GATE_REMAINS`

## Goal

Bind the completed P1C-H/P1C-I Owner signing-key import components into the
canonical TASK-036 trusted Product launcher without inventing a second Product,
settings store, custody implementation or secret transport.

## Canonical source

The existing private TASK-036 launch configuration remains the only
configuration source. Version `1.3.0` requires exact sections:

- all base `1.0.0` sections;
- `local_generation`, which may be null or a valid existing runtime object;
- `local_image_generation`, which may be null or a valid existing runtime
  object; and
- `owner_signing_key_import`.

The signing-key section has exactly:

- `expected_openssh_sha256_fingerprint`;
- `owner_scope_sha256`; and
- `custody_destination_path`.

It contains no PPK path, public-key path, key body, private seed, passphrase,
helper path or helper digest. Unknown and missing fields fail closed. Legacy
versions `1.0.0` through `1.2.0` do not accept this section and remain
unbound.

## Composition

The trusted Python composition root:

1. constructs the concrete Windows native file/Credential dialog backend;
2. constructs the existing one-use PPK native Operator adapter;
3. uses only the packaged helper identity embedded by the canonical Product
   build;
4. constructs the body-free P1C-I Shell service with the exact trusted
   fingerprint, Owner scope and destination;
5. supplies canonical TASK-029 custody receipt read-back for result-lost
   recovery; and
6. gives the service to the existing trusted-launch lifetime owner.

No WebView request can replace these objects or coordinates. The normal
launcher representation redacts the nested signing-key configuration.

## Pre-secret destination gate

After public identity confirmation and immediately before native secret input,
the parent checks the exact destination using `lexists`. Any existing regular
file, directory, symlink or broken symlink fails with the fixed
`ERR_PPK_CUSTODY_IMPORT_DESTINATION_EXISTS` response. The native secret dialog
is not called.

The helper independently checks the destination again after authentication and
before READY/custody, preserving TOCTOU defense and one-shot no-overwrite
semantics.

## Authority and effects

Configuration parsing and service composition do not authorize or start file
selection, Credential UI, PPK decryption, DPAPI custody or signing. Real
configuration values and the direct Human confirmations remain necessary.

No install, download, settings mutation, application launch, real key read,
custody write, signing, publish, promote, Release, Deploy or Production effect
is part of this unit.

## Critic

High finding: the P1C-I flow reached the native secret dialog before the parent
checked whether the custody destination already existed. Although the helper
would reject later, this violated the P1 requirement to reject before
passphrase receipt.

Resolution: add a parent-side `lexists` gate immediately before native secret
input and retain the helper-side recheck.

High finding: a normal dataclass repr of the new nested launch configuration
could include the custody path and Owner-scope coordinate.

Resolution: disable generated repr on the nested configuration and add
negative assertions against the enclosing launcher configuration repr.

Compatibility concern: a new version must not force a local generation runtime
merely to enable the signing-key card.

Resolution: `1.3.0` carries both generation keys explicitly but permits each
to be null. Version `1.2.0` retains its existing at-least-one-runtime rule.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

## Judge

`GO` for the synthetic-only trusted configuration and composition boundary.

`NO GO` remains for automated Credential UI interaction, real PPK/passphrase
use, DPAPI custody, signing, Authenticode, installer, publish, promote, Release,
Deploy and Production without their exact separate Gates.
