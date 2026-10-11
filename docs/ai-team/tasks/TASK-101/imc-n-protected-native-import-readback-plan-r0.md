# TASK-101 IMC-N-D0 — Protected Native Import/Readback Gate Plan R0

Status: `R2_DESIGN_ACCEPTED / EFFECT_ZERO / NATIVE_BLOCKED`

## 1. Outcome and non-outcome

This document freezes the pre-effect gate, responsibility split, future implementation scope and native-run acceptance boundary for importing one already completed Owner GPT-SoVITS model pair into protected BAI VIDEO PRODUCTION custody.

IMC-N-D0 is complete only as an **effect-zero gate design**. It does not make the native importer available and does not authorize any private source read, protected destination creation, copy, encryption, key use, DACL change, model load or inference. A future implementation or native run must not treat acceptance of this document, a receipt digest, a configured path, a successful fixture or a previous Human approval as native authority.

The normative public record ABI, state names and failure classifications remain those accepted in [IMC-D R3](imc-d-existing-model-import-custody-contract-r0.md). This plan narrows how a future backend may satisfy that contract; it does not add or reinterpret public fields, enums, digest domains or transitions.

## 2. Exact D0 authority

The Owner authorized `TASK-101 / IMC-N-D0` on 2026-10-11 with exactly these repository Allowed Files:

1. `docs/ai-team/tasks/TASK-101/task.md`
2. `docs/ai-team/tasks/TASK-101/imc-n-protected-native-import-readback-plan-r0.md`

Public-safe external Evidence is limited to:

```text
C:\home\baisound\evidence\bai-video-production\TASK-101\imc-n-d0\<run-id>\
```

D0 may create a dedicated Git worktree/branch, change the exact-two documents, run effect-zero documentation/static/diff checks, obtain independent Critic/Tester/Judge review and write/read back bounded public-safe Evidence. All Product source, schemas, tests, producer/consumer Task records, private files and native roots are read-only or prohibited.

The following effects are explicitly outside D0:

- WSL, Windows or other private model-source access;
- source handle open, metadata/body read or physical-identity observation;
- protected destination provisioning or per-operation destination creation;
- plaintext or ciphertext copy/write, cipher/key/DPAPI operation, DACL mutation or secret access;
- live receipt/readback/capability issuance;
- model/runtime load, inference, audio, Provider/network use, Product/Shell connection;
- cleanup, overwrite, delete, repair, Release, Deploy or Production.

## 3. Responsibility and reuse boundary

| concern | canonical owner / treatment |
|---|---|
| historical model/Dataset/training lineage, ModelArtifactBinding, current H4, Consent, rights, license | TASK-046 current producer evidence; never created or upgraded by TASK-101 |
| accepted public import intent/receipt/readback ABI and failure matrix | TASK-101 IMC-D R3 + IMC-I; consumed without semantic change |
| existing-model native import custody/currentness | future TASK-101 IMC-N implementation and exact native-run units |
| training-terminal custody | TASK-084; its variant, receipt and native history are not aliased or reopened |
| catalog and installed-identity assessment | TASK-100 downstream; no catalog mutation here |
| load lease and inference | future IMC-L plus TASK-014/TASK-075 and other named owners; prohibited here |

`SecureAuthorityIO` and the accepted TASK-082 Windows private-media backend demonstrate reviewed patterns for root/ancestor pinning, stable physical identity, no-replace publication, durable flush, pinned readback, one-use leases and ambiguous-completion handling. They are not an existing TASK-101 binary-model backend:

- `SecureAuthorityIO` is not authority for encrypted model binary streams or a sealed two-file model inventory;
- TASK-082 owns private-media contracts, chunk envelopes, policy identities and lifecycle, not TASK-101 model import;
- TASK-084's current accepted source is a body-free contract and does not provide an adopted native backend;
- generic `Path`, `shutil`, ordinary rename, `atomic.py`, receipt-as-path or caller-supplied absolute paths may not substitute for a reviewed exact-handle native port.

A future implementation may import unchanged shared primitives only for operations their accepted contracts actually provide. If binary no-replace publication, directory durability, handle pinning or security-descriptor verification requires a new shared primitive, implementation must stop and obtain a separately scoped design/Allowed Files review rather than silently extending a shared owner.

