# TASK-027 P-ORCH-2 Strategy/Parent Binding Implementation and Critic Evidence

Date: `2026-08-15`
Authority: `AUTONOMY_MAJOR_REFACTOR_CONTINUOUS_RELEASE`
Starting Source of Truth: exact main
`1ed59286991ff70452b3f3602bc512b1fcd38ae4`
Working branch: `codex/task-027-strategy-parent-binding-implementation`
DEV Profile: `DEV-4 PRODUCT ORCHESTRATION CRITICAL`
Status: `LOCAL_PASS / HOSTED_IMPLEMENTATION_PENDING`

## 1. Dependency and fresh-main proof

- P-ORCH-2 Design PR #82 exact head
  `7648529c0d009942514d73dc7aec016da496b677` passed hosted `9 / 9`.
- It merged at the exact starting main above, and its remote branch and clean
  dedicated checkout were removed before this fresh clone was created.
- No newer competing TASK-027 Source of Truth or open PR existed at
  implementation selection.
- Package and stable formal Release remain `0.21.0 / v0.21.0`.

## 2. Implemented bounded outcome

### Canonical Prompt regeneration binding

TASK-040 now persists `PromptRegenerationBinding` on the exact new immutable
Prompt version. It contains the exact parent Prompt ID/version/hash, parent
Attempt, selected Strategy, normalized reason codes and confirmed regeneration
Plan checksum. It contains no Prompt body, credential, host path or media.

Registration proves again that the parent Prompt/Attempt/Slot/hash and current
Strategy are exact, Strategy does not move backwards, Profile switching obeys
the existing escalation rule, the new Prompt is the next version and the
Draft's displayed Strategy/reasons equal the binding. Generic Prompt
registration cannot create a later unbound version.

### Strict compatibility

The Prompt Registry writer now emits `snapshot_version=1.1.0`. Its loader reads
only strict v1.0 or v1.1 shapes. Historical later Prompt rows without a binding
remain readable but cannot import a new Attempt, enter a new Queue record or be
adopted. No Strategy or Parent is guessed.

The Generation Queue writer emits `queue_version=1.1.0` and deterministic
v1.1 entries with exact `execution_lineage`. Initial lineage is fixed to
Strategy 0/no parent. Regenerated lineage copies the exact Prompt binding.
Historical v1.0 Queue entries remain readable and are not silently rewritten;
new entries always use v1.1.

### Regenerated output adoption

P-ORCH-1 adoption now validates Queue lineage against the exact Prompt binding,
includes it in deterministic Candidate preparation identity and creates the
PASS Attempt with the exact Strategy and parent Attempt. Binding drift, legacy
ambiguity, invalid format or stale confirmation creates no Asset/Candidate/
Attempt side effect. Restart recovery reuses the same immutable Queue lineage
and performs no Provider replay.

The endpoint is unchanged: `READY_FOR_AUDIT`. Human Audit, ACCEPT/LOCK,
publication, downstream generation, NLE/DAW mutation and release authority are
not granted.

## 3. Verification Evidence

- final focused Prompt/Queue/adoption/migration/recovery regression:
  `59 / 59 PASS`;
- TASK-013 execution, TASK-027 Queue/adoption, Production bundle and TASK-036
  Shell cross-regression before final Critic-only additions: `146 / 146 PASS`;
- final full WSL2 Ubuntu regression: `1147 / 1147 PASS`;
- final full Windows regression: `1146 PASS / 1 expected non-Windows skip`;
- real TASK-037/TASK-040 persisted-store regenerated adoption:
  Strategy `2`, parent `job-parent`, PASS Attempt and `READY_FOR_AUDIT` `PASS`;
- strict Prompt v1.0 read -> v1.1 write projection and strict legacy Queue v1.0
  read without silent entry upgrade: `PASS`;
- `python -m compileall -q src tests`: `PASS`;
- `git diff --check`: `PASS`;
- temporary Windows test dependencies were removed after validation.

No Native H3 generation, paid Provider, Credential, Human-owned Project write,
Resolve/Cubase mutation or Production Deploy was executed.

## 4. Implementation Critic

### Round 1 - authority and provenance

1. `CRITICAL / CLOSED`: regenerated output could still be recorded as Strategy
   0/no parent. Adoption now accepts only the exact Queue lineage and Prompt
   binding; the PASS Attempt uses those exact values.
2. `HIGH / CLOSED`: callers could inject Strategy/Parent during Queue or
   adoption. Neither API accepts loose lineage fields; Queue derives them from
   canonical Prompt metadata and adoption derives them from Queue.
3. `HIGH / CLOSED`: a later Prompt could enter through generic registration.
   The generic Application route is version-1-only; confirmed regeneration owns
   later version creation.
4. `HIGH / CLOSED`: Prompt binding and created Attempt could disagree. Domain
   validation requires exact Strategy and parent equality in addition to the
   existing Prompt/Slot/hash/profile checks.

### Round 2 - migration, tamper and restart

1. `CRITICAL / CLOSED`: old v1 data could be guessed or made unreadable. Strict
   v1 read compatibility is tested; ambiguity stays readable but non-runnable.
2. `HIGH / CLOSED`: a forged Plan could claim a current Strategy different from
   the parent Attempt. Draft compilation now rejects that mismatch and any
   Strategy regression.
3. `HIGH / CLOSED`: Draft display metadata could differ from the saved binding.
   Registration checks exact Strategy and normalized reasons before write.
4. `HIGH / CLOSED`: migration could rewrite historical Queue identity. v1
   entries retain their exact shape/version; only newly appended entries are
   v1.1 and include lineage in their deterministic ID.
5. `HIGH / CLOSED`: crash recovery could attach current rather than original
   lineage. The immutable deterministic Queue entry remains the source for the
   exact recovery suffix; Prompt/Queue drift fails closed.
6. `HIGH / CLOSED`: private material could leak in the new metadata. Tests and
   field allowlists limit it to logical IDs, enums, reason codes and hashes.

Unresolved implementation Critical/High findings: `0 / 0`.

## 5. Boundaries and next gate

This local result does not claim hosted closure, Native H3 completion, full
TASK-027 completion or a new Release. The next gate is an implementation PR,
all hosted checks, exact main merge and branch/checkout cleanup. Only then may a
fresh-main AUTONOMY cycle select the next safe Atomic Unit.
