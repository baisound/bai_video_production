from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.qwen3_tts_runtime_artifact_manifest import (
    MARKER_ENVIRONMENT_SHA256,
    RuntimeArtifactManifest,
    SCHEMA_ID,
    assert_no_effect_surface,
    compile_runtime_artifact_manifest,
    parse_runtime_artifact_manifest,
    runtime_file_mapping_sha256,
)


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "qwen3-tts-runtime-artifact-manifest.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "qwen3-tts-runtime-artifact-manifest.schema.json"
SHA = "sha256:" + "1" * 64


def artifact(artifact_id: str, filename: str, *, kind: str = "DISTRIBUTION_WHEEL", policy: str = "REQUIRED_RUNTIME") -> dict:
    if kind == "PYTHON_RUNTIME_ARCHIVE":
        provider, url, provenance = "PYTHON_ORG", f"https://www.python.org/ftp/python/{filename}", "OFFICIAL_RELEASE_DIGEST"
    elif kind == "NATIVE_TOOL_ARCHIVE":
        provider, url, provenance = "OFFICIAL_PROJECT_RELEASE", f"https://github.com/example/project/releases/download/v1/{filename}", "OFFICIAL_RELEASE_DIGEST"
    else:
        provider, url, provenance = "PYPI", f"https://files.pythonhosted.org/packages/{filename}", "OFFICIAL_INDEX_DIGEST"
    return {
        "artifact_id": artifact_id,
        "kind": kind,
        "provider": provider,
        "source_url": url,
        "filename": filename,
        "bytes": 100,
        "sha256": SHA,
        "provenance": provenance,
        "wheel_tags": (["py3-none-any"] if filename.endswith("-py3-none-any.whl") else ["cp312-cp312-win_amd64"]) if kind == "DISTRIBUTION_WHEEL" else [],
        "load_policy": policy,
        "local_build_binding": None,
        "source_contract": None,
    }


def distribution(name: str, artifact_id: str, dependencies: list[dict] | None = None) -> dict:
    return {
        "distribution_id": name,
        "version": "1.0.0",
        "artifact_id": artifact_id,
        "dist_info_dir": f"Lib/site-packages/{name.replace('-', '_')}-1.0.0.dist-info",
        "record_sha256": SHA,
        "payload_inventory_sha256": SHA,
        "dependencies": dependencies or [],
    }


