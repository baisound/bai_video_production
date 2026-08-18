from __future__ import annotations

from dataclasses import replace
from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.canonical_game_event import (
    CanonicalGameEvent,
    EventConfirmationState,
    EventReviewStatus,
    GameEnvironment,
    GameEventType,
    GameMatch,
    GameMatchStatus,
    GamePerspective,
)
from ai_video_production.dbd_perk_knowledge import (
    DBDPatchVersion,
    DbDPerkKnowledgeStore,
    PerkAlias,
    PerkAliasType,
    PerkEnvironment,
    PerkIdentity,
    PerkKnowledgeSource,
    PerkLocalization,
    PerkObservation,
    PerkObservationState,
    PerkRevision,
    PerkRevisionStatus,
    PerkRole,
    PerkSourceAuthority,
    normalize_perk_alias,
)
from ai_video_production.errors import ProductError
from ai_video_production.game_event_evidence import GameEvidence, GameEvidenceType, SourceFrameRange
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import sha256_bytes
from ai_video_production.timebase import FrameRate


def source(*, source_id: str = "src.patch.9.1.0", environment: PerkEnvironment | None = PerkEnvironment.LIVE, authority: PerkSourceAuthority = PerkSourceAuthority.OFFICIAL_PATCH_NOTE) -> PerkKnowledgeSource:
    return PerkKnowledgeSource(
        source_id=source_id,
        source_type="official_patch_note",
        authority=authority,
        environment=environment,
        uri="source://bhvr/patch/9.1.0",
        retrieved_at="2026-08-18T00:00:00Z",
        locale="en-US",
        content_sha256=sha256_bytes(b"synthetic source fixture" + source_id.encode()),
    )


def identity(*, perk_id: str = "perk_survivor_example", slug: str = "example") -> PerkIdentity:
    return PerkIdentity(perk_id=perk_id, slug=slug, role=PerkRole.SURVIVOR, introduced_version="8.0.0")


def revision(*, revision_id: str = "PERKREV-001", perk_id: str = "perk_survivor_example", version_from: str = "9.0.0", version_to: str | None = None, environment: PerkEnvironment = PerkEnvironment.LIVE, status: PerkRevisionStatus = PerkRevisionStatus.VERIFIED, source_ids: tuple[str, ...] = ("src.patch.9.1.0",)) -> PerkRevision:
    return PerkRevision(
        revision_id=revision_id,
        perk_id=perk_id,
        game_version_from=version_from,
        game_version_to_exclusive=version_to,
        environment=environment,
        status=status,
        source_ids=source_ids,
        official_effect_en="Synthetic verified effect for contract testing only.",
        structured_effect={"trigger": {"kind": "WINDOW_VAULT"}, "effects": [{"kind": "HASTE", "value": 1}]},
        tags=("CHASE", "WINDOW"),
    )


def populated_store(tmp_path: Path) -> DbDPerkKnowledgeStore:
    store = DbDPerkKnowledgeStore(tmp_path / "perk-knowledge.sqlite3")
    store.put_identity(identity())
    store.put_source(source())
    store.put_localization(PerkLocalization("perk_survivor_example", "en-US", "Example Perk", simple_text="Synthetic summary"))
    store.put_localization(PerkLocalization("perk_survivor_example", "ja-JP", "テストパーク", simple_text="テスト用説明"))
    store.put_alias(PerkAlias("alias.example.abbr", "perk_survivor_example", "en-US", "EP", PerkAliasType.ABBREVIATION, verified=True))
    store.put_alias(PerkAlias("alias.example.asr", "perk_survivor_example", "ja-JP", "てすとぱーく", PerkAliasType.ASR_VARIANT, verified=True))
    store.put_revision(revision())
    return store


