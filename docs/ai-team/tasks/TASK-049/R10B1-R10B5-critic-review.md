# TASK-049 R10B1-R10B5 Critic Review

## Result

`PASS_WITH_REMAINING_NATIVE_GATES`

## Strengths

- detector outputs preserve UNKNOWN rather than forced classification;
- ROI/reference learning is deterministic and reproducible without adding a heavy hidden runtime;
- OCR is an explicit optional dependency and cannot silently claim success when unavailable;
- Killer/Power knowledge remains separate from recognition evidence and requires provenance for VERIFIED revisions;
- Cross-modal Fusion does not treat knowledge context as direct event proof;
- LLM execution reuses existing provider/security boundaries and requires explicit authorization;
- LLM output still passes deterministic Fact Validation;
- mined trivia never auto-promotes to VERIFIED;
- manual trivia utility stores reusable knowledge outside the game-fact Canonical Store.

## Remaining gates

- real DbD media ROI calibration;
- real Tesseract Japanese/English OCR evaluation on captured upper-right HUD;
- full Perk/Killer/Power labeled slice references;
- held-out Human Gold accuracy evidence;
- Windows build/run evidence for both main BVP EXE and Trivia Editor EXE;
- learned CNN/embedding model only if reference baseline KPI proves insufficient.

## Final hardening review — 2026-08-18

Additional findings closed:

1. **Duplicate-reference ambiguity** — comparing the first two reference images could miss a competing label when the top two images belonged to the same class. Fixed by ranking the best reference per unique label before acceptance/ambiguity checks.
2. **Reference visual-state provenance** — CSV `group` was accepted by the tool but not persisted by the reference index. Fixed; the group now survives index serialization.
3. **Killer/Power revision mutability** — `INSERT OR REPLACE` could overwrite an existing revision/source identifier. Fixed with immutable-id semantics and integrity validation on lookup.
4. **Transcript trivia provenance** — text-file import existed, but canonical ASR manifests did not have a direct segment-provenanced candidate path. Added `capture_transcript_manifest`.
5. **Training reproducibility** — slice extraction now emits a provenance manifest and can consume a calibrated semantic ROI profile target, reducing manual coordinate drift.

Remaining Critic gates are evidence gates, not missing architecture: calibrated real-media ROI/reference data, Tesseract real-HUD evaluation, complete current Perk/Killer/Power knowledge population, held-out Human Gold KPI, and Windows packaged execution evidence.
