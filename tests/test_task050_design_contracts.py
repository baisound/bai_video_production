from ai_video_production.dbd_training_studio_task050_contracts import (
    PERK_SLOT_JA, STAGE_JA, STAGE_ORDER, StudioStage, UserFacingError,
)


def test_stage_order_is_operational_order():
    assert STAGE_ORDER[:5] == (
        StudioStage.INTRO,
        StudioStage.RUNTIME,
        StudioStage.KNOWLEDGE,
        StudioStage.HUD,
        StudioStage.VIDEO,
    )
    assert STAGE_JA[StudioStage.HUD] == "HUD位置を設定"


def test_perk_orientation_labels_are_japanese():
    assert PERK_SLOT_JA[0] == "パーク1（上向き）"
    assert PERK_SLOT_JA[3] == "パーク4（左向き）"


def test_bare_none_dialog_is_forbidden():
    try:
        UserFacingError("ERR_X", "None", "処理できませんでした。", "設定を確認してください。")
    except ValueError:
        return
    raise AssertionError("bare None must be rejected")