## 4. Four distinct gates

Acceptance of one row never implies another.

| unit | permitted work | prohibited work | exit |
|---|---|---|---|
| `IMC-N-D0` | exact-two design/Evidence only | all source, test, private and native effects | accepted gate plan; native remains blocked |
| future `IMC-N-I0` | separately authorized exact source/test files; private capability interfaces, exact-handle port and synthetic fault harness only beneath unique OS temp | private source, protected destination, production cipher/key/DACL, production construction, live receipt | accepted interface/port candidate with DEV-4 negative/recovery tests |
| future `IMC-N-I1` | separately authorized production-backend implementation against accepted I0 identities and approved policies; synthetic bytes only | private source/root, live key use, live receipt or native run | accepted production-disabled-by-authority backend candidate |
| future `IMC-N-V` | one separately authorized operation with exact issuers, roots, policies and effect list | every effect not named by that gate; load/inference; destructive cleanup | exact pair sealed, durably reread, public-safe Evidence reread, or a terminal fail-closed/unknown result |

Publication/PR authority, cleanup authority and native-run authority are also distinct. Implementation acceptance cannot be used to run the backend. A native-run approval cannot expand repository Allowed Files.

## 5. Closed prerequisite ledger

Every item below must be `SATISFIED` by immutable identity and fresh readback at the indicated start or exit gate. `PRESENT`, configured, previously approved, self-hashed, inferred or `NOT_CONFIRMED` is not `SATISFIED`.

| gate | required evidence | required for | D0 state |
|---|---|---|---|
| `N01_IMC_I_CURRENT` | accepted IMC-I exact contract/schema/mirror/test identities on current base | I0 start, I1 start, V start | `SATISFIED` at D0 base `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04` |
| `N02_NATIVE_OWNER_SCOPE` | named owner and exact Allowed Files for that implementation unit | I0 start, I1 start | `BLOCKED_UNALLOCATED` |
| `N03A_TASK046_VERIFIER` | accepted TASK-046 evidence parser/currentness-verifier and non-serializable reservation issuer contract plus implementation identity; no live reservation | I1 start, V start | `BLOCKED_UNSUPPLIED_OR_UNIMPLEMENTED` |
| `N03B_TASK046_RUN_CURRENTNESS` | exact fresh historical reconciliation, ModelArtifactBinding, H4, Consent, rights and license evidence plus one exact V-operation currentness reservation issued only after the V gate | V pre-effect and runtime | `BLOCKED_UNAUTHORIZED_AND_UNSUPPLIED` |
| `N04_STORAGE_POLICY` | approved protected-root class, containment, ownership, security, retention and revocation policy digests | I1 start, V start | `BLOCKED_UNSUPPLIED` |
| `N05_CIPHER_KEY_POLICY` | approved streaming authenticated-encryption backend identity, cipher policy and key-scope identity; key custodian and zeroization/readback contract | I1 start, V start | `BLOCKED_UNSUPPLIED` |
| `N06_PRINCIPAL_DACL_POLICY` | approved principal/access policy and trusted security-descriptor verifier; exact rule for inherited versus explicit child DACL | I1 start, V start | `BLOCKED_UNSUPPLIED` |
| `N07_SOURCE_ISSUER` | accepted exact non-serializable source-capability issuer and currentness/physical-identity verifier implementation identity | I0 exit, I1 start, V start | `DESIGN_BOUNDARY_FROZEN / IMPLEMENTATION_ABSENT` |
| `N08_DESTINATION_ISSUER` | accepted exact non-serializable destination-capability issuer, root binding and collision/currentness verifier implementation identity | I0 exit, I1 start, V start | `DESIGN_BOUNDARY_FROZEN / IMPLEMENTATION_ABSENT` |
| `N09_NATIVE_PORT` | accepted exact-handle binary read/write, no-replace, file+directory durability, authenticated decrypt/reread port with Windows support and synthetic fault injection | I0 exit, I1 start, V start | `DESIGN_BOUNDARY_FROZEN / IMPLEMENTATION_ABSENT` |
| `N10_EXACT_RUN_GATE` | one operation ID, exact intent, exact source/destination capability identities, exact allowed effects, run ID and expiry | V | `BLOCKED_UNAUTHORIZED` |
| `N11_EVIDENCE_ROOT` | canonical contained public-safe Evidence root resolved to the exact run and proven non-foreign | V | `BLOCKED_UNRESOLVED` |
| `N12_CLEANUP_POLICY` | separate exact-identity cleanup authority, if cleanup is desired | V cleanup only | `BLOCKED_UNAUTHORIZED`; preservation is default |

