# TASK-109 Owner Voice Preparation Consent ABI R0

## 1. Identity and boundary

[TASK-109](task.md) freezes new semantic owner `TASK-109`, ABI `TASK109_OWNER_VOICE_PREPARATION_CONSENT_V1`, integer version `1`. This is original effect-zero design, not implementation or an installed issuer. TASK-105 is accepted reconciliation dependency, not reopened. `NO_ADOPTION / NO_ABI_ALIAS` forbids copying or relabeling TASK-088 records/source.

Purposes, in canonical order: `QUALITY_FINISHING`, `TRAINING_COPY_CREATION`, `TRANSCRIPT_DERIVATION`, `DATASET_CANDIDATE_PROPOSAL`. No capture, Asset/Dataset adoption, training, model import/load, inference, playback, export or deletion permission follows. Each downstream effect needs its own current owner approvals and private custody capability. A copy is not training approval; a proposal is not Dataset adoption.

Consent is an existing canonical Product Project's selected domain child, not a second Project selector/Asset registry/Dataset catalog. Intended entrypoint is existing `BAI Video Production.exe` through later TASK-036 composition; no new EXE/service. TASK-102 owns protected mutation, 109 Consent meaning. Pure implementation has no I/O/live factory.

## 2. Source-bound dependencies

Base main `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04`; TASK-105 PR609 merged. Frozen105 text is historical, not a claim publication is still pending.

| Owner | Retained boundary / outstanding adapter requirement |
| --- | --- |
| 046 | Authenticated current subject/scope/rights; Dataset/model approvals separate. No proxy approval. |
| 071 | Dedicated Human issue/revoke. Existing V1 four preference/connector actions do not include Consent. |
| 072 | Authenticated dispatch/consume/containment. No missing Task directory implies free ID. 074's proposed profiles do not prove installed support. |
| 074 | Trusted time/floor/boot/session. Its design section5.6 still names043 floor transaction: future use requires accepted102 migration, never legacy direct floor writes. |
| 043/099 | Canonical Project grammar/currentness, not Consent semantics. Job-currentness is not Consent-currentness. |
| 102 | Sole protected writer, closed routes, witnesses/query. Current project_save enrolled participant branch rejects with ERR_PMST_ENROLLED_PARTICIPANT_ADAPTER_REQUIRED. |
| 003/089 | Canonical Asset registry/adoption. 089 pure source exists despite stale task wording, not proof of live availability. |
| 048/090 | Quality/terminal ownership;090 BOUND_VERIFIED is structural, not authenticated live currentness. |
| 082 | Body custody/lease; bodies/paths never enter this ABI. |
| 101 | Existing-model import remains separate; neither granted nor prerequisite here. |

Foreign adapters below are requirements, not changes to their wire ABI. Each must be accepted by its owner and validate native records with its owner's parser plus authenticated current reader. Foreign native readiness remains NOT_CONFIRMED. A digest or schema-valid projection never supplies authenticity.

## 3. Strict grammar and hashing

All serialized records are body-free internal audit/fixture data, never capabilities. Only C109_PUBLIC_STATUS is approved for unrestricted public projection; other records stay in the protected owner boundary because canonical Project IDs and linkable commitments can be sensitive. Exact keys; duplicate/missing/unknown keys at every depth rejected. UTF-8 no BOM/trailing data; root object; raw maximum65536 bytes, depth8(root=1), total members/elements2048, strings ASCII maximum128 bytes unless tighter below. No floats/nonfinite numbers/bool-as-int/coercion, free text, paths, display names, OS errors, raw foreign records or extension dictionaries. J below is the only canonical identifier exception to opaque I; it does not permit arbitrary display text.

| Type | Exact rule |
| --- | --- |
| D | string `^sha256:[0-9a-f]{64}$` |
| I | opaque random ID `^c109_[0-9a-f]{32}$`; not a foreign user/name/path |
| J | canonical Product Project ID string `^[a-z][a-z0-9-]{2,63}$`, exactly schemas/product-project-manifest.schema.json project_id; no109 alias |
| N | integer0..9007199254740991 |
| R | integer1..9007199254740991; overflow blocks |
| T | calendar-valid Gregorian UTC string YYYY-MM-DDTHH:mm:ss.ffffffZ, year0001..9999; no leap second/offset/alternate precision |
| F | literal JSON false |
| P | array1..4 unique section1 purposes in listed order |
| X? | required key, X or explicit null only under stated predicate |

