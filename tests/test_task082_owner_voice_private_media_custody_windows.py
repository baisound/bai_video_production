from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import threading
from typing import Any

import pytest

import ai_video_production.task082_owner_voice_private_media_custody_windows as windows
from ai_video_production.serialization import sha256_bytes
from ai_video_production.task082_owner_voice_private_media_custody import (
    ArtifactClass,
    CurrentnessState,
    ReadPurpose,
    Task082FixtureLeaseSentinel,
    WritePurpose,
    compile_fixture_write_lease_admission,
    derive_generation_currentness,
    mint_fixture_lease_sentinel,
)


def digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


class SyntheticCipher:
    cipher_suite = "TEST_ONLY_TASK082_XOR_SHA256_V1"
    backend_identity_sha256 = digest("synthetic-cipher-backend")

    def __init__(self) -> None:
        self.opened_plaintexts: list[bytearray] = []

    @staticmethod
    def _keystream(entropy: bytes, length: int) -> bytes:
        seed = hashlib.sha256(b"TASK082-TEST" + entropy).digest()
        return bytes(seed[index % len(seed)] for index in range(length))

    def seal(self, plaintext: bytearray, *, entropy: bytes) -> bytes:
        stream = self._keystream(entropy, len(plaintext))
        encrypted = bytes(value ^ stream[index] for index, value in enumerate(plaintext))
        tag = hashlib.sha256(b"TAG" + entropy + encrypted).digest()
        return tag + encrypted

    def open(self, ciphertext: bytes, *, entropy: bytes) -> bytearray:
        tag, encrypted = ciphertext[:32], ciphertext[32:]
        if tag != hashlib.sha256(b"TAG" + entropy + encrypted).digest():
            raise ValueError("synthetic authentication failure")
        stream = self._keystream(entropy, len(encrypted))
        plaintext = bytearray(
            value ^ stream[index] for index, value in enumerate(encrypted)
        )
        self.opened_plaintexts.append(plaintext)
        return plaintext


def root_binding(root: Path, cipher: Any) -> windows.WindowsPrivateMediaRootBinding:
    return windows.WindowsPrivateMediaRootBinding.create(
        root_path_binding_sha256=windows._path_binding_sha256(root),
        root_identity_sha256=windows._root_identity_sha256_from_path(root),
        root_security_sha256=digest("root-security"),
        principal_sid_sha256=digest("principal-sid"),
        cipher_backend_identity_sha256=cipher.backend_identity_sha256,
        observed_at="2026-09-06T00:00:00Z",
        fresh_until="2026-09-06T01:00:00Z",
        h1_authorization_sha256=digest("h1-authorization"),
    )


def backend(
    root: Path,
    *,
    cipher: SyntheticCipher | None = None,
    authorize: Any = True,
    current: Any = True,
    root_authorized: Any = True,
    root_observation_updates: dict[str, Any] | None = None,
    trusted_time_provider: Any = None,
    stage_hook: Any = None,
) -> tuple[
    windows.WindowsPrivateMediaCustodyBackend,
    windows.WindowsPrivateMediaRootBinding,
    SyntheticCipher,
]:
    selected = cipher or SyntheticCipher()
    binding = root_binding(root, selected)

    def flag(value: Any) -> bool:
        return value() if callable(value) else value

    def verify_root(
        observed_root: Path,
        expected: windows.WindowsPrivateMediaRootBinding,
        observed_at: str,
    ) -> windows.WindowsPrivateMediaRootObservation | bool:
        if not flag(root_authorized):
            return False
        assert observed_root == root.resolve()
        assert expected is binding
        values = {
            "root_path_binding_sha256": windows._path_binding_sha256(observed_root),
            "root_identity_sha256": binding.root_identity_sha256,
            "root_security_sha256": binding.root_security_sha256,
            "principal_sid_sha256": binding.principal_sid_sha256,
            "cipher_backend_identity_sha256": binding.cipher_backend_identity_sha256,
            "root_binding_sha256": binding.binding_sha256,
            "observed_at": observed_at,
        }
        values.update(root_observation_updates or {})
        return windows.WindowsPrivateMediaRootObservation.create(**values)

    def reserve_currentness(
        kind: Any,
        operation_id: str,
        grant_sha256: str,
        currentness_binding_sha256: str,
        canonical_head_sha256: str | None,
        acquired_at: str,
        expires_at: str,
    ) -> windows.WindowsPrivateMediaCurrentnessReservationReceipt:
        if not flag(current):
            raise RuntimeError("synthetic currentness changed before CAS")
        return windows.WindowsPrivateMediaCurrentnessReservationReceipt.create(
            lease_kind=kind,
            operation_id=operation_id,
            grant_sha256=grant_sha256,
            currentness_binding_sha256=currentness_binding_sha256,
            canonical_head_sha256=canonical_head_sha256,
            acquired_at=acquired_at,
            expires_at=expires_at,
        )

    value = windows.WindowsPrivateMediaCustodyBackend._for_test(
        root,
        root_binding=binding,
        authorization_verifier=lambda kind, grant_sha256, authorization_sha256: (
            flag(authorize)
            and len(grant_sha256) == 71
            and authorization_sha256
            in {digest("write-authorization"), digest("read-authorization")}
        ),
        currentness_verifier=lambda *_: flag(current),
        currentness_reservation_verifier=reserve_currentness,
        root_binding_verifier=verify_root,
        trusted_time_provider=(
            trusted_time_provider
            if trusted_time_provider is not None
            else lambda: "2026-09-06T00:00:20Z"
        ),
        cipher=selected,
        stage_hook=stage_hook,
    )
    return value, binding, selected


