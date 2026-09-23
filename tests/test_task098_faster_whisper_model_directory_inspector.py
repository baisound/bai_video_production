from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import ai_video_production.task098_faster_whisper_model_directory_inspector as inspector
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task098_faster_whisper_model_directory_inspector import (
    MAX_MODEL_DIRECTORY_ENTRIES,
    inspect_faster_whisper_model_directory,
)


def make_model(root: Path, *, vocabulary: str = "vocabulary.txt", optional: bool = False) -> Path:
    root.mkdir()
    (root / "config.json").write_text('{"model_type":"whisper"}', encoding="utf-8")
    (root / "model.bin").write_bytes(b"model-body")
    (root / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    if vocabulary == "vocabulary.txt":
        (root / vocabulary).write_text("token\n", encoding="utf-8")
    else:
        (root / vocabulary).write_text('{"token":0}', encoding="utf-8")
    if optional:
        (root / "preprocessor_config.json").write_text('{"feature_size":80}', encoding="utf-8")
    return root


@pytest.mark.parametrize("vocabulary", ["vocabulary.txt", "vocabulary.json"])
def test_valid_minimum_is_ready_and_locator_bound(tmp_path: Path, vocabulary: str) -> None:
    model = make_model(tmp_path / "private-model", vocabulary=vocabulary)
    result = inspect_faster_whisper_model_directory(model)
    canonical = model.resolve(strict=True)

    assert result.outcome == "READY"
    assert result.private_locator_sha256 == sha256_bytes(str(canonical).encode("utf-8"))
    assert result.model_id == "local-model-" + result.private_locator_sha256[7:19]
    assert tuple(item.name for item in result.files) == tuple(
        sorted({"config.json", "model.bin", "tokenizer.json", vocabulary})
    )
    serialized = json.dumps(result.to_dict(), ensure_ascii=False)
    public = json.dumps(result.to_public_dict(), ensure_ascii=False)
    assert str(model) not in serialized
    assert str(model) not in public
    assert all(result.to_dict()[field] is False for field in (
        "model_download_authorized", "model_load_started", "inference_started",
        "network_used", "execution_authorized",
    ))


def test_optional_preprocessor_is_hashed_but_only_presence_is_public(tmp_path: Path) -> None:
    result = inspect_faster_whisper_model_directory(make_model(tmp_path / "model", optional=True))
    assert result.outcome == "READY"
    assert result.optional_preprocessor_config_present is True
    assert "preprocessor_config.json" in {item.name for item in result.files}
    assert "files" not in result.to_public_dict()


@pytest.mark.parametrize("locator_kind", ["missing", "file", "relative"])
def test_invalid_directory_locator_fails_closed(tmp_path: Path, locator_kind: str) -> None:
    if locator_kind == "missing":
        locator = tmp_path / "missing"
        expected = "PATH_NOT_DIRECTORY"
    elif locator_kind == "file":
        locator = tmp_path / "file"
        locator.write_bytes(b"x")
        expected = "PATH_NOT_DIRECTORY"
    else:
        locator = Path("relative-model")
        expected = "PATH_ALIAS_UNSAFE"
    result = inspect_faster_whisper_model_directory(locator)
    assert result.outcome == "BLOCKED"
    assert result.reason_codes == (expected,)
    assert result.files == ()


def test_symlink_leaf_or_ancestor_is_rejected_when_supported(tmp_path: Path) -> None:
    real = make_model(tmp_path / "real")
    leaf = tmp_path / "leaf-link"
    ancestor = tmp_path / "ancestor-link"
    try:
        leaf.symlink_to(real, target_is_directory=True)
        ancestor.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    assert inspect_faster_whisper_model_directory(leaf).reason_codes == ("PATH_ALIAS_UNSAFE",)
    assert inspect_faster_whisper_model_directory(ancestor / "real").reason_codes == (
        "PATH_ALIAS_UNSAFE",
    )


def test_required_file_symlink_is_rejected_when_supported(tmp_path: Path) -> None:
    model = make_model(tmp_path / "model")
    target = model / "real-model.bin"
    target.write_bytes((model / "model.bin").read_bytes())
    (model / "model.bin").unlink()
    try:
        (model / "model.bin").symlink_to(target)
    except OSError:
        pytest.skip("file symlink creation is unavailable")
    assert inspect_faster_whisper_model_directory(model).reason_codes == (
        "FILE_ALIAS_UNSAFE",
    )


def test_directory_scan_failure_is_closed_and_path_free(tmp_path: Path, monkeypatch) -> None:
    model = make_model(tmp_path / "private-model")

    def fail_scan(root: Path):
        raise PermissionError("private-path-detail")

    monkeypatch.setattr(inspector, "_scan_entries", fail_scan)
    result = inspect_faster_whisper_model_directory(model)
    body = json.dumps(result.to_dict())
    assert result.reason_codes == ("DIRECTORY_SCAN_FAILED",)
    assert str(model) not in body
    assert "private-path-detail" not in body


def test_directory_entry_limit_is_enforced_before_file_reads(tmp_path: Path) -> None:
    model = make_model(tmp_path / "model")
    for index in range(MAX_MODEL_DIRECTORY_ENTRIES):
        (model / f"extra-{index:02d}.txt").write_bytes(b"x")
    result = inspect_faster_whisper_model_directory(model)
    assert result.reason_codes == ("DIRECTORY_ENTRY_LIMIT_EXCEEDED",)


def test_required_file_and_vocabulary_shape_fail_closed(tmp_path: Path) -> None:
    missing = make_model(tmp_path / "missing")
    (missing / "config.json").unlink()
    assert inspect_faster_whisper_model_directory(missing).reason_codes == (
        "REQUIRED_FILE_MISSING",
    )

    duplicate = make_model(tmp_path / "duplicate")
    (duplicate / "vocabulary.json").write_text('{"token":0}', encoding="utf-8")
    assert inspect_faster_whisper_model_directory(duplicate).reason_codes == (
        "VOCABULARY_SET_INVALID",
    )


def test_non_regular_and_hard_link_files_are_rejected(tmp_path: Path) -> None:
    nonregular = make_model(tmp_path / "nonregular")
    (nonregular / "tokenizer.json").unlink()
    (nonregular / "tokenizer.json").mkdir()
    assert inspect_faster_whisper_model_directory(nonregular).reason_codes == (
        "FILE_NOT_REGULAR",
    )

    hardlinked = make_model(tmp_path / "hardlinked")
    try:
        os.link(hardlinked / "model.bin", hardlinked / "extra-model-link.bin")
    except OSError:
        pytest.skip("hard links are unavailable")
    assert inspect_faster_whisper_model_directory(hardlinked).reason_codes == (
        "FILE_ALIAS_UNSAFE",
    )


def test_empty_oversized_and_invalid_json_files_are_rejected(tmp_path: Path) -> None:
    empty = make_model(tmp_path / "empty")
    (empty / "model.bin").write_bytes(b"")
    assert inspect_faster_whisper_model_directory(empty).reason_codes == (
        "FILE_SIZE_INVALID",
    )

    oversized = make_model(tmp_path / "oversized")
    with (oversized / "config.json").open("wb") as stream:
        stream.truncate(4 * 1024 * 1024 + 1)
    assert inspect_faster_whisper_model_directory(oversized).reason_codes == (
        "FILE_SIZE_INVALID",
    )

    invalid_json = make_model(tmp_path / "invalid-json")
    (invalid_json / "tokenizer.json").write_bytes(b"{not-json")
    assert inspect_faster_whisper_model_directory(invalid_json).reason_codes == (
        "REQUIRED_JSON_INVALID",
    )


def test_open_failure_and_mid_read_change_are_hash_failures(tmp_path: Path, monkeypatch) -> None:
    model = make_model(tmp_path / "open-failure")
    real_open = inspector.os.open

    def fail_model_open(path, flags):
        if Path(path).name == "model.bin":
            raise PermissionError("secret")
        return real_open(path, flags)

    monkeypatch.setattr(inspector.os, "open", fail_model_open)
    assert inspect_faster_whisper_model_directory(model).reason_codes == (
        "FILE_HASH_INVALID",
    )
    monkeypatch.setattr(inspector.os, "open", real_open)

    changed = make_model(tmp_path / "changed")
    real_read = inspector.os.read
    mutated = False

    def mutate_then_read(descriptor: int, count: int) -> bytes:
        nonlocal mutated
        if not mutated:
            mutated = True
            (changed / "config.json").write_text('{"changed":true}', encoding="utf-8")
        return real_read(descriptor, count)

    monkeypatch.setattr(inspector.os, "read", mutate_then_read)
    assert inspect_faster_whisper_model_directory(changed).reason_codes == (
        "FILE_HASH_INVALID",
    )


def test_directory_mutation_during_scan_is_rejected(tmp_path: Path, monkeypatch) -> None:
    model = make_model(tmp_path / "model")
    real_observe = inspector._read_stable_file
    mutated = False

    def observe_and_mutate(path: Path, *, name: str):
        nonlocal mutated
        result = real_observe(path, name=name)
        if not mutated:
            mutated = True
            (model / "late-entry.txt").write_bytes(b"late")
        return result

    monkeypatch.setattr(inspector, "_read_stable_file", observe_and_mutate)
    assert inspect_faster_whisper_model_directory(model).reason_codes == (
        "DIRECTORY_SCAN_FAILED",
    )


def test_inspection_is_read_only_and_deterministic(tmp_path: Path) -> None:
    model = make_model(tmp_path / "model", optional=True)
    before = {path.name: path.read_bytes() for path in model.iterdir() if path.is_file()}
    first = inspect_faster_whisper_model_directory(model)
    second = inspect_faster_whisper_model_directory(model)
    after = {path.name: path.read_bytes() for path in model.iterdir() if path.is_file()}
    assert first.to_dict() == second.to_dict()
    assert before == after


def test_programmer_type_misuse_is_rejected_before_filesystem_access() -> None:
    with pytest.raises(TypeError, match="local path"):
        inspect_faster_whisper_model_directory(123)  # type: ignore[arg-type]


@pytest.mark.parametrize("locator", ["", "bad\x00path"])
def test_malformed_text_locator_is_blocked_without_os_error(locator: str) -> None:
    assert inspect_faster_whisper_model_directory(locator).reason_codes == (
        "PATH_NOT_DIRECTORY",
    )