def make_event(perk_store: DbDPerkKnowledgeStore | None = None) -> CanonicalGameEvent:
    game_match = GameMatch(
        production_job_id=generate_id(IdKind.JOB),
        source_asset_id=generate_id(IdKind.ASSET),
        game_profile_id="dead_by_daylight",
        game_profile_version="1.0.0",
        game_version="9.1.0",
        environment=GameEnvironment.LIVE,
        perspective=GamePerspective.SURVIVOR,
        source_rate=FrameRate(30000, 1001),
        status=GameMatchStatus.ANALYZING,
    )
    ev = GameEvidence(
        production_job_id=game_match.production_job_id,
        match_id=game_match.match_id,
        source_asset_id=game_match.source_asset_id,
        producer="task049.synthetic",
        producer_version="1.0.0",
        evidence_type=GameEvidenceType.VISION,
        source_range=SourceFrameRange(100, 110),
        confidence_milli=950,
    )
    return CanonicalGameEvent(
        match_id=game_match.match_id,
        revision=1,
        event_type=GameEventType.WINDOW_VAULT,
        source_range=ev.source_range,
        game_version=game_match.game_version,
        environment=game_match.environment,
        perspective=game_match.perspective,
        state={"fixture": True},
        confidence_milli=940,
        confirmation_state=EventConfirmationState.CONFIRMED,
        evidence_refs=(ev.game_evidence_id,),
        review_status=EventReviewStatus.AUTO_ACCEPTED,
    )


def test_patch_version_is_numeric_not_lexical() -> None:
    assert DBDPatchVersion.parse("9.10.0") > DBDPatchVersion.parse("9.2.0")
    assert str(DBDPatchVersion.parse("9.1.0.2")) == "9.1.0.2"
    with pytest.raises(ValueError, match="numeric"):
        DBDPatchVersion.parse("9.x")


def test_alias_normalization_handles_nfkc_case_and_space() -> None:
    assert normalize_perk_alias("  ＥＰ  ") == "ep"
    assert normalize_perk_alias("Test   Perk") == "test perk"


def test_store_exact_alias_and_localized_name_resolve_same_stable_perk_id(tmp_path: Path) -> None:
    store = populated_store(tmp_path)
    assert store.resolve_alias("EP", locale="en-US") == "perk_survivor_example"
    assert store.resolve_alias("ｅｐ", locale="en-US") == "perk_survivor_example"
    assert store.resolve_alias("テストパーク", locale="ja-JP") == "perk_survivor_example"
    assert store.resolve_alias("てすとぱーく", locale="ja-JP") == "perk_survivor_example"
    result = store.lookup("EP", game_version="9.1.0", environment=GameEnvironment.LIVE, locale="en-US")
    assert result.identity.perk_id == "perk_survivor_example"
    assert result.revision.revision_id == "PERKREV-001"
    assert {x.locale for x in result.localizations} == {"en-US", "ja-JP"}


def test_unverified_alias_is_not_authoritative_lookup(tmp_path: Path) -> None:
    store = populated_store(tmp_path)
    store.put_alias(PerkAlias("alias.unverified", "perk_survivor_example", "en-US", "maybe", PerkAliasType.COMMUNITY, verified=False))
    assert store.resolve_alias("maybe", locale="en-US") is None


def test_alias_ambiguity_fails_closed(tmp_path: Path) -> None:
    store = populated_store(tmp_path)
    store.put_identity(identity(perk_id="perk_survivor_other", slug="other"))
    store.put_alias(PerkAlias("alias.other.ep", "perk_survivor_other", "en-US", "EP", PerkAliasType.ABBREVIATION, verified=True))
    with pytest.raises(ProductError, match="multiple perk IDs"):
        store.resolve_alias("EP", locale="en-US")


def test_live_ptb_are_separate_and_patch_compatible_lookup_is_exact(tmp_path: Path) -> None:
    store = populated_store(tmp_path)
    ptb_source = source(source_id="src.ptb.9.2.0", environment=PerkEnvironment.PTB, authority=PerkSourceAuthority.GAME_CLIENT)
    store.put_source(ptb_source)
    store.put_revision(revision(revision_id="PERKREV-PTB-001", version_from="9.2.0", environment=PerkEnvironment.PTB, source_ids=(ptb_source.source_id,)))
    assert store.resolve_verified_revision("perk_survivor_example", game_version="9.2.0", environment=GameEnvironment.LIVE).revision_id == "PERKREV-001"
    assert store.resolve_verified_revision("perk_survivor_example", game_version="9.2.0", environment=GameEnvironment.PTB).revision_id == "PERKREV-PTB-001"
    with pytest.raises(ProductError, match="Game patch cannot"):
        store.resolve_verified_revision("perk_survivor_example", game_version="9.x", environment=GameEnvironment.LIVE)


