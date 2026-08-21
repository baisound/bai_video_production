from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.dbd_reasoning_contracts import TunedModelBinding, TunedModelBindingStatus
from ai_video_production.dbd_tuned_model_registry import (
    BindingLifecycleTransition,
    DbDTunedModelRegistry,
    DbDTunedModelRegistryRecord,
    EXECUTION_AUTHORITY_STATE,
    admit_tuned_model_registry_record,
)
from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64
HUMAN_A = "human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FAV"
HUMAN_B = "human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FAW"
HUMAN_C = "human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FAX"
HUMAN_D = "human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FAY"


def binding(revision: int, status: TunedModelBindingStatus, *, binding_id: str = "dbd-ja", adapter: str = "a") -> TunedModelBinding:
    complete = status is not TunedModelBindingStatus.DRAFT
    approved = status is TunedModelBindingStatus.APPROVED
    return TunedModelBinding(
        binding_id=binding_id,
        revision=revision,
        status=status,
        base_model_ref="model://registry/base/v1",
        base_model_sha256=SHA_A,
        adapter_ref=f"model-adapter://registry/dbd/{adapter}",
        adapter_sha256="sha256:" + adapter * 64,
        training_dataset_sha256=SHA_B if complete else None,
        training_recipe_sha256=SHA_C if complete else None,
        evaluation_report_sha256=SHA_D if complete else None,
        rights_manifest_sha256=SHA_E if complete else None,
        supported_locales=("ja-JP",),
        approved_at="2026-08-22T00:02:00Z" if approved else None,
        approved_by_ref="human://operator/approval-1" if approved else None,
    )


def technical_ref(scheme: str, digest: str) -> str:
    return f"{scheme}://sha256/{digest.removeprefix('sha256:')}"


def record(
    value: TunedModelBinding,
    transition: BindingLifecycleTransition,
    previous: DbDTunedModelRegistryRecord | None,
    *,
    evidence_ref: str | None = None,
    evidence_sha: str = SHA_A,
    recorded_at: str | None = None,
) -> DbDTunedModelRegistryRecord:
    if evidence_ref is None:
        scheme = "registry-intake" if transition is BindingLifecycleTransition.REGISTER else "evaluation"
        evidence_ref = technical_ref(scheme, evidence_sha)
    return DbDTunedModelRegistryRecord(
        binding=value,
        transition=transition,
        previous_record_sha256=None if previous is None else previous.registry_record_sha256,
        decision_evidence_ref=evidence_ref,
        decision_evidence_sha256=evidence_sha,
        recorded_at=recorded_at or f"2026-08-22T00:0{value.revision}:00Z",
    )


def approved_chain(*, binding_id: str = "dbd-ja", adapter: str = "a") -> tuple[DbDTunedModelRegistryRecord, ...]:
    draft = record(binding(1, TunedModelBindingStatus.DRAFT, binding_id=binding_id, adapter=adapter), BindingLifecycleTransition.REGISTER, None)
    evaluated = record(binding(2, TunedModelBindingStatus.EVALUATED, binding_id=binding_id, adapter=adapter), BindingLifecycleTransition.EVALUATE, draft, evidence_sha=SHA_D)
    approved = record(binding(3, TunedModelBindingStatus.APPROVED, binding_id=binding_id, adapter=adapter), BindingLifecycleTransition.APPROVE, evaluated, evidence_ref=HUMAN_A)
    return draft, evaluated, approved


def test_schema_mirror_and_runtime_admission_are_exact() -> None:
    canonical = Path("schemas/dbd-tuned-model-registry.schema.json").read_bytes()
    mirror = Path("src/ai_video_production/schema_resources/dbd-tuned-model-registry.schema.json").read_bytes()
    assert canonical == mirror
    payload = approved_chain()[-1].to_dict()
    assert not list(Draft202012Validator(json.loads(canonical)).iter_errors(payload))
    assert admit_tuned_model_registry_record(payload).to_dict() == payload


def test_approved_latest_resolves_without_execution_authority() -> None:
    registry = DbDTunedModelRegistry(approved_chain())
    result = registry.resolve(locale="ja-JP")
    assert result.binding.status is TunedModelBindingStatus.APPROVED
    assert result.execution_authority_state == EXECUTION_AUTHORITY_STATE
    with pytest.raises(ValueError, match="cannot grant"):
        replace(result, execution_authority_state="AUTHORIZED")


