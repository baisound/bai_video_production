# TASK-001 Failure-Mode Design

| Failure mode | Detection | Fail-safe behavior | Recovery evidence |
|---|---|---|---|
| stale Job revision | conditional DB update / expected version | reject mutation | error envelope + observed state |
| illegal state transition | state transition table | reject mutation | allowed targets recorded in error details |
| process crash before manifest promotion | injected/real exception before `os.replace` | prior canonical remains intact; temp removed | retry can regenerate deterministically |
| path traversal / symlink escape | lexical + canonical root check | reject path | security error; no I/O outside allowlist |
| duplicate command delivery | unique idempotency key | return existing operation | same Operation ID proves no duplicate reservation |
| checkpoint inputs changed | input/profile/manifest hash comparison | refuse resume; side state/version stay unchanged | integrity error requiring re-plan/re-run |
| crash during resume bridge | atomic repository update | no durable `RESUMING` intermediate state; either side state remains or target commits | state revision consumes two logical transitions |
| unknown/blocked asset rights | Asset contract | auto-use disabled | later gate must request human/legal decision |
| automation targets human timeline | ownership guard | reject write | authorization error |
| secret/raw path enters canonical manifest | recursive payload guard | reject manifest creation | validation failure before write |
| Evidence correction | append-only writer | original retained; replacement linked | supersession link preserves lineage |
| SQLite interruption | WAL + transaction scope | partial transaction not committed | reopen store and verify canonical row state |
| newer MAJOR schema | SemVer compatibility rule | require migration/adapter | migration decision artifact |

| Manifest payload mutated by caller after creation | canonical payload snapshot + checksum binding | returned copies cannot mutate canonical envelope | regression test proves stable serialized content/checksum |
| Asset URI points to a different Job | Asset constructor cross-field validation | reject Asset record | no cross-Job persistence |
| checkpoint/current Profile substituted by caller | compare against DB-bound Job Profile Snapshot | reject resume and checkpoint persistence | integrity error; side state unchanged |

## Recovery boundary

TASK-001 proves recovery contracts locally. It does not claim real Resolve/Windows/cloud recovery. Those require later integration-specific evidence.
