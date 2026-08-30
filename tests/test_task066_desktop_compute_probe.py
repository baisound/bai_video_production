from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from ai_video_production.desktop_compute_policy import AdapterIdentity
from ai_video_production.desktop_compute_probe import (
    BoundedDesktopComputeProbe,
    DesktopComputeProbeError,
    MAX_PROBE_OUTPUT_BYTES,
    OsDisplayDriverRuntimePolicy,
    ProbeCommand,
    ProbeStatus,
    ProductRuntimeManifestBinding,
    RuntimeModuleEvidence,
    RuntimeTrustClass,
    admit_os_display_driver_runtime,
    admit_product_private_runtime,
    frozen_probe_registry,
    probe_command_sha256,
    validate_probe_registry,
)


def _identity() -> AdapterIdentity:
    return AdapterIdentity(
        luid="LUID-1",
        vendor_id="10DE",
        device_id="2783",
        subsystem_id="0000",
        driver_instance_digest="sha256:" + "a" * 64,
    )


def _file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _product_binding(path: Path, version: str = "TEST-1") -> ProductRuntimeManifestBinding:
    return ProductRuntimeManifestBinding(
        module_name=path.name,
        install_relative_path=path.name,
        version=version,
        sha256=_file_sha(path),
    )


def _payload(path: Path, *, runtime_modules: list[dict[str, object]] | None = None) -> dict[str, object]:
    modules = runtime_modules
    if modules is None:
        modules = [{
            "module_name": path.name,
            "trust_class": "PRODUCT_PRIVATE",
            "loaded_path": str(path.resolve()),
            "version": "TEST-1",
            "sha256": _file_sha(path),
            "signer": None,
        }]
    return {
        "schema_version": "1.0.0",
        "probe_id": "synthetic.cuda",
        "adapter_identity": _identity().to_dict(),
        "backend": "CUDA",
        "compatible_workload_ids": ["image.local.comfyui"],
        "runtime_modules": modules,
        "workload_observation_status": "NOT_EXECUTED",
    }


def _command(executable: Path, argv: tuple[str, ...], *, executable_sha256: str | None = None) -> ProbeCommand:
    return ProbeCommand(
        probe_id="synthetic.cuda",
        command=argv,
        adapter_identity=_identity(),
        backend="CUDA",
        workload_ids=("image.local.comfyui",),
        executable_sha256=executable_sha256 or _file_sha(executable),
        command_sha256=probe_command_sha256(argv),
        binary_root=executable.parent,
        product_runtime_bindings=(_product_binding(executable),),
    )


def test_shell_free_probe_separates_admitted_inventory_from_workload_observation() -> None:
    executable = Path(sys.executable).resolve()
    payload = _payload(executable)
    argv = (str(executable), "-c", f"print({json.dumps(json.dumps(payload))})")
    result = BoundedDesktopComputeProbe(
        network_isolation_attestor=lambda item: item.network_policy == "DENY",
        test_seam=True,
    ).run([_command(executable, argv)])[0]

    assert result.status is ProbeStatus.NOT_CONFIRMED
    assert result.reason_code == "TEST_SEAM_CAPABILITY_PARSED"
    assert result.workload_observation_status == "NOT_EXECUTED"
    assert result.compatible_workload_ids == ("image.local.comfyui",)
    assert len(result.runtime_modules) == 1


