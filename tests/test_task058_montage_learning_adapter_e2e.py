from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

import ai_video_production.montage_learning_connector_readiness as connector_readiness
from ai_video_production.montage_learning_bridge_application import (
    GenericObservationCoordinates,
    MontageLearningBridgeApplication,
)
from ai_video_production.montage_learning_canonical_admission_transaction import (
    MontageLearningCanonicalAdmissionTransactionStore,
)
from ai_video_production.montage_learning_connector_readiness import (
    ConnectorReadinessEvidence,
    _ConnectorReadinessEvidenceV2,
    _ConnectorReadinessComponentV2,
    _ConnectorReadinessPredicateV2,
    MontageLearningConnectorReadinessError,
    ProfileSourceBinding,
    production_readiness_evidence,
    publish_prebuilt_advisory_profile,
    validate_prebuilt_advisory_profile,
)
from ai_video_production.montage_learning_file_bridge import (
    BridgeLayout,
    publish_current_profile,
    provision_bridge,
    recover_current_profile,
)
from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.serialization import sha256_json


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(
    r"C:\Users\user\.codex\skills\bvp-montage-learning-adapter"
)
SKILL_SCRIPT = SKILL_ROOT / "scripts" / "bvp_adapter.py"
SKILL_CONFIG = SKILL_ROOT / "config" / "bvp-learning-connector.json"
SKILL_SCHEMA = SKILL_ROOT / "schemas" / "connector-file-bridge.schema.json"
EXTERNAL_SKILL_ROOT_ENV = "BVP_TASK058_SKILL_ROOT"
_SKILL_ROLES = (
    ("script", Path("scripts") / "bvp_adapter.py"),
    ("config", Path("config") / "bvp-learning-connector.json"),
    ("schema", Path("schemas") / "connector-file-bridge.schema.json"),
)
_EXTERNAL_SKILL_EXPECTATIONS = {
    "script": (
        53_438,
        "070d2295869cb43c9fe8cb733238ff04085fa6815ac006385072d9c18da3949e",
    ),
    "config": (
        406,
        "da41b71292fd2a9fa2070eba531e06fafc0e84f9bbc1d26c27b0af79c5e2db6c",
    ),
    "schema": (
        5_812,
        "470fb97a85bb924678e51a9fca313c21bc5eb9c6eb0f0f0da265ca9b6da43b9d",
    ),
}


def _is_reparse_or_symlink(path: Path) -> bool:
    metadata = path.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse_flag
    )


def _external_skill_paths(root: Path) -> tuple[Path, Path, Path]:
    if not root.is_absolute():
        raise AssertionError("TASK058_EXTERNAL_SKILL_ROOT_NOT_ABSOLUTE")
    try:
        root_metadata = root.lstat()
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise AssertionError("TASK058_EXTERNAL_SKILL_ROOT_UNAVAILABLE") from exc
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise AssertionError("TASK058_EXTERNAL_SKILL_ROOT_NOT_DIRECTORY")

    for candidate in (root, *root.parents):
        try:
            if _is_reparse_or_symlink(candidate):
                raise AssertionError("TASK058_EXTERNAL_SKILL_REPARSE_REJECTED")
        except OSError as exc:
            raise AssertionError("TASK058_EXTERNAL_SKILL_ANCESTOR_UNAVAILABLE") from exc
    if os.path.normcase(str(root.absolute())) != os.path.normcase(str(resolved_root)):
        raise AssertionError("TASK058_EXTERNAL_SKILL_ROOT_IDENTITY_DRIFT")

    paths: list[Path] = []
    identities: set[tuple[int, int]] = set()
    for role, relative_path in _SKILL_ROLES:
        path = root / relative_path
        try:
            component = root
            for part in relative_path.parts:
                component /= part
                if _is_reparse_or_symlink(component):
                    raise AssertionError("TASK058_EXTERNAL_SKILL_REPARSE_REJECTED")
            before = path.lstat()
            if _is_reparse_or_symlink(path) or not stat.S_ISREG(before.st_mode):
                raise AssertionError("TASK058_EXTERNAL_SKILL_ROLE_NOT_REGULAR")
            resolved_path = path.resolve(strict=True)
            resolved_path.relative_to(resolved_root)
            payload = path.read_bytes()
            after = path.lstat()
        except (OSError, ValueError) as exc:
            raise AssertionError("TASK058_EXTERNAL_SKILL_ROLE_UNAVAILABLE") from exc
        identity = (before.st_dev, before.st_ino)
        if before.st_ino and identity in identities:
            raise AssertionError("TASK058_EXTERNAL_SKILL_DUPLICATE_ROLE")
        identities.add(identity)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise AssertionError("TASK058_EXTERNAL_SKILL_ROLE_DRIFT")
        expected_size, expected_sha256 = _EXTERNAL_SKILL_EXPECTATIONS[role]
        if len(payload) != expected_size or sha256(payload).hexdigest() != expected_sha256:
            raise AssertionError("TASK058_EXTERNAL_SKILL_CONTENT_DRIFT")
        paths.append(path)

    for index, path in enumerate(paths):
        for other in paths[index + 1 :]:
            try:
                if os.path.samefile(path, other):
                    raise AssertionError("TASK058_EXTERNAL_SKILL_DUPLICATE_ROLE")
            except OSError as exc:
                raise AssertionError("TASK058_EXTERNAL_SKILL_IDENTITY_UNAVAILABLE") from exc
    return paths[0], paths[1], paths[2]


