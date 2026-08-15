# TASK-047 / P-OBS-1A Canonical Contract Lock Hosting Critic / Judge — 2026-08-15

## Authority and boundary

- Authorization: `BVP-AUTH-20260815-TASK047-POBS1A-CONTRACT-H0`
- Task unit: `TASK-047/P-OBS-1A-CONTRACT-HOST-H0`
- Authority: `HOST_DOCS_ONLY_CANONICAL_CONTRACT_LOCK`
- Implementation authority: `NOT_AUTHORIZED`
- Contract-content hosting H1: `NOT_AUTHORIZED_BY_H0`
- Lock closure H2 and state synchronization S0: `NOT_AUTHORIZED_BY_H0`

This unit hosts only the governance Lock required for a later, separately
authorized publication of the reviewed P-OBS-1A Rev.2.1 design contract. It
does not publish the contract itself and does not authorize Product or native
implementation, download, install, build, Plugin load, OBS launch or capture.

## Fresh source of truth

- Repository: `baisound/bai_video_production`
- Fresh pre-host main: `24d43daa201808fa2da11c0f6d8e61bbc1ffb45c`
- Immutable main tree: `01761943c9c0f9fa211857443404c723364d6cbf`
- Registry before this change: revision `5`, state `ACTIVE`
- Open pull requests at the transaction audit: `0`
- Active governance Locks: exact `2`
  - `BVP-LOCK-TASK046-PVS3A`
  - `BVP-LOCK-TASK048-PQC1A`
- Proposed four content paths present before H0: `0 / 4`
- Exact proposed-path overlap with either active Lock: `0`
- Remote H1 branch collision: `0`

P-VS-3A and P-QC-1A have hosted `ACTIVE` governance Locks, but their planned
contract implementation files are absent from main. No open PR or remote
implementation branch was present at the GitHub audit. The design coordinator
separately reported that P-VS-3A local implementation work had been authorized
and started in an isolated checkout; this H0 unit neither verifies that local
work nor upgrades it to hosted contract state.

## Exact H0 transaction

This branch changes exactly two files:

1. `docs/ai-team/work-locks/ACTIVE-WORK-LOCKS.json`
2. `docs/ai-team/work-locks/task047-pobs1a-contract-hosting-lock-critic-judge-2026-08-15.md`

The Registry delta is limited to:

- `registry_revision`: `5` -> `6`;
- `audit_base_main_sha`: exact fresh pre-host main;
- append one `BVP-LOCK-TASK047-POBS1A-CONTRACT-HOST` record with
  `status=ACTIVE`;
- reserve the exact four future contract-hosting files;
- retain `implementation_authority_state=NOT_AUTHORIZED` and
  `implementation_state=NOT_STARTED`.

There is no merge-order, Current State, Task Index, Roadmap, Architecture,
CHANGELOG, workflow, schema, source, test, package or runtime change.

## Future content boundary reserved by the Lock

The later H1 content unit, if separately authorized, may change only:

1. the consolidated Rev.2.1 canonical contract Markdown;
2. its machine-readable provenance JSON;
3. its pre-merge Builder/Critic/Judge hosting Evidence;
4. the existing TASK-047 Task document as a discoverability pointer.

The contract remains design authority only. A hosted design document does not
create P-VS-3A, TASK-043, TASK-003, P-QC or native runtime capability and does
not authorize an M0 or native implementation slice.

## Validation plan

Before commit and push, the Builder must prove:

- JSON parse succeeds and Registry revision is exactly `6`;
- active Lock IDs are unique and the active set is exactly the two existing
  Locks plus the new P-OBS contract-hosting Lock;
- the new Lock has exactly four unique allowed files;
- the H0 Git diff contains exactly the two authorized files;
- `git diff --check` passes;
- no existing implementation or shared-integration file changed;
- a fresh remote-main/open-PR/path-overlap race audit still passes.

Hosted checks must all become terminal `SUCCESS`. H0 stops at Draft PR until a
separate design Judge authorizes Ready and merge.

## Local pre-push validation

- UTF-8 JSON parse: `PASS`
- Registry revision: exact `6`
- Registry audit base: exact `24d43daa201808fa2da11c0f6d8e61bbc1ffb45c`
- Active Lock set: exact `3`, unique IDs `PASS`
- New Lock allowed files: exact `4`, unique paths `PASS`
- Existing active-Lock allowed-file overlap: `0 PASS`
- H0 changed files: exact authorized `2 PASS`
- `git diff --check`: `PASS`
- Product test suite: `NOT_REQUIRED_FOR_DOCS_ONLY_H0`; the clean Windows and
  WSL interpreters did not include `pytest`, so no local regression PASS is
  claimed. Hosted CI remains mandatory and is not replaced by this result.

## Critic pass 1 — source, overlap and authority

Initial findings:

1. **HIGH — an ACTIVE governance Lock could be mistaken for an implementation
   authorization.**
2. **HIGH — separately reported P-VS-3A local work could be misrepresented as
   a hosted dependency.**
3. **MEDIUM — adding Current State or Task Index repair here would expand a
   two-file Lock-host transaction and race the separate P-VS-3A work.**

Corrections:

- implementation and H1/H2/S0 authority are explicitly false;
- repository presence, open PRs and main contract state are recorded
  independently from the external coordination report;
- Current State and Task Index are denied and reserved for a separate
  authorized state-sync unit.

Post-correction unresolved Critical / High / Medium: `0 / 0 / 0`.

## Critic pass 2 — provenance, effects and closure

Initial findings:

1. **HIGH — a Lock could permit an incomplete or unverified conversation
   transcription to become canonical.**
2. **HIGH — design hosting could be allowed to imply OBS/native readiness.**
3. **MEDIUM — H0 could pre-authorize H1 or create a cyclic post-merge claim.**

Corrections:

- future H1 requires exact content/input digest verification, otherwise the
  Lock expires fail-closed;
- all Product/native/environment effects and implementation admission are
  denied;
- H1 and H2 require separate authorization, and H2 must record H1 merge and
  post-merge Evidence append-only without rewriting the contract artifacts.

Post-correction unresolved Critical / High / Medium: `0 / 0 / 0`.

## Pre-host Judge

- Fresh source, Registry and GitHub audit: `PASS`
- Exact two-file H0 scope: `PASS`
- Exact four-file future reservation: `PASS`
- Existing active-Lock path overlap: `0`
- Implementation/effect escalation: `0`
- Unresolved Critical / High / Medium: `0 / 0 / 0`
- Ready for exact Draft PR: `PASS`
- Ready or merge: `NOT_AUTHORIZED_PENDING_HOSTED_CHECKS_AND_DESIGN_JUDGE`
- H1/H2/S0: `NOT_AUTHORIZED`

Failure, drift, overlap, digest ambiguity or a non-success hosted check parks
this unit without rollback, history rewrite or authority expansion.