Canonical JSON C: lexicographically sorted ASCII keys, no whitespace; shortest decimal integers, no negative zero; lowercase booleans/null; printable ASCII emitted literally except quote/backslash escaped; control bytes use lowercase `\u00xx`. Slash unescaped. Raw whitespace/escape variants allowed within limits, but duplicate detection before canonicalization. Values are ASCII, no Unicode normalization. Arrays retain specified order.

Every top-level record has exactly common fields plus its own fields: `owner_task="TASK-109"`, `abi="TASK109_OWNER_VOICE_PREPARATION_CONSENT_V1"`, `version=1`, `record_type=K`, `authority_created=F`, `record_sha256=D`. K is one section5 type. Hash is `sha256:` + lowercase hex SHA256 of `ASCII("BAI:TASK-109:"+K+":V1") || 0x00 || C(record excluding only record_sha256)`. Common fields/nulls/array order included; nested fields have no implicit self-hash. Validate types before accepting digest. Self-hash means representation integrity, not authority.

Semantic key uses the same prefixed SHA256 output over `ASCII("BAI:TASK-109:CONSENT-KEY:V1") || 0x00 || C({project_id,subject_ref,scope_ref})`, exactly project_id:J,subject_ref:I,scope_ref:I. Opaque subject/scope aliases must be privately bound by accepted046 adapter to actual immutable subject/input-set identities. No caller assertion binds aliases. Scope changes require new scope/decision. One selected lifecycle per key; no second grant for the same key. Cross-key consumers must name the exact grant and input commitment, never search for any matching permission.

## 4. Closed embedded types

All objects have exactly listed fields.

| Type | Fields |
| --- | --- |
| Project | project_id:J, generation:R, manifest_sha256:D |
| Head | tag=ABSENT,event_sha256:null,revision:0 OR tag=SELECTED,event_sha256:D,revision:R |
| Rights | subject_ref:I,scope_ref:I,scope_sha256:D,rights_sha256:D,owner_readback_sha256:D |
| Time | observation_sha256:D,floor_revision:R,floor_sha256:D,boot_session_sha256:D,observed_tick:N,deadline_tick:N,utc:T |
| Dependencies | subject_rights:Rights,time:Time,binding_set_sha256:D,project_reader_sha256:D |
| Coord | revision:R,state_sha256:D |
| Consumer | consumer_id:I,operation_id:I,plan_sha256:D,purpose:(one section1 value),state:(RESERVED/IN_FLIGHT/STOP_PENDING/TERMINAL),terminal_sha256:D? |

Time ticks are microseconds in one boot/session; 0 < deadline-observed <=60000000. Authenticated074 supplies every field, floor/currentness and audit UTC. Public UTC never acts as clock; accepted074 policy must prove UTC-selected expiry. Changed/unavailable floor or boot invalidates observation. No109 extrapolation/caller time. Floor writes complete before request freeze. Fresh observation replaces no frozen request.

binding_set commits fixed Product/install/build/policy and accepted046/071/072/074/099/102 adapter versions. Wire fields never select an adapter. project_reader names authenticated pinned Project observation, not mere manifest hash. Physical handles/user/session identity remain private.

Project maps exactly to the already parsed canonical manifest's project_id,project_revision,project_manifest_sha256 (generation is the project_revision, not a new counter). Values beyond R are unavailable to109,never truncated. The authenticated Project adapter preserves this identity; no prefix rewrite or rehash creates a different Project.

Consumer terminal digest nonnull iff TERMINAL, otherwise null. Terminal requires authenticated consumer owner proof of never-started or stopped/completed with no continuing body/effect authority, not timeout/UI closure/process disappearance. Arrays max64, sorted by consumer_id ASCII, unique consumer_id and operation_id. Capacity exhaustion blocks, never evicts active consumers.

## 5. Record families and conditional invariants

### C109_REQUEST

