from __future__ import annotations

from dataclasses import replace

import pytest

from ai_video_production.dbd_killer_capability_registry import (
    KillerCapability, KillerCapabilityRegistry, KillerDetectorType, KillerEffectFamily,
    KillerRoiFamily, KillerSpecificDetection, KillerSpecificRoiKey, initial_killer_capabilities,
)
from ai_video_production.dbd_killer_knowledge import KillerKnowledgeKind, KillerPowerVisualObservation
from ai_video_production.dbd_killer_status_temporal import (
    KillerEffectDefinition, KillerStatusTemporalProfile, KillerStatusTemporalStateMachines,
)
from ai_video_production.dbd_temporal_state import TemporalDecisionStatus
from ai_video_production.dbd_vision_slices import GrayImage


IMAGE = GrayImage(2, 2, bytes((0, 64, 128, 255)))


class FakeDetector:
    def __init__(self, detection: KillerSpecificDetection | None = None, *, fail: bool = False) -> None:
        self.detection = detection or KillerSpecificDetection(
            "KILLER_SPECIFIC_HUD/killer_onryo/condemn", True, 2, 300, 900
        )
        self.fail = fail
        self.calls: list[tuple[str, int | None]] = []

    def detect(self, image, *, capability, survivor_slot):
        assert image is IMAGE
        self.calls.append((capability.killer_id, survivor_slot))
        if self.fail:
            raise RuntimeError("synthetic detector failure")
        return self.detection


def identity(killer_id: str | None, confidence: int = 900, kind=KillerKnowledgeKind.KILLER):
    return KillerPowerVisualObservation(killer_id, confidence, kind)


def roi(slot: int) -> KillerSpecificRoiKey:
    return KillerSpecificRoiKey(KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY, slot)


def route(registry: KillerCapabilityRegistry, killer, images=None, evidence_refs=None):
    return registry.route(
        killer, match_id="match-1", frame_index=10, identity_evidence_ref="identity-10",
        images=images or {}, evidence_refs=evidence_refs or {},
    )


def test_initial_fixtures_have_exact_namespaces_and_cross_killer_hard_negatives() -> None:
    capabilities = initial_killer_capabilities()
    assert [(item.killer_id, item.effect_id) for item in capabilities] == [
        ("killer_ghost_face", "mark_progress"),
        ("killer_onryo", "condemn"),
        ("killer_doctor", "madness"),
    ]
    for item in capabilities:
        assert item.training_label_namespace == f"KILLER_SPECIFIC_HUD/{item.killer_id}/{item.effect_id}"
        assert len(item.hard_negative_namespaces) == 2
        assert all(item.killer_id not in value for value in item.hard_negative_namespaces)


def test_unknown_low_confidence_and_power_identity_never_invoke_specific_detectors() -> None:
    detector = FakeDetector()
    registry = KillerCapabilityRegistry(initial_killer_capabilities(), {
        ("killer_onryo", "condemn"): detector,
    })
    for observed in (
        identity(None),
        identity("killer_onryo", 799),
        identity("killer_bad-id", 900),
        identity("power_deluge_of_fear", 900, KillerKnowledgeKind.POWER),
    ):
        result = route(registry, observed, {roi(0): IMAGE}, {roi(0): "roi-0"})
        assert result.selected_killer_id is None
        assert registry.required_roi_keys(observed) == ()
        assert result.records[0].reason_codes == ("KILLER_IDENTITY_UNKNOWN",)
        assert result.observations[0].killer_id is None
    assert detector.calls == []


def test_known_killer_exposes_only_exact_required_roi_keys() -> None:
    registry = KillerCapabilityRegistry(initial_killer_capabilities(), {})
    assert registry.required_roi_keys(identity("killer_onryo")) == tuple(roi(slot) for slot in range(4))
    assert registry.required_roi_keys(identity("killer_trapper")) == ()


def test_exact_killer_routes_only_its_detector_and_preserves_four_survivor_subjects() -> None:
    ghost = FakeDetector(KillerSpecificDetection(
        "KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress", True, None, 650, 920
    ))
    onryo = FakeDetector()
    registry = KillerCapabilityRegistry(initial_killer_capabilities(), {
        ("killer_ghost_face", "mark_progress"): ghost,
        ("killer_onryo", "condemn"): onryo,
    })
    images = {roi(slot): IMAGE for slot in range(4)}
    refs = {roi(slot): f"portrait-{slot}" for slot in range(4)}
    result = route(registry, identity("killer_ghost_face"), images, refs)
    assert result.selected_killer_id == "killer_ghost_face"
    assert [item.survivor_slot for item in result.observations] == [0, 1, 2, 3]
    assert {item.effect_id for item in result.observations} == {"mark_progress"}
    assert [item.evidence_ref for item in result.observations] == [f"portrait-{slot}" for slot in range(4)]
    assert ghost.calls == [("killer_ghost_face", slot) for slot in range(4)]
    assert onryo.calls == []


