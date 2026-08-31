"""TASK-054 local base-model catalog and fail-closed runtime preflight.

The catalog remains visible while Dataset/training gates are open. Product
process launch and selection writes stay disabled until TASK-066 supplies a
trusted, one-use compute-admission boundary. Fixture observations are data-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping
from uuid import uuid4

from .desktop_compute_policy import (
    ComputePreference,
    DesktopComputeProfileStore,
    ProfileLoadStatus,
)
from .desktop_compute_diagnostics import (
    BoundedDesktopDiagnostics,
    DiagnosticEvent,
    DiagnosticSeverity,
)
from .desktop_install_layout import (
    DesktopInstallLayout,
    derive_binary_root,
    resolve_desktop_install_layout,
)
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256


MODEL_SELECTION_SCHEMA_VERSION = "1.0.0"
_CANDIDATE_ID = "qwen3-8b-b968826d"
_REPOSITORY_ID = "Qwen/Qwen3-8B"
_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
_MODEL_REF = "model-cache://task054/qwen3-8b-b968826d"
_REPORT_SHA256 = "38e8e0d0398bd6661b519cf70188ffa7527893d3db086a1e153e477863046e0c"
_SMOKE_SHA256 = "c4eaba097ad76d85f595d28d9619c3cfdebdd87fd1968490ba9b8f703ff6824e"
_INVENTORY_SHA256 = "5e063d7779d5affb32b480e70534d667aef407cd5258a507ec8cd83afff116f6"
_MODEL_ROOT_RELATIVE = f"task054-r6b/models/Qwen3-8B-{_REVISION}"
_VENV_PYTHON_RELATIVE = ".venvs/bvp-task054-training/bin/python"
_EXPECTED_CUDA_VERSION = "12.8"
_RUNTIME_PACKAGES = (
    "accelerate", "bitsandbytes", "huggingface-hub", "torch", "transformers",
)
_TRAINING_PACKAGES = ("datasets", "peft", "trl")
_LOCKED_PACKAGES = _RUNTIME_PACKAGES + _TRAINING_PACKAGES
_SELECTION_ID_RE = re.compile(r"task054-model-selection-[0-9a-f]{32}")
_WORKSPACE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
_UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")
def _resource_path(relative: str) -> Path:
    if bool(getattr(sys, "frozen", False)):
        root = Path(getattr(sys, "_MEIPASS")) / "task054_runtime"
    else:
        root = Path(__file__).resolve().parents[2]
    return root / relative


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_canonical_text_file(path: Path) -> str:
    """Hash Git-canonical LF bytes so Windows checkout policy cannot create drift."""

    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _require_config_line(text: str, line: str) -> None:
    if sum(1 for item in text.splitlines() if item.strip() == line) != 1:
        raise ValueError(f"TASK-054 base-model catalog field is missing or duplicated: {line.split(':', 1)[0]}")


def _parse_lock_versions(text: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "==" not in value:
            continue
        name, remainder = value.split("==", 1)
        version = remainder.split()[0]
        key = name.casefold()
        if key in versions:
            raise ValueError("TASK-054 runtime lock contains a duplicate distribution")
        versions[key] = version
    if any(name not in versions for name in _LOCKED_PACKAGES):
        raise ValueError("TASK-054 runtime lock is missing a principal distribution")
    return {name: versions[name] for name in _LOCKED_PACKAGES}


@dataclass(frozen=True, slots=True)
class LocalModelFile:
    logical_path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        path = Path(self.logical_path)
        if (
            not self.logical_path
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != self.logical_path
        ):
            raise ValueError("model manifest path is not a safe relative path")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 1:
            raise ValueError("model manifest size is invalid")
        validate_sha256(self.sha256, field_name="model_file_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_path": self.logical_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256.removeprefix("sha256:"),
        }


@dataclass(frozen=True, slots=True)
class LocalModelCandidate:
    candidate_id: str
    display_name: str
    repository_id: str
    immutable_revision: str
    model_ref: str
    license_spdx: str
    file_count: int
    total_bytes: int
    inventory_sha256: str
    report_sha256: str
    smoke_sha256: str
    peak_gpu_bytes: int
    package_versions: Mapping[str, str]
    files: tuple[LocalModelFile, ...]
    catalog_sha256: str

    def __post_init__(self) -> None:
        if (
            self.candidate_id != _CANDIDATE_ID
            or self.repository_id != _REPOSITORY_ID
            or self.immutable_revision != _REVISION
            or self.model_ref != _MODEL_REF
            or self.license_spdx != "Apache-2.0"
        ):
            raise ValueError("unsupported TASK-054 base-model candidate")
        if self.file_count != len(self.files) or self.file_count != 15:
            raise ValueError("base-model file count is inconsistent")
        if self.total_bytes != sum(item.size_bytes for item in self.files):
            raise ValueError("base-model total size is inconsistent")
        if len({item.logical_path for item in self.files}) != len(self.files):
            raise ValueError("base-model manifest contains duplicate paths")
        for name in ("inventory_sha256", "report_sha256", "smoke_sha256", "catalog_sha256"):
            validate_sha256(getattr(self, name), field_name=name)
        if self.peak_gpu_bytes < 1 or set(self.package_versions) != set(_LOCKED_PACKAGES):
            raise ValueError("base-model runtime identity is incomplete")

    @property
    def display_label(self) -> str:
        return f"{self.display_name}（固定rev {self.immutable_revision[:8]}）"

    def probe_payload(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "repository_id": self.repository_id,
            "immutable_revision": self.immutable_revision,
            "model_root_relative": _MODEL_ROOT_RELATIVE,
            "venv_python_relative": _VENV_PYTHON_RELATIVE,
            "files": [item.to_dict() for item in self.files],
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "package_versions": dict(self.package_versions),
            "runtime_package_names": list(_RUNTIME_PACKAGES),
            "expected_cuda_version": _EXPECTED_CUDA_VERSION,
            "minimum_free_gpu_bytes": self.peak_gpu_bytes + (1024 ** 3),
        }


@dataclass(frozen=True, slots=True)
class LocalModelCatalogEntry:
    """Public, fail-closed admission state for one locally inventoried Model."""

    candidate: LocalModelCandidate
    cost_class: str
    selectable: bool
    status_code: str
    status_message_ja: str
    next_action_ja: str

    def __post_init__(self) -> None:
        if self.cost_class != "LOCAL_FREE_AI":
            raise ValueError("TASK-054 public catalog accepts only local-free Models")
        if not self.status_code or not self.status_message_ja or not self.next_action_ja:
            raise ValueError("TASK-054 public catalog status is incomplete")


@dataclass(frozen=True, slots=True)
class LocalModelCatalogSnapshot:
    entries: tuple[LocalModelCatalogEntry, ...]
    status_code: str
    status_message_ja: str
    next_action_ja: str

    def __post_init__(self) -> None:
        if not self.status_code or not self.status_message_ja or not self.next_action_ja:
            raise ValueError("TASK-054 public catalog snapshot is incomplete")

def load_local_model_catalog() -> tuple[LocalModelCandidate, ...]:
    config_path = _resource_path("config/task054/base-model-candidates.yaml")
    report_path = _resource_path("reports/task054/r6b-qwen3-8b-b968826d/base-model-verification.json")
    smoke_path = _resource_path("reports/task054/r6b-qwen3-8b-b968826d/local-nf4-smoke.json")
    lock_path = _resource_path("requirements/task054-training.lock")
    for path in (config_path, report_path, smoke_path, lock_path):
        if not path.is_file() or path.is_symlink():
            raise ValueError("TASK-054 packaged runtime Evidence is missing or unsafe")

    config_text = config_path.read_text(encoding="utf-8")
    for line in (
        "schema_version: 1",
        "task_id: TASK-054",
        "selection_state: verified_pilot_candidate_no_promotion",
        f"- candidate_id: {_CANDIDATE_ID}",
        f"repository_id: {_REPOSITORY_ID}",
        f"immutable_revision: {_REVISION}",
        f"model_ref: {_MODEL_REF}",
        "spdx: Apache-2.0",
        "public: true",
        "gated: false",
        "credential_required: false",
        "trust_remote_code: false",
        "file_count: 15",
        "total_bytes: 16397461266",
        f"inventory_sha256: {_INVENTORY_SHA256}",
        "verification_report_ref: reports/task054/r6b-qwen3-8b-b968826d/base-model-verification.json",
        f"verification_report_sha256: {_REPORT_SHA256}",
        "verification_status: PASS",
        "local_files_only: true",
        "promotion_allowed: false",
    ):
        _require_config_line(config_text, line)
    if config_text.count("candidate_id:") != 1:
        raise ValueError("TASK-054 packaged catalog has an unsupported candidate count")

    if (
        _sha256_canonical_text_file(report_path) != _REPORT_SHA256
        or _sha256_canonical_text_file(smoke_path) != _SMOKE_SHA256
    ):
        raise ValueError("TASK-054 packaged runtime Evidence checksum mismatch")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    if (
        report.get("candidate_id") != _CANDIDATE_ID
        or report.get("repository_id") != _REPOSITORY_ID
        or report.get("immutable_revision") != _REVISION
        or report.get("license_spdx") != "Apache-2.0"
        or report.get("verification_status") != "PASS"
        or report.get("state") != "VERIFIED_PUBLIC_BASE_MODEL_ACQUIRED_NO_TRAINING_NO_PROMOTION"
        or report.get("gated") is not False
        or report.get("trust_remote_code") is not False
    ):
        raise ValueError("TASK-054 base-model verification report is not canonical")
    raw_files = report.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("TASK-054 base-model verification file inventory is absent")
    files = tuple(
        LocalModelFile(
            logical_path=item["logical_path"],
            size_bytes=item["size_bytes"],
            sha256="sha256:" + item["sha256"],
        )
        for item in raw_files
        if isinstance(item, dict) and set(item) == {"logical_path", "size_bytes", "sha256"}
    )
    if len(files) != len(raw_files):
        raise ValueError("TASK-054 base-model file inventory has an invalid row")
    if (
        smoke.get("base_model_candidate_id") != _CANDIDATE_ID
        or smoke.get("result") != "PASS"
        or smoke.get("local_files_only") is not True
        or smoke.get("trust_remote_code") is not False
        or smoke.get("quantization") != "nf4-double-quant"
    ):
        raise ValueError("TASK-054 local smoke report is not canonical")
    packages = _parse_lock_versions(lock_path.read_text(encoding="utf-8"))
    if packages["torch"] != smoke.get("torch_version") or packages["transformers"] != smoke.get("transformers_version"):
        raise ValueError("TASK-054 smoke report and runtime lock disagree")

    catalog_body = {
        "config_sha256": _sha256_canonical_text_file(config_path),
        "report_sha256": _REPORT_SHA256,
        "smoke_sha256": _SMOKE_SHA256,
        "lock_sha256": _sha256_canonical_text_file(lock_path),
    }
    return (
        LocalModelCandidate(
            candidate_id=_CANDIDATE_ID,
            display_name="Qwen3-8B 日本語実況・解説ベースモデル",
            repository_id=_REPOSITORY_ID,
            immutable_revision=_REVISION,
            model_ref=_MODEL_REF,
            license_spdx="Apache-2.0",
            file_count=report["file_count"],
            total_bytes=report["total_bytes"],
            inventory_sha256="sha256:" + _INVENTORY_SHA256,
            report_sha256="sha256:" + _REPORT_SHA256,
            smoke_sha256="sha256:" + _SMOKE_SHA256,
            peak_gpu_bytes=smoke["peak_gpu_bytes"],
            package_versions=packages,
            files=files,
            catalog_sha256=sha256_bytes(canonical_json_bytes(catalog_body)),
        ),
    )


@dataclass(frozen=True, slots=True)
class LocalModelSelectionReceipt:
    receipt_id: str
    workspace_id: str
    candidate_id: str
    catalog_sha256: str
    selected_at: str
    previous_receipt_sha256: str | None

    def __post_init__(self) -> None:
        if not _SELECTION_ID_RE.fullmatch(self.receipt_id):
            raise ValueError("model-selection receipt_id is invalid")
        if not _WORKSPACE_ID_RE.fullmatch(self.workspace_id):
            raise ValueError("model-selection workspace_id is invalid")
        if self.candidate_id != _CANDIDATE_ID:
            raise ValueError("model-selection candidate_id is unsupported")
        validate_sha256(self.catalog_sha256, field_name="catalog_sha256")
        if not _UTC_RE.fullmatch(self.selected_at):
            raise ValueError("model-selection selected_at is invalid")
        datetime.fromisoformat(self.selected_at.replace("Z", "+00:00"))
        if self.previous_receipt_sha256 is not None:
            validate_sha256(self.previous_receipt_sha256, field_name="previous_receipt_sha256")

    def to_dict(self) -> dict[str, object]:
        body = {
            "schema_version": MODEL_SELECTION_SCHEMA_VERSION,
            "record_kind": "DBD_REASONING_LOCAL_MODEL_SELECTION",
            "receipt_id": self.receipt_id,
            "workspace_id": self.workspace_id,
            "candidate_id": self.candidate_id,
            "catalog_sha256": self.catalog_sha256,
            "selected_at": self.selected_at,
            "previous_receipt_sha256": self.previous_receipt_sha256,
            "provider_execution_authorized": False,
            "training_authorized": False,
            "dataset_adoption_authorized": False,
        }
        return {**body, "receipt_sha256": sha256_bytes(canonical_json_bytes(body))}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "LocalModelSelectionReceipt":
        expected = {
            "schema_version", "record_kind", "receipt_id", "workspace_id",
            "candidate_id", "catalog_sha256", "selected_at",
            "previous_receipt_sha256", "provider_execution_authorized",
            "training_authorized", "dataset_adoption_authorized", "receipt_sha256",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema_version") != MODEL_SELECTION_SCHEMA_VERSION
            or value.get("record_kind") != "DBD_REASONING_LOCAL_MODEL_SELECTION"
            or any(value.get(name) is not False for name in (
                "provider_execution_authorized", "training_authorized", "dataset_adoption_authorized",
            ))
        ):
            raise ValueError("model-selection receipt shape is invalid")
        body = {key: item for key, item in value.items() if key != "receipt_sha256"}
        if value.get("receipt_sha256") != sha256_bytes(canonical_json_bytes(body)):
            raise ValueError("model-selection receipt checksum mismatch")
        try:
            receipt = cls(
                receipt_id=value["receipt_id"], workspace_id=value["workspace_id"],
                candidate_id=value["candidate_id"], catalog_sha256=value["catalog_sha256"],
                selected_at=value["selected_at"],
                previous_receipt_sha256=value["previous_receipt_sha256"],
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("model-selection receipt is invalid") from exc
        if receipt.to_dict() != dict(value):
            raise ValueError("model-selection receipt is not canonical")
        return receipt


class LocalModelSelectionStore:
    def __init__(self, workspace_root: str | Path, *, workspace_id: str) -> None:
        self.directory = Path(workspace_root) / "control" / "dbd-reasoning-model-selection-receipts"
        if not isinstance(workspace_id, str) or not _WORKSPACE_ID_RE.fullmatch(workspace_id):
            raise ValueError("workspace_id is invalid")
        self.workspace_id = workspace_id

    def list_receipts(self) -> tuple[LocalModelSelectionReceipt, ...]:
        if not self.directory.exists():
            return ()
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise ValueError("model-selection receipt directory is unsafe")
        receipts: list[LocalModelSelectionReceipt] = []
        for path in sorted(self.directory.glob("*.json")):
            if path.is_symlink() or not path.is_file():
                raise ValueError("model-selection receipt file is unsafe")
            try:
                receipt = LocalModelSelectionReceipt.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError("model-selection receipt cannot be admitted") from exc
            if receipt.workspace_id != self.workspace_id or path.name != f"{receipt.receipt_id}.json":
                raise ValueError("model-selection receipt identity is crossed")
            receipts.append(receipt)
        ordered = tuple(sorted(receipts, key=lambda item: (item.selected_at, item.receipt_id)))
        previous: str | None = None
        for receipt in ordered:
            if receipt.previous_receipt_sha256 != previous:
                raise ValueError("model-selection receipt chain is discontinuous")
            previous = receipt.to_dict()["receipt_sha256"]
        return ordered

    def latest(self) -> LocalModelSelectionReceipt | None:
        values = self.list_receipts()
        return values[-1] if values else None

    def select(self, candidate: LocalModelCandidate) -> LocalModelSelectionReceipt:
        if not isinstance(candidate, LocalModelCandidate):
            raise ValueError("candidate is invalid")
        raise ValueError("feature-local model selection writes are disabled")


class RuntimeCheckId(str, Enum):
    CATALOG = "CATALOG"
    WSL = "WSL"
    VENV = "VENV"
    PACKAGES = "PACKAGES"
    MODEL_IDENTITY = "MODEL_IDENTITY"
    GPU = "GPU"
    INFERENCE = "INFERENCE"
    DATASET_TRAINING = "DATASET_TRAINING"


class RuntimeCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_REQUIRED = "NOT_REQUIRED"


_CHECK_LABELS_JA = {
    RuntimeCheckId.CATALOG: "Model Catalog",
    RuntimeCheckId.WSL: "WSL起動・接続",
    RuntimeCheckId.VENV: "専用Python環境",
    RuntimeCheckId.PACKAGES: "必要package/version",
    RuntimeCheckId.MODEL_IDENTITY: "Model revision/shard/hash",
    RuntimeCheckId.GPU: "CUDA/GPU/利用可能VRAM",
    RuntimeCheckId.INFERENCE: "最小offline推論",
    RuntimeCheckId.DATASET_TRAINING: "Dataset・学習Gate",
}


@dataclass(frozen=True, slots=True)
class RuntimePreflightCheck:
    check_id: RuntimeCheckId
    status: RuntimeCheckStatus
    detail_code: str
    message_ja: str
    next_action_ja: str

    def __post_init__(self) -> None:
        if not isinstance(self.check_id, RuntimeCheckId) or not isinstance(self.status, RuntimeCheckStatus):
            raise ValueError("runtime preflight enum is invalid")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", self.detail_code):
            raise ValueError("runtime preflight detail_code is invalid")
        for value in (self.message_ja, self.next_action_ja):
            if not isinstance(value, str) or not value or len(value) > 500 or any(ord(c) < 32 for c in value):
                raise ValueError("runtime preflight public message is invalid")

    @property
    def label_ja(self) -> str:
        return _CHECK_LABELS_JA[self.check_id]


@dataclass(frozen=True, slots=True)
class LocalRuntimePreflightSnapshot:
    candidate_id: str
    checks: tuple[RuntimePreflightCheck, ...]
    ready: bool
    process_ownership: str = "APPLICATION_OWNED_ONE_SHOT_CHILD_SHARED_WSL_NOT_STOPPED"
    provider_execution_authorized: bool = False
    training_authorized: bool = False
    authority_created: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != _CANDIDATE_ID:
            raise ValueError("runtime preflight candidate is invalid")
        if tuple(item.check_id for item in self.checks) != tuple(RuntimeCheckId):
            raise ValueError("runtime preflight checks are not canonically ordered")
        required = tuple(item for item in self.checks if item.status is not RuntimeCheckStatus.NOT_REQUIRED)
        if self.ready != all(item.status is RuntimeCheckStatus.PASS for item in required):
            raise ValueError("runtime preflight readiness does not match checks")
        if self.process_ownership != "APPLICATION_OWNED_ONE_SHOT_CHILD_SHARED_WSL_NOT_STOPPED":
            raise ValueError("runtime preflight process ownership is invalid")
        if (
            self.provider_execution_authorized
            or self.training_authorized
            or self.authority_created
        ):
            raise ValueError("runtime preflight cannot grant execution or training authority")


@dataclass(frozen=True, slots=True)
class DbDComputeProfileReadback:
    profile_status: ProfileLoadStatus
    install_instance_id: str | None
    profile_revision: int
    selected_preference: ComputePreference
    profile_reason_code: str
    reasoning_reason_code: str
    training_reason_code: str
    trivia_reason_code: str
    reasoning_execution_authorized: bool = False
    training_authorized: bool = False
    training_human_gate_required: bool = True
    trivia_control_plane_available: bool = True
    frontend_kind: str = "TKINTER"
    ui_gpu_rendering_confirmed: bool = False
    ui_renderer_reason_code: str = "TKINTER_GPU_RENDERING_NOT_CONFIRMED"
    authority_created: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.profile_status, ProfileLoadStatus):
            raise ValueError("compute profile status is invalid")
        if not isinstance(self.selected_preference, ComputePreference):
            raise ValueError("compute preference is invalid")
        if not isinstance(self.profile_revision, int) or self.profile_revision < 0:
            raise ValueError("compute profile revision is invalid")
        if self.profile_status is not ProfileLoadStatus.LOADED and self.profile_revision != 0:
            raise ValueError("default compute profile cannot claim a durable revision")
        for value in (
            self.profile_reason_code,
            self.reasoning_reason_code,
            self.training_reason_code,
            self.trivia_reason_code,
        ):
            if re.fullmatch(r"[A-Z][A-Z0-9_]{1,95}", value) is None:
                raise ValueError("compute profile reason code is invalid")
        if (
            self.reasoning_execution_authorized
            or self.training_authorized
            or self.authority_created
        ):
            raise ValueError("profile readback cannot grant execution or training authority")
        if not self.training_human_gate_required:
            raise ValueError("profile readback cannot remove the training Human Gate")
        if not self.trivia_control_plane_available:
            raise ValueError("CPU-only Trivia control plane must remain available")
        if self.frontend_kind != "TKINTER":
            raise ValueError("DbD standalone frontend kind is invalid")
        if self.ui_gpu_rendering_confirmed:
            raise ValueError("compute profile cannot confirm Tk GPU rendering")
        if self.ui_renderer_reason_code != "TKINTER_GPU_RENDERING_NOT_CONFIRMED":
            raise ValueError("DbD standalone renderer reason is invalid")


def read_dbd_compute_profile(
    layout: DesktopInstallLayout,
) -> DbDComputeProfileReadback:
    """Project GF-A profile state without minting live GPU authority."""
    result = DesktopComputeProfileStore(layout).load()
    if (
        result.status is ProfileLoadStatus.LOADED
        and result.profile.selected_preference is ComputePreference.CPU_EXPLICIT
    ):
        reasoning_reason = "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
    elif result.status is ProfileLoadStatus.LOADED:
        reasoning_reason = "TRUSTED_GPU_ADMISSION_REQUIRED"
    elif result.status is ProfileLoadStatus.DEFAULT_MISSING:
        reasoning_reason = "COMPUTE_PROFILE_NOT_CONFIGURED"
    else:
        reasoning_reason = "COMPUTE_PROFILE_REJECTED"
    return DbDComputeProfileReadback(
        profile_status=result.status,
        install_instance_id=layout.install_instance_id,
        profile_revision=(
            result.profile.revision
            if result.status is ProfileLoadStatus.LOADED
            else 0
        ),
        selected_preference=result.profile.selected_preference,
        profile_reason_code=result.reason_code,
        reasoning_reason_code=reasoning_reason,
        training_reason_code=(
            "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
            if result.status is ProfileLoadStatus.LOADED
            and result.profile.selected_preference is ComputePreference.CPU_EXPLICIT
            else "TRUSTED_GPU_ADMISSION_REQUIRED"
        ),
        trivia_reason_code="CPU_ONLY_NOT_GPU_APPLICABLE",
    )


def read_packaged_dbd_compute_profile(
    executable_path: str | Path,
) -> DbDComputeProfileReadback:
    """Resolve the packaged InstallLayout internally and fail closed body-free."""
    try:
        binary_root = derive_binary_root(executable_path)
        layout = resolve_desktop_install_layout(binary_root)
        return read_dbd_compute_profile(layout)
    except Exception:
        return _unbound_dbd_compute_profile_readback()


_PACKAGED_DBD_APPLICATIONS = {
    "dbd.training": (
        "DBD_TRAINING_STUDIO",
        "dbd.training",
        "DISABLED",
        "BLOCKED",
        "OPEN_COMPUTE_SETTINGS",
    ),
    "dbd.trivia": (
        "DBD_TRIVIA_EDITOR",
        "dbd.trivia.editor",
        "CPU",
        "NOT_APPLICABLE",
        "NO_ACTION_REQUIRED",
    ),
}


def prepare_packaged_dbd_compute_profile(
    *,
    application_family: str,
) -> DbDComputeProfileReadback:
    """Bind packaged profile readback and one body-free common diagnostic."""
    if application_family not in _PACKAGED_DBD_APPLICATIONS:
        raise ValueError("packaged DbD application family is invalid")
    try:
        binary_root = derive_binary_root(sys.executable)
        layout = resolve_desktop_install_layout(binary_root)
        readback = read_dbd_compute_profile(layout)
    except Exception:
        return _unbound_dbd_compute_profile_readback()
    try:
        diagnostics = BoundedDesktopDiagnostics(
            layout, application_family=application_family
        )
        diagnostics.emit(
            _dbd_profile_diagnostic_event(
                readback, application_family=application_family
            )
        )
    except Exception:
        # Diagnostics are bounded Evidence, never launch authority.
        pass
    return readback


def _dbd_profile_diagnostic_event(
    readback: DbDComputeProfileReadback,
    *,
    application_family: str,
) -> DiagnosticEvent:
    from . import __version__ as application_version

    application, workload_id, backend, compatibility, next_action = (
        _PACKAGED_DBD_APPLICATIONS[application_family]
    )
    workload_reason = (
        readback.training_reason_code
        if workload_id == "dbd.training"
        else readback.trivia_reason_code
    )
    reason_code = (
        workload_reason
        if readback.profile_status is ProfileLoadStatus.LOADED
        else readback.profile_reason_code
    )
    nonce = str(uuid4())
    session_id = sha256_bytes(nonce.encode("ascii"))
    correlation_id = sha256_bytes(
        canonical_json_bytes(
            {
                "application": application,
                "install_instance_id": readback.install_instance_id,
                "profile_revision": readback.profile_revision,
                "session_id": session_id,
            }
        )
    )
    return DiagnosticEvent(
        application=application,
        application_version=application_version,
        session_id=session_id,
        event_category="COMPUTE_PROFILE_READBACK",
        severity=(
            DiagnosticSeverity.INFO
            if readback.profile_status is ProfileLoadStatus.LOADED
            else DiagnosticSeverity.WARN
        ),
        selected_preference=readback.selected_preference.value,
        detected_adapter="NOT_ATTESTED",
        effective_backend=backend,
        compatibility_result=compatibility,
        failure_stage=(
            "NONE"
            if readback.profile_status is ProfileLoadStatus.LOADED
            else "PROFILE_READBACK"
        ),
        reason_code=reason_code,
        next_action=next_action,
        exception_category="NONE",
        correlation_id=correlation_id,
    )


def _unbound_dbd_compute_profile_readback() -> DbDComputeProfileReadback:
    return DbDComputeProfileReadback(
        profile_status=ProfileLoadStatus.DEFAULT_REJECTED,
        install_instance_id=None,
        profile_revision=0,
        selected_preference=ComputePreference.AUTO_GPU_FIRST,
        profile_reason_code="INSTALL_LAYOUT_UNAVAILABLE",
        reasoning_reason_code="TRUSTED_GPU_ADMISSION_REQUIRED",
        training_reason_code="TRUSTED_GPU_ADMISSION_REQUIRED",
        trivia_reason_code="CPU_ONLY_NOT_GPU_APPLICABLE",
    )


class LocalReasoningRuntimeService:
    def __init__(
        self,
        *,
        workspace_id: str,
        workspace_root: str | Path,
        catalog_provider: Callable[[], tuple[LocalModelCandidate, ...]] = load_local_model_catalog,
        compute_profile_readback: DbDComputeProfileReadback | None = None,
    ) -> None:
        candidates = tuple(catalog_provider())
        if not all(isinstance(item, LocalModelCandidate) for item in candidates):
            raise ValueError("TASK-054 catalog provider returned an invalid candidate")
        if len({item.candidate_id for item in candidates}) != len(candidates):
            raise ValueError("TASK-054 catalog provider returned duplicate candidates")
        self.candidates = candidates
        self._preflight_by_candidate: dict[str, LocalRuntimePreflightSnapshot] = {}
        self.store = LocalModelSelectionStore(workspace_root, workspace_id=workspace_id)
        self.compute_profile_readback = (
            compute_profile_readback or _unbound_dbd_compute_profile_readback()
        )

    def selected_candidate(self) -> LocalModelCandidate | None:
        # Legacy feature-local receipts remain immutable Evidence, not current
        # Settings authority. The central Settings consumer is not yet bound.
        return None

    def catalog_snapshot(self) -> LocalModelCatalogSnapshot:
        if not self.candidates:
            return LocalModelCatalogSnapshot(
                entries=(),
                status_code="LOCAL_MODEL_CATALOG_EMPTY",
                status_message_ja="利用可能なローカル実況・解説Modelは見つかりません。",
                next_action_ja="TASK-054の既存offline inventoryを確認してください。自動downloadやinstallは行いません。",
            )
        entries: list[LocalModelCatalogEntry] = []
        for candidate in self.candidates:
            preflight = self._preflight_by_candidate.get(candidate.candidate_id)
            if preflight is None:
                if self.compute_profile_readback.profile_status is ProfileLoadStatus.DEFAULT_MISSING:
                    status_code = "COMPUTE_PROFILE_NOT_CONFIGURED"
                    status_message = "中央設定の計算プロファイルが未設定です。"
                    next_action = "右上の［設定］で計算方法を確認してください。"
                elif self.compute_profile_readback.profile_status is ProfileLoadStatus.DEFAULT_REJECTED:
                    status_code = "COMPUTE_PROFILE_REJECTED"
                    status_message = "中央設定の計算プロファイルを安全に読み取れません。"
                    next_action = "［設定］で計算方法を再確認してください。既存ファイルは自動変更しません。"
                else:
                    if (
                        self.compute_profile_readback.reasoning_reason_code
                        == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
                    ):
                        status_code = "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
                        status_message = "この機能はGPU必須のため、CPU指定では実行できません。"
                        next_action = "右上の［設定］で計算方法を［自動］または［GPU］に変更してください。"
                    else:
                        status_code = "TRUSTED_GPU_ADMISSION_REQUIRED"
                        status_message = "計算設定は読み取り済みですが、GPU実行確認は未完了です。"
                        next_action = "信頼済みの製品事前チェックが利用可能になるまで実行・保存しません。"
                entries.append(LocalModelCatalogEntry(
                    candidate=candidate, cost_class="LOCAL_FREE_AI", selectable=False,
                    status_code=status_code,
                    status_message_ja=status_message,
                    next_action_ja=next_action,
                ))
            else:
                cpu_blocked = (
                    self.compute_profile_readback.reasoning_reason_code
                    == "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
                )
                entries.append(LocalModelCatalogEntry(
                    candidate=candidate, cost_class="LOCAL_FREE_AI", selectable=False,
                    status_code=(
                        "CPU_NOT_ADMITTED_FOR_GPU_REQUIRED"
                        if cpu_blocked else "TRUSTED_GPU_ADMISSION_REQUIRED"
                    ),
                    status_message_ja=(
                        "この機能はGPU必須のため、CPU指定では実行できません。"
                        if cpu_blocked else "信頼済みのGPU実行確認が未完了です。"
                    ),
                    next_action_ja=(
                        "右上の［設定］で計算方法を［自動］または［GPU］に変更してください。"
                        if cpu_blocked
                        else "中央設定とGPU状態を確認してください。自動実行・保存は行いません。"
                    ),
                ))
        return LocalModelCatalogSnapshot(
            entries=tuple(entries),
            status_code="LOCAL_FREE_MODEL_NOT_SELECTABLE",
            status_message_ja="候補は参照専用です。機能画面ではモデルを変更・保存しません。",
            next_action_ja=(
                "右上の［設定］→［AIモデル］で実況・解説用モデルを確認してください。"
                "信頼済み事前チェック前は実行しません。"
            ),
        )

    def save_selection(self, candidate_id: str) -> LocalModelSelectionReceipt:
        candidate = next((item for item in self.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError("selected model candidate is unknown")
        raise ValueError(
            "selected model candidate requires trusted Product compute admission"
        )

    @staticmethod
    def _check(
        check_id: RuntimeCheckId,
        passed: bool,
        pass_code: str,
        fail_code: str,
        pass_message: str,
        fail_message: str,
        next_action: str,
    ) -> RuntimePreflightCheck:
        return RuntimePreflightCheck(
            check_id=check_id,
            status=RuntimeCheckStatus.PASS if passed else RuntimeCheckStatus.FAIL,
            detail_code=pass_code if passed else fail_code,
            message_ja=pass_message if passed else fail_message,
            next_action_ja="操作は不要です。" if passed else next_action,
        )

    def preflight(self, candidate_id: str) -> LocalRuntimePreflightSnapshot:
        candidate = next((item for item in self.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError("selected model candidate is unknown")
        return self._evaluate_probe_observation(
            candidate_id,
            {},
            process_error=RuntimeError(
                "trusted TASK-066 Product probe is not sealed"
            ),
            cache_result=True,
        )

    def _evaluate_probe_observation_for_test(
        self, candidate_id: str, value: Mapping[str, Any]
    ) -> LocalRuntimePreflightSnapshot:
        """Evaluate data-only fixture output without creating Product authority."""
        return self._evaluate_probe_observation(
            candidate_id, value, process_error=None, cache_result=False
        )

    def _evaluate_probe_observation(
        self,
        candidate_id: str,
        value: Mapping[str, Any],
        *,
        process_error: Exception | None,
        cache_result: bool,
    ) -> LocalRuntimePreflightSnapshot:
        candidate = next((item for item in self.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError("selected model candidate is unknown")

        bootstrap = value.get("bootstrap")
        wsl_ok = bootstrap in {
            "PASS", "VENV_MISSING", "PREFLIGHT_BUSY", "PREFLIGHT_LOCK_UNSAFE",
        }
        venv_ok = (
            bootstrap == "PASS"
            and value.get("venv_match") is True
            and isinstance(value.get("python"), str)
            and re.fullmatch(r"3\.12\.\d+", value["python"]) is not None
        )
        raw_packages = value.get("packages")
        packages_ok = isinstance(raw_packages, dict) and set(raw_packages) == set(_LOCKED_PACKAGES) and all(
            isinstance(raw_packages.get(name), dict)
            and raw_packages[name].get("match") is True
            for name in _RUNTIME_PACKAGES
        )
        model = value.get("model") if isinstance(value.get("model"), dict) else {}
        model_ok = (
            model.get("found") is True and model.get("safe_root") is True
            and model.get("file_count") == candidate.file_count
            and model.get("total_bytes") == candidate.total_bytes
            and model.get("mismatch_count") == 0
        )
        gpu = value.get("gpu") if isinstance(value.get("gpu"), dict) else {}
        minimum_free = candidate.peak_gpu_bytes + (1024 ** 3)
        gpu_ok = (
            gpu.get("available") is True
            and gpu.get("cuda_version") == _EXPECTED_CUDA_VERSION
            and isinstance(gpu.get("count"), int) and gpu["count"] >= 1
            and isinstance(gpu.get("name"), str) and bool(gpu["name"].strip())
            and isinstance(gpu.get("total_bytes"), int) and gpu["total_bytes"] >= minimum_free
            and isinstance(gpu.get("free_bytes"), int)
            and gpu["free_bytes"] >= minimum_free
        )
        inference = value.get("inference") if isinstance(value.get("inference"), dict) else {}
        inference_ok = inference.get("attempted") is True and inference.get("passed") is True

        checks = (
            RuntimePreflightCheck(
                RuntimeCheckId.CATALOG, RuntimeCheckStatus.PASS, "CATALOG_VERIFIED",
                "packaged catalog・revision・Evidenceは一致しています。", "操作は不要です。",
            ),
            self._check(
                RuntimeCheckId.WSL, wsl_ok, "WSL_READY", "WSL_UNAVAILABLE",
                "Ubuntu WSLを再利用または安全に起動して接続しました。",
                "Ubuntu WSLへ接続できません。",
                "WindowsのWSL/Ubuntu状態を確認してください。自動installは行いません。",
            ),
            self._check(
                RuntimeCheckId.VENV, venv_ok, "VENV_EXACT", "VENV_MISSING_OR_MISMATCH",
                "TASK-054専用Python環境を確認しました。",
                "TASK-054専用Python環境が見つからないか、別環境です。",
                "既存TASK-054 R6B runbookの専用venvを確認してください。",
            ),
            self._check(
                RuntimeCheckId.PACKAGES, packages_ok, "PACKAGES_EXACT", "PACKAGE_VERSION_MISMATCH",
                "必要packageのversionは固定lockと一致しています。",
                "必要packageの欠落またはversion不一致があります。",
                "不足一覧を確認し、既存offline lock手順を使用してください。自動installは行いません。",
            ),
            self._check(
                RuntimeCheckId.MODEL_IDENTITY, model_ok, "MODEL_IDENTITY_EXACT", "MODEL_PATH_OR_HASH_MISMATCH",
                "Qwen3-8Bのrevision・15ファイル・5 shardをsize/hashで確認しました。",
                "Modelが未取得、専用root不一致、またはfile/hashが一致しません。",
                "TASK-054専用Model rootとR6B verification reportを確認してください。再downloadは自動実行しません。",
            ),
            self._check(
                RuntimeCheckId.GPU, gpu_ok, "GPU_VRAM_READY", "GPU_OR_VRAM_UNAVAILABLE",
                "CUDA/GPUと最小推論に必要な利用可能VRAMを確認しました。",
                "CUDA/GPUを認識できないか、利用可能VRAMが不足しています。",
                "GPUを使用中の処理とWSL CUDA状態を確認してください。",
            ),
            self._check(
                RuntimeCheckId.INFERENCE, inference_ok, "OFFLINE_INFERENCE_READY", "OFFLINE_INFERENCE_FAILED",
                "固定Modelで1-tokenのoffline最小推論を確認しました。",
                "固定Modelのoffline最小推論を完了できませんでした。",
                "上流のvenv/package/Model/GPU項目を解消して再実行してください。",
            ),
            RuntimePreflightCheck(
                RuntimeCheckId.DATASET_TRAINING, RuntimeCheckStatus.NOT_REQUIRED,
                "DATASET_TRAINING_SEPARATE_GATE",
                "Dataset権利・学習・実データ評価は未完でも、base Model選択とoffline事前チェックを妨げません。",
                "学習を行う場合だけ、別のDataset/Human Gateを完了してください。",
            ),
        )
        if bootstrap in {"PREFLIGHT_BUSY", "PREFLIGHT_LOCK_UNSAFE"}:
            busy = bootstrap == "PREFLIGHT_BUSY"
            detail_code = "PREFLIGHT_ALREADY_RUNNING" if busy else "PREFLIGHT_LOCK_UNSAFE"
            message = (
                "別のDbD Training Studioが同じ事前チェックを実行中です。"
                if busy
                else "重複起動防止lockの安全性を確認できません。"
            )
            next_action = (
                "実行中の事前チェック完了後に再実行してください。"
                if busy
                else "WSLの一時directoryと所有者を確認してください。"
            )
            checks = tuple(
                item if item.check_id in {RuntimeCheckId.CATALOG, RuntimeCheckId.WSL, RuntimeCheckId.DATASET_TRAINING}
                else RuntimePreflightCheck(
                    item.check_id, RuntimeCheckStatus.FAIL, detail_code, message, next_action,
                )
                for item in checks
            )
        if process_error is not None:
            # Public diagnostics remain classified; raw exception/path/stderr is not projected.
            checks = tuple(
                RuntimePreflightCheck(
                    item.check_id,
                    item.status if item.check_id is RuntimeCheckId.CATALOG else (
                        RuntimeCheckStatus.NOT_REQUIRED
                        if item.check_id is RuntimeCheckId.DATASET_TRAINING
                        else RuntimeCheckStatus.FAIL
                    ),
                    item.detail_code if item.check_id in {RuntimeCheckId.CATALOG, RuntimeCheckId.DATASET_TRAINING} else "RUNTIME_PROCESS_FAILED",
                    item.message_ja if item.check_id in {RuntimeCheckId.CATALOG, RuntimeCheckId.DATASET_TRAINING} else "runtime事前チェックprocessを完了できませんでした。",
                    item.next_action_ja if item.check_id in {RuntimeCheckId.CATALOG, RuntimeCheckId.DATASET_TRAINING} else "WSLとTASK-054専用runtimeの状態を確認してください。",
                )
                for item in checks
            )
        ready = all(
            item.status is RuntimeCheckStatus.PASS
            for item in checks
            if item.status is not RuntimeCheckStatus.NOT_REQUIRED
        )
        snapshot = LocalRuntimePreflightSnapshot(candidate.candidate_id, checks, ready)
        if cache_result:
            self._preflight_by_candidate[candidate.candidate_id] = snapshot
        return snapshot

    def close(self) -> None:
        return None


__all__ = [
    "DbDComputeProfileReadback",
    "LocalModelCandidate", "LocalModelCatalogEntry", "LocalModelCatalogSnapshot",
    "LocalModelSelectionReceipt", "LocalModelSelectionStore",
    "LocalReasoningRuntimeService", "LocalRuntimePreflightSnapshot",
    "RuntimeCheckId", "RuntimeCheckStatus", "RuntimePreflightCheck",
    "load_local_model_catalog", "read_dbd_compute_profile",
    "prepare_packaged_dbd_compute_profile",
    "read_packaged_dbd_compute_profile",
]
