# Parallel Lock / Roadmap Hosting Governance Evidence

Date: `2026-08-15`
Unit: `DOCS_ONLY_LOCK_AND_ROADMAP_HOSTING`
Branch: `codex/parallel-lock-task036-task046`
Exact audit base main: `25e2e04fb3360af77017a4a42e868fc95b15ec80`
Governance: `BAI Development OS CONSUMER_PROJECT_MODE / DEV-4`

## Owner Directive and package integrity

The Owner-authorized package
`BAI_VIDEO_PRODUCTION_PARALLEL_DEVELOPMENT_LOCK_HANDOFF_Ver1.0_2026-08-15.zip`
was read in the prescribed order. Its observed SHA-256 is
`e6297d54fbbe4f7d4418358ba57d243ecd81aca55b2c112b2a07954b58bb098d`,
which exactly matches the supplied digest.

The existing TASK-036 P-UX-1C checkout was not used to create this branch and
was not patched, copied, stashed, reset, cleaned, committed or re-based. This
unit uses an independent clean clone from exact remote main.

## Current Main Audit

- remote main and the clean checkout both resolved to
  `25e2e04fb3360af77017a4a42e868fc95b15ec80`;
- open pull requests: `0` at audit time;
- PR #90 exact head `664722d0fac8cc0e79f7c424c6911f4651ceb303`
  is `MERGED` at the exact audited main;
- PR #90 hosted checks: `9 / 9 PASS`;
- post-merge main CI workflow `31871164920`: PASS;
- post-merge main Security workflow `31871164981`: PASS;
- the canonical documents still said P-VS-0 `HOSTED_PENDING` and incorrectly
  kept TASK-046 P-VS-0 as the active route;
- the existing `owner_narration.py::VoiceProfile` is canonical; proposed new
  `voice_profile*.py` files did not yet exist on main.

The checkout and GitHub main are the implementation Source of Truth. The Pack
is Owner authority and a proposal, not a replacement for fresh-main evidence.

## DEV-4 re-decision

This coordination remains DEV-4 because it controls concurrent modification
of Shell/native WIP and future private VoiceProfile metadata, plus merge order
and Shared Integration Files. The docs-only unit itself performs no runtime,
private-data, Provider or external application operation.

## Integration Lock and Allowed Files

The exact Allowed Files are machine-readable in
`ACTIVE-WORK-LOCKS.json::integration_lock.allowed_files`. They comprise twelve
Product-owned Governance documents: Project/Changelog state, current-state,
task-index, canonical Roadmap, Voice architecture, TASK-046 Task/P-VS-0/
acceptance Evidence and the three Work Lock documents.

No `src/`, schema, package-version, `.github`, release, native-app or external
Project file is changed by this unit.

## Builder Design

1. Synchronize PR #90/P-VS-0 to `HOSTED_CLOSED` with exact head/main/checks.
2. Make TASK-036 P-UX-1C the active Consumer route while retaining its frozen
   WIP resume gate.
3. Split P-VS-1 into:
   - P-VS-1A: Shell-independent, body-free, non-executing
     `VoiceProfileRevision` Backend;
   - P-VS-1B: successor-mock-gated Voice Shell/TASK-014 integration.
4. Host two disjoint ACTIVE File Locks and the Shared Integration Lock rule.
5. Allow P-VS-1A branch development after fresh-main audit/design review, but
   require P-UX-1C hosted closure and fresh-main rebase before P-VS-1A merge.
6. Preserve every Native/paid/Cloud/Credential/private-body/release prohibition.

## Critic Pass 1

Decision: `CHANGES_REQUIRED`.

Findings:

1. **High — duplicate VoiceProfile authority risk.** The Pack's candidate
   `voice_profile.py` name could be implemented as a second canonical
   `VoiceProfile`, even though `owner_narration.py::VoiceProfile` already owns
   narration identity.
2. **High — P-VS-1A Allowed Files were broader than the final separation.** The
   historical P-VS-0 design still tentatively included `__init__.py`, broad
   `test_task046_*` and global synchronization files that the new Developer 2
   Lock explicitly denies.

Corrections:

- renamed the new domain/file/schema authority to `VoiceProfileRevision` /
  `voice_profile_revision`;
- recorded `owner_narration.py` as read-only and prohibited a second
  `VoiceProfile` class or narration planner;
- removed `__init__.py`, global documents and the broad test glob from P-VS-1A
  Allowed Files;
- aligned the P-VS-1A Registry, Architecture, Task and P-VS-0 design text.

Post-correction unresolved Critical/High: `0 / 0`.

## Critic Pass 2

Decision: `CHANGES_REQUIRED`.

Finding:

1. **High — initial Integration Lock was not exact-file enforceable.** Shared
   Integration Files existed, but `integration_lock` itself omitted the exact
   Allowed Files for this hosting branch.

Correction:

- added all twelve exact changed paths to
  `integration_lock.allowed_files` and re-ran branch-diff containment;
- changed files outside Integration Allowed Files: `0`;
- exact P-UX-1C/P-VS-1A Allowed File overlap: `0`;
- both implementation Locks: `ACTIVE`;
- stale current `HOSTED_PENDING` and unqualified current P-VS-1 references:
  `0` (the Addendum title and explanatory split heading are not Task-unit
  state claims).

Post-correction unresolved Critical/High: `0 / 0`.

## Judge Decision

Decision: `PASS_FOR_DOCS_ONLY_HOSTING`.

The state, Roadmap, P-VS-1 split and File Locks are coherent and may be hosted
as one documentation-only coordination PR. This decision does not authorize
P-UX-1C implementation until the hosting PR is merged to main and every WIP
hash matches. It does not authorize P-VS-1A patching until Developer 2 records
fresh-main Audit, DEV-4, exact Allowed Files, two Critic correction cycles and
Judge. P-VS-1A may not merge before P-UX-1C hosted closure and fresh-main
rebase. P-VS-1B remains blocked by successor mock and separate Authorization.

Model download/load/inference, recording, training, voice/audio body storage,
Credential, paid/Cloud Provider, external application mutation, Human ACCEPT/
LOCK, version, Tag, Release and Deploy remain unauthorized.

## Local Validation

- Windows Python 3.12 full regression: `1166 passed / 1 intentional
  non-Windows skip`;
- Ubuntu WSL2 full regression: `1167 / 1167 PASS`;
- Windows compileall `src tests`: PASS;
- Ubuntu WSL2 compileall `src tests`: PASS;
- WSL2 test venv: isolated under `/tmp` and removed after validation;
- Lock Registry JSON parse: PASS;
- P-UX-1C/P-VS-1A exact Allowed File overlap: `0`;
- Integration branch changed files outside exact Allowed Files: `0`;
- runtime/source/schema/package-version changes: `0`;
- `git diff --check`: PASS (platform line-ending notices only).

Hosted PR checks, exact merge SHA and post-merge CI remain the external closure
gates for this unit.
