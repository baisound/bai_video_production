# TASK-054 Design Critic and Judge Decision

Date: `2026-08-21 JST`

Profile: `DEV-3 HIGH ASSURANCE`

## Critic findings and resolution

1. **LLM before canonical Event admission** — rejected. Tuned reasoning is after
   CGEL and compatible Knowledge/RAG assembly.
2. **Weights as current DbD Knowledge** — rejected. Facts/patches remain in
   Knowledge/RAG; tuning owns behavior/style only.
3. **Generic route silently impersonates tuned route** — rejected. Exact binding,
   capability, artifact digest and approval state are mandatory.
4. **Tactical prose bypasses deterministic validation** — rejected. Structured
   hypotheses/assertion levels/citations pass Fact and Policy Validators.
5. **Aggregate quality hides a safety failure** — rejected. Unsupported facts,
   leakage and provenance failures are non-compensating promotion blockers.
6. **Chain-of-thought collection** — rejected. Only bounded structured claims,
   reason/uncertainty codes and refs are stored.
7. **Silent fallback or auto-retry** — rejected. Both are explicit, bounded and
   visible with route/budget identity.
8. **Design implies training/Provider/activation authority** — rejected. Download,
   Dataset, training, inference, approval, activation and Production are separate
   Human Gates.
9. **Second canonical store/runtime** — rejected. Current CGEL, Knowledge, RAG,
   Candidate, Provider and Production owners are reused.
10. **Specific-person imitation** — rejected by default. Generalized style is
    canonical; a person-bound profile requires separate rights/consent.
11. **Generic ML dashboard harms Operator flow** — rejected. The accepted UI is a
    DbD commentary workflow with Setup Wizard, Dataset/Gold vocabulary, blind
    comparison and evidence-centered Runtime review.
12. **Critical controls hidden by scrolling/scaling** — rejected. Status and
    primary action are sticky; forms/media scroll independently; 1280×720,
    increased scale and Narrator are acceptance gates.
13. **Advanced ML terminology dominates normal use** — rejected. Human Japanese
    summaries are default and technical details are collapsed/read-only.
14. **Training completion looks like activation** — rejected. Quarantine,
    evaluation, approval and activation are separate visual states/actions.
15. **Preview feedback silently becomes training data** — rejected. Confirmation
    mode is `PREVIEW_NO_LEARNING`; Dataset/model/binding/job state is invariant and
    receipts are `training_eligible=false`.
16. **Learning mode self-trains on generated prose** — rejected. Only
    Human-approved/corrected targets enter a new Dataset revision; a new quarantined
    adapter revision is trained offline and never overwrites the active model.
17. **Narration learning conflates text style with voice cloning** — rejected.
    Timestamped実況/解説 text, role, timing and structure are learned after Human
    review; waveform/timbre/biometric identity remain outside TASK-054.

Unresolved Critical: `0`

Unresolved High: `0`

## Judge decision

Decision: `DESIGN_ACCEPTED / IMPLEMENTATION_NOT_AUTHORIZED`

The design restores the original RAG + LoRA intent without weakening the current
Evidence/CGEL/Fact Validator boundary. It is deep enough to implement as bounded
R0-R8 Atomic Units: module/API/schema contracts, state/failure matrices, concrete
environment/Dataset/SFT-QLoRA/evaluation/rollback procedures and DbD-specialized
Operator flows are specified, including narration intake and a non-learning
ordinary-video current-output confirmation mode.

The default Product remains baseline/disabled. Next eligible action is a separate
authorization for R0 pure contracts. No model was downloaded, trained, invoked,
approved or activated by this design decision.
