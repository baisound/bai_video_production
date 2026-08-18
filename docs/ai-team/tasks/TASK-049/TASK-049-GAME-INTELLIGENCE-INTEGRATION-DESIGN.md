# TASK-049 — Game Intelligence / Dead by Daylight Integration Detailed Design

- Status: `DESIGN COMPLETE / IMPLEMENTATION-READY CANDIDATE`
- Dependency: `TASK-009 — DBDProfilePlugin R0` (preserved unchanged)
- Existing TASK-009 R0: `IMPLEMENTED / AUTOMATED VALIDATED`
- Development depth: `R1 DEV-3 HIGH ASSURANCE`, then adaptive `DEV-2/DEV-1` by Atomic Unit
- Product: `BAI VIDEO PRODUCTION`
- Runtime form: `ONE BVP PRODUCT ENTRYPOINT`
- Standalone product: `NOT PLANNED`
- Independent analysis capability inside BVP: `REQUIRED`
- Primary design input: `input-evidence/Dead_by_Daylight_Video_Intelligence_Platform_Ver2.2_Game_Knowledge_Integrated.md`

## 1. Decision

Dead by Daylight Video Intelligence is integrated into BAI VIDEO PRODUCTION as the first `Game Intelligence` vertical. It is **not** implemented as a second desktop product or a second installer at this stage.

The Product must nevertheless support a complete analysis-only workflow:

```text
video
  -> ingest
  -> analysis
  -> Canonical Game Event Timeline
  -> human review
  -> report / JSON / JSONL / CSV / SRT / commentary export
  -> finish
```

Entering BVP production/editing is optional:

```text
Canonical Game Event Timeline
  -> GameEventToProductionBridge
  -> highlight/commentary/narration/subtitle candidates
  -> explicit human adoption
  -> BVP Production Timeline
  -> Resolve / Render / Export
```

This preserves future extractability without paying the present cost of a second EXE, installer, settings surface, AI runtime, updater, project store, or release train.

## 2. Why this design

### 2.1 Reuse existing BVP canonical capabilities

TASK-049 MUST reuse rather than duplicate:

| Capability | Existing owner |
|---|---|
| Asset identity, checksum, rights, provenance | TASK-003 |
| Media inspection / normalization / affine mapping | TASK-004 |
| Transcript / FasterWhisper / SRT / review | TASK-006 / TASK-023 |
| Multimodal scoring contract | TASK-008 |
| DbD taxonomy plugin R0 | TASK-009 |
| Exact rational source/normalized/Timeline mapping | TASK-022 |
| Narration / Voice Studio | TASK-014 / TASK-046 |
| Audio placement / production timeline | existing BVP audio/timeline tasks |
| Resolve assembly / render QA / export | existing BVP production tasks |
| Windows BVP EXE packaging | existing BVP Windows build contract |

TASK-049 MUST NOT create a second Asset Registry, a second ASR stack, a floating-point timebase, a second production timeline, or a separate settings/credential store.

### 2.2 Two timelines, two authorities

The integration defines two distinct canonical models.

**Canonical Game Event Timeline (CGEL)**

- answers: `what was observed in the game?`
- owns match/event/evidence/game-state/review meaning;
- never owns editorial placement or Resolve mutation.

**BAI VIDEO PRODUCTION Production Timeline**

- answers: `how is the finished video assembled?`
- owns production placement after explicit adoption;
- does not become the truth source for game events.

The two are connected only through a proposal/adoption bridge.

## 3. High-level architecture

```text
                           BAI VIDEO PRODUCTION
                                   |
                         Game Intelligence Workspace
                                   |
                 +-----------------+-----------------+
                 |                                   |
          Shared BVP services                    DbD Profile
    Asset / Media / ASR / Timebase          taxonomy / detectors
                 |                                   |
                 +-----------------+-----------------+
                                   |
                              Evidence Layer
                                   |
                        Entity / State Resolution
                                   |
                    Canonical Game Event Timeline
                                   |
                 +-----------------+-----------------+
                 |                                   |
          Game Knowledge Store                Human Review
                 |                                   |
                 +-----------------+-----------------+
                                   |
                    RAG / Commentary / Validator
                                   |
              +--------------------+--------------------+
              |                                         |
       Analysis-only Export                 GameEventToProductionBridge
                                                        |
                                             Production Candidates
                                                        |
                                              Human Adoption Gate
                                                        |
                                             BVP Production Timeline
```

