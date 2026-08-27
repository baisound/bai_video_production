from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_dataset_adoption_authority import (
    DatasetAdoptionRequest,
)
from ai_video_production.dbd_reasoning_dataset_adoption_preflight import (
    AUTHORITY_SCOPE,
    AUTHORITY_STATE,
    PLAN_STATE,
    DatasetAdoptionPreflightAuthority,
    DatasetManifestRead,
    DatasetStoreCapability,
    admit_dataset_adoption_commit_plan,
    admit_dataset_adoption_preflight_authority,
    build_dataset_adoption_execution_preflight,
)
from ai_video_production.dbd_reasoning_dataset_manifest import (
    ConsentDecision,
    DatasetRowDisposition,
    DatasetSplit,
    DbDReasoningDatasetRightsEntry,
    DbDReasoningDatasetRightsManifest,
    RightsDecision,
)
from ai_video_production.errors import ProductError


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64
SHA_F = "sha256:" + "f" * 64
MANIFEST = "MAN-" + "0" * 26
NOW = "2026-08-27T10:00:00Z"


def _ref(scheme: str, character: str) -> str:
    return f"{scheme}://sha256/{character * 64}"


def _entry(
    suffix: str,
    *,
    split: DatasetSplit,
    eligible: bool = True,
) -> DbDReasoningDatasetRightsEntry:
    rights = RightsDecision.ADMITTED_FOR_TRAINING if eligible else RightsDecision.REJECTED
    disposition = (
        DatasetRowDisposition.ELIGIBLE_CANDIDATE
        if eligible
        else DatasetRowDisposition.REJECTED
    )
    return DbDReasoningDatasetRightsEntry(
        candidate_id="CAND-R2D" + suffix * 23,
        candidate_sha256=SHA_A,
        lineage_sha256=SHA_B,
        human_review_sha256=SHA_C,
        human_review_ref=_ref("human-review", "c"),
        match_id="MATCH-" + suffix * 26,
        source_group_id=f"group/{split.value.lower()}/{suffix}",
        source_ref=_ref("media", "d"),
        split=split,
        patch_version="9.1.0",
        locale="ja-JP",
        rights_decision=rights,
        rights_ref=_ref("rights", "e"),
        consent_decision=ConsentDecision.EXPLICIT_TRAINING,
        consent_ref=_ref("consent", "f"),
        provenance_ref=_ref("provenance", "a"),
        disposition=disposition,
        reason_codes=() if eligible else ("RIGHTS_REJECTED",),
    )


def _manifest(*, eligible: bool = True) -> DbDReasoningDatasetRightsManifest:
    entries = (
        _entry("0", split=DatasetSplit.TRAIN, eligible=eligible),
        _entry("1", split=DatasetSplit.VALIDATION, eligible=eligible),
        _entry("2", split=DatasetSplit.TEST, eligible=False),
    )
    return DbDReasoningDatasetRightsManifest(
        manifest_id=MANIFEST,
        revision=3,
        entries=entries,
    )


def _request(manifest: DbDReasoningDatasetRightsManifest) -> DatasetAdoptionRequest:
    return DatasetAdoptionRequest(
        request_id="request/r6bc/001",
        authorization_sha256=SHA_A,
        authority_evidence_sha256=SHA_B,
        preflight_sha256=SHA_C,
        manifest_id=manifest.manifest_id,
        revision=manifest.revision,
        rights_manifest_sha256=manifest.to_dict()["rights_manifest_sha256"],
        logical_path_sha256=SHA_D,
        observation_sha256=SHA_E,
        created_at="2026-08-27T08:00:00Z",
    )


def _authority(request: DatasetAdoptionRequest) -> DatasetAdoptionPreflightAuthority:
    return DatasetAdoptionPreflightAuthority(
        authorization_id="auth/r6bd/001",
        authority_evidence_sha256=SHA_C,
        request_sha256=request.to_dict()["request_sha256"],
        manifest_id=request.manifest_id,
        revision=request.revision,
        rights_manifest_sha256=request.rights_manifest_sha256,
        logical_path_sha256=request.logical_path_sha256,
        observation_sha256=request.observation_sha256,
        dataset_store_id="store/dbd-reasoning/canonical",
        expected_store_sha256=SHA_F,
        not_before="2026-08-27T09:00:00Z",
        expires_at="2026-08-27T11:00:00Z",
    )


