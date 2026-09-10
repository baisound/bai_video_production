from __future__ import annotations

import ast
import copy
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import pickle
from collections.abc import Iterator, Mapping

import pytest

from ai_video_production.voice_quality_meter_display_policy import (
    DECISION_DIGEST_DOMAIN,
    FixtureMeterDisplayCurrentnessSeal,
    MeterDisplayBand,
    MeterDisplayDecision,
    MeterDisplayPolicyBinding,
    MeterDisplayPolicyError,
    MeterDisplayPolicyRevision,
    MeterDisplayReason,
    PeakObservationState,
    PolicyBindingState,
    UNCONFIRMED_LABEL,
    compile_fixture_meter_display_currentness,
    compile_meter_display,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]


def h(value: str) -> str:
    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


def rehash_decision(document: dict[str, object]) -> None:
    body = dict(document)
    body.pop("decision_sha256")
    document["decision_sha256"] = sha256_bytes(
        DECISION_DIGEST_DOMAIN + canonical_json_bytes(body)
    )


def policy(*, revision: int = 1, predecessor: str | None = None) -> MeterDisplayPolicyRevision:
    return MeterDisplayPolicyRevision(
        policy_ref="owner-voice-meter-policy",
        policy_revision=revision,
        predecessor_policy_sha256=predecessor,
        target_floor_dbfs=-24.0,
        target_ceiling_dbfs=-12.0,
        warning_dbfs=-1.0,
        true_clip_dbfs=0.0,
    )


def binding(
    state: PolicyBindingState = PolicyBindingState.FIXTURE_BOUND_VERIFIED,
    *,
    document: dict[str, object] | None = None,
) -> MeterDisplayPolicyBinding:
    if state is PolicyBindingState.NOT_BOUND:
        return MeterDisplayPolicyBinding(state, None, None, None, None, None)
    value = document or policy().to_dict()
    if state is PolicyBindingState.FIXTURE_BOUND_VERIFIED:
        seal = compile_fixture_meter_display_currentness(
            policy_document=value,
            current_head_document=value,
        )
        return MeterDisplayPolicyBinding.from_fixture_seal(seal=seal)
    return MeterDisplayPolicyBinding(
        state,
        value["policy_ref"],
        value["policy_revision"],
        value["predecessor_policy_sha256"],
        value["policy_revision_sha256"],
        h("currentness"),
    )


def compile_peak(
    peak: float | None,
    *,
    samples: int = 48_000,
    state: PolicyBindingState = PolicyBindingState.FIXTURE_BOUND_VERIFIED,
) -> MeterDisplayDecision:
    document = None if state is PolicyBindingState.NOT_BOUND else policy().to_dict()
    return compile_meter_display(
        policy_document=document,
        binding=binding(state, document=document),
        sample_peak_dbfs=peak,
        measured_sample_values=samples,
    )


@pytest.mark.parametrize(
    "peak,band,label",
    [
        (None, MeterDisplayBand.BELOW_TARGET, "目標未満"),
        (-60.0, MeterDisplayBand.BELOW_TARGET, "目標未満"),
        (-24.0, MeterDisplayBand.TARGET, "目標範囲"),
        (-12.0, MeterDisplayBand.TARGET, "目標範囲"),
        (-11.9, MeterDisplayBand.ABOVE_TARGET, "目標超過"),
        (-1.0, MeterDisplayBand.WARNING, "警告"),
        (-0.5, MeterDisplayBand.WARNING, "警告"),
        (0.0, MeterDisplayBand.TRUE_CLIP, "クリップ"),
    ],
)
def test_current_policy_classifies_required_meter_vectors(
    peak: float | None, band: MeterDisplayBand, label: str
) -> None:
    result = compile_peak(peak)
    assert result.display_band is band
    assert result.operator_label == label
    assert result.policy_currentness_confirmed is False
    assert result.fixture_policy_currentness_matched is True
    assert result.thresholds_available is True
    assert result.reason_codes == ()
    assert result.observation_state is (
        PeakObservationState.MEASURED_LINEAR_ZERO
        if peak is None
        else PeakObservationState.MEASURED
    )


@pytest.mark.parametrize(
    "state,reason",
    [
        (PolicyBindingState.NOT_BOUND, MeterDisplayReason.POLICY_NOT_BOUND),
        (PolicyBindingState.STALE, MeterDisplayReason.POLICY_STALE),
        (PolicyBindingState.REVOKED, MeterDisplayReason.POLICY_REVOKED),
        (PolicyBindingState.MISMATCH, MeterDisplayReason.POLICY_MISMATCH),
    ],
)
def test_noncurrent_policy_suppresses_threshold_labels_without_blocking_capture(
    state: PolicyBindingState, reason: MeterDisplayReason
) -> None:
    result = compile_peak(-12.0, state=state)
    value = result.to_dict()
    assert result.display_band is MeterDisplayBand.UNCONFIRMED
    assert result.operator_label == UNCONFIRMED_LABEL
    assert result.reason_codes == (reason,)
    assert result.policy_currentness_confirmed is False
    assert result.fixture_policy_currentness_matched is False
    assert result.thresholds_available is False
    assert all(
        value[name] is None
        for name in (
            "target_floor_dbfs",
            "target_ceiling_dbfs",
            "warning_dbfs",
            "true_clip_dbfs",
        )
    )
    assert value["capture_transport_blocked"] is False
    assert value["emergency_stop_blocked"] is False


