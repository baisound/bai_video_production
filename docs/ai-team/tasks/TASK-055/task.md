# TASK-055 — Montage Proposal / Human Edit Learning Integration

- Status: `R0_BVP_CONTRACT_ADMISSION_IMPLEMENTED_LOCAL_HOSTING_PENDING`
- Priority: `OWNER_PRIORITY_1_CREATOR_LEARNING_INTEGRATION`
- Governance: `DEV-4 FOUNDATION CRITICAL`
- BVP base main: `1fb8c27fdd378f484c32d34975c6a83ee70aeac4`
- BVP branch: `codex/task-055-recovery-r0`
- Source repository: `C:/home/baisound/projects/bai-davinci-montage-skills`
- Source branch/head: `main / f8afa4123467f949935659fbc6fddacf400c6763`

## Owner goal

Integrate the already committed Montage proposal and Human-edit interchange source into BAI VIDEO PRODUCTION before TASK-056, TASK-029 and TASK-019. The external source repository remains the implementation provenance for the Montage SKILL Suite. BVP owns canonical Product-side contract admission, Timeline authority, Human approval and future learning persistence.

## Source-of-truth correction

TASK-055 source is not an uncommitted local lane and is not missing. All current source is committed on the external `bai-davinci-montage-skills` repository `main` branch at `f8afa4123467f949935659fbc6fddacf400c6763`. Before this R0, BVP `main` did not contain the six TASK-055 schemas or a Product-side admission implementation.

## R0 — Exact contract recovery and BVP admission

R0 copies the six source-main JSON Schemas byte-for-byte into BVP's canonical and packaged schema locations, then adds fail-closed parsers and cross-document admission:

- `bvp-montage-skill-input.schema.json` — `8A0D4D535C57252E3430FA8A40B8E358E78E2C1CF452629F09677FFCE9E539B5`
- `montage-proposal.schema.json` — `6FF1425C8293977C1753E28AD732CAEA0B7A2829FFCA180DCFF8C95A96F655C9`
- `montage-approved-plan.schema.json` — `E44912442E5EAC5A5983132507B1CB2FD575658DA2AB7D582E779EF134949F38`
- `montage-human-edit-evidence.schema.json` — `8489338E877F6A5EBBA5FECACE92CC2D6ABD2A56658071F08C6C80101C38D152`
- `montage-preference-profile.schema.json` — `CC810C3540536C719947D4B48418278F76CB622BD7B99C99C42EFE15D6DEDB80`
- `montage-resolve-handoff.schema.json` — `95E7B0A92A58D565D135EC670E22016F9814E7B1E1C75A2134EF8591A9629F56`

Admission verifies canonical hashes, reduced rational frame rates, unique identities, exact source ranges and anchors, proposal/input binding, preset allowlists, approved-plan decision coverage and Human-evidence lineage. Parsed records are defensive copies and never create execution authority.

## Responsibility and safety boundaries

- Montage proposal and Human Final remain separate artifacts.
- A proposal is untrusted and always `REVIEW_REQUIRED`.
- BVP remains canonical for Timeline mapping, Human approval and learning persistence.
- R0 does not invoke DaVinci Resolve, mutate a Timeline, render media, call a Provider, upload private media or write a learning profile.
- Every runtime/authority flag remains false or `NOT_RUN`; static schema and admission verification is not runtime proof.
- Automatic Profile/Knowledge Pack promotion, Release and Deploy remain separately gated.

## Acceptance criteria

- Exact six-schema byte identity across external source main, BVP canonical schemas and packaged resources.
- Round-trip parsing for every contract.
- Negative coverage for hash tampering, non-reduced frame rates and invalid anchors.
- Cross-document proposal, approved-plan and Human-evidence admission.
- External source compatibility tests execute against this BVP implementation.
- Focused BVP and relevant TASK-056 regression pass.

## Next bounded unit

R1 may add the local Product worker/application-service route that invokes the consumer runtime and presents Human review. It must reuse these admitted contracts and existing BVP Timeline/approval responsibilities; it must not create a second canonical Timeline or learning store.
