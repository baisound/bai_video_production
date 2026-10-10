# TASK-101 — Existing Owner Model Import Custody

- Status: `IMC_D_R3_DESIGN_ACCEPTED / IMC_I_IMPLEMENTATION_ACCEPTED / NATIVE_BLOCKED / CANONICAL_INTEGRATION_PENDING`.
- Governance: DEV-4 FOUNDATION CRITICAL.
- Design intent: Owner's 2026-09-27 formal remaining-Task/detail-design request; independent Critic requires a separate import entrypoint rather than expanding TASK-084's training-terminal scope.
- Responsibility predecessor/dependency: TASK-084 protected training artifact custody design; its training branches/source/history are preserved, not reopened or aliased.
- Design coordinator: this voice-integration thread / TASK-073. Implementation owner/Allowed Files and native authority are not allocated by the separate Owner takeover of connection TASK-099/100.
- ID101 is unused at baseline main `e41110c8`; serialize canonical metadata allocation with a fresh ID/lock audit.
- Allowed for IMC-D R0: this task definition and `imc-d-existing-model-import-custody-contract-r0.md` only. No private file read/copy/encryption/load, source/schema/test or external-project change.

## Goal and boundary

Admit an already completed, externally supplied Owner model pair into protected Product custody without new recording, training, fabricated training terminal or TASK-083 reservation. Own **import artifact custody/currentness and one-operation load lease** only. Reuse independently accepted custody/security backend primitives where valid; do not create a second ModelCandidate catalog/store or assume TASK-068 immutable-JSON helpers can write/encrypt binary model trees.

TASK-046 owns verified historical model/Dataset/training lineage, subject/Consent/rights, model evaluation/current H4 and ModelArtifactBinding; TASK-100 owns catalog; TASK-014 owns FineTunedModelBinding/narration; TASK-075 owns inference; TASK-072 owns child authority/containment. A model downloaded/publicly released elsewhere is not current Product custody/permission. Historical completion remains Evidence, not a new live training operation.

## Proposed import contract and unit order

IMC-D freezes a strict `EXISTING_MODEL_IMPORT` receipt branch. Input is exact046-owned historical provenance reconciliation + current model/profile/Consent/rights/license + immutable pair content identity + runtime/format identity + exact import intent and authorized protected destination. It must preserve verified original training/model identities but must not accept/require an invented current083 reservation, TASK-084 training terminal or H3 TRAINING_START. Unverified historical facts remain NOT_CONFIRMED and block import. The exact field/type/nullability tables, parser limits, digest domains/preimages and failure matrix are frozen by `imc-d-existing-model-import-custody-contract-r0.md`; that exact revision must be independently accepted and recorded here before implementation-owner allocation or IMC-I source start.

Private receipt binds `import_intent_id`, `import_revision`, predecessor import digest, producer/task/version identity, model-pair inventory/hash/size, approved model/runtime/license/rights/Consent provenance, exact protected destination and content/physical inventory references, cipher/key/security policy identities, import commit/readback/currentness coordinates and retention/revocation status. Public projection contains bounded opaque references/digests/status only. Body-free fixture receipt is explicitly `FIXTURE_ONLY`, never trusted readback/load authority. Exact fields/digest preimage/schema/mirror/failure matrix must pass independent review before implementation allocation.

IMC-I implements pure contract/fake backend first under its future exact-files scope. IMC-N is separately authorized protected native import/no-clobber encryption+readback: pin source/destination ancestors/objects, reject foreign/reparse/replaced/partial/hash-mismatched pair, admit exact full set, publish atomically with recovery classification, re-read physical custody/currentness. No output path directly under a drive root. UNKNOWN commit leaves evidence and blocks blind retry; no destructive cleanup. Existing private plaintext source is not silently deleted or uploaded.

IMC-L supplies a bounded exact-model/runtime/014/075/Job/ticket/Consent lease for one operation. Trusted child reads via reviewed private handles; no parent plaintext body or reusable generic path token. Fresh time/revocation/custody revalidation before use, one-shot consume, handle closure and explicit ambiguous-consumption recovery. No lease merely from a receipt self-hash. Unauthorized model load stays blocked.

Consumers014/075/100 must accept an explicitly reviewed tagged union: `TRAINING_TERMINAL` from084 versus `EXISTING_MODEL_IMPORT` from101. This outcome uses101 only. Cross-variant issuer/type/digest/fields, copied/rehashed old receipts and unreviewed aliasing are rejected. Do not manufacture terminal training receipts to satisfy a legacy consumer.

## Exit and gates

Exit requires current protected import/readback +046 model approval/binding+current Consent/rights + exact operation lease and corresponding strict consumer tests, native proof and independent DEV-4 review. Test corrupted/partial pair, changed source/destination, privacy leakage, stale/revoked custody/Consent, old runtime, wrong issuer/variant/operation, replay/expiry, crash/UNKNOWN and no-clobber. Model selection/evaluation approval is not issued by101.