def body() -> dict:
    artifacts = [
        artifact("python-runtime", "python-3.12.4.zip", kind="PYTHON_RUNTIME_ARCHIVE"),
        artifact("qwen-wheel", "qwen_tts-0.1.1-py3-none-any.whl"),
        artifact("transformers-wheel", "transformers-4.57.3-py3-none-any.whl"),
        artifact("ffmpeg-archive", "ffmpeg.zip", kind="NATIVE_TOOL_ARCHIVE", policy="REQUIRED_TOOL"),
    ]
    artifacts[1].update({
        "bytes": 113_529,
        "sha256": "sha256:11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d",
        "source_contract": {
            "contract_id": "task014-qwen-tts-0.1.1-wheel-payload",
            "schema": "bai.task014.qwen-tts-locked-wheel-session-observation.v1",
            "semantic_sha256": "sha256:0a0568dfbbf716135c911322c22dc44df1e279dfd52ab25de9a4edb6a8a11dd6",
            "role": "QWEN_TTS_WHEEL_PAYLOAD",
        },
    })
    distributions = [
        distribution("qwen-tts", "qwen-wheel", [{"requirement_id": "qwen-transformers", "distribution_id": "transformers", "requirement": "transformers == 4.57.3", "marker_expression": None, "marker_environment_sha256": MARKER_ENVIRONMENT_SHA256, "marker_state": "ACTIVE"}]),
        distribution("transformers", "transformers-wheel"),
    ]
    distributions[0].update({"version": "0.1.1", "dist_info_dir": "Lib/site-packages/qwen_tts-0.1.1.dist-info"})
    distributions[1].update({"version": "4.57.3", "dist_info_dir": "Lib/site-packages/transformers-4.57.3.dist-info"})
    runtime_files = [
        {"logical_path": "Scripts/python.exe", "artifact_member_path": "python.exe", "role": "PYTHON_EXECUTABLE", "owner_kind": "ARTIFACT", "owner_id": "python-runtime", "bytes": 10, "sha256": SHA},
        {"logical_path": "Lib/site-packages/qwen_tts/__init__.py", "artifact_member_path": "qwen_tts/__init__.py", "role": "DISTRIBUTION_PAYLOAD", "owner_kind": "ARTIFACT", "owner_id": "qwen-wheel", "bytes": 10, "sha256": SHA},
        {"logical_path": "Lib/site-packages/transformers/__init__.py", "artifact_member_path": "transformers/__init__.py", "role": "DISTRIBUTION_PAYLOAD", "owner_kind": "ARTIFACT", "owner_id": "transformers-wheel", "bytes": 10, "sha256": SHA},
        {"logical_path": "tools/ffmpeg.exe", "artifact_member_path": "bin/ffmpeg.exe", "role": "TOOL_EXECUTABLE", "owner_kind": "ARTIFACT", "owner_id": "ffmpeg-archive", "bytes": 10, "sha256": SHA},
        {"logical_path": "tools/ffprobe.exe", "artifact_member_path": "bin/ffprobe.exe", "role": "TOOL_EXECUTABLE", "owner_kind": "ARTIFACT", "owner_id": "ffmpeg-archive", "bytes": 10, "sha256": SHA},
        {"logical_path": "system/nvcuda.dll", "artifact_member_path": None, "role": "NATIVE_LIBRARY", "owner_kind": "SYSTEM_PREREQUISITE", "owner_id": "nvidia-driver", "bytes": 10, "sha256": SHA},
    ]
    for item in runtime_files:
        item["mapping_sha256"] = runtime_file_mapping_sha256(item)
    flags = {name: False for name in (
        "filesystem_read", "filesystem_write", "network_accessed", "package_resolved",
        "package_downloaded", "package_installed", "target_python_executed",
        "target_package_imported", "model_loaded", "owner_audio_read",
        "inference_started", "native_tool_executed",
    )}
    return {
        "schema": SCHEMA_ID,
        "status": "CONTRACT_ONLY_UNACCEPTED",
        "manifest_id": "task014-runtime-r0",
        "revision": 1,
        "platform": {"os": "WINDOWS", "architecture": "win_amd64", "python_abi": "cp312", "python_version": "3.12.4"},
        "artifacts": artifacts,
        "distributions": distributions,
        "root_distribution_ids": ["qwen-tts"],
        "runtime_files": runtime_files,
        "system_exclusions": [{"exclusion_id": "nvidia-driver", "name": "nvcuda.dll", "reason": "HARDWARE_DRIVER", "required_at_load_only": True}],
        "tools": [
            {"tool_id": "ffmpeg", "kind": "FFMPEG", "artifact_id": "ffmpeg-archive", "logical_path": "tools/ffmpeg.exe"},
            {"tool_id": "ffprobe", "kind": "FFPROBE", "artifact_id": "ffmpeg-archive", "logical_path": "tools/ffprobe.exe"},
        ],
        "counts": {"artifact_count": 4, "distribution_count": 2, "runtime_file_count": 6, "system_exclusion_count": 1, "tool_count": 2, "total_artifact_bytes": 113_829},
        "diagnostic_only": True,
        "persistent_manifest_is_capability": False,
        "runtime_reuse_authorized": False,
        "model_load_authorized": False,
        "consumer_execution_authorized": False,
        "post_return_state_guaranteed": False,
        "consumer_revalidation_required": True,
        "no_effect_flags": flags,
    }


def compiled(value: dict | None = None) -> dict:
    return compile_runtime_artifact_manifest(value or body()).to_dict()


