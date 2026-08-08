# TASK-004 — Final Implementation Plan

1. Update the internal architecture/failure-mode contracts for three lanes before code changes.
2. Add exact rational timebase and bounded timing-probe contracts.
3. Add shared derived-asset publication, normalization service/CLI, manifests and Evidence.
4. Add ComfyUI endpoint/client/workflow/resource-admission contracts and Local Video Generation service/CLI.
5. Add Audacity mod-script-pipe transport, dynamic command discovery, OpenVINO capability report, Noise Suppression and 2/4 Stem Music Separation service/CLI.
6. Add package schemas and unit/boundary/integration/fault/idempotency tests across all lanes.
7. Add Windows live-probe runners for MiniMax H3 and Audacity OpenVINO without auto-installing runtimes/models.
8. Run complete regression, compileall, wheel build and installed-wheel golden verification.
9. Perform DEV-4 Critic review and fix blocking findings without restarting unrelated review scope.
10. Synchronize canonical Project/Roadmap/task docs. If actual user MiniMax H3/OpenVINO runtimes are unavailable to this build environment, mark only the *live runtime Evidence gates* pending; do not invent performance/support Evidence.
11. Produce the user-downloadable completion/checkpoint DOCX and `.git` repository ZIP only after implementation/verification reaches its final gate.