## 4. Canonical responsibility boundaries

### 4.1 Asset

Source media remains a TASK-003 canonical Asset. Game Intelligence stores `asset_id` references and never invents a parallel media identity.

### 4.2 Time

Canonical event time is exact frame/rational time, not a floating-point second.

All ranges use:

```text
[start_frame, end_frame_exclusive)
```

The source rate is represented as a reduced rational `{num, den}`. Display seconds are derived values only.

TASK-022 conversion semantics are reused:

- start mapping: FLOOR;
- end-exclusive mapping: CEIL;
- no floating-point canonical frame rate;
- source/normalized provenance stays explicit.

### 4.3 Evidence

An event cannot become `CONFIRMED` from unconstrained LLM inference alone. Every event must reference at least one admitted Evidence record. High-impact tactical claims should require multiple independent evidence sources where policy declares them mandatory.

### 4.4 Knowledge

Game Knowledge answers what a game entity/mechanic means for a compatible patch/environment. It does not claim that an event happened.

The Event Timeline answers what was observed. It references knowledge by stable identity/revision, rather than copying mutable effect text into every event.

### 4.5 Human authority

Recognition, event confirmation, perk correction, commentary adoption, and production adoption are separate decisions. A Human Review correction does not directly mutate the production timeline.

## 5. Core data contracts

The first implementation SHOULD add canonical schemas under `schemas/` and semantically identical packaged resources.

### 5.1 `game-match.schema.json`

Required minimum fields:

```text
match_id
production_job_id
source_asset_id
game_profile_id
game_profile_version
game_version
environment
perspective
source_rate
analysis_revision
status
created_at
```

`environment` initial closed enum:

```text
LIVE
PTB
UNKNOWN
```

### 5.2 `game-evidence.schema.json`

Purpose: game-analysis-specific typed evidence envelope that can reference the existing BVP Evidence record.

Required minimum:

```text
game_evidence_id
match_id
source_asset_id
producer
producer_version
evidence_type
source_range
confidence_milli
artifact_ref
bvp_evidence_id
created_at
```

Confidence canonical representation is integer milli-units `0..1000`; UI may render percentages.

Initial evidence types:

```text
VISION
HUD
ASR
AUDIO
STATE_TRANSITION
KNOWLEDGE_MATCH
HUMAN_REVIEW
```

### 5.3 `canonical-game-event.schema.json`

Required minimum:

```text
event_id
match_id
revision
event_type
source_range
game_version
environment
perspective
state
confidence_milli
confirmation_state
evidence_refs
knowledge_refs
review_status
created_at
```

Initial confirmation states:

```text
DETECTED
POSSIBLE
CONFIRMED
REJECTED
UNKNOWN
NEEDS_REVIEW
```

Initial DbD event types may begin as a bounded vertical slice:

```text
MATCH_START
CHASE_START
CHASE_END
INJURY
HOOK
UNHOOK
WINDOW_VAULT
PALLET_DROP
UNKNOWN_EVENT
```

Adding event types is a versioned Profile change; unknown detector output does not get laundered into a known enum.

### 5.4 `game-event-review.schema.json`

Stores append-only review decisions:

```text
review_id
event_id
reviewer_kind
original_state
corrected_state
original_event_type
corrected_event_type
reason_code
notes
created_at
```

### 5.5 `game-knowledge-ref.schema.json`

Stable reference only:

```text
knowledge_kind
entity_id
revision_id
environment
game_version_from
game_version_to
source_provenance_ref
```

The actual perk/killer/map knowledge can evolve independently.

## 6. Incremental Python module boundaries

TASK-049 MUST preserve the existing BVP package style during the first implementation campaign.
Do not reorganize existing `media`, `production`, `voice`, or `generation` code merely to make a new conceptual tree look cleaner.

R1 begins with a bounded flat module set under the existing package:

