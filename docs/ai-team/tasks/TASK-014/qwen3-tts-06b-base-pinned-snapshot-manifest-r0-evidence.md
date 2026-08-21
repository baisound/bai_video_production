# TASK-014 — Qwen3-TTS 0.6B Base Pinned Snapshot Manifest R0 Evidence

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / FRESH_MAIN_VALIDATED / COMMIT_READY / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`

## Scope

This Atomic Unit captures only public metadata and exact file digests for the
official pinned model revision required by TASK-014. It does not inspect any
private runtime/model root, download either model weight body, import a target
runtime, load the model, read Owner audio, mutate Firewall state or execute
inference.

The machine-readable source is
`qwen3-tts-06b-base-pinned-snapshot-manifest-r0.json`.

## Source binding

- model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
- requested revision: `5d83992436eae1d760afd27aff78a71d676296fc`
- resolved repository commit reported by the official endpoint:
  `5d83992436eae1d760afd27aff78a71d676296fc`
- official API:
  `https://huggingface.co/api/models/Qwen/Qwen3-TTS-12Hz-0.6B-Base/revision/5d83992436eae1d760afd27aff78a71d676296fc?blobs=true`
- exact resolved-file prefix:
  `https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/resolve/5d83992436eae1d760afd27aff78a71d676296fc/`

The API returned exactly 13 sibling paths. All 13 are present in the manifest.
For 11 small public files, SHA-256 was computed over the exact bytes returned
by the pinned resolve URL. For the two weight files, the manifest uses the
official API's LFS SHA-256 and byte count without downloading the weight body.
Every entry also records the API-provided repository blob ID as a secondary
coordinate; SHA-256 remains the content-verification coordinate.

The 13 entry records cover `2,516,106,051` bytes. Their digest and the complete
semantic manifest digest are recorded in the JSON after deterministic
canonicalization.

- entries digest:
  `8c40ca449eb8fcf1bd55c4b272d40a29dd6dd91d1c419120ae24795d0c9482a3`
- canonical semantic manifest digest:
  `8ee07dcddf13d95aa225df9167d4695b42e245b431686d8acb26bbd4a5e80935`

`TASK014_PINNED_MODEL_ENTRIES_V1` accepts ASCII paths only, rejects duplicate
and ASCII-case-fold-colliding paths, sorts by ASCII byte value, and hashes the
NUL-delimited record defined in the JSON. It includes `load_input`.

`TASK014_PINNED_MODEL_MANIFEST_V1` hashes UTF-8 records in this exact order:

1. algorithm identifier;
2. `schema_version`, `manifest_id`, `model_id`, `revision`, `retrieved_at`;
3. `source.provider`, `source.api`, `source.resolve_prefix`;
4. `entries_sha256`;
5. all file records in the entries algorithm's exact sorted order;
6. every `no_effect_flags` name/value pair sorted by ASCII byte value, using
   the full scalar field name `no_effect_flags.<key>` in the record.

Each scalar record is its full field name as shown above, NUL, its JSON scalar
rendered as lowercase `true`/`false` or invariant decimal/string, then LF. No
JSON container label is added other than the explicit dotted field names. The
algorithm identifier is
`TASK014_PINNED_MODEL_MANIFEST_V1` followed by LF. The
`canonical_manifest_sha256` field itself and the two human-readable algorithm
description fields are excluded. This binds the model/revision/source,
security-relevant file classification and no-effect claims without a recursive
self-digest.

JSON strings remain strings. In particular, the `retrieved_at` record contains
the exact 24-character JSON value `2026-08-20T15:27:32.139Z`; an implementation
must disable automatic timestamp coercion or read that property as its exact
JSON string before UTF-8 encoding. Reference component sizes are: identifier
`33` bytes, scalar block `569` bytes, entry block `2,016` bytes and flag block
`241` bytes, for a canonical stream of `2,859` bytes.

## Cross-checks

The pinned values independently reproduce the already recorded canonical
prechecks:

- `config.json`:
  `2e714c787c8edb98b05432685cddb634add2de4d4e645f653d68251ef72ba011`
- `model.safetensors`:
  `180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6`
- `speech_tokenizer/model.safetensors`:
  `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`

The manifest does not prove that a private local snapshot matches these
values. A later trusted verifier must enforce path containment, reject
reparse/symlink escape, require exact bytes/hashes for the exact normalized
13-file set, reject every additional file inside the model root, and reject
case/path-normalization collisions before issuing
`MODEL_REUSE_VERIFIED`.

Verifier-owned receipts and cache metadata must live outside the model root;
there is no implicit extra-file allowlist.

## Result

- official exact revision response: `PASS`
- complete public sibling enumeration: `PASS` (`13 / 13`)
- small-file byte digest capture: `PASS` (`11 / 11`)
- official LFS weight coordinates captured: `PASS` (`2 / 2`)
- private snapshot verification: `NOT_CONFIRMED`
- model weight body download: `NOT_EXECUTED`
- target runtime/model load: `NOT_EXECUTED`
- Owner audio/inference/native mutation: `NOT_EXECUTED`

## Fresh-main integration validation

The isolated worktree was rebased without conflict onto remote `main` commit
`be15b2d200b98b194d60813c009f24981c388ec1`. The resulting worktree contains
only this Evidence file and the machine-readable manifest as untracked paths;
there are no tracked or staged changes.

On `2026-08-21`, the pending AU2B2 strict manifest parser was loaded without
executing its filesystem verifier. It parsed this exact JSON and independently
reproduced all accepted coordinates:

- strict parse: `PASS`
- file count: `13`
- total bytes: `2,516,106,051`
- entries digest: `8c40ca449eb8fcf1bd55c4b272d40a29dd6dd91d1c419120ae24795d0c9482a3`
- canonical manifest digest: `8ee07dcddf13d95aa225df9167d4695b42e245b431686d8acb26bbd4a5e80935`
- strict parse after canonical object round-trip: `PASS`
- `git diff --check`: `PASS`
- independent Tester: `PASS` (`C0 / H0 / M0`)
- independent Critic/Judge: `ACCEPT` (`C0 / H0 / M0`)

This supplemental parser check reads the JSON only. It does not turn the
pending AU2B2 verifier into canonical implementation or grant model reuse,
runtime, import, audio, inference or dispatch authority.

This evidence removes the public model-manifest information gap only. Runtime
receipt, dependency artifacts, private snapshot verification, alignment and
exact Owner inputs remain separate gates.
