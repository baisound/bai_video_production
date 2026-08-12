"""TASK-023 FasterWhisper provider reconciliation and deterministic evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any

from .faster_whisper_asr import FasterWhisperProvider
from .serialization import sha256_json


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def sha256_file(path: str | Path, *, chunk_size: int = 4 * 1024 * 1024) -> str:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError("source file does not exist or is not a regular file")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _validate_sha256(value: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError("source_sha256 must be sha256:<64 lowercase hex>")
    return value


def _config_payload(provider: FasterWhisperProvider) -> dict[str, Any]:
    config = provider.config
    return {
        "provider_id": provider.provider_id,
        "model_id": provider.model_id,
        "model": config.model,
        "device": config.device,
        "compute_type": config.compute_type,
        "beam_size": config.beam_size,
        "vad_filter": config.vad_filter,
        "model_download_authorized": bool(config.allow_model_download),
        "custom_cache_directory_configured": config.cache_directory is not None,
    }


@dataclass(frozen=True, slots=True)
class FasterWhisperExecutionIdentity:
    source_sha256: str
    requested_language: str | None
    config_sha256: str
    execution_sha256: str
    provider: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_version": "1.0.0",
            "source_sha256": self.source_sha256,
            "requested_language": self.requested_language,
            "provider": dict(self.provider),
            "config_sha256": self.config_sha256,
            "execution_sha256": self.execution_sha256,
            "source_path_in_identity": False,
            "cache_path_in_identity": False,
            "transcript_text_in_identity": False,
        }


def build_execution_identity(
    provider: FasterWhisperProvider,
    *,
    source_sha256: str,
    requested_language: str | None,
) -> FasterWhisperExecutionIdentity:
    source_sha256 = _validate_sha256(source_sha256)
    provider_payload = _config_payload(provider)
    config_sha256 = sha256_json(provider_payload)
    execution_sha256 = sha256_json(
        {
            "identity_version": "1.0.0",
            "source_sha256": source_sha256,
            "requested_language": requested_language,
            "provider_config_sha256": config_sha256,
        }
    )
    return FasterWhisperExecutionIdentity(
        source_sha256=source_sha256,
        requested_language=requested_language,
        config_sha256=config_sha256,
        execution_sha256=execution_sha256,
        provider=provider_payload,
    )


def build_reconciliation_report(provider: FasterWhisperProvider) -> dict[str, Any]:
    config = _config_payload(provider)
    return {
        "report_version": "1.0.0",
        "ok": True,
        "task_owner": "TASK-023",
        "implementation_origin": "TASK-006",
        "transcript_contract_owner": "TASK-006",
        "product_architecture": "PRODUCT-ARCH-001",
        "integration_state": "INTEGRATION_DESIGNED",
        "final_user_entrypoint": "BAI Video Production.exe",
        "final_workspace": "Subtitle Workspace",
        "interface_classification": "DEVELOPER_DIAGNOSTIC_INTERFACE",
        "provider": config,
        "capabilities": {
            "local_faster_whisper_provider": True,
            "explicit_model_download_gate": True,
            "model_cache_directory_supported": True,
            "process_local_model_reuse": True,
            "resumable_large_media_private_state": True,
            "atomic_transcript_srt_report_publication": True,
            "text_free_operational_report": True,
            "public_final_transcript_result_cache": False,
            "word_timestamp_contract": "DEFERRED_NOT_CANONICAL",
            "condition_on_previous_text_contract": "DEFERRED_NO_BEHAVIOR_CHANGE",
        },
        "network_used": False,
        "model_loaded": False,
        "inference_performed": False,
        "source_path_in_evidence": False,
        "cache_path_in_evidence": False,
        "transcript_text_in_evidence": False,
    }
