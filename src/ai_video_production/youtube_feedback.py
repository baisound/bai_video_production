"""TASK-015 deterministic, credential-free YouTube feedback contracts.

This module accepts already-observed aggregate analytics rows.  It performs no
API call, authentication, publication, media access, profile tuning, or edit
mutation.  Output is advisory evidence for later Human-reviewed consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable

from .ids import IdKind, validate_id
from .multimodal_scoring import EvidenceValidity
from .serialization import canonical_json_bytes, sha256_bytes


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MAX_OBSERVATIONS = 32
_MAX_WINDOW_SECONDS = 366 * 24 * 60 * 60
_MAX_VALUE = (1 << 63) - 1


def _sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")
    return value


def _bounded_int(value: int, field_name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer in {minimum}..{maximum}")
    return value


class AnalyticsMetric(str, Enum):
    IMPRESSIONS_COUNT = "IMPRESSIONS_COUNT"
    VIEWS_COUNT = "VIEWS_COUNT"
    WATCH_TIME_SECONDS = "WATCH_TIME_SECONDS"
    AVERAGE_VIEW_DURATION_MILLISECONDS = "AVERAGE_VIEW_DURATION_MILLISECONDS"
    IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT = "IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT"
    AVERAGE_PERCENTAGE_VIEWED_MILLI_PERCENT = "AVERAGE_PERCENTAGE_VIEWED_MILLI_PERCENT"


class MetricUnit(str, Enum):
    COUNT = "COUNT"
    SECONDS = "SECONDS"
    MILLISECONDS = "MILLISECONDS"
    MILLI_PERCENT = "MILLI_PERCENT"


_METRIC_CONTRACT: dict[AnalyticsMetric, tuple[MetricUnit, int]] = {
    AnalyticsMetric.IMPRESSIONS_COUNT: (MetricUnit.COUNT, _MAX_VALUE),
    AnalyticsMetric.VIEWS_COUNT: (MetricUnit.COUNT, _MAX_VALUE),
    AnalyticsMetric.WATCH_TIME_SECONDS: (MetricUnit.SECONDS, _MAX_VALUE),
    AnalyticsMetric.AVERAGE_VIEW_DURATION_MILLISECONDS: (MetricUnit.MILLISECONDS, _MAX_VALUE),
    AnalyticsMetric.IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT: (
        MetricUnit.MILLI_PERCENT,
        100_000,
    ),
    AnalyticsMetric.AVERAGE_PERCENTAGE_VIEWED_MILLI_PERCENT: (
        MetricUnit.MILLI_PERCENT,
        100_000,
    ),
}


class FeedbackSnapshotState(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL_REQUIRED_METRICS = "PARTIAL_REQUIRED_METRICS"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    STALE_OR_REVOKED_EVIDENCE = "STALE_OR_REVOKED_EVIDENCE"


@dataclass(frozen=True, slots=True)
class YouTubePublicationBinding:
    platform_video_id: str
    channel_identity_sha256: str
    source_asset_id: str
    source_edit_plan_sha256: str
    render_receipt_sha256: str
    published_at_epoch_s: int

    def __post_init__(self) -> None:
        if not isinstance(self.platform_video_id, str) or not _VIDEO_ID_RE.fullmatch(
            self.platform_video_id
        ):
            raise ValueError("platform_video_id is invalid")
        _sha256(self.channel_identity_sha256, "channel_identity_sha256")
        validate_id(self.source_asset_id, IdKind.ASSET)
        _sha256(self.source_edit_plan_sha256, "source_edit_plan_sha256")
        _sha256(self.render_receipt_sha256, "render_receipt_sha256")
        _bounded_int(self.published_at_epoch_s, "published_at_epoch_s", 0, _MAX_VALUE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_video_id": self.platform_video_id,
            "channel_identity_sha256": self.channel_identity_sha256,
            "source_asset_id": self.source_asset_id,
            "source_edit_plan_sha256": self.source_edit_plan_sha256,
            "render_receipt_sha256": self.render_receipt_sha256,
            "published_at_epoch_s": self.published_at_epoch_s,
        }


@dataclass(frozen=True, slots=True)
class AnalyticsWindow:
    start_epoch_s: int
    end_epoch_s: int

    def __post_init__(self) -> None:
        _bounded_int(self.start_epoch_s, "start_epoch_s", 0, _MAX_VALUE)
        _bounded_int(self.end_epoch_s, "end_epoch_s", 1, _MAX_VALUE)
        if self.end_epoch_s <= self.start_epoch_s:
            raise ValueError("analytics window must be positive and end-exclusive")
        if self.end_epoch_s - self.start_epoch_s > _MAX_WINDOW_SECONDS:
            raise ValueError("analytics window exceeds the 366-day cap")

    def to_dict(self) -> dict[str, int]:
        return {"start_epoch_s": self.start_epoch_s, "end_epoch_s": self.end_epoch_s}


@dataclass(frozen=True, slots=True)
class FeedbackProfile:
    profile_id: str
    profile_version: str
    required_metrics: tuple[AnalyticsMetric, ...]
    optional_metrics: tuple[AnalyticsMetric, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not _STABLE_ID_RE.fullmatch(self.profile_id):
            raise ValueError("profile_id is invalid")
        if not isinstance(self.profile_version, str) or not _SEMVER_RE.fullmatch(
            self.profile_version
        ):
            raise ValueError("profile_version must be semantic version x.y.z")
        if not 1 <= len(self.required_metrics) <= len(AnalyticsMetric):
            raise ValueError("required_metrics must contain 1-6 metrics")
        for field_name, values in (
            ("required_metrics", self.required_metrics),
            ("optional_metrics", self.optional_metrics),
        ):
            if any(not isinstance(item, AnalyticsMetric) for item in values):
                raise ValueError(f"{field_name} must contain AnalyticsMetric values")
            if values != tuple(sorted(set(values), key=lambda item: item.value)):
                raise ValueError(f"{field_name} must be unique and canonically sorted")
        if set(self.required_metrics) & set(self.optional_metrics):
            raise ValueError("required_metrics and optional_metrics must be disjoint")

    @property
    def declared_metrics(self) -> frozenset[AnalyticsMetric]:
        return frozenset((*self.required_metrics, *self.optional_metrics))

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "required_metrics": [item.value for item in self.required_metrics],
            "optional_metrics": [item.value for item in self.optional_metrics],
        }
        body["profile_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


@dataclass(frozen=True, slots=True)
class AnalyticsObservation:
    metric: AnalyticsMetric
    unit: MetricUnit
    value: int
    provenance_manifest_sha256: str
    provenance_row_id: str
    provenance_row_sha256: str
    validity: EvidenceValidity

    def __post_init__(self) -> None:
        if not isinstance(self.metric, AnalyticsMetric):
            raise ValueError("metric must be an AnalyticsMetric")
        if not isinstance(self.unit, MetricUnit):
            raise ValueError("unit must be a MetricUnit")
        if not isinstance(self.validity, EvidenceValidity):
            raise ValueError("validity must be an EvidenceValidity")
        expected_unit, maximum = _METRIC_CONTRACT[self.metric]
        if self.unit is not expected_unit:
            raise ValueError(f"unit does not match metric {self.metric.value}")
        _bounded_int(self.value, "value", 0, maximum)
        _sha256(self.provenance_manifest_sha256, "provenance_manifest_sha256")
        _sha256(self.provenance_row_sha256, "provenance_row_sha256")
        if not isinstance(self.provenance_row_id, str) or not _STABLE_ID_RE.fullmatch(
            self.provenance_row_id
        ):
            raise ValueError("provenance_row_id is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric.value,
            "unit": self.unit.value,
            "value": self.value,
            "provenance_manifest_sha256": self.provenance_manifest_sha256,
            "provenance_row_id": self.provenance_row_id,
            "provenance_row_sha256": self.provenance_row_sha256,
            "validity": self.validity.value,
        }


@dataclass(frozen=True, slots=True)
class YouTubeFeedbackSnapshot:
    publication: YouTubePublicationBinding
    source_scoring_manifest_sha256: str
    window: AnalyticsWindow
    profile: FeedbackProfile
    observations: tuple[AnalyticsObservation, ...]
    state: FeedbackSnapshotState
    missing_required_metrics: tuple[AnalyticsMetric, ...]
    unknown_metrics: tuple[AnalyticsMetric, ...]
    stale_or_revoked_metrics: tuple[AnalyticsMetric, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.publication, YouTubePublicationBinding):
            raise ValueError("publication must be a YouTubePublicationBinding")
        _sha256(self.source_scoring_manifest_sha256, "source_scoring_manifest_sha256")
        if not isinstance(self.window, AnalyticsWindow):
            raise ValueError("window must be an AnalyticsWindow")
        if not isinstance(self.profile, FeedbackProfile):
            raise ValueError("profile must be a FeedbackProfile")
        if not isinstance(self.state, FeedbackSnapshotState):
            raise ValueError("state must be a FeedbackSnapshotState")
        if self.window.start_epoch_s < self.publication.published_at_epoch_s:
            raise ValueError("analytics window cannot start before publication")
        if not 1 <= len(self.observations) <= _MAX_OBSERVATIONS:
            raise ValueError("observations must contain 1-32 rows")
        if any(not isinstance(item, AnalyticsObservation) for item in self.observations):
            raise ValueError("observations must contain AnalyticsObservation values")
        if self.observations != tuple(sorted(self.observations, key=lambda item: item.metric.value)):
            raise ValueError("observations must be canonically sorted")
        expected = _classify_observations(self.profile, self.observations)
        actual = (
            self.state,
            self.missing_required_metrics,
            self.unknown_metrics,
            self.stale_or_revoked_metrics,
        )
        if actual != expected:
            raise ValueError("snapshot state and disposition partitions do not match observations")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "snapshot_version": "1.0.0",
            "task_owner": "TASK-015",
            "publication": self.publication.to_dict(),
            "source_scoring_manifest_sha256": self.source_scoring_manifest_sha256,
            "analytics_window": self.window.to_dict(),
            "feedback_profile": self.profile.to_dict(),
            "observations": [item.to_dict() for item in self.observations],
            "state": self.state.value,
            "missing_required_metrics": [item.value for item in self.missing_required_metrics],
            "unknown_metrics": [item.value for item in self.unknown_metrics],
            "stale_or_revoked_metrics": [item.value for item in self.stale_or_revoked_metrics],
            "aggregate_public_metrics_only": True,
            "audience_row_data_included": False,
            "credentials_accessed": False,
            "platform_api_called": False,
            "human_review_required": True,
            "automatic_profile_tuning_authorized": False,
            "automatic_edit_plan_mutation_authorized": False,
            "publication_mutation_authorized": False,
        }
        body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
        return body


def compile_youtube_feedback_snapshot(
    publication: YouTubePublicationBinding,
    source_scoring_manifest_sha256: str,
    window: AnalyticsWindow,
    profile: FeedbackProfile,
    observations: Iterable[AnalyticsObservation],
) -> YouTubeFeedbackSnapshot:
    """Compile bounded aggregate analytics Evidence into an advisory snapshot."""

    if not isinstance(publication, YouTubePublicationBinding):
        raise ValueError("publication must be a YouTubePublicationBinding")
    _sha256(source_scoring_manifest_sha256, "source_scoring_manifest_sha256")
    if not isinstance(window, AnalyticsWindow):
        raise ValueError("window must be an AnalyticsWindow")
    if not isinstance(profile, FeedbackProfile):
        raise ValueError("profile must be a FeedbackProfile")
    if window.start_epoch_s < publication.published_at_epoch_s:
        raise ValueError("analytics window cannot start before publication")
    rows = tuple(observations)
    if not 1 <= len(rows) <= _MAX_OBSERVATIONS:
        raise ValueError("observations must contain 1-32 rows")
    if any(not isinstance(item, AnalyticsObservation) for item in rows):
        raise ValueError("observations must contain AnalyticsObservation values")
    canonical_rows = tuple(sorted(rows, key=lambda item: item.metric.value))
    state, missing, unknown, stale_or_revoked = _classify_observations(profile, canonical_rows)
    return YouTubeFeedbackSnapshot(
        publication,
        source_scoring_manifest_sha256,
        window,
        profile,
        canonical_rows,
        state,
        missing,
        unknown,
        stale_or_revoked,
    )


def _classify_observations(
    profile: FeedbackProfile,
    rows: tuple[AnalyticsObservation, ...],
) -> tuple[
    FeedbackSnapshotState,
    tuple[AnalyticsMetric, ...],
    tuple[AnalyticsMetric, ...],
    tuple[AnalyticsMetric, ...],
]:
    metrics = [item.metric for item in rows]
    if len(metrics) != len(set(metrics)):
        raise ValueError("observation metrics must be unique")
    undeclared = set(metrics) - profile.declared_metrics
    if undeclared:
        raise ValueError("observation metric is not declared by the feedback profile")
    observed = set(metrics)
    missing = tuple(sorted(set(profile.required_metrics) - observed, key=lambda item: item.value))
    unknown = tuple(item.metric for item in rows if item.validity is EvidenceValidity.UNKNOWN)
    stale_or_revoked = tuple(
        item.metric
        for item in rows
        if item.validity in {EvidenceValidity.STALE, EvidenceValidity.REVOKED}
    )
    if stale_or_revoked:
        state = FeedbackSnapshotState.STALE_OR_REVOKED_EVIDENCE
    elif unknown:
        state = FeedbackSnapshotState.UNKNOWN_EVIDENCE
    elif missing:
        state = FeedbackSnapshotState.PARTIAL_REQUIRED_METRICS
    else:
        state = FeedbackSnapshotState.COMPLETE
    return state, missing, unknown, stale_or_revoked


def verify_youtube_feedback_snapshot_hash(payload: dict[str, Any]) -> None:
    """Verify nested and outer non-self digests without accepting digest-only Evidence."""

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    body = dict(payload)
    claimed = body.pop("snapshot_sha256", None)
    _sha256(claimed, "snapshot_sha256")
    profile = body.get("feedback_profile")
    if not isinstance(profile, dict):
        raise ValueError("feedback_profile must be an object")
    profile_body = dict(profile)
    profile_claimed = profile_body.pop("profile_sha256", None)
    _sha256(profile_claimed, "feedback_profile.profile_sha256")
    if profile_claimed != sha256_bytes(canonical_json_bytes(profile_body)):
        raise ValueError("feedback_profile.profile_sha256 does not match its canonical body")
    if claimed != sha256_bytes(canonical_json_bytes(body)):
        raise ValueError("snapshot_sha256 does not match the canonical snapshot body")
