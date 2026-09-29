# TASK-100 LVC-C2-D0 — Native Installed-Identity Boundary Design R0

Status: `DESIGN_IN_REVIEW / SOURCE_NOT_ALLOCATED / NATIVE_BLOCKED`

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

The pure verifier must reparse every public constructible record, bind contract and producer versions, compare pair/runtime/profile/candidate/custody/license/Consent identities, reject crossed or stale records, and remain effect-zero. Until the installed-observation producer and ABI are accepted, its only truthful result is dependency-blocked; it cannot manufacture `INSTALLED` from catalog state.

### 4.2 C2-N native observation

Native observation is a separate effect unit and requires an exact Owner Human Gate. Its producer and ABI are not allocated by this design. The future unit must use bounded private handles, not caller-supplied reusable paths, and must validate the exact protected pair inventory, file identities, pair digest, runtime/build identity, custody revision and trusted-time currentness. It must not load the model or infer audio.

Any hashing of private model bytes is a private-body read and must be named in the native authorization. Output and logs must remain under a unique verified OS temporary root or the canonical external Evidence root; public evidence contains opaque identities and digests only. Absolute private paths, account names, model bodies, reference audio/text and secrets must not be persisted.

Observation does not issue TASK-101's load lease, TASK-075 execution authority or TASK-071/072 Human action/ticket authority. UNKNOWN or partial observation fails closed and is not automatically retried, repaired or cleaned up.

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
2. accepted TASK-101 import custody/readback input contract or an explicit decision that C2 remains blocked without it;
3. exact source, canonical schema, package mirror and test Allowed Files;
4. frozen digest domain, parser limits, timestamp rules and negative/crossing vectors;
5. DEV-4 independent Critic and Tester plan.

C2-N additionally requires:

1. exact private roots/objects and no-drive-root containment preflight;
2. current TASK-046 H4/Consent/rights and TASK-101 protected custody authority;
3. exact TASK-066 compute/no-network policy evidence if live eligibility is claimed;
4. explicit authorization for private model-byte reads and exact observation effects;
5. unique output/Evidence roots, residual-artifact policy and no-clobber/recovery behavior;
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