`IMC-N-I0` may start only after fresh `N01` and a new exact `N02` allocation. Its exit requires accepted immutable `N07`, `N08` and `N09` implementation identities. `IMC-N-I1` may start only after every I1-marked row is satisfied and its own new exact `N02` allocation; `N03A` supplies only accepted verifier/issuer code and creates no live reservation. `IMC-N-V` may start only after every V-marked row is satisfied, including exact `N03B` evidence/reservation acquired under that V authority. This removes any circular claim that an implementation must already exist before the unit assigned to create and review it can start, and prevents a live operation reservation from leaking into an effect-zero implementation unit. D0 intentionally does not allocate either implementation unit or resolve the Owner/security dependencies.

## 6. Private capability boundary

Future source and destination authority must be non-serializable, exact built-in objects issued by reviewed authorities. They may contain or open private handles internally but must never expose an absolute path, account/SID, key, body, reusable token or generic filesystem accessor to public records, logs, exceptions or Evidence.

The source capability must bind at least:

- one immutable operation and accepted import intent;
- exactly two roles in `SOVITS`, `GPT` order;
- expected content digest, positive byte count and opaque source identity for each role;
- source root/ancestor/object physical-identity commitments and currentness;
- issuer, issue/expiry, one-open/burn and close/identity-readback semantics;
- read-only access; zero source delete, rename, repair or metadata mutation authority.

The destination capability must bind at least:

- the same operation and intent;
- an existing approved protected root and stable root/ancestor/security identities;
- one previously unused operation-owned relative namespace;
- destination class, cipher/backend/key-scope/principal/DACL/retention/revocation policy digests;
- exact create/publish limits, issuer, expiry and collision/currentness semantics;
- zero overwrite, replacement, foreign-object cleanup, root reprovisioning or generic child authority.

Strings, `Path` objects, mappings, receipts, public digests, fixture sentinels, copied/subclassed capabilities and capabilities from another process/operation/intent are rejected before body access. An issuer must durably prevent duplicate live issuance for the same operation; an exact duplicate request receives body-free state only.

The TASK-046 currentness reservation is a third, distinct non-serializable capability. `N03A` must freeze its exact issuer identity, purpose `EXISTING_MODEL_IMPORT_FINALIZATION`, operation/intent/evidence bindings, short issue/expiry times, verifier, replay/restart behavior and terminal release. The private lifecycle is closed:

```text
ISSUED -> HELD -> RELEASED_SUCCESS
ISSUED | HELD -> EXPIRED | FAILED_CLOSED | COMPLETION_UNKNOWN
RELEASED_SUCCESS | EXPIRED | FAILED_CLOSED | COMPLETION_UNKNOWN -> no transition
```

Only an exact `IMC-N-V` gate may acquire `N03B`. It is held from immediately before the first source capability open until the receipt/readback candidate pair is durably success-committed or a terminal failure is durably classified. Duplicate acquire/hold/release returns body-free state and never another capability. Expiry or verifier rejection before success prevents live issuance. Restart with `HELD` but without exact terminal release becomes `COMPLETION_UNKNOWN`, is not replayed, and blocks retry. `RELEASED_SUCCESS` is permitted only as part of one durable success commit that binds the exact canonical receipt/readback candidate digests; both the commit and reservation transition must be reread before the pair is exposed as live. Every failure path releases to its exact terminal state, and uncertain success commit/release/readback is `COMPLETION_UNKNOWN` with zero live issuance. After a confirmed success whose reply was lost, recovery may return only the exact already committed receipt/readback pair and body-free terminal state; it never reopens a capability or repeats native effects. I0/I1 may implement and test this contract only with synthetic non-production sentinels and may not acquire a live reservation.

