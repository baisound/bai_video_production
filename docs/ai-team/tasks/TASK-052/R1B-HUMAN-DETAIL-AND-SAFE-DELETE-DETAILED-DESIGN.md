# TASK-052 R1B — Human-first Detail and Safe Delete Detailed Design

Status: `DESIGN_BOUND`
Profile: `DEV-3 HIGH ASSURANCE`
Defects: `DBD-HA-052-003`, `DBD-HA-052-006`

## Goal

Replace the arbitrary Game Knowledge key/value dump with a kind-aware Human detail
surface and add a dependency-aware delete action that cannot silently orphan semantic
references or resurrect an exact deleted import revision.

## Human detail boundary

Normal detail fields are produced by a pure allowlist registry. Common operator fields
are name, aliases, kind, review state, source, image and a bounded description/effect.
Kind-specific fields include:

- Killer: movement/terror/height, power, unique Perks, evaluation/tactics, Add-on relation;
- Perk: owner and effect;
- Item/Add-on: owner/category, rarity, charges, effect and use conditions;
- Map: Realm, Offering, area, size, pallet count, features/objects and favorability.

Unknown values are not guessed. Empty fields are omitted.

Every non-allowlisted detail key plus `candidate_id`, source revision, classifier
provenance, canonical IDs and local image path is diagnostic. Diagnostics are read-only
and collapsed by default under `内部・診断情報`. The ordinary image surface displays a
preview and filename, not an absolute local path.

## Delete impact model

The catalog produces an immutable preview containing:

- candidate state and Human-touch protection;
- inbound relations from other catalog rows;
- externally supplied references from Trivia, Map Intelligence and Alias search index;
- protected/non-protected counts;
- selected action and a deterministic preview fingerprint.

Alias index rows are rebuildable derived references and do not by themselves prevent
candidate-row removal. Trivia refs, Map relations, catalog relations and Human decisions
are protected.

Action policy:

```text
CANDIDATE + no Human override + protected inbound refs 0
    -> REMOVE_CANDIDATE (second destructive confirmation)
otherwise
    -> TOMBSTONE (disable from normal use; preserve row and relations)
```

Execution recomputes the preview and rejects a stale fingerprint. Tombstone writes a
bounded `_tombstone` diagnostic. Candidate-row removal writes a catalog tombstone ledger
entry while leaving raw snapshots, provenance and cached assets untouched.

An exact external source revision matching the ledger is suppressed on later sync. A
genuinely newer revision may return only as review evidence. A tombstoned retained row
receives a pending external update but stays disabled until explicit Human action.

## UI flow

`削除` opens an impact preview listing dependency kinds/counts and the selected safe
action. Tombstone requires explicit confirmation. Physical candidate-row removal uses a
second destructive confirmation. On success, rebuildable Alias rows are invalidated;
Map relation state is disabled rather than physically removed.

## Non-goals and gates

- no Owner Workspace migration from R1A;
- no raw snapshot, cached asset, training sample, CGEL/evidence or canonical store purge;
- no hard purge API beyond bounded candidate-row removal;
- no release/deploy/Production action.

## Acceptance

1. normal detail output contains only allowlisted labels;
2. diagnostic keys are separate and read-only/collapsed in UI source;
3. unverified zero-protected-ref row previews/removes safely and exact revision stays suppressed;
4. verified, manually edited or referenced rows tombstone;
5. stale preview execution fails;
6. newer external revision becomes review evidence without automatic resurrection;
7. Alias invalidation and Map disable routes are wired;
8. focused/affected tests PASS and unresolved Critical/High findings are zero.
