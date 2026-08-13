# TASK-037..041 — Cross-Store Bundle Recovery Contract Ver.1.0

- Date: 2026-08-13
- Status: `AUTOMATED_FOUNDATION_PASS`

## Problem

Each Production Control, Audit, Prompt, Continuity and Audio JSON store can be internally valid while the **set** is inconsistent because only some stores were updated before a crash.

## Solution

A small `production-bundle.json` manifest pins the exact validated snapshot checksum of:

- `production-control.json`
- `candidate-audit.json`
- `prompt-registry.json`
- `continuity-registry.json`
- `audio-workspace.json`

The manifest is written only for a set that passes `ProductionBundleValidator`.

Recovery reloads every store, recomputes each domain snapshot hash and compares the complete set to the manifest before returning state.

If one valid store changed after the manifest was written:

```text
ERR_PRODUCTION_BUNDLE_SNAPSHOT_SET_CHANGED
```

No automatic repair and no automatic regeneration occur.

## Security

- fixed canonical relative filenames only;
- no path traversal aliases;
- manifest is self-hashed;
- replacement requires CAS against exact previous manifest hash;
- symlink manifest/root is rejected;
- manifest cannot grant repair/regeneration authority.

## Crash semantics

Individual stores remain atomic. If a multi-store update crashes before the new bundle manifest is published, recovery rejects the mixed set rather than guessing which version is correct. Operator/autonomous recovery must inspect and deliberately rebuild a new validated bundle checkpoint.