def _skill_paths_for_e2e() -> tuple[tuple[Path, Path, Path], bool]:
    candidate = os.environ.get(EXTERNAL_SKILL_ROOT_ENV)
    if candidate is None:
        return (SKILL_SCRIPT, SKILL_CONFIG, SKILL_SCHEMA), False
    if not candidate:
        raise AssertionError("TASK058_EXTERNAL_SKILL_ROOT_EMPTY")
    return _external_skill_paths(Path(candidate)), True


def _profile(profile_id: str = "PROFILE-FIXTURE-001") -> dict[str, object]:
    payload = {
        "projection_version": "1.0.0",
        "preferences": [
            {
                "preference_id": "protect-staccato-microcuts",
                "decision": "PROTECT",
                "target": "STACCATO_MICROCUT_CLUSTER",
                "contexts": ["high-energy build"],
                "confidence": 0.5,
                "confirmation_count": 1,
                "reason_codes": ["HUMAN_FINAL_CONFIRMED"],
                "ranking_bias": 0.5,
            }
        ],
    }
    return {
        "schema_version": "1.0.0",
        "message_type": "BvpMontagePreferenceProfileDelivery",
        "contract_profile": "bvp-task029-file-bridge-v1",
        "profile_contract": "bvp-task029-montage-preference-projection-v1",
        "profile_id": profile_id,
        "profile_version": 1,
        "owner_scope_hash": "sha256:" + "a" * 64,
        "source_record_count": 1,
        "profile_sha256": sha256_json(payload),
        "advisory_only": True,
        "canonical_timeline": False,
        "auto_apply_authorized": False,
        "payload": payload,
    }


def _learning() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "message_type": "MontageLearningExport",
        "record_id": "e2e-observation-001",
        "source_feedback_id": "feedback-001",
        "proposal_id": "proposal-001",
        "timeline_fps": {"numerator": 60, "denominator": 1},
        "style_profile": "dbd-aggressive",
        "music_context": {"anchor_kind": "DROP"},
        "video_context": {"event_type": "PALLET_DROP"},
        "proposal": {"timeline_frame": 600},
        "human_final": {
            "timeline_frame": 604,
            "status": "moved",
            "provenance": {"actor_role": "owner-editor"},
        },
        "delta_frames": 4,
        "result": "moved",
        "privacy": {
            "safe_export": True,
            "raw_actor_exported": False,
            "redacted_field_paths": [],
        },
        "validation_status": {
            "planning": "PASS",
            "static": "PASS",
            "package": "PASS",
            "runtime": "NOT_RUN",
        },
        "adapter_metadata": {
            "canonical_timeline": False,
            "absolute_host_path_included": False,
        },
    }


