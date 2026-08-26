# TASK-059 P1C-J1 - Trusted Launcher Lifetime Binding Evidence

Date: `2026-08-27`

Identity: `TASK-059-P1CJ1-TRUSTED-LAUNCHER-LIFETIME-BINDING-EVIDENCE-V1`

Status: `PASS_NATIVE_MANUAL_GATE_REMAINS`

Development depth: `DEV-4 PRIVACY, AUTHORIZATION AND RELEASE INTEGRITY`

## Outcome

The canonical TASK-036 trusted launcher now accepts one optional, already
constructed `OwnerSigningKeyPpkShellService`, passes the same instance to the
body-free Shell bridge and owns its transient lifetime.

This is a composition seam only. It does not infer or hardcode an expected
fingerprint, Owner-scope digest, custody destination, public/private key path or
packaged-helper digest. Without an exact trusted factory binding, the existing
Settings card remains fail-closed as `UNAVAILABLE_CONFIGURATION`.

## Implemented contract

- `build_trusted_launch` accepts one optional typed trusted signing-key import
  service.
- The exact service instance is injected into the canonical
  `Task036ShellBridge`.
- `Task036TrustedLaunch` owns and closes the service once.
- Repeated successful launch close does not close the service twice.
- A launch-construction failure closes the supplied service best-effort.
- A signing-key service close failure does not strand the local-operation
  lifetime, runtime lease or Product store; the original service exception is
  re-raised after those normal resources close.
- Existing runtime-lease in-flight close refusal remains unchanged: the lease
  field stays present so the caller can close again after the operation exits.

## Review findings and fixes

High finding: the first test insertion split the existing trusted composition
test and accidentally moved its later assertions under the new test.

Fix: restored the original test boundary and placed both lifetime tests after
the complete composition test.

High finding: clearing every resource field in nested `finally` blocks would
break the existing retry contract when an in-flight runtime lease refuses
close.

Fix: only the new transient signing-key service is detached before its close
attempt. Existing local lifetime, lease and store fields retain their original
close-success ownership semantics. A signing-key service error is delayed until
the normal resource chain completes.

Residual Critical/High/Medium/Low: `0 / 0 / 0 / 0`.

## Verification

Executed on Windows Python 3.12:

- Lifetime, signing-service-close failure and concurrent in-flight close:
  `3 PASS / 36 DESELECTED`.
- Complete TASK-036 trusted launcher module: `39 PASS`.
- Trusted launcher plus direct P1C-I Shell bridge/service regression:
  `53 PASS`.
- `git diff --check`: `PASS`.

No file picker, Credential UI, real PPK, passphrase, DPAPI custody, signing,
installer, publish, promote, Release, Deploy or Production action was executed.

## Remaining native gate

Actual Windows Credential UI masking, focus, accessibility, Cancel, OK,
timeout and result-lost observation remains `NOT_CONFIRMED`.
Authentication-dialog automation is prohibited by the applicable Computer Use
policy, and the available GUI-control kernel failed to initialize. This
unavailability does not authorize a different automation mechanism.

The next permitted implementation unit may define the exact trusted
configuration source and factory only when its canonical fingerprint,
Owner-scope and custody-path authority exists. Real-key import remains a
separate Human Gate.
