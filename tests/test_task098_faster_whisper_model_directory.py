from __future__ import annotations

import copy
import json
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.task098_faster_whisper_model_directory import (
    MANIFEST_DOMAIN,
    RECORD_DOMAIN,
    FasterWhisperModelDirectoryInspectionV1,
    FasterWhisperModelFileObservationV1,
    parse_model_directory_inspection,
    validate_schema_mirror,
)


LOCATOR = "sha256:" + "a" * 64
OTHER_LOCATOR = "sha256:" + "b" * 64


def observation(name: str, marker: str, size: int = 10) -> FasterWhisperModelFileObservationV1:
    return FasterWhisperModelFileObservationV1(
        name=name,
        size_bytes=size,
        sha256="sha256:" + marker * 64,
    )


def minimum_files(vocabulary: str = "vocabulary.txt") -> tuple[FasterWhisperModelFileObservationV1, ...]:
    return (
        observation("config.json", "1"),
        observation("model.bin", "2"),
        observation("tokenizer.json", "3"),
        observation(vocabulary, "4"),
    )


def ready(*, locator: str = LOCATOR, files=None) -> FasterWhisperModelDirectoryInspectionV1:
    return FasterWhisperModelDirectoryInspectionV1.ready(
        private_locator_sha256=locator,
        files=minimum_files() if files is None else files,
    )


def schema_document() -> dict:
    with resources.files("ai_video_production.schema_resources").joinpath(
        "task098-faster-whisper-model-directory.schema.json"
    ).open("r", encoding="utf-8") as source:
        return json.load(source)


def validate_definition(name: str, value: dict) -> None:
    document = schema_document()
    Draft202012Validator(
        {
            "$schema": document["$schema"],
            "$defs": document["$defs"],
            "$ref": f"#/$defs/{name}",
        }
    ).validate(value)


def reject_definition(name: str, value: dict) -> None:
    with pytest.raises(Exception):
        validate_definition(name, value)


def test_schema_mirror_and_private_public_round_trip() -> None:
    validate_schema_mirror()
    root = Path(__file__).parents[1]
    assert (root / "schemas/task098-faster-whisper-model-directory.schema.json").read_bytes() == (
        root
        / "src/ai_video_production/schema_resources/task098-faster-whisper-model-directory.schema.json"
    ).read_bytes()

    value = ready()
    validate_definition("inspection", value.to_dict())
    validate_definition("public_projection", value.to_public_dict())
    restored = parse_model_directory_inspection(json.loads(json.dumps(value.to_dict())))
    assert restored.to_dict() == value.to_dict()
    assert canonical_json_bytes(restored.to_dict()) == canonical_json_bytes(value.to_dict())


def test_schema_itself_closes_required_files_sizes_and_public_state_matrix() -> None:
    value = ready().to_dict()
    missing_config = copy.deepcopy(value)
    missing_config["files"] = [item for item in missing_config["files"] if item["name"] != "config.json"]
    reject_definition("inspection", missing_config)

    oversized_config = copy.deepcopy(value)
    next(item for item in oversized_config["files"] if item["name"] == "config.json")[
        "size_bytes"
    ] = 4 * 1024 * 1024 + 1
    reject_definition("inspection", oversized_config)

    blocked_public = FasterWhisperModelDirectoryInspectionV1.blocked(
        "PATH_NOT_DIRECTORY"
    ).to_public_dict()
    blocked_public["reason_codes"] = ["MODEL_DIRECTORY_VALID"]
    reject_definition("public_projection", blocked_public)

    ready_public = ready().to_public_dict()
    ready_public["model_id"] = None
    reject_definition("public_projection", ready_public)


def test_ready_contract_is_order_independent_and_domain_separated() -> None:
    first = ready(files=minimum_files())
    second = ready(files=tuple(reversed(minimum_files())))
    assert first.to_dict() == second.to_dict()

    manifest_body = [item.to_dict() for item in first.files]
    assert first.model_manifest_sha256 == sha256_bytes(
        MANIFEST_DOMAIN + canonical_json_bytes(manifest_body)
    )
    record_body = {key: value for key, value in first.to_dict().items() if key != "record_sha256"}
    assert first.record_sha256 == sha256_bytes(RECORD_DOMAIN + canonical_json_bytes(record_body))
    assert first.record_sha256 != first.model_manifest_sha256


def test_model_id_is_body_free_and_bound_to_private_locator() -> None:
    first = ready(locator=LOCATOR)
    second = ready(locator=OTHER_LOCATOR)
    assert first.model_id == "local-model-aaaaaaaaaaaa"
    assert second.model_id == "local-model-bbbbbbbbbbbb"
    assert first.model_manifest_sha256 == second.model_manifest_sha256
    assert first.record_sha256 != second.record_sha256


@pytest.mark.parametrize("missing", ["config.json", "model.bin", "tokenizer.json"])
def test_each_required_fixed_file_is_mandatory(missing: str) -> None:
    with pytest.raises(ValueError, match="required model files"):
        ready(files=tuple(item for item in minimum_files() if item.name != missing))


def test_exactly_one_supported_vocabulary_is_required() -> None:
    without = tuple(item for item in minimum_files() if not item.name.startswith("vocabulary."))
    with pytest.raises(ValueError, match="exactly one"):
        ready(files=without)
    with pytest.raises(ValueError, match="exactly one"):
        ready(files=minimum_files() + (observation("vocabulary.json", "5"),))
    assert ready(files=minimum_files("vocabulary.json")).outcome == "READY"


