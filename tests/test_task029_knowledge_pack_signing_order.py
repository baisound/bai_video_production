from dataclasses import replace

import pytest

from ai_video_production.knowledge_pack_signing import compile_knowledge_pack_signing_candidate
from test_task029_knowledge_pack_signing import bundle


def test_critic_review_must_follow_human_review(tmp_path) -> None:
    _, human, critic, kwargs = bundle(tmp_path)
    stale_critic = replace(critic, reviewed_at_epoch_ms=human.reviewed_at_epoch_ms)
    with pytest.raises(ValueError, match="Critic review must occur after"):
        compile_knowledge_pack_signing_candidate(
            **(kwargs | {"critic_review": stale_critic})
        )
