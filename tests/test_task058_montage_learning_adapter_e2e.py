from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.montage_learning_bridge_application import (
    GenericObservationCoordinates,
    MontageLearningBridgeApplication,
)
from ai_video_production.montage_learning_connector_readiness import (
    MontageLearningConnectorReadinessError,
    ProfileSourceBinding,
    production_readiness_evidence,
    publish_prebuilt_advisory_profile,
    validate_prebuilt_advisory_profile,
)
from ai_video_production.montage_learning_file_bridge import (
    BridgeLayout,
    provision_bridge,
)
from ai_video_production.serialization import sha256_json


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(
    r"C:\Users\user\.codex\skills\bvp-montage-learning-adapter"
)
SKILL_SCRIPT = SKILL_ROOT / "scripts" / "bvp_adapter.py"
SKILL_CONFIG = SKILL_ROOT / "config" / "bvp-learning-connector.json"
SKILL_SCHEMA = SKILL_ROOT / "schemas" / "connector-file-bridge.schema.json"


def _profile(profile_id: str = "PROFILE-FIXTURE-001") -> dict[str, object]:
    payload = {
        "projection_version": "1.0.0",
        "preferences": [
            {
                "preference_id": "protect-staccato-microcuts",
                "decision": "PROTECT",
                "target": "STACCATO_MICROCUT_CLUSTER",
                "contexts": ["high-energy build"],
                "confidence": 0.5,
                "confirmation_count": 1,
                "reason_codes": ["HUMAN_FINAL_CONFIRMED"],
                "ranking_bias": 0.5,
            }
        ],
    }
    return {
        "schema_version": "1.0.0",
        "message_type": "BvpMontagePreferenceProfileDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "profile_contract": "bvp-task029-montage-preference-projection-v1",
        "profile_id": profile_id,
        "profile_version": 1,
        "owner_scope_hash": "sha256:" + "a" * 64,
        "source_record_count": 1,
        "profile_sha256": sha256_json(payload),
        "advisory_only": True,
        "canonical_timeline": False,
        "auto_apply_authorized": False,
        "payload": payload,
    }


def _learning() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "message_type": "MontageLearningExport",
        "record_id": "e2e-observation-001",
        "source_feedback_id": "feedback-001",
        "proposal_id": "proposal-001",
        "timeline_fps": {"numerator": 60, "denominator": 1},
        "style_profile": "dbd-aggressive",
        "music_context": {"anchor_kind": "DROP"},
        "video_context": {"event_type": "PALLET_DROP"},
        "proposal": {"timeline_frame": 600},
        "human_final": {
            "timeline_frame": 604,
            "status": "moved",
            "provenance": {"actor_role": "owner-editor"},
        },
        "delta_frames": 4,
        "result": "moved",
        "privacy": {
            "safe_export": True,
            "raw_actor_exported": False,
            "redacted_field_paths": [],
        },
        "validation_status": {
            "planning": "PASS",
            "static": "PASS",
            "package": "PASS",
            "runtime": "NOT_RUN",
        },
        "adapter_metadata": {
            "canonical_timeline": False,
            "absolute_host_path_included": False,
        },
    }


@dataclass
class _Commit:
    receipt: dict[str, object]

    @property
    def record_id(self) -> str:
        return str(self.receipt["record_id"])

    @property
    def learning_sha256(self) -> str:
        return str(self.receipt["learning_sha256"])

    @property
    def status(self) -> str:
        return str(self.receipt["status"])

    def to_skill_v1_receipt(self) -> dict[str, object]:
        return dict(self.receipt)


class _Port:
    def record_exact_generic_observation(self, delivery, **kwargs):
        return _Commit(
            {
                "schema_version": "1.0.0",
                "message_type": "BvpMontageLearningAdmissionReceipt",
                "record_id": delivery["record_id"],
                "learning_sha256": delivery["learning_sha256"],
                "status": "ACCEPTED",
                "receipt_id": "e2e-generic-receipt-001",
                "timestamp": "2026-08-27T00:00:00Z",
            }
        )

    def admit_exact(self, delivery, **kwargs):  # pragma: no cover
        raise AssertionError("generic E2E crossed into exact v2 admission")


