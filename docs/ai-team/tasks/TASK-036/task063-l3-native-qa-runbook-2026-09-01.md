# TASK-063 L3 Native QA Runbook (Parked)

Runbook version: `task063-l3-native-qa-runbook/v1`
Current state: `NOT_AUTHORIZED / DO_NOT_EXECUTE`

## Preconditions for a future authorized run

- TASK-063 owner supplies the exact candidate commit, signed package/build
  manifest, native helper identity, Allowed Files and terminal-handoff schema.
- A clean disposable Windows/NTFS QA profile and an explicitly owned isolated
  installation root are allocated; no existing Product/user installation is
  used.
- The test-only barrier/fault port is proven unreachable from Production.
- Exact commands, target, rollback, evidence location and cleanup identities
  receive the required native/Human gate.
- No Provider, paid service, private media, secret, Release, Deploy or
  Production Activation is involved.

Without every precondition, execute nothing and retain the JSON fixture as
synthetic expected Evidence only.

## Future procedure

1. Pin and attest the QA root, ancestors, volume, DACL/owner, build manifest,
   helper and TASK-063 operation plan before creating state.
2. Provision only operation-owned synthetic descriptor/owner data using opaque
   instance IDs. Record exact opened identities privately.
3. For I63-NQA-01 and I63-NQA-02, start two separate worker processes and hold
   them on the named test barrier. Release simultaneously; never emulate
   concurrency by sequential calls in one process.
4. For I63-NQA-03 through I63-NQA-09, inject exactly one seam per fresh
   operation. Replacement objects are created by the QA controller with known
   foreign identities and must never be deleted or overwritten by TASK-063.
5. After each seam, pinned-read descriptor, owner, journal, receipt, lock, temp,
   selected root and unrelated sentinel objects. Compare mutable operation
   artifacts to the scenario-specific exact postcondition. Compare unrelated
   and designated foreign sentinels to their exact precondition bytes and
   identities.
6. A directory durability failure, ambiguous state, security drift, foreign
   replacement or post-publish mismatch yields no PASS/completion receipt.
7. Reconciliation uses a fresh authoritative resolver. Do not retry the same
   in-flight capability or replay a possibly committed operation.
8. Cleanup only objects whose exact identities are journal-bound as created by
   the current operation. Preserve every unknown/foreign replacement.

## Evidence and stop conditions

Record machine-readable private Evidence per matrix ID plus one public
body-free projection. Stop immediately on path/SID/error leakage, unrelated
delta, missing barrier, helper/build drift, ancestor/DACL drift outside the
injected scenario, or inability to prove cleanup identity. Preserve the whole
isolated QA root for owner review; do not repair, delete, or rerun.

PASS requires all nine scenarios, independent Tester/Critic/Judge, exact
package/helper readback and a trusted TASK-063 terminal completion receipt.
Partial results remain `NOT_CONFIRMED` and cannot unblock TASK-036.
