from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from ai_video_production.assets import (
    AssetRecord,
    AssetType,
    PermissionState,
    RetentionClass,
    RightsStatus,
)
from ai_video_production.durable_product_job import (
    DurableProductJob,
    DurableProductJobCollection,
    DurableProductJobState,
)
from ai_video_production.ids import IdKind, generate_id
from ai_video_production.interactive_timeline import (
    InteractiveTimeline,
    InteractiveTimelineClip,
    TimelineMediaKind,
    TimelineTrack,
    TimelineTrackRole,
)
from ai_video_production.task021_operations_dashboard import (
    EFFECT_SURFACE,
    CanonicalDashboardReaders,
    CanonicalValidationResult,
    DashboardDisplayState,
    Task021OperationsDashboard,
    render_accessible_dashboard_html,
)
from ai_video_production.timebase import FrameRate


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "ai_video_production" / "task021_operations_dashboard.py"
PROJECT_ID = "PRJ-01ARZ3NDEKTSV4RRFFQ69G5FAV"
T0 = "2026-09-22T00:00:00Z"
T1 = "2026-09-22T00:01:00Z"
H1 = "sha256:" + "1" * 64


def job(kind: str = "LOCAL_ANALYSIS", state: DurableProductJobState = DurableProductJobState.QUEUED) -> DurableProductJob:
    value = DurableProductJob.create(
        kind=kind,
        target_identity="dashboard-target",
        input_hashes={"input": H1},
        created_at=T0,
    )
    if state is DurableProductJobState.QUEUED:
        return value
    if state is DurableProductJobState.FAILED:
        value = value.transition(DurableProductJobState.PREFLIGHT, updated_at=T1)
        return value.transition(
            DurableProductJobState.FAILED,
            error_code="ERR_PRODUCT_JOB_INPUT_STALE",
            updated_at="2026-09-22T00:02:00Z",
        )
    if state is DurableProductJobState.SUCCEEDED:
        value = value.transition(DurableProductJobState.PREFLIGHT, updated_at=T1)
        value = value.transition(DurableProductJobState.READY, updated_at="2026-09-22T00:02:00Z")
        value = value.transition(DurableProductJobState.DISPATCHING, updated_at="2026-09-22T00:03:00Z")
        return value.transition(
            DurableProductJobState.SUCCEEDED,
            result_ref="export-result:canonical-output",
            updated_at="2026-09-22T00:04:00Z",
        )
    raise AssertionError("fixture state not implemented")


def jobs(*values: DurableProductJob) -> DurableProductJobCollection:
    collection = DurableProductJobCollection.create(PROJECT_ID)
    for value in values:
        collection = collection.replace(value)
    return collection


def asset(
    *,
    asset_type: AssetType = AssetType.VIDEO,
    rights: RightsStatus = RightsStatus.OWNED,
    retention: RetentionClass = RetentionClass.STANDARD,
) -> AssetRecord:
    job_id = generate_id(IdKind.JOB)
    return AssetRecord(
        production_job_id=job_id,
        asset_type=asset_type,
        logical_uri=f"asset://{job_id}/outputs/main.mp4",
        checksum=H1,
        rights_status=rights,
        owner="owner",
        retention_class=retention,
        commercial_use=PermissionState.ALLOWED,
        derivative_allowed=PermissionState.ALLOWED,
    )


def timeline(*, with_clip: bool = True) -> InteractiveTimeline:
    track = TimelineTrack("V1", 0, TimelineTrackRole.VIDEO, TimelineMediaKind.VIDEO, "Video")
    clips = ()
    if with_clip:
        clips = (
            InteractiveTimelineClip(
                "clip-1", "V1", 0, 30, "TASK-003", "asset-ref", H1, "Clip 1", "READY",
            ),
        )
    return InteractiveTimeline(
        PROJECT_ID,
        "timeline-main",
        FrameRate(30, 1),
        300,
        (track,),
        clips,
    )


def validation(state: str = "PASS") -> CanonicalValidationResult:
    return CanonicalValidationResult(
        validation_id="bundle-validation",
        source_owner="TASK-037",
        state=state,
        reason_codes=("BUNDLE_INVALID",) if state == "FAIL" else (),
        artifact_ref="evidence:bundle-validation",
        record_sha256=H1,
    )


def dashboard(
    *,
    job_values: DurableProductJobCollection | None = None,
    asset_values=(),
    timeline_value=None,
    validation_values=(),
) -> Task021OperationsDashboard:
    return Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=lambda: job_values or jobs(),
            read_assets=lambda: asset_values,
            read_timeline=lambda: timeline_value,
            read_validation_results=lambda: validation_values,
        ),
    )


def test_empty_dashboard_is_explicit_and_accessible() -> None:
    snapshot = dashboard().refresh()
    assert snapshot.state is DashboardDisplayState.EMPTY
    assert snapshot.state_ja == "対象なし"
    assert all(not section.rows for section in snapshot.sections)

    html = render_accessible_dashboard_html(snapshot)
    assert 'lang="ja"' in html
    assert 'aria-live="polite"' in html
    assert 'href="#task021-dashboard-content"' in html
    assert html.count('role="status"') == 6
    assert "全体状態" in html
    assert "表示する項目はありません" in html
    assert "外部実行、自動修復、Provider操作は行いません" in html


