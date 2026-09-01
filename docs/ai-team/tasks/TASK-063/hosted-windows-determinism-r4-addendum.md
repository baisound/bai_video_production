# TASK-063 — Hosted Windows Root-Validation Determinism R10 Addendum

Status: `DESIGN_COMPLETE / DEV-4 / SOURCE_START0 / RERUN0`

Design identity: `TASK063-PTD-HOSTED-WINDOWS-DETERMINISM-V7`

Historical design base: `origin/main@7dc91c2112923e357bb5e3eab597f0c18ef33bbc`

Current review parent: `origin/main@74b85d7d3f5965cd515ff44bd5f4b7179185e578`

Parent design: `TASK063-PTD-INSTALLER-SEMANTICS-READBACK-V2-R3`

Owner allocation: `2026-09-01 / Platform Trust & Delivery / Design B`

## 1. Decision

The TASK-063 R3 technical design remains immutable and accepted. This addendum
adds one nonconflicting hosted-validation contract: Windows root-boundary
verification must be deterministic under hosted parallel load and must not use
one undifferentiated 15-second process timeout as semantic proof.

This addendum does not relabel the observed failure as a Product defect or a
PASS. It keeps PR #485 failed until a later authorized implementation produces
fresh evidence. It performs no rerun and changes neither PR #485 nor any source,
test, tool, workflow, installer or shared document.

The frozen R4 review target was
`797B36D53E191BAABA8B0DF9E31A855375D2D1B8BA48725C88693F49F00EAADE`
(`426` lines / `18144` bytes). Independent Critic returned
Critical/High/Medium/Low `0/1/2/1`; independent Judge returned `0/4/0/0` and
FAIL. R5 supersedes that candidate without rewriting the review evidence. It
closes semantic-failure typing, process-lifecycle proof, fixed timeout/resource
policy and the proposed future file boundary.

The frozen R5 review target was
`9B6703F53E0BD7DA4A9CD0A5886ADC94871563A985C3260E497921AE232165CB`
(`562` lines / `24863` bytes). Independent Critic returned `0/2/1/0`; Judge
returned `0/1/0/0`, both REVISE/FAIL. R6 preserves the R5 closures and adds the
missing physical-mode operation, post-handle-close receipt commit and reviewed
fixed-matrix body/hash.

The frozen R6 review target was
`25CEE78DF706B7288BAA2F57AC7858E48FFB78661B327D2108A0CEA2682122DF`
(`667` lines / `31009` bytes). Independent Critic returned `0/1/2/1` and
REVISE; independent Judge returned `0/0/0/0` and PASS. R7 keeps the Judge-closed
R6 structure and closes the Critic's remaining physical handle-transfer,
predicate-matrix, cleanup/receipt-order and concurrency-scope findings.

The frozen R7 review target was
`6CBCF2DA58536FB83F524FCE1AF283A959DD311BE09E9CDE0D725BB8EBA6C3AB`
(`852` lines / `41529` bytes). Independent Critic returned `0/0/2/0` and PASS;
independent Judge returned `0/1/2/0` and FAIL. R8 preserves the R7 handle and
matrix closures, makes semantic and cleanup outcomes orthogonal, adds complete
cleanup preflight/partial evidence, and defines a real same-operation admission
claim.

The frozen R8 review target was
`3407F085BE3DA4AC67AA4A93A83624D5657A5FD4E9CDAA5F83908004DA4C9D7E`
(`989` lines / `48502` bytes). Independent Critic returned `0/2/0/0` and
REVISE; independent Judge returned `0/0/0/0` and PASS. R9 preserves the R8
semantic/cleanup and admission closures, distinguishes normal exit from every
confirmed termination, and retains exact known deletion evidence when residual
readback becomes uncertain.

The frozen R9 review target was
`E1CE1AFFBF664CD4A0FC22D24B96719191E57C4554ED7855059D6B6C51AFB0B1`
(`1092` lines / `53960` bytes). Independent Critic returned `0/1/1/0` and
REVISE; independent Judge returned `0/1/0/0` and FAIL. R10 makes the process
outcome common to lexical and physical modes and adds an explicit plan-frozen,
pre-delete cleanup outcome.

The frozen R10 review target was
`7BA88FE1F7792CB983396253995D4175F6941135D8B48D9B45429DF0A16BCD3E`
(`1095` lines / `54504` bytes). Independent Critic returned `0/0/1/0` and
PASS on the Critical/High gate; independent Judge returned `0/0/0/0` and PASS.
This completion finalization changes only status and receipt fields; the frozen
R10 technical review target is unchanged.

## 2. Exact evidence and bounded classification

Observed candidate and CI coordinates are:

- PR: `#485`, head
  `3ef775854154629146bd625c1fcdde2e3cc1114d`;
- PR files: five TASK-073 documentation/HTML paths; TASK-063 overlap `0`;
- workflow run: `33488402239`;
- Windows 3.11 job: `99793812103`;
- failing test:
  `tests/test_task063_main_installer_contract.py::test_acceptance_root_validation_is_boundary_aware_on_windows[D:\\BAI\\BAI VIDEO PRODUCTION FOR DRFX\\test-install-True]`;
- result: one `subprocess.TimeoutExpired` at `15.09s`, with `5070 passed`,
  `11 skipped` and `11 subtests passed`;
- a second accepted vector in the same parametrized test completed in `4.83s`;
- the Windows 3.12 and Windows 3.13 matrix jobs passed.

Current `origin/main` source proves:

1. every parameter vector launches a fresh `powershell.exe` process;
2. the outer `subprocess.run(..., timeout=15)` includes PowerShell process
   startup, pipe handling and all validation work;
3. `-ValidateRootOnly` normalizes the path, performs the lexical bounded-root
   test, then calls `Get-SafeAncestorSnapshot`;
4. the ancestor snapshot calls `Test-Path` and `Get-Item` for each ancestor;
5. `-ValidateRootOnly` returns before the installer `Start-Process` path and
   therefore has installer/native mutation effect zero.

The exact classification is `HOSTED_HARNESS_TIMEOUT / SEMANTIC_RESULT_UNKNOWN`.
The single timeout cannot distinguish PowerShell cold-start/pipe delay from an
ancestor filesystem call delayed by hosted load. No narrower root cause is
claimed without stage evidence. The Product boundary assertion was not
observed to fail, but it was also not observed to complete for that vector.

## 3. Responsibility, sole writer and authority ceiling

TASK-063 owns deterministic hosted verification of its own root-validation
contract. It does not own GitHub runner scheduling, global xdist policy,
PowerShell implementation, Windows filesystem scheduling or CI infrastructure.

This design Atomic Unit has exactly one writer:

```text
owner: Platform Trust & Delivery / Design B
branch: codex/task-063-hosted-windows-determinism-design
worktree: .worktrees/task-063-hosted-windows-determinism-design
allowed_file:
  docs/ai-team/tasks/TASK-063/hosted-windows-determinism-r4-addendum.md
```

The unit authorizes design, independent review, commit, push and one Draft PR
only after Critical/High `0/0` and Judge PASS. It creates no implementation,
test, native, rerun, CI, installer, release, deploy or Production authority.

## 4. One-way dependency and disposition graph

