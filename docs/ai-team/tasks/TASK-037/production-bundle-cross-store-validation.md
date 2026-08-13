# TASK-037..041 — Cross-Store Production Bundle Validation

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`

Crash-safe snapshots are individually checksummed, but individually valid stores can still disagree after stale restore/manual replacement. A read-only bundle validator now checks cross-TASK identities before autonomous resume or production admission.

Validated links:

- TASK-038 Audit -> exact TASK-037 Candidate Asset SHA
- Human audit decision -> existing Candidate
- TASK-040 PASS output -> exact Candidate/Slot/generation job (strict mode)
- TASK-039 Continuity source -> exact Candidate/Slot/Scene/Asset
- resolved Continuity target -> current locked target Asset
- TASK-041 decisions/placements -> existing Candidate
- accepted Audio placement -> still-locked Candidate

The validator never repairs, regenerates or changes lifecycle state automatically. Any mismatch is a fail-closed Data Integrity error for Human/recovery inspection.