This allocation is design-only. Actual import/load/key/DACL/native effects require an exact authorized implementation/native unit and approved storage/retention policy. Training/download/paid/cloud/Asset/Timeline/Export/Release/Deploy/Production remain out of scope. No implicit implementation takeover or third private-effect approval is inferred from the two-connection instruction.

See [delivery plan](../TASK-073/expression-master-wav-delivery-plan-r0.md). TASK-101 replaces084 on the delivery ledger, leaving17 scoped lanes; it is not an eighteenth training dependency.

## IMC-D R0 design authority — 2026-09-29

After accepted TASK-100 LVC-C2-D0 identified TASK-101 custody/readback and a distinct installed-identity observation capability as direct prerequisites, the Owner instructed this voice-integration thread to continue. TASK-101 already assigns this thread as design coordinator. That instruction binds only the design exact2 in [the IMC-D contract](imc-d-existing-model-import-custody-contract-r0.md).

Repository Allowed Files are exactly this Task record and the new design. External Evidence is limited to `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-d-r0\<run-id>\`. No implementation-owner allocation, source/schema/test mutation, WSL/private model read, copy, encryption, key/DACL operation, protected destination creation, lease/capability issuance, model load, inference, Product/Shell integration, Release, Deploy or Production authority is created.

Cycle-1 independent Critic review recorded C/H/M/L `0/1/0/0`: implementation start was not explicitly gated on a separately frozen exact ABI/failure matrix. Recovery R1 freezes those details inside the same exact2 design rather than adding another Task, and makes independent acceptance of this exact design revision a prerequisite to owner allocation and IMC-I source start.

Recovery R1 re-review recorded Critic `0/1/1/0` and Tester `0/1/1/0`. The bounded R2 correction fully specifies the capability-audit constants/types/conditional nullability/timestamp order and makes pre-open, post-open and ambiguous native failure rows mutually exclusive. One final re-review is required; any remaining Critical/High finding escalates rather than starting implementation.

Frozen R2 HEAD `272cbb84d55332c539b327c06fa88a42f19a2b5d` received Critic C/H/M/L `0/0/1/0` and Tester `PASS / ACCEPT`, `0/0/0/0`. The DEV-4 Judge accepted R2 as design because the declared design threshold is Critical/High zero, but imposed an explicit source gate for the real Medium finding: noninitial capability-audit records do not yet require `predecessor.transitioned_at <= transitioned_at`. Accepted R2 design payload SHA-256 is `05df814ba587f57d06bab4fbbbed0ea77046b0de67a77347305a6c8d9cc0748b`.

Acceptance is not implementation allocation. IMC-I owner allocation and every source/schema/test mutation remain blocked until the Owner authorizes a narrow design-only R3 erratum in the same exact2, the monotonic predecessor-time condition is frozen, and independent Critic/Tester/Judge accept the revised design digest.

## IMC-D R3 design erratum authority — 2026-09-29

After the explicit request to authorize a narrow exact-two R3 design erratum, the Owner instructed this thread to proceed. This authorizes only the two IMC-D design records already listed as Allowed Files. It does not authorize IMC-I source/schema/test mutation, implementation-owner allocation, private model access, native execution, import, capability issuance, model load, inference, Product/Shell integration, Release, Deploy or Production use.

R3 closes the sole R2 Medium by requiring every noninitial `ExistingModelImportCapabilityAuditV1` record to satisfy `predecessor.transitioned_at <= transitioned_at`. The predecessor must first pass canonical parse, self-digest and exact-link validation; only then may its timestamp participate in the monotonic comparison. No other ABI, lifecycle, custody or authority rule changes. IMC-I remains blocked until an independent Critic, Tester and DEV-4 Judge accept the frozen R3 revision and its digest is recorded here.

Frozen R3 HEAD `4709b274f37448140cb73fe1af5018e8905d4654` on current base `84d4fa75fa19bb99519dfb97f541dd0b6bfc7147`, with R3 unit commit `9cb5d58b2c3d4c59871e5d804d5809858b259de6`, received independent Critic `ACCEPT` C/H/M/L `0/0/0/0`, Tester `PASS / ACCEPT` C/H/M/L `0/0/0/0`, and DEV-4 Judge `R2_EXPLICIT_IMC_I_SOURCE_GATE_RELEASED` C/H/M/L `0/0/0/0`. Tester normative in-memory time vectors passed `9/9`; code/native tests were not applicable and no native/private effect ran. The accepted pre-record R3 design payload SHA-256 is `23ce20e29d4d92b9b2fe5e9b35eb0941fde0fa40ca3ed3d84e0890d805950208`.

This acceptance releases only the R2 design/ABI source gate. IMC-I still has no implementation owner, exact Allowed Files or source-mutation authority. A separate Owner/canonical allocation must bind the proposed exact five files before implementation starts. IMC-N and every private model read/copy/encryption/key/DACL/destination/capability/load/inference/Product/Shell/Release/Deploy/Production effect remain blocked.

## IMC-I implementation allocation — 2026-10-10

The Owner explicitly approved `TASK-101 IMC-I exact5` after the authority-gate audit. PR #599 already merged accepted R3 to canonical main `53e4f0ea8e219b773a2976ba40b956830ff2e1df`. IMC-I continues TASK-101's unchanged import-custody responsibility; it does not allocate a new capability or reopen final history.

Implementation owner is this TASK-101 voice-integration thread. Repository Allowed Files are exactly:

1. `docs/ai-team/tasks/TASK-101/task.md`
2. `src/ai_video_production/task101_existing_model_import_custody.py`
3. `schemas/task101-existing-model-import-custody.schema.json`
4. `src/ai_video_production/schema_resources/task101-existing-model-import-custody.schema.json`
5. `tests/test_task101_existing_model_import_custody.py`

IMC-I is governed as DEV-4 because it implements a security-sensitive state machine and canonical cross-owner contract. It may implement only strict parsing, exact validation, canonical digests, immutable public records, pure readback/currentness evaluation and an in-memory fake backend. It must remain effect-zero and must not read private audio or model bodies, open filesystem paths, create protected custody, issue a live private capability, load a runtime/model, run inference, call a Provider, download/install anything, connect Product/Shell, or perform Release/Deploy/Production work. IMC-N and IMC-L remain separately gated.

Completion requires exact schema/mirror equality, focused positive/negative/parser/digest/currentness/lifecycle tests, independent Critic and Tester acceptance, DEV-4 Judge closure, exact-five diff/scope validation, and external Evidence write/readback under `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-i\<run-id>\`. Publication is not authorized by this allocation; the unit stops commit-ready unless a separate current publication authority is confirmed.

## IMC-I implementation acceptance — 2026-10-10

IMC-I is accepted as the bounded, effect-zero pure contract/fake-backend unit. The implementation baseline is `53e4f0ea8e219b773a2976ba40b956830ff2e1df`; the frozen reviewed implementation HEAD is `3f67316466718fbe29fac3359c17d441ce17321e`. The three implementation commits are `153be2fbde1659eb94f8a32ced93e6a1aa3a9b9f`, `a405c6132d3fd654aedc305d66826906783ebde3`, and `3f67316466718fbe29fac3359c17d441ce17321e`.

The accepted surface implements strict record parsing, exact field and cross-record validation, canonical domain-separated digests, immutable public records, pure readback/currentness evaluation, the closed section 6.1 native failure classification, one-way capability audit validation, and a non-authoritative in-memory backend whose outputs are explicitly `FIXTURE_ONLY`. It does not open a path, read model bodies, create protected custody, issue a live capability, load a model/runtime, run inference, call a Provider, connect Product/Shell, or perform Release, Deploy, or Production work.

The initial independent review found Critic C/H/M/L `0/3/1/0` and Tester `0/3/0/0`. Recovery R1 closed the audit-chain, receipt-expiry/currentness, fake/live authority and failure-matrix findings; its Critic accepted `0/0/0/0`, while its Tester found two new High issues. Recovery R2 removed the unfrozen readback generation/time sequencing constraints and made `NativeImportFailureClassification` factory-only. The final independent Critic and Tester both accepted R2 at C/H/M/L `0/0/0/0`; the DEV-4 Judge accepted the unit with no unresolved finding after the maximum two bounded fix cycles.

Final local verification is TASK-101 focused `37 / 37 PASS`, TASK-101 plus direct TASK-100/TASK-084 regression `213 / 213 PASS`, compileall `PASS`, `git diff --check` `PASS`, and exact-five scope `PASS`. Independent Tester verification is TASK-101 focused `37 / 37 PASS`, its selected TASK-100/TASK-084 regression `185 / 185 PASS`, bounded prior-High probes `2 / 2 PASS`, effect-zero probe `1 / 1 PASS`, AST/import `PASS`, and exact-five scope `PASS`. The canonical schema and package mirror are byte-identical at SHA-256 `bf319c30c99f7586c272984ed96d0bb737e61cb00e67adcac26c9fcadc764195`.

During final verification, test caches and bytecode were disabled. Compile output was bound to the operation-specific WSL system-temp root `/tmp/bvp-task101-imci-r2-20261010-001/pycache`; it is the only intentional temporary residual. The final public-safe external checkpoint is bound to `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-i\20261010-imc-i-final-001\` and must be written and read back after this completion record is committed.

IMC-I acceptance does not complete TASK-101. IMC-N, IMC-L, private/native import, key/DACL work, protected destination creation, live capability/load/inference, consumer integration, publication, Release, Deploy, and Production remain separately blocked or unallocated. Current `origin/main` advanced to `110d595acd7802d599914823760ed622ac1983c7` after the implementation baseline; its changed paths have zero overlap with the exact-five IMC-I scope. Publication remains unauthorized, so this unit stops commit-ready without push or PR.
