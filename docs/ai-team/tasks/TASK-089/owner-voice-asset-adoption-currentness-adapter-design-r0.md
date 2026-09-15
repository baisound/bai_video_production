# TASK-089 — Owner Voice Asset Adoption and Currentness Adapter R0

Status: `DESIGN_CANDIDATE_R2 / DEV-4 / NONLIVE_ABI / INDEPENDENT_REVIEW_PENDING`

Correction cycle: `2 / 2`. R0/R1 external candidate bytes are immutable. The stable
R0 filename identifies the allocated design unit; R2 is this review candidate.

Design identity: `TASK089-OWNER-VOICE-ASSET-ADOPTION-CURRENTNESS-NONLIVE-V1`

## 1. Binding and outcome

[Task allocation](task.md) binds this exact-two design unit to
`main@5bc090bd515926606cce03d5c01f306ddf1e927c`. Program L0 may run independently
of LB-0. Completed TASK-003 is a dependency; TASK-089 is its allocated successor,
not a reopened historical unit. This design freezes an implementable pure fixture
ABI and its limitations. All production owner ports remain `NOT_BOUND`.

The existing TASK-003 Asset registry is the sole canonical Asset identity/store.
TASK-089 will adapt that boundary, not create a second registry, canonical
selection store, custody system or Dataset. TASK-082 owns encrypted bytes,
generation state and body leases; TASK-088 owns data-preparation Consent;
TASK-047/048 own producer output semantics; TASK-090 owns durable Q2 candidate,
terminal/publication/selection/restart; TASK-046 owns Q3 and H2/Dataset adoption.
A future fixed Product composition remains inside `BAI Video Production.exe`.
No new executable/UI or runtime dependency on BAI Development OS is proposed.

This ABI deliberately uses TASK-089-owned `Fixture` record names. It is not a
wire grammar for existing foreign-owner receipts except the imported TASK-082
V2 custody/event objects explicitly identified below. A fixture digest never
becomes a TASK-003 receipt or a TASK-088/047 Consent. Future live issuer and
consumer amendments must accept an exact successor identity and nominal API;
changing a fixture flag or owner string is forbidden.

## 2. Current source and compatibility facts

At the bound base, `AssetIngestService.ingest(AssetIngestRequest)` accepts a
source path and writes canonical source bytes/registry/manifest state.
`DerivedAssetPublisher.publish` also copies/hashes a path. Neither accepts a
custody-safe metadata adoption capability. Neither may be called by the pure
implementation or fed TASK-082 ciphertext/private plaintext by convention.

`SQLiteProductStore.register_asset` inserts an Asset and version 1; `get_asset`,
`find_asset_by_operation`, `find_asset_by_checksum`, `latest_manifest` and
`find_manifest_by_operation` are reusable existing primitives, not an atomic
owner-voice adoption/currentness port. `AssetRecord` has no version/head digest;
separate reads do not establish a same-snapshot guard. A content checksum,
`sha256(AssetRecord.to_dict())`, latest filename or ordinary-editing
`auto_use_allowed` cannot be promoted into adoption, revision or Consent proof.

The derived publisher returns a same-Job/checksum Asset before checking semantic
role/rights equivalence. In addition to the initial table constraint
`UNIQUE(job_id, logical_uri, checksum)`, `_apply_v2_migration` creates the effective
`uq_assets_job_checksum` UNIQUE index on `(job_id, checksum)` (store.py:593).
Current migrated stores therefore prohibit same-Job/equal-content distinct
Asset rows even if logical URIs differ. Generic ingest and derived publication
also deduplicate by Job/checksum. The current registry and those writers cannot
satisfy distinct processed/training-copy identities for equal bytes.

The NON-LIVE fixture may model that future semantic requirement. It must not
claim the existing store supports it. Live admission fails closed until either
the specific outputs have distinct bytes and all other accepted owner gates are
satisfied, or a separate canonical store/schema/dedup compatibility amendment
explicitly resolves the equal-content case. No automatic migration, removal of
the unique index, changed checksum, cross-Job workaround, or second registry is
authorized. Historical TASK-003 records and current source stay unchanged.

TASK-046 `Task046Q2Q3HandoffFixture` remains synthetic, `NOT_BOUND` and
`PREFLIGHT_BLOCKED`. Its existing distinct-Asset and non-aliasing digest checks
are unchanged. The new fixture grammar permits equal content in different roles,
but never distinct-role receipt/revision identity substitution; there is no
automatic conversion into the older fixture. Versioned downstream compatibility
is required before any consumer uses that distinction.

TASK-082 sources/docs are present at this base. Retained candidate/unmerged text
is historical status evidence, not absence of source and not native proof. Its
matching adoption-digest arguments do not implement a nominal live Asset port.

## 3. Frozen role and purpose matrix

Exactly these four `asset_role` strings exist:

| asset_role | producer_task | producer_output_role | custody write purpose | Consent scope | exact operation |
|---|---|---|---|---|---|
| RAW_CAPTURE | TASK-047 | TASK047_RAW_CAPTURE_OUTPUT | CAPTURE_RAW_PUBLISH | OWNER_VOICE_CAPTURE | CAPTURE_RAW_PUBLISH |
| CANONICAL_PCM | TASK-047 | TASK047_CANONICAL_PCM_OUTPUT | CAPTURE_CANONICAL_PUBLISH | OWNER_VOICE_CAPTURE | CAPTURE_CANONICAL_PUBLISH |
| PROCESSED_SPEECH_CONTINUOUS | TASK-048 | TASK048_SPEECH_CONTINUOUS_OUTPUT | QUALITY_SPEECH_CONTINUOUS_PUBLISH | OWNER_VOICE_DATA_PREPARATION | QUALITY_FINISHING |
| TRAINING_COPY | TASK-048 | TASK048_TRAINING_COPY_OUTPUT | QUALITY_TRAINING_COPY_PUBLISH | OWNER_VOICE_DATA_PREPARATION | TRAINING_COPY_CREATION |

The two capture operation labels here name fixture adoption prerequisites, not a
new TASK-047 Consent ABI. Capture uses its own observed capture authorization;
it does not require TASK-088 Consent already bound to adopted Q1 Assets.
Data-preparation Consent permits the matching processing use, not Asset adoption
by itself. The separate adoption owner capability remains unavailable.

`REVIEW_TRANSCRIPT`, Dataset, model and narration roles are rejected.
TASK-046 never creates, converts, custodies or adopts the Q2 training copy.
Raw source, canonical PCM, processed speech and training copy are separate
semantic roles even when byte hashes coincide.

## 4. Exact encoding and common grammar

The future schema is Draft 2020-12 with
`$id=bai.task089.owner-voice-asset-adoption-currentness.nonlive.v1`.
Its root is a closed `oneOf` over the nine record types in section 5 and the
bundle in section 6. No implicit defaults, extension fields or omitted nullable
keys are allowed. Every object including nested objects has
`additionalProperties=false`; all listed fields are required.

Three distinct validation entry levels are fixed; do not substitute one for
another:

| entry level | accepted variants | excluded variants |
|---|---|---|
| schema document root oneOf | all nine complete S/G/P/CU/R/A/O/E/H record variants, plus Task089FixtureBundleV1 | every unknown discriminator |
| bundle.records item schema | exactly seven input variants S/G/P/CU/R/A/O | E, H, nested bundle and unknown discriminator |
| parse_fixture_bundle public payload | Task089FixtureBundleV1 only, then its seven-variant records rule | every standalone S/G/P/CU/R/A/O/E/H record |

A complete E or H output is valid at the schema document root (and its named
output variant), but is never a bundle item or public parser payload. The parser
requires the bundle discriminator before selecting/validating the bundle schema
variant; standalone record rejection is MALFORMED_FIXTURE. Root schema shape
validity is not full digest/graph validation or eligibility.

Primitive notation:

- `D`: string matching `^sha256:[0-9a-f]{64}$`.
- `N`: exact integer 0..2147483647; booleans and floats are rejected.
- `P`: exact integer 1..2147483647.
- `Token`: `^[a-z][a-z0-9_-]{0,63}$`; no path, whitespace, principal name or
  free prose. Fixture session/case tokens must begin `fixture-`.
- `Project`: canonical `^[a-z][a-z0-9-]{2,63}$`.
- `Job`, `Asset`, `Operation`: existing JOB/ASSET/OP prefixes plus
  26 Crockford characters `[0-9A-HJKMNP-TV-Z]`; no fixture identifier is
  silently translated into a canonical ID.