Fields: operation_id:I,consent_id:I,semantic_key_sha256:D,action:(ISSUE/REVOKE),project:Project,expected_head:Head,expected_coord:Coord?,dependencies:Dependencies,purposes:P,valid_until:T,request_deadline:T.

ISSUE: ABSENT head,null coord,fresh consent ID. REVOKE: selected ACTIVE head,exact OPEN coord; consent/key/subject/scope/purposes/valid_until equal immutable selected grant. Recompute key. ISSUE requires time.utc < valid_until <= time.utc+30days. Both require time.utc < request_deadline <= time.utc+60seconds. Revoke valid_until can already be past; expiry may win. No scope/purpose widening or extension. V1 rejects replacement after terminal; a later separately approved version/migration is required, never erase history.

### C109_RESERVATION

Fields: operation_id:I,request_sha256:D,consent_id:I,project:Project,expected_head:Head,revision:R,predecessor_sha256:D?,state:(RESERVED/HUMAN_CONSUMED/COMMIT_KNOWN/NOT_COMMITTED_PROVEN/UNKNOWN),human_result_sha256:D?,pmst_witness_sha256:D?.

Initial revision1,predecessor null,RESERVED,both result digests null. Later increment1/link predecessor, preserve operation/request/consent/project/head. RESERVED->HUMAN_CONSUMED requires CONSUMED Human digest,witness null. RESERVED/HUMAN_CONSUMED->NOT_COMMITTED_PROVEN requires authenticated exhaustive no-effect102 witness, preserving Human digest if consumed. HUMAN_CONSUMED->COMMIT_KNOWN requires both digests. Nonterminal->UNKNOWN preserves known Human digest,witness optional; UNKNOWN->HUMAN_CONSUMED/COMMIT_KNOWN/NOT_COMMITTED_PROVEN requires authenticated exact reconciliation and corresponding fields; UNKNOWN->UNKNOWN may append knowledge. Terminals have no outgoing edge. Known commit never downgraded by later read failure; read failure is a separate readback. No equal-revision replacement.

Reservation is proposed protected102 non-selector state, not side-file writer and does not advance Project. Admission checks nonterminal key fence even before a child exists. Lost reply cannot allocate a second reservation/new ID. Human broker also deduplicates key+operation+request.

### C109_HUMAN_RESULT

Fields: operation_id:I,request_sha256:D,reservation_sha256:D,action:(ISSUE/REVOKE),action_code:(OWNER_VOICE_PREPARATION_CONSENT_ISSUE_V1/OWNER_VOICE_PREPARATION_CONSENT_REVOKE_V1 respectively),result:(CONSUMED/DENIED/EXPIRED/BURNED/UNKNOWN),owner071_sha256:D?,owner072_sha256:D?,observed_time:Time.

CONSUMED requires both owner digests; other known outcomes require071 digest,072 optional; UNKNOWN permits either null. Only authenticated owner observations produce this projection; serialized result cannot mint authority. Only CONSUMED permits issue/revoke. Exception burns budget; missing proof UNKNOWN. No result for automatic expiry. Retirement plus a new explicit Human decision is required for a new request; never automatically re-prompt.

### C109_EVENT

Fields: consent_id:I,semantic_key_sha256:D,revision:R,predecessor_sha256:D?,phase:(ACTIVE/REVOKE_PENDING/EXPIRY_PENDING/REVOKED/EXPIRED),operation_id:I,request_sha256:D?,human_result_sha256:D?,project_before:Project,subject_rights:Rights,purposes:P,issued_at:T,valid_until:T,transition_time:Time,closed_coord_sha256:D?.

ACTIVE: revision1,predecessor null,issue request and CONSUMED Human digests nonnull,closed_coord null; issued_at=transition_time.utc < valid_until,valid_until equals request. All later events increment1/exact-link, preserve consent/key/Rights/purposes/issued_at/valid_until. Current rights are separately revalidated, never grant-edited. REVOKE_PENDING follows ACTIVE with revoke request+CONSUMED Human; EXPIRY_PENDING follows ACTIVE with request/human null and trusted expiry proof; both closed_coord null. REVOKED follows REVOKE_PENDING, EXPIRED follows EXPIRY_PENDING, preserve pending operation/request/human, closed_coord nonnull naming exact CLOSED coordination. No other edges,terminal immutable.

