# TASK-021 Integrated Dashboard / Operations Foundation R0

## Authority and outcome

- Authorization: `BVP-AUTH-20260817-TASK021-INTEGRATED-DASHBOARD-OPERATIONS-R0-01`
- Base: `main@f6b20782a0e13e6683231593c99286af55fb7a18`
- Owner: 開発担当2 exclusive
- Scope: body-free pure metadata parse/hash/validate/classify/project only
- Effect authority: none. Dashboard does not read or mutate stores, operate Jobs/processes/apps, send alerts, access private bodies, or activate Production.
- Existing `production_dashboard.py` remains immutable and authoritative for its existing Plan/Scene/Slot/Candidate/Audit/Prompt/Continuity/Audio/Budget summary.

## A. Fresh source-of-truth audit

The operation-time preflight read back canonical main, Registry revision 23, no open PR, and the single unrelated active `BVP-LOCK-TASK046-PVS3B`. All five TASK-021 paths and the target branch/worktree were absent. Candidate overlap was zero. The serialized CHANGELOG preimage was `d52acb838b2a93a2d503cd969576ecfeb4d0e62c`.

Dependency blob evidence at allocation time:

| Canonical dependency | Git blob | Use |
|---|---|---|
| `production_dashboard.py` | `4661017949317129c816758df2184a9186fe20f0` | Existing dashboard projection, immutable |
| durable Job module / schema | `028896468851a5267c95443b94b186910580f32b` / `0443588a0087981ddb59217cd9467ee444587c66` | Job truth by digest reference |
| checkpoint module / schema | `c8232dcb6e22771c32adb2af491609c172b655a6` / `2201a756eef96788612a270495f42a8f0cdb9870` | Checkpoint truth by digest reference |
| Audit application | `41a6f7a560e6d1701cb293c59dbb67b73d2efa0a` | Audit truth by digest reference |
| candidate Audit | `794222871bd970714b823f7a44ca2962ebe4fd73` | Evidence source boundary |
| TASK-020 module / schema | `1e1c70e078c322f5d2fb59ddbd921bd6f5a7585b` / `1e900f4480d08fe598f5ea1ce76e3a325f1bc5e0` | Resource facts/decisions by reference |
| TASK-016 module / schema | `d83100f1b8108949c6ab85804d89800facfd3e41` / `79f3a54482c2cfe65ad5f09bfa170f730b414d7b` | Public privacy projection only |

## B. Existing versus missing contract

| Concern | Existing canonical owner | TASK-021 addition |
|---|---|---|
| Production plan/scene/slot summary | `production_dashboard.py` | No duplication or replacement |
| Job lifecycle and operation identity | durable Job contract | Body-free read model bound to exact source digest |
| Checkpoint state | checkpoint owner | Source binding only; no checkpoint issuance |
| Resource facts/admission | TASK-020 | Evidence view only; no recollection/recalculation |
| Privacy | TASK-016 | Canonical public projection only by default |
| Audit truth | TASK-038/Audit owners | Evidence/incident coordinates only |
| Cross-source staleness and coverage | Missing | Exact source binding, watermark and fail-closed snapshot state |
| Alert display | Missing | Deterministic classification receipt; no send effect |
| Operations | Missing | Proposal, Human confirmation binding and external receipt as three separate records |

## C. Ownership and dependency graph

```text
canonical Job / Checkpoint / Audit / TASK-020 / TASK-016 public truth
              │ exact ref + digest + revision + observed time
              ▼
DashboardSourceBinding ──► Job/Evidence/Incident read models
              │                         │
              └──────────► IntegratedDashboardSnapshotRevision
                                      │
                                      ▼
                         DashboardOperationProposalRevision
                                      │ no effect authority
                                      ▼
                       HumanOperationConfirmationBinding
                                      │ external owner executes
                                      ▼
                       DashboardExecutionReceiptBinding
```