def _run_adapter(
    tmp_path: Path,
    skill_script: Path,
    *arguments: str,
    skill_paths: tuple[Path, Path, Path] | None = None,
) -> dict[str, object]:
    before_digest = None
    if skill_paths is not None:
        observed = _external_skill_paths(skill_script.parents[1])
        if tuple(path.resolve() for path in observed) != tuple(
            path.resolve() for path in skill_paths
        ):
            raise AssertionError("TASK058_ADAPTER_SKILL_IDENTITY_DRIFT")
        before_digest = _skill_digest(observed)
    output = tmp_path / f"adapter-{len(list(tmp_path.glob('adapter-*.json')))}.json"
    child_environment = os.environ.copy()
    child_environment.pop(EXTERNAL_SKILL_ROOT_ENV, None)
    completed = subprocess.run(
        [sys.executable, str(skill_script), *arguments, "--output", str(output)],
        check=False,
        capture_output=True,
        env=child_environment,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise AssertionError("TASK058_ADAPTER_CHILD_FAILED")
    if skill_paths is not None:
        observed = _external_skill_paths(skill_script.parents[1])
        if tuple(path.resolve() for path in observed) != tuple(
            path.resolve() for path in skill_paths
        ) or _skill_digest(observed) != before_digest:
            raise AssertionError("TASK058_ADAPTER_SKILL_IDENTITY_DRIFT")
    return json.loads(output.read_text(encoding="utf-8"))


def _skill_digest(skill_paths: tuple[Path, Path, Path]) -> str:
    digest = sha256()
    for path in skill_paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _canonical_store(tmp_path: Path) -> MontageLearningCanonicalAdmissionTransactionStore:
    project = tmp_path / "e2e-canonical-project"
    anchor = tmp_path / "e2e-canonical-anchor"
    project.mkdir()
    anchor.mkdir()
    manifest = ProductProjectManifest.create(
        project_id="task058-e2e-project",
        project_revision=1,
        product_version="0.1.0",
        timebase=ProjectTimebase(30, 1),
        child_bindings=(),
        created_at="2026-08-27T00:00:00Z",
        updated_at="2026-08-27T00:00:00Z",
    )
    ProductProjectManifestStore.save(project, manifest)
    return MontageLearningCanonicalAdmissionTransactionStore(
        project,
        anchor,
        canonical_store_id="task058-e2e-canonical",
        bridge_instance_id="task058-e2e-bridge",
    )


def test_readiness_schema_mirror_and_unbound_production_are_fail_closed(tmp_path):
    public = ROOT / "schemas" / "montage-learning-connector-readiness.schema.json"
    packaged = (
        ROOT
        / "src"
        / "ai_video_production"
        / "schema_resources"
        / public.name
    )
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    result = publish_prebuilt_advisory_profile(
        layout,
        _profile(),
        source_binding=ProfileSourceBinding.unbound_production(),
    )
    assert result.status == "SOURCE_NOT_BOUND"
    assert result.written is False
    assert not layout.current_profile.exists()

    evidence = production_readiness_evidence(
        bridge_state="OWNERSHIP_UNVERIFIED",
        import_state="OBSERVATION_RECORDED",
        adapter_state="LOAD_PROFILE_PASS",
        adapter_contract_e2e_pass=True,
        default_skill_config_unchanged=True,
    ).to_dict()
    Draft202012Validator(schema).validate(evidence)
    assert evidence["production_profile_source_bound"] is False
    assert evidence["profile_state"] == "SOURCE_NOT_BOUND"
    assert evidence["activation_state"] == "BLOCKED"
    assert evidence["connector_enabled"] is False
    assert evidence["activation_authorized"] is False

    private_v2 = _readiness_v2("PASS").to_dict()
    assert not Draft202012Validator(schema).is_valid(private_v2)
    assert "ConnectorReadinessEvidenceV2" not in connector_readiness.__all__
    assert "ConnectorReadinessComponentV2" not in connector_readiness.__all__
    assert "ConnectorReadinessPredicateV2" not in connector_readiness.__all__


def test_prebuilt_profile_is_strict_immutable_transport_with_cas(tmp_path):
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    source = ProfileSourceBinding.bound_isolated_fixture()
    envelope = _profile()
    before = json.loads(json.dumps(envelope))

    first = publish_prebuilt_advisory_profile(
        layout,
        envelope,
        source_binding=source,
    )
    second = publish_prebuilt_advisory_profile(
        layout,
        envelope,
        source_binding=source,
    )
    assert first.status == "PUBLISHED"
    assert second.status == "DUPLICATE"
    assert first.written is True
    assert second.written is False
    assert envelope == before
    assert json.loads(layout.current_profile.read_text(encoding="utf-8")) == envelope
    assert first.semantic_projection_generated is False
    assert first.production_profile_source_bound is False

    changed = _profile("PROFILE-FIXTURE-002")
    with pytest.raises(ValueError, match="CAS"):
        publish_prebuilt_advisory_profile(
            layout,
            changed,
            source_binding=source,
        )


def test_profile_immutable_object_pointer_view_marker_and_restart_recovery(tmp_path):
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    value = validate_prebuilt_advisory_profile(_profile())

    def fail_after_payload(phase: str, path: Path) -> None:
        if phase == "after_profile_payload":
            assert path.is_file()
            raise RuntimeError("profile-crash-after-payload")

    with pytest.raises(RuntimeError, match="profile-crash-after-payload"):
        publish_current_profile(
            layout,
            value,
            expected_previous_profile_sha256=None,
            failure_hook=fail_after_payload,
        )
    journal = json.loads(layout.profile_journal.read_text(encoding="utf-8"))
    assert journal["state"] == "PAYLOAD_WRITTEN"
    assert set(journal).isdisjoint({"payload", "preferences", "private_key"})

    pointer = recover_current_profile(layout)
    assert pointer is not None
    assert not layout.profile_journal.exists()
    payload_path = layout.root / pointer["payload_relative_path"]
    assert payload_path.is_file()
    assert layout.profile_pointer.is_file()
    assert layout.profile_marker.is_file()
    assert layout.current_profile.read_bytes() == payload_path.read_bytes()
    assert json.loads(payload_path.read_text(encoding="utf-8")) == value


def test_profile_prepared_retry_is_idempotent_and_downgrade_fails_closed(tmp_path):
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    value = validate_prebuilt_advisory_profile(_profile())

    def fail_prepared(phase: str, path: Path) -> None:
        if phase == "after_profile_prepared":
            assert path == layout.profile_journal
            raise RuntimeError("profile-crash-prepared")

    with pytest.raises(RuntimeError, match="profile-crash-prepared"):
        publish_current_profile(
            layout,
            value,
            expected_previous_profile_sha256=None,
            failure_hook=fail_prepared,
        )
    assert json.loads(layout.profile_journal.read_text(encoding="utf-8"))[
        "state"
    ] == "PREPARED"
    assert publish_current_profile(
        layout, value, expected_previous_profile_sha256=None
    ) == "PUBLISHED"

    stale = _profile("PROFILE-FIXTURE-002")
    stale["profile_version"] = 0
    stale["payload"]["preferences"][0]["ranking_bias"] = 0.25
    stale["profile_sha256"] = sha256_json(stale["payload"])
    with pytest.raises(ValueError, match="stale"):
        publish_prebuilt_advisory_profile(
            layout,
            stale,
            source_binding=ProfileSourceBinding.bound_isolated_fixture(),
            expected_previous_profile_sha256=value["profile_sha256"],
        )


def test_profile_journal_relabel_and_marker_operation_tamper_fail_closed(tmp_path):
    layout = BridgeLayout.for_isolated_test(tmp_path / "journal")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    value = validate_prebuilt_advisory_profile(_profile())

    def fail_after_payload(phase: str, path: Path) -> None:
        del path
        if phase == "after_profile_payload":
            raise RuntimeError("leave-profile-journal")

    with pytest.raises(RuntimeError, match="leave-profile-journal"):
        publish_current_profile(
            layout,
            value,
            expected_previous_profile_sha256=None,
            failure_hook=fail_after_payload,
        )
    journal = json.loads(layout.profile_journal.read_text(encoding="utf-8"))
    journal["state"] = "POINTER_COMMITTED"
    journal["states"].append("POINTER_COMMITTED")
    journal["journal_revision"] += 1
    journal["previous_journal_sha256"] = "sha256:" + "f" * 64
    journal.pop("journal_sha256")
    journal["journal_sha256"] = sha256_json(journal)
    layout.profile_journal.write_text(json.dumps(journal), encoding="utf-8")
    with pytest.raises(ValueError, match="hash chain"):
        recover_current_profile(layout)

    marker_layout = BridgeLayout.for_isolated_test(tmp_path / "marker")
    provision_bridge(marker_layout, bridge_instance_id="bridge-fixture-001")
    assert publish_current_profile(
        marker_layout, value, expected_previous_profile_sha256=None
    ) == "PUBLISHED"
    marker = json.loads(marker_layout.profile_marker.read_text(encoding="utf-8"))
    marker["operation_id"] = "sha256:" + "9" * 64
    marker.pop("marker_self_hash")
    marker["marker_self_hash"] = sha256_json(marker)
    marker_layout.profile_marker.write_text(json.dumps(marker), encoding="utf-8")
    with pytest.raises(ValueError, match="marker binding"):
        recover_current_profile(marker_layout)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"auto_apply_authorized": True}),
        lambda value: value.update({"profile_sha256": "sha256:" + "b" * 64}),
        lambda value: value.update(
            {"payload": {"projection_version": "1.0.0", "timing_preferences": []}}
        ),
        lambda value: value["payload"]["preferences"][0].update(
            {"contexts": [r"C:\private\source.mp4"]}
        ),
        lambda value: value["payload"]["preferences"][0].update(
            {"contexts": ["verbatim transcript: keep this private"]}
        ),
        lambda value: value["payload"]["preferences"][0].update(
            {"contexts": ["api_key=secret"]}
        ),
    ],
)
def test_profile_unknown_authority_hash_and_task055_timing_shape_fail_closed(mutate):
    value = _profile()
    mutate(value)
    with pytest.raises(MontageLearningConnectorReadinessError):
        validate_prebuilt_advisory_profile(value)


