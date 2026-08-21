from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.qwen3_tts_runtime_artifact_closure_plan import (
    SCHEMA_ID,
    assert_no_effect_surface,
    candidate_set_sha256,
    compile_runtime_artifact_closure_plan,
    parse_runtime_artifact_closure_plan,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "qwen3-tts-runtime-artifact-closure-plan.schema.json"
MIRROR = ROOT / "src" / "ai_video_production" / "schema_resources" / "qwen3-tts-runtime-artifact-closure-plan.schema.json"
SHA = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def candidate(
    candidate_id: str = "qwen-tts-0.1.1-py3-none-any",
    *,
    project_id: str = "qwen-tts",
    provider: str = "PYPI",
    index_observation_id: str = "obs-qwen-index",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "artifact_kind": "DISTRIBUTION_WHEEL",
        "project_id": project_id,
        "provider": provider,
        "index_identity": "pypi-project-qwen-tts",
        "version": "0.1.1",
        "canonical_url": "https://files.pythonhosted.org/packages/qwen_tts-0.1.1-py3-none-any.whl",
        "filename": "qwen_tts-0.1.1-py3-none-any.whl",
        "bytes": 113529,
        "sha256": "sha256:11a290d8dabc7ef91a90c54478c8ab19b3edb1d85c0882313721892bdc4af15d",
        "metadata_sha256": SHA,
        "metadata_bytes": 2048,
        "requires_python": ">=3.9",
        "wheel_tags": ["py3-none-any"],
        "yanked": False,
        "prerelease": False,
        "development": False,
        "postrelease": False,
        "local_version": None,
        "requires_dist": [],
        "index_observation_id": index_observation_id,
        "metadata_observation_id": "obs-qwen-metadata",
        "artifact_head_observation_id": "obs-qwen-head",
        "checksum_observation_id": None,
        "license_id": "Apache-2.0",
        "manual_legal_review_required": False,
        "root_reachable": True,
        "availability": "NOT_CONFIRMED",
        "classification_state": "CALLER_REPORTED_UNVERIFIED",
        "upstream_observation_id": None,
        "tool_release_contract": None,
        "required_tool_kinds": [],
        "tool_member_mapping_state": "NOT_APPLICABLE",
    }


def observation(
    observation_id: str = "obs-qwen-index",
    *,
    evaluated_at: str = "2026-08-21T00:00:00.000Z",
    kind: str = "PROJECT_INDEX_GET",
    url: str = "https://pypi.org/simple/qwen-tts/",
    method: str = "GET",
    content_type: str = "APPLICATION_VND_PYPI_SIMPLE_V1_JSON",
    declared_bytes: int | None = 4096,
    observed_bytes: int = 4096,
    candidate_count: int = 1,
    response_sha256: str = SHA_B,
    asserted_artifact_sha256: str | None = None,
) -> dict[str, object]:
    return {
        "observation_id": observation_id,
        "source": "SYNTHETIC_CONTRACT_FIXTURE",
        "evaluated_at": evaluated_at,
        "provider": "PYPI",
        "project_id": "qwen-tts",
        "index_identity": "pypi-project-qwen-tts",
        "observer_id": "task014-metadata-observer",
        "observer_revision": 1,
        "observer_sha256": SHA,
        "observation_kind": kind,
        "canonical_url": url,
        "method": method,
        "status": 200,
        "content_type": content_type,
        "declared_bytes": declared_bytes,
        "observed_bytes": observed_bytes,
        "redirect_count": 0,
        "final_host_class": "PYPI_INDEX",
        "safe_content_path_sha256": SHA,
        "response_sha256": response_sha256,
        "candidate_count": candidate_count,
        "asserted_artifact_sha256": asserted_artifact_sha256,
        "transport_policy_passed": False,
    }


def body() -> dict[str, object]:
    item = candidate()
    observations = [
        observation(),
        observation(
            "obs-qwen-metadata", kind="METADATA_SIDECAR_GET",
            url="https://files.pythonhosted.org/metadata/qwen_tts-0.1.1.metadata",
            content_type="APPLICATION_OCTET_STREAM_METADATA", declared_bytes=2048,
            observed_bytes=2048, candidate_count=0, response_sha256=SHA,
        ),
        observation(
            "obs-qwen-head", kind="ARTIFACT_HEAD",
            url="https://files.pythonhosted.org/packages/qwen_tts-0.1.1-py3-none-any.whl",
            method="HEAD", content_type="APPLICATION_OCTET_STREAM_ARTIFACT", declared_bytes=113529,
            observed_bytes=0, candidate_count=0,
        ),
    ]
    return {
        "schema": SCHEMA_ID,
        "status": "CONTRACT_ONLY_UNRESOLVED",
        "plan_id": "task014-runtime-closure-plan-r0",
        "revision": 1,
        "target": {
            "os": "WINDOWS", "platform": "win_amd64", "python_tag": "cp312",
            "python_version": "3.12.4", "cuda": "cu130", "attention": "SDPA",
        },
        "resolver": {
            "resolver_id": "task014-closure-solver",
            "resolver_revision": 1,
            "resolver_sha256": SHA,
            "parser_distribution": "packaging",
            "parser_version": "25.0",
            "parser_artifact_sha256": SHA_B,
            "parser_pin_accepted": False,
        },
        "request_observations": observations,
        "candidate_snapshots": [{
            "project_id": "qwen-tts",
            "source_observation_id": "obs-qwen-index",
            "candidate_ids": [item["candidate_id"]],
            "candidate_set_sha256": candidate_set_sha256([item]),
        }],
        "candidates": [item],
        "constraints": [{
            "constraint_id": "root-qwen-tts",
            "project_id": "qwen-tts",
            "requirement": "qwen-tts==0.1.1",
            "parent_project_id": None,
            "marker_state": "ACTIVE",
            "root": True,
        }],
        "proposed_selections": [{
            "project_id": "qwen-tts",
            "candidate_id": item["candidate_id"],
            "version_rank": 0,
            "tag_rank": 0,
            "filename_rank": 0,
            "selection_state": "CALLER_PROPOSED_UNVERIFIED",
        }],
        "native_sox_executable_requirement": "UNKNOWN",
        "counts": {
            "observation_count": 3, "project_count": 1, "candidate_count": 1,
            "constraint_count": 1, "proposed_selection_count": 1,
        },
        "contract_only": True,
        "candidate_snapshots_authenticated": False,
        "deterministic_selection_verified": False,
        "active_dependency_closure_verified": False,
        "plan_review_accepted": False,
        "acquisition_eligible": False,
        "diagnostic_only": True,
        "persistent_plan_is_capability": False,
        "metadata_network_authorized": False,
        "artifact_download_authorized": False,
        "install_authorized": False,
        "runtime_reuse_authorized": False,
        "model_load_authorized": False,
        "consumer_execution_authorized": False,
        "post_return_state_guaranteed": False,
        "consumer_revalidation_required": True,
        "no_effect_flags": {
            "network_accessed": False,
            "artifact_body_downloaded": False,
            "file_written": False,
            "package_installed": False,
            "target_python_executed": False,
            "package_imported": False,
            "model_loaded": False,
            "owner_audio_read": False,
            "inference_executed": False,
            "native_tool_executed": False,
        },
    }


def compiled(value: dict[str, object] | None = None) -> dict[str, object]:
    return compile_runtime_artifact_closure_plan(value or body()).to_dict()


def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_round_trip_schema_mirror_and_canonical_digests() -> None:
    first = compiled()
    second = compiled(copy.deepcopy(body()))
    assert first == second
    assert parse_runtime_artifact_closure_plan(first).to_dict() == first
    validator().validate(first)
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    assert first["status"] == "CONTRACT_ONLY_UNRESOLVED"
    assert first["proposed_selections"][0]["selection_state"] == "CALLER_PROPOSED_UNVERIFIED"
    assert first["native_sox_executable_requirement"] == "UNKNOWN"


def test_semantic_digest_excludes_time_but_observation_digest_binds_it() -> None:
    first = compiled()
    changed = body()
    changed["request_observations"][0]["evaluated_at"] = "2026-08-21T00:00:01.000Z"
    second = compiled(changed)
    assert first["semantic_plan_sha256"] == second["semantic_plan_sha256"]
    assert first["observation_receipt_sha256"] != second["observation_receipt_sha256"]


def test_compile_canonicalizes_input_order_but_parser_rejects_reordered_document() -> None:
    value = body()
    value["request_observations"].reverse()
    document = compiled(value)
    assert [item["observation_id"] for item in document["request_observations"]] == [
        "obs-qwen-metadata", "obs-qwen-head", "obs-qwen-index",
    ]
    tampered = copy.deepcopy(document)
    tampered["request_observations"].reverse()
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(tampered)


@pytest.mark.parametrize(
    "field",
    [
        "persistent_plan_is_capability", "metadata_network_authorized",
        "artifact_download_authorized", "install_authorized",
        "runtime_reuse_authorized", "model_load_authorized",
        "consumer_execution_authorized", "post_return_state_guaranteed",
        "candidate_snapshots_authenticated", "deterministic_selection_verified",
        "active_dependency_closure_verified", "plan_review_accepted",
        "acquisition_eligible",
    ],
)
def test_authority_true_is_rejected_by_runtime_and_schema(field: str) -> None:
    document = compiled()
    document[field] = True
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(document)
    assert list(validator().iter_errors(document))


@pytest.mark.parametrize("field", ["contract_only", "diagnostic_only", "consumer_revalidation_required"])
def test_required_safe_true_claims_cannot_be_removed(field: str) -> None:
    document = compiled()
    document[field] = False
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(document)
    assert list(validator().iter_errors(document))


def test_unaccepted_parser_pin_cannot_be_laundered() -> None:
    document = compiled()
    document["resolver"]["parser_pin_accepted"] = True
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(document)
    assert list(validator().iter_errors(document))


@pytest.mark.parametrize("field", list(body()["no_effect_flags"]))
def test_every_effect_flag_true_is_rejected(field: str) -> None:
    document = compiled()
    document["no_effect_flags"][field] = True
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(document)
    assert list(validator().iter_errors(document))


@pytest.mark.parametrize(
    "url",
    [
        "https://pypi.org/simple/qwen-tts/?token=x",
        "https://user@pypi.org/simple/qwen-tts/",
        "https://pypi.org:443/simple/qwen-tts/",
        "http://pypi.org/simple/qwen-tts/",
        "https://localhost/simple/qwen-tts/",
    ],
)
def test_query_credentials_ports_scheme_and_unowned_hosts_are_rejected(url: str) -> None:
    value = body()
    value["request_observations"][0]["canonical_url"] = url
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)


