from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

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
from ai_video_production.integrated_dashboard_operations import (
    DashboardExecutionReceiptBinding,
    DashboardOperationProposalRevision,
    HumanOperationConfirmationBinding,
    IntegratedDashboardSnapshotRevision,
)
from ai_video_production.task021_operations_dashboard import (
    EFFECT_SURFACE,
    CanonicalDashboardReaders,
    CanonicalOperationState,
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
T2 = "2026-09-22T01:00:00Z"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64


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


def integrated_snapshot(
    *,
    project_id: str = PROJECT_ID,
    snapshot_state: str = "STALE",
    coverage_state: str = "PARTIAL",
) -> IntegratedDashboardSnapshotRevision:
    return IntegratedDashboardSnapshotRevision.create(
        snapshot_id="task021-integrated-snapshot",
        revision=1,
        parent_record_sha256=None,
        project_id=project_id,
        policy_sha256=H1,
        query_sha256=H2,
        source_binding_hashes=[H3],
        job_view_hashes=[],
        evidence_view_hashes=[],
        incident_view_hashes=[],
        alert_hashes=[],
        coverage_state=coverage_state,
        snapshot_state=snapshot_state,
        source_watermark_sha256=H1,
        generated_at=T1,
        body_included=False,
        private_detail_included=False,
        effect_started_by_dashboard=False,
    )


def operation_proposal(
    snapshot: IntegratedDashboardSnapshotRevision,
    **overrides,
) -> DashboardOperationProposalRevision:
    fields = dict(
        proposal_id="dashboard-operation-proposal",
        revision=1,
        parent_record_sha256=None,
        snapshot_sha256=snapshot.record_sha256,
        operation_kind="REQUEST_PAUSE",
        target_source_sha256=H2,
        expected_target_state_version=1,
        precondition_hashes=[H1, H2],
        proposal_state="PROPOSED",
        reason_codes=[],
        created_at=T0,
        expires_at=T2,
        proposal_only=True,
        execution_started=False,
    )
    fields.update(overrides)
    return DashboardOperationProposalRevision.create(**fields)


def human_confirmation(
    proposal: DashboardOperationProposalRevision,
    **overrides,
) -> HumanOperationConfirmationBinding:
    proposal_data = proposal.to_dict()
    fields = dict(
        contract_state="BOUND_VERIFIED",
        confirmation_id="dashboard-human-confirmation",
        confirmation_revision=1,
        confirmation_sha256=H3,
        proposal_sha256=proposal.record_sha256,
        snapshot_sha256=proposal_data["snapshot_sha256"],
        target_source_sha256=proposal_data["target_source_sha256"],
        operation_kind=proposal_data["operation_kind"],
        reviewer_kind="HUMAN",
        decision="APPROVE",
        decided_at=T0,
        expires_at=T2,
        one_shot=True,
        consumed=False,
        evidence_ref="owner-gate-evidence",
        evidence_sha256=H1,
    )
    fields.update(overrides)
    return HumanOperationConfirmationBinding.create(**fields)


def execution_receipt(
    proposal: DashboardOperationProposalRevision,
    confirmation: HumanOperationConfirmationBinding,
    **overrides,
) -> DashboardExecutionReceiptBinding:
    fields = dict(
        contract_state="BOUND_VERIFIED",
        receipt_id="dashboard-execution-receipt",
        receipt_ref="canonical-external-receipt",
        receipt_sha256=H1,
        proposal_sha256=proposal.record_sha256,
        confirmation_sha256=confirmation.record_sha256,
        operation_identity="external-operation",
        external_state="ACCEPTED",
        observed_at=T1,
        canonical_persistence_verified=True,
        effect_started_by_dashboard=False,
    )
    fields.update(overrides)
    return DashboardExecutionReceiptBinding.create(**fields)


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


def test_integrated_snapshot_public_state_is_read_once_without_identity_leak() -> None:
    calls = 0
    canonical = integrated_snapshot()

    def read_integrated_snapshot() -> IntegratedDashboardSnapshotRevision:
        nonlocal calls
        calls += 1
        return canonical

    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=read_integrated_snapshot,
        ),
    )

    snapshot = service.refresh()
    section = snapshot.section("operations-state")
    html = render_accessible_dashboard_html(snapshot)

    assert calls == 1
    assert snapshot.state is DashboardDisplayState.WARNING
    assert section.state is DashboardDisplayState.WARNING
    assert tuple(row.state_ja for row in section.rows) == ("情報が古い", "一部のみ")
    assert "識別子、ハッシュ、時刻、非公開情報は表示しません" in section.note_ja
    assert 'data-operation-enabled="false"' in html
    assert canonical.record_sha256 not in html
    assert "task021-integrated-snapshot" not in html
    assert H1 not in html and H2 not in html and H3 not in html
    assert T1 not in html


