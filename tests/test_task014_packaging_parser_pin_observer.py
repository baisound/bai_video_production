from __future__ import annotations

import ast
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import ssl

from jsonschema import Draft202012Validator
import pytest

from ai_video_production import packaging_parser_pin_observer as observer


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/packaging-parser-pin-observation.schema.json"
MIRROR = ROOT / "src/ai_video_production/schema_resources" / SCHEMA.name


def _document() -> dict[str, object]:
    return {
        "info": {"name": "packaging", "version": "25.0", "requires_python": ">=3.8"},
        "urls": [
            {
                "filename": "packaging-25.0.tar.gz", "packagetype": "sdist", "size": 1,
                "url": "https://files.pythonhosted.org/source.tar.gz", "requires_python": ">=3.8",
                "yanked": False, "python_version": "source", "digests": {"sha256": "0" * 64},
            },
            {
                "filename": observer.proposed.WHEEL_FILENAME, "packagetype": "bdist_wheel",
                "python_version": "py3", "size": observer.proposed.WHEEL_BYTES,
                "url": observer.proposed.SOURCE_URL, "requires_python": ">=3.8", "yanked": False,
                "digests": {"sha256": observer.proposed.WHEEL_SHA256.removeprefix("sha256:")},
                "core-metadata": {"sha256": observer.proposed.METADATA_SHA256.removeprefix("sha256:")},
            },
        ],
        "vulnerabilities": [],
    }


def _raw(document: object | None = None) -> bytes:
    return json.dumps(_document() if document is None else document, sort_keys=True, separators=(",", ":")).encode()


class FakePort:
    def __init__(self, body: bytes | None = None, *, failure: Exception | None = None) -> None:
        self.body = body if body is not None else _raw(); self.failure = failure; self.calls = 0

    def fetch(self) -> observer._FetchResult:
        self.calls += 1
        if self.failure is not None: raise self.failure
        return observer._FetchResult(self.body, 4, True, True, 0, "application/json")


def _observe(monkeypatch: pytest.MonkeyPatch, port: FakePort) -> dict[str, object]:
    monkeypatch.setattr(observer._StdlibHttpsPort, "fetch", lambda _self: port.fetch())
    return observer.observe_official_packaging_250_metadata("2026-08-21T02:00:00Z").to_dict()


def _assert_contract(receipt: dict[str, object]) -> None:
    assert observer.parse_packaging_pin_observation(receipt) == receipt
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert not list(Draft202012Validator(schema).iter_errors(receipt))


def test_success_observation_round_trips_schema_and_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    port = FakePort(); receipt = _observe(monkeypatch, port)
    assert port.calls == 1
    assert receipt["schema_version"] == "bai.task014.packaging-parser-pin-observation.v2"
    assert receipt["observer_revision"] == 2
    assert receipt["decision"] == "OFFICIAL_PACKAGING_PIN_OBSERVED_DIAGNOSTIC"
    assert receipt["official_metadata_observation_complete"] is True
    assert receipt["pin_acceptance_authorized"] is False
    assert receipt["artifact_body_observed"] is False
    assert receipt["metadata_network_accessed"] is True
    assert receipt["artifact_body_downloaded"] is False
    assert receipt["request_scheduled_count"] == 1 and receipt["request_sent_count"] == 1
    assert receipt["response_headers_observed"] is True and receipt["response_body_complete"] is True
    assert receipt["native_transport_origin_authenticated"] is False
    _assert_contract(receipt)


def test_historical_v1_receipt_cannot_be_confused_with_hardened_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _observe(monkeypatch, FakePort())
    receipt["schema_version"] = "bai.task014.packaging-parser-pin-observation.v1"
    receipt["observer_revision"] = 1
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = observer.sha256_bytes(
        b"TASK014_PACKAGING_PIN_OBSERVATION_V1\0" + observer.canonical_json_bytes(body)
    )
    with pytest.raises(ValueError):
        observer.parse_packaging_pin_observation(receipt)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(receipt))