@pytest.mark.parametrize(
    "state,reason",
    [
        (PolicyBindingState.STALE, MeterDisplayReason.POLICY_STALE),
        (PolicyBindingState.REVOKED, MeterDisplayReason.POLICY_REVOKED),
        (PolicyBindingState.MISMATCH, MeterDisplayReason.POLICY_MISMATCH),
    ],
)
def test_noncurrent_binding_reason_precedes_missing_policy_document(
    state: PolicyBindingState, reason: MeterDisplayReason
) -> None:
    result = compile_meter_display(
        policy_document=None,
        binding=binding(state),
        sample_peak_dbfs=-12.0,
        measured_sample_values=100,
    )
    assert result.reason_codes == (reason,)
    assert result.thresholds_available is False


@pytest.mark.parametrize("peak", [float("nan"), float("inf"), float("-inf"), 0.01])
def test_invalid_meter_scalar_fails_to_unconfirmed_without_serializing_it(peak: float) -> None:
    result = compile_peak(peak)
    assert result.display_band is MeterDisplayBand.UNCONFIRMED
    assert result.operator_label == UNCONFIRMED_LABEL
    assert result.reason_codes == (MeterDisplayReason.INVALID_METER_SCALAR,)
    assert result.sample_peak_dbfs is None
    assert result.measured_sample_values == 48_000
    assert result.thresholds_available is True
    assert result.fixture_policy_currentness_matched is True
    assert peak.__repr__() not in json.dumps(result.to_dict(), ensure_ascii=False)


def test_insufficient_input_is_not_treated_as_measured_silence() -> None:
    result = compile_peak(None, samples=0)
    assert result.observation_state is PeakObservationState.INSUFFICIENT_INPUT
    assert result.display_band is MeterDisplayBand.UNCONFIRMED
    assert result.reason_codes == (MeterDisplayReason.INSUFFICIENT_INPUT,)
    assert result.thresholds_available is True
    assert result.fixture_policy_currentness_matched is True


def test_policy_thresholds_are_revision_data_not_module_constants() -> None:
    custom = MeterDisplayPolicyRevision(
        policy_ref="custom-meter-policy",
        policy_revision=1,
        predecessor_policy_sha256=None,
        target_floor_dbfs=-30.0,
        target_ceiling_dbfs=-18.0,
        warning_dbfs=-3.0,
        true_clip_dbfs=-0.1,
    ).to_dict()
    result = compile_meter_display(
        policy_document=custom,
        binding=binding(document=custom),
        sample_peak_dbfs=-2.0,
        measured_sample_values=100,
    )
    assert result.display_band is MeterDisplayBand.WARNING
    assert result.target_floor_dbfs == -30.0
    assert result.true_clip_dbfs == -0.1


@pytest.mark.parametrize(
    "updates",
    [
        {"target_floor_dbfs": -12.0},
        {"target_ceiling_dbfs": -24.0},
        {"warning_dbfs": -12.0},
        {"true_clip_dbfs": -1.0},
        {"true_clip_dbfs": 0.1},
        {"target_floor_dbfs": float("nan")},
        {"policy_revision": True},
    ],
)
def test_invalid_policy_shape_or_threshold_order_is_rejected(updates: dict[str, object]) -> None:
    values: dict[str, object] = {
        "policy_ref": "owner-voice-meter-policy",
        "policy_revision": 1,
        "predecessor_policy_sha256": None,
        "target_floor_dbfs": -24.0,
        "target_ceiling_dbfs": -12.0,
        "warning_dbfs": -1.0,
        "true_clip_dbfs": 0.0,
    }
    values.update(updates)
    with pytest.raises(MeterDisplayPolicyError):
        MeterDisplayPolicyRevision(**values)


def test_revision_chain_is_closed() -> None:
    with pytest.raises(MeterDisplayPolicyError, match="first"):
        policy(predecessor=h("unexpected"))
    with pytest.raises(MeterDisplayPolicyError, match="requires"):
        policy(revision=2)
    assert policy(revision=2, predecessor=h("revision-1")).policy_revision == 2


