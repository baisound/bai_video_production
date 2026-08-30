"""Bounded, local-only Ollama runtime lifecycle for TASK-036 consumers.

The launcher may reuse an already-ready loopback service or start a verified,
installed executable once.  It never downloads models, uses cloud endpoints, or
terminates a process on close.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import threading
from time import monotonic, sleep
from typing import Callable

from .ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily
from .errors import ProductError, ProductErrorCategory
from .local_ollama_planning import LocalOllamaTransport, UrllibLocalOllamaTransport


_TAGS_URL = "http://127.0.0.1:11434/api/tags"
_MAX_MODELS = 64
_START_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True, slots=True)
class OllamaRuntimeSnapshot:
    """Public-safe runtime state; executable paths and process IDs never escape."""

    state: str
    model_ids: tuple[str, ...]
    started_by_product: bool
    reason_code: str | None
    message_ja: str

    def __post_init__(self) -> None:
        if self.state not in {"READY", "NO_MODEL", "STARTING", "NOT_INSTALLED", "FAILED"}:
            raise ValueError("state is invalid")
        if not isinstance(self.model_ids, tuple) or len(self.model_ids) > _MAX_MODELS:
            raise ValueError("model_ids are invalid")
        if any(not isinstance(value, str) for value in self.model_ids):
            raise ValueError("model_ids are invalid")
        if self.state == "READY" and not self.model_ids:
            raise ValueError("READY requires models")
        if self.state == "NO_MODEL" and self.model_ids:
            raise ValueError("NO_MODEL cannot include models")

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "model_ids": list(self.model_ids),
            "started_by_product": self.started_by_product,
            "reason_code": self.reason_code,
            "message_ja": self.message_ja,
            "endpoint": "loopback-only",
        }


def _models_from_tags(transport: LocalOllamaTransport) -> tuple[str, ...]:
    raw = transport.request("GET", _TAGS_URL, None, 5.0)
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductError(
            "ERR_LOCAL_OLLAMA_RESPONSE_INVALID",
            "Local Ollama inventory is not valid JSON",
            ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    rows = document.get("models") if isinstance(document, dict) else None
    if not isinstance(rows, list) or len(rows) > _MAX_MODELS:
        raise ProductError(
            "ERR_LOCAL_OLLAMA_RESPONSE_INVALID",
            "Local Ollama inventory is malformed",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    values: set[str] = set()
    for row in rows:
        model_id = row.get("name") if isinstance(row, dict) else None
        if not isinstance(model_id, str):
            raise ProductError(
                "ERR_LOCAL_OLLAMA_RESPONSE_INVALID",
                "Local Ollama inventory has an invalid model identity",
                ProductErrorCategory.DATA_INTEGRITY,
            )
        try:
            ModelRoute(
                "ollama-runtime-validation", AiWorkload.PLANNING,
                ProviderFamily.LOCAL_OPEN_SOURCE, "ollama", model_id,
                CostClass.LOCAL_FREE_AI, capabilities=("TEXT_GENERATION",),
            )
        except ValueError as exc:
            raise ProductError(
                "ERR_LOCAL_OLLAMA_RESPONSE_INVALID",
                "Local Ollama inventory has an invalid model identity",
                ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        values.add(model_id)
    return tuple(sorted(values))


def resolve_installed_ollama_executable() -> Path | None:
    """Resolve PATH installation only; never guesses or creates an executable."""
    candidate = shutil.which("ollama")
    if not candidate:
        return None
    path = Path(candidate)
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    if not resolved.is_file() or resolved.name.casefold() not in {"ollama", "ollama.exe"}:
        return None
    return resolved


class OllamaRuntimeLifecycle:
    """Single-process coordinator; loopback readiness remains the cross-process truth."""

    def __init__(
        self,
        *,
        transport: LocalOllamaTransport | None = None,
        executable_resolver: Callable[[], Path | None] = resolve_installed_ollama_executable,
        popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
        start_timeout_seconds: float = _START_TIMEOUT_SECONDS,
    ) -> None:
        if not 1.0 <= start_timeout_seconds <= 60.0:
            raise ValueError("start_timeout_seconds is invalid")
        self._transport = transport or UrllibLocalOllamaTransport()
        self._executable_resolver = executable_resolver
        self._popen_factory = popen_factory
        self._clock = clock
        self._sleeper = sleeper
        self._start_timeout_seconds = start_timeout_seconds
        self._lock = threading.RLock()
        self._product_process: subprocess.Popen | None = None

    def probe(self) -> OllamaRuntimeSnapshot:
        try:
            models = _models_from_tags(self._transport)
        except ProductError as exc:
            if exc.code == "ERR_LOCAL_OLLAMA_UNREACHABLE":
                return OllamaRuntimeSnapshot(
                    "FAILED", (), False, "OLLAMA_NOT_RUNNING",
                    "Ollamaは起動していません。BAI Video Productionが既存導入を確認して起動します。",
                )
            return OllamaRuntimeSnapshot(
                "FAILED", (), False, exc.code,
                "Ollamaの状態を確認できません。設定とローカルruntimeを確認してください。",
            )
        product_owned = self._product_process is not None and self._product_process.poll() is None
        if models:
            return OllamaRuntimeSnapshot("READY", models, product_owned, None, "Ollamaは利用可能です。")
        return OllamaRuntimeSnapshot(
            "NO_MODEL", (), product_owned, "OLLAMA_MODEL_NOT_INSTALLED",
            "Ollamaは起動済みですが、利用可能な企画Modelがありません。Modelを導入してから再確認してください。",
        )

    def ensure_started(self) -> OllamaRuntimeSnapshot:
        """Reuse ready runtime, or start a verified local executable at most once."""
        with self._lock:
            initial = self.probe()
            if initial.state in {"READY", "NO_MODEL"}:
                return initial
            if self._product_process is not None and self._product_process.poll() is None:
                return self._wait_for_ready(started_by_product=True)
            executable = self._executable_resolver()
            if executable is None:
                return OllamaRuntimeSnapshot(
                    "NOT_INSTALLED", (), False, "OLLAMA_EXECUTABLE_NOT_FOUND",
                    "Ollamaが導入されていません。無料ローカル企画Modelを使うにはOllamaを導入してください。",
                )
            try:
                self._product_process = self._popen_factory(
                    [str(executable), "serve"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                )
            except OSError:
                return OllamaRuntimeSnapshot(
                    "FAILED", (), False, "OLLAMA_START_FAILED",
                    "Ollamaを起動できませんでした。ローカルruntimeの状態を確認してください。",
                )
            return self._wait_for_ready(started_by_product=True)

    def _wait_for_ready(self, *, started_by_product: bool) -> OllamaRuntimeSnapshot:
        deadline = self._clock() + self._start_timeout_seconds
        while self._clock() < deadline:
            current = self.probe()
            if current.state in {"READY", "NO_MODEL"}:
                return OllamaRuntimeSnapshot(
                    current.state, current.model_ids, started_by_product,
                    current.reason_code, current.message_ja,
                )
            if self._product_process is not None and self._product_process.poll() is not None:
                return OllamaRuntimeSnapshot(
                    "FAILED", (), started_by_product, "OLLAMA_START_EXITED",
                    "Ollamaの起動処理が終了しました。port競合またはruntime設定を確認してください。",
                )
            self._sleeper(0.2)
        return OllamaRuntimeSnapshot(
            "FAILED", (), started_by_product, "OLLAMA_START_TIMEOUT",
            "Ollamaの起動待機が時間切れになりました。runtimeの状態を確認してください。",
        )


__all__ = ["OllamaRuntimeLifecycle", "OllamaRuntimeSnapshot", "resolve_installed_ollama_executable"]
