from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

import pytest

from ai_video_production.montage_learning_bridge_application import (
    GenericObservationCoordinates,
    MontageLearningBridgeApplication,
    MontageLearningBridgeApplicationError,
)
from ai_video_production.montage_learning_bridge_contracts import (
    canonical_learning_sha256,
)
from ai_video_production.montage_learning_file_bridge import (
    BridgeLayout,
    MontageLearningFileBridgeError,
    PRODUCTION_BRIDGE_ROOT,
    load_bridge_owner,
    provision_bridge,
    snapshot_delivery,
)
from ai_video_production.serialization import canonical_json_bytes


def _payload(record_id: str = "observation-001") -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "message_type": "MontageLearningExport",
        "record_id": record_id,
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


def _delivery(record_id: str = "observation-001") -> dict[str, object]:
    payload = _payload(record_id)
    return {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "record_id": record_id,
        "learning_sha256": canonical_learning_sha256(payload),
        "canonical_timeline": False,
        "auto_admit_authorized": False,
        "payload": payload,
    }


def _stage(layout: BridgeLayout, delivery: dict[str, object]) -> Path:
    digest = str(delivery["learning_sha256"]).removeprefix("sha256:")
    path = layout.inbox / f"{delivery['record_id']}--{digest}.json"
    path.write_bytes(canonical_json_bytes(delivery) + b"\n")
    return path


@dataclass
class _GenericCommit:
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
    def __init__(self) -> None:
        self.calls = 0

    def record_exact_generic_observation(self, delivery, **kwargs):
        self.calls += 1
        return _GenericCommit(
            {
                "schema_version": "1.0.0",
                "message_type": "BvpMontageLearningAdmissionReceipt",
                "record_id": delivery["record_id"],
                "learning_sha256": delivery["learning_sha256"],
                "status": "ACCEPTED",
                "receipt_id": "generic-receipt-001",
                "timestamp": "2026-08-27T00:00:00Z",
            }
        )

    def admit_exact(self, delivery, **kwargs):  # pragma: no cover - wrong lane
        raise AssertionError("generic delivery reached exact canonical API")


def _layout(tmp_path: Path) -> BridgeLayout:
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    return layout


def test_provision_is_idempotent_and_never_claims_isolated_root_as_production(tmp_path):
    layout = _layout(tmp_path)
    first = load_bridge_owner(layout)
    second = provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    assert first == second
    assert second.production_path is False
    assert layout.root != PRODUCTION_BRIDGE_ROOT
    with pytest.raises(MontageLearningFileBridgeError):
        BridgeLayout(PRODUCTION_BRIDGE_ROOT.parent / "alternate", True)
    with pytest.raises(MontageLearningFileBridgeError):
        BridgeLayout.for_isolated_test(PRODUCTION_BRIDGE_ROOT)


def test_generic_import_revalidates_commits_and_publishes_matching_v1_receipt(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    staged = _stage(layout, delivery)
    port = _Port()
    app = MontageLearningBridgeApplication(layout=layout, canonical_port=port)

    coordinates = GenericObservationCoordinates(expected_revision=0)
    first = app.import_path(staged, generic_coordinates=coordinates)
    second = app.import_path(staged, generic_coordinates=coordinates)

    assert first.status == second.status == "ACCEPTED"
    assert first.canonical_store_written is True
    assert first.learning_adoption_authorized is False
    assert first.timeline_mutation_authorized is False
    assert port.calls == 2
    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["record_id"] == delivery["record_id"]
    assert receipt["learning_sha256"] == delivery["learning_sha256"]
    assert receipt["status"] == "ACCEPTED"


def test_missing_generic_coordinates_raise_without_publishing_receipt(tmp_path):
    layout = _layout(tmp_path)
    staged = _stage(layout, _delivery())
    app = MontageLearningBridgeApplication(
        layout=layout,
        canonical_port=_Port(),
    )
    with pytest.raises(MontageLearningBridgeApplicationError, match="generic delivery"):
        app.import_path(staged)
    assert list(layout.receipts.glob("*.receipt.json")) == []


def test_snapshot_rejects_filename_body_digest_malformed_duplicate_and_oversize(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    staged = _stage(layout, delivery)

    wrong = layout.inbox / f"other--{str(delivery['learning_sha256'])[7:]}.json"
    staged.replace(wrong)
    with pytest.raises(MontageLearningFileBridgeError, match="record_id"):
        snapshot_delivery(wrong, layout)

    malformed = layout.inbox / ("bad--" + "a" * 64 + ".json")
    malformed.write_text('{"record_id":"bad","record_id":"bad"}', encoding="utf-8")
    with pytest.raises(MontageLearningFileBridgeError, match="duplicate"):
        snapshot_delivery(malformed, layout)

    oversized = layout.inbox / ("huge--" + "b" * 64 + ".json")
    with oversized.open("wb") as handle:
        handle.truncate(4 * 1024 * 1024 + 1)
    with pytest.raises(MontageLearningFileBridgeError, match="size"):
        snapshot_delivery(oversized, layout)


def test_symlink_delivery_and_owner_manifest_collision_fail_closed(tmp_path):
    layout = _layout(tmp_path)
    if hasattr(os, "symlink"):
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = layout.inbox / ("linked--" + "a" * 64 + ".json")
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlink creation not available")
        with pytest.raises(MontageLearningFileBridgeError):
            snapshot_delivery(link, layout)

    manifest = json.loads(layout.owner_manifest.read_text(encoding="utf-8"))
    manifest["bridge_instance_id"] = "other-owner"
    layout.owner_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(MontageLearningFileBridgeError):
        provision_bridge(layout, bridge_instance_id="bridge-fixture-001")


def test_exact_and_generic_lanes_never_silently_mix(tmp_path):
    layout = _layout(tmp_path)
    delivery = _delivery()
    delivery["message_type"] = "BvpMontageExactEvidenceDelivery"
    path = layout.inbox / (
        f"{delivery['record_id']}--{str(delivery['learning_sha256'])[7:]}.json"
    )
    path.write_bytes(canonical_json_bytes(delivery) + b"\n")
    app = MontageLearningBridgeApplication(layout=layout, canonical_port=_Port())
    with pytest.raises((MontageLearningFileBridgeError, MontageLearningBridgeApplicationError)):
        app.import_path(path)
