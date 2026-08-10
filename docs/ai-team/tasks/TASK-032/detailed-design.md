# TASK-032 — AI Connection Settings UI Foundation

- Status: `PREFLIGHT_API_IMPLEMENTED_UI_PENDING`
- Package: `0.8.0`
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

## Acceptance gates

| Gate | Due | Evidence |
|---|---|---|
| Safe Preflight API | 2026-08-10 | all workloads projected; no secret reference; deterministic hash tests |
| Settings persistence contract | 2026-08-17 | schema, migration, atomic save, rollback tests |
| Interactive screen | 2026-08-24 | screenshot, keyboard operation, error/help text, no paid call |
| Low-literacy usability review | 2026-08-31 | three scripted tasks completed by 2–3 consenting reviewers; blockers recorded |

## Next implementation slice

Add a persistence service and GUI-neutral form schema, then bind it to the chosen desktop/web UI technology. GUI technology selection must consider Windows packaging, accessibility, local-only operation, secret storage integration and future dashboard reuse.