def test_adjacent_verified_ranges_are_allowed_but_overlap_fails_closed(tmp_path: Path) -> None:
    store = DbDPerkKnowledgeStore(tmp_path / "db.sqlite3")
    store.put_identity(identity())
    store.put_source(source())
    store.put_revision(revision(revision_id="REV-A", version_from="9.0.0", version_to="9.2.0"))
    store.put_revision(revision(revision_id="REV-B", version_from="9.2.0", version_to="10.0.0"))
    assert store.resolve_verified_revision("perk_survivor_example", game_version="9.1.9", environment=GameEnvironment.LIVE).revision_id == "REV-A"
    assert store.resolve_verified_revision("perk_survivor_example", game_version="9.2.0", environment=GameEnvironment.LIVE).revision_id == "REV-B"
    with pytest.raises(ProductError, match="overlapping patch ranges"):
        store.put_revision(revision(revision_id="REV-C", version_from="9.1.0", version_to="9.3.0"))


def test_verified_revision_requires_compatible_non_unknown_source_provenance(tmp_path: Path) -> None:
    store = DbDPerkKnowledgeStore(tmp_path / "db.sqlite3")
    store.put_identity(identity())
    unknown = source(source_id="src.unknown", environment=PerkEnvironment.LIVE, authority=PerkSourceAuthority.UNKNOWN)
    store.put_source(unknown)
    with pytest.raises(ProductError, match="compatible non-UNKNOWN"):
        store.put_revision(revision(source_ids=(unknown.source_id,)))

    ptb = source(source_id="src.ptb", environment=PerkEnvironment.PTB)
    store.put_source(ptb)
    with pytest.raises(ProductError, match="compatible non-UNKNOWN"):
        store.put_revision(revision(revision_id="REV-LIVE-FROM-PTB", source_ids=(ptb.source_id,)))


def test_event_binding_adds_revisioned_reference_not_mutable_effect_text(tmp_path: Path) -> None:
    store = populated_store(tmp_path)
    event = make_event()
    bound = store.bind_event(event, "perk_survivor_example")
    assert bound.event_id == event.event_id
    assert bound.revision == 2
    assert len(bound.knowledge_refs) == 1
    ref = bound.knowledge_refs[0]
    assert ref.entity_id == "perk_survivor_example"
    assert ref.revision_id == "PERKREV-001"
    assert ref.source_provenance_ref == "perk-revision://PERKREV-001"
    payload = bound.to_dict()
    assert "Synthetic verified effect" not in str(payload)
    assert store.bind_event(bound, "perk_survivor_example") is bound


def test_perk_observation_separates_unknown_candidate_and_resolved_revision(tmp_path: Path) -> None:
    store = populated_store(tmp_path)
    match_id = generate_id(IdKind.GAME_MATCH)
    evidence_ref = generate_id(IdKind.GAME_EVIDENCE)
    unknown = PerkObservation(match_id, 1, evidence_ref, 400, PerkObservationState.UNKNOWN)
    assert store.resolve_observation(unknown, GameEnvironment.LIVE, "9.1.0") is unknown

    candidate = PerkObservation(match_id, 2, evidence_ref, 880, PerkObservationState.CANDIDATE, perk_id="perk_survivor_example")
    resolved = store.resolve_observation(candidate, GameEnvironment.LIVE, "9.1.0")
    assert resolved.state is PerkObservationState.RESOLVED
    assert resolved.resolved_revision_id == "PERKREV-001"
    with pytest.raises(ValueError, match="UNKNOWN observation"):
        replace(unknown, perk_id="perk_survivor_example")


