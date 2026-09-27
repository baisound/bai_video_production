# TASK-099 JCV-N-D — Secure native Project currentness backend R0

Status: `DESIGN_R1_ACCEPTED / OWNER_ARCHITECTURE_DECISION_REQUIRED / NATIVE_EFFECT_NOT_AUTHORIZED`

## 1. Decision and responsibility boundary

JCV-N cannot be implemented by promoting the legacy `ProductProjectManifestStore`, `_exclusive_project_lock`, `AtomicJsonWriter`, or TASK-068 `replace_json_cas` into secure authority. TASK-068 R6 is deliberately `IMMUTABLE_ONLY_V1`; its mutable same-path CAS surface is `CAS_ATOMIC_UNAVAILABLE`. The legacy Project store uses cooperative pathname locking and pathname replacement and therefore does not prove physical predecessor CAS, uncooperative-writer exclusion, ABA resistance, or exact post-seam classification.

The canonical Project manifest remains the sole currentness selector at `.bai-project/project.json`. JCV-N must not create a second Project store, derive a winner from directory order, or reinterpret an immutable index generation as current merely because it exists. TASK-068 remains the owner of immutable index-generation publication/readback. TASK-099 owns the exact manifest-selection transaction. TASK-076 owns Job events. TASK-072 owns child containment.

The candidate R1 architecture requires a Product-local Windows Secure Project Manifest Transaction Broker whose service identity is the only admitted principal with write/delete/rename access to the enrolled Project control directory. The ordinary BVP process and same-user peer processes receive read/traverse access but no control-directory mutation access. This security separation is necessary but is not sufficient by itself: the dependency feasibility gate must also prove long-lived sharing barriers, protected ownership/DACL state, client/server authentication, an implementable replacement primitive and durable operation evidence. Without those proofs, Windows same-path JSON replacement does not supply an identity-conditional kernel CAS sufficient to defeat an uncooperative same-user pathname swap, and implementation remains blocked.

That broker is **not owned by TASK-099**. Protecting `.bai-project` necessarily affects every canonical Project-manifest writer, including existing coordinated saves outside currentness selection. Assigning the generic broker to TASK-099 would overload its responsibility and silently take over TASK-043. A new Project Manifest Secure Transaction dependency Task must therefore be allocated after Owner architecture acceptance. It owns the generic enrolled-root broker, migration of all canonical manifest writers, and compatibility behavior. TASK-099 JCV-N consumes only its exact predecessor-CAS/readback capability and retains semantic currentness validation.

No Windows service installation, ACL change, Project enrollment, native manifest write, index publication, migration, Product integration, release, deploy or Production effect is authorized by this design.

## 2. Current dependencies

- Accepted JCV-I commit: `32c5badb1b354902754c54427fdfb2080b4cbe32`.
- JCV-I owns strict request/candidate/proposal/snapshot/phase/result parsing and the injected `ProjectJobCurrentnessBackendV2` orchestration only.
- TASK-068 canonical R6 supplies pinned reads, owner-issued writer capability, trusted immutable-plan publication, exact immutable receipt/readback and no-replace ambiguity classification. Its Windows native runtime remains independently `NOT_CONFIRMED` and must be re-proved for any JCV-N consumption.
- TASK-043 `ProductProjectManifest` remains the canonical manifest schema and generic child-binding model. Its current `1.0.0` contract can structurally carry one TASK-099 child binding; JCV-N adds an exact profile validator and does not silently widen the generic parser.
- TASK-043 `ProductProjectManifestStore.load/save` remains compatibility evidence. For an enrolled Project, every manifest write must eventually delegate to the new secure transaction owner; JCV-N alone may not reroute only its own write while leaving other writers blocked or privileged. V2 selection may not use `_save_unlocked` or `AtomicJsonWriter`.

## 3. Required security precondition

