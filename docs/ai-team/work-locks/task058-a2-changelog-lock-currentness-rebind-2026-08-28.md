# TASK-058 A2 CHANGELOG Lock Currentness Rebind

Date: 2026-08-28
Unit: TASK-058/A2-CANONICAL-READBACK-LOOKUP-CHANGELOG-LOCK-CURRENTNESS-REBIND
Authority: OWNER_BROAD_APPROVAL_KNOWN_PENDING_GATES_20260828
Status: LOCAL_CANDIDATE_NOT_HOSTED

## Canonical base and active lock

- canonical main: `ed23c7ff1e8a9525edef76432fa7c49a79b7fef6`
- Registry revision: `131 -> 132`
- active nonclosed integration lock: exactly one, `BVP-INTEGRATION-LOCK-TASK058-A2-CANONICAL-READBACK-LOOKUP-CHANGELOG-20260828`
- no new lock is added
- allowed shared effect remains exactly `CHANGELOG.md`
- integration authority, target merge authority, implementation authority, denied effects, expiry conditions, merge order, release condition and automatic flags are unchanged

## Target currentness correction

PR #417 remains open and Draft on remote head
`6d5ea807abed184e5320ef7afa98d2d46c76972d`. Its Hosted run
`33115922397` passed five of six CI jobs; Windows 3.11 alone failed the
process-wide HANDLE strict-equality oracle even though HANDLE count decreased.
Security run `33115922439` passed two of two and Release metadata run
`33115922447` passed one of one. This is not recorded as all-green Hosted
Evidence for the replacement candidate.

The exact local replacement candidate is
`ce174bc3f90c1d89ac47f8ef5dacdabe1a22f89d`. Its direct ancestry is:

```text
ce174bc3f90c1d89ac47f8ef5dacdabe1a22f89d
  -> 6d369b8cc0f4c29bc1553f80d4652280dfc67907
  -> 6d5ea807abed184e5320ef7afa98d2d46c76972d
```

The complete `6d5ea80..ce174bc` delta is one test path only:

`tests/test_task058_montage_learning_canonical_admission_transaction.py`

- Git blob: `9be0aefa563a4b91498bcf5de863f1c65921000d`
- file SHA-256: `24bc3661dfe6fadccd83630864b1f86e8a12a07cb5a9aba9d7941593eace974e`

The resource-local spawned-child oracle preserves explicit close and
double-close assertions, repeats the successful transfer three times, proves
no owned object remains open and does not fail on unrelated ambient HANDLE
cleanup. The fault-path exactly-once ownership assertions remain unchanged.

Independent DEV-4 re-Judge result for the exact candidate is C/H/M/L
`0/0/0/0`, Technical GO. Independent Windows execution recorded ownership and
path `19 PASS`, focused `59 PASS / 2 platform skips`, and direct dependency
`381 PASS / 2 platform skips`. Full local Product execution remains not
claimed; the next Hosted run remains required.

## Exact Registry delta

- `registry_revision`: `131 -> 132`
- `expected_pre_integration_head`: `cea711c... -> 6d5ea80...`, the exact
  current remote PR head at revision 132 activation
- `target_pull_request_state`: updated to distinguish the current remote
  `6d5ea80` Hosted result from the unpushed local `ce174bc` candidate
- `ce174bc` and its exact replacement test path, Git blob and SHA-256 are
  separately bound as typed pending-approved coordinates, not as the current
  remote head
- prior remote PR head and CI, Security and Release metadata run identities are
  bound as pre-rebind Evidence
- audit-only rebind provenance records revision 131, canonical base, branch,
  Evidence path, exact parent chain and independent verification
- the one-shot transition policy and the post-Hosted second-amendment
  requirement are typed explicitly

No other active-lock semantic field is changed.

## Effect boundary and continuation

This amendment performs no CHANGELOG, source, schema, design, Task, B+C,
runtime, native, Timeline, Resolve, Release, Deploy or Production effect. It
does not push PR #417 and does not make it Ready or merge it. It does not mint
implementation or shared-effect authority.

The continuation order is closed:

1. Host and read back revision 132 while PR #417 still has exact remote head
   `6d5ea80`. Before push, `TARGET_HEAD_MISMATCH` compares the remote head with
   `expected_pre_integration_head`, so the canonical amendment does not expire
   itself.
2. After that read-back only, push exact pending-approved head `ce174bc` once,
   without force or retry. During this bounded transition,
   `TARGET_HEAD_MISMATCH` compares the remote head with
   `target_currentness_pending_approved_head_sha`.
3. Run Hosted checks on exact `ce174bc`. Any different head, failed required
   check or attempted retry fails closed.
4. After exact Hosted terminal success, host a second bounded amendment that
   changes `expected_pre_integration_head` to `ce174bc` and binds the exact
   Hosted check coordinates.

Until step 4 is merged to main and read back, PR #417 Ready, merge and any new
shared effect remain prohibited. The existing `TARGET_HEAD_MISMATCH` expiry
condition and every other authority, denial, expiry and ordering field remain
unchanged.
