import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

import pytest

from ai_video_production import (
    AiConnectionProfile, AiWorkload, CostClass, ModelRoute, ProviderFamily,
    SelectionMode,
)
from ai_video_production.credential_vault import (
    CRED_MAX_CREDENTIAL_BLOB_SIZE, WindowsCredentialManagerStore, credential_target,
)
from ai_video_production.connection_settings_web import ConnectionSettingsWebService, launch_server
from ai_video_production.errors import ProductError


class FakeBackend:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def write(self, target: str, blob: bytes) -> None:
        self.values[target] = blob

    def read(self, target: str) -> bytes | None:
        return self.values.get(target)

    def delete(self, target: str) -> bool:
        return self.values.pop(target, None) is not None


def _profile() -> AiConnectionProfile:
    return AiConnectionProfile(
        "vault-test", "1.0.0", SelectionMode.AUTO,
        (
            ModelRoute(
                "paid", AiWorkload.PLANNING, ProviderFamily.OPENAI,
                "openai", "configured-model", CostClass.CLOUD_PAID_AI,
                credential_ref="credential://openai/default",
            ),
            ModelRoute(
                "local", AiWorkload.VIDEO, ProviderFamily.LOCAL_OPEN_SOURCE,
                "local", "configured-local", CostClass.LOCAL_FREE_AI,
            ),
        ),
    )


def _service(tmp_path: Path, vault: WindowsCredentialManagerStore) -> ConnectionSettingsWebService:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(_profile().to_dict()), encoding="utf-8")
    return ConnectionSettingsWebService.from_paths(
        tmp_path / "settings.json", profile_path, credential_vault=vault,
    )


def test_vault_round_trip_uses_opaque_target_and_never_returns_secret_metadata() -> None:
    backend = FakeBackend()
    vault = WindowsCredentialManagerStore(backend)
    ref, secret = "credential://openai/default", "sk-test-private"
    vault.write(ref, secret)
    target = next(iter(backend.values))
    assert target == credential_target(ref)
    assert ref not in target
    assert secret not in target
    assert vault.contains(ref)
    assert vault.resolve(ref) == secret
    assert vault.delete(ref) is True
    assert vault.delete(ref) is False


@pytest.mark.parametrize("secret", ["", "   ", "bad\x00value"])
def test_vault_rejects_invalid_secrets(secret: str) -> None:
    with pytest.raises(ValueError):
        WindowsCredentialManagerStore(FakeBackend()).write("credential://openai/default", secret)


def test_vault_enforces_windows_blob_limit() -> None:
    vault = WindowsCredentialManagerStore(FakeBackend())
    vault.write("credential://openai/default", "a" * CRED_MAX_CREDENTIAL_BLOB_SIZE)
    with pytest.raises(ValueError, match="size limit"):
        vault.write("credential://openai/default", "a" * (CRED_MAX_CREDENTIAL_BLOB_SIZE + 1))


def test_service_saves_status_only_and_does_not_persist_secret(tmp_path: Path) -> None:
    secret = "never-write-this-secret"
    backend = FakeBackend()
    service = _service(tmp_path, WindowsCredentialManagerStore(backend))
    result = service.save_credential({"route_id": "paid", "secret": secret})
    serialized = json.dumps(result)
    assert result["provider_call_started"] is False
    assert result["credential_configured"] is True
    assert secret not in serialized
    assert "credential://" not in serialized
    paid = result["form"]["workloads"][0]["routes"][0]
    assert paid["credential_configured"] is True
    assert not (tmp_path / "settings.json").exists()
    deleted = service.delete_credential({"route_id": "paid"})
    assert deleted["deleted"] is True
    assert deleted["provider_call_started"] is False


def test_service_rejects_unknown_or_noncredential_route(tmp_path: Path) -> None:
    service = _service(tmp_path, WindowsCredentialManagerStore(FakeBackend()))
    for route_id in ("missing", "local"):
        with pytest.raises(ValueError, match="does not require"):
            service.save_credential({"route_id": route_id, "secret": "value"})


def test_native_vault_fails_closed_outside_windows() -> None:
    if os.name == "nt":
        pytest.skip("non-Windows contract")
    with pytest.raises(ProductError) as error:
        WindowsCredentialManagerStore()
    assert error.value.code == "ERR_CREDENTIAL_VAULT_UNSUPPORTED"


def test_http_credential_round_trip_never_echoes_secret(tmp_path: Path) -> None:
    secret = "http-secret-must-not-echo"
    service = _service(tmp_path, WindowsCredentialManagerStore(FakeBackend()))
    server, thread, url = launch_server(service, port=0)
    try:
        with urlopen(url) as response:
            html = response.read().decode("utf-8")
        token = json.loads(re.search(r'const CSRF=("[^"]+")', html).group(1))
        request = Request(
            url + "api/credentials",
            data=json.dumps({"route_id": "paid", "secret": secret}).encode(),
            method="PUT",
            headers={"Content-Type": "application/json", "X-BAI-CSRF": token},
        )
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
        assert secret not in body
        assert "credential://" not in body
        assert json.loads(body)["provider_call_started"] is False
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