Transition UTC nondecreasing; same-session ticks nondecreasing. Cross-session recovery needs074 proof, not comparison of unrelated ticks. project_before is exact actual predecessor manifest of selecting transaction; constant Project ID,resulting generation+1. Event never contains own selecting-manifest digest, descendant proof/readback or own hash. Revoke/expiry semantic operation is fresh,not issue operation; finalization reuses pending operation as semantic parent with separate102 transaction,never reconsumes Human.

### C109_COORDINATION

Fields: consent_id:I,revision:R,predecessor_sha256:D?,grant_event_sha256:D,state:(OPEN/PENDING/CLOSED),winner_operation_id:I?,pending_event_sha256:D?,consumers:(Consumer array).

Initial revision1,null predecessor,OPEN,null winner/pending,empty consumers,grant_event ACTIVE. Later increment1/link,preserve grant. OPEN->OPEN registers/transitions/removes terminal consumers only under current ACTIVE guard; immutable operation evidence retains removed terminals. OPEN->PENDING chooses one winner and pending event even for empty consumers. PENDING preserves winner/pending and frozen IDs/plans/purposes; only settling states, no addition/removal. PENDING->CLOSED requires all TERMINAL (empty allowed but never skips PENDING). CLOSED terminal. Consumer transitions RESERVED->IN_FLIGHT or TERMINAL; IN_FLIGHT->STOP_PENDING or TERMINAL; STOP_PENDING->TERMINAL; TERMINAL immutable. Unknown keeps slot nonterminal and admission closed. Coordination is broker-protected non-selector,never alternate Consent head.

At EVERY revision, OPEN requires winner_operation_id=null AND pending_event_sha256=null; PENDING and CLOSED require both nonnull. CLOSED preserves exactly the preceding PENDING winner,pending event,grant,consent and consumer set. Every existing consumer preserves consumer_id,operation_id,plan_sha256,purpose across every state edge; only state and its predicate-governed terminal digest change. OPEN->PENDING preserves the entire OPEN consumer array at the CAS linearization point; no simultaneous addition,removal or state change. A newly added OPEN consumer starts RESERVED with terminal=null. Removed terminal IDs/operations remain spent in immutable operation evidence and cannot be registered again. Thus the empty winner and terminal close are not nullable/identity loopholes.

### C109_COMMIT_PROOF

Fields: operation_id:I,transaction_id:I,event_sha256:D,project_before:Project,project_after:Project,pmst_witness_sha256:D,participant_terminal_sha256:D,outcome=COMMITTED_DURABLE.

Same Project ID; after.generation=before+1; event.project_before equals before; event.operation equals operation. For ACTIVE/REVOKE_PENDING/EXPIRY_PENDING the exact authenticated witness must prove stage SELECT and proof publication uses stage PROOF. For REVOKED/EXPIRED it must prove FINAL_SELECT and publication uses FINAL_PROOF. transaction_id is the selected stage's ID,never the publication stage's ID. Each witness/participant terminal must bind that same operation+stage+transaction+event+Project pair; a stage mismatch is rejected. Publish durably outside attested manifest after event+manifest. No proof for absence/no-commit. Lost publication -> UNKNOWN while retaining known commit; digest alone no live proof.

### C109_READBACK

Fields: read_id:I,consent_id:I,semantic_key_sha256:D,project:Project?,head:Head?,coord:Coord?,dependencies:Dependencies?,commit_proof_sha256:D?,status:(CURRENT/ABSENT/PENDING/REVOKED/EXPIRED/STALE/UNKNOWN/UNBOUND),reason:(section10),retry_allowed:F.

CURRENT: all five nullable fields nonnull,selected ACTIVE,OPEN coord,matching proof/fresh dependencies,reason OK. ABSENT: Project+ABSENT Head+Dependencies nonnull,coord/proof null,authenticated absence/no nonterminal key reservation,reason OK. PENDING: all fields nonnull,selected pending event/exact PENDING or CLOSED coord and pending proof,reason REVOCATION_PENDING/EXPIRY_PENDING matching phase. REVOKED/EXPIRED: all nonnull,selected matching terminal/CLOSED coord/final proof,reason REVOKED/EXPIRED respectively. STALE: all five null,reason DEPENDENCY_STALE. UNKNOWN: all five null,reason OUTCOME_UNKNOWN or TIME_UNAVAILABLE. UNBOUND: all five null,reason DEPENDENCY_UNBOUND. No other tuple. A missing/corrupt selected object never means ABSENT.

