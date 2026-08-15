# Voice Studio Runtime, License and Capability Probe Plan

Date: 2026-08-15
Status: `PLAN_ONLY / NO_INSTALL_OR_EXECUTION`

## Purpose

Establish exact, reproducible facts before selecting a local Voice engine or
starting the native 60–90 second slice. A family name, downloaded file or
existing executable never proves compatibility, quality or commercial use.

## Read-only baseline probe

| Area | Required fact | Public Evidence rule |
|---|---|---|
| Host | OS/build, CPU, RAM, GPU, VRAM, driver | redact machine identity |
| Storage | exact runtime root and free-space floor `max(15%, 200 GB)` | no private Project paths |
| Audio | Blue Baby Bottle SL, SSL 2+, 48 kHz/24-bit/mono capability | no serial/device fingerprint |
| Runtime | exact Python/runtime/backend/component versions and hashes | no System PATH mutation |
| Engine | Japanese, zero-shot, fine-tune, timing, style, VRAM and offline capabilities | `PROBE_REQUIRED` until measured |
| Model | exact artifact/checkpoint/quantization/hash/source | no family-level approval |
| License | code, weight, dataset, reference and output terms separately | unknown => commercial blocked |
| Performance | load/generate time, peak VRAM/RAM, failure rate and output QA | private synthetic/Owner-approved sample only |

Candidates from the Owner design—Qwen3-TTS, CosyVoice and Chatterbox—remain
`CATALOG_ONLY/EVALUATION_CANDIDATE`. IndexTTS2, XTTS-v2 and F5-TTS remain
commercially blocked unless exact Artifact evidence proves otherwise.

## Installation gate

Before any download/install, show exact component, source, license evidence,
hash/signature source, download/unpacked/rollback capacity, isolated target,
network destinations and removal/rollback plan. Installation requires the
applicable explicit Human authorization and may not modify System Python,
Conda, PATH or the existing H3/ComfyUI runtime.

## Execution gate

Before local generation, bind exact Owner-approved reference, consent scope,
Project, script digest, VoiceProfile revision, Engine/Model/hash, output root,
operation identity, resource reservation, cancellation point and recovery
behavior. Paid/Cloud fallback is prohibited. UNKNOWN execution is not replayed.

## External applications

OBS, RX 12, REAPER, Resolve and Cubase are separate later probes. A discovered
path or installed product proves neither API capability nor authorization to
change a real Project or setting.