def test_source_binding_is_sealed_and_immutable():
    with pytest.raises(TypeError):
        ProfileSourceBinding(
            source_id="forged",
            production_profile_source_bound=True,
            isolated_fixture=False,
        )
    binding = ProfileSourceBinding.unbound_production()
    with pytest.raises(AttributeError):
        binding.production_profile_source_bound = True


def test_readiness_evidence_rejects_forged_production_profile_binding():
    with pytest.raises(
        MontageLearningConnectorReadinessError, match="SOURCE_NOT_BOUND"
    ):
        ConnectorReadinessEvidence(
            bridge_state="AVAILABLE",
            import_state="OBSERVATION_RECORDED",
            profile_state="PUBLISHED",
            adapter_state="LOAD_PROFILE_PASS",
            production_profile_source_bound=True,
            adapter_contract_e2e_pass=True,
            default_skill_config_unchanged=True,
            reason_codes=("SOURCE_NOT_BOUND",),
        )


_READINESS_PREDICATES = {
    "BRIDGE_ROOT_READY": (
        "OWNER_IDENTITY", "WINDOWS_DACL", "NO_REPARSE", "ANCESTOR_IDENTITY",
        "LAYOUT_COMPLETE", "MIGRATION_TERMINAL",
    ),
    "GENERIC_INTAKE_READY": (
        "A_AUTHORITY_CORE", "A_GENERIC_JOURNAL_RECOVERY",
        "DUPLICATE_REVISION_INVARIANT",
        "MANIFEST_CURRENTNESS_ROLLBACK_REJECTED", "IMPORTER_CLAIM_RECOVERY",
        "GENERIC_E2E",
    ),
    "EXACT_ADMISSION_READY": (
        "P1CB_REVALIDATION", "LEDGER_ANCHOR_MARKER_READBACK",
        "PUBLIC_V2_RECEIPT", "EXACT_E2E",
    ),
    "RECEIPT_CORRELATION_READY": (
        "TRUSTED_A_READBACK", "GENERIC_COMMIT_DOMAIN",
        "IMMUTABLE_OUTER_RECEIPT_IDENTITY", "OUTER_RECEIPT_EXACT_MATCH",
        "FORGED_RECEIPT_REJECTED", "LEGACY_STATUS_NON_AUTHORITY",
    ),
    "PROFILE_TRANSPORT_READY": (
        "PRODUCTION_SOURCE_BOUND", "IMMUTABLE_PAYLOAD", "POINTER_CAS_READBACK",
        "V1_VIEW_BYTE_MATCH", "SKILL_LOAD_PROFILE_E2E",
    ),
    "CONNECTOR_E2E_READY": (
        "DISABLED_DEFAULT", "LEGACY_SAFE", "NO_TIMELINE_RESOLVE_EFFECT",
        "NO_AUTOMATIC_PROMOTION", "PACKAGE_SCHEMA_IDENTITY",
    ),
}


