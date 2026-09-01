# TASK-078 — DEV-4 Critic / Judge Evidence

Date: `2026-09-02`

Kickoff design base:
`origin/main@74b85d7d3f5965cd515ff44bd5f4b7179185e578`.

Final integration base:
`origin/main@354ea2534ad5739a099d9eeaf0f1da9a7210ddb6`.

Scope: TASK-078 master contract plus E-C1, E-C2, E-C4, E-C3 and E-C5.

## Independence and TASK-077 boundary

- Completeness/Ownership Critic: independent agent `ec_completeness_critic`.
- Security/Integrity/Restart Critic: independent agent
  `ec_security_critic`.
- Both were explicitly prohibited from reading TASK-077 private diffs or
  worktrees. The Completeness Critic confirmed it read only canonical public
  TASK-077 material.
- Judge: `ACCEPT — TASK078_DESIGN_FROZEN` after the synchronized Critic evidence
  recorded below.

## Completeness/Ownership Critic

Initial and residual review waves identified ownership, ABI, restart,
deterministic-action and Allowed-Files defects. The design was corrected to:

- keep runtime Proposal epoch and Scene finalization solely under TASK-027;
- treat TASK-077 completion only as a public development/ABI Gate;
- prove Scene membership from the TASK-027 canonical ledger/set root;
- define exact adoption, playback, Human review and LOCK receipt chains;
- define reachable owner source applications/readers and TASK-003-only Rights;
- define Final Approval v2, dispatch linearization and exact artifact read-back;
- provide total F0-F10 substate-to-action rules; and
- replace implementation placeholders with exact repository-relative paths.

Final synchronized decision: `PASS`.

Residual findings: Critical `0`, High `0`, Medium `0`, Low `0`.

## Security/Integrity/Restart Critic

Initial decision: `FAIL`, with Critical `1`, High `11`, Medium `3`, Low `1`.
Successive remediation closed Scene membership/epoch timing, adoption TOCTOU,
trusted playback/Human authority, legacy IMAGE compatibility, ProjectSave
visibility, Rights ownership, F0-F10 precedence, exactly-once enqueue,
dispatch/revocation linearization, QA-pending recovery and artifact read-back.

The final upstream-writer race was closed by a Project-local interprocess
admission Gate, exact owner lock/head/mutator participation, a crash-safe
invalidation journal including `ABORTED_NO_UPSTREAM_WRITE`, and barrier race
fixtures. TASK-077 was removed from packaged runtime F3 sources.

Final synchronized decision: `PASS`.

Residual findings: Critical `0`, High `0`, Medium `0`, Low `0`.

## Judge

Decision: `ACCEPT — TASK078_DESIGN_FROZEN`.

Residual findings: Critical `0`, High `0`, Medium `0`, Low `0`.

The final recheck independently confirmed that E-C1 treats TASK-077 only as a
public development-completion/ABI gate; no packaged runtime reads its private
diff or receipt. E-C2 requires same-file terminal media evidence and exact
Asset/Audit/LOCK lineage. E-C3 preserves generated-video-only Timeline and
ProjectSave recovery boundaries. E-C4 keeps every Final Gate decision with its
canonical owner and linearizes dispatch with revocation. E-C5 derives F0-F10
from canonical owner records, preserves v1.0 Job history, and prevents renderer
replay after a result or QA-pending recovery state.

The Judge's final remediation recheck also confirmed these exact closures:

- the E-C5 read-back payload is checksum-closed inside the same durable v1.2
  `SUCCEEDED` Job CAS, so restart requires neither renderer replay nor media
  re-probe and creates no Job-hash cycle;
- the E-C2 Allowed Files include the canonical Candidate Audit store and
  Production Control application seams rather than a sidecar owner; and
- the E-C3 Allowed Files include both the public and packaged
  `project-command-history` schema mirrors.

This acceptance freezes the design only. It does not authorize TASK-079..083
implementation or any Product/runtime effect.

## Effect record

This design/review activity performed no Provider or paid call, media probe,
Asset/Audit/Timeline/Resolve mutation, Human Final Approval, Export Queue
mutation/dispatch, publication, Release, Deploy or Production Activation.
