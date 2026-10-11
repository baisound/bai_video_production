# TASK-101 IMC-N-D0 — Protected Native Import/Readback Gate Plan R0

Status: `FROZEN_R0_AWAITING_INDEPENDENT_DEV4_REVIEW / EFFECT_ZERO / NATIVE_BLOCKED`

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

## 4. Three distinct gates

Acceptance of one row never implies another.

| unit | permitted work | prohibited work | exit |
|---|---|---|---|
| `IMC-N-D0` | exact-two design/Evidence only | all source, test, private and native effects | accepted gate plan; native remains blocked |
| future `IMC-N-I` | separately authorized exact source/test files; synthetic bytes only beneath unique OS temp; no private roots | private source, protected destination, production cipher/key/DACL, live receipt | accepted backend candidate with DEV-4 negative/recovery tests |
| future `IMC-N-V` | one separately authorized operation with exact issuers, roots, policies and effect list | every effect not named by that gate; load/inference; destructive cleanup | exact pair sealed, durably reread, public-safe Evidence reread, or a terminal fail-closed/unknown result |

Publication/PR authority, cleanup authority and native-run authority are also distinct. Implementation acceptance cannot be used to run the backend. A native-run approval cannot expand repository Allowed Files.

## 5. Closed prerequisite ledger

Every item below must be `SATISFIED` by immutable identity and fresh readback before the corresponding future unit starts. `PRESENT`, configured, previously approved, self-hashed, inferred or `NOT_CONFIRMED` is not `SATISFIED`.

| gate | required evidence | required for | D0 state |
|---|---|---|---|
| `N01_IMC_I_CURRENT` | accepted IMC-I exact contract/schema/mirror/test identities on current base | I, V | `SATISFIED` at D0 base `5748203d4e61a6b8c3c3695af0ea4a78e5e1aa04` |
| `N02_NATIVE_OWNER_SCOPE` | named implementation owner and exact future Allowed Files | I | `BLOCKED_UNALLOCATED` |
| `N03_TASK046_CURRENTNESS` | exact current historical reconciliation, ModelArtifactBinding, H4, Consent, rights and license records and their trusted verifiers | V | `BLOCKED_UNSUPPLIED` |
| `N04_STORAGE_POLICY` | approved protected-root class, containment, ownership, security, retention and revocation policy digests | I, V | `BLOCKED_UNSUPPLIED` |
| `N05_CIPHER_KEY_POLICY` | approved streaming/binary cipher backend identity, cipher policy and key-scope identity; key custodian and zeroization/readback contract | I, V | `BLOCKED_UNSUPPLIED` |
| `N06_PRINCIPAL_DACL_POLICY` | approved principal/access policy and trusted security-descriptor verifier; exact rule for inherited versus explicit child DACL | I, V | `BLOCKED_UNSUPPLIED` |
| `N07_SOURCE_ISSUER` | reviewed non-serializable source-capability issuer and currentness/physical-identity verifier | I, V | `BLOCKED_UNALLOCATED` |
| `N08_DESTINATION_ISSUER` | reviewed non-serializable destination-capability issuer, root binding and collision/currentness verifier | I, V | `BLOCKED_UNALLOCATED` |
| `N09_NATIVE_PORT` | exact-handle binary read/write, no-replace, file+directory durability and pinned reread port with Windows support and synthetic fault injection | I, V | `BLOCKED_UNDESIGNED` |
| `N10_EXACT_RUN_GATE` | one operation ID, exact intent, exact source/destination capability identities, exact allowed effects, run ID and expiry | V | `BLOCKED_UNAUTHORIZED` |
| `N11_EVIDENCE_ROOT` | canonical contained public-safe Evidence root resolved to the exact run and proven non-foreign | V | `BLOCKED_UNRESOLVED` |
| `N12_CLEANUP_POLICY` | separate exact-identity cleanup authority, if cleanup is desired | V cleanup only | `BLOCKED_UNAUTHORIZED`; preservation is default |

`IMC-N-I` must not start while any I-marked row is blocked. `IMC-N-V` must not start while any V-marked row is blocked. D0 intentionally does not resolve these Owner/security dependencies.

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