def write_grant(
    private_body: bytes | bytearray,
    binding: windows.WindowsPrivateMediaRootBinding,
    **updates: Any,
) -> windows.WindowsPrivateMediaWriteGrant:
    body = bytes(private_body)
    values: dict[str, Any] = {
        "purpose": WritePurpose.CAPTURE_RAW_PUBLISH,
        "expected_purpose": WritePurpose.CAPTURE_RAW_PUBLISH,
        "producer_task": "TASK-047",
        "producer_output_role": "TASK047_RAW_CAPTURE_OUTPUT",
        "artifact_class": ArtifactClass.RAW_CAPTURE,
        "operation_id": "capture.raw.operation-1",
        "expected_operation_id": "capture.raw.operation-1",
        "logical_slot_ref": "owner.voice.raw.slot-1",
        "generation_revision": 1,
        "expected_generation_revision": 1,
        "event_revision": 1,
        "predecessor_event_sha256": None,
        "predecessor_receipt_sha256": None,
        "owner_subject_revision_sha256": digest("owner-subject"),
        "expected_owner_subject_revision_sha256": digest("owner-subject"),
        "consent_scope": "OWNER_VOICE_CAPTURE",
        "consent_rights_revision_sha256": digest("consent"),
        "expected_consent_rights_revision_sha256": digest("consent"),
        "current_event_head_sha256": None,
        "expected_event_head_sha256": None,
        "producer_output_record_type": "Task047RawCaptureOutputV1",
        "expected_producer_output_record_type": "Task047RawCaptureOutputV1",
        "producer_output_receipt_sha256": digest("producer-receipt"),
        "expected_producer_output_receipt_sha256": digest("producer-receipt"),
        "producer_output_currentness_sha256": digest("producer-currentness"),
        "expected_producer_output_currentness_sha256": digest("producer-currentness"),
        "producer_output_current": True,
        "expected_content_sha256": sha256_bytes(body),
        "media_metadata_sha256": digest("media-metadata"),
        "trusted_time_binding_sha256": digest("trusted-time"),
        "created_at": "2026-09-06T00:00:00Z",
        "issued_at": "2026-09-06T00:00:00Z",
        "expires_at": "2026-09-06T00:30:00Z",
        "observed_at": "2026-09-06T00:00:10Z",
        "fresh_until": "2026-09-06T00:45:00Z",
        "root_binding_sha256": binding.binding_sha256,
        "backend_authorization_sha256": digest("write-authorization"),
        "revoked": False,
        "receipt_as_capability": False,
    }
    values.update(updates)
    return windows.WindowsPrivateMediaWriteGrant(**values)


def published(
    tmp_path: Path,
    payload: bytes | None = None,
) -> tuple[
    windows.WindowsPrivateMediaCustodyBackend,
    windows.WindowsPrivateMediaRootBinding,
    SyntheticCipher,
    windows.WindowsPrivateMediaWriteResult,
]:
    value, binding, cipher = backend(tmp_path)
    body = bytearray(payload or b"synthetic owner voice pcm payload")
    lease = value.issue_write_lease(write_grant(body, binding))
    result = value.publish_private_media(lease, body)
    assert not any(body)
    return value, binding, cipher, result


def read_grant(
    result: windows.WindowsPrivateMediaWriteResult,
    binding: windows.WindowsPrivateMediaRootBinding,
    **updates: Any,
) -> windows.WindowsPrivateMediaReadGrant:
    currentness = derive_generation_currentness(
        [result.generation_event],
        observed_at="2026-09-06T00:00:20Z",
        expected_event_head_sha256=result.generation_event.event_sha256,
        expected_event_count=1,
        expected_current_custody_binding_sha256=(
            result.receipt.custody_binding_sha256
        ),
    )
    assert currentness.state is CurrentnessState.CURRENT
    values: dict[str, Any] = {
        "receipt": result.receipt,
        "currentness": currentness,
        "purpose": ReadPurpose.QUALITY_PROCESSING,
        "expected_purpose": ReadPurpose.QUALITY_PROCESSING,
        "consumer_task": "TASK-048",
        "operation_id": "quality.read.operation-1",
        "expected_operation_id": "quality.read.operation-1",
        "expected_owner_subject_revision_sha256": (
            result.receipt.owner_subject_revision_sha256
        ),
        "expected_consent_rights_revision_sha256": (
            result.receipt.consent_rights_revision_sha256
        ),
        "issued_at": "2026-09-06T00:00:15Z",
        "expires_at": "2026-09-06T00:30:00Z",
        "observed_at": "2026-09-06T00:00:20Z",
        "root_binding_sha256": binding.binding_sha256,
        "backend_authorization_sha256": digest("read-authorization"),
        "asset_adoption_readback_sha256": digest("asset-adoption"),
        "expected_asset_adoption_readback_sha256": digest("asset-adoption"),
        "producer_output_receipt_sha256": digest("q1-output"),
        "expected_producer_output_receipt_sha256": digest("q1-output"),
    }
    values.update(updates)
    return windows.WindowsPrivateMediaReadGrant(**values)


def test_publish_and_consume_two_chunks_is_encrypted_body_free_and_one_use(
    tmp_path: Path,
) -> None:
    payload = b"RIFF" + b"owner-voice-synthetic\x00" * 20_000
    value, binding, cipher, result = published(tmp_path, payload)
    assert result.chunk_count == 2
    assert result.plaintext_byte_count == len(payload)
    assert result.body_zeroization_confirmed is True
    assert result.production_backend_invoked is False
    assert result.private_media_effect_count == 17
    assert result.receipt.generation_event_sha256 == result.generation_event.event_sha256
    assert result.receipt.event_head_sha256 == result.generation_event.event_sha256
    assert result.receipt.custody_binding_sha256 == result.generation_event.custody_binding_sha256
    assert result.receipt.cipher_backend_identity_sha256 == cipher.backend_identity_sha256
    rendered = json.dumps(result.as_dict(), sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "owner-voice-synthetic" not in rendered
    stored = b"".join(path.read_bytes() for path in tmp_path.iterdir() if path.is_file())
    assert payload not in stored

    read_lease = value.issue_read_lease(read_grant(result, binding))
    observed: list[bytes] = []
    read_result = value.consume_private_media(
        read_lease,
        lambda body: observed.append(bytes(body)),
    )
    assert observed == [payload]
    assert read_result.plaintext_byte_count == len(payload)
    assert read_result.body_zeroization_confirmed is True
    assert read_result.callback_completed is True
    assert read_result.production_backend_invoked is False
    assert read_result.private_media_effect_count == 10
    assert value.read_lease_state(read_lease).state is windows.ProductionLeaseState.CONSUMED
    assert all(not any(item) for item in cipher.opened_plaintexts)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.consume_private_media(read_lease, lambda body: None)
    assert caught.value.reason is windows.WindowsBackendReason.REPLAY


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("expected_purpose", WritePurpose.CAPTURE_CANONICAL_PUBLISH),
        ("producer_task", "TASK-048"),
        ("producer_output_role", "TASK047_CANONICAL_PCM_OUTPUT"),
        ("artifact_class", ArtifactClass.CANONICAL_PCM),
        ("expected_operation_id", "other.operation"),
        ("expected_generation_revision", 2),
        ("expected_owner_subject_revision_sha256", digest("wrong-owner")),
        ("expected_consent_rights_revision_sha256", digest("wrong-consent")),
        ("producer_output_current", False),
        ("revoked", True),
        ("receipt_as_capability", True),
    ],
)
def test_write_admission_negatives_are_effect_zero(
    tmp_path: Path,
    field: str,
    replacement: Any,
) -> None:
    value, binding, _ = backend(tmp_path)
    grant = write_grant(b"synthetic", binding, **{field: replacement})
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.issue_write_lease(grant)
    assert caught.value.reason is windows.WindowsBackendReason.ADMISSION_REJECTED
    assert list(tmp_path.iterdir()) == []


