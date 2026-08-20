# BAISOUND Codex Development Workspace Policy

Version: `2.0`
Status: `CURRENT`
Primary use: `BAI VIDEO PRODUCTION development under BAI Development OS governance`

## 1. Purpose

This file is the durable bootstrap policy for Codex work in the BAISOUND development workspace.

The workspace uses **BAI Development OS** as development-time governance and **BAI VIDEO PRODUCTION** as an independent Consumer Product. The goal is high-quality autonomous development without applying foundation-grade ceremony, context, or model cost to every small change.

This policy governs:

- project and task scope,
- authority and Human Gates,
- Adaptive Governance (`DEV-0` through `DEV-4`),
- context economy,
- model-capability routing,
- Atomic Unit execution,
- Git/worktree safety,
- verification and evidence,
- session rotation and handoff.

It does **not** grant authority to perform paid, native, destructive, release, deployment, or production side effects.

---

## 2. Codex Project Topology

For the Codex multi-folder project used to develop BAI VIDEO PRODUCTION:

- **Primary folder:** BAI VIDEO PRODUCTION repository root.
- **Secondary governance source:** BAI Development OS repository root.

BAI Development OS is readable as a governance/reference source but is a separate product and repository.

When BAI VIDEO PRODUCTION is the Active Project:

- do not modify BAI Development OS source, registry, specifications, tasks, or tests unless the Owner explicitly requests an OS change;
- do not copy BAI Development OS Core into the Consumer Product;
- use BAI Development OS to determine development governance, not as a Product runtime dependency.

When work is explicitly about BAI Development OS itself, use a separate Codex project/session with the BAI Development OS repository as the Primary folder whenever practical.

---

## 3. Source-of-Truth Separation

Do not collapse implementation reality, governance authority, and evidence into one source.

### 3.1 Implementation reality

The current Git checkout is authoritative for what code/files actually exist now:

- repository identity,
- HEAD,
- branch/worktree,
- dirty state,
- current source and tests.

### 3.2 Governance and authority

Use the Active Project's current canonical state and Active Task authority artifacts.

For BAI VIDEO PRODUCTION, begin with:

1. `docs/ai-team/current-state.md`
2. the current canonical roadmap only when routing/priority is needed
3. the Active Task definition / summary / bound authorization
4. exact design/schema/contracts required by the current Atomic Unit

For BAI Development OS governance questions, begin with the secondary BAI Development OS source:

1. `registry/current-state.md`
2. `registry/ai-context-pack.md`
3. `registry/context-loading-rules.md`
4. only the exact canonical specification needed for the decision

Do not load the whole OS Architecture or all completed Tasks by default.

### 3.3 Evidence

Tests, Critic reports, Handoffs, CI results, manifests, dashboards, generated reports, and previous conversation claims are Evidence. They do not create implementation, release, paid-provider, native-runtime, deployment, or Production authority by themselves.

---

## 4. Active Project Resolution

Resolve the Active Project from the user's request, Primary folder, current working directory, Git root, and project identity.

Do **not** stop merely because the user did not restate the project name when the Active Project is unambiguous.

Stop or request Owner clarification only when a consequential ambiguity cannot be resolved safely from current Git/project evidence.

Never read or modify an unrelated project merely because it is attached as another source folder.

---

## 5. Active Task and Task Identity

Before implementation mutation, bind work to an existing authorized Task/Atomic Unit or to a newly allocated Task approved by the governing process.

### 5.1 Historical Task protection

Completed, rejected, cancelled, superseded, or otherwise final task history is immutable historical evidence.

Do not reuse an existing Task ID simply because its subject is adjacent to a new requirement.

Before extending an existing Task, verify all of the following:

- its current status,
- its original responsibility boundary,
- whether its own roadmap explicitly reserves the proposed continuation,
- whether the new scope remains within that responsibility boundary.

