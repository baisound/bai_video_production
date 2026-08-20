# TASK-049 R7 — Critic Review

- Result: `PASS_WITH_PROVIDER_AND_R8_AUTHORITY_BOUNDARY`

## Findings

1. **LLM treated as fact authority:** blocked; R7 performs no Provider call and exposes only canonical fact plans.
2. **Uncertain Event narrated as truth:** blocked; non-CONFIRMED / pending / rejected / UNKNOWN events abstain.
3. **Stale Perk revision:** blocked; Event knowledge references are re-resolved for the exact patch/environment and hash-compared.
4. **Fabricated numeric facts:** bounded deterministic guard rejects numeric tokens absent from canonical fact values.
5. **Fabricated status/activation claim:** typed claim validation and activation-language guard reject unsupported assertions.
6. **Unclaimed free-form prose:** blocked at baseline by `CLAIMS_REQUIRED`; every accepted draft must carry at least one canonical claim.
7. **Commentary candidate mistaken for production truth:** blocked; candidate store is downstream proposal state only.
8. **Rejected draft leaks through export:** default JSONL export includes only VALIDATED candidates.
9. **Stored candidate tamper:** nested plan/draft/candidate hashes are revalidated before read/export.
10. **Semantic-language completeness:** deterministic validation cannot prove every natural-language sentence is semantically entailed. Production Provider integration must preserve the typed-claim contract and should add model/evaluation coverage rather than weakening these guards.

## R8 risks to control

- VALIDATED commentary is still a proposal; it must not directly mutate Production Timeline / Resolve.
- Bridge output must preserve Event ID/revision, Commentary candidate ID/hash, Evidence refs, and Knowledge refs.
- Rejected/abstained/unvalidated commentary must be non-bridgeable.
- Adoption into BVP production state must go through existing BVP authority/application contracts rather than introducing a second edit-plan authority.
