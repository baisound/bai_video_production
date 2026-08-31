# TASK-067 historical coverage and missing-fixture mapping

Date: 2026-08-31

State: read-only comparison; TASK-067 `SOURCE_START0 / COMMIT_STOP / EFFECT0`

## 1. Fixed inputs and interpretation

This mapping compares two non-authoritative inputs:

- BVP `origin/main` at `35cdf1ad475633dcf035e0616e979b5a8fde0c88`,
  especially `montage_learning_canonical_admission_transaction.py` and
  `test_task058_montage_learning_canonical_admission_transaction.py`;
- the preserved, uncommitted TASK-067 candidate in
  `codex/task-067-generic-review-operation`, whose only paths remain the
  bounded canonical amendment, `montage_learning_generic_operation.py`, and
  `test_task067_generic_review_operation.py`.

The TASK-058 tests are historical regression inputs. The preserved tests are
candidate diagnostics. Neither set is a TASK-067 completion receipt, and
neither permits source mutation, commit, push, PR, TASK-036 execution or any
Production effect. A row below remains `N.C.` until its missing fixtures run
against the formally allocated implementation and record every delta/leakage
column from the mandatory matrix.

Preserved candidate identity at comparison time:

| Path | SHA-256 |
|---|---|
| `src/ai_video_production/montage_learning_canonical_admission_transaction.py` | `3f7a1d55e8b74954a21aac738cfda9fa36aecca02c0705e30e397e72ca2c163f` |
| `src/ai_video_production/montage_learning_generic_operation.py` | `b225142bc12bac651a3c36ff62adebf4c388070b5efbfd9426ffe0766fded26f` |
| `tests/test_task067_generic_review_operation.py` | `c956236749d597558e88ba7661495e61c3da19d7919d233f1d4cd750f4d515a4` |

## 2. Coverage-to-gap mapping