```text
src/ai_video_production/
  canonical_game_event.py
  canonical_game_event_timeline.py
  game_event_evidence.py
  game_event_store.py
  game_intelligence_application.py
```

Later Atomic Units add only the modules they actually require, for example:

```text
  game_match.py
  game_state.py
  dbd_event_detector.py
  game_knowledge_store.py
  perk_knowledge.py
  perk_revision.py
  perk_recognition.py
  game_commentary.py
  game_fact_validator.py
  game_event_production_bridge.py
```

A `game_intelligence/` subpackage MAY be introduced later only when module count, ownership, and import stability make extraction worthwhile. That refactor is not an R1 prerequisite.

The dependency rule is more important than directory shape:

```text
Game Intelligence core
    must not import Desktop Shell, Resolve mutation, or UI presentation modules.

BVP adapters / application services
    may import Game Intelligence core and existing BVP contracts.

Production bridge
    creates proposals only; existing BVP authority owns adoption/mutation.
```

## 7. Persistence

### 7.1 Canonical local store

Use a project-local deterministic store (SQLite is acceptable) for Game Intelligence state. The store is canonical for game-analysis records, but not system-wide BVP asset truth.

Minimum tables:

```text
game_matches
game_evidence
game_events
game_event_revisions
game_event_reviews
game_knowledge_refs
perk_observations              # introduced when R5 lands
commentary_candidates          # introduced when R7 lands
production_bridge_candidates   # introduced when R8 lands
```

### 7.2 Revision policy

Human correction and automated re-analysis MUST preserve history. No in-place destructive overwrite of a confirmed event revision.

### 7.3 Resume

Analysis jobs must be resumable at stage checkpoints. A failed detector run must not corrupt previously verified match/event records.

## 8. DbD game knowledge

R5 introduces the knowledge subsystem. The Perk Knowledge design from the input evidence is retained with BVP integration changes:

- SQLite/structured store is `Game Knowledge Canonical Fact Store`, not BVP-wide truth;
- LIVE/PTB separation is mandatory;
- every VERIFIED revision has Source Provenance;
- event records reference `perk_id + revision_id` rather than copying effect text;
- RAG retrieval is patch-aware;
- LLM must abstain if no compatible verified revision exists;
- correction output is eligible for Gold/Hard-Negative datasets only after explicit review.

Initial R5 can implement Perk identity/revision and knowledge lookup before full icon recognition accuracy exists.

## 9. Detector and multimodal policy

R0 deliberately has `runtime_feature_producer_state = NOT_SELECTED`; R4 is the first unit allowed to introduce bounded producers.

Detector output is Evidence/Candidate, not Event authority.

A typical flow:

```text
frame/audio/transcript
  -> feature producer
  -> typed Evidence
  -> profile scoring/state resolver
  -> event candidate
  -> policy threshold
  -> AUTO_ACCEPTED / NEEDS_REVIEW
  -> Human correction when needed
```

The first detector slice should prioritize event contracts and UNKNOWN behavior over wide event coverage.

## 10. Human Review UX

The first UI does not need the complete final visual design. It must expose enough state to verify the canonical path.

### Match view

- source video/asset identity;
- game version/environment;
- perspective;
- analysis state;
- event counts and unresolved count.

### Event Timeline view

- exact event ordering;
- display timestamp derived from exact frames;
- event type;
- confidence;
- confirmation/review state;
- evidence count.

### Event detail

- frame/video preview when available;
- exact source range;
- all evidence records;
- knowledge references;
- Approve / Correct / Reject / Mark UNKNOWN.

### Perk review (R5/R6)

- frame preview;
- perk-slot crop;
- Top-K candidates;
- confidence;
- selected perk;
- game version/environment;
- resolved knowledge revision;
- official/structured effect;
- source provenance;
- activation candidate;
- Approve / Correct / Reject.

## 11. Commentary

Commentary generation is downstream of reviewed/candidate events and compatible knowledge.

It must consider:

```text
event significance
confidence
knowledge certainty
tactical relevance
novelty
viewer educational value
time available
speech congestion
```

