"""Safe first-run Project composition for the ordinary TASK-036 executable."""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path
import stat

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .task036_trusted_launcher import (
    TASK036_LAUNCH_CONFIG_MAX_BYTES,
    Task036LaunchConfiguration,
)


_FIRST_RUN_PROJECT_ID = "bvp-first-run-project"
_FIRST_RUN_CONFIGURATION_NAME = "task036-first-run-launch.json"
_FIRST_RUN_DISPLAY_NAME = "新しいBAI Video Production Project"
_KNOWN_LEGACY_FIRST_RUN_DISPLAY_NAMES = frozenset(
    {"�V����BAI Video Production Project"}
)


def _bootstrap_error(code: str, message: str, *, category: ProductErrorCategory) -> ProductError:
    return ProductError(code, message, category)


def _ensure_directory(path: Path) -> None:
    if path.is_symlink():
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_PATH_UNSAFE",
            "初回Projectの保存先を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        )
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_STORAGE_UNAVAILABLE",
            "初回Projectの保存先を作成できません。書込み可能なローカル保存先を確認してください。",
            category=ProductErrorCategory.STATE,
        ) from exc
    if path.is_symlink() or not path.is_dir():
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_PATH_UNSAFE",
            "初回Projectの保存先を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        )


def _ensure_placeholder_file(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_PATH_UNSAFE",
            "初回Projectの内部状態を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        )
    if path.exists():
        return
    try:
        with path.open("xb") as stream:
            stream.write(b"BAI Video Production empty Project bootstrap; no user media is bound.\n")
    except FileExistsError:
        return
    except OSError as exc:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_STORAGE_UNAVAILABLE",
            "初回Projectの内部状態を保存できません。書込み可能なローカル保存先を確認してください。",
            category=ProductErrorCategory.STATE,
        ) from exc


def _configuration_document(project_root: Path, source_root: Path) -> dict[str, object]:
    source = source_root / "empty-project-source.placeholder"
    analysis = project_root / "analysis-placeholder.wav"
    return {
        "launch_config_version": "1.0.0",
        "project": {
            "project_id": _FIRST_RUN_PROJECT_ID,
            "display_name": _FIRST_RUN_DISPLAY_NAME,
            "project_root": str(project_root),
        },
        "paths": {
            "source_roots": [str(source_root)],
            "asset_root": str(project_root / "assets"),
            "job_root": str(project_root / "jobs"),
            "database_path": str(project_root / "product.sqlite3"),
            "analysis_source_path": str(source),
            "analysis_audio_path": str(analysis),
            "asr_cache_directory": str(project_root / "model-cache"),
            "transcription_output": str(project_root / "transcription"),
            "cut_output": str(project_root / "cut"),
            "handoff_destination": str(project_root / "handoff"),
            "native_render_evidence_root": str(project_root / "native-render"),
            "native_render_report_path": str(project_root / "native-render-report.json"),
        },
        "ingest": {
            "production_job_id": "JOB-00000000000000000000000000",
            "profile_snapshot_id": "PSN-00000000000000000000000000",
            "owner": "local-project-owner",
        },
        "asr": {
            "model": "cached-local-model",
            "device": "cpu",
            "compute_type": "int8",
            "beam_size": 5,
            "vad_filter": True,
            "allow_model_download": False,
            "language": "ja",
        },
        "resolve": {
            "sandbox_project": "BAI_CAPABILITY_PROBE_TASK036_FIRST_RUN",
            "timeline_rate": "30",
            "source_frame_rate": "30",
        },
    }


def _load_configuration_document(
    config_path: Path,
) -> tuple[
    dict[str, object],
    Task036LaunchConfiguration,
    tuple[int, int, int, int],
]:
    """Read and validate one existing configuration snapshot."""

    try:
        before_path = config_path.lstat()
        _require_regular_configuration_stat(before_path)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(config_path, flags)
        try:
            os.set_inheritable(descriptor, False)
            before_handle = os.fstat(descriptor)
            _require_regular_configuration_stat(before_handle)
            if _configuration_identity(before_path) != _configuration_identity(before_handle):
                raise ValueError("first-run configuration identity changed before read")
            chunks: list[bytes] = []
            remaining = TASK036_LAUNCH_CONFIG_MAX_BYTES + 1
            while remaining > 0:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            encoded = b"".join(chunks)
            after_handle = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after_path = config_path.lstat()
        _require_regular_configuration_stat(after_handle)
        _require_regular_configuration_stat(after_path)
        identity = _configuration_identity(before_handle)
        if (
            identity != _configuration_identity(after_handle)
            or identity != _configuration_identity(after_path)
            or (
                before_handle.st_size <= TASK036_LAUNCH_CONFIG_MAX_BYTES
                and len(encoded) != before_handle.st_size
            )
        ):
            raise ValueError("first-run configuration identity changed during read")
    except (OSError, ValueError) as exc:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE",
            "初回Project設定を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        ) from exc
    try:
        if not 0 < len(encoded) <= TASK036_LAUNCH_CONFIG_MAX_BYTES:
            raise ValueError("first-run configuration is outside the size bound")
        raw = json.loads(encoded.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("first-run configuration must be an object")
        configuration = Task036LaunchConfiguration.from_dict(raw)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        ProductError,
    ) as exc:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
            "初回Project設定を読み込めません。保存先を確認してください。",
            category=ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    return raw, configuration, identity


def _configuration_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _require_regular_configuration_stat(value: os.stat_result) -> None:
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise ValueError("first-run configuration must be one regular private file")