```text
TASK-063 R3 accepted semantic design
    + exact origin/main test/script snapshot
    + PR #485 failed hosted evidence (read-only)
    -> TASK063_HOSTED_ROOT_VALIDATION_CONTRACT_V7 fixture
    -> future U3-H HOSTED_ROOT_VALIDATION_DETERMINISM
    -> fresh Windows 3.11 / 3.12 / 3.13 hosted evidence
```

The design fixture does not depend on TASK-068, TASK-070 or TASK-072. A future
root-validation implementation unit remains non-authoritative and effect zero;
real installer/security binding and Production linkage still require every
producer and native Gate in the parent R3 packet.

PR #485 is a consumer of repository-wide CI only. Its branch is never updated,
rebased, rerun or repaired by this design. A future correction uses its own
TASK-063 branch and fresh head.

## 5. Exact Allowed Files for a future U3-H proposal

This section is a proposed implementation boundary, not current mutation
authority. U3-H may start only after a fresh authorization/overlap/lock check.

An early no-Product-change fixture slice may touch only:

- `tests/test_task063_main_installer_contract.py`;
- `tests/fixtures/task063/validate-root-matrix.ps1`;
- `docs/ai-team/tasks/TASK-063/hosted-windows-determinism-r4-addendum.md`.

That slice can prove one-process fan-out and the closed frame parser, but cannot
close lexical/physical separation by copying or reimplementing the Product
algorithm. Full U3-H closure requires the actual acceptance script to expose the
split test-only modes defined below. A separate exact amendment is mandatory
before touching:

- `tools/windows/test-task063-main-installer.ps1`.

The parent R3 corrective packet did not authorize that tool path for its future
units. This addendum does not silently expand it. No other source, workflow,
installer or package file is eligible.

## 6. Prohibited files and effects

- the immutable parent `complete-design-packet.md` and historical receipts;
- PR #485 branch or its TASK-073 files;
- `.github/workflows/**` and repository-wide xdist configuration;
- Product source, TASK-068/070/072 files, `atomic.py` or File Bridge source;
- packaging, Inno Setup, installer build, packaged entry or release metadata;
- shared current-state, roadmap, task index, registry or CHANGELOG;
- automatic rerun, retry-until-green or a blind timeout-only increase;
- real install, directory creation outside a test-owned temporary root,
  connector activation, Profile, migration, Release, Deploy or Production
  Activation;
- deletion/reset/cleanup of any existing worktree or unknown dirty path.

## 7. Closed hosted-validation protocol

The preferred contract uses one exact PowerShell process per fixed matrix, not
one process per parameter. It separates host readiness from semantic
validation:

```text
HOST_PROCESS_CREATED
    -> HOST_READY
    -> MATRIX_VALIDATING
    -> MATRIX_TERMINAL
```

The Python owner creates a dedicated Windows Job Object with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, assigns the exact PowerShell root before
validation can run, and retains the sole noninheritable Job handle plus the
exact process handle and bounded stdout/stderr readers. It accepts only one
closed protocol version and fixed matrix digest. It does not accept a path,
vector list, deadline, command, script body, callback or failure injector from
argv, environment, public JSON or test parameter data.

The fixed matrix contains exactly the canonical accepted/rejected cases already
owned by TASK-063. The harness emits opaque vector indices and stable codes,
never path bodies. A duplicate, missing, extra, reordered or unknown vector is
failure. A public JSON line is test evidence only and never installer authority.

`ROOT_BOUNDARY_MATRIX_V2` is the following exact ordered compact-ASCII-JSON
body with no trailing byte:

```json
[{"candidate":"D:\\BAI\\BAI VIDEO PRODUCTION FOR DRFX\\test-install","expected_result_code":"ACCEPTED","opaque_vector_index":0},{"candidate":"d:\\bai\\bai video production for drfx\\test-install\\child\\..","expected_result_code":"ACCEPTED","opaque_vector_index":1},{"candidate":"D:/BAI/BAI VIDEO PRODUCTION FOR DRFX/test-install/child/","expected_result_code":"ACCEPTED","opaque_vector_index":2},{"candidate":"D:\\BAI\\BAI VIDEO PRODUCTION FOR DRFX\\test-install-evil","expected_result_code":"REJECTED","opaque_vector_index":3},{"candidate":"D:\\BAI\\BAI VIDEO PRODUCTION FOR DRFX\\test-install\\..\\escape","expected_result_code":"REJECTED","opaque_vector_index":4},{"candidate":"relative\\test-install","expected_result_code":"REJECTED","opaque_vector_index":5},{"candidate":"C:\\test-install","expected_result_code":"REJECTED","opaque_vector_index":6}]
```

Its exact SHA-256 is
`05D5B3AE2BA5C01DDEB6E17AFC2E357212F7425599B17B2DA9CDEEF35BDF53D8`.
The body is private fixed fixture input; public frames and receipts expose only
the digest, seven opaque indices and result codes, never candidate strings.

### 7.0 Private operation admission

A session-scoped autouse fixture creates one nonserializable
`_TASK063_VALIDATION_SESSION_V3`. A function-scoped private factory derives a
noncopyable `_TASK063_OPERATION_CLAIM_V3` from the exact repository revision,
runner-job commitment, random pytest-session nonce, worker ID, Python process
ID, pytest node-ID hash, mode, profile hash and the mode's fixed matrix hash.
Callers cannot supply or serialize any of those coordinates.

The exact claim contract is sorted-key compact ASCII JSON with no trailing byte:

```json
{"claim_scope_fields":["repository_revision","runner_job_identity_sha256","pytest_session_nonce_sha256","pytest_worker_id","python_process_id","pytest_nodeid_sha256","mode","profile_sha256","matrix_sha256"],"duplicate_result":"DUPLICATE_BLOCKED_EFFECT0","exception_policy":"BURN","mode_values":["LEXICAL_MATRIX_V7","PHYSICAL_MATRIX_V7"],"registry_scope":"PYTEST_SESSION_WORKER_PROCESS","state_machine":["ABSENT","CLAIMED","IN_FLIGHT","TERMINAL_BURNED"],"transition":"ATOMIC_COMPARE_EXCHANGE_BEFORE_CREATEPROCESS","version":"TASK063_PRIVATE_OPERATION_CLAIM_V3"}
```

Its exact `operation_claim_contract_sha256` is
`71C4103772F18788C6C11E85A2A2E75BE00B48443455C74DC833087CCE9FEF8E`.
The private session registry performs atomic
`ABSENT -> CLAIMED -> IN_FLIGHT -> TERMINAL_BURNED` under one lock before any
`CreateProcessW`. Success, failure and exception all burn the key until session
end; entries are never reset or deleted for retry. A second/copy/stale/foreign
claim for the same key returns `DUPLICATE_BLOCKED` with process-create and
Product/filesystem effect zero. Lexical and physical modes use distinct keys.
Every process receipt binds the claim-contract and operation-key commitments.

The test-local native helper exposes one closed orchestration operation:

```text
execute_contained_root_validation_matrix_v7(
    _TASK063_OPERATION_CLAIM_V3[LEXICAL_MATRIX_V7]
) -> TASK063_HOSTED_ROOT_VALIDATION_RESULT_V7
```

The call accepts only the private matching claim and no path, command, matrix,
deadline, environment override, callback or failure injector. It claims before
spawn, uses `CreateProcessW` suspended with no visible window, creates the
dedicated Job, sets kill-on-close, assigns the retained process handle, records
exact process/Job identity, and only then resumes the primary thread. Failure
before assignment terminates/waits the exact suspended process. Uncertain
assignment, resume or handle ownership is failed-closed. Plain `subprocess.run`
is not the future U3-H process authority. The helper is test-only, contains no
generic command surface and is never packaged.

