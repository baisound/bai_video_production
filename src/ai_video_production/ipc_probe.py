from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import importlib.util
import json
import os
import platform
import secrets
import statistics
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing.connection import Client, Listener
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .ids import IdKind, generate_id
from .serialization import utc_now_iso


class IpcCandidate(str, Enum):
    LOCALHOST_HTTP_JSON = "LOCALHOST_HTTP_JSON"
    WINDOWS_NAMED_PIPE = "WINDOWS_NAMED_PIPE"
    GRPC = "GRPC"
    ZEROMQ = "ZEROMQ"


@dataclass(frozen=True, slots=True)
class IpcCandidateResult:
    candidate: IpcCandidate
    status: str
    target_platform_measured: bool
    auth_verified: bool | None = None
    restart_verified: bool | None = None
    round_trips: int = 0
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    dependency_present: bool | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.value,
            "status": self.status,
            "target_platform_measured": self.target_platform_measured,
            "auth_verified": self.auth_verified,
            "restart_verified": self.restart_verified,
            "round_trips": self.round_trips,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "dependency_present": self.dependency_present,
            "notes": list(self.notes),
        }


class _Handler(BaseHTTPRequestHandler):
    token = ""

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self.send_response(401)
            self.end_headers()
            return
        payload = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *args: object) -> None:
        return


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * q))))
    return ordered[idx]


def _run_http_roundtrip(round_trips: int = 8) -> tuple[bool, bool, list[float]]:
    token = secrets.token_urlsafe(24)
    handler = type("ProbeHandler", (_Handler,), {"token": token})

    def launch(port: int) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
        server = _ReusableThreadingHTTPServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, server.server_address[1]

    server, thread, port = launch(0)
    auth_verified = False
    latencies: list[float] = []
    try:
        try:
            urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
        except HTTPError as exc:
            auth_verified = exc.code == 401

        for _ in range(round_trips):
            req = Request(f"http://127.0.0.1:{port}/health", headers={"Authorization": f"Bearer {token}"})
            start = time.perf_counter()
            with urlopen(req, timeout=2) as response:
                payload = json.loads(response.read())
                if response.status != 200 or payload != {"ok": True}:
                    raise RuntimeError("unexpected localhost HTTP probe response")
            latencies.append((time.perf_counter() - start) * 1000)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)

    # Restart on the exact same loopback endpoint. This verifies recovery of the
    # configured endpoint rather than merely proving another random port works.
    server2, thread2, port2 = launch(port)
    try:
        req = Request(f"http://127.0.0.1:{port2}/health", headers={"Authorization": f"Bearer {token}"})
        with urlopen(req, timeout=2) as response:
            restart_verified = response.status == 200 and port2 == port
    finally:
        server2.shutdown(); server2.server_close(); thread2.join(timeout=2)
    return auth_verified, restart_verified, latencies


def _probe_http() -> IpcCandidateResult:
    try:
        auth, restart, latencies = _run_http_roundtrip()
    except Exception as exc:
        return IpcCandidateResult(
            IpcCandidate.LOCALHOST_HTTP_JSON,
            "FAILED",
            target_platform_measured=platform.system() == "Windows",
            notes=(f"{type(exc).__name__}: localhost probe failed",),
        )
    return IpcCandidateResult(
        IpcCandidate.LOCALHOST_HTTP_JSON,
        "MEASURED",
        target_platform_measured=platform.system() == "Windows",
        auth_verified=auth,
        restart_verified=restart,
        round_trips=len(latencies),
        latency_p50_ms=round(statistics.median(latencies), 3),
        latency_p95_ms=round(_percentile(latencies, 0.95), 3),
        dependency_present=True,
        notes=("Loopback-only stdlib HTTP/JSON probe; WSL2-to-Windows reachability is a separate live evidence requirement.",),
    )