@pytest.mark.parametrize(
    ("snapshot_state", "expected_state", "expected_label"),
    (
        ("ACTION_REQUIRED", DashboardDisplayState.WARNING, "対応が必要"),
        ("DEGRADED", DashboardDisplayState.IN_PROGRESS, "進行中または縮退"),
        (
            "NO_ACTIVE_INCIDENT_PROVEN",
            DashboardDisplayState.SUCCESS,
            "現在のIncidentなし（証明済み）",
        ),
        ("STALE", DashboardDisplayState.WARNING, "情報が古い"),
        ("UNKNOWN", DashboardDisplayState.UNKNOWN, "判定不能"),
    ),
)
def test_integrated_snapshot_closed_states_are_projected_without_reclassification(
    snapshot_state: str,
    expected_state: DashboardDisplayState,
    expected_label: str,
) -> None:
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: integrated_snapshot(
                snapshot_state=snapshot_state,
                coverage_state="COMPLETE",
            ),
        ),
    )

    snapshot = service.refresh()
    state_row = snapshot.section("operations-state").rows[0]
    assert state_row.state is expected_state
    assert state_row.state_ja == expected_label
    assert snapshot.state is expected_state


def test_integrated_snapshot_absence_and_read_failure_remain_fail_closed() -> None:
    empty_service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: None,
        ),
    )
    empty = empty_service.refresh()
    assert empty.section("operations-state").state is DashboardDisplayState.EMPTY
    assert empty.state is DashboardDisplayState.EMPTY

    def private_failure() -> IntegratedDashboardSnapshotRevision:
        raise RuntimeError(r"C:\private\secret-token")

    failed_service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=private_failure,
        ),
    )
    failed = failed_service.refresh()
    html = render_accessible_dashboard_html(failed)
    assert failed.section("operations-state").state is DashboardDisplayState.FAILURE
    assert "secret-token" not in html and r"C:\private" not in html


def test_integrated_snapshot_project_mismatch_is_rejected() -> None:
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: integrated_snapshot(
                project_id="PRJ-01ARZ3NDEKTSV4RRFFQ69G5FAW"
            ),
        ),
    )

    snapshot = service.refresh()
    assert snapshot.section("operations-state").state is DashboardDisplayState.FAILURE


def test_operation_gate_projects_exact_current_human_state_without_effect_authority() -> None:
    canonical = integrated_snapshot(
        snapshot_state="NO_ACTIVE_INCIDENT_PROVEN",
        coverage_state="COMPLETE",
    )
    proposal = operation_proposal(canonical)
    confirmation = human_confirmation(proposal)
    calls = {"snapshot": 0, "operation": 0}

    def read_snapshot() -> IntegratedDashboardSnapshotRevision:
        calls["snapshot"] += 1
        return canonical

    def read_operation() -> CanonicalOperationState:
        calls["operation"] += 1
        return CanonicalOperationState(proposal, confirmation, None, T1)

    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=read_snapshot,
            read_operation_state=read_operation,
        ),
    )

    snapshot = service.refresh()
    section = snapshot.section("operation-gate")
    html = render_accessible_dashboard_html(snapshot)

    assert calls == {"snapshot": 1, "operation": 1}
    assert section.state is DashboardDisplayState.WARNING
    assert tuple(row.state_ja for row in section.rows) == (
        "外部Human Gate準備完了",
        "人間承認済み",
        "未実行",
    )
    assert all(row.operation_available is False for row in section.rows)
    assert snapshot.external_execution_available is False
    assert EFFECT_SURFACE["dashboard_operation_execution"] is False
    assert 'data-operation-enabled="false"' in html
    assert proposal.record_sha256 not in html
    assert confirmation.record_sha256 not in html
    assert "dashboard-operation-proposal" not in html
    assert T0 not in html and T1 not in html and T2 not in html


def test_operation_gate_without_human_confirmation_remains_blocked() -> None:
    canonical = integrated_snapshot()
    proposal = operation_proposal(canonical)
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, None, None, T1
            ),
        ),
    )

    section = service.refresh().section("operation-gate")
    assert section.state is DashboardDisplayState.WARNING
    assert section.rows[0].state_ja == "ブロック中"
    assert "人間確認が結び付いていません" in section.rows[0].failure_reason_ja
    assert section.rows[1].state_ja == "人間確認なし"
    assert section.rows[2].state_ja == "未実行"


@pytest.mark.parametrize(
    ("confirmation_overrides", "expected_label"),
    (
        ({"decision": "REJECT"}, "人間が却下"),
        ({"decision": "REVISE"}, "修正依頼"),
        ({"expires_at": T1}, "再確認が必要"),
    ),
)
def test_operation_gate_preserves_closed_human_decisions(
    confirmation_overrides: dict[str, str],
    expected_label: str,
) -> None:
    canonical = integrated_snapshot()
    proposal = operation_proposal(canonical)
    confirmation = human_confirmation(proposal, **confirmation_overrides)
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, confirmation, None, T1
            ),
        ),
    )

    section = service.refresh().section("operation-gate")
    assert section.state is DashboardDisplayState.WARNING
    assert section.rows[0].state_ja == "ブロック中"
    assert section.rows[1].state_ja == expected_label


