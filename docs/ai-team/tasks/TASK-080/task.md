# TASK-080 — Base-owned Metadata Control Plane

Status: `DESIGN_ACCEPTED_R1_C_H0 / DOCS_PR_PENDING / SOURCE_START0 / EFFECT0`

Profile: `DEV-4 FOUNDATION CRITICAL`

Owner: Design Coordinator

Allocation date: `2026-09-02`

Canonical base at allocation: `cc6bac8307c7ea0bc6b3785328b0e0b85cfc0181`

Canonical base tree at allocation: `f293fd03542c753b1011c8f9c11a046927701935`

## Purpose

TASK-080 defines the base-owned control plane used to decide whether release
metadata and accepted-source transitions are current and eligible. It also
creates the bounded canonical Phase-B authority amendment that allows
TASK-064 to implement R0A through R0C without taking ownership of external
repository policy or TASK-079 source-gate semantics.

The control plane prevents a pull-request-controlled workflow, script,
manifest, environment value, or historical PR head from certifying itself.
Only bytes already read back from canonical `main`, plus separately admitted
external repository policy, may become a trusted launcher or verifier.

## Exact design scope

This design Atomic Unit may modify only:

1. `docs/ai-team/tasks/TASK-080/task.md`
2. `docs/ai-team/tasks/TASK-080/base-owned-metadata-control-plane-design.md`
3. `docs/ai-team/tasks/TASK-080/acceptance-negative-matrix.md`
4. `docs/ai-team/tasks/TASK-064/task.md`, limited to the Phase-B authority
   amendment defined by this Task

No other path is authorized by this design unit.

## Prohibited effects

- workflow, verifier, source-gate, Product source, schema, test, CHANGELOG, or
  version mutation;
- GitHub ruleset, required-check, branch-protection, environment, secret, app,
  token, or account mutation;
- issue, consume, transition, terminal, merge, Release, Tag, Deploy, or
  Production authority;
- use of the preserved TASK-064 R0A exact-two-file NO-GO candidate as accepted
  source;
- use of TASK-079's historical PR `#469` or prospective manifest as current
  base or successor authority;
- direct modification of TASK-079, TASK-051 historical records, GF-D source,
  or GF-D PR `#469`.

## Responsibility boundary

| Responsibility | Owner | TASK-080 relationship |
| --- | --- | --- |
| organization ruleset required-workflow admission | Owner / organization administrator | selects exact source repository, branch and workflow; performs no mutation in this unit |
| canonical control-plane contract and TASK-064 amendment | TASK-080 | owns this design |
| base-owned launcher/verifier implementation R0A-R0C | TASK-064 Metadata Builder | starts only after TASK-080 main readback and C/H0 |
| TASK-051 source transition gate | TASK-079 / Development 2 | starts only after R0A-R0C, a fresh signed R1A policy receipt, and an accepted signed R1B Broker Readiness receipt; then consumes the broker-issued TASK-080 transition receipt |
| GF-D successor source | Development 3 | fresh successor only after TASK-079 and TASK-080 gates |
| independent Critic/Tester/Judge | Development 4 and Development 5 | read-only review; no Builder edits |
| expected-head merge | Main Merge | performs only after all exact gates |
| montage production | Montage | no control-plane or metadata ownership |

## Dependency order

```text
TASK-080 R1 design C/H0
  -> docs-only TASK-080 main readback
  -> Owner-gated R1A key generation/custody and public-key handoff only
  -> TASK-064 R0A bootstrap implementation and post-main workflow/blob readback
  -> external organization-ruleset required-workflow admission
  -> TASK-080 R1A signed Policy Auditor implementation/admission
  -> R0A signed policy readback and terminal receipt
  -> TASK-064 R0B disabled verifier and post-main readback
  -> TASK-064 R0C first canary and terminal control-plane receipt
  -> TASK-080 R1B durable Transition Broker implementation/admission
  -> signed R1B Broker Readiness receipt accepted at C/H0
  -> TASK-079 source-gate implementation
  -> TASK-079 main readback
  -> separately Owner/Main-Merge-gated INITIALIZE_PREDECESSOR epoch-0 receipt
  -> fresh-main GF-D successor
  -> one-shot transition consume and terminal main readback
```

No later arrow may be treated as complete because an earlier design or local
diff exists.

## Current evidence classifications

- TASK-079 frozen design is `ACCEPT_DESIGN_ONLY`, not implementation or
  currentness authority.
- TASK-064's preserved exact-two-file candidate is `NO_GO / EFFECT0`; it may
  be inspected as historical implementation evidence only.
- `.github/workflows/release-metadata-check.yml` currently runs on
  `pull_request` and checks out the pull request context. It is not a
  base-owned transition issuer.
- `tools/ci/check-release-metadata.py` accepts caller-provided base/head
  arguments and evaluates the checked-out repository. It is a metadata check,
  not a sealed current-main or transition receipt issuer.
- the required organization ruleset workflow is `NOT_CONFIRMED`. A required
  status-check name is explicitly insufficient because it does not bind the
  workflow or event. Design does not imply account-mutation authority.
- TASK-080 R1 Policy Auditor, signing-key custody, durable state store, and
  merge-fence Broker are `NOT_IMPLEMENTED / EXTERNAL_GATE_NC`; the distinct
  R1B Broker Readiness and real `PREDECESSOR_INITIALIZED` receipts have not
  been issued.

## Completion criteria for this design unit

1. all four allowed documents are internally consistent;
2. the base-owned bootstrap, post-main readback, monotonic state machine,
   merge fence, receipt identity, and failure behavior are closed;
3. TASK-064 R0A-R0C authority is bounded without importing external policy;
4. TASK-079 historical manifest and TASK-080 dynamic receipt remain separate;
5. acceptance and negative cases map the material threat surface;
6. independent Critic and Judge both return Critical/High `0/0` against frozen
   byte identities;
7. `git diff --check` passes and only the exact four files are changed;
8. commit, push, and Draft PR remain blocked until items 1-7 pass.

Design completion creates no implementation, external account, merge,
Release, Deploy, or Production authority.
