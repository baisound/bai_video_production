# TASK-098 A3-R1 Model Directory Inspector Pre-Mutation Review

- Date: `2026-09-22`
- Project / Task / Unit: `BAI VIDEO PRODUCTION / TASK-098 / A3-R1`
- Development depth: `DEV-3 HIGH ASSURANCE`
- Starting HEAD: `fdab459d079791edf88a3e1c8be9d09b9952e132`
- Base/current-main identity at review: `28ba61e5f01047a716c681a3584be22500fe53fc`
- Parent integration review: `PR #562`
- Status: `DESIGN_ACCEPTED_FOR_BOUNDED_IMPLEMENTATION`

## 1. Goal

Create the contained read-only filesystem inspector that turns one explicitly
supplied local FasterWhisper model directory into the A3-R0 typed inspection
record. The inspector validates physical path safety, bounded directory shape,
stable regular-file identity, streaming SHA-256 and JSON syntax without model
construction, inference, settings mutation, network access or download.

## 2. Authority and responsibility boundary

The Owner's `2026-09-19` staged Universal WAV Review integration authority and
`2026-09-20` autonomous continuation cover the existing A3 roadmap. A3-R0
explicitly reserves A3-R1 for this contained inspector.

Canonical ownership remains unchanged:

- A3-R0 owns the typed observation/inspection contract and public projection.
- TASK-036 retains launch configuration, private ASR settings and Shell UI.
- TASK-006/023 retain FasterWhisper Provider and transcript truth.
- TASK-046/TASK-097 retain voice Dataset, training and ModelCandidate ownership.
- A3-R1 does not inspect Download migration assets or GPT-SoVITS checkpoints.

## 3. Compatibility claim

The Product currently declares `faster-whisper>=1.2.1,<2`, not one exact pinned
runtime version. Therefore A3-R1 proves only conformance to the A3-R0
offline-safe directory contract. It does not claim that a model is executable
by an installed runtime. Runtime-version binding, model construction and
inference remain later gated work.

## 4. Inspector design

### 4.1 Locator and directory safety

- Accept one absolute local `Path`/path-like locator only.
- Reject relative, missing and non-directory inputs with closed A3-R0 reasons.
- Reject symbolic-link or Windows reparse-point ancestry, including the leaf.
- Resolve the physical directory strictly only after alias checks.
- Bind the READY record to SHA-256 of the canonical private locator; never emit
  the locator or exception text.
- Enumerate only the top-level directory and reject more than 64 entries.
- Recheck directory physical identity after inspection to detect replacement or
  mutation during the scan.

### 4.2 File safety and hashing

- Consider only the six A3-R0 allowlisted filenames; unrelated top-level files
  are ignored but still count toward the 64-entry scan ceiling.
- Reject non-regular files, symlink/reparse leaves and files with link count
  other than one.
- Open with read-only/binary/no-follow flags where the platform supports them.
- Compare pre-open, opened-handle, post-read handle and post-read path identity.
- Hash through bounded chunks and reject zero, oversized, short, growing or
  identity-changing reads without exposing the file or host path.
- Parse each present `.json` allowlisted file as UTF-8 JSON from the same stable
  read. JSON bodies are not retained in the returned record.

### 4.3 Closed failure behavior

Expected host/input failures return an A3-R0 `BLOCKED` record using only closed
reason codes. No host path, exception text, file body or partial observation is
returned. Programmer misuse outside the declared input types may raise a
bounded `TypeError` before filesystem effects.

### 4.4 Effect boundary

The implementation may perform only top-level metadata reads and bounded file
reads. It creates no directory/file, writes no setting/cache, starts no model or
Provider, performs no network/download, and processes no audio. All A3-R0
effect flags stay false.

## 5. Allowed files

- `src/ai_video_production/task098_faster_whisper_model_directory.py`
  (export closed constants only; no semantic schema change)
- `src/ai_video_production/task098_faster_whisper_model_directory_inspector.py`
- `tests/test_task098_faster_whisper_model_directory_inspector.py`
- this review
- `docs/ai-team/tasks/TASK-098/task.md`
- `docs/ai-team/tasks/TASK-098/evidence/a3-r1-model-directory-inspector-20260922-r01.md`
- bounded `docs/ai-team/current-state.md` and `docs/ai-team/task-index.md` status
  synchronization at completion only

Schemas, TASK-036 settings/Shell, Provider/runtime, dependencies, packages,
installer, version and private assets must not change.

## 6. Acceptance tests

- valid TXT- and JSON-vocabulary minimums produce deterministic READY records;
- optional preprocessor JSON is represented only as its presence boolean;
- relative/missing/non-directory, symlink/reparse ancestry and directory scan
  failures map to closed BLOCKED reasons;
- entry count, required-file/vocabulary shape, regular-file, alias/hardlink,
  per-file size, stable-read/hash and JSON failures fail closed;
- READY locator binding uses the canonical private path but neither private nor
  public serialization contains the raw path;
- no file body, exception text, URL, transcript or audio enters the record;
- filesystem writes, model/runtime/provider calls and network calls are absent;
- focused A3-R1, A3-R0 and direct A2 contract regression pass;
- diff/Allowed Files and external durable Evidence read-back pass.

## 7. Critic / Tester / Judge decision

### Critic

- High: `Path.resolve()` before ancestry checks could normalize away an unsafe
  alias. Required order is lexical absolute path, no-follow ancestor inspection,
  then strict resolution.
- High: pathname-only hashing permits replacement races. Required design uses a
  no-follow descriptor plus four-way physical identity comparison.
- High: returning partial file observations on failure would leak private model
  metadata. BLOCKED records remain body-free with no observations.
- Medium: the dependency range cannot support an exact runtime-compatibility
  claim. A3-R1 is explicitly limited to contract conformance.

Final design finding count: `Critical 0 / High 0 / Medium 0 / Low 0`.

### Tester

The planned fake-directory matrix covers positive, boundary, negative, race,
privacy and effect-zero behavior without touching a private model.

Decision: `PASS / IMPLEMENTATION_TEST_PLAN_ACCEPTED`.

### Judge

The unit is read-only, bounded to A3-R0, reversible and inside existing Owner
authority. Native picker, settings and execution remain separately gated.

Decision: `ACCEPT / A3-R1_IMPLEMENTATION_ALLOCATED`.
