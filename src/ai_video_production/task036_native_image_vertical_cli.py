"""Human-gated canonical TASK-036 local IMAGE vertical.

This operator CLI owns no Product state.  It consumes an already-current
TASK-027 Queue through the leased TASK-036 Shell and keeps execution and output
adoption as separate Human-confirmed operations.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import stat
import sys
from typing import Any, Callable, Mapping, Sequence

from .errors import ProductError, ProductErrorCategory
from .product_project_store import ProductProjectManifestStore
from .serialization import canonical_json_bytes, sha256_bytes
from .task036_trusted_launcher import (
    Task036LaunchConfiguration,
    Task036TrustedLaunch,
    TASK036_LAUNCH_CONFIG_MAX_BYTES,
    build_trusted_launch,
)


_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_QUEUE_ID_RE = re.compile(r"QUEUE-[0-9A-F]{24}")
_EXECUTION_ID_RE = re.compile(r"EXEC-[0-9A-F]{24}")
_SAFE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_PUBLIC_ERROR_CODE_RE = re.compile(r"ERR_[A-Z0-9_]{1,124}")
_LOGICAL_REF_RE = re.compile(r"project-output://[A-Za-z0-9][A-Za-z0-9._/-]{0,499}")

OutputWriter = Callable[[str], None]
InputReader = Callable[[], str]
ConfigScopeLoader = Callable[[str | Path], tuple[Task036LaunchConfiguration, str]]
ManifestLoader = Callable[[str | Path], Any]
LaunchBuilder = Callable[..., Task036TrustedLaunch]


def _error(code: str, message: str, category: ProductErrorCategory) -> ProductError:
    return ProductError(code, message, category)


def _required_sha(value: str, *, code: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise _error(code, "Expected SHA-256 coordinate is invalid", ProductErrorCategory.VALIDATION)
    return value


def _required_id(value: str, pattern: re.Pattern[str], *, code: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise _error(code, "Expected logical identity is invalid", ProductErrorCategory.VALIDATION)
    return value


def _public_id(value: Any, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not _SAFE_ID_RE.fullmatch(value)
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        raise _error(code, "Public logical identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return value


def _public_enum(value: Any, allowed: set[str], *, code: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise _error(code, "Public enum value is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return value


def _public_error_code(value: Any) -> str:
    if isinstance(value, str) and _PUBLIC_ERROR_CODE_RE.fullmatch(value):
        return value
    return "ERR_TASK036_NATIVE_VERTICAL_REJECTED"


def _snapshot_sha(value: Mapping[str, Any], name: str, *, code: str) -> str:
    return _required_sha(value.get(name), code=code)


def _emit(writer: OutputWriter, value: Mapping[str, Any]) -> None:
    writer(json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _emit_safely(writer: OutputWriter, value: Mapping[str, Any]) -> bool:
    try:
        _emit(writer, value)
        return True
    except (OSError, UnicodeError, ValueError):
        return False


def _require_regular_file(path: Path, *, code: str) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise _error(code, "Required initialized Product file is unavailable", ProductErrorCategory.SECURITY)


def _require_directory(path: Path, *, code: str) -> None:
    if path.is_symlink() or not path.is_dir():
        raise _error(code, "Required initialized Product directory is unavailable", ProductErrorCategory.SECURITY)


def _require_initialized(configuration: Task036LaunchConfiguration) -> None:
    if configuration.local_image_generation is None:
        raise _error(
            "ERR_TASK036_NATIVE_IMAGE_RUNTIME_NOT_BOUND",
            "The reviewed trusted configuration has no local IMAGE runtime",
            ProductErrorCategory.NOT_SUPPORTED,
        )
    for directory in (
        configuration.project_root,
        configuration.asset_root,
        configuration.job_root,
        configuration.transcription_output,
        configuration.cut_output,
        configuration.handoff_destination,
        configuration.native_render_evidence_root.parent,
        configuration.native_render_report_path.parent,
    ):
        _require_directory(directory, code="ERR_TASK036_NATIVE_PROJECT_NOT_INITIALIZED")
    for path in (
        configuration.database_path,
        configuration.project_root / "ai-connection-settings.json",
        configuration.project_root / "generation-queue.json",
    ):
        _require_regular_file(path, code="ERR_TASK036_NATIVE_PROJECT_NOT_INITIALIZED")


def _load_config_scope(path: str | Path) -> tuple[Task036LaunchConfiguration, str]:
    source = Path(path)
    try:
        before = source.lstat()
        if source.is_symlink() or not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= TASK036_LAUNCH_CONFIG_MAX_BYTES:
            raise OSError("invalid configuration file identity")
        descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(descriptor)
            raw = b""
            while len(raw) <= TASK036_LAUNCH_CONFIG_MAX_BYTES:
                chunk = os.read(descriptor, min(65536, (TASK036_LAUNCH_CONFIG_MAX_BYTES + 1) - len(raw)))
                if not chunk:
                    break
                raw += chunk
        finally:
            os.close(descriptor)
        after = source.lstat()
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size)
        if identity(before) != identity(opened) or identity(opened) != identity(after) or len(raw) != opened.st_size:
            raise OSError("configuration file changed while loading")
        configuration = Task036LaunchConfiguration.from_dict(json.loads(raw.decode("utf-8")))
        return configuration, sha256_bytes(raw)
    except ProductError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _error("ERR_TASK036_NATIVE_LAUNCH_CONFIG_INVALID", "Trusted launch configuration is invalid", ProductErrorCategory.DATA_INTEGRITY) from exc


def _load_scope(
    args: argparse.Namespace,
    *,
    config_scope_loader: ConfigScopeLoader,
    manifest_loader: ManifestLoader,
    initialization_checker: Callable[[Task036LaunchConfiguration], None],
) -> tuple[Task036LaunchConfiguration, str, str]:
    configuration, config_sha = config_scope_loader(args.launch_config)
    expected_config = _required_sha(args.expected_launch_config_sha256, code="ERR_TASK036_NATIVE_LAUNCH_CONFIG_SHA_INVALID")
    if config_sha != expected_config:
        raise _error("ERR_TASK036_NATIVE_LAUNCH_CONFIG_STALE", "Trusted launch configuration differs from the reviewed identity", ProductErrorCategory.AUTHORIZATION)
    if configuration.project_id != args.expected_project_id:
        raise _error(
            "ERR_TASK036_NATIVE_PROJECT_ID_MISMATCH",
            "Trusted configuration Project identity differs from the expected identity",
            ProductErrorCategory.AUTHORIZATION,
        )
    initialization_checker(configuration)
    manifest = manifest_loader(configuration.project_root)
    if manifest.project_id != configuration.project_id:
        raise _error(
            "ERR_TASK036_NATIVE_MANIFEST_PROJECT_MISMATCH",
            "Canonical manifest Project identity differs from the trusted configuration",
            ProductErrorCategory.SECURITY,
        )
    expected_manifest = _required_sha(
        args.expected_manifest_sha256,
        code="ERR_TASK036_NATIVE_MANIFEST_SHA_INVALID",
    )
    if manifest.project_manifest_sha256 != expected_manifest:
        raise _error(
            "ERR_TASK036_NATIVE_MANIFEST_STALE",
            "Canonical manifest changed before the requested operation",
            ProductErrorCategory.AUTHORIZATION,
        )
    return configuration, expected_manifest, config_sha


def _require_manifest_current(
    configuration: Task036LaunchConfiguration,
    expected_sha256: str,
    *,
    manifest_loader: ManifestLoader,
) -> None:
    manifest = manifest_loader(configuration.project_root)
    if manifest.project_id != configuration.project_id or manifest.project_manifest_sha256 != expected_sha256:
        raise _error(
            "ERR_TASK036_NATIVE_MANIFEST_STALE",
            "Canonical manifest changed after Human review",
            ProductErrorCategory.AUTHORIZATION,
        )


def _queue_context(bridge: Any, queue_entry_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    queue = bridge.generation_queue_snapshot({})
    if queue.get("available") is not True:
        raise _error("ERR_TASK036_NATIVE_QUEUE_UNAVAILABLE", "Generation Queue is unavailable", ProductErrorCategory.STATE)
    entries = [item for item in queue.get("entries", []) if item.get("queue_entry_id") == queue_entry_id]
    if len(entries) != 1:
        raise _error("ERR_TASK036_NATIVE_QUEUE_ENTRY_NOT_FOUND", "Exact Queue entry is unavailable", ProductErrorCategory.STATE)
    entry = entries[0]
    execution = queue.get("execution_control")
    adoption = queue.get("output_adoption_control")
    if not isinstance(execution, dict) or execution.get("available") is not True:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_UNAVAILABLE", "Generation execution is unavailable", ProductErrorCategory.STATE)
    if not isinstance(adoption, dict) or adoption.get("available") is not True:
        raise _error("ERR_TASK036_NATIVE_ADOPTION_UNAVAILABLE", "Output adoption is unavailable", ProductErrorCategory.STATE)
    return queue, execution, adoption


def _execution_for_queue(execution: Mapping[str, Any], queue_entry_id: str) -> dict[str, Any] | None:
    events = [item for item in execution.get("latest_executions", []) if item.get("queue_entry_id") == queue_entry_id]
    if len(events) > 1:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_AMBIGUOUS", "Queue entry has ambiguous execution identity", ProductErrorCategory.DATA_INTEGRITY)
    return None if not events else dict(events[0])


def _require_completed_event(event: Mapping[str, Any], *, expected_output_sha256: str | None = None) -> dict[str, Any]:
    if event.get("state") != "COMPLETED" or event.get("media_kind") != "IMAGE":
        raise _error("ERR_TASK036_NATIVE_EXECUTION_NOT_COMPLETED", "Exact IMAGE execution is not completed", ProductErrorCategory.STATE)
    execution_id = _required_id(str(event.get("execution_id", "")), _EXECUTION_ID_RE, code="ERR_TASK036_NATIVE_EXECUTION_ID_INVALID")
    queue_entry_id = _required_id(str(event.get("queue_entry_id", "")), _QUEUE_ID_RE, code="ERR_TASK036_NATIVE_QUEUE_ID_INVALID")
    output_sha = _required_sha(str(event.get("output_sha256", "")), code="ERR_TASK036_NATIVE_OUTPUT_SHA_INVALID")
    output_ref = event.get("output_ref")
    output_path = None if not isinstance(output_ref, str) else output_ref.removeprefix("project-output://")
    if (
        not isinstance(output_ref, str)
        or not _LOGICAL_REF_RE.fullmatch(output_ref)
        or output_path is None
        or any(part in {"", ".", ".."} for part in PurePosixPath(output_path).parts)
    ):
        raise _error("ERR_TASK036_NATIVE_OUTPUT_REF_INVALID", "Completed output reference is invalid", ProductErrorCategory.DATA_INTEGRITY)
    if expected_output_sha256 is not None and output_sha != expected_output_sha256:
        raise _error("ERR_TASK036_NATIVE_OUTPUT_SHA_MISMATCH", "Completed output differs from the Human-reviewed digest", ProductErrorCategory.AUTHORIZATION)
    return {
        "execution_id": execution_id,
        "queue_entry_id": queue_entry_id,
        "output_ref": output_ref,
        "output_sha256": output_sha,
        "media_kind": "IMAGE",
        "state": "COMPLETED",
    }


def _confirmation(kind: str, body: Mapping[str, Any]) -> tuple[str, str]:
    digest = sha256_bytes(canonical_json_bytes(dict(body)))
    return digest, f"{kind} {digest}"


def _status_execution(bridge: Any, configuration: Task036LaunchConfiguration, manifest_sha: str, config_sha: str, queue_entry_id: str) -> dict[str, Any]:
    queue, execution, _adoption = _queue_context(bridge, queue_entry_id)
    event = _execution_for_queue(execution, queue_entry_id)
    queue_sha = _snapshot_sha(queue, "queue_snapshot_sha256", code="ERR_TASK036_NATIVE_QUEUE_SHA_INVALID")
    execution_sha = _snapshot_sha(execution, "execution_snapshot_sha256", code="ERR_TASK036_NATIVE_EXECUTION_SHA_INVALID")
    base = {
        "operation": "STATUS_EXECUTION",
        "project_id": configuration.project_id,
        "project_manifest_sha256": manifest_sha,
        "launch_config_sha256": config_sha,
        "queue_entry_id": queue_entry_id,
        "queue_snapshot_sha256": queue_sha,
        "execution_snapshot_sha256": execution_sha,
        "provider_dispatch_started": False,
        "automatic_retry_allowed": False,
    }
    if event is None:
        readiness = bridge.generation_execution_preflight({"queue_entry_id": queue_entry_id})
        if readiness.get("dispatch_performed") is not False:
            raise _error("ERR_TASK036_NATIVE_PREFLIGHT_DISPATCHED", "Runtime preflight unexpectedly dispatched work", ProductErrorCategory.DATA_INTEGRITY)
        return {
            **base,
            "status": "READY_TO_EXECUTE",
            "runtime_ready": True,
            "route_id": _public_id(readiness.get("route_id"), code="ERR_TASK036_NATIVE_ROUTE_ID_INVALID"),
            "provider_id": _public_id(readiness.get("provider_id"), code="ERR_TASK036_NATIVE_PROVIDER_ID_INVALID"),
            "model_id": _public_id(readiness.get("model_id"), code="ERR_TASK036_NATIVE_MODEL_ID_INVALID"),
            "workflow_sha256": _required_sha(readiness.get("workflow_sha256"), code="ERR_TASK036_NATIVE_WORKFLOW_SHA_INVALID"),
        }
    state = event.get("state")
    if state == "COMPLETED":
        return {**base, **_require_completed_event(event), "status": "COMPLETED_REDISCOVERED"}
    if state == "DISPATCHING":
        recovery_rows = execution.get("recovery", {}).get("dispatching", [])
        row = next((item for item in recovery_rows if item.get("execution_id") == event.get("execution_id")), {})
        recovery_supported = row.get("recovery_supported") is True
        return {**base, "status": "RECOVERY_REQUIRED" if recovery_supported else "RECOVERY_UNSUPPORTED", "execution_id": _required_id(event.get("execution_id"), _EXECUTION_ID_RE, code="ERR_TASK036_NATIVE_EXECUTION_ID_INVALID"), "recovery_supported": recovery_supported, "use_product_shell_recovery": recovery_supported}
    if state == "FAILED":
        return {**base, "status": "FAILED", "execution_id": _required_id(event.get("execution_id"), _EXECUTION_ID_RE, code="ERR_TASK036_NATIVE_EXECUTION_ID_INVALID"), "failure_code": _public_id(event.get("failure_code"), code="ERR_TASK036_NATIVE_FAILURE_CODE_INVALID")}
    raise _error("ERR_TASK036_NATIVE_EXECUTION_STATE_INVALID", "Execution state is not recognized", ProductErrorCategory.DATA_INTEGRITY)


def _execute(
    bridge: Any,
    configuration: Task036LaunchConfiguration,
    manifest_sha: str,
    config_sha: str,
    queue_entry_id: str,
    *,
    input_reader: InputReader,
    writer: OutputWriter,
    manifest_loader: ManifestLoader,
) -> dict[str, Any]:
    queue, execution, _adoption = _queue_context(bridge, queue_entry_id)
    if _execution_for_queue(execution, queue_entry_id) is not None:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_ALREADY_STARTED", "Use STATUS or Product Shell recovery for existing execution history", ProductErrorCategory.STATE)
    readiness = bridge.generation_execution_preflight({"queue_entry_id": queue_entry_id})
    if readiness.get("dispatch_performed") is not False:
        raise _error("ERR_TASK036_NATIVE_PREFLIGHT_DISPATCHED", "Runtime preflight unexpectedly dispatched work", ProductErrorCategory.DATA_INTEGRITY)
    queue_sha = _snapshot_sha(queue, "queue_snapshot_sha256", code="ERR_TASK036_NATIVE_QUEUE_SHA_INVALID")
    execution_sha = _snapshot_sha(execution, "execution_snapshot_sha256", code="ERR_TASK036_NATIVE_EXECUTION_SHA_INVALID")
    prepared = bridge.generation_execution_prepare({
        "queue_entry_id": queue_entry_id,
        "expected_queue_snapshot_sha256": queue_sha,
        "expected_execution_snapshot_sha256": execution_sha,
        "expected_project_manifest_sha256": manifest_sha,
    })
    for name in ("queue_entry_id", "route_id", "provider_id", "model_id"):
        expected = queue_entry_id if name == "queue_entry_id" else readiness[name]
        if prepared.get(name) != expected:
            bridge.generation_execution_cancel({"confirmation_id": prepared["confirmation_id"]})
            raise _error("ERR_TASK036_NATIVE_PREPARATION_IDENTITY_DRIFT", "Execution preparation identity changed", ProductErrorCategory.DATA_INTEGRITY)
    if prepared.get("media_kind") != "IMAGE" or prepared.get("capability") != "TEXT_TO_IMAGE" or prepared.get("cost_class") != "LOCAL_FREE_AI" or prepared.get("paid_execution_authorized") is not False or prepared.get("provider_execution_started") is not False:
        bridge.generation_execution_cancel({"confirmation_id": prepared["confirmation_id"]})
        raise _error("ERR_TASK036_NATIVE_PREPARATION_NOT_LOCAL_IMAGE", "Execution preparation is outside the local IMAGE boundary", ProductErrorCategory.AUTHORIZATION)
    try:
        prompt_version = prepared.get("prompt_version")
        if isinstance(prompt_version, bool) or not isinstance(prompt_version, int) or prompt_version < 1:
            raise _error("ERR_TASK036_NATIVE_PROMPT_VERSION_INVALID", "Prompt version is invalid", ProductErrorCategory.DATA_INTEGRITY)
        body = {
            "operation": "EXECUTE",
            "project_id": configuration.project_id,
            "project_manifest_sha256": manifest_sha,
            "launch_config_sha256": config_sha,
            "queue_entry_id": queue_entry_id,
            "queue_snapshot_sha256": queue_sha,
            "execution_snapshot_sha256": execution_sha,
            "scene_id": _public_id(prepared.get("scene_id"), code="ERR_TASK036_NATIVE_SCENE_ID_INVALID"),
            "slot_id": _public_id(prepared.get("slot_id"), code="ERR_TASK036_NATIVE_SLOT_ID_INVALID"),
            "prompt_id": _public_id(prepared.get("prompt_id"), code="ERR_TASK036_NATIVE_PROMPT_ID_INVALID"),
            "prompt_version": prompt_version,
            "prompt_sha256": _required_sha(prepared.get("prompt_sha256"), code="ERR_TASK036_NATIVE_PROMPT_SHA_INVALID"),
            "route_id": _public_id(prepared.get("route_id"), code="ERR_TASK036_NATIVE_ROUTE_ID_INVALID"),
            "provider_id": _public_id(prepared.get("provider_id"), code="ERR_TASK036_NATIVE_PROVIDER_ID_INVALID"),
            "model_id": _public_id(prepared.get("model_id"), code="ERR_TASK036_NATIVE_MODEL_ID_INVALID"),
            "capability": _public_enum(prepared.get("capability"), {"TEXT_TO_IMAGE"}, code="ERR_TASK036_NATIVE_CAPABILITY_INVALID"),
            "cost_class": _public_enum(prepared.get("cost_class"), {"LOCAL_FREE_AI"}, code="ERR_TASK036_NATIVE_COST_CLASS_INVALID"),
            "media_kind": _public_enum(prepared.get("media_kind"), {"IMAGE"}, code="ERR_TASK036_NATIVE_MEDIA_KIND_INVALID"),
            "workflow_sha256": _required_sha(readiness.get("workflow_sha256"), code="ERR_TASK036_NATIVE_WORKFLOW_SHA_INVALID"),
            "runtime_policy": _public_id(readiness.get("runtime_policy"), code="ERR_TASK036_NATIVE_RUNTIME_POLICY_INVALID"),
        }
    except ProductError:
        bridge.generation_execution_cancel({"confirmation_id": prepared["confirmation_id"]})
        raise
    digest, phrase = _confirmation("EXECUTE", body)
    _emit(writer, {"status": "HUMAN_CONFIRMATION_REQUIRED", "confirmation_sha256": digest, "confirmation_phrase": phrase, **body})
    try:
        response = input_reader()
    except (EOFError, KeyboardInterrupt):
        response = ""
    if response != phrase:
        bridge.generation_execution_cancel({"confirmation_id": prepared["confirmation_id"]})
        return {"operation": "EXECUTE", "status": "CANCELLED", "queue_entry_id": queue_entry_id, "provider_dispatch_started": False}
    _require_manifest_current(configuration, manifest_sha, manifest_loader=manifest_loader)
    result = bridge.generation_execution_apply({"confirmation_id": prepared["confirmation_id"]})
    event = _execution_for_queue(result, queue_entry_id)
    if event is None:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_RESULT_MISSING", "Execution result is missing", ProductErrorCategory.DATA_INTEGRITY)
    completed = _require_completed_event(event)
    return {"operation": "EXECUTE", "status": "COMPLETED", "project_id": configuration.project_id, "project_manifest_sha256": manifest_sha, "launch_config_sha256": config_sha, "execution_snapshot_sha256": _snapshot_sha(result, "execution_snapshot_sha256", code="ERR_TASK036_NATIVE_EXECUTION_SHA_INVALID"), **completed, "provider_dispatch_exactly_one_expected": True, "adoption_started": False}


def _adoption_context(bridge: Any, execution_id: str, expected_output_sha256: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    execution = bridge.generation_execution_snapshot({})
    if execution.get("available") is not True:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_UNAVAILABLE", "Generation execution is unavailable", ProductErrorCategory.STATE)
    events = [item for item in execution.get("latest_executions", []) if item.get("execution_id") == execution_id]
    if len(events) != 1:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_NOT_FOUND", "Exact execution is unavailable", ProductErrorCategory.STATE)
    completed = _require_completed_event(events[0], expected_output_sha256=expected_output_sha256)
    queue, current_execution, adoption = _queue_context(bridge, completed["queue_entry_id"])
    current = _execution_for_queue(current_execution, completed["queue_entry_id"])
    if current is None or _require_completed_event(current, expected_output_sha256=expected_output_sha256) != completed:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_IDENTITY_DRIFT", "Completed execution identity changed", ProductErrorCategory.DATA_INTEGRITY)
    production = bridge.production_snapshot({})
    prompt = bridge.prompt_evidence_snapshot({})
    if production.get("available") is not True or prompt.get("available") is not True:
        raise _error("ERR_TASK036_NATIVE_ADOPTION_DEPENDENCY_UNAVAILABLE", "Adoption dependency is unavailable", ProductErrorCategory.STATE)
    _snapshot_sha(queue, "queue_snapshot_sha256", code="ERR_TASK036_NATIVE_QUEUE_SHA_INVALID")
    _snapshot_sha(current_execution, "execution_snapshot_sha256", code="ERR_TASK036_NATIVE_EXECUTION_SHA_INVALID")
    _snapshot_sha(adoption, "adoption_snapshot_sha256", code="ERR_TASK036_NATIVE_ADOPTION_SHA_INVALID")
    _snapshot_sha(production, "snapshot_sha256", code="ERR_TASK036_NATIVE_PRODUCTION_SHA_INVALID")
    _snapshot_sha(prompt, "prompt_snapshot_sha256", code="ERR_TASK036_NATIVE_PROMPT_SNAPSHOT_SHA_INVALID")
    return completed, queue, current_execution, adoption, production, prompt


def _status_adoption(bridge: Any, configuration: Task036LaunchConfiguration, manifest_sha: str, config_sha: str, execution_id: str, expected_output_sha256: str) -> dict[str, Any]:
    completed, queue, execution, adoption, production, prompt = _adoption_context(bridge, execution_id, expected_output_sha256)
    latest = [item for item in adoption.get("latest_adoptions", []) if item.get("execution_id") == execution_id]
    if len(latest) > 1:
        raise _error("ERR_TASK036_NATIVE_ADOPTION_AMBIGUOUS", "Execution has ambiguous adoption identity", ProductErrorCategory.DATA_INTEGRITY)
    if latest:
        adoption_state = latest[0].get("state")
        if adoption_state == "READY_FOR_AUDIT":
            status = "READY_FOR_AUDIT_REDISCOVERED"
        elif adoption_state == "FAILED_KNOWN":
            status = "FAILED_KNOWN"
        else:
            status = "RECOVERY_REQUIRED"
        if status == "READY_FOR_AUDIT_REDISCOVERED":
            slot, candidate = _find_candidate(production, str(latest[0].get("candidate_id", "")))
            if (
                candidate.get("asset_sha256") != expected_output_sha256
                or candidate.get("lifecycle_state") != "READY_FOR_AUDIT"
                or candidate.get("asset_id") != latest[0].get("asset_id")
                or candidate.get("generation_job_id") != execution_id
                or candidate.get("slot_id") != latest[0].get("slot_id")
                or slot.get("slot_id") != latest[0].get("slot_id")
                or slot.get("locked_candidate_id") is not None
            ):
                raise _error(
                    "ERR_TASK036_NATIVE_CANDIDATE_RESULT_INVALID",
                    "Rediscovered Candidate is outside exact READY_FOR_AUDIT state",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
        projection = {"operation": "STATUS_ADOPTION", "status": status, "project_id": configuration.project_id, "project_manifest_sha256": manifest_sha, "launch_config_sha256": config_sha, **completed, "adoption_id": _public_id(latest[0].get("adoption_id"), code="ERR_TASK036_NATIVE_ADOPTION_ID_INVALID"), "candidate_id": _public_id(latest[0].get("candidate_id"), code="ERR_TASK036_NATIVE_CANDIDATE_ID_INVALID"), "candidate_accepted": False, "candidate_locked": False, "publication_authorized": False, "use_product_shell_recovery": status == "RECOVERY_REQUIRED", "provider_replay_started": False}
        if status == "FAILED_KNOWN":
            projection["failure_code"] = _public_id(latest[0].get("failure_code"), code="ERR_TASK036_NATIVE_FAILURE_CODE_INVALID")
        return projection
    eligible = [item for item in adoption.get("eligible_completed_outputs", []) if item.get("execution_id") == execution_id and item.get("adoption_status") == "READY"]
    if len(eligible) != 1:
        raise _error("ERR_TASK036_NATIVE_ADOPTION_NOT_READY", "Completed output is not ready for canonical adoption", ProductErrorCategory.STATE)
    return {"operation": "STATUS_ADOPTION", "status": "READY_TO_ADOPT", "project_id": configuration.project_id, "project_manifest_sha256": manifest_sha, "launch_config_sha256": config_sha, **completed, "queue_snapshot_sha256": queue["queue_snapshot_sha256"], "execution_snapshot_sha256": execution["execution_snapshot_sha256"], "production_snapshot_sha256": production["snapshot_sha256"], "prompt_snapshot_sha256": prompt["prompt_snapshot_sha256"], "adoption_snapshot_sha256": adoption["adoption_snapshot_sha256"], "provider_replay_started": False}


def _find_candidate(production: Mapping[str, Any], candidate_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    found: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for slot in production.get("slots", []):
        for candidate in slot.get("candidates", []):
            if candidate.get("candidate_id") == candidate_id:
                found.append((dict(slot), dict(candidate)))
    if len(found) != 1:
        raise _error("ERR_TASK036_NATIVE_CANDIDATE_IDENTITY", "Canonical Candidate identity is unavailable or ambiguous", ProductErrorCategory.DATA_INTEGRITY)
    return found[0]


def _adopt(
    bridge: Any,
    configuration: Task036LaunchConfiguration,
    manifest_sha: str,
    config_sha: str,
    execution_id: str,
    expected_output_sha256: str,
    *,
    input_reader: InputReader,
    writer: OutputWriter,
    manifest_loader: ManifestLoader,
) -> dict[str, Any]:
    completed, queue, execution, adoption, production, prompt = _adoption_context(bridge, execution_id, expected_output_sha256)
    if any(item.get("execution_id") == execution_id for item in adoption.get("latest_adoptions", [])):
        raise _error("ERR_TASK036_NATIVE_ADOPTION_ALREADY_STARTED", "Use STATUS or Product Shell recovery for existing adoption history", ProductErrorCategory.STATE)
    prepared = bridge.generation_output_adoption_prepare({
        "execution_id": execution_id,
        "expected_execution_snapshot_sha256": execution["execution_snapshot_sha256"],
        "expected_queue_snapshot_sha256": queue["queue_snapshot_sha256"],
        "expected_production_snapshot_sha256": production["snapshot_sha256"],
        "expected_prompt_snapshot_sha256": prompt["prompt_snapshot_sha256"],
        "expected_adoption_snapshot_sha256": adoption["adoption_snapshot_sha256"],
        "expected_project_manifest_sha256": manifest_sha,
    })
    for name in ("provider_execution_started", "provider_execution_replayed", "paid_execution_authorized", "human_audit_decision_created", "candidate_accepted", "candidate_locked", "publication_authorized", "nle_mutation_started"):
        if prepared.get(name) is not False:
            raise _error("ERR_TASK036_NATIVE_ADOPTION_AUTHORITY_EXPANDED", "Adoption preparation expanded authority", ProductErrorCategory.AUTHORIZATION)
    if prepared.get("execution_id") != execution_id or prepared.get("output_sha256") != expected_output_sha256:
        raise _error("ERR_TASK036_NATIVE_ADOPTION_IDENTITY_DRIFT", "Adoption preparation identity changed", ProductErrorCategory.DATA_INTEGRITY)
    slot_id = _public_id(prepared.get("slot_id"), code="ERR_TASK036_NATIVE_SLOT_ID_INVALID")
    candidate_id = _public_id(prepared.get("candidate_id"), code="ERR_TASK036_NATIVE_CANDIDATE_ID_INVALID")
    body = {
        "operation": "ADOPT",
        "project_id": configuration.project_id,
        "project_manifest_sha256": manifest_sha,
        "launch_config_sha256": config_sha,
        **completed,
        "slot_id": slot_id,
        "candidate_id": candidate_id,
        "queue_snapshot_sha256": queue["queue_snapshot_sha256"],
        "execution_snapshot_sha256": execution["execution_snapshot_sha256"],
        "production_snapshot_sha256": production["snapshot_sha256"],
        "prompt_snapshot_sha256": prompt["prompt_snapshot_sha256"],
        "adoption_snapshot_sha256": adoption["adoption_snapshot_sha256"],
    }
    digest, phrase = _confirmation("ADOPT", body)
    _emit(writer, {"status": "HUMAN_CONFIRMATION_REQUIRED", "confirmation_sha256": digest, "confirmation_phrase": phrase, **body})
    try:
        response = input_reader()
    except (EOFError, KeyboardInterrupt):
        response = ""
    if response != phrase:
        return {"operation": "ADOPT", "status": "CANCELLED", "execution_id": execution_id, "provider_replay_started": False, "asset_created": False}
    _require_manifest_current(configuration, manifest_sha, manifest_loader=manifest_loader)
    refreshed, *_ = _adoption_context(bridge, execution_id, expected_output_sha256)
    if refreshed != completed:
        raise _error("ERR_TASK036_NATIVE_EXECUTION_IDENTITY_DRIFT", "Completed execution changed after Human review", ProductErrorCategory.DATA_INTEGRITY)
    result = bridge.generation_output_adoption_apply({"confirmation_id": prepared["confirmation_id"]})
    records = [item for item in result.get("latest_adoptions", []) if item.get("execution_id") == execution_id]
    if (
        len(records) != 1
        or records[0].get("state") != "READY_FOR_AUDIT"
        or records[0].get("candidate_id") != candidate_id
        or records[0].get("slot_id") != slot_id
        or records[0].get("queue_entry_id") != completed["queue_entry_id"]
        or records[0].get("output_ref") != completed["output_ref"]
        or records[0].get("output_sha256") != expected_output_sha256
        or records[0].get("media_kind") != "IMAGE"
    ):
        raise _error("ERR_TASK036_NATIVE_ADOPTION_RESULT_INVALID", "Canonical adoption did not reach exact audit readiness", ProductErrorCategory.DATA_INTEGRITY)
    for name in ("provider_execution_started", "provider_execution_replayed", "paid_execution_authorized", "human_audit_decision_created", "candidate_accepted", "candidate_locked", "publication_authorized", "nle_mutation_started"):
        if result.get(name) is not False:
            raise _error("ERR_TASK036_NATIVE_ADOPTION_AUTHORITY_EXPANDED", "Canonical adoption expanded authority", ProductErrorCategory.AUTHORIZATION)
    current_production = bridge.production_snapshot({})
    slot, candidate = _find_candidate(current_production, records[0]["candidate_id"])
    if (
        candidate.get("asset_sha256") != expected_output_sha256
        or candidate.get("lifecycle_state") != "READY_FOR_AUDIT"
        or candidate.get("asset_id") != records[0].get("asset_id")
        or candidate.get("generation_job_id") != execution_id
        or candidate.get("slot_id") != slot_id
        or slot.get("slot_id") != slot_id
        or slot.get("locked_candidate_id") is not None
    ):
        raise _error("ERR_TASK036_NATIVE_CANDIDATE_RESULT_INVALID", "Candidate is outside exact READY_FOR_AUDIT state", ProductErrorCategory.DATA_INTEGRITY)
    return {"operation": "ADOPT", "status": "READY_FOR_AUDIT", "project_id": configuration.project_id, "project_manifest_sha256": manifest_sha, "launch_config_sha256": config_sha, **completed, "adoption_id": _public_id(records[0].get("adoption_id"), code="ERR_TASK036_NATIVE_ADOPTION_ID_INVALID"), "asset_id": _public_id(records[0].get("asset_id"), code="ERR_TASK036_NATIVE_ASSET_ID_INVALID"), "candidate_id": _public_id(records[0].get("candidate_id"), code="ERR_TASK036_NATIVE_CANDIDATE_ID_INVALID"), "candidate_lifecycle": "READY_FOR_AUDIT", "candidate_accepted": False, "candidate_locked": False, "publication_authorized": False, "provider_replay_started": False}


class _ClosedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise _error(
            "ERR_TASK036_NATIVE_ARGUMENT_SCHEMA",
            "Native vertical arguments do not match an exact operation schema",
            ProductErrorCategory.VALIDATION,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = _ClosedParser(description="Canonical Human-gated TASK-036 local IMAGE vertical", allow_abbrev=False)
    common = _ClosedParser(add_help=False, allow_abbrev=False)
    common.add_argument("--launch-config", required=True)
    common.add_argument("--expected-launch-config-sha256", required=True)
    common.add_argument("--expected-project-id", required=True)
    common.add_argument("--expected-manifest-sha256", required=True)
    sub = parser.add_subparsers(dest="operation", required=True, parser_class=_ClosedParser)
    for name in ("status-execution", "execute"):
        item = sub.add_parser(name, parents=[common], allow_abbrev=False)
        item.add_argument("--queue-entry-id", required=True)
    for name in ("status-adoption", "adopt"):
        item = sub.add_parser(name, parents=[common], allow_abbrev=False)
        item.add_argument("--execution-id", required=True)
        item.add_argument("--expected-output-sha256", required=True)
    return parser


def _require_exact_argv(argv: Sequence[str]) -> None:
    if not argv or argv[0] not in {"status-execution", "execute", "status-adoption", "adopt"}:
        raise _error("ERR_TASK036_NATIVE_ARGUMENT_SCHEMA", "Native vertical arguments do not match an exact operation schema", ProductErrorCategory.VALIDATION)
    common = {"--launch-config", "--expected-launch-config-sha256", "--expected-project-id", "--expected-manifest-sha256"}
    scoped = {"--queue-entry-id"} if argv[0] in {"status-execution", "execute"} else {"--execution-id", "--expected-output-sha256"}
    expected = common | scoped
    if len(argv) != 1 + (2 * len(expected)):
        raise _error("ERR_TASK036_NATIVE_ARGUMENT_SCHEMA", "Native vertical arguments do not match an exact operation schema", ProductErrorCategory.VALIDATION)
    options = argv[1::2]
    values = argv[2::2]
    if set(options) != expected or len(options) != len(set(options)) or any(not value or value.startswith("--") for value in values):
        raise _error("ERR_TASK036_NATIVE_ARGUMENT_SCHEMA", "Native vertical arguments do not match an exact operation schema", ProductErrorCategory.VALIDATION)


def run(
    argv: Sequence[str] | None = None,
    *,
    input_reader: InputReader = input,
    output_writer: OutputWriter = print,
    config_scope_loader: ConfigScopeLoader = _load_config_scope,
    manifest_loader: ManifestLoader = ProductProjectManifestStore.load,
    initialization_checker: Callable[[Task036LaunchConfiguration], None] = _require_initialized,
    launch_builder: LaunchBuilder = build_trusted_launch,
) -> int:
    operation = "UNKNOWN"
    launch: Task036TrustedLaunch | None = None
    exit_code = 1
    result: Mapping[str, Any] = {
        "operation": operation,
        "status": "ERROR",
        "error_code": "ERR_TASK036_NATIVE_VERTICAL_INTERNAL",
        "error_category": "INTERNAL",
        "automatic_retry_allowed": False,
    }
    try:
        raw_argv = list(sys.argv[1:] if argv is None else argv)
        _require_exact_argv(raw_argv)
        args = build_parser().parse_args(raw_argv)
        operation = args.operation.replace("-", "_").upper()
        configuration, manifest_sha, config_sha = _load_scope(
            args,
            config_scope_loader=config_scope_loader,
            manifest_loader=manifest_loader,
            initialization_checker=initialization_checker,
        )
        queue_entry_id = None
        execution_id = None
        output_sha = None
        if hasattr(args, "queue_entry_id"):
            queue_entry_id = _required_id(args.queue_entry_id, _QUEUE_ID_RE, code="ERR_TASK036_NATIVE_QUEUE_ID_INVALID")
        if hasattr(args, "execution_id"):
            execution_id = _required_id(args.execution_id, _EXECUTION_ID_RE, code="ERR_TASK036_NATIVE_EXECUTION_ID_INVALID")
            output_sha = _required_sha(args.expected_output_sha256, code="ERR_TASK036_NATIVE_OUTPUT_SHA_INVALID")
        launch = launch_builder(configuration, allow_product_job_bootstrap=False)
        bridge = launch.bridge
        if operation == "STATUS_EXECUTION":
            result = _status_execution(bridge, configuration, manifest_sha, config_sha, queue_entry_id)
        elif operation == "EXECUTE":
            result = _execute(bridge, configuration, manifest_sha, config_sha, queue_entry_id, input_reader=input_reader, writer=output_writer, manifest_loader=manifest_loader)
        elif operation == "STATUS_ADOPTION":
            result = _status_adoption(bridge, configuration, manifest_sha, config_sha, execution_id, output_sha)
        elif operation == "ADOPT":
            result = _adopt(bridge, configuration, manifest_sha, config_sha, execution_id, output_sha, input_reader=input_reader, writer=output_writer, manifest_loader=manifest_loader)
        else:  # pragma: no cover - argparse owns the closed operation set.
            raise _error("ERR_TASK036_NATIVE_OPERATION_INVALID", "Operation is invalid", ProductErrorCategory.VALIDATION)
        exit_code = 0
    except ProductError as exc:
        result = {"operation": operation, "status": "ERROR", "error_code": _public_error_code(exc.code), "error_category": exc.category.value, "automatic_retry_allowed": False}
    except Exception:
        result = {"operation": operation, "status": "ERROR", "error_code": "ERR_TASK036_NATIVE_VERTICAL_INTERNAL", "error_category": "INTERNAL", "automatic_retry_allowed": False}
    except KeyboardInterrupt:
        result = {"operation": operation, "status": "ERROR", "error_code": "ERR_TASK036_NATIVE_OPERATION_INTERRUPTED", "error_category": "STATE", "automatic_retry_allowed": False}
    finally:
        if launch is not None:
            try:
                launch.close()
            except BaseException:
                if exit_code == 0:
                    exit_code = 1
                    result = {"operation": operation, "status": "ERROR", "error_code": "ERR_TASK036_NATIVE_LAUNCH_CLOSE_FAILED", "error_category": "INTERNAL", "automatic_retry_allowed": False}
    return exit_code if _emit_safely(output_writer, result) else 1


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
