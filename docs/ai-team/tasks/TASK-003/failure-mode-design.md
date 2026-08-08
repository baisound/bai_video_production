# TASK-003 — Failure Mode Design

| Failure | Required behavior |
|---|---|
| source outside allowlist / symlink | reject before Job state transition |
| source mutates during copy | remove staging, reject integrity |
| empty source | reject; no Registry row |
| ffprobe missing/timeout/bad media/type mismatch | reject before Registry commit with explicit provider/input code |
| duplicate checksum, same metadata | return existing Asset idempotently/deduplicated |
| duplicate checksum, conflicting rights | human review required; do not overwrite canonical rights |
| atomic target collision with different bytes | integrity failure |
| failure after promotion before Registry | remove only newly promoted target; preserve raw source |
| failure after Registry before manifest/evidence | retain Asset; mark operation PARTIAL and allow source-free metadata repair |
| hard process death after Registry | recover Asset by producer operation binding |
| registered target missing/tampered during repair | refuse repair; keep PARTIAL with explicit integrity error |
| concurrent ingests | unique manifest revisions; latest pointer cannot roll backwards |
| pending manifest reservation | never exposed as current canonical manifest |
| same idempotency key bound to another command | explicit integrity conflict |
