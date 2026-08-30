"""TASK-054 local base-model catalog, selection, and packaged runtime preflight.

The catalog is visible even when Dataset/training gates are open.  Runtime
preflight is an offline, one-shot Windows -> WSL process: it may start the
configured WSL distribution, but it never downloads, installs, trains, starts
a persistent service, or stops a WSL distribution owned by another process.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4

from .atomic import exclusive_file_update_lock
from .dbd_reasoning_worker_lifecycle import no_console_popen_options
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
_MAX_OUTPUT_BYTES = 64 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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
        with exclusive_file_update_lock(self.directory / "selection-head"):
            previous = self.latest()
            if previous is not None and (
                previous.candidate_id == candidate.candidate_id
                and previous.catalog_sha256 == candidate.catalog_sha256
            ):
                return previous
            selected_at = _utc_now()
            if previous is not None and selected_at <= previous.selected_at:
                raise ValueError("model-selection time did not advance")
            receipt = LocalModelSelectionReceipt(
                receipt_id=f"task054-model-selection-{uuid4().hex}",
                workspace_id=self.workspace_id,
                candidate_id=candidate.candidate_id,
                catalog_sha256=candidate.catalog_sha256,
                selected_at=selected_at,
                previous_receipt_sha256=(
                    None if previous is None else previous.to_dict()["receipt_sha256"]
                ),
            )
            if self.directory.is_symlink() or not self.directory.is_dir():
                raise ValueError("model-selection receipt directory is unsafe")
            path = self.directory / f"{receipt.receipt_id}.json"
            data = canonical_json_bytes(receipt.to_dict())
            try:
                with path.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise ValueError("model-selection receipt already exists") from exc
            return receipt


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
        if self.provider_execution_authorized or self.training_authorized:
            raise ValueError("runtime preflight cannot grant execution or training authority")


_BOOTSTRAP_SCRIPT = r"""
import fcntl, json, os, pathlib, stat, sys
lock_path = pathlib.Path('/tmp') / f'bvp-task054-runtime-preflight-{os.getuid()}.lock'
flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
try:
    lock_fd = os.open(lock_path, flags, 0o600)
    lock_stat = os.fstat(lock_fd)
    if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_nlink != 1 or lock_stat.st_uid != os.getuid():
        raise OSError('unsafe lock identity')
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print(json.dumps({'bootstrap':'PREFLIGHT_BUSY'}, sort_keys=True))
    raise SystemExit(43)
except Exception:
    print(json.dumps({'bootstrap':'PREFLIGHT_LOCK_UNSAFE'}, sort_keys=True))
    raise SystemExit(44)
os.set_inheritable(lock_fd, True)
relative = pathlib.PurePosixPath('.venvs/bvp-task054-training/bin/python')
target = pathlib.Path.home().joinpath(*relative.parts)
if not target.is_file():
    print(json.dumps({'bootstrap':'VENV_MISSING'}, sort_keys=True))
    raise SystemExit(42)
os.execv(str(target), [str(target), '-I', '-c', sys.argv[1], sys.argv[2]])
""".strip()


_PROBE_SCRIPT = r"""
import base64, hashlib, json, os, pathlib, stat, sys
from importlib.metadata import PackageNotFoundError, version

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
payload = json.loads(base64.urlsafe_b64decode(sys.argv[1].encode('ascii')))
result = {'bootstrap':'PASS','python':sys.version.split()[0]}
expected_prefix = pathlib.Path.home() / pathlib.PurePosixPath(payload['venv_python_relative']).parent.parent
result['venv_match'] = pathlib.Path(sys.prefix).resolve() == expected_prefix.resolve()

versions = {}
for name, expected in payload['package_versions'].items():
    try:
        actual = version(name)
    except PackageNotFoundError:
        actual = None
    versions[name] = {'expected': expected, 'actual': actual, 'match': actual == expected}
result['packages'] = versions

home = pathlib.Path.home().resolve()
root = home / pathlib.PurePosixPath(payload['model_root_relative'])
model = {'found':False,'safe_root':False,'file_count':0,'total_bytes':0,'mismatch_count':0}
try:
    resolved = root.resolve(strict=True)
    resolved.relative_to(home)
    cursor = root
    unsafe = False
    while cursor != home:
        info = cursor.lstat()
        if stat.S_ISLNK(info.st_mode): unsafe = True
        cursor = cursor.parent
    model['safe_root'] = not unsafe and resolved.is_dir()
    mismatches = 0
    total = 0
    seen = set()
    for item in payload['files']:
        path = resolved / pathlib.PurePosixPath(item['logical_path'])
        info = path.lstat()
        safe = stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode) and info.st_nlink == 1
        digest = hashlib.sha256()
        if safe:
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                    digest.update(block)
        if not safe or info.st_size != item['size_bytes'] or digest.hexdigest() != item['sha256']:
            mismatches += 1
        total += info.st_size if stat.S_ISREG(info.st_mode) else 0
        seen.add(item['logical_path'])
    actual = {p.relative_to(resolved).as_posix() for p in resolved.iterdir() if p.is_file()}
    model.update(found=True,file_count=len(actual),total_bytes=total,mismatch_count=mismatches + len(actual - seen))
except Exception as exc:
    model['error'] = type(exc).__name__
result['model'] = model