1. Reparse the exact intent and all current producer evidence; verify trusted time, issuer identity, policy digests, operation uniqueness, capability type and expiry.
2. Complete the pre-effect placement/collision gate. Failure is `NO_EFFECT` with all native counters zero.
3. Burn/open the exact source capability, pin both source ancestors and objects, reject symlink/reparse, disallowed hardlink count, non-regular file, role crossing, shared identity, replacement, size/hash mismatch or close uncertainty.
4. Revalidate the destination capability and pin the existing protected root/ancestor/security identity. Create only the exact operation-owned temporary namespace. Never create or repair the protected root opportunistically.
5. Stream each source through the approved production cipher into operation-owned temporary objects. Bound all plaintext/ciphertext bytes; retain no full plaintext copy; zeroize bounded buffers with confirmed readback according to the approved key policy.
6. Flush each ciphertext file and its containing directory, pin and reread its ciphertext digest, byte count, physical identity and security commitment. No plaintext body is written to scratch or Evidence.
7. Build the closed private inventory from verified observations and publish the inventory seal last using no-replace semantics. Flush the seal and directory, then pin/reread the full sealed set.
8. Only after exact two-file membership, all content/ciphertext identities, policies, durability and physical reread agree may the backend construct the accepted private receipt and pure `CURRENT` readback.
9. Close every source/destination/key handle and confirm close/identity/zeroization. Any ambiguity at or after an attempted open maps to `COMPLETION_UNKNOWN` as required by IMC-D; no blind retry or alternate target is allowed.

The private on-disk envelope and operation journal are implementation details but security-critical. `IMC-N-I` must freeze their version, exact fields, bounds, cipher metadata, append-only transition semantics, recovery parser and publication order before production construction is enabled. The journal may not use same-path mutable phase authority. If a durable transition cannot be represented without changing the accepted IMC-D failure semantics, implementation stops for design revision.

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

Subject to satisfaction of all I-marked gates and a new Owner allocation, the narrow default `IMC-N-I` repository proposal is:

1. `docs/ai-team/tasks/TASK-101/task.md`
2. `docs/ai-team/tasks/TASK-101/imc-n-protected-native-import-readback-plan-r0.md`
3. `src/ai_video_production/task101_existing_model_import_custody_windows.py` (new)
4. `tests/test_task101_existing_model_import_custody_windows.py` (new)

The accepted IMC-I source/schema/mirror/test exact-five, TASK-082, TASK-084 and `secure_authority_io.py` remain read-only dependencies. If implementation cannot be completed within this exact-four boundary, it stops and requests an explicit scope/design amendment. The proposal is not current mutation authority.

Synthetic tests must use a run-unique directory beneath the OS temporary root supplied by the test framework and a cipher whose identity is provably non-production. No test path may be a drive root/direct child, repository, worktree, canonical Evidence root or existing foreign path. Tests must record their resolved temp root and intentional residuals; default residuals are zero.

## 12. Required verification matrix

`IMC-N-I` requires independent DEV-4 Critic/Tester/Judge and, at minimum:

- exact source/destination capability type, issuer, operation, intent, expiry and one-use tests;
- pre-effect zero-count tests for malformed/currentness/authority/containment/collision failures;
- exact-two role/order, size/hash, pair identity and runtime identity tests;
- symlink/reparse, hardlink, ancestor/root/object replacement, same-bytes/different-identity and shared-identity tests;
- foreign/unknown target, target-appears race, temp replacement and no-replace loser tests;
- short write/read, cipher failure, key rejection, file flush, directory flush, seal-last and pinned-reread fault injection at every boundary;
- crash/restart at every state and durable `COMPLETION_UNKNOWN`/no-retry proof;
- security-descriptor/principal/policy mismatch and post-create/post-seal change tests;
- bounded memory/bytes/count and zeroization confirmation/failure tests;
- private/path/key/account/SID/exception leakage probes for result, log, repr and public Evidence;
- receipt only after seal and full reread; every other terminal outcome produces zero live receipt/readback;
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
- the three distinct gates, closed prerequisites and future exact-file proposal are unambiguous;
- independent Critic and Tester report Critical/High zero;
- the DEV-4 Judge accepts the gate plan;
- public-safe external Evidence is written and reread.

D0 acceptance leaves TASK-101 active with `NATIVE_BLOCKED`. The next action is not native execution. It is an exact Owner decision resolving the blocked I prerequisites and allocating `IMC-N-I`, or a deliberate pause with the prerequisite ledger preserved.
