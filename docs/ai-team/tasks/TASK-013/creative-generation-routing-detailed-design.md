# TASK-013 — Provider-neutral Creative Generation Routing Detailed Design Ver.1.0

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTATION / PROVIDER_EXECUTION_NOT_AUTHORIZED`
- Depends on: TASK-013 Shot Feasibility, TASK-027/037 generation admission, TASK-028 AI Connection Profile, TASK-040 Prompt Registry

## Objective

Compile a provider-neutral Image/Video/SE/BGM generation execution plan **without executing a provider**. Provider selection must use the configured AI Connection Profile rather than hard-coded model/provider names.

## Contract

Supported generation modes:

- `TEXT_TO_IMAGE`
- `IMAGE_TO_IMAGE`
- `TEXT_TO_VIDEO`
- `IMAGE_TO_VIDEO`
- `SFX`
- `MUSIC_GENERATION`

Each mode maps to the matching `AiWorkload` and exact required provider capability. Selection is delegated to `AiConnectionResolver` so SelectionMode, route priority, availability, credentials and capabilities remain canonical.

## Admission

The planner requires:

1. exact Prompt/Profile identity;
2. Plan approval;
3. Shot Feasibility PASS;
4. all required input Scene Asset Slots locked and CURRENT;
5. explicit paid execution authorization **only when the selected route is `CLOUD_PAID_AI`**.

Free/local routes do not require a fake paid-cost approval merely to compile a plan. A cloud-paid route fails closed before any provider call when paid execution authorization is absent.

## Privacy / Evidence

General plan Evidence stores Prompt ID/version/hash and input hashes, not the raw Prompt body. It stores route/provider/model identity but does not persist credential refs or arbitrary route settings. `provider_execution_started=false` is explicit.

## Boundaries

This slice does not:

- call ComfyUI, Runway, ElevenLabs, Suno or any external Provider;
- retrieve raw credentials;
- spend credits;
- accept generated assets;
- bypass Audit / Human decision / Lock;
- claim generation-native validation.

## Acceptance

- free/local plan compiles with no paid authorization;
- cloud-paid plan fails before provider execution without explicit authorization;
- exact capability filtering is enforced;
- Prompt/Profile mismatch fails integrity checks;
- plan serialization is deterministic and contains no raw Prompt or credential ref.
