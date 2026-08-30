# TASK-036 P-UX-2K local transcription controls design

Date: `2026-08-22`
Status: `R1 LOCAL VERIFIED / INDEPENDENT REVIEW PENDING / NATIVE NO-GO`
Atomic unit: `P-UX-2K_LOCAL_TRANSCRIPTION_CONTROLS_R1`

## 1. Goal

Connect the V6.1.1 recommended-action controls to the existing trusted
`transcription.start` route. After one canonical TASK-003 source Asset is
bound, prepare -> Human confirmation -> apply runs the configured local
FasterWhisper adapter at most once for the durable operation. A verified
Transcript is promoted to the existing fixed transcription outputs and bound
to the current Editing Session.

TASK-036 reuses TASK-003 ingest, TASK-006 FasterWhisper publication and the
shared Product `operations` ledger. It does not create another Provider,
Transcript store, Project database or Provider selector.

## 2. Human and currentness admission

- Home and generic `Next action` controls call one JavaScript function. It
  reserves the UI admission before the first asynchronous call.
- Python prepare creates a bounded single-use private confirmation. It binds
  Project ID, Editing Session revision, source Asset ID/SHA-256, Shell context
  revision and normal/recovery mode. Decline consumes the token through cancel.
- Apply consumes the token before any Provider effect. Direct bridge calls
  cannot replace the Human confirmation with an empty request.
- The existing Shell command revalidates the exact Project context. Final
  re-derivation and Transcript binding occur under the coordinator state lock
  and compare Project, session revision, Asset ID/SHA-256, stage and context
  revision.
- The complete public bridge operation, including status reads that inspect
  durable operation state, is protected by the trusted launch lifetime. Close
  rejects new calls and drains an admitted call before releasing the store.

## 3. Canonical source bytes

- Picker paths never reach ASR. TASK-003 resolves the newly ingested Asset to
  its Project-contained managed path, and only that path is held privately by
  the pre-edit runtime.
- Before durable admission the port reads the managed Asset through one
  non-following regular-file descriptor, copies it to a private temporary
  snapshot, and verifies the exact canonical Asset SHA-256 and stable identity.
- For Provider execution, a second verified snapshot is held for the full
  call. Linux/WSL exposes the held descriptor path; Windows holds a read-only
  handle that denies write/delete sharing while the Provider opens the path.
  The held bytes and identity are revalidated after inference.
- Source mismatch, symlink, mutation while copying or unsafe Provider snapshot
  fails closed. Original picker-file mutation is irrelevant after ingest.

## 4. Durable exact-once operation

- The operation identity is a canonical digest of contract version, Project
  ID, source Asset ID/SHA-256, Provider/model, every output-affecting ASR and
  timebase option, and `model_download_authorized` false. It is scoped by the
  configured Product Job.
- `SQLiteProductStore.reserve_operation` is the only reservation. The new
  shared `find_operation` read and `compare_and_set_operation_status` CAS APIs
  expose no TASK-036-specific schema.
- A second Project/output-slot Operation serializes the single fixed output
  destination across different source operations. The slot remains owned
  through Provider execution, publication and the atomic Editing Session bind.
- Exactly one caller may transition `PENDING -> IN_PROGRESS`. No FAILED,
  PARTIAL, IN_PROGRESS or COMPLETED source operation can automatically re-enter
  the Provider. Cross-thread and cross-process callers observe recovery or slot
  ownership instead.
- Provider success is first written to an immutable operation-owned generation.
  Its checksum-closed publication-set SHA is durably bound by
  `IN_PROGRESS -> PARTIAL` before any fixed output is replaced. Only then is
  the fixed set rolled forward and the source Operation completed while
  retaining the publication-set SHA as `result_ref`.
- Recovery is an explicit, separately confirmed Provider-zero operation. It
  accepts only the same Project/Job/source/Provider/model/config identity and a
  PARTIAL/COMPLETED Operation with a non-null exact publication-set SHA.
  IN_PROGRESS or unbound PARTIAL state never infers success from mutable fixed
  files. PARTIAL rolls forward only from the immutable generation; COMPLETED
  fixed-output mismatch is tamper and stays blocked.

## 5. Verified fixed-output promotion

- TASK-006 first publishes into a private per-call temporary directory.
- Transcript JSON, SRT and report are bounded stable reads. The Transcript
  checksum/source/Provider/model and exact report fields are validated.
  Re-rendering through TASK-006 must reproduce all three bytes exactly.