- `T`: exact UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`, six fractional digits,
  Gregorian-valid year 2000..9999. No offsets/leap seconds or normalization.
- `?X`: X or JSON null, always present.
- `Media`: exact fields `format`, `sample_rate_hz`, `channels`,
  `sample_count`. Format is `PCM_S16LE`, `PCM_S24LE` or `FLOAT32LE`;
  rate is integer 8000..192000; channels 1..8; count 1..1382400000.
  Non-RAW roles require PCM_S24LE/48000/1. This is fixture syntax, not a new
  production training-format choice.

Every section-5 record has common fields `C`:

| field | exact value/type |
|---|---|
| record_type | row-specific literal |
| schema_version | 1 |
| adapter_owner_task | TASK-089 |
| canonical_asset_owner_task | TASK-003 |
| fixture_only | true |
| authority_created | false |
| execution_authorized | false |
| owner_port_contract_status | NOT_BOUND |
| private_media_effect_count | 0 |
| asset_adoption_count | 0 |
| record_sha256 | D |

The canonical owner field identifies the boundary being modeled, not the issuer
of an actual Task-003 receipt. Embedded foreign TASK-082 objects retain their
own unmodified discriminator/owner/digest grammar; C does not apply inside them.

The JSON API accepts only exact `bytes` or exact `str`, not arbitrary Mapping,
Sequence, callback or loader objects. Before traversal: strict UTF-8, at most
1 MiB encoded bytes, no BOM, duplicate keys, NaN/Infinity/floats, invalid
surrogates, control characters in decoded strings, trailing bytes or non-object
root. After parsing: depth at most 20 (root=1), 32768 total JSON nodes,
128 fields/object, 256 entries/array, 4096 UTF-8 bytes/string. Lower field limits
apply. Fail before unbounded recursion/allocation; validate limits while parsing
or use an explicit bounded structural pass. Canonicalization follows existing
`serialization.canonical_json_bytes`: UTF-8, sorted keys, compact separators,
ensure_ascii=false; no Unicode or timestamp rewriting. Integers only.

For record type `K`, compute
`sha256(b"BAI:TASK089:NONLIVE:" + K.encode("ascii") + b":V1" + bytes([0]) + canonical_json_bytes(record_without_record_sha256))`.
Every named digest domain below is its ASCII text followed by exactly one
zero byte (0x00), then the named canonical JSON preimage. Only the record's
own top-level `record_sha256` is excluded; nested digests and every other
field participate. Return `sha256:` plus lowercase hex. Input records must
carry a correct full digest; parsed objects recompute it before every relation
check. Direct construction, copy, pickle, subclass, field mutation or replacing
a digest is never authority. Exported immutable values reject subclass/pickle;
copying a public JSON fixture merely yields another revalidated fixture.

## 5. Exact record families

C plus the listed fields is the complete set for each record. Capital labels
S/G/P/CU/R/A/O/E below are graph labels only, not additional fields.

### 5.1 S — Task089SubjectFixtureV1

`fixture_case:Token`, `project_id:Project`, `production_job_id:Job`,
`project_revision:P`, `owner_subject_revision:P`.

S models one exact Project-to-Job/OwnerSubject readback. Its full digest is
only a synthetic fixture coordinate; actual Project/subject current-readback
issuance is absent. New project/subject coordinates produce a different S.

### 5.2 G — Task089PurposeGrantFixtureV1

`subject_sha256:D`, `scope:enum`, `operation:enum`,
`output_role:asset_role`, `decision:ALLOW|DENY|UNKNOWN`,
`policy_revision:P`, `grant_revision:P`, `issued_at:T`,
`expires_at:T`, `q1_readback_sha256:?D`.

Scope/operation/output-role must be one exact section-3 row. issued < expires.
Capture grants have q1_readback=null. Both Q2 grants require q1_readback pointing
to a canonical-PCM O whose full subgraph is consistent at the bundle observation
time. Its S must equal this S. They cannot reference the output being adopted.
A grant with DENY/UNKNOWN is well formed but cannot produce a consistent
assessment. G is a specimen, never TASK-088/Capture Consent.

### 5.3 P — Task089ProducerOutputFixtureV1

`subject_sha256:D`, `grant_sha256:D`, `producer_task:enum`,
`producer_output_role:enum`, `asset_role:enum`,
`producer_operation_id:Operation`, `output_sequence:P`,
`content_sha256:D`, `media:Media`, `upstream_producer_sha256:?D`,
`q1_readback_sha256:?D`.

Producer labels are exactly section 3; subject/grant/output role join exactly.
RAW has both nullable fields null. CANONICAL requires upstream=RAW P from the
same S, with matching capture scope (a distinct canonical-purpose G), and
q1_readback=null. PROCESSED has upstream=null and q1_readback equal to G's Q1 O.
TRAINING_COPY requires upstream=PROCESSED P from the same S and Q1 O, and
q1_readback equal to G's Q1 O. Q2 producer operations must match each other for
the pair handoff in section 8; Q1 raw/canonical operation equality is not
required. Content hashes are opaque synthetic media checksums: no file is
opened to establish them. They cannot serve as a receipt/revision digest.
P asserts output shape only; it cannot issue TASK-048 quality PASS, sample-map
truth or a TASK-090 terminal.

### 5.4 CU — Task089CustodyFixtureV1

`producer_sha256:D`, `custody_receipt:Task082PrivateMediaCustodyReceiptV2`,
`generation_events:array[1..64] of Task082PrivateMediaGenerationEventV2`.

Import the exact V2 schema/parser grammar from TASK-082 at the bound source IDs
in section 12; do not copy/reimplement its event/currentness semantics.
The new schema references the existing TASK-082 schema's custodyReceipt and
generationEvent definitions through its exact local $id. Validation registers
the pinned canonical/package-resource schema locally; network resolution is
forbidden. Mirror checks include the referenced TASK-082 resource identity.
Validate receipt and every event with the existing pure parser. Recompute their
staged-binding, full receipt and event digests. Derive currentness at the bundle
observation time using all provided events, their exact count, final event hash
and the receipt's staged binding. Require CURRENT for a consistent assessment,
matching current generation, publish event and slot/class. A tombstone, fork,
gap, missing event or nonmatching final head is non-current.

Receipt class/content equal P; purpose equals its row's custody write purpose;
owner_subject_revision_sha256 equals S.record_sha256 and
consent_rights_revision_sha256 equals G.record_sha256 **only inside this synthetic
case**. This deliberately constructs legal TASK-082 specimen bytes; it is not
a conversion of fixture hashes into live subject/Consent authority.
`media_metadata_sha256` equals
`sha256(b"BAI:TASK089:FIXTURE_MEDIA:V1" + bytes([0]) + canonical_json_bytes(P.media))`.
Physical/cipher identity digests are specimen values; they are never opened,
compared to a host object, or represented as verified native identity.

The receipt's source event must occur in the supplied chain; match all
generation/slot/media/staged-binding fields using the TASK-082 owner derivation.
Exactly one event must match receipt.generation_event_sha256, and it must be
GENERATION_PUBLISHED for that receipt. Its generation, artifact ID, slot, class,
purpose, subject/Consent, content/media/opened-physical/cipher identity and staged
binding equal the receipt's corresponding fields. Receipt.event_head_sha256 must
equal that same publish-event digest. Later tombstones in the supplied chain
make the receipt stale; they do not change its original publication identity.

For CONSISTENT_REGISTERED, independently require the receipt's own
`observed_at <= bundle.observed_at < fresh_until`. Owner event-currentness alone
does not satisfy this window; O's window is also a separate condition. Equality
at either expiry and a future-dated receipt yield CURRENTNESS_MISMATCH.

These CURRENT/freshness requirements apply to the CU of an assessed positive-use
R/O root and to each explicitly referenced Q1 positive-use R/O root. A CU present
only through predecessor A ancestry is historical chain evidence: validate its
full shape, digest, joins, publication identity and exact prefix structurally,
but do not assess that old generation as the CURRENT selected generation or
recursively apply its old R/O eligibility. Its supersession is expected and does
not itself stale an otherwise valid successor. If the same historical
O is explicitly referenced as a Q1 positive-use root, that separate use must
still pass currentness; ancestry alone never creates such a use.

This does not relax TASK-082 event-chain rules. Its current derivation checks
every event window in the supplied complete chain, including prefix events.
The staged binding includes observed_at and fresh_until, so a matching receipt
and publication event must have the same window (as well as the other bound
fields). A historical receipt with an expired window therefore also has an
expired prefix publication. That expiry still makes the imported successor
currentness fail and the requested result STALE. A positive next-generation
fixture may supersede a prior generation only while every prefix event window
remains valid under this pinned owner contract. Do not trim history,
refresh an immutable event or bypass that owner check to force success.

Use the owner full receipt digest, not custody_binding_sha256, when identifying
a custody receipt. At most one custody fixture per producer is allowed in a
bundle for a consistent result; a different custody for the same producer is a
modeled conflict, not a parser shape error.

### 5.5 R — Task089AdoptionRequestFixtureV1

`subject_sha256:D`, `producer_sha256:D`, `custody_sha256:D`,
`grant_sha256:D`, `adoption_operation_id:Operation`,
`expected_registry_generation:N`,
`predecessor_registration_sha256:?D`, `semantic_key_sha256:D`.

subject/producer/custody/grant must join exactly. The following closed matrix
applies to the custody generation being adopted, not to the registry generation:

| request case | R.predecessor_registration_sha256 | CU receipt generation / predecessor_receipt_sha256 | required chain binding |
|---|---|---|---|
| first custody generation in a slot | null | 1 / null | first event is publication of this generation at event revision 1 with null predecessor; no earlier publication exists |
| next custody generation in the same slot | exact prior REGISTERED A digest | prior CU receipt generation + 1 / exact prior CU full receipt_sha256 | complete prior CU event list is the byte-identical prefix of the new event list; exactly one new published generation follows that prefix |

Resolve the prior CU through predecessor A -> its R -> that R.custody_sha256;
require predecessor A.asset_snapshot.custody_receipt_sha256 equal that resolved
CU's nested full receipt digest. Comparing only a staged binding, event head or
an unrelated syntactically valid digest is insufficient. TASK-082's current
receipt parser/currentness derivation does not perform this adoption-predecessor
join, so TASK-089 must enforce it in addition to the imported owner checks.

Prior/current R/S/P/CU must have identical Project/Job/asset role/logical custody
slot, subject fixture and purpose-grant fixture. This matches the current
TASK-082 closed slot/event lineage. A changed subject/Consent starts a separate
slot/first-generation fixture, not a silently spliced event chain. The new P
digest and (producer operation, output sequence) pair differ; if its producer
operation is retained, output_sequence strictly increases. Prior A registry
generation is <= R.expected_registry_generation. Overflow rejects.

Compare the canonical JSON bytes of every event in the complete prior CU list,
including event digests; prefix length and order must match exactly. Following
that prefix, permit only an optional valid tombstone for the prior generation,
then the single new generation's publication, then an optional valid tombstone
for the new generation. TASK-082 must validate each transition; an extra
intermediate publication, omitted prefix event, unrelated receipt predecessor,
wrong slot/role/producer, skipped generation or changed prefix rejects as
REFERENCE_MISMATCH. A valid final tombstone is well formed but non-current.
First-generation fixtures may likewise include one valid post-publication
tombstone to exercise the STALE result; they never include another publication.
No terminal of TASK-090 is a field or prerequisite.

Semantic key preimage is the exact R object with C,
adoption_operation_id and semantic_key_sha256 removed. Include all remaining
fields (subject, producer, custody, grant, expected generation, predecessor).
Use domain `BAI:TASK089:FIXTURE_ADOPTION_KEY:V1` with the zero-byte rule above.
This projected key has its own named domain and is never the full R digest.
Changing the adoption operation ID alone retains the key and must cause a
conflict, not a new modeled adoption. Full R digest then includes that key and
the adoption operation ID.

The existing semantic_key is a request/CAS projection, not a complete stable
adoption-intent key: expected_registry_generation participates in its preimage.
Without adding a field or digest domain, define the derived same-output
coordinate of R as the ordered tuple of its exact subject_sha256,
producer_sha256, custody_sha256, grant_sha256 and resolved P.asset_role.
Compare those five values by exact equality after all normal joins validate;
do not substitute content hashes, staged custody binding or a logical slot.
Adoption operation, expected registry generation and predecessor registration
are not part of this derived coordinate. They remain fully validated R fields
and remain in their existing full/key digests as already specified.

All supplied R records with an equal same-output coordinate are contenders,
even when both adoption operation and expected registry generation differ.
Section 6 includes them and their supplied A results in the fixed-point closure.
Two or more distinct REGISTERED A records whose requests share this coordinate
always yield CONFLICT / SEMANTIC_CONFLICT, irrespective of operation, CAS
expectation, Asset ID or URI differences. Existing same-request and semantic-key
conflict rules also still apply. A legitimate later custody generation has a
different P and CU under the predecessor matrix, so it does not share this
coordinate and is not a replay conflict merely because its slot/role matches.
The module sees only supplied fixtures: one isolated attempt cannot reveal an
omitted prior attempt. No persistent journal, duplicate-write prevention or
live adoption proof is claimed by this bounded classifier.

### 5.6 A — Task089RegistrationFixtureV1

`request_sha256:D`, `outcome:REGISTERED|REJECTED_NO_WRITE|COMPLETION_UNKNOWN`,
`registry_generation:N`, `asset_snapshot:?AssetSnapshot`.

AssetSnapshot's exact fields:
`asset_id:Asset`, `production_job_id:Job`, `asset_type:"AUDIO"`,
`asset_role:asset_role`, `logical_uri:string`, `checksum:D`,
`asset_version:P`, `producer_operation_id:Operation`,
`custody_receipt_sha256:D`.

For REGISTERED: snapshot is nonnull; registry generation equals R.expected+1
and must not overflow N; version=1; Job/role/checksum match R's P/S.
AssetSnapshot.producer_operation_id equals R.adoption_operation_id, preserving
the canonical registry's operation-to-Asset recovery coordinate. P separately
retains the originating capture/quality producer operation; the two operation
roles must not be relabelled. Custody receipt digest is the nested TASK-082 full
receipt digest.
logical_uri is exactly
`asset://{production_job_id}/owner-voice/{asset_role_lowercase}/{asset_id}`
with no extension/query/fragment/escape. It is a **fixture proposed logical
coordinate**, never passed to a resolver. A live metadata/custody bridge must
separately accept its storage mapping; existing plaintext ingest is not that
bridge. For a consistent result, new asset_id/logical_uri differ from a
predecessor and every different role's REGISTERED snapshot in the bundle.
Colliding semantic identities are modeled CONFLICT, not shape failures.