def test_optional_preprocessor_presence_is_derived_not_caller_controlled() -> None:
    absent = ready()
    present = ready(files=minimum_files() + (observation("preprocessor_config.json", "5"),))
    assert absent.optional_preprocessor_config_present is False
    assert present.optional_preprocessor_config_present is True
    tampered = present.to_dict()
    tampered["optional_preprocessor_config_present"] = False
    with pytest.raises(ValueError):
        parse_model_directory_inspection(tampered)


def test_duplicate_file_observations_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        ready(files=minimum_files() + (observation("model.bin", "5"),))


@pytest.mark.parametrize(
    "name,oversize",
    [
        ("config.json", 4 * 1024 * 1024 + 1),
        ("model.bin", 32 * 1024 * 1024 * 1024 + 1),
        ("tokenizer.json", 128 * 1024 * 1024 + 1),
        ("vocabulary.txt", 128 * 1024 * 1024 + 1),
        ("preprocessor_config.json", 4 * 1024 * 1024 + 1),
    ],
)
def test_per_file_size_bounds_fail_closed(name: str, oversize: int) -> None:
    with pytest.raises(ValueError, match="size"):
        observation(name, "1", oversize)
    with pytest.raises(ValueError, match="size"):
        observation(name, "1", 0)


@pytest.mark.parametrize(
    "name",
    [
        "C:\\private\\model.bin",
        "/private/model.bin",
        "../model.bin",
        "https://example.invalid/model.bin",
        "README.md",
    ],
)
def test_paths_urls_and_unknown_files_are_unrepresentable(name: str) -> None:
    with pytest.raises(ValueError, match="file name"):
        observation(name, "1")


def test_invalid_file_and_locator_digests_fail_closed() -> None:
    with pytest.raises(ValueError):
        FasterWhisperModelFileObservationV1("model.bin", 1, "A" * 64)
    with pytest.raises(ValueError):
        ready(locator="sha256:" + "A" * 64)


def test_blocked_contract_is_sorted_body_free_and_round_trips() -> None:
    blocked = FasterWhisperModelDirectoryInspectionV1.blocked(
        "REQUIRED_FILE_MISSING", "PATH_ALIAS_UNSAFE"
    )
    assert blocked.reason_codes == ("PATH_ALIAS_UNSAFE", "REQUIRED_FILE_MISSING")
    assert blocked.model_id is None
    assert blocked.files == ()
    validate_definition("inspection", blocked.to_dict())
    validate_definition("public_projection", blocked.to_public_dict())
    assert parse_model_directory_inspection(blocked.to_dict()) == blocked


@pytest.mark.parametrize(
    "reasons",
    [(), ("UNKNOWN",), ("PATH_NOT_DIRECTORY", "PATH_NOT_DIRECTORY")],
)
def test_blocked_reasons_are_closed_unique_and_nonempty(reasons: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        FasterWhisperModelDirectoryInspectionV1.blocked(*reasons)


def test_public_projection_omits_all_private_identity_and_file_metadata() -> None:
    public = ready().to_public_dict()
    for forbidden in (
        "private_locator_sha256",
        "model_manifest_sha256",
        "files",
        "record_sha256",
        "path",
        "locator",
        "size_bytes",
        "sha256",
    ):
        assert forbidden not in public
    assert "C:\\" not in json.dumps(public)
    assert "/home/" not in json.dumps(public)


@pytest.mark.parametrize(
    "field",
    [
        "model_download_authorized",
        "model_load_started",
        "inference_started",
        "network_used",
        "execution_authorized",
    ],
)
def test_effect_flags_are_fixed_false_and_tamper_is_rejected(field: str) -> None:
    value = ready()
    assert value.to_dict()[field] is False
    tampered = value.to_dict()
    tampered[field] = True
    with pytest.raises(ValueError):
        parse_model_directory_inspection(tampered)


@pytest.mark.parametrize(
    "extra",
    [
        {"path": "C:\\private\\models"},
        {"transcript_body": "private words"},
        {"audio_body": "private audio"},
        {"credential": "secret"},
        {"url": "https://example.invalid/model"},
        {"exception_text": "traceback"},
    ],
)
def test_unknown_private_fields_are_rejected(extra: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_model_directory_inspection(ready().to_dict() | extra)


def test_file_or_manifest_tamper_is_rejected() -> None:
    value = ready().to_dict()
    file_tamper = copy.deepcopy(value)
    file_tamper["files"][0]["size_bytes"] += 1
    with pytest.raises(ValueError):
        parse_model_directory_inspection(file_tamper)
    manifest_tamper = copy.deepcopy(value)
    manifest_tamper["model_manifest_sha256"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError):
        parse_model_directory_inspection(manifest_tamper)


def test_ready_and_blocked_cross_products_fail_closed() -> None:
    ready_value = ready().to_dict()
    ready_value["outcome"] = "BLOCKED"
    with pytest.raises(ValueError):
        parse_model_directory_inspection(ready_value)
    blocked_value = FasterWhisperModelDirectoryInspectionV1.blocked(
        "PATH_NOT_DIRECTORY"
    ).to_dict()
    blocked_value["model_id"] = "local-model-aaaaaaaaaaaa"
    with pytest.raises(ValueError):
        parse_model_directory_inspection(blocked_value)
