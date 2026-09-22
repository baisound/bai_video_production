# TASK-098 A3-R0 Model Directory Contract Pre-Mutation Review

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A3-R0`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Base: `origin/main` / `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration head: `4ce43e43fb9bb4b80f86302142ba99422c70ea9e`
- Parent PR: `#562`
- Status: `DESIGN_ACCEPTED_FOR_BOUNDED_IMPLEMENTATION`

## 1. Goal

Define the body-free, deterministic contract used to prove that a selected local
FasterWhisper directory has the minimum offline CTranslate2 file set before any
Product setting, model construction, inference, network access or download may
occur.

A3-R0 is a pure contract/schema/test Unit. It does not inspect the host
filesystem. A later A3-R1 contained inspector may create the contract from a
Human-selected directory only after a fresh review.

## 2. Authority and canonical boundaries

The Owner authorized autonomous staged Universal WAV Review integration on
`2026-09-19`. TASK-098 already reserves A3 for native model-folder selection,
required-file validation, cache reuse and private path handling.

The following ownership is unchanged:

- `Task036LaunchConfiguration` remains the existing private ASR model/cache
  settings source. A3-R0 does not read or rewrite it.
- `FasterWhisperProviderSettingsV2` remains the static execution-settings value.
  A3-R0 grants no runtime authority and does not construct it.
- TASK-006 owns Transcript/SRT truth and TASK-023 owns FasterWhisper Provider
  identity/reconciliation.
- TASK-036 owns the unified Product Shell and any later native folder picker.
- `local_audio_model_inventory.py` remains the SFX/Music/Narration inventory and
  is not expanded into a second ASR settings authority.
- TASK-046/TASK-097 voice Dataset, training, ModelCandidate and Owner approval are
  unrelated to this Unit.

## 3. Official runtime compatibility basis

The official FasterWhisper loader accepts either a symbolic model name or a path
to a converted model directory. Its official download allowlist names
`config.json`, `preprocessor_config.json`, `model.bin`, `tokenizer.json` and
`vocabulary.*`. A3-R0 requires the offline-safe minimum:

1. `config.json`;
2. `model.bin`;
3. `tokenizer.json`, because absence may enter tokenizer resolution outside the
   selected directory;
4. exactly one supported vocabulary file: `vocabulary.txt` or
   `vocabulary.json`;
5. optional `preprocessor_config.json`.

Source references:

- `https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/utils.py`
- `https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py`

The later contained inspector must bind the Product's pinned FasterWhisper
version before claiming runtime compatibility. A3-R0 does not claim that an
arbitrary future FasterWhisper version has the same file contract.

## 4. Contract design

### 4.1 Private file observation

`FasterWhisperModelFileObservationV1` contains only:

- one allowlisted relative filename;
- byte size;
- lowercase `sha256:<64 hex>` content digest.

It cannot represent an absolute path, file body, credential, URL, transcript or
audio. Per-file size ceilings prevent an observation from admitting an
unbounded or obviously invalid file.

### 4.2 Directory inspection

`FasterWhisperModelDirectoryInspectionV1` is either:

- `READY / MODEL_DIRECTORY_VALID`; or
- `BLOCKED` with one or more unique sorted closed reason codes.

A READY inspection requires the exact offline minimum above, derives a private
locator-bound `model_id`, and binds a deterministic model-manifest digest.
BLOCKED inspections expose no model ID and grant no setting or execution effect.

The private locator itself is never represented. Only a validated SHA-256 of the
trusted host's canonical locator may enter a READY receipt. This is internal
binding metadata, not a public path substitute.

### 4.3 Public projection

The public projection includes only:

- outcome and closed reason codes;
- body-free model ID for READY;
- required-file and optional-preprocessor booleans;
- fixed false download, model-load, inference, network and execution flags.

It omits the private locator digest, file list, file sizes, content digests,
manifest digest and record digest.

### 4.4 Effect invariants

Every record fixes the following values to false:

- `model_download_authorized`;
- `model_load_started`;
- `inference_started`;
- `network_used`;
- `execution_authorized`.

No receipt is a model approval, runtime capability decision, Provider request,
Human confirmation or launch authorization.

## 5. Closed blocked reasons

- `PATH_NOT_DIRECTORY`
- `PATH_ALIAS_UNSAFE`
- `DIRECTORY_SCAN_FAILED`
- `DIRECTORY_ENTRY_LIMIT_EXCEEDED`
- `REQUIRED_FILE_MISSING`
- `FILE_NOT_REGULAR`
- `FILE_ALIAS_UNSAFE`
- `FILE_SIZE_INVALID`
- `FILE_HASH_INVALID`
- `VOCABULARY_SET_INVALID`
- `REQUIRED_JSON_INVALID`

R0 tests exercise the semantic matrix without touching a real directory. R1
must map filesystem failures to these values without returning exception text or
host paths.

## 6. A3 decomposition

1. `A3-R0` — pure file-observation and directory-inspection contracts, schema
   mirrors and fake-only tests.
2. `A3-R1` — contained read-only directory inspector, physical-path and symlink/
   reparse checks, bounded streaming hashes and required JSON validation.
3. `A3-R2` — expected-digest guarded update of the existing private TASK-036 ASR
   model/cache fields plus Shell projection and fake directory-picker tests.
4. `A3-R3` — cache reuse/read-back and restart tests without model construction.

Real native picker execution, model construction, inference and packaged
acceptance remain A6/native gates. A3 cannot serialize or activate the A2 v2
runtime request through launch configuration.

## 7. A3-R0 allowed files

- `src/ai_video_production/task098_faster_whisper_model_directory.py`
- `src/ai_video_production/schema_resources/task098-faster-whisper-model-directory.schema.json`
- `schemas/task098-faster-whisper-model-directory.schema.json`
- `tests/test_task098_faster_whisper_model_directory.py`
- this review
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r0-model-directory-contract-20260922-r01.md`
- bounded `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md` status
  synchronization only

No package, dependency, version, installer, launch configuration, Product store,
Provider, runtime or private asset path is allowed to change.

## 8. Acceptance

- private and public schemas are closed and mirrored byte-for-byte;
- READY requires the complete offline-safe minimum and one vocabulary file;
- missing, duplicate/conflicting, malformed, oversized and tampered observations
  fail closed;
- record and manifest digests are deterministic and domain-separated;
- paths, bodies, credentials, URLs and exception text are unrepresentable;
- public projection contains no locator or digest;
- all effect flags remain false;
- focused tests plus the direct A2 contract regression pass;
- diff/Allowed Files review and durable external Evidence read-back pass.

## 9. Critic / Tester / Judge pre-mutation decision

### Critic

Initial findings:

- High: reusing `local_audio_model_inventory` would expand a different canonical
  responsibility. Corrected by keeping A3-R0 in TASK-098.
- High: tokenizer omission could permit runtime resolution outside the selected
  directory. Corrected by requiring `tokenizer.json`.
- High: a raw path or path digest in the public projection would leak private
  operational identity. Corrected by limiting locator binding to the private
  receipt and omitting every digest publicly.
- Medium: model-folder validation could be mistaken for execution authority.
  Corrected with fixed false effect flags and an explicit A6 boundary.

Final finding count: `Critical 0 / High 0 / Medium 0 / Low 0`.

### Tester

The planned matrix covers schema mirror, deterministic round-trip, required file
sets, vocabulary exclusivity, size bounds, tamper, unknown fields, private-data
rejection, public minimization and fixed false effects. Real filesystem/model
tests are intentionally outside R0.

Decision: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.

### Judge

The Unit is bounded, reversible, fake-only and preserves all canonical owners.
It is eligible for implementation under the standing Owner authority.

Decision: `ACCEPT / A3-R0_IMPLEMENTATION_ALLOCATED`.
