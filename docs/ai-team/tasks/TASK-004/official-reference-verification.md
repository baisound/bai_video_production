# TASK-004 — Official Reference Verification

Verified on 2026-08-09 against current primary documentation/repositories before implementation and scope-amendment coding.

## ComfyUI Server API

- ComfyUI official Server API documentation defines `/system_stats`, `/object_info`, `/prompt` and `/history/{prompt_id}` used by the Adapter contract.
- API workflows are JSON node graphs (`class_type` + `inputs`) and can be submitted without browser automation.
- `/system_stats` exposes runtime/device information suitable for the narrow Resource Admission slice.

## MiniMax H3

- ComfyUI official MiniMax H3 workflow documentation states native local support for Text-to-Video, Image-to-Video and Reference-to-Video; the documented native workflows include first/last-frame control and native stereo audio capability.
- Product implementation depends on the generic ComfyUI API contract and native workflow compatibility, not a mandatory third-party custom node.

## FLUX.1

- Black Forest Labs official FLUX.1 Schnell model card states 1–4 step generation and Apache-2.0 licensing, including personal/scientific/commercial use. TASK-004 therefore permits this built-in profile at the runtime-license gate while retaining ordinary generated-asset rights review.
- Black Forest Labs official FLUX.1 Dev license restricts model/runtime use to non-commercial purposes unless separately licensed, while separately describing output usage. TASK-004 therefore keeps model-runtime authorization and generated-output rights as distinct fields and blocks commercial runtime execution without explicit authorization Evidence.

## Stable Diffusion

- Stability AI's official SDXL 1.0 repository declares CreativeML Open RAIL++-M. TASK-004 records that license identifier and does not silently collapse its use-based restrictions into a generic "unrestricted" state.
- Stability AI's official SD3.5 model card declares Stability Community License terms and describes commercial eligibility as conditional on the current license conditions. TASK-004 therefore treats this as a conditional runtime profile requiring caller authorization Evidence for commercial execution.
- SD1.5 is retained only as a legacy compatibility family in TASK-004 because concrete community checkpoints/LoRA/ControlNet assets may carry their own licenses; no blanket commercial-safe assertion is made for arbitrary custom models.

## Intel OpenVINO AI Plugins for Audacity

- Intel's official repository is GPL-3.0 and provides Music Separation, Noise Suppression, MusicGen, Whisper Transcription and Audio Super Resolution; processing is local and OpenVINO can use supported CPU/GPU/NPU devices.
- Current Noise Suppression documentation states its purpose is removing background noise from spoken audio.
- Music Separation documentation exposes 2-stem and 4-stem separation workflows.
- Product Core does not copy/link GPL plugin source. It integrates an installed local runtime through an external process boundary.

## Audacity scripting

- Audacity official documentation states `mod-script-pipe` can drive Audacity externally through named pipes and is disabled by default until enabled in Modules preferences.
- Audacity scripting reference exposes commands used to inspect/select/import/effect/export state.
- Audacity warns of security implications when external processes can control the application; TASK-004 therefore keeps it local-only and requires an empty/sandbox project before mutation.
- Command/effect availability can vary with installed modules/version, so the OpenVINO Adapter discovers effect descriptors dynamically instead of freezing one private implementation ID.
