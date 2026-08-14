# BAI VIDEO PRODUCTION — V6 Product Workflow
# Full Detailed Design Mandate Ver.1.0

Status: `MANDATORY_PREIMPLEMENTATION_DESIGN / NO_IMPLEMENTATION_AUTHORITY`
Date: `2026-08-14`

---

# 1. Mandatory instruction

The receiving team must NOT treat the supplied mock, this handoff, or prior assistant analysis as a complete implementation specification.

Independently inspect current main and create the complete implementation-ready detailed design.

Actively search for missing requirements.

---

# 2. Required design work packages

## DD-01 Current State / Existing Implementation
Map every V6 requirement to:
- Task
- source module
- schema
- store
- tests
- Shell command
- user-facing state
- native evidence

Output:
- already implemented
- partial
- migration
- genuinely new
- out of scope

## DD-02 Blueprint vNext / Frame Binding
Design:
- StartFrameSpec
- EndFrameSpec
- FrameReferenceBinding
- Character 0..N
- Space 0..1
- Composition 0..1
- ordering/roles
- validation
- hash identity
- schema version
- migration
- old-project read compatibility
- rollback

## DD-03 Reference Registry / World Lock
Design:
- reference identity
- Character / Space / Composition role
- candidate generation history
- Audit
- Human adoption
- Lock
- STALE
- dependency
- replacement impact
- retention
- compare

Reuse existing Candidate/Audit/Prompt truth.

## DD-04 Continuity
Design:
- DIRECT exact Asset reuse
- CUT
- MATCH_CUT
- Start/End differential binding
- changed Space/Composition
- stale propagation
- previous/next frame interaction

## DD-05 Visual Prompt Director
Design:
- internal structured inputs
- standard vs advanced UX
- Japanese Source
- normalized Japanese
- English Runtime
- manual override
- Prompt Registry
- hashes/versions
- reference role mapping
- conflict warnings
- provider-specific compilation

## DD-06 AI Video Prompt Compiler
Design:
- BGM/SE/Ambience flags before Prompt
- AI proofreading
- Narration/Music/SE/Ambience intent
- Provider capability
- negative prompt
- Start/End references
- Prompt version invalidation

## DD-07 Provider / Model / Adapter / Secret
Design:
- Provider -> Model dependent selector
- capability filtering
- adapter implementation status
- credential state
- connectivity
- cost mode
- unsupported parameter UI
- local/cloud state
- secret onboarding
- no secret redisplay

## DD-08 Quick Generate
Design:
- Image multi-reference
- Start/End multi-reference + locks
- Video Start/End one each
- Audio reference capability
- Negative Prompt
- File / Asset / Generation result source
- canonical internal asset identity
- explicit Quick authority
- Production adoption route

## DD-09 Audio Timeline
Design:
- Scene audio intent vs Timeline plan
- MusicPlan
- NarrationCue
- AudioCue
- AudioRange
- PlacementPlan
- whole BGM
- multi-BGM
- IN/OUT generation
- import
- crossfade
- SE cue
- Ambience range
- provider/native capability

## DD-10 Master SRT / Narration
Design:
- Scene narration script
- Master cue set
- SRT projection/import
- voice/provider/model
- timed generation
- placement
- editing
- Source-of-Truth decision when timing changes

## DD-11 Unified Shell Navigation
Design:
- Home/File/Edit/View/Project/Generate/Export
- command IDs
- risk/authority
- workspace state
- context
- background jobs
- settings
- project recovery

## DD-12 NLE Interaction
Design:
- Viewer
- Inspector
- Asset panels
- search
- Clip selection
- ruler seek/scrub
- Cut Candidate exception
- pixels-per-second zoom
- Fit Entire
- scroll
- tracks
- add/remove
- trim
- snap
- IN/OUT
- undo/redo
- long-duration behavior

## DD-13 Export Queue
Design:
- queue model
- prepare
- execute
- all execute
- progress
- cancel
- remove
- output
- STALE
- external mutation authority
- render QA
- restart/recovery

## DD-14 Background Jobs
Design:
- shared job identity
- provider job
- local job
- export
- progress
- unknown state
- navigation persistence
- restart recovery

## DD-15 Asset / Generation Reference
Design:
- internal canonical identity even before favorite/library registration
- SHA
- provenance
- rights
- source attempt
- reference role
- delete/retention
- used-by locations

## DD-16 Project Save / Migration / Recovery
Design:
- Project state version
- migration
- autosave boundary if accepted
- crash recovery
- stale state
- atomic save
- backup
- portable project implications

## DD-17 UX Acceptance
Design actual tests for:
- dead controls
- focus
- menu
- click vs drag
- scroll
- clipping
- modal
- DPI
- multi-monitor
- accessibility
- file picker
- long Timeline
- large Asset list
- job persistence
- error recovery

## DD-18 Performance
Design:
- 2h Timeline
- asset count
- generation history count
- virtualized lists
- media thumbnails
- memory
- background task throttling

## DD-19 Security / Cost / Authority
Design:
- paid generation
- local free generation
- credential
- external egress
- prompt/privacy
- destructive delete
- export
- provider timeout
- idempotency
- unknown dispatch state

## DD-20 Observability / Learning
Candidate metrics:
- generation attempts to accepted lock
- frame-reference failure
- continuity failure
- prompt override rate
- provider/model failure
- human correction rate
- dead-control regression
- queue failure
- audio placement correction

Metrics do not automatically modify Product behavior.

## DD-21 Rollout / Regression
Design:
- feature flags if required
- project migration canary
- old project open/save
- W0/W1/W2 regression
- full pytest
- Windows native acceptance
- rollback
- release decision

---

# 3. Mandatory Critic questions

Before approving implementation, Critic must ask:

- What important requirement is missing from the handoff?
- Which new-looking feature already exists?
- Which current invariant would this break?
- Where is the migration?
- What happens after restart?
- What becomes STALE?
- What can be retried safely?
- What happens after a timeout with unknown provider state?
- How are paid operations gated?
- What if Provider supports only some reference roles?
- What if Start and End intentionally use different Spaces?
- What if four Characters are present?
- What if Master SRT timing conflicts with Scene timing?
- What if a Quick-generated Asset is used as reference without Library favorite?
- What if the Project changes after an Export job is queued?
- What if a Clip click accidentally changes Playhead?
- What if Cut Candidate click has older seek semantics?
- What happens on 200% DPI / multi-monitor?
- What proves the UI actually works beyond JavaScript syntax?

---

# 4. Mandatory artifacts before implementation

1. Current-main audit
2. Requirement adjudication table
3. Existing implementation coverage matrix
4. Design Gap Register
5. Roadmap/task split decision
6. Domain model
7. Schema/migration package
8. Application Service design
9. Prompt architecture
10. Provider/capability architecture
11. Audio timing architecture
12. Quick authority contract
13. Shell/command contract
14. UX interaction contract
15. Error/recovery/idempotency contract
16. Security/cost/credential review
17. regression matrix
18. native acceptance plan
19. Critic review
20. Owner approval / exact allowed files

---

# 5. Completion floor

Do not start implementation with Critical/High design findings unresolved.

Do not mark V6 Product work complete from static HTML, unit tests alone, or hosted CI alone.

Native/user-interaction Evidence is required for user-facing interaction claims.
