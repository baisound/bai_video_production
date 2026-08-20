# TASK-036 P-UX-2 — Current Implementation Revalidation

Date: `2026-08-18`

## Purpose

This record corrects canonical-state drift discovered while preparing the
TASK-049 Game Intelligence V6 integration.  Historical P-UX-2 design and audit
records are preserved unchanged; this document records what the current source
and focused tests actually establish.

## Revalidated implementation state

The current runtime is **not** at the old `P-UX-2A0 not started / no model
selection` state.  The following bounded units are present in source and have
focused regression coverage:

| Unit | Current local state |
|---|---|
| P-UX-2A0 Element / Selection Contract | `PASS_PUX2A0_ELEMENT_SELECTION_CONTRACT_NO_EFFECT` |
| P-UX-2A Connection Settings integration | `IMPLEMENTED_LOCAL / HOSTED_GATE_PENDING` |
| P-UX-2A1 Provider / Model capability projection | `IMPLEMENTED_NO_EFFECT / REVIEW_CANDIDATE` |
| P-UX-2B1 Human Proposal Revision | `IMPLEMENTED_NO_PROVIDER_EFFECT / REVIEW_CANDIDATE` |
| P-UX-2B2 Scene Ledger Revision | `IMPLEMENTED_NO_PROVIDER_EFFECT / REVIEW_CANDIDATE` |
| P-UX-2B3 Scene Contract Finalization | `IMPLEMENTED_NO_PROVIDER_EFFECT / REVIEW_CANDIDATE` |
| P-UX-2C1 Visual Generation Handoff | `TASK036_PUX2C1_VISUAL_HANDOFF_READY / LOCAL_PENDING_HOSTED_EVIDENCE` |
| P-UX-2D1 Final Review Readiness | `PASS_READ_ONLY_FOUNDATION` |
| P-UX-2D2 Final Approval / Export Binding | `PASS_NO_EFFECT_CONTRACT` |
| P-UX-2D3 Final Approval Application | `PASS_NO_EFFECT_APPLICATION` |

The checked-in V6 runtime includes canonical Provider/model selectors for the
Planning, Image, Video and Quick routes.  Therefore the earlier statement that
"no runtime select chooses a generation model" is superseded for current-state
purposes.

## Verification

Revalidation command:

```text
python -m pytest -q \
  tests/test_task036_model_selection.py \
  tests/test_task036_element_contract.py \
  tests/test_task036_shell_ui.py \
  tests/test_task036_visual_generation_handoff.py \
  tests/test_task036_final_review.py \
  tests/test_task036_final_review_readiness.py \
  tests/test_task036_final_review_application.py
```

Result:

```text
102 passed
```

This is local verification.  It does not manufacture missing hosted/native
Evidence.

## What is still not closed

`P-UX-2E` remains the outstanding closure unit.

The token:

```text
TASK036_MOCK_ABSOLUTE_FUNCTIONAL_EXPORT_FLOW_COMPLETE
```

is **not** minted by this revalidation.  A packaged-native vertical E2E must
still prove the same Project/revision/Asset/job lineage through output artifact
read-back, including checksum/media/QA/restart/UNKNOWN behavior.

No new Product version, Tag, Release, Deploy, paid Provider, Credential,
publication or external mutation authority is created by this record.

## TASK-049 shared-Shell ownership revalidation

The Owner explicitly authorized TASK-049 to proceed with the shared V6 UI/Shell
on `2026-08-18` after this implementation-state revalidation.

TASK-049 must remain an **additive extension** rather than rewriting the
V6.1.1 mock contract.  Runtime controls/pages owned by TASK-049 are marked with:

```text
data-contract-extension="TASK-049"
```

The P-UX-2A0 compiler excludes explicitly marked additive extensions from the
TASK-036 base mock-parity inventory.  Existing V6.1.1 destinations remain
required and unchanged.

This authorization permits the bounded TASK-049 analysis/review/export UI
integration.  It does not grant TASK-049 a second Production Timeline, Resolve,
Asset-adoption, subtitle-adoption, release or publication authority.
