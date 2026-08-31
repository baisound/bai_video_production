# TASK-067 formal scope and uncommitted freeze packet

State: `OWNER_APPROVED_TASK_LOCAL_FORMALIZATION / SOURCE_START_DEPENDENCY_GATED / EFFECT0`

This TASK-065-local packet records the Owner-approved formal scope for
`TASK-067 — Generic Review Operation Facade` and preserves the read-only
identity of an already-existing uncommitted candidate. The formal scope is not
implementation-start authority: it does not accept or approve the preserved
diff, satisfy any start dependency, authorize a source/test commit, push or PR,
or create a completion receipt.

## 1. Authority and freeze

- Canonical audit base: `35cdf1ad475633dcf035e0616e979b5a8fde0c88`.
- Dedicated candidate branch: `codex/task-067-generic-review-operation`.
- The three candidate paths below are uncommitted and unpushed.
- They must not be deleted, moved, overwritten, further edited, tested,
  committed, pushed, opened as a PR or consumed by TASK-036/061/065 before all
  exact implementation-start dependencies in section 7 are current.
- Their earlier local syntax/import, focused `7 PASS`, and TASK-058 regression
  `83 PASS / 5 SKIP` observations predate the authority correction. They are
  historical diagnostics only, not accepted Evidence or completion.

Read-only freeze inventory:

| Path | State | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `src/ai_video_production/montage_learning_canonical_admission_transaction.py` | tracked modified, `+59/-0` | 177508 | `3f7a1d55e8b74954a21aac738cfda9fa36aecca02c0705e30e397e72ca2c163f` |
| `src/ai_video_production/montage_learning_generic_operation.py` | untracked | 40797 | `b225142bc12bac651a3c36ff62adebf4c388070b5efbfd9426ffe0766fded26f` |
| `tests/test_task067_generic_review_operation.py` | untracked | 7532 | `c956236749d597558e88ba7661495e61c3da19d7919d233f1d4cd750f4d515a4` |

Fresh read-only overlap check at the TASK-065 checkpoint reproduced exactly
this three-path dirty set and every byte count/hash above. The candidate branch
is still based on `origin/main`, with related PR count zero. The result confirms
preservation only: canonical TASK-067 allocation, the bounded cross-owner
amendment, dependency receipts and fresh owner/work-lock PASS are still absent,
so additional source mutation, commit, push and PR remain zero.

Any later byte change requires a fresh freeze identity after authority is
established. The current files are not a source of truth.

## 2. Candidate objective and responsibility

TASK-067 would add a Generic review-observation-only sealed operation facade
and immutable no-write/no-create current-coordinate readback. It must preserve
the completed TASK-058 writer/import semantics and expose no exact-evidence
operation, external-anchor authority, private loader/parser or caller-selectable
path/revision/store/scope coordinate.

The receipt remains Project-owned. It does not contain install instance,
descriptor, Bridge root or transport authority. TASK-036/065 would separately
compose it with TASK-063 discovery and the TASK-061-A PREACTIVATION PREPARE
operation plan.

The dependency is deliberately one-way: TASK-067 consumes TASK-061-A only and
does not wait for TASK-061-B final CA-C. TASK-036 later composes TASK-061-A,
TASK-063, SKILL-D2S-001 and the completed TASK-067 facade to execute real
installed E2E; TASK-061-B alone consumes that E2E receipt. Any requirement that
TASK-067 wait for whole-task TASK-061 completion is SUPERSEDED because it would
create a TASK-067/TASK-036/TASK-061 cycle.

## 3. Formal Allowed Files and prohibited surface

The Owner-approved minimal implementation scope, still subject to every start
dependency and fresh collision/ownership check, is:

```text
src/ai_video_production/montage_learning_generic_operation.py
tests/test_task067_generic_review_operation.py
docs/ai-team/tasks/TASK-067/task.md
```

The released TASK-058 path below is conditionally allowed only through the
separate canonical owner-preserving amendment in section 3.1:

```text
src/ai_video_production/montage_learning_canonical_admission_transaction.py
```