def test_wrong_root_or_backend_authorization_is_effect_zero(tmp_path: Path) -> None:
    body = b"synthetic"
    value, binding, _ = backend(tmp_path, root_authorized=False)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.issue_write_lease(write_grant(body, binding))
    assert caught.value.reason is windows.WindowsBackendReason.ROOT_BINDING_MISMATCH
    assert list(tmp_path.iterdir()) == []

    value, binding, _ = backend(tmp_path, authorize=False)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.issue_write_lease(write_grant(body, binding))
    assert caught.value.reason is windows.WindowsBackendReason.AUTHORIZATION_REJECTED
    assert list(tmp_path.iterdir()) == []


def test_stale_tampered_or_wrong_path_root_binding_is_effect_zero(tmp_path: Path) -> None:
    value, binding, _ = backend(tmp_path)
    stale = replace(binding, fresh_until="2026-09-06T00:00:05Z")
    stale_value = windows.WindowsPrivateMediaCustodyBackend._for_test(
        tmp_path,
        root_binding=stale,
        authorization_verifier=lambda *_: True,
        currentness_verifier=lambda *_: True,
        currentness_reservation_verifier=lambda *_: False,
        root_binding_verifier=lambda *_: False,
        trusted_time_provider=lambda: "2026-09-06T00:00:10Z",
        cipher=SyntheticCipher(),
    )
    with pytest.raises(windows.WindowsPrivateMediaBackendError):
        stale_value.issue_write_lease(write_grant(b"synthetic", stale))
    tampered = replace(binding, root_security_sha256=digest("tampered-security"))
    tampered_value = windows.WindowsPrivateMediaCustodyBackend._for_test(
        tmp_path,
        root_binding=tampered,
        authorization_verifier=lambda *_: True,
        currentness_verifier=lambda *_: True,
        currentness_reservation_verifier=lambda *_: False,
        root_binding_verifier=lambda *_: False,
        trusted_time_provider=lambda: "2026-09-06T00:00:10Z",
        cipher=SyntheticCipher(),
    )
    with pytest.raises(windows.WindowsPrivateMediaBackendError):
        tampered_value.issue_write_lease(write_grant(b"synthetic", tampered))
    wrong_path = replace(binding, root_path_binding_sha256=digest("other-root"))
    wrong_value = windows.WindowsPrivateMediaCustodyBackend._for_test(
        tmp_path,
        root_binding=wrong_path,
        authorization_verifier=lambda *_: True,
        currentness_verifier=lambda *_: True,
        currentness_reservation_verifier=lambda *_: False,
        root_binding_verifier=lambda *_: False,
        trusted_time_provider=lambda: "2026-09-06T00:00:10Z",
        cipher=SyntheticCipher(),
    )
    with pytest.raises(windows.WindowsPrivateMediaBackendError):
        wrong_value.issue_write_lease(write_grant(b"synthetic", wrong_path))
    assert list(tmp_path.iterdir()) == []
    assert value.read_lease_state  # keep the valid backend live for exact-root coverage


def test_body_hash_mismatch_burns_durable_open_and_zeroizes(tmp_path: Path) -> None:
    value, binding, _ = backend(tmp_path)
    body = bytearray(b"synthetic-private-body")
    grant = write_grant(body, binding, expected_content_sha256=digest("wrong-body"))
    lease = value.issue_write_lease(grant)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert caught.value.completion_unknown is True
    assert not any(body)
    state = value.read_lease_state(lease)
    assert state.state is windows.ProductionLeaseState.COMPLETION_UNKNOWN
    assert state.replayable is False
    assert state.durable is True
    assert state.issuance_record_sha256 is not None
    assert state.burn_record_sha256 is not None
    assert list(tmp_path.glob("*.issued.json"))
    assert list(tmp_path.glob("*.open.json"))


def test_manifest_stage_fault_is_completion_unknown_nonreplayable_and_zeroized(
    tmp_path: Path,
) -> None:
    def fault(stage: str) -> None:
        if stage == "before_manifest_publish":
            raise RuntimeError("synthetic fault")

    value, binding, _ = backend(tmp_path, stage_hook=fault)
    body = bytearray(b"x" * (windows.CHUNK_PLAINTEXT_BYTES + 1))
    lease = value.issue_write_lease(write_grant(body, binding))
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert caught.value.completion_unknown is True
    assert not any(body)
    state = value.read_lease_state(lease)
    assert state.state is windows.ProductionLeaseState.COMPLETION_UNKNOWN
    assert state.body_returned is False and state.capability_returned is False
    assert not list(tmp_path.glob("*.manifest.json"))
    assert len(list(tmp_path.glob("*.chunk.json"))) == 2
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as replay:
        value.publish_private_media(lease, bytearray(b"different"))
    assert replay.value.reason is windows.WindowsBackendReason.REPLAY


def test_same_bytes_replacement_or_tamper_fails_before_callback(tmp_path: Path) -> None:
    value, binding, _, result = published(tmp_path)
    chunk = next(tmp_path.glob("*.chunk.json"))
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(chunk.read_bytes())
    os.replace(replacement, chunk)
    read_lease = value.issue_read_lease(read_grant(result, binding))
    called: list[bool] = []
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.consume_private_media(read_lease, lambda body: called.append(True))
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert called == []
    assert value.read_lease_state(read_lease).state is (
        windows.ProductionLeaseState.COMPLETION_UNKNOWN
    )


def test_ciphertext_digest_tamper_fails_before_callback(tmp_path: Path) -> None:
    value, binding, _, result = published(tmp_path)
    chunk_path = next(tmp_path.glob("*.chunk.json"))
    document = json.loads(chunk_path.read_text(encoding="utf-8"))
    document["ciphertext_b64"] = base64_value = document["ciphertext_b64"][:-4] + "AAAA"
    assert base64_value
    chunk_path.write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    lease = value.issue_read_lease(read_grant(result, binding))
    called: list[bool] = []
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.consume_private_media(lease, lambda body: called.append(True))
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert called == []