Positive observations require one authenticated guarded interval joining current manifest,selected event,proof,coordination and dependencies. Proof.project_after may be an ancestor of current Project only with authenticated child-preserving transitions/current selection,not scan/hash equality. Current readback names actual current generation,never an old proof's generation by assumption. Final readback cannot mix pending Pp with terminal event at P2. A public readback is not reusable freshness authority.

### C109_PUBLIC_STATUS

Fields: operation_id:I,status:(FIXTURE_ONLY/BLOCKED/PENDING/COMMITTED/NOT_COMMITTED/UNKNOWN),reason:(section10),event_sha256:D?,proof_sha256:D?,retry_allowed:F,live_capability_available:F.

FIXTURE_ONLY: reason FIXTURE_ONLY,both digests null. BLOCKED: reason DEPENDENCY_UNBOUND/DEPENDENCY_STALE/INPUT_INVALID/HUMAN_NOT_CONSUMED/TIME_UNAVAILABLE,both null. PENDING: reason REVOCATION_PENDING/EXPIRY_PENDING,both nonnull. COMMITTED: reason OK,both nonnull. NOT_COMMITTED: reason NO_COMMIT_PROVEN,both null. UNKNOWN: reason OUTCOME_UNKNOWN,both null. No other tuple. COMMITTED means historical commit,not CURRENT. UNKNOWN read does not erase protected COMMIT_KNOWN. Invalid requests may return local fixed INPUT_INVALID before any record; do not fabricate live operation ID.

### Normative cross-record joins (all required before graph acceptance)

Resolve references by exact record_sha256 and record_type,validate each referenced object and predecessor chain first; no missing object is treated as null/absence. Pure validation proves these equalities only,never native authenticity. Every identity/hash comparison below is exact; PROJECT means the whole three-field Project object unless project_id is explicitly named.

| Relation | Required equalities and predicates |
| --- | --- |
| Request -> reservation | reservation.request_sha256=request.record_sha256; operation_id,consent_id,project,expected_head equal. Unique semantic key fence derives from that exact request,not a caller-supplied parallel key. |
| Reservation -> Human -> consumed reservation | Human.reservation_sha256 names the initial revision1 RESERVED record (not its future consumed successor); Human.request_sha256/action/operation equal request and initial reservation. Correct action_code for action. HUMAN_CONSUMED reservation.human_result_sha256 resolves to this same CONSUMED Human. All later records preserve this binding. No reference to a descendant reservation,so no digest cycle. |
| ISSUE request -> ACTIVE event | event.request_sha256=request.record_sha256; event.human_result_sha256 equals consumed reservation.human_result_sha256; exact operation_id,consent_id,semantic_key_sha256,purposes,valid_until equality; event.project_before=request.project; event.subject_rights=request.dependencies.subject_rights (all five fields). Request.action=ISSUE and Head ABSENT. Recompute event key using event Project ID and Rights subject/scope. |
| REVOKE request -> pending event | action REVOKE; request.expected_head exactly identifies predecessor ACTIVE event hash/revision; expected_coord resolves to selected OPEN coord for that same grant. Event operation/request/Human equal its revoke chain,project_before=request.project. Request consent/key/subject/scope/scope_sha256/purposes/valid_until equal predecessor grant; event preserves entire predecessor Rights. A fresh046 readback in revoke request may differ only in rights_sha256/owner_readback_sha256: it is reduction evidence,never a widened event. |
| EXPIRY -> pending event | no request/Human exists; exact predecessor ACTIVE and selected OPEN coord,authenticated074 observation proves expiry for this exact grant.valid_until. Bind fresh semantic operation to that grant/key in the accepted102 expiry stage mapping; no fabricated Human reservation. |
| Pending -> final event | exact predecessor pending hash/revision; consent,key,operation,request,Human,Rights,purposes,issued_at,valid_until unchanged; closed_coord resolves to CLOSED for this grant,whose pending_event is that predecessor and winner equals pending operation. Project before is the fresh authenticated selected-pending predecessor manifest,not an arbitrary same-ID Project. |
| Coordination -> grant/pending | consent equals ACTIVE grant.consent; grant_event resolves ACTIVE. Nonnull pending_event resolves pending of this same grant with predecessor_sha256=grant hash; winner_operation_id=pending.operation_id. Each consumer purpose belongs to grant.purposes and its authenticated plan/input scope exactly matches grant scope; cannot switch plan/operation at an edge. |
| Readback -> selected objects | readback consent/key equal selected event; head.event_sha256/revision equal event; Project actually selects that head; coord hash/revision resolve to that grant's coordination; proof.event_sha256 equals selected event and proof satisfies exact stage rules above. Current046 subject/scope/scope_sha256 equal grant and CURRENT requires its rights commitment still current; time/binding/Project reader are fresh for this observation. ABSENT key is recomputed from Project+Dependencies and absence is proven for that key; supplied consent_id is a proposed unused identity,not proof of absence. |
| Public status -> event/proof | any nonnull digests resolve to matching event and proof,whose operation_id equals public operation. PENDING requires pending phase and matching reason; COMMITTED allows ACTIVE or terminal phase only. No cross-operation receipt substitution. |

