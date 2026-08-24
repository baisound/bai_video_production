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

- `bvp-montage-skill-input.schema.json` — `511945F24CFFAF37B6B0B158E16C9AF8FBBFEB2B1F3D4CB48BB4EC49A064EF76`
- `montage-proposal.schema.json` — `1B7F33B1AF464C7C6F6FB9ECEE35C3674D6F5B81E4EC16B1488F6EB3D6A48137`
- `montage-approved-plan.schema.json` — `4BCE10CF3A29578BDE6E0D1708A7C07179CA2DA7626220DA72FA85CDF0684FA3`
- `montage-human-edit-evidence.schema.json` — `112D557F0A5E377A9049BFD3625F636165B47C888FCDD8A21F6255F463F09307`
- `montage-preference-profile.schema.json` — `7D89B0973CA69FEF66AADB49F913332DC6DF7928C95709C7FB05725364BBB412`
- `montage-resolve-handoff.schema.json` — `C06D6506BF8618C813AC2F8114B790D275205CF89DEF5103459F4D5814D00910`

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