If the new capability materially expands responsibility, architecture, or ownership, allocate a **new Task ID** and express the existing Task as a dependency instead of overloading it.

A revision (`R1`, `R2`, etc.) is valid only when it is a genuine continuation of the same Task responsibility.

### 5.2 New requirements

A new requirement may begin as intake/design work before implementation authority exists. Do not invent implementation authority from design activity.

A direct Owner request to implement is Owner intent, but Codex must still bind that intent to an explicit bounded Task/Atomic Unit, allowed-file scope, safety gates, and completion criteria before mutation.

---

## 6. Adaptive Development Governance

Select the minimum safe development depth using BAI Development OS Adaptive Governance.

### DEV-0 QUICK

Use for micro, local, low-impact and highly reversible work, such as obvious documentation corrections.

Default behavior:

- Builder responsibility only,
- minimal plan,
- targeted validation,
- no ceremonial Critic/Judge loop.

### DEV-1 LIGHT

Use for small, ordinary and reversible changes.

Default behavior:

- short change plan,
- targeted unit/smoke verification,
- add review only when change characteristics justify it,
- maximum one review/fix cycle.

### DEV-2 STANDARD

Use for normal production features and bug fixes.

Default behavior:

- focused design,
- Tester responsibility required,
- Critic responsibility on design or implementation as appropriate,
- relevant unit/integration/targeted regression,
- Judge only when a real gate/high-risk decision exists.

### DEV-3 HIGH ASSURANCE

Minimum for core functions, security/authorization/state-machine/data-migration work, multi-project behavior, cross-project contracts, or comparable high-risk work.

Default behavior:

- detailed design,
- Critic on design and implementation,
- independent Tester where supported,
- boundary/negative/integration/regression coverage,
- Judge for material gates/high-risk decisions,
- maximum two review/fix cycles before escalation.

### DEV-4 FOUNDATION CRITICAL

Use for BAI Development OS foundation changes or critical failure-impact changes.

Default behavior:

- architecture + failure-mode design,
- independent Critic/Tester,
- Judge,
- contract/recovery/fault tests where applicable,
- impacted core regression and consumer fixtures where applicable,
- no arbitrary unrelated full-history revalidation.

### Safety floors

Do not classify below the applicable OS floor. In particular, security, authorization, state-machine, data-migration, cross-project contract, multi-project, CORE, FOUNDATION, or CRITICAL-impact changes require the stronger profiles defined by the current BAI Development OS governance.

Adaptive Governance changes **workflow depth**, not authority and not the permanent model policy.

---

## 7. Roles Are Responsibilities, Not Mandatory Ceremony

Builder, Critic, Tester, Judge, Project Policy, and Orchestrator remain distinct responsibilities where required.

Do not assume every Atomic Unit needs a separate full artifact and a separate agent for every Role.

Use the selected DEV profile to determine:

- which responsibilities are required,
- whether independence is required,
- which artifacts/evidence are useful,
- how many review/fix cycles are allowed.

For DEV-0/DEV-1, compress ceremony aggressively while preserving validation.

For DEV-3/DEV-4, preserve required independence and gates. Subagents may be used for independent Critic/Tester work when they improve assurance or keep exploratory context out of the main thread.

No Role may create Owner Authority.

---

## 8. Model Capability Routing

Route work by required capability and cost efficiency, after Authority/Safety/DEV eligibility is satisfied.

### High-reasoning tier

Use for work such as:

- architecture,
- contradiction resolution across canonical designs,
- canonical responsibility boundaries,
- high-impact schema decisions,
- high-assurance Critic/Judge reasoning,
- difficult debugging after ordinary methods fail,
- final integration review.

### Implementation tier

Use as the default engineering workhorse for:

- Python/application implementation,
- adapters,
- stores and migrations within an approved design,
- application services,
- UI wiring,
- ordinary tests,
- refactoring.

### Bulk/mechanical tier

Use for bounded low-risk work such as:

- additional tests,
- fixtures,
- schema boilerplate,
- documentation synchronization,
- renames,
- repetitive mechanical edits,
- static audits.

When the configured models are available, the current BAISOUND example mapping is:

- high-reasoning: `GPT-5.6 Sol`
- implementation: `GPT-5.6 Terra`
- bulk/mechanical: `GPT-5.6 Luna`

This mapping is an execution preference, not a safety rule. If model availability changes, preserve the capability tiers rather than the vendor/model names.

Context savings or cheaper models must never lower required quality, Authority, Safety, Security, or DEV floors.

---

## 9. Context Scope Contract

Context is a budgeted engineering resource.

Every nontrivial Atomic Unit should have an explicit or inferable Context Scope with:

- `MUST READ`
- `READ IF REQUIRED`
- `DO NOT READ BY DEFAULT`
- `MAY MODIFY`
- `MUST NOT MODIFY`
- escalation conditions.

### 9.1 Default read strategy

Read the smallest current set first:

1. current state,
2. Active Task / Atomic Unit,
3. exact dependency contract summaries,
4. target source,
5. target tests,
6. exact schemas/interfaces required by the change.

Prefer summaries and exact sections over complete historical documents.

### 9.2 Default exclusions

Do not read/search these by default unless the Atomic Unit requires them:

- `archive/**`
- historical/superseded roadmaps,
- all completed Task folders,
- full Architecture documents,
- unrelated Product subsystems,
- unrelated schemas/tests,
- old Evidence packs,
- generated reports unrelated to the current decision,
- the entire secondary BAI Development OS repository.

### 9.3 Search discipline

Avoid unbounded context-generating commands such as repository-wide file dumps or reading large documents in full without a reason.

Prefer:

- exact `rg` queries scoped to relevant directories,
- bounded line/range reads,
- symbol/path searches,
- changed-file and dependency-driven exploration,
- focused tests before broad tests.

Do not run `find .`, unrestricted recursive grep, or equivalent broad enumeration merely "to understand the repository" when current summaries provide a narrower route.

### 9.4 Escalation rule

If required information is missing:

1. identify the missing contract/fact;
2. search only likely relevant paths;
3. read the smallest additional set;
4. record why the scope expanded when the expansion is material.

As an operating target, begin with roughly 8 or fewer primary documents/files and add roughly 5 or fewer supplemental reads before reassessing the Context Scope. This is a cost-control heuristic, not a hard safety limit.

Do not raise context limits merely to accommodate duplicated history.

---

## 10. Atomic Unit Execution

Large Tasks must be decomposed into bounded Atomic Units.

The preferred unit lifecycle is:

```text
Design
→ Implement
→ Focused Test
→ Required Review
→ Fix / Retest if bounded
→ Diff / Scope Check
→ Commit-ready
→ Completion Summary / Handoff
```

Do not start several dependent implementation slices at once merely to appear autonomous.

An Atomic Unit should have:

- one clear goal,
- explicit inputs/dependencies,
- allowed files,
- prohibited files/side effects,
- acceptance criteria,
- focused tests,
- completion evidence.

Finish a safe Atomic Unit before rotating sessions whenever practical.

Do not leave a unit half-mutated merely because context is becoming large; reach a safe checkpoint or enter an explicit Recovery/Handoff state.

---

## 11. Autonomy and Human Gates

Autonomy may select and execute only work already eligible under the governing authority and safety rules.

A Human Gate blocks **the gated side effect**, not necessarily every independent safe work item.

When a gated action can be isolated safely:

- mark/park that action,
- preserve the evidence needed to resume it,
- continue another authorized independent Atomic Unit if one exists.

Stop the entire lane only when the gate is shared, unsafe to bypass, or leaves source-of-truth/ownership uncertain.

Human or Owner authorization remains required where applicable for actions including:

- paid-provider calls or credit purchases,
- production/native side effects outside an already authorized bounded gate,
- external account mutation,
- real Resolve/Cubase project writes when not specifically authorized,
- model/runtime downloads when separately gated,
- release/deploy/Production Activation,
- destructive cleanup or irreversible migration beyond the approved scope.

Design approval never automatically implies implementation, release, deploy, paid, native, or Production authority.

---

## 12. BAI VIDEO PRODUCTION Product Boundaries

BAI VIDEO PRODUCTION is a standalone Consumer Product.

BAI Development OS is development-time Governance and must not become a Product runtime dependency.

When working in BAI VIDEO PRODUCTION:

- preserve the Product's canonical Asset/Timeline/Provider/Voice/Export responsibility boundaries;
- prefer reuse of existing Product capabilities over duplicating parallel implementations;
- do not invent a second canonical store/timeline when an existing canonical responsibility already owns that domain;
- when a new canonical model is genuinely required, define the boundary and bridge explicitly;
- distinguish Product Jobs from BAI Development OS development Tasks;
- distinguish Product cost/Provider execution from development model/context cost.

New architecture must identify how it integrates with the unified `BAI Video Production.exe` Product entrypoint unless the Owner explicitly allocates a separate Product.

---

## 13. Git and Worktree Safety

Before mutation:

- confirm repository identity,
- inspect HEAD/branch/worktree/status,
- preserve unknown dirty changes,
- confirm the intended base and task branch.

Default rules:

- no direct push to protected `main`,
- no force push,
- no `reset --hard` to discard unknown work,
- no destructive branch cleanup without eligibility/ownership confirmation,
- avoid `git add .`; stage explicit files,
- do not overwrite unrelated local changes,
- one dedicated work branch/worktree per bounded development unit or coherent Task slice.

If HEAD, base branch, worktree ownership, merge state, or dirty-path ownership changes unexpectedly, enter Recovery before continuing mutation.

After an externally merged branch, re-audit current `main` before beginning the next unit; do not assume the previous checkout remains canonical.

---

## 14. Verification Strategy

Verification depth follows the selected DEV profile and actual impact.

Default order:

1. syntax/schema/static validation where relevant,
2. focused unit tests,
3. relevant integration/boundary tests,
4. targeted regression,
5. broader/full regression only when required by profile, contract breadth, release/closure gate, or observed risk.

Do not run the full repository suite after every tiny edit merely as ceremony.

Do not report PASS for work that was not executed or observed.

Top-level technical results are:

- `PASS`
- `FAIL`
- `NOT_CONFIRMED`

Execution/observation status should remain separate from technical result when relevant.

A successful implementation checkpoint requires the tests required by the Atomic Unit/profile to pass and any required Critical/High review findings to be resolved or explicitly gated.

---

## 15. Context Cost and Session Rotation

Do not keep one Codex thread alive indefinitely simply because it can continue.

At a safe Atomic Unit boundary, evaluate:

- completed work,
- current HEAD/branch/dirty state,
- remaining Task units,
- Context size/noise,
- provider/model usage constraints,
- unresolved gates.

When context becomes inefficient, produce a compact conversation-independent Handoff containing at least:

- Active Project and Task/Atomic Unit,
- exact HEAD/branch/worktree/status,
- completed unit(s),
- current authority/gates,
- next action,
- minimal next-session read list,
- do-not-touch list,
- test/evidence summary.

Target a concise Handoff rather than carrying raw logs and prior debate into the next session.

Never rotate in the middle of an unsafe partial mutation when a safe checkpoint can still be reached.

---

## 16. Progress Stall and Recovery

Do not repeat identical commands or full workflows without a changed hypothesis or new evidence.

Enter Recovery/Handoff when there is:

- changed or unknown HEAD,
- merge conflict,
- unknown dirty ownership,
- source-of-truth conflict,
- partial/corrupt evidence,
- repeated test failure beyond the bounded rework budget,
- external provider/usage limit,
- persistent process with no new evidence,
- native failure requiring Owner/environment intervention.

