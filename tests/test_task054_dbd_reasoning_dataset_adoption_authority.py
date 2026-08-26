from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from ai_video_production.dbd_reasoning_dataset_adoption_authority import (
    AUTHORITY_SCOPE,
    AUTHORITY_STATE,
    REQUEST_STATE,
    DatasetAdoptionAuthority,
    admit_dataset_adoption_authority,
    admit_dataset_adoption_request,
    build_dataset_adoption_request,
)
from ai_video_production.dbd_reasoning_dataset_discovery import (
    DISCOVERY_POLICY_SHA256,
    DatasetDiscoveryItem,
    DatasetDiscoveryItemStatus,
    DatasetDiscoveryReport,
    DatasetDiscoveryStatus,
)
from ai_video_production.dbd_reasoning_dataset_preflight import (
    DatasetEvidencePreflightMode,
    build_dataset_evidence_preflight,
)
from ai_video_production.errors import ProductError


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
MANIFEST = "MAN-" + "0" * 26
NOW = "2026-08-26T10:00:00Z"


class Verifier:
    def __init__(self, trusted: bool = True) -> None:
        self.trusted = trusted
        self.calls: list[str] = []

    def verify(self, authority_evidence_sha256: str) -> bool:
        self.calls.append(authority_evidence_sha256)
        return self.trusted


class UseStore:
    def __init__(self) -> None:
        self.claimed: set[str] = set()
        self.calls: list[str] = []

    def claim_once(self, authorization_sha256: str) -> bool:
        self.calls.append(authorization_sha256)
        if authorization_sha256 in self.claimed:
            return False
        self.claimed.add(authorization_sha256)
        return True


def _preflight(*, confirmation_only: bool = False, eligible: int = 1) -> dict[str, object]:
    needs_review = 2 if eligible == 0 else 1
    rejected = 1
    count = eligible + needs_review + rejected
    item = DatasetDiscoveryItem(
        logical_path_sha256=SHA_A,
        observation_sha256=SHA_B,
        status=DatasetDiscoveryItemStatus.ADMITTED,
        detail_code="PASS",
        manifest_id=MANIFEST,
        revision=3,
        rights_manifest_sha256=SHA_C,
        entry_count=count,
        eligible_candidate_count=eligible,
        needs_review_count=needs_review,
        rejected_count=rejected,
        train_count=1,
        validation_count=1,
        test_count=count - 2,
    )
    report = DatasetDiscoveryReport(
        observed_at="2026-08-26T06:00:00Z",
        root_observation_sha256=SHA_D,
        discovery_policy_sha256=DISCOVERY_POLICY_SHA256,
        status=DatasetDiscoveryStatus.DISCOVERED_CANDIDATE_ONLY,
        detail_code="PASS",
        items=(item,),
    )
    mode = (
        DatasetEvidencePreflightMode.CONFIRMATION_ONLY
        if confirmation_only
        else DatasetEvidencePreflightMode.LEARNING_PREPARATION
    )
    return build_dataset_evidence_preflight(
        report.to_dict(),
        created_at="2026-08-26T08:00:00Z",
        mode=mode,
        selected_manifest_id=MANIFEST,
        selected_revision=3,
        selected_rights_manifest_sha256=SHA_C,
    ).to_dict()


def _authority(preflight: dict[str, object]) -> DatasetAdoptionAuthority:
    return DatasetAdoptionAuthority(
        authorization_id="auth/r6bc/001",
        authority_evidence_sha256=SHA_D,
        preflight_sha256=preflight["preflight_sha256"],
        manifest_id=preflight["selected_manifest_id"],
        revision=preflight["selected_revision"],
        rights_manifest_sha256=preflight["selected_rights_manifest_sha256"],
        logical_path_sha256=preflight["selected_logical_path_sha256"],
        observation_sha256=preflight["selected_observation_sha256"],
        not_before="2026-08-26T09:00:00Z",
        expires_at="2026-08-26T11:00:00Z",
    )


