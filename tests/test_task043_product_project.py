from __future__ import annotations

from importlib import resources
import json
from pathlib import Path

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.product_project import (
    ProductProjectManifest,
    ProjectChildBinding,
    ProjectTimebase,
    parse_product_project_manifest,
    validate_project_relative_path,
)
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_migration import (
    CompatibilityState,
    MigrationRegistry,
    MigrationTransition,
    ProjectCompatibilityInspector,
    ProjectMigrationPlanner,
    SupportedFormatRange,
)
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
CREATED = "2026-08-15T00:00:00.000Z"
UPDATED = "2026-08-15T00:01:00.000Z"


def binding(
    *,
    owner: str = "TASK-037",
    path: str = "state/production-control.json",
    format_id: str = "bai.production-control",
    version: str = "1.0.0",
    checksum: str = SHA_A,
    required: bool = True,
) -> ProjectChildBinding:
    return ProjectChildBinding(owner, path, format_id, version, checksum, required)


def manifest(*bindings: ProjectChildBinding, revision: int = 1, updated_at: str = CREATED) -> ProductProjectManifest:
    return ProductProjectManifest.create(
        project_id="project-1",
        project_revision=revision,
        product_version="0.20.1",
        timebase=ProjectTimebase(30000, 1001),
        child_bindings=bindings,
        created_at=CREATED,
        updated_at=updated_at,
    )


def test_manifest_is_deterministic_sorted_and_closed() -> None:
    source = manifest(
        binding(owner="TASK-041", path="state/audio.json", format_id="bai.audio-workspace", checksum=SHA_B),
        binding(),
    )
    assert [item.domain_owner for item in source.child_bindings] == ["TASK-037", "TASK-041"]
    assert source == parse_product_project_manifest(source.to_dict())
    assert source.project_manifest_sha256 == manifest(*reversed(source.child_bindings)).project_manifest_sha256
    assert source.to_dict()["authority"] == {
        "provider_execution_authorized": False,
        "paid_execution_authorized": False,
        "native_execution_authorized": False,
        "external_mutation_authorized": False,
    }


def test_manifest_schema_is_valid_and_packaged_copy_is_exact() -> None:
    public = Path(__file__).parents[1] / "schemas/product-project-manifest.schema.json"
    packaged = resources.files("ai_video_production").joinpath("schema_resources", public.name)
    assert public.read_bytes() == packaged.read_bytes()
    validate_instance(manifest(binding()).to_dict(), public)


@pytest.mark.parametrize(
    "value",
    ["../outside.json", "/absolute.json", "C:/secret.json", "state\\secret.json", "state/../secret.json", "./state.json", ".bai-project/project.json"],
)
def test_relative_path_rejects_escape_and_noncanonical_forms(value: str) -> None:
    with pytest.raises(ValueError):
        validate_project_relative_path(value)


def test_manifest_rejects_case_colliding_child_paths() -> None:
    with pytest.raises(ValueError):
        manifest(
            binding(owner="TASK-037", path="state/Control.json"),
            binding(owner="TASK-041", path="state/control.json", format_id="bai.audio-workspace", checksum=SHA_B),
        )


def test_manifest_checksum_tampering_is_detected() -> None:
    document = manifest(binding()).to_dict()
    document["project_revision"] = 2
    with pytest.raises(ProductError) as exc:
        parse_product_project_manifest(document)
    assert exc.value.code == "ERR_PROJECT_FORMAT_INVALID"


