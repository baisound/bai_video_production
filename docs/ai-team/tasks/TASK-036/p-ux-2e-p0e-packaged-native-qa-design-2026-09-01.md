# TASK-036 P-UX-2E P0-E Packaged-Native QA Design

Date: `2026-09-01`
Execution owner: `L3 Integration, Packaging & QA`
Development depth: `DEV-4`
State: `IMPLEMENTATION_CORRECTION / PINNED_SNAPSHOT_AND_TASK063_HANDOFF_PARKED`

## 1. Goal and current boundary

P0-E extends the existing effect-free model-to-export fixture with a bounded,
versioned packaged-native QA contract. The fixture currently proves the real
Application and Shell composition through exactly one `QUEUED` Export Job; it
does not dispatch, launch the packaged EXE, or prove native output.

The current PowerShell harness is only a deterministic template projection. It
accepts expected source/package/fixture coordinates, validates their grammar,
and emits a path-free JSON projection to stdout. It reads and writes the
filesystem zero times. Every expected coordinate is explicitly unverified,
`authority_created=false`, `technical_result=NOT_CONFIRMED`, and every effect
flag remains false.

The previous inspection-harness design is **SUPERSEDED**. Two path reads or
byte-equal snapshots do not prove one pinned physical package/fixture snapshot,
and `CreateNew` through an unpinned parent does not prove safe durable receipt
publication. The correction closes those claims by removing the reads, writes,
and currentness assertions. It does not claim PowerShell solved them.

## 2. Authority and effect ceiling

- Template projection, static tests, fixture tests, runbook design, acceptance
  design, and negative/fault matrices are allowed now.
- Expected commit and digest values are coordinates only. They are not package
  build-manifest verification, installed-byte verification, or authority.
- Real package/fixture verification requires a future trusted native helper
  that pins nofollow handles, ancestor/parent identity and security state,
  returns raw bytes/hash and physical identity from the same snapshot, and
  preserves that currentness through launch/readback.
- Receipt persistence requires an operation-owned pinned parent and safe
  noreplace publication/readback. The current template persists nothing.
- Final packaged-entry adoption remains parked until the TASK-063 terminal
  handoff is consumed by the trusted operation.
- No install, download, Provider selection, generation, Export dispatch,
  Resolve mutation, Release, Deploy, or Production Activation is authorized.

## 3. Allowed files and scope

The PR #474 follow-up unit is limited to:

- this TASK-036 Design Packet;
- `tools/windows/run-task036-p0e-native-qa.ps1`;
- `tests/test_task036_p0e_native_qa_contract.py`;
- `tests/test_task036_p0e_fixture_vertical_slice.py` for additive fixture
  identity or effect-zero assertions;
- `packaging/task036_shell.spec` only after a concrete static omission is
  proved and accompanied by a focused packaging test.

It must not modify TASK-064, TASK-065, TASK-067, PR #471, its Dev2 branch,
Provider/Credential/generation/Timeline/Export/installation/connector/
activation state machines, or shared roadmap/current-state/CHANGELOG files.

## 4. Current projection contract

`task036-p0e-native-qa/v1` emits:

- `TASK036-P0E-AI-SETTINGS-STARTUP-INTEGRATION-V1`;
- expected source commit and expected fixture/executable/package-tree SHA-256;
- `source_commit_verified=false`;
- `fixture_snapshot_verified=false`;
- `package_snapshot_verified=false`;
- `receipt_persisted=false`;
- `task063_terminal_handoff_consumed=false`;
- packaged-entry, first-run, single-instance, startup-error/readback, model
  setting persistence, native/provider/install/export/Resolve/release/deploy/
  activation/path-persistence flags all false.

Well-formed but wrong expected coordinates remain unverified. The projection
cannot distinguish them from correct coordinates and must never be used as a
completion receipt.

## 5. PR #471 startup-integration candidate

PR #471 is a preserved implementation candidate at
`e11dabca1a6c5ed17b2f93bf2bbcabfdb85a2dea`. It remains Draft; this unit does
not mutate or adopt its source.

Its intended integration contract keeps two states separate:

- `configuration_selectable=true`: a candidate may be selected and persisted
  in central AI settings;
- runtime `READY`: the configured candidate is currently executable.

Feature pages must read the central setting, show a stable Japanese reason and
navigation link when unset/unavailable, and must not create a second selection
authority. Final binding to `task036_packaged_entry.py`, first-run startup and
packaged persistence awaits the TASK-063 terminal handoff plus fresh source and
overlap review.

## 6. Packaged-native acceptance after the park clears

The trusted Windows operation must verify, in one bound run:

1. exact TASK-063 selected package/EXE identity and build manifest;
2. clean-profile first run and the complete F0..F10 visible flow;
3. single-instance behavior for a second/concurrent launch;
4. body-free stable Japanese startup errors with durable UI readback;
5. central model selection persistence across close/restart without silently
   turning a selectable-but-unavailable candidate into runtime `READY`;
6. UI settings readback matching the bound Product setting and build;
7. UI-to-Export flow reaching exactly one queued Job while dispatch remains
   zero until its separate Human gate;
8. only after the dispatch gate, exact output bytes/media properties, TASK-011
   Render QA and packaged UI readback of that same Job/result.

## 7. Required native negative and recovery matrix

- missing/wrong/stale TASK-063 handoff, package manifest, EXE, fixture or build;
- ancestor reparse, same bytes/different inode, parent swap, package member
  swap, DACL drift and receipt-parent replacement;
- corrupt/missing settings, stale configured candidate, runtime unavailable,
  first-run crash and restart during persistence;
- second/concurrent launch and single-instance ownership loss;
- missing, reordered or stale F0..F10 checkpoints and wrong Project/Job;
- crash before dispatch, possible-dispatch `UNKNOWN`, output-before-readback and
  readback-before-receipt; never replay a possibly dispatched Job;
- foreign replacement during cleanup: preserve it, effect zero on that object;
- public error/receipt leakage of paths, usernames, values, prompts, media,
  credentials, confirmation tokens or raw OS exceptions.

## 8. Verification and checkpoint

Current effect-zero verification order:

1. PowerShell 5.1 AST/static safety contract;
2. deterministic projection and malformed-coordinate rejection;
3. focused fixture, packaging and packaged-entry regressions;
4. independent Critic/Tester/Judge;
5. hosted checks.

Future gated verification adds the trusted native pinned-snapshot helper,
TASK-063 handoff consumption, clean Windows package build, packaged EXE launch,
restart/readback, and separately authorized Export/native QA.

Historical pre-correction PowerShell package inspection and receipt-write test
results are not current acceptance Evidence. The current template performs
filesystem read/write zero, creates no durable receipt, and claims no package,
fixture, commit, startup, persistence, or native currentness.
