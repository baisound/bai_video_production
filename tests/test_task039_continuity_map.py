from __future__ import annotations

import pytest

from ai_video_production.continuity_map import (
    ContinuityBoundaryType,
    ContinuityEdge,
    ContinuityValidationService,
)
from ai_video_production.errors import ProductError


SHA = "sha256:" + "e" * 64


def edge(boundary: ContinuityBoundaryType) -> ContinuityEdge:
    return ContinuityEdge(
        "edge-1", "scene-1", "end-slot", "candidate-1", "asset-1", SHA,
        "scene-2", "start-slot", boundary,
        ("character-1",), ("space-1",),
    )


def test_direct_continuation_requires_exact_same_asset_identity_and_hash():
    result = ContinuityValidationService.validate_locked_target(
        edge(ContinuityBoundaryType.DIRECT_CONTINUATION),
        target_asset_id="asset-1",
        target_asset_sha256=SHA,
    )
    assert result.status == "PASS"
    assert result.exact_asset_identity_pass is True


def test_direct_continuation_rejects_similar_but_new_asset_identity():
    result = ContinuityValidationService.validate_locked_target(
        edge(ContinuityBoundaryType.DIRECT_CONTINUATION),
        target_asset_id="asset-regenerated",
        target_asset_sha256=SHA,
    )
    assert result.status == "FAIL"
    assert result.reason_code == "DIRECT_CONTINUATION_ASSET_MISMATCH"
    with pytest.raises(ProductError) as exc:
        ContinuityValidationService.require_generation_safe(result)
    assert exc.value.code == "ERR_CONTINUITY_GENERATION_BLOCKED"


def test_soft_continuity_requires_human_inspection_not_exact_hash():
    result = ContinuityValidationService.validate_locked_target(
        edge(ContinuityBoundaryType.SOFT_CONTINUITY),
        target_asset_id="asset-2",
        target_asset_sha256="sha256:" + "f" * 64,
    )
    assert result.status == "HUMAN_REVIEW_REQUIRED"
    assert result.exact_asset_identity_required is False


def test_discontinuous_boundary_does_not_block_generation():
    result = ContinuityValidationService.validate_locked_target(
        edge(ContinuityBoundaryType.DISCONTINUOUS),
        target_asset_id="asset-2",
        target_asset_sha256="sha256:" + "f" * 64,
    )
    ContinuityValidationService.require_generation_safe(result)
    assert result.status == "PASS"
