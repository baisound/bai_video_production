# TASK-022 — Timeline Mapping Service

- Status: `IMPLEMENTED_AWAITING_NATIVE_WINDOWS_REGRESSION`
- Authorization: `OWNER_AUTHORIZED_IMPLEMENTATION — 2026-08-10`
- Package: `0.5.0`
- Governance: `DEV-4 TIMELINE INTEGRITY`

## Objective

Compile canonical source or normalized Asset ranges into exact, deterministic, non-overlapping Timeline frame placements shared by existing-video editing and new-video creation.

## Scope

- exact rational Timeline rates including `30000/1001` and `24000/1001`;
- end-exclusive source, normalized and Timeline ranges;
- TASK-004 whole-file affine handoff consumption;
- explicit FLOOR start and CEIL end mapping;
- exact rational playback-speed handling;
- sequential placement with explicit frame gaps and Timeline origin;
- duplicate/overlap/out-of-order rejection;
- deterministic canonical Plan SHA-256;
- JSON Schema and packaged schema resource;
- golden NTSC, affine, speed, gap and negative fixtures.

## Out of scope

- Cut-candidate selection and editorial scoring (TASK-007/024);
- subtitle placement policy (TASK-006/010);
- SE/BGM/narration placement policy (TASK-026);
- Resolve mutation (TASK-010);
- GUI editing (TASK-027/TASK-021).

## Acceptance criteria

1. No canonical mapping uses floating-point frame rates or timestamps.
2. Starts round down and end-exclusive boundaries round up, preventing content loss.
3. Source ranges outside their affine normalization map are rejected.
4. Normalized Asset ID and affine map are an inseparable binding.
5. Playback rates are positive rational values.
6. Placement IDs are unique and Timeline ranges never overlap.
7. Plan serialization is deterministic and schema-valid.
8. The schema shipped in the Python package is semantically identical to the canonical schema.
9. Existing-video and generated-Asset routes use the same mapping contract.
10. Native-Windows full regression and compileall pass before completion.