That amendment is limited to a private Generic-only factory,
`admit_generic_observation`, `recover_generic_observation`,
`get_verified_generic_observation`, and the directly required Generic
manifest/journal same-snapshot helpers. It grants no broader file or symbol
ownership.

Shared metadata candidates are excluded until a sole-Builder/LOCK checkpoint:

```text
docs/ai-team/task-index.md
docs/ai-team/current-state.md
docs/roadmap/PROJECT-ROADMAP-CANONICAL.md
CHANGELOG.md
```

Exact lane, public receipt, Profile, Timeline, Release, File Bridge,
activation, installation, TASK-036, SKILL, generic `atomic` helpers, shared
docs and public config/hash/seal authority-minting semantics are prohibited.
Caller-selectable mode, Project/root/revision/store coordinates are also
prohibited. TASK-058 historical Evidence, TASK-061, TASK-065 implementation
source, Bridge runtime state and native installation remain must-not-modify.

### 3.1 Required TASK-058 cross-owner amendment

`montage_learning_canonical_admission_transaction.py` remains released
TASK-058 canonical-admission ownership. A closed historical work lock does not
transfer that ownership to TASK-067. Before this path can enter TASK-067
Allowed Files, canonical metadata must grant a bounded cross-owner amendment
that:

- keeps TASK-058 ownership while permitting only the exact Generic-only
  extension symbols required by TASK-067;
- lists the affected symbols and path explicitly;
- changes no Exact lane, public receipt, Profile, learning-adoption, Timeline or
  Resolve semantics;
- requires TASK-058 owner regression for Generic admission/recovery/get/A2,
  exact/generic serialization and the Bridge application;
- stops on any active/new TASK-058 corrective branch or overlapping work lock;
  and
- treats version, CHANGELOG, Release asset and Production authority as separate
  canonical Gates. A TASK-067 source commit alone grants none of them.

TASK-065 cannot use its own Allowed Files to bypass this amendment. It consumes
only a future canonical TASK-067 completion receipt.

## 4. Required design surface

The facade public call surface is exactly:

1. `admit_generic_observation`;
2. `recover_generic_observation`;
3. `get_verified_generic_observation`.

The modes must satisfy the unmodified Bridge sequence:

- FRESH: admit exact delivery, then get the same bound result;
- RECOVERY: journal recovery or sealed terminal A2 duplicate, then get the same
  bound result;
- VERIFIED_READBACK: noncreating A2 lookup and get only.

Mode resolution matches the unmodified Bridge branches: receipt plus matching
correlation selects VERIFIED_READBACK; receipt without correlation is STOP;
matching correlation without receipt also selects VERIFIED_READBACK; otherwise
exact pending selects RECOVERY; only total receipt/correlation/pending absence
plus an exact fresh plan selects FRESH. Correlation outranks a coexisting
pending record, which Bridge later cleans up. Mismatch, multiple state, tamper
or unknown identity is STOP/effect zero.

Bridge receipt/pending/correlation readers are only state hints, not pinned
authority proof. TASK-067 independently proves Project canonical currentness.
The TASK-036 resolver must not hold the create-capable Bridge publisher lock
around nested `import_path`. A resolver/Bridge race that produces a method-mode
mismatch burns the old facade FAILED_CLOSED; there is no automatic retry or mode
refresh. A subsequent attempt requires a fresh authoritative resolver object
and, when stale, a fresh plan. Inbox-wide `import_once`, exact APIs, raw storage,
watcher behavior and caller coordinates are prohibited.

RECOVERY must distinguish three sealed internal subtypes without changing the
fixed public method: exact present journal uses JOURNAL_RECOVERY; absent journal
plus exact terminal entry uses TERMINAL_A2_DUPLICATE; absent journal and terminal
entry plus exact pending/plan/current-coordinate equality uses
PRECOMMIT_RESUME. PRECOMMIT_RESUME is the only valid restart for a crash after
Bridge pending publication but before canonical admit/journal creation. It
delegates the exact fixed delivery once to admission internally, returns typed
ACCEPTED, then supports the normal immediate bound get. Drift, collision,
ambiguity or unknown authority is STOP; no revision recompute, fallback to a
fresh mode or automatic retry is allowed.

