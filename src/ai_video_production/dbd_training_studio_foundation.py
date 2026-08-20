"""TASK-050 R1 operational foundation for BAI DbD Training Studio.

This module owns machine-local Workspace discovery/selection metadata and
Runtime Environment Profiles. Training data remains inside the selected
Workspace; machine-local registry data stays outside the dataset.

Important boundaries:
- workspace_id is stable identity; display name and path are mutable metadata.
- LOCALAPPDATA is only a settings/default suggestion location, never a forced
  training-data destination.
- Runtime Profiles contain paths and execution settings only; credentials are
  deliberately unsupported.
- Workspace relocation is not performed here. R1 exposes a non-mutating
  migration preflight so a later atomic unit can implement journaled migration.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Callable
from uuid import uuid4


WORKSPACE_SCHEMA_VERSION = "1.0.0"
RUNTIME_PROFILE_SCHEMA_VERSION = "1.0.0"
REGISTRY_SCHEMA_VERSION = "1.0.0"
WORKSPACE_MARKER = "workspace.json"

_INVALID_FOLDER_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    temp = Path(raw_temp)
    try:
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def training_studio_settings_root() -> Path:
    """Return machine-local settings root, not the training Workspace root."""
    override = os.environ.get("BVP_DBD_TRAINING_SETTINGS_ROOT")
    if override:
        return Path(override).expanduser()
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / ".local" / "share"
    return base / "BAI Video Production" / "training-studio"


def legacy_training_workspace_root() -> Path:
    """Return the pre-TASK-050 default only as a migration/adoption candidate."""
    override = os.environ.get("BVP_DBD_TRAINING_ROOT")
    if override:
        return Path(override).expanduser()
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / ".local" / "share"
    return base / "BAI Video Production" / "training" / "dbd"


def safe_workspace_folder_name(display_name: str) -> str:
    value = _INVALID_FOLDER_CHARS.sub("-", display_name.strip()).strip(" .")
    if not value:
        raise ValueError("ワークスペース名を入力してください。")
    if len(value) > 96:
        value = value[:96].rstrip(" .")
    return value


@dataclass(frozen=True, slots=True)
class WorkspaceDescriptor:
    workspace_id: str
    display_name: str
    root_path: str
    created_at: str
    updated_at: str
    selected_runtime_profile_id: str | None = None

    @property
    def root(self) -> Path:
        return Path(self.root_path)

    def to_dict(self) -> dict:
        return {
            "schema_version": WORKSPACE_SCHEMA_VERSION,
            "workspace_id": self.workspace_id,
            "display_name": self.display_name,
            "root_path": self.root_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "selected_runtime_profile_id": self.selected_runtime_profile_id,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "WorkspaceDescriptor":
        if payload.get("schema_version") != WORKSPACE_SCHEMA_VERSION:
            raise ValueError("対応していないワークスペース形式です。")
        workspace_id = str(payload.get("workspace_id") or "").strip()
        display_name = str(payload.get("display_name") or "").strip()
        root_path = str(payload.get("root_path") or "").strip()
        if not workspace_id or not display_name or not root_path:
            raise ValueError("ワークスペース情報が不足しています。")
        return cls(
            workspace_id=workspace_id,
            display_name=display_name,
            root_path=root_path,
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            selected_runtime_profile_id=(
                str(payload["selected_runtime_profile_id"]).strip()
                if payload.get("selected_runtime_profile_id")
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class WorkspaceMigrationPreflight:
    source_path: str
    destination_path: str
    source_file_count: int
    source_bytes: int
    destination_exists: bool
    destination_empty: bool
    same_location: bool
    can_migrate: bool
    blockers: tuple[str, ...] = ()


class WorkspaceRegistry:
    """Machine-local recent/default Workspace registry."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else training_studio_settings_root() / "workspace-registry.json"

    def _empty(self) -> dict:
        return {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "default_workspace_id": None,
            "recent": [],
        }

    def load(self) -> dict:
        if not self.path.is_file():
            return self._empty()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("ワークスペース履歴を読み込めません。") from exc
        if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
            raise ValueError("対応していないワークスペース履歴形式です。")
        if not isinstance(payload.get("recent", []), list):
            raise ValueError("ワークスペース履歴が壊れています。")
        return payload

    def remember(self, workspace: WorkspaceDescriptor, *, make_default: bool = True) -> None:
        payload = self.load()
        recent = [
            row for row in payload.get("recent", [])
            if row.get("workspace_id") != workspace.workspace_id
        ]
        recent.insert(0, {
            "workspace_id": workspace.workspace_id,
            "display_name": workspace.display_name,
            "root_path": workspace.root_path,
            "last_opened_at": _utc_now(),
        })
        payload["recent"] = recent[:20]
        if make_default:
            payload["default_workspace_id"] = workspace.workspace_id
        _atomic_write_json(self.path, payload)

    def recent(self) -> tuple[dict, ...]:
        return tuple(self.load().get("recent", []))

    def default_candidate(self) -> Path | None:
        payload = self.load()
        default_id = payload.get("default_workspace_id")
        if default_id:
            for row in payload.get("recent", []):
                if row.get("workspace_id") == default_id:
                    candidate = Path(str(row.get("root_path") or ""))
                    if candidate.is_dir():
                        return candidate
        return None