@pytest.mark.parametrize(
    "mutation",
    ["project", "version", "requires-python", "filename", "size", "wheel-sha", "metadata-sha", "url", "yanked", "vulnerability", "duplicate-wheel"],
)
def test_candidate_mutations_block(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    document = _document(); info = document["info"]; urls = document["urls"]; wheel = urls[1]  # type: ignore[index]
    if mutation == "project": info["name"] = "evil"  # type: ignore[index]
    elif mutation == "version": info["version"] = "26.0"  # type: ignore[index]
    elif mutation == "requires-python": info["requires_python"] = ">=3.9"  # type: ignore[index]
    elif mutation == "filename": wheel["filename"] = "packaging-25.0-evil.whl"  # type: ignore[index]
    elif mutation == "size": wheel["size"] = 1  # type: ignore[index]
    elif mutation == "wheel-sha": wheel["digests"]["sha256"] = "0" * 64  # type: ignore[index]
    elif mutation == "metadata-sha": wheel["core-metadata"]["sha256"] = "0" * 64  # type: ignore[index]
    elif mutation == "url": wheel["url"] = "https://example.com/evil.whl"  # type: ignore[index]
    elif mutation == "yanked": wheel["yanked"] = True  # type: ignore[index]
    elif mutation == "vulnerability": document["vulnerabilities"] = [{"id": "x"}]
    else: urls.append(deepcopy(wheel))  # type: ignore[union-attr]
    receipt = _observe(monkeypatch, FakePort(_raw(document)))
    assert receipt["decision"] == "BLOCKED"
    assert receipt["official_metadata_observation_complete"] is False
    assert receipt["metadata_network_accessed"] is True
    assert receipt["metadata_response_observed"] is True
    _assert_contract(receipt)


@pytest.mark.parametrize(
    "body",
    [b"not-json", b'{"info":{},"info":{}}', b'{"info":{"name":NaN}}', b"\xff"],
)
def test_malformed_or_duplicate_json_blocks(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    receipt = _observe(monkeypatch, FakePort(body))
    assert receipt["decision"] == "BLOCKED" and receipt["reason_codes"] == ["METADATA_JSON_MALFORMED"]


@pytest.mark.parametrize(
    "result",
    [
        observer._FetchResult(_raw(), 0, True, True, 0, "application/json"),
        observer._FetchResult(_raw(), 1, False, True, 0, "application/json"),
        observer._FetchResult(_raw(), 1, True, False, 0, "application/json"),
        observer._FetchResult(_raw(), 1, True, True, 1, "application/json"),
        observer._FetchResult(_raw(), 1, True, True, 0, "text/plain"),
    ],
)
def test_transport_fact_mismatch_blocks(monkeypatch: pytest.MonkeyPatch, result: observer._FetchResult) -> None:
    class Port:
        def fetch(self) -> observer._FetchResult: return result
    monkeypatch.setattr(observer._StdlibHttpsPort, "fetch", lambda _self: Port().fetch())
    receipt = observer.observe_official_packaging_250_metadata("2026-08-21T02:00:00Z").to_dict()
    assert receipt["decision"] == "BLOCKED" and receipt["reason_codes"] == ["TRANSPORT_FACTS_MISMATCH"]
    _assert_contract(receipt)


def test_unknown_failure_is_phase_truthful(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = observer._PhaseFacts(
        resolved_address_count=2, all_resolved_addresses_global=True,
        tls_certificate_verified=True, connected_peer_in_resolved_set=True,
        request_sent_count=1, request_send_state="COMPLETE", response_headers_observed=True,
        content_type="application/json",
    )
    receipt = _observe(monkeypatch, FakePort(failure=observer._Unknown("RESPONSE_READ_FAILED", facts)))
    assert receipt["decision"] == "UNKNOWN" and receipt["reason_codes"] == ["RESPONSE_READ_FAILED"]
    assert receipt["response_bytes"] == 0 and receipt["response_sha256"] is None
    assert receipt["metadata_network_accessed"] is True and receipt["metadata_response_observed"] is False
    assert receipt["resolved_address_count"] == 2 and receipt["request_sent_count"] == 1
    assert receipt["response_headers_observed"] is True and receipt["response_body_complete"] is False
    _assert_contract(receipt)


def test_production_port_rejects_private_dns_before_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))])
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("socket opened for non-global DNS"))
    receipt = observer.observe_official_packaging_250_metadata("2026-08-21T02:00:00Z").to_dict()
    assert receipt["decision"] == "BLOCKED" and receipt["reason_codes"] == ["DNS_NON_GLOBAL_OR_AMBIGUOUS"]
    assert receipt["resolved_address_count"] == 1 and receipt["request_sent_count"] == 0
    _assert_contract(receipt)


def test_conflicting_metadata_aliases_block(monkeypatch: pytest.MonkeyPatch) -> None:
    document = _document()
    wheel = document["urls"][1]  # type: ignore[index]
    wheel["dist_info_metadata"] = {"sha256": "0" * 64}  # type: ignore[index]
    receipt = _observe(monkeypatch, FakePort(_raw(document)))
    assert receipt["decision"] == "BLOCKED" and receipt["reason_codes"] == ["CORE_METADATA_MALFORMED"]
    _assert_contract(receipt)


