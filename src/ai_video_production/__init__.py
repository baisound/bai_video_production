"""AI video production foundation contracts.

TASK-001 deliberately contains only product-domain foundations. It does not
embed or depend on BAI Development OS runtime code.
"""

from .assets import AssetRecord, AssetType, RetentionClass, RightsStatus
from .checkpoint import CheckpointRecord, ResumeContext, assert_resume_compatible
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id, validate_project_id, validate_schema_id
from .manifest import ManifestEnvelope, Producer
from .ownership import ActorKind, TimelineOwner, TimelineRef, TimelineWriteGuard
from .paths import LogicalPathResolver, PathMapping
from .profile import PluginDescriptor, ProfileSnapshot, merge_allowed_overrides
from .state import JobStateService, ProductionJobState
from .store import SQLiteProductStore

__all__ = [
    "ActorKind", "AssetRecord", "AssetType", "CheckpointRecord", "IdKind",
    "JobStateService", "LogicalPathResolver", "ManifestEnvelope", "PathMapping",
    "PluginDescriptor", "Producer", "ProductError", "ProductErrorCategory",
    "ProductionJobState", "ProfileSnapshot", "ResumeContext", "RetentionClass",
    "RightsStatus", "SQLiteProductStore", "TimelineOwner", "TimelineRef",
    "TimelineWriteGuard", "assert_resume_compatible", "generate_id",
    "merge_allowed_overrides", "validate_id", "validate_project_id",
    "validate_schema_id",
]
