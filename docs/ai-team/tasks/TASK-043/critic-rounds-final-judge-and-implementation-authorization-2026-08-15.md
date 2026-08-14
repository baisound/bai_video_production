# TASK-043 — Critic Rounds, Final Judge and Implementation Authorization

- Baseline: `main@6784a44e6831daa2b3db8ff85e2abe7b197ba3de`
- Profile: `DEV-4 FOUNDATION CRITICAL`
- Builder design: `major-refactor-full-detailed-design-2026-08-15.md`

## Critic Round 1 — architecture and authority

1. `HIGH / CLOSED` — A unified Project file could become a duplicate canonical
   database. The design now limits it to child identity/version/hash bindings;
   domain payload and ownership remain in existing stores.
2. `HIGH / CLOSED` — An in-place migration could destroy a human project. The
   design requires read-only planning, staging-copy migration, complete validation,
   manifest-last commit and a retained pre-migration backup. Lossy/destructive
   apply remains a Human Gate.
3. `HIGH / CLOSED` — Undo could rewrite Audit/Prompt Evidence or unlock Assets.
   Undo is now a compensating Product command that invokes normal authority and
   STALE rules; it never deletes history or bypasses confirmation.
4. `HIGH / CLOSED` — Autosave could persist confirmation tokens, credentials,
   media bytes or active external operations. The persistence boundary excludes
   them and only saves quiescent Product-local state.
5. `HIGH / CLOSED` — A durable job store could duplicate TASK-027 Provider Queue.
   Its ownership is restricted to Product background/Export operations and may
   reference, but never replace, Generation Queue or Attempt Evidence.
6. `MEDIUM / CLOSED` — Legacy discovery could silently combine unrelated files.
   Import is read-only, requires recognized filenames and explicit project identity,
   and emits a visible plan instead of writing.

Round 1 unresolved Critical/High: `0 / 0`.

## Critic Round 2 — concurrency, recovery, UX and release

1. `HIGH / CLOSED` — Child stores could change after staging validation but before
   manifest switch. The design now holds a Project coordinator lock and revalidates
   every child binding immediately before the manifest-last atomic replacement.
2. `HIGH / CLOSED` — A crashed Export dispatch might be retried and duplicate an
   external render. `DISPATCHING` timeout becomes `UNKNOWN`; only typed reconcile
   or Human action may advance it. Operation identity is immutable.
3. `HIGH / CLOSED` — Backup restore could overwrite a newer human revision. Restore
   is a new CAS transaction; revision divergence becomes a Human Gate.
4. `HIGH / CLOSED` — UI visibility could be mistaken for capability. Shell controls
   derive enabled state from Application capabilities; static labels do not count
   as implementation or Evidence.
5. `MEDIUM / CLOSED` — A fixed performance threshold invented during design could
   make false native claims. The corpus size is fixed, while exact time/memory
   budgets are set only after reproducible TASK-045 baseline measurement.
6. `MEDIUM / CLOSED` — Releasing a backend-only foundation would create meaningless
   version churn. TASK-043 is explicitly a checkpoint; SemVer is decided after an
   integrated user-facing slice and required native acceptance.

Round 2 unresolved Critical/High: `0 / 0`.

## Final Critic / Judge

### Evidence considered

- clean current-main checkout and exact HEAD/Release/package audit;
- hosted green status of main and PR #61 merge;
- current store version guards, CAS/atomic-write implementations and recovery
  boundaries;
- Shell UI/bridge/BackgroundJobRegistry and desktop checkpoint exclusions;
- task collision audit showing TASK-043..045 unused;
- Owner Directive replacing all earlier Owner instructions.

### Decision

`AUTHORIZED_FOR_IMPLEMENTATION` for TASK-043 only, in the recorded implementation
order and Allowed Files. The design closes the foundational risk without reopening
completed domain Tasks or expanding external authority.

TASK-042 P-V6-4, TASK-044 and TASK-045 are allocated but remain dependency-waiting.
Their implementation must be re-audited against the actual TASK-043 result. Native
H3, paid narration, Production Deploy and destructive migration remain parked.

### Release decision

`NO_RELEASE_AT_DESIGN_OR_FOUNDATION_CHECKPOINT`. Release/Tag authorization exists,
but there is no meaningful new user-facing milestone yet. Exact SemVer remains
`UNDECIDED` until integrated compatibility and acceptance Evidence exists.

Final unresolved Critical/High: `0 / 0`.

