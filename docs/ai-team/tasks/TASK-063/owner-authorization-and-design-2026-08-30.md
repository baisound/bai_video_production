# TASK-063 Owner Authorization and Canonical Design

## Authority

The Owner explicitly rejected the fixed production Bridge path, required
installer-selected-root-relative placement, asked the design responsibility to
record the decision, prohibited interruption of the three active development
lanes, and authorized this lane to compile, install and test the result.

This authorizes bounded implementation and native installation under:

`D:\BAI\BAI VIDEO PRODUCTION FOR DRFX\test-install\BAI Video Production`

It does not authorize Release, Deploy, production activation, legacy deletion,
cross-instance merge, private-media upload or Resolve Timeline mutation.

## Canonical coordinate

- `install_root`: exact installer-selected absolute root.
- `install_instance_id`: stable per-installation opaque UUID identity.
- `bridge_relative_path`: `data/montage-learning-bridge`.
- `bridge_root`: contained join of `install_root` and `bridge_relative_path`.
- `bridge-instance.json`: installer-instance descriptor with exact relative path,
  installer payload digest and self-hash.
- `bridge-owner.json`: existing BVP Bridge ownership contract bound to the same
  installation instance.

No active fixed absolute fallback is permitted. Multiple or unknown instances
must not be selected implicitly. The repository connector default remains
disabled until TASK-060 and TASK-061 close their separate source and activation
gates.

## Installer and lifecycle rules

- The installer owns application payload placement and invokes the private,
  headless provisioning command after the EXE is installed.
- Provision/read-back failure makes installation fail; file existence alone is
  not PASS.
- Upgrade/repair preserves an existing valid instance ID.
- Installer-created application payload may be uninstalled, but Bridge data is
  preserved by default and is never listed in recursive uninstall deletion.
- Legacy ProgramData data is untouched in this Task.
- Portable move, legacy copy migration, stronger Windows DACL attestation and
  Human activation remain follow-up responsibilities; no silent PASS is allowed.

## Design handoff provenance

The separate design task returned the bounded candidate
`DESIGN_RECORDED_IN_TASK_MESSAGE / IMPLEMENTATION0`, including install-root
containment, instance identity, descriptor/read-back, fail-closed discovery,
legacy copy-not-move, upgrade preservation, uninstall preservation and
multi-install isolation. TASK-063 records the source-bound subset that can be
implemented without expanding TASK-061 or interrupting other developer lanes.
