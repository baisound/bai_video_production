# TASK-050 R4 Knowledge Usability Implementation Report

Status: IMPLEMENTED_IN_PACK

## Backend
- generalized Entity Alias Catalog
- stable canonical `entity_id` + `GameKnowledgeKind`
- official Japanese name
- reading
- official English
- community short name
- nickname
- ASR variant
- common misspelling
- CANDIDATE / VERIFIED / REJECTED
- priority
- source_ref
- ambiguous aliases fail closed
- bridge mapping from existing TASK-049 `PerkAliasType`

## UI metadata
- Japanese Trivia categories
- Japanese display for the existing CGEL GameEventType enum
- Japanese environment labels
- Japanese Knowledge kinds
- contextual field help/examples

## Authority boundary
The alias catalog is an auxiliary resolver/search index. It does not replace
Perk/Killer/Item/Add-on canonical Knowledge stores.