For REJECTED_NO_WRITE: snapshot=null, registry generation=R.expected.
For COMPLETION_UNKNOWN: snapshot=null, registry generation is either R.expected
or R.expected+1; neither asserts absence/success or permits replay. This is an
unknown modeled observation, not a canonical store journal.

A is the sole fixture registration result for its request. Multiple differing A
records for one request, or two REGISTERED records for the same semantic key,
or multiple REGISTERED A records for the same derived same-output coordinate
across distinct requests, are a modeled conflict. Exact duplicate bytes are represented once; duplicate record
entries in a bundle are rejected. Re-assessing the same bundle returns the
same result, without mutating or appending anything.

### 5.7 O — Task089CurrentReadbackFixtureV1

`request_sha256:D`, `registration_sha256:?D`,
`observation_kind:SNAPSHOT|NO_WRITE|UNRESOLVED|UNAVAILABLE|RESTARTED`,
`observed_subject_sha256:?D`, `observed_grant_sha256:?D`,
`observed_registry_generation:?N`, `selected_asset_id:?Asset`,
`selected_registration_sha256:?D`, `observed_custody_sha256:?D`,
`fixture_session:Token`, `observed_at:T`, `fresh_until:T`.

The nullable fields have these exact closed arms. In every row, request is a
present R digest; fixture_session, observed_at and fresh_until remain required.

| observation_kind | registration_sha256 | observed_subject / observed_grant / observed_custody | observed_registry_generation | selected_asset_id / selected_registration_sha256 | referenced A outcome |
|---|---|---|---|---|---|
| SNAPSHOT | D | D / D / D | N | Asset / D | REGISTERED for both referenced A records |
| NO_WRITE | D | D / D / D | N | null / null | REJECTED_NO_WRITE |
| UNRESOLVED | D | null / null / null | N | null / null | COMPLETION_UNKNOWN |
| UNAVAILABLE | null | null / null / null | null | null / null | no A is asserted by O |
| RESTARTED | null | null / null / null | null | null / null | no A is asserted by O |

Only the A referenced by O.registration_sha256 must have A.request equal to
O.request. This equality does not apply to O.selected_registration_sha256.
For SNAPSHOT, subject/grant/custody reference S/G/CU respectively. Selected A may
differ from requested A and reference its own older R to model stale selection.
Validate that selected A's own complete R/S/G/P/CU ancestry and all its ordinary
joins; it must be REGISTERED and have the same exact S, Project/Job/asset role/
logical custody slot as the requested R. Do not replace its own R with O.request
or require its own P/CU digests to equal the current output's P/CU digests.
For a selected A whose own R differs from O.request, that A must be a strict
ancestor reached by following the current R.predecessor_registration_sha256
chain transitively through each ancestor A's own R. Every edge satisfies the
section-5.5 predecessor matrix. Same role/slot alone cannot admit a foreign
lineage; a non-ancestor selection is REFERENCE_MISMATCH. A distinct selected A
for the same O.request is permitted structurally only as a same-request
conflicting result, reaching CONFLICT before STALE; it is not a prior generation.
Observed generation equals selected A.registry_generation
and selected Asset ID equals its snapshot Asset ID. For NO_WRITE, observed S/G/CU
equal R's exact inputs and observed generation equals A.registry_generation
(therefore R.expected). There is no Asset or selected-registration reference,
so an isolated first attempt that writes nothing needs no fabricated Asset.
For UNRESOLVED, observed generation equals A.registry_generation: R.expected or
R.expected+1 as specified by A. This reports uncertainty, not a registry write
or a selected Asset. Cross-arm fields, wrong A outcome or inconsistent numeric
generation fail validation rather than being coerced to null/success.

With different requested and selected A, different own R records, valid distinct
custody generations/producer outputs, and no conflict contender, the SNAPSHOT is
well formed and reaches STALE / CURRENTNESS_MISMATCH. A different A for the same
requested R instead remains CONFLICT at section 7 row 1. An older selected A
is a structural observation, not an extra positive-use R/O root; do not demand
that its generation still be selected CURRENT or synthesize an older O.

For every arm, observed_at < fresh_until is a shape invariant. Session and
bundle-time freshness are assessed in section 7. UNKNOWN arms do not imply a
trusted/current observation. NO_WRITE reports an observed rejected operation;
it cannot issue a positive adoption/currentness result even with a valid window.