def test_round_trip_is_deterministic_and_schema_valid() -> None:
    first = compiled()
    second = compiled()
    assert first == second
    assert parse_runtime_artifact_manifest(first).to_dict() == first
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(first)
    assert first["status"] == "CONTRACT_ONLY_UNACCEPTED"
    assert first["diagnostic_only"] is True
    assert first["runtime_reuse_authorized"] is False


def test_schema_mirror_is_byte_exact() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()


@pytest.mark.parametrize("mutation", ["missing", "orphan", "cycle", "inactive"])
def test_dependency_graph_is_complete_acyclic_and_active(mutation: str) -> None:
    value = body()
    if mutation == "missing":
        value["distributions"][0]["dependencies"][0]["distribution_id"] = "missing"
    elif mutation == "orphan":
        value["root_distribution_ids"] = ["transformers"]
    elif mutation == "cycle":
        value["distributions"][1]["dependencies"] = [{"requirement_id": "transformers-qwen", "distribution_id": "qwen-tts", "requirement": "qwen-tts==0.1.1", "marker_expression": None, "marker_environment_sha256": MARKER_ENVIRONMENT_SHA256, "marker_state": "ACTIVE"}]
    else:
        value["distributions"][0]["dependencies"][0]["marker_state"] = "INACTIVE"
        value["distributions"][0]["dependencies"][0]["requirement"] = "transformers==4.57.3;python_version<'0'"
        value["distributions"][0]["dependencies"][0]["marker_expression"] = "python_version<'0'"
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_inactive_marker_may_name_an_uninstalled_optional_distribution() -> None:
    value = body()
    value["distributions"][0]["dependencies"][0]["marker_state"] = "INACTIVE"
    value["distributions"][0]["dependencies"][0]["requirement"] = "transformers==4.57.3;python_version<'0'"
    value["distributions"][0]["dependencies"][0]["marker_expression"] = "python_version<'0'"
    value["distributions"] = value["distributions"][:1]
    value["artifacts"] = [item for item in value["artifacts"] if item["artifact_id"] != "transformers-wheel"]
    value["runtime_files"] = [item for item in value["runtime_files"] if item["owner_id"] != "transformers-wheel"]
    value["counts"].update({"artifact_count": 3, "distribution_count": 1, "runtime_file_count": 5, "total_artifact_bytes": 113_729})
    assert compiled(value)["distributions"][0]["dependencies"][0]["marker_state"] == "INACTIVE"


@pytest.mark.parametrize("field,value", [
    ("runtime_reuse_authorized", True),
    ("model_load_authorized", True),
    ("consumer_execution_authorized", True),
    ("post_return_state_guaranteed", True),
    ("consumer_revalidation_required", False),
])
def test_authority_escalation_is_rejected(field: str, value: bool) -> None:
    candidate = compiled()
    candidate[field] = value
    with pytest.raises(ValueError):
        parse_runtime_artifact_manifest(candidate)
    assert list(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(candidate))


def test_digest_unknown_key_and_effect_tamper_are_rejected() -> None:
    candidate = compiled()
    candidate["manifest_id"] = "changed"
    with pytest.raises(ValueError, match="digest"):
        parse_runtime_artifact_manifest(candidate)
    candidate = compiled()
    candidate["extra"] = False
    with pytest.raises(ValueError):
        parse_runtime_artifact_manifest(candidate)


def test_direct_construction_and_mutable_alias_bypass_are_closed() -> None:
    with pytest.raises(TypeError):
        RuntimeArtifactManifest({})  # type: ignore[call-arg]
    source = body()
    manifest = compile_runtime_artifact_manifest(source)
    source["artifacts"][0]["filename"] = "changed.zip"
    projection = manifest.to_dict()
    projection["artifacts"][0]["filename"] = "also-changed.zip"
    assert manifest.to_dict()["artifacts"][0]["filename"] == "python-3.12.4.zip"
    candidate = compiled()
    candidate["no_effect_flags"]["network_accessed"] = True
    with pytest.raises(ValueError):
        parse_runtime_artifact_manifest(candidate)