An enrolled Project root has a versioned `PROJECT_CURRENTNESS_BROKER_ENROLLMENT_V1` record held by the broker and a matching public-safe digest in Product configuration. Enrollment is a separate Human/native gate and must prove all of the following before any transaction is eligible:

1. the root is an existing Human-selected Project root, not created as a task artifact and not reused from an unknown QA path;
2. the resolved control directory is inside that exact root, is neither a drive root nor a direct child of a drive root, and every ancestor/target is local, regular, non-reparse and identity-pinned;
3. the volume exposes the tested atomic replacement and durability semantics; network, cloud-placeholder, removable, unsupported or unknown filesystems are rejected;
4. the broker service SID is the sole write/delete/rename principal for `.bai-project`; ordinary user/UI and unrelated service principals lack those rights;
5. root/control/manifest owner and DACL commitments match the enrollment receipt and are revalidated at every open and immediately before/after namespace effects;
6. the existing canonical manifest passes the exact TASK-043 parser and the JCV-N profile validator before security ownership changes are considered complete;
7. enrollment, ACL repair and format migration never occur in the same operation as Job-head selection.

The protected namespace boundary is exact. The service owns `.bai-project` with a protected, non-inheriting DACL; the interactive user has no `WRITE_DAC`, `WRITE_OWNER`, write, delete or rename right on it. The broker holds non-inheritable handles for the enrolled Project root and control directory without delete sharing for the full enrollment lifetime, and holds the canonical manifest under a compatible no-peer-write sharing barrier except during its own bounded replacement seam. Enrollment fails before ACL mutation unless it can acquire the complete barrier and thereby prove that no incompatible pre-enrollment write/delete handle remains. The control-directory DACL is not inherited from the user-owned Project root. Startup reopens and revalidates the exact physical ancestor chain, control owner/DACL, volume and enrollment commitment before admitting any client.

The threat model includes an arbitrary same-logon-user peer that can open paths, race names, hold handles before enrollment, connect to discoverable local IPC and attempt replay. It excludes administrator/SeBackupPrivilege/SeRestorePrivilege takeover, kernel compromise and code injection into an already admitted Product worker; those conditions invalidate currentness and require recovery rather than continued writes. PMST-D must verify that the long-lived no-share barriers plus protected control owner/DACL actually prevent root/control rename, parent `DELETE_CHILD` bypass, ACL reassignment and stale-handle mutation on every supported Windows/NTFS configuration. If a supported configuration cannot prove that boundary, enrollment is unavailable there.

Missing enrollment or any identity/security drift returns `BLOCKED_NO_WRITE`; configuration presence alone creates no authority.

## 4. Broker and client trust boundary

The generic secure transaction broker is a separate local Windows service or equivalently isolated service process with a dedicated service SID. An ordinary child process running as the interactive user is insufficient. The broker owns all mutation handles and never accepts an arbitrary host path in a transaction request. Its Task is the canonical TASK-043 successor dependency, not a TASK-099 submodule.

The client connects through a local authenticated named pipe with a fixed protocol version, bounded message size, strict duplicate-key JSON parsing and no handle inheritance. The broker creates the pipe with a restrictive explicit security descriptor and first-instance protection. The client pins and verifies the server PID, service SID, configured service identity, installed-image digest/signature, protocol and broker instance before sending private data. The server obtains and pins the client process handle, PID plus creation time, logon session, installed-image digest/signature and expected build/security-reader binding; PID or path alone is never identity.

After mutual admission, the broker mints a cryptographically random connection-local request nonce bound to that pinned client-process instance, broker instance, protocol, registration, transaction/request digests and one operation. It is accepted only on that connection, is atomically consumed before the first filesystem callback and is lost on disconnect/restart. A nonce copied to another process/connection, presented before its bound client, replayed, raced, or used after either process instance ends is rejected. Same-process memory compromise and code injection are explicitly outside the admitted threat model and invalidate the session. PMST-D must prove this mechanism or select a stronger packaged/AppContainer/restricted-worker identity; same-user token equality, executable pathname or an application-supplied bearer string alone is insufficient.

