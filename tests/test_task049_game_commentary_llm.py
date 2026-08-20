import json
from types import SimpleNamespace
import pytest
from ai_video_production.game_commentary import CommentaryClaimKind, CommentaryDisposition, CommentaryFact, CommentaryPlan
from ai_video_production.game_commentary_llm import CommentaryLlmService
from ai_video_production.ids import IdKind, generate_id

class FakeProvider:
    def generate_planning_text(self, profile, availability, request):
        fact=json.loads(request.prompt)['allowed_facts'][0]
        return SimpleNamespace(text=json.dumps({'text':fact['value'],'claims':[fact]},ensure_ascii=False),provider_id='fake',model_id='fake-model',provider_request_id='req',route_id='r')


def _plan():
    return CommentaryPlan(generate_id(IdKind.GAME_MATCH),generate_id(IdKind.GAME_EVENT),1,'ja-JP',CommentaryDisposition.PROPOSE,800,(),(CommentaryFact(CommentaryClaimKind.EVENT_OCCURRED,'event.type','HOOK'),),(),())


def test_llm_requires_explicit_execution_authority():
    with pytest.raises(PermissionError): CommentaryLlmService(FakeProvider()).draft(plan=_plan(), profile=object(), availability=object(), execution_authorized=False)


def test_llm_output_is_fact_validated():
    candidate=CommentaryLlmService(FakeProvider()).draft(plan=_plan(), profile=object(), availability=object(), execution_authorized=True)
    assert candidate.validation.passed
    assert candidate.status.value == 'VALIDATED'