def test_missing_roi_detector_unavailable_failure_and_low_confidence_fail_closed() -> None:
    capabilities = initial_killer_capabilities()
    onryo = next(item for item in capabilities if item.killer_id == "killer_onryo")
    for detector, expected in (
        (None, "DETECTOR_UNAVAILABLE"),
        (FakeDetector(fail=True), "DETECTOR_FAILED"),
        (FakeDetector(KillerSpecificDetection(
            "KILLER_SPECIFIC_HUD/killer_onryo/condemn", True, 2, 300, 699
        )), "DETECTION_CONFIDENCE_LOW"),
    ):
        detectors = {} if detector is None else {("killer_onryo", "condemn"): detector}
        registry = KillerCapabilityRegistry((onryo,), detectors)
        result = route(registry, identity("killer_onryo"), {roi(0): IMAGE}, {roi(0): "roi-0"})
        assert result.records[0].reason_codes == (expected,)
        assert result.records[0].observation.active is None
    missing = route(KillerCapabilityRegistry((onryo,), {}), identity("killer_onryo"))
    assert missing.records[0].reason_codes == ("REQUIRED_ROI_MISSING",)


def test_recognized_unregistered_killer_is_explicit_unknown() -> None:
    result = route(KillerCapabilityRegistry(initial_killer_capabilities(), {}), identity("killer_trapper"))
    assert result.selected_killer_id == "killer_trapper"
    assert result.records[0].reason_codes == ("KILLER_CAPABILITY_UNAVAILABLE",)
    assert result.observations[0].killer_id == "killer_trapper"
    assert result.observations[0].effect_id is None


def test_registry_output_feeds_r3c_temporal_consistency_without_cross_namespace_fallback() -> None:
    onryo = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    detector = FakeDetector(KillerSpecificDetection(
        "KILLER_SPECIFIC_HUD/killer_onryo/condemn", True, 2, 300, 900
    ))
    registry = KillerCapabilityRegistry((onryo,), {("killer_onryo", "condemn"): detector})
    result = route(registry, identity("killer_onryo"), {roi(0): IMAGE}, {roi(0): "roi-0"})
    profile = KillerStatusTemporalProfile(
        "r4a_temporal", 1,
        (KillerEffectDefinition("killer_onryo", "condemn", True, 7, True, True),), (),
    )
    machine = KillerStatusTemporalStateMachines(profile)
    first = machine.consume_killer(result.observations[0])
    second = machine.consume_killer(replace(result.observations[0], frame_index=11, evidence_ref="roi-0-11"))
    assert first.status is TemporalDecisionStatus.CANDIDATE
    assert second.status is TemporalDecisionStatus.CONFIRMED


def test_capability_rejects_namespace_drift_and_detector_without_contract() -> None:
    base = initial_killer_capabilities()[0]
    with pytest.raises(ValueError, match="exact killer/effect namespace"):
        replace(base, training_label_namespace="KILLER_SPECIFIC_HUD/killer_onryo/condemn")
    with pytest.raises(ValueError, match="matching capability"):
        KillerCapabilityRegistry((base,), {("killer_onryo", "condemn"): FakeDetector()})
    with pytest.raises(ValueError, match="requires a survivor_slot"):
        KillerSpecificRoiKey(KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY, None)
    with pytest.raises(ValueError, match="cannot carry"):
        KillerSpecificRoiKey(KillerRoiFamily.KILLER_POWER_HUD, 0)
    with pytest.raises(ValueError, match="cross-namespace"):
        KillerCapability(
            "killer_test", "effect", KillerEffectFamily.POWER_STATE,
            KillerRoiFamily.KILLER_POWER_HUD, KillerDetectorType.REFERENCE_SLICE,
            False, "KILLER_SPECIFIC_HUD/killer_test/effect", (),
        )
    with pytest.raises(ValueError, match="must agree"):
        replace(base, survivor_scoped=False)


def test_runtime_hard_negative_namespace_and_impossible_stage_abstain() -> None:
    onryo = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    hard_negative = FakeDetector(KillerSpecificDetection(
        "KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress", True, 2, 300, 900
    ))
    impossible = FakeDetector(KillerSpecificDetection(
        "KILLER_SPECIFIC_HUD/killer_onryo/condemn", True, 8, 900, 900
    ))
    for detector, reason in (
        (hard_negative, "HARD_NEGATIVE_NAMESPACE"),
        (impossible, "DETECTION_SEMANTICS_INVALID"),
    ):
        registry = KillerCapabilityRegistry((onryo,), {("killer_onryo", "condemn"): detector})
        result = route(registry, identity("killer_onryo"), {roi(0): IMAGE}, {roi(0): "roi-0"})
        assert result.records[0].reason_codes == (reason,)
        assert result.records[0].observation.active is None


def test_image_without_exact_evidence_reference_is_not_routed() -> None:
    onryo = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    detector = FakeDetector()
    registry = KillerCapabilityRegistry((onryo,), {("killer_onryo", "condemn"): detector})
    result = route(registry, identity("killer_onryo"), {roi(0): IMAGE})
    assert result.records[0].reason_codes == ("ROI_EVIDENCE_REF_MISSING",)
    assert detector.calls == []
