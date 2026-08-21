from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai_video_production.qwen3_tts_pinned_snapshot_verifier import (
    ACCEPTED_SEMANTIC_SHA256,
    ACCEPTED_ENTRIES_SHA256, ACCEPTED_FILE_COUNT, ACCEPTED_MODEL_ID, ACCEPTED_REVISION,
    ACCEPTED_TOTAL_BYTES,
    Qwen3TtsPinnedSnapshotManifest,
    VerificationDecision,
    _canonical_manifest_digest,
    _entries_digest,
    _receipt_body,
    _verify_manifest,
    parse_qwen3_tts_pinned_snapshot_manifest,
    parse_qwen3_tts_pinned_snapshot_verification,
    verify_qwen3_tts_pinned_snapshot,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


EVALUATED_AT = "2026-08-21T00:00:00Z"


def _rehash_receipt(value: dict[str, object]) -> dict[str, object]:
    unsigned = dict(value)
    unsigned.pop("receipt_sha256", None)
    value["receipt_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    return value


def _write_fixture(root: Path) -> dict[str, bytes]:
    bodies = {f"file-{index:02d}.bin": f"body-{index}".encode() for index in range(12)}
    bodies["speech_tokenizer/tokenizer.bin"] = b"tokenizer"
    for relative, body in bodies.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return bodies


def _manifest(bodies: dict[str, bytes]) -> dict[str, object]:
    files = [
        {"path": path, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
         "blob_id_sha1": "a" * 40, "digest_source": "resolved_bytes", "load_input": True}
        for path, body in sorted(bodies.items())
    ]
    retrieved_at = "2026-08-20T00:00:00Z"
    data = {"schema_version": "1.0.0", "manifest_id": "test-pinned-manifest", "model_id": "test/qwen3",
        "revision": "a" * 40, "retrieved_at": retrieved_at,
        "source": {"provider": "test", "api": "https://example.invalid/api", "resolve_prefix": "https://example.invalid/resolve/"},
        "entries_sha256": _entries_digest(files),
        "entries_digest_algorithm": "TASK014_PINNED_MODEL_ENTRIES_V1: SHA-256 over UTF-8 file records sorted by ASCII bytewise ascending path; reject non-ASCII paths, duplicates and ASCII-case-fold collisions; each record is path, NUL, decimal bytes, NUL, sha256, NUL, blob_id_sha1, NUL, digest_source, NUL, lowercase load_input, LF",
        "canonical_manifest_sha256": "0" * 64,
        "canonical_manifest_digest_algorithm": "TASK014_PINNED_MODEL_MANIFEST_V1 defined in the companion Evidence",
        "files": files,
        "no_effect_flags": {"model_weights_downloaded": False, "model_loaded": False, "package_installed": False, "owner_audio_read": False, "inference_executed": False, "firewall_changed": False}}
    data["canonical_manifest_sha256"] = _canonical_manifest_digest(data, files)
    return data


def _parsed_fixture(tmp_path: Path) -> tuple[Qwen3TtsPinnedSnapshotManifest, Path]:
    root = tmp_path / "snapshot"
    bodies = _write_fixture(root)
    return parse_qwen3_tts_pinned_snapshot_manifest(_manifest(bodies)), root


def _accepted_diagnostic_receipt_body() -> dict[str, object]:
    manifest = Qwen3TtsPinnedSnapshotManifest(
        manifest_id="receipt-test", model_id=ACCEPTED_MODEL_ID, revision=ACCEPTED_REVISION,
        retrieved_at="2026-08-20T15:27:32.139Z", source={}, files=tuple({} for _ in range(ACCEPTED_FILE_COUNT)),
        total_bytes=ACCEPTED_TOTAL_BYTES, entries_sha256=ACCEPTED_ENTRIES_SHA256,
        semantic_sha256=ACCEPTED_SEMANTIC_SHA256,
    )
    body = _receipt_body(manifest=manifest, decision=VerificationDecision.VERIFIED, reasons=(),
        evaluated_at=EVALUATED_AT, root_fingerprint="sha256:" + "a" * 64,
        file_bodies_hashed=True, filesystem_enumerated=True, snapshot_modified=False)
    return _rehash_receipt(body)


def test_generic_fixture_is_verified_but_persistent_verified_requires_accepted_pin(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)

    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False)

    assert receipt.decision is VerificationDecision.VERIFIED
    assert receipt.reason_codes == ()
    assert receipt.file_bodies_hashed is True
    with pytest.raises(ValueError, match="VERIFIED receipt"):
        parse_qwen3_tts_pinned_snapshot_verification(receipt.to_private_dict())
    public = receipt.to_public_dict()
    assert "snapshot_root_fingerprint" not in public
    assert public["snapshot_root_fingerprint_persisted"] is False
    assert public["diagnostic_only"] is True
    assert public["persistent_receipt_is_capability"] is False
    assert public["model_reuse_authorized"] is False
    assert public["model_load_authorized"] is False
    assert public["post_return_state_guaranteed"] is False
    assert public["consumer_revalidation_required"] is True
    assert public["model_loaded"] is False


def test_accepted_pin_diagnostic_receipt_parser_round_trips_without_io() -> None:
    parsed = parse_qwen3_tts_pinned_snapshot_verification(_accepted_diagnostic_receipt_body())
    assert parsed.decision is VerificationDecision.VERIFIED
    private = parsed.to_private_dict()
    assert private["diagnostic_only"] is True
    assert private["persistent_receipt_is_capability"] is False
    assert private["model_reuse_authorized"] is False
    assert private["model_load_authorized"] is False
    assert private["post_return_state_guaranteed"] is False
    assert private["consumer_revalidation_required"] is True


@pytest.mark.parametrize("field,value", [
    ("schema_version", "wrong"), ("files", []),
    ("entries_sha256", "0" * 64), ("canonical_manifest_sha256", "0" * 64),
])
def test_manifest_parser_rejects_tampering(tmp_path: Path, field: str, value: object) -> None:
    _, root = _parsed_fixture(tmp_path)
    data = _manifest({path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()})
    data[field] = value
    with pytest.raises(ValueError):
        parse_qwen3_tts_pinned_snapshot_manifest(data)


@pytest.mark.parametrize("bad_path", ["../escape", "speech_tokenizer\\x", "/absolute", "a//b", "a/../b", "bad\u0000name"])
def test_manifest_rejects_unsafe_paths(tmp_path: Path, bad_path: str) -> None:
    manifest, _ = _parsed_fixture(tmp_path)
    data = manifest.to_dict()
    data["files"][0]["path"] = bad_path
    with pytest.raises(ValueError):
        parse_qwen3_tts_pinned_snapshot_manifest(data)


def test_public_production_wrapper_rejects_nonaccepted_semantic_digest(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    assert manifest.semantic_sha256 != ACCEPTED_SEMANTIC_SHA256

    receipt = verify_qwen3_tts_pinned_snapshot(manifest, root, EVALUATED_AT)

    assert receipt.decision is VerificationDecision.BLOCKED
    assert "UNACCEPTED_SEMANTIC_DIGEST" in receipt.reason_codes


@pytest.mark.parametrize("action,reason", [
    (lambda root: (root / "file-00.bin").unlink(), "SNAPSHOT_FILE_MISSING"),
    (lambda root: (root / "extra.bin").write_bytes(b"x"), "SNAPSHOT_EXTRA_ENTRY"),
    (lambda root: (root / ".cache").mkdir(), "SNAPSHOT_EXTRA_DIRECTORY"),
    (lambda root: (root / "file-00.bin").write_bytes(b"wrong"), "SNAPSHOT_FILE_SIZE_MISMATCH"),
])
def test_generic_verifier_blocks_snapshot_shape_or_size(tmp_path: Path, action, reason: str) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    action(root)
    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert receipt.decision is VerificationDecision.BLOCKED
    assert reason in receipt.reason_codes


def test_generic_verifier_blocks_digest_and_case_mismatch(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    target = root / "file-00.bin"
    target.write_bytes(b"body-X")  # same length, different digest
    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert "SNAPSHOT_FILE_DIGEST_MISMATCH" in receipt.reason_codes

    target.unlink()
    (root / "FILE-00.BIN").write_bytes(b"body-0")
    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert "SNAPSHOT_PATH_CASE_MISMATCH" in receipt.reason_codes


def test_generic_verifier_blocks_a_reparse_point_when_supported(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    target = root / "file-00.bin"
    link = root / "file-01.bin"
    link.unlink()
    try:
        link.symlink_to(target.name)
    except OSError:
        pytest.skip("the host does not permit symlink fixtures")
    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert receipt.decision is VerificationDecision.BLOCKED
    assert "SNAPSHOT_REPARSE_POINT" in receipt.reason_codes


def test_known_blocker_overrides_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    (root / "extra.bin").write_bytes(b"x")
    import ai_video_production.qwen3_tts_pinned_snapshot_verifier as verifier

    original_open = Path.open

    def denied(self: Path, *args, **kwargs):
        if self.name == "file-00.bin":
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    receipt = verifier._verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert receipt.decision is VerificationDecision.BLOCKED
    assert "SNAPSHOT_EXTRA_ENTRY" in receipt.reason_codes
    assert "SNAPSHOT_FILE_ACCESS_UNKNOWN" in receipt.reason_codes


def test_invalid_root_and_controlled_race_are_not_fully_hashed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    invalid = _verify_manifest(manifest, Path("relative-snapshot"), EVALUATED_AT, production=False)
    assert invalid.decision is VerificationDecision.BLOCKED
    assert invalid.filesystem_enumerated is False
    assert invalid.file_bodies_hashed is False

    import ai_video_production.qwen3_tts_pinned_snapshot_verifier as verifier
    original = verifier._stat_signature
    calls = 0

    def changing_signature(metadata):
        nonlocal calls
        calls += 1
        return (*original(metadata), calls) if calls == 3 else original(metadata)

    monkeypatch.setattr(verifier, "_stat_signature", changing_signature)
    raced = verifier._verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert raced.decision is VerificationDecision.UNKNOWN
    assert raced.snapshot_modified is True
    assert raced.file_bodies_hashed is False


def test_known_absence_is_blocked_and_timestamp_requires_full_utc(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    absent = _verify_manifest(manifest, tmp_path / "absent", EVALUATED_AT, production=False)
    assert absent.decision is VerificationDecision.BLOCKED
    assert "SNAPSHOT_ROOT_NOT_ADMITTED" in absent.reason_codes
    (root / "speech_tokenizer" / "tokenizer.bin").unlink()
    (root / "speech_tokenizer").rmdir()
    missing = _verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert missing.decision is VerificationDecision.BLOCKED
    assert "SNAPSHOT_FILE_MISSING" in missing.reason_codes
    with pytest.raises(ValueError):
        _verify_manifest(manifest, root, "2026-08-21Z", production=False)


@pytest.mark.parametrize("unsafe", [Path("relative"), Path("//server/share"), Path("\\\\?\\C:\\")])
def test_unsafe_root_is_rejected_before_any_filesystem_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe: Path) -> None:
    manifest, _ = _parsed_fixture(tmp_path)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("unsafe root attempted filesystem I/O")
    monkeypatch.setattr(Path, "lstat", forbidden)
    receipt = _verify_manifest(manifest, unsafe, EVALUATED_AT, production=False)
    assert receipt.decision is VerificationDecision.BLOCKED
    assert receipt.filesystem_enumerated is False


def test_windows_remote_drive_is_rejected_before_filesystem_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name != "nt":
        pytest.skip("Windows drive locality gate")
    manifest, _ = _parsed_fixture(tmp_path)
    import ai_video_production.qwen3_tts_pinned_snapshot_verifier as verifier
    monkeypatch.setattr(verifier, "_windows_drive_type", lambda _: 4)  # DRIVE_REMOTE
    monkeypatch.setattr(Path, "lstat", lambda *_args, **_kwargs: pytest.fail("unexpected filesystem I/O"))
    receipt = verifier._verify_manifest(manifest, Path("C:\\mapped-snapshot"), EVALUATED_AT, production=False)
    assert receipt.decision is VerificationDecision.BLOCKED
    assert receipt.filesystem_enumerated is False


def test_inventory_cap_stops_before_unbounded_empty_directories(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    for index in range(65):
        (root / f"extra-{index:03d}").mkdir()
    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False)
    assert receipt.decision is VerificationDecision.BLOCKED
    assert receipt.filesystem_enumerated is False
    assert "SNAPSHOT_EXTRA_ENTRY" in receipt.reason_codes


def test_rehashed_decision_reason_class_tampering_is_rejected(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    receipt = verify_qwen3_tts_pinned_snapshot(manifest, root, EVALUATED_AT).to_private_dict()
    receipt["reason_codes"] = ["SNAPSHOT_FILE_ACCESS_UNKNOWN"]
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    with pytest.raises(ValueError, match="BLOCKED receipt"):
        parse_qwen3_tts_pinned_snapshot_verification(receipt)


def test_manifest_and_receipt_are_strict_and_no_effect_fields_cannot_change(tmp_path: Path) -> None:
    manifest, root = _parsed_fixture(tmp_path)
    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False).to_private_dict()
    receipt["model_loaded"] = True
    with pytest.raises(ValueError):
        parse_qwen3_tts_pinned_snapshot_verification(receipt)

    for field in ("snapshot_modified", "persistent_receipt_is_capability", "model_reuse_authorized",
                  "model_load_authorized", "post_return_state_guaranteed",
                  "model_weights_downloaded", "package_installed", "package_imported",
                  "model_loaded", "owner_audio_read", "inference_executed", "firewall_changed"):
        receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False).to_private_dict()
        receipt[field] = not receipt[field]
        with pytest.raises(ValueError):
            parse_qwen3_tts_pinned_snapshot_verification(receipt)

    for field in ("diagnostic_only", "consumer_revalidation_required"):
        receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False).to_private_dict()
        receipt[field] = False
        with pytest.raises(ValueError):
            parse_qwen3_tts_pinned_snapshot_verification(receipt)

    receipt = _verify_manifest(manifest, root, EVALUATED_AT, production=False).to_private_dict()
    receipt["reason_codes"] = ["Z", "A"]
    with pytest.raises(ValueError):
        parse_qwen3_tts_pinned_snapshot_verification(receipt)


def test_diagnostic_receipt_rejects_impossible_phase_and_timestamp_claims() -> None:
    unknown = _accepted_diagnostic_receipt_body()
    unknown.update({"decision": "UNKNOWN", "reason_codes": ["SNAPSHOT_FILE_ACCESS_UNKNOWN"],
                    "filesystem_enumerated": True, "file_bodies_hashed": True})
    with pytest.raises(ValueError, match="unknown observations"):
        parse_qwen3_tts_pinned_snapshot_verification(_rehash_receipt(unknown))

    early = _accepted_diagnostic_receipt_body()
    early.update({"decision": "BLOCKED", "reason_codes": ["SNAPSHOT_ROOT_NOT_ADMITTED"],
                  "filesystem_enumerated": False, "file_bodies_hashed": False})
    with pytest.raises(ValueError, match="pre-observation blockers"):
        parse_qwen3_tts_pinned_snapshot_verification(_rehash_receipt(early))

    timestamp = _accepted_diagnostic_receipt_body()
    timestamp["evaluated_at"] = "nonsenseZ"
    with pytest.raises(ValueError, match="RFC3339 UTC"):
        parse_qwen3_tts_pinned_snapshot_verification(_rehash_receipt(timestamp))


def test_schema_mirror_is_byte_identical_and_json_parseable() -> None:
    root = Path(__file__).parents[1]
    public = root / "schemas" / "qwen3-tts-pinned-snapshot-verification.schema.json"
    mirror = root / "src" / "ai_video_production" / "schema_resources" / public.name
    assert public.read_bytes() == mirror.read_bytes()
    assert json.loads(public.read_text(encoding="utf-8"))["additionalProperties"] is False


def test_draft_schema_enforces_receipt_decision_and_truth_invariants(tmp_path: Path) -> None:
    root_path = Path(__file__).parents[1]
    schema = json.loads((root_path / "schemas" / "qwen3-tts-pinned-snapshot-verification.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    manifest, root = _parsed_fixture(tmp_path)
    base = _verify_manifest(manifest, root, EVALUATED_AT, production=False).to_private_dict()

    verified = dict(base)
    verified.update({"model_id": ACCEPTED_MODEL_ID, "revision": ACCEPTED_REVISION,
        "manifest_entries_sha256": ACCEPTED_ENTRIES_SHA256, "manifest_semantic_sha256": ACCEPTED_SEMANTIC_SHA256,
        "file_count": ACCEPTED_FILE_COUNT, "total_bytes": ACCEPTED_TOTAL_BYTES, "decision": "VERIFIED",
        "reason_codes": [], "snapshot_root_fingerprint": "sha256:" + "a" * 64,
        "filesystem_enumerated": True, "file_bodies_hashed": True, "snapshot_modified": False})
    blocked = dict(base)
    blocked.update({"decision": "BLOCKED", "reason_codes": ["SNAPSHOT_EXTRA_ENTRY"],
                    "filesystem_enumerated": False, "file_bodies_hashed": False, "snapshot_modified": False})
    unknown = dict(base)
    unknown.update({"decision": "UNKNOWN", "reason_codes": ["SNAPSHOT_MODIFIED_DURING_VERIFICATION"],
                    "filesystem_enumerated": False, "file_bodies_hashed": False, "snapshot_modified": True})
    for receipt in (verified, blocked, unknown):
        assert not list(validator.iter_errors(receipt))
    swapped = dict(blocked); swapped["reason_codes"] = ["SNAPSHOT_FILE_ACCESS_UNKNOWN"]
    wrong_pin = dict(verified); wrong_pin["revision"] = "b" * 40
    wrong_flag = dict(verified); wrong_flag["file_bodies_hashed"] = False
    wrong_parity = dict(unknown); wrong_parity["snapshot_modified"] = False
    wrong_authority = dict(verified); wrong_authority["model_reuse_authorized"] = True
    impossible_unknown = dict(unknown); impossible_unknown["filesystem_enumerated"] = True
    early_with_fingerprint = dict(blocked); early_with_fingerprint.update({
        "reason_codes": ["SNAPSHOT_ROOT_NOT_ADMITTED"],
        "snapshot_root_fingerprint": "sha256:" + "b" * 64,
    })
    missing_boundary = dict(verified); missing_boundary.pop("consumer_revalidation_required")
    bad_timestamps = []
    for bad in ("nonsenseZ", "20260821T000000Z", "2026-08-21 00:00:00Z", "2026-08-21T00:00Z"):
        item = dict(verified); item["evaluated_at"] = bad; bad_timestamps.append(item)
    for receipt in (swapped, wrong_pin, wrong_flag, wrong_parity, wrong_authority,
                    impossible_unknown, early_with_fingerprint, missing_boundary, *bad_timestamps):
        assert list(validator.iter_errors(receipt))


def test_no_dangerous_execution_surface() -> None:
    module = Path(__file__).parents[1] / "src" / "ai_video_production" / "qwen3_tts_pinned_snapshot_verifier.py"
    source = module.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "socket", "requests", "urllib", "http.client", "importlib", "torch"):
        assert forbidden not in source