def test_provider_ownership_is_closed_and_release_flags_remain_unverified() -> None:
    value = body()
    value["candidates"][0]["provider"] = "PYTORCH_INDEX"
    value["candidates"][0]["canonical_url"] = "https://download.pytorch.org/whl/cu130/qwen.whl"
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)

    for field in ("yanked", "prerelease", "development"):
        value = body()
        value["candidates"][0][field] = True
        value["candidate_snapshots"][0]["candidate_set_sha256"] = candidate_set_sha256(value["candidates"])
        document = compiled(value)
        validator().validate(document)
        assert document["candidates"][0][field] is True
        assert document["candidates"][0]["classification_state"] == "CALLER_REPORTED_UNVERIFIED"
        assert document["deterministic_selection_verified"] is False


def test_b1a_is_synthetic_only_and_cannot_launder_transport_truth() -> None:
    schema = validator()
    for source, passed, accepted in (
        ("SYNTHETIC_CONTRACT_FIXTURE", False, True),
        ("SYNTHETIC_CONTRACT_FIXTURE", True, False),
        ("BOUND_NETWORK_OBSERVATION", True, False),
        ("BOUND_NETWORK_OBSERVATION", False, False),
    ):
        value = body()
        value["request_observations"][0]["source"] = source
        value["request_observations"][0]["transport_policy_passed"] = passed
        if accepted:
            document = compiled(value)
            schema.validate(document)
        else:
            with pytest.raises(ValueError):
                compile_runtime_artifact_closure_plan(value)
            document = compiled()
            document["request_observations"][0].update(source=source, transport_policy_passed=passed)
            assert list(schema.iter_errors(document))


