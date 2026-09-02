# TASK-081 Acceptance and Negative Matrix

| ID | Fixture | Expected result | Filesystem / authority result |
|---|---|---|---|
| WIN-F01 | Two fresh Windows contenders observe a zero-length lock | OS byte-zero lock is acquired before either raw marker write; both complete serially | One `b"0"` marker; consumer result exact; no currentness authority |
| WIN-F02 | Instrumented empty unbuffered handle | `lock -> write -> body -> unlock` order | No pre-lock or deferred write |
| WIN-F03 | Lock acquisition raises access/contended error | Body, marker write and unlock are not called | Handle closes; target effect zero |
| WIN-F04 | Raw marker write raises after acquisition | Original error propagates after unlock and close | Consumer body effect zero; later acquisition remains possible |
| LOCK-E01 | Existing nonempty regular lock | Lock and body succeed without rewriting marker | Existing bytes preserved |
| LOCK-E02 | Body raises | Original body exception propagates after release | Next caller can acquire |
| LOCK-P01 | Lock path is directory or symlink | Fail before lock body | Target and foreign symlink target unchanged |
| CONS-01 | Two synchronized spawned TASK-029 R9D consumers | Exactly one `SIGNED_AND_VERIFIED`, one `ERR_KNOWLEDGE_PACK_SIGNING_ALREADY_FINAL` | Historical R9D semantics unchanged |
| SCOPE-01 | Changed-file audit | Exact seven Allowed Files only | Shared metadata and unrelated source delta zero |

Every result is technical evidence only. No Release, Deploy, Production,
provider, native, external-account, historical-task, or Product-currentness
authority is created.
