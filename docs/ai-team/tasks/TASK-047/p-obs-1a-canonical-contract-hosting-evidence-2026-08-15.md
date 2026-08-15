# TASK-047 / P-OBS-1A Canonical Contract Hosting Evidence — 2026-08-15

## Authority and scope

- Authorization: `BVP-AUTH-20260815-TASK047-POBS1A-CONTRACT-H1`
- Task unit: `TASK-047/P-OBS-1A CANONICAL CONTRACT HOSTING H1`
- Authority: `DOCS_ONLY_MATERIALIZE_VALIDATE_AND_DRAFT_PR`
- Base: fresh main `901324902242724a9f441a26339392b62b07e3a4`
- Active Lock: `BVP-LOCK-TASK047-POBS1A-CONTRACT-HOST`
- Allowed Files: exact `4`
- Ready / Merge / H2 / S0 / Product or native implementation: `NOT_AUTHORIZED`

## Fresh audit

- Registry revision `6`, active H0 Lock exact read-back: `PASS`
- H0 post-merge CI `31887257293`: `SUCCESS`
- H0 post-merge Security `31887257407`: `SUCCESS`
- Open pull requests at H1 start: `0`
- H1 target branch collision: `0`
- Exact target-path overlap: `0`
- Three new target files absent and TASK-047 pointer present: `PASS`
- Dependency blobs rebound to exact H1 base: `PASS`

## Source materialization

R1-R12 and superseded X1 were fetched twice by exact thread/turn/item ref. The
two reads matched for every normalized byte length and SHA-256. Truncation was
`0`. X1 remains `SUPERSEDED_NOT_NORMATIVE`. The provenance JSON records the
exact refs, lengths, digests and dispositions.

Precedence is R9 Rev.2.1 over the corrected R4/R5/R6 layer over the unaffected
R2/R3 baseline, with R1 as the non-weakenable Owner floor and R10 as the Final
Judge. Later R11/R12 only replace unproven atomic package wording with the
journaled transactional publish and separate rollback result.

## Builder validation

- canonical A normalized UTF-8 LF bytes: `20234`
- canonical A SHA-256:
  `5ec78a4aeaafd921b0a5f81b483a176ac99a54cbf0cce02a1db4443cf2f65362`
- provenance JSON parse and canonical SHA fields: `PASS`
- A-U heading count/order and invariant coverage: `PASS`
- obsolete clauses are present only as explicit rejections, never as active
  requirements: `PASS`
- Public provenance private-value denylist scan: `PASS`
- exact four-file diff and `git diff --check`: `PASS`
- final race audit: remote main remains exact
  `901324902242724a9f441a26339392b62b07e3a4`; H0 Lock remains `ACTIVE` with
  exact four Allowed Files and implementation authority `NOT_AUTHORIZED`;
  Draft PR `#101` has five P-VS-3A files and target-path overlap `0`: `PASS`

No future commit, PR, merge, hosted-check or post-merge outcome is claimed by
this pre-merge Evidence.

## Critic pass 1 — source, precedence and ownership

Initial findings:

1. **HIGH** — the initial draft and superseded long Rev.2 send could reintroduce
   auto Assetization, Adapter-owned semantic state or device-raw language.
2. **HIGH** — a hosted governance Lock could be mistaken for a hosted P-VS-3A
   API or an implementation admission.
3. **MEDIUM** — TASK-043, TASK-003 and P-QC absence could be silently filled or
   overblock strict metadata design.

Corrections:

- one consolidated A-U contract applies the recorded precedence and rejects
  obsolete clauses;
- design/reference status and all implementation authority flags remain false;
- missing owners use explicit `CANONICAL_REF_NOT_PROVIDED`, opaque optional refs
  and effect/dispatch false.

Post-correction Critical / High / Medium: `0 / 0 / 0`.

## Critic pass 2 — provenance, privacy and transaction truth

Initial findings:

1. **HIGH** — self-hash or future Git blob fields could create a post-commit
   rewrite cycle.
2. **HIGH** — source/device/Profile/Collection facts could leak through Public
   provenance.
3. **MEDIUM** — unsigned upstream identities or unproven package atomicity could
   be mislabeled PASS.

Corrections:

- A has no self-hash; B records A content SHA and leaves Git blob recording to
  separate H2; C does not claim future merge Evidence;
- B contains only public upstream/repository refs and source-message digests,
  with a strict private-value denylist;
- unsigned states are truthful, and publish/rollback require future journaled
  probes and authoritative read-back.

Post-correction Critical / High / Medium: `0 / 0 / 0`.

## Pre-commit Judge

- Consolidated design authority: `PASS`
- Exact four-file boundary: `PASS`
- Implementation/effect escalation: `0`
- Critical / High / Medium: `0 / 0 / 0`
- Draft PR readiness: `PASS_FOR_ATOMIC_COMMIT_PUSH_AND_DRAFT_PR`
- Ready / merge: `NOT_AUTHORIZED`

Drift, digest mismatch, privacy leakage or any non-success hosted check parks H1
without rollback, history rewrite or authority expansion.
