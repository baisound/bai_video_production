"""TASK-054 R5D read-only Dataset and evaluation Training Studio view model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .dbd_reasoning_blind_human_review import BlindReviewPresentation, admit_blind_review_presentation
from .dbd_reasoning_dataset_leakage import (
    DbDReasoningDatasetLeakageReport, admit_dbd_reasoning_dataset_leakage_report,
)
from .dbd_reasoning_dataset_manifest import (
    DatasetRowDisposition, DatasetSplit, DbDReasoningDatasetRightsManifest,
    admit_dbd_reasoning_dataset_rights_manifest,
)
from .dbd_reasoning_offline_evaluation import (
    DbDReasoningOfflineEvaluationReport, admit_dbd_reasoning_offline_evaluation_report,
)
from .dbd_reasoning_promotion_candidate import (
    DbDReasoningPromotionCandidateReport, admit_dbd_reasoning_promotion_candidate_report,
)


class EvidenceStageStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True, slots=True)
class DatasetSplitView:
    split: DatasetSplit
    total_count: int
    eligible_count: int
    needs_review_count: int
    target_text_visible: bool
    editable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.split, DatasetSplit):
            raise ValueError("split is invalid")
        for name in ("total_count", "eligible_count", "needs_review_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.total_count != self.eligible_count + self.needs_review_count:
            raise ValueError("split counts do not reconcile")
        if self.split is DatasetSplit.TEST and (self.target_text_visible or self.editable):
            raise ValueError("TEST split must remain locked and target-hidden")


@dataclass(frozen=True, slots=True)
class EvaluationArmView:
    arm: str
    status: str
    sample_count: int
    schema_valid_milli: int
    citation_coverage_milli: int
    replay_stability_milli: int
    safe_negative_abstention_milli: int | None
    failure_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.arm or not self.status:
            raise ValueError("evaluation arm identity and status are required")
        if isinstance(self.sample_count, bool) or not isinstance(self.sample_count, int) or self.sample_count < 1:
            raise ValueError("sample_count must be positive")
        for name in (
            "schema_valid_milli", "citation_coverage_milli", "replay_stability_milli",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1000:
                raise ValueError(f"{name} must be between 0 and 1000")
        if (
            self.safe_negative_abstention_milli is not None
            and (
                isinstance(self.safe_negative_abstention_milli, bool)
                or not isinstance(self.safe_negative_abstention_milli, int)
                or not 0 <= self.safe_negative_abstention_milli <= 1000
            )
        ):
            raise ValueError("safe_negative_abstention_milli must be null or between 0 and 1000")
        if not isinstance(self.failure_codes, tuple) or any(not item for item in self.failure_codes):
            raise ValueError("failure_codes must be a tuple of non-empty codes")


@dataclass(frozen=True, slots=True)
class DatasetEvaluationSnapshot:
    manifest_id: str
    manifest_revision: int
    manifest_sha256: str
    splits: tuple[DatasetSplitView, ...]
    leakage_status: str
    leakage_finding_count: int
    evaluation_status: EvidenceStageStatus
    evaluation_arms: tuple[EvaluationArmView, ...]
    blind_review_status: EvidenceStageStatus
    blind_sample_count: int
    promotion_status: str
    adoption_enabled: bool = False
    promotion_enabled: bool = False
    state: str = "READ_ONLY_EVIDENCE_NO_ADOPTION_OR_PROMOTION"

    def __post_init__(self) -> None:
        if not self.manifest_id or self.manifest_revision < 1 or not self.manifest_sha256:
            raise ValueError("manifest identity is invalid")
        if tuple(item.split for item in self.splits) != tuple(DatasetSplit):
            raise ValueError("split views must use canonical order")
        if self.leakage_finding_count < 0 or self.blind_sample_count < 0:
            raise ValueError("evidence counts must be non-negative")
        if self.evaluation_status is EvidenceStageStatus.AVAILABLE and not self.evaluation_arms:
            raise ValueError("available evaluation requires arm views")
        if self.evaluation_status is EvidenceStageStatus.NOT_AVAILABLE and self.evaluation_arms:
            raise ValueError("unavailable evaluation cannot expose arm views")
        if self.blind_review_status is EvidenceStageStatus.AVAILABLE and self.blind_sample_count < 1:
            raise ValueError("available blind review requires samples")
        if self.blind_review_status is EvidenceStageStatus.NOT_AVAILABLE and self.blind_sample_count:
            raise ValueError("unavailable blind review cannot expose samples")
        if self.adoption_enabled or self.promotion_enabled:
            raise ValueError("R5D view cannot grant adoption or promotion")
        if self.state != "READ_ONLY_EVIDENCE_NO_ADOPTION_OR_PROMOTION":
            raise ValueError("R5D state is fixed")


def build_dataset_evaluation_snapshot(
    manifest: DbDReasoningDatasetRightsManifest,
    *,
    leakage_report: DbDReasoningDatasetLeakageReport | None = None,
    offline_report: DbDReasoningOfflineEvaluationReport | None = None,
    blind_presentation: BlindReviewPresentation | None = None,
    promotion_report: DbDReasoningPromotionCandidateReport | None = None,
) -> DatasetEvaluationSnapshot:
    manifest = admit_dbd_reasoning_dataset_rights_manifest(manifest.to_dict())
    manifest_record = manifest.to_dict()
    splits = []
    for split in DatasetSplit:
        entries = tuple(item for item in manifest.entries if item.split is split)
        eligible = sum(item.disposition is DatasetRowDisposition.ELIGIBLE_CANDIDATE for item in entries)
        splits.append(DatasetSplitView(
            split=split, total_count=len(entries), eligible_count=eligible,
            needs_review_count=len(entries) - eligible,
            target_text_visible=False if split is DatasetSplit.TEST else True,
            editable=False if split is DatasetSplit.TEST else True,
        ))

    leakage_status = "NOT_AVAILABLE"
    leakage_findings = 0
    leakage = None
    if leakage_report is not None:
        leakage = admit_dbd_reasoning_dataset_leakage_report(leakage_report.to_dict())
        if leakage.rights_manifest_sha256 != manifest_record["rights_manifest_sha256"]:
            raise ValueError("leakage report crosses Dataset manifest")
        leakage_status = leakage.status.value
        leakage_findings = len(leakage.findings)

    evaluation_status = EvidenceStageStatus.NOT_AVAILABLE
    arm_views: tuple[EvaluationArmView, ...] = ()
    evaluation = None
    if offline_report is not None:
        evaluation = admit_dbd_reasoning_offline_evaluation_report(offline_report.to_dict())
        if evaluation.rights_manifest_sha256 != manifest_record["rights_manifest_sha256"]:
            raise ValueError("evaluation report crosses Dataset manifest")
        if leakage is None or evaluation.leakage_report_sha256 != leakage.to_dict()["report_sha256"]:
            raise ValueError("evaluation report requires the exact leakage report")
        evaluation_status = EvidenceStageStatus.AVAILABLE
        arm_views = tuple(EvaluationArmView(
            arm=item.arm.value, status=item.status.value, sample_count=item.sample_count,
            schema_valid_milli=item.schema_valid_milli,
            citation_coverage_milli=item.citation_coverage_milli,
            replay_stability_milli=item.replay_stability_milli,
            safe_negative_abstention_milli=item.safe_negative_abstention_milli,
            failure_codes=item.failure_codes,
        ) for item in evaluation.evaluations)

    blind_status = EvidenceStageStatus.NOT_AVAILABLE
    blind_count = 0
    presentation = None
    if blind_presentation is not None:
        if evaluation is None:
            raise ValueError("blind review requires an offline evaluation")
        presentation = admit_blind_review_presentation(blind_presentation.to_dict())
        if presentation.offline_evaluation_report_sha256 != evaluation.to_dict()["evaluation_report_sha256"]:
            raise ValueError("blind review crosses offline evaluation")
        if presentation.test_sample_set_sha256 != evaluation.test_sample_set_sha256:
            raise ValueError("blind review crosses TEST sample set")
        blind_status = EvidenceStageStatus.AVAILABLE
        blind_count = len(presentation.samples)

    promotion_status = "NOT_AVAILABLE"
    if promotion_report is not None:
        if evaluation is None or presentation is None:
            raise ValueError("promotion candidate requires evaluation and blind review")
        promotion = admit_dbd_reasoning_promotion_candidate_report(promotion_report.to_dict())
        if (
            promotion.offline_evaluation_report_sha256 != evaluation.to_dict()["evaluation_report_sha256"]
            or promotion.presentation_sha256 != presentation.to_dict()["presentation_sha256"]
            or promotion.test_sample_set_sha256 != evaluation.test_sample_set_sha256
        ):
            raise ValueError("promotion candidate crosses evaluation evidence")
        promotion_status = promotion.status.value

    return DatasetEvaluationSnapshot(
        manifest_id=manifest.manifest_id, manifest_revision=manifest.revision,
        manifest_sha256=manifest_record["rights_manifest_sha256"], splits=tuple(splits),
        leakage_status=leakage_status, leakage_finding_count=leakage_findings,
        evaluation_status=evaluation_status, evaluation_arms=arm_views,
        blind_review_status=blind_status, blind_sample_count=blind_count,
        promotion_status=promotion_status,
    )


__all__ = [
    "DatasetEvaluationSnapshot", "DatasetSplitView", "EvaluationArmView",
    "EvidenceStageStatus", "build_dataset_evaluation_snapshot",
]
