"""TASK-058 one-shot Product operation for the BVP-owned file bridge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from .montage_learning_bridge_contracts import (
    EXACT_CONTRACT_PROFILE,
    validate_exact_evidence_delivery,
    validate_generic_learning_delivery,
)
from .montage_learning_canonical_admission_transaction import (
    GenericReviewObservationReceipt,
    MontageLearningCanonicalAdmissionError,
    MontageLearningCanonicalAdmissionResult,
    MontageLearningCanonicalAdmissionTransactionStore,
    MontageLearningVerifiedAdmissionReceipt,
)
from .montage_learning_file_bridge import (
    BridgeLayout,
    DeliveryClaim,
    DeliverySnapshot,
    EXACT_RECEIPT_NAMESPACE,
    GENERIC_RECEIPT_NAMESPACE,
    MontageLearningFileBridgeError,
    ReceiptPublicationPaths,
    build_receipt_publication_pending,
    claim_delivery,
    clear_pending_receipt_publication_exact,
    create_pending_receipt_publication_new_or_identical,
    list_delivery_paths,
    load_published_receipt,
    load_receipt_publication_pending,
    load_bridge_owner,
    mark_claim_receipt_published,
    provision_bridge,
    publish_receipt_new_or_identical,
    quarantine_claim,
    receipt_identity_publisher_guard,
    snapshot_delivery,
)
from .montage_learning_receipt_contracts import (
    ACCEPTED,
    DUPLICATE,
    EXACT_EVIDENCE,
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
FailureHook = Callable[[str, Path], None]


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
        canonical_port: MontageLearningCanonicalAdmissionTransactionStore,
        # Test-only crash seam; production construction leaves this unset.
        failure_hook: FailureHook | None = None,
    ) -> None:
        if failure_hook is not None and not callable(failure_hook):
            raise TypeError("failure_hook must be callable")
        self.layout = layout
        self._canonical_port = canonical_port
        self._failure_hook = failure_hook

    @classmethod
    def production(
        cls,
        *,
        canonical_port: MontageLearningCanonicalAdmissionTransactionStore,
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
        claim = claim_delivery(path, self.layout)
        self._call_failure_hook(
            "after_claim_rename_before_snapshot", claim.processing_path
        )
        try:
            snapshot = snapshot_delivery(claim, self.layout)
        except Exception as exc:
            self._quarantine_pre_admission(claim, exc)
            raise AssertionError("unreachable")
        message_type = snapshot.document.get("message_type")
        if message_type == "BvpMontageLearningDelivery":
            if generic_coordinates is None:
                raise MontageLearningBridgeApplicationError(
                    "generic delivery requires revision and store coordinates"
                )
            _validate_generic_coordinates(generic_coordinates)
            try:
                candidate = validate_generic_learning_delivery(snapshot.document)
                if (
                    candidate.record_id != snapshot.record_id
                    or candidate.source_sha256 != snapshot.source_sha256
                ):
                    raise MontageLearningBridgeApplicationError(
                        "generic independent validation binding mismatch"
                    )
            except Exception as exc:
                self._quarantine_pre_admission(claim, exc)
                raise AssertionError("unreachable")
            return self._import_generic(snapshot, claim, generic_coordinates)
        if message_type == "BvpMontageExactEvidenceDelivery":
            if exact_coordinates is None:
                raise MontageLearningBridgeApplicationError(
                    "exact delivery requires staging and anchor coordinates"
                )
            _validate_exact_coordinates(exact_coordinates)
            try:
                candidate = validate_exact_evidence_delivery(
                    snapshot.document,
                    expected_owner_scope_hash=(
                        exact_coordinates.expected_owner_scope_hash
                    ),
                )
                if (
                    candidate.record_id != snapshot.record_id
                    or candidate.source_sha256 != snapshot.source_sha256
                ):
                    raise MontageLearningBridgeApplicationError(
                        "exact independent validation binding mismatch"
                    )
            except Exception as exc:
                self._quarantine_pre_admission(claim, exc)
                raise AssertionError("unreachable")
            return self._import_exact(
                snapshot,
                claim,
                owner.bridge_instance_id,
                exact_coordinates,
            )
        error = MontageLearningBridgeApplicationError(
            "delivery lane is unsupported"
        )
        self._quarantine_pre_admission(claim, error)
        raise AssertionError("unreachable")

    def _import_generic(
        self,
        snapshot: DeliverySnapshot,
        claim: DeliveryClaim,
        coordinates: GenericObservationCoordinates,
    ) -> ImportResult:
        with receipt_identity_publisher_guard(
            self.layout,
            record_id=snapshot.record_id,
            source_sha256=snapshot.source_sha256,
            exact_v2=False,
        ) as paths:
            pending = build_receipt_publication_pending(
                paths,
                lane="GENERIC_REVIEW_OBSERVATION",
                namespace=GENERIC_RECEIPT_NAMESPACE,
                record_id=snapshot.record_id,
                source_sha256=snapshot.source_sha256,
                delivery_file_sha256=snapshot.file_sha256,
                expected_revision=coordinates.expected_revision,
                coordinates={
                    "expected_revision": coordinates.expected_revision,
                    "generic_store_id": coordinates.generic_store_id,
                },
            )
            restarting = self._load_matching_pending(paths, pending)
            existing = self._load_existing(paths)
            if existing is not None:
                try:
                    receipt = _parse_skill_v1_receipt(
                        existing,
                        record_id=snapshot.record_id,
                        learning_sha256=snapshot.source_sha256,
                    )
                except MontageLearningBridgeApplicationError as exc:
                    raise _recovery_required("published generic receipt is invalid", exc)
                self._mark_published(claim)
                if restarting:
                    self._clear_pending(paths, pending)
                return _result("GENERIC_REVIEW_OBSERVATION", snapshot, receipt, paths)
            if not restarting:
                self._create_pending(paths, pending)
            try:
                committed = self._canonical_port.record_exact_generic_observation(
                    snapshot.document,
                    expected_revision=coordinates.expected_revision,
                    generic_store_id=coordinates.generic_store_id,
                )
            except MontageLearningCanonicalAdmissionError as exc:
                if not restarting or str(exc) != "generic CAS/scope is stale":
                    raise _recovery_required("generic canonical admission failed", exc)
                try:
                    committed = self._canonical_port.record_exact_generic_observation(
                        snapshot.document,
                        expected_revision=coordinates.expected_revision + 1,
                        generic_store_id=coordinates.generic_store_id,
                    )
                except MontageLearningCanonicalAdmissionError as retry_exc:
                    raise _recovery_required(
                        "generic restart CAS retry failed", retry_exc
                    ) from retry_exc
                receipt = _validate_generic_commit(
                    committed,
                    snapshot,
                    required_duplicate_revision=coordinates.expected_revision + 2,
                )
            else:
                receipt = _validate_generic_commit(committed, snapshot)
            self._call_failure_hook("after_canonical_commit_before_receipt", paths.receipt_path)
            receipt_path = publish_receipt_new_or_identical(
                self.layout,
                record_id=snapshot.record_id,
                source_sha256=snapshot.source_sha256,
                receipt=receipt,
                exact_v2=False,
            )
            self._mark_published(claim)
            self._call_failure_hook("after_receipt_publish_before_pending_cleanup", receipt_path)
            self._clear_pending(paths, pending)
            return _result("GENERIC_REVIEW_OBSERVATION", snapshot, receipt, paths)

    def _import_exact(
        self,
        snapshot: DeliverySnapshot,
        claim: DeliveryClaim,
        bridge_instance_id: str,
        coordinates: ExactAdmissionCoordinates,
    ) -> ImportResult:
        with receipt_identity_publisher_guard(
            self.layout,
            record_id=snapshot.record_id,
            source_sha256=snapshot.source_sha256,
            exact_v2=True,
        ) as paths:
            pending = build_receipt_publication_pending(
                paths,
                lane="EXACT_EVIDENCE",
                namespace=EXACT_RECEIPT_NAMESPACE,
                record_id=snapshot.record_id,
                source_sha256=snapshot.source_sha256,
                delivery_file_sha256=snapshot.file_sha256,
                expected_revision=coordinates.expected_staging_revision,
                coordinates=_exact_coordinate_mapping(coordinates),
            )
            restarting = self._load_matching_pending(paths, pending)
            existing = self._load_existing(paths)
            if existing is not None:
                receipt = _validate_exact_receipt(
                    existing, snapshot, bridge_instance_id, coordinates
                )
                self._mark_published(claim)
                if restarting:
                    self._clear_pending(paths, pending)
                return _result("EXACT_EVIDENCE", snapshot, receipt, paths)
            if restarting:
                try:
                    verified = self._canonical_port.get_verified_receipt()
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    raise _recovery_required("exact trusted recovery read failed", exc)
                else:
                    receipt = _trusted_exact_receipt(
                        verified, snapshot, bridge_instance_id, coordinates
                    )
                    self._call_failure_hook(
                        "after_canonical_commit_before_receipt", paths.receipt_path
                    )
                    receipt_path = publish_receipt_new_or_identical(
                        self.layout,
                        record_id=snapshot.record_id,
                        source_sha256=snapshot.source_sha256,
                        receipt=receipt,
                        exact_v2=True,
                    )
                    self._mark_published(claim)
                    self._call_failure_hook(
                        "after_receipt_publish_before_pending_cleanup", receipt_path
                    )
                    self._clear_pending(paths, pending)
                    return _result("EXACT_EVIDENCE", snapshot, receipt, paths)
            if not restarting:
                self._create_pending(paths, pending)
            try:
                committed = self._canonical_port.admit_exact(
                    snapshot.document,
                    **_exact_coordinate_mapping(coordinates),
                )
            except MontageLearningCanonicalAdmissionError as exc:
                raise _recovery_required("exact canonical admission failed", exc) from exc
            if not isinstance(committed, MontageLearningCanonicalAdmissionResult):
                raise _recovery_required("canonical port returned an untyped exact result")
            receipt = _validate_exact_receipt(
                committed.receipt.to_dict(), snapshot, bridge_instance_id, coordinates
            )
            self._call_failure_hook("after_canonical_commit_before_receipt", paths.receipt_path)
            receipt_path = publish_receipt_new_or_identical(
                self.layout,
                record_id=snapshot.record_id,
                source_sha256=snapshot.source_sha256,
                receipt=receipt,
                exact_v2=True,
            )
            self._mark_published(claim)
            self._call_failure_hook("after_receipt_publish_before_pending_cleanup", receipt_path)
            self._clear_pending(paths, pending)
            return _result("EXACT_EVIDENCE", snapshot, receipt, paths)

    def _load_matching_pending(
        self, paths: ReceiptPublicationPaths, expected: Mapping[str, object]
    ) -> bool:
        try:
            current = load_receipt_publication_pending(paths)
            if current is None:
                return False
            if current != dict(expected):
                raise _recovery_required("pending receipt request does not match")
            create_pending_receipt_publication_new_or_identical(paths, expected)
            return True
        except MontageLearningFileBridgeError as exc:
            raise _recovery_required("pending receipt is invalid", exc) from exc

    def _load_existing(
        self, paths: ReceiptPublicationPaths
    ) -> dict[str, Any] | None:
        try:
            return load_published_receipt(paths)
        except MontageLearningFileBridgeError as exc:
            raise _recovery_required("published receipt is invalid", exc) from exc

    def _create_pending(
        self, paths: ReceiptPublicationPaths, pending: Mapping[str, object]
    ) -> None:
        try:
            create_pending_receipt_publication_new_or_identical(paths, pending)
        except MontageLearningFileBridgeError as exc:
            raise _recovery_required("pending receipt publication failed", exc) from exc

    def _clear_pending(
        self, paths: ReceiptPublicationPaths, pending: Mapping[str, object]
    ) -> None:
        try:
            clear_pending_receipt_publication_exact(paths, pending)
        except MontageLearningFileBridgeError as exc:
            raise _recovery_required("pending receipt cleanup failed", exc) from exc

    def _mark_published(self, claim: DeliveryClaim) -> None:
        try:
            mark_claim_receipt_published(claim, self.layout)
        except MontageLearningFileBridgeError as exc:
            raise _recovery_required(
                "import journal receipt state publication failed", exc
            ) from exc

    def _quarantine_pre_admission(
        self, claim: DeliveryClaim, cause: Exception
    ) -> None:
        try:
            quarantine_claim(claim, self.layout)
        except MontageLearningFileBridgeError as quarantine_error:
            raise _recovery_required(
                "pre-admission failure could not be quarantined",
                quarantine_error,
            ) from cause
        raise cause

    def _call_failure_hook(self, phase: str, path: Path) -> None:
        if self._failure_hook is not None:
            self._failure_hook(phase, path)


def _recovery_required(
    message: str, cause: Exception | None = None,
) -> MontageLearningBridgeApplicationError:
    error = MontageLearningBridgeApplicationError(f"RECOVERY_REQUIRED: {message}")
    if cause is not None:
        error.__cause__ = cause
    return error


def _result(
    lane: str,
    snapshot: DeliverySnapshot,
    receipt: Mapping[str, object],
    paths: ReceiptPublicationPaths,
) -> ImportResult:
    return ImportResult(
        lane=lane,
        record_id=snapshot.record_id,
        source_sha256=snapshot.source_sha256,
        status=str(receipt["status"]),
        receipt_path=paths.receipt_path,
        canonical_store_written=True,
    )


def _validate_generic_commit(
    committed: object,
    snapshot: DeliverySnapshot,
    *,
    required_duplicate_revision: int | None = None,
) -> dict[str, object]:
    if not isinstance(committed, GenericReviewObservationReceipt):
        raise _recovery_required("canonical port returned an untyped generic result")
    if (
        committed.record_id != snapshot.record_id
        or committed.learning_sha256 != snapshot.source_sha256
    ):
        raise _recovery_required("generic commit binding mismatch")
    try:
        receipt = _parse_skill_v1_receipt(
            committed.to_skill_v1_receipt(),
            record_id=snapshot.record_id,
            learning_sha256=snapshot.source_sha256,
        )
    except MontageLearningBridgeApplicationError as exc:
        raise _recovery_required("generic receipt is invalid", exc) from exc
    if committed.status != receipt["status"] or receipt["status"] not in {
        ACCEPTED,
        DUPLICATE,
    }:
        raise _recovery_required("generic result is ambiguous")
    if required_duplicate_revision is not None and (
        committed.status != DUPLICATE
        or committed.ledger_revision != required_duplicate_revision
        or not isinstance(committed.duplicate_of_receipt_sha256, str)
        or _SHA_RE.fullmatch(committed.duplicate_of_receipt_sha256) is None
    ):
        raise _recovery_required("generic restart result is not the exact duplicate")
    return receipt


def _exact_coordinate_mapping(
    coordinates: ExactAdmissionCoordinates,
) -> dict[str, object]:
    return {
        "staging_store_id": coordinates.staging_store_id,
        "expected_owner_scope_hash": coordinates.expected_owner_scope_hash,
        "expected_staging_revision": coordinates.expected_staging_revision,
        "expected_staging_entry_sha256": coordinates.expected_staging_entry_sha256,
        "expected_canonical_store_commit_sha256": (
            coordinates.expected_canonical_store_commit_sha256
        ),
        "expected_external_anchor_document_sha256": (
            coordinates.expected_external_anchor_document_sha256
        ),
    }


def _validate_exact_receipt(
    value: Mapping[str, object],
    snapshot: DeliverySnapshot,
    bridge_instance_id: str,
    coordinates: ExactAdmissionCoordinates,
) -> dict[str, object]:
    try:
        receipt = parse_montage_learning_admission_receipt(value).to_dict()
    except Exception as exc:
        raise _recovery_required("exact receipt is invalid", exc) from exc
    expected = {
        "admission_class": EXACT_EVIDENCE,
        "source_contract_profile": EXACT_CONTRACT_PROFILE,
        "source_record_id": snapshot.record_id,
        "source_sha256": snapshot.source_sha256,
        "owner_scope_hash": coordinates.expected_owner_scope_hash,
        "bridge_instance_id": bridge_instance_id,
    }
    for field, expected_value in expected.items():
        if receipt[field] != expected_value:
            raise _recovery_required(f"exact receipt {field} binding mismatch")
    if receipt["status"] not in {ACCEPTED, DUPLICATE}:
        raise _recovery_required("exact canonical admission did not commit")
    if receipt["canonical_store_written"] is not True:
        raise _recovery_required("exact receipt lacks durable canonical commit")
    return receipt


def _trusted_exact_receipt(
    verified: object,
    snapshot: DeliverySnapshot,
    bridge_instance_id: str,
    coordinates: ExactAdmissionCoordinates,
) -> dict[str, object]:
    if not isinstance(verified, MontageLearningVerifiedAdmissionReceipt):
        raise _recovery_required("exact trusted reader returned an untyped result")
    return _validate_exact_receipt(
        verified.receipt.to_dict(), snapshot, bridge_instance_id, coordinates
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
    if value["status"] not in {ACCEPTED, DUPLICATE}:
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
    "ExactAdmissionCoordinates",
    "GenericObservationCoordinates",
    "ImportResult",
    "MontageLearningBridgeApplication",
    "MontageLearningBridgeApplicationError",
]