## 5. Mandatory blockers before commit-ready

### P0 — secure first Generic lock establishment

The current candidate checks absence under Product lock, releases it and later
allows the global create-capable update-lock helper to create/write the lock.
That leaves a race and does not meet the TASK-067 path-identity floor.

The accepted design must close absence check through no-follow exclusive
creation, regular one-byte content/readback, exact file identity and pinned
ancestor identities while still under the secure establishment protocol. Only
after establishment may the normal Generic-lock then Product-lock order apply.
Broken link, reparse, hardlink, ancestor drift, appeared-between-check and
case-collision must fail closed.

### P0 — terminal A2 same-snapshot currentness

Terminal DUPLICATE must prove, in one Generic-existing-lock then Product-lock
critical section: Generic journal absent, Product recovery none, exact
manifest/binding/ledger/head/target marker, and exact payload-object/marker
inventories. The sealed capability body and cached typed result bind that same
snapshot. A Product journal appearing between phases, orphan/unknown authority,
access failure or ancestor substitution must fail closed.

### P0 — Manifest/journal bytes and physical identity same-snapshot binding

The candidate reads the Product Manifest through
`ProductProjectManifestStore.load` and later probes the Manifest path
separately. A cooperating Project lock does not prove that parsed bytes and the
reported physical identity came from the same file instance when a
non-cooperating replacement, hardlink or reparse race occurs. This affects
FRESH, current-coordinate, RECOVERY and terminal A2 modes and is an independent
COMMIT STOP.

Future authorized code must, while the existing Product lock is held, pin the
full ancestor snapshot, lstat the Manifest, open no-follow, fstat, bounded-read
the bytes, post-fstat/post-lstat, require a regular non-reparse file with
`st_nlink == 1` and a non-inheritable descriptor, and parse those exact bytes.
The parsed Project ID/hash/revision, opened-file identity and
`authority_identity_sha256` belong to one sealed read result; a later path probe
cannot substitute for this proof. Operation exit and immediate verification
recheck Manifest path, ancestor and lock identities.

The Product save journal needs the same bytes-plus-identity binding. Absence is
proved only by ENOENT under pinned ancestors; a separate probe followed by an
unbound journal-store load is insufficient. Tests must not monkeypatch only
`ProductProjectManifestStore.load` or the journal loader and infer PASS.
Required negatives cover initial-stat-to-open swap, same-ID/same-canonical-
bytes inode replacement, hardlink alias, Manifest or ancestor reparse,
post-read path replacement, equivalent Project-journal races, and Manifest
replacement while the Product lock remains valid. Every case is effect zero,
burns the facade FAILED_CLOSED and preserves unrelated Project/Bridge
inventory. Whether the exact helper/symbol changes fit the future TASK-058
cross-owner amendment is a fresh Critic/Judge decision; otherwise the
dependency remains N.C.

### P1 — seal and capability forgery resistance

`Task036LaunchConfiguration` is a public dataclass and coordinate candidate,
not an authorization receipt or seal. Its exact type, direct/`from_dict`/copy
construction, matching caller hashes, subclass, mapping, duck type, serialized
projection, alternate Project root or Project-ID-only match must not construct
a factory or capability. Only the future TASK-036 packaged Product-operation
composition may pass a private in-process bound-Project capability after it has
freshly bound the TASK-061 plan and record identity, TASK-063 installed-instance
discovery, pinned launch-config bytes, selected Project Manifest physical
identity/currentness and operation authority. TASK-067's public `__all__` and
factory surface must not expose caller-selected Project, mode or authority.
A module-visible token or bound-project value, forged/rehashed JSON or old
sealed object must not construct or refresh authority. Tests must not use the
production token as their fixture shortcut.

### P0 — claimed-delivery restart late binding

The current prevalidated-delivery factory requires TASK-036 to read the raw
inbox mapping before mode/facade creation. That cannot restart after unmodified
Bridge has renamed the original inbox file into processing and retained the
exact import journal. TASK-036 therefore derives the fixed original inbox Path
only from plan-bound record ID plus source digest and calls one `import_path`;
it does not scan, parse private journals, search processing, claim again or
prevalidate raw JSON. Original-file absence is not by itself a rejection when
the exact restart journal owns the processing claim.