def _require_current_configuration_identity(
    config_path: Path,
    expected: tuple[int, int, int, int],
) -> None:
    try:
        current = config_path.lstat()
        _require_regular_configuration_stat(current)
    except (OSError, ValueError) as exc:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE",
            "初回Project設定を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        ) from exc
    if _configuration_identity(current) != expected:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE",
            "初回Project設定を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        )


def _repair_known_legacy_display_name(
    config_path: Path,
    document: dict[str, object],
    configuration: Task036LaunchConfiguration,
    expected_identity: tuple[int, int, int, int],
) -> Task036LaunchConfiguration:
    project = document.get("project")
    if not isinstance(project, dict):
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
            "初回Project設定を読み込めません。保存先を確認してください。",
            category=ProductErrorCategory.DATA_INTEGRITY,
        )
    raw_display_name = project.get("display_name")
    if raw_display_name == _FIRST_RUN_DISPLAY_NAME:
        return configuration
    if raw_display_name not in _KNOWN_LEGACY_FIRST_RUN_DISPLAY_NAMES:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_DISPLAY_NAME_UNKNOWN",
            "初回Project名を安全に更新できません。既存設定を確認してください。",
            category=ProductErrorCategory.DATA_INTEGRITY,
        )
    updated = dict(document)
    updated_project = dict(project)
    updated_project["display_name"] = _FIRST_RUN_DISPLAY_NAME
    updated["project"] = updated_project

    def require_current_before_replace(stage: str, _temporary: Path) -> None:
        if stage == "before_replace":
            _require_current_configuration_identity(config_path, expected_identity)

    try:
        AtomicJsonWriter.write(
            config_path,
            updated,
            validator=lambda raw: Task036LaunchConfiguration.from_dict(raw),
            failure_injector=require_current_before_replace,
        )
    except ProductError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_WRITE_FAILED",
            "初回Project設定を保存できません。保存先を確認してください。",
            category=ProductErrorCategory.DATA_INTEGRITY,
        ) from exc
    repaired_document, repaired, _ = _load_configuration_document(config_path)
    repaired_project = repaired_document.get("project")
    if (
        repaired.display_name != _FIRST_RUN_DISPLAY_NAME
        or not isinstance(repaired_project, dict)
        or repaired_project.get("display_name") != _FIRST_RUN_DISPLAY_NAME
    ):
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
            "初回Project設定を読み込めません。保存先を確認してください。",
            category=ProductErrorCategory.DATA_INTEGRITY,
        )
    return repaired


def _default_application_root(environment: Mapping[str, str]) -> Path:
    raw = environment.get("LOCALAPPDATA") or environment.get("APPDATA")
    if not raw:
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_STORAGE_UNAVAILABLE",
            "初回Projectのローカル保存先を確認できません。Windowsのアプリ保存先を確認してください。",
            category=ProductErrorCategory.STATE,
        )
    root = Path(raw)
    if not root.is_absolute():
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_PATH_UNSAFE",
            "初回Projectの保存先を安全に確認できません。Windowsのアプリ保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        )
    return root / "BAISOUND" / "BAI Video Production"


def ensure_first_run_launch_configuration(
    *,
    application_root: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return one validated, private first-run launch config without touching user media.

    The internal placeholder exists only to satisfy the existing trusted-launch
    schema.  It is never ingested automatically and does not represent a user
    source asset.  User media remains unbound until the visible intake flow.
    """
    root = (
        Path(application_root)
        if application_root is not None
        else _default_application_root(os.environ if environment is None else environment)
    )
    if not root.is_absolute():
        raise _bootstrap_error(
            "ERR_TASK036_FIRST_RUN_PATH_UNSAFE",
            "初回Projectの保存先を安全に確認できません。保存先を確認してください。",
            category=ProductErrorCategory.SECURITY,
        )
    control_root = root / "control"
    project_root = root / "projects" / _FIRST_RUN_PROJECT_ID
    source_root = project_root / "incoming"
    config_path = control_root / _FIRST_RUN_CONFIGURATION_NAME
    for directory in (root, control_root, project_root, source_root, project_root / "model-cache"):
        _ensure_directory(directory)
    with exclusive_file_update_lock(config_path):
        if config_path.is_symlink() or (config_path.exists() and not config_path.is_file()):
            raise _bootstrap_error(
                "ERR_TASK036_FIRST_RUN_CONFIG_UNSAFE",
                "初回Project設定を安全に確認できません。保存先を確認してください。",
                category=ProductErrorCategory.SECURITY,
            )
        _ensure_placeholder_file(source_root / "empty-project-source.placeholder")
        _ensure_placeholder_file(project_root / "analysis-placeholder.wav")
        if not config_path.exists():
            document = _configuration_document(project_root, source_root)
            try:
                AtomicJsonWriter.write(
                    config_path,
                    document,
                    validator=lambda raw: Task036LaunchConfiguration.from_dict(raw),
                )
            except (OSError, UnicodeError, ValueError) as exc:
                raise _bootstrap_error(
                    "ERR_TASK036_FIRST_RUN_CONFIG_WRITE_FAILED",
                    "初回Project設定を保存できません。保存先を確認してください。",
                    category=ProductErrorCategory.DATA_INTEGRITY,
                ) from exc
        document, configuration, configuration_identity = _load_configuration_document(
            config_path
        )
        if configuration.project_id != _FIRST_RUN_PROJECT_ID or configuration.project_root != project_root:
            raise _bootstrap_error(
                "ERR_TASK036_FIRST_RUN_CONFIG_IDENTITY",
                "初回Project設定の識別情報が一致しません。保存先を確認してください。",
                category=ProductErrorCategory.SECURITY,
            )
        configuration = _repair_known_legacy_display_name(
            config_path,
            document,
            configuration,
            configuration_identity,
        )
    return config_path


__all__ = ["ensure_first_run_launch_configuration"]
