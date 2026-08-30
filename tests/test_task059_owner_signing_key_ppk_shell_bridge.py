from __future__ import annotations

import pytest

from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.task036_shell_ui import HTML, Task036ShellBridge


class ShellServiceStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def snapshot(self):
        self.calls.append(("snapshot", None))
        return {"available": True, "state": "IDLE_NOT_CONFIGURED"}

    def choose_files(self):
        self.calls.append(("choose", None))
        return {"available": True, "state": "FILES_SELECTED_PUBLIC_CANDIDATE"}

    def confirm_public_identity(self, **kwargs):
        self.calls.append(("confirm_public", kwargs))
        return {"available": True, "state": "PUBLIC_IDENTITY_CONFIRMED"}

    def open_native_secret_dialog(self, **kwargs):
        self.calls.append(("open_native", kwargs))
        return {"available": True, "state": "READY_FOR_EXPLICIT_IMPORT"}

    def confirm_ready(self, **kwargs):
        self.calls.append(("confirm_ready", kwargs))
        return {"available": True, "state": "CUSTODIED_READBACK_VERIFIED"}

    def cancel(self, **kwargs):
        self.calls.append(("cancel", kwargs))
        return {"available": True, "state": "IDLE_NOT_CONFIGURED"}


def _bridge(service=None) -> Task036ShellBridge:
    return Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        owner_signing_key_import=service,
    )


def test_shell_bridge_is_body_free_and_fail_closed_when_unbound() -> None:
    snapshot = _bridge().owner_signing_key_import_snapshot({})
    assert snapshot["available"] is False
    assert snapshot["state"] == "UNAVAILABLE_CONFIGURATION"
    assert snapshot["passphrase_exposed"] is False
    assert snapshot["selected_paths_exposed"] is False
    assert snapshot["signing_authorized"] is False
    assert snapshot["deploy_authorized"] is False


def test_shell_bridge_forwards_only_exact_opaque_coordinates() -> None:
    service = ShellServiceStub()
    bridge = _bridge(service)

    bridge.owner_signing_key_import_snapshot({})
    bridge.owner_signing_key_import_choose_files({})
    bridge.owner_signing_key_import_confirm_public_identity({
        "candidate_id": "candidate-1",
        "explicit_human_confirmation": True,
    })
    bridge.owner_signing_key_import_open_native_secret_dialog({
        "candidate_id": "candidate-1",
    })
    bridge.owner_signing_key_import_confirm_ready({
        "attempt_id": "attempt-1",
        "explicit_human_confirmation": True,
    })
    bridge.owner_signing_key_import_cancel({"attempt_id": "attempt-1"})

    assert service.calls == [
        ("snapshot", None),
        ("choose", None),
        (
            "confirm_public",
            {
                "candidate_id": "candidate-1",
                "explicit_human_confirmation": True,
            },
        ),
        ("open_native", {"candidate_id": "candidate-1"}),
        (
            "confirm_ready",
            {
                "attempt_id": "attempt-1",
                "explicit_human_confirmation": True,
            },
        ),
        ("cancel", {"attempt_id": "attempt-1"}),
    ]


@pytest.mark.parametrize(
    ("method", "payload"),
    [
        ("owner_signing_key_import_snapshot", {"secret": True}),
        ("owner_signing_key_import_choose_files", {"path": "C:/secret.ppk"}),
        (
            "owner_signing_key_import_confirm_public_identity",
            {"candidate_id": "candidate-1", "explicit_human_confirmation": False},
        ),
        (
            "owner_signing_key_import_open_native_secret_dialog",
            {"candidate_id": "candidate-1", "passphrase": "forbidden"},
        ),
        (
            "owner_signing_key_import_confirm_ready",
            {"attempt_id": "attempt-1", "explicit_human_confirmation": True, "retry": True},
        ),
        ("owner_signing_key_import_cancel", {"candidate_id": "candidate-1"}),
    ],
)
def test_shell_bridge_rejects_broad_or_nonexplicit_requests(
    method: str, payload: dict[str, object]
) -> None:
    with pytest.raises(ProductError) as error:
        getattr(_bridge(ShellServiceStub()), method)(payload)
    assert error.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_connection_secret_card_has_canonical_safe_operator_route() -> None:
    for method in (
        "owner_signing_key_import_snapshot",
        "owner_signing_key_import_choose_files",
        "owner_signing_key_import_confirm_public_identity",
        "owner_signing_key_import_open_native_secret_dialog",
        "owner_signing_key_import_confirm_ready",
        "owner_signing_key_import_cancel",
    ):
        assert method in HTML
    assert "Owner signing key" in HTML
    assert "PPKと公開鍵を選択" in HTML
    assert "この公開fingerprintを確認" in HTML
    assert "パスフレーズを安全に入力" in HTML
    assert "確認してone-shot取込" in HTML
    assert "正本を再読込" in HTML
    assert "This does not sign, publish, promote, release or deploy." in HTML
    assert "ファイルpath・鍵本文・パスフレーズ・保管先path" in HTML
    assert 'type="password"' not in HTML
    assert "passphrase_utf8" not in HTML
    assert "passphrase:" not in HTML
    assert "currentOwnerSigningKeyImport" in HTML
    assert "ownerSigningKeyImportId(currentOwnerSigningKeyImport)" in HTML
    assert "window.addEventListener('beforeunload'" in HTML
    assert "void cancel({attempt_id:attemptId})" in HTML
