# TASK-045 — Critic Rounds, Final Judge and Authorization

## Critic round 1 — architecture, authority and migration safety

1. `CRITICAL / CLOSED` — A migration executor could accept arbitrary code and
   become an execution boundary. Transformers are code-registered exact identities,
   receive/return bounded bytes and have no public plugin/callable input.
2. `CRITICAL / CLOSED` — Migrating in place could destroy a human Project. Apply
   creates and verifies a retained backup, stages every child, commits through the
   existing child-first/manifest-last CAS coordinator and reopens before success.
3. `CRITICAL / CLOSED` — Legacy discovery could silently adopt unrelated files or
   invent identity. It uses closed canonical rules plus caller-supplied identity
   and returns a read-only preview before any Product mutation.
4. `HIGH / CLOSED` — Lossless planning could accidentally authorize lossy apply.
   Any lossy, human-gated, unsupported or ambiguous transition remains parked;
   the apply API accepts only a `READY_FOR_COPY_ON_WRITE_APPLY` exact plan.
5. `HIGH / CLOSED` — Migration success could be claimed after a partial commit.
   Success requires exact manifest/child reopen verification; otherwise the
   existing journal reports `RECOVERY_REQUIRED`.
6. `HIGH / CLOSED` — Release authority could be confused with Production Deploy.
   Tag/Release is conditionally authorized after gates; Production Deploy remains
   blocked and is not chained from the release workflow.

Design fixes applied: typed transformer registry, explicit legacy identity,
pre-backup, journal composition, reopen proof and separated release/deploy states.

## Critic round 2 — compatibility, performance, UX and release engineering

1. `HIGH / CLOSED` — A synthetic generic migration could claim all v0.20.1
   projects are compatible. The corpus distinguishes exact current manifests,
   explicit no-manifest imports, supported registered transitions and blocked
   unknown/newer/corrupt cases; claims remain limited to tested formats.
2. `HIGH / CLOSED` — The large Asset acceptance could load all 10,000 rows. Add a
   bounded stable keyset query and prohibit full materialization in the Product
   library projection.
3. `HIGH / CLOSED` — A single timing sample could overclaim performance. Record
   fixture size, environment, repeated measurements and median; budgets apply to
   the accepted environment and bounded projection, not all hardware.
4. `HIGH / CLOSED` — Restore could erase Evidence or rewind revision identity.
   Restore remains a verified new CAS revision and never deletes history/Evidence.
5. `HIGH / CLOSED` — Native acceptance could repeat only old v0.20.1 Evidence.
   P-RC-2 reruns the packaged integrated candidate for Project open/reopen,
   Timeline, Export recovery, keyboard/UIA, display and install/restart paths.
6. `HIGH / CLOSED` — Preselecting `0.21.0` could bypass exact SemVer review. The
   design records only an expected MINOR class; exact version remains undecided
   until compatibility/native/clean-install Evidence passes.
7. `MEDIUM / CLOSED` — Release metadata is duplicated across several files.
   P-RC-3 enumerates exact version surfaces and the metadata check must pass before
   PR; no broad search-and-replace is authorized.
8. `MEDIUM / CLOSED` — Browser automation unavailability could falsely block or
   inflate native claims. Browser is recorded separately; only real packaged
   Windows UI Automation/native Evidence satisfies Native acceptance.

Design fixes applied: bounded paging, measured budgets, exact corpus claim scope,
new-revision restore, integrated native rerun and deferred exact version decision.

## Final Critic / Judge

- duplicate Product truth: none; existing TASK owners remain authoritative;
- security/credential/paid boundary: preserved;
- migration/recovery/rollback: explicit and fail closed;
- performance/accessibility/native matrix: measurable and bounded;
- release order: PR -> main merge -> exact SHA -> annotated Tag -> GitHub Release;
- Production Deploy: explicitly excluded;
- unresolved Critical/High: `0 / 0`.

## Final plan

1. Host this design/status synchronization PR and clean its branch/checkout.
2. Fresh-main select `BVP-TASK-045-P-RC-1 / IMPLEMENTATION`.
3. Implement compatibility corpus, explicit legacy discovery, registered
   lossless copy-on-write migration, backup/restore roundtrip and Asset paging.
4. Run focused/full Windows and WSL2 tests, Evidence/Critic, PR, main merge and
   cleanup.
5. Fresh-main select `BVP-TASK-045-P-RC-2 / ACCEPTANCE`.
6. Run long-project, packaged Windows, clean-install and conversation-free restart
   acceptance; repair only observed bounded defects; decide exact SemVer.
7. Host P-RC-2 Evidence/status closure and clean up.
8. Fresh-main create `release/<exact-version>`, finalize exact metadata, run all
   release gates, merge PR, verify main SHA, create/push annotated Tag, publish and
   verify GitHub Release.
9. Create Release Evidence, clean release branch/checkout, fresh-clone main and
   continue AUTONOMY to the next authorized milestone.

## Authorization

- Design/status synchronization: `AUTHORIZED`
- P-RC-1: `AUTHORIZED_AFTER_DESIGN_HOSTED_CLOSURE_AND_FRESH_MAIN_RESELECTION`
- P-RC-2: `DEPENDENCY_WAIT` until P-RC-1 hosted closure
- P-RC-3 Release: `CONDITIONALLY_OWNER_AUTHORIZED` only after P-RC-1/P-RC-2 and
  exact release gates pass
- Credential input: `NOT_AUTHORIZED / HUMAN_GATE`
- Production Deploy, paid Provider and destructive/ambiguous real Project
  migration: `NOT_AUTHORIZED / HUMAN_GATE`
