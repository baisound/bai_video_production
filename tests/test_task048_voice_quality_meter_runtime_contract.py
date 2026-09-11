"""P2 synthetic-only contract evidence; no real media, native runtime or transport.

All files are pytest-owned beneath a run-specific OS temporary base. The writer
store is separate from the exclusively leased reader. Monkeypatches are tests,
never a production admission bypass or proof of C1 timing/noninterference.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from copy import copy, deepcopy
import gc
import hashlib
from importlib import resources
import json
import math
from pathlib import Path
import pickle
import struct
import sys
import threading
import uuid

from jsonschema import Draft202012Validator
import pytest

from ai_video_production.product_project import ProductProjectManifest, ProjectChildBinding, ProjectTimebase
from ai_video_production.product_project_store import ProductProjectManifestStore
from ai_video_production.project_save import ProductProjectSaveCoordinator
from ai_video_production.serialization import sha256_bytes
from ai_video_production.voice_quality_meter_display_policy import MeterDisplayPolicyRevision
from ai_video_production import voice_quality_meter_policy_store as p1
from ai_video_production import voice_quality_meter_runtime_contract as m

ROOT = Path(__file__).resolve().parents[1]
UIDS = [f"00000000-0000-4000-8000-{number:012x}" for number in range(1, 9)]
CONTEXT = dict(project_id="meter-project", session_id=UIDS[0], consumer_epoch=UIDS[1],
               window_sequence=1, request_id=UIDS[2])
DOMAINS = {
    "observation": b"TASK048_METER_RUNTIME_OBSERVATION_V1\0",
    "request": b"TASK048_METER_RUNTIME_WINDOW_REQUEST_V1\0",
    "projection": b"TASK048_METER_RUNTIME_DECISION_PROJECTION_V1\0",
}
DIGESTS = {name: name + "_sha256" for name in DOMAINS}


def uid():
    return str(uuid.uuid4())


def wire(document):
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def rehash(document, kind="observation"):
    field = DIGESTS[kind]
    document[field] = "sha256:" + hashlib.sha256(
        DOMAINS[kind] + wire({key: value for key, value in document.items() if key != field})
    ).hexdigest()
    return document


def metric(value=-18.0, state="FINITE"):
    return dict(state=state, value_dbfs=value if state == "FINITE" else None)


def observation(context=None, *, peak=-18.0, finite=1, nonfinite=0,
                total=None, session_peak=None, clips=None, session_clips=None, **changes):
    if clips is None:
        clips = int(peak is not None and peak >= m.OBSERVED_CLIP_DBFS)
    if total is None:
        total = finite
    if session_peak is None:
        session_peak = peak
    if session_clips is None:
        session_clips = clips
    current = metric(peak, "LINEAR_ZERO" if peak is None else "FINITE")
    historic = (deepcopy(session_peak) if type(session_peak) is dict else
                metric(session_peak, "LINEAR_ZERO" if session_peak is None else "FINITE"))
    if finite == 0:
        current = metric(state="NO_VALUE")
    if total == 0:
        historic = metric(state="NO_VALUE")
    document = dict(
        record_type=m.OBSERVATION_RECORD_TYPE, schema_version=1, canonical_owner_task="TASK-048",
        query_context=deepcopy(context or CONTEXT), capture_point=m.KNOWN_CAPTURE_POINT,
        paused=False, window_loss_state="NO_LOSS_REPORTED",
        window_counts=dict(state="VALID", finite_sample_values=finite,
                           nonfinite_sample_values=nonfinite, clip_sample_values=clips),
        session_counts=dict(state="VALID", finite_sample_values=total, clip_sample_values=session_clips),
        window_peak=current, window_rms=deepcopy(current), session_peak=historic,
    )
    document.update(changes)
    return rehash(document)


def request(ticket=None, obs=None, **changes):
    context = deepcopy(CONTEXT) if ticket is None else ticket.query_context.to_dict()
    document = dict(
        record_type=m.REQUEST_RECORD_TYPE, schema_version=1, canonical_owner_task="TASK-048",
        query_context=context, runtime_epoch=UIDS[3] if ticket is None else ticket.runtime_epoch,
        policy_producer_epoch=UIDS[4] if ticket is None else ticket.policy_producer_epoch,
        observation=observation(context) if obs is None else obs,
    )
    document.update(changes)
    return rehash(document, "request")


def policy():
    return MeterDisplayPolicyRevision("meter-policy", 1, None, -24.0, -12.0, -3.0, 0.0).to_dict()


def diagnostic(req=None, *, initial="PROJECT_HEAD_MATCHED_SNAPSHOT",
               final="PROJECT_HEAD_MATCHED_SNAPSHOT", band="TARGET", reason="WINDOW_POLICY_CLASSIFIED",
               state="MEASURED", label="目標範囲"):
    req = request() if req is None else req
    matched = initial == final == "PROJECT_HEAD_MATCHED_SNAPSHOT"
    document = {key: deepcopy(value) for key, value in req.items() if key != "record_type"}
    document.update(
        record_type=m.PROJECTION_RECORD_TYPE, observation_state=state, display_band=band,
        reason_code=reason, operator_label=label, scope_label="今回の観測窓に対する方針照合",
        window_only=True, live_admission_serialized=False,
        policy_observation=dict(
            initial_status=initial, final_status=final,
            effective_status=final if final != "PROJECT_HEAD_MATCHED_SNAPSHOT" else initial,
            window_policy_matched=matched,
            identity=dict(project_id="meter-project", project_revision=4,
                          project_manifest_sha256="sha256:" + "a" * 64, child_sha256="sha256:" + "b" * 64,
                          state_revision=3, selected_policy_sha256=policy()["policy_revision_sha256"],
                          producer_epoch=req["policy_producer_epoch"]) if matched else None,
            policy_document=policy() if matched else None,
        ),
        authority=dict.fromkeys((
            "authority_created", "quality_pass_issued", "capture_authorized",
            "gain_change_authorized", "hardware_or_obs_setting_changed",
            "consent_asset_training_model_authorized", "temporal_freshness_confirmed",
            "production_authorized", "provider_invoked",
            "capture_path_noninterference_confirmed", "emergency_stop_noninterference_confirmed",
        ), False),
        io_boundary=dict(
            audio_semantic_decode_executed=False, audio_used_as_policy_input=False,
            project_integrity_hash_reads_possible=True, policy_or_project_write_executed=False,
            capture_transport_api_invoked=False, emergency_stop_api_invoked=False,
        ),
    )
    return rehash(document, "projection")


def expect_error(reason, call, *args):
    with pytest.raises(m.MeterRuntimeContractError) as caught:
        call(*args)
    error = caught.value
    if reason is not None:
        assert error.reason == reason
    assert str(error) == error.code == "ERR_TASK048_METER_RUNTIME_" + error.reason
    assert error.__cause__ is None
    assert error.__context__ is None
    return error


@pytest.fixture(autouse=True)
def owned_lease_cleanup():
    before = tuple(m._LEASES)
    yield
    for lease in tuple(m._LEASES):
        if not any(lease is entry for entry in before):
            assert lease.evaluation is None, "test left a synchronous evaluation running"
            lease.controller.close()
    assert tuple(m._LEASES) == before


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "synthetic-project"
    root.mkdir()
    ProductProjectManifestStore.save(root, ProductProjectManifest.create(
        project_id="meter-project", project_revision=1, product_version="0.23.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-09-01T00:00:00.000Z", updated_at="2026-09-01T00:00:00.000Z",
    ))
    return root


def apply(project, writer, action, payload):
    current = ProductProjectManifestStore.load(project)
    child = next((item for item in current.child_bindings if item.relative_path == p1.CHILD_PATH), None)
    body = dict(
        record_type="Task048MeterPolicyOperationRequestV1", schema_version=1,
        canonical_owner_task="TASK-048", project_id="meter-project", operation_id=uid(),
        action=action, expected_project_revision=current.project_revision,
        expected_project_manifest_sha256=current.project_manifest_sha256,
        expected_child_sha256=None if child is None else child.content_sha256, payload=payload,
    )
    body["request_sha256"] = sha256_bytes(p1.REQUEST_DOMAIN + wire(body))
    return writer.apply(body)


@pytest.fixture
def live(project):
    writer = p1.MeterPolicyProjectStore(project, "meter-project")
    apply(project, writer, "BOOTSTRAP", {"policy_ref": "meter-policy"})
    apply(project, writer, "PUBLISH_POLICY", {"policy_document": policy()})
    apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": policy()["policy_revision_sha256"]})
    reader = p1.MeterPolicyProjectStore(project, "meter-project")
    controller = m.MeterRuntimeController(reader)
    controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[1])
    try:
        yield controller, reader, writer, project
    finally:
        controller.close()
        writer.close()


def emit(controller, **kwargs):
    ticket = controller.begin_window()
    obs = observation(ticket.query_context.to_dict(), **kwargs)
    result = controller.project(ticket, wire(request(ticket, obs)))
    return result.to_dict()


def test_schema_entrypoints_mirror_and_no_remote_refs():
    canonical = (ROOT / "schemas" / m.SCHEMA_NAME).read_bytes()
    assert canonical == resources.files("ai_video_production.schema_resources").joinpath(m.SCHEMA_NAME).read_bytes()
    schema = json.loads(canonical)
    assert schema["$id"] == m.SCHEMA_URI
    assert schema["$ref"] == "#/$defs/projection"
    Draft202012Validator.check_schema(schema)
    for kind, document in (("observation", observation()), ("request", request()), ("projection", diagnostic())):
        wrapper = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/" + kind}
        Draft202012Validator.check_schema(wrapper)
        Draft202012Validator(wrapper).validate(document)
        for other in {"observation": observation(), "request": request(), "projection": diagnostic()}:
            if other != kind:
                invalid = {"observation": observation, "request": request, "projection": diagnostic}[other]()
                assert not Draft202012Validator(wrapper).is_valid(invalid)
    assert set(m._load_entrypoints()) == {"observation", "request", "projection"}


@pytest.mark.parametrize("kind,factory", [("observation", observation), ("request", request), ("projection", diagnostic)])
def test_each_parser_serializer_roundtrip_and_discriminator(kind, factory):
    parse = getattr(m, "parse_meter_runtime_" + kind)
    serialize = getattr(m, "serialize_meter_runtime_" + kind)
    document = factory()
    assert serialize(document) == wire(document)
    assert wire(parse(serialize(document))) == wire(document)
    assert parse(json.dumps(document, ensure_ascii=False, indent=2).encode()) == document
    for key, value in (("schema_version", 1.0), ("schema_version", True),
                       ("schema_version", 2), ("canonical_owner_task", "TASK-047"),
                       ("record_type", "Task048MeterDisplayDecisionV1"), ("extra", False)):
        invalid = deepcopy(document)
        invalid[key] = value
        rehash(invalid, kind)
        expect_error(None, parse, wire(invalid))
        expect_error(None, serialize, invalid)


@pytest.mark.parametrize("value", [0.1, 6.0, 12.0, 18.0, sys.float_info.max, -sys.float_info.max, 0.0, -0.0])
def test_finite_bit_exact_pure_and_positive_policy_band(value):
    obs = observation(peak=value)
    parsed = m.parse_meter_runtime_observation(m.serialize_meter_runtime_observation(obs))
    for name in ("window_peak", "window_rms", "session_peak"):
        assert struct.pack(">d", parsed[name]["value_dbfs"]) == struct.pack(">d", value)
    band = "TRUE_CLIP" if value >= 0.0 else "BELOW_TARGET"
    label = "クリップ" if band == "TRUE_CLIP" else "目標未満"
    projected = diagnostic(request(obs=obs), band=band, label=label)
    assert m.parse_meter_runtime_projection(wire(projected)) == projected


@pytest.mark.parametrize("scope", ["window_peak", "window_rms", "session_peak"])
@pytest.mark.parametrize("bad", [0, True, "NaN", "1.5", None])
def test_metric_exact_float_not_coercion(scope, bad):
    doc = observation()
    doc[scope]["value_dbfs"] = bad
    rehash(doc)
    expect_error(None, m.parse_meter_runtime_observation, wire(doc))


@pytest.mark.parametrize("bad", [b"NaN", b"Infinity", b"-Infinity", b"1e309"])
def test_nonfinite_raw_json_rejected(bad):
    raw = wire(observation()).replace(b"-18.0", bad)
    expect_error("INVALID_NUMBER", m.parse_meter_runtime_observation, raw)


@pytest.mark.parametrize("raw", [
    b"\xef\xbb\xbf{}", b"\xff", b'{"x":"\\ud800"}', b'{"x":"\\udfff"}',
    b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b"{}{}", b'{"x":',
    b'{"x":[1]}', b'{"x":"\x00"}', b'{"x":01}',
])
def test_malformed_json_safe(raw):
    expect_error(None, m.parse_meter_runtime_observation, raw)


@pytest.mark.parametrize("kind,limit,factory", [
    ("observation", 16_384, observation), ("request", 24_576, request),
    ("projection", 49_152, diagnostic),
])
def test_exact_byte_limit_and_one_over(kind, limit, factory):
    parse = getattr(m, "parse_meter_runtime_" + kind)
    raw = wire(factory())
    assert parse(raw + b" " * (limit - len(raw))) == factory()
    expect_error("LIMIT_EXCEEDED", parse, raw + b" " * (limit + 1 - len(raw)))


def test_structural_limits_before_recursive_decode(monkeypatch):
    decoded = []
    original = m.json.loads

    def track(*args, **kwargs):
        decoded.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(m.json, "loads", track)
    expect_error("LIMIT_EXCEEDED", m.parse_meter_runtime_observation, b'{"x":' * 13 + b"0" + b"}" * 13)
    assert not decoded
    # Root depth zero, primitive/key depth 12 is allowed by the bounded reader.
    m._decode(b'{"x":' * 12 + b"0" + b"}" * 12, 16_384)
    expect_error("LIMIT_EXCEEDED", m._decode, wire({"x" * 257: None}), 16_384)
    m._decode(wire({"x" * 256: None}), 16_384)
    m._decode(wire({str(i): None for i in range(64)}), 16_384)
    expect_error("LIMIT_EXCEEDED", m._decode, wire({str(i): None for i in range(65)}), 16_384)
    # Containers + keys + values; direct preflight isolates node cap from byte cap.
    body = "{" + ",".join('"%d":0' % i for i in range(2048)) + "}"
    with pytest.raises(m.MeterRuntimeContractError, match="LIMIT_EXCEEDED"):
        m._preflight(body, schema=False)
    m._preflight("{" + ",".join('"%d":0' % i for i in range(2047)) + "}", schema=False)


class HostileMapping(Mapping):
    def __getitem__(self, key):
        raise AssertionError("must not touch Mapping")
    def __iter__(self):
        raise AssertionError("must not iterate Mapping")
    def __len__(self):
        raise AssertionError("must not size Mapping")


class HostileBytes(bytes):
    def __bytes__(self):
        raise AssertionError("must not convert bytes subclass")


@pytest.mark.parametrize("value", [HostileMapping(), HostileBytes(b"{}"), bytearray(b"{}"),
                                   memoryview(b"{}"), "{}", {}, []])
def test_exact_live_bytes_only_no_conversion_or_io(live, monkeypatch, value):
    controller, reader, _, _ = live
    calls = []
    monkeypatch.setattr(reader, "read_snapshot", lambda context: calls.append(context))
    ticket = controller.begin_window()
    expect_error("RECORD_TYPE_MISMATCH", controller.project, ticket, value)
    assert not calls
    expect_error("WINDOW_STALE", controller.project, ticket, wire(request()))
    assert controller._lease.evaluation is None


@pytest.mark.parametrize("value", [HostileMapping(), HostileBytes(b"{}"), bytearray(b"{}"),
                                   memoryview(b"{}"), "{}", []])
def test_standalone_no_stateful_mapping_or_implicit_encoding(value):
    expect_error("RECORD_TYPE_MISMATCH", m.parse_meter_runtime_request, value)
    expect_error("RECORD_TYPE_MISMATCH", m.serialize_meter_runtime_request, value)


@pytest.mark.parametrize("scope", ["window", "session"])
@pytest.mark.parametrize("peak,clips,bits", [
    (-0.000868776543637768, 0, "bf4c77d36bd59a3c"),
    (-0.000868258772501058, 1, "bf4c737b8424476f"),
    (-0.0008686323961501121, 1, "bf4c769dddea3cb0"),
    (math.nextafter(-0.0008686323961501121, -math.inf), 0, None),
    (math.nextafter(-0.0008686323961501121, math.inf), 1, None),
])
def test_clip_existence_fixed_vectors_both_scopes(scope, peak, clips, bits):
    if bits:
        assert struct.pack(">d", peak).hex() == bits
    doc = observation(peak=peak, clips=clips, session_clips=clips, total=2)
    assert m.parse_meter_runtime_observation(wire(doc)) == doc
    # Keep independent count inequalities valid while flipping only one scope.
    if scope == "window":
        doc["window_counts"]["clip_sample_values"] = 1 - clips
        if not clips:
            doc["session_counts"]["clip_sample_values"] = 1
            doc["session_peak"] = metric(0.0)
    else:
        doc["session_counts"]["clip_sample_values"] = 1 - clips
        if clips:
            doc["window_counts"]["clip_sample_values"] = 0
            doc["window_peak"] = doc["window_rms"] = metric(-18.0)
    rehash(doc)
    expect_error("INVALID_OBSERVATION", m.parse_meter_runtime_observation, wire(doc))
    doc["capture_point"] = "UNKNOWN"
    rehash(doc)
    assert m.parse_meter_runtime_observation(wire(doc)) == doc


@pytest.mark.parametrize("changes,state", [
    ({"peak": None}, "MEASURED_LINEAR_ZERO"),
    ({"finite": 0}, "NO_INPUT"),
    ({"finite": 0, "nonfinite": 3}, "INVALID_NONFINITE"),
    ({"nonfinite": 1}, "INVALID_NONFINITE"),
    ({"capture_point": "UNKNOWN"}, "CAPTURE_POINT_UNKNOWN"),
    ({"window_loss_state": "LOSS_REPORTED"}, "LOSS_REPORTED"),
    ({"window_loss_state": "UNKNOWN"}, "LOSS_UNKNOWN"),
    ({"paused": True}, "PAUSED"),
    ({"window_peak": metric(state="INVALID")}, "INVALID_NUMERIC"),
    ({"window_rms": metric(state="OVERFLOW")}, "INVALID_NUMERIC"),
    ({"window_counts": dict(state="COUNTER_OVERFLOW", finite_sample_values=None,
                           nonfinite_sample_values=None, clip_sample_values=None)}, "INVALID_NUMERIC"),
    ({"session_counts": dict(state="UNAVAILABLE", finite_sample_values=None,
                            clip_sample_values=None)}, "COUNTS_UNAVAILABLE"),
])
def test_observation_states_and_precedence(live, changes, state):
    document = emit(live[0], **changes)
    assert document["observation_state"] == state
    assert document["observation"] == m.parse_meter_runtime_observation(wire(document["observation"]))
    if state.startswith("MEASURED"):
        assert document["display_band"] != "UNCONFIRMED"
    else:
        assert document["display_band"] == "UNCONFIRMED"
        assert document["operator_label"] == "適正判定 未確定"
    assert document["authority"]["quality_pass_issued"] is False


@pytest.mark.parametrize("path,value", [
    (("window_counts", "finite_sample_values"), True),
    (("window_counts", "finite_sample_values"), 1.0),
    (("session_counts", "finite_sample_values"), -1),
    (("session_counts", "finite_sample_values"), 9_007_199_254_740_992),
    (("window_counts", "clip_sample_values"), 2),
    (("window_counts", "state"), "UNAVAILABLE"),
    (("window_rms", "value_dbfs"), -12.0),
    (("window_peak", "state"), "LINEAR_ZERO"),
    (("session_peak", "value_dbfs"), -24.0),
])
def test_count_metric_contradictions(path, value):
    doc = observation()
    doc[path[0]][path[1]] = value
    rehash(doc)
    expect_error(None, m.parse_meter_runtime_observation, wire(doc))


def test_no_value_not_measured_zero_or_abnormal():
    for changes in (
        {"finite": 0, "window_peak": metric(None, "LINEAR_ZERO")},
        {"window_rms": metric(None, "NO_VALUE")},
        {"window_rms": metric(None, "LINEAR_ZERO")},
        {"session_peak": metric(None, "NO_VALUE")},
        {"peak": None, "clips": 1, "session_clips": 1},
    ):
        expect_error("INVALID_OBSERVATION", m.parse_meter_runtime_observation, wire(observation(**changes)))


@pytest.mark.parametrize("key", ["capture_transport_blocked", "emergency_stop_blocked", "audio_body_read",
                                 "fixture_only", "production_eligible"])
def test_removed_or_fixture_flags_rejected_even_rehashed(key):
    for location in ("authority", "io_boundary"):
        doc = diagnostic()
        doc[location][key] = False
        expect_error("SCHEMA_INVALID", m.parse_meter_runtime_projection, wire(rehash(doc, "projection")))


def test_every_fixed_boundary_key_presence_type_value():
    for location in ("authority", "io_boundary"):
        baseline = diagnostic()
        for key in baseline[location]:
            for operation in ("remove", "flip", "int"):
                doc = deepcopy(baseline)
                if operation == "remove":
                    del doc[location][key]
                elif operation == "int":
                    doc[location][key] = int(doc[location][key])
                else:
                    doc[location][key] = not doc[location][key]
                expect_error("SCHEMA_INVALID", m.parse_meter_runtime_projection, wire(rehash(doc, "projection")))


@pytest.mark.parametrize("field,value", [("display_band", "TRUE_CLIP"), ("reason_code", "POLICY_STALE"),
                                        ("operator_label", "PASS"), ("observation_state", "PAUSED"),
                                        ("scope_label", "承認"), ("window_only", False),
                                        ("live_admission_serialized", True)])
def test_projection_derived_claim_tamper_even_rehashed(field, value):
    doc = diagnostic()
    doc[field] = value
    expect_error("SCHEMA_INVALID", m.parse_meter_runtime_projection, wire(rehash(doc, "projection")))


def test_nested_tamper_and_cross_domain_hashes():
    for kind, factory in (("observation", observation), ("request", request), ("projection", diagnostic)):
        doc = factory()
        doc[DIGESTS[kind]] = "sha256:" + "0" * 64
        expect_error("DIGEST_MISMATCH", getattr(m, "parse_meter_runtime_" + kind), wire(doc))
        doc = factory()
        doc[DIGESTS[kind]] = "sha256:" + hashlib.sha256(
            b"WRONG_DOMAIN\0" + wire({k: v for k, v in doc.items() if k != DIGESTS[kind]})
        ).hexdigest()
        expect_error("DIGEST_MISMATCH", getattr(m, "parse_meter_runtime_" + kind), wire(doc))
    doc = diagnostic()
    doc["observation"]["paused"] = True
    expect_error("DIGEST_MISMATCH", m.parse_meter_runtime_projection, wire(rehash(doc, "projection")))
    rehash(doc["observation"])
    doc.update(observation_state="PAUSED", display_band="UNCONFIRMED",
               reason_code="OBSERVATION_PAUSED", operator_label="適正判定 未確定")
    expect_error("DIGEST_MISMATCH", m.parse_meter_runtime_projection, wire(rehash(doc, "projection")))


def test_real_p1_fresh_reads_final_identity_no_write(live, monkeypatch):
    controller, reader, _, project = live
    before = {path.relative_to(project).as_posix(): path.read_bytes() for path in project.rglob("*") if path.is_file()}
    calls, snapshots = [], []
    original_read, original_revalidate = reader.read_snapshot, reader.revalidate

    def read(context):
        calls.append(("read", context.to_dict()))
        result = original_read(context)
        snapshots.append(result.snapshot)
        return result

    def revalidate(snapshot, context):
        calls.append(("revalidate", context.to_dict()))
        assert snapshot is snapshots[-1]
        result = original_revalidate(snapshot, context)
        snapshots.append(result.snapshot)
        return result
    monkeypatch.setattr(reader, "read_snapshot", read)
    monkeypatch.setattr(reader, "revalidate", revalidate)
    first = emit(controller)
    assert [name for name, _ in calls] == ["read", "revalidate"]
    assert first["policy_observation"]["identity"]["project_manifest_sha256"] == snapshots[-1].project_manifest_sha256
    assert first["policy_observation"]["policy_document"] == snapshots[-1].policy.to_dict()
    second = emit(controller, total=2)
    assert [name for name, _ in calls] == ["read", "revalidate", "read", "revalidate"]
    assert first["query_context"]["request_id"] != second["query_context"]["request_id"]
    assert first["policy_observation"]["window_policy_matched"] is True
    assert before == {path.relative_to(project).as_posix(): path.read_bytes() for path in project.rglob("*") if path.is_file()}
    assert second["io_boundary"]["project_integrity_hash_reads_possible"] is True


@pytest.mark.parametrize("status,reason", [
    ("NOT_BOUND", "POLICY_NOT_BOUND"), ("REVOKED", "POLICY_REVOKED"), ("STALE", "POLICY_STALE"),
    ("MISMATCH", "POLICY_MISMATCH"), ("RECOVERY_REQUIRED", "PROJECT_RECOVERY_REQUIRED"),
    ("ROLLBACK_UNCERTAIN", "PROJECT_ROLLBACK_UNCERTAIN"), ("INVALID", "POLICY_INVALID"),
    ("READBACK_FAILED", "POLICY_READBACK_FAILED"),
])
@pytest.mark.parametrize("which", ["initial", "final"])
def test_policy_status_precedence_and_no_rehabilitation(live, monkeypatch, status, reason, which):
    controller, reader, _, _ = live
    real_read = reader.read_snapshot
    count = []

    def read(context):
        count.append("read")
        if which == "initial" and len(count) == 1:
            return p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus(status), None)
        return real_read(context)
    monkeypatch.setattr(reader, "read_snapshot", read)
    if which == "final":
        monkeypatch.setattr(reader, "revalidate", lambda *_: p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus(status), None))
    doc = emit(controller, paused=True, nonfinite=1, window_loss_state="LOSS_REPORTED")
    assert doc["reason_code"] == reason
    assert doc["display_band"] == "UNCONFIRMED"
    assert doc["policy_observation"]["identity"] is None
    assert doc["policy_observation"]["policy_document"] is None
    assert doc["observation_state"] == "INVALID_NONFINITE"
    assert doc["policy_observation"]["window_policy_matched"] is False
    assert count == (["read", "read"] if which == "initial" else ["read"])


@pytest.mark.parametrize("boundary", ["initial", "final", "diagnostic"])
def test_ordinary_p1_exception_safe_with_diagnostic_rule(live, monkeypatch, boundary):
    controller, reader, _, _ = live
    real_read = reader.read_snapshot
    calls = []

    def read(context):
        calls.append("read")
        if boundary == "initial" and len(calls) == 1 or boundary == "diagnostic" and len(calls) == 2:
            raise OSError("SECRET input path must not escape")
        if boundary == "diagnostic":
            return p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus.NOT_BOUND, None)
        return real_read(context)

    def fail(*_):
        calls.append("revalidate")
        raise RuntimeError("SECRET revalidate")
    monkeypatch.setattr(reader, "read_snapshot", read)
    if boundary == "final":
        monkeypatch.setattr(reader, "revalidate", fail)
    doc = emit(controller)
    assert doc["reason_code"] == "POLICY_READBACK_FAILED"
    assert b"SECRET" not in wire(doc)
    assert calls == (["read", "revalidate"] if boundary == "final" else ["read", "read"])
    assert controller._lease.evaluation is None
    expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)


@pytest.mark.parametrize("bad", [None, {}, p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT, None)])
def test_nominal_success_missing_or_invalid_snapshot(live, monkeypatch, bad):
    controller, reader, _, _ = live
    monkeypatch.setattr(reader, "read_snapshot", lambda _: bad)
    doc = emit(controller)
    assert doc["policy_observation"]["initial_status"] == "MISMATCH"
    assert doc["policy_observation"]["final_status"] == "MISMATCH"
    assert doc["policy_observation"]["identity"] is None


@pytest.mark.parametrize("change", ["revoke", "select", "unrelated", "child_tamper"])
def test_project_changes_between_reads_via_separate_writer(live, monkeypatch, change):
    controller, reader, writer, project = live
    original = reader.read_snapshot

    def read(context):
        result = original(context)
        if change == "revoke":
            apply(project, writer, "REVOKE_POLICY", {"policy_revision_sha256": policy()["policy_revision_sha256"]})
        elif change == "select":
            doc = MeterDisplayPolicyRevision("meter-policy", 2, policy()["policy_revision_sha256"],
                                             -25.0, -12.0, -3.0, 0.0).to_dict()
            apply(project, writer, "PUBLISH_POLICY", {"policy_document": doc})
            apply(project, writer, "SELECT_POLICY", {"policy_revision_sha256": doc["policy_revision_sha256"]})
        elif change == "unrelated":
            current = ProductProjectManifestStore.load(project)
            target = ProductProjectManifest.create(
                project_id=current.project_id, project_revision=current.project_revision + 1,
                product_version=current.product_version, timebase=current.timebase,
                child_bindings=current.child_bindings, created_at=current.created_at,
                updated_at=current.updated_at,
            )
            ProductProjectSaveCoordinator().save(
                project, target, {}, expected_previous_manifest_sha256=current.project_manifest_sha256,
            )
        else:
            (project / p1.CHILD_PATH).write_bytes(b"synthetic tampered body")
        return result
    monkeypatch.setattr(reader, "read_snapshot", read)
    doc = emit(controller)
    assert doc["policy_observation"]["final_status"] == {
        "revoke": "REVOKED", "select": "STALE", "unrelated": "STALE", "child_tamper": "INVALID",
    }[change]
    assert doc["policy_observation"]["identity"] is None


def test_current_clip_separate_from_history_and_near_clip_not_forced(live):
    controller = live[0]
    first = emit(controller, peak=-0.000868258772501058, total=1)
    assert first["display_band"] == "WARNING"
    second = emit(controller, peak=-18.0, total=2, session_peak=0.0, session_clips=1)
    assert second["display_band"] == "TARGET"
    assert second["observation"]["window_counts"]["clip_sample_values"] == 0
    assert second["observation"]["session_counts"]["clip_sample_values"] == 1
    assert second["observation"]["window_peak"]["value_dbfs"] == -18.0


def test_history_lower_bounds_through_unknown_then_restore(live):
    controller = live[0]
    unavailable = dict(state="UNAVAILABLE", finite_sample_values=None, clip_sample_values=None)
    emit(controller, total=4)
    emit(controller, session_counts=unavailable)
    assert controller._lease.finite_floor == 5
    emit(controller, session_counts=unavailable)
    assert controller._lease.finite_floor == 6
    restored = emit(controller, total=9)
    assert restored["display_band"] == "TARGET"
    assert controller._lease.finite_floor == 9


@pytest.mark.parametrize("kind", ["count", "peak", "overflow"])
def test_history_atomic_latch_persists_across_reconnect(live, kind):
    controller = live[0]
    emit(controller, total=m.MAX_INTEGER if kind == "overflow" else 4)
    before = (controller._lease.finite_floor, controller._lease.clip_floor, deepcopy(controller._lease.peak_floor))
    ticket = controller.begin_window()
    obs = observation(ticket.query_context.to_dict(), total=4 if kind != "overflow" else m.MAX_INTEGER,
                      peak=-20.0 if kind == "peak" else -18.0)
    if kind == "peak":
        obs["session_counts"]["finite_sample_values"] = 5
        rehash(obs)
    code = "CAPACITY_EXHAUSTED" if kind == "overflow" else "SESSION_HISTORY_REGRESSION"
    expect_error(code, controller.project, ticket, wire(request(ticket, obs)))
    assert before == (controller._lease.finite_floor, controller._lease.clip_floor, controller._lease.peak_floor)
    controller.invalidate("RECONNECT")
    controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[6])
    ticket = controller.begin_window()
    expect_error(code, controller.project, ticket, wire(request(ticket, observation(
        ticket.query_context.to_dict(), total=m.MAX_INTEGER))))
    controller.activate_consumer(session_id=UIDS[7], consumer_epoch=uid())
    assert emit(controller)["display_band"] == "TARGET"


def test_session_epoch_reset_retirement_and_collision(live, monkeypatch):
    controller = live[0]
    controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[6])
    assert controller.begin_window().query_context.window_sequence == 1
    expect_error("EPOCH_MISMATCH", lambda: controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[1]))
    controller.activate_consumer(session_id=UIDS[7], consumer_epoch=uid())
    expect_error("EPOCH_MISMATCH", lambda: controller.activate_consumer(session_id=UIDS[0], consumer_epoch=uid()))
    controller.activate_consumer(session_id=UIDS[7], consumer_epoch=uid())
    monkeypatch.setattr(m.uuid, "uuid4", lambda: uuid.UUID(UIDS[2]))
    first = controller.begin_window()
    assert first.query_context.request_id == UIDS[2]
    expect_error("IDENTITY_COLLISION", controller.begin_window)
    expect_error("CONTEXT_MISMATCH", controller.begin_window)


@pytest.mark.parametrize("entrypoint", ["observation", "request", "projection"])
@pytest.mark.parametrize("mutation", ["remote", "dynamic_ref", "recursive_ref", "nested_id", "wrong_id", "wrong_root", "oversize"])
def test_schema_loader_fails_closed(monkeypatch, entrypoint, mutation):
    import io
    schema = json.loads((ROOT / "schemas" / m.SCHEMA_NAME).read_bytes())
    if mutation == "remote":
        schema["$defs"][entrypoint]["properties"]["query_context"] = {"$ref": "https://invalid.local/remote"}
    elif mutation in {"dynamic_ref", "recursive_ref"}:
        schema["$defs"][entrypoint]["$dynamicRef" if mutation == "dynamic_ref" else "$recursiveRef"] = "https://invalid.local/remote"
    elif mutation == "nested_id":
        schema["$defs"][entrypoint]["$id"] = "https://invalid.local/nested"
    elif mutation == "wrong_id":
        schema["$id"] = "https://invalid.local/identity"
    elif mutation == "wrong_root":
        schema["$ref"] = "#/$defs/request"
    data = wire(schema)
    if mutation == "oversize":
        data += b" " * (131_073 - len(data))

    class FixedResource:
        def joinpath(self, name):
            assert name == m.SCHEMA_NAME
            return self
        def open(self, mode):
            assert mode == "rb"
            return io.BytesIO(data)
    monkeypatch.setattr(m.resources, "files", lambda package: FixedResource())
    monkeypatch.setattr(m, "_SCHEMA_ENTRYPOINTS", None)
    expect_error("SCHEMA_INVALID", getattr(m, "parse_meter_runtime_" + entrypoint),
                 wire({"observation": observation, "request": request, "projection": diagnostic}[entrypoint]()))


@pytest.mark.parametrize("field", ["project_id", "session_id", "consumer_epoch", "request_id", "window_sequence",
                                   "runtime_epoch", "policy_producer_epoch"])
def test_request_context_epoch_mismatch_no_p1_io(live, monkeypatch, field):
    controller, reader, _, _ = live
    calls = []
    monkeypatch.setattr(reader, "read_snapshot", lambda *_: calls.append(True))
    ticket = controller.begin_window()
    doc = request(ticket)
    if field in ("runtime_epoch", "policy_producer_epoch"):
        doc[field] = uid()
    else:
        changed = {"project_id": "other-project", "window_sequence": 2}.get(field, uid())
        doc["query_context"][field] = changed
        doc["observation"]["query_context"][field] = changed
        rehash(doc["observation"])
    rehash(doc, "request")
    expect_error("EPOCH_MISMATCH" if field in ("runtime_epoch", "policy_producer_epoch") else "CONTEXT_MISMATCH",
                 controller.project, ticket, wire(doc))
    assert calls == []


def test_nested_context_mismatch_full_uuid_grammar():
    doc = request()
    doc["observation"]["query_context"]["request_id"] = UIDS[6]
    rehash(doc["observation"])
    expect_error("CONTEXT_MISMATCH", m.parse_meter_runtime_request, wire(rehash(doc, "request")))
    for value in (UIDS[0].upper().replace("4000", "4ABC"), UIDS[0] + "\n",
                  UIDS[0].replace("4000", "1000"), UIDS[0].replace("8000", "7000")):
        doc = observation()
        doc["query_context"]["session_id"] = value
        expect_error(None, m.parse_meter_runtime_observation, wire(rehash(doc)))


def test_duplicate_late_foreign_parsed_fixture_cannot_replace_current(live):
    controller, reader, _, _ = live
    old = controller.begin_window()
    old_bytes = wire(request(old))
    current = controller.begin_window()
    current_bytes = wire(request(current))
    expect_error("WINDOW_STALE", controller.project, old, old_bytes)
    expect_error("TICKET_INVALID", controller.project, m.parse_meter_runtime_request(current_bytes), current_bytes)
    result = controller.project(current, current_bytes)
    doc = result.to_dict()
    expect_error("TICKET_CONSUMED", controller.project, current, current_bytes)
    assert result.to_dict() == doc
    changed = json.loads(current_bytes)
    changed["observation"]["paused"] = True
    rehash(changed["observation"])
    expect_error("TICKET_CONSUMED", controller.project, current, wire(rehash(changed, "request")))
    assert result.to_dict() == doc
    controller.begin_window()
    expect_error("TICKET_INVALID", result.to_dict)
    controller.close()
    replacement = m.MeterRuntimeController(reader)
    replacement.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[1])
    assert replacement.runtime_epoch != doc["runtime_epoch"]
    expect_error("WINDOW_STALE", replacement.project, current, current_bytes)


@pytest.mark.parametrize("which", ["ticket", "projection", "controller"])
def test_capability_copy_pickle_subclass_rehydrate_forgery_rejected(live, which):
    controller = live[0]
    ticket = controller.begin_window()
    raw = wire(request(ticket))
    result = controller.project(ticket, raw)
    obj = {"ticket": ticket, "projection": result, "controller": controller}[which]
    cls = type(obj)
    for operation in (copy, deepcopy, pickle.dumps):
        expect_error("NOT_SUPPORTED", operation, obj)
    expect_error("NOT_SUPPORTED", lambda: type("Subclass", (cls,), {}))
    expect_error("NOT_SUPPORTED", lambda: obj.__setstate__({}))
    if which != "controller":
        expect_error("NOT_SUPPORTED", cls)
        forged = object.__new__(cls)
        if which == "ticket":
            expect_error("WINDOW_STALE", controller.project, forged, raw)
        else:
            expect_error("INTERNAL_ERROR", forged.to_dict)
    else:
        expect_error("NOT_SUPPORTED", obj.__init__, live[1])
        forged = object.__new__(cls)
        object.__setattr__(forged, "_lease", controller._lease)
        expect_error("TICKET_INVALID", forged.begin_window)
        expect_error("TICKET_INVALID", forged.close)


@pytest.mark.parametrize("field", ["_context_bytes", "_runtime", "_producer", "_owner"])
def test_low_level_ticket_mutation_rejected(live, field):
    controller = live[0]
    ticket = controller.begin_window()
    raw = wire(request(ticket))
    object.__setattr__(ticket, field, object() if field == "_owner" else b"mutated")
    expect_error("TICKET_INVALID", controller.project, ticket, raw)
    assert controller._lease.evaluation is None


def test_low_level_projection_mutation_rejected(live):
    controller = live[0]
    ticket = controller.begin_window()
    projected = controller.project(ticket, wire(request(ticket)))
    object.__setattr__(projected, "_document", wire(diagnostic()))
    expect_error("TICKET_INVALID", projected.to_dict)


@pytest.mark.parametrize("boundary", ["read", "revalidate", "build"])
@pytest.mark.parametrize("event", ["new_window", "activate", "invalidate", "close"])
def test_lifecycle_interleaving_drops_old_output_retains_exact_lease(live, monkeypatch, boundary, event):
    controller, reader, _, _ = live
    ticket = controller.begin_window()
    raw = wire(request(ticket))
    replacement = []
    events = []

    def transition():
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
        if event == "new_window":
            replacement.append(controller.begin_window())
        elif event == "activate":
            controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[6])
            replacement.append(controller.begin_window())
        elif event == "invalidate":
            controller.invalidate("TIMEOUT")
            replacement.append(controller.begin_window())
        else:
            controller.close()
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
        events.append(event)

    if boundary == "read":
        original = reader.read_snapshot
        def wrapper(context):
            result = original(context)
            transition()
            return result
        monkeypatch.setattr(reader, "read_snapshot", wrapper)
        monkeypatch.setattr(reader, "revalidate", lambda *_: pytest.fail("stale initial read must skip final read"))
    elif boundary == "revalidate":
        original = reader.revalidate
        def wrapper(snapshot, context):
            result = original(snapshot, context)
            transition()
            return result
        monkeypatch.setattr(reader, "revalidate", wrapper)
    else:
        original = m._build_projection
        def wrapper(*args):
            data = original(*args)
            transition()
            return data
        monkeypatch.setattr(m, "_build_projection", wrapper)

    expect_error("RUNTIME_CLOSED" if event == "close" else "WINDOW_STALE", controller.project, ticket, raw)
    assert events == [event]
    assert controller._lease.evaluation is None
    if event == "close":
        new = m.MeterRuntimeController(reader)
        assert new.policy_producer_epoch == reader.producer_epoch
    else:
        assert controller._lease.ticket is replacement[0]
        assert controller._lease.ticket_state == "UNUSED"
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)


@pytest.mark.parametrize("boundary", ["read", "revalidate"])
def test_busy_before_history_duplicate_foreign_cannot_release_running_slot(live, monkeypatch, boundary):
    controller, reader, _, _ = live
    old = controller.begin_window()
    old_raw = wire(request(old))
    newer = []
    called = []
    method = "read_snapshot" if boundary == "read" else "revalidate"
    original = getattr(reader, method)

    def interleave(*args):
        result = original(*args)
        owner = controller._lease.evaluation
        assert owner is not None
        expect_error("TICKET_CONSUMED", controller.project, old, old_raw)
        assert controller._lease.evaluation is owner
        current = controller.begin_window()
        before = (controller._lease.finite_floor, controller._lease.clip_floor,
                  deepcopy(controller._lease.peak_floor), controller._lease.history_latch)
        # This otherwise regresses history; busy must take precedence and not latch.
        bad_history = observation(current.query_context.to_dict(), total=1, peak=-30.0)
        expect_error("RUNTIME_BUSY", controller.project, current, wire(request(current, bad_history)))
        assert before == (controller._lease.finite_floor, controller._lease.clip_floor,
                          controller._lease.peak_floor, controller._lease.history_latch)
        assert controller._lease.evaluation is owner
        fresh = controller.begin_window()
        fresh_raw = wire(request(fresh, observation(fresh.query_context.to_dict(), total=2)))
        expect_error("WINDOW_STALE", controller.project, old, old_raw)
        assert controller._lease.ticket is fresh
        assert controller._lease.evaluation is owner
        newer.append((fresh, fresh_raw))
        called.append(True)
        return result
    monkeypatch.setattr(reader, method, interleave)
    expect_error("WINDOW_STALE", controller.project, old, old_raw)
    assert called == [True]
    assert controller._lease.evaluation is None
    monkeypatch.setattr(reader, method, original)
    assert controller.project(*newer[0]).to_dict()["display_band"] == "TARGET"


def test_guard_not_held_across_p1_io_and_close_drains_before_reacquire(live, monkeypatch):
    controller, reader, _, _ = live
    ticket = controller.begin_window()
    raw = wire(request(ticket))
    read_entered, release_read, control_finished = threading.Event(), threading.Event(), threading.Event()
    outcomes = []

    def slow(context):
        read_entered.set()
        assert release_read.wait(5), "bounded test read not released"
        return p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus.NOT_BOUND, None)
    monkeypatch.setattr(reader, "read_snapshot", slow)

    def evaluate():
        try:
            controller.project(ticket, raw)
        except BaseException as error:
            outcomes.append(error)

    def close_host():
        controller.close()
        control_finished.set()
    worker = threading.Thread(target=evaluate)
    closer = threading.Thread(target=close_host)
    worker.start()
    try:
        assert read_entered.wait(5)
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
        closer.start()
        assert control_finished.wait(5), "short guard was held across P1 I/O"
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
    finally:
        release_read.set()
        worker.join(5)
        if closer.ident is not None:
            closer.join(5)
    assert not worker.is_alive() and not closer.is_alive()
    assert len(outcomes) == 1 and outcomes[0].reason == "RUNTIME_CLOSED"
    replacement = m.MeterRuntimeController(reader)
    assert replacement.policy_producer_epoch == reader.producer_epoch


@pytest.mark.parametrize("boundary", ["read", "revalidate", "diagnostic", "build"])
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_baseexception_reraised_same_object_finally_cleans(live, monkeypatch, boundary, exception):
    controller, reader, _, _ = live
    sentinel = exception("synthetic interrupt")
    calls = []
    original = reader.read_snapshot

    def read(context):
        calls.append("read")
        if boundary == "read" or boundary == "diagnostic" and len(calls) == 2:
            raise sentinel
        if boundary == "diagnostic":
            return p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus.NOT_BOUND, None)
        return original(context)

    def fail(*_):
        calls.append(boundary)
        raise sentinel
    monkeypatch.setattr(reader, "read_snapshot", read)
    if boundary == "revalidate":
        monkeypatch.setattr(reader, "revalidate", fail)
    elif boundary == "build":
        monkeypatch.setattr(m, "_build_projection", fail)
    ticket = controller.begin_window()
    with pytest.raises(exception) as caught:
        controller.project(ticket, wire(request(ticket)))
    assert caught.value is sentinel
    if boundary == "read":
        assert calls == ["read"]
    assert controller._lease.evaluation is None
    assert controller._lease.ticket is None
    expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
    controller.close()
    m.MeterRuntimeController(reader)


@pytest.mark.parametrize("boundary", ["parse", "history", "build", "serialize"])
def test_unexpected_pure_error_safe_no_output_cleanup(live, monkeypatch, boundary):
    controller, reader, _, _ = live
    ticket = controller.begin_window()
    raw = wire(request(ticket))

    def fail(*_args, **_kwargs):
        raise RuntimeError("SECRET: input body and private file path")
    target = {"parse": "_parse", "history": "_history", "build": "_build_projection",
              "serialize": "_serialize"}[boundary]
    with monkeypatch.context() as patch:
        patch.setattr(m, target, fail)
        error = expect_error("INTERNAL_ERROR", controller.project, ticket, raw)
        assert "SECRET" not in str(error)
    assert controller._lease.evaluation is None
    assert controller._lease.projection is None
    expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
    # Accepted history stays a lower bound; retry must use a new window/cumulative report.
    assert emit(controller, total=2)["display_band"] == "TARGET"


def test_parsing_interleave_does_not_clear_new_ticket(live, monkeypatch):
    controller = live[0]
    old = controller.begin_window()
    raw = wire(request(old))
    replacement = []
    original = m.parse_meter_runtime_request

    def parse(data):
        replacement.append(controller.begin_window())
        return original(data)
    monkeypatch.setattr(m, "parse_meter_runtime_request", parse)
    expect_error("WINDOW_STALE", controller.project, old, raw)
    assert controller._lease.ticket is replacement[0]
    assert controller._lease.ticket_state == "UNUSED"


def test_exact_store_identity_gc_strong_owner_and_no_reinit(project):
    reader = p1.MeterPolicyProjectStore(project, "meter-project")
    controller = m.MeterRuntimeController(reader)
    identity = id(controller)
    del controller
    gc.collect()
    expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
    owner = next(item.controller for item in m._LEASES if item.store is reader)
    assert id(owner) == identity
    expect_error("NOT_SUPPORTED", owner.__init__, reader)
    owner.close()
    owner.close()
    expect_error("NOT_SUPPORTED", owner.__init__, reader)
    expect_error("RUNTIME_CLOSED", owner.begin_window)
    replacement = m.MeterRuntimeController(reader)
    assert replacement is not owner
    # An old terminal owner cannot release a subsequently acquired owner.
    owner.close()
    expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)


def test_lease_cap_exact_distinct_objects_same_project_and_epoch(project, monkeypatch):
    monkeypatch.setattr(p1.MeterPolicyProjectStore, "producer_epoch", property(lambda self: UIDS[4]))
    stores = [p1.MeterPolicyProjectStore(project, "meter-project") for _ in range(65)]
    controllers = [m.MeterRuntimeController(store) for store in stores[:64]]
    assert len({id(item) for item in controllers}) == 64
    expect_error("CAPACITY_EXHAUSTED", m.MeterRuntimeController, stores[64])
    expect_error("RUNTIME_BUSY", m.MeterRuntimeController, stores[0])
    controllers[0].close()
    m.MeterRuntimeController(stores[64])


def test_constructor_partial_failure_does_not_release_other_owner(project, monkeypatch):
    first = p1.MeterPolicyProjectStore(project, "meter-project")
    second = p1.MeterPolicyProjectStore(project, "meter-project")
    owner = m.MeterRuntimeController(first)

    class AppendThenFail(list):
        def append(self, item):
            super().append(item)
            raise RuntimeError("synthetic partial admission failure")
    registry = AppendThenFail(m._LEASES)
    with monkeypatch.context() as patch:
        patch.setattr(m, "_LEASES", registry)
        expect_error("INTERNAL_ERROR", m.MeterRuntimeController, second)
        assert len(registry) == 1 and registry[0].controller is owner
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, first)
    assert owner._lease in m._LEASES


def test_window_capacity_exact_and_one_over(project):
    reader = p1.MeterPolicyProjectStore(project, "meter-project")
    controller = m.MeterRuntimeController(reader)
    controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[1])
    ids = set()
    for sequence in range(1, 65_537):
        ticket = controller.begin_window()
        context = ticket.query_context
        assert context.window_sequence == sequence
        ids.add(context.request_id)
    assert len(ids) == 65_536
    expect_error("CAPACITY_EXHAUSTED", controller.begin_window)
    assert controller._lease.sequence == 65_536
    controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[6])
    assert controller.begin_window().query_context.window_sequence == 1


def test_epoch_and_session_capacity_exact_one_over(project):
    reader = p1.MeterPolicyProjectStore(project, "meter-project")
    controller = m.MeterRuntimeController(reader)
    for _ in range(4096):
        controller.activate_consumer(session_id=UIDS[0], consumer_epoch=uid())
    expect_error("CAPACITY_EXHAUSTED", lambda: controller.activate_consumer(session_id=UIDS[0], consumer_epoch=uid()))
    controller.close()
    controller = m.MeterRuntimeController(reader)
    for _ in range(64):
        controller.activate_consumer(session_id=uid(), consumer_epoch=uid())
    expect_error("CAPACITY_EXHAUSTED", lambda: controller.activate_consumer(session_id=uid(), consumer_epoch=uid()))


@pytest.mark.parametrize("reason", ["PROJECT_CHANGED", "READBACK_UNAVAILABLE", "TIMEOUT", "PAUSED",
                                    "RESUMED", "RECONNECT", "HOST_RESTORE_UNCERTAIN"])
def test_invalidation_reset_rules(live, reason):
    controller, reader, _, _ = live
    doc = emit(controller, total=4)
    controller.invalidate(reason)
    assert controller._lease.projection is None
    assert controller._lease.finite_floor == 4
    if reason == "HOST_RESTORE_UNCERTAIN":
        expect_error("RUNTIME_CLOSED", controller.begin_window)
        m.MeterRuntimeController(reader)
    else:
        expect_error("RUNTIME_BUSY", m.MeterRuntimeController, reader)
        if reason == "RECONNECT":
            expect_error("CONTEXT_MISMATCH", controller.begin_window)
            controller.activate_consumer(session_id=doc["query_context"]["session_id"], consumer_epoch=uid())
        assert emit(controller, total=5)["display_band"] == "TARGET"


def test_no_effect_routes_or_p1_private_admission_access():
    source = (ROOT / "src/ai_video_production/voice_quality_meter_runtime_contract.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name and any(part in name for part in ("provider", "audio", "project_save", "subprocess")) for name in imports)
    calls = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not any(isinstance(call, ast.Attribute) and call.attr in {
        "apply", "read_operation_receipt", "save", "recover", "Popen", "run", "Thread", "start",
        "_collect", "_read_once", "_require_open", "_result",
    } for call in calls)
    assert not any(isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                   and node.value.id == "snapshot" and node.attr in {"_token", "_admitted"}
                   for node in ast.walk(tree))
    assert "audio_body_read" not in source
    assert "capture_transport_blocked" not in source
    assert "emergency_stop_blocked" not in source
    assert not any(isinstance(call, ast.Name) and call.id in {"open", "exec", "eval", "compile"} for call in calls)


def test_audio_shaped_child_hash_disclosure_without_semantic_decode(project, monkeypatch):
    payload = b"RIFF\x10\x00\x00\x00WAVEsynthetic-silence-only"
    current = ProductProjectManifestStore.load(project)
    binding = ProjectChildBinding("TASK-043", "synthetic-audio.wav", "synthetic.audio", "1.0.0",
                                  sha256_bytes(payload), False)
    target = ProductProjectManifest.create(
        project_id=current.project_id, project_revision=2, product_version=current.product_version,
        timebase=current.timebase, child_bindings=[binding],
        created_at=current.created_at, updated_at=current.updated_at,
    )
    ProductProjectSaveCoordinator().save(
        project, target, {binding.relative_path: payload},
        expected_previous_manifest_sha256=current.project_manifest_sha256,
    )
    reader = p1.MeterPolicyProjectStore(project, "meter-project")
    controller = m.MeterRuntimeController(reader)
    controller.activate_consumer(session_id=UIDS[0], consumer_epoch=UIDS[1])
    doc = emit(controller)
    assert doc["reason_code"] == "POLICY_NOT_BOUND"
    assert doc["io_boundary"]["project_integrity_hash_reads_possible"] is True
    assert doc["io_boundary"]["audio_semantic_decode_executed"] is False
    # Corrupt only our synthetic bound child: the inherited integrity path notices.
    (project / binding.relative_path).write_bytes(b"changed synthetic bytes")
    doc = emit(controller, total=2)
    assert doc["policy_observation"]["initial_status"] == "INVALID"
    assert b"RIFF" not in wire(doc)


# Literal canonical preimages and hashes, fixed independently of runtime helpers.
GOLDEN_RECORDS = {
    "observation": (
        "{\"canonical_owner_task\":\"TASK-048\",\"capture_point\":\"TASK047_CONTROLLER_RECEIVED_FLOAT32_PRE_DRAW\",\"paused\":false,\"query_context\":{\"consumer_epoch\":\"00000000-0000-4000-8000-000000000002\",\"project_id\":\"meter-project\",\"request_id\":\"00000000-0000-4000-8000-000000000003\",\"session_id\":\"00000000-0000-4000-8000-000000000001\",\"window_sequence\":1},\"record_type\":\"Task048MeterRuntimeObservationV1\",\"schema_version\":1,\"session_counts\":{\"clip_sample_values\":0,\"finite_sample_values\":1,\"state\":\"VALID\"},\"session_peak\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0},\"window_counts\":{\"clip_sample_values\":0,\"finite_sample_values\":1,\"nonfinite_sample_values\":0,\"state\":\"VALID\"},\"window_loss_state\":\"NO_LOSS_REPORTED\",\"window_peak\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0},\"window_rms\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0}}",
        "sha256:0988969cd5eb0982ce6c21b9cf05d63d5bda92dafb8f161d7774a29bcd533730",
    ),
    "request": (
        "{\"canonical_owner_task\":\"TASK-048\",\"observation\":{\"canonical_owner_task\":\"TASK-048\",\"capture_point\":\"TASK047_CONTROLLER_RECEIVED_FLOAT32_PRE_DRAW\",\"observation_sha256\":\"sha256:0988969cd5eb0982ce6c21b9cf05d63d5bda92dafb8f161d7774a29bcd533730\",\"paused\":false,\"query_context\":{\"consumer_epoch\":\"00000000-0000-4000-8000-000000000002\",\"project_id\":\"meter-project\",\"request_id\":\"00000000-0000-4000-8000-000000000003\",\"session_id\":\"00000000-0000-4000-8000-000000000001\",\"window_sequence\":1},\"record_type\":\"Task048MeterRuntimeObservationV1\",\"schema_version\":1,\"session_counts\":{\"clip_sample_values\":0,\"finite_sample_values\":1,\"state\":\"VALID\"},\"session_peak\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0},\"window_counts\":{\"clip_sample_values\":0,\"finite_sample_values\":1,\"nonfinite_sample_values\":0,\"state\":\"VALID\"},\"window_loss_state\":\"NO_LOSS_REPORTED\",\"window_peak\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0},\"window_rms\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0}},\"policy_producer_epoch\":\"00000000-0000-4000-8000-000000000005\",\"query_context\":{\"consumer_epoch\":\"00000000-0000-4000-8000-000000000002\",\"project_id\":\"meter-project\",\"request_id\":\"00000000-0000-4000-8000-000000000003\",\"session_id\":\"00000000-0000-4000-8000-000000000001\",\"window_sequence\":1},\"record_type\":\"Task048MeterRuntimeWindowRequestV1\",\"runtime_epoch\":\"00000000-0000-4000-8000-000000000004\",\"schema_version\":1}",
        "sha256:bfb0abc58ea59ef4821df2113b9a5c9d913765663df7e001deb1c399a72e506e",
    ),
    "projection": (
        "{\"authority\":{\"authority_created\":false,\"capture_authorized\":false,\"capture_path_noninterference_confirmed\":false,\"consent_asset_training_model_authorized\":false,\"emergency_stop_noninterference_confirmed\":false,\"gain_change_authorized\":false,\"hardware_or_obs_setting_changed\":false,\"production_authorized\":false,\"provider_invoked\":false,\"quality_pass_issued\":false,\"temporal_freshness_confirmed\":false},\"canonical_owner_task\":\"TASK-048\",\"display_band\":\"TARGET\",\"io_boundary\":{\"audio_semantic_decode_executed\":false,\"audio_used_as_policy_input\":false,\"capture_transport_api_invoked\":false,\"emergency_stop_api_invoked\":false,\"policy_or_project_write_executed\":false,\"project_integrity_hash_reads_possible\":true},\"live_admission_serialized\":false,\"observation\":{\"canonical_owner_task\":\"TASK-048\",\"capture_point\":\"TASK047_CONTROLLER_RECEIVED_FLOAT32_PRE_DRAW\",\"observation_sha256\":\"sha256:0988969cd5eb0982ce6c21b9cf05d63d5bda92dafb8f161d7774a29bcd533730\",\"paused\":false,\"query_context\":{\"consumer_epoch\":\"00000000-0000-4000-8000-000000000002\",\"project_id\":\"meter-project\",\"request_id\":\"00000000-0000-4000-8000-000000000003\",\"session_id\":\"00000000-0000-4000-8000-000000000001\",\"window_sequence\":1},\"record_type\":\"Task048MeterRuntimeObservationV1\",\"schema_version\":1,\"session_counts\":{\"clip_sample_values\":0,\"finite_sample_values\":1,\"state\":\"VALID\"},\"session_peak\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0},\"window_counts\":{\"clip_sample_values\":0,\"finite_sample_values\":1,\"nonfinite_sample_values\":0,\"state\":\"VALID\"},\"window_loss_state\":\"NO_LOSS_REPORTED\",\"window_peak\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0},\"window_rms\":{\"state\":\"FINITE\",\"value_dbfs\":-18.0}},\"observation_state\":\"MEASURED\",\"operator_label\":\"目標範囲\",\"policy_observation\":{\"effective_status\":\"PROJECT_HEAD_MATCHED_SNAPSHOT\",\"final_status\":\"PROJECT_HEAD_MATCHED_SNAPSHOT\",\"identity\":{\"child_sha256\":\"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"producer_epoch\":\"00000000-0000-4000-8000-000000000005\",\"project_id\":\"meter-project\",\"project_manifest_sha256\":\"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"project_revision\":4,\"selected_policy_sha256\":\"sha256:bb7625e026b618867acf591450d5696ec825cdcd09b88b973809c9045d7d39be\",\"state_revision\":3},\"initial_status\":\"PROJECT_HEAD_MATCHED_SNAPSHOT\",\"policy_document\":{\"canonical_owner_task\":\"TASK-048\",\"policy_ref\":\"meter-policy\",\"policy_revision\":1,\"policy_revision_sha256\":\"sha256:bb7625e026b618867acf591450d5696ec825cdcd09b88b973809c9045d7d39be\",\"predecessor_policy_sha256\":null,\"record_type\":\"Task048MeterDisplayPolicyRevisionV1\",\"schema_version\":1,\"target_ceiling_dbfs\":-12.0,\"target_floor_dbfs\":-24.0,\"true_clip_dbfs\":0.0,\"warning_dbfs\":-3.0},\"window_policy_matched\":true},\"policy_producer_epoch\":\"00000000-0000-4000-8000-000000000005\",\"query_context\":{\"consumer_epoch\":\"00000000-0000-4000-8000-000000000002\",\"project_id\":\"meter-project\",\"request_id\":\"00000000-0000-4000-8000-000000000003\",\"session_id\":\"00000000-0000-4000-8000-000000000001\",\"window_sequence\":1},\"reason_code\":\"WINDOW_POLICY_CLASSIFIED\",\"record_type\":\"Task048MeterRuntimeDecisionProjectionV1\",\"request_sha256\":\"sha256:bfb0abc58ea59ef4821df2113b9a5c9d913765663df7e001deb1c399a72e506e\",\"runtime_epoch\":\"00000000-0000-4000-8000-000000000004\",\"schema_version\":1,\"scope_label\":\"今回の観測窓に対する方針照合\",\"window_only\":true}",
        "sha256:02290e0a58ef1b031955286138c72626c3084c8ffd7df8b59b9a5e9b4548ba65",
    ),
}


@pytest.mark.parametrize("kind", ["observation", "request", "projection"])
def test_literal_golden_complete_preimages_and_domain_hashes(kind):
    literal, digest = GOLDEN_RECORDS[kind]
    preimage = literal.encode("utf-8")
    assert "sha256:" + hashlib.sha256(DOMAINS[kind] + preimage).hexdigest() == digest
    document = json.loads(preimage)
    document[DIGESTS[kind]] = digest
    serialize = getattr(m, "serialize_meter_runtime_" + kind)
    parse = getattr(m, "parse_meter_runtime_" + kind)
    raw = serialize(document)
    assert parse(raw) == document
    assert wire({k: v for k, v in parse(raw).items() if k != DIGESTS[kind]}) == preimage


@pytest.mark.parametrize("scalar,clips,expected", [
    ("0.1", 1, "0f4bbcec2bf08947184b88628b5f953c96e238821dcd6090b06a02146e0de893"),
    ("6.0", 1, "59d91535b18dd456e86de5fde07ae640c3d6e052478519c103f245c61334738a"),
    ("12.0", 1, "6856354a6b5efd8627f64f291412e4d269f8cb0d11d75487061fde91f8383e29"),
    ("18.0", 1, "024eaf433e97822e79d255f7f17084ca8c6031f6dbf242381d5a18f04da5a903"),
    ("1.7976931348623157e+308", 1, "4fbcd948af411590cfd668dbf8d9fc894742a597d69711b279c60465280b1621"),
    ("-1.7976931348623157e+308", 0, "c3c6dba8ed9b387c74fdfe64ffece490ccce8a5e7312b872e6bc921c67341560"),
    ("0.0", 1, "956f1f8accb2b7c789aeda52b933aba0fa75e95a8b8fb15a2e8a50f6ca0b6806"),
    ("-0.0", 1, "107ebc0632c4a39a34a147e1d74504329855c8e8466ef90899c8bf1f9f3f83bc"),
    ("-0.000868776543637768", 0, "d829df36a94d6a6ef6489ae2fd4d114a71659f7c4ed5e4e99508096954256141"),
    ("-0.000868258772501058", 1, "0d33158a8ed0ef6cf82e8689377536bc94c809aabf83c534cc3b71a11b45a4fe"),
    ("-0.0008686323961501121", 1, "a0cf5ca5a9e8244e6f334cbd56ae92932526beff44746336306910f17701db79"),
])
def test_literal_scalar_golden_preimages_not_derived_by_runtime(scalar, clips, expected):
    preimage = GOLDEN_RECORDS["observation"][0].replace("-18.0", scalar)
    if clips:
        preimage = preimage.replace('"clip_sample_values":0', '"clip_sample_values":1')
    literal = preimage.encode("utf-8")
    assert hashlib.sha256(DOMAINS["observation"] + literal).hexdigest() == expected
    doc = json.loads(literal)
    doc["observation_sha256"] = "sha256:" + expected
    actual = m.parse_meter_runtime_observation(m.serialize_meter_runtime_observation(doc))
    assert wire({k: v for k, v in actual.items() if k != "observation_sha256"}) == literal


@pytest.mark.parametrize("late_failure", [False, True])
def test_duplicate_finishes_during_other_parse_cannot_clear_admitted_owner(live, monkeypatch, late_failure):
    controller = live[0]
    ticket = controller.begin_window()
    raw = wire(request(ticket))
    original = m.parse_meter_runtime_request
    nested = []
    entered = False

    def parse(data):
        nonlocal entered
        if not entered:
            entered = True
            nested.append(controller.project(ticket, raw))
            if late_failure:
                raise RuntimeError("synthetic late parser failure")
        return original(data)
    monkeypatch.setattr(m, "parse_meter_runtime_request", parse)
    expect_error("INTERNAL_ERROR" if late_failure else "TICKET_CONSUMED", controller.project, ticket, raw)
    assert nested[0].to_dict()["display_band"] == "TARGET"
    assert controller._lease.ticket_state == "CONSUMED"
    assert controller._lease.evaluation is None


def test_changed_store_epoch_still_permits_exact_owner_close(live, monkeypatch):
    controller, reader, _, _ = live
    with monkeypatch.context() as patch:
        # Deliberate violation of the documented host precondition, not a supported
        # way to change producer identity. P2 still must allow owner-only teardown.
        patch.setattr(p1.MeterPolicyProjectStore, "producer_epoch", property(lambda self: UIDS[6]))
        expect_error("EPOCH_MISMATCH", controller.begin_window)
        controller.close()
    replacement = m.MeterRuntimeController(reader)
    assert replacement.policy_producer_epoch == reader.producer_epoch


def test_unexpected_schema_loader_error_is_internal_not_readback(monkeypatch):
    def fail():
        raise RuntimeError("SECRET resource fault")
    monkeypatch.setattr(m, "_SCHEMA_ENTRYPOINTS", None)
    monkeypatch.setattr(m, "_load_entrypoints", fail)
    expect_error("INTERNAL_ERROR", m.parse_meter_runtime_observation, wire(observation()))


@pytest.mark.parametrize("attribute", ["status", "snapshot"])
def test_malformed_exact_read_result_maps_mismatch(live, monkeypatch, attribute):
    controller, reader, _, _ = live
    result = p1.MeterPolicyReadResult(p1.MeterPolicyReadStatus.PROJECT_HEAD_MATCHED_SNAPSHOT, None)
    object.__delattr__(result, attribute)
    monkeypatch.setattr(reader, "read_snapshot", lambda _: result)
    doc = emit(controller)
    assert doc["policy_observation"]["initial_status"] == "MISMATCH"
    assert doc["policy_observation"]["final_status"] == "MISMATCH"


@pytest.mark.parametrize("field", ["producer_epoch", "context", "project_revision", "policy", "context_missing"])
def test_invalid_nominal_final_snapshot_is_mismatch(live, monkeypatch, field):
    controller, reader, _, _ = live
    original = reader.revalidate

    def revalidate(snapshot, context):
        result = original(snapshot, context)
        changed = result.snapshot
        assert changed is not None
        if field == "context_missing":
            object.__delattr__(changed, "context")
        else:
            value = {
                "producer_epoch": UIDS[6],
                "context": p1.MeterPolicyQueryContext("meter-project", UIDS[6], UIDS[1], 1, UIDS[2]),
                "project_revision": 4.0, "policy": {},
            }[field]
            object.__setattr__(changed, field, value)
        return result
    monkeypatch.setattr(reader, "revalidate", revalidate)
    doc = emit(controller)
    assert doc["policy_observation"]["initial_status"] == "PROJECT_HEAD_MATCHED_SNAPSHOT"
    assert doc["policy_observation"]["final_status"] == "MISMATCH"
    assert doc["policy_observation"]["identity"] is None


@pytest.mark.parametrize("initial", [status.value for status in p1.MeterPolicyReadStatus])
@pytest.mark.parametrize("final", [status.value for status in p1.MeterPolicyReadStatus])
def test_complete_effective_status_matrix_is_recomputed(initial, final):
    matched = initial == final == "PROJECT_HEAD_MATCHED_SNAPSHOT"
    effective = final if final != "PROJECT_HEAD_MATCHED_SNAPSHOT" else initial
    reasons = {
        "NOT_BOUND": "POLICY_NOT_BOUND", "REVOKED": "POLICY_REVOKED", "STALE": "POLICY_STALE",
        "MISMATCH": "POLICY_MISMATCH", "RECOVERY_REQUIRED": "PROJECT_RECOVERY_REQUIRED",
        "ROLLBACK_UNCERTAIN": "PROJECT_ROLLBACK_UNCERTAIN", "INVALID": "POLICY_INVALID",
        "READBACK_FAILED": "POLICY_READBACK_FAILED",
    }
    doc = diagnostic(initial=initial, final=final,
                     band="TARGET" if matched else "UNCONFIRMED",
                     reason="WINDOW_POLICY_CLASSIFIED" if matched else reasons[effective],
                     label="目標範囲" if matched else "適正判定 未確定")
    assert m.parse_meter_runtime_projection(wire(doc)) == doc
    for key, value in (("window_policy_matched", not matched),
                       ("effective_status", "INVALID" if effective != "INVALID" else "STALE")):
        invalid = deepcopy(doc)
        invalid["policy_observation"][key] = value
        expect_error("SCHEMA_INVALID", m.parse_meter_runtime_projection, wire(rehash(invalid, "projection")))


@pytest.mark.parametrize("peak", [0.1, 6.0, 12.0, 18.0, sys.float_info.max, -sys.float_info.max, 0.0, -0.0])
def test_finite_values_through_genuine_live_projection(live, peak):
    doc = emit(live[0], peak=peak)
    for name in ("window_peak", "window_rms", "session_peak"):
        assert struct.pack(">d", doc["observation"][name]["value_dbfs"]) == struct.pack(">d", peak)
    assert doc["display_band"] == ("TRUE_CLIP" if peak >= 0.0 else "BELOW_TARGET")


@pytest.mark.parametrize("changes,reason", [
    ({"paused": True}, "OBSERVATION_PAUSED"),
    ({"window_loss_state": "LOSS_REPORTED"}, "OBSERVATION_LOSS"),
    ({"nonfinite": 1}, "OBSERVATION_NONFINITE"),
])
def test_positive_raw_peak_never_bypasses_observation_gates(live, changes, reason):
    doc = emit(live[0], peak=18.0, **changes)
    assert doc["display_band"] == "UNCONFIRMED"
    assert doc["reason_code"] == reason
    assert doc["observation"]["window_peak"]["value_dbfs"] == 18.0


@pytest.mark.parametrize("corruption", ["child", "partial", "journal", "manifest", "missing", "unreadable"])
def test_p2_corrupt_missing_unreadable_project_never_repairs(live, monkeypatch, corruption):
    from ai_video_production.project_save import ProjectSaveJournalStore
    controller, _, _, project = live
    target = {
        "child": project / p1.CHILD_PATH, "partial": project / p1.CHILD_PATH,
        "journal": ProjectSaveJournalStore.path(project), "manifest": ProductProjectManifestStore.path(project),
        "missing": project / p1.CHILD_PATH, "unreadable": project / p1.CHILD_PATH,
    }[corruption]
    if corruption == "missing":
        target.rename(target.with_name("preserved-test-child.json"))
    elif corruption == "unreadable":
        # Inject only exact test-owned file-open failure, not an ACL/native change.
        original = p1.os.open
        def deny(path, *args, **kwargs):
            if Path(path) == target:
                raise PermissionError("synthetic denied child")
            return original(path, *args, **kwargs)
        monkeypatch.setattr(p1.os, "open", deny)
    else:
        target.write_bytes(b"{" if corruption == "partial" else b"synthetic malformed")
    before = {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    doc = emit(controller)
    assert doc["policy_observation"]["initial_status"] in {"INVALID", "READBACK_FAILED"}
    assert doc["policy_observation"]["identity"] is None
    assert before == {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}


def test_p2_pending_recovery_is_parked_without_repair(live):
    controller, _, _, project = live

    def fail(stage, _root):
        if stage == "before_manifest_commit":
            raise RuntimeError("synthetic pending commit")
    writer = p1.MeterPolicyProjectStore(
        project, "meter-project", coordinator=ProductProjectSaveCoordinator(failure_injector=fail),
    )
    with pytest.raises(p1.MeterPolicyStoreError, match="COMMIT_NOT_CONFIRMED"):
        apply(project, writer, "REVOKE_POLICY", {"policy_revision_sha256": policy()["policy_revision_sha256"]})
    before = {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    doc = emit(controller)
    assert doc["policy_observation"]["initial_status"] == "RECOVERY_REQUIRED"
    assert doc["policy_observation"]["final_status"] == "RECOVERY_REQUIRED"
    assert before == {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    writer.close()


def test_p2_known_rollback_survives_controller_replacement_same_store(live):
    from ai_video_production.project_save import ProjectSaveJournalStore
    controller, reader, _, project = live
    old = ProductProjectManifestStore.load(project)
    assert emit(controller)["display_band"] == "TARGET"
    target = ProductProjectManifest.create(
        project_id=old.project_id, project_revision=old.project_revision + 1,
        product_version=old.product_version, timebase=old.timebase, child_bindings=old.child_bindings,
        created_at=old.created_at, updated_at=old.updated_at,
    )
    ProductProjectSaveCoordinator().save(
        project, target, {}, expected_previous_manifest_sha256=old.project_manifest_sha256,
    )
    assert emit(controller, total=2)["display_band"] == "TARGET"
    ProductProjectManifestStore.path(project).write_bytes(wire(old.to_dict()))
    journal = ProjectSaveJournalStore.path(project)
    journal.rename(journal.with_name("preserved-test-terminal-journal.json"))
    doc = emit(controller, total=3)
    assert doc["reason_code"] == "PROJECT_ROLLBACK_UNCERTAIN"
    controller.invalidate("HOST_RESTORE_UNCERTAIN")
    replacement = m.MeterRuntimeController(reader)
    replacement.activate_consumer(session_id=uid(), consumer_epoch=uid())
    assert emit(replacement)["reason_code"] == "PROJECT_ROLLBACK_UNCERTAIN"