def test_in_progress_job_and_export_queue_are_read_only_projections() -> None:
    ordinary = job()
    export = job(kind="EXPORT")
    snapshot = dashboard(job_values=jobs(ordinary, export), timeline_value=timeline()).refresh()

    assert snapshot.state is DashboardDisplayState.IN_PROGRESS
    assert len(snapshot.section("jobs").rows) == 1
    assert len(snapshot.section("export-queue").rows) == 1
    export_row = snapshot.section("export-queue").rows[0]
    assert export_row.state_ja == "待機中"
    assert export_row.operation_available is False
    assert "正本Job側" in export_row.next_action_ja
    assert snapshot.read_only is True
    assert snapshot.external_execution_available is False
    assert all(value is False for value in EFFECT_SURFACE.values())


def test_failure_states_show_japanese_reason_next_action_and_location() -> None:
    failed = job(state=DurableProductJobState.FAILED)
    blocked = asset(rights=RightsStatus.BLOCKED)
    snapshot = dashboard(
        job_values=jobs(failed),
        asset_values=(blocked,),
        timeline_value=timeline(with_clip=False),
        validation_values=(validation("FAIL"),),
    ).refresh()

    assert snapshot.state is DashboardDisplayState.FAILURE
    job_row = snapshot.section("jobs").rows[0]
    assert job_row.failure_reason_ja == "入力が更新され、再準備が必要です。"
    assert job_row.artifact_location_ja == "未生成"
    assert "再準備" in job_row.next_action_ja
    assert snapshot.section("assets").rows[0].state_ja == "利用不可"
    assert snapshot.section("timeline").rows[0].state_ja == "空のTimeline"
    assert snapshot.section("validation").rows[0].failure_reason_ja == "検証理由コード: BUNDLE_INVALID"


def test_complete_state_shows_canonical_artifact_references() -> None:
    completed_export = job(kind="EXPORT", state=DurableProductJobState.SUCCEEDED)
    snapshot = dashboard(
        job_values=jobs(completed_export),
        asset_values=(asset(),),
        timeline_value=timeline(),
        validation_values=(validation(),),
    ).refresh()

    assert snapshot.state is DashboardDisplayState.SUCCESS
    export_row = snapshot.section("export-queue").rows[0]
    assert export_row.state_ja == "完了"
    assert export_row.artifact_location_ja == "export-result:canonical-output"
    assert snapshot.section("assets").rows[0].artifact_location_ja.startswith("asset://")
    assert snapshot.section("timeline").rows[0].artifact_location_ja == "timeline:timeline-main"
    assert snapshot.section("validation").rows[0].artifact_location_ja == "evidence:bundle-validation"
    html = render_accessible_dashboard_html(snapshot)
    assert "状態" in html and "失敗理由" in html and "次に可能な操作" in html and "成果物場所" in html
    assert '<th scope="row" translate="no">' in html and '<th scope="col">' in html
    assert '<td translate="no">export-result:canonical-output</td>' in html


def test_audio_and_private_media_are_omitted_without_exposing_identity() -> None:
    audio = asset(asset_type=AssetType.AUDIO)
    private = asset(retention=RetentionClass.CONFIDENTIAL)
    snapshot = dashboard(asset_values=(audio, private)).refresh()

    section = snapshot.section("assets")
    assert section.rows == ()
    assert "2件" in section.note_ja
    html = render_accessible_dashboard_html(snapshot)
    assert audio.asset_id not in html
    assert private.asset_id not in html
    assert audio.logical_uri not in html
    assert private.logical_uri not in html


def test_each_canonical_reader_is_called_once_and_failure_is_redacted() -> None:
    counts = {"jobs": 0, "assets": 0, "timeline": 0, "validation": 0}

    def read(name, value=None, *, fail=False):
        def inner():
            counts[name] += 1
            if fail:
                raise RuntimeError(r"C:\private\secret-token.txt")
            return value
        return inner

    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=read("jobs", fail=True),
            read_assets=read("assets", ()),
            read_timeline=read("timeline", None),
            read_validation_results=read("validation", ()),
        ),
    )
    snapshot = service.refresh()

    assert counts == {"jobs": 1, "assets": 1, "timeline": 1, "validation": 1}
    assert snapshot.section("jobs").state is DashboardDisplayState.FAILURE
    html = render_accessible_dashboard_html(snapshot)
    assert "secret-token" not in html and "C:\\private" not in html


def test_project_mismatch_fails_closed_and_html_escapes_canonical_labels() -> None:
    foreign = DurableProductJobCollection.create("PRJ-01ARZ3NDEKTSV4RRFFQ69G5FAW")
    snapshot = dashboard(job_values=foreign).refresh()
    assert snapshot.section("jobs").state is DashboardDisplayState.FAILURE

    escaped = replace(snapshot.section("jobs").rows[0], name_ja="<script>alert(1)</script>")
    changed_section = replace(snapshot.section("jobs"), rows=(escaped,))
    changed = replace(snapshot, sections=(changed_section,) + snapshot.sections[1:])
    html = render_accessible_dashboard_html(changed)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_large_sections_are_bounded_with_explicit_overflow_guidance() -> None:
    results = tuple(
        CanonicalValidationResult(
            validation_id=f"validation-{index:03}",
            source_owner="TASK-037",
            state="PASS",
            artifact_ref=f"evidence:validation-{index:03}",
            record_sha256=H1,
        )
        for index in range(205)
    )
    section = dashboard(validation_values=results).refresh().section("validation")
    assert len(section.rows) == 200
    assert "残り5件" in section.note_ja


def test_static_surface_has_no_store_filesystem_network_or_process_control() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported.isdisjoint({"os", "pathlib", "subprocess", "socket", "requests", "urllib", "httpx"})
    text = MODULE.read_text(encoding="utf-8")
    assert "Store(" not in text
    assert ".save(" not in text
    assert "open(" not in text
