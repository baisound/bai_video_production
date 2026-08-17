# TASK-046 P-VS-4B Beginner Client R4 Evidence

## Outcome

R4 makes the validated 12-step Voice Model Builder preview understandable without
requiring users to interpret machine states such as `ACTION_REQUIRED`. The
canonical `BeginnerClientSnapshot` remains unchanged; R4 only enriches its
body-free public projection and preview rendering.

Implementation authority is limited to display-only metadata. It does not start
Dataset adoption, Job dispatch, training, model loading or inference, audio
access, recording, publication, Release, or Deploy.

## Exact change set

1. `CHANGELOG.md`
2. `docs/ai-team/tasks/TASK-046/p-vs-4b-friendly-readiness-r4-evidence-2026-08-17.md`
3. `src/ai_video_production/voice_model_builder_beginner_client.py`
4. `tests/test_task046_voice_model_builder_beginner_client.py`

No schema changes are required because the canonical snapshot and its digest are
not modified. The existing public schema and mirror remain byte-identical.

## Design

- Every one of the 18 closed workflow states has exact Japanese and English
  current-state and next-action guidance.
- Runtime validation derives the exact current step, client state, per-step
  state, and reason codes from the closed workflow state. Rehashing a forged
  completion cannot inflate the friendly progress display.
- The public projection keeps the machine state for deterministic consumers and
  adds a localized `state_label` for people.
- Progress is an integer count of canonical `COMPLETE` steps over the fixed 12
  steps. It is not a guessed readiness percentage.
- Workflow hashes, canonical references, paths, bodies, credentials, and raw
  reason coordinates remain absent from the public projection.
- `UNKNOWN` and `FAILED_KNOWN` remain `BLOCKED`; text never upgrades them to
  success or recommends automatic replay.
- The Tk and HTML previews display the same localized guidance. No action button
  or runtime effect is added.

## Acceptance inventory

- Japanese and English guidance exists and is non-empty for all 18 states.
- All 12 step labels use localized human-readable states.
- Progress is bounded from 0 through 12 and derives only from current canonical
  step facts.
- HTML contains the current summary and next action, but not the uppercase
  `ACTION_REQUIRED` label, local drive paths, or an operation button.
- Public projection excludes workflow digest and canonical source coordinates.
- Effect flags remain false and the static forbidden-effect surface scan passes.
- Existing JSON import bounds, duplicate-key rejection, digest validation, and
  schema validation remain covered by focused regression.

## Critic pass 1 — Builder

- Finding: UI-only wording could drift from canonical workflow states.
- Correction: one closed mapping covers exactly every accepted workflow state,
  and the parameterized test exercises both locales for each state.
- Finding: a percentage could imply unsupported readiness.
- Correction: expose only exact integer completed/total counts.
- Finding: a caller could recompute a snapshot digest after changing step states.
- Correction: validate every derived state and reason against the closed
  workflow state before producing a public projection.

Result: Critical/High/Medium = 0/0/0.

## Critic pass 2 — Security and compatibility

- Finding: friendly guidance could leak private coordinates or become effect
  authority.
- Correction: guidance is constant text selected by a closed state; public
  projection remains body-free and every operation authority flag stays false.
- Finding: adding fields to the canonical snapshot would break its digest/schema.
- Correction: fields are added only to the derived public projection; canonical
  serialization and schema are unchanged.

Result: Critical/High/Medium = 0/0/0.

## Judge

- Domain correctness: PASS
- Beginner usability: PASS
- Canonical compatibility: PASS
- Privacy/security: PASS
- Effect boundary: PASS_FAIL_CLOSED
- Installer impact: NONE; published `.installer.2` remains the current package
- Unresolved Critical/High/Medium: 0/0/0

## Validation receipt

- Focused Windows: 60 passed.
- Python compileall: PASS.
- WSL full regression on the final R4 content: 1962 passed, 1 Windows-only
  installer test skipped.
- Initial Windows full diagnostic: 1959 passed, 1 skipped; two environment-only
  failures were isolated before the final semantic-hardening test was added.
  The WebView probe received a deliberately overlong managed basetemp, and the
  existing TASK-047 Inno installer acceptance was denied access to HKCU and the
  Start Menu. Neither failure touches an R4 path. The required privileged retry
  was rejected by the execution environment's approval quota and is not treated
  as a final Windows PASS.
- Schema mirror: unchanged from the byte-exact hosted R3 pair.
- Diff check: PASS; exact changed paths are the four files listed above.
- Hosted Windows checks remain the final Windows regression authority for the
  Draft PR.

The exact commit, PR head, hosted checks, and post-merge read-back are appended
at the delivery checkpoint.