The broker maps an opaque enrolled `project_registration_id` to its private canonical root. The caller supplies only JCV-I records and the opaque registration ID after admission. Private broker-to-adapter replies are the full JCV-I phase envelopes required by JCV-D, including OPEN/REREAD full parsed snapshots and private opaque identity references. Only the adapter's separately validated Product/public projection is redacted; it contains no paths, handles, SIDs, DACL bodies, raw manifest/index bodies, OS messages, private opaque references or secrets.

The broker authenticates the mutually pinned process instances, expected install/build/security-reader binding, broker instance, protocol version and connection-local request nonce before opening the Project. A direct constructor, copied capability, replay, pipe squat, foreign broker instance, wrong build, unknown registration or second use fails before filesystem effects. It exposes a generic exact-manifest predecessor-CAS/readback primitive only to admitted Product compositions; TASK-099 supplies the already validated successor bytes and consumes the returned private identity/outcome evidence.

The named-pipe protocol is not Product runtime authority by itself. Service installation, startup and connection admission remain separate composition gates.

## 5. Canonical filesystem layout

- Canonical selector: `.bai-project/project.json` — the existing sole Product Project manifest.
- Broker lock: `.bai-project/.task099-currentness-v2.lock` — service-owned, regular, non-reparse, link-count one; never caller-created authority.
- Same-directory stage: `.bai-project/.task099-stage-<opaque-operation-digest>.tmp` — exact operation-owned, create-new only, never reused.
- Recovery witness: `.bai-project/.transaction-witness/<opaque-operation-digest>.json` — service-owned, immutable after terminalization and never a selector. Its bounded canonical record binds registration, transaction/request/proposal digests, prior/successor manifest bytes and physical identities, index receipt, broker/enrollment epochs, and exactly `PREPARED | COMMITTED_DURABLE | NOT_COMMITTED_PROVEN | UNKNOWN_QUARANTINED`. Names are keyed digests not caller values; records cannot be enumerated through public IPC.
- Immutable index generation: `.immutable-authority/<trusted-plan-name>.json` through TASK-068, with the exact relative path bound by one `ProjectChildBinding` whose owner is `TASK-099`, format is `bai-video-production.project-job-currentness-index`, version is `2.0.0`, and content digest is the JCV-I index digest.

The manifest never points to a mutable fixed index name. A published but unselected generation is an orphan and is preserved. The witness tree is recovery evidence only: it never determines the current Project head and is not a second Project store/selector. JCV-N does not delete published index generations, witnesses, backups, unknown stage files or foreign artifacts. Witness retention/compaction and any other cleanup/GC are a separate Task and Human Gate; until then terminal witnesses are retained.

## 6. Exact manifest profile

JCV-N accepts the current TASK-043 top-level Project format only when every generic invariant remains exact. It applies an additional closed profile over `child_bindings`:

- zero TASK-099 binding means `UNINITIALIZED` only after a complete authenticated absence check;
- one TASK-099 binding must use the exact owner/format/version/path grammar and required=true;
- more than one, wrong version, fixed mutable name, reserved control-directory path, unknown dependency hash, missing target, copied physical identity or hash mismatch is invalid, never absence;
- initialization adds the sole binding with index revision 1; later selection replaces exactly that binding and preserves every unrelated binding byte-for-byte after canonical parsing;
- `project_revision` advances exactly once, `created_at`, `product_version`, `timebase`, authority flags, secret/media flags and unrelated bindings are invariant, and `updated_at` comes only from the admitted broker clock;
- the successor canonical bytes and digest must equal the accepted JCV-I proposal before staging.

No top-level Project format migration is inferred. If a future format change is required, it is a separate predecessor operation with its own Task/authorization and may not be combined with selection.

## 7. Native transaction algorithm

The broker executes one bounded transaction per enrolled root:

