# Voice Studio Acceptance Matrix

Date: 2026-08-15

| Gate | Acceptance | Evidence | Not claimed |
|---|---|---|---|
| P-VS-0 Intake | 13/13 hashes; OR-01..32 and Q1..44 traced; TASK-046..048 uniquely allocated; Critic 2x/Judge; current docs agree | audit, Crosswalk, roadmap, Task docs, hosted checks | runtime or Voice support |
| TASK-036 P-UX-1C | existing V6.1.1 clicks/drags/menus/focus/DPI/accessibility/restart pass | packaged EXE/native matrix | Voice top-level UI |
| Successor mock | Voice destination/workspace approved in V6.1.1 design language | canonical mock revision + design review | runtime implementation |
| P-VS-1 Foundation | private metadata revision/CAS/tamper/restart/redaction; non-executing local capability preflight | focused/full tests; schemas; Evidence | model install, audio body, generation |
| Runtime/license | exact Engine/Model/hash/license/VRAM/performance established | probe and license Evidence | commercial support beyond exact artifacts |
| P-VS-2 Vertical slice | real Japanese 60–90 s local/free path through QA/restart | Windows/WSL2/full/native/lineage/recovery | fine-tune, OBS, RX, locales |
| P-VS-3 Recording | 48 kHz/24-bit/mono preflight, segment checkpoint, review and encrypted storage | native device/session/failure Evidence | automatic Dataset adoption |
| P-VS-4 Fine-tune | 30/60/90/120 min revisions, exclusive job, comparison, Human approval | Model/Dataset/quality/recovery Evidence | guaranteed quality percentage |
| TASK-048 Calibration | separate Gold dataset, versioned score calibration, threshold simulation/drift | validation and decision trace | default auto approve/reject |
| TASK-047 OBS | exact OBS ABI/plugin/IPC/source/consent/drop/quarantine pass | sandbox/native/License Evidence | meeting participants or auto training |
| TASK-035 Finishing | RX 12/REAPER exact capabilities and new derived Asset round-trip | prepare/confirm/apply/QA/recovery | RX equivalence or training-data license |
| Locale L2–L5 | locale-specific G2P/split/alignment/font/license/provider/Human QA | per-locale matrix | translation-only completion |

Every implementation unit also records exact base/head, branch/PR/checks,
Allowed Files, focused/full Windows/WSL2/native tests, failure/recovery,
boundaries and the next parking condition.
