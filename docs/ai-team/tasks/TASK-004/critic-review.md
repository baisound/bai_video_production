# TASK-004 — DEV-4 Critic Review

- Review result: `APPROVED_FOR_LIVE_CAPABILITY_EVIDENCE`
- Blocking findings remaining: `0`
- Task completion: `NOT YET — TARGET RUNTIME EVIDENCE PENDING`

## Blocking findings found and resolved

1. **Derived output partial publication risk**
   - Resolution: proxy/audio and multi-stem outputs are fully produced/QA-validated as a batch before any canonical publication.
2. **Character reference metadata trusted without re-reading bytes**
   - Resolution: Character Identity service resolves canonical same-Job assets and rejects missing, symlinked or checksum-mismatched reference bytes.
3. **ComfyUI timeout/crash could duplicate an expensive generation**
   - Resolution: request fingerprint is bound to the idempotency key, external `prompt_id` is persisted immediately, and replay reconciles `/history/{prompt_id}` rather than issuing another `/prompt`.
4. **ComfyUI dispatch ambiguous before `prompt_id` persistence**
   - Resolution: ambiguous `IN_PROGRESS/PARTIAL` state without a persisted prompt ID fails closed with an explicit state error.
5. **Audacity external side effect lacks a stable external job identifier**
   - Resolution: ambiguous `IN_PROGRESS/PARTIAL` operations require reconciliation and are never automatically replayed. Regression test proves worker call count remains zero.
6. **H3 external reference path could bypass TASK-003 Asset boundary**
   - Resolution: I2V/First-Last/Reference/SingleFrame/Foley binary references accept only same-Job canonical Assets with rights/checksum validation and Product-owned staging.
7. **H3 Production Brief could allow reference-tag injection/reordering**
   - Resolution: Product-native structured reference binding owns ordering and rejects reserved-tag injection in free text.
8. **H3 SingleFrame source has no verified repository license**
   - Resolution: no source is copied; use is restricted to an independently installed external custom node and requires explicit local-use authorization plus H3 model-license acknowledgement.
9. **Spectrum treated as equivalent to native execution**
   - Resolution: `NATIVE` is default, Spectrum is marked approximate, output QA is required, competing EasyCache/LazyCache-style wrappers are rejected, and external GPL code is not incorporated.
10. **H3 32x32 Foley community experiment could be presented as official capability**
    - Resolution: FAST_32 and >15 s profiles require explicit experimental acknowledgement; Evidence records `official_capability_claim=false` and quality remains live/human-review dependent.
11. **Provider effect parameters/raw prompts could leak sensitive local paths/text**
    - Resolution: canonical Evidence retains hashes/safe names rather than raw prompt/effect parameter values.
12. **Local AI runtime discovery could fabricate PASS when runtime is absent**
    - Resolution: CLI probes return structured ProductError envelopes and non-zero exit codes; absent runtimes remain `NOT_VERIFIED`.

## Non-blocking follow-up ownership

- full resource scheduling/monitoring remains TASK-020;
- exact generated-media placement remains TASK-022/TASK-010/TASK-026;
- automatic SFX/BGM/narration creative selection remains downstream editing/intelligence tasks;
- live provider benchmarking is environment-specific Evidence, not a compile-time claim.
