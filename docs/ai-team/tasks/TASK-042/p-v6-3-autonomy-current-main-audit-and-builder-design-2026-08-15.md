# TASK-042 — P-V6-3 AUTONOMY Current-main Audit and Builder Design

## 1. Authority and Source of Truth

- Product Authority: `BAI VIDEO PRODUCTION`
- Owner priority: `OWNER_MAXIMUM / CURRENT_HIGHEST`
- Fresh checkout: clean main `92ff6938b9def12161d8635048ad3714315ed9d4`
- Branch: `codex/task-042-p-v6-3-design`
- Open BVP PRs at Bootstrap: `0`
- BAI Development OS checkout: clean main
  `3dd77892187aec65dffa0ef9723d5bc7537c06dc`
- Handoff status: `HANDOFF_STALE`; current clean checkout is Source of Truth
- Handoff manifest checksum:
  `sha256:32f8848632f31228da7d90e1b7f2bb1185b18028ab5cf1036a533beda98454b4`
- Bootstrap checksum:
  `sha256:55b301345c5697d9812edd7aa9d4980dc0004f8c26cdfa8793208e175ebf41d8`
- Autonomous Queue result: `RUNNABLE_TASK_SELECTED`
- Selected: `BVP-TASK-042-P-V6-3-DESIGN / DESIGN_ONLY`
- Queue checksum:
  `sha256:9791617d02cf79ba4f0b9d4c61113edd68ce129988fd477cb39e3311b83c006a`
- Waiting: `BVP-TASK-042-P-V6-3-IMPLEMENTATION / DEPENDENCY_WAIT`
- Parked: Native H3 Human Gate and unauthorized OS TASK-017
- System blocked: `false`

The prior two-merge cadence completed through PR #56 and PR #57. PR #57 exact
head `34bedb48591e713475b438f4b5074d581cd73fd2` passed `9 / 9`, merged at exact
main `92ff6938b9def12161d8635048ad3714315ed9d4`, and completed remote branch and
dedicated clone cleanup before this fresh checkout was created.

## 2. Current OS audit

The BAI Development OS autonomy contracts were executed rather than described:

1. Handoff Bootstrap selected the newer checkout and prevented stale handoff
   text from overriding current main.
2. Autonomous Queue selected only P-V6-3 Design and kept implementation in
   dependency wait.
3. Native H3 remained task-locally parked with no replay authority.
4. OS TASK-017 remained unauthorized and was not conflated with Product
   TASK-042.
5. The prior context used the minimum six canonical/current-task sources;
   provider usage fields remain unavailable and are not inferred.

No OS runtime dependency is added to the Product.

## 3. Registry and implementation audit

| Required truth/capability | Current owner | Current implementation | P-V6-3 decision |
|---|---|---|---|
| Prompt version and Attempt lineage | TASK-040 | `PromptGenerationRegistry`, crash-safe `Task040PromptEvidenceApplication` | extend existing Prompt metadata; no second Prompt/Attempt registry |
| Prompt body privacy | TASK-040 | `body_ref` + `body_sha256`; general Evidence omits body | preserve; compilation exposes references/hashes only in durable/public serialization |
| JA / normalized JA / runtime EN | none | one body ref/hash only | additive typed compilation binding and deterministic compiler |
| audio toggles/intents in Prompt identity | none | absent | bind narration/music/SE/ambience hashes and generate flags into compilation checksum |
| Provider/Model truth | TASK-028/032/033 | `AiConnectionProfile`, `ModelRoute`, capability catalog | read-only projection only; no second catalog |
| credential truth | TASK-034 | credential reference/availability and vault | expose booleans only; never reveal reference or secret |
| generation plan | TASK-013 | Approved-Plan-bound planner, no Provider call | keep unchanged; Quick uses a distinct authority contract |
| Generation Queue | TASK-027 | Approved Plan/Prompt/Safety/Continuity durable admission | approved route unchanged; Quick never forges its plan proof |
| Candidate/LOCK/STALE | TASK-037 | canonical Production Control registry | Quick outputs must use an exact target Slot and normal Candidate lifecycle |
| Human Audit | TASK-038 | ACCEPT/REJECT/NEEDS_REGENERATION | required before Quick output can be production-locked |
| Quick authority | none | absent | new versioned intent registry, not a Prompt/Candidate registry |
| Quick Provider execution | TASK-013/native adapters | separately gated and currently parked | no dispatch in P-V6-3 source integration |

### 3.1 Current defects/gaps confirmed on exact main

