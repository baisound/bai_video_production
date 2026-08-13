# TASK-040 — Generation Attempt Integrity Contract

- Date: 2026-08-13
- Status: `FOUNDATION_HARDENED / AUTOMATED_VALIDATED`

Generation Attempt persistence now fails closed when an Attempt drifts from the Prompt Version that authorized it.

Required identity checks:

- exact Prompt body SHA
- exact Prompt-bound Slot when present
- exact input Asset hash tuple
- provider profile version when reported
- regeneration parent exists and belongs to the same Slot

This prevents an Attempt or retry lineage from being silently rebound to a different production input/Slot while retaining the original Prompt identity.
