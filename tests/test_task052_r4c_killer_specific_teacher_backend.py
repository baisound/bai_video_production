from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_video_production.dbd_killer_capability_registry import (
    KillerCapabilityRegistry, KillerRoiFamily, KillerSpecificRoiKey, initial_killer_capabilities,
)
from ai_video_production.dbd_killer_knowledge import KillerKnowledgeKind, KillerPowerVisualObservation
from ai_video_production.dbd_killer_specific_detector import (
    KillerSpecificReferenceDetector, KillerSpecificTeacherLabel, KillerSpecificTeacherRole,
)
from ai_video_production.dbd_training_workspace import (
    VisualTrainingDomain, VisualTrainingManifest, VisualTrainingSample,
)
from ai_video_production.dbd_vision_slices import GrayImage, ReferenceSliceIndex


def _pgm(path: Path, seed: int) -> Path:
    pixels = bytearray()
    for y in range(16):
        for x in range(16):
            pixels.append(255 if ((x * (seed + 1) + y * (seed + 3) + seed) % 11) < 5 else 0)
    path.write_bytes(b"P5\n16 16\n255\n" + bytes(pixels))
    return path


def _sample(path: Path, *, role=KillerSpecificTeacherRole.POSITIVE, namespace=None) -> VisualTrainingSample:
    return VisualTrainingSample(
        domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD,
        label="condemn-stage-2" if role is KillerSpecificTeacherRole.POSITIVE else "ghost-face-hard-negative",
        image_path=str(path),
        group="positive" if role is KillerSpecificTeacherRole.POSITIVE else "hard-negative",
        source_ref="video://owned#frame=10&roi=survivor_slot_0",
        registration_origin="MANUAL_IMAGE",
        match_id="match-r4c",
        survivor_slot=0,
        killer_id="killer_onryo",
        effect_id="condemn",
        label_namespace=namespace or "KILLER_SPECIFIC_HUD/killer_onryo/condemn",
        teacher_role=role,
        active=True if role is KillerSpecificTeacherRole.POSITIVE else None,
        stage=2 if role is KillerSpecificTeacherRole.POSITIVE else None,
        progress_milli=300 if role is KillerSpecificTeacherRole.POSITIVE else None,
    )


def test_teacher_label_codec_is_canonical_and_rejects_invalid_role_state() -> None:
    label = KillerSpecificTeacherLabel(
        KillerSpecificTeacherRole.POSITIVE,
        "KILLER_SPECIFIC_HUD/killer_onryo/condemn",
        True, 2, 300,
    )
    assert KillerSpecificTeacherLabel.decode(label.encode()) == label
    with pytest.raises(ValueError, match="requires active"):
        KillerSpecificTeacherLabel(
            KillerSpecificTeacherRole.POSITIVE,
            "KILLER_SPECIFIC_HUD/killer_onryo/condemn",
            None, None, None,
        )
    with pytest.raises(ValueError, match="cannot carry"):
        KillerSpecificTeacherLabel(
            KillerSpecificTeacherRole.HARD_NEGATIVE,
            "KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress",
            True, None, None,
        )


def test_manifest_round_trips_positive_and_cross_killer_hard_negative(tmp_path: Path) -> None:
    positive = _sample(_pgm(tmp_path / "onryo.pgm", 1))
    negative = _sample(
        _pgm(tmp_path / "ghost.pgm", 2),
        role=KillerSpecificTeacherRole.HARD_NEGATIVE,
        namespace="KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress",
    )
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    assert manifest.append(positive) is True
    assert manifest.append(negative) is True
    restored = manifest.list(domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD)
    assert restored == (positive, negative)
    header = manifest.path.read_text(encoding="utf-8-sig").splitlines()[0]
    assert header.endswith("killer_id,effect_id,label_namespace,teacher_role,active,stage,progress_milli")


def test_existing_manifest_without_r4c_columns_remains_readable(tmp_path: Path) -> None:
    path = tmp_path / "legacy.csv"
    path.write_text(
        "domain,label,image_path,group,source_ref,notes,registration_origin,slot,display_state,source_video,source_frame,match_id,survivor_slot,signal_kind\n"
        "PERK_ICON,perk_a,C:/owned/perk.png,normal,manual://owner,,LEGACY,,,,,,,\n",
        encoding="utf-8-sig",
    )
    rows = VisualTrainingManifest(path).list()
    assert len(rows) == 1
    assert rows[0].domain is VisualTrainingDomain.PERK_ICON
    assert rows[0].killer_id == "" and rows[0].teacher_role is None


