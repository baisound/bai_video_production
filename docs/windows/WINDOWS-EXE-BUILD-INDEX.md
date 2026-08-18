# Windows EXE / Installer Build Index

This page is the canonical entry point for building every user-facing Windows executable or installer currently shipped or developed in this repository.

> Normal users do not need to build every target. Build only the application or installer you actually intend to test. A successful local build does **not** authorize signing, publishing, deployment, paid Provider execution, or Production activation.

## Build targets

| Target | Purpose | Build guide | Usage guide |
|---|---|---|---|
| `BAI Video Production.exe` | Main BAI VIDEO PRODUCTION desktop application, including Game Intelligence | [BUILDING-WINDOWS-EXE.md](BUILDING-WINDOWS-EXE.md) | [WINDOWS-EXE-USAGE.md](../user/WINDOWS-EXE-USAGE.md) |
| `BAI DbD Training Studio.exe` | GUI for single-item, CSV batch, and direct-video teacher-data / knowledge intake | [BUILDING-DBD-TRAINING-STUDIO-EXE.md](BUILDING-DBD-TRAINING-STUDIO-EXE.md) | [DBD-TRAINING-STUDIO-USAGE.md](../user/DBD-TRAINING-STUDIO-USAGE.md) |
| `BAI DbD Trivia Editor.exe` | Lightweight manual DbD trivia editor | [BUILDING-DBD-TRIVIA-EDITOR-EXE.md](BUILDING-DBD-TRIVIA-EDITOR-EXE.md) | [DBD-TRIVIA-EDITOR-USAGE.md](../user/DBD-TRIVIA-EDITOR-USAGE.md) |
| `BAI Voice Model Builder` installer / EXE | Windows client for the voice-model workflow Technical Preview | [BUILDING-VOICE-MODEL-BUILDER-INSTALLER.md](BUILDING-VOICE-MODEL-BUILDER-INSTALLER.md) | [VOICE-MODEL-BUILDER.md](../user/VOICE-MODEL-BUILDER.md) |
| `BAI Voice Capture` OBS installer | Installs the OBS voice-capture plugin/runtime package | [BUILDING-OBS-VOICE-CAPTURE-INSTALLER.md](BUILDING-OBS-VOICE-CAPTURE-INSTALLER.md) | [OBS-VOICE-CAPTURE-PLUGIN.md](../user/OBS-VOICE-CAPTURE-PLUGIN.md) |

## Common Game Intelligence environment

Before building or using the Task-049 Game Intelligence / Training Studio features, read:

- [WINDOWS-GAME-INTELLIGENCE-ENVIRONMENT.md](WINDOWS-GAME-INTELLIGENCE-ENVIRONMENT.md)

It covers Python, the repository virtual environment, FFmpeg, Tesseract OCR, Faster-Whisper, cloud LLM Providers, credentials, CPU/GPU choices, and verification commands.

## Important packaging distinction

The first three targets are PyInstaller **one-dir** applications. Keep the generated application directory together; do not copy only the `.exe` file.

The Voice Model Builder and OBS Voice Capture targets use installer-specific packaging and have additional toolchain / provenance requirements described in their dedicated guides.
