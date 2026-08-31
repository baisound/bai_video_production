# TASK-065 dependency currentness reconciliation

State: `CANDIDATE_SOURCE_PRESENT / COMPLETION_RECEIPTS_MISSING / EFFECT0`

Audit base: `origin/main = 35cdf1ad475633dcf035e0616e979b5a8fde0c88`

This task-local read-only reconciliation supersedes only stale missing-source
classifications in earlier TASK-065 design freezes. It does not rewrite their
historical observations, promote a candidate to PASS, authorize PL-A source, or
write shared task/index/roadmap/current-state metadata.

## 1. Fresh dependency classification

| Gate | Current main fact | Missing completion/currentness | Admission |
| --- | --- | --- | --- |
| D0 / TASK-063 | initial installer-relative `20f5360`, read-back boundary `0b95e40` and publication race/path-safety `8fd17ed` are canonical; task status remains `OWNER_AUTHORIZED / IMPLEMENTATION_ACTIVE` | secure provision/readback operation lock; pinned descriptor+owner one-snapshot discovery; identity-CAS/no-replace descriptor/readback/snapshot publication and identity-bound rollback/temp cleanup; focused Windows fault tests; post-correction real provision/repair/upgrade installed read-back and canonical completion receipt | `SOURCE_CORRECTIONS_CANONICAL / PRODUCTION_PHYSICAL_RACE_CORRECTION_AND_INSTALLED_COMPLETION_N.C. / EFFECT0` |
| D1 / TASK-060 | PP-C candidate head `ea5d495` is an ancestor; PP-A/B/C candidate source exists; task status `PP_C_IMPLEMENTATION_CANDIDATE / INDEPENDENT_DEV4_PENDING` | independent DEV-4 acceptance; trusted pinned encrypted source readback and private single-use Production Profile publish capability replacing public token/self-hash authority; TASK-058/TASK-060 cross-owner boundary completion and canonical receipt | `CANDIDATE_PRESENT / PRODUCTION_PROFILE_AUTHORITY_N.C. / EFFECT0` |
| D2 / TASK-061 | CA-C candidate head `32c4dde` is an ancestor; CA-A/B/C disabled candidate source exists; task status `CA_C_DISABLED_HISTORY_IMPLEMENTATION_CANDIDATE / REAL_E2E_GATE_PENDING` | trusted native-backend-fixed one-use apply capability replacing forgeable public CA-B readiness/Human/E2E dataclasses and module sentinels; secure activation-lock establishment and identity-bound no-overwrite/expected-target config writer; CA-A secure migration lock, identity-CAS journal phases, no-replace Manifest/snapshot commit and owned-temp cleanup; random-challenge trusted Human one-shot receipt/atomic consume; focused Windows/authority tests and canonical completion receipt | `DISABLED_CANDIDATE_PRESENT / EFFECT0` |
| D2.5 / SKILL adapter Production transport | canonical SKILL `origin/main=c86ec8c11724a3170d37e0fdc5a516979fcca703` confirms the released adapter/default-disabled historical TASK-058 Evidence while retaining replace-capable publication, unpinned config/delivery/receipt/Profile reads, an AdmissionReceipt schema/runtime validator that accepts extra fields, and obsolete fixed-ProgramData/default-config activation instructions | separate SKILL-owner Task/Allowed Files/fresh clean main worktree; code safety plus closed exact-v1 receipt schema/runtime validation and connector-ready/SKILL workflow/interface/contract/tests/inventory alignment; canonical PR/main/release; installed exact sync/read-back and PL-A baseline hash rebind | `PRODUCTION_LINKAGE_N.C. / EFFECT0` |
| D2.5 / TASK-058 File Bridge Production safety | released File Bridge remains canonical historical Evidence; current immutable publication, security-relevant reads, mutable import/Profile journals, ordered Profile pointer/current/marker publication and pending/temp cleanup do not bind opened physical identity against races | separate TASK-058-owner corrective Unit with exact paths/symbols and amendment authority, focused fault/Windows regression, canonical main/release/install exact read-back and downstream baseline rebind | `PRODUCTION_LINKAGE_N.C. / EFFECT0` |
| D2.5 / TASK-058/TASK-060 Profile publish authority | public `PromotedPreferenceSourceRead` and `ProfileSourceBinding` token/self-hash objects can be caller-constructed and can reach the public prebuilt Profile publisher without a pinned actual promotion-source reread | explicit cross-owner corrective authority; trusted same-open-snapshot encrypted source read; private single-use late-bound Production publish capability; File Bridge ordered publication/readback correction and focused forgery/stale-source tests | `AUTHORITY_LAUNDERING_N.C. / EFFECT0` |
| D2.5 / TASK-067 | no canonical task allocation, authority or completion receipt; preserved uncommitted diff is COMMIT STOP | canonical allocation, explicit source authority, DEV-4 implementation/review and completion receipt | `N.C. / EFFECT0` |
| D2.5 / TASK-036 | packaged single-record Product-operation entrypoint completion receipt absent | TASK-061 operation plan, TASK-063 corrected installed read-back, TASK-067 cross-owner amendment/completion, exact Allowed Files/overlap/lock and installed-payload implementation plus real read-back verification | `PREREQUISITE_MISSING / EFFECT0` |
| D3 / TASK-065 | task-local Option B design candidate exists | D0-D2.5 current receipts, accepted design, implementation Gate | `SOURCE_START0` |