The LLM must not create missing game facts. Fact Validator checks numbers, patch compatibility, entity IDs, and activation claims against the Evidence + Knowledge references.

## 12. Production bridge

`GameEventToProductionBridge` is proposal-only.

It can propose:

```text
highlight source ranges
commentary candidate
narration candidate
subtitle candidate
marker/annotation candidate
```

It cannot:

```text
write Resolve directly
mutate a human-owned timeline
silently approve commentary
silently publish generated narration
```

A separate BVP adoption action converts accepted bridge proposals to existing production-domain candidates/assets/placements.

## 13. Independent analysis workflow

This is a formal Product requirement, replacing the current idea of a separate standalone EXE.

A user must be able to:

```text
open BAI Video Production
  -> choose Game Intelligence / Dead by Daylight
  -> ingest/select a video
  -> analyze
  -> review events
  -> generate optional commentary
  -> export analysis
  -> close project
```

without entering Resolve assembly, production planning, AI video generation, or final video render.

Minimum analysis exports by R9:

```text
JSON
JSONL
CSV
Markdown report
SRT commentary/subtitle when commentary exists
```

## 14. Windows test EXE goal

R9 must produce the normal BVP Windows test build using the existing packaging contract. Do not create `BAI DbD Intelligence.exe`.

The packaged BVP build must prove at least:

```text
launch
 -> open Game Intelligence
 -> select/import deterministic test media
 -> create/load Match
 -> render Event Timeline
 -> review one event
 -> export JSON/JSONL/CSV/MD
 -> optional bridge candidate creation
 -> restart and read back the same canonical state
```

Native real-media detector accuracy is a later R10 gate.

## 15. Fail-closed conditions

At minimum:

- unknown game patch when policy requires a known patch;
- invalid rational frame rate;
- source range outside admitted Asset/normalization map;
- missing Evidence on a confirmed Event;
- unknown event enum presented as confirmed known type;
- incompatible knowledge revision;
- PTB-only knowledge treated as LIVE;
- missing knowledge Source Provenance for VERIFIED fact;
- failed schema validation;
- store revision/hash mismatch;
- production bridge attempt without explicit adoption authority.

## 16. Migration and compatibility

TASK-049 is additive. Existing R0 `DBDProfilePluginSnapshot` remains readable and deterministic.

No migration may reinterpret an existing BVP production timeline as a game-event timeline.

Existing projects without Game Intelligence data remain valid.

## 17. Definition of Done for TASK-049 program

The complete TASK-049 program is done only when:

1. Canonical Game Event Timeline uses exact rational/frame semantics.
2. Events require traceable Evidence.
3. DbD profile state can resolve at least the bounded event vertical slice.
4. UNKNOWN/NEEDS_REVIEW are first-class and tested.
5. Human correction is revisioned and recoverable.
6. Perk knowledge supports patch/environment/source provenance.
7. Commentary uses Evidence + compatible Knowledge and can abstain.
8. Analysis-only workflow completes without production editing.
9. Production bridge creates proposals only; adoption remains explicit.
10. Existing BVP canonical assets/timebase/ASR/production functionality is reused, not duplicated.
11. BVP Windows test EXE can run the deterministic vertical slice and read back the persisted result.
12. Native real-media R10 results are measured against a Gold Dataset and do not claim unsupported production accuracy.

## 18. Explicit non-goals for the first 1250-credit development campaign

- production-grade recognition of every perk/killer/map/tile;
- full DbD tactical coaching correctness;
- broad LoRA training;
- separate standalone desktop app;
- separate installer/updater/runtime stack;
- anti-cheat hooks, process memory reading, DLL injection, game-process mutation;
- automatic publishing;
- bypassing Human Gate for external/paid/destructive operations.

## 19. Future standalone extraction seam

No standalone app is built now. Future extraction is allowed only if product evidence establishes a real need. To keep that option cheap:

- `game_intelligence` core does not import Desktop Shell or Resolve modules;
- BVP-specific production behavior lives behind `production_bridge.py`;
- UI calls application services, not store internals;
- exports are portable;
- credentials remain in existing BVP settings infrastructure, not Game Intelligence core.

This provides standalone **capability** without paying standalone **product** cost today.
