# TASK-047 OBS installer Release inclusion Evidence

## Objective

Every future GitHub Release must contain the verified OBS Plugin Windows installer,
runtime archive and matching source archive. Japanese and English README sections must
document the complete Plugin-to-installer build flow without relying on private paths.

## Exact assets

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `bai-voice-capture-0.1.0-dev.8-installer.4-windows-x64-setup.exe` | 2136413 | `7f1dff48059f3eb292bae32185080d26a50303313e1128ee1286666bc9faabd6` |
| `bai-voice-capture-0.1.0-dev.8-windows-x64.zip` | 36357 | `4e8fcdf6f697da059ef3aa9ae703a400d0f85e9ed89d77ace9f624dc2783e20f` |
| `bai-voice-capture-0.1.0-dev.8-source.zip` | 41065 | `4dcd50f3aadaf95798a4d82ad511a66b14ad5a1e81a131a3bd65c0c5f933b0a4` |

The installer was rebuilt from the main-hosted ISS, exact runtime ZIP and Inno Setup
7.1.0 compiler and reproduced the accepted installer SHA-256. The build performed no
download, OBS mutation, Plugin load, capture or recording.

## Release boundary

The release workflow verifies `SHA256SUMS`, copies the three files and their checksum
manifest into the existing flat `dist` release staging directory, and passes them to
the existing `gh release create` command. A missing or changed file stops before publication.
This implementation changes the future Release composition but does not create a Tag,
GitHub Release or Deploy in this task.

## Critic self-pass 1

Finding: uploading only the installer would provide no corresponding source/runtime
recovery artifact. Correction: bind all three exact artifacts and their hashes as one set.

## Critic self-pass 2 / Judge

- installer reproducibility drift: 0
- Release omission path: 0
- README private-path leak: 0
- unsigned/OBS/recording false completion: 0
- focused Release contract: `4 passed`
- Windows full regression: `1273 passed, 1 skipped`
- WSL2 Ubuntu full regression: `1274 passed`
- Python compileall (Windows/WSL2): `PASS`
- unresolved Critical/High/Medium: `0 / 0 / 0`

Judge: `PASS_FOR_DRAFT_PR`; actual Tag/GitHub Release creation remains a separate Release Gate.
