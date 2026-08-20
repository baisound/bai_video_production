# TASK-014 AU2B2 — Qwen3-TTS Pinned Snapshot Verifier R0 Evidence

- Authority: TASK-014 / AU2B2, DEV-4
- Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / COMMIT_READY / UNCOMMITTED`
- Worktree: `codex/task-014-pinned-snapshot-verifier-r0` at `4ae3ea8df56ba76ef4eb29c10584ff3de55be740`
- Scope: the five AU2B2 contract files plus the CI-required `CHANGELOG.md` release-metadata entry

## Implemented boundary

`qwen3_tts_pinned_snapshot_verifier.py` is a pure local verifier. It accepts a strict, body-free manifest mapping; recomputes its entries and semantic SHA-256 values including the exact `retrieved_at` string; and verifies only already-local files through bounded streaming hashes.

The production entrypoint admits only the Owner-supplied Qwen/Qwen3-TTS-12Hz-0.6B-Base pin:

- revision: `5d83992436eae1d760afd27aff78a71d676296fc`
- entries digest: `sha256:8c40ca449eb8fcf1bd55c4b272d40a29dd6dd91d1c419120ae24795d0c9482a3`
- semantic digest: `sha256:8ee07dcddf13d95aa225df9167d4695b42e245b431686d8acb26bbd4a5e80935`
- 13 files / 2,516,106,051 bytes

The generic internal verifier is test-only plumbing for a generated 13-file fixture. It does not grant production admission.

The manifest parser consumes the exact AU2B1 machine-readable artifact shape
(`schema_version`, source object, file `bytes`/SHA-1/digest-source/load-input
coordinates, descriptions, and no-effect flags). It reproduces the documented
ASCII/NUL entry stream and canonical scalar stream rather than substituting a
JSON-container digest. A direct read-only parse of the JUDGE_ACCEPTED AU2B1
artifact reproduced both accepted bare SHA-256 digests.

Receipt decisions are `VERIFIED`, `BLOCKED`, or `UNKNOWN`. Reason codes are closed and ordinal-sorted. Known safety blockers take precedence over unknown filesystem observations. Private receipts contain only a root fingerprint; the public projection redacts it. All serialized effect flags remain false: no download, package operation/import, model load, audio read, inference, or firewall change is exposed.

Both the private receipt and public projection are diagnostic observations only.
The private receipt may be persisted for Evidence, but its ordinary SHA-256 is
self-consistency rather than origin authentication and is not a capability or
gate. Both forms explicitly keep model reuse, model load, and post-return state
authority false and require consumer revalidation. The public projection is
non-persisted and redacts the private root fingerprint.

## Filesystem safety

- rejects non-leaf, relative, UNC/device, volume-root, symlink, and Windows reparse roots;
- on Windows, admits only a `DRIVE_FIXED` local root before any `lstat`/directory enumeration; mapped/remote, removable, unknown, optical, RAM, and failed drive-type classifications fail closed;
- permits exactly the manifest’s 13 normalized files and the sole `speech_tokenizer` ancestor directory;
- rejects extra files/directories (including an empty `.cache`), case changes, missing paths, and all reparse components;
- treats pre/open/post stat mutation and access failures as `UNKNOWN`; hashes only through streaming reads.

The path-based checks are a bounded point-in-time observation. They do not hold
root or directory identity handles and therefore cannot exclude a
swap-and-restore race or guarantee the tree after return. A later runtime gate
must use fresh revalidation with an authenticated handoff or a live held
capability; this persisted receipt alone cannot authorize reuse or load.

No provider, package installer, model/runtime loader, network, subprocess, snapshot copy, or write operation is imported or invoked.

## Local verification

- Manual generated-fixture integration: `PASS` (generic internal `VERIFIED`, same-size digest mismatch, and strict rejection of a nonaccepted persistent `VERIFIED` receipt). A separate no-I/O accepted-pin receipt test covers the persistent parser positive path.
- Python compileall: `NOT_CONFIRMED`; both available runtimes attempted to write a bytecode cache under the shared worktree and encountered the host permission boundary. A no-bytecode manual import/integration check passed instead.
- Schema JSON parse and public/package mirror byte equality: `PASS`
- `git diff --check`: `PASS`
- Focused pytest: `33 PASS` under the isolated `pytest 8.4.2` + `jsonschema 4.25.1` environment after the diagnostic-authority and receipt-parity hardening.
- Combined TASK-014 verifier + preflight/admission/owner targeted checks: `93 PASS`.
- Exact AU2B1 artifact parse, no-bytecode compile, Draft 2020-12 schema validation, schema mirror, diff check, and five-file scope check: `PASS`.
- Fresh-main rerun on `4ae3ea8df56ba76ef4eb29c10584ff3de55be740`: focused `33 PASS`; combined direct-dependency regression `93 PASS`; schema mirror SHA-256 `4a0d58b41afdd19ff0db6d6d4ec90ae8dc361c9be5758b6579ae8196fe8fc9ac`; JSON parse, no-write compile, diff and exact five-file scope checks `PASS`.
- Critic authority/provenance fix: private/public receipts are schema/parser-enforced diagnostic observations; capability, reuse, load and post-return guarantees are false; consumer revalidation is true. Exact RFC3339-UTC lexical schema parity and impossible UNKNOWN/pre-observation phase claims are rejected.
- Independent Tester: `PASS` (`C0 / H0 / M0`).
- Independent Critic/Judge: `ACCEPT` (`C0 / H0 / M0`).
- The final traversal hardening replaces `os.walk` with bounded `os.scandir`; it stops at 64 discovered directory/file entries and truthfully marks incomplete enumeration after a cap or pruned subtree.
- Windows ctime is excluded while stable device/inode/type/size/mtime observations remain before/open/after checks.

No native, paid, provider, model-download/load, audio, production, or deployment side effect occurred.
