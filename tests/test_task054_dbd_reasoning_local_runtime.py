from __future__ import annotations

from dataclasses import replace
import json

import pytest

from ai_video_production.dbd_reasoning_local_runtime import (
    LocalModelSelectionReceipt,
    LocalModelSelectionStore,
    LocalReasoningRuntimeService,
    RuntimeCheckId,
    RuntimeCheckStatus,
    load_local_model_catalog,
)


def _pass_result(candidate) -> dict[str, object]:
    return {
        "bootstrap": "PASS",
        "python": "3.12.3",
        "venv_match": True,
        "packages": {
            name: {"expected": version, "actual": version, "match": True}
            for name, version in candidate.package_versions.items()
        },
        "model": {
            "found": True,
            "safe_root": True,
            "file_count": candidate.file_count,
            "total_bytes": candidate.total_bytes,
            "mismatch_count": 0,
        },
        "gpu": {
            "available": True,
            "cuda_version": "12.8",
            "count": 1,
            "name": "NVIDIA GeForce RTX 4070 SUPER",
            "free_bytes": candidate.peak_gpu_bytes + 2 * (1024 ** 3),
            "total_bytes": 12_878_086_144,
        },
        "inference": {"attempted": True, "passed": True},
    }


def test_packaged_catalog_projects_verified_base_model_without_dataset_gate() -> None:
    candidates = load_local_model_catalog()

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_id == "qwen3-8b-b968826d"
    assert candidate.repository_id == "Qwen/Qwen3-8B"
    assert candidate.immutable_revision == "b968826d9c46dd6066d109eabc6255188de91218"
    assert candidate.file_count == 15
    assert candidate.total_bytes == 16_397_461_266
    assert len(candidate.files) == 15
    assert sum(item.logical_path.endswith(".safetensors") for item in candidate.files) == 5


def test_public_catalog_requires_current_ready_preflight_before_selection(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )

    initial = service.catalog_snapshot()

    assert initial.status_code == "LOCAL_FREE_MODEL_NOT_SELECTABLE"
    assert initial.entries[0].cost_class == "LOCAL_FREE_AI"
    assert initial.entries[0].selectable is False
    assert initial.entries[0].status_code == "COMPUTE_PROFILE_REJECTED"
    assert "参照専用" in initial.status_message_ja
    assert "［設定］→［AIモデル］" in initial.next_action_ja
    assert "Modelごとに事前チェック" not in initial.next_action_ja
    assert service.selected_candidate() is None
    with pytest.raises(ValueError, match="trusted Product compute admission"):
        service.save_selection(candidate.candidate_id)

    assert service.preflight(candidate.candidate_id).ready is False
    blocked = service.catalog_snapshot()
    assert blocked.status_code == "LOCAL_FREE_MODEL_NOT_SELECTABLE"
    assert blocked.entries[0].selectable is False
    with pytest.raises(ValueError, match="trusted Product compute admission"):
        service.save_selection(candidate.candidate_id)
    assert service.store.latest() is None


def test_public_catalog_keeps_zero_candidates_actionable_and_unselectable(tmp_path) -> None:
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
        catalog_provider=lambda: (),
    )

    snapshot = service.catalog_snapshot()

    assert service.selected_candidate() is None
    assert snapshot.entries == ()
    assert snapshot.status_code == "LOCAL_MODEL_CATALOG_EMPTY"
    assert "自動downloadやinstallは行いません" in snapshot.next_action_ja
    with pytest.raises(ValueError, match="unknown"):
        service.save_selection("missing-candidate")
def test_feature_local_selection_store_is_read_only(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    store = LocalModelSelectionStore(tmp_path, workspace_id="workspace-1")

    with pytest.raises(ValueError, match="feature-local model selection writes are disabled"):
        store.select(candidate)
    assert store.latest() is None
    assert not store.directory.exists()

    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1", workspace_root=tmp_path
    )
    assert service.selected_candidate() is None
    assert service.store.latest() is None


def test_tampered_or_foreign_selection_fails_closed(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    store = LocalModelSelectionStore(tmp_path, workspace_id="workspace-1")
    receipt = LocalModelSelectionReceipt(
        receipt_id="task054-model-selection-" + "a" * 32,
        workspace_id="workspace-1",
        candidate_id=candidate.candidate_id,
        catalog_sha256=candidate.catalog_sha256,
        selected_at="2026-08-31T00:00:00.000Z",
        previous_receipt_sha256=None,
    )
    store.directory.mkdir(parents=True)
    path = store.directory / f"{receipt.receipt_id}.json"
    path.write_text(json.dumps(receipt.to_dict()), encoding="utf-8")
    value = json.loads(path.read_text(encoding="utf-8"))
    value["workspace_id"] = "workspace-2"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="receipt"):
        store.latest()


def test_data_only_probe_observation_keeps_dataset_training_separate(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1", workspace_root=tmp_path,
    )
    snapshot = service._evaluate_probe_observation_for_test(
        candidate.candidate_id, _pass_result(candidate)
    )

    assert snapshot.ready is True
    assert [item.check_id for item in snapshot.checks] == list(RuntimeCheckId)
    assert snapshot.checks[-1].status is RuntimeCheckStatus.NOT_REQUIRED
    assert snapshot.provider_execution_authorized is False
    assert snapshot.training_authorized is False
    assert snapshot.authority_created is False
    with pytest.raises(ValueError, match="cannot grant execution"):
        replace(snapshot, authority_created=True)
    assert service.catalog_snapshot().entries[0].selectable is False
    service._preflight_by_candidate[candidate.candidate_id] = snapshot
    forged_cache_entry = service.catalog_snapshot().entries[0]
    assert forged_cache_entry.selectable is False
    assert forged_cache_entry.status_code == "TRUSTED_GPU_ADMISSION_REQUIRED"
    with pytest.raises(ValueError, match="trusted Product compute admission"):
        service.save_selection(candidate.candidate_id)
    assert service.store.latest() is None


