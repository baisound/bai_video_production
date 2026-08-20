from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from ai_video_production.ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily, ReasoningEffort
from ai_video_production.errors import ProductError
from ai_video_production.local_ollama_planning import (
    LOCAL_PLANNING_CANDIDATE_SCHEMA,
    LocalOllamaPlanningAdapter,
    UrllibLocalOllamaTransport,
    parse_local_planning_candidate,
)
import ai_video_production.local_ollama_planning as local_ollama_planning
from ai_video_production.production_blueprint import AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk, ProductionBlueprint, SceneAudioPlan
from ai_video_production.production_proposal import CreationIntent, ProductionProposalRevision, ProposalSection, ProviderPolicyBinding
from ai_video_production.timebase import FrameRate


def route(**changes) -> ModelRoute:
    values = {
        "route_id": "local-planning", "workload": AiWorkload.PLANNING,
        "provider_family": ProviderFamily.LOCAL_OPEN_SOURCE, "provider_id": "ollama",
        "model_id": "qwen3:8b", "cost_class": CostClass.LOCAL_FREE_AI,
        "capabilities": ("TEXT_GENERATION",),
    }
    values.update(changes)
    return ModelRoute(**values)


def candidate() -> dict:
    return {
        "intent": {
            "purpose": "Product intro", "audience": "Creators", "platform": "YouTube",
            "aspect_ratio": "16:9", "target_duration_seconds": 2, "style_tone": "Clear",
            "story_message": "Explain the workflow", "language": "ja-JP", "free_text": "",
            "rights_constraints": [],
        },
        "proposal_title": "Local plan", "timeline_fps": 30,
        "sections": [{"section_id": "concept", "kind": "CONCEPT", "title": "Concept", "body": "A clear introduction"}],
        "scenes": [
            {"scene_id": "SC01", "start_frame": 0, "end_frame": 30, "narrative_role": "Opening", "source_strategy": "AI_GENERATED", "generation_risk": "A_LOW_TEXT", "camera_motion": "SUBTLE", "audio": {"narration": True, "dialogue": False, "sound_effects": [], "bgm": True, "sound_logo": False}, "locked_reference": False, "post_composite_text": False, "final_hold_frames": 0},
            {"scene_id": "SC02", "start_frame": 30, "end_frame": 60, "narrative_role": "Close", "source_strategy": "COMPOSITE", "generation_risk": "B_HEADLINE", "camera_motion": "STATIC", "audio": {"narration": True, "dialogue": False, "sound_effects": ["soft click"], "bgm": True, "sound_logo": False}, "locked_reference": False, "post_composite_text": True, "final_hold_frames": 3},
        ],
        "rights_warnings": [],
    }


class FakeTransport:
    def __init__(self, *, model_present: bool = True, response: bytes | None = None):
        self.model_present, self.response = model_present, response
        self.calls: list[tuple[str, str, bytes | None, float]] = []

    def request(self, method, url, body, timeout):
        self.calls.append((method, url, body, timeout))
        if method == "GET":
            return json.dumps({"models": [{"name": "qwen3:8b"}] if self.model_present else []}).encode()
        return self.response if self.response is not None else json.dumps({"message": {"content": json.dumps(candidate())}}).encode()


def test_fixed_loopback_model_admission_and_exact_structured_schema_body():
    transport = FakeTransport()
    adapter = LocalOllamaPlanningAdapter(route(), transport)
    assert adapter.ready() is True
    result = adapter.generate("30秒の企画を提案")
    assert result.intent.purpose == "Product intro"
    assert [item.scene_id for item in result.scenes] == ["SC01", "SC02"]
    assert [call[:2] for call in transport.calls] == [
        ("GET", "http://127.0.0.1:11434/api/tags"),
        ("GET", "http://127.0.0.1:11434/api/tags"),
        ("POST", "http://127.0.0.1:11434/api/chat"),
    ]
    body = json.loads(transport.calls[-1][2])
    assert body["format"] == LOCAL_PLANNING_CANDIDATE_SCHEMA
    assert body["stream"] is False and body["think"] is False
    assert body["options"] == {"temperature": 0, "num_predict": 8192}
    schema_text = json.dumps(LOCAL_PLANNING_CANDIDATE_SCHEMA, ensure_ascii=False, separators=(",", ":"))
    assert schema_text in body["messages"][0]["content"]
    assert "target_duration_seconds * timeline_fps" in body["messages"][0]["content"]


def test_missing_model_never_posts_or_downloads():
    transport = FakeTransport(model_present=False)
    adapter = LocalOllamaPlanningAdapter(route(), transport)
    assert adapter.ready() is False
    with pytest.raises(ProductError) as exc:
        adapter.generate("plan")
    assert exc.value.code == "ERR_LOCAL_OLLAMA_MODEL_MISSING"
    assert all(call[0] == "GET" for call in transport.calls)