def test_fixture_currentness_requires_exact_head_and_nonserializable_seal() -> None:
    document = policy().to_dict()
    later = policy(
        revision=2,
        predecessor=document["policy_revision_sha256"],
    ).to_dict()
    with pytest.raises(MeterDisplayPolicyError, match="exact"):
        compile_fixture_meter_display_currentness(
            policy_document=document,
            current_head_document=later,
        )
    seal = compile_fixture_meter_display_currentness(
        policy_document=document,
        current_head_document=document,
    )
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(seal)
    with pytest.raises(TypeError, match="immutable"):
        seal.policy_ref = "changed"
    with pytest.raises(TypeError):
        class ForgedSeal(FixtureMeterDisplayCurrentnessSeal):
            pass


def test_fixture_verified_binding_cannot_be_self_declared_or_copied() -> None:
    document = policy().to_dict()
    with pytest.raises(MeterDisplayPolicyError, match="seal"):
        MeterDisplayPolicyBinding(
            PolicyBindingState.FIXTURE_BOUND_VERIFIED,
            document["policy_ref"],
            document["policy_revision"],
            document["predecessor_policy_sha256"],
            document["policy_revision_sha256"],
            h("forged-currentness"),
        )
    admitted = binding(document=document)
    operations = [copy.copy, copy.deepcopy, replace, pickle.dumps]
    if hasattr(copy, "replace"):
        operations.append(copy.replace)
    for operation in operations:
        with pytest.raises((TypeError, MeterDisplayPolicyError)):
            operation(admitted)


def test_policy_parser_rejects_unknown_field_and_digest_tamper() -> None:
    unknown = policy().to_dict()
    unknown["audio_path"] = "private.wav"
    with pytest.raises(MeterDisplayPolicyError, match="fields"):
        MeterDisplayPolicyRevision.from_dict(unknown)
    tampered = policy().to_dict()
    tampered["warning_dbfs"] = -2.0
    with pytest.raises(MeterDisplayPolicyError, match="sha256"):
        MeterDisplayPolicyRevision.from_dict(tampered)
    bool_version = policy().to_dict()
    bool_version["schema_version"] = True
    with pytest.raises(MeterDisplayPolicyError, match="discriminator"):
        MeterDisplayPolicyRevision.from_dict(bool_version)


def test_invalid_or_mismatched_policy_compiles_to_safe_unknown() -> None:
    document = policy().to_dict()
    tampered = deepcopy(document)
    tampered["warning_dbfs"] = -2.0
    invalid = compile_meter_display(
        policy_document=tampered,
        binding=binding(document=document),
        sample_peak_dbfs=-12.0,
        measured_sample_values=100,
    )
    assert invalid.reason_codes == (MeterDisplayReason.POLICY_DOCUMENT_INVALID,)
    assert invalid.thresholds_available is False
    wrong_document = MeterDisplayPolicyRevision(
        policy_ref="another-policy",
        policy_revision=1,
        predecessor_policy_sha256=None,
        target_floor_dbfs=-24.0,
        target_ceiling_dbfs=-12.0,
        warning_dbfs=-1.0,
        true_clip_dbfs=0.0,
    ).to_dict()
    mismatch = compile_meter_display(
        policy_document=wrong_document,
        binding=binding(document=document),
        sample_peak_dbfs=-12.0,
        measured_sample_values=100,
    )
    assert mismatch.reason_codes == (MeterDisplayReason.POLICY_BINDING_MISMATCH,)
    assert mismatch.thresholds_available is False


def test_missing_document_or_unbound_document_substitution_is_safe_unknown() -> None:
    current = binding()
    missing = compile_meter_display(
        policy_document=None,
        binding=current,
        sample_peak_dbfs=-12.0,
        measured_sample_values=100,
    )
    assert missing.reason_codes == (MeterDisplayReason.POLICY_DOCUMENT_MISSING,)
    substituted = compile_meter_display(
        policy_document=policy().to_dict(),
        binding=binding(PolicyBindingState.NOT_BOUND),
        sample_peak_dbfs=-12.0,
        measured_sample_values=100,
    )
    assert substituted.reason_codes == (MeterDisplayReason.POLICY_MISMATCH,)


def test_host_paths_and_uris_are_rejected_from_policy_identity() -> None:
    for value in (r"C:\private\meter", "/private/meter", "https://example.test/policy"):
        with pytest.raises(MeterDisplayPolicyError):
            MeterDisplayPolicyRevision(
                policy_ref=value,
                policy_revision=1,
                predecessor_policy_sha256=None,
                target_floor_dbfs=-24.0,
                target_ceiling_dbfs=-12.0,
                warning_dbfs=-1.0,
                true_clip_dbfs=0.0,
            )


