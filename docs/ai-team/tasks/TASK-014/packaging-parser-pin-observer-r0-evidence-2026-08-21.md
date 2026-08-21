# TASK-014 Packaging Parser Pin Observer R0 Evidence

Status: JUDGE_ACCEPTED / ACTUAL_METADATA_OBSERVATION_COMPLETE / PIN_ACCEPTANCE_BLOCKED / FRESH_MAIN_VALIDATED / COMMIT_READY / UNCOMMITTED

## Atomic Unit

- Unit: AU2C2B1b0-B network-observer implementation and one bounded diagnostic observation.
- DEV depth: DEV-4.
- Exact scope: observer module, public schema, packaged mirror, focused tests, this Evidence.
- Input dependency: merged proposed verifier contract from PR #204 / main `385082ecfbdda39b93586bca27dfd6770a8819bd`.

## Exact effect boundary

The public operation is limited to one scheduled `GET https://pypi.org/pypi/packaging/25.0/json` request. It sends no credential, permits no redirect, requests identity encoding, reads at most 1 MiB of response body, and incrementally bounds the complete response-header block to 64 KiB, 128 fields and 8 KiB per line. It performs no artifact-body request, filesystem write, install, import of `packaging`, target runtime execution, E: access, model operation, or audio read.

Before HTTP bytes are accepted, the production port requires every DNS answer to be IPv4/IPv6 and globally routable, rejects mixed/private or more than 32 answers, and records overflow as a bounded 32-plus fact rather than an impossible exact count. It attempts at most the first four canonical addresses, connects directly without proxy fallback, validates the default TLS trust chain for `pypi.org`, and requires the connected TLS peer to be one of the resolved addresses. Socket/TLS/HTTP work after DNS has one 30-second deadline; the remaining time is recomputed before every send/receive, and there is no automatic retry after a completed or partially sent request. A DNS, connection, TLS or response ambiguity fails closed.

The receipt records monotonic phase facts separately: request scheduled, request send state (`NOT_ATTEMPTED`, `UNKNOWN_PARTIAL`, or `COMPLETE`), request completely sent, complete headers observed, complete body observed, bounded DNS count/overflow/globality, TLS verification and connected-peer membership. Content-Length is mandatory and exact; Transfer-Encoding and Content-Length/Transfer-Encoding ambiguity are rejected. BLOCKED and UNKNOWN receipts retain observed phase facts, discard incomplete response bytes, and must round-trip through both the strict parser and schema. The ordinary receipt self-hash does not authenticate whether the native transport or a synthetic test seam produced those facts; `native_transport_origin_authenticated=false` is mandatory and later acceptance must bind independent execution Evidence.

## Same-response verification

The observer uses one bounded response byte sequence to verify:

- strict UTF-8 JSON with duplicate/non-finite rejection;
- exact project `packaging`, version `25.0`, Requires-Python `>=3.8`;
- empty vulnerability list;
- exactly one matching wheel candidate;
- exact filename, size, SHA-256, core-metadata SHA-256, canonical files.pythonhosted.org URL, `bdist_wheel`, `py3`, non-yanked state.

## Receipt authority

Even a complete observation forces `pin_acceptance_authorized=false`, `artifact_body_observed=false`, `persistent_receipt_is_capability=false`, and download/import/resolver/install/runtime/model/audio authorities false. The receipt self-hash is serialization consistency only. A later Judge-bound acceptance artifact must bind the exact observer identity/revision, response digest and receipt digest before the proposed pin becomes an accepted resolver dependency.

## Verification

- pre-execution DEV-4 Tester and Critic/Judge: `C0 / H0 / M0`, exact one-shot diagnostic GET GO;
- after the one-shot observation, an independent self-audit identified unexpected native-exception escape paths; these were normalized into phase-appropriate UNKNOWN receipts without another network request;
- fresh-main base/HEAD before Unit commit: `3a76e05e2a9fec27a902e76ebe2533b125936480`;
- fresh-main focused pytest: `62 PASS` in `2.10s`;
- fresh-main related TASK-014 trust-chain regression: `368 PASS` in `12.91s`;
- schema mirror, syntax compile without bytecode write, and diff-check: PASS;
- current module SHA-256: `2f101bc05542ff46fa017e6fe7ed85b27673fc2eca6dbb32f4dfab800dbd11d0`;
- current public/mirror schema SHA-256: `c8eecb290563457d76c4494adb012571752d6da9cb821ce38f5a1357c22d5d42`;
- current focused-test SHA-256: `41c2c34f3d75fe95e4511034a496effce67f92b8be3b4e853046f142f06ad27c`;
- post-actual independent Tester: `C0 / H0 / M0`, PASS;
- post-actual independent Critic/Judge: `C0 / H0 / M0`, PASS.

