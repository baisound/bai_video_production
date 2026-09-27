# TASK-101 — Existing Owner Model Import Custody

- Status: `DESIGN_ONLY_ALLOCATION / CANONICAL_INTEGRATION_PENDING`.
- Governance: DEV-4 FOUNDATION CRITICAL.
- Design intent: Owner's 2026-09-27 formal remaining-Task/detail-design request; independent Critic requires a separate import entrypoint rather than expanding TASK-084's training-terminal scope.
- Responsibility predecessor/dependency: TASK-084 protected training artifact custody design; its training branches/source/history are preserved, not reopened or aliased.
- Design coordinator: this voice-integration thread / TASK-073. Implementation owner/Allowed Files and native authority are not allocated by the separate Owner takeover of connection TASK-099/100.
- ID101 is unused at baseline main `e41110c8`; serialize canonical metadata allocation with a fresh ID/lock audit.
- Allowed now: this task definition only. No private file read/copy/encryption/load, source/schema/test or external-project change.

## Goal and boundary

Admit an already completed, externally supplied Owner model pair into protected Product custody without new recording, training, fabricated training terminal or TASK-083 reservation. Own **import artifact custody/currentness and one-operation load lease** only. Reuse independently accepted custody/security backend primitives where valid; do not create a second ModelCandidate catalog/store or assume TASK-068 immutable-JSON helpers can write/encrypt binary model trees.

TASK-046 owns verified historical model/Dataset/training lineage, subject/Consent/rights, model evaluation/current H4 and ModelArtifactBinding; TASK-100 owns catalog; TASK-014 owns FineTunedModelBinding/narration; TASK-075 owns inference; TASK-072 owns child authority/containment. A model downloaded/publicly released elsewhere is not current Product custody/permission. Historical completion remains Evidence, not a new live training operation.

## Proposed import contract and unit order

IMC-D freezes a strict `EXISTING_MODEL_IMPORT` receipt branch. Input is exact046-owned historical provenance reconciliation + current model/profile/Consent/rights/license + immutable pair content identity + runtime/format identity + exact import intent and authorized protected destination. It must preserve verified original training/model identities but must not accept/require an invented current083 reservation, TASK-084 training terminal or H3 TRAINING_START. Unverified historical facts remain NOT_CONFIRMED and block import.

Private receipt binds `import_intent_id`, `import_revision`, predecessor import digest, producer/task/version identity, model-pair inventory/hash/size, approved model/runtime/license/rights/Consent provenance, exact protected destination and content/physical inventory references, cipher/key/security policy identities, import commit/readback/currentness coordinates and retention/revocation status. Public projection contains bounded opaque references/digests/status only. Body-free fixture receipt is explicitly `FIXTURE_ONLY`, never trusted readback/load authority. Exact fields/digest preimage/schema/mirror/failure matrix must pass independent review before implementation allocation.

IMC-I implements pure contract/fake backend first under its future exact-files scope. IMC-N is separately authorized protected native import/no-clobber encryption+readback: pin source/destination ancestors/objects, reject foreign/reparse/replaced/partial/hash-mismatched pair, admit exact full set, publish atomically with recovery classification, re-read physical custody/currentness. No output path directly under a drive root. UNKNOWN commit leaves evidence and blocks blind retry; no destructive cleanup. Existing private plaintext source is not silently deleted or uploaded.

IMC-L supplies a bounded exact-model/runtime/014/075/Job/ticket/Consent lease for one operation. Trusted child reads via reviewed private handles; no parent plaintext body or reusable generic path token. Fresh time/revocation/custody revalidation before use, one-shot consume, handle closure and explicit ambiguous-consumption recovery. No lease merely from a receipt self-hash. Unauthorized model load stays blocked.

Consumers014/075/100 must accept an explicitly reviewed tagged union: `TRAINING_TERMINAL` from084 versus `EXISTING_MODEL_IMPORT` from101. This outcome uses101 only. Cross-variant issuer/type/digest/fields, copied/rehashed old receipts and unreviewed aliasing are rejected. Do not manufacture terminal training receipts to satisfy a legacy consumer.

## Exit and gates

Exit requires current protected import/readback +046 model approval/binding+current Consent/rights + exact operation lease and corresponding strict consumer tests, native proof and independent DEV-4 review. Test corrupted/partial pair, changed source/destination, privacy leakage, stale/revoked custody/Consent, old runtime, wrong issuer/variant/operation, replay/expiry, crash/UNKNOWN and no-clobber. Model selection/evaluation approval is not issued by101.

This allocation is design-only. Actual import/load/key/DACL/native effects require an exact authorized implementation/native unit and approved storage/retention policy. Training/download/paid/cloud/Asset/Timeline/Export/Release/Deploy/Production remain out of scope. No implicit implementation takeover or third private-effect approval is inferred from the two-connection instruction.

See [delivery plan](../TASK-073/expression-master-wav-delivery-plan-r0.md). TASK-101 replaces084 on the delivery ledger, leaving17 scoped lanes; it is not an eighteenth training dependency.