def test_suspension_reinstatement_and_revocation_are_latest_only() -> None:
    rows = list(approved_chain())
    suspended = record(binding(4, TunedModelBindingStatus.SUSPENDED), BindingLifecycleTransition.SUSPEND, rows[-1], evidence_ref=HUMAN_B, evidence_sha=SHA_B)
    rows.append(suspended)
    with pytest.raises(ProductError, match="No current approved"):
        DbDTunedModelRegistry(tuple(rows)).resolve(locale="ja-JP")
    reinstated_binding = replace(binding(5, TunedModelBindingStatus.APPROVED), approved_at="2026-08-22T00:05:00Z", approved_by_ref="human://operator/approval-2")
    reinstated = record(reinstated_binding, BindingLifecycleTransition.REINSTATE, suspended, evidence_ref=HUMAN_C, evidence_sha=SHA_C)
    rows.append(reinstated)
    assert DbDTunedModelRegistry(tuple(rows)).resolve(locale="ja-JP").binding.revision == 5
    suspended_again = record(binding(6, TunedModelBindingStatus.SUSPENDED), BindingLifecycleTransition.SUSPEND, reinstated, evidence_ref=HUMAN_D, evidence_sha=SHA_D)
    revoked = record(binding(7, TunedModelBindingStatus.REVOKED), BindingLifecycleTransition.REVOKE, suspended_again, evidence_ref="human-confirmation://01ARZ3NDEKTSV4RRFFQ69G5FAZ", evidence_sha=SHA_E)
    with pytest.raises(ProductError, match="No current approved"):
        DbDTunedModelRegistry(tuple(rows + [suspended_again, revoked])).resolve(locale="ja-JP")


def test_rejected_binding_is_terminal_and_unresolvable() -> None:
    draft, evaluated, _ = approved_chain()
    rejected = record(binding(3, TunedModelBindingStatus.REJECTED), BindingLifecycleTransition.REJECT, evaluated, evidence_ref=HUMAN_A)
    registry = DbDTunedModelRegistry((draft, evaluated, rejected))
    with pytest.raises(ProductError):
        registry.resolve(locale="ja-JP")
    forged = record(binding(4, TunedModelBindingStatus.APPROVED), BindingLifecycleTransition.APPROVE, rejected, evidence_ref=HUMAN_B, evidence_sha=SHA_B)
    with pytest.raises(ValueError, match="transition"):
        DbDTunedModelRegistry((draft, evaluated, rejected, forged))


@pytest.mark.parametrize("mutation", ["gap", "fork", "transition", "artifact", "locale", "time"])
def test_chain_crossing_and_mutation_fail_closed(mutation: str) -> None:
    draft, evaluated, approved = approved_chain()
    if mutation == "gap":
        approved = replace(approved, binding=replace(approved.binding, revision=4))
    elif mutation == "fork":
        approved = replace(approved, previous_record_sha256=SHA_E)
    elif mutation == "transition":
        approved = replace(approved, transition=BindingLifecycleTransition.REINSTATE)
    elif mutation == "artifact":
        approved = replace(approved, binding=replace(approved.binding, adapter_sha256=SHA_E))
    elif mutation == "locale":
        approved = replace(approved, binding=replace(approved.binding, supported_locales=("en-US",)))
    else:
        with pytest.raises(ValueError):
            replace(approved, recorded_at="2026-08-22T00:01:00Z")
        return
    with pytest.raises(ValueError):
        DbDTunedModelRegistry((draft, evaluated, approved))


def test_technical_and_human_evidence_namespaces_are_transition_specific() -> None:
    draft, evaluated, approved = approved_chain()
    with pytest.raises(ValueError):
        DbDTunedModelRegistry((replace(draft, decision_evidence_ref=technical_ref("evaluation", SHA_A)), evaluated, approved))
    with pytest.raises(ValueError):
        replace(evaluated, decision_evidence_ref=technical_ref("registry-intake", SHA_D))
    with pytest.raises(ValueError):
        replace(approved, decision_evidence_ref="human-confirmation://operator/sk-secret")