class WorkspaceService:
    REQUIRED_SUBDIRS = (
        "runtime-profiles",
        "hud-profiles",
        "training-data",
        "video-slices",
        "ocr",
        "trivia",
        "knowledge",
        "human-gold",
        "indexes",
        "receipts",
        "backups",
    )

    def __init__(self, registry: WorkspaceRegistry | None = None) -> None:
        self.registry = registry or WorkspaceRegistry()

    @staticmethod
    def marker_path(root: str | Path) -> Path:
        return Path(root) / WORKSPACE_MARKER

    def create(self, *, display_name: str, parent_directory: str | Path) -> WorkspaceDescriptor:
        folder = safe_workspace_folder_name(display_name)
        parent = Path(parent_directory).expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        root = parent / folder
        if root.exists() and any(root.iterdir()):
            raise ValueError(
                "作成先フォルダに既存ファイルがあります。既存ワークスペースとして開くか、別の名前を指定してください。"
            )
        root.mkdir(parents=True, exist_ok=True)
        now = _utc_now()
        descriptor = WorkspaceDescriptor(
            workspace_id=f"dbdws-{uuid4().hex}",
            display_name=display_name.strip(),
            root_path=str(root.resolve()),
            created_at=now,
            updated_at=now,
        )
        self._initialize(descriptor)
        self.registry.remember(descriptor)
        return descriptor

    def adopt_existing(self, root: str | Path, *, display_name: str | None = None) -> WorkspaceDescriptor:
        resolved = Path(root).expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError("選択したワークスペースフォルダが存在しません。")
        marker = self.marker_path(resolved)
        if marker.is_file():
            descriptor = self.open(resolved)
            self.registry.remember(descriptor)
            return descriptor
        now = _utc_now()
        descriptor = WorkspaceDescriptor(
            workspace_id=f"dbdws-{uuid4().hex}",
            display_name=(display_name or resolved.name or "DbD学習環境").strip(),
            root_path=str(resolved),
            created_at=now,
            updated_at=now,
        )
        self._initialize(descriptor, preserve_existing=True)
        self.registry.remember(descriptor)
        return descriptor

    def open(self, root: str | Path) -> WorkspaceDescriptor:
        resolved = Path(root).expanduser().resolve()
        marker = self.marker_path(resolved)
        if not marker.is_file():
            raise ValueError("workspace.json が見つかりません。既存データとして取り込んでください。")
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("workspace.json を読み込めません。") from exc
        descriptor = WorkspaceDescriptor.from_dict(payload)
        # Physical location is authoritative at open time. This allows a copied
        # Workspace to be detected without silently changing workspace identity.
        if Path(descriptor.root_path).resolve() != resolved:
            descriptor = WorkspaceDescriptor(
                workspace_id=descriptor.workspace_id,
                display_name=descriptor.display_name,
                root_path=str(resolved),
                created_at=descriptor.created_at,
                updated_at=_utc_now(),
                selected_runtime_profile_id=descriptor.selected_runtime_profile_id,
            )
            _atomic_write_json(marker, descriptor.to_dict())
        self.registry.remember(descriptor)
        return descriptor

    def rename(self, workspace: WorkspaceDescriptor, display_name: str) -> WorkspaceDescriptor:
        safe_workspace_folder_name(display_name)  # validate display text bounds/emptiness
        updated = WorkspaceDescriptor(
            workspace_id=workspace.workspace_id,
            display_name=display_name.strip(),
            root_path=workspace.root_path,
            created_at=workspace.created_at,
            updated_at=_utc_now(),
            selected_runtime_profile_id=workspace.selected_runtime_profile_id,
        )
        _atomic_write_json(self.marker_path(workspace.root), updated.to_dict())
        self.registry.remember(updated)
        return updated

    def set_runtime_profile(
        self,
        workspace: WorkspaceDescriptor,
        profile_id: str | None,
    ) -> WorkspaceDescriptor:
        updated = WorkspaceDescriptor(
            workspace_id=workspace.workspace_id,
            display_name=workspace.display_name,
            root_path=workspace.root_path,
            created_at=workspace.created_at,
            updated_at=_utc_now(),
            selected_runtime_profile_id=profile_id.strip() if profile_id else None,
        )
        _atomic_write_json(self.marker_path(workspace.root), updated.to_dict())
        self.registry.remember(updated)
        return updated

    def migration_preflight(
        self,
        workspace: WorkspaceDescriptor,
        destination_parent: str | Path,
    ) -> WorkspaceMigrationPreflight:
        source = workspace.root.resolve()
        parent = Path(destination_parent).expanduser().resolve()
        destination = parent / source.name
        blockers: list[str] = []
        same = destination == source
        if same:
            blockers.append("移動先が現在のワークスペースと同じです。")
        if not source.is_dir():
            blockers.append("現在のワークスペースが見つかりません。")
        destination_exists = destination.exists()
        destination_empty = (
            destination_exists and destination.is_dir() and not any(destination.iterdir())
        )
        if destination_exists and not destination_empty and not same:
            blockers.append("移動先に同名の空ではないフォルダがあります。")

        count = 0
        total = 0
        if source.is_dir():
            for path in source.rglob("*"):
                if path.is_file():
                    count += 1
                    try:
                        total += path.stat().st_size
                    except OSError:
                        blockers.append(f"サイズを確認できないファイルがあります: {path.name}")
                        break

        return WorkspaceMigrationPreflight(
            source_path=str(source),
            destination_path=str(destination),
            source_file_count=count,
            source_bytes=total,
            destination_exists=destination_exists,
            destination_empty=destination_empty,
            same_location=same,
            can_migrate=not blockers,
            blockers=tuple(blockers),
        )

    def _initialize(self, descriptor: WorkspaceDescriptor, *, preserve_existing: bool = False) -> None:
        root = descriptor.root
        root.mkdir(parents=True, exist_ok=True)
        marker = self.marker_path(root)
        if marker.exists() and preserve_existing:
            raise ValueError("既にworkspace.jsonがあります。")
        for name in self.REQUIRED_SUBDIRS:
            (root / name).mkdir(parents=True, exist_ok=True)
        _atomic_write_json(marker, descriptor.to_dict())


