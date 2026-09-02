# TASK-063 Terminal Handoff Fixture Plan

Status: `PREPARATION_COMPLETE / SOURCE_EFFECT_PARKED / NATIVE_NOT_CONFIRMED`

## Current binding

- Repository: `baisound/bai_video_production`.
- Canonical source: `origin/main@df99723ee6e94d657652641b1b2825bbaa8fffc6`.
- Preparation branch: `codex/task-063-terminal-handoff-fixtures-r0`.
- Development profile: `DEV-3 HIGH ASSURANCE` with the existing DEV-4
  corrective design retained as the stronger design boundary.
- Target-path open PR overlap at preparation start: zero.
- Existing TASK-063 worktrees are historical or separately owned and remain
  untouched.
- The primary checkout's unrelated untracked TASK-036/TASK-066 files and
  worktree directories are preserved and are not inputs to this unit.

The current `origin/main` contains the historical TASK-063 path-safety and
installer-readback race corrections, but it does not contain
`src/ai_video_production/secure_authority_io.py`. Therefore the corrective
source cannot yet consume the required TASK-068 `IMMUTABLE_SECURE_IO_V1`
foundation. Only the source effect is parked; the fixture and handoff contract
below are complete.

## Why the historical native PASS is not terminal evidence

`windows-install-relative-bridge-evidence-2026-08-30.md` remains valid evidence
for its exact historical source, installer and bounded custom-root run. It does
not prove the current corrective terminal handoff because that run did not
produce all of the following in one live operation:

1. a TASK-068-backed pinned selected-root and secure I/O identity;
2. a TASK-070 descriptor/owner pair terminal plus private simultaneous pair
   readback;
3. a TASK-063 private `INSTALLATION_READBACK_V2` issued from that live pair;
4. a TASK-072 installed-instance Profile binding followed by terminal-success
   readback before lease/handle release;
5. current corrective repair, upgrade and portable-rebind observations; and
6. a fresh uninstall-preservation readback for the exact current package.

Consequently `post_repair_native_installed_receipt` is absent and Production
linkage remains `NOT_CONFIRMED`. Public descriptor, owner, discovery and legacy
installer-readback documents remain audit evidence only.

## Existing regression coverage retained

The following current tests are reusable historical regressions:

- Unicode/spaced custom root and exact relative layout;
- repair preserves `install_instance_id` and `created_at`;
- descriptor tamper rejection;
- unsafe existing readback directory, symlink and hardlink rejection;
- forged layout root, migration ancestor swap and upper ancestor drift;
- concurrent new readback target no-clobber;
- post-write readback mismatch;
- exact safe readback update with one link;
- forged predecessor and missing predecessor receipt rejection;
- update/fresh rollback fixtures;
- fixed ProgramData active literal zero; and
- installer destination selection, reparse checks and uninstall data
  preservation source contract.

These regressions do not establish the same-open pair generation, secure
operation lock, strict authority JSON, identity-bound rollback or terminal
installed receipt required by the corrective design.

## Frozen fixture contract

The machine-readable fixture is
`tests/fixtures/task063/terminal-handoff-negative-fixtures-v1.json`. It is
explicitly `fixture_only:true`, `authority_created:false` and
`native_effect_executed:false`.

### I63-R01 — sealed descriptor/owner read

Exercise descriptor and owner stat-open, read-post, same-bytes/different-inode
and mixed-generation swaps. Apply strict bounded UTF-8 rejection to descriptor,
owner, installer readback and rollback preimage: equal/different nested
duplicates, NaN/Infinity, BOM, trailing bytes, control characters, excessive
depth and excessive size. Parse and hash only bytes from the same pinned open
snapshot. Every rejection preserves the ambiguous bytes and yields discovery
receipt zero and filesystem delta zero.

### I63-L01 — secure installer operation lock

Exercise initial race loser, existing lock identity swap, symlink, reparse,
hardlink, DACL drift and ancestor drift. The future source must use the
TASK-068/TASK-070 producer contract; it must not recreate a generic lock inside
TASK-063. Race losers fail closed without automatic retry, pair effect or
cleanup of a foreign object.

### I63-P01 — provision/update pair publication

Exercise concurrent first provision, absent target appearing with identical or
different bytes, expected inode/bytes changes immediately before publication,
mixed owner generation, post-publication swaps and directory durability
failure. Pair publication belongs to TASK-070. TASK-063 may issue an installed
readback only after the exact pair terminal and simultaneous pinned readback.
The result is pair generation exact zero or one, unrelated overwrite/delete
zero, and no PASS when durability is unknown.

### I63-B01 — installer readback publication