For ISSUE and REVOKE, fresh time at Human consume and at SELECT must prove request.time.utc <= observed UTC < request_deadline and observed tick < frozen Time.deadline_tick in the SAME boot/session; accepted074 validates clock/floor relations. ACTIVE commit also requires current UTC < valid_until. event.transition_time represents that fresh SELECT observation (not an arbitrary supplied date); Human.observed_time is the actual consume observation with Human UTC <= event UTC. A floor/security/head change after freeze rejects instead of re-signing or silently refreshing the request. Terminal settling/finalization may occur after request expiry or restart only under separately accepted same-operation recovery/current-time proof; it never reuses expired Human authority for a new pending selection. History records retain their authentic old times even if no longer currently usable.

## 6. Acyclic ordering and generation rules

Future issue: accepted binding -> reconcile time floor -> pin P0/ABSENT/key fence -> immutable request -> protected non-selector reservation -> dedicated071/072 consume -> revalidate P0/head/rights/time/binding -> ACTIVE E1 plus initial OPEN coord -> accepted102 participant/manifest SELECT at P1 -> durable witness/participant terminals -> proof W1 outside P1 -> fresh guarded read. No CURRENT until E1/P1/coord/W1 agree. Selected event without coord is UNKNOWN,not usable.

Semantic operation and physical transaction differ. Fixed stages RESERVE,SELECT,PROOF,FINAL_SELECT,FINAL_PROOF,COORD_CAS each get a unique broker-issued transaction ID persisted against operation+stage before dispatch. Reconciliation uses exact mapping,never another ID for retry. Repeated coord stages use monotonic ordinal and exact predecessor; same ordinal/different bytes rejected. Mapping storage belongs to accepted102 profile. A RESERVE/PROOF witness cannot prove SELECT.

Revoke: request against ACTIVE P0/coord -> reservation -> consume -> revalidate -> fenced participant transaction creates pending Ep and PENDING coord and selects Ep at Pp -> proof Wp. Admission stays CLOSED across all seams. Ep contains no successor-coord digest,coord references Ep: no cycle. Partial publication remains UNKNOWN and never reopens new use. Concurrent revoke/expiry/consumer-register serialized by same protected CAS; one pending winner. Loser does not invent another Human consume.

Expiry: authenticated074 proves now>=valid_until -> same pending/settlement/final pipeline,without Human. Detection blocks new use even before persistence; unavailable/rollback time also blocks but cannot claim proven expiry. Explicit revoke is a reduction and may proceed with stale positive-use rights if exact identity/current grant/security are proven. Otherwise fence and UNKNOWN,not fictitious success.

After Pp/Wp: settle every frozen consumer -> append CLOSED C1 -> final E2 binding C1 and actual preceding Project -> select at P2 -> W2 outside P2 -> final current R2 joining E2/C1/W2 at P2 or proved child-preserving successor. E2 never references W2/R2/P2. CLOSED before E2 still blocks use. Empty set still requires PENDING winner,CLOSED,final event. Unknown consumer can remain pending indefinitely; deadline never proves stopped.