def test_closed_reason_and_phase_tamper_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = _observe(monkeypatch, FakePort(failure=observer._Unknown("CONNECTION_FAILED")))
    for field, value in (("reason_codes", ["ARBITRARY"]), ("response_headers_observed", True)):
        tampered = deepcopy(receipt); tampered[field] = value
        body = {key: item for key, item in tampered.items() if key != "receipt_sha256"}
        tampered["receipt_sha256"] = observer.sha256_bytes(b"TASK014_PACKAGING_PIN_OBSERVATION_V2\0" + observer.canonical_json_bytes(body))
        with pytest.raises(ValueError): observer.parse_packaging_pin_observation(tampered)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        assert list(Draft202012Validator(schema).iter_errors(tampered))


class _Headers:
    def __init__(self, pairs: list[tuple[str, str]]) -> None:
        self._pairs = pairs

    def items(self) -> list[tuple[str, str]]:
        return list(self._pairs)

    def get_all(self, name: str, default: list[str]) -> list[str]:
        values = [value for key, value in self._pairs if key.lower() == name.lower()]
        return values or default

    def get(self, name: str, default: str | None = None) -> str | None:
        values = self.get_all(name, [])
        return values[0] if values else default


class _Response:
    def __init__(
        self, body: bytes = b"{}", *, status: int = 200,
        headers: list[tuple[str, str]] | None = None, read_error: bool = False,
    ) -> None:
        self.status = status
        self.headers = headers or [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]
        self._body = body
        self._read_error = read_error

    def raw(self) -> bytes:
        reason = "OK" if self.status == 200 else "STATUS"
        header = b"".join(f"{name}: {value}\r\n".encode("latin-1") for name, value in self.headers)
        return f"HTTP/1.1 {self.status} {reason}\r\n".encode("ascii") + header + b"\r\n" + self._body


class _Stream(io.BytesIO):
    def __init__(self, response: _Response) -> None:
        super().__init__(response.raw()); self._read_error = response._read_error

    def read(self, amount: int = -1) -> bytes:
        if self._read_error:
            raise OSError("read failed")
        return super().read(amount)


class _RawSocket:
    family = socket.AF_INET

    def __init__(self) -> None:
        self.timeouts: list[float] = []

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def connect(self, _sockaddr: object) -> None:
        return None

    def close(self) -> None:
        return None


class _TlsSocket(_RawSocket):
    def __init__(self, request: list[bytes], response: _Response, peer: str = "8.8.8.8", send_error: bool = False) -> None:
        super().__init__(); self._request = request; self._response = response; self._peer = peer
        self._wire = response.raw(); self._offset = 0; self._send_error = send_error

    def getpeername(self) -> tuple[str, int]:
        return self._peer, 443

    def sendall(self, value: bytes) -> None:
        if self._send_error:
            raise OSError("partial send")
        self._request.append(value)

    def recv(self, amount: int) -> bytes:
        if self._response._read_error:
            raise OSError("read failed")
        value = self._wire[self._offset:self._offset + amount]
        self._offset += len(value)
        return value


def _native_port(
    monkeypatch: pytest.MonkeyPatch, response: _Response, *, peer: str = "8.8.8.8",
    addresses: list[str] | None = None, tls_error: bool = False, send_error: bool = False,
) -> list[bytes]:
    ips = addresses or ["8.8.8.8"]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443)) for ip in ips
    ])
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: _RawSocket())
    request: list[bytes] = []

    class Context:
        def wrap_socket(self, _raw: object, *, server_hostname: str) -> _TlsSocket:
            assert server_hostname == "pypi.org"
            if tls_error:
                raise ssl.SSLError("TLS failed")
            return _TlsSocket(request, response, peer, send_error)

    monkeypatch.setattr(ssl, "create_default_context", Context)
    return request


