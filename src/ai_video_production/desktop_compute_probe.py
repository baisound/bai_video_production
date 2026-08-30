"""Bounded, shell-free TASK-066 desktop compute probe infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import queue
import stat
import subprocess
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Protocol

from .desktop_compute_policy import (
    AdapterCapability,
    AdapterIdentity,
    CapabilityAdmissionReceipt,
)
from .serialization import canonical_json_bytes, sha256_bytes


PER_ADAPTER_TIMEOUT_SECONDS = 5.0
TOTAL_PROBE_TIMEOUT_SECONDS = 20.0
MAX_PROBE_OUTPUT_BYTES = 256 * 1024
_REPARSE_POINT = 0x400
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

def _unsealed_probe_row(workload_id: str) -> dict[str, object]:
    return {
        "probe_id": workload_id,
        "workload_id": workload_id,
        "admission_state": "DISABLED_UNTIL_HELPER_SEALED",
        "helper_filename": None,
        "helper_sha256": None,
        "backend": None,
        "command_sha256": None,
        "fixed_arguments": [],
        "required_runtime_modules": [],
    }


_FROZEN_PROBE_ROWS: tuple[dict[str, object], ...] = tuple(
    _unsealed_probe_row(item)
    for item in (
        "planning.local.ollama",
        "image.local.comfyui",
        "video.local.generation",
        "audio.asr.faster_whisper",
        "audio.voice.local",
        "dbd.reasoning.qwen3_8b",
        "dbd.training",
    )
)


class DesktopComputeProbeError(ValueError):
    """A probe request or observation is outside the admitted boundary."""


class ProbeStatus(str, Enum):
    PASS = "PASS"
    NOT_CONFIRMED = "NOT_CONFIRMED"


class RuntimeTrustClass(str, Enum):
    PRODUCT_PRIVATE = "PRODUCT_PRIVATE"
    OS_DISPLAY_DRIVER = "OS_DISPLAY_DRIVER"


@dataclass(frozen=True, slots=True)
class RuntimeModuleEvidence:
    module_name: str
    trust_class: RuntimeTrustClass
    loaded_path: Path
    version: str
    sha256: str
    signer: str | None

    def __post_init__(self) -> None:
        if not self.module_name or len(self.module_name) > 160:
            raise DesktopComputeProbeError("runtime module name is invalid")
        if not self.loaded_path.is_absolute():
            raise DesktopComputeProbeError("runtime module path must be absolute")
        if not self.version or len(self.version) > 160:
            raise DesktopComputeProbeError("runtime module version is invalid")
        if _SHA_RE.fullmatch(self.sha256) is None:
            raise DesktopComputeProbeError("runtime module hash is invalid")


@dataclass(frozen=True, slots=True)
class ProductRuntimeManifestBinding:
    module_name: str
    install_relative_path: str
    version: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.module_name or len(self.module_name) > 160:
            raise DesktopComputeProbeError("runtime manifest module name is invalid")
        path = Path(self.install_relative_path)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise DesktopComputeProbeError("runtime manifest path is unsafe")
        if _SHA_RE.fullmatch(self.sha256) is None:
            raise DesktopComputeProbeError("runtime manifest hash is invalid")


@dataclass(frozen=True, slots=True)
class OsDisplayDriverRuntimePolicy:
    module_name: str
    approved_roots: tuple[Path, ...]
    approved_signers: tuple[str, ...]
    approved_versions: tuple[str, ...]
    driver_instance_digest: str

    def __post_init__(self) -> None:
        if not self.module_name or len(self.module_name) > 160:
            raise DesktopComputeProbeError("OS runtime module name is invalid")
        if not self.approved_roots or any(not item.is_absolute() for item in self.approved_roots):
            raise DesktopComputeProbeError("OS runtime roots are invalid")
        if not self.approved_signers or not self.approved_versions:
            raise DesktopComputeProbeError("OS runtime signer/version policy is empty")
        if _SHA_RE.fullmatch(self.driver_instance_digest) is None:
            raise DesktopComputeProbeError("OS runtime driver identity is invalid")


@dataclass(frozen=True, slots=True)
class ProbeCommand:
    probe_id: str
    command: tuple[str, ...]
    adapter_identity: AdapterIdentity
    backend: str
    workload_ids: tuple[str, ...]
    executable_sha256: str
    command_sha256: str
    binary_root: Path | None = None
    product_runtime_bindings: tuple[ProductRuntimeManifestBinding, ...] = ()
    os_display_driver_policies: tuple[OsDisplayDriverRuntimePolicy, ...] = ()
    timeout_seconds: float = PER_ADAPTER_TIMEOUT_SECONDS
    network_policy: str = "DENY"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,95}", self.probe_id):
            raise DesktopComputeProbeError("probe_id is invalid")
        if not self.command:
            raise DesktopComputeProbeError("probe command is empty")
        executable = Path(self.command[0])
        if not executable.is_absolute():
            raise DesktopComputeProbeError("probe executable must be absolute")
        if not 0 < self.timeout_seconds <= PER_ADAPTER_TIMEOUT_SECONDS:
            raise DesktopComputeProbeError("per-adapter probe timeout exceeds contract")
        if _SHA_RE.fullmatch(self.executable_sha256) is None:
            raise DesktopComputeProbeError("probe executable hash is invalid")
        if self.command_sha256 != probe_command_sha256(self.command):
            raise DesktopComputeProbeError("probe command manifest binding is invalid")
        if self.network_policy != "DENY":
            raise DesktopComputeProbeError("network-enabled probes are prohibited")
        if not self.backend or not self.workload_ids:
            raise DesktopComputeProbeError("probe backend/workloads are incomplete")
        if len(set(self.workload_ids)) != len(self.workload_ids):
            raise DesktopComputeProbeError("probe workloads are duplicated")
        expected_names = [item.module_name for item in self.product_runtime_bindings]
        expected_names.extend(item.module_name for item in self.os_display_driver_policies)
        if not expected_names or len(set(expected_names)) != len(expected_names):
            raise DesktopComputeProbeError("probe runtime admission set is empty or duplicated")
        if self.product_runtime_bindings:
            if self.binary_root is None or not self.binary_root.is_absolute():
                raise DesktopComputeProbeError("Product runtime binary_root is invalid")


@dataclass(frozen=True, slots=True)
class ProbeResult:
    probe_id: str
    status: ProbeStatus
    reason_code: str
    adapter_identity: AdapterIdentity
    backend: str
    compatible_workload_ids: tuple[str, ...]
    runtime_modules: tuple[RuntimeModuleEvidence, ...]
    workload_observation_status: str
    process_pid: int | None
    elapsed_seconds: float


class _Process(Protocol):
    pid: int
    returncode: int | None

    def communicate(self, input: bytes | None = None, timeout: float | None = None) -> tuple[bytes, bytes]: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...


ProcessFactory = Callable[..., _Process]
NetworkIsolationAttestor = Callable[[ProbeCommand], bool]
SignatureVerifier = Callable[[Path], tuple[str, str]]
_LIVE_CAPABILITY_TOKENS: dict[str, object] = {}
_LIVE_CAPABILITY_TOKEN_LOCK = threading.Lock()


def frozen_probe_registry() -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "1.0.0",
        "message_type": "BvpDesktopComputeProbeRegistry",
        "registry_revision": 1,
        "probes": [dict(item) for item in _FROZEN_PROBE_ROWS],
    }
    value = dict(body)
    value["registry_sha256"] = "sha256:" + hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    validate_probe_registry(value)
    return json.loads(json.dumps(value))


def validate_probe_registry(document: Mapping[str, Any]) -> None:
    if set(document) != {
        "schema_version", "message_type", "registry_revision", "probes", "registry_sha256"
    }:
        raise DesktopComputeProbeError("probe registry fields mismatch")
    if document["schema_version"] != "1.0.0" or document["message_type"] != "BvpDesktopComputeProbeRegistry" or document["registry_revision"] != 1:
        raise DesktopComputeProbeError("probe registry identity mismatch")
    if document["probes"] != [dict(item) for item in _FROZEN_PROBE_ROWS]:
        raise DesktopComputeProbeError("probe registry frozen rows mismatch")
    body = dict(document)
    supplied = body.pop("registry_sha256")
    expected = "sha256:" + hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if supplied != expected:
        raise DesktopComputeProbeError("probe registry digest mismatch")


def capability_from_probe_result(
    *,
    result: ProbeResult,
    command: ProbeCommand,
    workload_id: str,
    discrete: bool,
    dedicated_memory_bytes: int,
) -> AdapterCapability:
    """Only conversion route from a sealed production PASS to policy admission."""
    registry = frozen_probe_registry()
    row = next(
        (item for item in registry["probes"] if item["probe_id"] == result.probe_id),
        None,
    )
    if row is None or row["admission_state"] != "SEALED":
        raise DesktopComputeProbeError("probe helper is not sealed")
    if result.status is not ProbeStatus.PASS or result.process_pid is None:
        raise DesktopComputeProbeError("probe result is not a production PASS")
    if workload_id not in result.compatible_workload_ids or workload_id != row["workload_id"]:
        raise DesktopComputeProbeError("probe workload receipt mismatch")
    if result.backend != row["backend"] or command.backend != row["backend"]:
        raise DesktopComputeProbeError("probe backend receipt mismatch")
    if Path(command.command[0]).name != row["helper_filename"]:
        raise DesktopComputeProbeError("probe helper filename mismatch")
    if command.executable_sha256 != row["helper_sha256"] or command.command_sha256 != row["command_sha256"]:
        raise DesktopComputeProbeError("probe helper identity mismatch")
    if list(command.command[1:]) != row["fixed_arguments"]:
        raise DesktopComputeProbeError("probe fixed arguments mismatch")
    module_names = sorted(item.module_name for item in result.runtime_modules)
    if module_names != sorted(row["required_runtime_modules"]):
        raise DesktopComputeProbeError("probe runtime inventory mismatch")
    runtime_versions = tuple(sorted(item.version for item in result.runtime_modules))
    adapter_digest = sha256_bytes(canonical_json_bytes(result.adapter_identity.to_dict()))
    runtime_inventory_digest = sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "module_name": item.module_name,
                    "trust_class": item.trust_class.value,
                    "loaded_path": str(item.loaded_path),
                    "version": item.version,
                    "sha256": item.sha256,
                    "signer": item.signer,
                }
                for item in sorted(result.runtime_modules, key=lambda value: value.module_name)
            ]
        )
    )
    body = {
        "registry_revision": registry["registry_revision"],
        "registry_sha256": registry["registry_sha256"],
        "probe_id": result.probe_id,
        "workload_id": workload_id,
        "backend": result.backend,
        "adapter_identity_sha256": adapter_digest,
        "runtime_inventory_sha256": runtime_inventory_digest,
        "runtime_versions_sha256": sha256_bytes(canonical_json_bytes(list(runtime_versions))),
        "helper_sha256": command.executable_sha256,
        "command_sha256": command.command_sha256,
        "consumer_process_pid": os.getpid(),
        "probe_process_pid": result.process_pid,
    }
    receipt = CapabilityAdmissionReceipt(
        **body,
        receipt_sha256=sha256_bytes(canonical_json_bytes(body)),
    )
    live_token = object()
    with _LIVE_CAPABILITY_TOKEN_LOCK:
        if len(_LIVE_CAPABILITY_TOKENS) >= 128:
            _LIVE_CAPABILITY_TOKENS.pop(next(iter(_LIVE_CAPABILITY_TOKENS)))
        _LIVE_CAPABILITY_TOKENS[receipt.receipt_sha256] = live_token
    capability = AdapterCapability(
        backend=result.backend,
        device_kind="GPU",
        identity=result.adapter_identity,
        supported_workloads=frozenset({workload_id}),
        implemented=True,
        compatible=True,
        discrete=discrete,
        dedicated_memory_bytes=dedicated_memory_bytes,
        current_bind_verified=True,
        loaded_runtime_versions=runtime_versions,
        admission_receipt=receipt,
        runtime_inventory_sha256=runtime_inventory_digest,
        live_admission_token=live_token,
    )
    validate_capability_admission_receipt(capability, workload_id=workload_id)
    return capability


def validate_capability_admission_receipt(
    capability: AdapterCapability,
    *,
    workload_id: str,
) -> None:
    registry = frozen_probe_registry()
    row = next((item for item in registry["probes"] if item["workload_id"] == workload_id), None)
    receipt = capability.admission_receipt
    if row is None or row["admission_state"] != "SEALED" or receipt is None:
        raise DesktopComputeProbeError("sealed capability receipt is unavailable")
    if capability.identity is None:
        raise DesktopComputeProbeError("capability receipt lacks adapter identity")
    with _LIVE_CAPABILITY_TOKEN_LOCK:
        live_token = _LIVE_CAPABILITY_TOKENS.get(receipt.receipt_sha256)
    if live_token is None or capability.live_admission_token is not live_token:
        raise DesktopComputeProbeError("capability receipt is not live in this process")
    expected = {
        "registry_revision": registry["registry_revision"],
        "registry_sha256": registry["registry_sha256"],
        "probe_id": row["probe_id"],
        "workload_id": workload_id,
        "backend": capability.backend,
        "adapter_identity_sha256": sha256_bytes(canonical_json_bytes(capability.identity.to_dict())),
        "runtime_versions_sha256": sha256_bytes(canonical_json_bytes(list(capability.loaded_runtime_versions))),
        "runtime_inventory_sha256": capability.runtime_inventory_sha256,
        "helper_sha256": row["helper_sha256"],
        "command_sha256": row["command_sha256"],
        "consumer_process_pid": os.getpid(),
        "probe_process_pid": receipt.probe_process_pid,
    }
    body = receipt.body()
    for key, value in expected.items():
        if body[key] != value:
            raise DesktopComputeProbeError("capability receipt binding mismatch")
    if receipt.receipt_sha256 != sha256_bytes(canonical_json_bytes(body)):
        raise DesktopComputeProbeError("capability receipt digest mismatch")


class BoundedDesktopComputeProbe:
    """Run admitted helper probes without shell/network orchestration."""

    def __init__(
        self,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
        monotonic: Callable[[], float] = time.monotonic,
        total_timeout_seconds: float = TOTAL_PROBE_TIMEOUT_SECONDS,
        network_isolation_attestor: NetworkIsolationAttestor | None = None,
        signature_verifier: SignatureVerifier | None = None,
        test_seam: bool = False,
    ) -> None:
        if not 0 < total_timeout_seconds <= TOTAL_PROBE_TIMEOUT_SECONDS:
            raise DesktopComputeProbeError("total probe timeout exceeds contract")
        self._process_factory = process_factory
        self._monotonic = monotonic
        self._total_timeout = total_timeout_seconds
        if not test_seam and (network_isolation_attestor is not None or signature_verifier is not None):
            raise DesktopComputeProbeError("callback trust seams are test-only")
        self._network_isolation_attestor = network_isolation_attestor
        self._signature_verifier = signature_verifier
        self._test_seam = test_seam

    def run(self, commands: Iterable[ProbeCommand]) -> tuple[ProbeResult, ...]:
        items = tuple(commands)
        if len({item.probe_id for item in items}) != len(items):
            raise DesktopComputeProbeError("duplicate probe_id")
        started = self._monotonic()
        total_deadline = started + self._total_timeout
        results: list[ProbeResult] = []
        for item in items:
            elapsed = self._monotonic() - started
            remaining = total_deadline - self._monotonic()
            if remaining <= 0:
                results.append(_not_confirmed(item, "TOTAL_PROBE_TIMEOUT", None, elapsed))
                continue
            results.append(
                self._run_one(
                    item,
                    deadline=min(total_deadline, self._monotonic() + item.timeout_seconds),
                )
            )
        return tuple(results)

    def _run_one(self, item: ProbeCommand, *, deadline: float) -> ProbeResult:
        started = self._monotonic()
        if not self._test_seam:
            return _not_confirmed(
                item,
                "PROBE_HELPER_NOT_SEALED",
                None,
                self._monotonic() - started,
            )
        executable = Path(item.command[0])
        try:
            admitted_hash = _bounded_call(
                lambda: (_require_safe_executable(executable), _sha256_file(executable))[1],
                max(0.0, deadline - self._monotonic()),
            )
            if admitted_hash != item.executable_sha256:
                return _not_confirmed(
                    item,
                    "PROBE_EXECUTABLE_HASH_MISMATCH",
                    None,
                    self._monotonic() - started,
                )
        except TimeoutError:
            return _not_confirmed(item, "PROBE_TIMEOUT", None, self._monotonic() - started)
        except Exception:
            return _not_confirmed(
                item,
                "PROBE_EXECUTABLE_NOT_ADMITTED",
                None,
                self._monotonic() - started,
            )
        if self._monotonic() >= deadline:
            return _not_confirmed(item, "PROBE_TIMEOUT", None, self._monotonic() - started)
        try:
            isolated = _bounded_call(
                lambda: (
                    self._network_isolation_attestor is not None
                    and self._network_isolation_attestor(item) is True
                ),
                max(0.0, deadline - self._monotonic()),
            )
        except TimeoutError:
            return _not_confirmed(item, "PROBE_TIMEOUT", None, self._monotonic() - started)
        except Exception:
            isolated = False
        if not isolated:
            return _not_confirmed(
                item,
                "NETWORK_ISOLATION_NOT_CONFIRMED",
                None,
                self._monotonic() - started,
            )
        if self._monotonic() >= deadline:
            return _not_confirmed(item, "PROBE_TIMEOUT", None, self._monotonic() - started)
        options: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "shell": False,
            "cwd": str(executable.parent),
            "env": _sanitized_probe_environment(),
        }
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        try:
            process = self._process_factory(list(item.command), **options)
        except Exception:
            return _not_confirmed(
                item,
                "PROBE_START_FAILED",
                None,
                self._monotonic() - started,
            )
        try:
            try:
                stdout, stderr, exceeded = _collect_bounded_output(
                    process,
                    max(0.0, deadline - self._monotonic()),
                )
            except subprocess.TimeoutExpired:
                _terminate_owned_process(process)
                return _not_confirmed(
                    item,
                    "PROBE_TIMEOUT",
                    process.pid,
                    self._monotonic() - started,
                )
            if exceeded:
                return _not_confirmed(
                    item,
                    "PROBE_OUTPUT_EXCEEDED",
                    process.pid,
                    self._monotonic() - started,
                )
            if process.returncode != 0:
                return _not_confirmed(
                    item,
                    "PROBE_PROCESS_FAILED",
                    process.pid,
                    self._monotonic() - started,
                )
            try:
                payload = json.loads(stdout.decode("utf-8"))
                parsed = _bounded_call(
                    lambda: _parse_probe_payload(
                        item,
                        payload,
                        process.pid,
                        self._monotonic() - started,
                        signature_verifier=self._signature_verifier,
                    ),
                    max(0.0, deadline - self._monotonic()),
                )
                return replace(
                    parsed,
                    status=ProbeStatus.NOT_CONFIRMED,
                    reason_code="TEST_SEAM_CAPABILITY_PARSED",
                )
            except TimeoutError:
                return _not_confirmed(
                    item,
                    "PROBE_TIMEOUT",
                    process.pid,
                    self._monotonic() - started,
                )
            except DesktopComputeProbeError:
                return _not_confirmed(
                    item,
                    "RUNTIME_ADMISSION_FAILED",
                    process.pid,
                    self._monotonic() - started,
                )
            except Exception:
                return _not_confirmed(
                    item,
                    "PROBE_OUTPUT_INVALID",
                    process.pid,
                    self._monotonic() - started,
                )
        except Exception:
            _terminate_owned_process(process)
            return _not_confirmed(
                item,
                "PROBE_CRASHED",
                process.pid,
                self._monotonic() - started,
            )


def admit_product_private_runtime(
    *,
    binary_root: str | Path,
    binding: ProductRuntimeManifestBinding,
    observation: RuntimeModuleEvidence,
) -> RuntimeModuleEvidence:
    """Admit only exact manifest-bound modules below immutable binary_root."""
    if observation.trust_class is not RuntimeTrustClass.PRODUCT_PRIVATE:
        raise DesktopComputeProbeError("runtime trust class mismatch")
    root = Path(binary_root).resolve(strict=True)
    expected = (root / binding.install_relative_path).resolve(strict=True)
    try:
        expected.relative_to(root)
    except ValueError as exc:
        raise DesktopComputeProbeError("runtime manifest path escaped binary_root") from exc
    observed = observation.loaded_path.resolve(strict=True)
    if os.path.normcase(str(expected)) != os.path.normcase(str(observed)):
        raise DesktopComputeProbeError("loaded Product runtime path mismatch")
    _require_safe_regular_file(observed, "Product runtime module")
    if observation.version != binding.version or observation.sha256 != binding.sha256:
        raise DesktopComputeProbeError("loaded Product runtime identity mismatch")
    if _sha256_file(observed) != binding.sha256:
        raise DesktopComputeProbeError("Product runtime file hash mismatch")
    return observation


def admit_os_display_driver_runtime(
    *,
    policy: OsDisplayDriverRuntimePolicy,
    adapter_identity: AdapterIdentity,
    signature_verifier: SignatureVerifier,
    observation: RuntimeModuleEvidence,
) -> RuntimeModuleEvidence:
    """Admit driver modules only from approved system/vendor-signed roots."""
    if observation.trust_class is not RuntimeTrustClass.OS_DISPLAY_DRIVER:
        raise DesktopComputeProbeError("runtime trust class mismatch")
    loaded = observation.loaded_path.resolve(strict=True)
    _require_safe_regular_file(loaded, "OS display-driver module")
    if observation.module_name != policy.module_name:
        raise DesktopComputeProbeError("OS display-driver module name mismatch")
    if adapter_identity.driver_instance_digest != policy.driver_instance_digest:
        raise DesktopComputeProbeError("OS display-driver device identity mismatch")
    roots = tuple(Path(item).resolve(strict=True) for item in policy.approved_roots)
    if not any(_is_relative_to(loaded, root) for root in roots):
        raise DesktopComputeProbeError("OS display-driver path is not approved")
    verified_signer, verified_version = signature_verifier(loaded)
    if observation.signer != verified_signer or verified_signer not in set(policy.approved_signers):
        raise DesktopComputeProbeError("OS display-driver signer is not approved")
    if observation.version != verified_version or verified_version not in set(policy.approved_versions):
        raise DesktopComputeProbeError("OS display-driver version is not approved")
    if _sha256_file(loaded) != observation.sha256:
        raise DesktopComputeProbeError("OS display-driver file hash mismatch")
    return observation


def _parse_probe_payload(
    item: ProbeCommand,
    payload: Any,
    pid: int,
    elapsed: float,
    *,
    signature_verifier: SignatureVerifier | None,
) -> ProbeResult:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "probe_id",
        "adapter_identity",
        "backend",
        "compatible_workload_ids",
        "runtime_modules",
        "workload_observation_status",
    }:
        raise DesktopComputeProbeError("probe payload fields mismatch")
    if payload["schema_version"] != "1.0.0" or payload["probe_id"] != item.probe_id:
        raise DesktopComputeProbeError("probe payload identity mismatch")
    identity = AdapterIdentity.from_dict(payload["adapter_identity"])
    if identity != item.adapter_identity or payload["backend"] != item.backend:
        raise DesktopComputeProbeError("probe adapter/backend mismatch")
    workloads = tuple(payload["compatible_workload_ids"])
    if not workloads or not set(workloads).issubset(item.workload_ids) or len(set(workloads)) != len(workloads):
        raise DesktopComputeProbeError("probe workload result is invalid")
    modules = tuple(_runtime_module_from_dict(value) for value in payload["runtime_modules"])
    expected_names = {
        binding.module_name for binding in item.product_runtime_bindings
    } | {policy.module_name for policy in item.os_display_driver_policies}
    if {module.module_name for module in modules} != expected_names or len(modules) != len(expected_names):
        raise DesktopComputeProbeError("probe runtime inventory does not match admission set")
    by_name = {module.module_name: module for module in modules}
    for binding in item.product_runtime_bindings:
        assert item.binary_root is not None
        admit_product_private_runtime(
            binary_root=item.binary_root,
            binding=binding,
            observation=by_name[binding.module_name],
        )
    if item.os_display_driver_policies and signature_verifier is None:
        raise DesktopComputeProbeError("trusted OS signature verifier is unavailable")
    for policy in item.os_display_driver_policies:
        assert signature_verifier is not None
        admit_os_display_driver_runtime(
            policy=policy,
            adapter_identity=item.adapter_identity,
            signature_verifier=signature_verifier,
            observation=by_name[policy.module_name],
        )
    observation = payload["workload_observation_status"]
    if observation not in {"PASS", "NOT_CONFIRMED", "NOT_EXECUTED"}:
        raise DesktopComputeProbeError("workload observation status is invalid")
    # Capability PASS is intentionally not actual workload execution proof.
    return ProbeResult(
        probe_id=item.probe_id,
        status=ProbeStatus.PASS,
        reason_code="CAPABILITY_INVENTORY_CONFIRMED",
        adapter_identity=identity,
        backend=item.backend,
        compatible_workload_ids=workloads,
        runtime_modules=modules,
        workload_observation_status=observation,
        process_pid=pid,
        elapsed_seconds=elapsed,
    )


def _runtime_module_from_dict(value: Mapping[str, Any]) -> RuntimeModuleEvidence:
    if set(value) != {"module_name", "trust_class", "loaded_path", "version", "sha256", "signer"}:
        raise DesktopComputeProbeError("runtime module fields mismatch")
    return RuntimeModuleEvidence(
        module_name=value["module_name"],
        trust_class=RuntimeTrustClass(value["trust_class"]),
        loaded_path=Path(value["loaded_path"]),
        version=value["version"],
        sha256=value["sha256"],
        signer=value["signer"],
    )


def probe_command_sha256(command: tuple[str, ...]) -> str:
    if not command or any(not isinstance(item, str) or "\x00" in item for item in command):
        raise DesktopComputeProbeError("probe command arguments are invalid")
    encoded = json.dumps(
        list(command),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _not_confirmed(
    item: ProbeCommand,
    reason: str,
    pid: int | None,
    elapsed: float,
) -> ProbeResult:
    return ProbeResult(
        probe_id=item.probe_id,
        status=ProbeStatus.NOT_CONFIRMED,
        reason_code=reason,
        adapter_identity=item.adapter_identity,
        backend=item.backend,
        compatible_workload_ids=(),
        runtime_modules=(),
        workload_observation_status="NOT_EXECUTED",
        process_pid=pid,
        elapsed_seconds=max(0.0, elapsed),
    )


def _sanitized_probe_environment() -> dict[str, str]:
    admitted = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC")
    environment = {key: os.environ[key] for key in admitted if key in os.environ}
    environment.update(
        {
            "BVP_TASK066_NETWORK_POLICY": "DENY",
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
    )
    return environment


def _collect_bounded_output(
    process: _Process,
    timeout: float,
) -> tuple[bytes, bytes, bool]:
    """Drain production Popen pipes incrementally and stop at the byte ceiling."""
    stdout_stream = getattr(process, "stdout", None)
    stderr_stream = getattr(process, "stderr", None)
    if stdout_stream is None or stderr_stream is None or not hasattr(process, "wait"):
        stdout, stderr = process.communicate(timeout=timeout)
        return (
            stdout[: MAX_PROBE_OUTPUT_BYTES + 1],
            stderr[: MAX_PROBE_OUTPUT_BYTES + 1],
            len(stdout) > MAX_PROBE_OUTPUT_BYTES or len(stderr) > MAX_PROBE_OUTPUT_BYTES,
        )

    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()

    def drain(stream: Any, index: int) -> None:
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    return
                remaining = MAX_PROBE_OUTPUT_BYTES + 1 - len(buffers[index])
                if remaining > 0:
                    buffers[index].extend(chunk[:remaining])
                if len(buffers[index]) > MAX_PROBE_OUTPUT_BYTES or len(chunk) > remaining:
                    exceeded.set()
                    return
        except Exception:
            exceeded.set()

    threads = (
        threading.Thread(target=drain, args=(stdout_stream, 0), daemon=True),
        threading.Thread(target=drain, args=(stderr_stream, 1), daemon=True),
    )
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    while True:
        if exceeded.is_set():
            _terminate_owned_process(process)
            break
        if process.poll() is not None:
            break
        if time.monotonic() >= deadline:
            _terminate_owned_process(process)
            raise subprocess.TimeoutExpired("probe", timeout)
        time.sleep(0.005)
    for thread in threads:
        thread.join(timeout=0.5)
    return bytes(buffers[0]), bytes(buffers[1]), exceeded.is_set()


def _bounded_call(operation: Callable[[], Any], timeout: float) -> Any:
    if timeout <= 0:
        raise TimeoutError("bounded operation deadline expired")
    outcome: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            outcome.put((True, operation()), block=False)
        except BaseException as exc:
            outcome.put((False, exc), block=False)

    worker = threading.Thread(target=invoke, daemon=True)
    worker.start()
    worker.join(timeout=timeout)
    if worker.is_alive():
        raise TimeoutError("bounded operation deadline expired")
    ok, value = outcome.get_nowait()
    if not ok:
        raise value
    return value


def _terminate_owned_process(process: _Process) -> None:
    if process.returncode is not None:
        return
    waiter = getattr(process, "wait", None)
    try:
        process.terminate()
        if waiter is not None:
            waiter(timeout=1.0)
        else:
            process.communicate(timeout=1.0)
    except Exception:
        try:
            process.kill()
            if waiter is not None:
                waiter(timeout=1.0)
            else:
                process.communicate(timeout=1.0)
        except Exception:
            pass


def _require_safe_executable(path: Path) -> None:
    _require_safe_regular_file(path, "probe executable")
    for ancestor in (path, *path.parents):
        if not ancestor.exists() and not ancestor.is_symlink():
            continue
        metadata = ancestor.stat(follow_symlinks=False)
        if ancestor.is_symlink() or getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT:
            raise DesktopComputeProbeError("probe executable ancestry is unsafe")


def _require_safe_regular_file(path: Path, label: str) -> None:
    if not path.is_absolute():
        raise DesktopComputeProbeError(f"{label} must be absolute")
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise DesktopComputeProbeError(f"{label} is unavailable") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise DesktopComputeProbeError(f"{label} must be a single-link regular file")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


__all__ = [
    "BoundedDesktopComputeProbe",
    "DesktopComputeProbeError",
    "MAX_PROBE_OUTPUT_BYTES",
    "NetworkIsolationAttestor",
    "OsDisplayDriverRuntimePolicy",
    "PER_ADAPTER_TIMEOUT_SECONDS",
    "ProbeCommand",
    "ProbeResult",
    "ProbeStatus",
    "ProductRuntimeManifestBinding",
    "RuntimeModuleEvidence",
    "RuntimeTrustClass",
    "TOTAL_PROBE_TIMEOUT_SECONDS",
    "admit_os_display_driver_runtime",
    "admit_product_private_runtime",
    "frozen_probe_registry",
    "capability_from_probe_result",
    "validate_probe_registry",
    "validate_capability_admission_receipt",
    "probe_command_sha256",
]