1. `HIGH`: Blueprint v2 Queue input proof derives
   `WORLD_LOCKED_CURRENT_CANDIDATE`, while durable Queue validation accepts only
   the two legacy proof kinds. Existing tests exercise the helper but not
   `prepare_enqueue -> apply_enqueue -> reload` for v2. A real v2 enqueue would
   fail its own persistence validation.
2. `HIGH`: `PromptEntity` cannot bind the three required language layers,
   proofreading/manual-override state, audio flags/intents or the exact WORLD
   LOCK/compiler input identity.
3. `HIGH`: the approved generation route cannot represent Quick authority
   without a false `plan_approved` input. It must remain unchanged.
4. `HIGH`: settings preflight chooses one route per workload; it does not expose
   the full Provider -> compatible Model selection projection with catalog,
   adapter, credential and cost readiness reasons.
5. `MEDIUM`: `TASK-042/task.md` still carries the historical P-V6-1B Design
   status even though P-V6-2 is hosted-closed. This design sync corrects it.

Baseline remains Windows full `960 / 960 PASS` with one intentional platform
skip. Stable Product release is `v0.20.1`.

## 4. DEV Profile re-decision

- Blast radius: Prompt history, Provider/Model selection, generation authority,
  durable intent and Candidate adoption.
- Security/cost risk: private Prompt material, credential state, paid routes and
  local/native side effects.
- Recovery risk: append-only Prompt/Intent versions and cross-snapshot staleness.
- Compatibility risk: existing Prompt snapshots and approved Queue entries.
- Decision: `DEV-4 FOUNDATION CRITICAL`.

Required process is current-main audit, exact Allowed Files, Builder design, two
Critic cycles, focused compatibility/security/recovery tests, full regression,
hosted matrix, exact main verification and cleanup.

## 5. Builder design

### 5.1 P-V6-2 integrity corrective

The durable Queue validator accepts the additive proof kind
`WORLD_LOCKED_CURRENT_CANDIDATE`. It must also validate that this kind has all
four non-null typed identities: `reference_id`, `slot_id`, `candidate_id` and
`asset_id`. Legacy proof kinds retain their current nullability/shape.

An end-to-end v2 test must publish real Planning/Production/Safety/Continuity/
Prompt snapshots, enqueue, persist, restart and reload the Queue. Helper-only
coverage is insufficient.

### 5.2 Visual Prompt Director

Add `visual_prompt_compilation.py` with closed enums and immutable input/output
contracts. `VisualPromptDirectorService` receives structured fields for:

- WORLD, BEFORE, NOW, TRACE, PHYSICS, PLACE and OWNER constraints;
- SUBJECT, SPACE, OFF-SCREEN, CAMERA, LIGHT, FRAME and AFTER intent;
- exact Scene/target Slot and Blueprint v2 WORLD LOCK checksum;
- narration, music direction, SE intent and ambience intent;
- `generate_bgm`, `generate_se`, `generate_ambience`;
- AI proofreading state and manual English override state;
- exact Provider profile/version/hash, route and required capabilities;
- source Japanese, normalized Japanese, runtime English and optional negative
  Prompt private bodies plus their Product-private references.

The standard UX may hide advanced structure, but the service never flattens the
canonical structured input into one mutable source string.

### 5.3 Immutable compilation

`PromptCompilationService` computes all body and intent hashes and returns an
immutable compilation result. Its durable/public manifest contains only:

- `source_ja_ref/hash`;
- `normalized_ja_ref/hash`;
- `runtime_en_ref/hash`;
- optional negative Prompt ref/hash;
- proofreading/manual override state;
- exact structured-director checksum and WORLD LOCK checksum;
- narration/music/SE/ambience intent hashes and generation flags;
- Provider profile/version/hash, selected route and sorted capabilities;
- exact input Asset hashes and compilation version/checksum;
- `prompt_bodies_embedded=false`, `provider_execution_started=false`.

Raw bodies remain only in the in-memory private result/caller-owned private body
facility. They are never included in `to_manifest`, Queue, Context Cost, general
Evidence, exception details or status projection. P-V6-3 does not add a second
body store or claim durable secret-grade storage.

Changing any compiler input changes the compilation checksum and requires the
next Prompt version. Identical input is deterministic.

### 5.4 Extend the one Prompt registry

Extend `PromptEntity` with an optional typed `compilation_binding`. It contains
the compilation manifest reference/checksum plus the three language-layer
references/hashes, negative Prompt identity, director/WORLD LOCK checksum,
audio-intent hashes/flags and exact route capability identity.