A consistent current fixture requires SNAPSHOT, REGISTERED A, selected A equals
registration, requested R equals A.request and O.request, selected Asset equals
A snapshot, observed subject/grant/custody equal R's exact inputs, session equals
bundle.fixture_session, and observed <= bundle.observed_at < fresh_until.
Grant issued <= observed <= bundle.observed_at < grant expiry; CU receipt's own
observed_at <= bundle.observed_at < fresh_until and owner event chain must both
be current. O, G, receipt and events have independent validity windows; equality
at any expiry rejects positive currentness. Fixture timestamps do not invoke a
clock or establish trusted time.

Registry generation is explicitly a modeled coherent snapshot coordinate; no
claim is made that current SQLite exposes this counter/ABI. Real coherent
readback/version selection must be designed over the existing owner store
before any live acceptance. O is neither persisted by this module nor a second
canonical selection store.

### 5.8 E — Task089AdoptionAssessmentFixtureV1

`request_sha256:D`, `readback_sha256:D`, `registration_sha256:?D`,
`fixture_state:CONSISTENT_REGISTERED|NOT_READY|STALE|UNKNOWN|CONFLICT`,
`reason_code:enum`, `guard_status:"UNAVAILABLE"`,
`required_owner_contracts:array`.

The required_owner_contracts array is exactly
`["CANONICAL_ASSET","PRIVATE_CUSTODY","PURPOSE_CONSENT","OWNER_SUBJECT"]`.
This is a declaration list, **not** an acquisition order. Production acquisition
order belongs to the accepted TASK-088 aggregate-fence contract.

E is generated only by assessment; it is not accepted among bundle input records.
Its exact state/reason pairs and precedence appear in section 7. Even
CONSISTENT_REGISTERED has C's adoption count 0 and unavailable live guard.

### 5.9 H — Task089Q2PairHandoffFixtureV1

`subject_sha256:D`, `q1_readback_sha256:D`,
`q2_producer_operation_id:Operation`,
`processed_request_sha256:D`, `processed_readback_sha256:D`,
`copy_request_sha256:D`, `copy_readback_sha256:D`,
`processed_assessment_sha256:D`, `copy_assessment_sha256:D`,
`consumer_owner_task:"TASK-090"`, `terminal_binding_status:"NOT_BOUND"`.

H is an output only. Both assessments must be CONSISTENT_REGISTERED over the
same bundle, observation time/session/S and Q1 canonical O. Their R/P/A/CU roles
must be processed versus copy, with distinct Asset IDs, logical URIs, P/CU/R/A/O
full digests and TASK-082 custody receipt identities. Content checksums may
coincide. Copy P.upstream_producer must equal processed P; both producer
operations equal q2_producer_operation_id. Their grants may differ because
operations/output roles differ, but bind the same S/Q1 and current policy
revision. H records these distinct grants transitively; it cannot collapse them
into one fake Consent. H does not contain or issue a Q2 terminal. TASK-090's
accepted producer/quality/Consent/transaction protocol remains a separate gate.

## 6. Bundle, references and public API

`Task089FixtureBundleV1` has exactly:
`record_type:"Task089FixtureBundleV1"`, `schema_version:1`,
`fixture_case:Token`, `fixture_session:Token`, `observed_at:T`,
`records:array[1..256]`, `fixture_only:true`,
`authority_created:false`, `execution_authorized:false`,
`owner_port_contract_status:"NOT_BOUND"`, `bundle_sha256:D`.

records contains only S/G/P/CU/R/A/O, each with C. Bundle digest domain is
`BAI:TASK089:NONLIVE:Task089FixtureBundleV1:V1` plus the zero byte; exclude only its own
bundle_sha256. Input array order is significant for hashing, but it cannot
affect relation results; the validator resolves by full digest. Reject duplicate
full digests, unknown reference, wrong referenced type, cross-case S, reverse
cycles or more than 256 records. Every S.fixture_case equals bundle.fixture_case.
Assessment starts from the requested O/R pair (or two pairs for H), follows all
references including predecessors, Q1 subgraphs, selected observations and
producer lineage, and expands the closure with contenders as follows. For every
reached R, include all supplied R records sharing either its semantic key or
its section-5.5 same-output coordinate, and all supplied A records whose request
is any reached R. Also include contenders sharing an A request, a CU producer,
or an Asset ID/logical URI with reached records. Follow every newly included
record's ordinary outgoing references and repeat the same contender expansion.
Expansion repeats to a fixed point within the 256-record bound. Records outside
that closure are rejected as REFERENCE_MISMATCH at assessment, not parse time.
This permits explicit conflicting sibling records to reach the CONFLICT arm.
Do not reverse-follow A to every O that observes it. A contender's unreferenced
old O is still surplus unless reached by an explicit reference or public root.
No filesystem/lookup is used to resolve a missing digest.

Reachability roots are part of the API call, not extra serialized fields.
Single assessment uses one O/R pair. Pair construction validates the union
closure of both O/R pairs once, then evaluates both roots and their Q1
dependencies internally against that already validated union. It must not call
the public single-root assessment on the complete pair bundle, which would
correctly reject the other pair's records as surplus. Likewise recursive Q1
evaluation does not reapply a single-root orphan check to its enclosing bundle.
Different standalone operations use the segmented minimal bundles in section 8.

Content hashes may equal other content hashes. A content hash must not equal a
top-level record digest, semantic key, imported full custody/event digest or
staged custody binding. Those are different typed domains; equality is rejected
as REFERENCE_MISMATCH rather than inferred equivalence.

Positive tests compute opaque content/physical/cipher leaf digests from distinct
explicit synthetic byte literals in the test, never unexplained repeated-zero
placeholders. These bytes are not audio or a host identity. Every record and
internal cross-edge, including imported custody/event digests, is recomputed
from complete supplied fixture content in causal order.

Exact future public API:

- `parse_fixture_bundle(payload: bytes | str) -> Task089FixtureBundle`
- `assess_adoption_fixture(bundle: Task089FixtureBundle, *, request_sha256: str, readback_sha256: str) -> Task089AdoptionAssessment`
- `build_q2_pair_handoff_fixture(bundle: Task089FixtureBundle, *, processed_request_sha256: str, processed_readback_sha256: str, copy_request_sha256: str, copy_readback_sha256: str) -> Task089Q2PairHandoff`

The three returned classes expose only `to_dict()` returning a detached exact
built-in tree and immutable properties matching the documented fields. They
are nominal final classes, not runtime-checkable Protocols or dependency
injection seams. Construction remains internal; every API revalidates exact
class, full canonical bytes/digests and relations. Reject subclasses, forged
internal state and restoration without invoking attacker-defined methods.
No public callback/backend/path/store/clock/guard/lease parameter or effectful
factory exists. Errors are `Task089ContractError` with one constant code from
`MALFORMED_FIXTURE`, `REFERENCE_MISMATCH`, `CYCLIC_FIXTURE`,
`ROLE_MISMATCH`, `PAIR_MISMATCH`; no input text/exception details.

No extra builder API is required: focused tests construct dictionaries in
causal order and compute the fully specified hashes using independent helpers.
E/H are serialized public outputs; their dedicated schema variants validate them,
but parse_fixture_bundle accepts only the bundle discriminator.

### 6.1 Decoder, schema and semantic responsibilities