def test_read_admission_wrong_consumer_stale_currentness_or_missing_binding_is_effect_zero(
    tmp_path: Path,
) -> None:
    value, binding, _, result = published(tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}
    for updates in (
        {"consumer_task": "TASK-046"},
        {"expected_owner_subject_revision_sha256": digest("wrong-owner")},
        {"asset_adoption_readback_sha256": None},
        {"producer_output_receipt_sha256": None},
        {"receipt_as_capability": True},
    ):
        with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
            value.issue_read_lease(read_grant(result, binding, **updates))
        assert caught.value.reason is windows.WindowsBackendReason.ADMISSION_REJECTED
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}
    assert after == before


def test_fixture_sentinel_receipt_or_foreign_lease_never_opens_body(tmp_path: Path) -> None:
    value, binding, _, result = published(tmp_path)
    fixture_decision = compile_fixture_write_lease_admission(
        purpose=WritePurpose.CAPTURE_RAW_PUBLISH,
        expected_purpose=WritePurpose.CAPTURE_RAW_PUBLISH,
        producer_task="TASK-047",
        producer_output_role="TASK047_RAW_CAPTURE_OUTPUT",
        artifact_class=ArtifactClass.RAW_CAPTURE,
        operation_id="capture.fixture.operation",
        expected_operation_id="capture.fixture.operation",
        logical_slot_ref="owner.voice.raw.fixture",
        generation_revision=1,
        expected_generation_revision=1,
        owner_subject_revision_sha256=digest("owner"),
        expected_owner_subject_revision_sha256=digest("owner"),
        consent_scope="OWNER_VOICE_CAPTURE",
        consent_rights_revision_sha256=digest("consent-fixture"),
        expected_consent_rights_revision_sha256=digest("consent-fixture"),
        current_event_head_sha256=None,
        expected_event_head_sha256=None,
        producer_output_record_type="Task047RawCaptureOutputV1",
        expected_producer_output_record_type="Task047RawCaptureOutputV1",
        producer_output_receipt_sha256=digest("producer-fixture"),
        expected_producer_output_receipt_sha256=digest("producer-fixture"),
        producer_output_currentness_sha256=digest("current-fixture"),
        expected_producer_output_currentness_sha256=digest("current-fixture"),
        producer_output_current=True,
        issued_at="2026-09-06T00:00:00Z",
        expires_at="2026-09-06T00:30:00Z",
        observed_at="2026-09-06T00:00:10Z",
    )
    sentinel: Task082FixtureLeaseSentinel = mint_fixture_lease_sentinel(fixture_decision)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(sentinel, bytearray(b"synthetic"))  # type: ignore[arg-type]
    assert caught.value.reason is windows.WindowsBackendReason.RECEIPT_AS_CAPABILITY

    other, other_binding, _ = backend(tmp_path)
    foreign = other.issue_read_lease(read_grant(result, other_binding))
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.consume_private_media(foreign, lambda body: None)
    assert caught.value.reason is windows.WindowsBackendReason.RECEIPT_AS_CAPABILITY


def test_leases_are_redacted_nonserializable_and_exact_type_checked(tmp_path: Path) -> None:
    value, binding, _ = backend(tmp_path)
    lease = value.issue_write_lease(write_grant(b"synthetic", binding))
    assert str(tmp_path) not in repr(lease)
    assert "capture.raw.operation-1" not in repr(lease)
    with pytest.raises(TypeError):
        pickle.dumps(lease)
    with pytest.raises(TypeError):
        lease._state = windows.ProductionLeaseState.CONSUMED  # type: ignore[misc]
    with pytest.raises(windows.WindowsPrivateMediaBackendError):
        windows.Task082PrivateMediaWriteLeaseV1(
            object(),
            backend_nonce=object(),
            grant=write_grant(b"synthetic", binding),
            kind=windows.LeaseKind.WRITE,
            issuance_record_sha256=digest("issuance"),
        )


def test_direct_drive_child_or_relative_root_is_rejected_before_effect(tmp_path: Path) -> None:
    cipher = SyntheticCipher()
    root = Path(tmp_path.anchor) / "task082-unsafe-direct-child"
    binding = root_binding(tmp_path, cipher)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        windows.WindowsPrivateMediaCustodyBackend._for_test(
            root,
            root_binding=binding,
            authorization_verifier=lambda *_: True,
            currentness_verifier=lambda *_: True,
            currentness_reservation_verifier=lambda *_: False,
            root_binding_verifier=lambda *_: True,
            trusted_time_provider=lambda: "2026-09-06T00:00:10Z",
            cipher=cipher,
        )
    assert caught.value.reason is windows.WindowsBackendReason.ROOT_UNSAFE


def test_test_cipher_cannot_claim_production_suite(tmp_path: Path) -> None:
    cipher = SyntheticCipher()
    cipher.cipher_suite = windows.WINDOWS_DPAPI_CIPHER_SUITE
    binding = root_binding(tmp_path, cipher)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        windows.WindowsPrivateMediaCustodyBackend._for_test(
            tmp_path,
            root_binding=binding,
            authorization_verifier=lambda *_: True,
            currentness_verifier=lambda *_: True,
            currentness_reservation_verifier=lambda *_: False,
            root_binding_verifier=lambda *_: True,
            trusted_time_provider=lambda: "2026-09-06T00:00:10Z",
            cipher=cipher,
        )
    assert caught.value.reason is windows.WindowsBackendReason.CIPHER_REJECTED

    identity_alias = SyntheticCipher()
    identity_alias.backend_identity_sha256 = (
        windows.WINDOWS_DPAPI_BACKEND_IDENTITY_SHA256
    )
    alias_binding = root_binding(tmp_path, identity_alias)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as alias:
        windows.WindowsPrivateMediaCustodyBackend._for_test(
            tmp_path,
            root_binding=alias_binding,
            authorization_verifier=lambda *_: True,
            currentness_verifier=lambda *_: True,
            currentness_reservation_verifier=lambda *_: False,
            root_binding_verifier=lambda *_: True,
            trusted_time_provider=lambda: "2026-09-06T00:00:10Z",
            cipher=identity_alias,
        )
    assert alias.value.reason is windows.WindowsBackendReason.CIPHER_REJECTED


