# TASK-038 — Local Audit Persistence Contract Ver.1.0

- Date: 2026-08-13
- Status: `FOUNDATION_IMPLEMENTED / AUTOMATED_VALIDATED`
- Storage: local crash-safe JSON snapshot

Candidate audit persistence now preserves immutable AI/Human audit history across application restarts without embedding Asset bytes or creating physical-delete authority.

Safety:

- snapshot SHA-256;
- nested AuditRecord SHA verification;
- Human Decision audit references are revalidated on load;
- Candidate identity mismatch remains fail-closed;
- atomic replace;
- exact compare-and-swap required for replacement;
- symlink snapshot paths rejected;
- Reject remains logical history, not file deletion.

Implementation: `candidate_audit_store.py`.
