"""Human-selected Product binding for the TASK-098 WAV review runtime.

The adapter reuses the canonical TASK-041 Candidate projection and Product
Asset registry.  Selection and all derived review records are process-local;
this module never decodes audio, renders a waveform, starts playback or writes
canonical state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import threading
from typing import Any, Callable, Protocol
import wave

from .assets import AssetRecord, AssetType, RightsStatus
from .audio_workspace_media_review import (
    AudioMediaReviewIntent,
    AudioMediaReviewPolicyRevision,
    AudioMediaSourceBinding,
    PlaybackWaveformCapabilityBinding,
)
from .errors import ProductError, ProductErrorCategory
from .ids import IdKind, validate_id, validate_project_id
from .paths import LogicalPathResolver
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .subtitle_workspace import SubtitleWorkspace
from .subtitles import TranscriptManifest
from .task098_review_media_runtime_windows import (
    MAX_AUDIO_CHANNELS,
    MAX_DECODED_RANGE_BYTES,
    MAX_SOURCE_WAV_BYTES,
)
from .task098_review_shell_application import Task098ReviewShellBinding
from .task098_review_workspace_coordinator import open_review_workspace


MAX_REVIEW_DURATION_SAMPLES = 30 * 48_000
MAX_OBSERVATION_AGE_SECONDS = 3_600
_ALLOWED_ASSET_TYPES = frozenset({AssetType.AUDIO, AssetType.BGM, AssetType.SFX})
_ALLOWED_RIGHTS = frozenset(
    {RightsStatus.OWNED, RightsStatus.LICENSED, RightsStatus.PERMISSION_GRANTED}
)
_CANDIDATE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}")
_POLICY_SHA256 = sha256_bytes(
    canonical_json_bytes(
        {
            "policy": "task098-a6-r2-local-product-review",
            "sample_rate_hz": 48_000,
            "max_review_duration_samples": MAX_REVIEW_DURATION_SAMPLES,
            "max_decoded_range_bytes": MAX_DECODED_RANGE_BYTES,
            "operations": ["AUDITION", "WAVEFORM_VIEW"],
            "persistence": False,
        }
    )
)
_CAPABILITY_SHA256 = sha256_bytes(
    canonical_json_bytes(
        {
            "profile": "task098-a6-r2-windows-wave",
            "decode": "PCM_WAV",
            "playback": "WINDOWS_MEMORY_WAVE",
            "waveform": "EPHEMERAL_BOUNDED",
        }
    )
)
_APP_IDENTITY_SHA256 = sha256_bytes(
    b"ai_video_production.task098_product_review_binding/1.0.0"
)


class AssetLookupPort(Protocol):
    def get_asset(self, asset_id: str) -> AssetRecord: ...


CandidateSnapshotProvider = Callable[[], dict[str, Any]]
Clock = Callable[[], str]


@dataclass(frozen=True, slots=True)
class _SelectedCandidate:
    candidate_id: str
    asset_id: str
    asset_sha256: str
    production_snapshot_sha256: str
    audio_snapshot_sha256: str
    selected_at: str
    channel_count: int
    sample_width: int
    duration_samples: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _closed_error(code: str, message: str, category: ProductErrorCategory) -> ProductError:
    return ProductError(code, message, category)


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


class Task098ProductReviewBindingSelector:
    """Process-local Human selection over canonical Candidate/Asset truth."""

    def __init__(
        self,
        *,
        assets: AssetLookupPort,
        resolver: LogicalPathResolver,
        candidate_snapshot_provider: CandidateSnapshotProvider,
        project_id: str,
        production_job_id: str,
        clock: Clock = _utc_now,
    ) -> None:
        if not hasattr(assets, "get_asset"):
            raise ValueError("Asset lookup is invalid")
        if type(resolver) is not LogicalPathResolver:
            raise ValueError("Asset resolver is invalid")
        if not callable(candidate_snapshot_provider) or not callable(clock):
            raise ValueError("review selection provider dependencies are invalid")
        validate_project_id(project_id)
        validate_id(production_job_id, IdKind.JOB)
        self._assets = assets
        self._resolver = resolver
        self._candidate_snapshot_provider = candidate_snapshot_provider
        self._project_id = project_id
        self._production_job_id = production_job_id
        self._clock = clock
        self._lock = threading.Lock()
        self._selection: _SelectedCandidate | None = None
        self._closed = False

    def close(self) -> None:
        with self._lock:
            self._selection = None
            self._closed = True

    def _ensure_open(self) -> None:
        with self._lock:
            if self._closed:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_SELECTION_CLOSED",
                    "Universal WAV Review selection is closed",
                    ProductErrorCategory.STATE,
                )

    def _candidate(self, candidate_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            if (
                not isinstance(candidate_id, str)
                or _CANDIDATE_ID.fullmatch(candidate_id) is None
            ):
                raise ValueError("Candidate identity is invalid")
            snapshot = self._candidate_snapshot_provider()
            if (
                not isinstance(snapshot, dict)
                or snapshot.get("project_id") != self._project_id
            ):
                raise ValueError("Candidate snapshot scope is invalid")
            production_sha = snapshot["production_snapshot_sha256"]
            audio_sha = snapshot["audio_snapshot_sha256"]
            validate_sha256(production_sha, field_name="production_snapshot_sha256")
            validate_sha256(audio_sha, field_name="audio_snapshot_sha256")
            candidates = snapshot.get("available_audio_candidates")
            if not isinstance(candidates, list):
                raise ValueError("Candidate snapshot rows are invalid")
            matches = [row for row in candidates if isinstance(row, dict) and row.get("candidate_id") == candidate_id]
            if len(matches) != 1:
                raise ValueError("Candidate is not currently reviewable")
            row = matches[0]
            validate_id(row.get("asset_id"), IdKind.ASSET)
            validate_sha256(row.get("asset_sha256"), field_name="asset_sha256")
            if row.get("lifecycle_state") not in {"ACCEPTED", "LOCKED"}:
                raise ValueError("Candidate lifecycle is not reviewable")
            return snapshot, row
        except (KeyError, ProductError, TypeError, ValueError):
            raise _closed_error(
                "ERR_TASK098_REVIEW_CANDIDATE_NOT_CURRENT",
                "Universal WAV Review Candidate is not current",
                ProductErrorCategory.AUTHORIZATION,
            ) from None

    def _asset(self, row: dict[str, Any]) -> AssetRecord:
        try:
            asset = self._assets.get_asset(row["asset_id"])
        except ProductError:
            raise _closed_error(
                "ERR_TASK098_REVIEW_ASSET_NOT_CURRENT",
                "Universal WAV Review Asset is not current",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from None
        if (
            type(asset) is not AssetRecord
            or asset.production_job_id != self._production_job_id
            or asset.asset_id != row["asset_id"]
            or asset.checksum != row["asset_sha256"]
            or asset.asset_type not in _ALLOWED_ASSET_TYPES
            or asset.rights_status not in _ALLOWED_RIGHTS
        ):
            raise _closed_error(
                "ERR_TASK098_REVIEW_ASSET_NOT_CURRENT",
                "Universal WAV Review Asset is not current",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        return asset

    def _inspect_wav_header(self, asset: AssetRecord) -> tuple[int, int, int]:
        """Read bounded container facts only; never decode samples or hash the body."""

        try:
            self._resolver.assert_job_scope(asset.logical_uri, asset.production_job_id)
            resolved = self._resolver.resolve_existing_regular_file(asset.logical_uri)
            if not isinstance(resolved, Path) or resolved.is_symlink():
                raise ValueError("Asset path is invalid")
            before = resolved.stat(follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size <= 0
                or before.st_size > MAX_SOURCE_WAV_BYTES
            ):
                raise ValueError("Asset file is invalid")
            with resolved.open("rb") as handle:
                opened = os.fstat(handle.fileno())
                if _file_identity(before) != _file_identity(opened):
                    raise ValueError("Asset identity changed")
                with wave.open(handle, "rb") as source:
                    channels = source.getnchannels()
                    sample_width = source.getsampwidth()
                    sample_rate = source.getframerate()
                    duration_samples = source.getnframes()
                    compression = source.getcomptype()
                after_open = os.fstat(handle.fileno())
            after_path = resolved.stat(follow_symlinks=False)
            if (
                _file_identity(opened) != _file_identity(after_open)
                or _file_identity(opened) != _file_identity(after_path)
                or self._resolver.resolve_existing_regular_file(asset.logical_uri) != resolved
                or resolved.is_symlink()
            ):
                raise ValueError("Asset identity changed")
            if (
                compression != "NONE"
                or sample_rate != 48_000
                or not 1 <= channels <= MAX_AUDIO_CHANNELS
                or sample_width not in {1, 2, 3, 4}
                or duration_samples <= 0
            ):
                raise ValueError("WAV format is unsupported")
            return channels, sample_width, duration_samples
        except (EOFError, OSError, ProductError, ValueError, wave.Error):
            raise _closed_error(
                "ERR_TASK098_REVIEW_WAV_NOT_SUPPORTED",
                "Universal WAV Review requires a supported canonical PCM WAV",
                ProductErrorCategory.VALIDATION,
            ) from None

    def select(self, candidate_id: str) -> dict[str, object]:
        self._ensure_open()
        snapshot, row = self._candidate(candidate_id)
        asset = self._asset(row)
        channels, sample_width, duration_samples = self._inspect_wav_header(asset)
        try:
            selected_at = self._clock()
            selection = _SelectedCandidate(
                candidate_id=candidate_id,
                asset_id=asset.asset_id,
                asset_sha256=asset.checksum,
                production_snapshot_sha256=snapshot["production_snapshot_sha256"],
                audio_snapshot_sha256=snapshot["audio_snapshot_sha256"],
                selected_at=selected_at,
                channel_count=channels,
                sample_width=sample_width,
                duration_samples=duration_samples,
            )
            # Build once before publishing the process-local selection.  A
            # malformed clock or contract leaves no partially selected state.
            self._build_binding(selection, evaluated_at=selected_at)
        except (TypeError, ValueError):
            raise _closed_error(
                "ERR_TASK098_REVIEW_BINDING_INVALID",
                "Universal WAV Review binding is invalid",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from None
        with self._lock:
            if self._closed:
                raise _closed_error(
                    "ERR_TASK098_REVIEW_SELECTION_CLOSED",
                    "Universal WAV Review selection is closed",
                    ProductErrorCategory.STATE,
                )
            self._selection = selection
        return {
            "task_owner": "TASK-098",
            "selected": True,
            "candidate_id": candidate_id,
            "canonical_state_changed": False,
            "wav_header_read": True,
            "audio_body_read": False,
            "playback_started": False,
            "waveform_render_started": False,
        }

    def is_ready(self) -> bool:
        try:
            self()
            return True
        except (ProductError, TypeError, ValueError):
            return False

    def __call__(self) -> Task098ReviewShellBinding:
        self._ensure_open()
        with self._lock:
            selection = self._selection
        if selection is None:
            raise _closed_error(
                "ERR_TASK098_REVIEW_CANDIDATE_NOT_SELECTED",
                "Universal WAV Review Candidate is not selected",
                ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
            )
        snapshot, row = self._candidate(selection.candidate_id)
        asset = self._asset(row)
        if (
            asset.asset_id != selection.asset_id
            or asset.checksum != selection.asset_sha256
            or snapshot["production_snapshot_sha256"]
            != selection.production_snapshot_sha256
            or snapshot["audio_snapshot_sha256"] != selection.audio_snapshot_sha256
        ):
            raise _closed_error(
                "ERR_TASK098_REVIEW_SELECTION_STALE",
                "Universal WAV Review selection is stale",
                ProductErrorCategory.AUTHORIZATION,
            )
        return self._build_binding(selection, evaluated_at=self._clock())

    def _build_binding(
        self, selection: _SelectedCandidate, *, evaluated_at: str
    ) -> Task098ReviewShellBinding:
        range_limit = min(
            selection.duration_samples,
            MAX_REVIEW_DURATION_SAMPLES,
            MAX_DECODED_RANGE_BYTES
            // (selection.channel_count * selection.sample_width),
        )
        if range_limit <= 0:
            raise ValueError("review range is empty")
        policy = AudioMediaReviewPolicyRevision.create(
            policy_id="task098-a6-r2-local-review-policy",
            revision=1,
            parent_record_sha256=None,
            required_sample_rate_hz=48_000,
            max_review_duration_samples=MAX_REVIEW_DURATION_SAMPLES,
            max_observation_age_seconds=MAX_OBSERVATION_AGE_SECONDS,
            official_policy_ref="task098-a6-r2-local-review-policy-v1",
            official_policy_sha256=_POLICY_SHA256,
            effective_at=selection.selected_at,
            expires_at=None,
            audio_read_started=False,
            media_mutation_started=False,
        )
        source = AudioMediaSourceBinding.create(
            source_id=f"task098-source-{selection.candidate_id}",
            media_kind="AUDIO_ASSET",
            contract_state="BOUND_VERIFIED",
            canonical_ref=f"asset-revision-{selection.asset_id}-1",
            canonical_sha256=selection.asset_sha256,
            canonical_revision=1,
            candidate_id=selection.candidate_id,
            asset_id=selection.asset_id,
            rights_state="PASS",
            sample_rate_hz=48_000,
            channel_count=selection.channel_count,
            duration_samples=selection.duration_samples,
            observed_at=selection.selected_at,
            body_included=False,
            absolute_path_included=False,
        )
        capability = PlaybackWaveformCapabilityBinding.create(
            capability_id="task098-a6-r2-windows-wave-runtime",
            contract_state="BOUND_VERIFIED",
            player_state="SUPPORTED",
            waveform_state="SUPPORTED",
            decode_state="SUPPORTED",
            sample_accurate_range_state="SUPPORTED",
            capability_profile_ref="task098-a6-r2-windows-wave-v1",
            capability_profile_sha256=_CAPABILITY_SHA256,
            app_identity_sha256=_APP_IDENTITY_SHA256,
            observed_at=selection.selected_at,
            body_included=False,
            absolute_path_included=False,
        )
        intent = AudioMediaReviewIntent.create(
            intent_id=f"task098-a6-r2-{selection.candidate_id}",
            revision=1,
            parent_record_sha256=None,
            project_id=self._project_id,
            policy_sha256=policy.record_sha256,
            source_binding_sha256=source.record_sha256,
            capability_binding_sha256=capability.record_sha256,
            audio_workspace_snapshot_sha256=selection.audio_snapshot_sha256,
            requested_operations=["AUDITION", "WAVEFORM_VIEW"],
            range_start_sample=0,
            range_end_sample=range_limit,
            requested_at=selection.selected_at,
            body_included=False,
            absolute_path_included=False,
            playback_started=False,
            waveform_render_started=False,
            media_mutation_started=False,
        )
        transcript = TranscriptManifest(
            source_asset_id=selection.asset_id,
            language="und",
            provider_id="task098-local-review",
            model_id="none",
            segments=(),
        )
        workspace_id = "task098.a6r2." + sha256_bytes(
            selection.candidate_id.encode("utf-8")
        ).removeprefix("sha256:")[:24]
        workspace = SubtitleWorkspace(workspace_id=workspace_id, revision=0)
        transcript_sha256 = transcript.to_dict()["manifest_sha256"]
        workspace_sha256 = sha256_bytes(canonical_json_bytes(workspace.to_dict()))
        view_model = open_review_workspace(
            policy=policy,
            source=source,
            capability=capability,
            intent=intent,
            transcript=transcript,
            expected_transcript_sha256=transcript_sha256,
            workspace=workspace,
            expected_workspace_snapshot_sha256=workspace_sha256,
            evaluated_at=evaluated_at,
        )
        return Task098ReviewShellBinding(
            policy=policy,
            source=source,
            capability=capability,
            intent=intent,
            view_model=view_model,
            evaluated_at=evaluated_at,
        )


__all__ = [
    "MAX_OBSERVATION_AGE_SECONDS",
    "MAX_REVIEW_DURATION_SAMPLES",
    "Task098ProductReviewBindingSelector",
]
