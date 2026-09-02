# TASK-064 — Reproducible Windows Evidence and Metadata Builder

Status: `PHASE_B_DEPENDENCY_NC / PRESERVED_R0A_NO_GO / SOURCE_START0 / EFFECT0`

Profile: `DEV-4 FOUNDATION CRITICAL`

Owner: TASK-064 Metadata Builder

## Historical boundary

TASK-064's earlier local checkout and preserved R0A exact-two-file candidate
are Evidence only. They have no canonical implementation, commit, PR, merge,
metadata, launcher, verifier, receipt, or Production authority. No preserved
hunk is grandfathered by this amendment.

## Phase-B authority amendment

TASK-064 is the implementation owner for TASK-080 R0A through R0C only after:

1. the TASK-080 R1 design is frozen and independently accepted at
   Critical/High `0/0`;
2. the TASK-080 docs-only PR is merged at its exact head;
3. canonical `main` and the four design blobs are read back;
4. a fresh implementation Atomic Unit records exact Allowed Files, base OID,
   worktree, tests, and external-policy dependency state.

Until all four conditions pass, TASK-064 keeps the current candidate preserved
and performs no source, workflow, test, commit, push, or PR mutation.

## Authorized implementation sequence after the gate

### R0A — base-owned launcher bootstrap

- implement a launcher/verifier identity that becomes trusted only after
  canonical main readback;
- bind exact workflow/verifier/contract blob OIDs and organization-ruleset
  required-workflow readback;
- keep transition `issue=false` and `consume=false`;
- never execute head-controlled code;
- produce no TASK-079 transition receipt.

R0A implementation may merge and be read back before external ruleset
admission, but R0B cannot begin until TASK-080 R1A has independently admitted
the exact base-owned workflow and produced a fresh signed Policy Auditor
receipt for the current ruleset/workflow binding. TASK-064 neither implements
nor operates that external auditor.

### R0B — disabled verifier

- install the transition verifier in disabled/report-only mode;
- execute focused and negative verification without changing accepted hashes;
- keep transition `issue=false` and `consume=false`;
- prove shallow/missing/forged/transformed objects fail closed with no fetch.

### R0C — first canary

- execute one body-free canary through the exact required base-owned check;
- bind current base, expected canary head, run, launcher/verifier blobs, and
  policy readback;
- produce canary Evidence only;
- keep real TASK-079 issue and consume disabled.

Each unit requires a separate frozen diff, focused and negative tests,
independent Critic/Tester/Judge, Critical/High `0/0`, expected-head merge, and
post-main readback before the next unit.

## Responsibility exclusions

TASK-064 does not own or modify:

- external GitHub organization ruleset, branch protection, required workflow,
  account, secret,
  token, app, or environment;
- TASK-079 source-gate semantics or its accepted-source transition;
- TASK-051 historical records;
- GF-D source or PR `#469`;
- CHANGELOG or version policy;
- Main Merge decisions;
- Montage production;
- Release, Tag, Deploy, Production Activation, Provider, model, native, or real
  user-data effects.

## Required acceptance

- exact current base/worktree/dirty/overlap/ownership PASS before mutation;
- exact Allowed Files with shared/external paths excluded;
- no self-bootstrap and no PR-controlled authority;
- hermetic Git/object handling and raw Git blob semantics;
- TASK-080 receipt/state/merge-fence contract implemented without semantic
  weakening;
- all applicable TASK-080 acceptance/negative matrix cases PASS;
- required repository-policy readback is PASS or the affected unit remains
  dependency N.C.;
- independent Critical/High `0/0`;
- no commit, push, PR, or merge before its unit-specific gate.

Completion of R0C permits only the separately authorized TASK-080 R1B durable
Transition Broker implementation/admission review. TASK-079 remains N.C. until
the admitted R1B Broker has an independently accepted signed Broker Readiness
receipt and each later transition carries a fresh signed TASK-080 R1A Policy
Auditor receipt. R0C does not authorize TASK-079 source mutation, a real
transition, GF-D successor, Release, Deploy, or Production effect.