Before-consume head movement rejects. After-consume/before-SELECT movement burns/retires via exact outcome,never rewrites request. During settlement,unrelated Project advance allowed only by fresh authenticated proof that same pending event/key/winner remains selected; FINAL_SELECT binds actual predecessor. Otherwise UNKNOWN. No rollback after commit.

## 7. Private admission, Human and time

Future071 amendment needs the two dedicated codes, Japanese Product-owned purpose/input-set/validity review and explicit deny/cancel. Bind exact request,key,operation/reservation,Project/head/coord,scope/purposes/validity and fixed policy. No caller text/bool/token. Existing five-minute challenge and <=60-second verified-to-consume ceilings remain floors; stricter frozen request and Time deadline also apply. A request expiring during review closes,not automatic re-prompt.

Proposed072 profiles: task109.consent.issue, task109.consent.revoke, task109.consent.expire, task109.consent.reconcile, task109.consent.read. First two need matching071 consume; expiry needs trusted time; read/query never write. Recovery mutation needs separately accepted102 same-operation continuation authority. These profiles are not registered by this design.

Future private ConsentGuard is nominal/nonserializable/process-session-bound,budget1,only fixed accepted Product composition may construct it from authenticated owner ports. No public constructor/from_dict/pickle/clone/schema-to-live conversion. Bind read_id,current Project/head/coord,consumer operation/plan/purpose,input scope,rights,time,build/version/policy. At registration/dispatch atomically burn budget and revalidate under same102 exclusion as pending transition; no check/use race. Exception burns while preserving unknown consumer state. Closing guard does not prove effect stopped. Body operations require separate owner capability.

Restart burns all live guards; durable JSON supports reconciliation only,never reconstruction. Unknown in-flight consumer must reach authenticated containment/terminal before new dispatch. Stale subject/rights,time expiry,binding/session change or pending grant stops new admission and invokes accepted consumer fencing,with terminal evidence required. No rollback of completed derivatives or automatic purge promised. Future074 adapter must freeze a native trusted clock contract compatible with these bounded projections before native allocation.

## 8. TASK-102 amendment requirements — not implemented

Proposed logical profiles TASK109_RESERVATION_V1,TASK109_COORDINATION_V1,TASK109_EVENT_SELECT_V1,TASK109_PROOF_V1,TASK109_RECOVERY_QUERY_V1 map only through owner-accepted closed operations/targets/participant validators. No current registry entries are implied.

Required child key is owner_voice_preparation_consent_v1 under existing manifest,with bounded key-to-head map,immutable events and broker-only coordination/journals/proofs. Physical paths,child container schema,capacity/compaction,ACL/locking and protected stage mapping belong to future102/043 amendment; they are not guessed or implemented by pure event ABI. Without their acceptance no native writer exists. No arbitrary path/callback/SQL/bytes sink,second selector,user-writable fallback or dual journal.

Owner must prove reservation preserves P0,per-key serialization,initial/pending coord+manifest participants,shared consumer exclusion,complete stage/commit/abort/reconcile receipts,proof publication while generic admission barrier remains closed without deadlock,exact stage queries,known-commit monotonicity,all writer/lock migrations including time floor,physical identity and no rollback. Generic PMST does not alone prove this. Enrollment/service downtime must not enable old direct writes. The future pure exact6 does not implement child-container or protected profiles.

## 9. Compatibility and recovery

Reject TASK-088 records/bare hex/asset: aliases,089 fixture IDs and090 structural hashes as109. No stripping prefix,issuer retagging/rehash or same-version widening. Old evidence immutable; V1 has no import/migration endpoint. Future bridge requires new reviewed version/owner acceptance and fresh Human/currentness,not inherited historical permission.

Recovery queries exact operation/request/stage. Missing file/reply or102 WITNESS_NOT_FOUND alone after admitted request is UNKNOWN,not no-commit. Exhaustive authenticated retirement must prove all participant effects and SELECT absent before NOT_COMMITTED_PROVEN. Human burn is never refunded. Child-only,manifest-only,coord-only or missing proof retains evidence/barrier and reconciles forward; no orphan adoption/delete/scan-latest/blind retry/new ID. Known COMMIT_KNOWN remains even when current read fails.