The following states exist only inside the call and are nonserializable,
noncopyable and one-use:

```text
UNSTARTED
  -> SPAWNING
  -> ASSIGNED_SUSPENDED
  -> RUNNING_HOST
  -> HOST_READY
  -> MATRIX_VALIDATING
  -> TERMINATING | ROOT_EXITED
  -> TERMINAL_PRE_CLOSE_PROOF
  -> HANDLES_CLOSED
  -> RECEIPT_COMMITTED
  -> CLOSED
```

No pending/ready object or native handle crosses the call boundary. One owner
retains the sole Job and root-process handles through pre-close proof, closes
them, and only then commits the receipt. Every return arm states whether the
process was not created, exited with exact readback, was terminated with exact
readback, or has an unconfirmed disposition.
An owner crash or final-handle close may contain the process tree through
kill-on-close, but cannot create a terminal receipt and remains N.C.

### 7.1 Separate deadlines

`FIXED_TASK063_HOSTED_PROFILE_V3` is immutable and contains exactly:

```text
clock_id: PYTHON_TIME_MONOTONIC_NS_QPC_V1
host_ready_deadline_ms: 60000
matrix_terminal_deadline_ms: 30000
post_terminal_exit_deadline_ms: 5000
termination_wait_ms: 5000
pipe_drain_after_exit_ms: 2000
stdout_total_bytes_max: 65536
stderr_total_bytes_max: 16384
protocol_frame_bytes_max: 4096
protocol_frame_count_max: 16
json_depth_max: 5
json_object_members_max: 24
json_array_items_max: 16
json_string_codepoints_max: 256
matrix_vector_count: 7
job_active_process_limit: 1
automatic_retry_count: 0
```

The profile is encoded as sorted-key compact ASCII JSON with no trailing byte.
The exact hashed body is:

```json
{"automatic_retry_count":0,"clock_id":"PYTHON_TIME_MONOTONIC_NS_QPC_V1","host_ready_deadline_ms":60000,"job_active_process_limit":1,"json_array_items_max":16,"json_depth_max":5,"json_object_members_max":24,"json_string_codepoints_max":256,"matrix_terminal_deadline_ms":30000,"matrix_vector_count":7,"pipe_drain_after_exit_ms":2000,"post_terminal_exit_deadline_ms":5000,"protocol_frame_bytes_max":4096,"protocol_frame_count_max":16,"stderr_total_bytes_max":16384,"stdout_total_bytes_max":65536,"termination_wait_ms":5000}
```

Its exact SHA-256 is
`EC65A73F975F598E4A57806B26D62C4F65608AA970B4A3ECF5E41EC1525D7D18`.

The Python owner samples `time.monotonic_ns()`; on supported Windows CPython
this profile binds the QueryPerformanceCounter-backed implementation and records
its clock implementation coordinate. Host time begins immediately before the
single `CreateProcessW` call and ends only when the strict complete `HOST_READY`
frame is committed. Matrix time begins at that commit and ends only when the
strict complete terminal frame is committed. Post-terminal exit time begins at
that terminal commit and ends only when the exact root process exits normally.
At `elapsed >= deadline`, timeout wins unless the exact stage terminal was
already committed under the same owner lock. Post-terminal expiry terminates the
exact Job and records `POST_TERMINAL_EXIT`; it cannot produce PASS. Wall time,
timezone and caller clocks are irrelevant.

Protocol frames are ASCII-only strict JSON followed by exact CRLF. Duplicate
keys, unknown fields, nonfinite numbers, BOM, invalid UTF-8, control/NUL,
trailing bytes and any profile ceiling breach fail closed before hashing or
semantic use. PASS requires stderr length zero. The receipt binds the exact
profile body and `profile_sha256`; changing any value creates a new profile and
requires fresh review. Merely changing `15` to a larger number without the
one-process matrix, stage separation, bounded capture and exact termination
rules does not satisfy this contract. The test never automatically retries any
stage deadline.

### 7.2 Lexical and physical separation

`ROOT_BOUNDARY_MATRIX_V2` exercises normalization and bounded-root semantics in
one process without calling ancestor filesystem inspection. It must prove the
same accepted/rejected truth table as the current test.

`ROOT_ANCESTOR_NATIVE_V7` is a separate Windows test over one runner-local,
test-owned, already-existing bounded root. It tests directory/reparse/currentness
behavior without relying on whether the canonical `D:` sample tree exists.
Its exact outer operation and private internal lease step are:

```text
execute_contained_root_ancestor_native_v7(
    _TASK063_OPERATION_CLAIM_V3[PHYSICAL_MATRIX_V7],
    pytest_tmp_path_factory
) -> TASK063_ROOT_ANCESTOR_NATIVE_RESULT_V7

  internally only:
  _acquire_task063_native_root_lease_v5(pytest_tmp_path_factory)
      -> _TASK063_NATIVE_ROOT_LEASE_V5 | ROOT_LEASE_FAILED_CLOSED
```

The outer operation first atomically consumes the matching private physical
claim, then accepts only pytest's in-process `tmp_path_factory`; it accepts no
raw path, mode, command or public DTO. The private factory creates
one unpredictable operation directory under that exact test-owned base. It
opens the directory with `FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES |
READ_CONTROL | DELETE`, `FILE_FLAG_BACKUP_SEMANTICS |
FILE_FLAG_OPEN_REPARSE_POINT`, and share READ/WRITE but not DELETE. It rejects
reparse state, pins volume serial plus 128-bit File ID, and retains the original
noninheritable handle. Ancestor identity/security commitments, operation nonce,
created-entry journal and cleanup state form a nonserializable, noncopyable,
one-use lease. Lease acquisition failure becomes
`BLOCKED / ROOT_LEASE_FAILED_CLOSED` with process-create count zero. A raw path,
public JSON, argv, environment, stale or foreign lease is rejected before
process creation.

`ROOT_ANCESTOR_PREDICATE_MATRIX_V3` is the following exact ordered compact-
ASCII-JSON body with no trailing byte:

```json
[{"expected_result_code":"ACCEPTED","fixture_code":"STABLE_REGULAR_CHAIN","opaque_vector_index":0},{"expected_result_code":"REJECTED_NOT_DIRECTORY","fixture_code":"LEAF_IS_FILE","opaque_vector_index":1},{"expected_result_code":"REJECTED_REPARSE","fixture_code":"LEAF_REPARSE","opaque_vector_index":2},{"expected_result_code":"REJECTED_REPARSE","fixture_code":"INTERMEDIATE_REPARSE","opaque_vector_index":3},{"expected_result_code":"REJECTED_IDENTITY_CHANGED","fixture_code":"SAME_FIELDS_DIFFERENT_FILE_ID","opaque_vector_index":4},{"expected_result_code":"REJECTED_CURRENTNESS","fixture_code":"ANCESTOR_SWAP_BETWEEN_READS","opaque_vector_index":5},{"expected_result_code":"REPLACEMENT_BLOCKED","fixture_code":"POST_READ_REPLACEMENT_ATTEMPT","opaque_vector_index":6}]
```

