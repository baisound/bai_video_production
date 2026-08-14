"""TASK-040 crash-safe Prompt/Generation Attempt metadata persistence.

Prompt bodies and credential values are intentionally not embedded in this store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import AtomicJsonWriter, AtomicWriteResult
from .errors import ProductError, ProductErrorCategory
from .prompt_registry import (
    GenerationAttempt,
    GenerationResult,
    PromptEntity,
    PromptGenerationRegistry,
    RegenerationStrategy,
)
from .serialization import canonical_json_bytes, sha256_bytes
from .production_control_store import _exclusive_snapshot_lock


_MAX_BYTES = 16 * 1024 * 1024
_DOCUMENT_FIELDS = {
    "snapshot_version", "task_owner", "prompts", "attempts", "prompt_body_embedded",
    "credential_values_embedded", "provider_execution_authorized", "snapshot_sha256",
}
_PROMPT_FIELDS = {
    "prompt_id", "prompt_version", "purpose", "scene_id", "slot_id", "body_ref",
    "body_sha256", "provider_profile_id", "provider_profile_version", "input_asset_hashes",
    "keep_conditions", "prompt_body_embedded_in_general_evidence",
}
_ATTEMPT_FIELDS = {
    "generation_job_id", "slot_id", "prompt_id", "prompt_version", "prompt_sha256",
    "provider_id", "model_id", "provider_profile_version", "strategy_level", "result",
    "failure_codes", "output_candidate_id", "parent_attempt_id", "input_asset_hashes",
    "cost", "latency_ms",
}


def _body(registry: PromptGenerationRegistry) -> dict[str, Any]:
    body: dict[str, Any] = {
        "snapshot_version": "1.0.0",
        "task_owner": "TASK-040",
        "prompts": [registry.prompts[key].to_dict() for key in sorted(registry.prompts)],
        "attempts": [registry.attempts[key].to_dict() for key in sorted(registry.attempts)],
        "prompt_body_embedded": False,
        "credential_values_embedded": False,
        "provider_execution_authorized": False,
    }
    body["snapshot_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _parse(document: dict[str, Any]) -> PromptGenerationRegistry:
    if set(document) != _DOCUMENT_FIELDS or document.get("snapshot_version") != "1.0.0" or document.get("task_owner") != "TASK-040":
        raise ProductError("ERR_PROMPT_SNAPSHOT_VERSION", "Unsupported Prompt Registry snapshot version", ProductErrorCategory.DATA_INTEGRITY)
    expected = document.get("snapshot_sha256")
    body = {k: v for k, v in document.items() if k != "snapshot_sha256"}
    if expected != sha256_bytes(canonical_json_bytes(body)):
        raise ProductError("ERR_PROMPT_SNAPSHOT_CHECKSUM", "Prompt Registry snapshot checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if document.get("prompt_body_embedded") is not False or document.get("credential_values_embedded") is not False or document.get("provider_execution_authorized") is not False:
        raise ProductError("ERR_PROMPT_SNAPSHOT_BOUNDARY", "Prompt Registry snapshot violates body/credential/execution boundaries", ProductErrorCategory.SECURITY)
    try:
        prompt_rows = document["prompts"]
        attempt_rows = document["attempts"]
        if not isinstance(prompt_rows, list) or not isinstance(attempt_rows, list):
            raise TypeError("rows must be lists")
        for row in prompt_rows:
            if (
                not isinstance(row, dict)
                or set(row) != _PROMPT_FIELDS
                or isinstance(row["prompt_version"], bool)
                or not isinstance(row["prompt_version"], int)
                or not isinstance(row["input_asset_hashes"], list)
                or not isinstance(row["keep_conditions"], list)
                or row["prompt_body_embedded_in_general_evidence"] is not False
            ):
                raise TypeError("Prompt row fields are invalid")
        for row in attempt_rows:
            if (
                not isinstance(row, dict)
                or set(row) != _ATTEMPT_FIELDS
                or isinstance(row["prompt_version"], bool)
                or not isinstance(row["prompt_version"], int)
                or isinstance(row["strategy_level"], bool)
                or not isinstance(row["strategy_level"], int)
                or not isinstance(row["failure_codes"], list)
                or not isinstance(row["input_asset_hashes"], list)
            ):
                raise TypeError("Attempt row fields are invalid")
        prompts = [
            PromptEntity(
                prompt_id=row["prompt_id"],
                prompt_version=row["prompt_version"],
                purpose=row["purpose"],
                body_sha256=row["body_sha256"],
                provider_profile_id=row["provider_profile_id"],
                provider_profile_version=row["provider_profile_version"],
                keep_conditions=tuple(row["keep_conditions"]),
                scene_id=row.get("scene_id"),
                slot_id=row.get("slot_id"),
                body_ref=row.get("body_ref"),
                input_asset_hashes=tuple(row.get("input_asset_hashes", [])),
            )
            for row in prompt_rows
        ]
        attempts = [
            GenerationAttempt(
                generation_job_id=row["generation_job_id"],
                slot_id=row["slot_id"],
                prompt_id=row["prompt_id"],
                prompt_version=row["prompt_version"],
                prompt_sha256=row["prompt_sha256"],
                provider_id=row["provider_id"],
                model_id=row["model_id"],
                provider_profile_version=row.get("provider_profile_version"),
                strategy_level=RegenerationStrategy(row["strategy_level"]),
                result=GenerationResult(row["result"]),
                failure_codes=tuple(row.get("failure_codes", [])),
                output_candidate_id=row.get("output_candidate_id"),
                parent_attempt_id=row.get("parent_attempt_id"),
                input_asset_hashes=tuple(row.get("input_asset_hashes", [])),
                cost=row.get("cost"),
                latency_ms=row.get("latency_ms"),
            )
            for row in attempt_rows
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError("ERR_PROMPT_SNAPSHOT_INVALID", "Prompt Registry snapshot contains invalid records", ProductErrorCategory.DATA_INTEGRITY) from exc

    registry = PromptGenerationRegistry()
    for prompt in sorted(prompts, key=lambda item: (item.prompt_id, item.prompt_version)):
        registry.add_prompt(prompt)
    pending = {item.generation_job_id: item for item in attempts}
    while pending:
        progressed = False
        for key in sorted(tuple(pending)):
            item = pending[key]
            if item.parent_attempt_id is not None and item.parent_attempt_id not in registry.attempts:
                continue
            registry.add_attempt(item)
            del pending[key]
            progressed = True
        if not progressed:
            raise ProductError("ERR_PROMPT_SNAPSHOT_PARENT_GRAPH", "Generation Attempt parent graph is missing a parent or contains a cycle", ProductErrorCategory.DATA_INTEGRITY)
    if len(registry.prompts) != len(prompt_rows) or len(registry.attempts) != len(attempt_rows):
        raise ProductError("ERR_PROMPT_SNAPSHOT_DUPLICATE_ID", "Prompt Registry snapshot contains duplicate identities", ProductErrorCategory.DATA_INTEGRITY)
    if _body(registry)["snapshot_sha256"] != expected:
        raise ProductError("ERR_PROMPT_SNAPSHOT_DOMAIN_HASH", "Prompt Registry identity changed during recovery", ProductErrorCategory.DATA_INTEGRITY)
    return registry


class PromptRegistrySnapshotStore:
    @staticmethod
    def snapshot(registry: PromptGenerationRegistry) -> dict[str, Any]:
        return _body(registry)

    @staticmethod
    def load(path: str | Path) -> PromptGenerationRegistry:
        target = Path(path)
        if target.is_symlink() or not target.is_file():
            raise ProductError("ERR_PROMPT_SNAPSHOT_FILE_INVALID", "Prompt Registry snapshot must be a regular non-symlink file", ProductErrorCategory.VALIDATION)
        size = target.stat().st_size
        if size <= 0 or size > _MAX_BYTES:
            raise ProductError("ERR_PROMPT_SNAPSHOT_SIZE", "Prompt Registry snapshot size is outside the allowed bound", ProductErrorCategory.VALIDATION, details={"size_bytes": size})
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_PROMPT_SNAPSHOT_READ", "Prompt Registry snapshot could not be read as UTF-8 JSON", ProductErrorCategory.DATA_INTEGRITY) from exc
        if not isinstance(value, dict):
            raise ProductError("ERR_PROMPT_SNAPSHOT_INVALID", "Prompt Registry snapshot root must be an object", ProductErrorCategory.DATA_INTEGRITY)
        return _parse(value)

    @staticmethod
    def save(path: str | Path, registry: PromptGenerationRegistry, *, expected_previous_snapshot_sha256: str | None = None) -> AtomicWriteResult:
        target = Path(path)
        with _exclusive_snapshot_lock(target):
            if target.is_symlink():
                raise ProductError("ERR_PROMPT_SNAPSHOT_FILE_INVALID", "Refusing to replace a symlink Prompt Registry snapshot", ProductErrorCategory.SECURITY)
            if target.exists():
                if not target.is_file():
                    raise ProductError("ERR_PROMPT_SNAPSHOT_FILE_INVALID", "Prompt Registry target must be a regular file", ProductErrorCategory.VALIDATION)
                if expected_previous_snapshot_sha256 is None:
                    raise ProductError("ERR_PROMPT_SNAPSHOT_CAS_REQUIRED", "Replacing an existing Prompt Registry snapshot requires its exact previous checksum", ProductErrorCategory.AUTHORIZATION)
                current = _body(PromptRegistrySnapshotStore.load(target))["snapshot_sha256"]
                if current != expected_previous_snapshot_sha256:
                    raise ProductError("ERR_PROMPT_SNAPSHOT_REVISION_CONFLICT", "Prompt Registry snapshot changed before save; reload before retry", ProductErrorCategory.STATE, details={"current_snapshot_sha256": current})
            elif expected_previous_snapshot_sha256 is not None:
                raise ProductError("ERR_PROMPT_SNAPSHOT_PREVIOUS_MISSING", "Expected previous Prompt Registry snapshot does not exist", ProductErrorCategory.STATE)
            document = _body(registry)
            return AtomicJsonWriter.write(target, document, validator=lambda value: _parse(value))