## 10. Failure matrix and validation

Closed reasons: OK,FIXTURE_ONLY,INPUT_INVALID,DEPENDENCY_UNBOUND,DEPENDENCY_STALE,HUMAN_NOT_CONSUMED,TIME_UNAVAILABLE,REVOCATION_PENDING,EXPIRY_PENDING,REVOKED,EXPIRED,NO_COMMIT_PROVEN,OUTCOME_UNKNOWN. Per-record subsets above are normative. Never echo secret input.

| Required future vector | Expected boundary |
| --- | --- |
| Duplicate/unknown/missing key,bool-int,float,invalid/null variant,date/precision,each bound/bound+1 | INPUT_INVALID,zero dispatch |
| Wrong issuer/version/domain,rehash,old alias,wrong semantic key | Reject,no authenticity inference |
| Narrow request/widened ACTIVE purposes;foreign operation's CONSUMED;scope/Project/reservation substitution | Reject every broken normative join even when each self-hash is valid |
| Canonical Project ID vs c109 alias;OPEN with winner;CLOSED losing winner/consumer plan | Canonical J accepted,alias and invalid coordination tuples rejected |
| Terminal proof with SELECT witness or ACTIVE proof with FINAL_SELECT | Reject stage/transaction mapping mismatch |
| All record roundtrips,digest field mutations,null vs missing,whitespace variants | Structural fixture only |
| Missing owner adapter or foreign build/session | UNBOUND,no effect |
| Head/coord drift before vs after consume | No consume before;burn/reconcile after,no request rewriting |
| Denied/expired/exception/replay/concurrent consume | No reused Human budget |
| Caller time/rollback/floor unavailable/boot change/forward jump | No extension or fabricated expiry |
| Trusted expiry exactly at equality vs one microsecond before | Equality blocks use;trusted proof selects expiry pipeline |
| Lost replies at reservation/Human/stage/child/manifest/proof | Exact query,preserve knowledge,barrier closed |
| SELECT absent but participant outcome unknown | UNKNOWN,not no-effect |
| Revoke/expiry/registration race | One CAS winner,closed frozen set |
| Empty pending set vs unknown consumer | Persist pending+closed+final;unknown never timeout-terminal |
| Pp/P2 or pending/final proof mixing | Reject positive readback |
| Later unrelated manifest with unchanged child | Fresh authenticated preservation/current read needed |
| Stale rights/custody/quality or090 hash-only record | No consumer authority;reduction may still proceed safely |
| Restart/copied JSON/guard/forged port/unenrolled fallback | No live capability |
| Revision overflow/64 slots/map capacity exhaustion | Block,preserve history,no active eviction |

D0 validates specification relations/digests in memory and static scope/links only. No Product/native tests or physical durability claim. Future pure tests cover every field,null/limit/allowed-forbidden edge and fixture nonauthority. Native power-loss/authenticated dependency/real Consent remain NOT_CONFIRMED.

## 11. Future pure exact6 and gates

Names frozen as proposals,not current Allowed Files:

1. src/ai_video_production/task109_owner_voice_preparation_consent.py
2. src/ai_video_production/task109_owner_voice_preparation_consent_fixture.py
3. schemas/task109-owner-voice-preparation-consent.schema.json
4. src/ai_video_production/schema_resources/task109-owner-voice-preparation-consent.schema.json
5. tests/test_task109_owner_voice_preparation_consent.py
6. tests/test_task109_owner_voice_preparation_consent_fixture.py

Pure parser/serializer/graph validation only,no clocks/filesystem/network/ports/live ID/capability factory/backend selection. Fixture results always FIXTURE_ONLY even when validating structural CURRENT input. Schema mirror exact bytes,synthetic opaque fixtures,no OS runtime dependency.

Gates: Critic/Tester then designated Judge exact-hash acceptance; separate pure allocation; owner102/043 child/profile and071/072 action/074 time amendments; foreign046 and089/090 bridges; separately authorized Product/native/real Consent/private/enrollment; Git publication;release/deploy/Production. D0 acceptance opens none automatically.