Apply these stages in order; schema validity alone never establishes digest,
foreign-owner truth, referential integrity, currentness or fixture eligibility:

1. Strict decoder: exact bytes/str input, encoding, duplicate-key detection,
   scalar exclusions and bounded size/depth/node traversal from section 4.
   No file/network schema discovery. Failure is MALFORMED_FIXTURE.
2. Local JSON Schema: discriminator/common constants, exact required fields,
   scalar formats/ranges, closed section-3 role unions, Media limits, A's
   outcome-dependent snapshot nullability, O's five null/type arms, section-4
   schema document root nine-record-plus-bundle union, bundle.records seven
   input variants excluding E/H, public parser's bundle-only selection, and
   imported TASK-082 structural schema.
   Schema checks only locally expressible conditions. Failure is
   MALFORMED_FIXTURE; date calendar validity and all cross-record conditions
   are additionally required by the semantic validator.
3. Semantic graph validation: Gregorian/time interval checks; recompute every
   own/embedded digest; invoke imported owner record parsers; index full
   digests; reject duplicate/unknown/wrong-type references and cycles; apply
   role/field joins, R's first/next custody predecessor and event-prefix matrix,
   A's numeric/operation relations and O's referenced-outcome/generation joins.
   Bad digest/record encoding is MALFORMED_FIXTURE; broken references/joins are
   REFERENCE_MISMATCH, wrong section-3 role is ROLE_MISMATCH, cycles are
   CYCLIC_FIXTURE. Whole-bundle graph validation is parse_fixture_bundle's
   responsibility, and is rechecked on API ingress. No foreign runtime is called.
4. Root-scoped assessment: apply exact single/dual root closure and conflict
   expansion, reject surplus, then section 7 eligibility precedence. Custody
   currentness and all positive-use validity windows are assessed here using
   the imported pure owner derivation plus TASK-089's extra relations. A valid
   tombstone/expired observation is STALE, not malformed. Conflicting siblings
   specifically allowed by section 5 reach CONFLICT. Pair construction applies
   the same internal assessment to each root and then section 5.9's pair joins;
   any non-consistent pair or pair mismatch raises PAIR_MISMATCH, returning no H.

Keep a structural visited set separate from the positive-use root set. Walking
R.predecessor_registration_sha256 includes historical A/R/CU/P/G/S for validation
and closure; it does not recursively assess the predecessor as a current root.
Only requested R/O roots and their explicit Q1 readback dependencies receive
the section-7 eligibility evaluation. For example, a generation-1 predecessor
superseded by a structurally exact generation-2 chain with fresh current CU/R/O
and all prefix event windows still valid remains eligible for
CONSISTENT_REGISTERED. An expired predecessor window instead remains STALE due
to the unchanged TASK-082 complete-chain rule, not a historical-R/O assessment.
Both the historical event prefix and current successor publication must still
be accepted by the imported owner structural/event-chain checks.

These responsibilities also delimit test claims: schema shape PASS, strict
decoder PASS, semantic graph PASS and fixture eligibility are recorded
separately. None is a production/current-owner PASS.

## 7. Assessment order and modeled state transitions

First perform shape/digest/reference/role/causal validation. Invalid shape,
broken joins declared invariant in section 5, wrong type or cycle raise the
fixed exception; they never become a positive or partial result. Validation
then deterministically selects the first matching row below. State classification
is a pure result, not a mutation of A, O or any owner store.

| precedence | condition | fixture_state / reason_code |
|---|---|---|
| 1 | semantic key reused by different request operation, differing results for one request, multiple REGISTERED results sharing the derived same-output coordinate across requests/CAS expectations, conflicting Asset identity or custody-per-producer | CONFLICT / SEMANTIC_CONFLICT |
| 2 | O is RESTARTED or session differs | UNKNOWN / SESSION_NOT_CURRENT |
| 3 | O is UNAVAILABLE or UNRESOLVED (the latter binds A outcome COMPLETION_UNKNOWN) | UNKNOWN / OUTCOME_UNKNOWN |
| 4 | O.observed_at > bundle.observed_at or bundle.observed_at >= O.fresh_until | STALE / CURRENTNESS_MISMATCH |
| 5 | G decision DENY or UNKNOWN | NOT_READY / PURPOSE_NOT_ALLOWED |
| 6 | O is NO_WRITE (binds A outcome REJECTED_NO_WRITE) | NOT_READY / REGISTRATION_REJECTED |
| 7 | SNAPSHOT selects another A, subject/grant/custody drift, G/receipt/event positive-use window fails, or owner custody non-current | STALE / CURRENTNESS_MISMATCH |
| 8 | SNAPSHOT and every section-5 consistency requirement hold | CONSISTENT_REGISTERED / FIXTURE_RELATIONS_MATCH |

registration_sha256 in E is O.registration_sha256, including null for UNAVAILABLE
and RESTARTED. NO_WRITE and UNRESOLVED retain their exact A reference without an
Asset/selection. With fresh matching session/time and ALLOW G, an isolated
first-attempt rejected A reaches row 6; it needs no prior REGISTERED A. Both
permitted unknown registry generations reach row 3, asserting neither success
nor absence. NO_WRITE may truthfully report rejection without satisfying
positive-use G/receipt/event freshness; it still cannot authorize use. Missing
grant/producer/reference is an invalid graph, not a new runtime fact.

No retry transition rewrites an old result. A changed bundle/session/time is a
new observation, not a revived capability. UNKNOWN never implies no effect.
Exact duplicate assessment is deterministic read-only re-evaluation; a new
random adoption operation cannot evade the semantic conflict rule.
Changing the expected registry generation as well cannot evade same-output
REGISTERED contender classification when both attempts are supplied. Closure
and conflict results are input-order independent; neither rule invents missing
history when only one attempt is supplied.
The future live registry operation must have a separately accepted durable
reservation/burn/CAS/reconciliation contract; no such journal is implemented
or claimed here.

## 8. Acyclic construction and downstream boundary

First construct S, capture G_RAW/P_RAW, then G_CAN/P_CAN. P_CAN references P_RAW;
neither capture G references any Q1 Asset/readback. Build each needed custody
specimen in TASK-082 staged-binding -> publication event -> full receipt order,
then CU -> R -> A -> O. Q2 G references the already-constructed O_CAN; build
G_PROC/P_PROC then G_COPY/P_COPY (P_COPY references P_PROC), their custody and
R/A/O outputs. Compute all own hashes only after complete upstream objects.

Use separate **minimal bundles**, not one accumulating batch. Labels in this
table denote record instances; every array entry is still one of the exact
section-5 types. No root/manifest field is added to the grammar.