@pytest.mark.parametrize("path", ["../python.exe", "/python.exe", "C:/python.exe", "Lib\\python.exe", "Lib//python.exe", "Lib/../python.exe"])
def test_unsafe_runtime_paths_are_rejected(path: str) -> None:
    value = body()
    value["runtime_files"][0]["logical_path"] = path
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_casefold_path_collision_owner_and_count_mismatch_are_rejected() -> None:
    value = body()
    duplicate = deepcopy(value["runtime_files"][0])
    duplicate["logical_path"] = "scripts/PYTHON.EXE"
    duplicate["mapping_sha256"] = runtime_file_mapping_sha256(duplicate)
    value["runtime_files"].append(duplicate)
    value["counts"]["runtime_file_count"] += 1
    with pytest.raises(ValueError, match="collision"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["runtime_files"][0]["owner_id"] = "missing"
    value["runtime_files"][0]["mapping_sha256"] = runtime_file_mapping_sha256(value["runtime_files"][0])
    with pytest.raises(ValueError, match="owner"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["counts"]["artifact_count"] = 5
    with pytest.raises(ValueError, match="counts"):
        compile_runtime_artifact_manifest(value)


def test_tool_mapping_and_url_are_fail_closed() -> None:
    value = body()
    value["tools"][0]["logical_path"] = "Scripts/python.exe"
    with pytest.raises(ValueError, match="tool runtime"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["artifacts"][0]["source_url"] = "https://user@example.com/python.zip?token=x"
    with pytest.raises(ValueError, match="source_url"):
        compile_runtime_artifact_manifest(value)
    candidate = compiled()
    candidate["artifacts"][0]["source_url"] = "https://user@example.com/python.zip"
    assert list(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(candidate))


def test_complete_artifact_tool_and_system_ownership_is_required() -> None:
    value = body()
    value["tools"] = value["tools"][:1]
    value["counts"]["tool_count"] = 1
    with pytest.raises(ValueError, match="tool pair"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["system_exclusions"].append({"exclusion_id": "unused-os", "name": "kernel32.dll", "reason": "HOST_OS", "required_at_load_only": True})
    value["counts"]["system_exclusion_count"] = 2
    with pytest.raises(ValueError, match="unused system"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["artifacts"].append(artifact("orphan-wheel", "orphan-1.0-py3-none-any.whl"))
    value["counts"]["artifact_count"] = 5
    value["counts"]["total_artifact_bytes"] = 113_929
    with pytest.raises(ValueError, match="unbound"):
        compile_runtime_artifact_manifest(value)


@pytest.mark.parametrize("mutation", ["system-python", "tool-python", "dist-tool", "member-missing", "mapping-tamper", "split-tools"])
def test_runtime_member_role_and_tool_pair_matrix_is_closed(mutation: str) -> None:
    value = body()
    target = value["runtime_files"][0]
    if mutation == "system-python":
        target.update({"owner_kind": "SYSTEM_PREREQUISITE", "owner_id": "nvidia-driver", "artifact_member_path": None})
    elif mutation == "tool-python":
        target["owner_id"] = "ffmpeg-archive"
    elif mutation == "dist-tool":
        value["runtime_files"][3]["owner_id"] = "qwen-wheel"
        value["runtime_files"][3]["mapping_sha256"] = runtime_file_mapping_sha256(value["runtime_files"][3])
    elif mutation == "member-missing":
        target["artifact_member_path"] = None
    elif mutation == "mapping-tamper":
        target["mapping_sha256"] = SHA
    else:
        value["artifacts"].append(artifact("ffprobe-archive", "ffprobe.zip", kind="NATIVE_TOOL_ARCHIVE", policy="REQUIRED_TOOL"))
        value["runtime_files"][4]["owner_id"] = "ffprobe-archive"
        value["runtime_files"][4]["mapping_sha256"] = runtime_file_mapping_sha256(value["runtime_files"][4])
        value["tools"][1]["artifact_id"] = "ffprobe-archive"
        value["counts"].update({"artifact_count": 5, "total_artifact_bytes": 113_929})
    if mutation not in {"dist-tool", "mapping-tamper", "split-tools"}:
        target["mapping_sha256"] = runtime_file_mapping_sha256(target)
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


@pytest.mark.parametrize("mutation", ["wrong-host", "wrong-tag", "filename-tag", "wrong-kind-policy", "local-without-attestation"])
def test_artifact_origin_platform_and_policy_matrix_is_closed(mutation: str) -> None:
    value = body()
    target = value["artifacts"][2]
    if mutation == "wrong-host":
        target["source_url"] = "https://localhost/private.whl"
    elif mutation == "wrong-tag":
        target["wheel_tags"] = ["cp312-cp312-linux_x86_64"]
    elif mutation == "filename-tag":
        target["wheel_tags"] = ["cp312-cp312-win_amd64"]
    elif mutation == "wrong-kind-policy":
        value["artifacts"][0]["load_policy"] = "REQUIRED_TOOL"
    else:
        target["kind"] = "LOCAL_BUILD_WHEEL"
        target["provider"] = "OWNER_ACCEPTED_LOCAL_BUILD"
        target["source_url"] = "https://github.com/example/project/archive/source.zip"
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_requirement_name_marker_and_multiple_rows_are_bound() -> None:
    value = body()
    value["distributions"][0]["dependencies"][0]["requirement"] = "torch==9"
    with pytest.raises(ValueError, match="requirement name"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["distributions"][0]["dependencies"][0]["marker_expression"] = "python_version<'3.9'"
    with pytest.raises(ValueError, match="marker mismatch"):
        compile_runtime_artifact_manifest(value)
    value = body()
    extra = deepcopy(value["distributions"][0]["dependencies"][0])
    extra.update({"requirement_id": "qwen-transformers-old-python", "requirement": "transformers==4.57.3;python_version<'3.9'", "marker_expression": "python_version<'3.9'", "marker_state": "INACTIVE"})
    value["distributions"][0]["dependencies"].append(extra)
    assert len(compiled(value)["distributions"][0]["dependencies"]) == 2


@pytest.mark.parametrize("requirement", ["transformers===", "transformers!", "transformers=>4", "transformers[bar]==4.57.3", "transformers[,,]==1", "transformers>=4.*", "transformers~=4", "transformers>=4.0+local"])
def test_malformed_pep508_requirement_subset_is_rejected(requirement: str) -> None:
    value = body()
    value["distributions"][0]["dependencies"][0]["requirement"] = requirement
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_inactive_marker_cannot_bypass_common_specifier_validation() -> None:
    value = body()
    dependency = value["distributions"][0]["dependencies"][0]
    dependency.update({
        "requirement": "transformers~=4;python_version<'0'",
        "marker_expression": "python_version<'0'",
        "marker_state": "INACTIVE",
    })
    with pytest.raises(ValueError, match="compatible-release"):
        compile_runtime_artifact_manifest(value)


def test_wheel_distribution_identity_and_active_version_are_bound() -> None:
    value = body()
    value["distributions"][1]["version"] = "9.9.9"
    with pytest.raises(ValueError, match="distribution wheel identity"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["distributions"][0]["dependencies"][0]["requirement"] = "transformers>=9"
    with pytest.raises(ValueError, match="active dependency version"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["distributions"][1]["dist_info_dir"] = "other/transformers-4.57.3.dist-info"
    with pytest.raises(ValueError, match="distribution wheel identity"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["artifacts"][2]["filename"] = "transformers-4.57.3rc1-py3-none-any.whl"
    value["distributions"][1].update({"version": "4.57.3rc1", "dist_info_dir": "Lib/site-packages/transformers-4.57.3rc1.dist-info"})
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


@pytest.mark.parametrize("path", ["NUL", "COM1.txt", "CONIN$", "CONOUT$.txt", "CLOCK$", "Lib/a?.dll", "Lib/a<.dll", "Lib/a|.dll"])
def test_windows_reserved_and_forbidden_paths_are_rejected(path: str) -> None:
    value = body()
    value["runtime_files"][0]["logical_path"] = path
    value["runtime_files"][0]["mapping_sha256"] = runtime_file_mapping_sha256(value["runtime_files"][0])
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_qwen_external_contract_identity_is_exact() -> None:
    value = body()
    value["artifacts"][1]["source_contract"]["schema"] = "bogus"
    with pytest.raises(ValueError, match="qwen source contract"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["artifacts"][1].update({
        "provider": "OFFICIAL_PROJECT_RELEASE",
        "provenance": "OFFICIAL_RELEASE_DIGEST",
        "source_url": "https://github.com/example/project/releases/download/v1/qwen_tts-0.1.1-py3-none-any.whl",
    })
    with pytest.raises(ValueError, match="qwen source contract"):
        compile_runtime_artifact_manifest(value)
    value = body()
    value["artifacts"][1]["source_contract"]["semantic_sha256"] = SHA
    with pytest.raises(ValueError, match="qwen source contract"):
        compile_runtime_artifact_manifest(value)

    candidate = compiled()
    candidate["artifacts"][1]["source_contract"]["schema"] = "bogus"
    assert list(Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).iter_errors(candidate))


def test_marker_environment_and_evaluated_state_are_reproducible() -> None:
    value = body()
    dependency = value["distributions"][0]["dependencies"][0]
    dependency.update({
        "requirement": "transformers >= 4.57.3; python_version >= '3.12' and sys_platform == 'win32'",
        "marker_expression": "python_version >= '3.12' and sys_platform == 'win32'",
    })
    accepted = compiled(value)
    assert accepted["distributions"][0]["dependencies"][0]["marker_state"] == "ACTIVE"
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(accepted)

    dependency["marker_environment_sha256"] = SHA
    with pytest.raises(ValueError, match="marker environment"):
        compile_runtime_artifact_manifest(value)
    dependency["marker_environment_sha256"] = MARKER_ENVIRONMENT_SHA256
    dependency["marker_state"] = "INACTIVE"
    with pytest.raises(ValueError, match="marker state"):
        compile_runtime_artifact_manifest(value)

    value = body()
    dependency = value["distributions"][0]["dependencies"][0]
    dependency.update({
        "requirement": "transformers==4.57.3;sys_platform!='WIN32'",
        "marker_expression": "sys_platform!='WIN32'",
        "marker_state": "ACTIVE",
    })
    assert compiled(value)["distributions"][0]["dependencies"][0]["marker_state"] == "ACTIVE"

    value = body()
    dependency = value["distributions"][0]["dependencies"][0]
    dependency.update({
        "requirement": "transformers==4.57.3;python_version!='3.12rc1'",
        "marker_expression": "python_version!='3.12rc1'",
        "marker_state": "ACTIVE",
    })
    with pytest.raises(ValueError, match="version comparison unsupported"):
        compile_runtime_artifact_manifest(value)

    value = body()
    dependency = value["distributions"][0]["dependencies"][0]
    dependency.update({
        "requirement": "transformers==4.57.3;python_version=='3.12.0'",
        "marker_expression": "python_version=='3.12.0'",
        "marker_state": "ACTIVE",
    })
    assert compiled(value)["distributions"][0]["dependencies"][0]["marker_state"] == "ACTIVE"


def test_wheel_tag_set_matches_filename_exactly() -> None:
    value = body()
    value["artifacts"][2]["wheel_tags"].append("cp312-cp312-win_amd64")
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_public_release_specifier_ignores_candidate_local_label() -> None:
    value = body()
    value["artifacts"][2]["filename"] = "transformers-4.57.3+local-py3-none-any.whl"
    value["artifacts"][2]["source_url"] = "https://files.pythonhosted.org/packages/transformers-4.57.3+local-py3-none-any.whl"
    value["distributions"][1].update({
        "version": "4.57.3+local",
        "dist_info_dir": "Lib/site-packages/transformers-4.57.3+local.dist-info",
    })
    value["distributions"][0]["dependencies"][0]["requirement"] = "transformers!=4.57.3"
    with pytest.raises(ValueError, match="active dependency version"):
        compile_runtime_artifact_manifest(value)


@pytest.mark.parametrize("candidate,requirement", [
    ("4.57.3+01", "transformers!=4.57.3+1"),
    ("4.0+local", "transformers!=4.0.*"),
])
def test_local_and_wildcard_version_normalization_cannot_exclude_dependency(candidate: str, requirement: str) -> None:
    value = body()
    value["artifacts"][2]["filename"] = f"transformers-{candidate}-py3-none-any.whl"
    value["artifacts"][2]["source_url"] = f"https://files.pythonhosted.org/packages/transformers-{candidate}-py3-none-any.whl"
    value["distributions"][1].update({
        "version": candidate,
        "dist_info_dir": f"Lib/site-packages/transformers-{candidate}.dist-info",
    })
    value["distributions"][0]["dependencies"][0]["requirement"] = requirement
    with pytest.raises(ValueError, match="active dependency version"):
        compile_runtime_artifact_manifest(value)


def test_schema_rejects_windows_reserved_path_and_explicit_https_port() -> None:
    schema = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    candidate = compiled()
    candidate["runtime_files"][0]["logical_path"] = "COM1.txt"
    assert list(schema.iter_errors(candidate))
    candidate = compiled()
    candidate["artifacts"][0]["source_url"] = "https://www.python.org:443/python.zip"
    assert list(schema.iter_errors(candidate))


def test_local_build_requires_exact_attestation_and_same_machine() -> None:
    value = body()
    target = value["artifacts"][2]
    target.update({
        "kind": "LOCAL_BUILD_WHEEL",
        "provider": "OWNER_ACCEPTED_LOCAL_BUILD",
        "provenance": "LOCAL_BUILD_ATTESTATION",
        "local_build_binding": {"source_sha256": SHA, "build_matrix_sha256": SHA, "same_machine_only": True},
        "source_url": "https://github.com/example/project/archive/source.zip",
    })
    assert compiled(value)["artifacts"][2]["local_build_binding"]["same_machine_only"] is True
    value["artifacts"][2]["local_build_binding"]["same_machine_only"] = False
    with pytest.raises(ValueError):
        compile_runtime_artifact_manifest(value)


def test_local_build_native_tool_requires_exact_provider_provenance_pair() -> None:
    value = body()
    target = value["artifacts"][3]
    target.update({
        "provider": "OWNER_ACCEPTED_LOCAL_BUILD",
        "provenance": "LOCAL_BUILD_ATTESTATION",
        "source_url": "https://github.com/example/project/archive/source.zip",
        "local_build_binding": {"source_sha256": SHA, "build_matrix_sha256": SHA, "same_machine_only": True},
    })
    accepted = compiled(value)
    assert accepted["artifacts"][3]["provider"] == "OWNER_ACCEPTED_LOCAL_BUILD"
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(accepted)

    value["artifacts"][3]["provider"] = "OFFICIAL_PROJECT_RELEASE"
    value["artifacts"][3]["source_url"] = "https://github.com/example/project/releases/download/v1/ffmpeg.zip"
    with pytest.raises(ValueError, match="local build coordinates"):
        compile_runtime_artifact_manifest(value)


def test_no_effect_surface_and_source_imports() -> None:
    assert_no_effect_surface()
    source = (ROOT / "src" / "ai_video_production" / "qwen3_tts_runtime_artifact_manifest.py").read_text(encoding="utf-8")
    for forbidden in ("import os", "import subprocess", "import socket", "import requests", "import torch", "open(", "Path(", "urlopen(", "pip"):
        assert forbidden not in source