- Before fixed projection, the exact three files and a strict publication-set
  manifest are durably stored beneath an operation-owned immutable generation.
  The manifest binds Project/source/Provider/model/config, Transcript SHA and
  all three file hashes.
- The Project root is pinned before its fixed transcription child is opened.
  Each verified file is written by exclusive temporary create and atomic
  replace with directory durability, using the existing audited pinned-file
  primitive. Read-back uses the same bounded pinned directory chain.
- Fixed locations remain exactly `transcript.json`, `subtitles.srt` and
  `transcription-report.json` under the configured transcription output. This
  preserves existing Subtitle, Resolve and handoff bindings.
- A partial multi-file crash never becomes success: the durable operation is
  PARTIAL with a previously committed exact set SHA. Explicit recovery can
  deterministically finish that same generation without Provider replay.
  Recovery never rewrites a mismatched COMPLETED truth.

## 6. Provider and privacy boundary

- The trusted launcher owns model/device/cache/language configuration.
  JavaScript supplies no Provider settings.
- The port requires exact `faster-whisper`, a non-empty configured model and
  `allow_model_download is False`, including injected test/runtime Providers.
  No paid/cloud/network/download fallback exists.
- WebView receives only the Transcript SHA-256, stage, local execution and
  recovery booleans, plus explicit privacy booleans. Text, segments, source
  names/paths, cache/model paths, private receipts and Editing Session bodies
  do not cross the bridge.

## 7. Authority and excluded effects

This unit exposes the existing local-free transcription effect only after its
Human confirmation. It grants no model installation/download, paid/cloud
Provider, Audio Completion PASS, Resolve mutation, Export, publication,
Release or Deploy authority. Fake Provider tests are not native Evidence.

No real FasterWhisper/model execution is part of implementation verification.
Any later native execution remains a separate Owner-gated procedure.

## 8. Allowed scope

May modify the pre-edit runtime/bindings, media workflow, Shell/V6.1.1,
trusted launcher, shared Product operation read/CAS methods, direct tests and
this document. Owner separately approved the bounded TASK-006 adapter change
that preserves a POSIX `/proc/.../fd/...` stable descriptor without resolving
it back to a replaceable path; inference and download policy remain unchanged.
Must not modify TASK-003 schema, Audio, Resolve/Export, CHANGELOG, release files
or user-owned `tmp/`.

## 9. Verification

- typed prepare/apply/cancel, direct-call bypass rejection and Provider-zero
  cancel;
- same-runtime, cross-instance and cross-process exactly-one admission;
- managed Asset mismatch/symlink and stable Provider snapshot behavior;
- fixed-output symlink, checksum-valid foreign Provider, resource-bound and
  incomplete recovery rejection;
- completion-CAS failure then explicit Provider-zero recovery;
- Project-scoped recovery identity and coordinator atomic compare-and-bind;
- real trusted-launch composition with TASK-003 managed ingest, fake ASR
  transport, fixed output promotion and downstream analysis binding;
- closed bridge envelope, launch close barrier and old-bridge rejection;
- Home/generic UI routing, confirmation, busy state and refresh;
- focused regression, Python compile, embedded JavaScript syntax and diff
  scope/check.

## 10. Completion boundary

P-UX-2K ends when the visible action safely reaches local transcription,
persists exact-once state, promotes the verified fixed publication and binds
the Transcript identity. Actual native FasterWhisper execution and later
Subtitle/Cut/Resolve/Export steps remain separate gated work.

## 11. R1 recovery closure

R1 implements the successor contracts: immutable set binding, Project output
slot, exact ASR configuration identity, strict lifetime-pinned Product store,
deterministically closed shared operation connections, stable TASK-006
descriptor input, Windows held-handle hashing, and downstream managed-Asset
SHA binding. Direct tests cover interrupted fixed projection and Provider-zero
roll-forward, fabricated unbound output rejection, cross-source slot exclusion,
configuration drift, descriptor-path preservation, original picker deletion,
database identity and connection closure.

Fake-provider verification does not authorize or claim native success. Full
regression and independent implementation review remain completion gates.

Fresh-main local Evidence after merge of `origin/main` at `f6548b5`:

- impacted Product/Shell/UI/operation/ingest tests: `225 PASS`;
- Subtitle/Cut/editing/downstream compatibility tests: `52 PASS`;
- combined focused/affected result: `277 PASS`;
- changed Python compile and `git diff --check`: PASS;
- full repository collection: `NOT_CONFIRMED` because the WSL environment
  lacks the declared `referencing` dependency. No dependency was installed;
- real FasterWhisper/model/native/network execution: zero.
