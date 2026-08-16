from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import inspect
import json
from pathlib import Path

import pytest

from ai_video_production.dbd_profile import (
    DBDProfilePluginSnapshot,
    DBDSignalFamily,
    DBDSignalKind,
    DBDSignalRule,
    compile_dbd_profile_plugin,
    verify_dbd_profile_snapshot_hash,
)
from ai_video_production.multimodal_scoring import (
    FeatureModality,
    FeaturePolarity,
    FeatureRule,
    FeatureSourceSelector,
    ScoringProfile,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64


def feature_rule(key: str, modality: FeatureModality, weight: int, task: str) -> FeatureRule:
    return FeatureRule(
        key,
        modality,
        weight,
        0,
        1000,
        FeaturePolarity.DIRECT,
        True,
        None,
        (FeatureSourceSelector(task, f"{key}.v1"),),
    )


def rules() -> tuple[DBDSignalRule, ...]:
    return (
        DBDSignalRule(
            DBDSignalKind.CHASE_INTENSITY,
            DBDSignalFamily.CHASE,
            feature_rule("dbd.chase_intensity", FeatureModality.AUDIO, 400, "TASK-006"),
        ),
        DBDSignalRule(
            DBDSignalKind.EVENT_HOOK,
            DBDSignalFamily.EVENT,
            feature_rule("dbd.event_hook", FeatureModality.LANGUAGE_TEXT, 250, "TASK-024"),
        ),
        DBDSignalRule(
            DBDSignalKind.HUD_GENERATOR_PROGRESS,
            DBDSignalFamily.HUD_STATE,
            feature_rule("dbd.hud_generator_progress", FeatureModality.VISUAL, 350, "TASK-005"),
        ),
    )


def snapshot() -> DBDProfilePluginSnapshot:
    return compile_dbd_profile_plugin("1.0.0", "1.0.0", rules())


def test_snapshot_is_deterministic_schema_valid_and_no_effect():
    first = snapshot().to_dict()
    second = snapshot().to_dict()
    assert first == second
    assert first["task_owner"] == "TASK-009"
    assert first["plugin"]["plugin_id"] == "dbd.multimodal-profile"
    assert first["runtime_feature_producer_state"] == "NOT_SELECTED"
    assert {row["family"] for row in first["signal_taxonomy"]} == {"HUD_STATE", "CHASE", "EVENT"}
    assert first["human_review_required"] is True
    for name in (
        "media_read_performed",
        "hud_detection_performed",
        "game_process_accessed",
        "automatic_edit_plan_mutation_authorized",
        "timeline_mutation_authorized",
        "external_effect_authorized",
    ):
        assert first[name] is False
    verify_dbd_profile_snapshot_hash(first)
    validate_instance(first, ROOT / "schemas" / "dbd-profile-plugin.schema.json")


def test_schema_mirror_is_byte_identical():
    public = (ROOT / "schemas" / "dbd-profile-plugin.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "dbd-profile-plugin.schema.json"
    ).read_bytes()
    assert public == packaged
    validate_instance(snapshot().to_dict(), json.loads(public))


def test_profile_exactly_reuses_task008_rules_without_duplicate_scoring_logic():
    compiled = snapshot()
    assert compiled.scoring_profile.rules == tuple(row.feature_rule for row in compiled.signal_rules)
    assert compiled.scoring_profile.to_dict()["profile_id"] == "dbd.multimodal-advisory"
    assert sum(row.feature_rule.weight_milli for row in compiled.signal_rules) == 1000
    assert len({row.feature_rule.modality for row in compiled.signal_rules}) == 3


def test_plugin_descriptor_is_closed_and_cannot_claim_core_mutation():
    descriptor = snapshot().descriptor
    descriptor.validate_boundary()
    assert descriptor.capabilities == (
        "DECLARE_MULTIMODAL_SCORING_PROFILE",
        "MAP_DBD_SIGNAL_TAXONOMY",
    )
    assert "MUTATE_JOB_STATE" not in descriptor.capabilities
    assert "DIRECT_NLE_WRITE" not in descriptor.capabilities


@pytest.mark.parametrize(
    ("kind", "family"),
    [
        (DBDSignalKind.CHASE_INTENSITY, DBDSignalFamily.HUD_STATE),
        (DBDSignalKind.EVENT_HOOK, DBDSignalFamily.CHASE),
        (DBDSignalKind.HUD_GENERATOR_PROGRESS, DBDSignalFamily.EVENT),
    ],
)
def test_signal_kind_cannot_be_laundered_into_wrong_family(kind, family):
    with pytest.raises(ValueError, match="does not belong"):
        DBDSignalRule(kind, family, rules()[0].feature_rule)


def test_closed_enums_reject_plain_strings():
    with pytest.raises(ValueError, match="DBDSignalKind"):
        replace(rules()[0], signal_kind="CHASE_INTENSITY")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="DBDSignalFamily"):
        replace(rules()[0], family="CHASE")  # type: ignore[arg-type]


