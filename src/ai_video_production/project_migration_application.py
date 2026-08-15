"""TASK-045 explicit legacy import and lossless copy-on-write migration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Callable, Iterable

from .errors import ProductError, ProductErrorCategory
from .ids import validate_project_id
from .product_project import (
    ProductProjectManifest,
    ProjectChildBinding,
    ProjectTimebase,
    sha256_file_exact,
)
from .product_project_store import ProductProjectManifestStore
from .project_history import ProductProjectBackupStore
from .project_migration import (
    MigrationRegistry,
    MigrationTransformerRegistry,
    ProjectCompatibilityInspector,
    ProjectMigrationPlan,
    ProjectMigrationPlanner,
    SupportedFormatRange,
)
from .project_save import ProductProjectSaveCoordinator
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso


_MAX_LEGACY_CHILD_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class LegacyProjectBindingRule:
    domain_owner: str
    relative_path: str
    format_id: str
    format_version: str
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.required, bool):
            raise ValueError("legacy binding required flag must be boolean")
        # Reuse the canonical binding validation rather than maintain a second
        # path/owner/format validator.
        ProjectChildBinding(
            domain_owner=self.domain_owner,
            relative_path=self.relative_path,
            format_id=self.format_id,
            format_version=self.format_version,
            content_sha256=sha256_bytes(b"legacy-rule-validation"),
            required=self.required,
        )


@dataclass(frozen=True, slots=True)
class LegacyProjectCandidate:
    project_id: str
    product_version: str
    timebase: ProjectTimebase
    created_at: str
    child_bindings: tuple[ProjectChildBinding, ...]
    preview_sha256: str

    def __post_init__(self) -> None:
        validate_project_id(self.project_id)
        SemVer.parse(self.product_version)
        if not self.child_bindings:
            raise ValueError("legacy Project candidate must contain at least one known child")
        if tuple(sorted(self.child_bindings, key=lambda item: item.identity)) != self.child_bindings:
            raise ValueError("legacy Project child bindings must be sorted")
        if sha256_bytes(canonical_json_bytes(self._body())) != self.preview_sha256:
            raise ValueError("preview_sha256 does not match the legacy Project candidate")

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        product_version: str,
        timebase: ProjectTimebase,
        child_bindings: Iterable[ProjectChildBinding],
        created_at: str | None = None,
    ) -> "LegacyProjectCandidate":
        bindings = tuple(sorted(child_bindings, key=lambda item: item.identity))
        timestamp = created_at or utc_now_iso()
        body = _legacy_candidate_body(
            project_id=project_id,
            product_version=product_version,
            timebase=timebase,
            created_at=timestamp,
            child_bindings=bindings,
        )
        return cls(
            project_id=project_id,
            product_version=product_version,
            timebase=timebase,
            created_at=timestamp,
            child_bindings=bindings,
            preview_sha256=sha256_bytes(canonical_json_bytes(body)),
        )

    def _body(self) -> dict[str, object]:
        return _legacy_candidate_body(
            project_id=self.project_id,
            product_version=self.product_version,
            timebase=self.timebase,
            created_at=self.created_at,
            child_bindings=self.child_bindings,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "preview_sha256": self.preview_sha256}

    def to_manifest(self) -> ProductProjectManifest:
        return ProductProjectManifest.create(
            project_id=self.project_id,
            project_revision=1,
            product_version=self.product_version,
            timebase=self.timebase,
            child_bindings=self.child_bindings,
            created_at=self.created_at,
            updated_at=self.created_at,
        )


def _legacy_candidate_body(
    *,
    project_id: str,
    product_version: str,
    timebase: ProjectTimebase,
    created_at: str,
    child_bindings: tuple[ProjectChildBinding, ...],
) -> dict[str, object]:
    return {
        "legacy_project_preview_version": "1.0.0",
        "project_id": project_id,
        "product_version": product_version,
        "timebase": timebase.to_dict(),
        "created_at": created_at,
        "child_bindings": [item.to_dict() for item in child_bindings],
        "authority": {
            "store_write_authorized": False,
            "migration_apply_authorized": False,
            "external_execution_authorized": False,
        },
    }


class LegacyProjectDiscovery:
    @staticmethod
    def discover(
        project_root: str | Path,
        *,
        project_id: str,
        product_version: str,
        timebase: ProjectTimebase,
        rules: Iterable[LegacyProjectBindingRule],
        created_at: str | None = None,
    ) -> LegacyProjectCandidate:
        root = _safe_project_root(project_root)
        manifest_path = ProductProjectManifestStore.path(root)
        if manifest_path.exists():
            raise ProductError(
                "ERR_PROJECT_LEGACY_MANIFEST_EXISTS",
                "Project already has a Product Project manifest",
                ProductErrorCategory.STATE,
            )
        rule_values = tuple(sorted(rules, key=lambda item: (item.domain_owner, item.relative_path)))
        identities = [(item.domain_owner, item.relative_path) for item in rule_values]
        case_paths = [item.relative_path.casefold() for item in rule_values]
        if not rule_values or len(identities) != len(set(identities)) or len(case_paths) != len(set(case_paths)):
            raise ProductError(
                "ERR_PROJECT_LEGACY_RULES_INVALID",
                "Legacy Project discovery rules are empty, duplicate or case-colliding",
                ProductErrorCategory.VALIDATION,
            )
        bindings: list[ProjectChildBinding] = []
        for rule in rule_values:
            target = root.joinpath(*rule.relative_path.split("/"))
            if not target.exists():
                if rule.required:
                    raise ProductError(
                        "ERR_PROJECT_LEGACY_REQUIRED_CHILD_MISSING",
                        "Required legacy Project child is missing",
                        ProductErrorCategory.DATA_INTEGRITY,
                        details={"relative_path": rule.relative_path},
                    )
                continue
            try:
                resolved = target.resolve(strict=True)
            except OSError as exc:
                raise ProductError(
                    "ERR_PROJECT_LEGACY_CHILD_INVALID",
                    "Legacy Project child could not be resolved safely",
                    ProductErrorCategory.SECURITY,
                    details={"relative_path": rule.relative_path},
                ) from exc
            if target.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(root):
                raise ProductError(
                    "ERR_PROJECT_LEGACY_CHILD_INVALID",
                    "Legacy Project child must be a contained regular non-symlink file",
                    ProductErrorCategory.SECURITY,
                    details={"relative_path": rule.relative_path},
                )
            size = resolved.stat().st_size
            if size <= 0 or size > _MAX_LEGACY_CHILD_BYTES:
                raise ProductError(
                    "ERR_PROJECT_LEGACY_CHILD_SIZE",
                    "Legacy Project child is empty or exceeds the bounded maximum",
                    ProductErrorCategory.RESOURCE_EXHAUSTED,
                    details={"relative_path": rule.relative_path, "size_bytes": size},
                )
            bindings.append(
                ProjectChildBinding(
                    domain_owner=rule.domain_owner,
                    relative_path=rule.relative_path,
                    format_id=rule.format_id,
                    format_version=rule.format_version,
                    content_sha256=sha256_file_exact(resolved),
                    required=rule.required,
                )
            )
        if not bindings:
            raise ProductError(
                "ERR_PROJECT_LEGACY_NO_KNOWN_CHILDREN",
                "Legacy Project has no known canonical child files",
                ProductErrorCategory.VALIDATION,
            )
        return LegacyProjectCandidate.create(
            project_id=project_id,
            product_version=product_version,
            timebase=timebase,
            child_bindings=bindings,
            created_at=created_at,
        )


@dataclass(frozen=True, slots=True)
class _PendingLegacyImport:
    candidate: LegacyProjectCandidate
    rules: tuple[LegacyProjectBindingRule, ...]


@dataclass(frozen=True, slots=True)
class _PendingMigration:
    source_manifest_sha256: str
    plan: ProjectMigrationPlan
    target_content_sha256: tuple[tuple[str, str], ...]


class ProductProjectMigrationApplication:
    """Typed Product-local migration composition with one-shot confirmations."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        supported_formats: Iterable[SupportedFormatRange],
        migration_registry: MigrationRegistry | None = None,
        transformer_registry: MigrationTransformerRegistry | None = None,
        save_coordinator: ProductProjectSaveCoordinator | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self.project_root = _safe_project_root(project_root)
        self.inspector = ProjectCompatibilityInspector(supported_formats)
        self.planner = ProjectMigrationPlanner(migration_registry or MigrationRegistry())
        self.transformers = transformer_registry or MigrationTransformerRegistry()
        self.save_coordinator = save_coordinator or ProductProjectSaveCoordinator()
        self.token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self._legacy_pending: dict[str, _PendingLegacyImport] = {}
        self._migration_pending: dict[str, _PendingMigration] = {}
        self._completed: dict[str, dict[str, object]] = {}

    def prepare_legacy_import(
        self,
        *,
        project_id: str,
        product_version: str,
        timebase: ProjectTimebase,
        rules: Iterable[LegacyProjectBindingRule],
    ) -> dict[str, object]:
        rule_values = tuple(rules)
        candidate = LegacyProjectDiscovery.discover(
            self.project_root,
            project_id=project_id,
            product_version=product_version,
            timebase=timebase,
            rules=rule_values,
        )
        manifest = candidate.to_manifest()
        report = self.inspector.inspect(manifest, project_root=self.project_root)
        if not report.can_open_read_only:
            raise ProductError(
                "ERR_PROJECT_LEGACY_COMPATIBILITY_BLOCKED",
                "Legacy Project candidate is not readable by the registered formats",
                ProductErrorCategory.NOT_SUPPORTED,
                details={"compatibility_report_sha256": report.report_sha256},
            )
        token = self._new_token()
        self._legacy_pending[token] = _PendingLegacyImport(candidate, rule_values)
        return {
            "confirmation_id": token,
            "candidate": candidate.to_dict(),
            "compatibility_report_sha256": report.report_sha256,
            "human_final_authority_required": True,
            "store_write_performed": False,
            "external_execution_started": False,
        }

    def apply_legacy_import(self, *, confirmation_id: str) -> dict[str, object]:
        if confirmation_id in self._completed:
            return dict(self._completed[confirmation_id])
        pending = self._legacy_pending.pop(confirmation_id, None)
        if pending is None:
            raise ProductError(
                "ERR_PROJECT_LEGACY_CONFIRMATION_INVALID",
                "Legacy Project import confirmation is missing or already consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        refreshed = LegacyProjectDiscovery.discover(
            self.project_root,
            project_id=pending.candidate.project_id,
            product_version=pending.candidate.product_version,
            timebase=pending.candidate.timebase,
            rules=pending.rules,
            created_at=pending.candidate.created_at,
        )
        if refreshed.preview_sha256 != pending.candidate.preview_sha256:
            raise ProductError(
                "ERR_PROJECT_LEGACY_PREVIEW_STALE",
                "Legacy Project files changed after import preparation",
                ProductErrorCategory.STATE,
            )
        manifest = refreshed.to_manifest()
        report = self.inspector.inspect(manifest, project_root=self.project_root)
        if not report.can_open_read_only:
            raise ProductError(
                "ERR_PROJECT_LEGACY_COMPATIBILITY_BLOCKED",
                "Legacy Project candidate is no longer readable",
                ProductErrorCategory.NOT_SUPPORTED,
            )
        ProductProjectManifestStore.save(self.project_root, manifest)
        reopened = ProductProjectManifestStore.load(self.project_root)
        reopened_report = self.inspector.inspect(reopened, project_root=self.project_root)
        if reopened.project_manifest_sha256 != manifest.project_manifest_sha256 or not reopened_report.can_open_read_only:
            raise ProductError(
                "ERR_PROJECT_LEGACY_REOPEN_FAILED",
                "Imported Product Project did not reopen with the exact accepted identity",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        result: dict[str, object] = {
            "operation": "LEGACY_PROJECT_IMPORT",
            "project_id": reopened.project_id,
            "project_revision": reopened.project_revision,
            "project_manifest_sha256": reopened.project_manifest_sha256,
            "legacy_preview_sha256": refreshed.preview_sha256,
            "child_count": len(reopened.child_bindings),
            "store_write_performed": True,
            "external_execution_started": False,
            "paid_execution_authorized": False,
        }
        self._completed[confirmation_id] = result
        return dict(result)

    def inspect_and_plan(self) -> tuple[ProductProjectManifest, ProjectMigrationPlan]:
        manifest = ProductProjectManifestStore.load(self.project_root)
        report = self.inspector.inspect(manifest, project_root=self.project_root)
        return manifest, self.planner.plan(manifest, report)

    def prepare_lossless_migration(self) -> dict[str, object]:
        manifest, plan = self.inspect_and_plan()
        self.transformers.assert_plan_supported(plan)
        targets: list[tuple[str, str]] = []
        for binding_plan in plan.binding_plans:
            source = self._read_exact_child(binding_plan.relative_path, binding_plan.source_sha256)
            transformed = self.transformers.apply_binding(binding_plan, source)
            targets.append((binding_plan.relative_path, sha256_bytes(transformed.content)))
        token = self._new_token()
        target_hashes = tuple(sorted(targets))
        self._migration_pending[token] = _PendingMigration(
            manifest.project_manifest_sha256,
            plan,
            target_hashes,
        )
        return {
            "confirmation_id": token,
            "project_id": manifest.project_id,
            "source_manifest_sha256": manifest.project_manifest_sha256,
            "migration_plan_sha256": plan.plan_sha256,
            "binding_count": len(plan.binding_plans),
            "target_content_sha256": dict(target_hashes),
            "human_final_authority_required": True,
            "store_write_performed": False,
            "external_execution_started": False,
        }

    def apply_lossless_migration(self, *, confirmation_id: str) -> dict[str, object]:
        if confirmation_id in self._completed:
            return dict(self._completed[confirmation_id])
        pending = self._migration_pending.pop(confirmation_id, None)
        if pending is None:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_CONFIRMATION_INVALID",
                "Migration confirmation is missing or already consumed",
                ProductErrorCategory.AUTHORIZATION,
            )
        current, plan = self.inspect_and_plan()
        if (
            current.project_manifest_sha256 != pending.source_manifest_sha256
            or plan.plan_sha256 != pending.plan.plan_sha256
        ):
            raise ProductError(
                "ERR_PROJECT_MIGRATION_PLAN_STALE",
                "Project or migration plan changed after preparation",
                ProductErrorCategory.STATE,
            )
        self.transformers.assert_plan_supported(plan)
        documents: dict[str, bytes] = {}
        final_versions: dict[str, str] = {}
        transformer_ids: dict[str, tuple[str, ...]] = {}
        target_hashes: dict[str, str] = {}
        for binding_plan in plan.binding_plans:
            source = self._read_exact_child(binding_plan.relative_path, binding_plan.source_sha256)
            transformed = self.transformers.apply_binding(binding_plan, source)
            documents[binding_plan.relative_path] = transformed.content
            final_versions[binding_plan.relative_path] = transformed.target_version
            transformer_ids[binding_plan.relative_path] = transformed.transformer_ids
            target_hashes[binding_plan.relative_path] = sha256_bytes(transformed.content)
        if tuple(sorted(target_hashes.items())) != pending.target_content_sha256:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_OUTPUT_NONDETERMINISTIC",
                "Migration output changed after preparation",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        replacements: dict[str, str] = {}
        referenced_hashes = {
            value
            for binding in current.child_bindings
            for value in binding.dependency_hashes
        }
        for source_hash in {
            binding.content_sha256
            for binding in current.child_bindings
            if binding.relative_path in target_hashes
        }:
            matching = tuple(
                binding for binding in current.child_bindings
                if binding.content_sha256 == source_hash
            )
            migrated = tuple(
                binding for binding in matching
                if binding.relative_path in target_hashes
            )
            outputs = {target_hashes[binding.relative_path] for binding in migrated}
            if source_hash in referenced_hashes and (
                len(migrated) != len(matching) or len(outputs) != 1
            ):
                raise ProductError(
                    "ERR_PROJECT_MIGRATION_DEPENDENCY_AMBIGUOUS",
                    "A dependency checksum cannot be mapped to one exact migrated child",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"source_sha256": source_hash},
                )
            if len(outputs) == 1:
                replacements[source_hash] = next(iter(outputs))
        target_bindings = []
        for binding in current.child_bindings:
            target_bindings.append(
                ProjectChildBinding(
                    domain_owner=binding.domain_owner,
                    relative_path=binding.relative_path,
                    format_id=binding.format_id,
                    format_version=final_versions.get(binding.relative_path, binding.format_version),
                    content_sha256=target_hashes.get(binding.relative_path, binding.content_sha256),
                    required=binding.required,
                    dependency_hashes=tuple(sorted({replacements.get(value, value) for value in binding.dependency_hashes})),
                )
            )
        target_manifest = ProductProjectManifest.create(
            project_id=current.project_id,
            project_revision=current.project_revision + 1,
            product_version=current.product_version,
            timebase=current.timebase,
            child_bindings=target_bindings,
            created_at=current.created_at,
            updated_at=max(current.updated_at, utc_now_iso()),
        )
        backup_id = ProductProjectBackupStore.create(self.project_root)
        saved = self.save_coordinator.save(
            self.project_root,
            target_manifest,
            documents,
            expected_previous_manifest_sha256=current.project_manifest_sha256,
        )
        reopened = ProductProjectManifestStore.load(self.project_root)
        reopened_report = self.inspector.inspect(reopened, project_root=self.project_root)
        if reopened.project_manifest_sha256 != saved.project_manifest_sha256 or not reopened_report.can_open_read_only:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_REOPEN_FAILED",
                "Migrated Product Project did not reopen with exact compatible identity",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"backup_id": backup_id},
            )
        result: dict[str, object] = {
            "operation": "LOSSLESS_COPY_ON_WRITE_MIGRATION",
            "project_id": reopened.project_id,
            "source_manifest_sha256": current.project_manifest_sha256,
            "target_manifest_sha256": reopened.project_manifest_sha256,
            "target_project_revision": reopened.project_revision,
            "migration_plan_sha256": plan.plan_sha256,
            "backup_id": backup_id,
            "target_content_sha256": dict(sorted(target_hashes.items())),
            "transformer_ids": {key: list(value) for key, value in sorted(transformer_ids.items())},
            "reopen_verified": True,
            "store_write_performed": True,
            "external_execution_started": False,
            "paid_execution_authorized": False,
        }
        self._completed[confirmation_id] = result
        return dict(result)

    def _read_exact_child(self, relative_path: str, expected_sha256: str) -> bytes:
        target = self.project_root.joinpath(*relative_path.split("/"))
        try:
            resolved = target.resolve(strict=True)
        except OSError as exc:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_SOURCE_MISSING",
                "Migration source child is unavailable",
                ProductErrorCategory.DATA_INTEGRITY,
                details={"relative_path": relative_path},
            ) from exc
        if target.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(self.project_root):
            raise ProductError(
                "ERR_PROJECT_MIGRATION_SOURCE_INVALID",
                "Migration source child is not a contained regular file",
                ProductErrorCategory.SECURITY,
                details={"relative_path": relative_path},
            )
        size = resolved.stat().st_size
        if size <= 0 or size > _MAX_LEGACY_CHILD_BYTES:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_SOURCE_SIZE",
                "Migration source child is empty or exceeds the bounded maximum",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
                details={"relative_path": relative_path, "size_bytes": size},
            )
        data = resolved.read_bytes()
        if sha256_bytes(data) != expected_sha256:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_SOURCE_STALE",
                "Migration source child changed after planning",
                ProductErrorCategory.STATE,
                details={"relative_path": relative_path},
            )
        return data

    def _new_token(self) -> str:
        token = self.token_factory()
        if (
            not isinstance(token, str)
            or not token.strip()
            or token in self._legacy_pending
            or token in self._migration_pending
            or token in self._completed
        ):
            raise ValueError("confirmation token must be unique non-empty text")
        return token


def _safe_project_root(value: str | Path) -> Path:
    root = Path(value)
    if root.is_symlink() or not root.is_dir():
        raise ProductError(
            "ERR_PROJECT_FORMAT_ROOT_INVALID",
            "Project root must be an existing regular directory",
            ProductErrorCategory.SECURITY,
        )
    return root.resolve(strict=True)
