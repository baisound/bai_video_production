# TASK-098 A2-R2c Recovery R1 Review and Allocation

Date: `2026-09-20`

## 1. Recovery trigger and authority

- Active Project / Task / Atomic Unit: `BAI VIDEO PRODUCTION / TASK-098 / A2-R2c`.
- Development depth remains `DEV-3 HIGH ASSURANCE`.
- Owner authority is the approved A2-R2c implementation request, the explicit
  approval for additional corrections, and the direction to continue
  autonomously. This recovery does not add a Product capability or external
  effect; it only closes the final Judge findings inside the same responsibility.
- The pre-recovery implementation and Evidence are preserved. Final Judge result
  was `REJECT / NOT_COMMIT_READY / 0 Critical / 2 High / 1 Medium / 0 Low` after
  the ordinary two review/fix cycles were exhausted. No commit is allowed until
  this recovery allocation passes its own bounded review and implementation gate.

The rejected findings are:

1. a validated but not control-row-committed terminal commit could be projected
   while control remained `PARTIAL`, incorrectly allowing slot release;
2. R2c relaxed the existing `RuntimeTranscriptionCoordinatesV1` decision-pair
   contract even though the allocation only permitted a read-only coordinator
   reader; and
3. Shell JavaScript announced success after an apply error/null response.

## 2. Recovery boundary

Recovery R1 preserves the accepted R2a/R2b1/R2b2 state machine and the accepted
R2c application boundary. It receives a fresh maximum of two bounded
review/fix cycles. It authorizes only the following corrections.

### 2.1 Commit visibility follows the control-row commit point

The read-only reader may load and validate `terminal-commit.json` while control
is `PARTIAL` so corruption and predecessor mismatch still fail closed. The
private chain identity continues to include the validated record digest.
However, the TASK-036 port must not classify or pass that terminal commit to the
R2a reducer until the exact control row is `COMPLETED` and its result ref is the
typed ref of that same terminal commit. While control is `PARTIAL`, the reducer
receives the validated closure/barrier/generation-absence facts with
`terminal_commit=None`; the projection remains `BLOCKED` and slot release stays
false. No repair, CAS, or Evidence write is performed by capture.

A direct fake-only crash-window test must stop at
`after_terminal_commit_write`, capture the actual durable state, and prove:

- main is `FAILED`, control is `PARTIAL`, and slot is retained `IN_PROGRESS`;
- public projection is blocked with no available action and
  `slot_release_allowed=False`;
- resuming the existing coordinator closure commits control first and only then
  permits exact slot release.

### 2.2 Preserve the existing decision-pair coordinate contract

`RuntimeTranscriptionCoordinatesV1` returns exactly to its committed contract:
`runtime_decision` is required, `validate_runtime_pair` is mandatory, and no
digest-only constructor field/property is added.

R2c may add one distinct frozen private
`RuntimeTranscriptionDurableControlCoordinatesV1` type for detached Human/control
application. It contains only the exact identifiers and bindings already
validated by the accepted read-only reader: request object/digest, admitted
decision digest, admission ref, provider/model/config, main attempt, and slot.
Its constructor validates every ID/digest, derives and verifies the admission
ref, validates the request round trip, and exposes the same derived operation
and control keys. It cannot represent a runtime admission decision or enter the
Provider execution path.

Existing coordinator mutation methods keep accepting only
`RuntimeTranscriptionCoordinatesV1`. R2c may add narrowly named durable-control
entrypoints for cancel request and Human adjudication closure. Those entrypoints
accept only `RuntimeTranscriptionDurableControlCoordinatesV1` and delegate to
shared private coordinator logic after exact validation. Worker acknowledgement,
publication, Provider execution, and every existing write API keep the original
validated decision-pair contract. The TASK-036 private capture stores the new
durable-control type and invokes only those two R2c entrypoints.

Tests must prove the legacy coordinate rejects a missing decision, the new type
rejects mixed admission/request/decision/config coordinates, the legacy write
APIs do not accept the new type, and the R2c entrypoints do not accept the legacy
type by accidental duck typing.

### 2.3 Shell success acknowledgement

`runRuntimeTranscriptionControl` may notify success only when the apply call
returns an exact object whose ordered top-level keys are `task_owner`, `status`,
`transcription_control`, whose owner/status are the exact accepted constants,
and whose nested projection passes a bounded JavaScript validator generated
from the Python canonical `_RUNTIME_CONTROL_KEYS` and
`_RUNTIME_CONTROL_EXACT_ROWS`. The validator requires the exact ordered twelve
keys, `control_mode=PHASE_ONLY_V1`, the five exact booleans,
`no_replay=true`, and membership of the complete closed signature table. It
must not maintain a second hand-written row table.

A null/error, rejected or throwing apply, array, top-level or nested
missing/extra/private key, wrong type, or enum-valid but combination-invalid row
produces no success notification. The apply path uses `try/finally` so Shell
refresh is attempted once after every confirmed apply outcome, independently
of notification eligibility. No private coordinate is exposed to JavaScript.

## 3. Context and files

MUST READ:

- this recovery allocation;
- `a2-r2c-shell-human-pre-mutation-review-20260920.md`;
- the three exact affected source sections and their focused tests;
- the R2 terminal commit ordering in
  `a2-r2-progress-cancel-adjudication-design-20260920.md`.

MAY MODIFY:

- `src/ai_video_production/task098_runtime_transcription_coordination.py`;
- `src/ai_video_production/task036_product_ports.py`;
- `src/ai_video_production/task036_pre_edit_runtime.py` only if a test exposes a
  necessary exact response-contract correction;
- `src/ai_video_production/task036_shell_ui.py`;
- `tests/test_task098_runtime_transcription_coordination.py`;
- `tests/test_task098_task036_runtime_managed_transcription.py`;
- `tests/test_task036_pre_edit_runtime.py` only for the permitted response path;
- `tests/test_task036_shell_ui.py`;
- bounded `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`, and
  `docs/ai-team/tasks/TASK-098/**` Evidence/status updates.

MUST NOT MODIFY or execute:

- store/schema/reducer contracts, launcher/first-run/CLI or packaged/native v2;
- real Provider/model/private audio, recording, Dataset adoption, voice learning
  or training;
- installation, release, deploy, Production Activation, paid/network effects;
- any source or test outside the exact ceiling above.

## 4. Verification and completion gate

Required before commit-ready:

1. focused tests for all three findings, including the real fake-only fault
   window and negative type/binding cases;
2. the existing six-file R2a/R2b1/R2b2/R2c/R1c/TASK-036 regression;
3. Python compile and `git diff --check`;
4. independent DEV-3 Critic and Tester on the recovery diff;
5. final Judge with zero unresolved Critical/High findings;
6. a new unique external Evidence checkpoint under the canonical TASK-098 root,
   read back and hashed; the rejected checkpoint remains immutable;
7. explicit-scope staging and a Japanese commit only after Judge acceptance.

No native, real-provider, private-media, training, release or production action
is part of this recovery.
