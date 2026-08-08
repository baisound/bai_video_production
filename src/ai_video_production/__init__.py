"""AI video production Consumer Project package.

TASK-001 provides product-domain foundations. TASK-002 establishes measured
DaVinci Resolve/IPC capability boundaries. TASK-003 adds secure Asset Registry,
Ingest and Logical URI path-resolution services without embedding BAI
Development OS runtime code into the product.
"""

from .assets import (
    ApprovedSegment,
    AssetRecord,
    AssetType,
    AudioRightsStatus,
    PermissionState,
    RetentionClass,
    RightsStatus,
)
from .checkpoint import CheckpointRecord, ResumeContext, assert_resume_compatible
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id, validate_project_id, validate_schema_id
from .ingest import AssetIngestRequest, AssetIngestResult, AssetIngestService
from .manifest import ManifestEnvelope, Producer
from .media_probe import FFprobeMediaProbe, MediaProbeResult
from .ownership import ActorKind, TimelineOwner, TimelineRef, TimelineWriteGuard
from .paths import LogicalPathResolver, PathMapping, SourcePathPolicy
from .profile import PluginDescriptor, ProfileSnapshot, merge_allowed_overrides
from .resolve_capabilities import CapabilityStatus, ProbeMode, ResolveCapabilityProbe, authorize_mutation_probe
from .resolve_loader import ResolveModuleLoader
from .state import JobStateService, ProductionJobState
from .store import ManifestRecord, SQLiteProductStore

__version__ = "0.3.0"

__all__ = [
    "ActorKind", "ApprovedSegment", "AssetIngestRequest", "AssetIngestResult", "AssetIngestService",
    "AssetRecord", "AssetType", "AudioRightsStatus", "CapabilityStatus", "CheckpointRecord",
    "FFprobeMediaProbe", "IdKind", "JobStateService", "LogicalPathResolver", "ManifestEnvelope",
    "ManifestRecord", "MediaProbeResult", "PathMapping", "PermissionState", "PluginDescriptor",
    "ProbeMode", "Producer", "ProductError", "ProductErrorCategory", "ProductionJobState",
    "ProfileSnapshot", "ResumeContext", "RetentionClass", "ResolveCapabilityProbe", "ResolveModuleLoader",
    "RightsStatus", "SQLiteProductStore", "SourcePathPolicy", "TimelineOwner", "TimelineRef",
    "TimelineWriteGuard", "assert_resume_compatible", "authorize_mutation_probe", "generate_id",
    "merge_allowed_overrides", "validate_id", "validate_project_id", "validate_schema_id",
]
