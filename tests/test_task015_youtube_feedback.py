from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import inspect
import json
from pathlib import Path

import pytest

from ai_video_production.multimodal_scoring import EvidenceValidity
from ai_video_production.schema_contracts import validate_instance
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.youtube_feedback import (
    AnalyticsMetric,
    AnalyticsObservation,
    AnalyticsWindow,
    FeedbackProfile,
    FeedbackSnapshotState,
    MetricUnit,
    YouTubePublicationBinding,
    compile_youtube_feedback_snapshot,
    verify_youtube_feedback_snapshot_hash,
)


ROOT = Path(__file__).resolve().parents[1]
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64


def publication() -> YouTubePublicationBinding:
    return YouTubePublicationBinding(
        "abcDEF_123", SHA_A, "ASSET-01ARZ3NDEKTSV4RRFFQ69G5FAV", SHA_B, SHA_C, 1_700_000_000
    )


def profile() -> FeedbackProfile:
    return FeedbackProfile(
        "youtube.aggregate-feedback",
        "1.0.0",
        (AnalyticsMetric.IMPRESSIONS_COUNT, AnalyticsMetric.VIEWS_COUNT),
        (AnalyticsMetric.IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT,),
    )


def observation(
    metric: AnalyticsMetric,
    value: int,
    validity: EvidenceValidity = EvidenceValidity.CURRENT_VALID,
) -> AnalyticsObservation:
    units = {
        AnalyticsMetric.IMPRESSIONS_COUNT: MetricUnit.COUNT,
        AnalyticsMetric.VIEWS_COUNT: MetricUnit.COUNT,
        AnalyticsMetric.IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT: MetricUnit.MILLI_PERCENT,
    }
    return AnalyticsObservation(metric, units[metric], value, SHA_A, f"row.{metric.value.lower()}", SHA_D, validity)


def snapshot(*rows: AnalyticsObservation):
    if not rows:
        rows = (
            observation(AnalyticsMetric.VIEWS_COUNT, 120),
            observation(AnalyticsMetric.IMPRESSIONS_COUNT, 1000),
            observation(AnalyticsMetric.IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT, 12_500),
        )
    return compile_youtube_feedback_snapshot(
        publication(), SHA_D, AnalyticsWindow(1_700_000_000, 1_700_086_400), profile(), rows
    )


def test_snapshot_is_deterministic_schema_valid_and_no_effect():
    first = snapshot().to_dict()
    second = snapshot(*reversed(snapshot().observations)).to_dict()
    assert first == second
    assert first["task_owner"] == "TASK-015"
    assert first["state"] == "COMPLETE"
    assert [row["metric"] for row in first["observations"]] == sorted(
        row["metric"] for row in first["observations"]
    )
    assert first["aggregate_public_metrics_only"] is True
    assert first["human_review_required"] is True
    for name in (
        "audience_row_data_included",
        "credentials_accessed",
        "platform_api_called",
        "automatic_profile_tuning_authorized",
        "automatic_edit_plan_mutation_authorized",
        "publication_mutation_authorized",
    ):
        assert first[name] is False
    verify_youtube_feedback_snapshot_hash(first)
    validate_instance(first, ROOT / "schemas" / "youtube-feedback.schema.json")


def test_schema_mirror_is_byte_identical():
    public = (ROOT / "schemas" / "youtube-feedback.schema.json").read_bytes()
    packaged = resources.files("ai_video_production").joinpath(
        "schema_resources", "youtube-feedback.schema.json"
    ).read_bytes()
    assert public == packaged
    validate_instance(snapshot().to_dict(), json.loads(public))


def test_missing_unknown_and_stale_are_distinct_fail_closed_states():
    partial = snapshot(observation(AnalyticsMetric.VIEWS_COUNT, 120))
    assert partial.state is FeedbackSnapshotState.PARTIAL_REQUIRED_METRICS
    assert partial.missing_required_metrics == (AnalyticsMetric.IMPRESSIONS_COUNT,)
    unknown = snapshot(
        observation(AnalyticsMetric.IMPRESSIONS_COUNT, 1000, EvidenceValidity.UNKNOWN),
        observation(AnalyticsMetric.VIEWS_COUNT, 120),
    )
    assert unknown.state is FeedbackSnapshotState.UNKNOWN_EVIDENCE
    assert unknown.unknown_metrics == (AnalyticsMetric.IMPRESSIONS_COUNT,)
    stale = snapshot(
        observation(AnalyticsMetric.IMPRESSIONS_COUNT, 1000, EvidenceValidity.STALE),
        observation(AnalyticsMetric.VIEWS_COUNT, 120, EvidenceValidity.UNKNOWN),
    )
    assert stale.state is FeedbackSnapshotState.STALE_OR_REVOKED_EVIDENCE
    assert stale.stale_or_revoked_metrics == (AnalyticsMetric.IMPRESSIONS_COUNT,)
    assert stale.unknown_metrics == (AnalyticsMetric.VIEWS_COUNT,)


