from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.desktop_compute_policy import (
    ComputePreference,
    DesktopComputePolicyError,
    frozen_renderer_evidence_registry,
    validate_renderer_evidence_registry,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def test_renderer_registry_separates_ui_evidence_from_compute_preference() -> None:
    registry = frozen_renderer_evidence_registry()
    entries = {item["renderer_id"]: item for item in registry["renderers"]}
    shell = entries["shell.webview2.renderer"]
    assert shell["preference_applies"] is False
    assert shell["hardware_acceleration_policy"] == "ENABLED_WHEN_SUPPORTED"
    assert shell["capability_inventory"]["status"] == "NOT_CONFIRMED"
    assert shell["packaged_renderer_observation"]["status"] == "NOT_CONFIRMED"
    assert all(item["preference_applies"] is False for item in entries.values())
    assert ComputePreference.CPU_EXPLICIT.value not in json.dumps(registry)


def test_tk_and_winforms_cannot_inherit_webview_or_compute_pass() -> None:
    entries = {
        item["renderer_id"]: item
        for item in frozen_renderer_evidence_registry()["renderers"]
    }
    assert entries["dbd.training.tk"]["hardware_acceleration_policy"] == "NO_GPU_RENDERING_CLAIM"
    assert entries["dbd.trivia.tk"]["capability_inventory"]["status"] == "NOT_APPLICABLE"
    assert entries["voice.model.builder.tk"]["packaged_renderer_observation"]["status"] == "NOT_CONFIRMED"
    assert entries["voice.capture.winforms"]["hardware_acceleration_policy"] == "INDEPENDENT_EVIDENCE_REQUIRED"


def test_renderer_schema_mirror_and_registry_validation() -> None:
    root = Path(__file__).parents[1]
    schema_path = root / "schemas" / "desktop-renderer-evidence.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / schema_path.name
    assert schema_path.read_bytes() == mirror.read_bytes()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(frozen_renderer_evidence_registry()))
    assert errors == []


def _with_pass(document: dict[str, object], renderer_id: str) -> dict[str, object]:
    row = next(item for item in document["renderers"] if item["renderer_id"] == renderer_id)
    digest = "sha256:" + "a" * 64
    row["capability_inventory"] = {
        "status": "PASS",
        "runtime_version": "1.0.0",
        "adapter_identity_sha256": digest,
    }
    observation = {
        "status": "PASS",
        "process_identity_sha256": digest,
        "window_identity_sha256": digest,
        "adapter_identity_sha256": digest,
        "core_webview2_version": "1.0.0" if row["frontend"] == "WEBVIEW2" else None,
        "renderer_kind": "HARDWARE",
        "software_renderer": False,
        "observation_sha256": None,
    }
    body = dict(observation)
    body.pop("observation_sha256")
    observation["observation_sha256"] = sha256_bytes(canonical_json_bytes(body))
    row["packaged_renderer_observation"] = observation
    registry_body = dict(document)
    registry_body.pop("registry_sha256")
    document["registry_sha256"] = sha256_bytes(canonical_json_bytes(registry_body))
    return document


def test_webview_pass_requires_hardware_evidence_and_exact_digest() -> None:
    document = _with_pass(frozen_renderer_evidence_registry(), "shell.webview2.renderer")
    validate_renderer_evidence_registry(document)
    shell = next(item for item in document["renderers"] if item["renderer_id"] == "shell.webview2.renderer")
    shell["packaged_renderer_observation"]["renderer_kind"] = "WARP"
    body = dict(document)
    body.pop("registry_sha256")
    document["registry_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(DesktopComputePolicyError, match="validation"):
        validate_renderer_evidence_registry(document)


def test_tk_frontend_cannot_publish_renderer_pass_even_with_complete_evidence() -> None:
    document = _with_pass(frozen_renderer_evidence_registry(), "dbd.training.tk")
    with pytest.raises(DesktopComputePolicyError, match="Tk frontend"):
        validate_renderer_evidence_registry(document)


@pytest.mark.parametrize("field", ["adapter_identity_sha256", "core_webview2_version"])
def test_webview_pass_rejects_capability_observation_identity_mismatch(field: str) -> None:
    document = _with_pass(frozen_renderer_evidence_registry(), "shell.webview2.renderer")
    shell = next(item for item in document["renderers"] if item["renderer_id"] == "shell.webview2.renderer")
    shell["packaged_renderer_observation"][field] = (
        "sha256:" + "c" * 64 if field == "adapter_identity_sha256" else "2.0.0"
    )
    observation = dict(shell["packaged_renderer_observation"])
    observation.pop("observation_sha256")
    shell["packaged_renderer_observation"]["observation_sha256"] = sha256_bytes(
        canonical_json_bytes(observation)
    )
    body = dict(document)
    body.pop("registry_sha256")
    document["registry_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(DesktopComputePolicyError, match="mismatch"):
        validate_renderer_evidence_registry(document)