def test_store_rejects_foreign_unversioned_and_newer_sqlite(tmp_path: Path) -> None:
    import sqlite3

    foreign = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(foreign) as connection:
        connection.execute("CREATE TABLE alien(id TEXT)")
    with pytest.raises(ProductError, match="unversioned"):
        DbDPerkKnowledgeStore(foreign)

    newer = tmp_path / "newer.sqlite3"
    with sqlite3.connect(newer) as connection:
        connection.execute("PRAGMA user_version = 99")
    with pytest.raises(ProductError, match="newer"):
        DbDPerkKnowledgeStore(newer)


def test_revision_reinsert_is_idempotent_before_overlap_check(tmp_path: Path) -> None:
    store = DbDPerkKnowledgeStore(tmp_path / "db.sqlite3")
    store.put_identity(identity())
    store.put_source(source())
    item = revision()
    store.put_revision(item)
    store.put_revision(item)
    assert store.resolve_verified_revision("perk_survivor_example", game_version="9.1.0", environment=GameEnvironment.LIVE).revision_id == "PERKREV-001"


def test_alias_index_tamper_fails_closed(tmp_path: Path) -> None:
    import sqlite3

    store = populated_store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE perk_aliases SET normalized_alias='corrupted' WHERE alias_id='alias.example.abbr'")
    # Original value no longer matches the index and therefore cannot resolve.
    assert store.resolve_alias("EP", locale="en-US") is None
    # Corrupted indexed value is detected against the canonical payload/hash.
    with pytest.raises(ProductError, match="index does not match"):
        store.resolve_alias("corrupted", locale="en-US")


def test_verified_lookup_revalidates_source_payload_hash(tmp_path: Path) -> None:
    import sqlite3

    store = populated_store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        row = connection.execute("SELECT payload_json FROM perk_sources WHERE source_id='src.patch.9.1.0'").fetchone()
        payload = row[0].replace('OFFICIAL_PATCH_NOTE', 'UNKNOWN')
        connection.execute("UPDATE perk_sources SET payload_json=? WHERE source_id='src.patch.9.1.0'", (payload,))
    with pytest.raises(ProductError, match="payload/hash is corrupt"):
        store.resolve_verified_revision("perk_survivor_example", game_version="9.1.0", environment=GameEnvironment.LIVE)


ROOT = Path(__file__).resolve().parents[1]
PERK_SCHEMA_NAMES = (
    "perk-identity.schema.json",
    "perk-localization.schema.json",
    "perk-alias.schema.json",
    "perk-source.schema.json",
    "perk-revision.schema.json",
    "perk-observation.schema.json",
)


def test_perk_contract_schemas_validate_and_package_mirrors_match(tmp_path: Path) -> None:
    identity_item = identity()
    source_item = source()
    localization_item = PerkLocalization("perk_survivor_example", "en-US", "Example Perk")
    alias_item = PerkAlias("alias.example.schema", "perk_survivor_example", "en-US", "EP", PerkAliasType.ABBREVIATION, verified=True)
    revision_item = revision()
    observation_item = PerkObservation(generate_id(IdKind.GAME_MATCH), 1, generate_id(IdKind.GAME_EVIDENCE), 800, PerkObservationState.CANDIDATE, perk_id="perk_survivor_example")
    payloads = {
        "perk-identity.schema.json": identity_item.to_dict(),
        "perk-localization.schema.json": localization_item.to_dict(),
        "perk-alias.schema.json": alias_item.to_dict(),
        "perk-source.schema.json": source_item.to_dict(),
        "perk-revision.schema.json": revision_item.to_dict(),
        "perk-observation.schema.json": observation_item.to_dict(),
    }
    from jsonschema import Draft202012Validator

    for name in PERK_SCHEMA_NAMES:
        public = (ROOT / "schemas" / name).read_bytes()
        packaged = resources.files("ai_video_production").joinpath("schema_resources", name).read_bytes()
        assert public == packaged
        Draft202012Validator.check_schema(json.loads(public))
        validate_instance(payloads[name], ROOT / "schemas" / name)
