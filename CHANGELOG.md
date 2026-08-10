# Changelog

このProjectはSemantic Versioningを基本とします。詳細な変更履歴は注釈付きGit TagとCommit logを参照してください。

## [Unreleased]

- Integrated end-user GUI and complete automatic editing workflow remain under development.

## [0.12.1] - 2026-08-10

- Fixed API-key re-registration suggestions so every credential row has an independent password-manager section, ID, and name instead of only the first row being recognized.
- Changed the credential input hint from new-password suppression to route-scoped current-password lookup while retaining password masking and post-operation clearing.

## [0.12.0] - 2026-08-10

- Added API-key onboarding from the loopback settings screen into the current user's Windows Credential Manager.
- Added opaque hashed credential targets, UTF-8/size validation, save/read/status/delete operations, and fail-closed non-Windows behavior.
- Exposed registration state only; secret values and internal credential references remain absent from settings JSON and browser responses.
- Added bilingual safety copy and regression tests proving that credential mutations never start Provider calls, billing, generation, or editing.

## [0.11.0] - 2026-08-10

- Added a local Provider/Model Catalog editor for safe add, edit, and disable operations without JSON editing.
- Added truthful `IMPLEMENTED`, `LOCAL_RUNTIME`, and `PLANNED_ADAPTER` labels so configuration never implies execution support.
- Added generated internal credential references while excluding keys, tokens, references, endpoints, headers, and arbitrary settings from the browser contract.
- Reused atomic revision storage, CSRF, Host, CSP, and bounded-request protections and added Catalog regression coverage.

## [0.10.0] - 2026-08-10

- Added a responsive bilingual AI Connection settings screen served exclusively on local loopback.
- Added interactive mode and preferred configured-model selection across planning, video, image, audio, and music.
- Added a narrow mutation contract with revision conflict checks, random CSRF protection, Host validation, restrictive CSP, JSON/size limits, and no Provider execution path.
- Added a Windows launcher plus beginner and developer guides with diagrams, safety explanations, and truthful remaining gates.

## [0.9.0] - 2026-08-10

- Added atomic, checksummed AI Connection settings persistence with optimistic revision checks.
- Added safe migration from the 0.8 raw profile document and fail-closed handling for damaged or unsupported data.
- Added a bilingual GUI-neutral form contract with five workloads, plain-language mode/status help, exact safe model metadata, and no credential or endpoint references.
- Added power-loss rollback, stale-write, migration, integrity, schema-packaging, and secret-exclusion regression tests.

## [0.8.0] - 2026-08-10

- Added a GUI-safe, secret-free AI Connection settings preflight across planning, video, image, audio, and music.
- Reports selected exact model metadata, cost/locality class, credential readiness, disabled/blocked state, normalized errors, and a deterministic hash without executing a provider.
- Added a dated detailed design for persistence, interactive settings UI, and low-literacy usability review.

## [0.7.0] - 2026-08-10

- Added GitHub-rendered architecture and roadmap visuals plus a credential-free five-minute demo.
- Added complete Japanese/English public README navigation and equivalent English project, impact, safety and contribution guidance.
- Added guarded GitHub Release and PyPI Trusted Publishing workflows.
- Added monthly release-readiness automation, good-first-issue intake and measurable adoption/impact protocols.

## [0.6.7] - 2026-08-10

- Removed process-global `os.name` mutation from the Audacity Windows import regression test.
- Added an explicit OS-name seam so Linux/Python 3.11 pytest never attempts to instantiate `WindowsPath`.

## [0.6.6] - 2026-08-10

- Provisioned and verified FFmpeg/ffprobe on Linux and Windows GitHub-hosted CI runners.
- Corrected the six-job CI failure caused by missing media executables rather than a product regression.

## [0.6.5] - 2026-08-10

- Corrected every public repository URL to `baisound/bai_video_production`.
- Added a regression check that prevents the former repository URL from returning.

## [0.6.4] - 2026-08-10

- Added OSS public documentation, MIT license, governance, security and contribution policies.
- Added GitHub CI, security scanning, Dependabot, Issue forms and Pull Request template.
- Added public-package metadata and repository structure regression checks.

## [0.6.3] - 2026-08-10

- Replaced provider-purpose assumptions with exact model capability routing.

## [0.6.2] - 2026-08-10

- Added ElevenLabs TTS/SFX/music and SunoAPI.org asynchronous music adapters.

## [0.6.1] - 2026-08-10

- Added OpenAI, Anthropic and Google text execution adapters.

## [0.6.0] - 2026-08-10

- Added unified AI connection profiles and deterministic route resolution.

## [0.5.0] - 2026-08-10

- Added exact rational Timeline Mapping Service.

## [0.4.10] - 2026-08-09

- Completed Media Normalization and Local Visual/Audio AI Runtime foundation after native-Windows regression.

## [0.3.0] - 2026-08-08

- Added secure Asset ingest, rights/checksum and Logical Path Resolver.

## [0.2.4] - 2026-08-08

- Completed DaVinci Resolve capability spike.

## [0.1.0] - 2026-08-08

- Added Product domain, canonical manifest, state, evidence and persistence foundation.