Its exact `physical_matrix_sha256` is
`B62831FED3CA9F3772427FC702BE1A1C7CA92AD511EFA022B4589019D0747B3E`.
All seven fixtures are created beneath the leased root, identified only by
opaque index in output, and evaluated once in the listed order. PASS requires
seven exact matches: accepted `1`, rejected-not-directory `1`,
rejected-reparse `2`, rejected-identity/currentness `2`, and replacement-blocked
`1`. An implementation-selected subset or different order is not this matrix.
The exact candidate fixture script owns the private deterministic choreography:
vector 4 creates two objects with matched visible metadata but distinct File
IDs; vector 5 releases only its fixture-local negative-test handle at the named
seam, swaps the ancestor and requires the currentness validator to reject;
vector 6 retains the observed component no-delete-share handle and requires the
replacement attempt to fail. No public fault injector or Product path can select
those seams. All ordinary physical observations retain their nofollow component
handles through post-check.

### 7.3 Native root handle and control protocol

Before suspended create, the owner makes exactly three anonymous pipe pairs and
one inheritable duplicate of the pinned root directory handle. It launches with
`STARTUPINFOEXW`, `EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED |
CREATE_NO_WINDOW`, `bInheritHandles=TRUE`, and one
`PROC_THREAD_ATTRIBUTE_HANDLE_LIST` containing exactly four child handles in
this fixed role order:

```text
0 CONTROL_STDIN_READ
1 PROTOCOL_STDOUT_WRITE
2 PROTOCOL_STDERR_WRITE
3 LEASED_ROOT_DIRECTORY
```

`STARTUPINFO` binds roles 0/1/2 as standard handles. No other handle is
inheritable. The parent keeps only the control write, protocol read and original
pinned-root ends; after successful assign-before-resume it closes its copies of
all four child ends. The root duplicate retains the same access/share contract.
The numeric role-3 value is private data, not authority by itself.

The control protocol descriptor is exact sorted-key compact ASCII JSON with no
trailing byte:

```json
{"ack_code":"ROOT_HANDLE_BOUND","control_body_bytes_max":4096,"control_stream_bytes_max":4616,"first_body_fields":["ancestor_chain_sha256","operation_nonce_sha256","physical_matrix_sha256","profile_sha256","root_file_id_128_hex","root_handle_value_u64_decimal","root_path_private","root_security_sha256","root_volume_serial_u64_decimal"],"frame_encoding":"TWO_U32BE_LENGTH_SORTED_COMPACT_ASCII_JSON_THEN_EOF","handle_roles":["CONTROL_STDIN_READ","PROTOCOL_STDOUT_WRITE","PROTOCOL_STDERR_WRITE","LEASED_ROOT_DIRECTORY"],"parent_write_count":2,"permit_body_bytes_max":512,"permit_code":"START_MATRIX","process_attribute":"STARTUPINFOEX_HANDLE_LIST_EXACT4","protocol":"TASK063_NATIVE_ROOT_CONTROL_V2","root_path_codepoints_max":1024,"root_share_mode":"READ_WRITE_NO_DELETE","same_object_check":"VOLUME_SERIAL_FILE_ID_PRE_EACH_POST"}
```

Its `control_protocol_sha256` is
`789D5C7F22E1801785D4DCF8E9493F2F28EC708647855D26E8047A1C3DA3B8DA`.
After exact `HOST_READY`, the parent writes the first frame: four-byte unsigned
big-endian body length followed by one sorted-key compact ASCII JSON body
containing exactly the listed fields. The private path is capped at 1024
codepoints and JSON-escaped into ASCII; this body is capped at 4096 bytes. The
parent writes every byte or fails but keeps its control-write handle open while
the child validates and ACKs.

The parent hashes the exact control body. Before any predicate, the child uses
the inherited role-3 handle directly with `GetFileInformationByHandleEx` and
requires its volume serial and 128-bit File ID to equal both the frame and its
own strict pre-read. It also resolves the handle final path, requires it to equal
the private normalized path, and verifies the security/ancestor commitments.
The no-delete-sharing parent and child handles remain open, so the leased root
cannot be renamed or replaced. The child repeats volume/File-ID checks before
each vector and after the last vector.

Only then may the child emit one strict ACK:

```text
ROOT_HANDLE_BOUND_ACK_V1 := {
  status=ROOT_HANDLE_BOUND,
  control_body_sha256,
  operation_nonce_sha256,
  root_volume_serial_u64_decimal,
  root_file_id_128_hex
}
```

The ACK is sorted compact ASCII JSON plus exact CRLF and is capped at 512 bytes.
The owner admits exactly one matching ACK before the matrix deadline under the
same one-winner state lock. It then writes one and only one second control frame:

```text
START_MATRIX_PERMIT_V1 := {
  status=START_MATRIX,
  control_body_sha256,
  root_bind_ack_sha256,
  operation_nonce_sha256
}
```

The permit body is sorted compact ASCII JSON, length-prefixed identically and
capped at 512 bytes. The parent writes every byte, closes the control-write
handle, and the child requires the exact permit followed immediately by EOF
before entering any predicate. The complete two-frame parent stream including
prefixes is capped at 4616 bytes. Duplicate/unknown fields, partial prefix/body,
extra byte, missing EOF, invalid ASCII, bad numeric/hex grammar, wrong digest or
write-close failure is `BLOCKED / CONTROL_FRAME_INVALID`.

The one-winner state is `HOST_READY -> CONTROL_SENT -> ACK_ACCEPTED ->
PERMIT_SENT -> MATRIX_VALIDATING`. Duplicate ACK, ACK-before-first-frame,
wrong digest/identity/nonce, EOF or ACK loss means the parent never sends the
permit and returns `BLOCKED / ROOT_BIND_ACK_NOT_CONFIRMED`. Partial/failed
control or permit transfer never authorizes predicate execution; the exact Job
is terminated and read back through the common lifecycle. Any root
pre/every/post identity mismatch is
`BLOCKED / LEASED_ROOT_CURRENTNESS_NOT_CONFIRMED`, not PHYSICAL_FAIL. No path
commitment can substitute for the inherited handle proof.

The native-mode contract is sorted-key compact ASCII JSON with no trailing byte:

```json
{"control_protocol_sha256":"789D5C7F22E1801785D4DCF8E9493F2F28EC708647855D26E8047A1C3DA3B8DA","mode":"ROOT_ANCESTOR_NATIVE_V7","operation_claim_contract_sha256":"71C4103772F18788C6C11E85A2A2E75BE00B48443455C74DC833087CCE9FEF8E","operation_root_source":"PRIVATE_ONE_USE_PINNED_LEASE","physical_matrix_sha256":"B62831FED3CA9F3772427FC702BE1A1C7CA92AD511EFA022B4589019D0747B3E","powershell_profile_sha256":"EC65A73F975F598E4A57806B26D62C4F65608AA970B4A3ECF5E41EC1525D7D18","process_lifecycle":"ROOT_VALIDATION_PROCESS_LIFECYCLE_V6","public_path_input":false,"script_hash_policy":"EXACT_CANDIDATE_BYTES","test_only":true}
```

Its exact `native_mode_contract_sha256` is
`5E3947140064758D57CF5AA857C2671A2FA6261B88A8A7916A0F761413C361BC`.
The native receipt binds this digest, control/profile/physical-matrix digests,
exact candidate fixture-script bytes hash, control-body/ACK/permit hashes and
lease/root/ancestor identities plus the claim/operation-key commitments.
Test-only root transfer is structurally unreachable from installer execution.