def test_metric_unit_range_and_profile_declaration_are_closed():
    with pytest.raises(ValueError, match="unit does not match"):
        replace(observation(AnalyticsMetric.VIEWS_COUNT, 1), unit=MetricUnit.SECONDS)
    with pytest.raises(ValueError, match="0..100000"):
        observation(AnalyticsMetric.IMPRESSIONS_CLICK_THROUGH_RATE_MILLI_PERCENT, 100_001)
    undeclared = AnalyticsObservation(
        AnalyticsMetric.WATCH_TIME_SECONDS, MetricUnit.SECONDS, 10, SHA_A, "row.watch", SHA_D,
        EvidenceValidity.CURRENT_VALID,
    )
    with pytest.raises(ValueError, match="not declared"):
        snapshot(undeclared)


def test_duplicate_metrics_and_noncanonical_profile_fail_closed():
    row = observation(AnalyticsMetric.VIEWS_COUNT, 10)
    with pytest.raises(ValueError, match="unique"):
        snapshot(row, row)
    with pytest.raises(ValueError, match="canonically sorted"):
        FeedbackProfile(
            "youtube.aggregate-feedback", "1.0.0",
            (AnalyticsMetric.VIEWS_COUNT, AnalyticsMetric.IMPRESSIONS_COUNT), (),
        )
    with pytest.raises(ValueError, match="disjoint"):
        FeedbackProfile(
            "youtube.aggregate-feedback", "1.0.0",
            (AnalyticsMetric.VIEWS_COUNT,), (AnalyticsMetric.VIEWS_COUNT,),
        )


def test_publication_window_identity_and_caps_fail_closed():
    with pytest.raises(ValueError, match="platform_video_id"):
        replace(publication(), platform_video_id="../x")
    with pytest.raises(ValueError, match="before publication"):
        compile_youtube_feedback_snapshot(
            publication(), SHA_D, AnalyticsWindow(1_699_999_999, 1_700_000_001), profile(),
            (observation(AnalyticsMetric.VIEWS_COUNT, 1),),
        )
    with pytest.raises(ValueError, match="366-day"):
        AnalyticsWindow(0, 366 * 24 * 60 * 60 + 1)
    with pytest.raises(ValueError, match="1-32"):
        compile_youtube_feedback_snapshot(
            publication(), SHA_D, AnalyticsWindow(1_700_000_000, 1_700_000_001), profile(), ()
        )


def test_hash_verifier_rejects_outer_and_nested_tamper():
    payload = snapshot().to_dict()
    payload["observations"][0]["value"] += 1
    with pytest.raises(ValueError, match="snapshot_sha256"):
        verify_youtube_feedback_snapshot_hash(payload)
    payload = snapshot().to_dict()
    payload["feedback_profile"]["profile_version"] = "1.0.1"
    body = dict(payload)
    body.pop("snapshot_sha256")
    payload["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    with pytest.raises(ValueError, match="feedback_profile.profile_sha256"):
        verify_youtube_feedback_snapshot_hash(payload)


def test_contract_objects_are_immutable():
    compiled = snapshot()
    with pytest.raises(FrozenInstanceError):
        compiled.state = FeedbackSnapshotState.UNKNOWN_EVIDENCE  # type: ignore[misc]


def test_manual_snapshot_cannot_launder_derived_state_or_partitions():
    compiled = snapshot(observation(AnalyticsMetric.VIEWS_COUNT, 120))
    with pytest.raises(ValueError, match="state and disposition"):
        replace(
            compiled,
            state=FeedbackSnapshotState.COMPLETE,
            missing_required_metrics=(),
        )


def test_public_api_and_import_surface_have_no_effect_capability():
    assert set(inspect.signature(compile_youtube_feedback_snapshot).parameters) == {
        "publication", "source_scoring_manifest_sha256", "window", "profile", "observations"
    }
    tree = ast.parse(
        (ROOT / "src" / "ai_video_production" / "youtube_feedback.py").read_text("utf-8")
    )
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(
        {"subprocess", "requests", "urllib", "httpx", "pathlib", "googleapiclient", "socket"}
    )
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile"})
