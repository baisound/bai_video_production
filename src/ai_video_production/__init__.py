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
from .ai_connections import (
    AiConnectionProfile, AiConnectionResolver, AiWorkload, ConnectionAvailability,
    CostClass, ModelRoute, ProviderFamily, ReasoningEffort, SelectionMode,
)
from .connection_settings import (
    AiConnectionSettingsService, SettingsPreflightReport, SettingsRouteStatus,
    WorkloadSettingsStatus,
)
from .connection_settings_store import (
    ConnectionCatalogEditor, ConnectionSettingsEditor, ConnectionSettingsFormBuilder, ConnectionSettingsLoadResult,
    ConnectionSettingsRecord, ConnectionSettingsSaveResult, ConnectionSettingsStore,
)
from .credential_vault import CredentialVault, WindowsCredentialManagerStore
from .provider_execution import (
    AiProviderExecutionService, AnthropicMessagesAdapter, EnvironmentCredentialStore,
    GoogleInteractionsAdapter, OpenAiResponsesAdapter, RouteDiagnostic,
    RouteDiagnosticStatus, TextGenerationRequest, TextGenerationResult, UrllibJsonTransport,
)
from .external_media_providers import (
    BinaryResponse, ElevenLabsMediaAdapter, ElevenLabsMusicRequest,
    ElevenLabsSoundEffectRequest, ElevenLabsTtsRequest, ExternalMediaJob,
    ProviderCatalogEntry, ProviderIntegrationStatus, SunoApiMusicAdapter,
    SunoMusicRequest, UrllibBinaryTransport, builtin_media_provider_catalog,
)
from .capability_execution import (
    CapabilityExecutionRegistry, CapabilityExecutionRequest, CapabilityExecutionResult,
    ModelCapabilityCatalog, ModelCapabilityDescriptor, TextCapabilityAdapter,
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
from .local_comfy_generation_port import (
    LocalComfyGenerationConfig, LocalComfyTextToVideoPort,
    MINIMAX_H3_NATIVE_WORKFLOW_SHA256, default_minimax_h3_workflow_path,
)
from .normalization import MediaNormalizationService, NormalizationProfile, NormalizationRequest, NormalizationResult
from .timebase import FFprobeTimingProbe, FrameRate, FrameRounding, TimingInspection, TimingKind
from .timeline_mapping import AffineTimeMap, EditSegment, TimelineMappingPlan, TimelineMappingService, TimelinePlacement
from .subtitles import (
    AsrProvider, AsrRequest, SrtRenderer, SubtitleCue, SubtitlePlan,
    SubtitlePlanningService, TranscriptManifest, TranscriptSegment,
)
from .faster_whisper_asr import (
    FasterWhisperConfig, FasterWhisperProvider, LocalTranscriptionService,
    TranscriptionPublication,
)
from .large_media_transcription import (
    ChunkedTranscriptionConfig, FfmpegAudioChunkExtractor, ResumableTranscriptionService,
    TranscriptionCheckpoint, TranscriptionChunk, build_chunk_plan,
)
from .subtitle_workspace import (
    NarrationCue, SrtWorkspaceCodec, SubtitleOrigin, SubtitleReviewState,
    SubtitleWorkspace, SubtitleWorkspaceStore, WorkspaceCue,
)
from .resolve_subtitle_handoff import (
    ResolveSubtitleHandoffService, ResolveSubtitlePlacement, ResolveSubtitlePlacementPlan,
)
from .cut_candidates import (
    CutCandidate, CutCandidateAnalyzer, CutCandidateConfig, CutCandidateKind,
    CutCandidateManifest, CutCandidatePublication, CutCandidatePublicationService,
    FfmpegSilenceDetector, KeepBlock, SilenceRange, load_transcript_manifest,
)
from .production_blueprint import (
    AssetSourceStrategy, BlueprintReference, BlueprintScene, CameraMotion,
    GenerationRisk, ProductionBlueprint, ReferenceKind, ReferenceStatus,
    SceneAudioPlan,
)
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
from .edit_plan import (
    CandidateGraphEdge, CandidateGraphNode, CandidateReviewDecision, EditDecision,
    EditPlan, EditPlanService, PlannedRange,
)
from .resolve_assembly import (
    AudioPlacement, ResolveAssemblyPlan, ResolveAssemblyResult, ResolveAssemblyService,
    ResolveAssetBindings, ResolveScriptingAssemblyAdapter,
)
from .render_qa import (
    FfmpegLoudnessAnalyzer, LoudnessMeasurement, LoudnessProfile, RenderQAReport, RenderQAService,
)
from .manual_handoff import EditorHandoffManifest, EditorHandoffService, HandoffFile
from .technical_mvp import TechnicalMvpApplicationService
from .product_project import (
    ProductProjectManifest, ProjectChildBinding, ProjectTimebase,
    parse_product_project_manifest, sha256_file_exact, validate_project_relative_path,
)
from .product_project_store import ProductProjectManifestStore
from .project_save import (
    ProductProjectSaveCoordinator, ProjectSaveState,
)
from .project_history import (
    ProductProjectAutosaveCoordinator, ProductProjectBackupStore,
    ProjectAutosavePolicy, ProjectAutosaveResult, ProjectBackupPreview,
    ProjectCommandAction, ProjectCommandHistory, ProjectCommandHistoryStore,
    ProjectCommandRecord, parse_project_command_history,
)
from .durable_product_job import (
    DurableProductJob, DurableProductJobCollection, DurableProductJobService,
    DurableProductJobState, DurableProductJobStore, durable_job_shell_projection,
    parse_durable_product_job, parse_durable_product_job_collection,
)
from .project_migration import (
    BindingCompatibility, BindingMigrationPlan, CompatibilityState,
    MigrationRegistry, MigrationTransition, ProjectCompatibilityInspector,
    ProjectCompatibilityReport, ProjectMigrationPlan, ProjectMigrationPlanner,
    SupportedFormatRange,
)
from .timeline_audio import (
    AudioCue as TimelineAudioCue, AudioFitPolicy, AudioRange, AudioSourceBinding,
    AudioSourceIntent, ImportedSrtCue, MusicPlan, NarrationCue as TimelineNarrationCue,
    NarrationCueOrigin, SrtProposal, SrtProposalService, SrtProposalState,
    TimelineAudioPlan, TimelineAudioRole, TimelinePlacementBinding,
)
from .timeline_audio_store import TimelineAudioHistory, TimelineAudioSnapshotStore
from .timeline_audio_application import Task042TimelineAudioApplication
from .interactive_timeline import (
    InteractiveTimeline, InteractiveTimelineClip, TimelineFitMode,
    TimelineFocusKind, TimelineInteractionReducer, TimelineInteractionState,
    TimelineMediaKind, TimelineTrack, TimelineTrackRole, TimelineViewport,
    TimelineWindowProjection, TimelineWindowProjector,
)
from .interactive_timeline_projection import InteractiveTimelineProjectionService
from .interactive_timeline_edit import (
    SnapAnchor, SnapDecision, SnapKind, TimelineEditCommand, TimelineEditHistory,
    TimelineEditKind, TimelineEditProjector, TimelineEditRevision, TimelineSnapService,
)
from .interactive_timeline_store import TimelineEditSnapshotStore, parse_timeline_edit_history
from .interactive_timeline_application import Task044TimelineEditApplication
from .export_queue import ExportAuthorityClass, ExportDispatchResult, ExportOutputContract, ExportPreparation, ExportPreset
from .export_queue_application import ExportQueueApplication

__version__ = "0.20.1"

__all__ = [
    "AiConnectionProfile", "AiConnectionResolver", "AiWorkload", "ConnectionAvailability", "CostClass",
    "ModelRoute", "ProviderFamily", "ReasoningEffort", "SelectionMode",
    "AiConnectionSettingsService", "SettingsPreflightReport", "SettingsRouteStatus",
    "WorkloadSettingsStatus",
    "ConnectionCatalogEditor", "ConnectionSettingsEditor", "ConnectionSettingsFormBuilder", "ConnectionSettingsLoadResult",
    "ConnectionSettingsRecord", "ConnectionSettingsSaveResult", "ConnectionSettingsStore",
    "CredentialVault", "WindowsCredentialManagerStore",
    "AiProviderExecutionService", "AnthropicMessagesAdapter", "EnvironmentCredentialStore",
    "GoogleInteractionsAdapter", "OpenAiResponsesAdapter", "RouteDiagnostic", "RouteDiagnosticStatus",
    "TextGenerationRequest", "TextGenerationResult", "UrllibJsonTransport",
    "BinaryResponse", "ElevenLabsMediaAdapter", "ElevenLabsMusicRequest",
    "ElevenLabsSoundEffectRequest", "ElevenLabsTtsRequest", "ExternalMediaJob",
    "ProviderCatalogEntry", "ProviderIntegrationStatus", "SunoApiMusicAdapter",
    "SunoMusicRequest", "UrllibBinaryTransport", "builtin_media_provider_catalog",
    "CapabilityExecutionRegistry", "CapabilityExecutionRequest", "CapabilityExecutionResult",
    "ModelCapabilityCatalog", "ModelCapabilityDescriptor", "TextCapabilityAdapter",
    "ActorKind", "ApprovedSegment", "AssetIngestRequest", "AssetIngestResult", "AssetIngestService",
    "AssetRecord", "AssetType", "AudioRightsStatus", "CapabilityStatus", "CheckpointRecord",
    "FFprobeMediaProbe", "IdKind", "JobStateService", "LogicalPathResolver", "ManifestEnvelope",
    "ManifestRecord", "MediaProbeResult", "PathMapping", "PermissionState", "PluginDescriptor",
    "ProbeMode", "Producer", "ProductError", "ProductErrorCategory", "ProductionJobState",
    "ProfileSnapshot", "ResumeContext", "RetentionClass", "ResolveCapabilityProbe", "ResolveModuleLoader",
    "RightsStatus", "SQLiteProductStore", "SourcePathPolicy", "TimelineOwner", "TimelineRef",
    "TimelineWriteGuard", "assert_resume_compatible", "authorize_mutation_probe", "generate_id",
    "AsrProvider", "AsrRequest", "SrtRenderer", "SubtitleCue", "SubtitlePlan",
    "SubtitlePlanningService", "TranscriptManifest", "TranscriptSegment",
    "FasterWhisperConfig", "FasterWhisperProvider", "LocalTranscriptionService",
    "TranscriptionPublication",
    "ChunkedTranscriptionConfig", "FfmpegAudioChunkExtractor", "ResumableTranscriptionService",
    "TranscriptionCheckpoint", "TranscriptionChunk", "build_chunk_plan",
    "NarrationCue", "SrtWorkspaceCodec", "SubtitleOrigin", "SubtitleReviewState",
    "SubtitleWorkspace", "SubtitleWorkspaceStore", "WorkspaceCue",
    "ResolveSubtitleHandoffService", "ResolveSubtitlePlacement", "ResolveSubtitlePlacementPlan",
    "CutCandidate", "CutCandidateAnalyzer", "CutCandidateConfig", "CutCandidateKind",
    "CutCandidateManifest", "CutCandidatePublication", "CutCandidatePublicationService",
    "FfmpegSilenceDetector", "KeepBlock", "SilenceRange", "load_transcript_manifest",
    "AssetSourceStrategy", "BlueprintReference", "BlueprintScene", "CameraMotion",
    "GenerationRisk", "ProductionBlueprint", "ReferenceKind", "ReferenceStatus",
    "SceneAudioPlan",
    "merge_allowed_overrides", "validate_id", "validate_project_id", "validate_schema_id",
    "AudioAiOperation", "AudioAiRequest", "AudioAiResult", "AudacityOpenVinoService", "SeparationMode",
    "CharacterIdentityProfile", "CharacterIdentityService", "CharacterReferenceBundle",
    "ComfyEndpointPolicy", "ComfyResourcePolicy", "ComfyUIClient", "ImageGenerationMode",
    "LocalImageGenerationRequest", "LocalImageGenerationResult", "LocalImageGenerationService",
    "LocalImageModelProfile", "RuntimeLicenseState", "VisualModelFamily", "authorize_image_runtime_license",
    "builtin_image_model_profile", "LocalVideoGenerationRequest", "LocalVideoGenerationResult",
    "LocalVideoGenerationService", "VideoGenerationMode",
    "LocalComfyGenerationConfig", "LocalComfyTextToVideoPort",
    "MINIMAX_H3_NATIVE_WORKFLOW_SHA256", "default_minimax_h3_workflow_path",
    "DerivedAssetPublisher", "DerivedAssetSpec", "MediaNormalizationService", "NormalizationProfile",
    "NormalizationRequest", "NormalizationResult", "FFprobeTimingProbe", "FrameRate", "FrameRounding",
    "AffineTimeMap", "EditSegment", "TimelineMappingPlan", "TimelineMappingService", "TimelinePlacement",
    "TimingInspection", "TimingKind",
    "H3AccelerationContract", "H3AccelerationMode", "SPECTRUM_CLASS_TYPE",
    "H3FoleyDurationTier", "H3FoleyMode", "H3FoleyRequest", "H3FoleyResult", "H3FoleyService",
    "H3AudioRetention", "H3BriefTemplate", "H3DurationTier", "H3ProductionBriefBuilder",
    "H3ProductionBriefPlan", "H3ReferenceBinding", "H3ReferenceKind", "H3ReferenceRole",
    "H3Shot", "H3VisibleRetention", "H3SingleFrameContract", "H3SingleFrameMode",
    "H3SingleFrameRequest", "H3SingleFrameResult", "H3SingleFrameService",
    "CandidateGraphEdge", "CandidateGraphNode", "CandidateReviewDecision", "EditDecision",
    "EditPlan", "EditPlanService", "PlannedRange",
    "AudioPlacement", "ResolveAssemblyPlan", "ResolveAssemblyResult", "ResolveAssemblyService",
    "ResolveAssetBindings", "ResolveScriptingAssemblyAdapter",
    "FfmpegLoudnessAnalyzer", "LoudnessMeasurement", "LoudnessProfile", "RenderQAReport",
    "RenderQAService", "EditorHandoffManifest", "EditorHandoffService", "HandoffFile",
    "TechnicalMvpApplicationService",
    "ProductProjectManifest", "ProjectChildBinding", "ProjectTimebase",
    "parse_product_project_manifest", "sha256_file_exact", "validate_project_relative_path",
    "ProductProjectManifestStore", "BindingCompatibility", "BindingMigrationPlan",
    "CompatibilityState", "MigrationRegistry", "MigrationTransition",
    "ProjectCompatibilityInspector", "ProjectCompatibilityReport",
    "ProjectMigrationPlan", "ProjectMigrationPlanner", "SupportedFormatRange",
    "ProductProjectSaveCoordinator", "ProjectSaveState",
    "ProductProjectAutosaveCoordinator", "ProductProjectBackupStore",
    "ProjectAutosavePolicy", "ProjectAutosaveResult", "ProjectBackupPreview",
    "ProjectCommandAction", "ProjectCommandHistory", "ProjectCommandHistoryStore",
    "ProjectCommandRecord", "parse_project_command_history",
    "DurableProductJob", "DurableProductJobCollection", "DurableProductJobService",
    "DurableProductJobState", "DurableProductJobStore", "durable_job_shell_projection",
    "parse_durable_product_job", "parse_durable_product_job_collection",
    "TimelineAudioCue", "AudioFitPolicy", "AudioRange", "AudioSourceBinding",
    "AudioSourceIntent", "ImportedSrtCue", "MusicPlan", "TimelineNarrationCue",
    "NarrationCueOrigin", "SrtProposal", "SrtProposalService", "SrtProposalState",
    "TimelineAudioPlan", "TimelineAudioRole", "TimelinePlacementBinding",
    "TimelineAudioHistory", "TimelineAudioSnapshotStore", "Task042TimelineAudioApplication",
    "InteractiveTimeline", "InteractiveTimelineClip", "TimelineFitMode",
    "TimelineFocusKind", "TimelineInteractionReducer", "TimelineInteractionState",
    "TimelineMediaKind", "TimelineTrack", "TimelineTrackRole", "TimelineViewport",
    "TimelineWindowProjection", "TimelineWindowProjector",
    "SnapAnchor", "SnapDecision", "SnapKind", "TimelineEditCommand", "TimelineEditHistory",
    "TimelineEditKind", "TimelineEditProjector", "TimelineEditRevision", "TimelineSnapService",
    "TimelineEditSnapshotStore", "parse_timeline_edit_history", "Task044TimelineEditApplication",
    "InteractiveTimelineProjectionService",
    "ExportAuthorityClass", "ExportDispatchResult", "ExportOutputContract", "ExportPreparation", "ExportPreset",
    "ExportQueueApplication",
]
