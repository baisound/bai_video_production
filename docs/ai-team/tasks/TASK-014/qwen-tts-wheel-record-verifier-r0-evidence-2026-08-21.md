# TASK-014 — Qwen-TTS Wheel and Installed RECORD Verifier R0 Evidence

Date: `2026-08-21`
Status: `DIAGNOSTIC_OBSERVATION_COMPLETE / JUDGE_ACCEPTED / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Scope and authority

The Owner authorized free local model/runtime artifact download and execution,
TASK-014 design and implementation, and the mandatory procedure. This Atomic
Unit may retain the one exact public `qwen-tts 0.1.1` wheel and implement a
read-only verifier that compares that wheel's RECORD contract with the existing
isolated installed distribution. It does not install or import the wheel, start
the target Python, load model weights, read Owner audio or execute inference.

This observer can record only a bounded, non-atomic read observation of the
`qwen-tts` distribution. It cannot issue the complete
`RUNTIME_REUSE_VERIFIED` decision, which also requires accepted
receipts for Python, PyTorch, Torchaudio, Transformers, Accelerate, Hugging Face
Hub, SoundFile/native library, ffmpeg, ffprobe and every required dependency.

## Official retained-wheel coordinates

- source authority: PyPI JSON API for `qwen-tts 0.1.1`
- filename: `qwen_tts-0.1.1-py3-none-any.whl`
- package type: `bdist_wheel`
- size: `113,529` bytes
- SHA-256:
  `11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d`
- Python requirement: `>=3.9`
- yanked: `false`
- retained public-artifact destination:
  `E:\BAI_AI\downloads\TASK-014\qwen_tts-0.1.1-py3-none-any.whl`

The direct file URL is bound to the PyPI API response and is used only for this
exact filename, byte count and digest. No dependency resolver or install command
is used.

## Existing installed-distribution observation

The target Python was not executed. Trusted host tooling observed the exact
`qwen_tts-0.1.1.dist-info` metadata only:

- metadata name/version: `qwen-tts 0.1.1`
- wheel tag: `py3-none-any`
- retained wheel ZIP / RECORD rows: `24 / 24`
- wheel-trusted hashed rows: `23`
- wheel RECORD unhashed row: `1`
- installed RECORD rows: `45`
- installed hashed rows: `27`
- unhashed installed rows: `18`
- unhashed rows consist of the RECORD row and `17` generated
  `__pycache__/*.cpython-312.pyc` rows
- the `4` installed-only hashed rows are pip-generated artifacts:
  `Scripts/qwen-tts-demo.exe`, `INSTALLER`, `REQUESTED` and `direct_url.json`
- the wheel-trusted `entry_points.txt` binds the console entry point
  `qwen-tts-demo = qwen_tts.cli.demo:main`; it does not bind the generated
  launcher executable bytes
- direct requirements declared by METADATA: Transformers `4.57.3`, Accelerate
  `1.12.0`, Gradio, Librosa, Torchaudio, SoundFile, SoX, ONNX Runtime and Einops

These observations do not yet prove installed-tree integrity.

## Required verifier boundary

The implementation must use a separately trusted verifier runtime and remain
read-only. It must validate the retained wheel bytes and archive shape, parse
the wheel RECORD without extraction or import, safely reconcile every
wheel-trusted hashed row against the explicit installed distribution,
separately observe but never trust the exact four pip-generated hashed
artifacts, allow only the RECORD row and bounded generated CPython 3.12 cache
rows as unhashed installed additions,
reject path escape/reparse/case collision/missing/extra/size/hash/race, and emit
only a body-free receipt.

The generated launcher, pip metadata and bytecode caches remain untrusted even
when their current bodies match the installed RECORD. Their bodies may be
hashed into non-authoritative observation digests, but they cannot contribute
to the wheel-trusted row count or authorize runtime execution. The
`direct_url.json` body and any local path it contains must never be exposed in
the receipt, Evidence or diagnostics.

## Execution Evidence

- official PyPI coordinate read: `PASS`
- retained wheel download: `PASS`
  - only the exact PyPI-bound URL was used
  - download used a new task-owned partial file followed by same-parent rename
  - partial file no longer exists
- retained wheel size/SHA-256: `PASS`
  - bytes: `113,529`
  - SHA-256:
    `11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d`
- retained-wheel acquisition independent Acceptance: `PASS`
  - unresolved Critical / High / Medium findings: `0 / 0 / 0`
  - ZIP opened read-only without extraction: `PASS`
  - archive entries: `24`
  - unsafe or duplicate archive paths: `0`
- verifier implementation: `IMPLEMENTATION_CHECKPOINT_COMPLETE / UNCOMMITTED`
  - authorized files only: verifier module, public/resource schemas, focused test
    module and this Evidence record
  - implementation performs only stream reads and temporary synthetic-fixture
    tests; it exposes no install/import/provider/network/subprocess/extraction
    operation
  - exact receipt boundary is `BOUNDED_NONATOMIC_WHEEL_PAYLOAD_OBSERVATION_ONLY`;
    `QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE` is diagnostic only
  - public projection redacts private path fingerprints, receipt/observation
    digests and `direct_url.json` content
- final focused pytest: `37 / 37 PASS`
- final related focused regression: `97 / 97 PASS`
- prior hardening history: focused `17 / 17`, then `22 / 22`; synthetic success
  route `24 / 24`; related regression `82 / 82` across three runs
  - transient false-race failures in the earlier implementation were reproduced,
    rejected and fixed before the final results above
  - static/schema mirror/Draft 2020-12/diff/scope checks: `PASS`
  - actual retained-wheel / installed-runtime observation remains `NOT_EXECUTED`
  - receipt self-hashes protect receipt integrity only; they do not establish
    verifier origin or runtime authenticity
  - both private and public receipts are diagnostic supporting Evidence only;
    neither is a next-AU gate input and neither can authorize reuse or dispatch
- Acceptance H / Architecture-Judge A: the verifier is explicitly a bounded
  non-atomic mutable-tree observation. Its COMPLETE decision is
  `QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE`, never a runtime-authentication or
  reuse decision. Post-return state is not guaranteed; actual E remains
  diagnostic-only and cannot satisfy runbook §5.1 or a next-dispatch gate.
- static/manual checks: `PASS`
  - WSL Python `py_compile` passed for the verifier module
  - synthetic parser/receipt construction and unsafe-relative-root guard passed
  - synthetic wrong-pin wheel check returned `WHEEL_PIN_MISMATCH` before the
    missing runtime root was accessed
  - public and package schema resources are byte-identical and JSON-parseable
- actual installed-tree observation: `QWEN_PAYLOAD_READ_OBSERVATION_COMPLETE`
  - final revalidation time: `2026-08-20T18:16:05.0495750Z`
  - receipt SHA-256:
    `sha256:f5ebc22130735d497075aca30bca9a9ee57a9cf2d72ecd78749730d6915737e0`
  - wheel members / wheel RECORD rows / trusted payload reads: `24 / 24 / 23`
  - installed RECORD rows / pip-generated observations / untrusted cache rows:
    `45 / 4 / 17`
  - trusted payload inventory digest matched the admitted constant: `true`
  - reason codes: none
  - first launch attempt stopped before observation because the trusted observer
    environment lacked its already-isolated `jsonschema` dependency; target
    Python and the qwen package were not executed. The dependency path used by
    the accepted test environment was then supplied and the observation ran.
  - a first successful diagnostic receipt used a fixed example timestamp and
    was not selected as final Evidence; the final receipt above is a fresh
    re-observation with the actual UTC evaluation time
  - `tree_mutability`: `MUTABLE_UNLOCKED`
  - `post_return_state_guaranteed`: `false`
  - `authoritative_runtime_gate`: `false`
  - `immutable_snapshot_verified`: `false`
  - `locked_handles_held_through_consumer`: `false`
  - `consumer_revalidation_required`: `true`
  - `runtime_reuse_authorized`: `false`
  - both private and public receipts are diagnostic supporting Evidence only;
    neither can satisfy runbook §5.1, a next-AU gate or dispatch authority.
    Receipt self-hashes do not prove verifier origin or runtime authenticity.

## No-effect record

- dependency resolved/installed: `false`
- target Python executed: `false`
- target package imported: `false`
- model loaded: `false`
- Owner audio read: `false`
- inference executed: `false`
- Firewall changed: `false`
- native audio application invoked: `false`
