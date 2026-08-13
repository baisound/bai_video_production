# TASK-040 — Regeneration Prompt Version Contract

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Provider execution: NOT started

`RegenerationPromptDraftService` consumes a Human-authorized `RegenerationPlan` and compiles a new immutable Prompt version without calling any Provider.

The draft is bound to the exact parent Prompt ID/version/body SHA, parent Generation Attempt and Slot. Registration rechecks that the parent is still the latest Prompt version; a concurrently-added version makes the draft stale instead of being overwritten.

Provider Profile changes are rejected until the regeneration strategy has escalated to `PROVIDER_SWITCH` or higher. A regeneration that neither changes Prompt/control identity nor escalates strategy is rejected as a no-op.

The general Evidence form stores Prompt identity/hashes and body reference only; Prompt body text remains outside general Evidence. Registering a Prompt version still does not authorize paid execution or create a Candidate.
