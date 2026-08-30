"""Safe first-run Project composition for the ordinary TASK-036 executable."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path

from .atomic import AtomicJsonWriter, exclusive_file_update_lock
from .errors import ProductError, ProductErrorCategory
from .task036_trusted_launcher import Task036LaunchConfiguration


_FIRST_RUN_PROJECT_ID = "bvp-first-run-project"
_FIRST_RUN_CONFIGURATION_NAME = "task036-first-run-launch.json"


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
            "display_name": "新しいBAI Video Production Project",
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
        try:
            configuration = Task036LaunchConfiguration.load(config_path)
        except ProductError as exc:
            raise _bootstrap_error(
                "ERR_TASK036_FIRST_RUN_CONFIG_INVALID",
                "初回Project設定を読み込めません。保存先を確認してください。",
                category=ProductErrorCategory.DATA_INTEGRITY,
            ) from exc
        if configuration.project_id != _FIRST_RUN_PROJECT_ID or configuration.project_root != project_root:
            raise _bootstrap_error(
                "ERR_TASK036_FIRST_RUN_CONFIG_IDENTITY",
                "初回Project設定の識別情報が一致しません。保存先を確認してください。",
                category=ProductErrorCategory.SECURITY,
            )
    return config_path


__all__ = ["ensure_first_run_launch_configuration"]