The private TASK-067 resolver arms expected operation/record/digest identity
without raw delivery. After Bridge claim/snapshot/lane validation, admit or
recover validates the actual mapping exactly once at method entry and late-
binds the sealed payload. Any record/digest/canonical-delivery-hash mismatch
burns the object FAILED_CLOSED before canonical effect. PRECOMMIT_RESUME uses
the actual recover-entry snapshot for its single internal admission;
VERIFIED_READBACK binds Bridge-provided record/digest/commit to plan and
correlation without raw-body authority. Public `validate_delivery`, factory and
mode-selection surfaces are prohibited.

Tests cover restart after claim rename before snapshot/classification and after
classification/pending with the original file absent but the same original
Path; forged/mismatched journal filename, processing identity swap and same-
filename different digest/body; zero TASK-036 calls to scan/import-once/claim/
private parser; zero facade prevalidation plus exactly one actual-Bridge-mapping
entry validation; and unchanged unrelated inbox files.

### P0 — capability burn-after-call and immutable facade state

The current candidate changes mode only after success. Validation, canonical
operation, terminal lookup or get mismatch exceptions can therefore leave the
same object reusable. A fault after canonical commit is especially critical:
the old FRESH object can attempt a second admit.

The future contract burns authority at method admission, before validation or
canonical effects, into one-way `IN_FLIGHT`/`CONSUMING`. Success alone moves to
the exact bound-result state or CLOSED. Any `BaseException`, validation
mismatch, fault hook, canonical/recovery/lookup error or get mismatch moves to
`FAILED_CLOSED`; FAILED_CLOSED, CLOSED and already-IN_FLIGHT objects reject all
methods before effect. A fresh operation requires a new authoritative read and
mode resolution; an old object cannot be refreshed, rearmed or revived.

Facade state, result, expected commit and bound coordinates, plus factory and
capability state, must resist ordinary assignment, mangled-slot assignment,
subclass/duck-type substitution, serialization, copy/deepcopy and pickle where
applicable. Concurrent double-call admits at most the first caller; the second
is rejected before a canonical effect.

### Exact S0-S5 fault matrix

- `S0a`: exact Bridge pending publish/readback completes and the process stops
  before canonical call. Restart uses PRECOMMIT_RESUME.
- `S0b`: restart resolves RECOVERY and stops before facade recovery entry.
- `S0c`: PRECOMMIT_RESUME stops immediately before or after secure initial
  Generic-lock establishment.
- `S0d`: an unrelated canonical revision advances after pending publication.
- `S0e`: the same record identity has a terminal different-digest collision.

- `S1a`: existing canonical
  `failure_hook("after_generic_project_commit", generic_observation_path)`;
  journal remains and restart is journal-bound recovery.
- `S1b`: existing canonical
  `failure_hook("before_generic_journal_cleanup", generic_journal_path)`;
  verified terminal result plus present journal still selects journal recovery.
- `S2`: journal unlink succeeds before canonical return. No exact hook exists;
  after future authority, review a production-default-effect-zero test hook
  immediately after `generic_journal_path.unlink()` in `_generic_finish_v1`.
  Restart is sealed A2 typed DUPLICATE. No source hook is added now.
- `S3`: facade admit/recover returns before Bridge trusted-result/get. TASK-067
  does not change Bridge source; use a delegating test canonical-port wrapper
  that raises after capturing the typed result, or an exact TASK-036 fixture.
- `S4`: facade get returns before hidden correlation publish, using a stateful
  test port wrapper that raises after delegated get. Restart is sealed A2 typed
  DUPLICATE.
- `S5`: existing Bridge
  `failure_hook("after_canonical_commit_before_receipt")` after correlation and
  before public receipt. Restart is VERIFIED_READBACK-only. Also cover public
  receipt publication before matching pending cleanup.

