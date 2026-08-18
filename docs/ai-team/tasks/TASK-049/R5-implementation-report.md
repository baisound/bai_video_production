# TASK-049 R5 — Implementation Report

- Unit: `R5 DbD Game Knowledge / Perk Baseline`
- Status: `IMPLEMENTED / FOCUSED+DEPENDENCY TEST PASS`
- Development depth: `DEV-3 for knowledge/schema responsibility; DEV-2 implementation`
- External effects: none
- Real DbD data ingestion: `NOT PERFORMED`; tests use synthetic facts/sources only

## Implemented

### Canonical Perk knowledge contracts

- stable `perk_id` identity independent of display name;
- Survivor/Killer role contract;
- localization records separated from identity;
- verified/unverified Alias records with NFKC + case-fold + whitespace normalization;
- Source Provenance with authority/environment/content SHA;
- patch-aware Perk Revision with explicit `game_version_from` and `game_version_to_exclusive`;
- LIVE/PTB/ARCHIVE/UNKNOWN knowledge environments;
- revision lifecycle states including `VERIFIED` / `NEEDS_REVIEW` / `SUPERSEDED` / `REJECTED`;
- official effect fact body separated from localization/explanation;
- structured-effect and tag payload retained in the revision fact body;
- deterministic content hash + revision hash;
- canonical ordering for source IDs/tags.

### Patch/version policy

- numeric `DBDPatchVersion` comparison; no lexical version ordering;
- patch values such as `9.x` fail closed for VERIFIED lookup;
- revision ranges use inclusive `from` / exclusive `to` semantics;
- overlapping VERIFIED ranges for the same Perk/environment are rejected;
- adjacent ranges are allowed;
- LIVE and PTB are queried independently and never auto-promoted/mixed.

### Source Provenance policy

- every revision references existing Source records;
- a VERIFIED revision must be explicitly LIVE or PTB;
- VERIFIED requires at least one compatible, non-UNKNOWN Source authority;
- lookup revalidates Source payload/hash and indexed authority/environment instead of trusting SQLite index columns alone.

### Alias / exact lookup

- exact stable perk ID lookup before alias/name fallback;
- localized names participate in exact normalized lookup;
- only verified aliases are authoritative;
- ambiguous alias/name resolution fails closed;
- alias/localization indexed values are revalidated against their canonical hashed payload before use.

### Perk Observation baseline

- slot `1..4`;
- `UNKNOWN`, `CANDIDATE`, `RESOLVED` are distinct states;
- UNKNOWN cannot claim a Perk/Revision;
- CANDIDATE may claim a Perk ID but not a resolved Revision;
- RESOLVED requires a patch-compatible VERIFIED Revision;
- no full icon recognizer accuracy is claimed in R5.

### CGEL binding

- `DbDPerkKnowledgeStore.bind_event()` resolves the Event's exact game version/environment;
- binding creates a new append-only Event revision;
- Event stores only `GameKnowledgeRef` (`perk_id`, revision, patch/environment/provenance reference);
- mutable official effect text is not copied into CGEL Event state;
- existing Event Evidence is unchanged: knowledge cannot manufacture Evidence retroactively.

### Persistence

- separate versioned SQLite `task049.dbd-perk-knowledge.sqlite` fact store;
- foreign/unversioned/newer/corrupt store admission fails closed;
- immutable/idempotent canonical identity/source/localization/alias/revision rows;
- public + packaged JSON Schema mirrors for Identity, Localization, Alias, Source, Revision, Observation.

## Verification

```text
TASK-049 R1-R5 + direct TASK-003/004/006/009/022 dependency regression:
165 PASS

R5 focused tests:
15 PASS

compileall: PASS (performed before closure)
git diff --check: PASS (performed before closure)
```
