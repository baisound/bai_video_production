# TASK-060 PP-A Implementation Authorization Candidate

## Decision and activation boundary

- Task: `TASK-060`
- Capability: `BVP-MONTAGE-PREFERENCE-PROJECTION-001`
- Atomic Unit: `PP-A`
- Development profile: `DEV_4_FOUNDATION_CRITICAL`
- Review/fix budget: maximum `2` cycles, then Owner escalation
- Candidate state: `OWNER_APPROVED_PENDING_CANONICAL_METADATA_HOSTING`
- Implementation state: `NOT_STARTED / NOT_AUTHORIZED_BY_THIS_LOCAL_CANDIDATE`

The Owner approved preparation of this bounded PP-A authorization candidate on
2026-08-28. It becomes implementation authority only after the exact metadata
commit passes independent DEV-4 Critic/Tester/Judge with unresolved
Critical/High `0/0`, Hosted checks, an exact Owner Ready/merge decision,
canonical-main merge/read-back, and post-main CI/Security. Before those gates,
source, schema, test, runtime, native, Release, Deploy, and Production mutation
remain unauthorized.

This record activates no PP-B or PP-C work. It does not amend the immutable
Owner allocation record dated 2026-08-27.

## Bound coordinates

- Accepted design commit: `0ac8971174ab227a6f62b8b797307bbc31b70145`
- Accepted design SHA-256: `sha256:c54623039fc8197c6bf8d02d5363ae53b601e4feef400243fa8be1f4b2280353`
- Canonical BVP base: `ed23c7ff1e8a9525edef76432fa7c49a79b7fef6`
- Registry revision at preflight: `131`
- Active nonclosed integration lock: `BVP-INTEGRATION-LOCK-TASK058-A2-CANONICAL-READBACK-LOOKUP-CHANGELOG-20260828`
- Active lock allowed shared effect: `CHANGELOG.md` only
- PP-A metadata and future implementation overlap with the active lock: `0`
- Metadata branch: `codex/task-060-ppa-implementation-authorization`
- Open-PR exact-path overlap at preflight: `0`

Drift in the accepted design, canonical main, dependency API/schema, this exact
scope, or the task identity requires a new read-only audit before implementation.

## PP-A objective

Implement the typed, versioned projection policy and the pure deterministic
`PreferenceProjectionCandidate` compiler described by accepted design
`BVP_PREFERENCE_SOURCE_DESIGN_FREEZE.md` sections 1 through 6.

The compiler consumes independently verified typed TASK-019/TASK-029 history
snapshots, reconstructs the latest Human-confirmed feature changes, selects one
closed policy row, performs the accepted integer-only strength calculation, and
produces either a body-free closed failure state or an advisory-only v1 envelope
candidate. It performs no filesystem, DPAPI, promotion-store, transport,
Timeline, Resolve, Provider, network, native, or Product runtime mutation.

## Exact PP-A implementation Allowed Files

Only these six paths may change in the later PP-A implementation Unit:

```text
src/ai_video_production/montage_preference_projection.py
schemas/montage-preference-projection-policy.schema.json
src/ai_video_production/schema_resources/montage-preference-projection-policy.schema.json
tests/test_montage_preference_projection.py
docs/ai-team/tasks/TASK-060/task.md
docs/ai-team/tasks/TASK-060/pp-a-implementation-evidence-2026-08-28.md
```

`src/ai_video_production/__init__.py` is intentionally excluded. The new module
must remain directly importable without a package-root export. Any required
Allowed Files expansion is a stop condition and needs a new exact Owner Gate.

## Read-only dependencies

PP-A may read, but must not modify, the current canonical contracts in:

```text
src/ai_video_production/human_edit_learning.py
src/ai_video_production/profile_tuning.py
src/ai_video_production/profile_tuning_owner_decision.py
src/ai_video_production/owner_profile_materialization.py
src/ai_video_production/owner_profile_registry.py
src/ai_video_production/owner_profile_registry_store.py
src/ai_video_production/owner_profile_store.py
tests/test_task019_owner_decision_bridge.py
tests/test_task019_profile_tuning.py
tests/test_task029_human_edit_learning.py
tests/test_task029_owner_decision_store.py
tests/test_task029_owner_profile_materialization.py
tests/test_task029_owner_profile_registry.py
tests/test_task029_owner_profile_registry_store.py
tests/test_task029_owner_profile_store.py
```

TASK-029 remains the owner of Human learning decisions, Owner Profile source
semantics, and their durable stores. TASK-019 remains the owner of evaluation,
proposal, Human decision binding, promotion-decision, and rollback semantics.
PP-A revalidates their typed inputs without writing either owner domain.

TASK-055 `MontagePreferenceProfile`, timing medians, event/music anchors, raw
transcript, and media observations are forbidden inputs. TASK-058 remains the
owner of bridge, intake, receipt, transport, and readiness. PP-A creates no
TASK-058 object and claims no production-source binding.