Preserve the work and evidence needed to resume. Do not fabricate completion.

---

## 17. External / Native / Secret Safety

Never print, commit, or copy secret values into documentation, logs, fixtures, prompts, or Evidence.

Do not treat configuration presence as execution authority.

Do not silently:

- purchase credits,
- call paid providers,
- upload private media/voice data,
- install/update third-party runtimes or models,
- mutate production accounts/projects,
- activate deployment/production,
- retry a previously unsafe native operation.

Use existing Product/OS gates and fail closed when a consequential external action lacks exact authority.

---

## 18. Documentation and Evidence Economy

Create documentation that changes decisions, preserves contracts, enables handoff, or satisfies a required gate.

Do not generate duplicate narrative artifacts solely to repeat unchanged state.

Prefer updating the canonical current-state/Task record and producing one bounded completion summary over creating many redundant reports.

Historical evidence remains immutable; later corrections belong in current canonical records or a newly authorized follow-up Task.

### Documentation filename policy

Documentation file and directory names under `docs/` MUST use ASCII English-safe names. Japanese prose is allowed inside documents, but Japanese/non-ASCII path names and escaped/mojibake forms such as `#Uxxxx` are not allowed. When correcting an existing documentation filename, update all in-repository references and keep the OSS/readiness link checks green.

---

## 19. Definition of Done for an Atomic Unit

An Atomic Unit is complete only when all applicable items are true:

- scope matches the authorized unit,
- only allowed files were changed,
- implementation matches the bound design/contracts,
- required tests passed,
- required Critic/Tester/Judge responsibilities were satisfied for the selected DEV profile,
- unresolved high-severity findings are zero or explicitly gated,
- diff/scope was reviewed,
- no unauthorized external/native/paid/production side effect occurred,
- repository state is commit-ready or the exact commit is recorded,
- next action and Human Gates are explicit.

Do not equate "code written" with "unit complete".

---

## 20. Startup Procedure for BAI VIDEO PRODUCTION Work

For a normal BAI VIDEO PRODUCTION Codex run:

1. confirm BAI VIDEO PRODUCTION is the Primary/Active Project;
2. inspect Git root, HEAD, branch/worktree and status;
3. read `docs/ai-team/current-state.md`;
4. identify the Active Task/Atomic Unit from current authority and the Owner request;
5. verify that an existing Task ID is not being incorrectly reused;
6. select/confirm DEV profile;
7. establish the minimal Context Scope;
8. read only exact source/schema/tests needed;
9. execute one bounded Atomic Unit through commit-ready state;
10. create/update concise Evidence/Handoff only as required.

Use BAI Development OS secondary-source documents only when exact governance/contract interpretation is necessary. Do not recursively inspect the entire OS repository at startup.

---

## 21. Stop Conditions

Stop or escalate only when continued autonomous work would be unsafe or unauthorized, including:

- consequential Active Project ambiguity that cannot be resolved,
- source-of-truth conflict,
- unknown dirty ownership affecting the target scope,
- implementation authority absent for the requested mutation,
- required Human Gate for a shared blocking side effect,
- secret/instruction-injection risk,
- unsafe/destructive operation without exact approval,
- bounded review/fix budget exhausted with unresolved blocker.

Do **not** stop merely because a safe local detail is unspecified when it can be resolved from canonical contracts, existing project conventions, tests, or a reversible engineering choice.

When possible, park only the blocked action and continue another independent authorized unit.

---

## 22. Compact Operating Principle

Use this order of priorities:

```text
Correct Project / Current Git
→ Authority & Safety
→ Correct Task Responsibility
→ Adaptive DEV Profile
→ Minimal Context Scope
→ Appropriate Model Capability
→ Atomic Unit
→ Focused Verification
→ Commit-ready Evidence
→ Safe Handoff / Next Unit
```

Optimize cost and context **inside** the safety/quality boundary, never by weakening it.
