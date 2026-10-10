# TASK-074 R19 Independent Review Receipt

Status: `REVIEW_FAILED / TESTER_FAIL / CRITIC_REVISE / JUDGE_WITHHELD / EFFECT0`

Date: `2026-10-11`

Reviewed Git HEAD: `8246792e6e475bf98d54b0cc14c2cd890f62a7f5`

Review target: `TASK074-R19-ACYCLIC-RUNTIME-AND-EXACT-FAILURE-V1`

## Exact reviewed bytes

| File | SHA-256 |
| --- | --- |
| `docs/ai-team/tasks/TASK-074/complete-design-packet-r19-acyclic-runtime-exact-failure.md` | `E0989AC7CE1365B4C9BA70F60CFD80477A7D16C40B151DF39FD23D087FA72C7D` |
| `docs/ai-team/tasks/TASK-014/d4-three-phase-runtime-contract-r19.md` | `C4D3AC87368E1DD1054015193D454CF82FB0274BE75C0EB264587896F3FAF294` |
| `docs/ai-team/tasks/TASK-074/r19-direct-transfer-runtime-phases-contract.md` | `1DA5DEC22F5CFF51DDF216B258ED50CAB360A59102659C748699EB12C45B9BCC` |
| `docs/ai-team/tasks/TASK-041/audio-completion-pass-contract-r19.md` | `B0BFDF1BC50BB9022FF2F875D319FC752622C2BA3412F8E709D97BF57AE57026` |
| `docs/ai-team/tasks/TASK-036/audio-completion-exclusive-binder-contract-r19.md` | `F76D7225D0897C0DFB5519A380E2933268376471ACA85D74E4C008223DB13899` |
| `docs/ai-team/tasks/TASK-014/task.md` | `62F95370BBF2EF72CA8136C99B2375852ABDCB1BB2464F9F2E5D741F807EA01C` |
| `docs/ai-team/tasks/TASK-074/task.md` | `BFF6A522C4ECE0C30E71FCC21CA64D646AC99C269FF09B2CBA3F3B3FED2AD790` |
| `docs/ai-team/tasks/TASK-074/design-r18-independent-review-receipt.md` | `39EEC9556C44CCE9A63E5A24EA5639103ECF54E3A69F049CB8F76C9CDCE8B9EF` |

Pinned dependencies also matched:

- TASK-075 complete design:
  `2F35E01A6EC3BAFB4703E74CC4DBA34EBFC972157AFDF26B07C61F064B5D7B3B`;
- TASK-076 complete design:
  `C2B94DCA029EDB2BE8E3024A65BCD2E0A171E68E12E478EB3834DEDD7588BF86`.

## Independent results

The independent DEV-4 Tester returned `FAIL`, with
`Critical/High/Medium/Low = 0/3/0/0`. The independent Critic returned
`REVISE`, with `0/3/1/0`. The final Judge was correctly withheld because High
findings remained.

Both reviewers independently confirmed that the source, positive-runtime and
failure-runtime graphs were syntactically acyclic, the eight-file scope and
hashes matched, `git diff --check` passed, and repository/native/private/audio/
model/provider effects were all zero.

## Unresolved findings

1. R19 began a TASK-014 call-dispatch lease before TASK-076 arm even though the
   exact arm ABI had no such input and canonical TASK-075 section 9.5 begins
   call dispatch only after `ARTIFACT_PREPARE_PENDING`. A metadata-only pre-arm
   reservation and an exact four-owner adapter amendment were required.
2. The pre-arm lease had no complete terminal state machine for arm rejection
   or unknown, orphan/prebootstrap/bootstrap rejection, bind/preflight failure,
   prepare abort/failure, release rejection, restart or reply loss.
3. R19 incorrectly required a TASK-075 success result together with
   `TASK075_NONCURRENT_OPERATION_TERMINAL_UNION_V1`, although that exact union
   excludes `RESULT_BOUND` and forbids D4 result/POST. Success, noncurrent,
   aborted and burned-unknown branches had to be distinct tagged branches.
4. Known-no-child acceptance admitted only aborted readbacks and omitted exact
   `JOB_CHILD_REJECTED_READBACK_V3` and
   `JOB_CHILD_BOOTSTRAP_REJECTED_READBACK_V3` known-no-process results.
5. Restart rules omitted the canonical DISPATCHING-current unselected-orphan
   exception for `abort_armed_orphan_job_child_v3`.
6. The owner acceptance envelope did not enumerate an exact R19 key set or fix
   path form, digest case and the domain separator as one byte `0x00`.

## Decision

R19 is immutable rejected Evidence. It grants no owner acceptance, source,
runtime, child/process, private handle/body, model, audio/WAV, publication,
ledger PASS, Final Review PASS, Release, Deploy or Production authority. R20
must receive a fresh exact-byte independent review.
