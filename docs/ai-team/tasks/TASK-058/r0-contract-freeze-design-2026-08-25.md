# TASK-058 R0 Montage Learning Bridge Contract Freeze

Date: `2026-08-25`
Profile: `DEV-4 FOUNDATION CRITICAL`
Atomic Unit: `P0 / contract and parser only`
Execution class: `NO_EXTERNAL_OR_MUTABLE_I/O`

## 1. Decision

BAI VIDEO PRODUCTION accepts two structurally separate input lanes and emits
only body-free validation candidates. Neither lane becomes canonical learning
data in P0.

The implementation is deterministic for the same admitted input. It may reuse
TASK-055's deterministic parser, including lazy read-only loading of packaged
immutable schemas through `importlib.resources`. Literal “no filesystem I/O” is
therefore not claimed. External/mutable file reads, writes, network, database,
media, native application, provider, store, and receipt effects are forbidden.

The completion diff contains exactly eight files: seven Builder-owned files
(this task record, this design, two public schemas, two byte-identical packaged
schema mirrors, and one source module) plus one independently authored focused
test file. The Builder may not modify the independent test.

## 2. Exact BVP-native lane

Schema: `montage-exact-evidence-delivery.schema.json`
Message: `BvpMontageExactEvidenceDelivery`
Profile: `bvp-task058-montage-exact-evidence-v1`

The closed outer envelope embeds all three immutable bodies:

- `proposal`
- `approved_plan`
- `human_edit_evidence`

It also carries their top-level digests, one delivery `record_id`, the
`owner_scope_hash`, and closed authority/effect flag objects. Embedded document
identity is established by the three hashes; no self-asserted outer proposal,
plan, or evidence identifier is accepted. Each digest is an
exact lowercase `sha256:<64 hex>` value and must equal the matching embedded
body digest (`proposal_sha256`, `plan_sha256`, or `evidence_sha256`).

The caller must supply `expected_owner_scope_hash`; absence, malformed value,
or mismatch fails closed. No fallback owner scope is inferred. P0 equality is
only an expectation match and is not origin ownership proof. A future P1 caller
may obtain the expected value only from BVP's authenticated current-owner
context, and must revalidate BVP-owned source/project scope before any canonical
admission.

After envelope checks, validation delegates the three bodies to
`admit_montage_human_edit_evidence()`. This reuses TASK-055 schema, digest,
proposal→plan, placement/style/event/music-anchor, and frame-lineage checks.
Success produces only `EXACT_LINEAGE_VERIFIED`,
`OWNER_SCOPE_EXPECTATION_MATCHED_NONAUTHORITATIVE`, and
`REVIEW_REQUIRED`. It is not `ACCEPTED` and does not write a canonical store.

## 3. Generic SKILL lane

Schema: `montage-learning-file-bridge.schema.json`
Outer message: `BvpMontageLearningDelivery`
Outer profile: `bvp-task029-file-bridge-v1`
Payload message: `MontageLearningExport`

The outer field set is exactly the current SKILL contract:

`schema_version`, `message_type`, `contract_profile`, `record_id`,
`learning_sha256`, `canonical_timeline`, `auto_admit_authorized`, `payload`.

`learning_sha256` is recomputed from canonical JSON and must equal
`sha256:<64 hex>`. `canonical_timeline` and `auto_admit_authorized` must each be
the JSON/Python boolean `false`; integer `0` is rejected.

BVP independently revalidates the payload rather than trusting the adapter:

- file-safe `record_id`, non-empty string source/proposal identifiers, and all
  other required MontageLearningExport fields;
- reduced, positive rational timeline FPS;
- string (including empty/whitespace for v1 compatibility) or object
  `style_profile`;
- integer proposal/final frames (including negative source coordinates), frame
  delta consistency, result/status equality, and provenance object;
- exact validation status keys and closed values;
- `privacy.safe_export is true` and `raw_actor_exported is false`;
- `adapter_metadata.canonical_timeline is false`;
- source runtime `PASS` only when `runtime_evidence.executed is true` and at
  least one non-empty `evidence_id` or `report_ref` exists.

Even a fully evidenced source runtime PASS becomes
`SOURCE_PASS_CLAIM_STRUCTURALLY_VALID_NONAUTHORITATIVE`. It does not create
BVP
runtime authority. Every generic result remains `OWNER_SCOPE_UNBOUND` and
`REVIEW_REQUIRED`.

## 4. Privacy rule

All nested mapping/list values are recursively inspected. Keys containing any
of the following case-insensitive substrings fail unless the value is exactly
`[REDACTED]`:

`path`, `filename`, `account`, `player`, `email`, `transcript`, `token`,
`secret`, `password`, `credential`, `username`, `display_name`, `real_name`.

Two typed safe markers are validated separately rather than treated as leaked
values:

- `absolute_host_path_included` must be the boolean `false`;
- `redacted_field_paths` must be an array of non-empty field references.

No other sensitive-key exception is implied.

## 5. Authority and effect closure

The exact envelope's `authority_flags` and `effect_flags` are closed objects.
Every required member must be present, no unknown member is allowed, and every
value must be the boolean `false` (`0` is rejected).

The body-free result repeats only negative authority/effect facts. It never
returns embedded proposal, plan, evidence, actor data, transcript, paths, media,
or provider data.

## 6. Receipt coexistence freeze

The existing connector v1 terminal receipt namespace remains:

`learning-receipts/<record_id>--<learning_sha256_hex>.receipt.json`

It is reserved for the legacy terminal statuses `ACCEPTED`, `DUPLICATE`, and
`REJECTED`.

Any future review-first v2 receipt must use the disjoint namespace:

`learning-receipts/review-required/v2/<record_id>--<source_sha256_hex>.receipt.json`

and must not be interpreted by a v1 terminal receipt reader. The v2 schema,
writer, CAS/recovery behavior, and promotion authority are deliberately not
defined by P0. P0 mints neither receipt version.

## 7. Failure mode

Missing/extra fields, wrong constant/type, malformed or mismatched digest,
owner-scope mismatch, invalid TASK-055 lineage, unreduced FPS, inconsistent
delta/status/provenance, unsafe privacy markers, an unredacted sensitive key,
unsupported validation status, or false-like integer authority flags all raise
`MontageLearningBridgeContractError` before any candidate is returned.

There is no fallback admission, automatic repair, partial success, store write,
or receipt side effect.

## 8. P0 acceptance

- both public and packaged schema mirrors are byte-identical;
- exact positive and tamper/owner-scope/authority negatives pass;
- generic positive and hash/FPS/privacy/runtime/authority negatives pass;
- existing TASK-055 admission regression remains green;
- scope contains exactly eight authorized files, including the one independent
  focused test file;
- independent DEV-4 Tester/Critic/Judge gates have zero unresolved C/H.