@pytest.mark.parametrize("changes", [
    {"workload": AiWorkload.VIDEO}, {"provider_family": ProviderFamily.OPENAI},
    {"provider_id": "other"}, {"cost_class": CostClass.CLOUD_PAID_AI},
    {"capabilities": ()}, {"capabilities": ("TEXT_GENERATION", "IGNORED")},
    {"reasoning_effort": ReasoningEffort.HIGH}, {"credential_ref": "credential://local/test"},
    {"endpoint_ref": "endpoint://local/ollama"}, {"settings": {"temperature": 0}}, {"enabled": False},
])
def test_ineligible_routes_fail_before_transport(changes):
    with pytest.raises(ProductError) as exc:
        LocalOllamaPlanningAdapter(route(**changes), FakeTransport())
    assert exc.value.code == "ERR_LOCAL_OLLAMA_ROUTE_INELIGIBLE"


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(extra=True), lambda x: x["intent"].update(extra=True),
    lambda x: x["sections"][0].update(extra=True), lambda x: x["scenes"][0]["audio"].update(extra=True),
    lambda x: x["intent"].update(aspect_ratio="21:9"), lambda x: x["scenes"][0].update(source_strategy="UNKNOWN"),
    lambda x: x["scenes"][0].update(start_frame=1), lambda x: x["scenes"][1].update(end_frame=59),
    lambda x: x["scenes"][1].update(scene_id="SC01"), lambda x: x["sections"].append(dict(x["sections"][0])),
    lambda x: x["intent"].update(purpose="bad\x00value"), lambda x: x["intent"].update(free_text="\ud800"),
    lambda x: x["intent"].update(free_text=r"C:\\private\\source.mov"), lambda x: x["sections"][0].update(body="/tmp/private.mov"),
    lambda x: x["scenes"][0].update(narrative_role="../private.mov"), lambda x: x.update(rights_warnings=["~/private.mov"]),
    lambda x: x["sections"][0].update(body="path=/tmp/private.mov"), lambda x: x["sections"][0].update(body="asset=(/tmp/private.mov)"),
    lambda x: x["sections"][0].update(body="./private.mov"),
    lambda x: x["intent"].update(story_message="C:private.mov"),
    lambda x: x["scenes"][0].update(generation_risk="C_DENSE_UI"),
])
def test_closed_candidate_rejects_recursive_unknowns_enums_continuity_and_bounds(mutation):
    value = candidate()
    mutation(value)
    with pytest.raises(ValueError):
        parse_local_planning_candidate(value)


@pytest.mark.parametrize("response", [b"", b"{", b"\xff", b"[]", b"{}", b'{"message":{"content":1}}', b'{"message":{"content":"not-json"}}'])
def test_invalid_provider_envelopes_and_candidate_fail_closed(response):
    adapter = LocalOllamaPlanningAdapter(route(), FakeTransport(response=response))
    with pytest.raises(ProductError):
        adapter.generate("plan")


def test_prompt_and_response_size_bounds_are_fail_closed():
    adapter = LocalOllamaPlanningAdapter(route(), FakeTransport())
    with pytest.raises(ProductError) as exc:
        adapter.generate("x" * (16 * 1024 + 1))
    assert exc.value.code == "ERR_LOCAL_OLLAMA_PROMPT_INVALID"
    with pytest.raises(ProductError):
        LocalOllamaPlanningAdapter(route(), FakeTransport(response=b"{" + b" " * (256 * 1024))).generate("plan")
    with pytest.raises(ProductError) as exc:
        adapter.generate("\ud800")
    assert exc.value.code == "ERR_LOCAL_OLLAMA_PROMPT_INVALID"
    surrogate = json.dumps({"message": {"content": "\ud800"}}).encode()
    with pytest.raises(ProductError) as exc:
        LocalOllamaPlanningAdapter(route(), FakeTransport(response=surrogate)).generate("plan")
    assert exc.value.code == "ERR_LOCAL_OLLAMA_RESPONSE_INVALID"


@pytest.mark.parametrize("method,url,body", [
    ("GET", "http://localhost:11434/api/tags", None),
    ("GET", "http://127.0.0.1:11434/api/chat", None),
    ("POST", "https://127.0.0.1:11434/api/chat", b"{}"),
])
def test_production_transport_rejects_every_non_exact_endpoint(method, url, body):
    with pytest.raises(ProductError) as exc:
        UrllibLocalOllamaTransport().request(method, url, body, 1)
    assert exc.value.code == "ERR_LOCAL_OLLAMA_ENDPOINT_FORBIDDEN"


def test_production_transport_disables_all_proxies_and_redirects():
    transport = UrllibLocalOllamaTransport()
    proxy_handlers = [item for item in transport._opener.handlers if hasattr(item, "proxies")]
    # Passing ProxyHandler({}) suppresses build_opener's default environment
    # proxy handler; CPython omits the empty handler from the final list.
    assert proxy_handlers == []
    redirect_handlers = [item for item in transport._opener.handlers if item.__class__.__name__ == "_NoRedirect"]
    assert len(redirect_handlers) == 1
    assert redirect_handlers[0].redirect_request(None, None, 302, "Found", {}, "https://example.invalid/") is None