class Verifier:
    def __init__(self, trusted: bool = True) -> None:
        self.trusted = trusted
        self.calls: list[tuple[str, str]] = []

    def verify(self, evidence_sha256: str, authorization_sha256: str) -> bool:
        self.calls.append((evidence_sha256, authorization_sha256))
        return self.trusted


class ManifestReader:
    def __init__(
        self,
        manifest: DbDReasoningDatasetRightsManifest,
        *,
        logical_path_sha256: str = SHA_D,
        observation_sha256: str = SHA_E,
    ) -> None:
        self.manifest = manifest
        self.logical_path_sha256 = logical_path_sha256
        self.observation_sha256 = observation_sha256
        self.calls: list[tuple[str, int]] = []

    def read_current_manifest(self, manifest_id: str, revision: int) -> DatasetManifestRead:
        self.calls.append((manifest_id, revision))
        return DatasetManifestRead(
            logical_path_sha256=self.logical_path_sha256,
            observation_sha256=self.observation_sha256,
            manifest_record=self.manifest.to_dict(),
        )


class CapabilityReader:
    def __init__(self, capability: DatasetStoreCapability | object | None = None) -> None:
        self.value = capability or DatasetStoreCapability(
            dataset_store_id="store/dbd-reasoning/canonical",
            current_store_sha256=SHA_F,
            encrypted_at_rest=True,
            atomic_compare_and_swap=True,
            authoritative_read_back=True,
            append_only_revisions=True,
            one_shot_authority_evidence=True,
        )
        self.calls = 0

    def read_capability(self) -> object:
        self.calls += 1
        return self.value


def _build(
    *,
    manifest: DbDReasoningDatasetRightsManifest | None = None,
    authority: DatasetAdoptionPreflightAuthority | None = None,
    verifier: Verifier | None = None,
    reader: ManifestReader | None = None,
    capability_reader: CapabilityReader | None = None,
    now: str = NOW,
):
    current = manifest or _manifest()
    request = _request(current)
    return build_dataset_adoption_execution_preflight(
        request.to_dict(),
        (authority or _authority(request)).to_dict(),
        plan_id="plan/r6bd/001",
        now=now,
        authority_verifier=verifier or Verifier(),
        manifest_reader=reader or ManifestReader(current),
        store_capability_reader=capability_reader or CapabilityReader(),
    )


def test_read_only_plan_contains_only_current_eligible_memberships() -> None:
    manifest = _manifest()
    plan = _build(manifest=manifest)

    assert tuple(item.candidate_id for item in plan.memberships) == (
        "CAND-R2D" + "0" * 23,
        "CAND-R2D" + "1" * 23,
    )
    assert (plan.member_count, plan.train_count, plan.validation_count, plan.test_count) == (
        2,
        1,
        1,
        0,
    )
    assert plan.plan_state == PLAN_STATE
    assert plan.dataset_adoption_requested is True
    assert plan.dataset_adoption_started is False
    assert plan.dataset_store_mutated is False
    assert plan.training_authorized is False
    assert plan.training_started is False
    assert admit_dataset_adoption_commit_plan(plan.to_dict()) == plan
    public = json.dumps(plan.to_dict())
    for forbidden in (
        "raw_path",
        "manifest.json",
        "transcript",
        "narration",
        "media_body",
        "commit_once",
    ):
        assert forbidden not in public