def test_public_results_and_errors_never_include_body_path_key_or_capability(
    tmp_path: Path,
) -> None:
    value, binding, _, result = published(tmp_path)
    read = value.issue_read_lease(read_grant(result, binding))
    read_result = value.consume_private_media(read, lambda body: None)
    rendered = json.dumps(
        {"write": result.as_dict(), "read": read_result.as_dict()},
        sort_keys=True,
    )
    for forbidden in (
        str(tmp_path),
        "ciphertext_b64",
        "private_body",
        "speaker_fingerprint",
        "key_material",
        "capability",
    ):
        assert forbidden not in rendered
    error = windows.WindowsPrivateMediaBackendError(
        windows.WindowsBackendReason.READ_FAILED
    )
    assert str(error) == "READ_FAILED"
    assert repr(value) == "<WindowsPrivateMediaCustodyBackend root=redacted>"


def test_durable_one_use_state_survives_backend_restart(tmp_path: Path) -> None:
    payload = b"synthetic durable owner voice"
    value, binding, cipher, result = published(tmp_path, payload)
    exact_write_grant = write_grant(payload, binding)
    write_state = value.read_durable_lease_state(exact_write_grant)
    assert write_state.state is windows.ProductionLeaseState.CONSUMED
    assert write_state.replayable is False
    assert write_state.issuance_record_sha256 is not None
    assert write_state.burn_record_sha256 is not None
    assert write_state.completion_record_sha256 is not None

    restarted, restarted_binding, _ = backend(tmp_path, cipher=cipher)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as duplicate_write:
        restarted.issue_write_lease(write_grant(payload, restarted_binding))
    assert duplicate_write.value.reason is windows.WindowsBackendReason.REPLAY
    restarted_write_state = restarted.read_durable_lease_state(
        write_grant(payload, restarted_binding)
    )
    assert restarted_write_state.as_dict() == write_state.as_dict()

    exact_read_grant = read_grant(result, binding)
    read_lease = value.issue_read_lease(exact_read_grant)
    value.consume_private_media(read_lease, lambda body: None)
    read_state = value.read_durable_lease_state(exact_read_grant)
    assert read_state.state is windows.ProductionLeaseState.CONSUMED

    restarted_again, restarted_again_binding, _ = backend(tmp_path, cipher=cipher)
    duplicate_read_grant = read_grant(result, restarted_again_binding)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as duplicate_read:
        restarted_again.issue_read_lease(duplicate_read_grant)
    assert duplicate_read.value.reason is windows.WindowsBackendReason.REPLAY
    assert (
        restarted_again.read_durable_lease_state(duplicate_read_grant).as_dict()
        == read_state.as_dict()
    )


def test_durable_ledger_same_bytes_replacement_is_completion_unknown(
    tmp_path: Path,
) -> None:
    payload = b"synthetic durable ledger identity"
    value, binding, _, _ = published(tmp_path, payload)
    issue_path = next(tmp_path.glob("*.issued.json"))
    replacement = tmp_path / "same-issuance-bytes.json"
    replacement.write_bytes(issue_path.read_bytes())
    os.replace(replacement, issue_path)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.read_durable_lease_state(write_grant(payload, binding))
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert caught.value.completion_unknown is True


def test_write_recovery_same_bytes_replacement_is_completion_unknown(
    tmp_path: Path,
) -> None:
    payload = b"synthetic recovery identity"
    value, binding, _, _ = published(tmp_path, payload)
    recovery_path = next(tmp_path.glob("*.write-result.json"))
    replacement = tmp_path / "same-recovery-bytes.json"
    replacement.write_bytes(recovery_path.read_bytes())
    os.replace(replacement, recovery_path)
    grant = write_grant(payload, binding)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.read_durable_write_result(grant)
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert caught.value.completion_unknown is True


def test_same_grant_concurrent_issue_mints_one_capability(tmp_path: Path) -> None:
    value, binding, _ = backend(tmp_path)
    grant = write_grant(b"synthetic concurrent issue", binding)
    start = threading.Barrier(3)

    def issue() -> tuple[str, Any]:
        start.wait()
        try:
            return "LEASE", value.issue_write_lease(grant)
        except windows.WindowsPrivateMediaBackendError as exc:
            return "ERROR", exc.reason

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(issue) for _ in range(2)]
        start.wait()
        outcomes = [future.result() for future in futures]
    assert [kind for kind, _ in outcomes].count("LEASE") == 1
    assert outcomes.count(("ERROR", windows.WindowsBackendReason.REPLAY)) == 1


def test_same_read_lease_concurrent_consume_opens_body_once(tmp_path: Path) -> None:
    value, binding, _, result = published(tmp_path)
    lease = value.issue_read_lease(read_grant(result, binding))
    start = threading.Barrier(3)
    callback_count = 0
    callback_lock = threading.Lock()

    def consume() -> tuple[str, Any]:
        nonlocal callback_count
        start.wait()

        def callback(body: memoryview) -> None:
            nonlocal callback_count
            with callback_lock:
                callback_count += 1

        try:
            value.consume_private_media(lease, callback)
            return "OK", None
        except windows.WindowsPrivateMediaBackendError as exc:
            return "ERROR", exc.reason

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(consume) for _ in range(2)]
        start.wait()
        outcomes = [future.result() for future in futures]
    assert outcomes.count(("OK", None)) == 1
    assert outcomes.count(("ERROR", windows.WindowsBackendReason.REPLAY)) == 1
    assert callback_count == 1


def test_concurrent_same_slot_generation_is_durable_cas(tmp_path: Path) -> None:
    value, binding, _ = backend(tmp_path)
    bodies = [bytearray(b"slot generation A"), bytearray(b"slot generation B")]
    first = write_grant(
        bodies[0],
        binding,
        operation_id="capture.raw.slot-cas-a",
        expected_operation_id="capture.raw.slot-cas-a",
    )
    second = write_grant(
        bodies[1],
        binding,
        operation_id="capture.raw.slot-cas-b",
        expected_operation_id="capture.raw.slot-cas-b",
    )
    leases = [value.issue_write_lease(first), value.issue_write_lease(second)]
    grants = [first, second]
    start = threading.Barrier(3)

    def publish(index: int) -> tuple[str, Any]:
        start.wait()
        try:
            result = value.publish_private_media(leases[index], bodies[index])
            return "OK", result.receipt.receipt_sha256
        except windows.WindowsPrivateMediaBackendError as exc:
            return "ERROR", exc.reason

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish, index) for index in range(2)]
        start.wait()
        outcomes = [future.result() for future in futures]
    assert [kind for kind, _ in outcomes].count("OK") == 1, outcomes
    assert outcomes.count(("ERROR", windows.WindowsBackendReason.COMPLETION_UNKNOWN)) == 1
    assert all(not any(body) for body in bodies)
    assert len(list(tmp_path.glob("*.reservation.json"))) == 1
    assert len(list(tmp_path.glob("*.manifest.json"))) == 1
    local_states = [value.read_lease_state(lease).state for lease in leases]
    assert sorted(state.value for state in local_states) == [
        windows.ProductionLeaseState.COMPLETION_UNKNOWN.value,
        windows.ProductionLeaseState.CONSUMED.value,
    ]
    durable_states = [
        value.read_durable_lease_state(grant).state for grant in grants
    ]
    assert windows.ProductionLeaseState.CONSUMED in durable_states
    assert all(state is not windows.ProductionLeaseState.OPEN_STARTED for state in durable_states)


