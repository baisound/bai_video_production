"""Pure no-I/O contract for a provisional TASK-014 artifact closure plan.

This module canonicalizes already-supplied metadata observations and candidate
snapshots.  It performs no HTTP, filesystem, installation, import, runtime,
model, audio, or native-tool operation.  A valid plan is diagnostic only and
is never an acquisition or execution capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit

from .serialization import canonical_json_bytes


SCHEMA_ID = "bai.task014.qwen3-tts-runtime-artifact-closure-plan.v1"
_SEMANTIC_DOMAIN = b"TASK014_RUNTIME_ARTIFACT_CLOSURE_PLAN_SEMANTIC_V1\n"
_OBSERVATION_DOMAIN = b"TASK014_RUNTIME_ARTIFACT_CLOSURE_OBSERVATION_V1\n"
_CANDIDATE_SET_DOMAIN = b"TASK014_RUNTIME_ARTIFACT_CANDIDATE_SET_V1\n"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DIST = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+!-]{0,127}$")
_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+!-]{0,254}$")
_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_TIMESTAMP = re.compile(
    r"^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{3,7})?Z$"
)
_REQUIREMENT = re.compile(r"^(?! )(?!.* $)[\x20-\x7e]{1,512}$")
_URL_PATH = re.compile(r"^/[A-Za-z0-9!$&'()+,./:;=@_%~-]*$")
_COMMIT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_MAX_PROJECTS = 256
_MAX_CANDIDATES = 4096
_MAX_OBSERVATIONS = 512
_MAX_REQUIREMENTS = 512
_MAX_RESPONSE_BYTES = 16 * 1024**2
_MAX_METADATA_BYTES = 4 * 1024**2
_MAX_ARTIFACT_BYTES = 16 * 1024**3
_MAX_TOTAL_REQUIREMENTS = 8192
_MAX_PLAN_BYTES = 16 * 1024**2

_PROVIDERS = {"PYTHON_ORG", "PYPI", "PYTORCH_INDEX", "FFMPEG_ORG", "GITHUB_RELEASE"}
_METHODS = {"GET", "HEAD"}
_CONTENT_TYPES = {
    "APPLICATION_JSON", "APPLICATION_VND_PYPI_SIMPLE_V1_JSON",
    "APPLICATION_OCTET_STREAM_METADATA", "APPLICATION_OCTET_STREAM_ARTIFACT",
    "TEXT_HTML", "TEXT_PLAIN",
}
_ARTIFACT_KINDS = {"PYTHON_INSTALLER", "DISTRIBUTION_WHEEL", "NATIVE_TOOL_ARCHIVE"}
_OBSERVATION_KINDS = {
    "PROJECT_INDEX_GET", "PROJECT_RELEASE_GET", "METADATA_SIDECAR_GET",
    "ARTIFACT_HEAD", "CHECKSUM_ASSET_GET", "UPSTREAM_REFERENCE_GET",
}
_HOSTS_BY_PROVIDER = {
    "PYTHON_ORG": {"python.org", "www.python.org"},
    "PYPI": {"pypi.org", "files.pythonhosted.org"},
    "PYTORCH_INDEX": {"download.pytorch.org"},
    "FFMPEG_ORG": {"ffmpeg.org", "www.ffmpeg.org"},
    "GITHUB_RELEASE": {"github.com", "api.github.com"},
}
_INDEX_OWNER = {
    "python": "PYTHON_ORG",
    "torch": "PYTORCH_INDEX",
    "torchaudio": "PYTORCH_INDEX",
    "btbn-ffmpeg-builds": "GITHUB_RELEASE",
}
_NO_EFFECT_FIELDS = (
    "network_accessed", "artifact_body_downloaded", "file_written",
    "package_installed", "target_python_executed", "package_imported",
    "model_loaded", "owner_audio_read", "inference_executed",
    "native_tool_executed",
)


def _expect(value: Mapping[str, Any], fields: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} fields are not exact")


def _text(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label} invalid")
    return value


def _integer(value: Any, minimum: int, maximum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} invalid")
    return value


def _choice(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} invalid")
    return value


def _sha(value: Any, label: str) -> str:
    return _text(value, _SHA, label)


def _timestamp(value: Any) -> str:
    value = _text(value, _TIMESTAMP, "evaluated_at")
    from datetime import datetime
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("evaluated_at invalid") from exc
    return value


def _url(value: Any, provider: str, label: str) -> str:
    if (not isinstance(value, str) or len(value) > 2048 or not value.isascii() or
            value != value.strip() or not value.startswith("https://") or "\\" in value or
            any(ord(character) <= 0x20 or ord(character) == 0x7f for character in value)):
        raise ValueError(f"{label} invalid")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.port is not None or parsed.query or
            parsed.fragment or parsed.netloc != parsed.hostname or
            parsed.hostname not in _HOSTS_BY_PROVIDER[provider] or not _URL_PATH.fullmatch(parsed.path)):
        raise ValueError(f"{label} invalid")
    return value


def _ascii_sorted(values: list[str]) -> list[str]:
    return sorted(values, key=lambda item: item.encode("ascii"))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _digest(domain: bytes, value: Any) -> str:
    return "sha256:" + sha256(domain + canonical_json_bytes(value)).hexdigest()


def _validate_resolver(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "resolver_id", "resolver_revision", "resolver_sha256", "parser_distribution",
        "parser_version", "parser_artifact_sha256", "parser_pin_accepted",
    }
    _expect(value, fields, "resolver")
    result = dict(value)
    result["resolver_id"] = _text(result["resolver_id"], _ID, "resolver_id")
    result["resolver_revision"] = _integer(result["resolver_revision"], 1, 2**31 - 1, "resolver_revision")
    result["resolver_sha256"] = _sha(result["resolver_sha256"], "resolver_sha256")
    if result["parser_distribution"] != "packaging":
        raise ValueError("parser distribution invalid")
    result["parser_version"] = _text(result["parser_version"], _VERSION, "parser_version")
    result["parser_artifact_sha256"] = _sha(result["parser_artifact_sha256"], "parser_artifact_sha256")
    if result["parser_pin_accepted"] is not False:
        raise ValueError("closure-plan contract cannot claim an accepted parser pin")
    return result


def _validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "observation_id", "source", "evaluated_at", "provider", "project_id",
        "index_identity", "observer_id", "observer_revision", "observer_sha256",
        "observation_kind", "canonical_url", "method", "status", "content_type", "declared_bytes",
        "observed_bytes", "redirect_count", "final_host_class",
        "safe_content_path_sha256", "response_sha256", "candidate_count",
        "asserted_artifact_sha256", "transport_policy_passed",
    }
    _expect(value, fields, "observation")
    result = dict(value)
    result["observation_id"] = _text(result["observation_id"], _ID, "observation_id")
    if result["source"] != "SYNTHETIC_CONTRACT_FIXTURE":
        raise ValueError("B1a accepts synthetic observations only")
    result["evaluated_at"] = _timestamp(result["evaluated_at"])
    result["provider"] = _choice(result["provider"], _PROVIDERS, "observation provider")
    result["project_id"] = _text(result["project_id"], _DIST, "observation project_id")
    result["index_identity"] = _text(result["index_identity"], _ID, "observation index_identity")
    result["observer_id"] = _text(result["observer_id"], _ID, "observer_id")
    result["observer_revision"] = _integer(result["observer_revision"], 1, 2**31 - 1, "observer_revision")
    result["observer_sha256"] = _sha(result["observer_sha256"], "observer_sha256")
    result["observation_kind"] = _choice(result["observation_kind"], _OBSERVATION_KINDS, "observation kind")
    result["canonical_url"] = _url(result["canonical_url"], result["provider"], "canonical_url")
    result["method"] = _choice(result["method"], _METHODS, "method")
    result["status"] = _integer(result["status"], 200, 299, "status")
    result["content_type"] = _choice(result["content_type"], _CONTENT_TYPES, "content_type")
    declared_max = _MAX_ARTIFACT_BYTES if result["method"] == "HEAD" else _MAX_RESPONSE_BYTES
    if result["declared_bytes"] is not None:
        result["declared_bytes"] = _integer(result["declared_bytes"], 0, declared_max, "declared_bytes")
    result["observed_bytes"] = _integer(result["observed_bytes"], 0, _MAX_RESPONSE_BYTES, "observed_bytes")
    if result["method"] == "HEAD" and result["observed_bytes"] != 0:
        raise ValueError("HEAD observation cannot claim response body bytes")
    if (result["method"] == "GET" and result["declared_bytes"] is not None and
            result["declared_bytes"] != result["observed_bytes"]):
        raise ValueError("observation byte count mismatch")
    if result["content_type"] == "APPLICATION_OCTET_STREAM_METADATA":
        if result["observed_bytes"] > _MAX_METADATA_BYTES or (
                result["declared_bytes"] is not None and result["declared_bytes"] > _MAX_METADATA_BYTES):
            raise ValueError("metadata sidecar exceeds bound")
    result["redirect_count"] = _integer(result["redirect_count"], 0, 3, "redirect_count")
    result["final_host_class"] = _text(result["final_host_class"], _ID, "final_host_class")
    result["safe_content_path_sha256"] = _sha(result["safe_content_path_sha256"], "safe_content_path_sha256")
    result["response_sha256"] = _sha(result["response_sha256"], "response_sha256")
    result["candidate_count"] = _integer(result["candidate_count"], 0, _MAX_CANDIDATES, "candidate_count")
    if result["asserted_artifact_sha256"] is not None:
        result["asserted_artifact_sha256"] = _sha(result["asserted_artifact_sha256"], "asserted_artifact_sha256")
    if result["transport_policy_passed"] is not False:
        raise ValueError("transport policy state contradicts observation source")
    kind = result["observation_kind"]
    if kind in {"PROJECT_INDEX_GET", "PROJECT_RELEASE_GET"}:
        if result["method"] != "GET" or result["candidate_count"] < 1 or result["asserted_artifact_sha256"] is not None:
            raise ValueError("candidate-bearing observation kind invalid")
        expected_content = {
            ("PROJECT_INDEX_GET", "PYPI"): "APPLICATION_VND_PYPI_SIMPLE_V1_JSON",
            ("PROJECT_INDEX_GET", "PYTORCH_INDEX"): "TEXT_HTML",
            ("PROJECT_RELEASE_GET", "PYTHON_ORG"): "TEXT_HTML",
            ("PROJECT_RELEASE_GET", "GITHUB_RELEASE"): "APPLICATION_JSON",
        }.get((kind, result["provider"]))
        if result["content_type"] != expected_content:
            raise ValueError("candidate-bearing observation content invalid")
    elif kind == "METADATA_SIDECAR_GET":
        if (result["method"] != "GET" or result["candidate_count"] != 0 or
                result["content_type"] != "APPLICATION_OCTET_STREAM_METADATA" or
                result["asserted_artifact_sha256"] is not None):
            raise ValueError("metadata observation kind invalid")
    elif kind == "ARTIFACT_HEAD":
        if (result["method"] != "HEAD" or result["candidate_count"] != 0 or
                result["content_type"] != "APPLICATION_OCTET_STREAM_ARTIFACT" or
                result["declared_bytes"] is None or result["declared_bytes"] < 1 or
                result["asserted_artifact_sha256"] is not None):
            raise ValueError("artifact HEAD observation kind invalid")
    elif kind == "CHECKSUM_ASSET_GET":
        if (result["method"] != "GET" or result["candidate_count"] != 0 or
                result["content_type"] != "TEXT_PLAIN" or
                result["asserted_artifact_sha256"] is None):
            raise ValueError("checksum observation kind invalid")
    elif (result["method"] != "GET" or result["candidate_count"] != 0 or
          result["provider"] != "FFMPEG_ORG" or result["content_type"] != "TEXT_HTML" or
          result["asserted_artifact_sha256"] is not None):
        raise ValueError("upstream reference observation kind invalid")
    return result


def _validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "candidate_id", "artifact_kind", "project_id", "provider", "index_identity", "version",
        "canonical_url", "filename", "bytes", "sha256", "metadata_sha256",
        "metadata_bytes", "requires_python", "wheel_tags", "yanked",
        "prerelease", "development", "postrelease", "local_version",
        "requires_dist", "index_observation_id", "metadata_observation_id",
        "artifact_head_observation_id", "checksum_observation_id", "license_id",
        "manual_legal_review_required", "root_reachable", "availability",
        "classification_state", "upstream_observation_id", "tool_release_contract",
        "required_tool_kinds", "tool_member_mapping_state",
    }
    _expect(value, fields, "candidate")
    result = dict(value)
    result["candidate_id"] = _text(result["candidate_id"], _ID, "candidate_id")
    result["artifact_kind"] = _choice(result["artifact_kind"], _ARTIFACT_KINDS, "artifact kind")
    result["project_id"] = _text(result["project_id"], _DIST, "candidate project_id")
    result["provider"] = _choice(result["provider"], _PROVIDERS, "candidate provider")
    expected_provider = _INDEX_OWNER.get(result["project_id"], "PYPI")
    if result["provider"] != expected_provider:
        raise ValueError("candidate provider does not own project")
    result["index_identity"] = _text(result["index_identity"], _ID, "index_identity")
    result["version"] = _text(result["version"], _VERSION, "candidate version")
    result["canonical_url"] = _url(result["canonical_url"], result["provider"], "candidate canonical_url")
    result["filename"] = _text(result["filename"], _FILENAME, "candidate filename")
    expected_kind = {
        "PYTHON_ORG": ("PYTHON_INSTALLER", ".exe"),
        "PYPI": ("DISTRIBUTION_WHEEL", ".whl"),
        "PYTORCH_INDEX": ("DISTRIBUTION_WHEEL", ".whl"),
        "GITHUB_RELEASE": ("NATIVE_TOOL_ARCHIVE", ".zip"),
    }.get(result["provider"])
    if expected_kind is None or result["artifact_kind"] != expected_kind[0] or not result["filename"].endswith(expected_kind[1]):
        raise ValueError("candidate artifact/provider/filename matrix invalid")
    result["bytes"] = _integer(result["bytes"], 1, _MAX_ARTIFACT_BYTES, "candidate bytes")
    result["sha256"] = _sha(result["sha256"], "candidate sha256")
    is_wheel = result["artifact_kind"] == "DISTRIBUTION_WHEEL"
    if is_wheel:
        result["metadata_sha256"] = _sha(result["metadata_sha256"], "metadata sha256")
        result["metadata_bytes"] = _integer(result["metadata_bytes"], 1, _MAX_METADATA_BYTES, "metadata bytes")
        if (not isinstance(result["requires_python"], str) or not
                _REQUIREMENT.fullmatch(result["requires_python"]) or len(result["requires_python"]) > 128):
            raise ValueError("requires_python invalid")
    elif any(result[key] is not None for key in ("metadata_sha256", "metadata_bytes", "requires_python")):
        raise ValueError("non-wheel candidate cannot claim wheel metadata")
    if not isinstance(result["wheel_tags"], list) or len(result["wheel_tags"]) > 16 or (is_wheel and not result["wheel_tags"]):
        raise ValueError("wheel_tags invalid")
    result["wheel_tags"] = [_text(item, _TAG, "wheel tag") for item in result["wheel_tags"]]
    if result["wheel_tags"] != _ascii_sorted(result["wheel_tags"]) or len(set(result["wheel_tags"])) != len(result["wheel_tags"]):
        raise ValueError("wheel_tags are not canonical")
    if not is_wheel and result["wheel_tags"]:
        raise ValueError("non-wheel candidate cannot claim wheel tags")
    for key in ("yanked", "prerelease", "development", "postrelease"):
        if not isinstance(result[key], bool):
            raise ValueError(f"{key} invalid")
    if result["classification_state"] != "CALLER_REPORTED_UNVERIFIED":
        raise ValueError("candidate classification state invalid")
    if result["local_version"] is not None:
        result["local_version"] = _text(result["local_version"], _VERSION, "local_version")
        if result["project_id"] not in {"torch", "torchaudio"} or result["local_version"] != "cu130":
            raise ValueError("local version unsupported")
    if not isinstance(result["requires_dist"], list) or len(result["requires_dist"]) > _MAX_REQUIREMENTS or (not is_wheel and result["requires_dist"]):
        raise ValueError("requires_dist invalid")
    result["requires_dist"] = [_text(item, _REQUIREMENT, "requires_dist") for item in result["requires_dist"]]
    if result["requires_dist"] != _ascii_sorted(result["requires_dist"]) or len(set(result["requires_dist"])) != len(result["requires_dist"]):
        raise ValueError("requires_dist not canonical")
    result["index_observation_id"] = _text(result["index_observation_id"], _ID, "candidate index_observation_id")
    result["artifact_head_observation_id"] = _text(result["artifact_head_observation_id"], _ID, "artifact_head_observation_id")
    for key in ("metadata_observation_id", "checksum_observation_id", "upstream_observation_id"):
        if result[key] is not None:
            result[key] = _text(result[key], _ID, key)
    if is_wheel != (result["metadata_observation_id"] is not None):
        raise ValueError("wheel metadata observation binding invalid")
    if (result["artifact_kind"] == "NATIVE_TOOL_ARCHIVE") != (result["checksum_observation_id"] is not None):
        raise ValueError("tool checksum observation binding invalid")
    is_tool = result["artifact_kind"] == "NATIVE_TOOL_ARCHIVE"
    if is_tool != (result["upstream_observation_id"] is not None):
        raise ValueError("tool upstream observation binding invalid")
    if not isinstance(result["license_id"], str) or not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$", result["license_id"]):
        raise ValueError("license_id invalid")
    if not isinstance(result["manual_legal_review_required"], bool) or not isinstance(result["root_reachable"], bool):
        raise ValueError("candidate review or reachability invalid")
    if result["availability"] != "NOT_CONFIRMED":
        raise ValueError("B1a cannot classify retained availability")
    if not isinstance(result["required_tool_kinds"], list):
        raise ValueError("required_tool_kinds invalid")
    if is_tool:
        if result["required_tool_kinds"] != ["FFMPEG", "FFPROBE"] or result["tool_member_mapping_state"] != "UNRESOLVED_UNACQUIRED":
            raise ValueError("native tool pair contract invalid")
        contract = result["tool_release_contract"]
        _expect(contract, {
            "repository_id", "release_id", "release_tag", "asset_id",
            "upstream_ffmpeg_version", "upstream_commit_id",
            "build_configuration_sha256", "checksum_provenance", "state",
        }, "tool_release_contract")
        contract = dict(contract)
        if contract["repository_id"] != "BtbN/FFmpeg-Builds":
            raise ValueError("tool repository identity invalid")
        for key in ("release_id", "release_tag", "asset_id"):
            contract[key] = _text(contract[key], _ID, f"tool {key}")
        contract["upstream_ffmpeg_version"] = _text(
            contract["upstream_ffmpeg_version"], _VERSION, "upstream_ffmpeg_version"
        )
        contract["upstream_commit_id"] = _text(
            contract["upstream_commit_id"], _COMMIT_ID, "upstream_commit_id"
        )
        contract["build_configuration_sha256"] = _sha(
            contract["build_configuration_sha256"], "build_configuration_sha256"
        )
        if (contract["checksum_provenance"] != "PUBLISHER_CONTROLLED_RELEASE_CHECKSUM_UNVERIFIED" or
                contract["state"] != "CALLER_REPORTED_UNVERIFIED"):
            raise ValueError("tool release provenance invalid")
        expected_asset_url = (
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
            f"{contract['release_tag']}/{result['filename']}"
        )
        if result["canonical_url"] != expected_asset_url:
            raise ValueError("tool release asset coordinate invalid")
        result["tool_release_contract"] = contract
    elif (result["required_tool_kinds"] or result["tool_member_mapping_state"] != "NOT_APPLICABLE" or
          result["upstream_observation_id"] is not None or result["tool_release_contract"] is not None):
        raise ValueError("non-tool candidate claims tool mapping")
    return result


def _validate_snapshot(value: Mapping[str, Any], candidate_by_id: Mapping[str, Mapping[str, Any]], observation_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    _expect(value, {"project_id", "source_observation_id", "candidate_ids", "candidate_set_sha256"}, "candidate snapshot")
    result = dict(value)
    result["project_id"] = _text(result["project_id"], _DIST, "snapshot project_id")
    result["source_observation_id"] = _text(result["source_observation_id"], _ID, "source_observation_id")
    observation = observation_by_id.get(result["source_observation_id"])
    if observation is None or observation["project_id"] != result["project_id"]:
        raise ValueError("snapshot observation binding invalid")
    if not isinstance(result["candidate_ids"], list) or not 1 <= len(result["candidate_ids"]) <= _MAX_CANDIDATES:
        raise ValueError("snapshot candidate_ids invalid")
    result["candidate_ids"] = [_text(item, _ID, "snapshot candidate_id") for item in result["candidate_ids"]]
    if result["candidate_ids"] != _ascii_sorted(result["candidate_ids"]) or len(set(result["candidate_ids"])) != len(result["candidate_ids"]):
        raise ValueError("snapshot candidate_ids not canonical")
    candidates = []
    for candidate_id in result["candidate_ids"]:
        candidate = candidate_by_id.get(candidate_id)
        if (candidate is None or candidate["project_id"] != result["project_id"] or
                candidate["index_observation_id"] != result["source_observation_id"] or
                candidate["provider"] != observation["provider"] or
                candidate["index_identity"] != observation["index_identity"]):
            raise ValueError("snapshot candidate binding invalid")
        candidates.append(candidate)
    expected = _digest(_CANDIDATE_SET_DOMAIN, candidates)
    if result["candidate_set_sha256"] != expected:
        raise ValueError("candidate snapshot digest mismatch")
    if observation["candidate_count"] != len(candidates):
        raise ValueError("observation candidate count mismatch")
    return result


def _validate_constraint(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {"constraint_id", "project_id", "requirement", "parent_project_id", "marker_state", "root"}
    _expect(value, fields, "constraint")
    result = dict(value)
    result["constraint_id"] = _text(result["constraint_id"], _ID, "constraint_id")
    result["project_id"] = _text(result["project_id"], _DIST, "constraint project_id")
    result["requirement"] = _text(result["requirement"], _REQUIREMENT, "constraint requirement")
    if result["parent_project_id"] is not None:
        result["parent_project_id"] = _text(result["parent_project_id"], _DIST, "parent_project_id")
    if result["marker_state"] != "ACTIVE":
        raise ValueError("only active constraints belong in closure")
    if not isinstance(result["root"], bool):
        raise ValueError("constraint root invalid")
    if result["root"] != (result["parent_project_id"] is None):
        raise ValueError("constraint root binding invalid")
    return result


def _validate_selection(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {"project_id", "candidate_id", "version_rank", "tag_rank", "filename_rank", "selection_state"}
    _expect(value, fields, "selection")
    result = dict(value)
    result["project_id"] = _text(result["project_id"], _DIST, "selection project_id")
    result["candidate_id"] = _text(result["candidate_id"], _ID, "selection candidate_id")
    result["version_rank"] = _integer(result["version_rank"], 0, _MAX_CANDIDATES - 1, "version_rank")
    result["tag_rank"] = _integer(result["tag_rank"], 0, 4095, "tag_rank")
    result["filename_rank"] = _integer(result["filename_rank"], 0, _MAX_CANDIDATES - 1, "filename_rank")
    if result["selection_state"] != "CALLER_PROPOSED_UNVERIFIED":
        raise ValueError("selection state invalid")
    return result


def _normalize_body(body: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema", "status", "plan_id", "revision", "target", "resolver",
        "request_observations", "candidate_snapshots", "candidates", "constraints",
        "proposed_selections", "native_sox_executable_requirement", "counts",
        "contract_only", "candidate_snapshots_authenticated",
        "deterministic_selection_verified", "active_dependency_closure_verified",
        "plan_review_accepted", "acquisition_eligible",
        "diagnostic_only", "persistent_plan_is_capability",
        "metadata_network_authorized", "artifact_download_authorized",
        "install_authorized", "runtime_reuse_authorized", "model_load_authorized",
        "consumer_execution_authorized", "post_return_state_guaranteed",
        "consumer_revalidation_required", "no_effect_flags",
    }
    _expect(body, fields, "closure plan body")
    result = dict(body)
    if result["schema"] != SCHEMA_ID or result["status"] != "CONTRACT_ONLY_UNRESOLVED":
        raise ValueError("closure plan identity invalid")
    result["plan_id"] = _text(result["plan_id"], _ID, "plan_id")
    result["revision"] = _integer(result["revision"], 1, 2**31 - 1, "revision")
    target = result["target"]
    _expect(target, {"os", "platform", "python_tag", "python_version", "cuda", "attention"}, "target")
    if dict(target) != {
        "os": "WINDOWS", "platform": "win_amd64", "python_tag": "cp312",
        "python_version": "3.12.4", "cuda": "cu130", "attention": "SDPA",
    }:
        raise ValueError("target matrix invalid")
    result["target"] = dict(target)
    result["resolver"] = _validate_resolver(result["resolver"])

    if not isinstance(result["request_observations"], list) or not 1 <= len(result["request_observations"]) <= _MAX_OBSERVATIONS:
        raise ValueError("request observations invalid")
    observations = [_validate_observation(item) for item in result["request_observations"]]
    observations.sort(key=lambda item: (
        item["provider"].encode("ascii"), item["project_id"].encode("ascii"),
        item["canonical_url"].encode("ascii"), item["observation_id"].encode("ascii"),
    ))
    observation_ids = [item["observation_id"] for item in observations]
    if len({item.casefold() for item in observation_ids}) != len(observation_ids):
        raise ValueError("observation id collision")
    result["request_observations"] = observations

    if not isinstance(result["candidates"], list) or not 1 <= len(result["candidates"]) <= _MAX_CANDIDATES:
        raise ValueError("candidates invalid")
    candidates = []
    total_requirements = 0
    total_requirement_bytes = 0
    for item in result["candidates"]:
        normalized_candidate = _validate_candidate(item)
        total_requirements += len(normalized_candidate["requires_dist"])
        total_requirement_bytes += sum(len(row.encode("ascii")) for row in normalized_candidate["requires_dist"])
        if total_requirements > _MAX_TOTAL_REQUIREMENTS or total_requirement_bytes > 4 * 1024**2:
            raise ValueError("aggregate requirement bound exceeded")
        candidates.append(normalized_candidate)
    candidates.sort(key=lambda item: (item["project_id"].encode("ascii"), item["candidate_id"].encode("ascii")))
    candidate_ids = [item["candidate_id"] for item in candidates]
    if len({item.casefold() for item in candidate_ids}) != len(candidate_ids):
        raise ValueError("candidate id collision")
    candidate_by_id = {item["candidate_id"]: item for item in candidates}
    observation_by_id = {item["observation_id"]: item for item in observations}
    for candidate in candidates:
        index_observation = observation_by_id.get(candidate["index_observation_id"])
        expected_index_kind = (
            "PROJECT_INDEX_GET" if candidate["provider"] in {"PYPI", "PYTORCH_INDEX"}
            else "PROJECT_RELEASE_GET"
        )
        if (index_observation is None or index_observation["observation_kind"] != expected_index_kind or
                index_observation["project_id"] != candidate["project_id"] or
                index_observation["provider"] != candidate["provider"] or
                index_observation["index_identity"] != candidate["index_identity"]):
            raise ValueError("candidate index observation binding invalid")
        if candidate["artifact_kind"] == "NATIVE_TOOL_ARCHIVE":
            expected_release_url = (
                "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/"
                + candidate["tool_release_contract"]["release_tag"]
            )
            if index_observation["canonical_url"] != expected_release_url:
                raise ValueError("tool release observation coordinate invalid")
        head_observation = observation_by_id.get(candidate["artifact_head_observation_id"])
        if (head_observation is None or head_observation["observation_kind"] != "ARTIFACT_HEAD" or
                head_observation["project_id"] != candidate["project_id"] or
                head_observation["provider"] != candidate["provider"] or
                head_observation["index_identity"] != candidate["index_identity"] or
                head_observation["canonical_url"] != candidate["canonical_url"] or
                head_observation["declared_bytes"] != candidate["bytes"]):
            raise ValueError("candidate artifact HEAD binding invalid")
        metadata_id = candidate["metadata_observation_id"]
        if metadata_id is not None:
            metadata_observation = observation_by_id.get(metadata_id)
            if (metadata_observation is None or metadata_observation["observation_kind"] != "METADATA_SIDECAR_GET" or
                    metadata_observation["project_id"] != candidate["project_id"] or
                    metadata_observation["provider"] != candidate["provider"] or
                    metadata_observation["index_identity"] != candidate["index_identity"] or
                    metadata_observation["response_sha256"] != candidate["metadata_sha256"] or
                    metadata_observation["observed_bytes"] != candidate["metadata_bytes"]):
                raise ValueError("candidate metadata observation binding invalid")
        checksum_id = candidate["checksum_observation_id"]
        if checksum_id is not None:
            checksum_observation = observation_by_id.get(checksum_id)
            if (checksum_observation is None or checksum_observation["observation_kind"] != "CHECKSUM_ASSET_GET" or
                    checksum_observation["project_id"] != candidate["project_id"] or
                    checksum_observation["provider"] != candidate["provider"] or
                    checksum_observation["index_identity"] != candidate["index_identity"] or
                    checksum_observation["asserted_artifact_sha256"] != candidate["sha256"]):
                raise ValueError("candidate checksum observation binding invalid")
            checksum_prefix = (
                "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
                + candidate["tool_release_contract"]["release_tag"] + "/"
            )
            if not checksum_observation["canonical_url"].startswith(checksum_prefix):
                raise ValueError("tool checksum coordinate invalid")
        upstream_id = candidate["upstream_observation_id"]
        if upstream_id is not None:
            upstream_observation = observation_by_id.get(upstream_id)
            if (upstream_observation is None or
                    upstream_observation["observation_kind"] != "UPSTREAM_REFERENCE_GET" or
                    upstream_observation["project_id"] != "ffmpeg" or
                    upstream_observation["provider"] != "FFMPEG_ORG"):
                raise ValueError("candidate upstream observation binding invalid")
    referenced_observation_ids = {
        observation_id
        for candidate in candidates
        for observation_id in (
            candidate["index_observation_id"], candidate["metadata_observation_id"],
            candidate["artifact_head_observation_id"], candidate["checksum_observation_id"],
            candidate["upstream_observation_id"],
        )
        if observation_id is not None
    }
    if referenced_observation_ids != set(observation_ids):
        raise ValueError("request observation reference closure invalid")
    result["candidates"] = candidates

    if not isinstance(result["candidate_snapshots"], list) or not 1 <= len(result["candidate_snapshots"]) <= _MAX_PROJECTS:
        raise ValueError("candidate snapshots invalid")
    snapshots = []
    total_snapshot_ids = 0
    for item in result["candidate_snapshots"]:
        snapshot = _validate_snapshot(item, candidate_by_id, observation_by_id)
        total_snapshot_ids += len(snapshot["candidate_ids"])
        if total_snapshot_ids > _MAX_CANDIDATES:
            raise ValueError("aggregate snapshot id bound exceeded")
        snapshots.append(snapshot)
    snapshots.sort(key=lambda item: item["project_id"].encode("ascii"))
    snapshot_projects = [item["project_id"] for item in snapshots]
    if len(set(snapshot_projects)) != len(snapshot_projects) or set(snapshot_projects) != {item["project_id"] for item in candidates}:
        raise ValueError("candidate snapshot project closure invalid")
    snapshot_candidate_ids = [candidate_id for item in snapshots for candidate_id in item["candidate_ids"]]
    if (len(set(snapshot_candidate_ids)) != len(snapshot_candidate_ids) or
            set(snapshot_candidate_ids) != set(candidate_ids)):
        raise ValueError("candidate snapshot union mismatch")
    candidate_observation_ids = {item["source_observation_id"] for item in snapshots}
    positive_observation_ids = {item["observation_id"] for item in observations if item["candidate_count"] > 0}
    if candidate_observation_ids != positive_observation_ids:
        raise ValueError("candidate-bearing observation closure mismatch")
    result["candidate_snapshots"] = snapshots

    if not isinstance(result["constraints"], list) or not 1 <= len(result["constraints"]) <= _MAX_REQUIREMENTS:
        raise ValueError("constraints invalid")
    constraints = [_validate_constraint(item) for item in result["constraints"]]
    constraints.sort(key=lambda item: (item["project_id"].encode("ascii"), item["constraint_id"].encode("ascii")))
    constraint_ids = [item["constraint_id"] for item in constraints]
    if len({item.casefold() for item in constraint_ids}) != len(constraint_ids):
        raise ValueError("constraint id collision")
    if any(item["project_id"] not in snapshot_projects for item in constraints):
        raise ValueError("constraint project missing")
    result["constraints"] = constraints

    if not isinstance(result["proposed_selections"], list) or len(result["proposed_selections"]) != len(snapshot_projects):
        raise ValueError("proposed_selections invalid")
    selections = [_validate_selection(item) for item in result["proposed_selections"]]
    selections.sort(key=lambda item: item["project_id"].encode("ascii"))
    if [item["project_id"] for item in selections] != snapshot_projects:
        raise ValueError("selection project closure invalid")
    for selection in selections:
        candidate = candidate_by_id.get(selection["candidate_id"])
        if candidate is None or candidate["project_id"] != selection["project_id"]:
            raise ValueError("selection candidate binding invalid")
        snapshot = next(item for item in snapshots if item["project_id"] == selection["project_id"])
        if selection["candidate_id"] not in snapshot["candidate_ids"]:
            raise ValueError("selection candidate is outside project snapshot")
        if selection["version_rank"] != 0 or selection["tag_rank"] != 0 or selection["filename_rank"] != 0:
            raise ValueError("provisional contract only accepts first-ranked selections")
    result["proposed_selections"] = selections

    if result["native_sox_executable_requirement"] != "UNKNOWN":
        raise ValueError("Stage A cannot resolve native SoX executable requirement")
    counts = result["counts"]
    _expect(counts, {"observation_count", "project_count", "candidate_count", "constraint_count", "proposed_selection_count"}, "counts")
    expected_counts = {
        "observation_count": len(observations), "project_count": len(snapshots),
        "candidate_count": len(candidates), "constraint_count": len(constraints),
        "proposed_selection_count": len(selections),
    }
    if dict(counts) != expected_counts:
        raise ValueError("counts mismatch")
    result["counts"] = expected_counts

    authority = {
        "contract_only": True, "candidate_snapshots_authenticated": False,
        "deterministic_selection_verified": False,
        "active_dependency_closure_verified": False,
        "plan_review_accepted": False, "acquisition_eligible": False,
        "diagnostic_only": True, "persistent_plan_is_capability": False,
        "metadata_network_authorized": False, "artifact_download_authorized": False,
        "install_authorized": False, "runtime_reuse_authorized": False,
        "model_load_authorized": False, "consumer_execution_authorized": False,
        "post_return_state_guaranteed": False, "consumer_revalidation_required": True,
    }
    if any(result[key] != expected for key, expected in authority.items()):
        raise ValueError("closure plan authority boundary invalid")
    flags = result["no_effect_flags"]
    _expect(flags, set(_NO_EFFECT_FIELDS), "no_effect_flags")
    if any(flags[key] is not False for key in _NO_EFFECT_FIELDS):
        raise ValueError("closure plan claims prohibited effect")
    result["no_effect_flags"] = dict(flags)
    if len(canonical_json_bytes(result)) > _MAX_PLAN_BYTES:
        raise ValueError("closure plan canonical body exceeds bound")
    return result


def _semantic_projection(body: Mapping[str, Any]) -> dict[str, Any]:
    projected = dict(body)
    observations = projected.pop("request_observations")
    projected["observation_semantic_inputs"] = [
        {
            "observation_id": item["observation_id"], "source": item["source"],
            "provider": item["provider"], "project_id": item["project_id"],
            "index_identity": item["index_identity"], "observer_id": item["observer_id"],
            "observer_revision": item["observer_revision"], "observer_sha256": item["observer_sha256"],
            "observation_kind": item["observation_kind"], "canonical_url": item["canonical_url"],
            "method": item["method"], "status": item["status"], "content_type": item["content_type"],
            "declared_bytes": item["declared_bytes"],
            "observed_bytes": item["observed_bytes"], "final_host_class": item["final_host_class"],
            "safe_content_path_sha256": item["safe_content_path_sha256"],
            "response_sha256": item["response_sha256"], "candidate_count": item["candidate_count"],
            "asserted_artifact_sha256": item["asserted_artifact_sha256"],
            "transport_policy_passed": item["transport_policy_passed"],
        }
        for item in observations
    ]
    return projected


def candidate_set_sha256(candidates: list[Mapping[str, Any]]) -> str:
    """Return the domain-separated digest used by candidate snapshots."""
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= _MAX_CANDIDATES:
        raise ValueError("candidates invalid")
    normalized = []
    total_requirements = 0
    total_requirement_bytes = 0
    for item in candidates:
        candidate = _validate_candidate(item)
        total_requirements += len(candidate["requires_dist"])
        total_requirement_bytes += sum(len(row.encode("ascii")) for row in candidate["requires_dist"])
        if total_requirements > _MAX_TOTAL_REQUIREMENTS or total_requirement_bytes > 4 * 1024**2:
            raise ValueError("aggregate requirement bound exceeded")
        normalized.append(candidate)
    normalized.sort(key=lambda item: (item["project_id"].encode("ascii"), item["candidate_id"].encode("ascii")))
    projects = {item["project_id"] for item in normalized}
    if len(projects) != 1:
        raise ValueError("candidate set crosses projects")
    if len(canonical_json_bytes(normalized)) > _MAX_PLAN_BYTES:
        raise ValueError("candidate set canonical body exceeds bound")
    return _digest(_CANDIDATE_SET_DOMAIN, normalized)


@dataclass(frozen=True, slots=True, init=False)
class RuntimeArtifactClosurePlan:
    _value: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._value)


def _new(value: Mapping[str, Any]) -> RuntimeArtifactClosurePlan:
    plan = object.__new__(RuntimeArtifactClosurePlan)
    object.__setattr__(plan, "_value", _freeze(value))
    return plan


def compile_runtime_artifact_closure_plan(body: Mapping[str, Any]) -> RuntimeArtifactClosurePlan:
    if not isinstance(body, Mapping) or {"semantic_plan_sha256", "observation_receipt_sha256"} & set(body):
        raise ValueError("closure plan body invalid")
    normalized = _normalize_body(body)
    normalized["semantic_plan_sha256"] = _digest(_SEMANTIC_DOMAIN, _semantic_projection(normalized))
    normalized["observation_receipt_sha256"] = _digest(
        _OBSERVATION_DOMAIN, normalized["request_observations"]
    )
    return _new(_validate_document(normalized))


def _validate_document(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("closure plan invalid")
    expected = {
        "schema", "status", "plan_id", "revision", "target", "resolver",
        "request_observations", "candidate_snapshots", "candidates", "constraints",
        "proposed_selections", "native_sox_executable_requirement", "counts",
        "contract_only", "candidate_snapshots_authenticated",
        "deterministic_selection_verified", "active_dependency_closure_verified",
        "plan_review_accepted", "acquisition_eligible",
        "diagnostic_only", "persistent_plan_is_capability", "metadata_network_authorized",
        "artifact_download_authorized", "install_authorized", "runtime_reuse_authorized",
        "model_load_authorized", "consumer_execution_authorized",
        "post_return_state_guaranteed", "consumer_revalidation_required",
        "no_effect_flags", "semantic_plan_sha256", "observation_receipt_sha256",
    }
    _expect(value, expected, "closure plan")
    body = {key: value[key] for key in value if key not in {"semantic_plan_sha256", "observation_receipt_sha256"}}
    normalized = _normalize_body(body)
    if list(value["request_observations"]) != normalized["request_observations"]:
        raise ValueError("observation order is not canonical")
    if list(value["candidates"]) != normalized["candidates"] or list(value["candidate_snapshots"]) != normalized["candidate_snapshots"]:
        raise ValueError("candidate order is not canonical")
    if (list(value["constraints"]) != normalized["constraints"] or
            list(value["proposed_selections"]) != normalized["proposed_selections"]):
        raise ValueError("closure order is not canonical")
    semantic = _sha(value["semantic_plan_sha256"], "semantic_plan_sha256")
    observation = _sha(value["observation_receipt_sha256"], "observation_receipt_sha256")
    if semantic != _digest(_SEMANTIC_DOMAIN, _semantic_projection(normalized)):
        raise ValueError("semantic plan digest mismatch")
    if observation != _digest(_OBSERVATION_DOMAIN, normalized["request_observations"]):
        raise ValueError("observation receipt digest mismatch")
    return {**normalized, "semantic_plan_sha256": semantic, "observation_receipt_sha256": observation}


def parse_runtime_artifact_closure_plan(value: Mapping[str, Any]) -> RuntimeArtifactClosurePlan:
    return _new(_validate_document(value))


def assert_no_effect_surface() -> None:
    forbidden = {"download", "request", "open", "write", "install", "execute", "launch", "load_model"}
    public = {name for name, item in globals().items() if callable(item) and not name.startswith("_")}
    if public & forbidden:
        raise AssertionError("forbidden effect surface exposed")


__all__ = [
    "RuntimeArtifactClosurePlan", "SCHEMA_ID", "assert_no_effect_surface",
    "candidate_set_sha256", "compile_runtime_artifact_closure_plan",
    "parse_runtime_artifact_closure_plan",
]
