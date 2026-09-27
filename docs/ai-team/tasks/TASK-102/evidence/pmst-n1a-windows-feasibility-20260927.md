# TASK-102 PMST-N1A Windows Feasibility Evidence

- Run: `20260927-n1a-final-007`
- Result: `PASS`
- Environment class: supported Windows host, fixed local NTFS, unique system-Temp child
- Native report file SHA-256: `3eba567cc83001211174f34e06924de91f67cda8a0bcbcd726ca27c44e867692`
- Native report self-commitment: `sha256:2f4285c5c3ba52d1e5a7bd96b48dec76639846f870bd2d6789ff2174b6edfc32`
- External Evidence identity: `TASK-102/pmst-n1/20260927-n1a-final-007`

## Observed proofs

1. Root, control and manifest were newly created under one operation-owned system-Temp child on fixed NTFS; live handles reported no reparse point and the manifest had one link.
2. Non-inheritable root/control handles denied delete sharing. The non-inheritable manifest handle denied write and delete sharing. A second process observed five required rename/write/delete rejections.
3. The staged successor was flushed, then renamed by its DELETE-capable live handle over the predecessor on the same volume. The successor had the exact expected bytes and a different physical identity.
4. `FlushFileBuffers` on the successor and `NtFlushBuffersFile` on the control directory both succeeded; exact successor bytes survived reopen.
5. Process termination before replacement classified exact predecessor plus PREPARED as `NOT_COMMITTED_PROVEN`; termination after replacement and after terminal witness both classified exact successor as `COMMITTED_WITH_READBACK`.
6. The task-owned control directory used a protected, non-inheriting DACL whose descriptor digest remained stable through final readback.
7. The local named pipe used an explicit protected descriptor and remote-client rejection flag. With capacity for a second ordinary instance, a second `FILE_FLAG_FIRST_PIPE_INSTANCE` creator was rejected specifically with `ERROR_ACCESS_DENIED`. Server and client each read back and matched the peer process ID.

## Verification and limits

- `tests/test_task102_windows_feasibility.py`: `13 PASS`
- PMST-I1 plus PMST-N1 focused regression: `78 PASS`
- Python syntax compilation: `PASS`
- Real Product Project writes, service registration, existing ACL mutation, Release, Deploy and Production effects: none
- Physical power-loss durability: `NOT_CONFIRMED`; process termination does not prove it
- PMST-N1B service-SID exclusion: `NOT_CONFIRMED / BLOCKED_PRIVILEGE` because the available host token was non-elevated
- PMST-N1 overall: `NOT_CONFIRMED`; PMST-I2 remains blocked

The exact resolved Temp and external Evidence paths, checkpoint, full body-free JSON report and intentional residual list remain in the canonical external Evidence run. No private voice, media, Project body, SID, raw ACL, pipe name or absolute private path is committed here.