The production/installer path continues to perform both lexical and physical
checks. Test separation does not weaken runtime validation.

## 8. Typed result and receipt

Lexical and physical modes share one closed process outcome:

```text
TASK063_VALIDATION_PROCESS_OUTCOME_V7 :=
    NOT_CREATED {
        process_result=NOT_CREATED,
        termination_requested=false,
        terminal_readback=ABSENT
    }
  | NORMAL_EXIT_EXACT {
        process_result=NORMAL_EXIT_EXACT,
        termination_requested=false,
        exit_code=0,
        terminal_readback=EXACT
    }
  | FAILED_CLOSED_EXIT_EXACT {
        process_result=FAILED_CLOSED_EXIT_EXACT,
        stable_reason_code=NORMAL_EXIT_NONZERO,
        termination_requested=false,
        exit_code_commitment,
        terminal_readback=EXACT
    }
  | TIMEOUT_TERMINATED_EXACT {
        process_result=TIMEOUT_TERMINATED_EXACT,
        timeout_stage=HOST_START|MATRIX_VALIDATION|POST_TERMINAL_EXIT,
        termination_requested=true,
        exit_code_commitment,
        terminal_readback=EXACT
    }
  | FAILED_CLOSED_TERMINATED_EXACT {
        process_result=FAILED_CLOSED_TERMINATED_EXACT,
        stable_reason_code,
        termination_requested=true,
        exit_code_commitment,
        terminal_readback=EXACT
    }
  | NOT_CONFIRMED {
        process_result=NOT_CONFIRMED,
        stable_reason_code,
        termination_requested=false|true|UNKNOWN,
        terminal_readback=ABSENT|NOT_CONFIRMED
    }
```

The closed lexical semantic and composite result are:

```text
TASK063_LEXICAL_SEMANTIC_OUTCOME_V7 :=
    MATCHED_ALL {
        semantic_result=PASS,
        vector_count=7,
        matched_count=7,
        accepted_count=3,
        rejected_count=4
    }
  | MISMATCH {
        semantic_result=FAIL,
        opaque_vector_index,
        expected_result_code,
        observed_result_code,
        observation_frame_sha256
    }
  | NOT_OBSERVED {
        semantic_result=NOT_CONFIRMED,
        stable_reason_code
    }

TASK063_HOSTED_ROOT_VALIDATION_RESULT_V7 := {
    technical_result=PASS|FAIL|NOT_CONFIRMED,
    protocol_version,
    operation_claim_contract_sha256,
    operation_key_sha256,
    profile_sha256,
    fixed_matrix_sha256,
    semantic_outcome=TASK063_LEXICAL_SEMANTIC_OUTCOME_V7,
    process_outcome=TASK063_VALIDATION_PROCESS_OUTCOME_V7,
    installer_process_started=false,
    Product_filesystem_mutation_count=0,
    harness_process_create_count=0|1
}
```

The lexical projection is total and closed:

```text
semantic=FAIL                               -> technical_result=FAIL
semantic=PASS + process=NORMAL_EXIT_EXACT  -> technical_result=PASS
semantic=PASS + any other process outcome  -> technical_result=NOT_CONFIRMED
semantic=NOT_CONFIRMED                      -> technical_result=NOT_CONFIRMED
```

Thus a complete lexical PASS frame followed by nonzero normal exit is
`FAILED_CLOSED_EXIT_EXACT` and technical N.C.; a post-terminal hang with exact
termination is `TIMEOUT_TERMINATED_EXACT / POST_TERMINAL_EXIT` and technical
N.C. An exact lexical mismatch remains technical FAIL even if later process
exit/termination becomes N.C. NOT_CREATED cannot pair with semantic PASS/FAIL,
and a duplicate claim is semantic N.C. plus NOT_CREATED and technical N.C.

The receipt binds exact Product repository revision, test/script/harness hashes,
Python/PowerShell/Windows runner coordinates, claim/operation-key,
protocol/profile/matrix hashes, monotonic stage durations, terminal code,
dedicated Job identity commitment, root-process exit identity and active-member-
zero readback. Public output omits path, command, username, runner directory, OS
error and captured body.

`ROOT_VALIDATION_PROCESS_TERMINAL_READBACK_V6` binds the exact root-process and
Job identity commitments, whether termination was requested, exact root wait
completion and exit-code commitment, stdout/stderr EOF and bounded byte counts,
`QueryInformationJobObject` active-process count zero, and exact successful
`CloseHandle` outcomes for both retained handles. The owner first captures a
pre-close proof, then closes both handles, records their outcomes, and only then
commits/returns the receipt. Any exact process arm requires that readback; if a
pre-close element is unavailable, process outcome is
`NOT_CONFIRMED / PROCESS_EXIT_NOT_CONFIRMED`; if a close outcome is unavailable,
it is `NOT_CONFIRMED / HANDLE_CLOSE_NOT_CONFIRMED`. No stronger process state may
be inferred from kill-on-close. Spawn failure maps to NOT_CREATED plus semantic
N.C. with process-create count zero.

Physical ancestor validation has a separate result:

```text
TASK063_PHYSICAL_SEMANTIC_OUTCOME_V7 :=
    MATCHED_ALL {
        semantic_result=PASS,
        vector_count=7,
        matched_count=7
    }
  | MISMATCH {
        semantic_result=FAIL,
        opaque_vector_index,
        expected_predicate_code,
        observed_predicate_code,
        observation_frame_sha256
    }
  | NOT_OBSERVED {
        semantic_result=NOT_CONFIRMED,
        stable_reason_code
    }

TASK063_PHYSICAL_CLEANUP_OUTCOME_V7 :=
    NOT_REQUIRED {
        cleanup_result=NOT_REQUIRED,
        cleanup_plan_sha256=ABSENT,
        deleted_count=0,
        residual_count=0,
        root_lease_handle_close=ABSENT
    }
  | CONFIRMED {
        cleanup_result=CONFIRMED,
        cleanup_plan_sha256,
        planned_count,
        deleted_count=planned_count,
        deleted_identity_set_sha256,
        residual_count=0,
        residual_identity_set_sha256=
            4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945,
        root_lease_handle_close=CONFIRMED,
        root_path_residual=ABSENT
    }
  | PRESERVED {
        cleanup_result=NOT_CONFIRMED,
        stable_reason_code=PREFLIGHT_UNKNOWN_OR_FOREIGN,
        cleanup_plan_sha256=ABSENT,
        deleted_count=0,
        deleted_identity_set_sha256=
            4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945,
        residual_readback=EXACT|NOT_CONFIRMED,
        residual_count=NONNEGATIVE_INTEGER|UNKNOWN,
        residual_identity_set_sha256=OPAQUE_COMMITMENT|ABSENT,
        root_lease_handle_close=CONFIRMED|NOT_CONFIRMED,
        root_path_residual=PRESERVED|UNKNOWN,
        automatic_retry=false
    }
  | NOT_CONFIRMED_PREDELETE {
        cleanup_result=NOT_CONFIRMED,
        stable_reason_code,
        cleanup_plan_sha256,
        planned_count,
        delete_disposition_started=false,
        deleted_count=0,
        deleted_identity_set_sha256=
            4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945,
        residual_readback=EXACT|NOT_CONFIRMED,
        residual_count=NONNEGATIVE_INTEGER|UNKNOWN,
        residual_identity_set_sha256=OPAQUE_COMMITMENT|ABSENT,
        root_lease_handle_close=CONFIRMED|NOT_CONFIRMED,
        root_path_residual=PRESERVED|UNKNOWN,
        automatic_retry=false
    }
  | PARTIAL {
        cleanup_result=PARTIAL,
        stable_reason_code,
        cleanup_plan_sha256,
        planned_count,
        deleted_count=0..planned_count,
        deleted_identity_set_sha256,
        delete_disposition_started=true,
        residual_readback=EXACT|NOT_CONFIRMED,
        residual_count=NONNEGATIVE_INTEGER|UNKNOWN,
        residual_identity_set_sha256=OPAQUE_COMMITMENT|ABSENT,
        root_lease_handle_close=CONFIRMED|NOT_CONFIRMED,
        root_path_residual=PRESERVED|UNKNOWN,
        automatic_retry=false
    }
  | NOT_CONFIRMED_PREPLAN {
        cleanup_result=NOT_CONFIRMED,
        stable_reason_code,
        cleanup_plan_sha256=ABSENT,
        deleted_count=0,
        deleted_identity_set_sha256=
            4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945,
        residual_count=UNKNOWN|NONNEGATIVE_INTEGER,
        residual_identity_set_sha256=ABSENT|OPAQUE_COMMITMENT,
        root_lease_handle_close=ABSENT|CONFIRMED|NOT_CONFIRMED,
        root_path_residual=ABSENT|PRESERVED|UNKNOWN,
        automatic_retry=false
    }

TASK063_ROOT_ANCESTOR_NATIVE_RESULT_V7 := {
    technical_result=PASS|FAIL|NOT_CONFIRMED,
    protocol_version,
    operation_claim_contract_sha256,
    operation_key_sha256,
    profile_sha256,
    native_mode_contract_sha256,
    control_protocol_sha256,
    physical_matrix_sha256,
    fixture_script_sha256,
    control_body_sha256=ABSENT|OPAQUE_COMMITMENT,
    root_bind_ack_sha256=ABSENT|OPAQUE_COMMITMENT,
    start_matrix_permit_sha256=ABSENT|OPAQUE_COMMITMENT,
    root_lease_identity_commitment=ABSENT|OPAQUE_COMMITMENT,
    test_root_identity_commitment=ABSENT|OPAQUE_COMMITMENT,
    semantic_outcome=TASK063_PHYSICAL_SEMANTIC_OUTCOME_V7,
    process_outcome=TASK063_VALIDATION_PROCESS_OUTCOME_V7,
    cleanup_outcome=TASK063_PHYSICAL_CLEANUP_OUTCOME_V7,
    installer_process_started=false,
    Product_filesystem_mutation_count=0,
    unrelated_mutation_count=0
}
```

The projection is total and closed:

```text
semantic=FAIL                               -> technical_result=FAIL
semantic=PASS + process=NORMAL_EXIT_EXACT
              + cleanup=CONFIRMED          -> technical_result=PASS
semantic=PASS + any other process/cleanup  -> technical_result=NOT_CONFIRMED
semantic=NOT_CONFIRMED                      -> technical_result=NOT_CONFIRMED
```

The product is constrained, not an arbitrary Cartesian tuple. MATCHED_ALL or
MISMATCH requires an admitted ACK/permit, exact operation/root commitments and
a process that was created; NOT_CREATED cannot pair with semantic PASS/FAIL.
Technical FAIL requires the exact authenticated mismatch frame. NOT_REQUIRED
cleanup is valid only when no native lease/root was acquired or a duplicate was
blocked before acquisition. These combinations are produced only by the private
owner state machine and are revalidated before receipt commit.

Therefore a later process, cleanup or lease-close failure never erases an exact
observed predicate mismatch: its technical result stays FAIL while the separate
cleanup outcome records CONFIRMED, PARTIAL or NOT_CONFIRMED. A duplicate claim
projects semantic NOT_CONFIRMED, process NOT_CREATED, cleanup NOT_REQUIRED and
technical NOT_CONFIRMED with process/Product/filesystem effect zero.

A complete semantic-PASS frame followed by a child that does not exit is
`process_result=TIMEOUT_TERMINATED_EXACT` with
`timeout_stage=POST_TERMINAL_EXIT`; even exact Job termination and CONFIRMED
cleanup project technical NOT_CONFIRMED, never PASS. `EXACT` is not a standalone
process result, nonzero normal exit is FAILED_CLOSED, and no confirmed
termination is equivalent to successful normal exit.

For PRESERVED, NOT_CONFIRMED_PREDELETE or PARTIAL,
`residual_readback=EXACT` requires a nonnegative exact count and exact set
commitment. `residual_readback=NOT_CONFIRMED` requires
`residual_count=UNKNOWN` and an absent or last-known opaque commitment. A failure
after plan freeze but before the first disposition is NOT_CONFIRMED_PREDELETE and
retains the plan hash plus exact zero-deletion evidence. Once a frozen-plan
disposition starts, the operation is PARTIAL and can never fall back to a
preplan/predelete arm; it always preserves the exact known deleted count/set,
including the empty-set hash when zero.

This native fixture may create only its exact operation-owned temporary root.
After process-terminal readback, the parent still holds the original no-delete-
share root handle. Before the first delete disposition it opens and pins every
journaled entry, enumerates the complete current directory set, verifies exact
name/type/volume/File-ID/security against the created-entry journal, proves
there are no extras, and freezes an immutable `cleanup_plan_sha256`. If any
entry is unknown/foreign or cannot be pinned, it issues zero delete dispositions
and returns PRESERVED.

Only after full preflight may the owner execute the frozen handle-bound cleanup
plan. A failure/cancel after plan freeze but before the first disposition returns
NOT_CONFIRMED_PREDELETE with that exact plan and zero-deletion proof. Every
successful disposition is appended to an in-memory immutable deleted-identity
set. A failure after the first disposition begins returns PARTIAL with exact plan
plus known-deleted count/set. It records exact
residual count/set when readback succeeds, or explicit UNKNOWN/opaque residual
state when it does not; it never rewrites known deletion evidence to zero. It
preserves the remainder and never retries or reconstructs a plan. If all entries
are deleted, the owner sets handle-bound root deletion, closes the lease handle
with exact success, and verifies the original operation path absent. A different
object at that path is foreign, preserved and NOT_CONFIRMED.

The physical receipt is committed only after semantic, process and cleanup
outcomes are independently final. Public output exposes commitments/counts only;
unknown/foreign state is never deleted. The terminal order is exact:

```text
PROCESS_OUTCOME_FINAL
  -> COMPLETE_TREE_PREFLIGHT_AND_PIN
  -> CLEANUP_PLAN_FROZEN | ZERO_DELETE_PRESERVE
  -> PREDELETE_NC | COMPLETE_DELETE | PARTIAL_DELETE | PRESERVED
  -> ROOT_LEASE_HANDLE_CLOSED_OR_NC
  -> PHYSICAL_RECEIPT_COMMITTED
```

## 9. Process-tree termination and recovery

- On a normal terminal frame, the owner retains both native handles and waits
  the exact root only until `post_terminal_exit_deadline_ms`. Normal exit within
  that bound drains and closes the bounded pipe readers, queries the still-open
  Job for active member count zero, captures a pre-close proof, closes both
  process/Job handles with exact successful outcomes, and only then commits
  terminal readback. A lexical mismatch follows this normal-exit path and
  commits semantic MISMATCH plus technical FAIL.