@dataclass(frozen=True, slots=True)
class RuntimeTool:
    tool_id: str
    effective_path: str | None
    source: str
    health: str
    version: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeEnvironmentProfile:
    profile_id: str
    display_name: str
    python_executable: str
    ffmpeg: RuntimeTool
    ffprobe: RuntimeTool
    tesseract: RuntimeTool
    faster_whisper_package_version: str | None
    faster_whisper_model_cache: str | None
    default_whisper_model: str = "small"
    device: str = "auto"
    compute_type: str = "int8"
    ocr_language: str = "jpn+eng"
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        return {
            "schema_version": RUNTIME_PROFILE_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "python_executable": self.python_executable,
            "ffmpeg": self.ffmpeg.to_dict(),
            "ffprobe": self.ffprobe.to_dict(),
            "tesseract": self.tesseract.to_dict(),
            "faster_whisper_package_version": self.faster_whisper_package_version,
            "faster_whisper_model_cache": self.faster_whisper_model_cache,
            "default_whisper_model": self.default_whisper_model,
            "device": self.device,
            "compute_type": self.compute_type,
            "ocr_language": self.ocr_language,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "RuntimeEnvironmentProfile":
        if payload.get("schema_version") != RUNTIME_PROFILE_SCHEMA_VERSION:
            raise ValueError("対応していない実行環境プロファイル形式です。")
        def tool(name: str) -> RuntimeTool:
            value = payload.get(name) or {}
            return RuntimeTool(
                tool_id=name,
                effective_path=value.get("effective_path"),
                source=str(value.get("source") or "PROFILE_SAVED"),
                health=str(value.get("health") or "UNKNOWN"),
                version=value.get("version"),
            )
        return cls(
            profile_id=str(payload.get("profile_id") or "").strip(),
            display_name=str(payload.get("display_name") or "").strip(),
            python_executable=str(payload.get("python_executable") or "").strip(),
            ffmpeg=tool("ffmpeg"),
            ffprobe=tool("ffprobe"),
            tesseract=tool("tesseract"),
            faster_whisper_package_version=payload.get("faster_whisper_package_version"),
            faster_whisper_model_cache=payload.get("faster_whisper_model_cache"),
            default_whisper_model=str(payload.get("default_whisper_model") or "small"),
            device=str(payload.get("device") or "auto"),
            compute_type=str(payload.get("compute_type") or "int8"),
            ocr_language=str(payload.get("ocr_language") or "jpn+eng"),
            updated_at=str(payload.get("updated_at") or _utc_now()),
        )


def _tool_from_path(tool_id: str, path: str | None, source: str) -> RuntimeTool:
    return RuntimeTool(
        tool_id=tool_id,
        effective_path=path,
        source=source,
        health="AVAILABLE" if path else "MISSING",
        version=None,
    )


def default_model_cache() -> str:
    # Hugging Face cache is used by faster-whisper/CTranslate2 model downloads
    # unless the environment explicitly redirects it.
    explicit = os.environ.get("HF_HOME")
    if explicit:
        return str(Path(explicit).expanduser())
    return str(Path.home() / ".cache" / "huggingface" / "hub")


def resolve_workspace_runtime_profile(
    workspace: WorkspaceDescriptor,
    *,
    store: "RuntimeProfileStore | None" = None,
) -> RuntimeEnvironmentProfile:
    """Return the workspace-selected runtime profile with safe auto-detect fallback.

    Saved runtime settings are Product state.  Training surfaces must not silently
    ignore them and fall back to PATH-only tools, otherwise OCR/ASR can behave
    differently from the Runtime tab that the operator already configured.
    """
    active_store = store or RuntimeProfileStore()
    profile_id = (workspace.selected_runtime_profile_id or "").strip()
    if profile_id:
        try:
            return active_store.load(profile_id)
        except Exception:
            # A stale/deleted profile must not brick the Studio.  Auto-detect is
            # explicit fallback and the Runtime tab can save a new selection.
            pass
    return active_store.autodetect()


class RuntimeProfileStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else training_studio_settings_root() / "runtime-profiles"

    @staticmethod
    def autodetect(
        *,
        which: Callable[[str], str | None] = shutil.which,
    ) -> RuntimeEnvironmentProfile:
        try:
            whisper_version = importlib.metadata.version("faster-whisper")
        except importlib.metadata.PackageNotFoundError:
            whisper_version = None
        return RuntimeEnvironmentProfile(
            profile_id="auto",
            display_name="自動検出",
            python_executable=sys.executable,
            ffmpeg=_tool_from_path("ffmpeg", which("ffmpeg"), "AUTO_DETECTED"),
            ffprobe=_tool_from_path("ffprobe", which("ffprobe"), "AUTO_DETECTED"),
            tesseract=_tool_from_path("tesseract", which("tesseract"), "AUTO_DETECTED"),
            faster_whisper_package_version=whisper_version,
            faster_whisper_model_cache=default_model_cache(),
        )

    def save(self, profile: RuntimeEnvironmentProfile) -> Path:
        if not profile.profile_id.strip() or not profile.display_name.strip():
            raise ValueError("実行環境プロファイル名が不足しています。")
        payload = profile.to_dict()
        forbidden_keys = {"api_key", "token", "password", "secret", "private_key"}
        if forbidden_keys.intersection(payload):
            raise ValueError("実行環境プロファイルに認証情報は保存できません。")
        path = self.root / f"{safe_workspace_folder_name(profile.profile_id)}.json"
        _atomic_write_json(path, payload)
        return path

    def load(self, profile_id: str) -> RuntimeEnvironmentProfile:
        path = self.root / f"{safe_workspace_folder_name(profile_id)}.json"
        if not path.is_file():
            raise ValueError("実行環境プロファイルが見つかりません。")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("実行環境プロファイルを読み込めません。") from exc
        return RuntimeEnvironmentProfile.from_dict(payload)

    def list_profiles(self) -> tuple[RuntimeEnvironmentProfile, ...]:
        if not self.root.is_dir():
            return ()
        values: list[RuntimeEnvironmentProfile] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                values.append(RuntimeEnvironmentProfile.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return tuple(values)
