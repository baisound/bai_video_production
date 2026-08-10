import http.client
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from ai_video_production import (
    AiConnectionProfile, AiWorkload, CostClass, ModelRoute, ProviderFamily,
    ReasoningEffort, SelectionMode,
)
from ai_video_production.connection_settings_store import ConnectionSettingsEditor
from ai_video_production.connection_settings_web import (
    ConnectionSettingsWebService, launch_server,
)


def profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "screen-test", "1.0.0", SelectionMode.AUTO,
        (
            ModelRoute(
                "openai", AiWorkload.PLANNING, ProviderFamily.OPENAI,
                "openai", "gpt-screen", CostClass.CLOUD_PAID_AI,
                priority=10, reasoning_effort=ReasoningEffort.MEDIUM,
                credential_ref="credential://openai/default",
            ),
            ModelRoute(
                "local", AiWorkload.PLANNING, ProviderFamily.LOCAL_OPEN_SOURCE,
                "local", "local-screen", CostClass.LOCAL_FREE_AI, priority=20,
            ),
        ),
        {
            AiWorkload.VIDEO: SelectionMode.DISABLED,
            AiWorkload.IMAGE: SelectionMode.DISABLED,
            AiWorkload.AUDIO: SelectionMode.DISABLED,
            AiWorkload.MUSIC: SelectionMode.DISABLED,
        },
    )


@pytest.fixture
def live_screen(tmp_path: Path):
    raw = tmp_path / "profile.json"
    raw.write_text(json.dumps(profile().to_dict()), encoding="utf-8")
    settings = tmp_path / "settings.json"
    service = ConnectionSettingsWebService.from_paths(settings, raw)
    server, thread, url = launch_server(service, port=0)
    try:
        yield service, settings, server, url
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _get_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read())


def test_editor_changes_mode_and_preferred_route_without_mutating_input() -> None:
    original = profile()
    modes = {workload.value: SelectionMode.DISABLED.value for workload in AiWorkload}
    modes[AiWorkload.PLANNING.value] = SelectionMode.OFFLINE_ONLY.value
    edited = ConnectionSettingsEditor.apply(
        original,
        workload_modes=modes,
        preferred_route_ids={AiWorkload.PLANNING.value: "local"},
    )
    assert original.mode_for(AiWorkload.PLANNING) is SelectionMode.AUTO
    assert edited.mode_for(AiWorkload.PLANNING) is SelectionMode.OFFLINE_ONLY
    assert next(route for route in edited.routes if route.route_id == "local").priority == 0


def test_editor_rejects_cross_workload_or_incomplete_selections() -> None:
    with pytest.raises(ValueError, match="every workload"):
        ConnectionSettingsEditor.apply(profile(), workload_modes={}, preferred_route_ids={})
    modes = {workload.value: SelectionMode.AUTO.value for workload in AiWorkload}
    with pytest.raises(ValueError, match="does not belong"):
        ConnectionSettingsEditor.apply(
            profile(), workload_modes=modes,
            preferred_route_ids={AiWorkload.VIDEO.value: "local"},
        )


def test_service_rejects_secret_in_credential_ready_argument(tmp_path: Path) -> None:
    raw = tmp_path / "profile.json"
    raw.write_text(json.dumps(profile().to_dict()), encoding="utf-8")
    with pytest.raises(ValueError, match="never secret values"):
        ConnectionSettingsWebService.from_paths(
            tmp_path / "settings.json", raw,
            available_credential_refs=frozenset({"sk-not-a-reference"}),
        )


def test_screen_is_local_bilingual_and_never_exposes_credential_reference(live_screen) -> None:
    _service, _settings, _server, url = live_screen
    with urlopen(url) as response:
        html = response.read().decode("utf-8")
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "AI Connection 設定" in html
    assert "BAI Video Production v0.16.0 —" in html
    assert "Saving here never starts paid APIs" in html
    form = _get_json(url + "api/form")
    serialized = json.dumps(form)
    assert "credential://" not in serialized
    assert form["save_does_not_authorize_generation"] is True


def test_valid_save_persists_modes_and_returns_new_revision(live_screen) -> None:
    _service, settings, _server, url = live_screen
    with urlopen(url) as response:
        html = response.read().decode("utf-8")
    token = json.loads(re.search(r"const CSRF=(\"[^\"]+\")", html).group(1))
    form = _get_json(url + "api/form")
    modes = {item["workload"]: item["selection_mode"] for item in form["workloads"]}
    modes["PLANNING"] = "OFFLINE_ONLY"
    payload = json.dumps({
        "revision": 0,
        "workload_modes": modes,
        "preferred_route_ids": {"PLANNING": "local"},
    }).encode()
    request = Request(
        url + "api/settings", data=payload, method="PUT",
        headers={"Content-Type": "application/json", "X-BAI-CSRF": token},
    )
    with urlopen(request) as response:
        saved = json.loads(response.read())
    assert saved["revision"] == 1
    assert settings.exists()
    planning = next(item for item in saved["workloads"] if item["workload"] == "PLANNING")
    assert planning["preferred_route_id"] == "local"
    assert planning["selected_route_id"] == "local"


def test_catalog_api_adds_candidate_without_execution_or_secret_exposure(live_screen) -> None:
    _service, settings, _server, url = live_screen
    with urlopen(url) as response:
        html = response.read().decode("utf-8")
    token = json.loads(re.search(r"const CSRF=(\"[^\"]+\")", html).group(1))
    entry = {
        "route_id": "runway-video", "workload": "VIDEO",
        "provider_family": "RUNWAY", "provider_id": "runway",
        "model_id": "configured-runway-model", "cost_class": "CLOUD_PAID_AI",
        "reasoning_effort": "none", "capabilities": ["TEXT_TO_VIDEO"],
        "credential_required": True, "enabled": True,
    }
    request = Request(
        url + "api/catalog",
        data=json.dumps({"revision": 0, "entry": entry}).encode(),
        method="PUT",
        headers={"Content-Type": "application/json", "X-BAI-CSRF": token},
    )
    with urlopen(request) as response:
        result = json.loads(response.read())
    assert result["revision"] == 1
    video = next(item for item in result["workloads"] if item["workload"] == "VIDEO")
    added = next(item for item in video["routes"] if item["route_id"] == "runway-video")
    assert added["implementation_status"] == "PLANNED_ADAPTER"
    assert "credential://" not in json.dumps(result)
    assert json.loads(settings.read_text())["profile"]["routes"][-1]["credential_ref"].startswith("credential://")


def test_save_rejects_missing_csrf_and_stale_revision(live_screen) -> None:
    service, _settings, _server, url = live_screen
    form = service.form()
    modes = {item["workload"]: item["selection_mode"] for item in form["workloads"]}
    payload = json.dumps({"revision": 0, "workload_modes": modes, "preferred_route_ids": {}}).encode()
    with pytest.raises(HTTPError) as missing:
        urlopen(Request(url + "api/settings", data=payload, method="PUT", headers={"Content-Type": "application/json"}))
    assert missing.value.code == 403
    service.update({"revision": 0, "workload_modes": modes, "preferred_route_ids": {}})
    with pytest.raises(Exception) as stale:
        service.update({"revision": 0, "workload_modes": modes, "preferred_route_ids": {}})
    assert getattr(stale.value, "code", None) == "ERR_CONNECTION_SETTINGS_CONFLICT"


def test_server_rejects_untrusted_host_header(live_screen) -> None:
    _service, _settings, server, _url = live_screen
    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
    connection.putrequest("GET", "/", skip_host=True)
    connection.putheader("Host", "attacker.example")
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 421
    connection.close()
