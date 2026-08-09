"""AI video production Consumer Project package.

TASK-001 provides product-domain foundations. TASK-002 establishes measured
DaVinci Resolve/IPC capability boundaries. TASK-003 adds secure Asset Registry/Ingest. TASK-004 adds exact media
timebase normalization and bounded local ComfyUI/Audacity OpenVINO runtime
adapters without embedding BAI Development OS or GPL plugin code.
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

from .audacity_openvino import AudioAiOperation, AudioAiRequest, AudioAiResult, AudacityOpenVinoService, SeparationMode
from .character_identity import CharacterIdentityProfile, CharacterIdentityService, CharacterReferenceBundle
from .comfyui import (
    ComfyEndpointPolicy, ComfyResourcePolicy, ComfyUIClient, ImageGenerationMode, LocalImageGenerationRequest,
    LocalImageGenerationResult, LocalImageGenerationService, LocalImageModelProfile, LocalVideoGenerationRequest,
    LocalVideoGenerationResult, LocalVideoGenerationService, RuntimeLicenseState, VideoGenerationMode,
    VisualModelFamily, authorize_image_runtime_license, builtin_image_model_profile,
)
from .derived_assets import DerivedAssetPublisher, DerivedAssetSpec
from .normalization import MediaNormalizationService, NormalizationProfile, NormalizationRequest, NormalizationResult
from .timebase import FFprobeTimingProbe, FrameRate, FrameRounding, TimingInspection, TimingKind
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, generate_id, validate_id, validate_project_id, validate_schema_id
from .h3_acceleration import H3AccelerationContract, H3AccelerationMode, SPECTRUM_CLASS_TYPE
from .h3_foley import H3FoleyDurationTier, H3FoleyMode, H3FoleyRequest, H3FoleyResult, H3FoleyService
from .h3_production_brief import (
    H3AudioRetention, H3BriefTemplate, H3DurationTier, H3ProductionBriefBuilder, H3ProductionBriefPlan,
    H3ReferenceBinding, H3ReferenceKind, H3ReferenceRole, H3Shot, H3VisibleRetention,
)
from .h3_single_frame import H3SingleFrameContract, H3SingleFrameMode
from .h3_single_frame_service import H3SingleFrameRequest, H3SingleFrameResult, H3SingleFrameService
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

__version__ = "0.4.4"

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
    "AudioAiOperation", "AudioAiRequest", "AudioAiResult", "AudacityOpenVinoService", "SeparationMode",
    "CharacterIdentityProfile", "CharacterIdentityService", "CharacterReferenceBundle",
    "ComfyEndpointPolicy", "ComfyResourcePolicy", "ComfyUIClient", "ImageGenerationMode",
    "LocalImageGenerationRequest", "LocalImageGenerationResult", "LocalImageGenerationService",
    "LocalImageModelProfile", "RuntimeLicenseState", "VisualModelFamily", "authorize_image_runtime_license",
    "builtin_image_model_profile", "LocalVideoGenerationRequest", "LocalVideoGenerationResult",
    "LocalVideoGenerationService", "VideoGenerationMode",
    "DerivedAssetPublisher", "DerivedAssetSpec", "MediaNormalizationService", "NormalizationProfile",
    "NormalizationRequest", "NormalizationResult", "FFprobeTimingProbe", "FrameRate", "FrameRounding",
    "TimingInspection", "TimingKind",
    "H3AccelerationContract", "H3AccelerationMode", "SPECTRUM_CLASS_TYPE",
    "H3FoleyDurationTier", "H3FoleyMode", "H3FoleyRequest", "H3FoleyResult", "H3FoleyService",
    "H3AudioRetention", "H3BriefTemplate", "H3DurationTier", "H3ProductionBriefBuilder",
    "H3ProductionBriefPlan", "H3ReferenceBinding", "H3ReferenceKind", "H3ReferenceRole",
    "H3Shot", "H3VisibleRetention", "H3SingleFrameContract", "H3SingleFrameMode",
    "H3SingleFrameRequest", "H3SingleFrameResult", "H3SingleFrameService",
]
