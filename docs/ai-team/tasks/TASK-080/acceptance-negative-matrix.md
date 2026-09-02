# TASK-080 Acceptance and Negative Matrix

Status: `R1 DESIGN ACCEPTED_C_H0 / TESTS_NOT_EXECUTED / EFFECT0`

Every future implementation case records: case ID, frozen base OID/tree,
launcher/verifier/contract blob OIDs, policy readback identity, event and run
identity, expected typed result, receipt delta, state epoch delta, merge-fence
delta, public leakage, and unrelated repository delta.

## A. Bootstrap and base ownership

| ID | Scenario | Expected result |
| --- | --- | --- |
| `B01` | PR changes and immediately runs its own workflow/verifier | reject; trusted receipt 0 |
| `B02` | launcher/verifier is merged and exact main blobs are read back before ruleset admission | R0A partial readback only; R0B start0 |
| `B03` | workflow/check name matches but required-workflow source repo/branch/path or blob differs | reject |
| `B04` | base OID/tree advances after request creation | stale/effect0 |
| `B05` | historical PR head or local worktree used as base | reject |
| `B06` | organization ruleset required-workflow state not independently readable | dependency N.C. |
| `B07` | external policy mutation inferred from design approval | reject/effect0 |
| `B08` | action tag instead of immutable action OID | reject |
| `B09` | head code imported, sourced, executed, or checked out | reject |
| `B10` | write token, secret, or broader permission present | reject |
| `B11` | name-only required status check used instead of required workflow | reject/dependency N.C. |
| `B12` | required workflow source repo/branch/path or bypass actors drift | reject |
| `B13` | merge queue enabled but required workflow lacks `merge_group` | reject/dependency N.C. |
| `B14` | ruleset admission attempted before workflow exists on canonical main | reject |
| `B15` | unsigned, caller-built, self-rehashed, or wrong-key Policy Auditor envelope | reject; policy authority 0 |
| `B16` | auditor lacks complete ruleset permission or omits/truncates bypass actors | reject/dependency N.C. |
| `B17` | receipt App/installation/key ID, ruleset coordinate, workflow blob, or five-minute currentness differs | reject/stale/effect0 |
| `B18` | nonempty bypass actor list, bypass-capable merge actor, or merge-queue/event combination differs | reject |
| `B19` | Policy Auditor attempts non-GET, redirect, alternate host/path, credential export, or lacks exact private audit readback | reject; policy receipt 0 |
| `B20` | policy envelope alternate serialization/hash, unpinned or pre-activated key, revoked/dual-active key, or receipt crossing rotation | reject; policy authority 0 |
| `B21` | same GitHub repository/ref or default OIDC subject but different workflow path/SHA or reusable workflow identity | reject before broker access |
| `B22` | OIDC issuer/audience/repository owner ID/event/ref differs, or JWT is expired, replayed, or has invalid bounded time | reject before store access |
| `B23` | pull_request_target/merge_group is cross-substituted, queue ref has wrong base/malformed descendant, or signed event ref/SHA differs | reject before broker access |

## B. Git and object isolation

| ID | Scenario | Expected result |
| --- | --- | --- |
| `G01` | required base/head object missing in shallow store | fail closed/no fetch |
| `G02` | replace refs, alternates, grafts, hooks, or filters active | reject |
| `G03` | submodule/LFS/smudge/credential helper activated | reject |
| `G04` | checkout CRLF bytes differ from raw Git blob | hash raw blob; transformed bytes reject |
| `G05` | forged/incomplete object data | reject/no repair |
| `G06` | path traversal, non-ASCII alias, case collision, duplicate path | reject |
| `G07` | mode-only drift with same blob | reject |
| `G08` | extra/missing projection path | reject |

## C. R0A-R0C rollout

