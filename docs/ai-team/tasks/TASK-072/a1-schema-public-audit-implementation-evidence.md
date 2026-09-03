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
| `schemas/product-operation-ticket.schema.json` | `A295CF7E867D67A68203434A60CB30E53A083E462E53887A78E9D207F6BA98B6` |
| `schemas/product-operation-config.schema.json` | `596BA93A39F75B9933E3B6922B36C5EFDBCCEFE10B2EC814974D02BA61698ACD` |
| `schemas/product-operation-receipt.schema.json` | `61E48985DE8B7414FF5DAC38CF737ED498786A6F3F10DCFBD62E59D0A6312A13` |
| `src/ai_video_production/schema_resources/product-operation-ticket.schema.json` | `A295CF7E867D67A68203434A60CB30E53A083E462E53887A78E9D207F6BA98B6` |
| `src/ai_video_production/schema_resources/product-operation-config.schema.json` | `596BA93A39F75B9933E3B6922B36C5EFDBCCEFE10B2EC814974D02BA61698ACD` |
| `src/ai_video_production/schema_resources/product-operation-receipt.schema.json` | `61E48985DE8B7414FF5DAC38CF737ED498786A6F3F10DCFBD62E59D0A6312A13` |
| `tests/test_task072_product_operation_broker.py` | `BF973014D74912F7875C580F6AC84922CF9B489C1E3D68D831B3BDCA11E2F1E9` |
| `tests/test_task072_product_operation_config.py` | `57E0F32E53E216637DEFAC2060E63296709844C75B2C31D59073D73F2AF51765` |
| `tests/fixtures/task072/operation-port-v1/action-profiles.json` | `E7511D5C67FD1A089F7FA9BCF3030AB982816132BB6E079D21F9A7817E545127` |
| `tests/fixtures/task072/operation-port-v1/ticket-schema-vectors.json` | `E885156571531DCE2A8B3243802CD6502CC88EE5A96EAE87126D42DA86BDAD78` |

Each root schema and packaged resource has the same raw hash. All five JSON
schema/fixture documents parse with the built-in JSON parser.

## Verification

Focused command:

```text
python -m pytest tests/test_task072_product_operation_broker.py tests/test_task072_product_operation_config.py -q
```

Result in the default local runtime: `107 passed, 5 skipped, 0 failed`.

The five skips are the Draft 2020-12 schema execution checks because the
default local Python runtime does not contain the declared project dependency
`jsonschema`. An isolated temporary validation environment using Python
3.13.14, `jsonschema` 4.26.0 and `pytest` 9.1.1 executed the same focused
command with result `112 passed, 0 skipped, 0 failed`.

CI run `33707958266` exposed that a `date-time` format checker may be inert
when its optional validation dependency is unavailable. The original ticket
and receipt schema tests therefore accepted an impossible calendar date. The
successor change makes ticket, config and receipt UTC fields independently
calendar-complete for years 0001 through 9999, including Gregorian leap-year
rules, and directly tests all three with no format checker.

Additional checks:

- `compileall`: PASS for both source and focused test modules;
- root/resource schema byte identity: PASS for all three pairs;
- built-in JSON parse: PASS for schemas and fixtures;
- `git diff --check`: PASS;
- source effect scan: filesystem/subprocess/native/broker-ticket effects `0`.

## Independent Assurance

- Design Judge successor verdict: `GO`, Critical/High/Medium `0/0/0`.
- Independent Tester successor verdict: `PASS`, Critical/High/Medium `0/0/0`.
- Implementation Critic successor verdict: `GO`, Critical/High/Medium `0/0/0`.

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