| ID | origin/main historical source/test evidence | Preserved candidate evidence | Reusable classification | Missing fixture required for corrective acceptance | Current result |
|---|---|---|---|---|---|
| G67-A01 | `_exact` and `test_raw_mapping_snapshot_and_scalar_subclasses_fail_before_authority` reject raw/subclass ambiguity at the TASK-058 store boundary; `test_generic_and_exact_namespaces_cannot_cross_replay` covers lane separation. | `GenericReviewOperationFactory`, `_SealedDocument`, `ValidatedGenericReviewDelivery`, `GenericReviewCurrentCoordinateReceipt` and `GenericReviewRecoveryCapability` exist, but the tests construct `_BoundProject` and pass module `_SEAL` directly. The factory and sealed document types are exported in `__all__`. | Reuse TASK-058 raw-tree and cross-lane negatives only. Candidate token/seal behavior is evidence of the gap, not authority. | Direct/copy/deepcopy/pickle/deserialize/duck/subclass/module-token/public-`__all__` attempts for factory, delivery, coordinate and recovery capability; each must prove capability 0 and full Project/Bridge/Profile/config/history delta 0. | `N.C.` |
| G67-C01 | `test_multiprocess_generic_same_cas_has_one_accepted_and_cleans_journal` and `test_multiprocess_generic_and_exact_project_writes_serialize` cover store-level contention; recovery tests cover durable convergence. | `test_fresh_operation_commits_once_then_immediate_verify_has_no_extra_effect` proves one positive commit and rejects a second get. Candidate state names are mode/result labels such as `COMMITTED_RESULT_BOUND`, `RECOVERED_RESULT_BOUND` and `CLOSED`; there is no tested entry-time `IN_FLIGHT` plus exception-time `FAILED_CLOSED` transition. | Reuse store contention and terminal convergence as lower-layer regression. Positive facade test covers only the no-extra-effect get path. | Every facade method after: same-object retry, concurrent double call, validation failure, underlying throw, commit-then-throw and get/readback throw. Assert `ARMED -> IN_FLIGHT -> COMPLETED|FAILED_CLOSED`, invocation count, and later effect 0. | `N.C.` |
| G67-M01 | `test_pinned_read_rejects_equal_size_target_substitution`, `test_pinned_read_is_non_inheritable_and_rejects_ancestor_identity_drift`, `test_generic_trusted_reader_rejects_payload_object_substitution`, `test_generic_currentness_validates_every_historical_artifact`, lock-substitution tests and `test_windows_junction_root_is_rejected` provide strong historical physical-currentness coverage. | `_path_probe`, `_project_journal_state`, `_read_locked_current` and `_read_current_coordinate` collect identities; only `test_broken_generic_lock_symlink_is_not_treated_as_absent` directly attacks a preserved physical path. Candidate reads still compose manifest/journal results from helpers rather than demonstrating one pinned manifest+journal snapshot receipt. | Reuse physical fault fixtures and historical artifact enumeration. | Manifest and Project-save journal: stat-open, read-post and valid-lock-time swaps; same bytes/project ID on a different inode; hardlink/nlink; ancestor reparse; mixed-generation manifest/journal. Bind opened bytes, canonical hashes and identities in one receipt; failure preserves all state. | `N.C.` |
| G67-L01 | `test_store_initialization_requires_existing_product_authority_without_writes`, `test_store_initialization_rejects_product_lock_substitution_without_writes`, invalid/unsafe/FIFO/check-open Generic lock tests and Windows handle-transfer tests cover existing-lock rejection and no-effect lookup. | `_read_current_coordinate` distinguishes absent/existing, while `test_empty_project_current_coordinate_is_revision_zero_without_effect`, `test_existing_empty_generic_lock_is_accepted_without_effect` and the broken-symlink test cover read-only classification. `_prepare_empty_authority_for_admission` prepares directories, but the preserved tests do not prove secure initial lock publication. | Reuse existing-lock classifiers and no-create read/status assertions. | CREATE_NEW/nofollow one-byte initial lock under pinned ancestors; post-open regular/nlink1/reparse/DACL verification; absent-to-foreign race and one fresh loser classification; safe-empty/prior lock, orphan/nonempty/case collision; before/after creation seams and exact-own cleanup. | `N.C.` |
| G67-S0 | No origin/main test models a durable Bridge pending item with canonical Generic journal absent. Existing fresh-admission and recovery tests begin at the canonical store boundary. | No preserved test covers `PRECOMMIT_RESUME`; the candidate factory requires the caller to choose fresh/recovery/readback construction. | No fixture is activation-eligible. Lower-layer fresh admission may be reused only after the resolver selects S0. | S0a pending-after-durable/before-journal, S0b before recover entry, S0c before/after initial lock, S0d unrelated canonical revision and S0e same record/different digest; resolver must choose fresh exactly once and prove Bridge correlation/receipt/pending deltas plus old-object burn. | `N.C.` |
| G67-S1 | `test_generic_prepared_journal_recovers_to_byte_identical_accept` covers the parameterized journal/project/marker/pre-cleanup seams; `test_crash_after_project_commit_republishes_exact_prepared_receipt`, `test_crash_after_anchor_write_before_participant_result_recovers` and later exact/generic interleaving tests cover lower-layer recovery ordering. | `test_terminal_recovery_returns_duplicate_then_bound_verify_without_effect` covers one already-terminal lookup. It does not inject after facade entry/result capture, Bridge receipt publication or pending cleanup, and does not prove the old facade burns on every seam. | Reuse canonical recovery seam fixtures and expected byte-stable terminal results. | S1a-S5 facade/Bridge seams: journal phases, Project commit/manifest advance, object/ledger/marker/readback, facade return-before-get, correlation, public receipt and pending cleanup. Record typed ACCEPTED/DUPLICATE and exact Project/Bridge deltas at each seam. | `N.C.` |
| G67-A2 | `test_generic_lookup_is_read_only_and_closes_outer_correlation_restart_window`, wrong/missing-coordinate tests, pending/corrupt-journal rejection, incomplete-tail rejection, outer-receipt-without-commit rejection, equal-revision tamper/rollback rejection and multiprocess read-only lookup are reusable A2 foundations. | `test_verified_readback_restart_uses_noncreating_a2_lookup` and `test_terminal_recovery_returns_duplicate_then_bound_verify_without_effect` prove two positive read-only terminal paths. | Strong historical positive/negative lookup foundation; preserved positive candidate only. | With Generic journal absent: exact one terminal entry -> typed DUPLICATE; orphan object/marker, multiple match, unknown entry, stale head, mismatched manifest/binding/ledger/object and same-bytes-different-inode -> STOP_PRESERVE/EFFECT0. One same-snapshot receipt must bind every artifact. | `N.C.` |
| G67-R01 | TASK-058 exposes distinct `admit_generic_observation`, `recover_generic_observation` and `get_verified_generic_observation`; it has no Product resolver for Bridge pending/correlation precedence. | `fresh_operation`, `recovery_operation` and `verified_readback_operation` are separate caller-selected factory methods. No preserved test proves fixed resolver precedence or rejects caller-selected mode before effect. | Method-specific lower-layer behavior may be reused after trusted resolution only. | Durable precedence fixture: existing correlation, pending, nonterminal journal, exact terminal entry and empty state combinations; caller mode ignored; method-mode mismatch burns capability; race between resolve and entry produces effect 0 and never auto-refreshes. | `N.C.` |
| G67-B01 | origin/main TASK-058 canonical tests operate on Generic mappings already supplied to the store; they do not prove TASK-036 Bridge actual mapping provenance. | `validate_delivery` builds `ValidatedGenericReviewDelivery` before facade creation, and facade methods compare a caller mapping again. No BridgeApplication/TASK-036 actual mapping fixture or invocation counter exists. | Schema/store validation is reusable only after the trusted Bridge mapping is late-bound. | TASK-036 operation binds actual pending file/record/digest at facade entry exactly once; prevalidation mapping, raw JSON factory, repeated bind, wrong pending, and identity swap before entry all burn with effect 0. | `N.C.` |
| G67-D01 | `test_generic_observation_namespace_accept_duplicate_and_collision` records Project deltas; Generic lookup tests prove read-only Project state and no outer Bridge receipt creation. These are direct-store, not real Bridge integration, tests. | All seven preserved tests are Project-root tests. Positive tests use `_snapshot_inventory(project)` and therefore show direct facade Bridge delta 0 only indirectly; no separate Bridge inventory participates. | Reuse Project inventory helpers and direct facade no-extra-effect assertions. | Two explicit modes: direct facade with complete Project and separate Bridge inventories proving Bridge 0; real TASK-036 integration permitting only exact correlation/public-receipt add plus matching pending removal, with unrelated Bridge, Profile, config and history deltas 0. | `N.C.` |
| G67-X01 | `test_schema_mirror_and_runtime_documents`, exact/generic namespace isolation, multiprocess serialization, generic-child/exact-receipt stability and exact-retry-after-generic tests form the historical canonical regression floor. | Preserved canonical amendment adds `_generic_operation_store` and an optional expected-manifest precondition to Generic admission. No preserved test traces `BridgeApplication.import_path`, exact method order, public receipt serialization or the complete TASK-058 suite. | Reuse the named TASK-058 exact/generic regression set and compare the bounded canonical amendment symbol-by-symbol. | Trace the unmodified BridgeApplication call sequence; assert no repeated/skipped/reordered calls, no Exact-lane/public-receipt/Profile/Timeline widening, stable serialization, and focused plus relevant TASK-058 regressions with Critical/High findings 0. | `N.C.` |