def test_native_port_uses_exact_request_and_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _native_port(monkeypatch, _Response(_raw()))
    result = observer._StdlibHttpsPort().fetch()
    assert result.body == _raw() and len(request) == 1
    assert request[0].startswith(b"GET /pypi/packaging/25.0/json HTTP/1.1\r\nHost: pypi.org\r\n")
    assert b"Accept-Encoding: identity\r\n" in request[0] and b"Authorization:" not in request[0]


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (_Response(status=302), "REDIRECT_REJECTED"),
        (_Response(status=500), "HTTP_STATUS_REJECTED"),
        (_Response(headers=[("Content-Type", "text/plain")]), "CONTENT_TYPE_REJECTED"),
        (_Response(headers=[("Content-Type", "application/json"), ("Content-Type", "application/json")]), "CONTENT_TYPE_REJECTED"),
        (_Response(headers=[("Content-Type", "application/json"), ("Content-Encoding", "gzip")]), "CONTENT_ENCODING_REJECTED"),
        (_Response(headers=[("Content-Type", "application/json"), ("Transfer-Encoding", "chunked")]), "TRANSFER_ENCODING_REJECTED"),
        (_Response(headers=[("Content-Type", "application/json")]), "CONTENT_LENGTH_REQUIRED"),
        (_Response(headers=[("Content-Type", "application/json"), ("Content-Length", "2"), ("Content-Length", "2")]), "CONTENT_LENGTH_REQUIRED"),
        (_Response(body=b"x", headers=[("Content-Type", "application/json"), ("Content-Length", "2")]), "RESPONSE_BOUNDS_EXCEEDED"),
        (_Response(headers=[("X", "y")] * 129), "RESPONSE_HEADERS_BOUNDS_EXCEEDED"),
    ],
)
def test_native_port_classifies_http_failures(monkeypatch: pytest.MonkeyPatch, response: _Response, reason: str) -> None:
    _native_port(monkeypatch, response)
    with pytest.raises(observer._Blocked) as caught:
        observer._StdlibHttpsPort().fetch()
    assert str(caught.value) == reason
    assert caught.value.facts.request_sent_count == 1


def test_native_port_read_and_tls_faults_retain_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    _native_port(monkeypatch, _Response(read_error=True))
    with pytest.raises(observer._Unknown) as read_fault:
        observer._StdlibHttpsPort().fetch()
    assert str(read_fault.value) == "RESPONSE_READ_FAILED"
    assert read_fault.value.facts.response_headers_observed is False
    assert read_fault.value.facts.response_body_complete is False
    assert read_fault.value.facts.request_send_state == "COMPLETE"

    _native_port(monkeypatch, _Response(), tls_error=True)
    with pytest.raises(observer._Unknown) as tls_fault:
        observer._StdlibHttpsPort().fetch()
    assert str(tls_fault.value) == "TLS_VERIFICATION_FAILED"
    assert tls_fault.value.facts.resolved_address_count == 1
    assert tls_fault.value.facts.request_sent_count == 0


def test_native_port_partial_send_is_truthful_and_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    _native_port(monkeypatch, _Response(), send_error=True)
    receipt = observer.observe_official_packaging_250_metadata("2026-08-21T02:00:00Z").to_dict()
    assert receipt["decision"] == "UNKNOWN" and receipt["reason_codes"] == ["REQUEST_SEND_FAILED"]
    assert receipt["request_send_state"] == "UNKNOWN_PARTIAL" and receipt["request_sent_count"] == 0
    _assert_contract(receipt)


@pytest.mark.parametrize(
    ("phase", "reason"),
    [
        ("dns", "DNS_LOOKUP_FAILED"),
        ("connect", "CONNECTION_FAILED"),
        ("tls", "TLS_VERIFICATION_FAILED"),
        ("send", "REQUEST_SEND_FAILED"),
        ("read", "RESPONSE_READ_FAILED"),
    ],
)
def test_unexpected_native_faults_become_contract_valid_unknown_receipts(
    monkeypatch: pytest.MonkeyPatch, phase: str, reason: str,
) -> None:
    _native_port(monkeypatch, _Response())
    if phase == "dns":
        monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("dns")))
    elif phase == "connect":
        monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("connect")))
    elif phase == "tls":
        monkeypatch.setattr(ssl, "create_default_context", lambda: (_ for _ in ()).throw(RuntimeError("tls")))
    elif phase == "send":
        monkeypatch.setattr(_TlsSocket, "sendall", lambda _self, _value: (_ for _ in ()).throw(RuntimeError("send")))
    else:
        monkeypatch.setattr(_TlsSocket, "recv", lambda _self, _amount: (_ for _ in ()).throw(RuntimeError("read")))

    receipt = observer.observe_official_packaging_250_metadata("2026-08-21T02:00:00Z").to_dict()
    assert receipt["decision"] == "UNKNOWN" and receipt["reason_codes"] == [reason]
    _assert_contract(receipt)