def _readiness_component(
    component_id: str, state: str
) -> _ConnectorReadinessComponentV2:
    predicates = []
    for index, predicate_id in enumerate(_READINESS_PREDICATES[component_id]):
        predicate_state = "PASS"
        evidence = "sha256:" + "d" * 64
        reasons: tuple[str, ...] = ()
        if state == "NOT_RUN":
            predicate_state = "NOT_RUN"
            evidence = None
        elif state == "SOURCE_NOT_BOUND":
            predicate_state = "FAIL" if index == 0 else "NOT_RUN"
            evidence = "sha256:" + "e" * 64 if index == 0 else None
            reasons = ("SOURCE_NOT_BOUND",) if index == 0 else ()
        predicates.append(
            _ConnectorReadinessPredicateV2(
                predicate_id=predicate_id,
                state=predicate_state,
                evidence_sha256=evidence,
                reason_codes=reasons,
            )
        )
    complete_evidence = tuple(
        sorted(
            {
                "sha256:" + "a" * 64,
                "sha256:" + "b" * 64,
                "sha256:" + "c" * 64,
                "sha256:" + "d" * 64,
            }
        )
    )
    return _ConnectorReadinessComponentV2.compile(
        component_id=component_id,
        state=state,
        code_sha256="sha256:" + "a" * 64,
        schema_sha256="sha256:" + "b" * 64,
        test_vector_sha256="sha256:" + "c" * 64,
        observed_at="2026-08-27T00:00:00Z",
        expires_at="2026-08-27T00:10:00Z",
        evidence_sha256=complete_evidence if state == "PASS" else (),
        predicates=tuple(predicates),
        reason_codes=("SOURCE_NOT_BOUND",) if state == "SOURCE_NOT_BOUND" else (),
    )


def _readiness_v2(profile_state: str) -> _ConnectorReadinessEvidenceV2:
    components = tuple(
        _readiness_component(
            component_id,
            profile_state if component_id == "PROFILE_TRANSPORT_READY" else "PASS",
        )
        for component_id in _READINESS_PREDICATES
    )
    return _ConnectorReadinessEvidenceV2.compile(
        bvp_main_sha256="sha256:" + "1" * 64,
        bvp_package_sha256="sha256:" + "2" * 64,
        skill_package_sha256="sha256:" + "3" * 64,
        connector_config_sha256="sha256:" + "4" * 64,
        bridge_owner_attestation_sha256="sha256:" + "5" * 64,
        evaluation_mode="FULL_E2E",
        activation_record_sha256=None,
        config_enabled=False,
        verified_at="2026-08-27T00:01:00Z",
        expires_at="2026-08-27T00:09:00Z",
        components=components,
        reason_codes=("SOURCE_NOT_BOUND",) if profile_state == "SOURCE_NOT_BOUND" else (),
    )