### Current canonical-to-installed SKILL baseline

Read-only comparison against canonical SKILL
`origin/main=c86ec8c11724a3170d37e0fdc5a516979fcca703` found zero scoped
worktree differences under `skills/bvp-montage-learning-adapter/`. The current
installed distribution copy matches these exact canonical bytes:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `scripts/bvp_adapter.py` | 53438 | `070d2295869cb43c9fe8cb733238ff04085fa6815ac006385072d9c18da3949e` |
| `config/bvp-learning-connector.json` | 406 | `da41b71292fd2a9fa2070eba531e06fafc0e84f9bbc1d26c27b0af79c5e2db6c` |
| `schemas/connector-file-bridge.schema.json` | 5812 | `470fb97a85bb924678e51a9fca313c21bc5eb9c6eb0f0f0da265ca9b6da43b9d` |
| `references/connector-ready-bridge.md` | 4758 | `669d34b4788493bb851149522d0beac1bc4a46c5f9e0b5b7b96bcab6c9faeee2` |
| `SKILL.md` | 10257 | `1a7ba2d4967cfc7bf30b5d9f64cadf77bd9b19e558a7bd11c92d9161cb9c6308` |

Classification is `EXACT_UNSAFE_BASELINE_MATCH / PRODUCTION_LINKAGE_N.C.`:
the equality proves distribution currentness for the known baseline, not the
missing transport/reader/receipt-schema/Option-B documentation corrections.
None of these hashes may be reused as the future corrected release/install PASS;
that chain requires new canonical release identities and a fresh installed-copy
read-back.

The TASK-065 PL-A docs head `66537ed` is also an ancestor of main, but its
historical audit base and missing-source statements are not current facts. This
document replaces those reason codes with candidate-present/completion-missing;
it does not change the fail-closed outcome.

Earlier TASK-063 fixtures, hashes and native Evidence predate the canonical
`8fd17ed` correction set and cannot be reused as current D0 PASS. A future PL-A
read admits only the post-correction source contract plus freshly provisioned
installed Evidence and exact completion receipt.

## 2. Read-only PP-C field map candidate

Current TASK-060 `PromotedPreferenceSourceRead` supplies these candidate inputs
for later PL-A mapping:

- `source_id`, pinned `source_file_identity_sha256` and `store_id`;
- `owner_scope_sha256`;
- `promotion_revision`, `promotion_revision_sha256` and `history_sha256`;
- `profile_id`, `profile_version` and `active_payload_sha256`;
- exactly one detached `envelope` plus `envelope_sha256`;
- `readback_sha256` over the complete read-back body;
- fixed advisory-only, no automatic promotion, no Timeline/Resolve/external
  effect flags.

PL-A may later bind this exact sealed/pinned type and hashes only after D1
completion. It must reject mutable/subclass/mapping substitutes, zero/multiple
active envelopes, stale file identity/revision/history/payload, Owner-scope
drift or any non-advisory authority. Reading current source now does not admit a
Profile or satisfy D1.

## 3. Read-only CA-B/CA-C field map candidate

Current TASK-061 candidate types expose the following potential PL-A inputs:

- `ConnectorSourceBindingReadiness`: binding/plan identity; target install
  instance; descriptor and owner-manifest hashes; security and migration
  read-backs; PP-C source/envelope hashes; TASK-058 public readiness v1 hash;
  profile ID/version/hash; publish status; final `binding_sha256`; fixed
  `SOURCE_BOUND_ACTIVATION_BLOCKED`, `connector_enabled:false` and
  `activation_authorized:false` flags.