def test_open_revalidates_expiry_authorization_currentness_and_root(
    tmp_path: Path,
) -> None:
    expiry_root = tmp_path / "expiry"
    expiry_root.mkdir()
    now = ["2026-09-06T00:00:20Z"]
    value, binding, _ = backend(
        expiry_root,
        trusted_time_provider=lambda: now[0],
    )
    body = bytearray(b"expiry body")
    lease = value.issue_write_lease(write_grant(body, binding))
    now[0] = "2026-09-06T00:30:00Z"
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as expired:
        value.publish_private_media(lease, body)
    assert expired.value.reason is windows.WindowsBackendReason.AUTHORIZATION_REJECTED
    assert not any(body)
    assert not list(expiry_root.glob("*.open.json"))

    for gate in ("authorization", "root"):
        root = tmp_path / gate
        root.mkdir()
        flags = {"authorization": True, "root": True}
        current_value, current_binding, _ = backend(
            root,
            authorize=lambda: flags["authorization"],
            root_authorized=lambda: flags["root"],
        )
        current_body = bytearray(gate.encode("ascii"))
        current_lease = current_value.issue_write_lease(
            write_grant(current_body, current_binding)
        )
        flags[gate] = False
        with pytest.raises(windows.WindowsPrivateMediaBackendError) as rejected:
            current_value.publish_private_media(current_lease, current_body)
        assert rejected.value.reason in {
            windows.WindowsBackendReason.AUTHORIZATION_REJECTED,
            windows.WindowsBackendReason.ROOT_BINDING_MISMATCH,
        }
        assert not any(current_body)
        assert not list(root.glob("*.open.json"))

    current_root = tmp_path / "currentness"
    current_root.mkdir()
    is_current = [True]
    current_value, current_binding, _ = backend(
        current_root,
        current=lambda: is_current[0],
    )
    publish_body = bytearray(b"currentness source")
    publish_lease = current_value.issue_write_lease(
        write_grant(publish_body, current_binding)
    )
    result = current_value.publish_private_media(publish_lease, publish_body)
    read = read_grant(result, current_binding)
    read_lease = current_value.issue_read_lease(read)
    is_current[0] = False
    called: list[bool] = []
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as superseded:
        current_value.consume_private_media(
            read_lease,
            lambda body: called.append(True),
        )
    assert superseded.value.reason is windows.WindowsBackendReason.AUTHORIZATION_REJECTED
    assert called == []


def test_write_open_revalidates_grant_freshness_before_private_effect(
    tmp_path: Path,
) -> None:
    now = ["2026-09-06T00:00:20Z"]
    value, binding, _ = backend(
        tmp_path,
        trusted_time_provider=lambda: now[0],
    )
    body = bytearray(b"write freshness race")
    grant = write_grant(
        body,
        binding,
        fresh_until="2026-09-06T00:05:00Z",
    )
    lease = value.issue_write_lease(grant)
    before_open = set(tmp_path.glob("*.open.json"))

    now[0] = "2026-09-06T00:05:00Z"
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as stale:
        value.publish_private_media(lease, body)

    assert stale.value.reason is windows.WindowsBackendReason.AUTHORIZATION_REJECTED
    assert not any(body)
    assert set(tmp_path.glob("*.open.json")) == before_open
    assert not list(tmp_path.glob("*.manifest.json"))


def test_read_open_revalidates_receipt_freshness_before_body_access(
    tmp_path: Path,
) -> None:
    now = ["2026-09-06T00:00:20Z"]
    value, binding, _ = backend(
        tmp_path,
        trusted_time_provider=lambda: now[0],
    )
    body = bytearray(b"read freshness race")
    write = write_grant(
        body,
        binding,
        fresh_until="2026-09-06T00:05:00Z",
    )
    write_lease = value.issue_write_lease(write)
    result = value.publish_private_media(write_lease, body)
    read = read_grant(result, binding)
    read_lease = value.issue_read_lease(read)
    before_open = set(tmp_path.glob("*.open.json"))
    called: list[bool] = []

    now[0] = "2026-09-06T00:05:00Z"
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as stale:
        value.consume_private_media(read_lease, lambda private: called.append(bool(private)))

    assert stale.value.reason is windows.WindowsBackendReason.AUTHORIZATION_REJECTED
    assert called == []
    assert set(tmp_path.glob("*.open.json")) == before_open


def test_publish_readback_same_bytes_replacement_is_not_success(tmp_path: Path) -> None:
    replaced = False

    def replace_after_publish(stage: str) -> None:
        nonlocal replaced
        if stage == "after_chunk_publish_before_readback_0" and not replaced:
            replaced = True
            chunk_path = next(tmp_path.glob("*.chunk.json"))
            replacement = tmp_path / "same-bytes-replacement.json"
            replacement.write_bytes(chunk_path.read_bytes())
            os.replace(replacement, chunk_path)

    value, binding, _ = backend(tmp_path, stage_hook=replace_after_publish)
    body = bytearray(b"same bytes replacement")
    lease = value.issue_write_lease(write_grant(body, binding))
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert replaced is True
    assert not any(body)


