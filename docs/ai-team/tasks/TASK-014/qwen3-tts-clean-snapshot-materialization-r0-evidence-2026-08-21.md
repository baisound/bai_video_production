# TASK-014 — Qwen3-TTS Clean Snapshot Materialization R0 Evidence

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / COMMIT_READY / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Authority and scope

The Owner authorized local free-model weight download and execution, identified
`E:\BAI_AI` as the AI artifact root, and authorized TASK-014 design and
implementation. This Atomic Unit does not download weights because the existing
local bodies already passed exact digest verification. It may only copy the 13
accepted public model files into a new task-owned clean snapshot leaf and verify
that leaf read-only.

No existing model root is deleted, cleaned, renamed or modified. No package is
installed or imported into the target runtime. No model is loaded. No Owner
audio is read. No inference, Firewall change, provider call, REAPER operation or
iZotope operation is performed.

## Bound coordinates

- source snapshot:
  `E:\BAI_AI\models\Qwen3-TTS-12Hz-0.6B-Base\5d83992436eae1d760afd27aff78a71d676296fc`
- task-owned public-artifact parent: `E:\BAI_AI\artifacts\TASK-014`
- staging leaf:
  `E:\BAI_AI\artifacts\TASK-014\.qwen3-tts-06b-base-5d839924-clean-r0.partial`
- final clean leaf:
  `E:\BAI_AI\artifacts\TASK-014\qwen3-tts-06b-base-5d839924-clean-r0`
- accepted model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
- accepted revision: `5d83992436eae1d760afd27aff78a71d676296fc`
- accepted files: `13`
- accepted bytes: `2,516,106,051`
- entries SHA-256:
  `8c40ca449eb8fcf1bd55c4b272d40a29dd6dd91d1c419120ae24795d0c9482a3`
- semantic manifest SHA-256:
  `8ee07dcddf13d95aa225df9167d4695b42e245b431686d8acb26bbd4a5e80935`

## Procedure

1. Confirm the source exists on a fixed local Windows drive and both staging and
   final leaves are absent.
2. Create only the task-owned public-artifact parent and staging leaf.
3. Copy only the exact 13 manifest paths; do not recursively copy the source.
4. Run the accepted strict verifier against the staging leaf.
5. Rename the verified staging leaf atomically within the same volume to the
   final leaf.
6. Re-run the strict verifier against the final leaf and record the body-free
   receipt coordinates below.

If copy or verification fails, do not delete either the existing source or any
unknown path. Preserve the task-owned partial leaf for bounded recovery and
report the exact gate.

## Execution Evidence

The following materialization-time receipts predate the merged AU2B2
diagnostic-authority hardening. They are retained as historical operation
Evidence, not as current parser-compatible receipts or runtime capabilities.

- source strict verification: `BLOCKED` only by
  `SNAPSHOT_EXTRA_DIRECTORY`; all 13 expected bodies were hashed
- source receipt SHA-256:
  `sha256:333db127e2899fab3989fe8362ce01adf8752696ca5577cbfaa06a9857ce261c`
- preflight: `PASS`
  - Windows drive type: `Fixed`
  - source existed: `true`
  - staging and final leaves existed before this unit: `false`
  - free bytes before materialization: `1,278,882,988,032`
- staging materialization: `PASS`
  - copied files: `13`
  - copied bytes: `2,516,106,051`
  - copy source: only the exact manifest paths; no recursive source copy
- staging strict verification: `VERIFIED`
  - evaluated at: `2026-08-20T16:49:34.149Z`
  - reason codes: none
  - filesystem enumerated: `true`
  - all expected file bodies hashed: `true`
  - snapshot modified during verification: `false`
  - receipt SHA-256:
    `sha256:57c4babf378742b2604ba6d5aa7655b69f82338e573b9a8d49e764885e55d053`
- final rename: `PASS`
  - same-volume task-owned staging leaf renamed to the bound final leaf
  - staging leaf no longer exists
  - final leaf contains exactly `13` files
- final strict verification: `VERIFIED`
  - evaluated at: `2026-08-20T16:50:13.281Z`
  - reason codes: none
  - filesystem enumerated: `true`
  - all expected file bodies hashed: `true`
  - snapshot modified during verification: `false`
  - historical precursor private receipt parser round-trip: `PASS`
  - receipt SHA-256:
    `sha256:0c2567c910bc9e308b7c2dd09bd8e307785a522e38193276f4a7a12855036513`

## Fresh current diagnostic re-observation

After AU2B2 merged to `origin/main` at
`8fa446df1cfbc871239e7ac83f4318cfe667feb9`, the exact final clean leaf was
re-observed read-only with the merged verifier. No source or clean-snapshot file
was written, renamed or deleted.

- evaluated at: `2026-08-20T21:09:28.867368Z`
- decision: `VERIFIED`
- reason codes: none
- filesystem enumerated: `true`
- all expected file bodies hashed: `true`
- snapshot modified during observation: `false`
- current strict private receipt parser round-trip: `PASS`
- current receipt SHA-256:
  `sha256:de3cf5ce56637fd088981afe0162b543507cd38ce0f414eaaa283754cf806ab6`
- diagnostic only: `true`
- persistent receipt is capability: `false`
- model reuse authorized: `false`
- model load authorized: `false`
- post-return state guaranteed: `false`
- consumer revalidation required: `true`

## No-effect record

- model weights downloaded: `false`
- existing source modified: `false`
- package installed/imported: `false`
- model loaded: `false`
- Owner audio read: `false`
- inference executed: `false`
- Firewall changed: `false`
- native audio application invoked: `false`

## Result and next gate

At the fresh observation time, the accepted public model snapshot was present
as an exact body-matching clean leaf without altering the pre-existing
cache-bearing source. This is a bounded point-in-time diagnostic observation;
it does not guarantee post-return state or authorize reuse. It does not prove
or authorize the target Python
runtime, the official package RECORD, offline model loading, Owner-reference
selection, alignment, dispatch, audio generation or QA acceptance. Those remain
separate TASK-014 gates.

## Prior independent review

- Acceptance: `PASS`
- Critic / Judge: `ACCEPT / commit-ready`
- unresolved Critical / High / Medium findings: `0 / 0 / 0`
- independent final-leaf inventory: exact `13` files and only the admitted
  `speech_tokenizer` subdirectory
- independent final-leaf SHA-256 verification: `13 / 13 PASS`
- final root and ancestor reparse check: `PASS`
- repository scope: this one untracked Evidence document only

## Fresh-main independent review

- independent Tester: `PASS` (`C0 / H0 / M0`)
- independent Critic / Judge: `ACCEPT` (`C0 / H0 / M0`)
- E: re-access during independent reviews: `false`