@pytest.mark.parametrize("field", ["request_send_state", "content_type"])
def test_unhashable_phase_values_are_rejected_as_value_error(
    monkeypatch: pytest.MonkeyPatch, field: str,
) -> None:
    receipt = _observe(monkeypatch, FakePort())
    receipt[field] = []
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = observer.sha256_bytes(
        b"TASK014_PACKAGING_PIN_OBSERVATION_V2\0" + observer.canonical_json_bytes(body)
    )
    with pytest.raises(ValueError):
        observer.parse_packaging_pin_observation(receipt)


@pytest.mark.parametrize("addresses", [["127.0.0.1", "8.8.8.8"], [f"8.8.8.{index}" for index in range(1, 34)]])
def test_native_port_rejects_mixed_or_excessive_dns(monkeypatch: pytest.MonkeyPatch, addresses: list[str]) -> None:
    _native_port(monkeypatch, _Response(), addresses=addresses)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("socket must not open"))
    with pytest.raises(observer._Blocked) as caught:
        observer._StdlibHttpsPort().fetch()
    assert str(caught.value) == "DNS_NON_GLOBAL_OR_AMBIGUOUS"


def test_public_observer_round_trips_dns_overflow_and_malformed_row(monkeypatch: pytest.MonkeyPatch) -> None:
    for answers, overflow in (
        ([(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (f"8.8.8.{index}", 443)) for index in range(1, 34)], True),
        ([None], False),
    ):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *args, _answers=answers, **kwargs: _answers)
        monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("socket must not open"))
        receipt = observer.observe_official_packaging_250_metadata("2026-08-21T02:00:00Z").to_dict()
        assert receipt["decision"] == "BLOCKED" and receipt["reason_codes"] == ["DNS_NON_GLOBAL_OR_AMBIGUOUS"]
        assert receipt["resolved_address_count_overflow"] is overflow
        if overflow:
            assert receipt["resolved_address_count"] == 32
        _assert_contract(receipt)


def test_native_port_rejects_peer_swap(monkeypatch: pytest.MonkeyPatch) -> None:
    _native_port(monkeypatch, _Response(), peer="8.8.4.4")
    with pytest.raises(observer._Blocked) as caught:
        observer._StdlibHttpsPort().fetch()
    assert str(caught.value) == "CONNECTED_PEER_NOT_IN_RESOLVED_SET"
    assert caught.value.facts.tls_certificate_verified is True
    assert caught.value.facts.connected_peer_in_resolved_set is False


def test_native_port_deadline_is_recomputed_before_each_recv(monkeypatch: pytest.MonkeyPatch) -> None:
    _native_port(monkeypatch, _Response())
    ticks = iter([0.0, 0.0, 0.0, 0.0, 0.0, 31.0])
    monkeypatch.setattr(observer.time, "monotonic", lambda: next(ticks))
    with pytest.raises(observer._Unknown) as caught:
        observer._StdlibHttpsPort().fetch()
    assert str(caught.value) == "RESPONSE_READ_FAILED"
    assert caught.value.facts.request_send_state == "COMPLETE"


def test_native_port_accepts_exact_128_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = [("Content-Type", "application/json"), ("Content-Length", "2"), *[(f"X-{index}", "v") for index in range(126)]]
    _native_port(monkeypatch, _Response(b"{}", headers=headers))
    assert observer._StdlibHttpsPort().fetch().body == b"{}"


@pytest.mark.parametrize("field", ["pin_acceptance_authorized", "artifact_download_authorized", "parser_import_authorized", "resolver_use_authorized", "install_authorized"])
def test_authority_tamper_is_rejected_by_parser_and_schema(monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    receipt = _observe(monkeypatch, FakePort()); receipt[field] = True
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = observer.sha256_bytes(b"TASK014_PACKAGING_PIN_OBSERVATION_V2\0" + observer.canonical_json_bytes(body))
    with pytest.raises(ValueError): observer.parse_packaging_pin_observation(receipt)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(receipt))


@pytest.mark.parametrize("timestamp", ["2026-08-21Z", "2026-08-21 02:00:00Z", "2026-08-21T02:00Z", "2026-13-21T02:00:00Z"])
def test_timestamp_is_strict(timestamp: str) -> None:
    with pytest.raises(ValueError): observer.observe_official_packaging_250_metadata(timestamp)


def test_schema_mirror_and_static_no_artifact_or_runtime_effect() -> None:
    assert SCHEMA.read_bytes() == MIRROR.read_bytes()
    source = (ROOT / "src/ai_video_production/packaging_parser_pin_observer.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".", 1)[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not imports.intersection({"subprocess", "requests", "pathlib", "importlib", "packaging", "torch", "soundfile"})
    for forbidden in ("pip install", "artifact.open", "model.load", "audio.read"):
        assert forbidden not in source
