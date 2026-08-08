# TASK-004 — Final Implementation Plan

1. Freeze the amended internal architecture/failure-mode contracts for four lanes before implementing Local Image AI.
2. Add exact rational timebase and bounded timing-probe contracts.
3. Add shared derived-asset publication, normalization service/CLI, manifests and Evidence.
4. Add the generic ComfyUI endpoint/client/workflow/resource-admission contracts shared by Image/Video AI.
5. Add Local Image Generation T2I/I2I Product contracts, model/license profiles (FLUX.1 Schnell/Dev, SDXL, SD3.5, SD1.5/custom), safe output resolution and IMAGE Asset publication.
6. Add Local Video Generation service/CLI using MiniMax H3 as the first intended provider profile, including conditional model-license acknowledgement, canonical reference-Asset staging for I2V/First-Last/Reference modes and stale-operation staging recovery.
7. Add Audacity mod-script-pipe transport, dynamic command discovery, OpenVINO capability report, Noise Suppression and 2/4 Stem Music Separation service/CLI.
8. Add package schemas and unit/boundary/integration/fault/idempotency tests across all lanes, including image/video model-license gating before ComfyUI queue submission, multi-output batch-preflight before publication, and byte-dedupe/per-operation lineage behavior.
9. Add local-runtime capability/live-probe instructions/runners where they do not auto-install runtimes/models.
10. Run complete regression, compileall, wheel build and installed-wheel golden verification.
11. Perform DEV-4 Critic review and fix blocking findings without restarting unrelated review scope.
12. Synchronize canonical Project/Roadmap/task docs. If actual user MiniMax H3/FLUX-SD/OpenVINO runtimes are unavailable to this build environment, mark only provider-specific live runtime Evidence gates pending; do not invent performance/support Evidence.
13. Produce the user-downloadable final DOCX and `.git` repository ZIP only after implementation/verification reaches its final gate.