def _run_adapter(tmp_path: Path, *arguments: str) -> dict[str, object]:
    output = tmp_path / f"adapter-{len(list(tmp_path.glob('adapter-*.json')))}.json"
    completed = subprocess.run(
        [sys.executable, str(SKILL_SCRIPT), *arguments, "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(output.read_text(encoding="utf-8"))


def _skill_digest() -> str:
    digest = sha256()
    for path in (SKILL_SCRIPT, SKILL_CONFIG, SKILL_SCHEMA):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_readiness_schema_mirror_and_unbound_production_are_fail_closed(tmp_path):
    public = ROOT / "schemas" / "montage-learning-connector-readiness.schema.json"
    packaged = (
        ROOT
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / public.name
    )
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    result = publish_prebuilt_advisory_profile(
        layout,
        _profile(),
        source_binding=ProfileSourceBinding.unbound_production(),
    )
    assert result.status == "SOURCE_NOT_BOUND"
    assert result.written is False
    assert not layout.current_profile.exists()

    evidence = production_readiness_evidence(
        bridge_state="OWNERSHIP_UNVERIFIED",
        import_state="OBSERVATION_RECORDED",
        adapter_state="LOAD_PROFILE_PASS",
        adapter_contract_e2e_pass=True,
        default_skill_config_unchanged=True,
    ).to_dict()
    Draft202012Validator(schema).validate(evidence)
    assert evidence["production_profile_source_bound"] is False
    assert evidence["profile_state"] == "SOURCE_NOT_BOUND"
    assert evidence["activation_state"] == "BLOCKED"
    assert evidence["connector_enabled"] is False
    assert evidence["activation_authorized"] is False


def test_prebuilt_profile_is_strict_immutable_transport_with_cas(tmp_path):
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    source = ProfileSourceBinding.bound_isolated_fixture()
    envelope = _profile()
    before = json.loads(json.dumps(envelope))

    first = publish_prebuilt_advisory_profile(
        layout,
        envelope,
        source_binding=source,
    )
    second = publish_prebuilt_advisory_profile(
        layout,
        envelope,
        source_binding=source,
    )
    assert first.status == "PUBLISHED"
    assert second.status == "DUPLICATE"
    assert envelope == before
    assert json.loads(layout.current_profile.read_text(encoding="utf-8")) == envelope
    assert first.semantic_projection_generated is False
    assert first.production_profile_source_bound is False

    changed = _profile("PROFILE-FIXTURE-002")
    with pytest.raises(ValueError, match="CAS"):
        publish_prebuilt_advisory_profile(
            layout,
            changed,
            source_binding=source,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"auto_apply_authorized": True}),
        lambda value: value.update({"profile_sha256": "sha256:" + "b" * 64}),
        lambda value: value.update(
            {"payload": {"projection_version": "1.0.0", "timing_preferences": []}}
        ),
    ],
)
def test_profile_unknown_authority_hash_and_task055_timing_shape_fail_closed(mutate):
    value = _profile()
    mutate(value)
    with pytest.raises(MontageLearningConnectorReadinessError):
        validate_prebuilt_advisory_profile(value)


def test_source_binding_is_sealed_and_immutable():
    with pytest.raises(TypeError):
        ProfileSourceBinding(
            source_id="forged",
            production_profile_source_bound=True,
            isolated_fixture=False,
        )
    binding = ProfileSourceBinding.unbound_production()
    with pytest.raises(AttributeError):
        binding.production_profile_source_bound = True


@pytest.mark.skipif(not SKILL_SCRIPT.is_file(), reason="installed SKILL unavailable")
def test_unchanged_skill_isolated_connector_publish_receipt_and_profile_e2e(tmp_path):
    before_digest = _skill_digest()
    default_config = json.loads(SKILL_CONFIG.read_text(encoding="utf-8"))
    assert default_config["enabled"] is False

    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    config = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningConnectorConfig",
        "enabled": True,
        "contract_profile": "bvp-task029-file-bridge-v1",
        "bridge_root": str(layout.root),
        "learning_publish_enabled": True,
        "preference_read_enabled": True,
        "require_admission_receipt": True,
        "legacy_behavior_when_unavailable": True,
    }
    config_path = tmp_path / "isolated-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    learning_path = tmp_path / "learning.json"
    learning_path.write_text(json.dumps(_learning()), encoding="utf-8")

    status = _run_adapter(
        tmp_path, "connector-status", "--config", str(config_path)
    )
    assert status["status"] == "READY"

    staged = _run_adapter(
        tmp_path,
        "publish-learning",
        "--learning",
        str(learning_path),
        "--config",
        str(config_path),
    )
    assert staged["status"] == "STAGED_PENDING_REQUIRED_RECEIPT"
    assert staged["canonical_store_written"] is False

    delivery_path = Path(str(staged["delivery_path"]))
    app = MontageLearningBridgeApplication(layout=layout, canonical_port=_Port())
    imported = app.import_path(
        delivery_path,
        generic_coordinates=GenericObservationCoordinates(expected_revision=0),
    )
    assert imported.status == "ACCEPTED"

    matched = _run_adapter(
        tmp_path,
        "publish-learning",
        "--learning",
        str(learning_path),
        "--config",
        str(config_path),
    )
    assert matched["status"] == "BVP_REPORTED_ACCEPTED"
    assert matched["canonical_store_written"] is True

    published = publish_prebuilt_advisory_profile(
        layout,
        _profile(),
        source_binding=ProfileSourceBinding.bound_isolated_fixture(),
    )
    assert published.status == "PUBLISHED"
    loaded = _run_adapter(tmp_path, "load-profile", "--config", str(config_path))
    assert loaded["status"] == "PASS"
    assert loaded["advisory_only"] is True
    assert loaded["canonical_timeline"] is False
    assert loaded["auto_apply_authorized"] is False

    assert _skill_digest() == before_digest
    assert json.loads(SKILL_CONFIG.read_text(encoding="utf-8"))["enabled"] is False
