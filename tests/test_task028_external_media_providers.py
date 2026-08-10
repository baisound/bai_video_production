import pytest

from ai_video_production import (
    AiWorkload, BinaryResponse, CostClass, ElevenLabsMediaAdapter,
    ElevenLabsMusicRequest, ElevenLabsSoundEffectRequest, ElevenLabsTtsRequest,
    ModelRoute, ProductError, ProviderFamily, ProviderIntegrationStatus,
    SunoApiMusicAdapter, SunoMusicRequest, UrllibBinaryTransport,
    builtin_media_provider_catalog,
)


AUTH = "authorization://owner/external-generation"


class BinaryTransport:
    def __init__(self): self.calls = []
    def post_binary(self, url, *, headers, body, timeout_seconds):
        self.calls.append((url, headers, body, timeout_seconds)); return BinaryResponse(b"media", "audio/mpeg", "req-1")


class JsonTransport:
    def __init__(self, response): self.response, self.calls = response, []
    def post_json(self, url, *, headers, body, timeout_seconds):
        self.calls.append((url, headers, body, timeout_seconds)); return self.response


def route(route_id, workload, family, capability, model="configured-model"):
    return ModelRoute(route_id, workload, family, family.value.lower(), model, CostClass.CLOUD_PAID_AI, credential_ref=f"credential://{family.value.lower()}/default", capabilities=(capability,))


def test_elevenlabs_tts_uses_voice_model_and_runtime_credential():
    transport = BinaryTransport(); adapter = ElevenLabsMediaAdapter(transport)
    result = adapter.text_to_speech(route("tts", AiWorkload.AUDIO, ProviderFamily.ELEVENLABS, "TTS", "eleven_multilingual_v2"), ElevenLabsTtsRequest("hello", "voice-1", AUTH), "secret")
    url, headers, body, _ = transport.calls[0]
    assert result.data == b"media" and "/text-to-speech/voice-1" in url
    assert headers["xi-api-key"] == "secret" and body["model_id"] == "eleven_multilingual_v2"


def test_elevenlabs_sound_effect_bounds_duration_and_loop():
    transport = BinaryTransport(); adapter = ElevenLabsMediaAdapter(transport)
    request = ElevenLabsSoundEffectRequest("door slam", AUTH, duration_seconds=2.5, loop=True)
    adapter.sound_effect(route("sfx", AiWorkload.AUDIO, ProviderFamily.ELEVENLABS, "SFX"), request, "secret")
    assert transport.calls[0][2]["duration_seconds"] == 2.5 and transport.calls[0][2]["loop"] is True
    with pytest.raises(ValueError): ElevenLabsSoundEffectRequest("x", AUTH, duration_seconds=31)


def test_elevenlabs_music_uses_configured_model_and_duration():
    transport = BinaryTransport(); adapter = ElevenLabsMediaAdapter(transport)
    adapter.music(route("music", AiWorkload.MUSIC, ProviderFamily.ELEVENLABS, "MUSIC_GENERATION", "music_v2"), ElevenLabsMusicRequest("cinematic", AUTH, duration_ms=60000), "secret")
    _, _, body, _ = transport.calls[0]
    assert body["model_id"] == "music_v2" and body["music_length_ms"] == 60000 and body["force_instrumental"] is True


def test_suno_submit_normalizes_async_task():
    transport = JsonTransport({"code":200,"msg":"success","data":{"taskId":"task-1"}})
    request = SunoMusicRequest("calm piano", "Title", "Classical", "https://owner.example/callback", AUTH, duration_seconds=60)
    job = SunoApiMusicAdapter(transport).submit(route("suno", AiWorkload.MUSIC, ProviderFamily.SUNO_API, "MUSIC_GENERATION", "V5"), request, "secret")
    _, headers, body, _ = transport.calls[0]
    assert job.provider_task_id == "task-1" and job.state == "SUBMITTED"
    assert headers["Authorization"] == "Bearer secret" and body["model"] == "V5" and body["duration"] == 60


def test_suno_invalid_response_and_callback_fail_closed():
    with pytest.raises(ValueError): SunoMusicRequest("x", "t", "s", "http://localhost/callback", AUTH)
    request = SunoMusicRequest("x", "t", "s", "https://owner.example/callback", AUTH)
    with pytest.raises(ProductError):
        SunoApiMusicAdapter(JsonTransport({"code":500})).submit(route("suno", AiWorkload.MUSIC, ProviderFamily.SUNO_API, "MUSIC_GENERATION"), request, "secret")


def test_route_capability_mismatch_fails_before_transport():
    transport = BinaryTransport()
    bad = route("bad", AiWorkload.AUDIO, ProviderFamily.ELEVENLABS, "DENOISE")
    with pytest.raises(ProductError) as exc:
        ElevenLabsMediaAdapter(transport).text_to_speech(bad, ElevenLabsTtsRequest("x", "voice", AUTH), "secret")
    assert exc.value.code == "ERR_PROVIDER_ROUTE_INCOMPATIBLE" and transport.calls == []


def test_rights_authorization_is_required():
    with pytest.raises(ValueError): ElevenLabsMusicRequest("x", "")


def test_binary_transport_rejects_unreviewed_origin_before_network():
    with pytest.raises(ProductError) as exc:
        UrllibBinaryTransport().post_binary("https://evil.example/v1/music", headers={}, body={}, timeout_seconds=1)
    assert exc.value.code == "ERR_SECURITY_MEDIA_PROVIDER_ENDPOINT"


def test_catalog_exposes_implemented_and_planned_major_providers():
    catalog = {entry.family:entry for entry in builtin_media_provider_catalog()}
    assert catalog[ProviderFamily.ELEVENLABS].status is ProviderIntegrationStatus.IMPLEMENTED
    assert catalog[ProviderFamily.SUNO_API].status is ProviderIntegrationStatus.IMPLEMENTED
    for family in (ProviderFamily.RUNWAY, ProviderFamily.LUMA, ProviderFamily.STABILITY_AI, ProviderFamily.REPLICATE, ProviderFamily.FAL_AI, ProviderFamily.MINIMAX, ProviderFamily.KLING):
        assert family in catalog
