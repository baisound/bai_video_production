# TASK-012 — Native EDITOR_WORK / Cubase Return Acceptance Gate Ver.1.0

- Date: 2026-08-13
- Depends on: TASK-007 approved Edit Plan, TASK-010 completed assembly, TASK-011 PASS Render QA
- Scope: deterministic handoff/native acceptance
- Automatic Cubase project conversion: explicitly out of scope

## Objective

Prove the durable handoff contract at the boundary where automated backend editing becomes human-editable editor work:

`approved Cut Plan -> applied Resolve assembly -> PASS Render QA -> deterministic EDITOR_WORK -> optional Cubase 48 kHz PCM return -> verified Evidence`.

The existing TASK-012 service already creates the handoff and registers a bounded Cubase return. This gate independently verifies the durable package after creation and, for final native close, after a real Cubase round-trip.

## EDITOR_WORK integrity checks

- root is a regular directory;
- root name equals `handoff_id`;
- manifest declares `editor_work_root="."` and `absolute_paths_persisted=false`;
- every manifest file path is POSIX-relative and traversal-free;
- every manifested file exists, is non-symlink, non-empty, and matches stored SHA-256/size;
- duplicate relative paths fail closed;
- required roles exist: Edit Plan, Resolve assembly report, Render QA report, Render Master;
- embedded upstream report identities exactly match the handoff manifest linkage;
- Edit Plan remains approved;
- assembly remains `APPLIED` or `ALREADY_APPLIED`;
- Render QA remains `PASS`.

## Cubase boundary

The gate does not drive Cubase. Human/editor/native automation performs the DAW operation and the existing TASK-012 registration contract copies the returned WAV into the deterministic package.

Final native close with `--require-cubase-return` requires:

- round-trip was enabled by the handoff;
- canonical return record exists;
- canonical `AUDIO_ROUNDTRIP/RETURN/cubase-return.wav` exists;
- record and WAV checksum/size match;
- WAV remains readable PCM;
- sample rate remains exactly 48 kHz;
- channels/sample width/duration recorded by TASK-012 still match the WAV;
- return status remains `ACCEPTED`;
- `automatic_cubase_project_conversion=false`.

A handoff without a return may pass package-integrity validation but cannot close the real Cubase native acceptance gate.

## Evidence privacy

The native gate report persists the deterministic `handoff_id`, hashes, roles, counts and audio metadata. It does not persist the host absolute EDITOR_WORK path.

## Native acceptance

On Windows:

1. create an EDITOR_WORK package through the real product/backend flow;
2. open the supplied audio material in Cubase using the documented human workflow;
3. export the bounded return as 48 kHz PCM WAV;
4. register the return through TASK-012;
5. run this gate with `--require-cubase-return`;
6. retain PASS report as native Evidence.

Only then may TASK-012 backend handoff be labeled `NATIVE_VALIDATED`. Unified Desktop Shell acceptance remains TASK-036.