def test_manifest_authority_escalation_is_rejected() -> None:
    document = manifest(binding()).to_dict()
    document["authority"]["native_execution_authorized"] = True
    body = {key: value for key, value in document.items() if key != "project_manifest_sha256"}
    document["project_manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ProductError) as exc:
        parse_product_project_manifest(document)
    assert exc.value.code == "ERR_PROJECT_FORMAT_AUTHORITY"


def test_newer_project_manifest_version_has_specific_fail_closed_error() -> None:
    document = manifest(binding()).to_dict()
    document["project_format_version"] = "2.0.0"
    with pytest.raises(ProductError) as exc:
        parse_product_project_manifest(document)
    assert exc.value.code == "ERR_PROJECT_FORMAT_NEWER_UNSUPPORTED"


def test_store_roundtrip_and_exact_revision_cas(tmp_path: Path) -> None:
    first = manifest(binding())
    ProductProjectManifestStore.save(tmp_path, first)
    assert ProductProjectManifestStore.load(tmp_path) == first
    second = manifest(binding(checksum=SHA_B), revision=2, updated_at=UPDATED)
    ProductProjectManifestStore.save(
        tmp_path,
        second,
        expected_previous_manifest_sha256=first.project_manifest_sha256,
    )
    assert ProductProjectManifestStore.load(tmp_path) == second


def test_store_rejects_replace_without_cas(tmp_path: Path) -> None:
    first = manifest(binding())
    ProductProjectManifestStore.save(tmp_path, first)
    with pytest.raises(ProductError) as exc:
        ProductProjectManifestStore.save(tmp_path, manifest(binding(), revision=2, updated_at=UPDATED))
    assert exc.value.code == "ERR_PROJECT_SAVE_CAS_REQUIRED"


def test_store_rejects_revision_skip(tmp_path: Path) -> None:
    first = manifest(binding())
    ProductProjectManifestStore.save(tmp_path, first)
    with pytest.raises(ProductError) as exc:
        ProductProjectManifestStore.save(
            tmp_path,
            manifest(binding(), revision=3, updated_at=UPDATED),
            expected_previous_manifest_sha256=first.project_manifest_sha256,
        )
    assert exc.value.code == "ERR_PROJECT_SAVE_REVISION_INVALID"


def test_store_rejects_symlink_control_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    control = tmp_path / ".bai-project"
    try:
        control.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink unavailable")
    with pytest.raises(ProductError) as exc:
        ProductProjectManifestStore.save(tmp_path, manifest(binding()))
    assert exc.value.code == "ERR_PROJECT_FORMAT_CONTROL_DIR_INVALID"


def test_compatibility_inspector_verifies_exact_child_bytes(tmp_path: Path) -> None:
    child = tmp_path / "state/production-control.json"
    child.parent.mkdir()
    child.write_bytes(b'{"snapshot_version":"1.0.0"}\n')
    source = manifest(binding(checksum=sha256_bytes(child.read_bytes())))
    inspector = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "1.0.0", "1.9.9", "1.0.0"),
    ))
    report = inspector.inspect(source, project_root=tmp_path)
    assert report.can_open_read_only is True
    assert report.bindings[0].state is CompatibilityState.READABLE
    assert report.bindings[0].actual_content_sha256 == source.child_bindings[0].content_sha256


def test_compatibility_inspector_detects_checksum_drift(tmp_path: Path) -> None:
    child = tmp_path / "state/production-control.json"
    child.parent.mkdir()
    child.write_text("changed", encoding="utf-8")
    source = manifest(binding(checksum=SHA_A))
    report = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "1.0.0", "1.9.9", "1.0.0"),
    )).inspect(source, project_root=tmp_path)
    assert report.can_open_read_only is False
    assert report.bindings[0].state is CompatibilityState.CHECKSUM_MISMATCH


def test_optional_missing_child_does_not_block_read_only_open(tmp_path: Path) -> None:
    source = manifest(binding(required=False))
    report = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "1.0.0", "1.9.9", "1.0.0"),
    )).inspect(source, project_root=tmp_path)
    assert report.can_open_read_only is True
    assert report.bindings[0].state is CompatibilityState.OPTIONAL_MISSING


def test_newer_required_child_fails_closed_without_touching_disk() -> None:
    source = manifest(binding(version="3.0.0"))
    report = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "1.0.0", "2.0.0", "2.0.0"),
    )).inspect(source)
    assert report.can_open_read_only is False
    assert report.bindings[0].state is CompatibilityState.UNSUPPORTED_NEWER


def test_read_only_migration_plan_finds_lossless_chain() -> None:
    source = manifest(binding(version="1.0.0"))
    inspector = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "2.0.0", "2.0.0", "2.0.0"),
    ))
    report = inspector.inspect(source)
    registry = MigrationRegistry((
        MigrationTransition("bai.production-control", "1.0.0", "1.5.0", True, False),
        MigrationTransition("bai.production-control", "1.5.0", "2.0.0", True, False),
    ))
    plan = ProjectMigrationPlanner(registry).plan(source, report)
    assert plan.state == "READY_FOR_COPY_ON_WRITE_APPLY"
    assert len(plan.binding_plans[0].transitions) == 2
    assert plan.to_dict()["authority"]["migration_apply_authorized"] is False


def test_lossy_migration_plan_is_human_gated() -> None:
    source = manifest(binding(version="1.0.0"))
    report = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "2.0.0", "2.0.0", "2.0.0"),
    )).inspect(source)
    registry = MigrationRegistry((
        MigrationTransition("bai.production-control", "1.0.0", "2.0.0", False, True),
    ))
    plan = ProjectMigrationPlanner(registry).plan(source, report)
    assert plan.state == "READY_FOR_HUMAN_GATE"


def test_missing_migration_path_is_blocked() -> None:
    source = manifest(binding(version="1.0.0"))
    report = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "2.0.0", "2.0.0", "2.0.0"),
    )).inspect(source)
    plan = ProjectMigrationPlanner(MigrationRegistry()).plan(source, report)
    assert plan.state == "BLOCKED"
    assert plan.blockers == ("NO_MIGRATION_PATH:TASK-037:state/production-control.json",)


def test_planner_rejects_stale_compatibility_report() -> None:
    first = manifest(binding())
    second = manifest(binding(checksum=SHA_B))
    report = ProjectCompatibilityInspector((
        SupportedFormatRange("bai.production-control", "1.0.0", "1.9.9", "1.0.0"),
    )).inspect(first)
    with pytest.raises(ValueError, match="stale"):
        ProjectMigrationPlanner(MigrationRegistry()).plan(second, report)