| ID | Scenario | Expected result |
| --- | --- | --- |
| `R01` | R0A attempts issue or consume | reject; both false |
| `R02` | R0A main blob readback or policy readback missing | dependency N.C. |
| `R03` | R0B verifier reports a candidate while disabled | report-only; acceptance unchanged |
| `R04` | R0B creates transition state | reject |
| `R05` | R0C body-free canary exact current base/head | canary Evidence only |
| `R06` | R0C uses real predecessor/candidate transition | reject |
| `R07` | preserved NO-GO exact-two-file candidate replay | reject |
| `R08` | C/H is not 0/0 at any rollout unit | commit/merge stop |

## D. Canonical receipt encoding

| ID | Scenario | Expected result |
| --- | --- | --- |
| `J01` | exact schema literal and canonical preimage | deterministic receipt hash |
| `J02` | wrong/non-string/absent schema version | reject |
| `J03` | schema version changes between phases | reject |
| `J04` | unknown/absent/empty/alternate-type field | reject |
| `J05` | object key or projection array reordered | reject/noncanonical |
| `J06` | duplicate projection path | reject |
| `J07` | caller supplies receipt or consume hash | reject |
| `J08` | receipt hash is uppercase, wrong length, or non-hex | reject |
| `J09` | manifest and dynamic receipt identities are substituted | reject |
| `J10` | canonical preimage includes terminal newline or alternate separators | reject |
| `J11` | base verifier request has unknown/duplicate field, reordered contract blobs, invalid null combination, or caller hash | reject before task evaluation |
| `J12` | signed auditor/broker projection is deserialized or rehashed into a live capability | reject; authority 0 |
| `J13` | broker request has wrong schema version, operation/audience/null matrix, body hash, unknown/duplicate field, caller request hash, or replayed nonce | reject before store evaluation |
| `J14` | broker envelope has alternate serialization, wrong signature/key/build/App/install/endpoint, stale policy, or expired issued/expiry window | reject; authority 0 |
| `J15` | broker outcome, transition receipt, generation/token/audit/fence fields do not come from one committed snapshot | reject; no trusted receipt |
| `J16` | signed R1B Broker Readiness receipt is used as a TASK-079 phase, consume, merge, or terminal receipt | reject; transition authority 0 |

## E. Monotonic state and consume

| ID | Scenario | Expected result |
| --- | --- | --- |
| `S01` | valid epoch `0 -> 1` with exact expected head | one consume |
| `S02` | valid epoch `1 -> 2` after exact main readback | terminal |
| `S03` | `0 -> 2`, `1 -> 0`, repeated `0 -> 1`, or epoch 3 | reject |
| `S04` | phase null/value combination is impossible | reject |
| `S05` | state/base/tree/manifest coordinate drifts | reject |
| `S06` | second successor or replayed consume | reject |
| `S07` | old predecessor after consume | reject |
| `S08` | public JSON is deserialized as live authority | reject |
| `S09` | broker compare token, generation, policy receipt, nonce, caller, or expected head is stale | reject; store delta 0 |
| `S10` | concurrent consume, repeated nonce, second successor, or cross-action request | exactly one winner; all others reject |
| `S11` | crash/timeout after epoch-1 commit or uncertain response | epoch1/fence retained; predecessor remains false; no replay |
| `S12` | recovery attempts a new head or predecessor reactivation | reject; same-head authoritative recovery only |
| `S13` | readiness canary leaves live fence/state, has incomplete passed-check set, or claims transition authority | readiness receipt 0; TASK-079 remains N.C. |
| `S14` | caller hash/role/audience is substituted, one peer appears in two roles, or a valid role invokes another role's operation | reject before store access; state delta 0 |
| `S15` | valid gated initialization plan, exact TASK-079 main/V3/base/policy and absent state | create exactly one epoch-0 PREDECESSOR_ACTIVE record and signed receipt |
| `S16` | second/concurrent initialization, existing state, replayed nonce, or consumed/expired plan | reject; store delta 0 |
| `S17` | initializer supplies state ID/generation/token/phase, or readiness envelope substitutes for initialization plan | reject; authority/state 0 |
| `S18` | initialization TASK-079 blob/manifest/base/tree/policy/caller binding differs | reject; plan remains unconsumed; store delta 0 |