1. Authenticate pipe/client/capability and snapshot all request records before filesystem callbacks.
2. Resolve the private enrollment; open and pin root, control directory, lock and manifest using no-follow/open-reparse semantics and non-inheritable handles.
3. Revalidate volume, owner/DACL, file type, link count, root/control/manifest physical identity and enrollment commitment.
4. Acquire the broker-global per-root queue and the OS lock. Revalidate every identity after lock acquisition.
5. Read bounded canonical manifest bytes through the pinned handle, parse TASK-043 plus the exact JCV-N profile, and construct `OPEN` snapshot/readback.
6. Authenticate and pin the exact TASK-076 candidate and predecessor physical identities. Revalidate request expiry using broker trusted time.
7. Re-read the manifest under the held service-only mutation boundary. Same state with a newer authenticated observation is allowed; identity/state drift is no-write conflict or unknown according to proof.
8. Independently compile and validate the successor manifest/index/proposal. Recompute invariant and unrelated-binding digests from prior and successor canonical bytes.
9. Create and durably persist the operation witness as `PREPARED`, including the exact prior/successor and request/proposal commitments, before index publication or the manifest namespace effect. Re-read it through a pinned service handle. An existing exact terminal witness routes to query; an in-flight or mismatched record blocks the root.
10. Publish the immutable index generation through an admitted TASK-068 trusted plan and exact receipt/readback. A collision is accepted only when the trusted receipt proves the exact already-published same generation; otherwise it is foreign/unknown. Any unselected generation remains an orphan.
11. Create the same-directory stage with create-new semantics, write the already-validated successor canonical bytes once, flush, re-read through the live handle and prove exact bytes/digest/identity.
12. Immediately before the namespace effect, revalidate every held barrier, root/control DACL commitment, exact predecessor manifest bytes/identity and PREPARED witness. The protected DACL, successfully held no-peer-write/delete sharing barriers and broker queue jointly form the exclusion proof; pathname lock alone is insufficient.
13. Invoke one platform port operation `replace_exact_service_owned_manifest`. PMST-D must select and document the concrete Windows API sequence, desired/share flags, handle/identity binding, supported NTFS/version matrix, partial-failure states, file flush, namespace/directory durability mechanism and power-loss claim. `ReplaceFileW` with `REPLACEFILE_WRITE_THROUGH` is not assumed sufficient, and a documented failure that can remove the canonical name is not classified old-or-new. If the target platform cannot demonstrate the required predecessor CAS and durability, the port is unavailable and no Product enrollment/implementation acceptance is allowed.
14. Re-open `.bai-project/project.json` from the pinned control directory and prove exact successor canonical bytes, physical identity, predecessor binding and selected immutable index receipt. While the root queue and exclusion barriers remain held, durably terminalize and re-read the witness as `COMMITTED_DURABLE`; only then may the broker admit any later manifest transaction. Then emit a fresh trusted currentness readback.
15. Release lock/handles. Release failure adds `LEASE_RELEASE_WARNING` and never erases an already determined commit/readback result.

The backend never retries the manifest namespace effect blindly.

## 8. Crash and recovery matrix