Exercise operation-temp replacement after close, absent/existing target races,
prepublish and postpublish swaps, directory fsync failure and exact readback
mismatch. Operation-owned identity must remain pinned; foreign replacement is
never unlinked. Receipt count is exact zero or one, and public failures expose
neither absolute paths nor OS details.

### I63-RB01 — rollback and recovery

Exercise foreign descriptor/readback replacement in fresh and update paths,
ambiguous preimages, one-sided descriptor/owner states and unknown terminal
state. Path-only restore/delete is forbidden. Unknown and foreign state is
STOP+preserve with automatic repair, cleanup, restore and delete all zero.

### I63-LC01 — lifecycle

Exercise verify/repair, upgrade revision, portable rebind, multiple-install
ambiguity, uninstall preservation and fixed ProgramData fallback absence.
Repair is read-only and preserves the exact instance. Upgrade advances one
bound revision without replacing the immutable pair. Portable rebind requires
the exact predecessor and an admitted empty destination. Cross-instance
adoption and automatic old-data deletion remain zero.

## Exact Allowed Files candidate

### This preparation unit

- `docs/ai-team/tasks/TASK-063/terminal-handoff-fixture-plan-2026-09-02.md`
- `tests/fixtures/task063/terminal-handoff-negative-fixtures-v1.json`

### Future corrective source unit after producer receipts

- `src/ai_video_production/montage_learning_installation.py`
- `tests/test_task063_install_relative_bridge.py`
- `tests/test_task063_main_installer_contract.py`
- `tests/fixtures/task063/**`
- `docs/ai-team/tasks/TASK-063/**`
- `schemas/montage-learning-installation-readback.schema.json` and
  `src/ai_video_production/schema_resources/montage-learning-installation-readback.schema.json`
  only as a byte-identical pair when the public audit projection requires a
  schema change.

Excluded: `atomic.py`, TASK-068/TASK-070/TASK-072 source or tests, File Bridge,
promotion, activation, SKILL, GF-D, installer packaging/build scripts, shared
current-state/roadmap/task index, `CHANGELOG.md`, real install and all
Release/Deploy/Production effects.

## Source-start prerequisites

Before source or test mutation, all of the following must be fresh and exact:

1. TASK-068 is integrated on canonical `main` with its completion receipt and
   exact implementation identity.
2. TASK-070 pair producer and TASK-072 ticket/binding producer contracts needed
   by the selected Atomic Unit are integrated or supplied as explicitly
   non-authoritative fixture ABIs.
3. a new worktree is created from then-current `origin/main`;
4. target-path open PR, worktree, dirty ownership and work-lock overlap are
   zero; and
5. the implementation unit is restricted to the exact Allowed Files above.

No old TASK-063 worktree or historical native receipt may be reused as current
authority.

## Acceptance for terminal handoff

- `I63-R01/L01/P01/B01/RB01/LC01` fixture cases are all mapped to a focused
  test or a named producer-owned contract test.
- Descriptor and owner are accepted only as one simultaneous pinned pair
  generation; same fields or bytes from another identity never pass.
- Strict JSON ambiguity causes effect zero and preserves the input.
- Locks, temporary files, targets, rollback and cleanup are identity-bound;
  unrelated overwrite/delete/restore remains zero.
- Directory durability failure and post-readback mismatch never produce a
  receipt or PASS.
- First provision, repair, upgrade, adoption and portable rebind preserve exact
  instance and predecessor semantics; uninstall preserves Bridge data.
- A private `INSTALLATION_READBACK_V2` exists only inside the exact live
  TASK-070/TASK-063/TASK-072 operation. Public evidence creates no authority.
- Native and installed completion remain `NOT_CONFIRMED` until fresh Windows
  evidence for one exact current candidate closes the Product linkage Gate.

## Next action

After TASK-068 reaches canonical `main`, rebind this fixture to the new main,
verify producer ABI currentness, allocate one corrective source Atomic Unit,
and implement `I63-R01` plus the read-only part of `I63-LC01` first. Pair write,
ticket and terminal effects remain parked until their exact producer receipts
are available.

## Preparation verification

- strict JSON parse of the machine-readable fixture: `PASS`;
- exact group order and non-authority flags: `PASS`;
- `git diff --check`: `PASS`;
- existing TASK-063 focused pytest suites: `NOT_EXECUTED` because both the host
  Python and the bundled workspace Python lack the already-required
  `jsonschema`/`pytest` packages. The host attempt stopped during collection
  with `ModuleNotFoundError: jsonschema`; the bundled runtime has neither
  package. No dependency install or weaker-environment workaround was
  authorized or performed;
- source, schema, package, installer, native, Release, Deploy and Production
  effects: zero.