def _build(
    preflight: dict[str, object],
    authority: DatasetAdoptionAuthority,
    *,
    verifier: Verifier | None = None,
    store: UseStore | None = None,
    now: str = NOW,
):
    return build_dataset_adoption_request(
        preflight,
        authority.to_dict(),
        request_id="request/r6bc/001",
        now=now,
        authority_verifier=verifier or Verifier(),
        authority_use_store=store or UseStore(),
    )


def test_exact_authority_builds_body_free_no_effect_request() -> None:
    preflight = _preflight()
    authority = _authority(preflight)
    store = UseStore()
    request = _build(preflight, authority, store=store)

    assert request.manifest_id == MANIFEST
    assert request.dataset_adoption_requested is True
    assert request.dataset_adoption_started is False
    assert request.training_authorized is False
    assert request.training_started is False
    assert request.request_state == REQUEST_STATE
    assert store.calls == [authority.to_dict()["authorization_sha256"]]
    assert admit_dataset_adoption_authority(authority.to_dict()) == authority
    assert admit_dataset_adoption_request(request.to_dict()) == request
    public = json.dumps(request.to_dict())
    for forbidden in ("raw_path", "manifest.json", "transcript", "narration", "media_body"):
        assert forbidden not in public


def test_authority_and_request_validate_against_schema_and_mirror() -> None:
    root = Path(__file__).resolve().parents[1]
    canonical = root / "schemas" / "dbd-reasoning-dataset-adoption-authority.schema.json"
    mirror = (
        root
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / canonical.name
    )
    assert canonical.read_bytes() == mirror.read_bytes()
    schema = json.loads(canonical.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    preflight = _preflight()
    authority = _authority(preflight)
    request = _build(preflight, authority)
    assert list(validator.iter_errors(authority.to_dict())) == []
    assert list(validator.iter_errors(request.to_dict())) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preflight_sha256", SHA_D),
        ("manifest_id", "MAN-" + "1" * 26),
        ("revision", 4),
        ("rights_manifest_sha256", SHA_D),
        ("logical_path_sha256", SHA_D),
        ("observation_sha256", SHA_D),
    ],
)
def test_crossed_dataset_coordinates_fail_before_verifier_or_claim(field: str, value: object) -> None:
    preflight = _preflight()
    authority = replace(_authority(preflight), **{field: value})
    verifier = Verifier()
    store = UseStore()
    with pytest.raises(ProductError) as caught:
        _build(preflight, authority, verifier=verifier, store=store)
    assert caught.value.code == "ERR_DBD_R6BC_AUTHORITY_CROSSED"
    assert verifier.calls == []
    assert store.calls == []


@pytest.mark.parametrize(
    "now",
    ["2026-08-26T08:59:59Z", "2026-08-26T11:00:00Z"],
)
def test_inactive_authority_fails_before_verifier_or_claim(now: str) -> None:
    preflight = _preflight()
    verifier = Verifier()
    store = UseStore()
    with pytest.raises(ProductError) as caught:
        _build(preflight, _authority(preflight), verifier=verifier, store=store, now=now)
    assert caught.value.code == "ERR_DBD_R6BC_AUTHORITY_INACTIVE"
    assert verifier.calls == []
    assert store.calls == []


def test_untrusted_authority_fails_before_claim() -> None:
    preflight = _preflight()
    verifier = Verifier(trusted=False)
    store = UseStore()
    with pytest.raises(ProductError) as caught:
        _build(preflight, _authority(preflight), verifier=verifier, store=store)
    assert caught.value.code == "ERR_DBD_R6BC_AUTHORITY_UNTRUSTED"
    assert verifier.calls == [SHA_D]
    assert store.calls == []


def test_authority_is_claimed_exactly_once() -> None:
    preflight = _preflight()
    authority = _authority(preflight)
    store = UseStore()
    first = _build(preflight, authority, store=store)
    with pytest.raises(ProductError) as caught:
        _build(preflight, authority, store=store)
    assert caught.value.code == "ERR_DBD_R6BC_AUTHORITY_REUSED"
    assert len(store.calls) == 2
    assert first.authorization_sha256 == store.calls[0] == store.calls[1]