def test_exact_inputs_are_deterministic_and_do_not_consume_authority() -> None:
    manifest = _manifest()
    request = _request(manifest)
    authority = _authority(request)
    verifier = Verifier()
    reader = ManifestReader(manifest)
    capability_reader = CapabilityReader()
    kwargs = dict(
        plan_id="plan/r6bd/001",
        now=NOW,
        authority_verifier=verifier,
        manifest_reader=reader,
        store_capability_reader=capability_reader,
    )
    first = build_dataset_adoption_execution_preflight(
        request.to_dict(), authority.to_dict(), **kwargs
    )
    second = build_dataset_adoption_execution_preflight(
        request.to_dict(), authority.to_dict(), **kwargs
    )
    assert first.to_dict() == second.to_dict()
    assert len(verifier.calls) == len(reader.calls) == capability_reader.calls == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_sha256", SHA_A),
        ("manifest_id", "MAN-" + "1" * 26),
        ("revision", 4),
        ("rights_manifest_sha256", SHA_A),
        ("logical_path_sha256", SHA_A),
        ("observation_sha256", SHA_A),
    ],
)
def test_crossed_authority_fails_before_any_reader(
    field: str,
    value: object,
) -> None:
    manifest = _manifest()
    request = _request(manifest)
    authority = replace(_authority(request), **{field: value})
    verifier = Verifier()
    reader = ManifestReader(manifest)
    capability_reader = CapabilityReader()
    with pytest.raises(ProductError) as caught:
        _build(
            manifest=manifest,
            authority=authority,
            verifier=verifier,
            reader=reader,
            capability_reader=capability_reader,
        )
    assert caught.value.code == "ERR_DBD_R6BD_AUTHORITY_CROSSED"
    assert verifier.calls == reader.calls == []
    assert capability_reader.calls == 0


@pytest.mark.parametrize("now", ["2026-08-27T08:59:59Z", "2026-08-27T11:00:00Z"])
def test_inactive_authority_fails_before_any_reader(now: str) -> None:
    verifier = Verifier()
    reader = ManifestReader(_manifest())
    capability_reader = CapabilityReader()
    with pytest.raises(ProductError) as caught:
        _build(verifier=verifier, reader=reader, capability_reader=capability_reader, now=now)
    assert caught.value.code == "ERR_DBD_R6BD_AUTHORITY_INACTIVE"
    assert verifier.calls == reader.calls == []
    assert capability_reader.calls == 0


def test_untrusted_authority_fails_before_store_or_manifest_read() -> None:
    verifier = Verifier(False)
    reader = ManifestReader(_manifest())
    capability_reader = CapabilityReader()
    with pytest.raises(ProductError) as caught:
        _build(verifier=verifier, reader=reader, capability_reader=capability_reader)
    assert caught.value.code == "ERR_DBD_R6BD_AUTHORITY_UNTRUSTED"
    assert len(verifier.calls) == 1
    assert reader.calls == []
    assert capability_reader.calls == 0


@pytest.mark.parametrize(
    "field",
    [
        "encrypted_at_rest",
        "atomic_compare_and_swap",
        "authoritative_read_back",
        "append_only_revisions",
        "one_shot_authority_evidence",
    ],
)
def test_store_capability_floor_fails_before_manifest_read(field: str) -> None:
    capability = DatasetStoreCapability(
        dataset_store_id="store/dbd-reasoning/canonical",
        current_store_sha256=SHA_F,
        encrypted_at_rest=True,
        atomic_compare_and_swap=True,
        authoritative_read_back=True,
        append_only_revisions=True,
        one_shot_authority_evidence=True,
    )
    capability_reader = CapabilityReader(replace(capability, **{field: False}))
    reader = ManifestReader(_manifest())
    with pytest.raises(ProductError) as caught:
        _build(reader=reader, capability_reader=capability_reader)
    assert caught.value.code == "ERR_DBD_R6BD_STORE_CAPABILITY_INSUFFICIENT"
    assert reader.calls == []


def test_crossed_or_invalid_store_capability_fails_closed() -> None:
    crossed = CapabilityReader(
        DatasetStoreCapability(
            dataset_store_id="store/other",
            current_store_sha256=SHA_F,
            encrypted_at_rest=True,
            atomic_compare_and_swap=True,
            authoritative_read_back=True,
            append_only_revisions=True,
            one_shot_authority_evidence=True,
        )
    )
    with pytest.raises(ProductError) as caught:
        _build(capability_reader=crossed)
    assert caught.value.code == "ERR_DBD_R6BD_STORE_CAPABILITY_INSUFFICIENT"
    with pytest.raises(ProductError) as caught:
        _build(capability_reader=CapabilityReader(object()))
    assert caught.value.code == "ERR_DBD_R6BD_STORE_CAPABILITY_INVALID"