| Seam | Required classification | Recovery |
|---|---|---|
| before immutable index publication | `BLOCKED_NO_WRITE` or `CONFLICT_NO_WRITE` with proof | safe new request after fresh read |
| index publish unknown | `COMMIT_OUTCOME_UNKNOWN`; no manifest write starts | exact TASK-068 same-operation receipt query |
| index published, before manifest stage/replace | manifest `NOT_COMMITTED`; index orphan preserved | same request may query; no automatic deletion |
| stage written, before namespace effect | manifest `NOT_COMMITTED`; stage ownership recorded | preserve residual; separate owned cleanup only |
| exception during/after replacement primitive | `COMMIT_OUTCOME_UNKNOWN` | exact manifest reopen by registration and request/proposal digest |
| exact successor manifest present while PREPARED | durably terminalize `COMMITTED_DURABLE`; continue fresh readback | never admit a later write first; never downgrade to no-write |
| exact predecessor still present with unchanged identity, PREPARED witness and continuous service exclusion intact | durably terminalize `NOT_COMMITTED_PROVEN` | no blind replay; caller may create a new authorized request |
| any other manifest, missing canonical name, identity/DACL drift or ambiguous durability | durably mark `UNKNOWN_QUARANTINED` when safely possible | quarantine root; Human/recovery lane; no later write/repair/reset |
| successor readback lost after durable commit | `COMMIT_OUTCOME_UNKNOWN / COMMITTED / ORPHAN_PRESERVED` | same-operation query and fresh exact read |
| release failure after determined outcome | preserve outcome + `LEASE_RELEASE_WARNING` | no outcome downgrade |

Known committed evidence is monotonic. A later no-commit observation cannot downgrade it. Same bytes under a different physical identity do not prove the same outcome.

On broker startup, no root accepts a client or later transaction until every nonterminal witness is reconciled under reacquired exclusion barriers. A current exact successor terminalizes COMMITTED; an exact predecessor may terminalize NOT_COMMITTED only with a continuous or otherwise independently proven commit-seam exclusion; every other case becomes UNKNOWN_QUARANTINED. Because a later transaction is prohibited until the prior witness is terminal and durable, a committed operation cannot become superseded without first gaining an operation-bound durable witness. `query_operation(transaction_id, request_sha256)` therefore proves `SAME_OPERATION_COMMITTED_CURRENT`, `SAME_OPERATION_COMMITTED_SUPERSEDED`, `SAME_OPERATION_NOT_COMMITTED`, or UNKNOWN independently of the currently selected head. Loss, mismatch or unreadability of a required witness is UNKNOWN and blocks new writes; it never triggers reconstruction by filename scan, mtime or content equality alone.

## 9. Trusted time and coordinate

The broker owns time observation. It combines precise UTC wall time with a broker-instance/boot clock binding and a monotonic observation sequence. The state coordinate is stable for the same committed manifest; observation sequence/time may advance on reread. A manifest successor advances the manifest generation sequence exactly once. Durable witnesses bind the broker/enrollment epoch but remain queryable after restart through their transaction/request commitments; a restart never discards terminal outcome knowledge.

The client/request timestamp is admission data, not trusted-now authority. The broker evaluates `observed_at <= broker_trusted_now < expires_at` at OPEN, REREAD, VALIDATE and successor readback. Broker restart changes the observation clock binding but not the committed state coordinate. Service identity/epoch drift that cannot be reconciled from the exact enrolled root and manifest returns `EPOCH_RECONCILIATION_REQUIRED` with no selection write.

## 10. Error and privacy contract

Native/private errors are reduced to stable body-free codes after the private handler ends. No public exception/result retains paths, canonical bytes, JSON bodies, handle values, SIDs, ACL material, OS messages, verifier exceptions or private cause/context. Physical identities remain opaque private references admitted only by the broker and are not accepted from a public caller.

Every result keeps retry, blind replay, Job effect, cleanup, release/deploy/Production authority false. `COMMITTED_WITH_READBACK` selects currentness only; it does not authorize TASK-076's next effect.

## 11. Development decomposition and gates

### JCV-N0 — this design/feasibility unit

Allowed files are this document and `docs/ai-team/tasks/TASK-099/task.md`. No source, test, ACL, service, installer or filesystem effect.

Independent DEV-4 rereview accepted R1 with Critic/Judge and Tester C/H/M/L both `0/0/0/0`. The design/review portion is complete. The remaining exit is an explicit Owner architecture decision accepting or rejecting the service-SID broker prerequisite.

### PMST-D / PMST-I — new direct dependency Task

