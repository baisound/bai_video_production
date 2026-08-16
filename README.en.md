# BAI Video Production

[日本語](README.md) | **English**

[![CI](https://github.com/baisound/bai_video_production/actions/workflows/ci.yml/badge.svg)](https://github.com/baisound/bai_video_production/actions/workflows/ci.yml)
[![Security](https://github.com/baisound/bai_video_production/actions/workflows/security.yml/badge.svg)](https://github.com/baisound/bai_video_production/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

BAI Video Production is a Python foundation for gradually automating secure media ingest, normalization, AI provider selection, local/cloud generation, exact timeline mapping, and DaVinci Resolve workflows.

## Choose your guide

| Reader | Page | Purpose |
|---|---|---|
| First-time or non-developer reader | [Beginner guide (Japanese)](docs/user/GETTING-STARTED.md) | Capabilities, cost/safety, five-minute demo, troubleshooting |
| OBS voice-capture user | [OBS Voice Capture Plugin guide](docs/user/OBS-VOICE-CAPTURE-PLUGIN.md) | Beginner-friendly Japanese/English guidance from preparation through gain check, recording, save, and recovery |
| Evaluator | [Project status](PROJECT.md) | Implemented versus planned scope and milestones |
| Developer or contributor | [Developer Architecture Guide](docs/developer/ARCHITECTURE.md) | Data flow, boundaries, adapters, tests, change procedure |
| OSS reviewer | [Public-readiness schedule](docs/oss/PUBLIC-READINESS-SCHEDULE.md) | Deadlines, evidence, adoption and application gates |

> **Project status: Alpha**
>
> The project currently implements foundations, provider boundaries, and timeline mapping. It is not yet a one-click end-user product that turns any input into a finished video. Unimplemented capabilities are never presented as complete.

## Why this project exists

Useful video automation requires more than generation. It must handle media rights, exact timing, external API cost, retries, provenance, interruption recovery, and human edits inside a professional NLE as one auditable workflow. This project separates probabilistic AI decisions from deterministic execution, protects source media, and keeps results reproducible, inspectable, and manually correctable.

## Expected public impact

Video production capacity affects education, local culture, research communication, accessibility, nonprofit work, creators, and small businesses. Today, users must assemble multiple AI providers, specialist NLE skills, infrastructure, rights checks, and privacy controls themselves. That burden excludes people and organizations with fewer financial and technical resources.

BAI Video Production aims to provide a reusable public foundation that:

- avoids vendor lock-in and lets users choose local, free-tier, or paid AI according to privacy, quality, and budget;
- automates proposals, generation, and placement while preserving human approval, asset replacement, and final editing control;
- treats rights, consent, cost, provenance, privacy, reproducibility, and recovery as core production requirements;
- publishes common contracts so developers do not repeatedly solve the same provider, media, and NLE integration problems from scratch;
- can eventually learn from evaluated evidence of good human edits without blindly imitating poor operations.

This impact is an objective, not a claim of demonstrated scale. We intend to publish only measured results: human time and cost saved against a defined baseline, recovery rate, rights-metadata completion, local-processing rate, reproducibility, contributors, adopters, and downstream integrations.

## Current capabilities

- Canonical Asset Registry, rights/checksum metadata, and Logical Path Resolver
- ffprobe media inspection, CFR proxies, and 48 kHz analysis audio
- exact rational timebase and source-to-timeline mapping
- DaVinci Resolve capability probes and automation-owned timeline boundaries
- local ComfyUI image/video runtime boundaries
- Audacity/OpenVINO Noise Suppression and verified two-stem separation boundary
- OpenAI, Anthropic, and Google text-capability adapters
- ElevenLabs TTS, sound-effect, and music adapters
- SunoAPI.org asynchronous music adapter
- routing based on exact model capabilities rather than fixed provider purposes
- a secret-free settings preflight API covering planning, video, image, audio, and music
- a bilingual GUI-neutral settings contract with atomic save, integrity checks, conflict protection, and legacy migration
- a local bilingual screen for editing five workload modes and preferred configured models
- a GUI Catalog for adding, editing, and disabling Provider/Model candidates with truthful adapter status
- execution boundaries that keep credentials out of profiles, manifests, and evidence

See [PROJECT.md](PROJECT.md) and the [Canonical Roadmap](docs/roadmap/PROJECT-ROADMAP-CANONICAL.md) for detailed status.

After installation, start the AI Connection settings screen with:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows\run-ai-connection-settings.ps1
```

See the [beginner screen guide](docs/user/AI-CONNECTION-SETTINGS.en.md) and [developer contract](docs/developer/AI-CONNECTION-SETTINGS-WEB.md).

## Not implemented yet

- integrated production GUI beyond the implemented AI Connection settings screen
- completed existing-video ASR, silence/filler cuts, and subtitle placement E2E
- completed new-video planning, generation, and Resolve assembly E2E
- every catalogued Runway, Luma, Kling, MiniMax, and other adapter
- automated publishing

A provider in the catalog does not imply that its adapter is implemented. Integration status distinguishes `IMPLEMENTED`, `LOCAL_RUNTIME`, and `PLANNED_ADAPTER`.

## Architecture

```mermaid
flowchart TD
    UI["GUI / CLI intent"] --> PLAN["AI proposal + human approval"]
    PLAN --> ASSET["Canonical Assets + rights"]
    ASSET --> ROUTE["Model capability routing"]
    ROUTE --> EXEC["Local / cloud adapters"]
    EXEC --> MAP["Exact timeline mapping"]
    MAP --> NLE["Automation-owned Resolve timeline"]
    NLE --> QA["QA + human handoff"]
    QA --> EVIDENCE["Manifest / Evidence / learning"]
```

AI produces proposals and generated candidates. Deterministic services own assets, time, state, recovery, and publication boundaries. External cost and NLE mutation require explicit authorization.

## Roadmap at a glance

```mermaid
flowchart LR
    A["Foundation\ncomplete"] --> B["Analysis\nASR / cuts"]
    B --> C["Editing MVP\nResolve assembly"]
    C --> D["Production pilot\nprivacy / operations"]
    D --> E["Learning loop\nverified improvement"]
```

The foundation, timeline mapping, and provider boundaries are implemented. The next major outcome is an Editing MVP that produces a cut and subtitled Resolve timeline from an existing video.

## Requirements

- Python 3.11+
- Windows 10/11 is the primary verified product target
- FFmpeg/ffprobe for media-processing features
- DaVinci Resolve Studio for Resolve integration
- ComfyUI or Audacity/OpenVINO only for their respective local AI features
- an account/API key only for each cloud provider a user explicitly enables

External runtimes, models, API keys, and paid services are not bundled or automatically installed.

## Installation

```bash
git clone https://github.com/baisound/bai_video_production.git
cd bai_video_production
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Upgrading to 0.21.0 and migrating Projects

To install the formal release from this repository after publication, select the
annotated `v0.21.0` tag and use the same installation command:

```powershell
git fetch --tags
git checkout v0.21.0
python -m pip install -e ".[dev]"
```

Existing v0.20.1 Projects remain readable. When migration is required, the
Product applies only code-registered lossless transforms through a backed-up
copy-on-write flow and reopens the result before reporting success. A legacy
Project without a Manifest requires explicit Project identity and a preview.
Unknown, newer, corrupt, lossy, or ambiguous formats fail closed and are never
silently rewritten; do not point migration at an ambiguous human-owned Project.

### Building the OBS Voice Capture Plugin and installer

Each GitHub Release includes these three TASK-047 artifacts in addition to the
BAI Video Production Python packages:

- `bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe` — beginner-friendly Windows installer
- `bai-voice-capture-0.1.0-dev.10-windows-x64.zip` — runtime package for verification and recovery
- `bai-voice-capture-0.1.0-dev.10-source.zip` — corresponding Plugin source

The Release workflow verifies [`SHA256SUMS`](packaging/release-assets/task047/SHA256SUMS)
before publishing and stops if an artifact is missing or changed. This unsigned
development candidate targets OBS Studio 32.2.1 x64. Follow the
[beginner guide](docs/user/OBS-VOICE-CAPTURE-PLUGIN.md) from top to bottom for installation and use.

The current public Technical Preview is
[BAI Voice Capture v0.1.0-dev.10 installer.1](https://github.com/baisound/bai_video_production/releases/tag/obs-voice-capture-v0.1.0-dev.10-installer.1).
Most users should download
`bai-voice-capture-0.1.0-dev.10-installer.1-windows-x64-setup.exe` from its Release Assets.
It is an unsigned Pre-release and is separate from the stable BAI Video Production `v0.21.0` release.
The Dev.10 Controller can select a destination, run the five-second gain check, start, pause, resume, and
stop while OBS 32.2.1 remains open. Keep the live gain meter and the persistent recording/paused banner visible.

To rebuild the Plugin, runtime package, and installer, use a fresh directory with
the OBS Studio `32.2.1` source and submodules, Visual Studio Build Tools 2026,
Windows SDK `10.0.26100.0`, CMake `3.30.5`, and Inno Setup `7.1.0`.
Use the real absolute CMake path instead of relying on `cmake` from `PATH`.

```powershell
$ObsSource = 'C:\src\obs-studio-32.2.1'
$PluginSource = Join-Path $ObsSource 'plugins\bai-voice-capture'
$Cmake = 'C:\Tools\CMake\3.30.5\bin\cmake.exe'
$Ctest = 'C:\Tools\CMake\3.30.5\bin\ctest.exe'
$Csc = 'C:\Program Files\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
$Iscc = 'C:\Program Files (x86)\Inno Setup 7\ISCC.exe'

git clone --recursive --branch 32.2.1 https://github.com/obsproject/obs-studio.git $ObsSource
New-Item -ItemType Directory -Path $PluginSource | Out-Null
Expand-Archive .\packaging\release-assets\task047\bai-voice-capture-0.1.0-dev.10-source.zip -DestinationPath $PluginSource

& "$PluginSource\scripts\configure.ps1" -CMakeExecutable $Cmake
& "$PluginSource\scripts\build-controller.ps1" -Compiler $Csc
& "$PluginSource\scripts\build.ps1" -CMakeExecutable $Cmake -Configuration Release
& "$PluginSource\scripts\test.ps1" -CMakeExecutable $Cmake -CtestExecutable $Ctest -Configuration Release
& "$PluginSource\scripts\package.ps1" -Configuration Release

$Artifacts = Join-Path (Split-Path $ObsSource -Parent) 'artifacts'
$RuntimeZip = Join-Path $Artifacts 'bai-voice-capture-0.1.0-dev.10-windows-x64.zip'
$InstallerWork = Join-Path $env:TEMP 'bai-task047-installer-build-work'
$InstallerOut = Join-Path $env:TEMP 'bai-task047-installer-build-output'
powershell -ExecutionPolicy Bypass -File .\tools\windows\build-task047-obs-installer.ps1 `
  -RuntimeZip $RuntimeZip -InnoCompiler $Iscc `
  -WorkRoot $InstallerWork -OutputDirectory $InstallerOut
```

The scripts fail closed across configure, build, test, package, and hash validation.
They refuse to overwrite existing work/output directories. This procedure does not
create a Tag or GitHub Release, sign files, install/load the Plugin, or start recording.
On the verified machine, CMake 3.30.5 does not recognize the Visual Studio 18 generator. A Release rebuild
through the existing VS18 graph passed, but a fresh configure must not silently fall back to another CMake or
the PATH. Stop and resolve toolchain compatibility. The installer itself remains reproducible from the
hash-pinned runtime ZIP and Inno Setup 7.1.0 with the script shown above.

## Five-minute, credential-free demo

The quickstart uses no API key, network, paid AI, real media, or NLE mutation. It demonstrates offline capability routing and exact NTSC timeline mapping.

```powershell
ai-video-quickstart --output .\quickstart-output.json
Get-Content .\quickstart-output.json
```

See the [Five-minute demo guide](docs/quickstart/FIVE-MINUTE-DEMO.md) for expected output and explicit non-claims.

## Verification

```powershell
python -c "import ai_video_production; print(ai_video_production.__version__)"
python -m pytest -q
python -m compileall -q src tests
```

Ordinary CI does not invoke paid APIs, ComfyUI, Audacity, or Resolve. Live evidence probes run only under documented safety conditions.

## Provider configuration

- [AI Connection profile example](profiles/ai-connection-creator.example.json)
- [External media profile example](profiles/external-media-providers.example.json)

Profiles store `credential://...` references, never raw API keys. External media generation also requires an explicit rights-authorization reference.

## Security, privacy, and rights

Do not disclose vulnerabilities, credentials, personal data, private media, cookies, authorization headers, or signed URLs in public issues or pull requests. Follow [SECURITY.md](SECURITY.md) for private vulnerability reporting.

Users remain responsible for provider/model terms, fees, commercial-use conditions, copyright, likeness/voice consent, privacy, and applicable law. This project is not an official product of, or endorsed by, the external providers and runtimes named in its compatibility documentation.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). First-time contributors should start with a `good first issue` that requires no credentials, paid API, private media, or destructive NLE action.

## Governance and releases

- [Governance](GOVERNANCE.md)
- [Changelog](CHANGELOG.md)
- [Support scope](SUPPORT.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)
- [Adoption and impact plan](docs/oss/ADOPTION-AND-IMPACT-PLAN.md)

## License

Original code and documentation in this repository are available under the [MIT License](LICENSE.md), unless a file states otherwise. Third-party runtimes, models, dependencies, media, and trademarks remain subject to their own terms.