def test_standalone_record_admission_enforces_root_target_and_evaluation_digest() -> None:
    draft, evaluated, approved = approved_chain()
    with pytest.raises(ValueError, match="target"):
        replace(approved, transition=BindingLifecycleTransition.SUSPEND)
    with pytest.raises(ValueError, match="root"):
        replace(draft, previous_record_sha256=SHA_A)
    with pytest.raises(ValueError, match="evaluation_report"):
        replace(evaluated, decision_evidence_sha256=SHA_A, decision_evidence_ref=technical_ref("evaluation", SHA_A))
    with pytest.raises(ValueError, match="DRAFT"):
        replace(draft, binding=replace(draft.binding, training_dataset_sha256=SHA_B))


def test_approval_time_cannot_precede_evaluated_record() -> None:
    draft, evaluated, approved = approved_chain()
    stale_approval = replace(approved.binding, approved_at="2026-08-22T00:01:00Z")
    with pytest.raises(ValueError, match="approval time"):
        DbDTunedModelRegistry((draft, evaluated, replace(approved, binding=stale_approval)))


def test_human_confirmation_is_one_shot_across_registry() -> None:
    rows = approved_chain()
    other = list(approved_chain(binding_id="dbd-ja-b", adapter="b"))
    with pytest.raises(ValueError, match="confirmation"):
        DbDTunedModelRegistry(tuple(sorted(rows + tuple(other), key=lambda item: (item.binding.binding_id, item.binding.revision))))


def test_ambiguous_resolution_requires_explicit_binding() -> None:
    first = approved_chain()
    second = list(approved_chain(binding_id="dbd-ja-b", adapter="b"))
    second[-1] = replace(second[-1], decision_evidence_ref=HUMAN_B, decision_evidence_sha256=SHA_B)
    registry = DbDTunedModelRegistry(tuple(sorted(first + tuple(second), key=lambda item: (item.binding.binding_id, item.binding.revision))))
    with pytest.raises(ProductError, match="Multiple approved"):
        registry.resolve(locale="ja-JP")
    assert registry.resolve(locale="ja-JP", binding_id="dbd-ja-b").binding.binding_id == "dbd-ja-b"
    with pytest.raises(ProductError, match="No current approved"):
        registry.resolve(locale="ja-JP", binding_id="missing")


def test_model_adapter_identity_cannot_be_registered_under_two_binding_ids() -> None:
    first = approved_chain()
    second = tuple(
        replace(item, binding=replace(item.binding, binding_id="dbd-ja-copy"))
        for item in approved_chain()
    )
    rows = tuple(sorted(first + second, key=lambda item: (item.binding.binding_id, item.binding.revision)))
    with pytest.raises(ValueError, match="multiple binding chains"):
        DbDTunedModelRegistry(rows)


def test_unknown_schema_extra_field_nested_tamper_and_checksum_fail() -> None:
    payload = approved_chain()[-1].to_dict()
    for mutate in (
        lambda value: value.update(schema_version="9.9.9"),
        lambda value: value.update(extra=True),
        lambda value: value["binding"].update(revision=99),
        lambda value: value.update(registry_record_sha256=SHA_E),
    ):
        changed = json.loads(json.dumps(payload))
        mutate(changed)
        with pytest.raises(ValueError):
            admit_tuned_model_registry_record(changed)
    target_crossing = json.loads(json.dumps(payload))
    target_crossing["transition"] = "SUSPEND"
    body = {key: value for key, value in target_crossing.items() if key != "registry_record_sha256"}
    target_crossing["registry_record_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="target"):
        admit_tuned_model_registry_record(target_crossing)


def test_rehashed_redundant_coordinate_crossing_is_rejected() -> None:
    payload = approved_chain()[-1].to_dict()
    payload["binding_revision"] = 99
    body = {key: value for key, value in payload.items() if key != "registry_record_sha256"}
    payload["registry_record_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="exact canonical"):
        admit_tuned_model_registry_record(payload)


def test_registry_has_no_effectful_runtime_surface() -> None:
    source = Path("src/ai_video_production/dbd_tuned_model_registry.py").read_text(encoding="utf-8")
    for forbidden in ("sqlite3", "subprocess", "requests", "urllib", "Path(", "open(", "write_text", "write_bytes"):
        assert forbidden not in source
