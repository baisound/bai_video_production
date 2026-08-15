"""TASK-043 compatibility inspection and read-only migration planning."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Callable, Iterable, Mapping

from .errors import ProductError, ProductErrorCategory
from .product_project import ProductProjectManifest, ProjectChildBinding, sha256_file_exact
from .schema_contracts import SemVer
from .serialization import canonical_json_bytes, sha256_bytes


_MAX_MIGRATION_BYTES = 128 * 1024 * 1024
_TRANSFORMER_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9][a-z0-9._-]*)+$")


class CompatibilityState(str, Enum):
    READABLE = "READABLE"
    OPTIONAL_MISSING = "OPTIONAL_MISSING"
    REQUIRED_MISSING = "REQUIRED_MISSING"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    SECURITY_REJECTED = "SECURITY_REJECTED"
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    UNSUPPORTED_NEWER = "UNSUPPORTED_NEWER"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"


@dataclass(frozen=True, slots=True)
class SupportedFormatRange:
    format_id: str
    minimum_version: str
    maximum_version: str
    preferred_version: str

    def __post_init__(self) -> None:
        minimum = SemVer.parse(self.minimum_version)
        maximum = SemVer.parse(self.maximum_version)
        preferred = SemVer.parse(self.preferred_version)
        if minimum > maximum or not minimum <= preferred <= maximum:
            raise ValueError("supported format range is inconsistent")

    def classify(self, version: str) -> CompatibilityState:
        current = SemVer.parse(version)
        if current > SemVer.parse(self.maximum_version):
            return CompatibilityState.UNSUPPORTED_NEWER
        if current < SemVer.parse(self.minimum_version):
            return CompatibilityState.MIGRATION_REQUIRED
        return CompatibilityState.READABLE


@dataclass(frozen=True, slots=True)
class BindingCompatibility:
    domain_owner: str
    relative_path: str
    format_id: str
    source_version: str
    target_version: str | None
    state: CompatibilityState
    required: bool
    actual_content_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "domain_owner": self.domain_owner,
            "relative_path": self.relative_path,
            "format_id": self.format_id,
            "source_version": self.source_version,
            "target_version": self.target_version,
            "state": self.state.value,
            "required": self.required,
            "actual_content_sha256": self.actual_content_sha256,
        }


@dataclass(frozen=True, slots=True)
class ProjectCompatibilityReport:
    project_id: str
    project_revision: int
    manifest_sha256: str
    bindings: tuple[BindingCompatibility, ...]
    report_sha256: str

    def __post_init__(self) -> None:
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if expected != self.report_sha256:
            raise ValueError("report_sha256 does not match the compatibility report")

    @property
    def can_open_read_only(self) -> bool:
        blocking = {
            CompatibilityState.REQUIRED_MISSING,
            CompatibilityState.CHECKSUM_MISMATCH,
            CompatibilityState.SECURITY_REJECTED,
            CompatibilityState.MIGRATION_REQUIRED,
            CompatibilityState.UNSUPPORTED_NEWER,
            CompatibilityState.UNSUPPORTED_FORMAT,
        }
        return not any(item.required and item.state in blocking for item in self.bindings)

    @property
    def migration_required(self) -> bool:
        return any(item.state is CompatibilityState.MIGRATION_REQUIRED for item in self.bindings)

    def _body(self) -> dict[str, object]:
        return {
            "compatibility_report_version": "1.0.0",
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "manifest_sha256": self.manifest_sha256,
            "can_open_read_only": self.can_open_read_only,
            "migration_required": self.migration_required,
            "bindings": [item.to_dict() for item in self.bindings],
            "authority": {"store_write_authorized": False, "migration_apply_authorized": False},
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "report_sha256": self.report_sha256}


class ProjectCompatibilityInspector:
    def __init__(self, supported_formats: Iterable[SupportedFormatRange]) -> None:
        values = tuple(supported_formats)
        self._supported = {item.format_id: item for item in values}
        if len(self._supported) != len(values):
            raise ValueError("supported format IDs must be unique")

    def inspect(self, manifest: ProductProjectManifest, *, project_root: str | Path | None = None) -> ProjectCompatibilityReport:
        root = None if project_root is None else self._safe_root(project_root)
        rows = tuple(self._inspect_binding(binding, root) for binding in manifest.child_bindings)
        body = {
            "compatibility_report_version": "1.0.0",
            "project_id": manifest.project_id,
            "project_revision": manifest.project_revision,
            "manifest_sha256": manifest.project_manifest_sha256,
            "can_open_read_only": self._can_open(rows),
            "migration_required": any(item.state is CompatibilityState.MIGRATION_REQUIRED for item in rows),
            "bindings": [item.to_dict() for item in rows],
            "authority": {"store_write_authorized": False, "migration_apply_authorized": False},
        }
        return ProjectCompatibilityReport(
            project_id=manifest.project_id,
            project_revision=manifest.project_revision,
            manifest_sha256=manifest.project_manifest_sha256,
            bindings=rows,
            report_sha256=sha256_bytes(canonical_json_bytes(body)),
        )

    @staticmethod
    def _safe_root(value: str | Path) -> Path:
        root = Path(value)
        if root.is_symlink() or not root.is_dir():
            raise ValueError("project_root must be an existing regular directory")
        return root.resolve(strict=True)

    @staticmethod
    def _can_open(rows: tuple[BindingCompatibility, ...]) -> bool:
        blocking = {
            CompatibilityState.REQUIRED_MISSING,
            CompatibilityState.CHECKSUM_MISMATCH,
            CompatibilityState.SECURITY_REJECTED,
            CompatibilityState.MIGRATION_REQUIRED,
            CompatibilityState.UNSUPPORTED_NEWER,
            CompatibilityState.UNSUPPORTED_FORMAT,
        }
        return not any(item.required and item.state in blocking for item in rows)

    def _inspect_binding(self, binding: ProjectChildBinding, root: Path | None) -> BindingCompatibility:
        supported = self._supported.get(binding.format_id)
        state = CompatibilityState.UNSUPPORTED_FORMAT if supported is None else supported.classify(binding.format_version)
        target_version = None if supported is None else supported.preferred_version
        actual = None
        if root is not None:
            target = root.joinpath(*binding.relative_path.split("/"))
            try:
                resolved = target.resolve(strict=True)
            except FileNotFoundError:
                state = CompatibilityState.REQUIRED_MISSING if binding.required else CompatibilityState.OPTIONAL_MISSING
            except OSError:
                state = CompatibilityState.SECURITY_REJECTED
            else:
                if target.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(root):
                    state = CompatibilityState.SECURITY_REJECTED
                else:
                    try:
                        actual = sha256_file_exact(resolved)
                    except OSError:
                        state = CompatibilityState.SECURITY_REJECTED
                    else:
                        if actual != binding.content_sha256:
                            state = CompatibilityState.CHECKSUM_MISMATCH
        return BindingCompatibility(
            domain_owner=binding.domain_owner,
            relative_path=binding.relative_path,
            format_id=binding.format_id,
            source_version=binding.format_version,
            target_version=target_version,
            state=state,
            required=binding.required,
            actual_content_sha256=actual,
        )


@dataclass(frozen=True, slots=True)
class MigrationTransition:
    format_id: str
    from_version: str
    to_version: str
    lossless: bool
    requires_human_gate: bool

    def __post_init__(self) -> None:
        source = SemVer.parse(self.from_version)
        target = SemVer.parse(self.to_version)
        if source >= target:
            raise ValueError("migration transition must advance the version")
        if not isinstance(self.lossless, bool) or not isinstance(self.requires_human_gate, bool):
            raise ValueError("migration transition flags must be boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "format_id": self.format_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "lossless": self.lossless,
            "requires_human_gate": self.requires_human_gate,
        }


class MigrationRegistry:
    def __init__(self, transitions: Iterable[MigrationTransition] = ()) -> None:
        self._transitions: dict[tuple[str, str], list[MigrationTransition]] = {}
        seen: set[tuple[str, str, str]] = set()
        for item in transitions:
            identity = (item.format_id, item.from_version, item.to_version)
            if identity in seen:
                raise ValueError("duplicate migration transition")
            seen.add(identity)
            self._transitions.setdefault((item.format_id, item.from_version), []).append(item)

    def path(self, format_id: str, from_version: str, to_version: str) -> tuple[MigrationTransition, ...] | None:
        if from_version == to_version:
            return ()
        queue: deque[tuple[str, tuple[MigrationTransition, ...]]] = deque([(from_version, ())])
        visited = {from_version}
        while queue:
            current, path = queue.popleft()
            for step in sorted(self._transitions.get((format_id, current), ()), key=lambda item: SemVer.parse(item.to_version)):
                if step.to_version == to_version:
                    return (*path, step)
                if step.to_version not in visited and len(path) < 31:
                    visited.add(step.to_version)
                    queue.append((step.to_version, (*path, step)))
        return None


@dataclass(frozen=True, slots=True)
class BindingMigrationPlan:
    domain_owner: str
    relative_path: str
    source_sha256: str
    transitions: tuple[MigrationTransition, ...]

    @property
    def requires_human_gate(self) -> bool:
        return any(not item.lossless or item.requires_human_gate for item in self.transitions)

    def to_dict(self) -> dict[str, object]:
        return {
            "domain_owner": self.domain_owner,
            "relative_path": self.relative_path,
            "source_sha256": self.source_sha256,
            "transitions": [item.to_dict() for item in self.transitions],
            "requires_human_gate": self.requires_human_gate,
        }


@dataclass(frozen=True, slots=True)
class ProjectMigrationPlan:
    project_id: str
    source_manifest_sha256: str
    binding_plans: tuple[BindingMigrationPlan, ...]
    blockers: tuple[str, ...]
    plan_sha256: str

    def __post_init__(self) -> None:
        expected = sha256_bytes(canonical_json_bytes(self._body()))
        if expected != self.plan_sha256:
            raise ValueError("plan_sha256 does not match the migration plan")

    @property
    def state(self) -> str:
        if self.blockers:
            return "BLOCKED"
        if any(item.requires_human_gate for item in self.binding_plans):
            return "READY_FOR_HUMAN_GATE"
        if self.binding_plans:
            return "READY_FOR_COPY_ON_WRITE_APPLY"
        return "NO_MIGRATION_REQUIRED"

    def _body(self) -> dict[str, object]:
        return {
            "migration_plan_version": "1.0.0",
            "project_id": self.project_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "state": self.state,
            "binding_plans": [item.to_dict() for item in self.binding_plans],
            "blockers": list(self.blockers),
            "authority": {"store_write_authorized": False, "migration_apply_authorized": False},
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "plan_sha256": self.plan_sha256}


class ProjectMigrationPlanner:
    def __init__(self, registry: MigrationRegistry) -> None:
        self.registry = registry

    def plan(self, manifest: ProductProjectManifest, report: ProjectCompatibilityReport) -> ProjectMigrationPlan:
        if report.manifest_sha256 != manifest.project_manifest_sha256:
            raise ValueError("compatibility report is stale for this manifest")
        by_identity: Mapping[tuple[str, str], ProjectChildBinding] = {item.identity: item for item in manifest.child_bindings}
        plans: list[BindingMigrationPlan] = []
        blockers: list[str] = []
        for item in report.bindings:
            binding = by_identity[(item.domain_owner, item.relative_path)]
            if item.state is CompatibilityState.MIGRATION_REQUIRED and item.target_version is not None:
                path = self.registry.path(item.format_id, item.source_version, item.target_version)
                if path is None:
                    blockers.append(f"NO_MIGRATION_PATH:{item.domain_owner}:{item.relative_path}")
                else:
                    plans.append(BindingMigrationPlan(item.domain_owner, item.relative_path, binding.content_sha256, path))
            elif item.required and item.state not in {CompatibilityState.READABLE, CompatibilityState.OPTIONAL_MISSING}:
                blockers.append(f"{item.state.value}:{item.domain_owner}:{item.relative_path}")
        plans.sort(key=lambda item: (item.domain_owner, item.relative_path))
        blockers.sort()
        body = {
            "migration_plan_version": "1.0.0",
            "project_id": manifest.project_id,
            "source_manifest_sha256": manifest.project_manifest_sha256,
            "state": _plan_state(plans, blockers),
            "binding_plans": [item.to_dict() for item in plans],
            "blockers": blockers,
            "authority": {"store_write_authorized": False, "migration_apply_authorized": False},
        }
        return ProjectMigrationPlan(
            project_id=manifest.project_id,
            source_manifest_sha256=manifest.project_manifest_sha256,
            binding_plans=tuple(plans),
            blockers=tuple(blockers),
            plan_sha256=sha256_bytes(canonical_json_bytes(body)),
        )


def _plan_state(plans: list[BindingMigrationPlan], blockers: list[str]) -> str:
    if blockers:
        return "BLOCKED"
    if any(item.requires_human_gate for item in plans):
        return "READY_FOR_HUMAN_GATE"
    if plans:
        return "READY_FOR_COPY_ON_WRITE_APPLY"
    return "NO_MIGRATION_REQUIRED"


@dataclass(frozen=True, slots=True)
class MigrationTransformResult:
    content: bytes
    target_version: str
    transformer_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MigrationTransformer:
    """Code-registered exact lossless child transformation.

    Transformers are constructed by Product code/tests, never deserialized from
    a Project or accepted through a UI/CLI boundary.
    """

    transition: MigrationTransition
    transformer_id: str
    transform: Callable[[bytes], bytes]
    validate_target: Callable[[bytes], None]

    def __post_init__(self) -> None:
        if not _TRANSFORMER_ID_RE.fullmatch(self.transformer_id):
            raise ValueError("transformer_id must be a stable dotted identity")
        if not self.transition.lossless or self.transition.requires_human_gate:
            raise ValueError("automatic migration transformers must be exact lossless transitions")
        if not callable(self.transform) or not callable(self.validate_target):
            raise ValueError("migration transformer functions must be callable")


class MigrationTransformerRegistry:
    def __init__(self, transformers: Iterable[MigrationTransformer] = ()) -> None:
        self._transformers: dict[tuple[str, str, str], MigrationTransformer] = {}
        ids: set[str] = set()
        for transformer in transformers:
            key = (
                transformer.transition.format_id,
                transformer.transition.from_version,
                transformer.transition.to_version,
            )
            if key in self._transformers or transformer.transformer_id in ids:
                raise ValueError("duplicate migration transformer transition or identity")
            self._transformers[key] = transformer
            ids.add(transformer.transformer_id)

    def assert_plan_supported(self, plan: ProjectMigrationPlan) -> None:
        if plan.state != "READY_FOR_COPY_ON_WRITE_APPLY":
            raise ProductError(
                "ERR_PROJECT_MIGRATION_APPLY_NOT_READY",
                "Migration plan is not eligible for lossless automatic apply",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                details={"plan_state": plan.state},
            )
        for binding_plan in plan.binding_plans:
            for transition in binding_plan.transitions:
                key = (transition.format_id, transition.from_version, transition.to_version)
                if key not in self._transformers:
                    raise ProductError(
                        "ERR_PROJECT_MIGRATION_TRANSFORMER_MISSING",
                        "Exact migration transformer is not registered",
                        ProductErrorCategory.NOT_SUPPORTED,
                        details={
                            "format_id": transition.format_id,
                            "from_version": transition.from_version,
                            "to_version": transition.to_version,
                        },
                    )

    def apply_binding(self, plan: BindingMigrationPlan, source: bytes) -> MigrationTransformResult:
        if not isinstance(source, bytes) or not 0 < len(source) <= _MAX_MIGRATION_BYTES:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_SOURCE_SIZE",
                "Migration source bytes are empty or exceed the bounded maximum",
                ProductErrorCategory.RESOURCE_EXHAUSTED,
            )
        if sha256_bytes(source) != plan.source_sha256:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_SOURCE_STALE",
                "Migration source bytes no longer match the exact plan",
                ProductErrorCategory.STATE,
            )
        current = source
        transformer_ids: list[str] = []
        target_version: str | None = None
        for transition in plan.transitions:
            key = (transition.format_id, transition.from_version, transition.to_version)
            transformer = self._transformers.get(key)
            if transformer is None:
                raise ProductError(
                    "ERR_PROJECT_MIGRATION_TRANSFORMER_MISSING",
                    "Exact migration transformer is not registered",
                    ProductErrorCategory.NOT_SUPPORTED,
                    details={"format_id": transition.format_id},
                )
            try:
                output = transformer.transform(current)
            except ProductError:
                raise
            except Exception as exc:
                raise ProductError(
                    "ERR_PROJECT_MIGRATION_TRANSFORM_FAILED",
                    "Registered migration transformer failed",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"transformer_id": transformer.transformer_id},
                ) from exc
            if not isinstance(output, bytes) or not 0 < len(output) <= _MAX_MIGRATION_BYTES:
                raise ProductError(
                    "ERR_PROJECT_MIGRATION_TARGET_SIZE",
                    "Migration target bytes are empty or exceed the bounded maximum",
                    ProductErrorCategory.RESOURCE_EXHAUSTED,
                    details={"transformer_id": transformer.transformer_id},
                )
            try:
                transformer.validate_target(output)
            except ProductError:
                raise
            except Exception as exc:
                raise ProductError(
                    "ERR_PROJECT_MIGRATION_TARGET_INVALID",
                    "Migration target bytes failed exact target validation",
                    ProductErrorCategory.DATA_INTEGRITY,
                    details={"transformer_id": transformer.transformer_id},
                ) from exc
            current = output
            target_version = transition.to_version
            transformer_ids.append(transformer.transformer_id)
        if target_version is None:
            raise ProductError(
                "ERR_PROJECT_MIGRATION_TRANSITIONS_EMPTY",
                "Migration binding plan has no transitions",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return MigrationTransformResult(current, target_version, tuple(transformer_ids))
