# TASK-040 / TASK-037 — Generation Output Production Binding

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Provider execution: NONE

A registered PASS GenerationAttempt can now be bound to an already registered Production Candidate only when:

- Attempt has an explicit output Candidate
- Candidate exists
- Candidate Slot exactly matches Attempt Slot
- Candidate `generation_job_id` exactly matches Attempt job identity
- Prompt Version exists and retains its exact body hash

The binding creates an idempotent `PROMPT(version) -> CANDIDATE` `GENERATED_FROM` dependency carrying the Prompt body SHA. It stores no Prompt body, Provider secret or media bytes and does not execute generation.