def test_operation_gate_renders_persisted_external_result_without_receipt_identity() -> None:
    canonical = integrated_snapshot(
        snapshot_state="NO_ACTIVE_INCIDENT_PROVEN",
        coverage_state="COMPLETE",
    )
    proposal = operation_proposal(canonical)
    confirmation = human_confirmation(proposal)
    receipt = execution_receipt(proposal, confirmation)
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, confirmation, receipt, T1
            ),
        ),
    )

    snapshot = service.refresh()
    section = snapshot.section("operation-gate")
    html = render_accessible_dashboard_html(snapshot)
    assert section.state is DashboardDisplayState.SUCCESS
    assert tuple(row.state_ja for row in section.rows) == (
        "外部結果記録済み",
        "人間承認済み",
        "外部で受理済み",
    )
    assert receipt.record_sha256 not in html
    assert "canonical-external-receipt" not in html
    assert "external-operation" not in html


@pytest.mark.parametrize(
    ("external_state", "expected_state", "expected_label"),
    (
        ("REJECTED", DashboardDisplayState.WARNING, "外部で拒否"),
        ("FAILED", DashboardDisplayState.FAILURE, "外部で失敗"),
    ),
)
def test_operation_gate_preserves_closed_external_results(
    external_state: str,
    expected_state: DashboardDisplayState,
    expected_label: str,
) -> None:
    canonical = integrated_snapshot()
    proposal = operation_proposal(canonical)
    confirmation = human_confirmation(proposal)
    receipt = execution_receipt(
        proposal,
        confirmation,
        external_state=external_state,
        canonical_persistence_verified=False,
    )
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, confirmation, receipt, T1
            ),
        ),
    )

    section = service.refresh().section("operation-gate")
    assert section.state is expected_state
    assert section.rows[2].state_ja == expected_label


def test_operation_gate_unknown_external_result_forbids_automatic_replay() -> None:
    canonical = integrated_snapshot()
    proposal = operation_proposal(canonical)
    confirmation = human_confirmation(proposal)
    receipt = execution_receipt(
        proposal,
        confirmation,
        external_state="UNKNOWN",
        canonical_persistence_verified=False,
    )
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, confirmation, receipt, T1
            ),
        ),
    )

    section = service.refresh().section("operation-gate")
    assert section.state is DashboardDisplayState.UNKNOWN
    assert section.rows[2].state_ja == "外部結果不明"
    assert "自動再実行は禁止" in section.rows[2].next_action_ja
    assert "自動再実行" in section.rows[0].next_action_ja


def test_operation_gate_receipt_mismatch_is_unknown_not_recorded_success() -> None:
    canonical = integrated_snapshot()
    proposal = operation_proposal(canonical)
    confirmation = human_confirmation(proposal)
    mismatched = execution_receipt(
        proposal,
        confirmation,
        confirmation_sha256=H2,
        external_state="REJECTED",
    )
    service = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, confirmation, mismatched, T1
            ),
        ),
    )

    section = service.refresh().section("operation-gate")
    assert section.state is DashboardDisplayState.UNKNOWN
    assert section.rows[0].state_ja == "外部結果照合不能"
    assert "一致しません" in section.rows[0].failure_reason_ja
    assert "自動再実行は禁止" in section.rows[0].next_action_ja


def test_operation_gate_snapshot_crossing_and_private_reader_failure_fail_closed() -> None:
    canonical = integrated_snapshot()
    foreign = integrated_snapshot(
        project_id=PROJECT_ID,
        snapshot_state="UNKNOWN",
    )
    proposal = operation_proposal(foreign)
    crossed = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                proposal, None, None, T1
            ),
        ),
    ).refresh()
    assert crossed.section("operation-gate").state is DashboardDisplayState.FAILURE

    def private_failure() -> CanonicalOperationState:
        raise RuntimeError(r"C:\private\secret-token")

    failed = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=private_failure,
        ),
    ).refresh()
    html = render_accessible_dashboard_html(failed)
    assert failed.section("operation-gate").state is DashboardDisplayState.FAILURE
    assert "secret-token" not in html and r"C:\private" not in html

    invalid = Task021OperationsDashboard(
        project_id=PROJECT_ID,
        readers=CanonicalDashboardReaders(
            read_jobs=jobs,
            read_assets=lambda: (),
            read_timeline=lambda: None,
            read_validation_results=lambda: (),
            read_integrated_snapshot=lambda: canonical,
            read_operation_state=lambda: CanonicalOperationState(
                "not-a-proposal", None, None, T1  # type: ignore[arg-type]
            ),
        ),
    ).refresh()
    assert invalid.section("operation-gate").state is DashboardDisplayState.FAILURE


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
