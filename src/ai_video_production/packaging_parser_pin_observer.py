"""Bounded official-metadata observer for the proposed packaging 25.0 pin."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import ipaddress
import json
import re
import socket
import ssl
import time
from types import MappingProxyType
from typing import Mapping, Protocol

from .serialization import canonical_json_bytes, sha256_bytes
from . import packaging_parser_artifact as proposed


SCHEMA_VERSION = "bai.task014.packaging-parser-pin-observation.v2"
OBSERVER_ID = "bai.task014.packaging-parser-pin-observer"
OBSERVER_REVISION = 2
REQUEST_URL = "https://pypi.org/pypi/packaging/25.0/json"
_HOST = "pypi.org"
_PORT = 443
_PATH = "/pypi/packaging/25.0/json"
_MAX_RESPONSE_BYTES = 1024 * 1024
_MAX_HEADER_BYTES = 64 * 1024
_MAX_HEADERS = 128
_MAX_HEADER_LINE_BYTES = 8 * 1024
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?Z$")
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STATUS_RE = re.compile(rb"^HTTP/1\.[01] ([0-9]{3}) [\x20-\x7e]*\r\n$")
_HEADER_NAME_RE = re.compile(rb"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_CONSTRUCTION_TOKEN = object()
_BLOCKER_REASONS = frozenset({
    "DNS_NON_GLOBAL_OR_AMBIGUOUS", "CONNECTED_PEER_NOT_IN_RESOLVED_SET", "REDIRECT_REJECTED",
    "HTTP_STATUS_REJECTED", "CONTENT_TYPE_REJECTED", "CONTENT_ENCODING_REJECTED",
    "TRANSFER_ENCODING_REJECTED", "CONTENT_LENGTH_REQUIRED",
    "RESPONSE_BOUNDS_EXCEEDED", "RESPONSE_HEADERS_BOUNDS_EXCEEDED", "METADATA_JSON_MALFORMED",
    "RESPONSE_HEADERS_MALFORMED", "TRANSPORT_FACTS_MISMATCH",
    "INFO_MALFORMED", "DIGESTS_MALFORMED", "CORE_METADATA_MALFORMED",
    "PROJECT_IDENTITY_MISMATCH", "VULNERABILITY_STATE_NOT_EMPTY", "RELEASE_FILE_SET_MALFORMED",
    "PIN_CANDIDATE_COUNT_MISMATCH", "PIN_COORDINATE_MISMATCH", "PIN_DIGEST_MISMATCH",
    "METADATA_DIGEST_MISMATCH",
})
_UNKNOWN_REASONS = frozenset({
    "DNS_LOOKUP_FAILED", "CONNECTION_FAILED", "TLS_VERIFICATION_FAILED",
    "REQUEST_SEND_FAILED", "RESPONSE_READ_FAILED",
})
_RECEIPT_KEYS = {
    "schema_version", "observer_id", "observer_revision", "evaluated_at", "decision", "reason_codes",
    "request_url", "request_method", "request_scheduled_count", "request_sent_count",
    "request_send_state", "resolved_address_count_overflow",
    "response_headers_observed", "response_body_complete", "response_bytes", "response_sha256",
    "resolved_address_count", "all_resolved_addresses_global", "connected_peer_in_resolved_set",
    "tls_certificate_verified", "redirect_count", "content_type", "distribution_name",
    "distribution_version", "wheel_filename", "wheel_bytes", "wheel_sha256", "metadata_sha256",
    "source_url", "official_metadata_observation_complete", "pin_acceptance_authorized",
    "artifact_body_observed", "diagnostic_only", "persistent_receipt_is_capability",
    "artifact_download_authorized", "parser_import_authorized", "resolver_use_authorized",
    "install_authorized", "post_return_state_guaranteed", "consumer_revalidation_required",
    "metadata_network_accessed", "metadata_response_observed", "credentials_sent", "artifact_body_downloaded", "package_installed",
    "parser_imported", "target_runtime_executed", "model_loaded", "audio_read",
    "native_transport_origin_authenticated", "receipt_sha256",
}


@dataclass(frozen=True, slots=True)
class _PhaseFacts:
    resolved_address_count: int = 0
    resolved_address_count_overflow: bool = False
    all_resolved_addresses_global: bool = False
    connected_peer_in_resolved_set: bool = False
    tls_certificate_verified: bool = False
    request_sent_count: int = 0
    request_send_state: str = "NOT_ATTEMPTED"
    response_headers_observed: bool = False
    response_body_complete: bool = False
    content_type: str | None = None
    body: bytes | None = None


class _PortFault(Exception):
    def __init__(self, reason: str, facts: _PhaseFacts | None = None) -> None:
        super().__init__(reason)
        self.facts = facts or _PhaseFacts()


class _Blocked(_PortFault):
    pass


class _Unknown(_PortFault):
    pass


@dataclass(frozen=True, slots=True)
class _FetchResult:
    body: bytes
    resolved_address_count: int
    connected_peer_in_resolved_set: bool
    tls_certificate_verified: bool
    redirect_count: int
    content_type: str

    def phase_facts(self) -> _PhaseFacts:
        return _PhaseFacts(
            resolved_address_count=self.resolved_address_count,
            resolved_address_count_overflow=False,
            all_resolved_addresses_global=True,
            connected_peer_in_resolved_set=self.connected_peer_in_resolved_set,
            tls_certificate_verified=self.tls_certificate_verified,
            request_sent_count=1,
            request_send_state="COMPLETE",
            response_headers_observed=True,
            response_body_complete=True,
            content_type=self.content_type,
            body=self.body,
        )


class _Port(Protocol):
    def fetch(self) -> _FetchResult: ...


def _global_address(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def _remaining(deadline: float, facts: _PhaseFacts, reason: str) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _Unknown(reason, facts)
    return remaining


class _StdlibHttpsPort:
    def fetch(self) -> _FetchResult:
        facts = _PhaseFacts()
        try:
            answers = socket.getaddrinfo(_HOST, _PORT, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        except Exception as exc:
            raise _Unknown("DNS_LOOKUP_FAILED", facts) from exc
        if not isinstance(answers, list):
            raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts)
        unique: dict[tuple[int, str], tuple[object, ...]] = {}
        for answer in answers:
            try:
                family, socktype, proto, _canonname, sockaddr = answer
            except (TypeError, ValueError):
                raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts) from None
            if family not in {socket.AF_INET, socket.AF_INET6} or socktype != socket.SOCK_STREAM or proto not in {0, socket.IPPROTO_TCP}:
                raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts)
            try:
                ip = ipaddress.ip_address(str(sockaddr[0])).compressed
            except (ValueError, IndexError, TypeError):
                raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts) from None
            unique[(family, ip)] = sockaddr
            if len(unique) > 32:
                facts = replace(facts, resolved_address_count=32, resolved_address_count_overflow=True)
                raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts)
        facts = replace(facts, resolved_address_count=len(unique))
        if any(not _global_address(ip) for _family, ip in unique):
            raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts)
        if not unique:
            raise _Blocked("DNS_NON_GLOBAL_OR_AMBIGUOUS", facts)
        facts = replace(facts, all_resolved_addresses_global=True)
        deadline = time.monotonic() + 30.0

        raw_socket: socket.socket | None = None
        last_error: Exception | None = None
        for (family, _ip), sockaddr in sorted(unique.items(), key=lambda item: (item[0][0], item[0][1]))[:4]:
            candidate: socket.socket | None = None
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                candidate = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
                candidate.settimeout(min(5.0, remaining))
                candidate.connect(sockaddr)
                raw_socket = candidate
                break
            except Exception as exc:
                last_error = exc
                try:
                    if candidate is not None:
                        candidate.close()
                except Exception:
                    pass
        if raw_socket is None:
            raise _Unknown("CONNECTION_FAILED", facts) from last_error

        tls_socket: ssl.SSLSocket | None = None
        try:
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise OSError("network observation deadline exceeded")
                raw_socket.settimeout(remaining)
                tls_socket = ssl.create_default_context().wrap_socket(raw_socket, server_hostname=_HOST)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise OSError("network observation deadline exceeded")
                tls_socket.settimeout(remaining)
            except Exception as exc:
                raise _Unknown("TLS_VERIFICATION_FAILED", facts) from exc
            facts = replace(facts, tls_certificate_verified=True)
            try:
                peer = ipaddress.ip_address(str(tls_socket.getpeername()[0])).compressed
                peer_family = tls_socket.family
            except Exception:
                raise _Blocked("CONNECTED_PEER_NOT_IN_RESOLVED_SET", facts) from None
            if (peer_family, peer) not in unique:
                raise _Blocked("CONNECTED_PEER_NOT_IN_RESOLVED_SET", facts)
            facts = replace(facts, connected_peer_in_resolved_set=True)
            request = (
                f"GET {_PATH} HTTP/1.1\r\nHost: {_HOST}\r\n"
                "User-Agent: BAI-VIDEO-PRODUCTION-TASK014-METADATA-OBSERVER/1\r\n"
                "Accept: application/json\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n"
            ).encode("ascii")
            try:
                facts = replace(facts, request_send_state="UNKNOWN_PARTIAL")
                tls_socket.settimeout(_remaining(deadline, facts, "REQUEST_SEND_FAILED"))
                tls_socket.sendall(request)
            except Exception as exc:
                raise _Unknown("REQUEST_SEND_FAILED", facts) from exc
            facts = replace(facts, request_sent_count=1, request_send_state="COMPLETE")
            header_buffer = bytearray()
            body_prefix = b""
            while True:
                tls_socket.settimeout(_remaining(deadline, facts, "RESPONSE_READ_FAILED"))
                chunk = tls_socket.recv(4096)
                if not chunk:
                    raise _Blocked("RESPONSE_HEADERS_MALFORMED", facts)
                header_buffer.extend(chunk)
                marker = header_buffer.find(b"\r\n\r\n")
                if marker >= 0:
                    header_end = marker + 4
                    if header_end > _MAX_HEADER_BYTES:
                        raise _Blocked("RESPONSE_HEADERS_BOUNDS_EXCEEDED", facts)
                    body_prefix = bytes(header_buffer[header_end:])
                    header_block = bytes(header_buffer[:marker])
                    break
                if len(header_buffer) > _MAX_HEADER_BYTES:
                    raise _Blocked("RESPONSE_HEADERS_BOUNDS_EXCEEDED", facts)
            lines = header_block.split(b"\r\n")
            status_line, header_lines = lines[0] + b"\r\n", lines[1:]
            if len(status_line) > _MAX_HEADER_LINE_BYTES or len(header_lines) > _MAX_HEADERS:
                raise _Blocked("RESPONSE_HEADERS_BOUNDS_EXCEEDED", facts)
            status_match = _STATUS_RE.fullmatch(status_line)
            if status_match is None:
                raise _Blocked("RESPONSE_HEADERS_MALFORMED", facts)
            status = int(status_match.group(1))
            header_items: list[tuple[str, str]] = []
            for line in header_lines:
                if len(line) + 2 > _MAX_HEADER_LINE_BYTES or b":" not in line or line[:1] in {b" ", b"\t"}:
                    raise _Blocked("RESPONSE_HEADERS_MALFORMED", facts)
                name_raw, value_raw = line.split(b":", 1)
                if _HEADER_NAME_RE.fullmatch(name_raw) is None or any((byte < 32 and byte != 9) or byte == 127 for byte in value_raw):
                    raise _Blocked("RESPONSE_HEADERS_MALFORMED", facts)
                header_items.append((name_raw.decode("ascii"), value_raw.decode("latin-1").strip()))
            facts = replace(facts, response_headers_observed=True)
            if 300 <= status <= 399:
                raise _Blocked("REDIRECT_REJECTED", facts)
            if status != 200:
                raise _Blocked("HTTP_STATUS_REJECTED", facts)
            content_types = [value for name, value in header_items if name.lower() == "content-type"]
            if len(content_types) != 1 or content_types[0].split(";", 1)[0].strip().lower() != "application/json":
                raise _Blocked("CONTENT_TYPE_REJECTED", facts)
            facts = replace(facts, content_type="application/json")
            encodings = [value for name, value in header_items if name.lower() == "content-encoding"]
            if len(encodings) > 1 or (encodings and encodings[0].lower() != "identity"):
                raise _Blocked("CONTENT_ENCODING_REJECTED", facts)
            transfer_encodings = [value for name, value in header_items if name.lower() == "transfer-encoding"]
            if transfer_encodings:
                raise _Blocked("TRANSFER_ENCODING_REJECTED", facts)
            lengths = [value for name, value in header_items if name.lower() == "content-length"]
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal():
                raise _Blocked("CONTENT_LENGTH_REQUIRED", facts)
            content_length = int(lengths[0])
            if content_length > _MAX_RESPONSE_BYTES or len(body_prefix) > content_length:
                raise _Blocked("RESPONSE_BOUNDS_EXCEEDED", facts)
            body_buffer = bytearray(body_prefix)
            while len(body_buffer) < content_length:
                tls_socket.settimeout(_remaining(deadline, facts, "RESPONSE_READ_FAILED"))
                chunk = tls_socket.recv(min(64 * 1024, content_length - len(body_buffer)))
                if not chunk:
                    raise _Blocked("RESPONSE_BOUNDS_EXCEEDED", facts)
                body_buffer.extend(chunk)
            body = bytes(body_buffer)
            facts = replace(facts, response_body_complete=True, body=body)
            return _FetchResult(body, len(unique), True, True, 0, "application/json")
        except (_Blocked, _Unknown):
            raise
        except Exception as exc:
            raise _Unknown("RESPONSE_READ_FAILED", facts) from exc
        finally:
            try:
                if tls_socket is not None:
                    tls_socket.close()
                else:
                    raw_socket.close()
            except Exception:
                pass


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant: {value}")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _Blocked(f"{field}_MALFORMED")
    return value


def _parse_candidate(raw: bytes) -> None:
    try:
        document = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise _Blocked("METADATA_JSON_MALFORMED") from exc
    root = _mapping(document, "METADATA_JSON")
    info = _mapping(root.get("info"), "INFO")
    if info.get("name") != proposed.PACKAGING_NAME or info.get("version") != proposed.PACKAGING_VERSION or info.get("requires_python") != ">=3.8":
        raise _Blocked("PROJECT_IDENTITY_MISMATCH")
    if root.get("vulnerabilities") != []:
        raise _Blocked("VULNERABILITY_STATE_NOT_EMPTY")
    urls = root.get("urls")
    if not isinstance(urls, list) or len(urls) > 16:
        raise _Blocked("RELEASE_FILE_SET_MALFORMED")
    matches = [item for item in urls if isinstance(item, Mapping) and item.get("filename") == proposed.WHEEL_FILENAME]
    if len(matches) != 1:
        raise _Blocked("PIN_CANDIDATE_COUNT_MISMATCH")
    item = matches[0]
    digests = _mapping(item.get("digests"), "DIGESTS")
    core_metadata = item.get("core-metadata")
    dist_info_metadata = item.get("dist_info_metadata")
    if core_metadata is not None and dist_info_metadata is not None and core_metadata != dist_info_metadata:
        raise _Blocked("CORE_METADATA_MALFORMED")
    metadata = core_metadata if core_metadata is not None else dist_info_metadata
    metadata_map = _mapping(metadata, "CORE_METADATA")
    expected = {
        "packagetype": "bdist_wheel",
        "python_version": "py3",
        "size": proposed.WHEEL_BYTES,
        "url": proposed.SOURCE_URL,
        "requires_python": ">=3.8",
        "yanked": False,
    }
    if any(item.get(key) != value for key, value in expected.items()):
        raise _Blocked("PIN_COORDINATE_MISMATCH")
    if digests.get("sha256") != proposed.WHEEL_SHA256.removeprefix("sha256:"):
        raise _Blocked("PIN_DIGEST_MISMATCH")
    if metadata_map.get("sha256") != proposed.METADATA_SHA256.removeprefix("sha256:"):
        raise _Blocked("METADATA_DIGEST_MISMATCH")


@dataclass(frozen=True, slots=True, init=False)
class PackagingPinObservation:
    _body: Mapping[str, object]
    _seal: object

    def __init__(self, body: Mapping[str, object], token: object) -> None:
        if token is not _CONSTRUCTION_TOKEN:
            raise TypeError("private observer construction token required")
        object.__setattr__(self, "_body", MappingProxyType(dict(body)))
        object.__setattr__(self, "_seal", token)

    def to_dict(self) -> dict[str, object]:
        if self._seal is not _CONSTRUCTION_TOKEN:
            raise RuntimeError("unsealed observation")
        return {key: list(value) if isinstance(value, tuple) else value for key, value in self._body.items()}


def _timestamp(value: str) -> str:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError("evaluated_at must be canonical RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("evaluated_at must be canonical RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("evaluated_at must be canonical RFC3339 UTC")
    return value


def _validate_phase_facts(facts: _PhaseFacts, *, validate_body_length: bool = True) -> None:
    integers = (facts.resolved_address_count, facts.request_sent_count)
    booleans = (
        facts.resolved_address_count_overflow, facts.all_resolved_addresses_global, facts.connected_peer_in_resolved_set,
        facts.tls_certificate_verified, facts.response_headers_observed, facts.response_body_complete,
    )
    invalid = (
        any(type(value) is not int for value in integers)
        or not 0 <= facts.resolved_address_count <= 32
        or facts.request_sent_count not in {0, 1}
        or any(type(value) is not bool for value in booleans)
        or not isinstance(facts.request_send_state, str)
        or facts.request_send_state not in {"NOT_ATTEMPTED", "UNKNOWN_PARTIAL", "COMPLETE"}
        or (facts.content_type is not None and not isinstance(facts.content_type, str))
        or facts.content_type not in {None, "application/json"}
        or (facts.resolved_address_count == 0 and facts.all_resolved_addresses_global)
        or (facts.resolved_address_count_overflow and not (
            facts.resolved_address_count == 32 and not facts.all_resolved_addresses_global
        ))
        or (facts.request_send_state == "NOT_ATTEMPTED" and facts.request_sent_count != 0)
        or (facts.request_send_state == "UNKNOWN_PARTIAL" and not (
            facts.request_sent_count == 0 and facts.connected_peer_in_resolved_set
        ))
        or (facts.request_send_state == "COMPLETE" and facts.request_sent_count != 1)
        or (facts.tls_certificate_verified and not (facts.all_resolved_addresses_global and facts.resolved_address_count > 0))
        or (facts.connected_peer_in_resolved_set and not facts.tls_certificate_verified)
        or (facts.request_sent_count == 1 and not facts.connected_peer_in_resolved_set)
        or (facts.response_headers_observed and facts.request_sent_count != 1)
        or (facts.content_type is not None and not facts.response_headers_observed)
        or (facts.response_body_complete and not facts.response_headers_observed)
        or (facts.response_body_complete and facts.content_type != "application/json")
        or (facts.response_body_complete and not isinstance(facts.body, bytes))
        or (not facts.response_body_complete and facts.body is not None)
        or (
            validate_body_length and isinstance(facts.body, bytes)
            and len(facts.body) > _MAX_RESPONSE_BYTES
        )
    )
    if invalid:
        raise _Blocked("TRANSPORT_FACTS_MISMATCH", facts)


def _body(
    *, evaluated_at: str, decision: str, reasons: tuple[str, ...],
    fetch: _FetchResult | None = None, facts: _PhaseFacts | None = None,
) -> dict[str, object]:
    success = decision == "OFFICIAL_PACKAGING_PIN_OBSERVED_DIAGNOSTIC"
    phase = fetch.phase_facts() if fetch is not None else (facts or _PhaseFacts())
    response_observed = phase.response_body_complete and phase.body is not None
    body: dict[str, object] = {
        "schema_version": SCHEMA_VERSION, "observer_id": OBSERVER_ID, "observer_revision": OBSERVER_REVISION,
        "evaluated_at": _timestamp(evaluated_at), "decision": decision, "reason_codes": reasons,
        "request_url": REQUEST_URL, "request_method": "GET", "request_scheduled_count": 1,
        "response_bytes": len(phase.body) if response_observed else 0,
        "response_sha256": sha256_bytes(phase.body) if response_observed else None,
        "resolved_address_count": phase.resolved_address_count,
        "resolved_address_count_overflow": phase.resolved_address_count_overflow,
        "all_resolved_addresses_global": phase.all_resolved_addresses_global,
        "connected_peer_in_resolved_set": phase.connected_peer_in_resolved_set,
        "tls_certificate_verified": phase.tls_certificate_verified,
        "request_sent_count": phase.request_sent_count,
        "request_send_state": phase.request_send_state,
        "response_headers_observed": phase.response_headers_observed,
        "response_body_complete": phase.response_body_complete,
        "redirect_count": 0,
        "content_type": phase.content_type,
        "distribution_name": proposed.PACKAGING_NAME, "distribution_version": proposed.PACKAGING_VERSION,
        "wheel_filename": proposed.WHEEL_FILENAME, "wheel_bytes": proposed.WHEEL_BYTES,
        "wheel_sha256": proposed.WHEEL_SHA256, "metadata_sha256": proposed.METADATA_SHA256,
        "source_url": proposed.SOURCE_URL, "official_metadata_observation_complete": success,
        "pin_acceptance_authorized": False, "artifact_body_observed": False,
        "diagnostic_only": True, "persistent_receipt_is_capability": False,
        "artifact_download_authorized": False, "parser_import_authorized": False,
        "resolver_use_authorized": False, "install_authorized": False,
        "post_return_state_guaranteed": False, "consumer_revalidation_required": True,
        "metadata_network_accessed": True, "metadata_response_observed": response_observed, "credentials_sent": False,
        "artifact_body_downloaded": False, "package_installed": False, "parser_imported": False,
        "target_runtime_executed": False, "model_loaded": False, "audio_read": False,
        "native_transport_origin_authenticated": False,
    }
    body["receipt_sha256"] = sha256_bytes(b"TASK014_PACKAGING_PIN_OBSERVATION_V2\0" + canonical_json_bytes(body))
    return body


def observe_official_packaging_250_metadata(evaluated_at: str) -> PackagingPinObservation:
    """Perform exactly one bounded official metadata request."""
    _timestamp(evaluated_at)
    fetch: _FetchResult | None = None
    try:
        fetch = _StdlibHttpsPort().fetch()
        try:
            _validate_phase_facts(fetch.phase_facts())
            if fetch.redirect_count != 0:
                raise _Blocked("TRANSPORT_FACTS_MISMATCH")
        except _Blocked as exc:
            fetch = None
            raise _Blocked("TRANSPORT_FACTS_MISMATCH", _PhaseFacts()) from exc
        _parse_candidate(fetch.body)
        body = _body(evaluated_at=evaluated_at, decision="OFFICIAL_PACKAGING_PIN_OBSERVED_DIAGNOSTIC", reasons=(), fetch=fetch)
    except _Blocked as exc:
        body = _body(evaluated_at=evaluated_at, decision="BLOCKED", reasons=(str(exc),), fetch=fetch, facts=exc.facts)
    except _Unknown as exc:
        body = _body(evaluated_at=evaluated_at, decision="UNKNOWN", reasons=(str(exc),), facts=exc.facts)
    return PackagingPinObservation(body, _CONSTRUCTION_TOKEN)


def parse_packaging_pin_observation(value: Mapping[str, object]) -> dict[str, object]:
    """Strictly parse a diagnostic observation without upgrading authority."""
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
        raise ValueError("invalid packaging pin observation")
    body = dict(value)
    digest = body.pop("receipt_sha256", None)
    if digest != sha256_bytes(b"TASK014_PACKAGING_PIN_OBSERVATION_V2\0" + canonical_json_bytes(body)):
        raise ValueError("invalid packaging pin observation")
    consts = {
        "schema_version": SCHEMA_VERSION, "observer_id": OBSERVER_ID, "observer_revision": OBSERVER_REVISION,
        "request_url": REQUEST_URL, "request_method": "GET", "request_scheduled_count": 1, "redirect_count": 0,
        "distribution_name": proposed.PACKAGING_NAME, "distribution_version": proposed.PACKAGING_VERSION,
        "wheel_filename": proposed.WHEEL_FILENAME, "wheel_bytes": proposed.WHEEL_BYTES,
        "wheel_sha256": proposed.WHEEL_SHA256, "metadata_sha256": proposed.METADATA_SHA256,
        "source_url": proposed.SOURCE_URL, "pin_acceptance_authorized": False,
        "artifact_body_observed": False, "diagnostic_only": True,
        "persistent_receipt_is_capability": False, "artifact_download_authorized": False,
        "parser_import_authorized": False, "resolver_use_authorized": False, "install_authorized": False,
        "post_return_state_guaranteed": False, "consumer_revalidation_required": True,
        "metadata_network_accessed": True, "native_transport_origin_authenticated": False,
        "credentials_sent": False, "artifact_body_downloaded": False, "package_installed": False,
        "parser_imported": False, "target_runtime_executed": False, "model_loaded": False, "audio_read": False,
    }
    if any(body.get(key) != expected for key, expected in consts.items()):
        raise ValueError("invalid packaging pin observation")
    _timestamp(body.get("evaluated_at"))  # type: ignore[arg-type]
    decision = body.get("decision")
    reasons = body.get("reason_codes")
    if not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason or len(reason) > 64 for reason in reasons):
        raise ValueError("invalid packaging pin observation")
    try:
        phase = _PhaseFacts(
            resolved_address_count=body["resolved_address_count"],  # type: ignore[arg-type]
            resolved_address_count_overflow=body["resolved_address_count_overflow"],  # type: ignore[arg-type]
            all_resolved_addresses_global=body["all_resolved_addresses_global"],  # type: ignore[arg-type]
            connected_peer_in_resolved_set=body["connected_peer_in_resolved_set"],  # type: ignore[arg-type]
            tls_certificate_verified=body["tls_certificate_verified"],  # type: ignore[arg-type]
            request_sent_count=body["request_sent_count"],  # type: ignore[arg-type]
            request_send_state=body["request_send_state"],  # type: ignore[arg-type]
            response_headers_observed=body["response_headers_observed"],  # type: ignore[arg-type]
            response_body_complete=body["response_body_complete"],  # type: ignore[arg-type]
            content_type=body["content_type"],  # type: ignore[arg-type]
            body=b"" if body["response_body_complete"] is True else None,
        )
        _validate_phase_facts(phase, validate_body_length=False)
    except (KeyError, TypeError, _Blocked):
        raise ValueError("invalid packaging pin observation") from None
    response_complete = body.get("response_body_complete") is True
    if body.get("metadata_response_observed") is not response_complete:
        raise ValueError("invalid packaging pin observation")
    if response_complete:
        if type(body.get("response_bytes")) is not int or not 0 <= body["response_bytes"] <= _MAX_RESPONSE_BYTES:  # type: ignore[operator]
            raise ValueError("invalid packaging pin observation")
        if not isinstance(body.get("response_sha256"), str) or not _SHA_RE.fullmatch(body["response_sha256"]):  # type: ignore[arg-type]
            raise ValueError("invalid packaging pin observation")
    elif body.get("response_bytes") != 0 or body.get("response_sha256") is not None:
        raise ValueError("invalid packaging pin observation")
    if decision == "OFFICIAL_PACKAGING_PIN_OBSERVED_DIAGNOSTIC":
        expected = {
            "official_metadata_observation_complete": True, "metadata_network_accessed": True,
            "metadata_response_observed": True,
            "all_resolved_addresses_global": True, "connected_peer_in_resolved_set": True,
            "tls_certificate_verified": True, "request_sent_count": 1,
            "resolved_address_count_overflow": False, "request_send_state": "COMPLETE",
            "response_headers_observed": True, "response_body_complete": True,
            "content_type": "application/json",
        }
        if reasons or any(body.get(key) != item for key, item in expected.items()):
            raise ValueError("invalid packaging pin observation")
        if type(body.get("response_bytes")) is not int or not 1 <= body["response_bytes"] <= _MAX_RESPONSE_BYTES:  # type: ignore[operator]
            raise ValueError("invalid packaging pin observation")
        if type(body.get("resolved_address_count")) is not int or not 1 <= body["resolved_address_count"] <= 32:  # type: ignore[operator]
            raise ValueError("invalid packaging pin observation")
        if not isinstance(body.get("response_sha256"), str) or not _SHA_RE.fullmatch(body["response_sha256"]):  # type: ignore[arg-type]
            raise ValueError("invalid packaging pin observation")
    elif decision in {"BLOCKED", "UNKNOWN"}:
        if len(reasons) != 1 or body.get("official_metadata_observation_complete") is not False:
            raise ValueError("invalid packaging pin observation")
        allowed = _BLOCKER_REASONS if decision == "BLOCKED" else _UNKNOWN_REASONS
        if reasons[0] not in allowed:
            raise ValueError("invalid packaging pin observation")
        reason = reasons[0]
        zero_phase = (
            body.get("resolved_address_count") == 0
            and body.get("resolved_address_count_overflow") is False
            and body.get("all_resolved_addresses_global") is False
            and body.get("tls_certificate_verified") is False
            and body.get("connected_peer_in_resolved_set") is False
            and body.get("request_sent_count") == 0
            and body.get("response_headers_observed") is False
            and body.get("response_body_complete") is False
        )
        if reason in {"DNS_LOOKUP_FAILED", "TRANSPORT_FACTS_MISMATCH"} and not zero_phase:
            raise ValueError("invalid packaging pin observation")
        if reason in {"CONNECTION_FAILED", "TLS_VERIFICATION_FAILED"} and not (
            body.get("resolved_address_count", 0) >= 1
            and body.get("all_resolved_addresses_global") is True
            and body.get("tls_certificate_verified") is False
            and body.get("request_sent_count") == 0
        ):
            raise ValueError("invalid packaging pin observation")
        if reason == "CONNECTED_PEER_NOT_IN_RESOLVED_SET" and not (
            body.get("resolved_address_count", 0) >= 1
            and body.get("all_resolved_addresses_global") is True
            and body.get("tls_certificate_verified") is True
            and body.get("connected_peer_in_resolved_set") is False
            and body.get("request_sent_count") == 0
        ):
            raise ValueError("invalid packaging pin observation")
        if reason == "DNS_NON_GLOBAL_OR_AMBIGUOUS" and not (
            body.get("all_resolved_addresses_global") is False
            and body.get("tls_certificate_verified") is False
            and body.get("connected_peer_in_resolved_set") is False
            and body.get("request_send_state") == "NOT_ATTEMPTED"
            and body.get("request_sent_count") == 0
            and body.get("response_headers_observed") is False
            and body.get("response_body_complete") is False
        ):
            raise ValueError("invalid packaging pin observation")
        if reason == "REQUEST_SEND_FAILED" and not (
            body.get("resolved_address_count", 0) >= 1
            and body.get("all_resolved_addresses_global") is True
            and body.get("tls_certificate_verified") is True
            and body.get("connected_peer_in_resolved_set") is True
            and body.get("request_send_state") == "UNKNOWN_PARTIAL"
            and body.get("request_sent_count") == 0
            and body.get("response_headers_observed") is False
        ):
            raise ValueError("invalid packaging pin observation")
        if reason == "RESPONSE_READ_FAILED" and not (
            body.get("resolved_address_count", 0) >= 1
            and body.get("all_resolved_addresses_global") is True
            and body.get("tls_certificate_verified") is True
            and body.get("connected_peer_in_resolved_set") is True
            and body.get("request_send_state") == "COMPLETE"
            and body.get("request_sent_count") == 1
            and body.get("response_body_complete") is False
        ):
            raise ValueError("invalid packaging pin observation")
        if reason in {"RESPONSE_HEADERS_BOUNDS_EXCEEDED", "RESPONSE_HEADERS_MALFORMED"} and not (
            body.get("request_sent_count") == 1
            and body.get("response_headers_observed") is False
            and body.get("response_body_complete") is False
        ):
            raise ValueError("invalid packaging pin observation")
        if reason in {
            "REDIRECT_REJECTED", "HTTP_STATUS_REJECTED", "CONTENT_TYPE_REJECTED",
            "CONTENT_ENCODING_REJECTED", "TRANSFER_ENCODING_REJECTED",
            "CONTENT_LENGTH_REQUIRED", "RESPONSE_BOUNDS_EXCEEDED",
        } and not (
            body.get("request_sent_count") == 1
            and body.get("response_headers_observed") is True
            and body.get("response_body_complete") is False
        ):
            raise ValueError("invalid packaging pin observation")
        semantic_reasons = _BLOCKER_REASONS - {
            "DNS_NON_GLOBAL_OR_AMBIGUOUS", "CONNECTED_PEER_NOT_IN_RESOLVED_SET",
            "REDIRECT_REJECTED", "HTTP_STATUS_REJECTED", "CONTENT_TYPE_REJECTED",
            "CONTENT_ENCODING_REJECTED", "TRANSFER_ENCODING_REJECTED",
            "CONTENT_LENGTH_REQUIRED", "RESPONSE_BOUNDS_EXCEEDED",
            "RESPONSE_HEADERS_BOUNDS_EXCEEDED", "RESPONSE_HEADERS_MALFORMED",
            "TRANSPORT_FACTS_MISMATCH",
        }
        if reason in semantic_reasons and body.get("response_body_complete") is not True:
            raise ValueError("invalid packaging pin observation")
    else:
        raise ValueError("invalid packaging pin observation")
    body["receipt_sha256"] = digest
    return body
