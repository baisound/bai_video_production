# TASK-034 — OS-backed Credential Onboarding

- Status: `IMPLEMENTED_AWAITING_NATIVE_WINDOWS_EVIDENCE`
- Package: `0.12.0`
- Authorization: Owner-directed continuation
- Dependencies: TASK-028 Provider routing, TASK-032 local settings UI, TASK-033 Catalog

Users can register and remove a required API key from the local settings screen without placing it in Project JSON. On Windows the secret is stored in Windows Credential Manager for the signed-in user. This operation never contacts a Provider and never starts billing, generation, editing, or a Product Job.

Completion requires the native Windows check in [`native-windows-verification.md`](native-windows-verification.md). Live Provider connectivity is intentionally a later, separately authorized task.