def test_killer_specific_sample_contract_rejects_namespace_and_scope_drift(tmp_path: Path) -> None:
    sample = _sample(_pgm(tmp_path / "sample.pgm", 1))
    with pytest.raises(ValueError, match="namespace must match"):
        replace(sample, label_namespace="KILLER_SPECIFIC_HUD/killer_doctor/madness")
    with pytest.raises(ValueError, match="different namespace"):
        replace(sample, teacher_role=KillerSpecificTeacherRole.HARD_NEGATIVE, active=None, stage=None, progress_milli=None)
    with pytest.raises(ValueError, match="survivor_slot"):
        replace(sample, survivor_slot=None)
    with pytest.raises(ValueError, match="require KILLER_SPECIFIC_HUD"):
        VisualTrainingSample(
            VisualTrainingDomain.PERK_ICON, "perk_a", str(sample.image_path),
            killer_id="killer_onryo",
        )


def test_namespaced_reference_detector_routes_positive_and_hard_negative(tmp_path: Path) -> None:
    positive_path = _pgm(tmp_path / "onryo.pgm", 1)
    negative_path = _pgm(tmp_path / "ghost.pgm", 8)
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    manifest.append(_sample(positive_path))
    manifest.append(_sample(
        negative_path,
        role=KillerSpecificTeacherRole.HARD_NEGATIVE,
        namespace="KILLER_SPECIFIC_HUD/killer_ghost_face/mark_progress",
    ))
    index_path = manifest.build_reference_index(
        domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD,
        output_path=tmp_path / "killer-specific-reference.json",
        index_id="killer-specific-reference",
        killer_capability_registry=KillerCapabilityRegistry(initial_killer_capabilities(), {}),
    )
    index = ReferenceSliceIndex.load(index_path)
    decoded = {KillerSpecificTeacherLabel.decode(item.label).role for item in index.references}
    assert decoded == {KillerSpecificTeacherRole.POSITIVE, KillerSpecificTeacherRole.HARD_NEGATIVE}

    capability = next(item for item in initial_killer_capabilities() if item.killer_id == "killer_onryo")
    detector = KillerSpecificReferenceDetector(index, acceptance_milli=500, ambiguity_margin_milli=0)
    registry = KillerCapabilityRegistry(
        (capability,), {(capability.killer_id, capability.effect_id): detector},
        detection_confidence_milli=500,
    )
    identity = KillerPowerVisualObservation("killer_onryo", 950, KillerKnowledgeKind.KILLER)
    key = KillerSpecificRoiKey(KillerRoiFamily.SURVIVOR_PORTRAIT_OVERLAY, 0)

    positive = registry.route(
        identity, match_id="match-r4c", frame_index=10, identity_evidence_ref="identity-10",
        images={key: GrayImage.read_pgm(positive_path)}, evidence_refs={key: "positive-10"},
    )
    assert positive.observations[0].active is True
    assert positive.observations[0].stage == 2
    assert positive.observations[0].progress_milli == 300

    negative = registry.route(
        identity, match_id="match-r4c", frame_index=11, identity_evidence_ref="identity-11",
        images={key: GrayImage.read_pgm(negative_path)}, evidence_refs={key: "negative-11"},
    )
    assert negative.records[0].reason_codes == ("HARD_NEGATIVE_NAMESPACE",)
    assert negative.observations[0].active is None


def test_killer_specific_index_requires_capability_binding_and_safe_coverage(tmp_path: Path) -> None:
    positive_path = _pgm(tmp_path / "onryo.pgm", 1)
    manifest = VisualTrainingManifest(tmp_path / "visual.csv")
    manifest.append(_sample(positive_path))
    with pytest.raises(ValueError, match="Capability Registry binding"):
        manifest.build_reference_index(
            domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD,
            output_path=tmp_path / "unsafe.json", index_id="unsafe",
        )
    registry = KillerCapabilityRegistry(initial_killer_capabilities(), {})
    with pytest.raises(ValueError, match="positive and hard-negative"):
        manifest.build_reference_index(
            domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD,
            output_path=tmp_path / "unsafe.json", index_id="unsafe",
            killer_capability_registry=registry,
        )
    invalid_negative = _sample(
        _pgm(tmp_path / "invalid-negative.pgm", 2),
        role=KillerSpecificTeacherRole.HARD_NEGATIVE,
        namespace="KILLER_SPECIFIC_HUD/killer_test/other_effect",
    )
    manifest.append(invalid_negative)
    with pytest.raises(ValueError, match="not registered"):
        manifest.build_reference_index(
            domain=VisualTrainingDomain.KILLER_SPECIFIC_HUD,
            output_path=tmp_path / "unsafe.json", index_id="unsafe",
            killer_capability_registry=registry,
        )