- If the terminal frame is committed but normal exit misses that deadline, the
  owner calls `TerminateJobObject` and performs the same exact-root wait, bounded
  drain, active-member-zero, preclose and exact-close sequence. Exact termination
  is the common `TIMEOUT_TERMINATED_EXACT / POST_TERMINAL_EXIT` process outcome.
  A committed PASS semantic remains technical N.C.; a committed mismatch remains
  technical FAIL. Neither can become PASS.
- Before `HOST_READY`, timeout calls `TerminateJobObject` while retaining the
  sole Job handle, waits the exact retained PowerShell root for at most
  `termination_wait_ms`, drains and closes both bounded pipe readers for at most
  `pipe_drain_after_exit_ms`, queries the still-open Job handle for active member
  count zero, captures pre-close proof, closes both handles with exact successful
  outcomes, and only then commits terminal readback. Exact proof permits
  `TIMEOUT_TERMINATED_EXACT / HOST_START` with semantic/technical N.C.
- After `HOST_READY`, timeout uses the same retain-terminate-wait-drain-query-
  preclose-close-commit sequence and permits
  `TIMEOUT_TERMINATED_EXACT / MATRIX_VALIDATION` with semantic/technical N.C.
- The lexical/native validation modes are statically forbidden from entering
  installer `Start-Process`; child-process count must remain zero.
- PID lookup, process-name search, `taskkill` by unpinned PID and broad runner
  process termination are forbidden.
- If exact Job membership, root-process exit, active-member zero or pipe closure
  cannot be proven, either mode records process N.C. with stable reason
  `PROCESS_EXIT_NOT_CONFIRMED`. It cannot create PASS or a typed timeout, while an
  exact lexical or physical mismatch already committed remains semantic and
  technical FAIL under section 8.
- Final-handle close is containment for owner crash only. Because it destroys
  the query authority, it can never support active-member-zero or a typed timeout
  receipt.
- A process/Job handle-close failure or unknown close outcome maps either mode to
  `process_outcome=NOT_CONFIRMED / HANDLE_CLOSE_NOT_CONFIRMED`. It cannot turn
  semantic PASS into technical PASS, but it does not erase a mismatch already
  observed and committed before close. Pre-close containment evidence alone
  never creates PASS or a typed timeout.
- A lexical or physical terminal PASS frame followed by a root process that
  fails to exit normally is `TIMEOUT_TERMINATED_EXACT /
  POST_TERMINAL_EXIT` only when the full termination readback succeeds. It
  remains technical N.C.; a confirmed kill is never promoted to
  `NORMAL_EXIT_EXACT`.
- No automatic second process, case retry, fallback shell or delayed adoption is
  allowed.
- A fresh CI run is a fresh observation, not recovery of the failed run.

No recovery path edits, deletes or repairs an install root. Test-owned temporary
native fixtures follow their own exact identity cleanup. Unknown/foreign state
found by complete preflight before the first disposition is preserved and the
cleanup count is zero. Once disposition has begun, later unknown/foreign state
is preserved while `PARTIAL` retains the exact journal/readback-proven deleted
set/count and every exact remaining set/count; only fields whose readback is not
confirmable are explicitly `UNKNOWN`/N.C.

## 10. Negative and fault matrix

### H63-PROCESS

- attempted one-PowerShell-process-per-vector fan-out;
- extra/reordered/missing process or matrix frame;
- wrong shell, protocol, script hash, repository revision or matrix digest;
- host reaches the old 15-second boundary but remains below the fixed host-ready
  budget;
- no HOST_READY before host deadline;
- HOST_READY followed by no terminal before semantic deadline;
- complete semantic-PASS frame followed by no normal process exit;
- complete semantic-PASS frame followed by nonzero normal exit;
- complete semantic-mismatch frame followed by nonzero exit, timeout or process
  readback N.C.;
- PowerShell root not assigned to the dedicated Job before resume;
- unexpected child in the Job at terminal or timeout;
- forged PID, PID reuse, process-name fallback or unrelated Job member;
- process exits while stdout/stderr reader remains uncertain;
- missing/extra/reordered inherited handle role or an inheritable fifth handle;
- partial control prefix/body, missing EOF, extra byte, write-close failure;
- ACK-before-first-frame completion, missing/duplicate/wrong ACK or ACK winner
  race;
- direct/copied/serialized/stale/foreign operation claim and exception reuse;
- caller requests retry, fallback shell or timeout override.

Expected: exact technical PASS, FAIL or one stable N.C. result; Product/
installer/filesystem effect zero; harness process create count exact zero/one;
retry process zero; every confirmed terminal has exact Job active count zero;
unrelated process termination zero; installer child zero.

### H63-SEMANTIC

- every accepted/rejected canonical vector;
- path normalization/case/separator/parent traversal edge cases;
- duplicate, omitted, reordered or unknown vector index;
- lexical mode reaches `Test-Path`, `Get-Item` or installer path;
- physical mode uses missing, foreign, reparsed or changed test root;
- slow/failing `Test-Path` or `Get-Item` fault;
- accepted body returned for rejected vector or inverse;
- raw/public/stale/foreign/cross-mode root lease, lease identity swap or replay;
- expected root placed in argv/environment/public frame or installer mode;
- native operation missing profile/native-mode/control/matrix/script/lease
  identity binding;
- inherited root handle versus frame/parent volume or File-ID mismatch;
- root handle closes before post-vector identity readback;
- cleanup entry swap or foreign entry found first/middle/last during complete
  preflight;
- delete failure at each frozen-plan index, root-delete failure, foreign root
  replacement or lease-close failure;
- failure/cancel after cleanup-plan freeze but before the first disposition;
- successful deletion followed by unavailable residual enumeration/readback.

Expected: fully observed lexical or physical mismatch remains technical FAIL
regardless of later process/cleanup status; only unobserved semantics is N.C.
Unknown/foreign preflight causes delete zero. Post-freeze/pre-delete failure
retains the exact plan and zero deletion; after a disposition starts, PARTIAL
retains every known deletion and explicit UNKNOWN residual state when necessary.
No retry. Install/config/descriptor/owner/learning delta zero.

### H63-PRIVACY/RESOURCE

- path/command/runner/account/OS-error echo;
- unbounded stdout/stderr, control/NUL, invalid UTF-8 or extra JSON;
- very long candidate encoded into a result;
- unknown result field, duplicate key or non-finite number;
- timeout exception serialized with subprocess arguments.

Expected: stable body-free code; sensitive raw bytes absent from receipt/log
projection; bounded capture; service remains available.

### H63-CONCURRENCY

- xdist schedules the matrix beside slow native tests;
- two independent repository jobs run concurrently;
- two calls with the same session/worker/node/mode operation key;
- copied claim, second call after terminal, and second call after exception;
- simultaneous distinct lexical/physical keys;
- result from another Python/PowerShell version or job is replayed.

Expected: each operation invocation owns at most one process and one process
receipt; the normal suite owns exactly one lexical plus one physical operation.
Atomic session registry CAS gives duplicate same-key invocation exactly one
winner; every loser is DUPLICATE_BLOCKED with process/effect zero and the key is
burned on exception. Distinct mode keys remain isolated; no cross-operation/job
adoption; both vector counts exact; unrelated file delta zero.

