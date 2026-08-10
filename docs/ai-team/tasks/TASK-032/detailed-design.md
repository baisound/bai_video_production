# TASK-032 — AI Connection Settings UI Foundation

- Status: `INTERACTIVE_SCREEN_IMPLEMENTED_AWAITING_NATIVE_SCREENSHOT_USABILITY`
- Package: `0.10.0`
- Target dates: API 2026-08-10; first interactive settings screen 2026-08-24; usability review 2026-08-31

## User outcome

A user who does not understand provider APIs can see, for each production purpose, whether AI is enabled, what model would be used, whether it is local/free/paid, and what must be configured before pressing GO.

## Proposed screen

```mermaid
flowchart TD
    H["AI Connection settings"] --> P["Planning: AUTO / OpenAI / model / Ready"]
    H --> V["Video: OFFLINE / ComfyUI / model / Ready"]
    H --> I["Image: FREE / local model / Ready"]
    H --> A["Audio: AI / ElevenLabs / Credential needed"]
    H --> M["Music: DISABLED"]
    P --> X["Run safe preflight"]
    V --> X
    I --> X
    A --> X
    M --> X
```

Each row will eventually expose:

- `AI / FREE / AUTO / OFFLINE_ONLY / DISABLED` selection;
- exact Provider and Model, without assigning a fixed purpose to a Provider family;
- locality and cost class;
- reasoning effort where supported;
- credential configured/not configured, never the credential value;
- required capability and adapter availability;
- a plain-language blocking reason.

## Implemented domain/API slice

`AiConnectionSettingsService.preflight()` evaluates all five workloads without a network call or provider execution. It returns a checksummed `SettingsPreflightReport` containing `READY`, `DISABLED`, or `BLOCKED` for each workload, selected safe model metadata, credential booleans, and normalized error codes.

The projection deliberately excludes credential references, endpoints, headers, raw Provider payloads and machine paths. The UI must consume this safe projection rather than inspect environment variables directly.

## State and action flow

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Preflight: validate
    Preflight --> Blocked: missing capability/credential
    Preflight --> Ready: all enabled workloads resolved
    Blocked --> Draft: correct settings
    Ready --> Saved: explicit save
    Saved --> Authorized: separate GO approval
```

Saving connection settings must never equal authorizing a paid generation or Resolve mutation.

## Persistence boundary implemented in 0.9.0

```mermaid
flowchart TD
    F["Bilingual form draft"] --> P["Safe preflight"]
    P --> S["Explicit Save"]
    S --> C{"Revision unchanged?"}
    C -->|Yes| A["Atomic checksummed replace"]
    C -->|No| B["Conflict: reload required"]
    A --> G["Saved, not authorized"]
    G --> GO["Separate GO approval"]
```

`ConnectionSettingsStore` saves a `1.0.0` envelope containing only the revision and validated `AiConnectionProfile`. `document_sha256` protects the whole envelope while the nested `profile_sha256` protects the profile. Existing files require an exact `expected_revision`; this prevents one open screen from silently overwriting a newer edit made elsewhere.

The write uses a temporary sibling file, filesystem flush, parse-and-contract validation and atomic replace. Failure before replace leaves the previous settings byte-for-byte unchanged. A raw `AiConnectionProfile` document from 0.8.0 is readable as revision zero and is converted only after the user explicitly saves it.

`ConnectionSettingsFormBuilder` exposes Japanese and English workload labels, simple explanations for every selection mode, current status messages, and safe Provider/Model metadata. It excludes credential references, endpoint references, route settings, environment variables and secret values.

## Interactive screen implemented in 0.10.0

The first UI is a dependency-free, responsive local web screen served only on `127.0.0.1`. It edits all five workload modes and the preferred route already defined for each workload. A bilingual beginner explanation remains visible above the controls, and the save confirmation explicitly states that generation has not started.

```mermaid
sequenceDiagram
    participant U as User
    participant B as Local browser
    participant S as Settings service
    participant F as Atomic file
    U->>B: choose mode and Model
    B->>S: PUT selections + revision + CSRF
    S->>S: validate known workloads/routes
    S->>F: atomic save if revision matches
    F-->>S: new revision
    S-->>B: safe form projection
    B-->>U: saved; generation not started
```

Security gates include loopback-only binding, Host validation, random CSRF token, restrictive CSP, same-origin fetch, JSON-only requests, 64 KiB request limit and a narrow selection DTO. The HTTP layer has no Provider execution, media generation, Resolve or shell dependency.

## Acceptance gates

| Gate | Due | Evidence |
|---|---|---|
| Safe Preflight API | 2026-08-10 | all workloads projected; no secret reference; deterministic hash tests |
| Settings persistence contract | 2026-08-17 | **Completed 2026-08-10**: schema, migration, atomic save, rollback and conflict tests |
| Interactive screen | 2026-08-24 | **Code completed 2026-08-10**: responsive controls, keyboard-native HTML, error/help text, no execution path; native Windows screenshot Evidence pending |
| Low-literacy usability review | 2026-08-31 | three scripted tasks completed by 2–3 consenting reviewers; blockers recorded |

## Next implementation slice

Run the screen on native Windows, capture truthful screenshot Evidence and complete the scripted usability review with 2–3 consenting reviewers. Credential onboarding and Provider/Model catalog editing remain separate follow-up contracts; secret values must use an OS credential store rather than this settings file.

Use [`native-windows-evidence-template.md`](native-windows-evidence-template.md) so every reviewer performs the same save, reload, keyboard, stale-tab conflict and safe-stop checks without sharing secrets or private media.
