# TASK-036 P-UX-1C V6.1.1 Element Parity Audit

Date: `2026-08-15`
Authority: `docs/ai-team/product-design/v6-integration/BVP-UI-MOCK-V6.1.1.html`
Supporting specification: `BVP-PRODUCT-WORKFLOW-V6-HANDOFF.md`, section 16.4
Result: `TRACK_DEFECT_CONFIRMED / WHOLE_SURFACE_PARITY_NOT_YET_CLAIMABLE`

## Owner acceptance rule

The canonical mock is a product UX specification, not an illustrative theme.
Responsive adaptation, real Product data and an explicitly documented safety or
compatibility improvement may change implementation details. A functional part
may not be omitted merely because the current Application Service is incomplete.
Such a part must be implemented, truthfully disabled with its dependency, or
remain an explicit blocking gap. A materially simplified screen is not parity.

## Track finding

The canonical mock contains five add controls: Video, Subtitle, Audio, SE and
BGM. Every rendered track contains visibility, lock and remove controls. The
workflow specification additionally requires mute/solo where relevant, height,
and add/remove with minimum-required category rules.

The pre-correction runtime rendered only a track name and lane. TASK-044 had
durable add/remove internals, but no P-NLE-4 bridge/UI wiring; its remove guard
checked a per-track flag and non-empty state but did not independently enforce
the last remaining track of the same UX category. Visibility, lock, mute, solo
and height were absent from the controller projection. This is a design and
implementation synchronization defect, not an approved mock deviation.

The corrective design preserves released Timeline checksum compatibility:

- derive the five UX categories from released role/identity fields rather than
  changing the released `TimelineTrack` serialization;
- reject deletion of required, locked, non-empty or last-in-category tracks;
- route add/remove through the existing prepare/confirm/apply history and CAS;
- keep visibility, lock, mute, solo and height in the Python controller, never
  as JavaScript durable truth;
- expose mute/solo only for audio media;
- keep controls visible but truthfully disable durable mutation when no Project
  edit history is bound.

## Page element inventory

The following mechanical inventory counts static panel and form/control parts.
Dynamic rows are not treated as exact data-count requirements, but a zero where
the canonical screen contains an editing form is a high-confidence missing
functional surface.

| Page | Canonical panel/button/input/textarea/select | Runtime panel/button/input/textarea/select | Decision |
|---|---:|---:|---|
| home | 3 / 7 / 0 / 0 / 0 | 3 / 6 / 0 / 0 / 0 | audit one missing action |
| planning | 2 / 2 / 0 / 2 / 3 | 2 / 1 / 0 / 0 / 0 | functional parts missing |
| scenes | 3 / 4 / 7 / 1 / 1 | 3 / 0 / 0 / 0 / 0 | functional parts missing |
| locks | 3 / 9 / 1 / 3 / 0 | 3 / 3 / 0 / 0 / 0 | functional parts missing |
| sceneDesign | 3 / 8 / 5 / 10 / 9 | 3 / 0 / 0 / 0 / 0 | functional parts missing |
| imageGen | 3 / 4 / 0 / 2 / 4 | 2 / 0 / 0 / 0 / 0 | functional parts missing |
| videoGen | 3 / 4 / 4 / 3 / 6 | 2 / 1 / 0 / 1 / 0 | functional parts missing |
| audio | 1 / 19 / 0 / 0 / 0 | 2 / 1 / 0 / 0 / 0 | functional parts missing |
| assetReview | 0 / 1 / 0 / 0 / 0 | 2 / 0 / 0 / 0 / 0 | adoption action missing |
| edit | 4 / 36 / 14 / 2 / 1 | 4 / 42 / 1 / 0 / 0 | Track controls corrected; inspector/forms remain incomplete |
| finalReview | 2 / 3 / 0 / 1 / 0 | 2 / 1 / 0 / 0 / 0 | review parts missing |
| export | 3 / 5 / 1 / 0 / 1 | 3 / 4 / 1 / 0 / 1 | audit one missing action |
| assets | 1 / 10 / 2 / 0 / 1 | 1 / 1 / 1 / 0 / 0 | functional parts missing |
| quick | 3 / 31 / 10 / 7 / 15 | 3 / 7 / 0 / 1 / 0 | functional parts missing |

The inventory is a minimum diagnostic, not a license to reproduce mock-only
timers, fake Provider success, sample Product records or browser-local durable
state. Each follow-up slice must bind the exact UI intent to an existing or new
typed Python Application Service, with truthfully disabled controls until its
authority exists.

## Closure consequence

The Track corrective slice can pass and merge independently. It must not claim
whole-surface `V6.1.1_VISUAL_PARITY_PASS`. P-UX-1C remains open across bounded
screen-by-screen correction slices until every canonical functional part is
implemented or an explicit UX improvement decision documents its replacement,
and packaged Windows Evidence verifies the resulting surface.