Only after JCV-N0 acceptance and Owner architecture acceptance, allocate a new unused Task ID for the Project Manifest Secure Transaction responsibility. It owns the generic service/client/enrollment protocol, service-SID ACL and long-lived sharing-barrier model, exact predecessor CAS, non-selector operation witnesses, migration of every canonical Project manifest writer, compatibility/read-only behavior and its own native assurance. It must not own TASK-099 semantic keys, index compilation or currentness decisions.

No Project may be enrolled until all of its manifest writers are routed or explicitly blocked by the accepted migration plan. Partial enrollment is prohibited.

PMST-D must produce a source-derived writer/security inventory before implementation: every `ProductProjectManifestStore.save`/private save route, recovery/import/migration utility, old Product binary and cross-version route must be either broker-delegated or deterministically read-only rejected. The same table must cover TASK-068 publication into `.immutable-authority`, including the admitted writer principal, root/control DACL, pinned physical identity/receipt retention and collision/readback behavior. JCV-N cannot select an index unless TASK-068 native publication is independently accepted on that protected topology. The feasibility exit also requires an API-specific proof plan for replacement/flush/power-loss behavior and a threat test matrix for pre-enrollment handles, parent rename/delete-child, owner ACL reassignment, ancestor swap, same-SID foreign clients, pipe squatting, PID reuse, nonce theft/replay, process/service restart, partial replacement failures and witness crash seams.

### JCV-N1 — pure TASK-099 native adapter over the accepted dependency

Only after the dependency's pure contract is accepted. It defines the bounded TASK-099 adapter, fake service serialization, trusted-time injection and the full fault matrix. It performs no OS, service, ACL or Project effects. Exact files must be allocated after the dependency decision.

### JCV-N2 — Windows broker/native backend implementation

Only after JCV-N1 acceptance, accepted dependency implementation, and explicit native implementation authority. It implements the TASK-099 adapter and TASK-068 composition over the generic broker; it does not implement a second service or manifest writer. Source mutation must use a dedicated worktree. Installation, ACL mutation and native execution remain separately gated.

### JCV-N3 — bounded Windows native verification

Requires explicit native QA authority. Every Project/QA root must be an OS-unique directory under the system temporary root or the canonical task Evidence root, never a drive-root child. It covers real NTFS identity, reparse/hardlink/security drift, two processes, ABA attempts, stage/replace crash seams, durability, service restart, expiry and result readback. Resolved roots and residuals are recorded; unknown residuals are preserved.

### JCV-N4 — canonical Product/store integration

Only after accepted native evidence and complete generic-writer migration. It adds one explicit JCV-N composition entry to the existing Product Project responsibility; legacy save remains non-authoritative for V2 currentness and cannot bypass the enrolled broker. JCV-C consumer amendments follow afterward.

## 12. Rejected alternatives

- Reusing `_exclusive_project_lock` or `AtomicJsonWriter`: cooperative pathname safety only; no physical CAS/uncooperative-writer proof.
- Treating TASK-068 immutable publication as manifest currentness: TASK-068 explicitly creates no currentness selector.
- Implementing a second SQLite/log/pointer store: violates the sole canonical Project manifest boundary.
- Directory scan, highest revision, newest mtime or lexicographic winner: prohibited derived currentness.
- Same-user child broker without protected service identity: does not exclude an uncooperative same-user writer.
- Auto-repair, rollback rename, cleanup or deletion after ambiguity: may mutate foreign/committed state and is not authorized.

## 13. Human decision

The Owner must explicitly choose whether BAI VIDEO PRODUCTION may introduce the service-SID Secure Project Manifest Transaction Broker and allocate its generic canonical-store responsibility as a new direct dependency Task. Rejecting that prerequisite leaves JCV-N blocked unless a different independently reviewed kernel/architecture mechanism supplies equivalent exclusive-writer and identity-CAS guarantees. Acceptance authorizes only allocation/design of the new dependency and subsequent bounded pure adapters; it does not authorize service installation, ACL mutation, native QA, release, deploy or Production.
