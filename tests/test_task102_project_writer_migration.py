from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task102_project_manifest_transaction import (
    PROTOCOL_VERSION,
    ContractRecord,
    seal_record,
)
from ai_video_production.task102_project_writer_migration import (
    ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
    PmstWriterMigrationRouter,
    WRITER_ROUTES,
)


def h(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def enrollment(
    *,
    status: str = "ACTIVE",
    matrix_sha256: str = ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256,
) -> dict:
    return seal_record(
        {
            "record_type": "PMST_ENROLLMENT_V1",
            "protocol_version": PROTOCOL_VERSION,
            "project_registration_id": "registration-1",
            "project_id": "project-1",
            "root_physical_identity_ref": "root-physical-1",
            "control_physical_identity_ref": "control-physical-1",
            "manifest_physical_identity_ref": "manifest-physical-1",
            "volume_binding_sha256": h("volume"),
            "owner_dacl_binding_sha256": h("dacl"),
            "writer_migration_matrix_sha256": matrix_sha256,
            "broker_install_binding_sha256": h("install"),
            "enrollment_epoch": "epoch-1",
            "created_at": "2026-09-29T00:00:00Z",
            "status": status,
        },
        kind="enrollment",
    )


def request(
    *,
    profile_id: str = "task043-manifest-create-v1",
    registration_id: str = "registration-1",
    operation_id: str = "operation-1",
) -> dict:
    successor = {"fixture": "manifest"}
    intent = seal_record(
        {
            "protocol_version": PROTOCOL_VERSION,
            "record_type": "PMST_OPERATION_INTENT_V1",
            "project_registration_id": registration_id,
            "operation_id": operation_id,
            "operation_kind": "MANIFEST_CREATE_V1",
            "operation_profile_id": profile_id,
            "caller_task_id": "TASK-043",
            "caller_build_sha256": h("build"),
            "caller_policy_sha256": h("policy"),
            "requested_at": "2026-09-29T00:00:00Z",
            "expires_at": "2026-09-29T00:05:00Z",
            "payload": {
                "successor_manifest": successor,
                "successor_manifest_sha256": sha256_bytes(canonical_json_bytes(successor)),
                "semantic_authorization_sha256": h("authority"),
            },
        },
        kind="intent",
    )
    return seal_record(
        {
            "protocol_version": PROTOCOL_VERSION,
            "record_type": "PMST_PRIVATE_REQUEST_V1",
            "broker_instance_id": "broker-1",
            "session_id": "session-1",
            "request_nonce_id": "nonce-1",
            "intent": intent,
        },
        kind="request",
    )


def public_status(req: dict, *, operation_id: str | None = None) -> dict:
    intent = req["intent"]
    return seal_record(
        {
            "record_type": "PMST_PUBLIC_OPERATION_STATUS_V1",
            "protocol_version": PROTOCOL_VERSION,
            "operation_id": operation_id or intent["operation_id"],
            "operation_kind": intent["operation_kind"],
            "operation_profile_id": intent["operation_profile_id"],
            "intent_sha256": intent["intent_sha256"],
            "request_sha256": req["request_sha256"],
            "status": "COMMITTED_WITH_READBACK",
            "reason_codes": [],
            "operation_witness_sha256": h("witness"),
            "readback_sha256": h("readback"),
            "retry_allowed": False,
            "human_recovery_required": False,
            "effect_count": 1,
        },
        kind="public",
    )


class Resolver:
    def __init__(self, value: dict | None) -> None:
        self.value = value
        self.observed_roots: list[Path] = []

    def resolve(self, project_root: Path) -> dict | None:
        self.observed_roots.append(project_root)
        return self.value


class Port:
    def __init__(self, response_factory=public_status) -> None:
        self.response_factory = response_factory
        self.calls: list[tuple[str, ContractRecord, ContractRecord]] = []

    def execute(
        self,
        *,
        route_id: str,
        request: ContractRecord,
        enrollment: ContractRecord,
    ) -> dict:
        self.calls.append((route_id, request, enrollment))
        return self.response_factory(request.to_dict())


def assert_error(code: str, call) -> ProductError:
    with pytest.raises(ProductError) as caught:
        call()
    assert caught.value.code == code
    return caught.value


def test_registry_exactly_matches_accepted_d1_routes_and_matrix_digest() -> None:
    assert tuple(WRITER_ROUTES) == tuple(f"PMST-R{index:03d}" for index in range(1, 14))
    assert {route.disposition for route in WRITER_ROUTES.values()} == {
        "BROKER_MANIFEST_TRANSACTION",
        "BROKER_OBJECT_OPERATION",
        "BROKER_READ_LEASE",
        "SEMANTIC_OWNER_REDESIGN_REQUIRED",
        "UNSUPPORTED_BLOCKED",
    }
    matrix = Path("docs/ai-team/tasks/TASK-102/pmst-d1-protected-control-mutation-matrix-r0.json")
    assert f"sha256:{hashlib.sha256(matrix.read_bytes()).hexdigest()}" == ACCEPTED_WRITER_MIGRATION_MATRIX_SHA256
    assert WRITER_ROUTES["PMST-R013"].admitted_profiles == ()
    assert all(route.admitted_profiles for route_id, route in WRITER_ROUTES.items() if route_id != "PMST-R013")


def test_default_feature_disabled_router_preserves_unenrolled_legacy_and_read_only(tmp_path: Path) -> None:
    router = PmstWriterMigrationRouter()
    assert router.require_legacy_access(tmp_path, route_id="PMST-R001", access_kind="MUTATION") is WRITER_ROUTES["PMST-R001"]
    assert router.require_legacy_access(tmp_path, route_id="PMST-R009", access_kind="LOCK") is WRITER_ROUTES["PMST-R009"]
    assert router.require_legacy_access(tmp_path, route_id="PMST-R004", access_kind="READ_ONLY") is WRITER_ROUTES["PMST-R004"]


@pytest.mark.parametrize("status", ["PREPARED", "ACTIVE", "SUSPENDED", "REVOKED"])
@pytest.mark.parametrize("access_kind", ["MUTATION", "LOCK"])
def test_every_enrolled_state_blocks_legacy_mutation_and_lock(
    tmp_path: Path,
    status: str,
    access_kind: str,
) -> None:
    router = PmstWriterMigrationRouter(enrollment_resolver=Resolver(enrollment(status=status)))
    error = assert_error(
        "ERR_PMST_LEGACY_WRITER_BLOCKED",
        lambda: router.require_legacy_access(
            tmp_path,
            route_id="PMST-R001",
            access_kind=access_kind,
        ),
    )
    assert error.details == {
        "route_id": "PMST-R001",
        "access_kind": access_kind,
        "enrollment_status": status,
    }
    assert router.require_legacy_access(tmp_path, route_id="PMST-R001", access_kind="READ_ONLY")


def test_active_exact_enrollment_routes_strict_request_without_forwarding_path(tmp_path: Path) -> None:
    resolver = Resolver(enrollment())
    port = Port()
    router = PmstWriterMigrationRouter(enrollment_resolver=resolver, writer_port=port)
    req = request()

    result = router.execute(tmp_path, route_id="PMST-R001", private_request=req)

    assert result.data["status"] == "COMMITTED_WITH_READBACK"
    assert resolver.observed_roots == [tmp_path.resolve()]
    assert len(port.calls) == 1
    route_id, parsed_request, parsed_enrollment = port.calls[0]
    assert route_id == "PMST-R001"
    assert isinstance(parsed_request, ContractRecord)
    assert isinstance(parsed_enrollment, ContractRecord)
    assert parsed_request.data["request_sha256"] == req["request_sha256"]


def test_unenrolled_inactive_matrix_mismatch_and_missing_port_fail_before_effect(tmp_path: Path) -> None:
    req = request()
    port = Port()
    cases = [
        (Resolver(None), port, "ERR_PMST_PROJECT_NOT_ENROLLED"),
        (Resolver(enrollment(status="SUSPENDED")), port, "ERR_PMST_ENROLLMENT_NOT_ACTIVE"),
        (Resolver(enrollment(matrix_sha256=h("other-matrix"))), port, "ERR_PMST_WRITER_MIGRATION_MATRIX_MISMATCH"),
        (Resolver(enrollment()), None, "ERR_PMST_WRITER_PORT_UNAVAILABLE"),
    ]
    for resolver, writer_port, code in cases:
        before = len(port.calls)
        router = PmstWriterMigrationRouter(enrollment_resolver=resolver, writer_port=writer_port)
        assert_error(code, lambda router=router: router.execute(tmp_path, route_id="PMST-R001", private_request=req))
        assert len(port.calls) == before


def test_unknown_old_malformed_registration_and_profile_routes_fail_closed(tmp_path: Path) -> None:
    port = Port()
    router = PmstWriterMigrationRouter(enrollment_resolver=Resolver(enrollment()), writer_port=port)
    assert_error(
        "ERR_PMST_ROUTE_UNREGISTERED",
        lambda: router.require_legacy_access(tmp_path, route_id="PMST-R999", access_kind="MUTATION"),
    )
    assert_error(
        "ERR_PMST_UNSUPPORTED_WRITER_BLOCKED",
        lambda: router.require_legacy_access(tmp_path, route_id="PMST-R013", access_kind="READ_ONLY"),
    )
    assert_error(
        "ERR_PMST_PRIVATE_REQUEST_INVALID",
        lambda: router.execute(tmp_path, route_id="PMST-R001", private_request={}),
    )
    assert_error(
        "ERR_PMST_REGISTRATION_MISMATCH",
        lambda: router.execute(tmp_path, route_id="PMST-R001", private_request=request(registration_id="registration-2")),
    )
    assert_error(
        "ERR_PMST_ROUTE_PROFILE_MISMATCH",
        lambda: router.execute(tmp_path, route_id="PMST-R001", private_request=request(profile_id="task036-bootstrap-create-v1")),
    )
    assert port.calls == []


def test_public_result_must_be_strict_and_bound_to_request(tmp_path: Path) -> None:
    req = request()
    invalid_port = Port(lambda routed: {"not": "a-status"})
    invalid_router = PmstWriterMigrationRouter(enrollment_resolver=Resolver(enrollment()), writer_port=invalid_port)
    assert_error(
        "ERR_PMST_PUBLIC_STATUS_INVALID",
        lambda: invalid_router.execute(tmp_path, route_id="PMST-R001", private_request=req),
    )

    mismatch_port = Port(lambda routed: public_status(routed, operation_id="operation-other"))
    mismatch_router = PmstWriterMigrationRouter(enrollment_resolver=Resolver(enrollment()), writer_port=mismatch_port)
    assert_error(
        "ERR_PMST_PUBLIC_STATUS_BINDING_MISMATCH",
        lambda: mismatch_router.execute(tmp_path, route_id="PMST-R001", private_request=req),
    )


def test_invalid_enrollment_and_project_root_fail_closed(tmp_path: Path) -> None:
    router = PmstWriterMigrationRouter(enrollment_resolver=Resolver({"invalid": True}), writer_port=Port())
    assert_error(
        "ERR_PMST_ENROLLMENT_INVALID",
        lambda: router.require_legacy_access(tmp_path, route_id="PMST-R001", access_kind="MUTATION"),
    )
    missing = tmp_path / "missing"
    assert_error(
        "ERR_PMST_PROJECT_ROOT_INVALID",
        lambda: PmstWriterMigrationRouter().require_legacy_access(
            missing,
            route_id="PMST-R001",
            access_kind="MUTATION",
        ),
    )
