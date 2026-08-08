# TASK-004 — Official Reference Verification

Verified on 2026-08-09 against current primary documentation/repositories before implementation.

## ComfyUI / MiniMax H3

- ComfyUI official MiniMax H3 workflow documentation states native local support for Text-to-Video, Image-to-Video (including first/last-frame control) and Reference-to-Video, with native stereo audio.
- ComfyUI official Server API documentation defines `/system_stats`, `/object_info`, `/prompt`, `/history/{prompt_id}` and `/ws` routes used by the Adapter contract.
- Product implementation depends on the generic ComfyUI API contract, not browser automation or a specific third-party custom-node implementation.

## Intel OpenVINO AI Plugins for Audacity

- Intel's official repository is GPL-3.0 and provides Music Separation (Demucs v4, 2/4 stems), Noise Suppression, MusicGen, Whisper Transcription and Audio Super Resolution.
- Current Noise Suppression documentation lists DeepFilterNet2/3 and legacy DenseUNet options and OpenVINO inference-device selection.
- Music Separation documentation describes 2-stem (Instrumental/Vocals) and 4-stem (Drums/Bass/Other/Vocals) modes using OpenVINO.
- Product Core does not copy/link GPL plugin source. It integrates an installed local runtime through an external process boundary.

## Audacity scripting

- Audacity official documentation states `mod-script-pipe` can drive Audacity externally, including selecting audio, applying effects and exporting results.
- The scripting reference provides `GetInfo`, `Import2`, `Export2`, `SelectTracks` and related commands.
- Audacity warns that script-pipe weakens local security and is not suitable as a web service; TASK-004 therefore keeps it local-only and requires an empty/sandbox project before modification.
- Audacity also warns that commands can change between versions; the OpenVINO Adapter therefore discovers effect descriptors dynamically instead of freezing one undocumented command ID.
