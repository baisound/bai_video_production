import pytest

from ai_video_production import (
    AiConnectionProfile, AiProviderExecutionService, AiWorkload, AnthropicMessagesAdapter,
    ConnectionAvailability, CostClass, EnvironmentCredentialStore, GoogleInteractionsAdapter, ModelRoute,
    OpenAiResponsesAdapter, ProductError, ProviderFamily, ReasoningEffort,
    RouteDiagnosticStatus, SelectionMode, TextGenerationRequest, UrllibJsonTransport,
)


class Transport:
    def __init__(self, response): self.response, self.calls = response, []
    def post_json(self, url, *, headers, body, timeout_seconds):
        self.calls.append((url, headers, body, timeout_seconds)); return self.response


class Credentials:
    def __init__(self, values): self.values = values
    def resolve(self, ref): return self.values[ref]


def planning(family, *, route_id="route", reasoning=ReasoningEffort.NONE):
    return ModelRoute(route_id, AiWorkload.PLANNING, family, family.value.lower(), "configured-model", CostClass.CLOUD_PAID_AI, reasoning_effort=reasoning, credential_ref=f"credential://{family.value.lower()}/default", capabilities=("TEXT_GENERATION",))


def test_openai_responses_request_and_result():
    transport = Transport({"id":"req-1","output":[{"content":[{"type":"output_text","text":"proposal"}]}],"usage":{"input_tokens":2,"output_tokens":3}})
    result = OpenAiResponsesAdapter(transport).generate(planning(ProviderFamily.OPENAI, reasoning=ReasoningEffort.MEDIUM), TextGenerationRequest("make", system_instruction="plan"), "secret")
    _, headers, body, _ = transport.calls[0]
    assert result.text == "proposal" and result.input_tokens == 2
    assert headers["Authorization"] == "Bearer secret" and body["reasoning"] == {"effort":"medium"} and body["store"] is False


def test_anthropic_messages_request_and_result():
    transport = Transport({"id":"msg-1","content":[{"type":"text","text":"script"}],"usage":{"input_tokens":4,"output_tokens":5}})
    result = AnthropicMessagesAdapter(transport).generate(planning(ProviderFamily.ANTHROPIC), TextGenerationRequest("make", max_output_tokens=200), "secret")
    _, headers, body, _ = transport.calls[0]
    assert result.text == "script" and result.output_tokens == 5
    assert headers["x-api-key"] == "secret" and body["max_tokens"] == 200


def test_google_interactions_request_and_result():
    transport = Transport({"id":"int-1","output_text":"storyboard"})
    result = GoogleInteractionsAdapter(transport).generate(planning(ProviderFamily.GOOGLE, reasoning=ReasoningEffort.LOW), TextGenerationRequest("make"), "secret")
    _, headers, body, _ = transport.calls[0]
    assert result.text == "storyboard" and headers["x-goog-api-key"] == "secret"
    assert body["generation_config"]["thinking_level"] == "low" and body["store"] is False


def test_service_resolves_route_and_adapter():
    route = planning(ProviderFamily.OPENAI)
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (route,))
    service = AiProviderExecutionService((OpenAiResponsesAdapter(Transport({"output_text":"ok"})),), Credentials({route.credential_ref:"secret"}))
    available = ConnectionAvailability(frozenset({route.route_id}), frozenset({route.credential_ref}))
    assert service.generate_planning_text(profile, available, TextGenerationRequest("make")).text == "ok"


def test_service_requires_capability_and_installed_adapter():
    route = ModelRoute("route", AiWorkload.PLANNING, ProviderFamily.OPENAI, "openai", "m", CostClass.CLOUD_PAID_AI, credential_ref="credential://openai/default")
    profile = AiConnectionProfile("p", "1", SelectionMode.AI, (route,))
    with pytest.raises(ProductError) as exc:
        AiProviderExecutionService((), Credentials({})).generate_planning_text(profile, ConnectionAvailability(frozenset({"route"}), frozenset({route.credential_ref})), TextGenerationRequest("make"))
    assert exc.value.code == "ERR_PROVIDER_ROUTE_UNAVAILABLE"


def test_diagnostics_distinguish_states():
    openai = planning(ProviderFamily.OPENAI, route_id="openai")
    other = planning(ProviderFamily.OTHER, route_id="other")
    disabled = ModelRoute("off", AiWorkload.IMAGE, ProviderFamily.COMFYUI, "comfyui", "wf", CostClass.LOCAL_FREE_AI, enabled=False)
    profile = AiConnectionProfile("p", "1", SelectionMode.AUTO, (openai, other, disabled))
    service = AiProviderExecutionService((OpenAiResponsesAdapter(Transport({})),), Credentials({}))
    rows = {x.route_id:x.status for x in service.diagnose(profile, ConnectionAvailability(frozenset({"openai","other","off"}), frozenset({other.credential_ref})))}
    assert rows == {"openai":RouteDiagnosticStatus.CREDENTIAL_MISSING, "other":RouteDiagnosticStatus.ADAPTER_MISSING, "off":RouteDiagnosticStatus.DISABLED}


def test_empty_text_and_duplicate_adapter_fail_closed():
    with pytest.raises(ProductError):
        OpenAiResponsesAdapter(Transport({"output":[]})).generate(planning(ProviderFamily.OPENAI), TextGenerationRequest("make"), "secret")
    adapter = OpenAiResponsesAdapter(Transport({}))
    with pytest.raises(ValueError, match="duplicate"):
        AiProviderExecutionService((adapter, adapter), Credentials({}))


@pytest.mark.parametrize("prompt", ["", "\x00"])
def test_request_rejects_invalid_prompt(prompt):
    with pytest.raises(ValueError): TextGenerationRequest(prompt)


def test_environment_credential_store_uses_explicit_mapping(monkeypatch):
    monkeypatch.setenv("BAI_OPENAI_KEY", "secret")
    store = EnvironmentCredentialStore({"credential://openai/default":"BAI_OPENAI_KEY"})
    assert store.resolve("credential://openai/default") == "secret"
    with pytest.raises(ProductError): store.resolve("credential://other/default")


def test_http_transport_rejects_non_allowlisted_endpoint_before_network():
    with pytest.raises(ProductError) as exc:
        UrllibJsonTransport().post_json("https://evil.example/v1", headers={}, body={}, timeout_seconds=1)
    assert exc.value.code == "ERR_SECURITY_PROVIDER_ENDPOINT"
