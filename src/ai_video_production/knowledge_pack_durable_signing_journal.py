"""TASK-029 R9D path-local signing journal for the R9C signing ceremony.

The journal reserves one exact ceremony before signing.  A process interruption
leaves an ambiguous reservation which is converted to RECOVERY_REQUIRED on the
next access and is never replayed automatically.  Only body-free hashes are
persisted; key and signature bytes remain inside the R9B/R9C boundaries.

The current R9D unit deliberately does not claim canonical or power-loss-safe
persistent replay prevention. A caller-selected path or external deletion is
outside this cooperative, path-local boundary and is reported explicitly.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

from .atomic import AtomicJsonWriter, FailureInjector, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .knowledge_pack_local_signing_ceremony import (
    LocalSigningCeremonyConfirmation,
    LocalSigningCeremonyReceipt,
    LocalSigningCeremonyResult,
    execute_local_signing_ceremony,
)
from .knowledge_pack_signature_request import (
    KnowledgePackSignatureVerificationRequest,
    verify_knowledge_pack_signature_verification_request,
)
from .knowledge_pack_signature_verification import (
    KnowledgePackSignatureVerificationReceipt,
    TrustedSignerPolicy,
    TrustedSignerPolicyState,
)
from .owner_signing_key_custody import (
    OwnerSigningKeyCustodyReceipt,
    OwnerSigningKeyCustodyStore,
)
from .serialization import canonical_json_bytes, sha256_bytes

JOURNAL_VERSION = JOURNAL_RECEIPT_VERSION = "1.0.0"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")


def _fail(code: str, message: str, **details: object) -> ProductError:
    return ProductError(code, message, ProductErrorCategory.STATE, details=dict(details))


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a stable identifier")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase sha256 coordinate")
    return value


def _positive(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be an integer >= 1")
    return value


class DurableSigningJournalState(str, Enum):
    SIGNING_RESERVED = "SIGNING_RESERVED"
    SIGNED_AND_VERIFIED = "SIGNED_AND_VERIFIED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class DurableSigningJournalReceipt:
    journal_id: str
    ceremony_id: str
    custody_receipt_sha256: str
    signature_request_sha256: str
    confirmation_sha256: str
    state: DurableSigningJournalState
    reserved_at_epoch_ms: int
    updated_at_epoch_ms: int
    ceremony_receipt_sha256: str | None = None
    verification_receipt_sha256: str | None = None

    def __post_init__(self) -> None:
        _id(self.journal_id, "journal_id")
        _id(self.ceremony_id, "ceremony_id")
        for field in ("custody_receipt_sha256", "signature_request_sha256", "confirmation_sha256"):
            _sha(getattr(self, field), field)
        _positive(self.reserved_at_epoch_ms, "reserved_at_epoch_ms")
        _positive(self.updated_at_epoch_ms, "updated_at_epoch_ms")
        if self.updated_at_epoch_ms < self.reserved_at_epoch_ms:
            raise ValueError("journal update time precedes reservation")
        completed = self.state is DurableSigningJournalState.SIGNED_AND_VERIFIED
        if completed:
            _sha(self.ceremony_receipt_sha256, "ceremony_receipt_sha256")
            _sha(self.verification_receipt_sha256, "verification_receipt_sha256")
        elif self.ceremony_receipt_sha256 is not None or self.verification_receipt_sha256 is not None:
            raise ValueError("non-final journal must not contain result receipt hashes")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "receipt_version": JOURNAL_RECEIPT_VERSION,
            "record_type": "KNOWLEDGE_PACK_DURABLE_SIGNING_JOURNAL_RECEIPT",
            "task_owner": "TASK-029",
            "journal_id": self.journal_id,
            "ceremony_id": self.ceremony_id,
            "custody_receipt_sha256": self.custody_receipt_sha256,
            "signature_request_sha256": self.signature_request_sha256,
            "confirmation_sha256": self.confirmation_sha256,
            "state": self.state.value,
            "reserved_at_epoch_ms": self.reserved_at_epoch_ms,
            "updated_at_epoch_ms": self.updated_at_epoch_ms,
            "ceremony_receipt_sha256": self.ceremony_receipt_sha256,
            "verification_receipt_sha256": self.verification_receipt_sha256,
            "persistent_replay_prevention_present": False,
            "path_local_replay_prevention_present": True,
            "canonical_project_binding_present": False,
            "journal_deletion_detection_present": False,
            "reservation_directory_durability_confirmed": False,
            "power_loss_replay_prevention_confirmed": False,
            "path_security_model": "COOPERATIVE_PROTECTED_LOCAL_WRITER_ONLY",
            "hostile_path_race_protection_verified": False,
            "symlink_path_rejection_present": True,
            "automatic_replay_authorized": False,
            "signature_bytes_included": False,
            "public_key_material_included": False,
            "private_key_material_included": False,
            "knowledge_pack_write_authorized": False,
            "knowledge_pack_promotion_authorized": False,
            "automatic_promotion_authorized": False,
            "runtime_profile_apply_authorized": False,
            "rollback_execution_authorized": False,
            "release_authorized": False,
            "external_effect_authorized": False,
        }
        body["journal_receipt_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DurableSigningJournalReceipt":
        try:
            result = cls(
                journal_id=value["journal_id"],
                ceremony_id=value["ceremony_id"],
                custody_receipt_sha256=value["custody_receipt_sha256"],
                signature_request_sha256=value["signature_request_sha256"],
                confirmation_sha256=value["confirmation_sha256"],
                state=DurableSigningJournalState(value["state"]),
                reserved_at_epoch_ms=value["reserved_at_epoch_ms"],
                updated_at_epoch_ms=value["updated_at_epoch_ms"],
                ceremony_receipt_sha256=value["ceremony_receipt_sha256"],
                verification_receipt_sha256=value["verification_receipt_sha256"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("durable signing journal receipt is invalid") from exc
        if result.to_dict() != dict(value):
            raise ValueError("durable signing journal identity or hash mismatch")
        return result


AfterReservationFaultHook = Callable[[], None]


class DurableSigningCeremonyJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _exact_receipt(
        *,
        journal_id: str,
        custody: OwnerSigningKeyCustodyReceipt,
        request: KnowledgePackSignatureVerificationRequest,
        confirmation: LocalSigningCeremonyConfirmation,
        state: DurableSigningJournalState,
        reserved_at_epoch_ms: int,
        updated_at_epoch_ms: int,
        ceremony_receipt_sha256: str | None = None,
        verification_receipt_sha256: str | None = None,
    ) -> DurableSigningJournalReceipt:
        return DurableSigningJournalReceipt(
            journal_id=journal_id,
            ceremony_id=confirmation.ceremony_id,
            custody_receipt_sha256=custody.to_dict()["custody_receipt_sha256"],
            signature_request_sha256=request.to_dict()["signature_request_sha256"],
            confirmation_sha256=confirmation.to_dict()["confirmation_sha256"],
            state=state,
            reserved_at_epoch_ms=reserved_at_epoch_ms,
            updated_at_epoch_ms=updated_at_epoch_ms,
            ceremony_receipt_sha256=ceremony_receipt_sha256,
            verification_receipt_sha256=verification_receipt_sha256,
        )

    @staticmethod
    def _validate_ceremony_result(
        *,
        result: object,
        receipt_id: str,
        verification_receipt_id: str,
        custody: OwnerSigningKeyCustodyReceipt,
        request: KnowledgePackSignatureVerificationRequest,
        confirmation: LocalSigningCeremonyConfirmation,
        completed_at_epoch_ms: int,
    ) -> LocalSigningCeremonyResult:
        """Reject any executor result that is not the exact typed R9C/R9A result."""
        if type(result) is not LocalSigningCeremonyResult:
            raise ValueError("ceremony executor returned an unexpected result type")
        if type(result.receipt) is not LocalSigningCeremonyReceipt:
            raise ValueError("ceremony executor returned an unexpected ceremony receipt type")
        if type(result.verification_receipt) is not KnowledgePackSignatureVerificationReceipt:
            raise ValueError("ceremony executor returned an unexpected verification receipt type")

        ceremony_payload = result.receipt.to_dict()
        verification_payload = result.verification_receipt.to_dict()
        if LocalSigningCeremonyReceipt.from_dict(ceremony_payload) != result.receipt:
            raise ValueError("ceremony executor receipt failed exact typed validation")
        if (
            KnowledgePackSignatureVerificationReceipt.from_dict(verification_payload)
            != result.verification_receipt
        ):
            raise ValueError("ceremony executor verification receipt failed exact typed validation")

        custody_sha = custody.to_dict()["custody_receipt_sha256"]
        request_payload = request.to_dict()
        request_sha = request_payload["signature_request_sha256"]
        confirmation_sha = confirmation.to_dict()["confirmation_sha256"]
        verification_sha = verification_payload["verification_receipt_sha256"]
        if (
            result.receipt.receipt_id,
            result.receipt.ceremony_id,
            result.receipt.custody_receipt_sha256,
            result.receipt.signature_request_sha256,
            result.receipt.signer_key_id_sha256,
            result.receipt.verification_receipt_sha256,
            result.receipt.confirmation_sha256,
            result.receipt.completed_at_epoch_ms,
        ) != (
            receipt_id,
            confirmation.ceremony_id,
            custody_sha,
            request_sha,
            custody.signer_key_id_sha256,
            verification_sha,
            confirmation_sha,
            completed_at_epoch_ms,
        ):
            raise ValueError("ceremony executor receipt is not bound to the exact ceremony")
        if (
            result.verification_receipt.receipt_id,
            result.verification_receipt.signature_request_id,
            result.verification_receipt.signature_request_sha256,
            result.verification_receipt.signing_candidate_sha256,
            result.verification_receipt.pack_id,
            result.verification_receipt.pack_version,
            result.verification_receipt.trusted_signer_policy_sha256,
            result.verification_receipt.signer_key_id_sha256,
            result.verification_receipt.signature_message_sha256,
            result.verification_receipt.detached_signature_sha256,
        ) != (
            verification_receipt_id,
            request.request_id,
            request_sha,
            request.signing_candidate_sha256,
            request.pack_id,
            request.pack_version,
            request.trusted_signer_policy_sha256,
            request.signer_key_id_sha256,
            request_payload["signature_message_sha256"],
            result.receipt.detached_signature_sha256,
        ):
            raise ValueError("verification receipt is not bound to the exact signature request")
        return result
    def _write(self, receipt: DurableSigningJournalReceipt, failure_injector: FailureInjector | None = None) -> None:
        AtomicJsonWriter.write(
            self.path,
            receipt.to_dict(),
            validator=DurableSigningJournalReceipt.from_dict,
            failure_injector=failure_injector,
        )

    def _read_unlocked(self) -> DurableSigningJournalReceipt:
        try:
            if self.path.is_symlink() or not self.path.is_file():
                raise ValueError("journal must be a regular non-symlink file")
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("journal must be an object")
            return DurableSigningJournalReceipt.from_dict(value)
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_INTEGRITY",
                "durable signing journal could not be verified safely",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"reason": type(exc).__name__},
            ) from exc

    def read_receipt(self) -> DurableSigningJournalReceipt:
        return self._read_unlocked()

    def execute_once(
        self,
        *,
        journal_id: str,
        reserved_at_epoch_ms: int,
        recovery_observed_at_epoch_ms: int,
        receipt_id: str,
        verification_receipt_id: str,
        custody_store: OwnerSigningKeyCustodyStore,
        custody_receipt_payload: Mapping[str, Any],
        signature_request_payload: Mapping[str, Any],
        signature_request_compile_kwargs: Mapping[str, Any],
        trusted_signer_policy_payload: Mapping[str, Any],
        confirmation: LocalSigningCeremonyConfirmation,
        completed_at_epoch_ms: int,
        after_reservation_fault_hook: AfterReservationFaultHook | None = None,
        reserve_failure_injector: FailureInjector | None = None,
        final_failure_injector: FailureInjector | None = None,
    ) -> tuple[DurableSigningJournalReceipt, LocalSigningCeremonyResult]:
        _id(journal_id, "journal_id")
        _id(receipt_id, "receipt_id")
        _id(verification_receipt_id, "verification_receipt_id")
        _positive(reserved_at_epoch_ms, "reserved_at_epoch_ms")
        _positive(recovery_observed_at_epoch_ms, "recovery_observed_at_epoch_ms")
        _positive(completed_at_epoch_ms, "completed_at_epoch_ms")
        if completed_at_epoch_ms < reserved_at_epoch_ms:
            raise ValueError("completion time precedes reservation")

        # Revalidate the exact request and non-secret policy before any journal
        # reservation or custody access. R9C repeats these checks before signing.
        verify_knowledge_pack_signature_verification_request(
            signature_request_payload, **dict(signature_request_compile_kwargs)
        )
        request = KnowledgePackSignatureVerificationRequest.from_dict(signature_request_payload)
        policy = TrustedSignerPolicy.from_dict(trusted_signer_policy_payload)
        if policy.state is not TrustedSignerPolicyState.ACTIVE:
            raise ValueError("trusted signer policy is not active")
        if policy.to_dict()["trusted_signer_policy_sha256"] != request.trusted_signer_policy_sha256:
            raise ValueError("trusted signer policy does not match signature request")
        custody = OwnerSigningKeyCustodyReceipt.from_dict(custody_receipt_payload)
        expected = LocalSigningCeremonyConfirmation(
            confirmation.confirmation_id,
            confirmation.ceremony_id,
            custody.to_dict()["custody_receipt_sha256"],
            request.to_dict()["signature_request_sha256"],
            confirmation.confirmed_at_epoch_ms,
        )
        if confirmation != expected:
            raise ValueError("local signing confirmation does not match exact custody and request")
        if completed_at_epoch_ms < confirmation.confirmed_at_epoch_ms:
            raise ValueError("completion time precedes Human confirmation")
        if custody.signer_key_id_sha256 != request.signer_key_id_sha256:
            raise ValueError("custodied signer key does not match signature request")
        if custody.signer_key_id_sha256 not in policy.trusted_signer_key_ids:
            raise ValueError("custodied signer key is not allowed by the exact request policy")

        with exclusive_file_update_lock(self.path):
            if self.path.is_symlink():
                raise ProductError(
                    "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_INTEGRITY",
                    "durable signing journal path is a symlink",
                    ProductErrorCategory.DATA_INTEGRITY,
                )
            if self.path.exists():
                existing = self._read_unlocked()
                exact_identity = (
                    existing.journal_id == journal_id
                    and existing.ceremony_id == confirmation.ceremony_id
                    and existing.custody_receipt_sha256 == custody.to_dict()["custody_receipt_sha256"]
                    and existing.signature_request_sha256 == request.to_dict()["signature_request_sha256"]
                    and existing.confirmation_sha256 == confirmation.to_dict()["confirmation_sha256"]
                )
                if not exact_identity:
                    raise _fail(
                        "ERR_KNOWLEDGE_PACK_SIGNING_JOURNAL_CONFLICT",
                        "durable signing journal belongs to a different exact ceremony",
                        state=existing.state.value,
                        journal_receipt_sha256=existing.to_dict()["journal_receipt_sha256"],
                    )
                if existing.state is DurableSigningJournalState.SIGNING_RESERVED:
                    if recovery_observed_at_epoch_ms < existing.reserved_at_epoch_ms:
                        raise ValueError("recovery observation time precedes existing reservation")
                    recovered = DurableSigningJournalReceipt(
                        journal_id=existing.journal_id,
                        ceremony_id=existing.ceremony_id,
                        custody_receipt_sha256=existing.custody_receipt_sha256,
                        signature_request_sha256=existing.signature_request_sha256,
                        confirmation_sha256=existing.confirmation_sha256,
                        state=DurableSigningJournalState.RECOVERY_REQUIRED,
                        reserved_at_epoch_ms=existing.reserved_at_epoch_ms,
                        updated_at_epoch_ms=recovery_observed_at_epoch_ms,
                    )
                    self._write(recovered)
                    raise _fail(
                        "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED",
                        "an interrupted signing reservation cannot be replayed automatically",
                        journal_receipt_sha256=recovered.to_dict()["journal_receipt_sha256"],
                    )
                raise _fail(
                    "ERR_KNOWLEDGE_PACK_SIGNING_ALREADY_FINAL",
                    "durable signing journal already has a terminal result",
                    state=existing.state.value,
                    journal_receipt_sha256=existing.to_dict()["journal_receipt_sha256"],
                )

            reserved = self._exact_receipt(
                journal_id=journal_id,
                custody=custody,
                request=request,
                confirmation=confirmation,
                state=DurableSigningJournalState.SIGNING_RESERVED,
                reserved_at_epoch_ms=reserved_at_epoch_ms,
                updated_at_epoch_ms=reserved_at_epoch_ms,
            )
            self._write(reserved, reserve_failure_injector)

            try:
                if custody_store.read_receipt() != custody:
                    raise ValueError("custody receipt does not match current encrypted custody")
                if after_reservation_fault_hook is not None:
                    after_reservation_fault_hook()
                result = execute_local_signing_ceremony(
                    receipt_id=receipt_id,
                    verification_receipt_id=verification_receipt_id,
                    custody_store=custody_store,
                    custody_receipt_payload=custody_receipt_payload,
                    signature_request_payload=signature_request_payload,
                    signature_request_compile_kwargs=signature_request_compile_kwargs,
                    trusted_signer_policy_payload=trusted_signer_policy_payload,
                    confirmation=confirmation,
                    completed_at_epoch_ms=completed_at_epoch_ms,
                )
                result = self._validate_ceremony_result(
                    result=result,
                    receipt_id=receipt_id,
                    verification_receipt_id=verification_receipt_id,
                    custody=custody,
                    request=request,
                    confirmation=confirmation,
                    completed_at_epoch_ms=completed_at_epoch_ms,
                )
            except Exception as exc:
                recovery = self._exact_receipt(
                    journal_id=journal_id,
                    custody=custody,
                    request=request,
                    confirmation=confirmation,
                    state=DurableSigningJournalState.RECOVERY_REQUIRED,
                    reserved_at_epoch_ms=reserved_at_epoch_ms,
                    updated_at_epoch_ms=recovery_observed_at_epoch_ms,
                )
                self._write(recovery)
                raise _fail(
                    "ERR_KNOWLEDGE_PACK_SIGNING_RECOVERY_REQUIRED",
                    "signing result was not durably committed and cannot be replayed automatically",
                    reason=type(exc).__name__,
                    journal_receipt_sha256=recovery.to_dict()["journal_receipt_sha256"],
                ) from exc

            final = self._exact_receipt(
                journal_id=journal_id,
                custody=custody,
                request=request,
                confirmation=confirmation,
                state=DurableSigningJournalState.SIGNED_AND_VERIFIED,
                reserved_at_epoch_ms=reserved_at_epoch_ms,
                updated_at_epoch_ms=completed_at_epoch_ms,
                ceremony_receipt_sha256=result.receipt.to_dict()["ceremony_receipt_sha256"],
                verification_receipt_sha256=result.verification_receipt.to_dict()["verification_receipt_sha256"],
            )
            self._write(final, final_failure_injector)
            return final, result


__all__ = [
    "DurableSigningCeremonyJournal",
    "DurableSigningJournalReceipt",
    "DurableSigningJournalState",
    "JOURNAL_RECEIPT_VERSION",
    "JOURNAL_VERSION",
]