def test_proxy_environment_is_bypassed_and_redirect_target_is_never_called(monkeypatch):
    direct_hits: list[str] = []
    trap_hits: list[str] = []

    class DirectHandler(BaseHTTPRequestHandler):
        redirect = False

        def do_GET(self):
            direct_hits.append(self.path)
            if self.redirect:
                self.send_response(302)
                self.send_header("Location", trap_url)
                self.end_headers()
            else:
                body = b'{"models":[]}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, *_):
            pass

    class TrapHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            trap_hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_):
            pass

    direct = ThreadingHTTPServer(("127.0.0.1", 0), DirectHandler)
    trap = ThreadingHTTPServer(("127.0.0.1", 0), TrapHandler)
    direct_url = f"http://127.0.0.1:{direct.server_port}/api/tags"
    trap_url = f"http://127.0.0.1:{trap.server_port}/trap"
    threads = [Thread(target=server.serve_forever, daemon=True) for server in (direct, trap)]
    for thread in threads:
        thread.start()
    try:
        monkeypatch.setenv("HTTP_PROXY", trap_url)
        monkeypatch.setenv("http_proxy", trap_url)
        monkeypatch.delenv("NO_PROXY", raising=False)
        monkeypatch.delenv("no_proxy", raising=False)
        monkeypatch.setattr(local_ollama_planning, "_TAGS_URL", direct_url)
        assert UrllibLocalOllamaTransport().request("GET", direct_url, None, 2) == b'{"models":[]}'
        assert direct_hits == ["/api/tags"] and trap_hits == []
        DirectHandler.redirect = True
        with pytest.raises(ProductError) as exc:
            UrllibLocalOllamaTransport().request("GET", direct_url, None, 2)
        assert exc.value.code == "ERR_LOCAL_OLLAMA_HTTP"
        assert exc.value.details == {"status": 302}
        assert trap_hits == []
    finally:
        for server in (direct, trap):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


@pytest.mark.parametrize("method,url,body", [
    ("GET", "http://127.0.0.1:11434/api/tags", b"{}"),
    ("POST", "http://127.0.0.1:11434/api/chat", None),
    ("POST", "http://127.0.0.1:11434/api/chat", b""),
    ("POST", "http://127.0.0.1:11434/api/chat", b"x" * (512 * 1024 + 1)),
])
def test_production_transport_rejects_invalid_method_body_combinations(method, url, body):
    with pytest.raises(ProductError) as exc:
        UrllibLocalOllamaTransport().request(method, url, body, 1)
    assert exc.value.code == "ERR_LOCAL_OLLAMA_REQUEST_INVALID"


@pytest.mark.parametrize("inventory", [{}, {"models": {}}, {"models": [1]}, {"models": [{}]}, {"models": [{"name": 1}]}])
def test_malformed_model_inventory_is_not_reported_as_model_missing(inventory):
    transport = FakeTransport(response=None)
    transport.request = lambda *_: json.dumps(inventory).encode()
    with pytest.raises(ProductError) as exc:
        LocalOllamaPlanningAdapter(route(), transport).ready()
    assert exc.value.code == "ERR_LOCAL_OLLAMA_RESPONSE_INVALID"


def test_candidate_constructs_all_existing_task027_v1_types_without_persistence():
    value = parse_local_planning_candidate(candidate())
    intent = CreationIntent(
        "INTENT-LOCAL-0001", 1, value.intent.purpose, value.intent.audience,
        value.intent.platform, value.intent.aspect_ratio, value.intent.target_duration_seconds,
        value.intent.style_tone, value.intent.story_message, value.intent.language,
        value.intent.free_text, currency="JPY", rights_constraints=value.intent.rights_constraints,
    )
    scenes = tuple(BlueprintScene(
        item.scene_id, item.start_frame, item.end_frame, item.narrative_role,
        AssetSourceStrategy(item.source_strategy), GenerationRisk(item.generation_risk),
        CameraMotion(item.camera_motion), (),
        SceneAudioPlan(item.narration, item.dialogue, item.sound_effects, item.bgm, item.sound_logo),
        item.locked_reference, item.post_composite_text, item.final_hold_frames,
    ) for item in value.scenes)
    blueprint = ProductionBlueprint("BP-LOCAL-0001", value.proposal_title, FrameRate(value.timeline_fps), value.intent.target_duration_seconds * value.timeline_fps, (), scenes)
    proposal = ProductionProposalRevision(
        "PROPOSAL-LOCAL-0001", 1, intent.to_dict()["intent_sha256"], blueprint,
        tuple(ProposalSection(item.section_id, item.kind, item.title, item.body) for item in value.sections),
        ProviderPolicyBinding("task036-local-planning", "1.0.0", "sha256:" + "0" * 64),
        currency="JPY", rights_warnings=value.rights_warnings,
    )
    assert proposal.estimated_cost_min == proposal.estimated_cost_max == 0
    assert proposal.blueprint.to_dict()["target_duration_frames"] == 60
