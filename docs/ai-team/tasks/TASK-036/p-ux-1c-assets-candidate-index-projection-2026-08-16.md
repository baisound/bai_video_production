# P-UX-1C Assets Candidate index projection

Date: 2026-08-16
Atomic unit: `ASSETS_CANDIDATE_INDEX_R0`

## Design and Critic

The Assets page currently labels a generic Production workspace dump as an
Asset Registry. The available Application Service does not expose a complete
Asset Library, rights registry, tags, host paths or Subtitle assets. It does
expose exact Production Slot and Candidate identities, lifecycle, lineage,
Asset SHA and optional Generation Job provenance.

Replace the generic dump with an explicitly scoped Production Candidate Asset
index. Classify only from exact `SlotKind`; classify AI video only when a VIDEO
Candidate has a `generation_job_id`. Keep Subtitle and Tag controls visible but
disabled because their canonical fields are absent. Bound rendering to 500
filtered rows and show the full matching count.

Builder Critic: calling this a complete Asset Registry would overstate the
source. Correction: the page names and explains the exact Candidate subset.
Security Critic: a file-import or tag UI could invent provenance, rights or host
paths. Correction: those controls remain disabled and no mutation method is
added.

Residual C/H/M: `0/0/0`.

## Post-change Evidence

- Exact Slot/Candidate rows are flattened without changing canonical order or
  creating a new Product registry.
- Enabled tabs use only `SlotKind` and Generation Job provenance predicates;
  Subtitle and Tag controls remain reasoned disabled.
- Search is limited to canonical identifiers, lifecycle and SHA fields.
- Rendering is bounded to 500 rows while the full filtered count remains
  visible.
- No Asset import, rights inference, host-path projection or Provider action
  was added.
- Python compile and embedded JavaScript syntax checks: PASS.
- TASK-036 focused regression: `171 passed`.
- Full regression: `1240 passed, 1 skipped`.
- `git diff --check`: PASS.

Post-change Residual C/H/M: `0/0/0`.
