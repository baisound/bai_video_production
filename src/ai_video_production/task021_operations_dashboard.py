"""TASK-021 read-only Japanese operations dashboard projection.

Canonical owners are injected as readers and are read once per refresh.  This
module keeps no store, performs no recovery or execution, and never opens an
artifact.  Export Queue rows are a second projection of the canonical durable
Product Job collection, not a second queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html import escape
import re
from types import MappingProxyType
from typing import Callable, Sequence

from .assets import AssetRecord, AssetType, RetentionClass, RightsStatus
from .durable_product_job import (
    DurableProductJob,
    DurableProductJobCollection,
    DurableProductJobState,
)
from .interactive_timeline import InteractiveTimeline
from .integrated_dashboard_operations import (
    CoverageState,
    DashboardExecutionReceiptBinding,
    DashboardOperationProposalRevision,
    DashboardSnapshotState,
    HumanOperationConfirmationBinding,
    IntegratedDashboardSnapshotRevision,
    operation_admission_report,
)
from .serialization import validate_sha256


_PUBLIC_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}")
_REASON_RE = re.compile(r"[A-Z][A-Z0-9_]{1,95}")
_PRIVATE_TERMS = ("credential", "password", "secret", "private-key", "access-token")
_MAX_RENDERED_ROWS_PER_SECTION = 200
_AUDIO_ASSET_TYPES = {
    AssetType.AUDIO,
    AssetType.BGM,
    AssetType.SFX,
    AssetType.VOICE_MODEL,
}


class DashboardDisplayState(str, Enum):
    EMPTY = "EMPTY"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"


_STATE_LABELS = MappingProxyType({
    DashboardDisplayState.EMPTY: "対象なし",
    DashboardDisplayState.IN_PROGRESS: "進行中",
    DashboardDisplayState.SUCCESS: "完了",
    DashboardDisplayState.WARNING: "確認が必要",
    DashboardDisplayState.FAILURE: "失敗",
    DashboardDisplayState.UNKNOWN: "状態不明",
})


def _public_ref(value: str, name: str) -> str:
    if not isinstance(value, str) or not _PUBLIC_REF_RE.fullmatch(value):
        raise ValueError(f"{name} is not a public logical reference")
    folded = value.casefold()
    if (
        "\\" in value
        or value.startswith("/")
        or re.match(r"^[A-Za-z]:/", value)
        or ".." in value.split("/")
        or any(term in folded for term in _PRIVATE_TERMS)
    ):
        raise ValueError(f"{name} violates the public-only dashboard boundary")
    return value


@dataclass(frozen=True, slots=True)
class CanonicalValidationResult:
    """Body-free result supplied by an existing validation owner."""

    validation_id: str
    source_owner: str
    state: str
    reason_codes: tuple[str, ...] = ()
    artifact_ref: str | None = None
    record_sha256: str | None = None

    def __post_init__(self) -> None:
        _public_ref(self.validation_id, "validation_id")
        _public_ref(self.source_owner, "source_owner")
        if self.state not in {"PASS", "FAIL", "UNKNOWN"}:
            raise ValueError("validation state must be PASS, FAIL or UNKNOWN")
        if len(self.reason_codes) > 32 or len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("validation reason_codes must be unique and bounded")
        for reason in self.reason_codes:
            if not isinstance(reason, str) or not _REASON_RE.fullmatch(reason):
                raise ValueError("validation reason code is invalid")
        if self.state == "FAIL" and not self.reason_codes:
            raise ValueError("failed validation requires a reason code")
        if self.artifact_ref is not None:
            _public_ref(self.artifact_ref, "artifact_ref")
        if self.record_sha256 is not None:
            validate_sha256(self.record_sha256, field_name="record_sha256")


@dataclass(frozen=True, slots=True)
class DashboardRow:
    row_id: str
    name_ja: str
    state: DashboardDisplayState
    state_ja: str
    failure_reason_ja: str
    next_action_ja: str
    artifact_location_ja: str
    source_owner: str
    operation_available: bool = False

    @property
    def accessible_label(self) -> str:
        return (
            f"{self.name_ja}。状態: {self.state_ja}。"
            f"失敗理由: {self.failure_reason_ja}。"
            f"次に可能な操作: {self.next_action_ja}。"
            f"成果物場所: {self.artifact_location_ja}。"
        )


@dataclass(frozen=True, slots=True)
class DashboardSection:
    section_id: str
    title_ja: str
    state: DashboardDisplayState
    rows: tuple[DashboardRow, ...]
    note_ja: str


@dataclass(frozen=True, slots=True)
class OperationsDashboardSnapshot:
    project_id: str
    state: DashboardDisplayState
    state_ja: str
    sections: tuple[DashboardSection, ...]
    read_only: bool = True
    auto_repair_available: bool = False
    external_execution_available: bool = False

    def section(self, section_id: str) -> DashboardSection:
        for section in self.sections:
            if section.section_id == section_id:
                return section
        raise KeyError(section_id)


JobReader = Callable[[], DurableProductJobCollection]
AssetReader = Callable[[], Sequence[AssetRecord]]
TimelineReader = Callable[[], InteractiveTimeline | None]
ValidationReader = Callable[[], Sequence[CanonicalValidationResult]]
IntegratedSnapshotReader = Callable[[], IntegratedDashboardSnapshotRevision | None]


@dataclass(frozen=True, slots=True)
class CanonicalOperationState:
    """Exact canonical records required for a no-effect operation-state view."""

    proposal: DashboardOperationProposalRevision
    confirmation: HumanOperationConfirmationBinding | None
    execution_receipt: DashboardExecutionReceiptBinding | None
    evaluated_at: str


OperationStateReader = Callable[[], CanonicalOperationState | None]


@dataclass(frozen=True, slots=True)
class CanonicalDashboardReaders:
    """Injected read ports owned outside TASK-021; no callback may be a writer."""

    read_jobs: JobReader
    read_assets: AssetReader
    read_timeline: TimelineReader
    read_validation_results: ValidationReader
    read_integrated_snapshot: IntegratedSnapshotReader | None = None
    read_operation_state: OperationStateReader | None = None


_JOB_JAPANESE = MappingProxyType({
    DurableProductJobState.QUEUED: (DashboardDisplayState.IN_PROGRESS, "待機中", "なし", "正本Job側で事前確認を開始できます。"),
    DurableProductJobState.PREFLIGHT: (DashboardDisplayState.IN_PROGRESS, "事前確認中", "なし", "事前確認の完了を待ってください。"),
    DurableProductJobState.READY: (DashboardDisplayState.IN_PROGRESS, "実行準備完了", "なし", "個別の人間確認後、正本の実行画面から開始できます。"),
    DurableProductJobState.DISPATCHING: (DashboardDisplayState.IN_PROGRESS, "開始処理中", "なし", "正本Job側の開始結果を待ってください。"),
    DurableProductJobState.RUNNING: (DashboardDisplayState.IN_PROGRESS, "実行中", "なし", "完了するまで待つか、正本Job側で状態を確認してください。"),
    DurableProductJobState.SUCCEEDED: (DashboardDisplayState.SUCCESS, "完了", "なし", "成果物を確認できます。"),
    DurableProductJobState.FAILED: (DashboardDisplayState.FAILURE, "失敗", "正本Jobが失敗しました。", "失敗理由を確認し、正本Job側で再準備してください。"),
    DurableProductJobState.CANCELLED: (DashboardDisplayState.WARNING, "キャンセル済み", "処理はキャンセルされました。", "必要なら正本Job側で新しい処理を準備してください。"),
    DurableProductJobState.UNKNOWN: (DashboardDisplayState.UNKNOWN, "結果不明", "実行結果を確定できません。", "正本Job側で結果を照合してください。"),
    DurableProductJobState.HUMAN_REQUIRED: (DashboardDisplayState.WARNING, "人間の確認待ち", "人間による判断が必要です。", "正本Job側で内容を確認し、明示的に判断してください。"),
})

_ERROR_JAPANESE = MappingProxyType({
    "ERR_PRODUCT_JOB_INPUT_STALE": "入力が更新され、再準備が必要です。",
    "ERR_PRODUCT_JOB_INTERRUPTED": "処理が中断され、結果の照合が必要です。",
})

_INTEGRATED_SNAPSHOT_JAPANESE = MappingProxyType({
    DashboardSnapshotState.ACTION_REQUIRED: (
        DashboardDisplayState.WARNING,
        "対応が必要",
        "正本の運用判定で対応が必要な状態です。",
        "正本のJob、Evidence、Incidentを確認してください。",
    ),
    DashboardSnapshotState.DEGRADED: (
        DashboardDisplayState.IN_PROGRESS,
        "進行中または縮退",
        "処理中または一部機能が縮退しています。",
        "正本側の進行状況と失敗理由を確認してください。",
    ),
    DashboardSnapshotState.NO_ACTIVE_INCIDENT_PROVEN: (
        DashboardDisplayState.SUCCESS,
        "現在のIncidentなし（証明済み）",
        "なし",
        "必要に応じて正本の最新状態を確認できます。",
    ),
    DashboardSnapshotState.STALE: (
        DashboardDisplayState.WARNING,
        "情報が古い",
        "表示元が期限切れ、無効、または更新待ちです。",
        "正本ソースの更新後に再読み取りしてください。",
    ),
    DashboardSnapshotState.UNKNOWN: (
        DashboardDisplayState.UNKNOWN,
        "判定不能",
        "判定に必要な正本情報が不足しています。",
        "正本の確認範囲と検証状態を確認してください。",
    ),
})

_COVERAGE_JAPANESE = MappingProxyType({
    CoverageState.COMPLETE: (
        DashboardDisplayState.SUCCESS,
        "完全",
        "なし",
        "対象範囲は正本スナップショットで確認済みです。",
    ),
    CoverageState.PARTIAL: (
        DashboardDisplayState.WARNING,
        "一部のみ",
        "対象範囲の一部だけが確認済みです。",
        "未確認の正本ソースを確認してください。",
    ),
    CoverageState.UNKNOWN: (
        DashboardDisplayState.UNKNOWN,
        "不明",
        "対象範囲を確定できません。",
        "正本の検索条件と参照元の結び付きを確認してください。",
    ),
})

_OPERATION_KIND_JAPANESE = MappingProxyType({
    "ACK_ALERT": "Alert確認",
    "REQUEST_RECONCILE": "状態照合の依頼",
    "REQUEST_PAUSE": "一時停止の依頼",
    "REQUEST_CANCEL": "キャンセルの依頼",
    "REQUEST_RESUME": "再開の依頼",
    "OPEN_HUMAN_REVIEW": "人間レビューを開く依頼",
    "REQUEST_PRIVATE_DETAIL": "非公開詳細の確認依頼",
})

_OPERATION_REASON_JAPANESE = MappingProxyType({
    "PROPOSAL_NOT_CURRENT": "操作候補が現在有効ではありません。",
    "HUMAN_CONFIRMATION_NOT_BOUND": "人間確認が結び付いていません。",
    "HUMAN_CONFIRMATION_MISMATCH_OR_EXPIRED": "人間確認が不一致または期限切れです。",
    "EXECUTION_RECEIPT_MISMATCH": "外部結果が操作候補または人間確認と一致しません。",
    "EXTERNAL_RESULT_UNKNOWN_NO_REPLAY": "外部結果は不明です。自動再実行できません。",
})


class Task021OperationsDashboard:
    """Refresh a read-only dashboard from canonical in-memory snapshots."""

    def __init__(self, *, project_id: str, readers: CanonicalDashboardReaders) -> None:
        self.project_id = _public_ref(project_id, "project_id")
        if not isinstance(readers, CanonicalDashboardReaders):
            raise TypeError("readers must be CanonicalDashboardReaders")
        self.readers = readers

    def refresh(self) -> OperationsDashboardSnapshot:
        jobs, jobs_error = self._safe_read(self.readers.read_jobs)
        assets, assets_error = self._safe_read(self.readers.read_assets)
        timeline, timeline_error = self._safe_read(self.readers.read_timeline)
        validations, validations_error = self._safe_read(self.readers.read_validation_results)
        integrated_snapshot: object | None = None
        integrated_snapshot_error = False
        if self.readers.read_integrated_snapshot is not None:
            integrated_snapshot, integrated_snapshot_error = self._safe_read(
                self.readers.read_integrated_snapshot
            )
        operation_state: object | None = None
        operation_state_error = False
        if self.readers.read_operation_state is not None:
            operation_state, operation_state_error = self._safe_read(
                self.readers.read_operation_state
            )

        job_collection = jobs if isinstance(jobs, DurableProductJobCollection) else None
        if job_collection is not None and job_collection.project_id != self.project_id:
            jobs_error, job_collection = True, None
        asset_values = self._validated_sequence(assets, AssetRecord)
        if assets is not None and asset_values is None:
            assets_error = True
        validation_values = self._validated_sequence(validations, CanonicalValidationResult)
        if validations is not None and validation_values is None:
            validations_error = True
        if timeline is not None and (
            not isinstance(timeline, InteractiveTimeline) or timeline.project_id != self.project_id
        ):
            timeline_error, timeline = True, None

        if integrated_snapshot is not None and (
            not isinstance(integrated_snapshot, IntegratedDashboardSnapshotRevision)
            or integrated_snapshot.to_dict()["project_id"] != self.project_id
        ):
            integrated_snapshot_error, integrated_snapshot = True, None

        operation_report: dict[str, object] | None = None
        if operation_state is not None:
            if not isinstance(operation_state, CanonicalOperationState):
                operation_state_error, operation_state = True, None
            elif (
                not isinstance(
                    operation_state.proposal, DashboardOperationProposalRevision
                )
                or operation_state.confirmation is not None
                and not isinstance(
                    operation_state.confirmation,
                    HumanOperationConfirmationBinding,
                )
                or operation_state.execution_receipt is not None
                and not isinstance(
                    operation_state.execution_receipt,
                    DashboardExecutionReceiptBinding,
                )
                or not isinstance(operation_state.evaluated_at, str)
            ):
                operation_state_error = True
            elif not isinstance(integrated_snapshot, IntegratedDashboardSnapshotRevision):
                operation_state_error = True
            elif (
                operation_state.proposal.to_dict()["snapshot_sha256"]
                != integrated_snapshot.record_sha256
            ):
                operation_state_error = True
            else:
                try:
                    operation_report = operation_admission_report(
                        proposal=operation_state.proposal,
                        confirmation=operation_state.confirmation,
                        execution_receipt=operation_state.execution_receipt,
                        evaluated_at=operation_state.evaluated_at,
                    )
                except (TypeError, ValueError):
                    operation_state_error = True

        sections = [
            self._jobs_section(job_collection, jobs_error, export_only=False),
            self._assets_section(asset_values, assets_error),
            self._timeline_section(timeline, timeline_error),
            self._jobs_section(job_collection, jobs_error, export_only=True),
            self._validation_section(validation_values, validations_error),
        ]
        if self.readers.read_integrated_snapshot is not None:
            sections.append(
                self._integrated_snapshot_section(
                    integrated_snapshot
                    if isinstance(integrated_snapshot, IntegratedDashboardSnapshotRevision)
                    else None,
                    integrated_snapshot_error,
                )
            )
        if self.readers.read_operation_state is not None:
            sections.append(
                self._operation_state_section(
                    operation_state
                    if isinstance(operation_state, CanonicalOperationState)
                    else None,
                    operation_report,
                    operation_state_error,
                )
            )
        section_values = tuple(sections)
        state = self._aggregate_state(tuple(section.state for section in section_values))
        return OperationsDashboardSnapshot(
            project_id=self.project_id,
            state=state,
            state_ja=_STATE_LABELS[state],
            sections=section_values,
        )

    @staticmethod
    def _safe_read(reader: Callable[[], object]) -> tuple[object | None, bool]:
        if not callable(reader):
            return None, True
        try:
            return reader(), False
        except Exception:
            # Canonical readers may fail, but private paths/bodies from an
            # exception must never become dashboard content.
            return None, True

    @staticmethod
    def _validated_sequence(value: object, kind: type) -> tuple | None:
        if value is None or isinstance(value, (str, bytes)):
            return None
        try:
            result = tuple(value)  # type: ignore[arg-type]
        except TypeError:
            return None
        return result if all(isinstance(item, kind) for item in result) else None

    def _jobs_section(
        self,
        collection: DurableProductJobCollection | None,
        failed: bool,
        *,
        export_only: bool,
    ) -> DashboardSection:
        section_id = "export-queue" if export_only else "jobs"
        title = "Export Queue" if export_only else "Job"
        if failed or collection is None:
            return self._failed_section(section_id, title, "正本Jobを読み取れませんでした。")
        selected = tuple(job for job in collection.jobs if (job.kind == "EXPORT") is export_only)
        rows = tuple(self._job_row(job, export_only=export_only) for job in selected)
        note = (
            "Durable Product Job正本のEXPORT Jobだけを読み取り表示しています。"
            if export_only
            else "Durable Product Job正本を読み取り表示しています。Export Jobは専用欄にも同じ状態を表示します。"
        )
        return self._section(section_id, title, rows, note)

    @staticmethod
    def _job_row(job: DurableProductJob, *, export_only: bool) -> DashboardRow:
        state, label, failure, action = _JOB_JAPANESE[job.state]
        if job.error_code is not None:
            failure = _ERROR_JAPANESE.get(job.error_code, f"正本Jobのエラーコード: {job.error_code}")
        location = job.result_ref or "未生成"
        return DashboardRow(
            row_id=("export-" if export_only else "job-") + job.job_id,
            name_ja=("書き出し" if export_only else "Job") + f" {job.job_id}",
            state=state,
            state_ja=label,
            failure_reason_ja=failure,
            next_action_ja=action,
            artifact_location_ja=location,
            source_owner="TASK-043/DURABLE_PRODUCT_JOB",
        )

    def _assets_section(
        self,
        assets: tuple[AssetRecord, ...] | None,
        failed: bool,
    ) -> DashboardSection:
        if failed or assets is None:
            return self._failed_section("assets", "Asset", "正本Asset一覧を読み取れませんでした。")
        visible = tuple(
            item for item in assets
            if item.asset_type not in _AUDIO_ASSET_TYPES
            and item.retention_class is RetentionClass.STANDARD
        )
        excluded = len(assets) - len(visible)
        rows = tuple(self._asset_row(asset) for asset in sorted(visible, key=lambda item: item.asset_id))
        note = "Asset正本を読み取り表示しています。"
        if excluded:
            note += f" 音声またはprivate media {excluded}件はR0対象外として内容を表示していません。"
        return self._section("assets", "Asset", rows, note)

    @staticmethod
    def _asset_row(asset: AssetRecord) -> DashboardRow:
        if asset.rights_status is RightsStatus.BLOCKED:
            state, label = DashboardDisplayState.FAILURE, "利用不可"
            failure, action = "権利状態がBLOCKEDです。", "正本Asset側で権利情報を確認してください。"
        elif asset.rights_review_required:
            state, label = DashboardDisplayState.WARNING, "権利確認待ち"
            failure, action = "権利または利用条件が未確定です。", "正本Asset側で権利情報を確認してください。"
        elif asset.human_lock:
            state, label = DashboardDisplayState.WARNING, "人間固定中"
            failure, action = "なし", "変更せず、正本Asset側の人間固定を尊重してください。"
        else:
            state, label = DashboardDisplayState.SUCCESS, "利用可能"
            failure, action = "なし", "成果物の参照情報を確認できます。"
        return DashboardRow(
            row_id="asset-" + asset.asset_id,
            name_ja=f"{asset.asset_type.value} Asset {asset.asset_id}",
            state=state,
            state_ja=label,
            failure_reason_ja=failure,
            next_action_ja=action,
            artifact_location_ja=asset.logical_uri,
            source_owner="ASSET_REGISTRY",
        )

    def _timeline_section(
        self,
        timeline: InteractiveTimeline | None,
        failed: bool,
    ) -> DashboardSection:
        if failed:
            return self._failed_section("timeline", "Timeline", "正本Timelineを読み取れませんでした。")
        if timeline is None:
            return self._section(
                "timeline", "Timeline", (), "正本Timelineはまだありません。",
            )
        if timeline.clips:
            state, label = DashboardDisplayState.SUCCESS, "構成あり"
            action = "正本Timelineの編集画面で内容を確認できます。"
        else:
            state, label = DashboardDisplayState.WARNING, "空のTimeline"
            action = "正本Timelineの編集画面でClipを配置してください。"
        row = DashboardRow(
            row_id="timeline-" + timeline.timeline_id,
            name_ja=f"Timeline {timeline.timeline_id}",
            state=state,
            state_ja=label,
            failure_reason_ja="なし",
            next_action_ja=action,
            artifact_location_ja="timeline:" + timeline.timeline_id,
            source_owner="TASK-044/INTERACTIVE_TIMELINE",
        )
        return self._section(
            "timeline",
            "Timeline",
            (row,),
            f"正本TimelineのTrack {len(timeline.tracks)}件、Clip {len(timeline.clips)}件を集計しています。",
        )

    def _validation_section(
        self,
        results: tuple[CanonicalValidationResult, ...] | None,
        failed: bool,
    ) -> DashboardSection:
        if failed or results is None:
            return self._failed_section("validation", "検証結果", "正本の検証結果を読み取れませんでした。")
        rows = tuple(self._validation_row(result) for result in sorted(results, key=lambda item: item.validation_id))
        return self._section(
            "validation", "検証結果", rows, "各検証ownerのbody-free結果を読み取り表示しています。",
        )

    @staticmethod
    def _validation_row(result: CanonicalValidationResult) -> DashboardRow:
        if result.state == "PASS":
            state, label, failure, action = (
                DashboardDisplayState.SUCCESS, "PASS", "なし", "検証成果物を確認できます。",
            )
        elif result.state == "FAIL":
            reasons = "、".join(result.reason_codes)
            state, label, failure, action = (
                DashboardDisplayState.FAILURE,
                "FAIL",
                f"検証理由コード: {reasons}",
                "正本の検証ownerで失敗理由を確認してください。",
            )
        else:
            state, label, failure, action = (
                DashboardDisplayState.UNKNOWN,
                "未確認",
                "検証結果を確定できません。",
                "正本の検証ownerで結果を確認してください。",
            )
        return DashboardRow(
            row_id="validation-" + result.validation_id,
            name_ja=f"検証 {result.validation_id}",
            state=state,
            state_ja=label,
            failure_reason_ja=failure,
            next_action_ja=action,
            artifact_location_ja=result.artifact_ref or "未登録",
            source_owner=result.source_owner,
        )

    @classmethod
    def _section(
        cls,
        section_id: str,
        title: str,
        rows: tuple[DashboardRow, ...],
        note: str,
    ) -> DashboardSection:
        state = cls._aggregate_state(tuple(row.state for row in rows))
        priority = {
            DashboardDisplayState.FAILURE: 0,
            DashboardDisplayState.UNKNOWN: 1,
            DashboardDisplayState.WARNING: 2,
            DashboardDisplayState.IN_PROGRESS: 3,
            DashboardDisplayState.SUCCESS: 4,
            DashboardDisplayState.EMPTY: 5,
        }
        visible = tuple(sorted(rows, key=lambda row: (priority[row.state], row.row_id))[:_MAX_RENDERED_ROWS_PER_SECTION])
        omitted = len(rows) - len(visible)
        if omitted:
            note += f" 優先度の高い200件を表示し、残り{omitted}件は正本画面で確認してください。"
        return DashboardSection(section_id, title, state, visible, note)

    @staticmethod
    def _failed_section(section_id: str, title: str, reason: str) -> DashboardSection:
        row = DashboardRow(
            row_id=section_id + "-read-error",
            name_ja=title,
            state=DashboardDisplayState.FAILURE,
            state_ja="読み取り失敗",
            failure_reason_ja=reason,
            next_action_ja="canonical ownerの状態と接続を確認してください。",
            artifact_location_ja="確認不可",
            source_owner="CANONICAL_OWNER",
        )
        return DashboardSection(section_id, title, DashboardDisplayState.FAILURE, (row,), reason)

    @staticmethod
    def _integrated_snapshot_section(
        snapshot: IntegratedDashboardSnapshotRevision | None,
        failed: bool,
    ) -> DashboardSection:
        section_id = "operations-state"
        title = "運用判定"
        if failed:
            return Task021OperationsDashboard._failed_section(
                section_id,
                title,
                "正本の統合スナップショットを安全に読み取れませんでした。",
            )
        if snapshot is None:
            return DashboardSection(
                section_id,
                title,
                DashboardDisplayState.EMPTY,
                (),
                "正本の統合スナップショットはまだありません。",
            )

        data = snapshot.to_dict()
        snapshot_state = DashboardSnapshotState(data["snapshot_state"])
        coverage_state = CoverageState(data["coverage_state"])
        display_state, state_ja, reason_ja, next_action_ja = (
            _INTEGRATED_SNAPSHOT_JAPANESE[snapshot_state]
        )
        coverage_display, coverage_ja, coverage_reason, coverage_next = (
            _COVERAGE_JAPANESE[coverage_state]
        )
        rows = (
            DashboardRow(
                row_id="integrated-snapshot-state",
                name_ja="統合スナップショット判定",
                state=display_state,
                state_ja=state_ja,
                failure_reason_ja=reason_ja,
                next_action_ja=next_action_ja,
                artifact_location_ja="非表示（公開状態のみ）",
                source_owner="TASK-021_CANONICAL_SNAPSHOT",
            ),
            DashboardRow(
                row_id="integrated-snapshot-coverage",
                name_ja="確認範囲",
                state=coverage_display,
                state_ja=coverage_ja,
                failure_reason_ja=coverage_reason,
                next_action_ja=coverage_next,
                artifact_location_ja="非表示（公開状態のみ）",
                source_owner="TASK-021_CANONICAL_SNAPSHOT",
            ),
        )
        section_state = Task021OperationsDashboard._aggregate_state(
            tuple(row.state for row in rows)
        )
        return DashboardSection(
            section_id,
            title,
            section_state,
            rows,
            "正本スナップショットの公開状態だけを表示します。"
            "識別子、ハッシュ、時刻、非公開情報は表示しません。",
        )

    @staticmethod
    def _operation_state_section(
        operation: CanonicalOperationState | None,
        report: dict[str, object] | None,
        failed: bool,
    ) -> DashboardSection:
        section_id = "operation-gate"
        title = "操作候補と外部結果"
        if failed:
            return Task021OperationsDashboard._failed_section(
                section_id,
                title,
                "正本snapshotに一致する操作状態を安全に読み取れませんでした。",
            )
        if operation is None:
            return DashboardSection(
                section_id,
                title,
                DashboardDisplayState.EMPTY,
                (),
                "正本snapshotに結び付いた操作候補はまだありません。",
            )
        if report is None:
            return Task021OperationsDashboard._failed_section(
                section_id,
                title,
                "操作状態の正本契約を検証できませんでした。",
            )

        proposal = operation.proposal.to_dict()
        gate_decision = str(report["gate_decision"])
        external_state = str(report["external_result_state"])
        reason_codes = tuple(str(value) for value in report["reason_codes"])
        reasons = tuple(
            _OPERATION_REASON_JAPANESE.get(value, "正本の理由コードを確認してください。")
            for value in reason_codes
        )
        reason_ja = " ".join(dict.fromkeys(reasons)) or "なし"

        if gate_decision == "READY_FOR_EXTERNAL_HUMAN_GATE":
            gate_display, gate_label, gate_failure, gate_next = (
                DashboardDisplayState.WARNING,
                "外部Human Gate準備完了",
                "この画面には実行権限がありません。",
                "必要な場合は正本の外部実行画面で改めて確認してください。",
            )
        elif "EXECUTION_RECEIPT_MISMATCH" in reason_codes:
            gate_display, gate_label, gate_failure, gate_next = (
                DashboardDisplayState.UNKNOWN,
                "外部結果照合不能",
                reason_ja,
                "正本の外部結果を照合してください。自動再実行は禁止です。",
            )
        elif gate_decision == "RESULT_RECORDED":
            gate_display, gate_label, gate_failure, gate_next = (
                DashboardDisplayState.SUCCESS,
                "外部結果記録済み",
                reason_ja,
                "正本の外部結果を確認してください。自動再実行は行いません。",
            )
        else:
            gate_display, gate_label, gate_failure, gate_next = (
                DashboardDisplayState.WARNING,
                "ブロック中",
                reason_ja,
                "正本の操作候補と人間確認を確認してください。",
            )

        confirmation = operation.confirmation
        if confirmation is None:
            confirmation_display, confirmation_label, confirmation_failure = (
                DashboardDisplayState.WARNING,
                "人間確認なし",
                "外部実行に必要な人間確認がありません。",
            )
        else:
            confirmation_data = confirmation.to_dict()
            decision = confirmation_data["decision"]
            if decision == "REJECT":
                confirmation_display, confirmation_label, confirmation_failure = (
                    DashboardDisplayState.WARNING,
                    "人間が却下",
                    "人間判断により外部実行できません。",
                )
            elif decision == "REVISE":
                confirmation_display, confirmation_label, confirmation_failure = (
                    DashboardDisplayState.WARNING,
                    "修正依頼",
                    "人間判断により操作候補の修正が必要です。",
                )
            elif "HUMAN_CONFIRMATION_MISMATCH_OR_EXPIRED" in reason_codes:
                confirmation_display, confirmation_label, confirmation_failure = (
                    DashboardDisplayState.WARNING,
                    "再確認が必要",
                    "人間確認が不一致または期限切れです。",
                )
            elif decision == "APPROVE":
                confirmation_display, confirmation_label, confirmation_failure = (
                    DashboardDisplayState.SUCCESS,
                    "人間承認済み",
                    "なし",
                )
            else:
                confirmation_display, confirmation_label, confirmation_failure = (
                    DashboardDisplayState.UNKNOWN,
                    "確認不能",
                    "人間確認の正本状態を確定できません。",
                )

        external_mapping = {
            "NOT_DISPATCHED": (
                DashboardDisplayState.EMPTY,
                "未実行",
                "なし",
                "この画面から外部実行は開始できません。",
            ),
            "ACCEPTED": (
                DashboardDisplayState.SUCCESS,
                "外部で受理済み",
                "なし",
                "正本の永続化済み結果を確認できます。",
            ),
            "REJECTED": (
                DashboardDisplayState.WARNING,
                "外部で拒否",
                "外部ownerが操作を受理しませんでした。",
                "正本の外部結果を確認してください。",
            ),
            "FAILED": (
                DashboardDisplayState.FAILURE,
                "外部で失敗",
                "外部実行が失敗しました。",
                "正本の外部結果を確認し、再実行を自動化しないでください。",
            ),
            "UNKNOWN": (
                DashboardDisplayState.UNKNOWN,
                "外部結果不明",
                "外部実行の結果を確定できません。",
                "正本で照合してください。自動再実行は禁止です。",
            ),
        }
        external_display, external_label, external_failure, external_next = (
            external_mapping.get(external_state, external_mapping["UNKNOWN"])
        )
        public_location = "非表示（公開状態のみ）"
        rows = (
            DashboardRow(
                row_id="operation-gate-decision",
                name_ja=_OPERATION_KIND_JAPANESE.get(
                    str(proposal["operation_kind"]), "正本の操作候補"
                ),
                state=gate_display,
                state_ja=gate_label,
                failure_reason_ja=gate_failure,
                next_action_ja=gate_next,
                artifact_location_ja=public_location,
                source_owner="TASK-021_CANONICAL_OPERATION",
            ),
            DashboardRow(
                row_id="operation-human-confirmation",
                name_ja="人間確認",
                state=confirmation_display,
                state_ja=confirmation_label,
                failure_reason_ja=confirmation_failure,
                next_action_ja="正本のHuman Gateでのみ判断できます。",
                artifact_location_ja=public_location,
                source_owner="TASK-021_CANONICAL_OPERATION",
            ),
            DashboardRow(
                row_id="operation-external-result",
                name_ja="外部結果",
                state=external_display,
                state_ja=external_label,
                failure_reason_ja=external_failure,
                next_action_ja=external_next,
                artifact_location_ja=public_location,
                source_owner="TASK-021_CANONICAL_OPERATION",
            ),
        )
        return DashboardSection(
            section_id,
            title,
            Task021OperationsDashboard._aggregate_state(tuple(row.state for row in rows)),
            rows,
            "正本snapshotに一致する操作候補・人間確認・外部結果の公開状態だけを表示します。"
            "この画面は操作を開始せず、識別子、ハッシュ、時刻、非公開情報を表示しません。",
        )

    @staticmethod
    def _aggregate_state(states: tuple[DashboardDisplayState, ...]) -> DashboardDisplayState:
        if not states or all(state is DashboardDisplayState.EMPTY for state in states):
            return DashboardDisplayState.EMPTY
        for candidate in (
            DashboardDisplayState.FAILURE,
            DashboardDisplayState.UNKNOWN,
            DashboardDisplayState.WARNING,
            DashboardDisplayState.IN_PROGRESS,
            DashboardDisplayState.SUCCESS,
        ):
            if candidate in states:
                return candidate
        return DashboardDisplayState.EMPTY


def render_accessible_dashboard_html(snapshot: OperationsDashboardSnapshot) -> str:
    """Render a semantic, inert fragment suitable for the Product shell."""

    if not isinstance(snapshot, OperationsDashboardSnapshot):
        raise TypeError("snapshot must be OperationsDashboardSnapshot")
    chunks = [
        '<a class="task021-skip-link" href="#task021-dashboard-content">状態一覧へ移動</a>',
        '<main lang="ja" aria-labelledby="task021-dashboard-title">',
        '<h1 id="task021-dashboard-title">統合オペレーション ダッシュボード</h1>',
        f'<p role="status" aria-live="polite">全体状態: {escape(snapshot.state_ja)}</p>',
        '<p>読み取り専用です。外部実行、自動修復、Provider操作は行いません。</p>',
        '<div id="task021-dashboard-content">',
    ]
    for section in snapshot.sections:
        section_id = escape(section.section_id)
        chunks.extend([
            f'<section aria-labelledby="{section_id}-title">',
            f'<h2 id="{section_id}-title">{escape(section.title_ja)}</h2>',
            f'<p>{escape(section.note_ja)}</p>',
        ])
        if not section.rows:
            chunks.append('<p role="status">表示する項目はありません。</p>')
        else:
            chunks.extend([
                '<table>',
                f'<caption>{escape(section.title_ja)}の状態一覧</caption>',
                '<thead><tr><th scope="col">項目</th><th scope="col">状態</th>'
                '<th scope="col">失敗理由</th><th scope="col">次に可能な操作</th>'
                '<th scope="col">成果物場所</th></tr></thead><tbody>',
            ])
            for row in section.rows:
                chunks.append(
                    f'<tr aria-label="{escape(row.accessible_label, quote=True)}" '
                    'data-operation-enabled="false">'
                    f'<th scope="row" translate="no">{escape(row.name_ja)}</th>'
                    f'<td>{escape(row.state_ja)}</td>'
                    f'<td>{escape(row.failure_reason_ja)}</td>'
                    f'<td>{escape(row.next_action_ja)}</td>'
                    f'<td translate="no">{escape(row.artifact_location_ja)}</td></tr>'
                )
            chunks.append('</tbody></table>')
        chunks.append('</section>')
    chunks.append('</div></main>')
    return "".join(chunks)


EFFECT_SURFACE = MappingProxyType({
    "dashboard_store_created": False,
    "canonical_source_mutation": False,
    "job_or_export_execution": False,
    "automatic_repair": False,
    "dashboard_operation_execution": False,
    "provider_or_model_operation": False,
    "private_media_read": False,
    "audio_scope_included": False,
    "release_or_deploy": False,
})


__all__ = [
    "CanonicalDashboardReaders",
    "CanonicalOperationState",
    "CanonicalValidationResult",
    "IntegratedSnapshotReader",
    "OperationStateReader",
    "DashboardDisplayState",
    "DashboardRow",
    "DashboardSection",
    "EFFECT_SURFACE",
    "OperationsDashboardSnapshot",
    "Task021OperationsDashboard",
    "render_accessible_dashboard_html",
]