## Actual one-shot diagnostic observation

The Owner's active sleep-window PC-operation authority was rebound by the pre-execution DEV-4 Judge to exactly one credential-free, no-redirect, no-retry `GET https://pypi.org/pypi/packaging/25.0/json`. It was executed once. The same returned receipt passed the strict application parser and Draft 2020-12 schema validation in that process.

- actual-execution observer/schema identity: `bai.task014.packaging-parser-pin-observer` revision `1` / `bai.task014.packaging-parser-pin-observation.v1`;
- actual-execution module SHA-256: `f2df82e5ac33e727152bfe0d2204c30cf89e6587813fbf4b9f769c372f178cd6`;
- actual-execution schema SHA-256: `41ddf7c1121fa95f04014d73a65c1a79f5a0ac2fdc53260a46b8313efd903924`;
- invocation identity: bundled Codex Python called public `observe_official_packaging_250_metadata` once, then `parse_packaging_pin_observation` and Draft 2020-12 validation on the returned mapping;
- evaluated_at: `2026-08-21T02:25:03.6616761Z`;
- decision: `OFFICIAL_PACKAGING_PIN_OBSERVED_DIAGNOSTIC`;
- reason_codes: none;
- request scheduled/sent: `1 / 1`, send state `COMPLETE`;
- resolved address count: `4`, overflow `false`, all global `true`;
- connected peer in resolved set / TLS verified: `true / true`;
- response headers/body complete: `true / true`;
- redirect count / credentials sent: `0 / false`;
- content type / response bytes: `application/json / 5,501`;
- response SHA-256: `sha256:6ab300d7b0735a50109912decebb1731ed292f1ed88a3ce5e4bb7876b182cac0`;
- receipt SHA-256: `sha256:79428d15daa597a3abe4be25df4c0d03be6d50e438631a6341a4675e264ad122`;
- official metadata observation complete: `true`;
- native transport origin authenticated / pin acceptance authorized: `false / false`.

No second request was scheduled or attempted. The later source hardening is explicitly versioned as observer revision `2`, schema `bai.task014.packaging-parser-pin-observation.v2`, with receipt-domain separation `TASK014_PACKAGING_PIN_OBSERVATION_V2`. It cannot be confused with or used to regenerate the historical revision-1 receipt. The later source and tests are bound to the observed receipt only as implementation Evidence; they do not retroactively authenticate the transport, authorize the proposed pin, or replace the exact one-shot result.

## No-effect checkpoint

- actual metadata network request: exactly one bounded GET executed; no retry;
- artifact body download/install/import: false;
- E:/target runtime/model/audio access: false;
- Product repository/runtime filesystem mutation outside the exact five-file worktree scope: false.

## Isolated development-test dependency procedure

Owner's active sleep-window instruction explicitly allowed required PC operations and installations, with a procedure document sent to the BAI Development OS secretary. The pre-existing temporary pytest directory had become unreadable, so a replacement was installed only into:

`C:\Users\user\AppData\Local\Temp\bvp-task014-pytest-8.4.2-r1`

Procedure executed from the bundled Codex Python, not the Product target runtime:

```powershell
$target = 'C:\Users\user\AppData\Local\Temp\bvp-task014-pytest-8.4.2-r1'
New-Item -ItemType Directory -Path $target -ErrorAction SilentlyContinue | Out-Null
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m pip install --disable-pip-version-check --no-input --target $target `
  pytest==8.4.2 jsonschema==4.25.1
```

- pip reported successful isolated installation and used cached wheel payloads; whether it performed metadata-only index traffic is NOT_CONFIRMED because `--no-index` was not used;
- Product dependency files, target Python and system site-packages were not modified;
- tests used this directory only through `PYTHONPATH`; sandboxed reads of its package subdirectories are denied by the managed environment, so the exact successful test commands were executed under the Owner-authorized operation boundary rather than claiming ordinary sandbox reproducibility;
- no cleanup/delete is authorized or performed by this Unit; the exact temporary directory remains available for reproducibility.
