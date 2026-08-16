from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from ai_video_production.task036_shell_ui import HTML as SHELL_HTML
from ai_video_production.task036_shell_v611 import HTML as V611_HTML


ROOT = Path(__file__).resolve().parents[1]
MOCK = (
    ROOT
    / "docs"
    / "ai-team"
    / "product-design"
    / "v6-integration"
    / "BVP-UI-MOCK-V6.1.1.html"
).read_text(encoding="utf-8")


class _SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.pages: set[str] = set()
        self.navigation: set[str] = set()
        self.buttons: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("data-page"):
            self.pages.add(str(values["data-page"]))
        if values.get("data-nav"):
            self.navigation.add(str(values["data-nav"]))
        if tag == "button":
            self.buttons.append(values)


def _surface(value: str) -> _SurfaceParser:
    parser = _SurfaceParser()
    parser.feed(value)
    return parser


def test_runtime_uses_owner_canonical_v611_template() -> None:
    assert SHELL_HTML is V611_HTML
    assert 'data-bvp-ui-contract="V6.1.1"' in SHELL_HTML
    for token in (
        "--bg:#0a0d11",
        "--chrome:#090c10",
        "--panel:#12171d",
        "grid-template-rows:36px 38px 1fr",
        "grid-template-columns:310px minmax(0,1fr) 315px",
    ):
        assert token in SHELL_HTML


def test_runtime_keeps_every_mock_destination_and_top_menu() -> None:
    expected = _surface(MOCK)
    actual = _surface(SHELL_HTML)
    assert actual.pages == expected.pages
    assert expected.pages.issubset(actual.navigation)
    for label in ("ファイル", "編集", "表示", "プロジェクト", "生成", "エクスポート"):
        assert f">{label}</button>" in SHELL_HTML


def test_static_controls_are_bound_or_truthfully_disabled() -> None:
    surface = _surface(SHELL_HTML)
    for button in surface.buttons:
        assert (
            "disabled" in button
            or button.get("id")
            or button.get("data-nav")
            or button.get("data-menu-button")
            or button.get("data-command")
            or button.get("data-settings-view")
            or button.get("data-add-track")
            or button.get("data-lock-kind")
            or button.get("data-asset-kind")
        ), button
        if "disabled" in button:
            # A few context-sensitive Product actions start disabled and are
            # enabled only from an exact snapshot; all fixed unavailable
            # controls must explain their boundary.
            if not button.get("id"):
                assert button.get("data-disabled-reason"), button


def test_runtime_rejects_mock_demo_state_and_fake_progress() -> None:
    for forbidden in (
        "Math.random",
        "setInterval",
        "BAI Promotion 90s",
        "Creator Studio Demo",
        "Tech Stack 03:58",
    ):
        assert forbidden not in SHELL_HTML
    assert "window.pywebview.api" in SHELL_HTML
    assert "replaceChildren" in SHELL_HTML
    assert "innerHTML" not in SHELL_HTML


def test_home_export_and_settings_keep_canonical_information_composition() -> None:
    for label in (
        "最近のプロジェクト",
        "玄人向け",
        "クイック生成を開く",
        "書き出し設定",
        "外部編集",
        "書き出しキュー",
        "DaVinci Resolveへ",
    ):
        assert label in SHELL_HTML
    for settings_label in (
        "一般",
        "プロジェクト",
        "AIモデル",
        "接続 / Secret",
        "制作プロファイル",
        "編集",
        "音声",
        "書き出し",
        "詳細",
    ):
        assert f">{settings_label}</button>" in SHELL_HTML
    assert "Projectの技術的な状態を表示" in SHELL_HTML


def test_home_has_explicit_project_open_action_without_demo_recent_state() -> None:
    assert 'id="homeOpenProjectButton"' in SHELL_HTML
    assert (
        "$('homeOpenProjectButton').addEventListener('click',()=>chooseAndReport('choose_project_folder','プロジェクト'))"
        in SHELL_HTML
    )
    assert "BAI Promotion 90s" not in SHELL_HTML


def test_export_keeps_execute_all_visible_but_fail_closed() -> None:
    assert 'id="runAllExportButton" disabled' in SHELL_HTML
    assert (
        'data-disabled-reason="Export AuthorityはJobごとの個別確認だけを許可します"'
        in SHELL_HTML
    )
    assert ">キュー全て実行</button>" in SHELL_HTML
    assert "blanket Execute All: NO" in SHELL_HTML
    assert "export_queue_dispatch_all" not in SHELL_HTML


def test_existing_product_authority_is_projected_into_mock_surfaces() -> None:
    for method in (
        "planning_snapshot",
        "production_snapshot",
        "audit_snapshot",
        "generation_safety_snapshot",
        "continuity_snapshot",
        "prompt_evidence_snapshot",
        "generation_queue_snapshot",
        "audio_workspace_snapshot",
        "interactive_timeline_snapshot",
        "export_queue_snapshot",
    ):
        assert method in SHELL_HTML
    assert "production_prepare_lock" in SHELL_HTML
    assert "interactive_timeline_select" in SHELL_HTML
    assert "interactive_timeline_seek" in SHELL_HTML
    assert "export_queue_prepare_dispatch" in SHELL_HTML
    assert "generation_queue_dispatch" not in SHELL_HTML