## 11. Focused, hosted and native QA

Future U3-H evidence must include:

1. static proof that validation-only modes cannot reach installer
   `Start-Process`;
2. one-process fixed-matrix tests with exact process-create count one;
3. private session/node/mode operation-key derivation, atomic claim before spawn,
   duplicate loser effect zero and success/failure/exception burn;
4. separate host-ready, semantic and post-terminal-exit timeout fault injection
   through a test-only, nonpackaged private seam selected by the test module,
   never by the public orchestration call;
5. dedicated Job Object assign-before-run, process-tree terminate/wait,
   active-member-zero, pipe-closure, exact handle-close and post-close receipt;
6. lexical matrix result parity with the current canonical vectors;
7. exact hashed seven-vector physical ancestor/reparse/currentness matrix;
8. exact four-handle STARTUPINFOEX allowlist, strict private control/ACK/permit,
   parent/child same-volume/File-ID pre/every/post checks;
9. all-entry pin/set preflight before delete, frozen plan, every delete/root/close
   post-freeze/pre-delete and post-delete residual-readback fault with exact plan,
   known-deletion and exact-or-UNKNOWN residual
   CONFIRMED/PRESERVED/PREDELETE/PARTIAL/NC evidence;
10. lexical and physical semantic FAIL retained across every process/cleanup
    outcome;
11. complete lexical/physical semantic-PASS frame followed by hung child or
    nonzero normal exit maps to failed-closed/confirmed termination and technical
    N.C., never PASS;
12. bounded/privacy-safe stdout, stderr and failure receipts;
13. xdist-load test proving no per-vector shell fan-out;
14. Windows Python 3.11, 3.12 and 3.13 hosted PASS on one exact candidate;
15. no automatic rerun and no PR #485 branch mutation.

The test-only delay/fault seam is absent from packaged Product composition.
Hosted PASS does not satisfy the parent R3 real installer/native/Production-
linkage Gate.

## 12. Acceptance

1. Parent R3 design and historical evidence remain unchanged.
2. PR #485 is proven non-overlapping and remains unmodified/unrerun.
3. The failure is recorded as `SEMANTIC_RESULT_UNKNOWN`, not Product FAIL or
   PASS.
4. One fixed matrix uses one PowerShell process and one exact protocol.
5. Host startup, semantic validation and post-terminal normal exit use the exact
   versioned timeout, monotonic-clock, boundary and resource profile in section
   7.1.
6. Increasing a timeout alone is insufficient.
7. Lexical and physical validation use the exact reviewed matrix bodies/hashes;
   physical execution uses the four-handle allowlist, inherited pinned root,
   strict control/ACK/permit and same-object checks without weakening installer
   paths.
8. Each session/worker/node/mode operation key has one private atomic claim
   winner before `CreateProcessW`; duplicate, copied, stale or foreign claims
   have process/effect zero, and success, failure or exception burns the key.
9. Lexical and physical semantic/process outcomes are independently final. An
   exact mismatch remains technical FAIL regardless of later process/cleanup
   N.C. Lexical technical PASS requires semantic PASS plus
   `NORMAL_EXIT_EXACT`; physical PASS additionally requires CONFIRMED cleanup.
   A complete PASS frame followed by nonzero exit or confirmed termination is
   N.C. in either mode.
10. Cleanup pins and verifies the complete journal/current-entry set and freezes
    its plan before the first delete. Unknown/foreign preflight yields zero
    deletion; a post-freeze/pre-delete failure retains the plan and zero-delete
    proof; a later failure preserves exact known deletion counts/set, records
    exact or explicitly UNKNOWN residual state, preserves the remainder and
    never retries.
11. Validation-only modes have installer child, descriptor, owner, config,
   learning and unrelated file mutation zero.
12. Timeout/failure retains the Job handle through terminate, exact-root wait,
   bounded pipe drain and active-member-zero query, then closes both handles and
   commits only after successful close outcomes; PID/name fallback and unrelated
   termination are zero; owner crash/final-handle-close, close failure and
   unknown Job/process exit remain N.C.
13. Results and errors are bounded, body/path/account/OS-detail free and strict.
14. No retry, fallback shell, cross-job adoption or stale receipt can produce
    PASS.
15. Windows 3.11/3.12/3.13 fresh evidence passes on one exact candidate before
    the Hosted determinism Gate closes.
16. Native installer/Production linkage remains separately N.C.
17. Independent Critic returns Critical/High `0/0` and Judge returns PASS.

## 13. Completion receipt template

```text
task: TASK-063
unit: HOSTED_WINDOWS_ROOT_VALIDATION_DETERMINISM_R10
design_identity: TASK063-PTD-HOSTED-WINDOWS-DETERMINISM-V7
historical_design_base: origin/main@7dc91c2112923e357bb5e3eab597f0c18ef33bbc
review_parent_main: origin/main@74b85d7d3f5965cd515ff44bd5f4b7179185e578
allowed_file: docs/ai-team/tasks/TASK-063/hosted-windows-determinism-r4-addendum.md
sole_writer: PLATFORM_TRUST_AND_DELIVERY_DESIGN_B
superseded_r4_sha256: 797B36D53E191BAABA8B0DF9E31A855375D2D1B8BA48725C88693F49F00EAADE
superseded_r4_critic: REVISE_0_1_2_1
superseded_r4_judge: FAIL_0_4_0_0
superseded_r5_sha256: 9B6703F53E0BD7DA4A9CD0A5886ADC94871563A985C3260E497921AE232165CB
superseded_r5_critic: REVISE_0_2_1_0
superseded_r5_judge: FAIL_0_1_0_0
superseded_r6_sha256: 25CEE78DF706B7288BAA2F57AC7858E48FFB78661B327D2108A0CEA2682122DF
superseded_r6_critic: REVISE_0_1_2_1
superseded_r6_judge: PASS_0_0_0_0
superseded_r7_sha256: 6CBCF2DA58536FB83F524FCE1AF283A959DD311BE09E9CDE0D725BB8EBA6C3AB
superseded_r7_critic: PASS_0_0_2_0
superseded_r7_judge: FAIL_0_1_2_0
superseded_r8_sha256: 3407F085BE3DA4AC67AA4A93A83624D5657A5FD4E9CDAA5F83908004DA4C9D7E
superseded_r8_critic: REVISE_0_2_0_0
superseded_r8_judge: PASS_0_0_0_0
superseded_r9_sha256: E1CE1AFFBF664CD4A0FC22D24B96719191E57C4554ED7855059D6B6C51AFB0B1
superseded_r9_critic: REVISE_0_1_1_0
superseded_r9_judge: FAIL_0_1_0_0
review_target_sha256: 7BA88FE1F7792CB983396253995D4175F6941135D8B48D9B45429DF0A16BCD3E
review_target_lines: 1095
review_target_bytes: 54504
critic: PASS_0_0_1_0
judge: PASS_0_0_0_0
design_frozen: true
pr_485_branch_effect: 0
rerun_effect: 0
source_effect: 0
test_effect: 0
native_effect: 0
release_deploy_production_effect: 0
authority_created: false
```

This addendum creates no implementation or evidence PASS. A later U3-H requires
fresh exact Allowed Files, sole-writer/overlap/lock currentness and its own
focused review before source or test mutation.
