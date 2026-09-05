from __future__ import annotations

import json
from pathlib import Path

import pytest

import ai_video_production.montage_learning_file_bridge as file_bridge
from ai_video_production.montage_learning_file_bridge import (
    BridgeLayout,
    MontageLearningFileBridgeError,
    load_bridge_owner,
    load_published_receipt,
    provision_bridge,
    receipt_publication_paths,
)
from ai_video_production.secure_authority_io import SecureAuthorityIO


def _layout(tmp_path: Path) -> BridgeLayout:
    layout = BridgeLayout.for_isolated_test(tmp_path / "bridge")
    provision_bridge(layout, bridge_instance_id="task069-bridge-fixture")
    return layout


def test_task069_owner_read_rejects_same_bytes_inode_swap_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _layout(tmp_path)
    original = layout.owner_manifest.read_bytes()
    replacement = layout.root / "owner-replacement.json"
    replaced = False

    def hook(stage: str) -> None:
        nonlocal replaced
        if stage == "target_lstat_complete" and not replaced:
            replacement.write_bytes(original)
            replacement.replace(layout.owner_manifest)
            replaced = True

    class HookedAuthority(SecureAuthorityIO):
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            kwargs["_stage_hook"] = hook
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(file_bridge, "SecureAuthorityIO", HookedAuthority)

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        load_bridge_owner(layout)

    assert replaced is True
    assert str(exc.value) in {
        "secure bridge read rejected",
        "duplicate or invalid JSON key",
    }
    assert layout.owner_manifest.read_bytes() == original


@pytest.mark.parametrize(
    "payload",
    (
        b'\xef\xbb\xbf{}',
        b'{"value":NaN}',
        b'{"one":1,"one":1}',
        b'{} trailing',
    ),
)
def test_task069_owner_read_strict_failures_are_body_free(
    tmp_path: Path, payload: bytes
) -> None:
    layout = _layout(tmp_path)
    layout.owner_manifest.write_bytes(payload)

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        load_bridge_owner(layout)

    assert str(exc.value) in {
        "secure bridge read rejected",
        "duplicate or invalid JSON key",
    }
    assert str(layout.owner_manifest) not in str(exc.value)
    assert payload.decode("utf-8", errors="replace") not in str(exc.value)


def test_task069_small_bridge_bytes_require_canonical_receipt_binding(
    tmp_path: Path,
) -> None:
    layout = _layout(tmp_path)
    layout.owner_manifest.write_bytes(b'{ "ordered" : false }\n')

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        file_bridge._read_regular_bytes(
            layout.owner_manifest, max_bytes=64 * 1024, layout=layout
        )

    assert str(exc.value) == "bridge bytes are not canonical"


def test_task069_owner_read_rejects_noncanonical_bytes(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    value = json.loads(layout.owner_manifest.read_text(encoding="utf-8"))
    layout.owner_manifest.write_text(json.dumps(value, indent=2), encoding="utf-8")

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        load_bridge_owner(layout)

    assert str(exc.value) == "bridge bytes are not canonical"


def test_task069_public_receipt_rejects_same_bytes_inode_swap_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _layout(tmp_path)
    paths = receipt_publication_paths(
        layout,
        record_id="task069-receipt-swap",
        source_sha256="sha256:" + "a" * 64,
        exact_v2=False,
    )
    original = b"{}\n"
    paths.receipt_path.write_bytes(original)
    replacement = layout.receipts / "receipt-replacement.json"
    replaced = False

    def hook(stage: str) -> None:
        nonlocal replaced
        if stage == "target_lstat_complete" and not replaced:
            replacement.write_bytes(original)
            replacement.replace(paths.receipt_path)
            replaced = True

    class HookedAuthority(SecureAuthorityIO):
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            kwargs["_stage_hook"] = hook
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(file_bridge, "SecureAuthorityIO", HookedAuthority)

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        load_published_receipt(paths)

    assert replaced is True
    assert str(exc.value) == "secure bridge read rejected"
    assert paths.receipt_path.read_bytes() == original


def test_task069_public_receipt_rejects_noncanonical_bytes(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    paths = receipt_publication_paths(
        layout,
        record_id="task069-receipt-canonical",
        source_sha256="sha256:" + "b" * 64,
        exact_v2=False,
    )
    paths.receipt_path.write_bytes(b"{ }\n")

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        load_published_receipt(paths)

    assert str(exc.value) == "bridge bytes are not canonical"


def test_task069_public_receipt_over_task068_bound_fails_without_legacy_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _layout(tmp_path)
    paths = receipt_publication_paths(
        layout,
        record_id="task069-receipt-over-bound",
        source_sha256="sha256:" + "c" * 64,
        exact_v2=False,
    )
    paths.receipt_path.write_bytes(b"{" + b" " * (1024 * 1024) + b"}\n")

    def legacy_read_forbidden(*args, **kwargs) -> bytes:  # type: ignore[no-untyped-def]
        pytest.fail("public receipt used the legacy reader")

    monkeypatch.setattr(
        file_bridge, "_legacy_read_regular_bytes", legacy_read_forbidden
    )

    with pytest.raises(MontageLearningFileBridgeError) as exc:
        load_published_receipt(paths)

    assert str(exc.value) == "secure bridge read rejected"
    assert paths.receipt_path.stat().st_size > 1024 * 1024