def test_asset_review_binds_exact_task038_human_decision_boundary() -> None:
    for marker in (
        "function renderAssetReview(audit)",
        "function decideAssetReview(audit,candidate,decisionName)",
        "candidate.available_human_actions",
        "audit_prepare_human_decision",
        "expected_production_snapshot_sha256:audit.production_snapshot_sha256",
        "expected_audit_snapshot_sha256:audit.audit_snapshot_sha256",
        "audit_apply_human_decision",
        "confirmation_id:prepared.confirmation_id",
        "actor_id:actor.trim()",
        "AIスコアはHuman Decisionではありません。",
        "LOCK・Provider実行・課金・自動再生成・AIラフ編集・物理削除は開始しません。",
    ):
        assert marker in SHELL_HTML
    assert "renderModel($('assetReviewContent'),audit" not in SHELL_HTML
    assert "buildRoughBtn" not in SHELL_HTML


def test_asset_review_recovery_and_empty_states_fail_closed() -> None:
    assert "if(audit?.recovery?.required)return" in SHELL_HTML
    assert "if(!audit.recovery?.required&&candidate.available_human_actions?.length)" in SHELL_HTML
    assert "既存のProduction Control復旧を完了するまで新しい判断はできません。" in SHELL_HTML
    assert "監査済みCandidateはまだありません。" in SHELL_HTML


def test_planning_projects_real_proposal_and_separates_go_from_install() -> None:
    for marker in (
        'id="planningSummary"',
        "function renderPlanning(model)",
        "function approvePlanning(model,workspace,blueprint)",
        "planning_prepare_go",
        "expected_snapshot_sha256:model.snapshot_sha256",
        "planning_approve_go",
        "approved_by:actor.trim()",
        "function installPlanning(model,workspace)",
        "planning_prepare_install_plan",
        "expected_proposal_snapshot_sha256:model.snapshot_sha256",
        "expected_production_snapshot_sha256:model.installation.production.snapshot_sha256",
        "planning_apply_install_plan",
        "workspace.go_status==='GO_REQUIRED'",
        "workspace.go_status==='APPROVED'&&model.installation.status==='NOT_INSTALLED'",
    ):
        assert marker in SHELL_HTML


def test_planning_does_not_invent_ai_proposal_or_execution_authority() -> None:
    for marker in (
        'data-disabled-reason="AI Proposal生成のtyped Application Serviceが未接続です"',
        "AI Proposal生成は実行しません。",
        "Provider: 未開始 / Paid: 未許可 / Budget reservation: なし / Resolve: 未変更 / Publish: 未開始",
        "if(warnings.length&&!window.confirm",
    ):
        assert marker in SHELL_HTML


def test_scenes_browser_projects_exact_blueprint_without_local_revision() -> None:
    for marker in (
        "function renderScenes(model)",
        "function renderSceneDetail(scene)",
        "const blueprint=model.workspace.blueprint,scenes=blueprint.scenes||[]",
        "button.setAttribute('aria-pressed','false')",
        "renderSceneDetail(scenes[0])",
        "この表示は正本Blueprintのread-only projectionです。",
        "GO: ${model.workspace.go_status}",
        "Slot投入: ${model.installation.status}",
    ):
        assert marker in SHELL_HTML


def test_scenes_mutations_are_visible_but_truthfully_disabled() -> None:
    assert SHELL_HTML.count(
        'data-disabled-reason="Blueprint Scene revisionのtyped Application Serviceが未接続です"'
    ) == 3
    assert (
        'data-disabled-reason="Timeline Contract finalizationのtyped Application Serviceが未接続です"'
        in SHELL_HTML
    )
    assert "Add・Remove・Update・Timeline確定はtyped revision service未接続のため実行できません。" in SHELL_HTML


def test_world_lock_registry_filters_exact_reference_slot_kinds() -> None:
    for marker in (
        'data-lock-kind="CHARACTER_REFERENCE"',
        'data-lock-kind="SPACE_REFERENCE"',
        'data-lock-kind="COMPOSITION_REFERENCE"',
        'id="lockSearch"',
        "function renderLockRegistry(model)",
        "slot.slot_kind===currentLockKind",
        "slot.locked_candidate_id",
        "Official: ${locked?locked.candidate_id+' / '+locked.asset_id+' / '+locked.asset_sha256:'正式LOCKなし'}",
    ):
        assert marker in SHELL_HTML


def test_world_lock_registry_is_read_only_and_does_not_invent_generation() -> None:
    assert "renderLockRegistry(model);renderAssetIndex(model);if(!model?.available)" in SHELL_HTML
    assert "production_register_candidate" not in SHELL_HTML
    assert "production_generate_lock" not in SHELL_HTML
    assert "正式LOCKを確認" in SHELL_HTML
    assert "production_prepare_lock" in SHELL_HTML
    assert "production_apply_lock" in SHELL_HTML