class _TimeoutProcess:
    pid = 1234
    returncode = None

    def __init__(self) -> None:
        self.terminated = False
        self.killed = False

    def communicate(self, input=None, timeout=None):
        if self.terminated or self.killed:
            self.returncode = -1
            return b"", b""
        raise subprocess.TimeoutExpired("probe", timeout)

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def test_timeout_terminates_only_owned_probe_and_returns_not_confirmed(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.write_bytes(b"synthetic")
    process = _TimeoutProcess()
    command = _command(executable.resolve(), (str(executable.resolve()),))
    command = ProbeCommand(**{
        name: getattr(command, name)
        for name in command.__dataclass_fields__
        if name != "timeout_seconds"
    }, timeout_seconds=0.5)
    result = BoundedDesktopComputeProbe(
        process_factory=lambda *args, **kwargs: process,
        network_isolation_attestor=lambda item: True,
        test_seam=True,
    ).run([command])[0]
    assert result.status is ProbeStatus.NOT_CONFIRMED
    assert result.reason_code == "PROBE_TIMEOUT"
    assert process.terminated is True


def test_total_timeout_marks_unstarted_probe_not_confirmed(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.write_bytes(b"synthetic")
    ticks = iter((0.0, 21.0, 21.0, 21.0))
    command = _command(executable.resolve(), (str(executable.resolve()),))
    probe = BoundedDesktopComputeProbe(
        process_factory=lambda *args, **kwargs: pytest.fail("process must not start"),
        monotonic=lambda: next(ticks),
        network_isolation_attestor=lambda item: True,
        test_seam=True,
    )
    assert probe.run([command])[0].reason_code == "TOTAL_PROBE_TIMEOUT"


def test_product_private_runtime_requires_exact_manifest_path_hash_and_version(tmp_path: Path) -> None:
    root = tmp_path / "binary"
    module = root / "runtime" / "cuda" / "cublas.dll"
    module.parent.mkdir(parents=True)
    module.write_bytes(b"official synthetic bytes")
    binding = ProductRuntimeManifestBinding(
        "cublas.dll", "runtime/cuda/cublas.dll", "12.9.2.10", _file_sha(module)
    )
    evidence = RuntimeModuleEvidence(
        "cublas.dll", RuntimeTrustClass.PRODUCT_PRIVATE, module.resolve(),
        "12.9.2.10", _file_sha(module), None,
    )
    assert admit_product_private_runtime(binary_root=root, binding=binding, observation=evidence) == evidence
    wrong = RuntimeModuleEvidence(
        evidence.module_name, evidence.trust_class, evidence.loaded_path,
        evidence.version, "sha256:" + "f" * 64, None,
    )
    with pytest.raises(DesktopComputeProbeError, match="identity"):
        admit_product_private_runtime(binary_root=root, binding=binding, observation=wrong)


def test_os_driver_uses_trusted_signer_version_hash_and_device_identity(tmp_path: Path) -> None:
    root = tmp_path / "System32" / "DriverStore"
    module = root / "nv.dll"
    module.parent.mkdir(parents=True)
    module.write_bytes(b"driver")
    evidence = RuntimeModuleEvidence(
        "nv.dll", RuntimeTrustClass.OS_DISPLAY_DRIVER, module.resolve(),
        "1.0", _file_sha(module), "NVIDIA Corporation",
    )
    policy = OsDisplayDriverRuntimePolicy(
        "nv.dll", (root.resolve(),), ("NVIDIA Corporation",), ("1.0",),
        _identity().driver_instance_digest,
    )
    assert admit_os_display_driver_runtime(
        policy=policy,
        adapter_identity=_identity(),
        signature_verifier=lambda path: ("NVIDIA Corporation", "1.0"),
        observation=evidence,
    ) == evidence
    with pytest.raises(DesktopComputeProbeError, match="signer"):
        admit_os_display_driver_runtime(
            policy=policy,
            adapter_identity=_identity(),
            signature_verifier=lambda path: ("Untrusted", "1.0"),
            observation=evidence,
        )


def test_missing_network_attestation_never_starts_process(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.write_bytes(b"synthetic")
    result = BoundedDesktopComputeProbe(
        process_factory=lambda *args, **kwargs: pytest.fail("process must not start"),
        test_seam=True,
    ).run([_command(executable.resolve(), (str(executable.resolve()),))])[0]
    assert result.reason_code == "NETWORK_ISOLATION_NOT_CONFIRMED"


def test_runtime_zero_inventory_cannot_be_capability_pass() -> None:
    executable = Path(sys.executable).resolve()
    payload = _payload(executable, runtime_modules=[])
    argv = (str(executable), "-c", f"print({json.dumps(json.dumps(payload))})")
    result = BoundedDesktopComputeProbe(
        network_isolation_attestor=lambda item: True,
        test_seam=True,
    ).run([_command(executable, argv)])[0]
    assert result.status is ProbeStatus.NOT_CONFIRMED
    assert result.reason_code == "RUNTIME_ADMISSION_FAILED"


def test_streaming_output_limit_terminates_before_unbounded_buffering() -> None:
    executable = Path(sys.executable).resolve()
    argv = (str(executable), "-c", f"print('x' * {MAX_PROBE_OUTPUT_BYTES + 8192})")
    result = BoundedDesktopComputeProbe(
        network_isolation_attestor=lambda item: True,
        test_seam=True,
    ).run([_command(executable, argv)])[0]
    assert result.status is ProbeStatus.NOT_CONFIRMED
    assert result.reason_code == "PROBE_OUTPUT_EXCEEDED"


def test_command_digest_executable_and_network_policy_fail_closed(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.write_bytes(b"synthetic")
    base = _command(executable.resolve(), (str(executable.resolve()),))
    values = {name: getattr(base, name) for name in base.__dataclass_fields__}
    values["command_sha256"] = "sha256:" + "f" * 64
    with pytest.raises(DesktopComputeProbeError, match="command manifest"):
        ProbeCommand(**values)
    values = {name: getattr(base, name) for name in base.__dataclass_fields__}
    values["network_policy"] = "ALLOW"
    with pytest.raises(DesktopComputeProbeError, match="network"):
        ProbeCommand(**values)


def test_probe_executable_hash_mismatch_never_starts_process(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.write_bytes(b"synthetic")
    command = _command(
        executable.resolve(),
        (str(executable.resolve()),),
        executable_sha256="sha256:" + "f" * 64,
    )
    result = BoundedDesktopComputeProbe(
        process_factory=lambda *args, **kwargs: pytest.fail("process must not start"),
        network_isolation_attestor=lambda item: True,
        test_seam=True,
    ).run([command])[0]
    assert result.status is ProbeStatus.NOT_CONFIRMED
    assert result.reason_code == "PROBE_EXECUTABLE_HASH_MISMATCH"


def test_production_registry_is_frozen_unsealed_and_never_launches_arbitrary_helper(tmp_path: Path) -> None:
    registry = frozen_probe_registry()
    assert all(row["admission_state"] == "DISABLED_UNTIL_HELPER_SEALED" for row in registry["probes"])
    executable = tmp_path / "arbitrary.exe"
    executable.write_bytes(b"arbitrary")
    command = _command(executable.resolve(), (str(executable.resolve()),))
    result = BoundedDesktopComputeProbe(
        process_factory=lambda *args, **kwargs: pytest.fail("unsealed helper must not start")
    ).run([command])[0]
    assert result.status is ProbeStatus.NOT_CONFIRMED
    assert result.reason_code == "PROBE_HELPER_NOT_SEALED"
    with pytest.raises(DesktopComputeProbeError, match="test-only"):
        BoundedDesktopComputeProbe(network_isolation_attestor=lambda item: True)
    registry["probes"][0]["helper_filename"] = "arbitrary.exe"
    with pytest.raises(DesktopComputeProbeError, match="frozen rows"):
        validate_probe_registry(registry)


def test_slow_network_attestor_times_out_before_process_launch(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.write_bytes(b"synthetic")
    base = _command(executable.resolve(), (str(executable.resolve()),))
    values = {name: getattr(base, name) for name in base.__dataclass_fields__}
    values["timeout_seconds"] = 0.1
    command = ProbeCommand(**values)
    launched = False

    def start(*args, **kwargs):
        nonlocal launched
        launched = True
        pytest.fail("expired attestation must prevent launch")

    def slow_attestor(item):
        time.sleep(0.4)
        return True

    result = BoundedDesktopComputeProbe(
        process_factory=start,
        network_isolation_attestor=slow_attestor,
        test_seam=True,
    ).run([command])[0]
    assert result.reason_code == "PROBE_TIMEOUT"
    assert launched is False


def test_slow_signature_and_runtime_admission_obey_same_deadline(tmp_path: Path) -> None:
    helper = Path(sys.executable).resolve()
    driver_root = tmp_path / "DriverStore"
    driver = driver_root / "nv.dll"
    driver.parent.mkdir(parents=True)
    driver.write_bytes(b"driver")
    policy = OsDisplayDriverRuntimePolicy(
        driver.name,
        (driver_root.resolve(),),
        ("NVIDIA Corporation",),
        ("1.0",),
        _identity().driver_instance_digest,
    )
    payload = _payload(helper, runtime_modules=[{
        "module_name": driver.name,
        "trust_class": "OS_DISPLAY_DRIVER",
        "loaded_path": str(driver.resolve()),
        "version": "1.0",
        "sha256": _file_sha(driver),
        "signer": "NVIDIA Corporation",
    }])
    argv = (str(helper), "-c", f"print({json.dumps(json.dumps(payload))})")
    command = ProbeCommand(
        probe_id="synthetic.cuda",
        command=argv,
        adapter_identity=_identity(),
        backend="CUDA",
        workload_ids=("image.local.comfyui",),
        executable_sha256=_file_sha(helper),
        command_sha256=probe_command_sha256(argv),
        os_display_driver_policies=(policy,),
        timeout_seconds=0.25,
    )

    def slow_verifier(path: Path) -> tuple[str, str]:
        time.sleep(0.6)
        return "NVIDIA Corporation", "1.0"

    started = time.monotonic()
    result = BoundedDesktopComputeProbe(
        network_isolation_attestor=lambda item: True,
        signature_verifier=slow_verifier,
        test_seam=True,
    ).run([command])[0]
    assert result.reason_code == "PROBE_TIMEOUT"
    assert time.monotonic() - started < 0.55