@pytest.mark.parametrize("package_name", ["datasets", "peft", "trl"])
def test_training_only_package_drift_does_not_block_base_model_preflight(
    tmp_path, package_name
) -> None:
    candidate = load_local_model_catalog()[0]
    value = _pass_result(candidate)
    value["packages"][package_name]["match"] = False
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )

    snapshot = service._evaluate_probe_observation_for_test(
        candidate.candidate_id, value
    )

    assert snapshot.ready is True
    checks = {item.check_id: item for item in snapshot.checks}
    assert checks[RuntimeCheckId.PACKAGES].status is RuntimeCheckStatus.PASS
    assert checks[RuntimeCheckId.DATASET_TRAINING].status is RuntimeCheckStatus.NOT_REQUIRED


def test_python_runtime_identity_mismatch_fails_venv_preflight(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    value = _pass_result(candidate)
    value["python"] = "3.11.9"
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )

    snapshot = service._evaluate_probe_observation_for_test(
        candidate.candidate_id, value
    )

    checks = {item.check_id: item for item in snapshot.checks}
    assert checks[RuntimeCheckId.VENV].status is RuntimeCheckStatus.FAIL
    assert snapshot.ready is False


@pytest.mark.parametrize(
    ("field", "expected_code"),
    [
        ("packages", "PACKAGE_VERSION_MISMATCH"),
        ("model", "MODEL_PATH_OR_HASH_MISMATCH"),
        ("gpu", "GPU_OR_VRAM_UNAVAILABLE"),
        ("inference", "OFFLINE_INFERENCE_FAILED"),
    ],
)
def test_runtime_failure_reasons_are_individual_and_public_safe(
    tmp_path, field, expected_code
) -> None:
    candidate = load_local_model_catalog()[0]
    value = _pass_result(candidate)
    if field == "packages":
        value[field]["torch"]["match"] = False
    elif field == "model":
        value[field]["mismatch_count"] = 1
    elif field == "gpu":
        value[field]["free_bytes"] = 1
    else:
        value[field]["passed"] = False

    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )
    snapshot = service._evaluate_probe_observation_for_test(
        candidate.candidate_id, value
    )

    assert snapshot.ready is False
    assert expected_code in {item.detail_code for item in snapshot.checks}
    public_text = " ".join(
        item.message_ja + " " + item.next_action_ja for item in snapshot.checks
    )
    assert "/home/" not in public_text
    assert "C:\\" not in public_text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cuda_version", "12.7"),
        ("count", 0),
        ("name", ""),
        ("total_bytes", 1),
    ],
)
def test_gpu_identity_requires_exact_cuda_device_and_capacity(
    tmp_path, field, value
) -> None:
    candidate = load_local_model_catalog()[0]
    result = _pass_result(candidate)
    result["gpu"][field] = value
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )

    snapshot = service._evaluate_probe_observation_for_test(
        candidate.candidate_id, result
    )

    check = next(item for item in snapshot.checks if item.check_id is RuntimeCheckId.GPU)
    assert check.status is RuntimeCheckStatus.FAIL
    assert check.detail_code == "GPU_OR_VRAM_UNAVAILABLE"
    assert snapshot.ready is False


@pytest.mark.parametrize(
    ("bootstrap", "expected_code"),
    [
        ("PREFLIGHT_BUSY", "PREFLIGHT_ALREADY_RUNNING"),
        ("PREFLIGHT_LOCK_UNSAFE", "PREFLIGHT_LOCK_UNSAFE"),
    ],
)
def test_cross_process_preflight_lock_fails_closed_without_duplicate_runtime(
    tmp_path, bootstrap, expected_code
) -> None:
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )

    snapshot = service._evaluate_probe_observation_for_test(
        "qwen3-8b-b968826d", {"bootstrap": bootstrap}
    )

    checks = {item.check_id: item for item in snapshot.checks}
    assert checks[RuntimeCheckId.WSL].status is RuntimeCheckStatus.PASS
    assert checks[RuntimeCheckId.VENV].detail_code == expected_code
    assert checks[RuntimeCheckId.INFERENCE].detail_code == expected_code
    assert checks[RuntimeCheckId.DATASET_TRAINING].status is RuntimeCheckStatus.NOT_REQUIRED
    assert snapshot.ready is False


def test_missing_venv_is_not_confused_with_model_or_dataset_gate(tmp_path) -> None:
    value = {"bootstrap": "VENV_MISSING"}
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
    )

    snapshot = service._evaluate_probe_observation_for_test(
        "qwen3-8b-b968826d", value
    )

    checks = {item.check_id: item for item in snapshot.checks}
    assert checks[RuntimeCheckId.WSL].status is RuntimeCheckStatus.PASS
    assert checks[RuntimeCheckId.VENV].detail_code == "VENV_MISSING_OR_MISMATCH"
    assert checks[RuntimeCheckId.DATASET_TRAINING].status is RuntimeCheckStatus.NOT_REQUIRED
    assert snapshot.ready is False


def test_process_failure_is_classified_without_raw_exception_or_path(tmp_path) -> None:
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1", workspace_root=tmp_path,
    )
    snapshot = service.preflight("qwen3-8b-b968826d")

    assert snapshot.ready is False
    assert {item.detail_code for item in snapshot.checks} >= {
        "CATALOG_VERIFIED", "RUNTIME_PROCESS_FAILED", "DATASET_TRAINING_SEPARATE_GATE",
    }
    assert "secret" not in " ".join(item.message_ja for item in snapshot.checks).casefold()