Source truth is never copied into a dashboard-owned store. A display state is not operation authority. An operation proposal is not Human approval. Human approval is not execution. An acknowledgement is not resolution or success.

## D. Canonical records and closed states

Canonical root union, exact 11:

1. `DashboardProjectionPolicyRevision`
2. `DashboardSourceBinding`
3. `DashboardQueryIntent`
4. `DashboardJobReadModel`
5. `DashboardEvidenceReadModel`
6. `DashboardIncidentReadModel`
7. `DashboardAlertClassificationReceipt`
8. `IntegratedDashboardSnapshotRevision`
9. `DashboardOperationProposalRevision`
10. `HumanOperationConfirmationBinding`
11. `DashboardExecutionReceiptBinding`

Key closed classifications:

- source contract: `CANONICAL_REF_NOT_PROVIDED / BOUND_VERIFIED / MISMATCH / UNKNOWN`
- freshness/validity: `CURRENT / STALE / INVALIDATED / UNKNOWN`
- snapshot: `ACTION_REQUIRED / DEGRADED / NO_ACTIVE_INCIDENT_PROVEN / STALE / UNKNOWN`
- incident: `ACTIVE / RESOLVED_PROVEN / UNKNOWN`
- alert lifecycle: `OPEN / ACKNOWLEDGED / RESOLVED_PROVEN / SUPPRESSED_BY_POLICY / UNKNOWN`
- proposal: `PROPOSED / BLOCKED / UNKNOWN`
- external receipt: `ACCEPTED / REJECTED / FAILED / UNKNOWN`

Caps are fixed at sources 256, items 4096, alerts/incidents 1024, proposals 256, reason codes 64 and page size 200. Arrays used in digests are unique and canonical sorted. Every record is immutable, rejects unknown fields, and carries a deterministic canonical SHA-256.

## E. Negative acceptance matrix

| Case | Required result |
|---|---|
| source canonical ref missing | `UNKNOWN`; invented coordinates rejected |
| TASK-016 private projection selected | rejected; `PRIVACY_PUBLIC` requires public projection |
| private path, credential-like identifier or body | rejected |
| source age exceeds current policy | snapshot `STALE` even if supplied state says current |
| stale/invalidated source | `STALE`; never healthy |
| unknown source/job/evidence | `UNKNOWN`; never PASS |
| empty incidents with partial/unknown coverage | `UNKNOWN`; absence is not health evidence |
| active incident or acknowledged open alert | `ACTION_REQUIRED` |
| running/queued Job | `DEGRADED`; not success |
| resolved incident without receipt | rejected |
| acknowledged alert without receipt | rejected |
| unordered/duplicate/cap-exceeding digest input | rejected |
| proposal with `execution_started=true` | rejected |
| raw `execution_authorized` | unknown field, rejected |
| missing, AI-forged, expired, consumed or mismatched Human confirmation | external gate blocked |
| external result `UNKNOWN` | retained as unknown with no replay |
| external `ACCEPTED` without canonical persistence proof | rejected |
| public projection | omits source refs/digests/revisions/times and all private detail |

## F. API and implementation boundary

The pure module exposes immutable record classes, `validate_record`, `classify_alert`, `build_snapshot`, `operation_admission_report`, and public/private projection functions. `operation_admission_report` returns only `READY_FOR_EXTERNAL_HUMAN_GATE`, `BLOCKED`, or `RESULT_RECORDED` metadata and keeps every effect-started flag false. It does not produce a command or authority token.

Static surface forbids OS/filesystem/network/process/app/provider imports. `EFFECT_SURFACE` explicitly fixes source read/mutation, Job/process/app control, network/provider, alert send, private body/path/credential read, and Release/Deploy/Production to false.

## Validation plan and evidence

- focused schema/runtime/hash/tamper/caps/staleness/privacy/authority suite
- schema mirror byte equality and all 11 root types
- existing Production Dashboard compatibility import and full regression
- Windows full suite
- WSL full suite
- hosted CI and Security checks
- first-parent exact-six read-back after canonical merge

