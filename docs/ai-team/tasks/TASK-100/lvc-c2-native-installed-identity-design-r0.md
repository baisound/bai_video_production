# TASK-100 LVC-C2-D0 — Native Installed-Identity Boundary Design R0

Status: `DESIGN_ACCEPTED / SOURCE_NOT_ALLOCATED / NATIVE_BLOCKED`

## 1. Goal

Define the fail-closed boundary by which a future TASK-100 consumer can confirm that the exact admitted GPT-SoVITS model pair and runtime identity are present in protected Product custody. This design closes ownership and ABI ambiguity only. It does not inspect files, hash private model bodies, start a runtime, load a model, infer audio, issue a load lease, or connect Product/Shell UI.

LVC-C2-D0 is a continuation of TASK-100's catalog-consumer responsibility, not a new Task. PR #595 merged the accepted body-free LVC-C1 readback into main `1d9f4a471ea8540a9fb2df19a0e2cd933e8374e2`. The Owner's subsequent `次へ進んで` binds this design-only Atomic Unit; native gates remain unchanged.

## 2. Exact design scope

Repository Allowed Files:

1. `docs/ai-team/tasks/TASK-100/task.md`
2. `docs/ai-team/tasks/TASK-100/lvc-c2-native-installed-identity-design-r0.md`