def test_assets_projects_bounded_production_candidate_index() -> None:
    for marker in (
        "Production Candidate Assets",
        'data-asset-kind="ALL"',
        'data-asset-kind="VIDEO"',
        'data-asset-kind="IMAGE"',
        'data-asset-kind="AIVIDEO"',
        'data-asset-kind="NARRATION"',
        'data-asset-kind="SE"',
        'data-asset-kind="BGM"',
        'data-asset-kind="AMBIENCE"',
        "function assetKindMatches(slot,candidate)",
        "function renderAssetIndex(model)",
        "rows.slice(0,500)",
        "candidate.asset_sha256",
        "candidate.generation_job_id",
    ):
        assert marker in SHELL_HTML


def test_assets_does_not_infer_missing_registry_domains() -> None:
    for marker in (
        'data-disabled-reason="Production ControlにSubtitle Asset種別がありません"',
        'data-disabled-reason="Production Control snapshotにTag正本がありません"',
        'data-disabled-reason="Tag正本がないため条件結合は使えません"',
        "Rights/Tag/host pathはこのsnapshotに含まれません。",
    ):
        assert marker in SHELL_HTML
    assert "renderModel($('assetContent')" not in SHELL_HTML


def test_final_review_aggregates_exact_gate_blockers_without_accepting() -> None:
    for marker in (
        'id="finalReviewState"',
        'id="finalApprovalButton" disabled',
        'data-disabled-reason="最終承認のtyped Application Serviceが未接続です"',
        "function renderFinalReview(production,audit)",
        "required=slots.filter(slot=>slot.required)",
        "unlocked=required.filter(slot=>slot.status!=='LOCKED')",
        "stale=slots.filter(slot=>slot.status==='STALE'||slot.stale_state==='STALE')",
        "pending=candidates.filter(candidate=>(candidate.available_human_actions||[]).length>0)",
        "state.textContent='REVIEW_REQUIRED'",
        "集約表示は最終承認を作りません。",
    ):
        assert marker in SHELL_HTML


def test_final_review_routes_to_owning_human_surfaces_only() -> None:
    assert '<button class="btn" data-nav="assetReview">素材確認へ戻る</button>' in SHELL_HTML
    assert '<button class="btn" data-nav="locks">WORLD LOCKへ戻る</button>' in SHELL_HTML
    assert "final_review_apply" not in SHELL_HTML
    assert "final_approve" not in SHELL_HTML


def test_scene_design_reuses_exact_continuity_application_contract() -> None:
    for marker in (
        'id="continuitySummary"',
        "function prepareContinuityEdge(model)",
        "function renderContinuity(model)",
        "continuity_prepare_edge",
        "expected_production_snapshot_sha256:model.production_snapshot_sha256",
        "expected_continuity_snapshot_sha256:model.continuity_snapshot_sha256",
        "continuity_apply_edge",
        "continuity_inspect",
        "continuity_prepare_soft_approval",
        "continuity_apply_soft_approval",
        "continuity_propagate_stale",
        "continuity_apply_recovery",
    ):
        assert marker in SHELL_HTML


def test_scene_design_preserves_human_and_generation_boundaries() -> None:
    for marker in (
        "if(!['DIRECT_CONTINUATION','SOFT_CONTINUITY','DISCONTINUOUS'].includes(boundary))return",
        "Human override for DIRECT: NO",
        "再生成・削除は行いません。",
        "自動再生成は行いません。",
        "if(!model.recovery?.required&&!row.resolution)",
        "if(!model.recovery?.required&&row.human_soft_approval_available)",
    ):
        assert marker in SHELL_HTML
    assert "continuity_generate" not in SHELL_HTML
    assert "continuity_delete" not in SHELL_HTML


def test_start_end_projects_human_approved_shot_feasibility() -> None:
    for marker in (
        'id="generationSafetySummary"',
        "const generationCheckLabels=Object.freeze",
        "function reviewGenerationScene(model,row)",
        "function renderGenerationSafety(model)",
        "if(model.plan_status!=='APPROVED')",
        "generation_safety_prepare_review",
        "expected_planning_snapshot_sha256:model.planning_snapshot_sha256",
        "expected_safety_snapshot_sha256:model.safety_snapshot_sha256",
        "generation_safety_apply_review",
        "reviewed_by:reviewer",
    ):
        assert marker in SHELL_HTML


def test_start_end_feasibility_does_not_gain_execution_authority() -> None:
    for marker in (
        "Provider・課金・Candidate生成は開始しません。",
        "この画面はFEASIBILITYだけを記録します。Provider・課金・Candidate生成・Human ACCEPT・Resolve/Cubase操作は開始しません。",
        "if(!['CUT','DIRECT_CONTINUATION','MATCH_CUT','GRAPHIC_TRANSITION'].includes(continuity))return",
        "if(!['NEW','PREV_END'].includes(startSource))return",
    ):
        assert marker in SHELL_HTML
    assert "generation_safety_execute" not in SHELL_HTML
    assert "generation_safety_accept" not in SHELL_HTML
