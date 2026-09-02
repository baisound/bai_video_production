# TASK-063 U2 fail-closed surface evidence

Date: 2026-09-03

## Binding

- Base chain: `origin/main@f46179ec2c32d1d81635ff9eaf1ff9c6a1efeee8`
- Prior TASK-063 commit: `8399ec8963a2c1f657e9eeaa188765ee68276491`
- Branch: `codex/task-063-r01-readonly-lc01-r0`
- Design unit: `U2 FAIL_CLOSED_SURFACE`

## Result

The three legacy public mutation surfaces now fail with the stable body-free
code `TASK063_PRIVATE_COMPOSITION_REQUIRED` before validating caller data,
calling a failure hook, or touching the selected path:

- `provision_installed_bridge`
- `provision_and_write_installer_readback`
- `write_installer_readback`

The historical mutation implementation is retained only under explicit
module-private test-only names so existing isolated regression fixtures remain
bounded. Those names are absent from `__all__`. They are not Product authority,
not private-composition substitutes, and are not used by the installer CLI or
packaged entry.

`discover_installed_bridge` remains a read-only audit surface. Its result and
public receipt remain data only.

## Verification and effects

- focused U2 plus retained U1/R01/LC01 tests: 19 PASS
- `python -m py_compile`: PASS
- `git diff --check`: PASS
- public provision effect: 0
- public readback publication effect: 0
- caller failure-hook invocation: 0
- unrelated overwrite/delete: 0
- native installer/package effect: 0
- real TASK-070/TASK-072 binding: 0
- Release/Deploy/Production Activation: 0

The packaged-entry runtime tests remain environment-blocked by the absent
`jsonschema` dependency in the available host interpreter. Source outside the
TASK-063 Allowed Files was not changed. The existing packaged route imports
the now-fail-closed public surfaces, so no legacy public mutation can complete
without the future owner-supplied private composition.

No TASK-063 corrective completion or Production-linkage PASS is claimed.