- `InstalledAdapterE2EReadback`: target instance, source binding, connector
  status, publish receipt, Profile read-back and `adapter_e2e_sha256`. The
  current public admission rejects real-installed evidence, so this type is not
  a valid D2 completion receipt.
- `ConnectorActivationTransactionReceipt`: target instance, source binding,
  Human evidence, optional adapter E2E, revision, action/enabled state,
  `history_sha256`, `config_readback_sha256` and `transaction_sha256`, with
  repository default false and external SKILL config unchanged.

Later PL-A must require all fields from the exact factory-minted current types
and separately bind the Option B runtime-config projection receipt. It must not
construct private seals, treat the disabled history candidate as activation,
or accept a transaction without the future real-installed E2E contract and
Human authority completion.

## 4. D2.5 explicit PL-C/CA-C prerequisite

Pre-activation E2E requires both current receipts:

1. TASK-067 Generic-only sealed current/fresh/recovery/readback facade; and
2. TASK-036 packaged exact single-record `import_path` entrypoint, selected by
   a closed headless dispatch and backed by a Montage-specific private
   composition. Public `Task036LaunchConfiguration`, raw paths/hashes/revision,
   caller-selected mode and full trusted-launch/Desktop lifecycles are not
   authority inputs.

TASK-067's preserved uncommitted source/test candidate is read-only audit
Evidence only. It is neither canonical source nor a dependency PASS and must
not be imported, executed, committed, pushed or used to unblock TASK-061/036/
065. The exact freeze and future start Gate are recorded in
`task067-candidate-allocation-and-freeze-packet-2026-08-31.md`.

## 5. Re-entry/currentness ledger

Each heartbeat or future implementation preflight evaluates these independently:

| Receipt | Identity/read-back requirement | Current |
| --- | --- | --- |
| D0 completion | canonical TASK-063 physical-race correction plus real provision/repair/upgrade installed read-back | missing |
| D1 completion | independent DEV-4 PP-A/B/C acceptance plus exact PP-C read-back | missing |
| D1 Profile authority | trusted pinned source plus private one-use Production publish completion | missing/N.C. |
| D2 completion | operation-plan/real-E2E/Human activation completion | missing |
| D2.5 SKILL safety | canonical SKILL correction/release plus installed exact sync and PL-A hash rebind | missing/N.C. |
| D2.5 TASK-058 File Bridge | canonical corrective completion/release/install read-back plus downstream baseline rebind | missing/N.C. |
| D2.5 TASK-067 | canonical allocation, implementation and focused completion | missing/N.C. |
| D2.5 TASK-036 | packaged entrypoint implementation and focused completion | missing |
| TASK-065 design | Option B Critic/Judge acceptance at exact current head | pending |

No row inherits PASS from another. Shared `task.md`, roadmap, task-index,
current-state or CHANGELOG synchronization waits for its sole-Builder/LOCK
checkpoint. Until every required receipt is current, TASK-065 source/config/
adapter/native/Production effects remain zero while task-local design and
fixture planning continue.

## 6. Shared Current State drift and sole-Builder candidate

At this audit base, shared metadata is not aligned with Git/task-local facts:

- `current-state.md` says `Development Candidate: NONE`;
- `task-index.md` still labels TASK-060
  `ALLOCATION_METADATA_PENDING_IMPLEMENTATION_NOT_AUTHORIZED` and TASK-061
  `DEPENDENCY_BLOCKED_IMPLEMENTATION_NOT_AUTHORIZED`;
- TASK-063 and TASK-065 have no aligned active rows in the inspected table; and
- TASK-067 has no canonical task record, task-index row, Current State row,
  Allowed Files or implementation authority.

Candidate source being an ancestor of main is not completion or Production
authority, but shared metadata claiming implementation absence also cannot
authorize a new TASK-067 mutation lane. The preserved TASK-067 diff therefore
remains COMMIT STOP.

A future exact sole-Builder/LOCK checkpoint should reconcile, without
overstating completion:

1. TASK-060/061 as candidate-present with independent/real-E2E completion
   pending;
2. TASK-063 corrections canonical with native installed read-back pending;
3. TASK-065 dependency-gated with separate D0/D1/D2/D2.5 rows;
4. TASK-067 as either explicit COMMIT STOP design candidate or formally
   allocated task with exact owner, Allowed Files and implementation-start
   Gate; and
5. the global Development Candidate value.

TASK-065 does not write these shared files. The list is a candidate handoff,
not a reservation, Lock acquisition or current authority.