## 3. Resulting fixture queue

The comparison closes one planning unknown: origin/main already supplies most
of the lower-layer canonical currentness, recovery and concurrency fixtures,
but it supplies none of the trusted Product resolver, TASK-036 Bridge mapping,
private capability or full cross-root delta proof. The preserved candidate
adds seven positive/read-only facade diagnostics, not the missing authority and
fault matrix.

The implementation-start fixture order is therefore:

1. G67-A01/C01 private authority and burn-state negatives;
2. G67-M01/L01 physical snapshot and secure-initial-lock negatives;
3. G67-R01/B01 resolver and late-bound Bridge mapping;
4. G67-S0/S1/A2 recovery and crash matrix;
5. G67-D01/X01 direct-versus-integration deltas and full bounded regression.

This queue does not change the canonical dependency graph:

```text
TASK-061-A -> TASK-067 -> TASK-036 -> TASK-061-B -> TASK-065
```

The former whole-task TASK-061 prerequisite is SUPERSEDED. TASK-067 remains
blocked on its formal start dependencies and explicit bounded cross-owner
amendment; the preserved source stays untouched.

## 4. Restart read-back validation

After the Owner-authorized PC-restart resume, the mapping was re-read against
the same pinned inputs before any further effect:

- TASK-065 worktree HEAD and upstream both remained
  `d247ed702083393567661f9117e5f43dad3cbd1f`;
- TASK-067 HEAD/upstream remained
  `35cdf1ad475633dcf035e0616e979b5a8fde0c88`, and all three preserved file
  hashes remained byte-identical to section 1;
- each of G67-A01/C01/M01/L01/S0/S1/A2/R01/B01/D01/X01 occurred exactly once
  as a mapping row;
- all 23 backticked `test_*` symbols in the mapping resolved to the pinned
  origin/main TASK-058 test or the preserved TASK-067 candidate test;
- every dirty TASK-065 path remained under
  `docs/ai-team/tasks/TASK-065/`, `git diff --check` reported no error, and no
  conflict marker was present; and
- `ACTIVE-WORK-LOCKS.json` contained no TASK-065 or TASK-067 entry. The GitHub
  API overlap query was unavailable under the sandbox network policy and was
  not retried; local upstream identity plus the existing TASK-065 Draft PR
  record are the bounded available evidence, not a remote-overlap PASS.

This is static mapping validation only. Executed TASK-067 tests, source
authority, dependency completion and Production evidence remain zero/N.C.