def test_profile_requires_all_three_families_and_canonical_order():
    with pytest.raises(ValueError, match="cover"):
        compile_dbd_profile_plugin("1.0.0", "1.0.0", (rules()[0], rules()[1], replace(rules()[1], feature_rule=feature_rule("dbd.event_rescue", FeatureModality.VISUAL, 350, "TASK-005"))))
    with pytest.raises(ValueError, match="canonically sorted"):
        compile_dbd_profile_plugin("1.0.0", "1.0.0", tuple(reversed(rules())))


def test_projection_mismatch_rejects_manual_snapshot():
    rows = rules()
    altered = replace(rows[2], feature_rule=replace(rows[2].feature_rule, weight_milli=349))
    with pytest.raises(ValueError, match="projection"):
        DBDProfilePluginSnapshot("1.0.0", ScoringProfile("dbd.multimodal-advisory", "1.0.0", tuple(row.feature_rule for row in rows)), (rows[0], rows[1], altered))


def test_task008_profile_rules_still_enforce_weight_and_multimodal_closure():
    rows = rules()
    bad_weight = replace(rows[2], feature_rule=replace(rows[2].feature_rule, weight_milli=349))
    with pytest.raises(ValueError, match="sum"):
        compile_dbd_profile_plugin("1.0.0", "1.0.0", (rows[0], rows[1], bad_weight))
    audio_only = (
        rows[0],
        replace(rows[1], feature_rule=replace(rows[1].feature_rule, modality=FeatureModality.AUDIO)),
        replace(rows[2], feature_rule=replace(rows[2].feature_rule, modality=FeatureModality.AUDIO)),
    )
    with pytest.raises(ValueError, match="two modalities"):
        compile_dbd_profile_plugin("1.0.0", "1.0.0", audio_only)


def test_caps_and_versions_fail_closed():
    with pytest.raises(ValueError, match="semantic"):
        compile_dbd_profile_plugin("latest", "1.0.0", rules())
    with pytest.raises(ValueError, match="3-64"):
        compile_dbd_profile_plugin("1.0.0", "1.0.0", rules()[:2])
    with pytest.raises(ValueError, match="3-64"):
        compile_dbd_profile_plugin("1.0.0", "1.0.0", (rules()[0],) * 65)


def test_hash_verifier_rejects_tamper_and_nested_digest_rehash():
    payload = snapshot().to_dict()
    payload["signal_taxonomy"][0]["family"] = "HUD_STATE"
    with pytest.raises(ValueError, match="snapshot_sha256"):
        verify_dbd_profile_snapshot_hash(payload)

    payload = snapshot().to_dict()
    payload["scoring_profile"]["profile_sha256"] = SHA_A
    body = dict(payload)
    body.pop("snapshot_sha256")
    payload["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="scoring_profile.profile_sha256"):
        verify_dbd_profile_snapshot_hash(payload)


def test_snapshot_is_immutable():
    compiled = snapshot()
    with pytest.raises(FrozenInstanceError):
        compiled.plugin_version = "2.0.0"  # type: ignore[misc]


def test_public_surface_has_no_effect_capability():
    assert set(inspect.signature(compile_dbd_profile_plugin).parameters) == {
        "plugin_version", "profile_version", "signal_rules"
    }
    tree = ast.parse((ROOT / "src" / "ai_video_production" / "dbd_profile.py").read_text("utf-8"))
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint({"subprocess", "requests", "urllib", "httpx", "cv2", "pathlib"})
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile"})