S0a/S0b nominal restart makes exactly one canonical commit, returns typed and
Bridge ACCEPTED, publishes exact correlation/public receipt and removes the
matching pending record. S0c resumes through secure lock/safe-empty
classification without double revision. S0d/S0e are effect zero, preserve the
pending record and unrelated Project/Bridge state, and require manual/fresh-plan
resolution. S0 is not covered by S1a-S5.

S1a/S1b permit one terminal journal recovery and only its expected Project
delta. S2-S4 require byte/inventory/revision-unchanged Project state plus Bridge
`ImportResult.status:DUPLICATE`, exact correlation/public-receipt add, matching
pending removal and unrelated Bridge delta zero. S5 requires unchanged Project,
public-receipt add, matching pending removal and duplicate-correlation zero.
Every injection burns the old facade FAILED_CLOSED; restart resolves a fresh
sealed capability with correlation-before-pending-before-fresh precedence.
Evidence names the exact hook/call boundary. S5 alone never counts as S2-S4,
and S1a-S5 never count as S0 coverage.

### Coverage floor

The future focused set must cover the exact S0a-S0e and S1a-S5 matrix above,
real mode
precedence, FRESH/RECOVERY/immediate-get state machines, terminal DUPLICATE,
Project-versus-Bridge root deltas, Windows reparse/hardlink,
stale/race/ancestor cases, mode misuse and unmodified Bridge integration. Each
before-call, canonical, recovery, lookup and get failure must be followed by
calls to every facade method proving same-object effect zero. It must also cover
commit-then-throw retry, concurrent double-call, immutable slot/state attacks,
copy/deepcopy/pickle/serialization attempts and an old capability after external
ledger advance.

The normalized mandatory row set and per-case Evidence columns are frozen in
`task067-task065-negative-matrix-v1-2026-08-31.md` (`G67-A01` through
`G67-X01`). That matrix is part of this implementation-start Gate; prose-only
coverage or a result assertion without explicit Project, Bridge, Profile,
config/history and public-leakage deltas is insufficient.

## 6. Critic, Tester and Judge candidate plan

- Security Critic: lock establishment, lstat/no-follow identities, DACL/reparse/
  hardlink, TOCTOU and authority forgery.
- Recovery Critic: Product/Generic journal combinations, A2 terminal recovery,
  five crash seams and no fresh fallback.
- API/ownership Critic: exact three-method port, exact APIs inaccessible,
  Project-only receipt and TASK-036/061/065 ownership separation.
- Independent Tester: positive and negative unit/boundary/integration tests on
  Windows and Linux, with before/after inventory and revision assertions.
- Judge: accepts only after Critical/High findings are zero or formally gated,
  scope/diff is exact, focused plus relevant regression passes, and no runtime,
  native, Release, Deploy or Production claim is inferred.

## 7. Exact implementation-start Gate

Source/test mutation may resume only after all are fresh and exact:

1. canonical TASK-067 metadata materializes this formal scope and accepted
   design identity without widening it;
2. TASK-068 and TASK-069 prerequisite completion receipts are canonical and
   current;
3. the required TASK-060 and TASK-063 completion receipts plus the TASK-061-A
   PREACTIVATION PREPARE receipt are canonical, current and bound to the same
   `enabled:false` planned operation; TASK-061-B is expressly not a start
   dependency;
4. explicit implementation-start authority names the executor and exact
   Allowed Files after the dependency receipts above are admitted;
5. explicit TASK-058-owner-preserving cross-owner amendment for the existing
   canonical admission source, including exact symbols and regression floor;
6. fresh canonical main and task/design read-back;
7. dedicated branch/worktree, clean authority baseline, dirty ownership,
   open-PR overlap, work-lock and shared sole-writer PASS;
8. the P0/P1 findings above are carried into acceptance and test plan; and
9. Human, version/CHANGELOG, native, config, Release, Deploy and Production
   Gates remain separate.

Until then TASK-067 is `SOURCE_START0 / EFFECT0`: the preserved candidate has
source mutation, test execution, commit, push and PR count zero. TASK-061/036/
065 production and adapter effects remain zero, while TASK-065 integration
design and dependency audit continue.
