from __future__ import annotations

import json
from pathlib import Path

from ai_video_production.faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from ai_video_production.faster_whisper_reconciliation import (
    build_execution_identity,
    build_reconciliation_report,
    sha256_file,
)
from ai_video_production.faster_whisper_reconciliation_cli import main


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def provider(**overrides) -> FasterWhisperProvider:
    values = {
        "model": "small",
        "device": "cpu",
        "compute_type": "int8",
        "beam_size": 5,
        "vad_filter": True,
        "allow_model_download": False,
        "cache_directory": None,
    }
    values.update(overrides)
    return FasterWhisperProvider(FasterWhisperConfig(**values))


def test_reconciliation_report_is_model_free_and_privacy_minimized() -> None:
    factory_calls: list[object] = []

    def factory(*args, **kwargs):
        factory_calls.append((args, kwargs))
        raise AssertionError("model must not load")

    p = FasterWhisperProvider(FasterWhisperConfig(model="small"), model_factory=factory)
    report = build_reconciliation_report(p)

    assert report["ok"] is True
    assert report["task_owner"] == "TASK-023"
    assert report["implementation_origin"] == "TASK-006"
    assert report["model_loaded"] is False
    assert report["inference_performed"] is False
    assert report["source_path_in_evidence"] is False
    assert report["cache_path_in_evidence"] is False
    assert report["transcript_text_in_evidence"] is False
    assert factory_calls == []


def test_reconciliation_report_registers_unified_application_target_without_overclaiming() -> None:
    report = build_reconciliation_report(provider())
    assert report["product_architecture"] == "PRODUCT-ARCH-001"
    assert report["integration_state"] == "INTEGRATION_DESIGNED"
    assert report["final_user_entrypoint"] == "BAI Video Production.exe"
    assert report["final_workspace"] == "Subtitle Workspace"
    assert report["interface_classification"] == "DEVELOPER_DIAGNOSTIC_INTERFACE"


def test_execution_identity_is_deterministic_and_source_sensitive() -> None:
    p = provider()
    first = build_execution_identity(p, source_sha256=SHA_A, requested_language="ja")
    second = build_execution_identity(p, source_sha256=SHA_A, requested_language="ja")
    changed = build_execution_identity(p, source_sha256=SHA_B, requested_language="ja")
    assert first.to_dict() == second.to_dict()
    assert first.execution_sha256 != changed.execution_sha256


def test_execution_identity_is_language_sensitive() -> None:
    p = provider()
    ja = build_execution_identity(p, source_sha256=SHA_A, requested_language="ja")
    en = build_execution_identity(p, source_sha256=SHA_A, requested_language="en")
    assert ja.config_sha256 == en.config_sha256
    assert ja.execution_sha256 != en.execution_sha256


def test_config_identity_changes_for_all_provider_runtime_settings(tmp_path: Path) -> None:
    base = build_execution_identity(provider(), source_sha256=SHA_A, requested_language="ja")
    variants = (
        provider(model="medium"),
        provider(device="cuda"),
        provider(compute_type="float16"),
        provider(beam_size=1),
        provider(vad_filter=False),
        provider(allow_model_download=True),
        provider(cache_directory=tmp_path / "models"),
    )
    hashes = {
        build_execution_identity(item, source_sha256=SHA_A, requested_language="ja").config_sha256
        for item in variants
    }
    assert base.config_sha256 not in hashes
    assert len(hashes) == len(variants)


def test_identity_does_not_expose_cache_path(tmp_path: Path) -> None:
    secretish_path = tmp_path / "private-user-name" / "models"
    identity = build_execution_identity(
        provider(cache_directory=secretish_path),
        source_sha256=SHA_A,
        requested_language="ja",
    ).to_dict()
    serialized = json.dumps(identity, ensure_ascii=False)
    assert str(secretish_path) not in serialized
    assert identity["provider"]["custom_cache_directory_configured"] is True


def test_invalid_sha_is_rejected() -> None:
    p = provider()
    try:
        build_execution_identity(p, source_sha256="bad", requested_language="ja")
    except ValueError as exc:
        assert "sha256" in str(exc)
    else:
        raise AssertionError("invalid SHA must fail")


def test_sha256_file_and_cli_do_not_print_source_path(tmp_path: Path, capsys) -> None:
    source = tmp_path / "private-name.wav"
    source.write_bytes(b"real local bytes")
    digest = sha256_file(source)
    assert digest.startswith("sha256:")
    rc = main(["--source-file", str(source), "--language", "ja"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution_identity"]["source_sha256"] == digest
    assert payload["source_path_in_evidence"] is False
    assert str(source) not in json.dumps(payload, ensure_ascii=False)


def test_cli_accepts_sha_without_media_file(capsys) -> None:
    rc = main(["--source-sha256", SHA_A, "--language", "ja"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution_identity"]["source_sha256"] == SHA_A
    assert payload["model_loaded"] is False
    assert payload["inference_performed"] is False