def _probe_windows_named_pipe() -> IpcCandidateResult:
    if platform.system() != "Windows":
        return IpcCandidateResult(
            IpcCandidate.WINDOWS_NAMED_PIPE,
            "PROBE_REQUIRED",
            target_platform_measured=False,
            dependency_present=True,
            notes=("Windows-only transport; not inferred from non-Windows execution.",),
        )
    authkey = secrets.token_bytes(24)
    address = rf"\\.\pipe\bai-resolve-probe-{os.getpid()}-{secrets.token_hex(4)}"

    def roundtrip() -> tuple[bool, float]:
        ready = threading.Event()
        error: list[BaseException] = []

        def serve() -> None:
            try:
                with Listener(address=address, family="AF_PIPE", authkey=authkey) as listener:
                    ready.set()
                    conn = listener.accept()
                    with conn:
                        request = conn.recv()
                        conn.send({"ok": request == {"ping": True}})
            except BaseException as exc:  # pragma: no cover - Windows live path
                error.append(exc)
                ready.set()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        if not ready.wait(timeout=3):
            raise TimeoutError("named-pipe probe server did not become ready")
        if error:
            raise error[0]
        start = time.perf_counter()
        with Client(address=address, family="AF_PIPE", authkey=authkey) as conn:
            conn.send({"ping": True})
            response = conn.recv()
        elapsed = (time.perf_counter() - start) * 1000
        thread.join(timeout=3)
        if thread.is_alive():
            raise TimeoutError("named-pipe probe server did not stop")
        return response == {"ok": True}, elapsed

    try:
        first_ok, elapsed = roundtrip()
        second_ok, _ = roundtrip()  # same named-pipe endpoint after listener restart
    except Exception as exc:  # pragma: no cover - Windows live path
        return IpcCandidateResult(IpcCandidate.WINDOWS_NAMED_PIPE, "FAILED", True, notes=(type(exc).__name__,))

    ok = first_ok and second_ok
    return IpcCandidateResult(
        IpcCandidate.WINDOWS_NAMED_PIPE,
        "MEASURED" if ok else "FAILED",
        True,
        auth_verified=first_ok,
        restart_verified=second_ok,
        round_trips=2,
        latency_p50_ms=round(elapsed, 3),
        latency_p95_ms=round(elapsed, 3),
        dependency_present=True,
        notes=("Local Windows named-pipe endpoint and same-endpoint restart only; WSL2 interoperability must be separately demonstrated.",),
    )


def _optional_dependency(candidate: IpcCandidate, module_name: str) -> IpcCandidateResult:
    present = importlib.util.find_spec(module_name) is not None
    return IpcCandidateResult(
        candidate,
        "PROBE_REQUIRED",
        target_platform_measured=False,
        dependency_present=present,
        notes=(("Dependency is installed; live transport/recovery probe is still required." if present else "Optional dependency is not installed; no package was added solely for this comparison."),),
    )


def _build_ipc_report(results: list[IpcCandidateResult], *, supervision: dict[str, Any] | None = None) -> dict[str, Any]:
    core = [r for r in results if r.candidate in {IpcCandidate.LOCALHOST_HTTP_JSON, IpcCandidate.WINDOWS_NAMED_PIPE}]
    target_windows_complete = bool(core) and all(
        r.target_platform_measured and r.status == "MEASURED" for r in core
    )
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "probe_id": generate_id(IdKind.EVIDENCE),
        "created_at": utc_now_iso(),
        "host_platform": platform.system(),
        "results": [r.to_dict() for r in results],
        "adr": {
            "status": "PROVISIONAL",
            "selected": "LOCALHOST_HTTP_JSON",
            "reason": "Product Design Baseline reference path only; final promotion requires target Windows plus WSL2 reachability/recovery evidence.",
            "target_windows_core_candidates_measured": target_windows_complete,
            "wsl2_reachability_verified": False,
        },
    }
    if supervision is not None:
        report["supervision"] = supervision
    return report


def build_ipc_unavailable_report(*, reason: str, supervision: dict[str, Any] | None = None) -> dict[str, Any]:
    results = [
        IpcCandidateResult(candidate, "PROBE_REQUIRED", target_platform_measured=False, notes=(reason,))
        for candidate in IpcCandidate
    ]
    return _build_ipc_report(results, supervision=supervision)


def run_ipc_probe() -> dict[str, Any]:
    results = [
        _probe_http(),
        _probe_windows_named_pipe(),
        _optional_dependency(IpcCandidate.GRPC, "grpc"),
        _optional_dependency(IpcCandidate.ZEROMQ, "zmq"),
    ]
    return _build_ipc_report(results)