gpu = {'available':False}
try:
    import torch
    gpu['available'] = bool(torch.cuda.is_available())
    gpu['cuda_version'] = torch.version.cuda
    gpu['count'] = torch.cuda.device_count()
    if gpu['available']:
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        gpu.update(name=torch.cuda.get_device_name(0),free_bytes=int(free_bytes),total_bytes=int(total_bytes))
except Exception as exc:
    gpu['error'] = type(exc).__name__
result['gpu'] = gpu

can_infer = (
    result['venv_match'] and sys.version_info[:2] == (3, 12)
    and all(versions[name]['match'] for name in payload['runtime_package_names'])
    and model['found'] and model['safe_root'] and model['file_count'] == payload['file_count']
    and model['total_bytes'] == payload['total_bytes'] and model['mismatch_count'] == 0
    and gpu.get('available') and gpu.get('free_bytes', 0) >= payload['minimum_free_gpu_bytes']
)
inference = {'attempted':False,'passed':False}
if can_infer:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        inference['attempted'] = True
        quant = BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
        tokenizer = AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        model_obj = AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,trust_remote_code=False,quantization_config=quant,device_map='auto',dtype=torch.bfloat16)
        encoded = tokenizer('日本語で一語だけ応答してください。',return_tensors='pt').to(model_obj.device)
        with torch.inference_mode():
            generated = model_obj.generate(**encoded,max_new_tokens=1,do_sample=False)
        inference['passed'] = int(generated.shape[-1]) > int(encoded['input_ids'].shape[-1])
        del generated, encoded, model_obj
        torch.cuda.empty_cache()
    except Exception as exc:
        inference['error'] = type(exc).__name__
result['inference'] = inference
print(json.dumps(result, sort_keys=True, separators=(',',':')))
""".strip()


class LocalReasoningRuntimeService:
    def __init__(
        self,
        *,
        workspace_id: str,
        workspace_root: str | Path,
        distro: str = "Ubuntu",
        popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        timeout_seconds: int = 300,
    ) -> None:
        self.candidates = load_local_model_catalog()
        self.store = LocalModelSelectionStore(workspace_root, workspace_id=workspace_id)
        if distro != "Ubuntu":
            raise ValueError("TASK-054 runtime distro is fixed to Ubuntu")
        if not 30 <= timeout_seconds <= 600:
            raise ValueError("runtime preflight timeout is outside bounds")
        self.distro = distro
        self._popen_factory = popen_factory
        self._timeout_seconds = timeout_seconds
        self._lock = threading.RLock()
        self._process: subprocess.Popen[bytes] | None = None

    def selected_candidate(self) -> LocalModelCandidate:
        latest = self.store.latest()
        if latest is None:
            return self.candidates[0]
        candidate = next((item for item in self.candidates if item.candidate_id == latest.candidate_id), None)
        if candidate is None or latest.catalog_sha256 != candidate.catalog_sha256:
            raise ValueError("saved model selection is stale or unknown")
        return candidate

    def save_selection(self, candidate_id: str) -> LocalModelSelectionReceipt:
        candidate = next((item for item in self.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError("selected model candidate is unknown")
        return self.store.select(candidate)

    def _run_probe(self, candidate: LocalModelCandidate) -> Mapping[str, Any]:
        payload = base64.urlsafe_b64encode(
            canonical_json_bytes(candidate.probe_payload())
        ).decode("ascii")
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        executable = str(Path(system_root) / "System32" / "wsl.exe")
        command = [
            executable, "-d", self.distro, "--", "/usr/bin/python3", "-c",
            _BOOTSTRAP_SCRIPT, _PROBE_SCRIPT, payload,
        ]
        options = no_console_popen_options()
        options.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise RuntimeError("runtime preflight is already running")
            try:
                self._process = self._popen_factory(command, **options)
            except Exception as exc:
                raise RuntimeError("WSL runtime process could not start") from exc
            process = self._process
        try:
            stdout, stderr = process.communicate(timeout=self._timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=3)
            raise RuntimeError("runtime preflight timed out") from exc
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None
        stdout = bytes(stdout or b"")
        stderr = bytes(stderr or b"")
        if len(stdout) > _MAX_OUTPUT_BYTES or len(stderr) > _MAX_OUTPUT_BYTES:
            raise RuntimeError("runtime preflight output exceeded the safety bound")
        try:
            value = json.loads(stdout.decode("utf-8", errors="strict"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("runtime preflight returned an invalid public result") from exc
        if not isinstance(value, dict):
            raise RuntimeError("runtime preflight returned an invalid public result")
        if process.returncode != 0 and value.get("bootstrap") not in {
            "VENV_MISSING", "PREFLIGHT_BUSY", "PREFLIGHT_LOCK_UNSAFE",
        }:
            raise RuntimeError("WSL runtime preflight process failed")
        return value

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
        try:
            value = self._run_probe(candidate)
            process_error: Exception | None = None
        except Exception as exc:
            value = {}
            process_error = exc

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
        return LocalRuntimePreflightSnapshot(candidate.candidate_id, checks, ready)

    def close(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


__all__ = [
    "LocalModelCandidate", "LocalModelSelectionReceipt", "LocalModelSelectionStore",
    "LocalReasoningRuntimeService", "LocalRuntimePreflightSnapshot",
    "RuntimeCheckId", "RuntimeCheckStatus", "RuntimePreflightCheck",
    "load_local_model_catalog",
]
