# Voice Studio Acceptance Matrix

Date: 2026-08-15

| Gate | Acceptance | Evidence | Not claimed |
|---|---|---|---|
| P-VS-0 Intake | 13/13 hashes; OR-01..32 and Q1..44 traced; TASK-046..048 uniquely allocated; Critic 2x/Judge; PR #90 hosted 9/9 and post-merge CI/Security PASS | audit, Crosswalk, roadmap, Task docs, hosted checks, exact main `25e2e04f` | runtime or Voice support |
| TASK-036 P-UX-1C | existing V6.1.1 clicks/drags/menus/focus/DPI/accessibility/restart pass | packaged EXE/native matrix | Voice top-level UI |
| Successor mock | Voice destination/workspace approved in V6.1.1 design language | canonical mock revision + design review | runtime implementation |
| P-VS-1A Backend | private metadata revision/CAS/tamper/restart/redaction; body-free, Shell-independent, non-executing capability description/preflight | focused/full tests; schemas; Evidence; hosted File Lock | model install, audio body, generation, Shell/TASK-014 integration |
| P-VS-1B Product integration | successor canonical mock approved; Voice destination/Shell/TASK-014 boundary matches the mock and receives separate Authorization | canonical mock, design review, focused/full/native Evidence | model install/inference unless separately authorized |
| Runtime/license | exact Engine/Model/hash/license/VRAM/performance established | probe and license Evidence | commercial support beyond exact artifacts |
| P-VS-2 Vertical slice | real Japanese 60–90 s local/free path through QA/restart | Windows/WSL2/full/native/lineage/recovery | fine-tune, OBS, RX, locales |
| P-OBS-0 Probe | exact `E:\SteamLibrary\steamapps\common\OBS Studio\bin` installed executable/module inventory, hash/version/architecture; separately identified official SDK/Plugin Template source/commit/headers/license; ABI/load/callback, IPC and toolchain synthetic contract | separate installed-target and official-development-source Evidence, compile-contract and license decision | assuming SDK headers exist in `bin`; Plugin load/install, OBS mutation or capture |
| P-OBS-1 Minimum Capture | hosted VoiceProfile/Revision, recording-session/segment/Dataset-candidate and TASK-043 recovery contracts; explicit selected input; session/segment identity; start/pause/resume/stop; callback copies native frames only; non-real-time canonical 48 kHz/24-bit/mono immutable staging with exact sample mapping; timestamp/drop/device; crash/restart; review-before-adoption | focused/full/native/failure/recovery/lineage/consent/encryption Evidence on exact supported OBS build | callback resample/analysis/encryption/filesystem write; Dataset-store/adoption ownership; automatic training; P-OBS-2 breadth |
| P-VS-3 Production Recording | P-OBS-1 hosted completion + P-OBS-0 exact-path PASS + recording Consent + encrypted storage + Owner GO; then 48 kHz/24-bit/mono capture/review | OBS/session/encryption/Owner decision/Dataset review Evidence | automatic Dataset adoption or training start |
| P-VS-4 Fine-tune | 30/60/90/120 min revisions, exclusive job, comparison, Human approval | Model/Dataset/quality/recovery Evidence | guaranteed quality percentage |
| TASK-048 Calibration | separate Gold dataset, versioned score calibration, threshold simulation/drift | validation and decision trace | default auto approve/reject |
| P-OBS-2 Later OBS breadth | continuous meeting/live, multiple Sources and advanced proposals after minimum production capture | separate design/native/privacy/Human Evidence | prerequisite for first production recording; automatic adoption/training |
| TASK-035 Finishing | RX 12/REAPER exact capabilities and new derived Asset round-trip | prepare/confirm/apply/QA/recovery | RX equivalence or training-data license |
| Locale L2–L5 | locale-specific G2P/split/alignment/font/license/provider/Human QA | per-locale matrix | translation-only completion |

Every implementation unit also records exact base/head, branch/PR/checks,
Allowed Files, focused/full Windows/WSL2/native tests, failure/recovery,
boundaries and the next parking condition.
