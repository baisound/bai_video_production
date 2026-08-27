"""TASK-058 one-shot Product operation for the BVP-owned file bridge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, runtime_checkable

from .montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    GENERIC_CONTRACT_PROFILE,
    validate_exact_evidence_delivery,
    validate_generic_learning_delivery,
)
from .montage_learning_file_bridge import (
    BridgeLayout,
    DeliverySnapshot,
    list_delivery_paths,
    load_bridge_owner,
    provision_bridge,
    publish_receipt_new_or_identical,
    snapshot_delivery,
)
from .montage_learning_receipt_contracts import (
    ACCEPTED,
    DUPLICATE,
    EXACT_EVIDENCE,
    MontageLearningAdmissionReceipt,
    parse_montage_learning_admission_receipt,
)


_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
_GENERIC_RECEIPT_FIELDS = {
    "schema_version",
    "message_type",
    "record_id",
    "learning_sha256",
    "status",
    "receipt_id",
    "timestamp",
}


class MontageLearningBridgeApplicationError(ValueError):
    """Raised when import/store/receipt coordinates do not close exactly."""


@dataclass(frozen=True, slots=True)
class ExactAdmissionCoordinates:
    staging_store_id: str
    expected_owner_scope_hash: str
    expected_staging_revision: int
    expected_staging_entry_sha256: str
    expected_canonical_store_commit_sha256: str | None
    expected_external_anchor_document_sha256: str | None


@dataclass(frozen=True, slots=True)
class GenericObservationCoordinates:
    expected_revision: int
    generic_store_id: str = "task058-generic-review-observations"


@runtime_checkable
class GenericObservationCommit(Protocol):
    @property
    def record_id(self) -> str: ...

    @property
    def learning_sha256(self) -> str: ...

    @property
    def status(self) -> str: ...

    def to_skill_v1_receipt(self) -> Mapping[str, object]: ...


@runtime_checkable
class ExactAdmissionCommit(Protocol):
    @property
    def receipt(self) -> MontageLearningAdmissionReceipt: ...

    @property
    def status(self) -> str: ...


class CanonicalAdmissionPort(Protocol):
    """Small adapter seam implemented by FAST-BATCH-1 subunit A."""

    def admit_exact(
        self,
        delivery: Mapping[str, object],
        *,
        staging_store_id: str,
        expected_owner_scope_hash: str,
        expected_staging_revision: int,
        expected_staging_entry_sha256: str,
        expected_canonical_store_commit_sha256: str | None,
        expected_external_anchor_document_sha256: str | None,
    ) -> ExactAdmissionCommit: ...

    def record_exact_generic_observation(
        self,
        delivery: Mapping[str, object],
        *,
        expected_revision: int,
        generic_store_id: str,
    ) -> GenericObservationCommit: ...


@dataclass(frozen=True, slots=True)
class ImportResult:
    lane: str
    record_id: str
    source_sha256: str
    status: str
    receipt_path: Path
    canonical_store_written: bool
    learning_adoption_authorized: bool = False
    automatic_promotion_authorized: bool = False
    timeline_mutation_authorized: bool = False
    resolve_write_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane,
            "record_id": self.record_id,
            "source_sha256": self.source_sha256,
            "status": self.status,
            "receipt_path": str(self.receipt_path),
            "canonical_store_written": self.canonical_store_written,
            "learning_adoption_authorized": False,
            "automatic_promotion_authorized": False,
            "timeline_mutation_authorized": False,
            "resolve_write_authorized": False,
        }


class MontageLearningBridgeApplication:
    """BVP Product-operation facade; intentionally no watcher or second CLI."""

    def __init__(
        self,
        *,
        layout: BridgeLayout,
        canonical_port: CanonicalAdmissionPort,
    ) -> None:
        self.layout = layout
        self._canonical_port = canonical_port

    @classmethod
    def production(
        cls,
        *,
        canonical_port: CanonicalAdmissionPort,
    ) -> "MontageLearningBridgeApplication":
        return cls(layout=BridgeLayout.production(), canonical_port=canonical_port)

    def provision(self, *, bridge_instance_id: str) -> dict[str, object]:
        owner = provision_bridge(
            self.layout,
            bridge_instance_id=bridge_instance_id,
        )
        return {
            "bridge_state": "OWNERSHIP_UNVERIFIED",
            "bridge_instance_id": owner.bridge_instance_id,
            "owner_manifest_sha256": owner.manifest_sha256,
            "production_path": owner.production_path,
            # Python stdlib cannot prove a Windows DACL owner.  Never overclaim it.
            "os_acl_owner_verified": False,
        }

    def import_once(
        self,
        *,
        exact_coordinates_by_record: Mapping[str, ExactAdmissionCoordinates] | None = None,
        generic_coordinates_by_record: Mapping[
            str, GenericObservationCoordinates
        ]
        | None = None,
    ) -> tuple[ImportResult, ...]:
        exact_coordinates = exact_coordinates_by_record or {}
        generic_coordinates = generic_coordinates_by_record or {}
        return tuple(
            self.import_path(
                path,
                exact_coordinates=exact_coordinates.get(_filename_record(path)),
                generic_coordinates=generic_coordinates.get(_filename_record(path)),
            )
            for path in list_delivery_paths(self.layout)
        )

    def import_path(
        self,
        path: str | Path,
        *,
        exact_coordinates: ExactAdmissionCoordinates | None = None,
        generic_coordinates: GenericObservationCoordinates | None = None,
    ) -> ImportResult:
        owner = load_bridge_owner(self.layout)
        snapshot = snapshot_delivery(path, self.layout)
        message_type = snapshot.document.get("message_type")
        if message_type == "BvpMontageLearningDelivery":
            if generic_coordinates is None:
                raise MontageLearningBridgeApplicationError(
                    "generic delivery requires revision and store coordinates"
                )
            return self._import_generic(snapshot, generic_coordinates)
        if message_type == "BvpMontageExactEvidenceDelivery":
            if exact_coordinates is None:
                raise MontageLearningBridgeApplicationError(
                    "exact delivery requires staging and anchor coordinates"
                )
            return self._import_exact(
                snapshot,
                owner.bridge_instance_id,
                exact_coordinates,
            )
        raise MontageLearningBridgeApplicationError("delivery lane is unsupported")

    def _import_generic(
        self,
        snapshot: DeliverySnapshot,
        coordinates: GenericObservationCoordinates,
    ) -> ImportResult:
        _validate_generic_coordinates(coordinates)
        candidate = validate_generic_learning_delivery(snapshot.document)
        if (
            candidate.record_id != snapshot.record_id
            or candidate.source_sha256 != snapshot.source_sha256
        ):
            raise MontageLearningBridgeApplicationError(
                "generic independent validation binding mismatch"
            )
        committed = self._canonical_port.record_exact_generic_observation(
            snapshot.document,
            expected_revision=coordinates.expected_revision,
            generic_store_id=coordinates.generic_store_id,
        )
        if not isinstance(committed, GenericObservationCommit):
            raise MontageLearningBridgeApplicationError(
                "canonical port returned an untyped generic result"
            )
        if (
            committed.record_id != snapshot.record_id
            or committed.learning_sha256 != snapshot.source_sha256
        ):
            raise MontageLearningBridgeApplicationError(
                "generic commit binding mismatch"
            )
        receipt = _parse_skill_v1_receipt(
            committed.to_skill_v1_receipt(),
            record_id=snapshot.record_id,
            learning_sha256=snapshot.source_sha256,
        )
        if committed.status != receipt["status"] or receipt["status"] not in {
            ACCEPTED,
            DUPLICATE,
        }:
            raise MontageLearningBridgeApplicationError(
                "generic commit requires matching ACCEPTED or DUPLICATE receipt"
            )
        receipt_path = publish_receipt_new_or_identical(
            self.layout,
            record_id=snapshot.record_id,
            source_sha256=snapshot.source_sha256,
            receipt=receipt,
            exact_v2=False,
        )
        return ImportResult(
            lane="GENERIC_REVIEW_OBSERVATION",
            record_id=snapshot.record_id,
            source_sha256=snapshot.source_sha256,
            status=str(receipt["status"]),
            receipt_path=receipt_path,
            canonical_store_written=True,
        )

    def _import_exact(
        self,
        snapshot: DeliverySnapshot,
        bridge_instance_id: str,
        coordinates: ExactAdmissionCoordinates,
    ) -> ImportResult:
        _validate_exact_coordinates(coordinates)
        candidate = validate_exact_evidence_delivery(
            snapshot.document,
            expected_owner_scope_hash=coordinates.expected_owner_scope_hash,
        )
        if (
            candidate.record_id != snapshot.record_id
            or candidate.source_sha256 != snapshot.source_sha256
        ):
            raise MontageLearningBridgeApplicationError(
                "exact independent validation binding mismatch"
            )
        committed = self._canonical_port.admit_exact(
            snapshot.document,
            staging_store_id=coordinates.staging_store_id,
            expected_owner_scope_hash=coordinates.expected_owner_scope_hash,
            expected_staging_revision=coordinates.expected_staging_revision,
            expected_staging_entry_sha256=coordinates.expected_staging_entry_sha256,
            expected_canonical_store_commit_sha256=(
                coordinates.expected_canonical_store_commit_sha256
            ),
            expected_external_anchor_document_sha256=(
                coordinates.expected_external_anchor_document_sha256
            ),
        )
        if not isinstance(committed, ExactAdmissionCommit):
            raise MontageLearningBridgeApplicationError(
                "canonical port returned an untyped exact result"
            )
        typed = parse_montage_learning_admission_receipt(committed.receipt.to_dict())
        receipt = typed.to_dict()
        expected = {
            "admission_class": EXACT_EVIDENCE,
            "source_contract_profile": EXACT_CONTRACT_PROFILE,
            "source_record_id": snapshot.record_id,
            "source_sha256": snapshot.source_sha256,
            "owner_scope_hash": coordinates.expected_owner_scope_hash,
            "bridge_instance_id": bridge_instance_id,
        }
        for field, value in expected.items():
            if receipt[field] != value:
                raise MontageLearningBridgeApplicationError(
                    f"exact receipt {field} binding mismatch"
                )
        if receipt["status"] not in {ACCEPTED, DUPLICATE}:
            raise MontageLearningBridgeApplicationError(
                "exact canonical admission did not commit"
            )
        if receipt["canonical_store_written"] is not True:
            raise MontageLearningBridgeApplicationError(
                "exact receipt lacks durable canonical commit"
            )
        receipt_path = publish_receipt_new_or_identical(
            self.layout,
            record_id=snapshot.record_id,
            source_sha256=snapshot.source_sha256,
            receipt=receipt,
            exact_v2=True,
        )
        return ImportResult(
            lane="EXACT_EVIDENCE",
            record_id=snapshot.record_id,
            source_sha256=snapshot.source_sha256,
            status=str(receipt["status"]),
            receipt_path=receipt_path,
            canonical_store_written=True,
        )


def _parse_skill_v1_receipt(
    value: Mapping[str, object],
    *,
    record_id: str,
    learning_sha256: str,
) -> dict[str, object]:
    if type(value) is not dict or set(value) != _GENERIC_RECEIPT_FIELDS:
        raise MontageLearningBridgeApplicationError(
            "SKILL v1 receipt fields mismatch"
        )
    if value["schema_version"] != "1.0.0":
        raise MontageLearningBridgeApplicationError("SKILL v1 receipt version mismatch")
    if value["message_type"] != "BvpMontageLearningAdmissionReceipt":
        raise MontageLearningBridgeApplicationError("SKILL v1 receipt type mismatch")
    if value["record_id"] != record_id or value["learning_sha256"] != learning_sha256:
        raise MontageLearningBridgeApplicationError("SKILL v1 receipt binding mismatch")
    if value["status"] not in {ACCEPTED, DUPLICATE, "REJECTED"}:
        raise MontageLearningBridgeApplicationError("SKILL v1 receipt status invalid")
    _require_id(value["receipt_id"], "receipt_id")
    if not isinstance(value["timestamp"], str) or not value["timestamp"].strip():
        raise MontageLearningBridgeApplicationError("receipt timestamp is invalid")
    return dict(value)


def _validate_exact_coordinates(value: ExactAdmissionCoordinates) -> None:
    _require_id(value.staging_store_id, "staging_store_id")
    if (
        isinstance(value.expected_staging_revision, bool)
        or not isinstance(value.expected_staging_revision, int)
        or value.expected_staging_revision < 1
    ):
        raise MontageLearningBridgeApplicationError(
            "expected_staging_revision is invalid"
        )
    for field in (
        "expected_owner_scope_hash",
        "expected_staging_entry_sha256",
    ):
        digest = getattr(value, field)
        if not isinstance(digest, str) or _SHA_RE.fullmatch(digest) is None:
            raise MontageLearningBridgeApplicationError(f"{field} is invalid")
    for field in (
        "expected_canonical_store_commit_sha256",
        "expected_external_anchor_document_sha256",
    ):
        digest = getattr(value, field)
        if digest is not None and (
            not isinstance(digest, str) or _SHA_RE.fullmatch(digest) is None
        ):
            raise MontageLearningBridgeApplicationError(f"{field} is invalid")


def _validate_generic_coordinates(value: GenericObservationCoordinates) -> None:
    if (
        isinstance(value.expected_revision, bool)
        or not isinstance(value.expected_revision, int)
        or value.expected_revision < 0
    ):
        raise MontageLearningBridgeApplicationError("expected_revision is invalid")
    _require_id(value.generic_store_id, "generic_store_id")


def _filename_record(path: Path) -> str:
    name = path.name
    if "--" not in name:
        raise MontageLearningBridgeApplicationError("delivery filename is invalid")
    return name.split("--", 1)[0]


def _require_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise MontageLearningBridgeApplicationError(f"{field} is invalid")
    return value


__all__ = [
    "CanonicalAdmissionPort",
    "ExactAdmissionCoordinates",
    "GenericObservationCoordinates",
    "GenericObservationCommit",
    "ImportResult",
    "MontageLearningBridgeApplication",
    "MontageLearningBridgeApplicationError",
]