@pytest.mark.parametrize(
    "preflight",
    [_preflight(confirmation_only=True), _preflight(eligible=0)],
)
def test_non_learning_or_zero_eligible_preflight_is_ineligible(preflight: dict[str, object]) -> None:
    authority = _authority(preflight)
    verifier = Verifier()
    store = UseStore()
    with pytest.raises(ProductError) as caught:
        _build(preflight, authority, verifier=verifier, store=store)
    assert caught.value.code == "ERR_DBD_R6BC_PREFLIGHT_INELIGIBLE"
    assert verifier.calls == []
    assert store.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authorization_scope", "TRAINING"),
        ("authorization_state", "APPROVED"),
        ("max_adoption_requests", 2),
    ],
)
def test_authority_cannot_expand_scope_or_effect(field: str, value: object) -> None:
    preflight = _preflight()
    with pytest.raises(ValueError):
        replace(_authority(preflight), **{field: value})


def test_forged_or_extended_records_fail_exact_admission() -> None:
    preflight = _preflight()
    authority = _authority(preflight)
    forged = authority.to_dict()
    forged["authority_evidence_sha256"] = SHA_A
    with pytest.raises(ValueError):
        admit_dataset_adoption_authority(forged)
    extended = authority.to_dict()
    extended["raw_path"] = "C:/private/dataset"
    with pytest.raises(ValueError):
        admit_dataset_adoption_authority(extended)

    request = _build(preflight, authority).to_dict()
    request["training_authorized"] = True
    with pytest.raises(ValueError):
        admit_dataset_adoption_request(request)


def test_required_collaborators_fail_closed() -> None:
    preflight = _preflight()
    authority = _authority(preflight).to_dict()
    with pytest.raises(ValueError, match="authority_verifier"):
        build_dataset_adoption_request(
            preflight,
            authority,
            request_id="request/r6bc/001",
            now=NOW,
            authority_verifier=None,
            authority_use_store=UseStore(),
        )
    with pytest.raises(ValueError, match="authority_use_store"):
        build_dataset_adoption_request(
            preflight,
            authority,
            request_id="request/r6bc/001",
            now=NOW,
            authority_verifier=Verifier(),
            authority_use_store=None,
        )


class TruthyCollaborator:
    def verify(self, authority_evidence_sha256: str) -> str:
        return "trusted"

    def claim_once(self, authorization_sha256: str) -> str:
        return "claimed"


def test_collaborator_truthy_non_boolean_result_fails_closed() -> None:
    preflight = _preflight()
    authority = _authority(preflight)
    with pytest.raises(ProductError) as caught:
        build_dataset_adoption_request(
            preflight,
            authority.to_dict(),
            request_id="request/r6bc/001",
            now=NOW,
            authority_verifier=TruthyCollaborator(),
            authority_use_store=UseStore(),
        )
    assert caught.value.code == "ERR_DBD_R6BC_AUTHORITY_UNTRUSTED"

    with pytest.raises(ProductError) as caught:
        build_dataset_adoption_request(
            preflight,
            authority.to_dict(),
            request_id="request/r6bc/001",
            now=NOW,
            authority_verifier=Verifier(),
            authority_use_store=TruthyCollaborator(),
        )
    assert caught.value.code == "ERR_DBD_R6BC_AUTHORITY_REUSED"


def test_boundary_constants_are_narrow_and_no_training() -> None:
    assert AUTHORITY_SCOPE == "DATASET_ADOPTION_REQUEST_ONLY"
    assert AUTHORITY_STATE == "ALLOWED_SINGLE_DATASET_ADOPTION_REQUEST"
    assert "NO_DATASET_ADOPTION_OR_TRAINING_EFFECT" in REQUEST_STATE