def test_private_readiness_v2_is_source_not_bound_or_blocked_without_oracle():
    unbound = _readiness_v2("SOURCE_NOT_BOUND")
    unbound_dict = unbound.to_dict()
    assert unbound_dict["overall_state"] == "SOURCE_NOT_BOUND"
    assert tuple(unbound_dict["components"]) == tuple(_READINESS_PREDICATES)
    assert unbound_dict["connector_enabled"] is False
    assert unbound_dict["activation_authorized"] is False
    assert _ConnectorReadinessEvidenceV2.from_dict(
        json.loads(json.dumps(unbound_dict, sort_keys=True))
    ) == unbound

    ready = _readiness_v2("PASS").to_dict()
    assert ready["overall_state"] == "BLOCKED"
    assert ready["connector_enabled"] is False
    assert ready["activation_authorized"] is False
    assert ready["automatic_promotion_authorized"] is False
    assert ready["timeline_mutation_authorized"] is False
    assert ready["resolve_write_authorized"] is False

    incomplete = _readiness_component("BRIDGE_ROOT_READY", "PASS").to_dict()
    incomplete["evidence_sha256"].pop()
    incomplete["component_self_hash"] = sha256_json(
        {key: value for key, value in incomplete.items() if key != "component_self_hash"}
    )
    with pytest.raises(
        MontageLearningConnectorReadinessError, match="evidence set is incomplete"
    ):
        _ConnectorReadinessComponentV2.from_dict(incomplete)

    expired = _readiness_v2("PASS").to_dict()
    expired["expires_at"] = expired["verified_at"]
    expired.pop("readiness_self_hash")
    expired.pop("readiness_id")
    expired["readiness_id"] = sha256_json(
        {"domain": "BVP_MONTAGE_CONNECTOR_READINESS_ID_V2", **expired}
    )
    expired["readiness_self_hash"] = sha256_json(expired)
    with pytest.raises(
        MontageLearningConnectorReadinessError, match="freshness interval"
    ):
        _ConnectorReadinessEvidenceV2.from_dict(expired)


def test_readiness_v2_relabel_rehash_and_security_model_alias_fail_closed():
    value = _readiness_v2("SOURCE_NOT_BOUND").to_dict()
    value["overall_state"] = "READY_TO_ENABLE"
    value.pop("readiness_self_hash")
    value.pop("readiness_id")
    readiness_id = sha256_json(
        {"domain": "BVP_MONTAGE_CONNECTOR_READINESS_ID_V2", **value}
    )
    value["readiness_id"] = readiness_id
    value["readiness_self_hash"] = sha256_json(
        {**value}
    )
    with pytest.raises(
        MontageLearningConnectorReadinessError, match="overall_state"
    ):
        _ConnectorReadinessEvidenceV2.from_dict(value)

    aliased = _readiness_v2("PASS").to_dict()
    aliased["bridge_security_model"] = "WINDOWS_DACL_VERIFIED"
    with pytest.raises(
        MontageLearningConnectorReadinessError, match="security model"
    ):
        _ConnectorReadinessEvidenceV2.from_dict(aliased)


def _write_test_skill_candidate(
    root: Path, payloads: dict[str, bytes], monkeypatch
) -> tuple[Path, Path, Path]:
    paths = []
    for role, relative_path in _SKILL_ROLES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = payloads[role]
        path.write_bytes(payload)
        monkeypatch.setitem(
            _EXTERNAL_SKILL_EXPECTATIONS,
            role,
            (len(payload), sha256(payload).hexdigest()),
        )
        paths.append(path)
    return paths[0], paths[1], paths[2]


def test_external_skill_candidate_uses_one_exact_runtime_root(tmp_path, monkeypatch):
    root = tmp_path / "external-skill"
    expected_paths = _write_test_skill_candidate(
        root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(root))

    observed_paths, external_candidate = _skill_paths_for_e2e()

    assert external_candidate is True
    assert observed_paths == expected_paths


def test_external_skill_selector_preserves_default_paths(monkeypatch):
    monkeypatch.delenv(EXTERNAL_SKILL_ROOT_ENV, raising=False)

    observed_paths, external_candidate = _skill_paths_for_e2e()

    assert external_candidate is False
    assert observed_paths == (SKILL_SCRIPT, SKILL_CONFIG, SKILL_SCHEMA)


@pytest.mark.parametrize(
    ("candidate", "expected_error"),
    (
        ("", "ROOT_EMPTY"),
        ("relative-skill-root", "ROOT_NOT_ABSOLUTE"),
    ),
)
def test_external_skill_candidate_invalid_root_fails_closed(
    candidate, expected_error, monkeypatch
):
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, candidate)

    with pytest.raises(AssertionError, match=expected_error):
        _skill_paths_for_e2e()