def test_schema_and_runtime_bind_candidate_provider_to_project_and_host() -> None:
    value = body()
    value["candidates"][0]["provider"] = "PYTORCH_INDEX"
    value["candidates"][0]["canonical_url"] = "https://download.pytorch.org/whl/cu130/qwen.whl"
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)
    document = compiled()
    document["candidates"][0].update(
        provider="PYTORCH_INDEX",
        canonical_url="https://download.pytorch.org/whl/cu130/qwen.whl",
    )
    assert list(validator().iter_errors(document))


def test_snapshot_union_selection_and_observation_binding_are_exact() -> None:
    value = body()
    extra = candidate("qwen-tts-extra")
    value["candidates"].append(extra)
    value["counts"]["candidate_count"] = 2
    value["proposed_selections"][0]["candidate_id"] = "qwen-tts-extra"
    value["request_observations"][0]["candidate_count"] = 2
    with pytest.raises(ValueError, match="snapshot union|outside project snapshot|candidate count"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["request_observations"][0]["project_id"] = "other-project"
    value["request_observations"][0]["index_identity"] = "pypi-project-other"
    value["request_observations"][0]["canonical_url"] = "https://pypi.org/simple/other-project/"
    with pytest.raises(ValueError, match="candidate index observation binding"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["request_observations"][0]["candidate_count"] = 2
    with pytest.raises(ValueError, match="candidate count"):
        compile_runtime_artifact_closure_plan(value)


def test_contract_can_express_python_installer_and_btbn_tool_candidates() -> None:
    value = body()
    python_index = observation("obs-python-index", kind="PROJECT_RELEASE_GET")
    python_index.update({
        "provider": "PYTHON_ORG", "project_id": "python",
        "index_identity": "python-org-3.12.4",
        "canonical_url": "https://www.python.org/downloads/release/python-3124/",
        "content_type": "TEXT_HTML",
    })
    python_head = observation(
        "obs-python-head", kind="ARTIFACT_HEAD",
        url="https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe",
        method="HEAD", content_type="APPLICATION_OCTET_STREAM_ARTIFACT", declared_bytes=26772456,
        observed_bytes=0, candidate_count=0,
    )
    python_head.update(provider="PYTHON_ORG", project_id="python", index_identity="python-org-3.12.4")
    python_candidate = candidate(
        "python-3.12.4-amd64", project_id="python", provider="PYTHON_ORG",
        index_observation_id="obs-python-index",
    )
    python_candidate.update({
        "artifact_kind": "PYTHON_INSTALLER", "index_identity": "python-org-3.12.4",
        "version": "3.12.4",
        "canonical_url": "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe",
        "filename": "python-3.12.4-amd64.exe", "bytes": 26772456,
        "metadata_sha256": None, "metadata_bytes": None, "requires_python": None,
        "wheel_tags": [], "requires_dist": [], "license_id": "PSF-2.0",
        "manual_legal_review_required": True,
        "metadata_observation_id": None, "artifact_head_observation_id": "obs-python-head",
    })
    btbn_index = observation("obs-btbn-index", kind="PROJECT_RELEASE_GET")
    btbn_index.update({
        "provider": "GITHUB_RELEASE", "project_id": "btbn-ffmpeg-builds",
        "index_identity": "github-btbn-ffmpeg-builds-release",
        "canonical_url": "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/autobuild-2026-08-21",
        "content_type": "APPLICATION_JSON",
    })
    btbn_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-21/ffmpeg-win64-gpl.zip"
    btbn_head = observation(
        "obs-btbn-head", kind="ARTIFACT_HEAD", url=btbn_url, method="HEAD",
        content_type="APPLICATION_OCTET_STREAM_ARTIFACT", declared_bytes=100000000, observed_bytes=0,
        candidate_count=0,
    )
    btbn_checksum = observation(
        "obs-btbn-checksum", kind="CHECKSUM_ASSET_GET",
        url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-21/checksums.txt",
        content_type="TEXT_PLAIN", declared_bytes=256, observed_bytes=256,
        candidate_count=0, asserted_artifact_sha256=SHA,
    )
    for item in (btbn_head, btbn_checksum):
        item.update(provider="GITHUB_RELEASE", project_id="btbn-ffmpeg-builds", index_identity="github-btbn-ffmpeg-builds-release")
    btbn_upstream = observation(
        "obs-ffmpeg-upstream", kind="UPSTREAM_REFERENCE_GET",
        url="https://ffmpeg.org/download.html", content_type="TEXT_HTML",
        declared_bytes=1024, observed_bytes=1024, candidate_count=0,
    )
    btbn_upstream.update(provider="FFMPEG_ORG", project_id="ffmpeg", index_identity="ffmpeg-upstream-release")
    btbn_candidate = candidate(
        "btbn-ffmpeg-win64-gpl", project_id="btbn-ffmpeg-builds",
        provider="GITHUB_RELEASE", index_observation_id="obs-btbn-index",
    )
    btbn_candidate.update({
        "artifact_kind": "NATIVE_TOOL_ARCHIVE",
        "index_identity": "github-btbn-ffmpeg-builds-release", "version": "2026.08.21",
        "canonical_url": btbn_url,
        "filename": "ffmpeg-win64-gpl.zip", "bytes": 100000000,
        "sha256": SHA,
        "metadata_sha256": None, "metadata_bytes": None, "requires_python": None,
        "wheel_tags": [], "requires_dist": [], "license_id": "GPL-3.0-or-later",
        "manual_legal_review_required": True,
        "metadata_observation_id": None, "artifact_head_observation_id": "obs-btbn-head",
        "checksum_observation_id": "obs-btbn-checksum",
        "upstream_observation_id": "obs-ffmpeg-upstream",
        "tool_release_contract": {
            "repository_id": "BtbN/FFmpeg-Builds",
            "release_id": "release-2026-08-21",
            "release_tag": "autobuild-2026-08-21",
            "asset_id": "asset-win64-gpl",
            "upstream_ffmpeg_version": "8.1.2",
            "upstream_commit_id": "1" * 40,
            "build_configuration_sha256": SHA_B,
            "checksum_provenance": "PUBLISHER_CONTROLLED_RELEASE_CHECKSUM_UNVERIFIED",
            "state": "CALLER_REPORTED_UNVERIFIED",
        },
        "required_tool_kinds": ["FFMPEG", "FFPROBE"],
        "tool_member_mapping_state": "UNRESOLVED_UNACQUIRED",
    })
    value["request_observations"].extend([
        python_index, python_head, btbn_index, btbn_head, btbn_checksum, btbn_upstream,
    ])
    value["candidates"].extend([python_candidate, btbn_candidate])
    value["candidate_snapshots"].extend([
        {
            "project_id": "python", "source_observation_id": "obs-python-index",
            "candidate_ids": ["python-3.12.4-amd64"],
            "candidate_set_sha256": candidate_set_sha256([python_candidate]),
        },
        {
            "project_id": "btbn-ffmpeg-builds", "source_observation_id": "obs-btbn-index",
            "candidate_ids": ["btbn-ffmpeg-win64-gpl"],
            "candidate_set_sha256": candidate_set_sha256([btbn_candidate]),
        },
    ])
    value["constraints"].extend([
        {"constraint_id": "root-python", "project_id": "python", "requirement": "python==3.12.4", "parent_project_id": None, "marker_state": "ACTIVE", "root": True},
        {"constraint_id": "root-btbn", "project_id": "btbn-ffmpeg-builds", "requirement": "btbn-ffmpeg-builds==2026.08.21", "parent_project_id": None, "marker_state": "ACTIVE", "root": True},
    ])
    value["proposed_selections"].extend([
        {"project_id": "python", "candidate_id": "python-3.12.4-amd64", "version_rank": 0, "tag_rank": 0, "filename_rank": 0, "selection_state": "CALLER_PROPOSED_UNVERIFIED"},
        {"project_id": "btbn-ffmpeg-builds", "candidate_id": "btbn-ffmpeg-win64-gpl", "version_rank": 0, "tag_rank": 0, "filename_rank": 0, "selection_state": "CALLER_PROPOSED_UNVERIFIED"},
    ])
    value["counts"] = {"observation_count": 9, "project_count": 3, "candidate_count": 3, "constraint_count": 3, "proposed_selection_count": 3}
    document = compiled(value)
    validator().validate(document)
    assert {item["artifact_kind"] for item in document["candidates"]} == {
        "DISTRIBUTION_WHEEL", "PYTHON_INSTALLER", "NATIVE_TOOL_ARCHIVE",
    }
    tool = next(item for item in document["candidates"] if item["artifact_kind"] == "NATIVE_TOOL_ARCHIVE")
    assert tool["required_tool_kinds"] == ["FFMPEG", "FFPROBE"]
    assert tool["tool_member_mapping_state"] == "UNRESOLVED_UNACQUIRED"

    bad = copy.deepcopy(value)
    next(item for item in bad["candidates"] if item["artifact_kind"] == "NATIVE_TOOL_ARCHIVE")["required_tool_kinds"] = ["FFMPEG"]
    with pytest.raises(ValueError, match="tool pair"):
        compile_runtime_artifact_closure_plan(bad)

    bad = copy.deepcopy(value)
    next(item for item in bad["request_observations"] if item["observation_id"] == "obs-btbn-checksum")["asserted_artifact_sha256"] = SHA_B
    with pytest.raises(ValueError, match="checksum observation"):
        compile_runtime_artifact_closure_plan(bad)

    bad = copy.deepcopy(value)
    next(item for item in bad["request_observations"] if item["observation_id"] == "obs-ffmpeg-upstream")["provider"] = "GITHUB_RELEASE"
    next(item for item in bad["request_observations"] if item["observation_id"] == "obs-ffmpeg-upstream")["canonical_url"] = "https://github.com/ffmpeg/ffmpeg"
    with pytest.raises(ValueError, match="upstream.*observation"):
        compile_runtime_artifact_closure_plan(bad)

    bad = copy.deepcopy(value)
    next(item for item in bad["request_observations"] if item["observation_id"] == "obs-ffmpeg-upstream")["content_type"] = "APPLICATION_JSON"
    with pytest.raises(ValueError, match="upstream reference"):
        compile_runtime_artifact_closure_plan(bad)

    bad = copy.deepcopy(value)
    next(item for item in bad["candidates"] if item["artifact_kind"] == "NATIVE_TOOL_ARCHIVE")["tool_release_contract"]["repository_id"] = "other/repo"
    with pytest.raises(ValueError, match="repository identity"):
        compile_runtime_artifact_closure_plan(bad)

    bad = copy.deepcopy(value)
    next(item for item in bad["candidates"] if item["artifact_kind"] == "NATIVE_TOOL_ARCHIVE")["canonical_url"] = "https://github.com/other/repo/releases/download/autobuild-2026-08-21/ffmpeg-win64-gpl.zip"
    with pytest.raises(ValueError, match="asset coordinate"):
        compile_runtime_artifact_closure_plan(bad)

    for length in (41, 63):
        bad = copy.deepcopy(value)
        next(item for item in bad["candidates"] if item["artifact_kind"] == "NATIVE_TOOL_ARCHIVE")["tool_release_contract"]["upstream_commit_id"] = "1" * length
        with pytest.raises(ValueError, match="upstream_commit_id"):
            compile_runtime_artifact_closure_plan(bad)


def test_head_and_metadata_sidecar_byte_truth_are_bounded() -> None:
    value = body()
    item = value["request_observations"][2]
    item.update(declared_bytes=113529, observed_bytes=0)
    validator().validate(compiled(value))

    value = body()
    value["request_observations"][2]["content_type"] = "TEXT_PLAIN"
    with pytest.raises(ValueError, match="artifact HEAD"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["request_observations"][0].update(method="GET", declared_bytes=5, observed_bytes=0)
    with pytest.raises(ValueError, match="byte count"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["request_observations"][1].update(
        declared_bytes=4 * 1024**2 + 1,
        observed_bytes=4 * 1024**2 + 1,
    )
    with pytest.raises(ValueError, match="metadata sidecar"):
        compile_runtime_artifact_closure_plan(value)


def test_observation_roles_and_candidate_metadata_bindings_are_exact() -> None:
    value = body()
    value["request_observations"][0]["content_type"] = "APPLICATION_OCTET_STREAM_ARTIFACT"
    with pytest.raises(ValueError, match="observation content"):
        compile_runtime_artifact_closure_plan(value)
    document = compiled()
    index = next(item for item in document["request_observations"] if item["observation_id"] == "obs-qwen-index")
    index["content_type"] = "APPLICATION_OCTET_STREAM_ARTIFACT"
    assert list(validator().iter_errors(document))

    value = body()
    unused = observation(
        "obs-unused", kind="METADATA_SIDECAR_GET",
        url="https://files.pythonhosted.org/metadata/unused.metadata",
        content_type="APPLICATION_OCTET_STREAM_METADATA", declared_bytes=10,
        observed_bytes=10, candidate_count=0,
    )
    value["request_observations"].append(unused)
    value["counts"]["observation_count"] = 4
    with pytest.raises(ValueError, match="reference closure"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["candidate_snapshots"][0]["source_observation_id"] = "obs-qwen-head"
    value["candidates"][0]["index_observation_id"] = "obs-qwen-head"
    with pytest.raises(ValueError, match="index observation"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["request_observations"][1]["response_sha256"] = SHA_B
    with pytest.raises(ValueError, match="metadata observation"):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["request_observations"][1]["observed_bytes"] = 2049
    value["request_observations"][1]["declared_bytes"] = 2049
    with pytest.raises(ValueError, match="metadata observation"):
        compile_runtime_artifact_closure_plan(value)


@pytest.mark.parametrize(
    "url",
    [
        "https://PYPI.org/simple/qwen-tts/", "https://pypi.org/simple/qwen tts/",
        "https://pypi.org/simple/雪/", "https://pypi.org/simple/qwen*tts/",
        "https://pypi.org/simple/qwen[tts/", 'https://pypi.org/simple/qwen"tts/',
        "https://pypi.org/simple/qwen-tts/\n", "https://pypi.org/simple/qwen-tts/\r",
    ],
)
def test_url_host_case_space_and_non_ascii_are_runtime_schema_rejected(url: str) -> None:
    value = body()
    value["request_observations"][0]["canonical_url"] = url
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)
    document = compiled()
    index = next(item for item in document["request_observations"] if item["observation_id"] == "obs-qwen-index")
    index["canonical_url"] = url
    assert list(validator().iter_errors(document))


def test_url_controls_extension_case_and_aggregate_requirement_bounds_fail_closed() -> None:
    for url in ("\nhttps://pypi.org/simple/qwen-tts/", "https://pypi.org/simple\\qwen-tts/"):
        value = body()
        value["request_observations"][0]["canonical_url"] = url
        with pytest.raises(ValueError):
            compile_runtime_artifact_closure_plan(value)

    value = body()
    value["candidates"][0]["filename"] = "qwen_tts-0.1.1-py3-none-any.WHL"
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    many = []
    for index in range(17):
        item = candidate(f"qwen-candidate-{index:02d}")
        item["filename"] = f"qwen_tts-0.1.1-{index}-py3-none-any.whl"
        item["canonical_url"] = f"https://files.pythonhosted.org/packages/qwen_tts-0.1.1-{index}-py3-none-any.whl"
        item["requires_dist"] = [f"dep-{row:03d}" for row in range(512)]
        many.append(item)
    value["candidates"] = many
    with pytest.raises(ValueError, match="aggregate requirement"):
        compile_runtime_artifact_closure_plan(value)
    with pytest.raises(ValueError, match="aggregate requirement"):
        candidate_set_sha256(many)


def test_snapshot_selection_counts_and_rank_bindings_are_fail_closed() -> None:
    value = body()
    value["candidate_snapshots"][0]["candidate_set_sha256"] = SHA
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["proposed_selections"][0]["candidate_id"] = "missing"
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["proposed_selections"][0]["version_rank"] = 1
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)

    value = body()
    value["counts"]["candidate_count"] = 2
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)


@pytest.mark.parametrize(
    "timestamp",
    ["nonsenseZ", "2026-08-21Z", "2026-08-21 00:00:00Z", "2026-08-21T00:00:00+00:00"],
)
def test_timestamp_contract_is_strict(timestamp: str) -> None:
    value = body()
    value["request_observations"][0]["evaluated_at"] = timestamp
    with pytest.raises(ValueError):
        compile_runtime_artifact_closure_plan(value)


def test_parser_rejects_digest_tamper_and_extra_or_missing_fields() -> None:
    for field in ("semantic_plan_sha256", "observation_receipt_sha256"):
        document = compiled()
        document[field] = SHA
        with pytest.raises(ValueError):
            parse_runtime_artifact_closure_plan(document)
    document = compiled()
    document["extra"] = False
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(document)
    document = compiled()
    document.pop("diagnostic_only")
    with pytest.raises(ValueError):
        parse_runtime_artifact_closure_plan(document)


def test_frozen_plan_does_not_alias_inputs_or_outputs() -> None:
    source = body()
    plan = compile_runtime_artifact_closure_plan(source)
    source["candidates"][0]["filename"] = "changed.whl"
    projection = plan.to_dict()
    projection["candidates"][0]["filename"] = "also-changed.whl"
    assert plan.to_dict()["candidates"][0]["filename"] == "qwen_tts-0.1.1-py3-none-any.whl"


def test_no_effect_surface_or_effectful_imports() -> None:
    assert_no_effect_surface()
    source = (ROOT / "src" / "ai_video_production" / "qwen3_tts_runtime_artifact_closure_plan.py").read_text(encoding="utf-8")
    for token in (
        "import requests", "import urllib.request", "import http.client",
        "import socket", "import subprocess", "from pathlib", "import pathlib",
        "import importlib", "import qwen_tts", "import soundfile",
    ):
        assert token not in source
