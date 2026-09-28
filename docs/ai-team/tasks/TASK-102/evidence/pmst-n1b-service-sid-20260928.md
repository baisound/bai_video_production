# TASK-102 PMST-N1B Service-SID Evidence

- Final run: `20260928-n1b-final-007`
- Result: `PASS`
- External Evidence identity: `TASK-102/pmst-n1/20260928-n1b-final-007`
- Report file SHA-256: `deea6770c9499d72319dd022dde6dec6d943432251ff836636f7ad86e573e446`
- Checkpoint file SHA-256: `4e8237a9886a51d71669334ec62bc2352a5a2fb4d1791549a7677d569f82d730`
- Residual matching test services after completion: `0`

## Proven behavior

1. A random prefixed service was create-new, configured as a demand-start own-process service with unrestricted service SID, and its exact image, account, start, type and SID configuration were read back before start.
2. The service ran only the copied bounded helper inside the unique Machine Temp run root.
3. Exact DACL readback found four explicit non-inherited allow ACEs: Full control only for the service-specific SID, and ReadAndExecute plus Synchronize for SYSTEM, Administrators and the interactive user.
4. The live service token contained the expected service SID and created the exact proof object.
5. The peer controller was rejected when attempting create, overwrite, delete and control-directory rename.
6. The explicit protected named pipe exercised first-instance rejection, remote-client rejection configuration and mutual server/client PID readback.
7. The exact test service stopped and was deleted. No matching test service remained.

## Recovery history and limits

- `20260928-n1b-native-001`: `SERVICE_CONFIG_FAILED`; exact service deletion `PASS`.
- `20260928-n1b-native-002`: virtual-account service start access denied; protected DACL and peer-create rejection passed; exact service deletion `PASS`.
- `20260928-n1b-native-003`: Machine Temp ruled out user-Temp parent traversal as the cause; virtual-account service start still denied; exact service deletion `PASS`.
- `20260928-n1b-native-004`: LocalSystem plus unrestricted service SID topology `PASS`; this exposed the remaining need for explicit installed-config readback.
- `20260928-n1b-final-005`: explicit config readback plus the functional matrix `PASS`.
- `20260928-n1b-final-006`: exact DACL comparison correctly rejected the test's incomplete RX constant; exact service deletion `PASS`.
- `20260928-n1b-final-007`: corrected RX plus Synchronize comparison and the complete matrix `PASS`.
- PMST-I1 plus N1 focused regression: `85 PASS`.
- N1A native regression after the N1B changes: `PASS`.
- Physical power-loss durability: `NOT_CONFIRMED` and not claimed.
- Real Project writes, existing service or ACL mutation, Product enrollment, Release, Deploy and Production effects: none.

The canonical external Evidence retains the exact resolved paths, body-free report, checkpoint and intentional Temp residual identities. This public-safe record contains no raw SID, service name, pipe name, ACL body, Project body or private absolute path.
