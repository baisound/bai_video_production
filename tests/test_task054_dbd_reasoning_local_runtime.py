from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from ai_video_production.dbd_reasoning_local_runtime import (
    LocalModelSelectionStore,
    LocalReasoningRuntimeService,
    RuntimeCheckId,
    RuntimeCheckStatus,
    load_local_model_catalog,
)


class _CompletedProcess:
    def __init__(self, value: dict[str, object], *, returncode: int = 0) -> None:
        self.returncode = returncode
        self._stdout = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self._running = True

    def poll(self):
        return None if self._running else self.returncode

    def communicate(self, timeout=None):
        self._running = False
        return self._stdout, b""

    def terminate(self):
        self._running = False

    def kill(self):
        self._running = False

    def wait(self, timeout=None):
        self._running = False
        return self.returncode


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


def test_selection_is_persisted_and_restored_without_granting_execution(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    store = LocalModelSelectionStore(tmp_path, workspace_id="workspace-1")

    receipt = store.select(candidate)
    restored = LocalModelSelectionStore(tmp_path, workspace_id="workspace-1").latest()

    assert restored == receipt
    assert restored.to_dict()["provider_execution_authorized"] is False
    assert restored.to_dict()["training_authorized"] is False
    assert restored.to_dict()["dataset_adoption_authorized"] is False
    assert store.select(candidate) == receipt
    assert len(store.list_receipts()) == 1


def test_concurrent_model_selection_is_serialized_to_one_current_receipt(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]

    def select():
        return LocalModelSelectionStore(
            tmp_path, workspace_id="workspace-1"
        ).select(candidate)

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = tuple(executor.map(lambda _index: select(), range(2)))

    store = LocalModelSelectionStore(tmp_path, workspace_id="workspace-1")
    assert receipts[0] == receipts[1]
    assert store.list_receipts() == (receipts[0],)


def test_tampered_or_foreign_selection_fails_closed(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    store = LocalModelSelectionStore(tmp_path, workspace_id="workspace-1")
    receipt = store.select(candidate)
    path = store.directory / f"{receipt.receipt_id}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["workspace_id"] = "workspace-2"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="receipt"):
        store.latest()


def test_exact_runtime_preflight_passes_and_keeps_dataset_training_separate(tmp_path) -> None:
    candidate = load_local_model_catalog()[0]
    observed: dict[str, object] = {}

    def popen(command, **options):
        observed["command"] = command
        observed["options"] = options
        return _CompletedProcess(_pass_result(candidate))

    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1", workspace_root=tmp_path, popen_factory=popen,
    )
    snapshot = service.preflight(candidate.candidate_id)

    assert snapshot.ready is True
    assert [item.check_id for item in snapshot.checks] == list(RuntimeCheckId)
    assert snapshot.checks[-1].status is RuntimeCheckStatus.NOT_REQUIRED
    assert snapshot.provider_execution_authorized is False
    assert snapshot.training_authorized is False
    assert observed["command"][0].lower().endswith("wsl.exe")
    assert observed["command"][1:4] == ["-d", "Ubuntu", "--"]
    assert observed["options"]["shell"] is False
    assert observed["options"]["stdin"] is not None


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
        popen_factory=lambda *_args, **_kwargs: _CompletedProcess(value),
    )

    snapshot = service.preflight(candidate.candidate_id)

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
        popen_factory=lambda *_args, **_kwargs: _CompletedProcess(value),
    )

    snapshot = service.preflight(candidate.candidate_id)

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
        popen_factory=lambda *_args, **_kwargs: _CompletedProcess(value),
    )
    snapshot = service.preflight(candidate.candidate_id)

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
        popen_factory=lambda *_args, **_kwargs: _CompletedProcess(result),
    )

    snapshot = service.preflight(candidate.candidate_id)

    check = next(item for item in snapshot.checks if item.check_id is RuntimeCheckId.GPU)
    assert check.status is RuntimeCheckStatus.FAIL
    assert check.detail_code == "GPU_OR_VRAM_UNAVAILABLE"
    assert snapshot.ready is False


@pytest.mark.parametrize(
    ("bootstrap", "returncode", "expected_code"),
    [
        ("PREFLIGHT_BUSY", 43, "PREFLIGHT_ALREADY_RUNNING"),
        ("PREFLIGHT_LOCK_UNSAFE", 44, "PREFLIGHT_LOCK_UNSAFE"),
    ],
)
def test_cross_process_preflight_lock_fails_closed_without_duplicate_runtime(
    tmp_path, bootstrap, returncode, expected_code
) -> None:
    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1",
        workspace_root=tmp_path,
        popen_factory=lambda *_args, **_kwargs: _CompletedProcess(
            {"bootstrap": bootstrap}, returncode=returncode
        ),
    )

    snapshot = service.preflight("qwen3-8b-b968826d")

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
        popen_factory=lambda *_args, **_kwargs: _CompletedProcess(value, returncode=42),
    )

    snapshot = service.preflight("qwen3-8b-b968826d")

    checks = {item.check_id: item for item in snapshot.checks}
    assert checks[RuntimeCheckId.WSL].status is RuntimeCheckStatus.PASS
    assert checks[RuntimeCheckId.VENV].detail_code == "VENV_MISSING_OR_MISMATCH"
    assert checks[RuntimeCheckId.DATASET_TRAINING].status is RuntimeCheckStatus.NOT_REQUIRED
    assert snapshot.ready is False


def test_process_failure_is_classified_without_raw_exception_or_path(tmp_path) -> None:
    def fail(*_args, **_kwargs):
        raise OSError(r"private path C:\\secret\\runtime")

    service = LocalReasoningRuntimeService(
        workspace_id="workspace-1", workspace_root=tmp_path, popen_factory=fail,
    )
    snapshot = service.preflight("qwen3-8b-b968826d")

    assert snapshot.ready is False
    assert {item.detail_code for item in snapshot.checks} >= {
        "CATALOG_VERIFIED", "RUNTIME_PROCESS_FAILED", "DATASET_TRAINING_SEPARATE_GATE",
    }
    assert "secret" not in " ".join(item.message_ja for item in snapshot.checks).casefold()