External Evidence may be written only below `C:\home\baisound\evidence\bai-video-production\TASK-100\lvc-c2-d0\<run-id>\`.

All source, schema, tests, producer Task records, current-state/index, Product/Shell code and external voice repositories are read-only or prohibited. No native/private/model/audio/runtime effect is authorized by this design.

## 3. Canonical owner resolution

The delivery overlay previously named `TASK-063-INSTALLED-READBACK` as a prerequisite. Current canonical TASK-063 owns only installer-root derivation and readback for the montage-learning Bridge. Its receipt cannot prove GPT-SoVITS model-pair custody, installation, currentness or load permission. Reusing its digest would be a cross-domain identity error.

This supersedes the earlier TASK-100 Task prose that named `063/036 installed binding` as model evidence, but it does not rewrite the accepted V1 ABI. The V1 `installed_binding_sha256` remains only the existing candidate/route/preflight correlation coordinate. It is not a C2 receipt and cannot be promoted or rehashed into one. A future C2 schema must add a separately named and versioned assessment/receipt coordinate.

The required boundary is therefore:

| Responsibility | Canonical owner | C2 treatment |
|---|---|---|
| ModelArtifactBinding, selected pair lineage, current H4, Consent, rights and license | TASK-046 | required typed body-free input; never re-issued by TASK-100 |
| Existing externally supplied pair import, protected custody/readback/currentness and one-operation load lease | TASK-101 | required future producer; currently design-only and unavailable |
| Catalog candidate/admission and consumer currentness | TASK-100 LVC-I/C1 | accepted input |
| Compute and no-network admission | TASK-066 | required producer evidence; not inferred from hardware presence |
| Runtime execution, model loading, inference and PCM handoff | TASK-075 | downstream owner; never executed by C2 |
| Fine-tuned route and private reference selection | TASK-074 | downstream/read-only identity binding |
| Narration admission and assembly | TASK-014 | downstream/read-only consumer |
| Product composition and Shell controls | TASK-073 / TASK-036 | separate owning Atomic Units |

TASK-093's Qwen Owner Voice Runtime installer does not establish installation of the selected GPT-SoVITS pair. A server health response, WSL path, matching filename, historical training export, public release record or self-declared digest is also insufficient.

## 4. Future ABI layers

### 4.1 C2-I pure verifier

A future source allocation may define a deterministic `LocalVoiceInstalledIdentityAssessmentV1`. It must accept only:

- the exact accepted `LocalVoiceCatalogConsumerReadbackV1`;
- current TASK-046 ModelArtifactBinding and approval/currentness identities;
- a reviewed TASK-101 existing-import custody/readback identity;
- a reviewed installed-observation record from the explicitly allocated producer;
- TASK-066 compute/no-network evidence when live eligibility is evaluated;
- a trusted evaluation time supplied by the orchestrator.

The pure verifier must reparse every public constructible record, bind contract and producer versions, compare pair/runtime/profile/candidate/custody/license/Consent identities, reject crossed or stale records, and remain effect-zero. Final installed/live eligibility is the explicit conjunction of the exact accepted C1 readback and an admitted separately versioned C2 assessment. C1 `consumer_live_eligible=true` is pre-native Human-Gate evidence only. Until the installed-observation producer and ABI are accepted, or whenever the C2 receipt is absent, the final result is `DEPENDENCY_BLOCKED`; catalog state cannot manufacture `INSTALLED`.

### 4.2 C2-N native observation

Native observation is a separate effect unit and requires an exact Owner Human Gate. Its producer and ABI are not allocated by this design. The accepted custody owner must issue a distinct one-operation `INSTALLED_IDENTITY_OBSERVATION` capability for the exact pair and observation operation. It is read-only, one-shot, non-replayable, non-load and non-executing, and carries bounded private handles rather than a caller-supplied reusable path. TASK-101's inference load lease and any generic path token are invalid substitutes. Missing or crossed observation capability yields `DEPENDENCY_BLOCKED` before any body is opened. The future unit validates the exact protected pair inventory, file identities, pair digest, runtime/build identity, custody revision and trusted-time currentness. It must not load the model or infer audio.

Any hashing of private model bytes is a private-body read and must be named in the native authorization. Private scratch and sensitive logs may exist only below a unique verified OS temporary root and must follow the authorized retention policy. Every native run must additionally persist a bounded public-safe checkpoint/receipt below `C:\home\baisound\evidence\bai-video-production\TASK-100\lvc-c2-n\<run-id>\`, reopen it, and verify its identity or digest. That durable checkpoint records result, receipt/hash, resolved scratch/output/Evidence roots and every intentional residual artifact. Public evidence contains opaque identities and digests only; absolute private paths, account names, model bodies, reference audio/text and secrets must not be persisted.

Observation neither issues nor consumes TASK-101's inference load lease, TASK-075 execution authority or TASK-071/072 Human action/ticket authority. Only the distinct `INSTALLED_IDENTITY_OBSERVATION` capability may authorize its bounded read. UNKNOWN or partial observation fails closed and is not automatically retried, repaired or cleaned up.

## 5. Decision states

The future assessment uses a closed state set:

- `DEPENDENCY_BLOCKED`: one or more required producer contracts or current receipts are unavailable;
- `IDENTITY_MISMATCH`: a typed current record exists but exact pair/runtime/custody identity differs;
- `STALE_OR_REVOKED`: time, Consent, rights, approval, custody or compute evidence is not current;
- `NATIVE_IDENTITY_CONFIRMED`: exact installed identity is observed and all required body-free inputs agree.

`NATIVE_IDENTITY_CONFIRMED` means observation only. It must keep execution, lease, runtime, model-load, inference, audio, Project mutation and Product activation authority false. It cannot be projected unless the separately authorized C2-N observation actually ran and its exact receipt is admitted.

## 6. Implementation and native start gates

C2-I source allocation requires all of the following:

1. accepted installed-observation producer owner and versioned ABI;
2. accepted observation-capability issuer and `INSTALLED_IDENTITY_OBSERVATION` ABI, distinct from the inference load lease;
3. accepted TASK-101 import custody/readback input contract or an explicit decision that C2 remains blocked without it;
4. exact source, canonical schema, package mirror and test Allowed Files;
5. frozen digest domain, parser limits, timestamp rules and negative/crossing vectors;
6. DEV-4 independent Critic and Tester plan.

C2-N additionally requires:

1. exact private roots/objects and no-drive-root containment preflight;
2. current TASK-046 H4/Consent/rights and TASK-101 protected custody authority;
3. exact TASK-066 compute/no-network policy evidence if live eligibility is claimed;
4. explicit authorization for private model-byte reads and exact observation effects;
5. unique OS-temp scratch plus mandatory canonical external Evidence/readback, residual-artifact policy and no-clobber/recovery behavior;
6. independent native verification and final integration review.

Absent any item, the unit remains `BLOCKED` and no file body is opened.

## 7. Product integration boundary

TASK-100 may publish only its accepted body-free assessment for other owners to consume. It must not directly modify TASK-036 Shell, TASK-073 composition, TASK-014 narration, TASK-074 selection, TASK-075 execution or their schemas/tests. Those owners may later bind the accepted TASK-100 assessment in separate exact-file Atomic Units.

No Product/Shell connection, model import, model load, inference, playback, private audio, Project/Asset/Timeline/Export mutation, Release, Deploy or Production use is included in LVC-C2-D0.

## 8. Design acceptance

This design is accepted only when independent DEV-4 review confirms:

- TASK-063 and TASK-093 are not misused as GPT-SoVITS installed-identity producers;
- TASK-046, TASK-101, TASK-066, TASK-075 and TASK-100 responsibilities remain distinct;
- pure verification, native observation, load lease and execution are separate units;
- missing producer authority yields `DEPENDENCY_BLOCKED`, never implied installation;
- future native private-body reads and output roots require exact authorization;
- Product/Shell wiring remains with its canonical owners;
- Critical and High findings are zero.

## 9. Acceptance record

The initial independent Critic returned C/H/M/L `0/1/2/0`. Recovery R1 explicitly superseded the obsolete TASK-063/036 model-proof wording without changing the V1 ABI, required exact C1-and-C2 final eligibility, introduced the dedicated non-load `INSTALLED_IDENTITY_OBSERVATION` capability, and made external public-safe Evidence/readback mandatory after every future native run.

Frozen Recovery HEAD `a1bc60cabc7eaf6d20f93216dcc2ee301b4af957` received independent Critic `ACCEPT` and Tester `PASS`, both C/H/M/L `0/0/0/0`. Exact-two scope, clean branch, resolved relative links, ASCII filenames and `git diff --check` passed. Code and native tests were not run because no C2 source or native implementation is allocated.

This acceptance does not authorize C2-I source, C2-N native observation, private model-body reads, model load, inference, audio handling, Product/Shell integration, Release, Deploy or Production.