| API case | exact first-generation input record set | count |
|---|---|---|
| RAW single assessment | S, G_RAW, P_RAW, CU_RAW, R_RAW, A_RAW, O_RAW | 7 |
| canonical single assessment | S, G_RAW, P_RAW, G_CAN, P_CAN, CU_CAN, R_CAN, A_CAN, O_CAN | 9 |
| processed single assessment | canonical set plus G_PROC, P_PROC, CU_PROC, R_PROC, A_PROC, O_PROC | 15 |
| copy single assessment | canonical set plus G_PROC, P_PROC, G_COPY, P_COPY, CU_COPY, R_COPY, A_COPY, O_COPY | 17 |
| Q2 pair construction | canonical set plus G_PROC, P_PROC, CU_PROC, R_PROC, A_PROC, O_PROC, G_COPY, P_COPY, CU_COPY, R_COPY, A_COPY, O_COPY | 21 |

The RAW adoption CU/R/A/O is a standalone assessment; P_CAN depends only on
P_RAW. Those four raw adoption records therefore must not be carried into the
canonical/Q2 bundles. Adding them is an orphan error, not presumed lineage.
The copy-only case needs processed producer G/P but not its adoption result;
H requires both complete adoption/readback subgraphs in the 21-record union.
The pair builder computes the two E outputs after dual-root closure validation;
H references the resulting complete E digests. E and H are never bundle inputs.
UNAVAILABLE/RESTARTED RAW uses the same RAW set without A_RAW (6 records) and
O's null arm. NO_WRITE/UNRESOLVED RAW keeps A_RAW (7 records), with its matching
outcome and no fabricated Asset snapshot. Contender expansion remains explicit
for negative conflict cases; unrelated surplus is always rejected.

For later-generation adoption include predecessor A and precisely its transitive
R/CU/P/G/S ancestry; include earlier O only when another explicit field references
it. The new CU embeds the exact prior event prefix and new publication, and its
full receipt predecessor equals that prior CU's full receipt digest. This
extends the acyclic closure without retaining unreferenced historical outputs.
References flow only to constructed upstream records.
Request R does not include A/O/E/H; A includes R, never O; O includes A/R;
E includes O/R/A; H includes earlier E and upstream references. Bundle hash
wraps the complete input list; none of those inputs reference its hash.
Q2 G -> Q1 O is an earlier-stage edge, not a same-generation back-edge.
The future Q2 terminal is downstream of H/adoption and cannot be required to
construct P, CU, R or A.

Current fixture logic does not pass H to existing TASK-046/TASK-082 live methods.
TASK-090 design may use H as non-live dependency evidence, then add its own
independently accepted quality, candidate, publication, current-selection and
restart contracts. Q3 remains blocked until those exact live boundaries and
the TASK-088 compound consumer are accepted and current.

## 9. Live-owner gap and future guard contract

These are implementation prerequisites for a separately scoped live successor,
not permission prompts blocking the pure ABI:

- accepted registry metadata adoption into the existing Asset store without a
  parallel private-body copy, with legitimate logical URI mapping and distinct
  semantic roles under dedup; no generic derived publisher bypass. Current
  schema-v2 UNIQUE(job_id, checksum) makes equal-content distinct-Asset adoption
  unavailable. That live case remains fail-closed until a separately scoped
  canonical store/schema/dedup compatibility amendment is accepted; no migration
  or unique-index change is part of the pure exact-four;
- canonical Project/Job and Asset/version/operation/manifest same-snapshot
  readback; exact compare token and role/rights binding, not fixture integers;
- explicit successor issuer acceptance by TASK-088's TASK-003-named port,
  TASK-082 custody consumers and TASK-090; no owner/digest alias;
- fixed authenticated authority ingress for capture/adoption and TASK-088
  processing Consent; each actual record obtained from its owning interface;
- owner acquire/revalidate/release protocol holding a nonserializable,
  session-bound guard for the exact heads across the linearization seam;
  public hashes, a token constructor, protocol instance or Python module
  sentinel cannot create it;
- aggregate fence order from accepted TASK-088, reverse release on partial
  failure, no positive result after head/session/time drift;
- durable one-use reservation/CAS/result reconciliation over the existing owner
  persistence boundary, current custody/rights/Consent/trusted-time readback and
  exact restart/lost-reply outcomes; unknown state preserves artifacts;
- no direct source path, caller-supplied clock/backend, deletion, purge,
  repair, body lease or native capability from this pure adapter.

TASK-082 write/publish occurs before adoption; its read lease for Q2/Q3 may
require the resulting genuine Asset readback. These are different operation
phases, avoiding a custody/adoption cycle. Consent revoke/expiry blocks future
use through its owners but never implicitly deletes or revokes an Asset here.

## 10. Negative/fault and independent acceptance matrix

| test group | exact required cases / evidence |
|---|---|
| WIRE | every unknown/missing field and invalid null arm; schema-root S/G/P/CU/R/A/O/E/H/bundle shape positives; public parser rejects every standalone record including E/H, accepting only bundle; bundle.records rejects E/H/nested bundle while seven input types remain allowed; all five O arms against schema and strict parser separately; cross-reference/outcome checks against the semantic validator; duplicate nested keys; BOM/UTF-8/surrogate/control/trailing; bool-as-int/float/NaN; each size/depth bound; exact mirror bytes |
| DIGEST | recompute every own digest with an independent helper; mutate each field/edge; staged-vs-full-custody alias; content-as-revision/key-as-record substitution; wrong domain/version; complete first/later-generation graphs without placeholder self/cross digests |
| ROLE | all four positive role cases; every cross-row producer/Consent/purpose/class; transcript/Dataset/model rejection; raw-native vs canonical-format mismatch; capture G's nonnull Q1 cycle rejected |
| IDENTITY | wrong Project/Job/S/grant/policy/Q1 lineage/producer operation/slot/generation/Asset/version; equal bytes in two roles require distinct semantic identities; equal identity with different content/role is CONFLICT |
| CUSTODY | full imported owner parser/event derivation plus exact predecessor-A -> R -> CU full receipt link; generation1/null and next-generation/exact-prefix positives; successor positive with superseded predecessor as structural ancestry and all prefix event windows fresh, without assessing old R/O; expired predecessor publication remains STALE under unchanged owner complete-chain rules; explicit expired Q1 readback still fails; wrong syntactically-valid predecessor (even if TASK-082 alone accepts it), staged/full alias, wrong slot/producer, skipped generation, changed/truncated/reordered prefix and extra intermediate publish rejection; valid tombstone on assessed current generation is STALE; no physical open or lease issuance |
| CURRENT | isolated first-attempt NO_WRITE with A REJECTED_NO_WRITE, no Asset and expected generation -> REGISTRATION_REJECTED; UNRESOLVED at expected and expected+1 -> OUTCOME_UNKNOWN without Asset/write claim; UNAVAILABLE/RESTARTED null arms; current R/A with legitimate prior-generation selected A -> own ancestor R/P/CU/G joins and STALE, not a same-output replay; distinct same-request A -> CONFLICT; different-S/role/slot or non-ancestor selected A -> REFERENCE_MISMATCH; exact selection joins and S/G/CU drift; independently expire/future-date O, G, custody receipt and event windows; equality at any positive-use expiry rejects; no clock read |
| REPLAY | identical bundle assessment stable; request ID replacement retains key and conflicts; same S/G/P/CU/role, expected=0/op1/A1 REGISTERED versus expected=1/op2/A2 REGISTERED -> fixed-point inclusion and SEMANTIC_CONFLICT in both input orders using shared S/G/P/CU, both R/A and only root O; same operation with changed expected generation and two REGISTERED results also conflicts; omitted prior attempt cannot be inferred; add unreferenced old O -> surplus REFERENCE_MISMATCH; legitimate next-generation distinct P/CU with predecessor A remains consistent; duplicate input record rejected; conflicting same-request result; conflicting custody for producer; UNKNOWN cannot become registered by same-result rewrite |
| PAIR | exact 7/9/15/17/21-record minimal closures; add raw CU/R/A/O to canonical or Q2 and reject surplus; dual-root validation permits both pair branches while standalone single-root assessment rejects the other branch; recursively evaluate Q1 without resetting closure; processed/copy roles, Q1/S/policy/producer-operation match; content-equal pair is non-live only and incompatible with current store's UNIQUE(job_id,checksum); existing TASK-046 fixture remains unchanged |
| NO_EFFECT | import/parser/assessment/H produce zero file/SQLite/network/process/clock/lease/ingest/publication calls; no mutable global canonical state; all outputs C invariants and guard UNAVAILABLE; no public runtime loader, path or backend injection |
| PRIVACY | only fixed codes for hostile objects/errors; detached immutable output; no principal/filename/path/body/fingerprint/secret fields; pickle/subclass/forged instance/state-rewind rejected before user hooks |
| COMPAT | relevant TASK-003/Asset store and TASK-082/TASK-046 fixture regression; no changed legacy schemas, dedup behavior, history or consumer flags; no automatic bridge from H |
| DESIGN | exact source correspondence and DAG/field-arm closure; independent Critic/Tester/Judge C/H=0; at most two ordinary correction cycles; immutable candidate and external readback |