## Critic pass 1 — Builder

- Finding: initial snapshot calculation trusted supplied freshness without applying the policy age limit.
- Correction: compare every exact `observed_at` with snapshot `generated_at` and policy `max_source_age_seconds`; over-age becomes `STALE`.
- Finding: digest arrays could encode caller-dependent order.
- Correction: require canonical sorted unique digest inputs and sort helper outputs.
- Result: unresolved Critical/High/Medium = `0/0/0`.

## Critic pass 2 — Security

- Finding: an initial admission report boolean could be confused with dispatch authority.
- Correction: replace it with the closed metadata-only `gate_decision`; retain all start/effect flags false.
- Finding: Windows absolute paths using forward slashes could pass the identifier pattern.
- Correction: reject drive-rooted identifiers as well as backslash, root, traversal and credential-like tokens.
- Result: unresolved Critical/High/Medium = `0/0/0`.

## Critic pass 3 — Operations UX

- Confirmed ACK is displayed separately from resolution/success.
- Confirmed empty incident sets cannot become healthy without current complete coverage.
- Confirmed running and queued states remain `DEGRADED`, while unknown stays `UNKNOWN`.
- Confirmed the public projection exposes states/reasons only, not low-count or private coordinates.
- Result: unresolved Critical/High/Medium = `0/0/0`.

## Critic pass 4 — Compatibility

- Existing `production_dashboard.py` and all upstream source contracts remain unchanged.
- The public schema and packaged mirror are byte-identical.
- No `__init__.py`, Registry, roadmap, workflow, source store or shared shell edit is required.
- Result: unresolved Critical/High/Medium = `0/0/0`.

## Provisional Judge

- `DOMAIN_READINESS=PASS`
- `PURE_METADATA_IMPLEMENTATION=PASS`
- `SCHEMA_MIRROR=PASS`
- `DASHBOARD_EFFECT_AUTHORITY=BLOCKED_FAIL_CLOSED`
- `PRIVATE_DETAIL_ACCESS=BLOCKED`
- `JOB/STORE/PROCESS/APP/PROVIDER/ALERT/PRODUCTION_EFFECT=NOT_AUTHORIZED`
- residual Critical/High/Medium = `0/0/0`

Final merge readiness additionally requires focused and full local tests, exact six-file diff, hosted checks 9/9 terminal SUCCESS, fresh zero-drift preflight, canonical merge, post-merge CI/Security SUCCESS, and serialized CHANGELOG Lock release.

## Local validation receipt

- focused TASK-021: `29 passed`
- public schema: parsed as Draft 2020-12; all 11 roots accepted
- schema mirror: byte exact
- AST/static effect surface: PASS
- Windows full regression: `1523 passed, 1 skipped`; the one remaining failure is the pre-existing TASK-047 Windows installer acceptance returning exit 4 under the managed sandbox. It is recorded as non-PASS external-environment Evidence and is not counted as TASK-021 success.
- WSL full regression: `1524 passed, 1 skipped` (the Windows-only TASK-047 installer case)
- exact TASK-021 focused/full failures: `0`
- Critic residual Critical/High/Medium: `0/0/0`

## Local Judge

- `TASK021_DOMAIN_AND_IMPLEMENTATION=PASS`
- `FOCUSED_AND_WSL_FULL=PASS`
- `WINDOWS_FULL=PASS_EXCEPT_KNOWN_MANAGED_SANDBOX_TASK047_INSTALLER_DENIAL`
- `EFFECT_AUTHORITY=ZERO`
- `READY_FOR_DRAFT_PR=PASS`
- `READY_FOR_CANONICAL_MERGE=CONDITIONAL_ON_HOSTED_9_OF_9_AND_FRESH_ZERO_DRIFT_PREFLIGHT`