def test_stale_store_head_fails_before_manifest_read() -> None:
    capability = DatasetStoreCapability(
        dataset_store_id="store/dbd-reasoning/canonical",
        current_store_sha256=SHA_A,
        encrypted_at_rest=True,
        atomic_compare_and_swap=True,
        authoritative_read_back=True,
        append_only_revisions=True,
        one_shot_authority_evidence=True,
    )
    reader = ManifestReader(_manifest())
    with pytest.raises(ProductError) as caught:
        _build(reader=reader, capability_reader=CapabilityReader(capability))
    assert caught.value.code == "ERR_DBD_R6BD_STORE_HEAD_DRIFT"
    assert reader.calls == []


def test_manifest_location_or_body_drift_fails_closed() -> None:
    manifest = _manifest()
    with pytest.raises(ProductError) as caught:
        _build(manifest=manifest, reader=ManifestReader(manifest, observation_sha256=SHA_A))
    assert caught.value.code == "ERR_DBD_R6BD_MANIFEST_LOCATION_DRIFT"

    forged = manifest.to_dict()
    forged["rights_manifest_sha256"] = SHA_A
    reader = ManifestReader(manifest)
    reader.manifest = type("Forged", (), {"to_dict": lambda self: forged})()
    with pytest.raises(ProductError) as caught:
        _build(manifest=manifest, reader=reader)
    assert caught.value.code == "ERR_DBD_R6BD_MANIFEST_INVALID"


def test_zero_current_eligible_members_requires_human_review() -> None:
    manifest = _manifest(eligible=False)
    with pytest.raises(ProductError) as caught:
        _build(manifest=manifest)
    assert caught.value.code == "ERR_DBD_R6BD_NO_ELIGIBLE_MEMBERS"


def test_authority_and_plan_schema_are_exact_and_mirrored() -> None:
    root = Path(__file__).resolve().parents[1]
    canonical = root / "schemas" / "dbd-reasoning-dataset-adoption-preflight.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / canonical.name
    assert canonical.read_bytes() == mirror.read_bytes()
    validator = Draft202012Validator(
        json.loads(canonical.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    manifest = _manifest()
    request = _request(manifest)
    authority = _authority(request)
    plan = _build(manifest=manifest)
    assert admit_dataset_adoption_preflight_authority(authority.to_dict()) == authority
    assert list(validator.iter_errors(authority.to_dict())) == []
    assert list(validator.iter_errors(plan.to_dict())) == []

    forged = plan.to_dict()
    forged["dataset_store_mutated"] = True
    with pytest.raises(ValueError):
        admit_dataset_adoption_commit_plan(forged)
    extended = plan.to_dict()
    extended["raw_path"] = "C:/private/dataset"
    with pytest.raises(ValueError):
        admit_dataset_adoption_commit_plan(extended)
    assert AUTHORITY_SCOPE == "DATASET_ADOPTION_READ_ONLY_PREFLIGHT"
    assert AUTHORITY_STATE == "ALLOWED_READ_ONLY_DATASET_ADOPTION_PREFLIGHT"


def test_plan_readmission_rejects_source_group_split_crossing() -> None:
    plan = _build()
    crossed_memberships = (
        plan.memberships[0],
        replace(plan.memberships[1], source_group_id=plan.memberships[0].source_group_id),
    )
    with pytest.raises(ValueError, match="source group"):
        replace(plan, memberships=crossed_memberships)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("authority_verifier", None),
        ("manifest_reader", None),
        ("store_capability_reader", None),
    ],
)
def test_required_read_only_collaborators_fail_closed(name: str, value: object) -> None:
    manifest = _manifest()
    request = _request(manifest)
    kwargs = {
        "plan_id": "plan/r6bd/001",
        "now": NOW,
        "authority_verifier": Verifier(),
        "manifest_reader": ManifestReader(manifest),
        "store_capability_reader": CapabilityReader(),
    }
    kwargs[name] = value
    with pytest.raises(ValueError, match=name):
        build_dataset_adoption_execution_preflight(
            request.to_dict(),
            _authority(request).to_dict(),
            **kwargs,
        )
