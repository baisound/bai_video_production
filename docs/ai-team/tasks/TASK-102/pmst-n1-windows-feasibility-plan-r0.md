# TASK-102 PMST-N1 Windows Feasibility Plan R0

Status: `N1A_PASS / N1B_BLOCKED_PRIVILEGE / OVERALL_NOT_CONFIRMED`

## 1. Decision target

PMST-N1 answers whether the current supported Windows host can supply the native primitives required by the accepted PMST-D0/D1/I1 contracts. It is an isolated proof harness, not the Product broker, service installer, Project enrollment flow or writer migration.

Top-level results are `PASS`, `FAIL` or `NOT_CONFIRMED`. N1 completes only when the service-SID exclusion boundary and every mandatory primitive pass. A non-elevated N1A PASS with N1B blocked remains `NOT_CONFIRMED`, while still preserving useful primitive Evidence.

## 2. N1A native primitive matrix

The harness must fail before effects unless its new run root is an exact operation-owned child beneath the resolved system temporary root and is neither a drive root nor a direct child of a drive root.

| Area | Required proof | Rejection result |
|---|---|---|
| topology | fixed local NTFS volume; no reparse root/control/manifest; stable volume/file identity | `UNSUPPORTED_TOPOLOGY` |
| root/control exclusion | pinned non-inheritable handles without delete sharing block rename/delete of the run and control directories from a second process | `BARRIER_UNPROVEN` |
| manifest exclusion | pinned handle denies foreign write/delete; replacement seam occurs only after the manifest handle is intentionally released while ancestor barriers remain held | `BARRIER_UNPROVEN` |
| replacement | exact predecessor bytes/identity, durable stage, handle-bound same-volume replacement, exact successor bytes/new identity | `REPLACEMENT_UNPROVEN` |
| durability | successor file `FlushFileBuffers` and parent directory `NtFlushBuffersFile` succeed and exact bytes survive reopen | `DURABILITY_UNPROVEN` |
| crash/recovery | PREPARED witness before the seam; predecessor, successor and ambiguous/missing evidence map only to the accepted closed outcomes | `RECOVERY_UNPROVEN` |
| DACL topology | task-owned control directory has protected inheritance and a read-back-stable descriptor; no foreign existing ACL is changed | `ACL_TOPOLOGY_UNPROVEN` |
| local IPC | explicit protected security descriptor, first-pipe-instance protection, remote-client rejection and server/client PID readback | `PIPE_IDENTITY_UNPROVEN` |

All reports are body-free: digests, opaque run IDs, stable result codes and non-secret platform facts only. No raw descriptor, token, path, handle, manifest body or OS error text enters repository Evidence.

## 3. N1B service-SID matrix

N1B requires an elevated execution context. It uses one random service name prefixed `BvpTask102PmstN1-`, a helper located inside the owned run root and an explicit service SID. It must prove:

1. exact installed service/image/configuration readback;
2. control-root DACL grants mutation only to the service SID while the interactive Owner retains admitted read/traverse;
3. ordinary-user and same-user peer write/delete/rename are rejected;
4. the service process can perform only the closed harness operation and reports its PID/token/service-SID binding;
5. the named pipe admits the pinned service/client pair, rejects a second creator and exposes exact process identities;
6. service stop/delete and owned-root cleanup succeed, or every residual is recorded and preserved for Human recovery.

`sc.exe create` access denial in a non-elevated context is an effect-zero `BLOCKED_PRIVILEGE`; it is not a service feasibility PASS or FAIL. No UAC bypass, credential request, account creation or mutation of an existing service is allowed.

## 4. Crash seams and claims

The harness covers child termination before replacement, immediately after replacement and after terminal witness persistence. It may prove observed old/new namespace and witness reconciliation under its contained topology. It must not claim physical power-loss durability from process-kill tests alone. Power-loss remains `NOT_CONFIRMED` unless a separate destructive reboot laboratory is explicitly authorized.

## 5. Exit

N1A exits with focused pure tests, a real Windows contained run, exact report hashes, zero unknown residuals and a reviewed diff. N1B exits only with exact elevated Evidence or a precise `BLOCKED_PRIVILEGE` record. PMST-I2 writer migration remains blocked until mandatory N1 results are accepted; no partial enrollment or fallback writer is authorized.

## 6. Observed result — 2026-09-27

PMST-N1A run `20260927-n1a-final-007` is `PASS`. It exercised every N1A matrix row in an operation-owned system-Temp root and copied/read back its body-free report from the canonical external TASK-102 Evidence root. The report file SHA-256 is `3eba567cc83001211174f34e06924de91f67cda8a0bcbcd726ca27c44e867692`. Pure plus direct PMST-I1 regression is `78 PASS`.

The current host token is not elevated, so PMST-N1B is `NOT_CONFIRMED / BLOCKED_PRIVILEGE`. No `sc.exe create`, service configuration, existing ACL mutation, Product Project mutation or UAC bypass was attempted. An elevated N1B run remains mandatory before PMST-N1 completion or PMST-I2 allocation.