def test_callback_failure_and_completion_fault_are_nonreplayable(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "callback"
    source_root.mkdir()
    value, binding, cipher, result = published(source_root)
    read = value.issue_read_lease(read_grant(result, binding))

    def reject_body(body: memoryview) -> None:
        raise RuntimeError("synthetic callback rejection")

    with pytest.raises(windows.WindowsPrivateMediaBackendError) as callback_error:
        value.consume_private_media(read, reject_body)
    assert callback_error.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert value.read_lease_state(read).state is (
        windows.ProductionLeaseState.COMPLETION_UNKNOWN
    )
    assert all(not any(item) for item in cipher.opened_plaintexts)

    completion_root = tmp_path / "completion"
    completion_root.mkdir()
    producer, producer_binding, producer_cipher, produced = published(completion_root)

    def fail_completion(stage: str) -> None:
        if stage == "before_durable_lease_completion":
            raise RuntimeError("synthetic lost completion reply")

    reader, reader_binding, _ = backend(
        completion_root,
        cipher=producer_cipher,
        stage_hook=fail_completion,
    )
    read_grant_value = read_grant(produced, reader_binding)
    read_lease = reader.issue_read_lease(read_grant_value)
    callback_count = 0

    def consume_once(body: memoryview) -> None:
        nonlocal callback_count
        callback_count += 1

    with pytest.raises(windows.WindowsPrivateMediaBackendError) as lost_reply:
        reader.consume_private_media(read_lease, consume_once)
    assert lost_reply.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert callback_count == 1
    durable = reader.read_durable_lease_state(read_grant_value)
    assert durable.state is windows.ProductionLeaseState.COMPLETION_UNKNOWN
    assert durable.replayable is False
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as replay:
        reader.consume_private_media(read_lease, consume_once)
    assert replay.value.reason is windows.WindowsBackendReason.REPLAY
    assert callback_count == 1


def test_open_publish_success_then_readback_fault_is_durable_unknown(
    tmp_path: Path,
) -> None:
    record_readbacks = 0

    def fault(stage: str) -> None:
        nonlocal record_readbacks
        if stage == "after_record_publish_before_readback":
            record_readbacks += 1
            if record_readbacks == 2:
                raise RuntimeError("synthetic lost open readback")

    value, binding, _ = backend(tmp_path, stage_hook=fault)
    body = bytearray(b"synthetic open burn fault")
    grant = write_grant(body, binding)
    lease = value.issue_write_lease(grant)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert caught.value.completion_unknown is True
    assert not any(body)
    assert len(list(tmp_path.glob("*.open.json"))) == 1
    assert not list(tmp_path.glob("*.reservation.json"))
    durable = value.read_durable_lease_state(grant)
    assert durable.state is windows.ProductionLeaseState.COMPLETION_UNKNOWN
    assert durable.burn_record_sha256 is not None
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as replay:
        value.publish_private_media(lease, bytearray(b"synthetic replay"))
    assert replay.value.reason is windows.WindowsBackendReason.REPLAY


def test_head_change_between_live_check_and_cas_fails_before_open(
    tmp_path: Path,
) -> None:
    state = {"current": True}

    def fault(stage: str) -> None:
        if stage == "before_currentness_cas_reservation":
            state["current"] = False

    value, binding, _ = backend(
        tmp_path,
        current=lambda: state["current"],
        stage_hook=fault,
    )
    body = bytearray(b"synthetic currentness race")
    lease = value.issue_write_lease(write_grant(body, binding))
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.AUTHORIZATION_REJECTED
    assert not any(body)
    assert not list(tmp_path.glob("*.open.json"))
    assert not list(tmp_path.glob("*.reservation.json"))
    assert not list(tmp_path.glob("*.manifest.json"))
    state_readback = value.read_lease_state(lease)
    assert state_readback.state is windows.ProductionLeaseState.ISSUED
    assert state_readback.replayable is False


def test_live_root_observation_drift_fails_under_writer_pin(
    tmp_path: Path,
) -> None:
    observed_updates: dict[str, Any] = {}
    value, binding, _ = backend(
        tmp_path,
        root_observation_updates=observed_updates,
    )
    body = bytearray(b"synthetic root drift")
    lease = value.issue_write_lease(write_grant(body, binding))
    observed_updates["root_security_sha256"] = digest("drifted-root-security")
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.ROOT_BINDING_MISMATCH
    assert not any(body)
    assert not list(tmp_path.glob("*.open.json"))
    assert not list(tmp_path.glob("*.manifest.json"))


def _replace_custody_root(root: Path) -> Path:
    """Replace the authority-root name with a distinct physical directory."""
    displaced = root.with_name(root.name + "-displaced")
    replacement = root.with_name(root.name + "-replacement")
    replacement.mkdir()
    os.replace(root, displaced)
    os.replace(replacement, root)
    return displaced


def test_root_replacement_after_issuance_is_rejected_before_private_publish(
    tmp_path: Path,
) -> None:
    custody_root = tmp_path / "custody"
    custody_root.mkdir()
    value, binding, _ = backend(custody_root)
    body = bytearray(b"synthetic root replacement after issuance")
    lease = value.issue_write_lease(write_grant(body, binding))
    displaced = _replace_custody_root(custody_root)

    with pytest.raises(windows.WindowsPrivateMediaBackendError) as rejected:
        value.publish_private_media(lease, body)

    assert rejected.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert not any(body)
    assert not list(custody_root.glob("*.chunk.json"))
    assert not list(custody_root.glob("*.manifest.json"))
    assert list(displaced.glob("*.issued.json"))


def test_replaced_root_with_copied_durable_graph_is_not_a_trusted_readback(
    tmp_path: Path,
) -> None:
    custody_root = tmp_path / "custody"
    custody_root.mkdir()
    value, binding, _cipher, result = published(custody_root)
    grant = write_grant(b"synthetic owner voice pcm payload", binding)
    replacement = custody_root.with_name(custody_root.name + "-replacement")
    shutil.copytree(custody_root, replacement)
    displaced = custody_root.with_name(custody_root.name + "-displaced")
    os.replace(custody_root, displaced)
    os.replace(replacement, custody_root)

    with pytest.raises(windows.WindowsPrivateMediaBackendError) as rejected:
        value.read_durable_lease_state(grant)

    assert rejected.value.reason is windows.WindowsBackendReason.ROOT_BINDING_MISMATCH
    assert result.receipt.opaque_artifact_id
    assert list(custody_root.glob("*.manifest.json"))


def test_write_completion_lost_reply_recovers_typed_body_free_result(
    tmp_path: Path,
) -> None:
    completion_started = False

    def fault(stage: str) -> None:
        nonlocal completion_started
        if stage == "before_durable_lease_completion":
            completion_started = True
        elif completion_started and stage == "after_record_publish_before_readback":
            raise RuntimeError("synthetic lost completion reply")

    payload = b"synthetic recoverable write result"
    value, binding, cipher = backend(tmp_path, stage_hook=fault)
    body = bytearray(payload)
    grant = write_grant(body, binding)
    lease = value.issue_write_lease(grant)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as caught:
        value.publish_private_media(lease, body)
    assert caught.value.reason is windows.WindowsBackendReason.COMPLETION_UNKNOWN
    assert not any(body)
    assert len(list(tmp_path.glob("*.write-result.json"))) == 1
    assert len(list(tmp_path.glob("*.completion.json"))) == 1

    restarted, restarted_binding, _ = backend(tmp_path, cipher=cipher)
    restarted_grant = write_grant(payload, restarted_binding)
    durable = restarted.read_durable_lease_state(restarted_grant)
    assert durable.state is windows.ProductionLeaseState.CONSUMED
    assert durable.write_recovery_record_sha256 is not None
    recovered = restarted.read_durable_write_result(restarted_grant)
    assert recovered.receipt.content_sha256 == sha256_bytes(payload)
    assert recovered.generation_event.event_sha256 == (
        recovered.receipt.generation_event_sha256
    )
    assert recovered.body_zeroization_confirmed is True
    assert "private_body" not in json.dumps(recovered.as_dict(), sort_keys=True)
    with pytest.raises(windows.WindowsPrivateMediaBackendError) as duplicate:
        restarted.issue_write_lease(restarted_grant)
    assert duplicate.value.reason is windows.WindowsBackendReason.REPLAY


@pytest.mark.skipif(os.name != "nt", reason="Windows Current User DPAPI only")
def test_windows_current_user_dpapi_round_trip_and_zeroizable_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cipher = windows.WindowsCurrentUserDpapiPrivateMediaCipher()
    original = bytearray(b"synthetic-task082-dpapi-smoke")
    entropy = bytes.fromhex(digest("dpapi-entropy").removeprefix("sha256:"))
    ciphertext = cipher.seal(original, entropy=entropy)
    assert ciphertext and bytes(original) not in ciphertext
    native_memset = windows.ctypes.memset
    native_wipes: list[tuple[int, int]] = []

    def observe_wipe(target: Any, value: int, count: int) -> Any:
        native_wipes.append((value, int(count)))
        return native_memset(target, value, count)

    monkeypatch.setattr(windows.ctypes, "memset", observe_wipe)
    plaintext = cipher.open(ciphertext, entropy=entropy)
    assert plaintext == original
    assert (0, len(original)) in native_wipes
    assert windows._zeroize(plaintext) is True
    assert not any(plaintext)


@pytest.mark.skipif(os.name != "nt", reason="Windows Current User DPAPI only")
def test_windows_production_backend_dpapi_synthetic_round_trip(tmp_path: Path) -> None:
    cipher = windows.WindowsCurrentUserDpapiPrivateMediaCipher()
    binding = root_binding(tmp_path, cipher)

    def observe_root(
        observed_root: Path,
        expected: windows.WindowsPrivateMediaRootBinding,
        observed_at: str,
    ) -> windows.WindowsPrivateMediaRootObservation:
        assert observed_root == tmp_path.resolve()
        assert expected is binding
        return windows.WindowsPrivateMediaRootObservation.create(
            root_path_binding_sha256=windows._path_binding_sha256(observed_root),
            root_identity_sha256=binding.root_identity_sha256,
            root_security_sha256=binding.root_security_sha256,
            principal_sid_sha256=binding.principal_sid_sha256,
            cipher_backend_identity_sha256=binding.cipher_backend_identity_sha256,
            root_binding_sha256=binding.binding_sha256,
            observed_at=observed_at,
        )

    def reserve_currentness(
        kind: Any,
        operation_id: str,
        grant_sha256: str,
        currentness_binding_sha256: str,
        canonical_head_sha256: str | None,
        acquired_at: str,
        expires_at: str,
    ) -> windows.WindowsPrivateMediaCurrentnessReservationReceipt:
        return windows.WindowsPrivateMediaCurrentnessReservationReceipt.create(
            lease_kind=kind,
            operation_id=operation_id,
            grant_sha256=grant_sha256,
            currentness_binding_sha256=currentness_binding_sha256,
            canonical_head_sha256=canonical_head_sha256,
            acquired_at=acquired_at,
            expires_at=expires_at,
        )

    value = windows.WindowsPrivateMediaCustodyBackend(
        tmp_path,
        root_binding=binding,
        authorization_verifier=lambda kind, grant_sha256, authorization_sha256: (
            len(grant_sha256) == 71
            and authorization_sha256
            in {digest("write-authorization"), digest("read-authorization")}
        ),
        currentness_verifier=lambda *_: True,
        currentness_reservation_verifier=reserve_currentness,
        root_binding_verifier=observe_root,
        trusted_time_provider=lambda: "2026-09-06T00:00:20Z",
    )
    payload = b"synthetic production dpapi body"
    body = bytearray(payload)
    write = value.issue_write_lease(write_grant(body, binding))
    result = value.publish_private_media(write, body)
    assert result.production_backend_invoked is True
    assert not any(body)
    assert payload not in b"".join(
        path.read_bytes() for path in tmp_path.iterdir() if path.is_file()
    )
    observed: list[bytes] = []
    read = value.issue_read_lease(read_grant(result, binding))
    read_result = value.consume_private_media(
        read,
        lambda private_body: observed.append(bytes(private_body)),
    )
    assert observed == [payload]
    assert read_result.production_backend_invoked is True
    assert value.read_durable_lease_state(read_grant(result, binding)).state is (
        windows.ProductionLeaseState.CONSUMED
    )


def test_exact_allowed_files_and_source_has_no_external_or_model_route() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "src/ai_video_production/task082_owner_voice_private_media_custody_windows.py"
    test = root / "tests/test_task082_owner_voice_private_media_custody_windows.py"
    assert source.is_file() and test.is_file()
    text = source.read_text(encoding="utf-8")
    for forbidden in (
        "requests.",
        "urllib",
        "subprocess",
        "socket.",
        "openai",
        "provider_execution",
        "obs_websocket",
        "obsws",
        "model.download",
        "Path.home",
        "expanduser",
    ):
        assert forbidden not in text
    assert "publish_json_noreplace" in text
    assert "read_json" in text
    assert "SecureAuthorityIO" in text
    assert "Task082FixtureLeaseSentinel" in text
    assert "COMPLETION_UNKNOWN" in text
    assert "WINDOWS_CURRENT_USER_DPAPI_TASK082_MEDIA_V1" in text