def test_external_skill_candidate_non_directory_root_fails_closed(
    tmp_path, monkeypatch
):
    candidate = tmp_path / "external-skill-file"
    candidate.write_bytes(b"not-a-directory")
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(candidate))

    with pytest.raises(AssertionError, match="ROOT_NOT_DIRECTORY"):
        _skill_paths_for_e2e()


def test_external_skill_candidate_faults_fail_closed(tmp_path, monkeypatch):
    root = tmp_path / "external-skill"
    _script, config, schema = _write_test_skill_candidate(
        root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(root))

    config.write_bytes(b"role-swapped-or-drifted")
    with pytest.raises(AssertionError, match="CONTENT_DRIFT"):
        _skill_paths_for_e2e()

    config.write_bytes(b"config")
    schema.unlink()
    with pytest.raises(AssertionError, match="ROLE_UNAVAILABLE"):
        _skill_paths_for_e2e()


def test_external_skill_candidate_nonregular_role_fails_closed(tmp_path, monkeypatch):
    root = tmp_path / "external-skill"
    _script, _config, schema = _write_test_skill_candidate(
        root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    schema.unlink()
    schema.mkdir()
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(root))

    with pytest.raises(AssertionError, match="ROLE_NOT_REGULAR"):
        _skill_paths_for_e2e()


def test_external_skill_candidate_duplicate_file_identity_fails_closed(
    tmp_path, monkeypatch
):
    root = tmp_path / "external-skill"
    script, config, _schema = _write_test_skill_candidate(
        root,
        {"script": b"same", "config": b"same", "schema": b"schema"},
        monkeypatch,
    )
    config.unlink()
    try:
        os.link(script, config)
    except OSError:
        pytest.skip("hardlink unavailable")
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(root))

    with pytest.raises(AssertionError, match="DUPLICATE_ROLE"):
        _skill_paths_for_e2e()


@pytest.mark.parametrize(
    "linked_directory",
    tuple(relative_path.parts[0] for _role, relative_path in _SKILL_ROLES),
)
def test_external_skill_candidate_intermediate_symlink_fails_closed(
    tmp_path, monkeypatch, linked_directory
):
    target_root = tmp_path / "target-skill"
    _write_test_skill_candidate(
        target_root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    root = tmp_path / "external-skill"
    root.mkdir()
    try:
        (root / linked_directory).symlink_to(
            target_root / linked_directory,
            target_is_directory=True,
        )
    except OSError:
        pytest.skip("directory symlink unavailable")
    for directory in ("config", "schemas"):
        if directory == linked_directory:
            continue
        source = target_root / directory
        destination = root / directory
        destination.mkdir()
        for child in source.iterdir():
            (destination / child.name).write_bytes(child.read_bytes())
    if linked_directory != "scripts":
        source = target_root / "scripts"
        destination = root / "scripts"
        destination.mkdir()
        for child in source.iterdir():
            (destination / child.name).write_bytes(child.read_bytes())
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(root))

    with pytest.raises(AssertionError, match="REPARSE_REJECTED"):
        _skill_paths_for_e2e()


@pytest.mark.parametrize(
    "relative_path",
    tuple(relative_path for _role, relative_path in _SKILL_ROLES),
)
def test_external_skill_candidate_leaf_symlink_fails_closed(
    tmp_path, monkeypatch, relative_path
):
    target_root = tmp_path / "target-skill"
    _write_test_skill_candidate(
        target_root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    root = tmp_path / "external-skill"
    _write_test_skill_candidate(
        root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    selected = root / relative_path
    selected.unlink()
    try:
        selected.symlink_to(target_root / relative_path)
    except OSError:
        pytest.skip("file symlink unavailable")
    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, str(root))

    with pytest.raises(AssertionError, match="REPARSE_REJECTED"):
        _skill_paths_for_e2e()


def test_run_adapter_scrubs_external_skill_selector(tmp_path, monkeypatch):
    observed_environment = {}

    class _Completed:
        returncode = 0

    def _fake_run(arguments, **kwargs):
        observed_environment.update(kwargs["env"])
        output = Path(arguments[arguments.index("--output") + 1])
        output.write_text("{}", encoding="utf-8")
        return _Completed()

    monkeypatch.setenv(EXTERNAL_SKILL_ROOT_ENV, "private-candidate")
    monkeypatch.setattr(subprocess, "run", _fake_run)

    assert _run_adapter(tmp_path, Path("selected-adapter.py"), "connector-status") == {}
    assert EXTERNAL_SKILL_ROOT_ENV not in observed_environment


def test_run_adapter_failure_does_not_echo_child_stderr(tmp_path, monkeypatch):
    class _Failed:
        returncode = 9
        stderr = "PRIVATE_STDERR_SENTINEL"

    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: _Failed())

    with pytest.raises(AssertionError) as failure:
        _run_adapter(tmp_path, Path("selected-adapter.py"), "connector-status")

    assert str(failure.value) == "TASK058_ADAPTER_CHILD_FAILED"
    assert _Failed.stderr not in str(failure.value)


