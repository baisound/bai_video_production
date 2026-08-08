"""AI video production Consumer Project package.

TASK-001 provides product-domain foundations. TASK-002 adds isolated DaVinci
Resolve capability-spike tooling without embedding BAI Development OS runtime
code or bypassing external-side-effect safety gates.
"""

from .assets import AssetRecord, AssetType, RetentionClass, RightsStatus
from .checkpoint import CheckpointRecord, ResumeContext, assert_resume_compatible
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id, validate_project_id, validate_schema_id
from .manifest import ManifestEnvelope, Producer
from .ownership import ActorKind, TimelineOwner, TimelineRef, TimelineWriteGuard
from .paths import LogicalPathResolver, PathMapping
from .profile import PluginDescriptor, ProfileSnapshot, merge_allowed_overrides
from .resolve_capabilities import CapabilityStatus, ProbeMode, ResolveCapabilityProbe, authorize_mutation_probe
from .resolve_loader import ResolveModuleLoader
from .state import JobStateService, ProductionJobState
from .store import SQLiteProductStore

__all__ = [
    "ActorKind", "AssetRecord", "AssetType", "CheckpointRecord", "IdKind",
    "JobStateService", "LogicalPathResolver", "ManifestEnvelope", "PathMapping",
    "CapabilityStatus", "PluginDescriptor", "ProbeMode", "Producer", "ProductError", "ProductErrorCategory",
    "ProductionJobState", "ProfileSnapshot", "ResumeContext", "RetentionClass",
    "ResolveCapabilityProbe", "ResolveModuleLoader", "RightsStatus", "SQLiteProductStore", "TimelineOwner", "TimelineRef",
    "TimelineWriteGuard", "assert_resume_compatible", "generate_id",
    "authorize_mutation_probe", "merge_allowed_overrides", "validate_id", "validate_project_id",
    "validate_schema_id",
]
