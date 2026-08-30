from __future__ import annotations

import ast
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from ai_video_production.montage_learning_connector_readiness import (
    MontageLearningConnectorReadinessError,
    ProfileSourceBinding,
    publish_prebuilt_advisory_profile,
    validate_prebuilt_advisory_profile,
)
from ai_video_production.montage_preference_source import (
    PreferencePromotionSourceError,
    PromotedPreferenceSource,
    PromotedPreferenceSourceCoordinates,
    PromotedPreferenceSourceRead,
    coordinates_from_verified_history,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from test_montage_preference_promotion_store import SyntheticCipher, _first, _second
from test_task058_montage_learning_file_bridge import _layout


SOURCE_ID = "task060.preference-source.production"


def _source(path: Path):
    store, saved, _, _ = _first(path)
    coordinates = coordinates_from_verified_history(
        source_id=SOURCE_ID,
        history=saved.history,
    )
    return store, saved, PromotedPreferenceSource(path, SyntheticCipher(), coordinates)


def test_exact_pinned_source_read_and_task058_contract_are_byte_equivalent(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    _, saved, source = _source(path)
    readback = source.read_current()
    expected = saved.history.active_envelope
    assert canonical_json_bytes(readback.envelope) == canonical_json_bytes(expected)
    assert canonical_json_bytes(validate_prebuilt_advisory_profile(readback.envelope)) == canonical_json_bytes(expected)
    assert readback.active_payload_sha256 == expected["profile_sha256"]
    assert readback.envelope_sha256 == sha256_bytes(canonical_json_bytes(expected))
    assert readback.production_source_bound is True
    document = readback.to_dict()
    assert document["exact_current_source_verified"] is True
    assert document["production_profile_source_bound"] is True
    assert document["advisory_profile_only"] is True
    for field in (
        "automatic_promotion_authorized", "timeline_mutation_authorized",
        "resolve_write_authorized", "external_effect_authorized",
    ):
        assert document[field] is False


def test_verified_source_mints_sealed_binding_and_publishes_synthetic_fixture(tmp_path: Path) -> None:
    _, _, source = _source(tmp_path / "preference-promotions.json")
    readback = source.read_current()
    binding = ProfileSourceBinding.bound_verified_production(readback)
    assert binding.source_id == SOURCE_ID
    assert binding.production_profile_source_bound is True
    assert binding.isolated_fixture is False
    assert binding.envelope_sha256 == readback.envelope_sha256
    layout = _layout(tmp_path / "bridge")
    result = publish_prebuilt_advisory_profile(
        layout,
        readback.envelope,
        source_binding=binding,
    )
    assert result.status == "PUBLISHED"
    assert result.production_profile_source_bound is True
    assert result.semantic_projection_generated is False
    assert result.timeline_mutation_authorized is False
    assert result.resolve_write_authorized is False
    assert canonical_json_bytes(json.loads(layout.current_profile.read_text(encoding="utf-8"))) == canonical_json_bytes(readback.envelope)


def test_binding_is_exact_envelope_not_transferable_capability(tmp_path: Path) -> None:
    _, _, source = _source(tmp_path / "preference-promotions.json")
    readback = source.read_current()
    binding = ProfileSourceBinding.bound_verified_production(readback)
    changed = deepcopy(readback.envelope)
    changed["profile_version"] += 100
    layout = _layout(tmp_path / "bridge")
    with pytest.raises(MontageLearningConnectorReadinessError, match="exact envelope"):
        publish_prebuilt_advisory_profile(layout, changed, source_binding=binding)
    assert not layout.current_profile.exists()


def test_mutated_readback_cannot_mint_production_binding(tmp_path: Path) -> None:
    _, _, source = _source(tmp_path / "preference-promotions.json")
    readback = source.read_current()
    readback.envelope["profile_version"] += 1
    with pytest.raises(ValueError, match="envelope_sha256|read-back"):
        ProfileSourceBinding.bound_verified_production(readback)


def test_source_readback_cannot_be_minted_by_a_caller(tmp_path: Path) -> None:
    _, _, source = _source(tmp_path / "preference-promotions.json")
    readback = source.read_current()
    values = {
        field: getattr(readback, field)
        for field in (
            "source_id", "source_file_identity_sha256", "store_id",
            "owner_scope_sha256", "promotion_revision",
            "promotion_revision_sha256", "history_sha256", "profile_id",
            "profile_version", "active_payload_sha256", "envelope",
            "envelope_sha256", "readback_sha256",
        )
    }
    with pytest.raises(TypeError, match="pinned source port"):
        PromotedPreferenceSourceRead(**values, _token=object())


def test_stale_revision_history_and_payload_coordinates_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    store, first, source = _source(path)
    _second(store, first.history)
    with pytest.raises(PreferencePromotionSourceError, match="stale|substituted"):
        source.read_current()
    current = store.load()
    exact = coordinates_from_verified_history(source_id=SOURCE_ID, history=current)
    for field, value in (
        ("promotion_revision", exact.promotion_revision + 1),
        ("promotion_revision_sha256", "sha256:" + "1" * 64),
        ("history_sha256", "sha256:" + "2" * 64),
        ("active_payload_sha256", "sha256:" + "3" * 64),
    ):
        values = {
            "source_id": exact.source_id,
            "store_id": exact.store_id,
            "owner_scope_sha256": exact.owner_scope_sha256,
            "promotion_revision": exact.promotion_revision,
            "promotion_revision_sha256": exact.promotion_revision_sha256,
            "history_sha256": exact.history_sha256,
            "active_payload_sha256": exact.active_payload_sha256,
        }
        values[field] = value
        drift = PromotedPreferenceSourceCoordinates(**values)
        with pytest.raises(PreferencePromotionSourceError, match="stale|substituted"):
            PromotedPreferenceSource(path, SyntheticCipher(), drift).read_current()


def test_path_substitution_after_pinned_read_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    _, _, source = _source(path)
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(path.read_bytes())

    def substitute(stage: str, target: Path) -> None:
        if stage == "after_read":
            os.replace(replacement, target)

    # Windows may deny replacement while the pinned handle is open; Unix permits
    # it and the post-read identity check rejects the substituted path.
    with pytest.raises(PreferencePromotionSourceError, match="substituted|read failed"):
        source.read_current(hook=substitute)


def test_final_and_ancestor_reparse_and_hardlink_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    _, saved, _ = _source(path)
    coordinates = coordinates_from_verified_history(source_id=SOURCE_ID, history=saved.history)
    link = tmp_path / "link.json"
    try:
        link.symlink_to(path)
    except OSError:
        pass
    else:
        with pytest.raises(PreferencePromotionSourceError, match="non-reparse"):
            PromotedPreferenceSource(link, SyntheticCipher(), coordinates).read_current()
    ancestor_target = tmp_path / "actual"
    ancestor_target.mkdir()
    nested = ancestor_target / "source.json"
    nested.write_bytes(path.read_bytes())
    ancestor_link = tmp_path / "ancestor-link"
    try:
        ancestor_link.symlink_to(ancestor_target, target_is_directory=True)
    except OSError:
        pass
    else:
        with pytest.raises(PreferencePromotionSourceError, match="ancestor"):
            PromotedPreferenceSource(
                ancestor_link / "source.json", SyntheticCipher(), coordinates
            ).read_current()
    hardlink = tmp_path / "hardlink.json"
    try:
        os.link(path, hardlink)
    except OSError:
        pass
    else:
        with pytest.raises(PreferencePromotionSourceError, match="hardlinked"):
            PromotedPreferenceSource(path, SyntheticCipher(), coordinates).read_current()


def test_wrong_cipher_corrupt_and_unknown_source_identity_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "preference-promotions.json"
    _, saved, source = _source(path)
    coordinates = coordinates_from_verified_history(source_id=SOURCE_ID, history=saved.history)
    with pytest.raises(PreferencePromotionSourceError, match="admission"):
        PromotedPreferenceSource(path, SyntheticCipher(0x31), coordinates).read_current()
    path.write_bytes(b"{}")
    with pytest.raises(PreferencePromotionSourceError, match="admission"):
        source.read_current()
    with pytest.raises(ValueError, match="source_id"):
        coordinates_from_verified_history(source_id="bad source", history=saved.history)


def test_production_source_module_has_no_write_or_runtime_authority_imports() -> None:
    source = Path(__file__).resolve().parents[1].joinpath(
        "src/ai_video_production/montage_preference_source.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint(
        {
            "subprocess", "socket", "requests", "montage_learning_file_bridge",
            "timeline", "resolve",
        }
    )
    assert "AtomicJsonWriter" not in source
    assert "publish_current_profile" not in source