## F. Merge fence and currentness

| ID | Scenario | Expected result |
| --- | --- | --- |
| `M01` | unrelated merge before consume | normal policy outside fence |
| `M02` | unrelated merge after consume before terminal | blocked |
| `M03` | successor head differs at merge time | blocked/stale |
| `M04` | merge succeeds, terminal readback unavailable | epoch1/fence held/unknown |
| `M05` | atomic predecessor invalidation unavailable | exclusive fence required |
| `M06` | timeout or rerun attempts to reactivate predecessor | reject |
| `M07` | terminal readback exact and current | epoch2; fence release candidate |
| `M08` | terminal main OID changes or is caller supplied | reject |
| `M09` | Main Merge has no fresh signed broker admission for exact head/generation/fence owner | merge blocked |
| `M10` | broker heartbeat expires or process dies during epoch 1 | fence remains logically held; no automatic unlock |
| `M11` | canonical main contains expected head after uncertain merge | same-head recovery terminalizes once |
| `M12` | canonical main does not contain expected head after uncertain merge | epoch1 remains current; separate recovery required |
| `M13` | merge admission has wrong audience/operation, is older than 30 seconds, or does not bind current generation/fence/policy | merge blocked |
| `M14` | broker key/build/App/install/endpoint pin changed without canonical pin/readback rotation | merge blocked; old and new identities rejected |
| `M15` | terminal/recovery request supplies caller-observed main OID, or unmerged recovery fabricates terminal truth | reject; broker authoritative readback only; epoch1 remains fenced when unmerged |

## G. Privacy, authority, and unrelated effects

| ID | Scenario | Expected result |
| --- | --- | --- |
| `P01` | error includes token, secret, absolute host path, or payload body | reject/redact |
| `P02` | workflow requests write permission or secret | reject |
| `P03` | design receipt treated as implementation/merge authority | reject |
| `P04` | external ruleset mutation attempted without separate gate | effect0 |
| `P05` | Release, Tag, Deploy, Production, Provider, model or native effect | effect0 |
| `P06` | unrelated source/docs/worktree changed | fail scope check |
| `P07` | an OIDC role lacks `id-token: write` or requests a non-broker audience | dependency N.C.; trusted receipt 0 |
| `P08` | workflow has extra GitHub write permission/secret or logs, caches, artifacts, echoes, or exports OIDC request/token data | reject; public leakage 0 |

## H. Required verification bundles

### Design R1

- frozen byte/hash/size/line identities for exact four documents;
- `git diff --check`;
- exact-path scope check;
- two independent reviews, both Critical/High `0/0`.
- R1A and R1B wire-contract review covers canonical envelope hashes, key
  bootstrap/rotation, GET-only enforcement, operation/audience/null matrices,
  readiness/transition separation, and signature/currentness failures.

### TASK-064 R0A-R0C

- syntax/static validation for workflow/verifier/contracts;
- focused bootstrap, disabled, canary, receipt and Git-isolation tests;
- all `B`, `G`, `R`, `J`, `S`, `M`, and `P` negatives applicable to the unit;
- targeted metadata/source-gate regression;
- post-main base-owned blob and external-policy readback;
- independent Critic, Tester, and Judge Critical/High `0/0`.

### Real transition

Not authorized by TASK-080 R1 design. A later Atomic Unit must bind the
accepted TASK-079 V3 manifest, a fresh signed R1A Policy Auditor receipt,
terminal TASK-064 control-plane receipts, the independently accepted signed
R1B Broker Readiness receipt, the admitted R1B durable Transition Broker, an
Owner/Main-Merge-gated signed `PREDECESSOR_INITIALIZED` epoch-0 receipt, an
operation-specific signed broker envelope, exact current main, exact successor
head, and Main Merge fence.
