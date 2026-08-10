# TASK-034 — OS-backed Credential Onboarding

- Status: `NATIVE_WINDOWS_PASS`
- Package: `0.12.2`
- Authorization: Owner-directed continuation
- Dependencies: TASK-028 Provider routing, TASK-032 local settings UI, TASK-033 Catalog

Users can register and remove a required API key from the local settings screen without placing it in Project JSON. On Windows the secret is stored in Windows Credential Manager for the signed-in user. This operation never contacts a Provider and never starts billing, generation, editing, or a Product Job.

Package 0.12.1 gives every credential row a distinct password-manager identity, correcting the case where only the first row offered a saved re-registration candidate.

Package 0.12.2 makes the Catalog lifecycle explicit: enabled routes marked `Credential required` appear in the active credential list; disabling a route removes it from the active list but retains any stored key in a separate cleanup section; removing the requirement is blocked until that retained key is explicitly deleted.

Completion requires the native Windows check in [`native-windows-verification.md`](native-windows-verification.md). Live Provider connectivity is intentionally a later, separately authorized task.

Native Windows Evidence accepted 2026-08-10: Catalog/Credential linkage, per-row Password Manager candidates, save/reload/delete behavior and retained-key lifecycle were confirmed by the Owner through package 0.12.2.
