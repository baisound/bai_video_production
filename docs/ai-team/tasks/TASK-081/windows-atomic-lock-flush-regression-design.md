# TASK-081 Windows Atomic Lock Flush Regression — Design

## Bound failure

GitHub run `33604510933`, Windows Python `3.12.10`, failed only
`test_actual_multiprocess_same_path_serializes_one_success`. The spawned child
raised `PermissionError: [Errno 13]` at
`exclusive_file_update_lock`'s initial `handle.flush()`.

The old order is:

```text
open/create lock
-> observe empty
-> buffered marker write + flush
-> seek byte zero
-> acquire OS lock
```

That order permits two fresh contenders to perform an unprotected byte-zero
initialization. On Windows, one contender may acquire the byte-zero range
after its flush while the other's delayed flush still targets that range.

## Corrected state transition

```text
open/create lock
-> seek byte zero
-> acquire OS lock
-> observe size while locked
-> if empty: write marker through an unbuffered handle
-> rewind
-> enter consumer critical section
-> rewind and unlock
-> close handle
```

Windows `msvcrt.locking` can lock byte zero of a zero-length regular file. It
was verified directly with the bundled Windows Python 3.12 runtime. The same
lock-first pattern is already used by the Product snapshot lock.

## Failure and recovery rules

- Open/create failure: no handle and no consumer effect.
- Acquisition failure: close only; do not initialize, unlock, or enter body.
- Empty-marker write failure after acquisition: unlock and close; do not
  enter body. A later caller re-observes actual size under the lock.
- Existing marker: preserve bytes; use byte zero solely as the lock range.
- Consumer exception: unlock and close, then re-raise unchanged.
- Unlock/close errors are not converted into success or currentness evidence.
- Symlink or nonregular lock path is rejected before body execution.

The correction does not promise hostile namespace-race protection, durable
lock metadata, lock deletion detection, or an uncooperative-writer CAS. Those
are outside this cooperative sibling-lock primitive and are not inferred from
successful acquisition.

## Test strategy

1. Instrument the Windows branch to prove acquisition occurs before marker
   write and release occurs after the body.
2. Inject acquisition failure and prove no marker or unlock action occurs.
3. Exercise initial empty, existing marker, body exception/reacquisition,
   synchronized same-path contention, symlink and nonregular paths.
4. Synchronize the two real spawned TASK-029 consumers at the lock boundary and
   retain the exact one-success/one-terminal expected result.
5. Run atomic, TASK-029 consumer and relevant sibling-lock regression, followed
   by independent DEV-4 review.
