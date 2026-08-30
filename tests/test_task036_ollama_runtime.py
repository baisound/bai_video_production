from __future__ import annotations

from pathlib import Path

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.task036_ollama_runtime import OllamaRuntimeLifecycle


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def request(self, method, url, body, timeout_seconds):
        assert (method, url, body, timeout_seconds) == ("GET", "http://127.0.0.1:11434/api/tags", None, 5.0)
        self.calls += 1
        current = self.responses.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


class Process:
    def __init__(self, states=(None,)):
        self.states = list(states)

    def poll(self):
        return self.states[0] if len(self.states) == 1 else self.states.pop(0)


def unavailable():
    return ProductError("ERR_LOCAL_OLLAMA_UNREACHABLE", "unreachable", ProductErrorCategory.EXTERNAL_DEPENDENCY)


def test_ready_runtime_is_reused_without_starting_or_exposing_host_details():
    started = []
    runtime = OllamaRuntimeLifecycle(
        transport=Transport([b'{"models":[{"name":"qwen3:8b"}]}']),
        executable_resolver=lambda: Path("C:/private/ollama.exe"),
        popen_factory=lambda *args, **kwargs: started.append((args, kwargs)),
    )
    snapshot = runtime.ensure_started()
    assert snapshot.state == "READY"
    assert snapshot.model_ids == ("qwen3:8b",)
    assert snapshot.started_by_product is False
    assert started == []
    assert "private" not in str(snapshot.as_dict())


def test_stopped_runtime_starts_once_then_reads_current_inventory():
    clock = [0.0]
    started = []
    process = Process()

    def sleeper(seconds):
        clock[0] += seconds

    runtime = OllamaRuntimeLifecycle(
        transport=Transport([unavailable(), b'{"models":[{"name":"qwen3:8b"}]}', b'{"models":[{"name":"qwen3:8b"}]}']),
        executable_resolver=lambda: Path("C:/verified/ollama.exe"),
        popen_factory=lambda *args, **kwargs: started.append((args, kwargs)) or process,
        clock=lambda: clock[0],
        sleeper=sleeper,
    )
    snapshot = runtime.ensure_started()
    assert snapshot.state == "READY"
    assert snapshot.started_by_product is True
    assert len(started) == 1
    assert started[0][0][0][1] == "serve"
    assert started[0][1]["shell"] is False
    assert runtime.ensure_started().state == "READY"
    assert len(started) == 1


def test_uninstalled_runtime_is_actionable_and_never_starts():
    started = []
    runtime = OllamaRuntimeLifecycle(
        transport=Transport([unavailable()]),
        executable_resolver=lambda: None,
        popen_factory=lambda *args, **kwargs: started.append((args, kwargs)),
    )
    snapshot = runtime.ensure_started()
    assert snapshot.state == "NOT_INSTALLED"
    assert snapshot.reason_code == "OLLAMA_EXECUTABLE_NOT_FOUND"
    assert snapshot.model_ids == ()
    assert started == []


def test_model_zero_is_distinct_from_runtime_failure():
    runtime = OllamaRuntimeLifecycle(
        transport=Transport([b'{"models":[]}']),
        executable_resolver=lambda: None,
    )
    snapshot = runtime.ensure_started()
    assert snapshot.state == "NO_MODEL"
    assert snapshot.reason_code == "OLLAMA_MODEL_NOT_INSTALLED"
    assert "Model" in snapshot.message_ja


def test_start_exit_is_not_reported_as_ready():
    clock = [0.0]
    runtime = OllamaRuntimeLifecycle(
        transport=Transport([unavailable(), unavailable()]),
        executable_resolver=lambda: Path("C:/verified/ollama.exe"),
        popen_factory=lambda *args, **kwargs: Process((1,)),
        clock=lambda: clock[0],
        sleeper=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    snapshot = runtime.ensure_started()
    assert snapshot.state == "FAILED"
    assert snapshot.reason_code == "OLLAMA_START_EXITED"