## Closed compiler contract

- policy and candidate records are immutable, closed, versioned, and self-hashed;
- `scope_mode` is exactly `OWNER_GLOBAL` for v1;
- policy rows are unique by `(feature_key, change_direction)` and use only
  Product-controlled uppercase tokens;
- caller summaries, caller hash claims, custom Mapping hooks, scalar subclasses,
  floats, free text, paths, URIs, names, credentials, transcripts, and media are
  never authority or public payload;
- latest-change reconstruction uses verified contiguous histories and distinct
  current `ADOPTED` Human decisions with no replay;
- rejected, revoked, stale, `DO_NOT_LEARN`, Safety-failed, Rights-failed,
  mixed-Owner, Project-only, incomplete, or conflicting sources fail closed;
- the accepted integer-only half-up formulas and sign rules are implemented
  exactly; no negative zero or binary-float equality participates in identity;
- only `READY_FOR_HUMAN_REVIEW` exposes a proposed envelope;
- all automatic learning, automatic promotion, canonical Timeline, Timeline
  mutation, and Resolve write flags remain false;
- PP-A does not persist, confirm, promote, rollback, transport, load, apply, or
  publish any preference.

## Acceptance and tests

The PP-A exact head must demonstrate:

- schema and package mirror byte identity and closed unknown-version rejection;
- duplicate/missing policy row, wrong sign, bad token, and invalid RETIRE/UPSERT negatives;
- integer golden vectors for zero, half, threshold, cap, insufficient strength,
  and no negative zero;
- multi-revision latest-change reconstruction and exact current-source hashes;
- one distinct adopted Human decision per feature and decision replay rejection;
- rejected, revoked, stale, `DO_NOT_LEARN`, Safety, Rights, mixed Owner,
  Project-only, incomplete history, source-revision drift, and policy drift negatives;
- custom Mapping/scalar hook count `0` and immutable single input snapshots;
- deterministic candidate, stable profile/preference identities, envelope payload,
  and self-hash golden vectors;
- TASK-055 timing import/reference and all prohibited side effects `0`;
- exact six-path diff, schema mirror, compile, diff check, focused tests,
  TASK-019/TASK-029 direct regression, and final full BVP regression PASS.

Required command families:

```text
python -m pytest -q -p no:cacheprovider tests/test_montage_preference_projection.py
python -m pytest -q -p no:cacheprovider tests/test_task019_owner_decision_bridge.py tests/test_task019_profile_tuning.py tests/test_task029_human_edit_learning.py tests/test_task029_owner_decision_store.py tests/test_task029_owner_profile_materialization.py tests/test_task029_owner_profile_registry.py tests/test_task029_owner_profile_registry_store.py tests/test_task029_owner_profile_store.py
python -m compileall -q src tests
python -m pytest -q -p no:cacheprovider
git diff --check
```

The future focused test path does not exist in this metadata Unit and is not
executed or claimed here.

## DEV-4 role separation

- Builder implements only the exact PP-A six-path Unit and supplies immutable
  exact-head, diff, schema, hash, and test evidence.
- Critic independently reviews projection semantics, integer formulas, source
  authority, privacy, failure modes, scope, and side-effect denial.
- Tester independently executes focused, negative, direct dependency, compile,
  and full regression suites without promoting Builder results.
- Judge accepts only one exact head with unresolved Critical/High `0/0` and
  separately identifies local, Hosted, and post-main evidence.

Maximum review/fix cycles are `2`. A third cycle, unresolved Critical/High,
runner inability, or scope expansion returns to the Owner.

## Prohibited effects and stop conditions

Prohibited: PP-B confirmation or promotion-store work; PP-C production-source
work; TASK-055 source/schema changes; TASK-058 bridge, receipt, store, transport,
or readiness changes; `__init__.py`; Registry, task-index, current-state,
CHANGELOG, roadmap, workflow, package, connector config, Product Project, real
Owner data, Timeline, Resolve, Provider, network, paid, native, external,
Release, Deploy, Production, automatic retry, automatic rollback, or automatic
preference application.

Stop on dependency source API/schema drift; inability to reconstruct full
history from typed snapshots; ambiguous Owner scope; float-dependent canonical
output; any new public v1 envelope field; private/raw data; custom hook execution;
dirty or unknown ownership; path, branch, PR, or lock overlap; Allowed Files
expansion; policy/design mismatch; more than two review/fix cycles; or a request
to persist, promote, transport, load, apply, or auto-apply a preference.

## Completion and continuation

PP-A is complete only after exact-scope implementation, all required local and
independent DEV-4 evidence, Hosted checks, exact Owner merge authorization,
canonical-main merge/read-back, and post-main CI/Security. Completion does not
authorize PP-B, PP-C, connector activation, runtime use, or release activity.

The next Unit may begin only through a separate exact Owner authorization after
PP-A is hosted-closed and its dependency/currentness coordinates are re-audited.