## 7. Pre-effect placement and identity gate

Before any future native open/read/create/write, the orchestrator must validate body-free records and capability projections only, resolve all effect destinations internally to canonical absolute paths, and fail closed unless:

- the protected root, operation namespace, scratch root and Evidence root are not a drive root or a direct child of a drive root;
- every writable path is contained beneath its exact authorized root using pinned physical ancestors, not string-prefix comparison;
- the operation namespace and unique OS-temp scratch are bound to the exact Task/unit/run/operation;
- the target is absent by fresh issuer observation and no foreign, historical or unknown ownership exists;
- the Evidence destination is exactly `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-n\<run-id>\` for a future V run;
- the source is read-only and the protected destination is not the repository, worktree, Evidence root, system-temp root or source tree;
- configured path text is never authority and never enters public-safe output.

The body-free preflight may return only `NO_EFFECT`. It performs zero native open/read/create/write through the importer. Checks requiring an OS handle occur only after capability consumption begins and therefore use the accepted IMC-D failure matrix.

## 8. Future native operation protocol

The future backend must preserve the accepted state sequence:

```text
PLANNED
-> SOURCE_OPEN_STARTED
-> DESTINATION_PREPARED
-> COPY_ENCRYPT_STARTED
-> INVENTORY_SEALED
-> READBACK_CURRENT
```

It must implement the following protocol without introducing a second public ABI:

1. Reparse the exact intent and all current producer evidence; verify trusted time, issuer identity, policy digests, operation uniqueness, capability type and expiry. Under the exact V gate only, acquire `N03B` from the accepted `N03A` issuer and hold it through the durable success-commit/terminal-state readback; no receipt/readback is exposed as live while the reservation remains `HELD`.
2. Complete the pre-effect placement/collision gate. Failure is `NO_EFFECT` with all native counters zero.
3. Burn/open the exact source capability, pin both source ancestors and objects, reject symlink/reparse, disallowed hardlink count, non-regular file, role crossing, shared identity, replacement, size/hash mismatch or close uncertainty.
4. Revalidate the destination capability and pin the existing protected root/ancestor/security identity. Create only the exact operation-owned temporary namespace. Never create or repair the protected root opportunistically.
5. Stream each source through the approved production cipher into operation-owned temporary objects. Bound all plaintext/ciphertext bytes; retain no full plaintext copy; zeroize bounded buffers with confirmed readback according to the approved key policy.
6. Flush each ciphertext file and its containing directory, pin and reread its ciphertext digest, byte count, physical identity and security commitment. No plaintext body is written to scratch or Evidence.
7. Build the closed private inventory from verified observations and publish the inventory seal last using no-replace semantics. Flush the seal and directory, then pin/reread the full sealed set.
8. Close every source/write/cipher handle from the copy/seal phase and confirm close, final physical identity and zeroization readback. Any ambiguity maps to `COMPLETION_UNKNOWN`; no receipt candidate is constructed.
9. After durable seal and confirmed writer closure, construct an internal **non-issued** canonical `ExistingModelImportCustodyReceiptV1` candidate. Keep it private and non-authoritative. Canonically serialize/reparse it and recompute its exact self-digest before it can drive readback. Because the seal already exists, parse/digest failure is `COMPLETION_UNKNOWN`: preserve the sealed set/evidence, issue no live receipt and prohibit retry.
10. Using the exact reparsed candidate, distinctly reopen the protected sealed inventory through the accepted native backend with fresh pinned readback/key handles. Revalidate root/ancestor/member/security identities and the sealed inventory, then perform authenticated decrypt verification. Recompute each plaintext digest and byte count in bounded buffers, compare them to the exact intent, authenticate every header/tag and confirm buffer zeroization. Because the seal already exists, wrong key, tag, header, truncation, digest, byte count or decrypt result is `COMPLETION_UNKNOWN`: preserve evidence, issue no live receipt and prohibit retry. No plaintext body is persisted.
11. Close every distinct readback/key handle and confirm close, final physical identity and zeroization readback. Any ambiguity is `COMPLETION_UNKNOWN`; the internal receipt candidate is discarded without live issuance.
12. Immediately before finalization, freshly reparse and revalidate TASK-046/H4/Consent/rights/license evidence, revocation, trusted time, intent/run/capability expiry, held `N03B`, destination security/policy, the exact reparsed receipt candidate and the independently reopened physical observations. Because the seal already exists, any mid-run change, expiry, revocation or unverifiable reservation is `COMPLETION_UNKNOWN`: preserve evidence, issue no live receipt and prohibit retry.
13. Only after steps 1–12 all succeed may the backend construct and canonically reparse an internal non-live pure `CURRENT` readback candidate from the exact receipt candidate and independently reopened observations. It then performs one durable success commit binding both candidate digests and `N03B -> RELEASED_SUCCESS`, and rereads the commit plus terminal reservation state. Only that confirmed reread exposes the exact receipt/readback pair as live. Receipt/readback live issuance before distinct reopen, authenticated decrypt, confirmed readback-handle close/identity/zeroization, fresh terminal currentness and confirmed success-commit/reservation readback is forbidden. Commit/release/readback ambiguity is `COMPLETION_UNKNOWN` with zero live issuance; a confirmed commit with a lost reply is recovered only by exact pair readback without repeating effects.

The private on-disk envelope and operation journal are implementation details but security-critical. `IMC-N-I0` must freeze and independently accept their version, exact fields, bounds, abstract authenticated-cipher metadata, append-only transition semantics, recovery parser and publication order before `IMC-N-I1` may start. The journal may not use same-path mutable phase authority. If a durable transition cannot be represented without changing the accepted IMC-D failure semantics, implementation stops for a separately authorized design revision.

## 9. DACL, key and destination provisioning split

Protected-root provisioning, key-scope provisioning and principal/DACL policy approval are not hidden setup steps. The recommended boundary is:

- a separately authorized bootstrap provisions an existing protected root/key scope and returns body-free root/security/key-policy bindings;
- the import backend validates those bindings and creates only its operation-owned child;
- child security must be verified against the approved policy after creation and again during sealed readback;
- any explicit DACL mutation or key creation/rotation must be named in the exact native-run gate and evidenced separately.

If the future backend would need to broaden a DACL, expose a principal name/SID, export key material, use a test cipher in production or fall back from the approved cipher, it must fail closed. TASK-082 Current User DPAPI is not selected by this document; production cipher and key policy remain `N05_CIPHER_KEY_POLICY`.

## 10. Failure, recovery and cleanup

The IMC-D section 6.1 matrix is normative. Future implementation must additionally prove:

- public errors are closed stable reason codes with no path, filename, account, SID, key, model metadata or exception-chain leakage;
- `FAILED_CLOSED` is used only when every opened handle is closed with exact identity readback and no visible sealed custody exists;
- any uncertain source close, temporary ownership, no-replace result, final namespace appearance, file/directory flush, security descriptor, zeroization or reread is `COMPLETION_UNKNOWN`;
- restart never resumes or retries an incomplete/untrusted chain and never selects an alternate destination;
- foreign, historical, unknown and ambiguous objects are preserved exactly;
- operation-owned temporary cleanup is optional and disabled by default; D0 and future I do not authorize it;
- even a future cleanup gate must re-pin the exact physical objects and prove current-operation ownership immediately before deletion.

A `COMPLETION_UNKNOWN` result blocks reissue and import of the same operation/intent until a new Owner-authorized recovery unit classifies the preserved evidence. It never constructs a live receipt or `CURRENT` readback.

## 11. Future implementation exact-file proposal

Subject to the exact start/exit gates above and a new Owner allocation for each unit, the narrow default `IMC-N-I0` repository proposal is:

1. `docs/ai-team/tasks/TASK-101/task.md`
2. `src/ai_video_production/task101_existing_model_import_custody_windows.py` (new)
3. `tests/test_task101_existing_model_import_custody_windows.py` (new)

After accepted I0 identities and policy gates exist, the default `IMC-N-I1` proposal is the same exact-three paths under a separate Owner allocation. The accepted D0 plan, IMC-I source/schema/mirror/test exact-five, TASK-082, TASK-084 and `secure_authority_io.py` remain read-only dependencies. Implementation status may be appended only to `task.md`; this accepted plan is not writable implementation status. A semantic design correction requires a separately authorized exact-two D0 revision and fresh DEV-4 review. If either implementation unit cannot be completed within its exact-three boundary, it stops and requests an explicit scope/design amendment. Neither proposal is current mutation authority.

Synthetic tests must use a run-unique directory beneath the OS temporary root supplied by the test framework and a cipher whose identity is provably non-production. No test path may be a drive root/direct child, repository, worktree, canonical Evidence root or existing foreign path. Tests must record their resolved temp root and intentional residuals; default residuals are zero.

## 12. Required verification matrix

`IMC-N-I0` and `IMC-N-I1` each require independent DEV-4 Critic/Tester/Judge appropriate to their boundary. Across the accepted implementation sequence, verification includes at minimum:

- exact source/destination capability type, issuer, operation, intent, expiry and one-use tests;
- pre-effect zero-count tests for malformed/currentness/authority/containment/collision failures;
- exact-two role/order, size/hash, pair identity and runtime identity tests;
- symlink/reparse, hardlink, ancestor/root/object replacement, same-bytes/different-identity and shared-identity tests;
- foreign/unknown target, target-appears race, temp replacement and no-replace loser tests;
- short write/read, cipher failure, wrong key, wrong/missing authentication tag, header corruption, ciphertext truncation, plaintext digest/length mismatch, file flush, directory flush, seal-last and pinned-reread fault injection at every boundary;
- crash/restart at every state and durable `COMPLETION_UNKNOWN`/no-retry proof;
- security-descriptor/principal/policy mismatch and post-create/post-seal change tests;
- bounded memory/bytes/count and zeroization confirmation/failure tests;
- private/path/key/account/SID/exception leakage probes for result, log, repr and public Evidence;
- wrong TASK-046 reservation issuer/purpose/operation/intent/evidence, duplicate acquire/release, expiry, replay and restart from `HELD`; live acquisition remains impossible in I0/I1;
- mid-run H4/Consent/rights/license/custody revocation, trusted-time advance, intent/run/capability expiry and currentness-reservation loss before finalization;
- no readback from writer observations: exact internal receipt candidate reparse followed by distinct pinned reopen, authenticated decrypt/plaintext comparison, fresh terminal currentness and confirmed readback-handle close/identity/zeroization; every other terminal outcome produces zero live receipt/readback;
- every failure after inventory seal, including candidate parse, decrypt/authentication/plaintext mismatch and terminal currentness failure, is exactly `COMPLETION_UNKNOWN` with preserved evidence and no retry;
- exact-file scope, schema/mirror unchanged, direct TASK-101/TASK-100/TASK-084 regression and static import/compile checks.

`IMC-N-V` additionally requires a pre-run readback of every V gate, exact resolved output roots, independent preflight review, and post-run public-safe Evidence readback. Technical result is `PASS`, `FAIL` or `NOT_CONFIRMED`; observation/execution status is recorded separately.

## 13. Public-safe Evidence contract

Every future D0/I/V checkpoint records:

- Project, Task, Atomic Unit, run and native operation identity;
- exact worktree, branch, HEAD, base/current-main and dirty state;
- changed paths and Allowed Files result;
- gate ledger state and immutable receipt/digest identities;
- tests with exact result;
- resolved output-root class and containment result, but no private absolute source/destination path;
- public-safe artifact digests/counts, terminal classification and intentional residual count/opaque identities;
- prohibited effects, Human Gates and next action.

It must not contain private model bytes, filenames, absolute private paths, usernames, SIDs, raw ACLs, key/ciphertext material, secrets or unrestricted logs. Large/private native evidence remains under its approved protected/private custody; canonical Evidence contains only opaque references and digests. The checkpoint is reopened and its digest verified before a unit stops, rotates, hands off or claims completion.

## 14. D0 acceptance

D0 may be accepted when:

- the exact-two diff and effect-zero boundary pass;
- this plan does not change the accepted public ABI/failure matrix;
- the four distinct gates, closed prerequisites and future exact-file proposal are unambiguous;
- independent Critic and Tester report Critical/High zero;
- the DEV-4 Judge accepts the gate plan;
- public-safe external Evidence is written and reread.

D0 acceptance leaves TASK-101 active with `NATIVE_BLOCKED`. The next action is not native execution. It is an exact Owner decision allocating `IMC-N-I0` after fresh `N01` readback and an exact `N02` owner/scope, or a deliberate pause with the prerequisite ledger preserved. I1 and V remain later separate gates.

## 15. Recovery R2 acceptance

Frozen pre-record R2 HEAD `5c36f7881cefb1ec32ccbc497e51824dc786e157` on base/current main `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04` received independent Critic `ACCEPT` C/H/M/L `0/0/0/1`, Tester `PASS / ACCEPT` C/H/M/L `0/0/0/0`, and DEV-4 Judge `ACCEPT` C/H/M/L `0/0/0/1`. The reviewed design SHA-256 is `bad9d067cf9630cd90d6d98dc459d037652792e118b6024df5076b4ce7bf75b5`; the reviewed Task-record SHA-256 is `bbb5543b78472591a45b88f26939d97dded4073ca741c52bb7e59b8947960fcd`.

Final effect-zero verification is TASK-101 contract plus OSS readiness `49 / 49 PASS`, `git diff --check` `PASS`, exact-two scope `PASS`, ASCII documentation paths `PASS`, relative links `PASS`, accepted IMC-D/IMC-I content unchanged and all run-specific test residuals zero. The initial Windows Python route was `NOT_CONFIRMED` because that interpreter lacked `jsonschema`; no dependency was installed, and the same checks passed in the existing WSL environment.

The one accepted Low is wording only: section 6 says `N03B` is held “immediately before” source open while protocol step 1 acquires it before the zero-importer-I/O placement preflight in step 2. The numbered protocol is normative and safe: exact V authority is required, preflight failure is `NO_EFFECT`, reservation failure terminalizes, and no live result is exposed while `HELD`. This Low does not block D0 or I0. Clarifying it before the first real V-run specification is recommended; any semantic change requires a separately authorized exact-two design revision.

IMC-N-D0 is therefore accepted only as an effect-zero gate plan. Its public-safe completion checkpoint is bound to `C:\home\baisound\evidence\bai-video-production\TASK-101\imc-n-d0\20261011-imc-n-d0-final-001\checkpoint.json` and must be written and reread after this acceptance record is committed.

This acceptance grants no implementation or native authority. IMC-N-I0 remains blocked pending fresh `N01` plus a new exact `N02` Owner allocation. I1, V, private model access, destination/key/DACL effects, cleanup, IMC-L, live capability/load/inference, Product/Shell integration, publication, Release, Deploy and Production remain separately blocked or unallocated.

## 16. Fresh-main publication reconciliation

On 2026-10-12 the Owner separately authorized publication of this already
accepted effect-zero plan through a dedicated Japanese pull request, excluding
merge authority. Canonical remote `main`
`1ba6edd590925ee527f6736c9a02d7647052bb0d` includes TASK-111 merge
`9fb74ff88b07597f8d9b06eb7289ef0c2b05d9c1` and the R24-S3
coordinated-prearm merge at that main identity.

The fresh-main path audit found zero overlap with the exact-two D0 scope. The
semantic audit found no contract displacement: TASK-111 owns Human Audit input
bridging, and R24-S3 owns an effect-zero coordinated prearm adapter. Neither
implements or reallocates this plan's TASK-101 native source, protected
destination, receipt/readback or capability gates. `git range-diff` mapped each
accepted commit to its rebased equivalent with `=`; the rebased acceptance HEAD
before this reconciliation record is
`fd79e4e0da773b5d02dcf7072e3283dbb37e491e`.

The rebased candidate reran the effect-zero TASK-101 contract plus OSS
readiness suite with `49 / 49 PASS`. Publication still requires exact-two scope,
diff/link/path checks, fresh independent Critic and Tester acceptance,
canonical external Evidence write/readback and green hosted checks. This
reconciliation changes no normative D0 gate, does not refresh `N01` for I0 and
does not allocate `N02`. IMC-N-I0 and every private/native, Provider,
model/audio, Release, Deploy or Production effect remain outside this unit.
