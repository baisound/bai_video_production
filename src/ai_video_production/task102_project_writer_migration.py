"""TASK-102 PMST-I2 Product writer-migration admission kernel.

This module is deliberately effect-free.  It binds the accepted D1 migration
matrix to strict I1 request/result records and keeps Product enrollment disabled
unless a later composition injects both an enrollment resolver and a PMST port.
It never forwards a host path to that port.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .errors import ProductError, ProductErrorCategory
from .task102_project_manifest_transaction import (
    OPERATION_KINDS,
    ContractRecord,
    parse_enrollment,
    parse_private_request,
    parse_public_status,
)


ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256 = (
    "sha256:ad7f4a22a560b84c8e317b2e450c3097110877e04f25f0352cc62651439a8dd5"
)

_DISPOSITIONS = frozenset(
    {
        "BROKER_MANIFEST_TRANSACTION",
        "BROKER_OBJECT_OPERATION",
        "BROKER_READ_LEASE",
        "SEMANTIC_OWNER_REDESIGN_REQUIRED",
        "UNSUPPORTED_BLOCKED",
    }
)
_LEGACY_ACCESS_KINDS = frozenset({"MUTATION", "LOCK", "READ_ONLY"})


@dataclass(frozen=True, slots=True)
class WriterRoute:
    """One immutable source-to-PMST route from the accepted D1 matrix."""

    route_id: str
    disposition: str
    admitted_profiles: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.route_id not in {f"PMST-R{index:03d}" for index in range(1, 14)}:
            raise ValueError("writer route id is outside the accepted D1 matrix")
        if self.disposition not in _DISPOSITIONS:
            raise ValueError("writer route disposition is unsupported")
        if type(self.admitted_profiles) is not tuple:
            raise ValueError("writer route profiles must be an immutable tuple")
        if len(self.admitted_profiles) != len(set(self.admitted_profiles)):
            raise ValueError("writer route profiles must be unique")
        if self.disposition == "UNSUPPORTED_BLOCKED" and self.admitted_profiles:
            raise ValueError("blocked writer route cannot admit profiles")
        if self.disposition != "UNSUPPORTED_BLOCKED" and not self.admitted_profiles:
            raise ValueError("migrated writer route requires an exact profile")
        for operation_kind, profile_id in self.admitted_profiles:
            if operation_kind not in OPERATION_KINDS or not profile_id:
                raise ValueError("writer route operation/profile binding is invalid")

    def admits(self, operation_kind: str, profile_id: str) -> bool:
        return (operation_kind, profile_id) in self.admitted_profiles


def _route(
    route_id: str,
    disposition: str,
    *profiles: tuple[str, str],
) -> WriterRoute:
    return WriterRoute(route_id, disposition, tuple(profiles))


WRITER_ROUTES: Mapping[str, WriterRoute] = MappingProxyType(
    {
        "PMST-R001": _route(
            "PMST-R001",
            "BROKER_MANIFEST_TRANSACTION",
            ("MANIFEST_CREATE_V1", "task043-manifest-create-v1"),
            ("MANIFEST_TRANSITION_V1", "task043-manifest-transition-v1"),
        ),
        "PMST-R002": _route(
            "PMST-R002",
            "SEMANTIC_OWNER_REDESIGN_REQUIRED",
            ("MANIFEST_TRANSITION_V1", "task043-coordinated-save-v1"),
        ),
        "PMST-R003": _route(
            "PMST-R003",
            "BROKER_OBJECT_OPERATION",
            ("CONTROL_OBJECT_CAS_V1", "task076-jobs-cas-v1"),
        ),
        "PMST-R004": _route(
            "PMST-R004",
            "BROKER_OBJECT_OPERATION",
            ("CONTROL_APPEND_CHAIN_V1", "task043-history-append-v1"),
        ),
        "PMST-R005": _route(
            "PMST-R005",
            "BROKER_OBJECT_OPERATION",
            ("CONTROL_SNAPSHOT_SET_V1", "task043-autosave-snapshot-v1"),
        ),
        "PMST-R006": _route(
            "PMST-R006",
            "BROKER_OBJECT_OPERATION",
            ("CONTROL_SNAPSHOT_SET_V1", "task043-backup-snapshot-v1"),
        ),
        "PMST-R007": _route(
            "PMST-R007",
            "BROKER_OBJECT_OPERATION",
            ("CONTROL_APPEND_CHAIN_V1", "task046-voice-profile-append-v1"),
        ),
        "PMST-R008": _route(
            "PMST-R008",
            "BROKER_OBJECT_OPERATION",
            ("CONTROL_RECOVERY_OBJECT_V1", "task044-timeline-history-recovery-v1"),
        ),
        "PMST-R009": _route(
            "PMST-R009",
            "BROKER_READ_LEASE",
            ("PROJECT_READ_LEASE_V1", "project-read-lease-v1"),
        ),
        "PMST-R010": _route(
            "PMST-R010",
            "SEMANTIC_OWNER_REDESIGN_REQUIRED",
            ("PROJECT_READ_LEASE_V1", "task029-read-lease-v1"),
            ("MANIFEST_TRANSITION_V1", "task029-participant-manifest-v1"),
        ),
        "PMST-R011": _route(
            "PMST-R011",
            "BROKER_MANIFEST_TRANSACTION",
            ("MANIFEST_CREATE_V1", "task036-bootstrap-create-v1"),
            ("MANIFEST_CREATE_V1", "task043-import-create-v1"),
        ),
        "PMST-R012": _route(
            "PMST-R012",
            "BROKER_MANIFEST_TRANSACTION",
            ("MANIFEST_TRANSITION_V1", "task026-audio-placement-manifest-v1"),
            ("MANIFEST_TRANSITION_V1", "task044-interactive-timeline-manifest-v1"),
            ("MANIFEST_TRANSITION_V1", "task043-project-migration-manifest-v1"),
            ("MANIFEST_TRANSITION_V1", "task043-history-restore-manifest-v1"),
            ("MANIFEST_TRANSITION_V1", "task042-timeline-audio-manifest-v1"),
            ("MANIFEST_TRANSITION_V1", "task048-meter-policy-manifest-v1"),
            ("MANIFEST_TRANSITION_V1", "task029-montage-learning-manifest-v1"),
        ),
        "PMST-R013": _route("PMST-R013", "UNSUPPORTED_BLOCKED"),
    }
)


class PmstEnrollmentResolver(Protocol):
    """Trusted local composition dependency; paths never cross the PMST port."""

    def resolve(self, project_root: Path) -> Mapping[str, Any] | None: ...


class PmstProductWriterPort(Protocol):
    """Closed Product-to-broker boundary for one already parsed request."""

    def execute(
        self,
        *,
        route_id: str,
        request: ContractRecord,
        enrollment: ContractRecord,
    ) -> Mapping[str, Any]: ...


class UnenrolledProjectResolver:
    """Default feature-disabled resolver: every Project stays unenrolled."""

    @staticmethod
    def resolve(project_root: Path) -> None:
        del project_root
        return None


class PmstWriterMigrationRouter:
    """Fail-closed routing without Product enrollment or filesystem mutation."""

    def __init__(
        self,
        *,
        enrollment_resolver: PmstEnrollmentResolver | None = None,
        writer_port: PmstProductWriterPort | None = None,
    ) -> None:
        self._enrollment_resolver = enrollment_resolver or UnenrolledProjectResolver()
        self._writer_port = writer_port

    @staticmethod
    def _project_root(value: str | Path) -> Path:
        root = Path(value)
        if root.is_symlink() or not root.is_dir():
            raise ProductError(
                "ERR_PMST_PROJECT_ROOT_INVALID",
                "PMST routing requires an existing regular Project root",
                ProductErrorCategory.SECURITY,
            )
        return root.resolve(strict=True)

    @staticmethod
    def _writer_route(route_id: str) -> WriterRoute:
        route = WRITER_ROUTES.get(route_id)
        if route is None:
            raise ProductError(
                "ERR_PMST_ROUTE_UNREGISTERED",
                "Protected Project mutation route is not registered",
                ProductErrorCategory.SECURITY,
                details={"route_id": route_id},
            )
        if route.disposition == "UNSUPPORTED_BLOCKED":
            raise ProductError(
                "ERR_PMST_UNSUPPORTED_WRITER_BLOCKED",
                "Old, external or unregistered Project writers are blocked",
                ProductErrorCategory.AUTHORIZATION,
                details={"route_id": route_id},
            )
        return route

    def _enrollment(self, project_root: Path) -> ContractRecord | None:
        value = self._enrollment_resolver.resolve(project_root)
        if value is None:
            return None
        try:
            return parse_enrollment(value)
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_PMST_ENROLLMENT_INVALID",
                "Project enrollment evidence is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc

    def require_legacy_access(
        self,
        project_root: str | Path,
        *,
        route_id: str,
        access_kind: str,
    ) -> WriterRoute:
        """Allow legacy access only for a proven unenrolled Project.

        READ_ONLY is compatibility inspection and creates no lease or mutation
        authority.  Callers that need a pinned integrity view must use R009/R010.
        """

        route = self._writer_route(route_id)
        if access_kind not in _LEGACY_ACCESS_KINDS:
            raise ValueError("legacy access kind is unsupported")
        root = self._project_root(project_root)
        enrollment = self._enrollment(root)
        if access_kind == "READ_ONLY":
            return route
        if enrollment is None:
            return route
        raise ProductError(
            "ERR_PMST_LEGACY_WRITER_BLOCKED",
            "Legacy Project mutation is blocked for an enrolled Project",
            ProductErrorCategory.AUTHORIZATION,
            details={
                "route_id": route_id,
                "access_kind": access_kind,
                "enrollment_status": enrollment.data["status"],
            },
        )

    def execute(
        self,
        project_root: str | Path,
        *,
        route_id: str,
        private_request: Mapping[str, Any],
    ) -> ContractRecord:
        """Validate and route one enrolled request without forwarding a path."""

        route = self._writer_route(route_id)
        root = self._project_root(project_root)
        enrollment = self._enrollment(root)
        if enrollment is None:
            raise ProductError(
                "ERR_PMST_PROJECT_NOT_ENROLLED",
                "Broker routing is unavailable for an unenrolled Project",
                ProductErrorCategory.STATE,
                details={"route_id": route_id},
            )
        if enrollment.data["status"] != "ACTIVE":
            raise ProductError(
                "ERR_PMST_ENROLLMENT_NOT_ACTIVE",
                "Project enrollment is not active",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"route_id": route_id, "enrollment_status": enrollment.data["status"]},
            )
        if enrollment.data["writer_migration_matrix_sha256"] != ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256:
            raise ProductError(
                "ERR_PMST_WRITER_MIGRATION_MATRIX_MISMATCH",
                "Project enrollment does not bind the accepted complete writer migration",
                ProductErrorCategory.SECURITY,
                details={"route_id": route_id},
            )
        if self._writer_port is None:
            raise ProductError(
                "ERR_PMST_WRITER_PORT_UNAVAILABLE",
                "PMST writer port is unavailable",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"route_id": route_id},
            )
        try:
            request = parse_private_request(private_request)
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_PMST_PRIVATE_REQUEST_INVALID",
                "PMST private request is invalid",
                ProductErrorCategory.VALIDATION,
                details={"route_id": route_id},
            ) from exc
        intent = request.data["intent"]
        if intent["project_registration_id"] != enrollment.data["project_registration_id"]:
            raise ProductError(
                "ERR_PMST_REGISTRATION_MISMATCH",
                "PMST request registration does not match enrollment",
                ProductErrorCategory.SECURITY,
                details={"route_id": route_id},
            )
        if not route.admits(intent["operation_kind"], intent["operation_profile_id"]):
            raise ProductError(
                "ERR_PMST_ROUTE_PROFILE_MISMATCH",
                "PMST operation kind/profile is not admitted for this writer route",
                ProductErrorCategory.AUTHORIZATION,
                details={"route_id": route_id},
            )
        response = self._writer_port.execute(
            route_id=route_id,
            request=request,
            enrollment=enrollment,
        )
        try:
            public = parse_public_status(response)
        except (TypeError, ValueError) as exc:
            raise ProductError(
                "ERR_PMST_PUBLIC_STATUS_INVALID",
                "PMST writer returned an invalid public status",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"route_id": route_id},
            ) from exc
        expected = (
            intent["operation_id"],
            intent["operation_kind"],
            intent["operation_profile_id"],
            intent["intent_sha256"],
            request.data["request_sha256"],
        )
        actual = tuple(
            public.data[field]
            for field in (
                "operation_id",
                "operation_kind",
                "operation_profile_id",
                "intent_sha256",
                "request_sha256",
            )
        )
        if actual != expected:
            raise ProductError(
                "ERR_PMST_PUBLIC_STATUS_BINDING_MISMATCH",
                "PMST public status does not bind the routed request",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"route_id": route_id},
            )
        return public


DEFAULT_PMST_WRITER_MIGRATION_ROUTER = PmstWriterMigrationRouter()


__all__ = [
    "ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256",
    "DEFAULT_PMST_WRITER_MIGRATION_ROUTER",
    "PmstEnrollmentResolver",
    "PmstProductWriterPort",
    "PmstWriterMigrationRouter",
    "UnenrolledProjectResolver",
    "WRITER_ROUTES",
    "WriterRoute",
]