def test_run_adapter_revalidates_exact3_after_child(tmp_path, monkeypatch):
    root = tmp_path / "external-skill"
    skill_paths = _write_test_skill_candidate(
        root,
        {"script": b"script", "config": b"config", "schema": b"schema"},
        monkeypatch,
    )
    script = skill_paths[0]

    class _Completed:
        returncode = 0

    def _drifting_run(command, **_kwargs):
        output = Path(command[command.index("--output") + 1])
        output.write_text("{}", encoding="utf-8")
        script.write_bytes(b"persistent-drift")
        return _Completed()

    monkeypatch.setattr(subprocess, "run", _drifting_run)

    with pytest.raises(AssertionError, match="CONTENT_DRIFT"):
        _run_adapter(
            tmp_path,
            script,
            "connector-status",
            skill_paths=skill_paths,
        )


def test_unchanged_skill_isolated_connector_publish_receipt_and_profile_e2e(tmp_path):
    skill_paths, external_candidate = _skill_paths_for_e2e()
    skill_script, skill_config, _skill_schema = skill_paths
    if not external_candidate and not skill_script.is_file():
        pytest.skip("installed SKILL unavailable")
    before_digest = _skill_digest(skill_paths)
    default_config = json.loads(skill_config.read_text(encoding="utf-8"))
    assert default_config["enabled"] is False

    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="bridge-fixture-001")
    config = {
        "schema_version": "1.0.0",
        "message_type": "BvpMontageLearningConnectorConfig",
        "enabled": True,
        "contract_profile": "bvp-task029-file-bridge-v1",
        "bridge_root": str(layout.root),
        "learning_publish_enabled": True,
        "preference_read_enabled": True,
        "require_admission_receipt": True,
        "legacy_behavior_when_unavailable": True,
    }
    config_path = tmp_path / "isolated-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    learning_path = tmp_path / "learning.json"
    learning_path.write_text(json.dumps(_learning()), encoding="utf-8")

    status = _run_adapter(
        tmp_path,
        skill_script,
        "connector-status",
        "--config",
        str(config_path),
        skill_paths=skill_paths,
    )
    assert status["status"] == "READY"

    staged = _run_adapter(
        tmp_path,
        skill_script,
        "publish-learning",
        "--learning",
        str(learning_path),
        "--config",
        str(config_path),
        skill_paths=skill_paths,
    )
    assert staged["status"] == "STAGED_PENDING_REQUIRED_RECEIPT"
    assert staged["canonical_store_written"] is False

    delivery_path = Path(str(staged["delivery_path"]))
    canonical_store = _canonical_store(tmp_path)
    app = MontageLearningBridgeApplication(
        layout=layout, canonical_port=canonical_store
    )
    imported = app.import_path(
        delivery_path,
        generic_coordinates=GenericObservationCoordinates(expected_revision=0),
    )
    assert imported.status == "ACCEPTED"
    ledger = json.loads(
        canonical_store.generic_observation_path.read_text(encoding="utf-8")
    )
    assert ledger["entries"][0]["record_id"] == _learning()["record_id"]
    assert ledger["entries"][0]["source_digest_sha256"] == staged[
        "learning_sha256"
    ].removeprefix("sha256:")
    assert ledger["learning_adopted"] is False

    matched = _run_adapter(
        tmp_path,
        skill_script,
        "publish-learning",
        "--learning",
        str(learning_path),
        "--config",
        str(config_path),
        skill_paths=skill_paths,
    )
    assert matched["status"] == "BVP_REPORTED_ACCEPTED"
    assert matched["canonical_store_written"] is True

    published = publish_prebuilt_advisory_profile(
        layout,
        _profile(),
        source_binding=ProfileSourceBinding.bound_isolated_fixture(),
    )
    assert published.status == "PUBLISHED"
    loaded = _run_adapter(
        tmp_path,
        skill_script,
        "load-profile",
        "--config",
        str(config_path),
        skill_paths=skill_paths,
    )
    assert loaded["status"] == "PASS"
    assert loaded["advisory_only"] is True
    assert loaded["canonical_timeline"] is False
    assert loaded["auto_apply_authorized"] is False

    if external_candidate:
        post_paths, post_external = _skill_paths_for_e2e()
        assert post_external is True
        assert tuple(path.resolve() for path in post_paths) == tuple(
            path.resolve() for path in skill_paths
        )
    else:
        post_paths = skill_paths
    assert _skill_digest(post_paths) == before_digest
    assert json.loads(skill_config.read_text(encoding="utf-8"))["enabled"] is False
