# TASK-072-A A1 Schema and Public Audit Implementation Evidence

Date: 2026-09-03 JST

Result: `PASS` for A1 source scope only

TASK-072-A completion: `NOT_CONFIRMED`

## Bound Scope

- Unit: `A1 SCHEMA_AND_PUBLIC_AUDIT`
- Base and local HEAD before commit: `4d233c8c77c7328f5b221642040faf06c0a6a15c`
- Branch: `codex/task-072-a-op-ticket-core-design-r0`
- Worktree: `task-072-a-op-ticket-core-design-r0`
- Accepted design SHA-256:
  `397BB12A8C6DE72F5DF691006F071314916D6BC2BD01D7DB8D85798B74173DBC`
- Fresh `origin/main`: `4d233c8c77c7328f5b221642040faf06c0a6a15c`
- Open PR overlap: `0`; PR #514 touches TASK-068/secure-authority paths and
  PR #513 touches TASK-046 voice paths only.

This unit contains schemas, packaged mirrors, immutable authority-zero public
audit objects, strict bounded validators and fixtures. It contains no ticket,
reservation publication, broker registry, child process, native handle,
filesystem mutation or Production authority.

## Exact Source and Evidence Hashes

| Path | Raw SHA-256 |
|---|---|
| `docs/ai-team/tasks/TASK-072/op-ticket-core-v1-detailed-design.md` | `397BB12A8C6DE72F5DF691006F071314916D6BC2BD01D7DB8D85798B74173DBC` |
| `src/ai_video_production/product_operation_broker.py` | `0B7BCFD9BC25DF4E2DCC0D4DFC88753FA5912750E8CAD5798DC25BD6BF566D6F` |
| `src/ai_video_production/product_operation_config.py` | `4A8F962ADDA0A9B7528703F040162995C0EE6A96E2A759B2FFDCF7897A4991DB` |
| `schemas/product-operation-ticket.schema.json` | `5DADD143FDEFAF04B7ACB577AC7938F69DB0C6B59FD224BE6B598EB941D16449` |
| `schemas/product-operation-config.schema.json` | `C03B403E1B0648CBF7E93CB171000CCB5FAEF8E1D2E3A8C5E50602AF47C1679E` |
| `schemas/product-operation-receipt.schema.json` | `94B412263E78601429AA9DFB286E2453BB7E0BB4DBB15C807071D967752373D6` |
| `src/ai_video_production/schema_resources/product-operation-ticket.schema.json` | `5DADD143FDEFAF04B7ACB577AC7938F69DB0C6B59FD224BE6B598EB941D16449` |
| `src/ai_video_production/schema_resources/product-operation-config.schema.json` | `C03B403E1B0648CBF7E93CB171000CCB5FAEF8E1D2E3A8C5E50602AF47C1679E` |
| `src/ai_video_production/schema_resources/product-operation-receipt.schema.json` | `94B412263E78601429AA9DFB286E2453BB7E0BB4DBB15C807071D967752373D6` |
| `tests/test_task072_product_operation_broker.py` | `1771D04B57D2EE33F050DE741C7FD285FCD279D7F151D5E87D18ADA91E0EF6F4` |
| `tests/test_task072_product_operation_config.py` | `F27E41E45ED9C838CF869226A06F1FCE61BD13E4BC9F80E4928D285B17A9F79C` |
| `tests/fixtures/task072/operation-port-v1/action-profiles.json` | `E7511D5C67FD1A089F7FA9BCF3030AB982816132BB6E079D21F9A7817E545127` |
| `tests/fixtures/task072/operation-port-v1/ticket-schema-vectors.json` | `E885156571531DCE2A8B3243802CD6502CC88EE5A96EAE87126D42DA86BDAD78` |

Each root schema and packaged resource has the same raw hash. All five JSON
schema/fixture documents parse with the built-in JSON parser.

## Verification

Focused command:

```text
python -m pytest tests/test_task072_product_operation_broker.py tests/test_task072_product_operation_config.py -q
```

Result: `107 passed, 5 skipped, 0 failed`.

The five skips are the Draft 2020-12 schema execution checks. The current
Python runtime does not contain the declared project dependency `jsonschema`,
so executable JSON Schema plus `FormatChecker` validation is
`NOT_CONFIRMED`; it is not reported as PASS. No dependency was installed.

Additional checks:

- `compileall`: PASS for both source and focused test modules;
- root/resource schema byte identity: PASS for all three pairs;
- built-in JSON parse: PASS for schemas and fixtures;
- `git diff --check`: PASS;
- source effect scan: filesystem/subprocess/native/broker-ticket effects `0`.

## Independent Assurance

- Design Judge: `PASS`, Critical/High `0/0`, exact design hash verified.
- Independent Tester: `PASS`, Critical/High/Medium `0/0/0`.
- Implementation Critic: `GO`, Critical/High/Medium `0/0/0`.

## Remaining Gates

- TASK-068 current accepted completion and exact API/version binding are still
  required for real A2 reservation publication, A4 config publication/readback
  and A6 completion.
- A2/A3/A4/A5 require their own exact source allocation before mutation.
- Windows native/package execution, real child launch, installer effect,
  Release, Deploy and Production Activation remain `NOT_EXECUTED` and outside
  this A1 result.
- This evidence must not be relabeled as TASK-072-A completion or as a
  TASK-063 U6 authority receipt.