def test_decision_round_trip_and_tamper_rejection() -> None:
    document = compile_peak(-12.0).to_dict()
    assert MeterDisplayDecision.from_dict(document).to_dict() == document
    tampered = deepcopy(document)
    tampered["display_band"] = "WARNING"
    with pytest.raises(MeterDisplayPolicyError, match="sha256"):
        MeterDisplayDecision.from_dict(tampered)
    forged = deepcopy(document)
    forged["quality_pass"] = True
    with pytest.raises(MeterDisplayPolicyError, match="fields"):
        MeterDisplayDecision.from_dict(forged)
    bool_version = deepcopy(document)
    bool_version["schema_version"] = True
    with pytest.raises(MeterDisplayPolicyError, match="discriminator"):
        MeterDisplayDecision.from_dict(bool_version)


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"display_band": "TRUE_CLIP", "operator_label": "クリップ"}, "band"),
        ({"target_floor_dbfs": -30.0}, "policy_revision_sha256"),
        ({"policy_currentness_confirmed": True}, "Product currentness"),
        ({"trusted_currentness_admitted": True}, "boundary"),
        ({"currentness_receipt_sha256": h("forged-currentness")}, "currentness receipt"),
    ],
)
def test_decision_parser_rejects_rehashed_semantic_or_authority_forgery(
    changes: dict[str, object], match: str
) -> None:
    document = compile_peak(-60.0).to_dict()
    document.update(changes)
    rehash_decision(document)
    with pytest.raises(MeterDisplayPolicyError, match=match):
        MeterDisplayDecision.from_dict(document)


def test_decision_parser_rejects_rehashed_binding_reason_alias() -> None:
    document = compile_peak(-12.0, state=PolicyBindingState.STALE).to_dict()
    document["reason_codes"] = [MeterDisplayReason.POLICY_REVOKED.value]
    rehash_decision(document)
    with pytest.raises(MeterDisplayPolicyError, match="binding state"):
        MeterDisplayDecision.from_dict(document)


class FlippingMapping(Mapping[str, object]):
    def __init__(self, value: dict[str, object]) -> None:
        self._value = value
        self._reads = 0

    def __iter__(self) -> Iterator[str]:
        return iter(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __getitem__(self, key: str) -> object:
        self._reads += 1
        if self._reads == 3:
            raise KeyError("mapping changed during read")
        return self._value[key]


def test_stateful_mapping_fails_closed_without_leaking_mapping_exception() -> None:
    document = policy().to_dict()
    with pytest.raises(MeterDisplayPolicyError, match="snapshot"):
        MeterDisplayPolicyRevision.from_dict(FlippingMapping(document))
    result = compile_meter_display(
        policy_document=FlippingMapping(document),
        binding=binding(document=document),
        sample_peak_dbfs=-12.0,
        measured_sample_values=100,
    )
    assert result.reason_codes == (MeterDisplayReason.POLICY_DOCUMENT_INVALID,)

    decision = compile_peak(-12.0).to_dict()
    with pytest.raises(MeterDisplayPolicyError, match="snapshot"):
        MeterDisplayDecision.from_dict(FlippingMapping(decision))


def test_decision_parser_rejects_not_bound_identity_smuggling() -> None:
    document = compile_peak(-12.0, state=PolicyBindingState.NOT_BOUND).to_dict()
    document["policy_ref"] = "smuggled-policy"
    body = dict(document)
    body.pop("decision_sha256")
    from ai_video_production.voice_quality_meter_display_policy import (
        DECISION_DIGEST_DOMAIN,
    )
    from ai_video_production.serialization import canonical_json_bytes, sha256_bytes

    document["decision_sha256"] = sha256_bytes(
        DECISION_DIGEST_DOMAIN + canonical_json_bytes(body)
    )
    with pytest.raises(MeterDisplayPolicyError, match="NOT_BOUND"):
        MeterDisplayDecision.from_dict(document)


def test_effect_and_authority_flags_are_permanently_false() -> None:
    value = compile_peak(-12.0).to_dict()
    for name in (
        "audio_body_read",
        "analyzer_executed",
        "quality_receipt_issued",
        "capture_authorized",
        "gain_change_authorized",
        "hardware_or_obs_setting_changed",
        "dataset_training_model_authorized",
        "production_backend_invoked",
        "capture_transport_blocked",
        "emergency_stop_blocked",
    ):
        assert value[name] is False
    assert value["external_effect_count"] == 0
    assert "PASS" not in json.dumps(value, ensure_ascii=False)


def test_module_has_no_audio_filesystem_process_network_or_native_surface() -> None:
    module_path = ROOT / "src" / "ai_video_production" / "voice_quality_meter_display_policy.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint(
        {
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "wave",
            "audioop",
            "numpy",
            "requests",
            "ctypes",
        }
    )
    lowered = source.lower()
    for forbidden in (
        "open(",
        "read_bytes",
        "write_bytes",
        "write_text",
        "subprocess",
        "urlopen",
        "obs_frontend",
        "qualitystate.pass",
    ):
        assert forbidden not in lowered