No actual Product/native tests are run by this documentation unit. Future pure
tests use generated in-memory metadata only; no real audio/database/guard
fixtures. Required source-no-effect checks may use subprocess isolation of
imports with effectful APIs forbidden, but no Product runtime is launched.
Any test outputs/caches use an exact Task/run-contained allowed root or approved
unique system temp; no drive-root artifact.

## 11. Future exact-four implementation and review gates

Proposed, not active under this documentation allocation:

1. `src/ai_video_production/task089_owner_voice_asset_adoption_currentness.py`
2. `schemas/task089-owner-voice-asset-adoption-currentness.schema.json`
3. `src/ai_video_production/schema_resources/task089-owner-voice-asset-adoption-currentness.schema.json`
4. `tests/test_task089_owner_voice_asset_adoption_currentness.py`

The module may use standard-library pure parsing/hash/dataclass/enum helpers,
existing pure serialization/ID validation and TASK-082 pure parsers/currentness.
It must not import the Windows custody backend or construct a store/resolver/
ingest/publisher. No TASK-088 source dependency is presumed present at base.
Its accepted design is the contract input; live consumer wiring is separate.

Independent design acceptance freezes this non-live exact-four scope. The
captain then binds a fresh base/worktree/ownership/output-root implementation
unit under the standing program. No extra acknowledgement is required for
already eligible internal work. Source implementation, publication and live
owner integration are not performed by this bootstrap.

Builder candidate status is REVIEW_PENDING. This document never self-awards
independent Critic/Tester/Judge PASS. Required L0 design and pure implementation
completion may unblock TASK-090 design/pure work only through the program's
L0 DONE predicate. R0 design alone does not complete the pure implementation or
dispatch L1. No such completion establishes live adoption or Q2/Q3 execution;
the later live-owner integration predicates remain separate.

## 12. Primary source identities and minimal resumption

At base `5bc090bd515926606cce03d5c01f306ddf1e927c`, these immutable Git blob
IDs identify implementation/contract inputs (SHA-1 Git object IDs, not raw
SHA-256 digests):

| exact repository-relative path | Git blob |
|---|---|
| docs/ai-team/tasks/TASK-003/task.md | 335bd9ed12c1c8b3e6c2449b099a77202b692dd6 |
| src/ai_video_production/assets.py | 7fd5340923c4844bed6eeef8c8e92ef409ef49ff |
| src/ai_video_production/store.py | b458448d1fb09465e8867fdfb5a5046e610c6ee0 |
| src/ai_video_production/ingest.py | 77a16061484c1a7fa27e401e162b36e65d09a110 |
| src/ai_video_production/derived_assets.py | c477e467fd696bff2250b401a1e96222c55d3ce9 |
| schemas/asset-record.schema.json | d6016ed2eec9e00c3bd828f7466fa3ea55c78f61 |
| tests/test_task003_asset_ingest.py | 7a5df5bd0d77321bcbd4c087150db8d1e708aa2e |
| src/ai_video_production/task046_q2_q3_handoff_contract.py | d91201de43c8891ccc0f01da518f708358dd16e4 |
| docs/ai-team/tasks/TASK-046/p0v-production-dependency-and-preserved-asset-rebind-r1-2026-09-03.md | 4b2ee0f98e54174bbec06ffbb0c186656dc5b87a |
| docs/ai-team/tasks/TASK-048/p0v-quality-finishing-preserved-rebind-r1-2026-09-03.md | 4aafaab9edcc5119d95537a3c2eff8932d67772c |
| docs/ai-team/tasks/TASK-082/task.md | 8c67152566bae551db8538fde675515c2bc767ae |
| docs/ai-team/tasks/TASK-082/voice-pipeline-execution-order.md | e83c5adbe1d21c4bb558147f7a408b0ccdaa07f9 |
| src/ai_video_production/task082_owner_voice_private_media_custody.py | 001beb34c699d48609b3aa32d9ebff2974feb266 |
| schemas/task082-owner-voice-private-media-custody.schema.json | 63348d75be5fb54c7754277659784188e4d6375b |

Accepted TASK-088 R4
`owner-voice-data-preparation-consent-live-binding-design-r0.md` raw SHA-256:
`a873681d41411889c1c1eb76243ceba6cd5e80931bf65c628c645a419d71755f`.
Its sections 3, 5.6 and 8.1 preserve owner/guard ordering. The separate pure
ports proposal was inspected at raw SHA-256
`5392bfe421e729341ba6c11fb997f571acea73103d4c74fcda13bfabfd4277e0`;
its TASK-003-named declarations remain non-live and are not silently rewritten.

TASK-046 external accepted R8 design raw SHA-256:
`c6ec946e206003c854f3a870a92ba8d15a9897ee715f20f5df4f2ad330ca3645`.
It reserves later Dataset adoption and the missing Q1/Q2 Asset/current-readback
dependency. Its embedded semantic-review digest is a different identity.

On resume read task.md, this design, the exact external allocation/program and
frozen review/checkpoint; verify HEAD/scope/hashes. Only then read the exact
owner source/API needed for the next bounded unit. Do not reopen completed
TASK-003 history, consume foreign dirty candidate bytes or infer live success.