- A legacy Prompt without the binding serializes byte/shape compatibly.
- A compiled Prompt requires `body_ref/body_sha256` to equal runtime English
  ref/hash and requires `input_asset_hashes` to equal the compilation manifest.
- Existing append-only version, provider profile and Attempt invariants remain.
- Prompt store loading accepts legacy and compiled records; saving a loaded
  legacy registry does not invent optional fields.
- `Task040PromptEvidenceApplication` publishes the compiled binding through its
  existing prepare/apply/CAS path; no second Prompt transaction exists.

### 5.5 Provider -> compatible Model projection

Add `generation_route_projection.py`. It reads, but never mutates:

- `AiConnectionProfile` / `ModelRoute`;
- `ConnectionAvailability`;
- `ModelCapabilityCatalog` when provided;
- an explicit installed-adapter capability map.

For each configured route in the requested workload, return a deterministic row
with Provider/Model/route IDs, enabled state, declared and catalog capability,
adapter implementation, route availability, credential required/configured,
cost class, local/cloud mode and exact blockers. `READY` requires every relevant
predicate. Catalog presence alone and credential registration alone never imply
runtime readiness.

The projection never emits credential refs, endpoints, route settings or secret
values and never probes a Provider. Provider grouping followed by model order is
deterministic.

### 5.6 Quick Generation authority

Add `quick_generation.py`, `quick_generation_store.py` and
`quick_generation_application.py`.

`QuickGenerationIntent` is an append-only, versioned authority record. It binds:

- intent/project/mode identity;
- exact existing or explicitly created target Scene Slot;
- compiled Prompt ID/version/body hash and compilation checksum;
- exact Provider profile/version/hash, selected route/capability;
- typed reference inputs with source kind `FILE`, `ASSET_LIBRARY` or
  `GENERATION_RESULT`, Asset ID/checksum and optional current Slot/Candidate;
- rights authorization reference;
- currency and non-negative cost ceiling;
- one-shot Human execution-decision identity/hash;
- expected Prompt/Production/Quick snapshot checksums.

Modes are closed:

- `IMAGE`: zero or more general/Character/Space/Composition references;
- `START_END`: multiple references with typed Character/Space/Composition lock
  roles and no duplicate frame-path identity;
- `VIDEO`: exactly one START and zero or one END reference, plus optional
  negative Prompt already bound by compilation;
- `AUDIO`: optional reference only when the selected route declares the exact
  audio-reference capability.

Every mode requires a real target Slot in the canonical TASK-037 registry. This
allows an already-produced output to enter the normal Candidate lifecycle
without a parallel staging Candidate database. The target Slot may be a
non-required expert-work Slot but remains project/Scene scoped.

The target Slot must be mutable, `CURRENT`, not already locked and match the
intent project/Scene/kind. Every Character/Space/Composition reference declared
as a Lock must resolve by exact Slot/Candidate/Asset/checksum and role to an
existing `LOCKED/CURRENT` TASK-037 Candidate; a display label, Human GO row or
same hash alone is insufficient. `FILE` input must first be ingested as an
internal Asset, so a host path never becomes Quick authority.

Quick serialization uses `authority_kind=QUICK_INTENT` and does not contain a
`plan_approved=true` field or an Approved Plan ID. The compiled plan explicitly
reports `approved_plan_used=false`, `human_go_used=false`,
`provider_execution_started=false`, `candidate_created=false`.

### 5.7 Persistence, CAS and restart

The Quick store is intent authority only, not a Prompt/Attempt/Candidate store.
It uses strict fields, bounded JSON, checksum, atomic replace, serialized CAS,
append-only `(intent_id, version)` sequencing and no symlink/path escape.

Application `prepare_intent` binds exact Prompt, Production and Quick snapshot
checksums and returns a one-shot confirmation. `apply_intent` revalidates all
three; any drift consumes and rejects the confirmation. Only the Quick snapshot
is written, so there is no partial multi-store mutation. Restart re-derives
`CURRENT`, `STALE_REPREPARE_REQUIRED` or `RECOVERY_REQUIRED` from current
canonical snapshots and never dispatches.

### 5.8 Quick output adoption boundary

`QuickGenerationAdoptionProjection` is read-only over existing TASK-040 Attempt,
TASK-037 Candidate/Slot and TASK-038 decision state. It requires exact
intent/prompt/job/target Slot/Candidate/Asset/checksum identity and reports only:

- `OUTPUT_NOT_REGISTERED`;
- `AUDIT_REQUIRED`;
- `ACCEPT_REQUIRED`;
- `LOCK_REQUIRED`;
- `PRODUCTION_ADOPTED`.

It never creates a Candidate, writes Audit, accepts, locks, favorites, deletes or
executes a Provider. `PRODUCTION_ADOPTED` requires the existing Candidate to be
Human-audited ACCEPT, lifecycle `LOCKED`, target Slot `LOCKED/CURRENT` and exact
identity. Reject remains not Delete.

### 5.9 Cost, native and execution boundaries

- A Quick execution decision is Product authority intent, not a Provider call.
- Cloud-paid routes require an explicit cost ceiling and later exact paid
  execution authorization/budget reservation before dispatch.
- Local/free routes still require later native/local execution authorization.
- P-V6-3 implementation contains no adapter invocation, credential resolution,
  media ingest/write, Candidate creation, native run, Tag, Release or Deploy.
- The preserved Native H3 attempt is never replayed.

## 6. Implementation order

1. Correct durable v2 Queue proof validation and add full enqueue/reload test.
2. Add typed compilation/domain tests and implement Visual Prompt compilation.
3. Extend legacy-compatible Prompt entity/store/application binding.
4. Add secret-free Provider/Model projection and tests.
5. Add Quick intent domain/store and mode/cardinality tests.
6. Add Quick application CAS/restart/stale behavior.
7. Add read-only adoption projection over existing Prompt/Attempt/Candidate/
   Audit/Lock truth.
8. Run focused compatibility/security/recovery tests, full regression, Windows
   and WSL2 compileall, diff check and implementation Critic.
9. Synchronize exact local truth; then PR, hosted matrix, exact main and cleanup.

## 7. Proposed implementation Allowed Files

- `src/ai_video_production/visual_prompt_compilation.py` (new)
- `src/ai_video_production/generation_route_projection.py` (new)
- `src/ai_video_production/quick_generation.py` (new)
- `src/ai_video_production/quick_generation_store.py` (new)
- `src/ai_video_production/quick_generation_application.py` (new)
- `src/ai_video_production/prompt_registry.py`
- `src/ai_video_production/prompt_registry_store.py`
- `src/ai_video_production/prompt_evidence_application.py`
- `src/ai_video_production/generation_queue_application.py`
- `tests/test_task042_visual_prompt_compilation.py` (new)
- `tests/test_task042_generation_route_projection.py` (new)
- `tests/test_task042_quick_generation.py` (new)
- `tests/test_task042_quick_generation_application.py` (new)
- `tests/test_task042_quick_generation_adoption.py` (new)
- `tests/test_task042_blueprint_v2_generation_admission.py`
- existing TASK-027/037/038/040 Prompt/Queue/store tests only for explicit
  backward compatibility and end-to-end persistence coverage
- `docs/ai-team/tasks/TASK-042/**`
- bounded state synchronization: `PROJECT.md`, `CHANGELOG.md`,
  `docs/ai-team/current-state.md`, `docs/ai-team/task-index.md`,
  `docs/roadmap/PROJECT-ROADMAP-CANONICAL.md`

No schema/package/version, Desktop Shell, Provider adapter, Credential vault,
native runtime, media output, Candidate/Audit mutation implementation, Release
or Deploy file is allowed. A newly proven required file outside this list stops
implementation and returns to Builder/Critic.

## 8. Required gates

- v2 Queue actual enqueue/persist/restart/reload PASS;
- legacy Prompt snapshot and Queue entry shape/behavior compatibility;
- every compilation input changes exact immutable identity; same input is stable;
- raw JA/normalized/EN/negative bodies absent from all public/durable Evidence;
- route projection cannot overclaim readiness or disclose credentials/settings;
- Quick mode cardinality and typed references fail closed;
- Quick has no Approved Plan/Human GO forgery and no Provider start;
- Prompt/Production/Quick checksum drift and replay fail closed;
- Quick output cannot reach adopted status before Audit ACCEPT and LOCK/CURRENT;
- corrupted/oversized/symlink/foreign-project persistence fails closed;
- focused tests, full regression, Windows/WSL2 compileall and diff check;
- Critic unresolved Critical/High `0 / 0` and hosted `9 / 9`.

## 9. Design boundary

This document authorizes design review only. P-V6-3 implementation stays
`NOT_STARTED` until the exact design commit passes hosted checks, merges, cleans
up, and a fresh-main BAI Development OS Queue selects the implementation unit.
