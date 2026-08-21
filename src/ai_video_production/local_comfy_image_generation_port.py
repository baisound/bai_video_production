"""Fail-closed TASK-013 local FLUX.1 Schnell text-to-image port."""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import AbstractContextManager
from importlib.resources import files
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import time
from typing import Any
from urllib.parse import urlparse
import zlib

from .ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily
from .comfyui import (
    ComfyResourcePolicy,
    ComfyUIClient,
    _history_entry,
    _image_descriptors,
    admit_comfy_resources,
    assert_workflow_inputs_available,
    assert_workflow_supported,
    render_workflow_placeholders,
)
from .creative_generation_execution_application import (
    LocalGenerationExecutionRequest,
    LocalGenerationExecutionResult,
    LocalGenerationRuntimeReadiness,
)
from .errors import ProductError, ProductErrorCategory
from .production_control_store import _exclusive_snapshot_lock
from .serialization import canonical_json_bytes, sha256_bytes


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_REQUIRED_CLASSES = frozenset({
    "CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage",
    "KSampler", "VAEDecode", "SaveImage",
})
_PROHIBITED_RUNTIME_FLAGS = frozenset({
    "--cpu", "--disable-async-offload", "--disable-dynamic-vram",
    "--disable-pinned-memory", "--gpu-only", "--highvram", "--lowvram",
    "--novram",
})
FLUX1_SCHNELL_FP8_WORKFLOW_SHA256 = "sha256:b0cf89899e237112239397b5978053a0212e11c37f6a2041e9e6fa3008550926"
_RUNTIME_POLICY = "FIXED_LOOPBACK_FLUX1_SCHNELL_FP8_IMAGE_V1"
_PREFLIGHT_PROMPT = "BAI TASK-013 IMAGE READINESS PREFLIGHT - NO DISPATCH"
_CHECKPOINT = "flux1-schnell-fp8.safetensors"


def default_flux1_schnell_fp8_workflow_path() -> Path:
    target = files("ai_video_production").joinpath(
        "workflow_resources/flux1_schnell_fp8_t2i_api.json"
    )
    path = Path(str(target))
    if path.is_symlink() or not path.is_file():
        raise ProductError(
            "ERR_GENERATION_COMFY_IMAGE_WORKFLOW_RESOURCE",
            "Packaged FLUX image workflow is unavailable",
            ProductErrorCategory.DATA_INTEGRITY,
        )
    return path


@dataclass(frozen=True, slots=True)
class LocalComfyImageGenerationConfig:
    endpoint: str
    workflow_path: Path
    workflow_sha256: str
    comfy_output_root: Path
    project_output_root: Path
    staging_root: Path
    dispatch_journal_root: Path
    route_id: str
    provider_id: str
    model_id: str
    width: int = 1024
    height: int = 1024
    steps: int = 4
    poll_interval_seconds: float = 1.0
    completion_timeout_seconds: int = 1800
    max_output_bytes: int = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if (
            parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.port != 8188 or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}
            or self.endpoint.rstrip("/") != "http://127.0.0.1:8188"
        ):
            raise ValueError("endpoint must be the exact bare 127.0.0.1 HTTP origin")
        for value, name in (
            (self.route_id, "route_id"), (self.provider_id, "provider_id"),
            (self.model_id, "model_id"),
        ):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"{name} is invalid")
        if not _SHA_RE.fullmatch(self.workflow_sha256):
            raise ValueError("workflow_sha256 is invalid")
        for value, name in (
            (self.width, "width"), (self.height, "height"),
            (self.steps, "steps"),
            (self.completion_timeout_seconds, "completion_timeout_seconds"),
            (self.max_output_bytes, "max_output_bytes"),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if self.width < 64 or self.height < 64 or self.width % 16 or self.height % 16:
            raise ValueError("width and height must be >=64 and divisible by 16")
        if self.width * self.height > 16_777_216:
            raise ValueError("image pixel count is too large")
        if not 1 <= self.steps <= 20:
            raise ValueError("steps must be 1-20")
        if isinstance(self.poll_interval_seconds, bool) or not isinstance(
            self.poll_interval_seconds, (int, float)
        ) or not 0.1 <= self.poll_interval_seconds <= 30:
            raise ValueError("poll_interval_seconds is invalid")
        if not 1 <= self.completion_timeout_seconds <= 86400:
            raise ValueError("completion_timeout_seconds is invalid")
        if not 1 <= self.max_output_bytes <= 256 * 1024 * 1024:
            raise ValueError("max_output_bytes is invalid")


def _require_directory(path: Path, *, code: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ProductError(code, "Configured image generation directory is missing or unsafe", ProductErrorCategory.SECURITY)
    return path.resolve(strict=True)


def _load_workflow(path: Path, expected_sha256: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW", "Image workflow is missing or unsafe", ProductErrorCategory.SECURITY)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW", "Image workflow is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
    if sha256_bytes(canonical_json_bytes(value)) != expected_sha256:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW_CHECKSUM", "Image workflow checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
    if not isinstance(value, dict) or not value:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW", "Image workflow must be a non-empty API object", ProductErrorCategory.DATA_INTEGRITY)
    classes = {node.get("class_type") for node in value.values() if isinstance(node, dict)}
    if classes != _REQUIRED_CLASSES:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW_CLASSES", "Image workflow classes are not exact", ProductErrorCategory.SECURITY)
    serialized = json.dumps(value, ensure_ascii=False)
    for placeholder in ("{{PROMPT}}", "{{SEED}}", "{{WIDTH}}", "{{HEIGHT}}", "{{STEPS}}", "{{OUTPUT_PREFIX}}"):
        if serialized.count(placeholder) != 1:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW_PLACEHOLDER", "Image workflow placeholders are invalid", ProductErrorCategory.DATA_INTEGRITY)
    if serialized.count(_CHECKPOINT) != 1:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_CHECKPOINT", "Image workflow checkpoint identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return value


def _with_hash(value: dict[str, Any]) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != "journal_sha256"}
    body["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return body


def _read_stable_file(path: Path, *, max_bytes: int) -> bytes:
    try:
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_FILE", "Generated image is missing or unsafe", ProductErrorCategory.SECURITY)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
            if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_FILE", "Generated image identity changed before read", ProductErrorCategory.SECURITY)
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                raw = handle.read(max_bytes + 1)
            after_open = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after_path = os.lstat(path)
        if identity(after_open) != identity(opened) or identity(after_path) != identity(opened) or not stat.S_ISREG(after_path.st_mode):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_FILE", "Generated image identity changed during read", ProductErrorCategory.SECURITY)
    except OSError as exc:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_READ", "Generated image is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
    if len(raw) <= 0 or len(raw) > max_bytes:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_SIZE", "Generated image size is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return raw


class _PinnedDirectory(AbstractContextManager["_PinnedDirectory"]):
    """Pin a non-reparse directory and perform child I/O relative to it."""

    def __init__(self, path: Path, *, parent: "_PinnedDirectory | None" = None,
                 child_name: str | None = None) -> None:
        self.path = path
        self.parent = parent
        self.child_name = child_name
        self.fd: int | None = None
        self.win_handle: int | None = None
        self.win_identity: tuple[int, int] | None = None
        self.identity: tuple[int, int] | None = None

    @staticmethod
    def _windows_handle_identity(handle: int) -> tuple[int, int]:
        import ctypes
        from ctypes import wintypes

        class _ByHandleFileInformation(ctypes.Structure):
            _fields_ = (
                ("file_attributes", wintypes.DWORD),
                ("creation_time", wintypes.FILETIME),
                ("last_access_time", wintypes.FILETIME),
                ("last_write_time", wintypes.FILETIME),
                ("volume_serial_number", wintypes.DWORD),
                ("file_size_high", wintypes.DWORD),
                ("file_size_low", wintypes.DWORD),
                ("number_of_links", wintypes.DWORD),
                ("file_index_high", wintypes.DWORD),
                ("file_index_low", wintypes.DWORD),
            )

        information = _ByHandleFileInformation()
        get_information = ctypes.windll.kernel32.GetFileInformationByHandle
        get_information.argtypes = (wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation))
        get_information.restype = wintypes.BOOL
        if not get_information(wintypes.HANDLE(handle), ctypes.byref(information)):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Pinned image directory identity is unavailable", ProductErrorCategory.SECURITY)
        file_index = (int(information.file_index_high) << 32) | int(information.file_index_low)
        return int(information.volume_serial_number), file_index

    def __enter__(self) -> "_PinnedDirectory":
        if self.parent is not None:
            self.parent.assert_current()
        if self.parent is not None and self.parent.fd is not None:
            name = self._name(self.child_name or "")
            before = os.stat(name, dir_fd=self.parent.fd, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image child directory is missing or unsafe", ProductErrorCategory.SECURITY)
            self.fd = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=self.parent.fd,
            )
            opened = os.fstat(self.fd)
            current = os.stat(name, dir_fd=self.parent.fd, follow_symlinks=False)
            expected = (before.st_dev, before.st_ino)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != expected
                or (current.st_dev, current.st_ino) != expected
            ):
                os.close(self.fd)
                self.fd = None
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image child directory identity changed", ProductErrorCategory.SECURITY)
            self.identity = expected
            self.parent.assert_current()
            return self

        before = os.lstat(self.path)
        if not stat.S_ISDIR(before.st_mode):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image directory is missing or unsafe", ProductErrorCategory.SECURITY)
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            kernel32.CreateFileW.argtypes = (
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            )
            kernel32.CreateFileW.restype = wintypes.HANDLE
            kernel32.GetFileAttributesW.argtypes = (wintypes.LPCWSTR,)
            kernel32.GetFileAttributesW.restype = wintypes.DWORD
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.CreateFileW(
                str(self.path), 0x80, 0x1 | 0x2, None, 3,
                0x02000000 | 0x00200000, None,
            )
            if handle == wintypes.HANDLE(-1).value:
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image directory cannot be pinned", ProductErrorCategory.SECURITY)
            attributes = kernel32.GetFileAttributesW(str(self.path))
            if attributes == 0xFFFFFFFF or attributes & 0x400:
                kernel32.CloseHandle(handle)
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image directory is a reparse point", ProductErrorCategory.SECURITY)
            after = os.lstat(self.path)
            try:
                handle_identity = self._windows_handle_identity(handle)
            except ProductError:
                kernel32.CloseHandle(handle)
                raise
            if (
                not stat.S_ISDIR(after.st_mode)
                or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
                or (after.st_ino not in {0, handle_identity[1]})
            ):
                kernel32.CloseHandle(handle)
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image directory identity changed while pinning", ProductErrorCategory.SECURITY)
            self.win_handle = handle
            self.win_identity = handle_identity
        else:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            self.fd = os.open(self.path, flags)
            opened = os.fstat(self.fd)
            if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                os.close(self.fd)
                self.fd = None
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Image directory identity changed", ProductErrorCategory.SECURITY)
        self.identity = (before.st_dev, before.st_ino)
        if self.parent is not None:
            self.parent.assert_current()
        return self

    def __exit__(self, *_args: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.win_handle is not None:
            import ctypes
            from ctypes import wintypes

            ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(self.win_handle))
            self.win_handle = None
            self.win_identity = None

    def assert_current(self) -> None:
        try:
            current = os.lstat(self.path)
        except OSError as exc:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Pinned image directory disappeared", ProductErrorCategory.SECURITY) from exc
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != self.identity:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Pinned image directory was replaced", ProductErrorCategory.SECURITY)

    def pin_child(self, name: str) -> "_PinnedDirectory":
        name = self._name(name)
        if self.fd is None and self.win_handle is None:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIRECTORY", "Parent image directory is not pinned", ProductErrorCategory.SECURITY)
        return _PinnedDirectory(self.path / name, parent=self, child_name=name)

    @staticmethod
    def _name(name: str) -> str:
        if not isinstance(name, str) or not name or Path(name).name != name or "/" in name or "\\" in name:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_CHILD", "Image child name is invalid", ProductErrorCategory.SECURITY)
        return name

    def read(self, name: str, *, max_bytes: int) -> bytes:
        name = self._name(name)
        if self.fd is None:
            return _read_stable_file(self.path / name, max_bytes=max_bytes)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_FILE", "Image child is not a regular file", ProductErrorCategory.SECURITY)
            if opened.st_size <= 0 or opened.st_size > max_bytes:
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_SIZE", "Image child size is invalid", ProductErrorCategory.DATA_INTEGRITY)
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                raw = handle.read(max_bytes + 1)
            after = os.fstat(descriptor)
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_FILE", "Image child changed during read", ProductErrorCategory.SECURITY)
        finally:
            os.close(descriptor)
        if len(raw) <= 0 or len(raw) > max_bytes:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_SIZE", "Image child size is invalid", ProductErrorCategory.DATA_INTEGRITY)
        return raw

    def child_exists(self, name: str) -> bool:
        name = self._name(name)
        try:
            if self.fd is not None:
                os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            else:
                os.lstat(self.path / name)
        except FileNotFoundError:
            return False
        return True

    def mkdir(self, name: str, *, exist_ok: bool = False) -> None:
        name = self._name(name)
        if self.fd is not None:
            try:
                os.mkdir(name, mode=0o700, dir_fd=self.fd)
            except FileExistsError:
                if not exist_ok:
                    raise
            os.fsync(self.fd)
        else:
            (self.path / name).mkdir(exist_ok=exist_ok)
            self.assert_current()

    def write_atomic(self, temporary: str, target: str, data: bytes) -> None:
        temporary, target = self._name(temporary), self._name(target)
        if self.fd is not None:
            descriptor: int | None = None
            try:
                descriptor = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
            except FileExistsError:
                descriptor = os.open(temporary, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.fd)
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or opened.st_size != len(data):
                    os.close(descriptor)
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_TEMP_CONFLICT", "Residual image temporary file differs from the authorized bytes", ProductErrorCategory.DATA_INTEGRITY)
                with os.fdopen(descriptor, "rb", closefd=False) as handle:
                    raw = handle.read(len(data) + 1)
                if raw != data:
                    os.close(descriptor)
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_TEMP_CONFLICT", "Residual image temporary file differs from the authorized bytes", ProductErrorCategory.DATA_INTEGRITY)
            else:
                with os.fdopen(descriptor, "wb", closefd=False) as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(descriptor)
            try:
                opened = os.fstat(descriptor)
                os.replace(temporary, target, src_dir_fd=self.fd, dst_dir_fd=self.fd)
                os.fsync(self.fd)
                moved = os.stat(target, dir_fd=self.fd, follow_symlinks=False)
                after = os.fstat(descriptor)
                expected_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
                if (
                    not stat.S_ISREG(moved.st_mode)
                    or (moved.st_dev, moved.st_ino) != (opened.st_dev, opened.st_ino)
                    or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != expected_identity
                ):
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_ATOMIC_IDENTITY", "Image atomic target differs from the authorized temporary file", ProductErrorCategory.SECURITY)
                os.lseek(descriptor, 0, os.SEEK_SET)
                with os.fdopen(descriptor, "rb", closefd=False) as handle:
                    moved_raw = handle.read(len(data) + 1)
                if moved_raw != data:
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_ATOMIC_BYTES", "Image atomic target bytes changed during publication", ProductErrorCategory.DATA_INTEGRITY)
            finally:
                os.close(descriptor)
        else:
            import ctypes
            from ctypes import wintypes

            temp_path, target_path = self.path / temporary, self.path / target
            try:
                with temp_path.open("xb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                if self.read(temporary, max_bytes=max(1, len(data))) != data:
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_TEMP_CONFLICT", "Residual image temporary file differs from the authorized bytes", ProductErrorCategory.DATA_INTEGRITY)
            move_file = ctypes.windll.kernel32.MoveFileExW
            move_file.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
            move_file.restype = wintypes.BOOL
            if not move_file(str(temp_path), str(target_path), 0x1 | 0x8):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_DURABILITY", "Image file rename could not be made durable", ProductErrorCategory.DATA_INTEGRITY)
            if self.read(target, max_bytes=max(1, len(data))) != data:
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_ATOMIC_BYTES", "Image atomic target bytes changed during publication", ProductErrorCategory.DATA_INTEGRITY)
            self.assert_current()


def _probe_png(path: Path | None = None, *, raw: bytes | None = None,
               width: int, height: int, max_bytes: int) -> bytes:
    if raw is None:
        if path is None:
            raise ValueError("path or raw is required")
        raw = _read_stable_file(path, max_bytes=max_bytes)
    if len(raw) <= 0 or len(raw) > max_bytes:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_SIZE", "Generated image size is invalid", ProductErrorCategory.DATA_INTEGRITY)
    if not raw.startswith(_PNG_SIGNATURE):
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "Generated output is not a PNG image", ProductErrorCategory.DATA_INTEGRITY)
    offset = len(_PNG_SIGNATURE)
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(raw):
        if len(chunks) >= 4096:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG contains too many chunks", ProductErrorCategory.DATA_INTEGRITY)
        if offset + 12 > len(raw):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG chunk is truncated", ProductErrorCategory.DATA_INTEGRITY)
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        chunk_type = raw[offset + 4:offset + 8]
        if len(chunk_type) != 4 or not all(
            65 <= byte <= 90 or 97 <= byte <= 122 for byte in chunk_type
        ):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG chunk type is invalid", ProductErrorCategory.DATA_INTEGRITY)
        end = offset + 12 + length
        if end > len(raw):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG chunk length is invalid", ProductErrorCategory.DATA_INTEGRITY)
        data = raw[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", raw[offset + 8 + length:end])[0]
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != crc:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG chunk checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        chunks.append((chunk_type, data))
        offset = end
        if chunk_type == b"IEND":
            break
    if offset != len(raw) or not chunks or chunks[0][0] != b"IHDR" or chunks[-1][0] != b"IEND":
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG structure or trailing bytes are invalid", ProductErrorCategory.DATA_INTEGRITY)
    if sum(kind == b"IHDR" for kind, _ in chunks) != 1 or sum(kind == b"IEND" for kind, _ in chunks) != 1:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG critical chunk count is invalid", ProductErrorCategory.DATA_INTEGRITY)
    if chunks[-1][1] or any(
        kind not in {b"IHDR", b"IDAT", b"IEND"}
        for kind, _data in chunks
    ):
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_METADATA", "PNG metadata or an unknown chunk is forbidden", ProductErrorCategory.DATA_INTEGRITY)
    chunk_types = [kind for kind, _data in chunks]
    idat_indexes = [index for index, kind in enumerate(chunk_types) if kind == b"IDAT"]
    if not idat_indexes or idat_indexes != list(range(idat_indexes[0], idat_indexes[-1] + 1)):
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG image data chunks are not contiguous", ProductErrorCategory.DATA_INTEGRITY)
    ihdr = chunks[0][1]
    if len(ihdr) != 13:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG header is invalid", ProductErrorCategory.DATA_INTEGRITY)
    actual_width, actual_height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if (actual_width, actual_height) != (width, height):
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DIMENSIONS", "Generated image dimensions differ from the authorized request", ProductErrorCategory.DATA_INTEGRITY)
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type)
    valid_depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 4: {8, 16}, 6: {8, 16}}
    if channels is None or bit_depth not in valid_depths[color_type] or compression != 0 or filtering != 0 or interlace != 0:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG encoding is unsupported or invalid", ProductErrorCategory.DATA_INTEGRITY)
    idat = b"".join(data for kind, data in chunks if kind == b"IDAT")
    if not idat:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG image data is missing", ProductErrorCategory.DATA_INTEGRITY)
    row_bytes = (actual_width * channels * bit_depth + 7) // 8
    expected = (row_bytes + 1) * actual_height
    try:
        inflater = zlib.decompressobj()
        decoded = inflater.decompress(idat, expected + 1)
    except zlib.error as exc:
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG image data cannot be decoded", ProductErrorCategory.DATA_INTEGRITY) from exc
    if (
        len(decoded) != expected or not inflater.eof or inflater.unused_data
        or inflater.unconsumed_tail
    ):
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG decoded length is invalid", ProductErrorCategory.DATA_INTEGRITY)
    if any(decoded[index * (row_bytes + 1)] > 4 for index in range(actual_height)):
        raise ProductError("ERR_GENERATION_COMFY_IMAGE_DECODE", "PNG scanline filter is invalid", ProductErrorCategory.DATA_INTEGRITY)
    return raw


class LocalComfyTextToImagePort:
    """Exact local/free FLUX image port; never mints Assets or Candidates."""

    def __init__(self, *, config: LocalComfyImageGenerationConfig, client: ComfyUIClient,
                 resource_policy: ComfyResourcePolicy | None = None,
                 monotonic: Any = time.monotonic, sleeper: Any = time.sleep) -> None:
        if client.endpoint != config.endpoint.rstrip("/"):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_ENDPOINT_DRIFT", "ComfyUI endpoint differs from trusted image configuration", ProductErrorCategory.SECURITY)
        packaged_workflow = default_flux1_schnell_fp8_workflow_path()
        try:
            workflow_matches = config.workflow_path.resolve(strict=True) == packaged_workflow.resolve(strict=True)
        except OSError:
            workflow_matches = False
        if not workflow_matches or config.workflow_sha256 != FLUX1_SCHNELL_FP8_WORKFLOW_SHA256:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_WORKFLOW_BINDING", "Image port requires the package-owned FLUX workflow", ProductErrorCategory.SECURITY)
        self.config = config
        self.client = client
        self.comfy_output_root = _require_directory(config.comfy_output_root, code="ERR_GENERATION_COMFY_IMAGE_OUTPUT_ROOT")
        self.project_output_root = _require_directory(config.project_output_root, code="ERR_GENERATION_COMFY_IMAGE_PROJECT_ROOT")
        self.staging_root = _require_directory(config.staging_root, code="ERR_GENERATION_COMFY_IMAGE_STAGING_ROOT")
        self.dispatch_journal_root = _require_directory(config.dispatch_journal_root, code="ERR_GENERATION_COMFY_IMAGE_JOURNAL_ROOT")
        self.workflow = _load_workflow(config.workflow_path, config.workflow_sha256)
        self.resource_policy = resource_policy or ComfyResourcePolicy(
            min_free_vram_bytes=8 * 1024**3, min_free_ram_bytes=16 * 1024**3,
            min_free_disk_bytes=10 * 1024**3,
        )
        self._monotonic = monotonic
        self._sleeper = sleeper

    def _validate_roots(self) -> None:
        for path, code in (
            (self.comfy_output_root, "ERR_GENERATION_COMFY_IMAGE_OUTPUT_ROOT"),
            (self.project_output_root, "ERR_GENERATION_COMFY_IMAGE_PROJECT_ROOT"),
            (self.staging_root, "ERR_GENERATION_COMFY_IMAGE_STAGING_ROOT"),
            (self.dispatch_journal_root, "ERR_GENERATION_COMFY_IMAGE_JOURNAL_ROOT"),
        ):
            _require_directory(path, code=code)

    def _render(self, prompt: str, seed: int, prefix: str) -> dict[str, Any]:
        return render_workflow_placeholders(self.workflow, {
            "PROMPT": prompt, "SEED": seed, "WIDTH": self.config.width,
            "HEIGHT": self.config.height, "STEPS": self.config.steps,
            "OUTPUT_PREFIX": prefix,
        })

    def _authorize_runtime(self, stats: dict[str, Any]) -> None:
        system = stats.get("system")
        argv = system.get("argv") if isinstance(system, dict) else None
        if not isinstance(argv, list) or not argv or any(not isinstance(item, str) for item in argv):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_RUNTIME_IDENTITY", "ComfyUI launch identity is unavailable", ProductErrorCategory.AUTHORIZATION)
        present = sorted(item for item in argv if any(item == flag or item.startswith(f"{flag}=") for flag in _PROHIBITED_RUNTIME_FLAGS))
        if present:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_RUNTIME_UNSAFE", "ComfyUI launch mode is outside the image boundary", ProductErrorCategory.RESOURCE_EXHAUSTED, details={"prohibited_flags": present})
        for required_flag in ("--disable-auto-launch", "--disable-metadata"):
            if required_flag not in argv:
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_RUNTIME_IDENTITY", "ComfyUI image runtime is missing a privacy/safety flag", ProductErrorCategory.AUTHORIZATION, details={"flag": required_flag})

        def exact_flag(name: str) -> str:
            indexes = [index for index, value in enumerate(argv) if value == name]
            if len(indexes) != 1 or indexes[0] + 1 >= len(argv):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_RUNTIME_IDENTITY", "ComfyUI launch flag is missing or ambiguous", ProductErrorCategory.AUTHORIZATION, details={"flag": name})
            return argv[indexes[0] + 1]

        parsed = urlparse(self.config.endpoint)
        if exact_flag("--listen") != "127.0.0.1" or exact_flag("--port") != str(parsed.port):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_RUNTIME_ENDPOINT", "ComfyUI runtime endpoint differs", ProductErrorCategory.SECURITY)
        try:
            matches = Path(exact_flag("--output-directory")).resolve(strict=True) == self.comfy_output_root
        except OSError:
            matches = False
        if not matches:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_RUNTIME_OUTPUT", "ComfyUI runtime output root differs", ProductErrorCategory.SECURITY)

    def _inspect_runtime(self, workflow: dict[str, Any]) -> None:
        self._validate_roots()
        object_info = self.client.object_info()
        assert_workflow_supported(workflow, object_info)
        assert_workflow_inputs_available(workflow, object_info)
        stats = self.client.system_stats()
        admit_comfy_resources(stats, self.resource_policy, staging_root=self.staging_root)
        self._authorize_runtime(stats)

    def preflight(self) -> LocalGenerationRuntimeReadiness:
        workflow = self._render(_PREFLIGHT_PROMPT, 0, "bai-task013-image-preflight/no-dispatch")
        self._inspect_runtime(workflow)
        return LocalGenerationRuntimeReadiness(
            self.config.route_id, self.config.provider_id, self.config.model_id,
            self.config.workflow_sha256, len(_REQUIRED_CLASSES), _RUNTIME_POLICY,
        )

    def _authorize(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> None:
        exact = (
            route.route_id == self.config.route_id and route.provider_id == self.config.provider_id
            and route.model_id == self.config.model_id and route.workload is AiWorkload.IMAGE
            and route.provider_family is ProviderFamily.COMFYUI
            and route.cost_class is CostClass.LOCAL_FREE_AI and route.credential_ref is None
            and route.endpoint_ref is None and not route.settings and route.enabled
            and route.capabilities == ("TEXT_TO_IMAGE",)
            and request.capability == "TEXT_TO_IMAGE" and not request.input_bindings
        )
        if not exact:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_ROUTE", "Route is not the exact local/free FLUX T2I target", ProductErrorCategory.AUTHORIZATION)
        try:
            encoded = request.prompt_text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_PROMPT", "Image Prompt is not valid UTF-8", ProductErrorCategory.VALIDATION) from exc
        if sha256_bytes(encoded) != request.prompt_sha256:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_PROMPT_CHECKSUM", "Image Prompt differs from authorized Evidence", ProductErrorCategory.DATA_INTEGRITY)

    def _journal_path(self, execution_id: str) -> Path:
        if not _ID_RE.fullmatch(execution_id):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_EXECUTION_ID", "Image execution identity is invalid", ProductErrorCategory.VALIDATION)
        return self.dispatch_journal_root / f"{execution_id}.json"

    @staticmethod
    def _validate_journal(value: Any) -> None:
        fields = {
            "journal_version", "task_owner", "media_kind", "execution_id",
            "queue_entry_id", "route_id", "provider_id", "model_id", "capability",
            "workflow_sha256", "prompt_sha256", "state", "prompt_id", "output_ref",
            "output_sha256", "journal_sha256",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal fields are invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("journal_version") != "1.0.0" or value.get("task_owner") != "TASK-013" or value.get("media_kind") != "IMAGE":
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal identity is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if value.get("journal_sha256") != _with_hash(value)["journal_sha256"]:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL_CHECKSUM", "Image journal checksum mismatch", ProductErrorCategory.DATA_INTEGRITY)
        for name in ("execution_id", "queue_entry_id", "route_id", "provider_id", "model_id", "capability"):
            if not isinstance(value.get(name), str) or not _ID_RE.fullmatch(value[name]):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal identifier is invalid", ProductErrorCategory.DATA_INTEGRITY, details={"field": name})
        for name in ("workflow_sha256", "prompt_sha256"):
            if not isinstance(value.get(name), str) or not _SHA_RE.fullmatch(value[name]):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal hash is invalid", ProductErrorCategory.DATA_INTEGRITY, details={"field": name})
        state = value.get("state")
        if state not in {"PREPARED", "QUEUED", "COMPLETED", "FAILED"}:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal state is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if state == "PREPARED" and any(value.get(name) is not None for name in ("prompt_id", "output_ref", "output_sha256")):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Prepared image journal contains dispatch identity", ProductErrorCategory.DATA_INTEGRITY)
        if state in {"QUEUED", "FAILED"} and (not isinstance(value.get("prompt_id"), str) or not _ID_RE.fullmatch(value["prompt_id"]) or value.get("output_ref") is not None or value.get("output_sha256") is not None):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Queued/failed image journal is invalid", ProductErrorCategory.DATA_INTEGRITY)
        if state == "COMPLETED":
            expected_ref = f"project-output://generated/{value['execution_id']}/result.png"
            if (
                not isinstance(value.get("prompt_id"), str)
                or not _ID_RE.fullmatch(value["prompt_id"])
                or value.get("output_ref") != expected_ref
                or not _SHA_RE.fullmatch(value.get("output_sha256", ""))
            ):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Completed image journal is invalid", ProductErrorCategory.DATA_INTEGRITY)

    def _load_journal(self, path: Path) -> dict[str, Any]:
        try:
            with _exclusive_snapshot_lock(path):
                with _PinnedDirectory(self.dispatch_journal_root) as journal_dir:
                    raw = journal_dir.read(path.name, max_bytes=1024 * 1024)
                    value = json.loads(raw.decode("utf-8"))
                    self._validate_journal(value)
                    temporary_name = f".{path.name}.tmp"
                    if value["state"] == "PREPARED" and journal_dir.child_exists(temporary_name):
                        pending_raw = journal_dir.read(temporary_name, max_bytes=1024 * 1024)
                        pending = json.loads(pending_raw.decode("utf-8"))
                        self._validate_journal(pending)
                        unchanged = set(value) - {"state", "prompt_id", "journal_sha256"}
                        if (
                            pending["state"] != "QUEUED"
                            or any(pending[name] != value[name] for name in unchanged)
                            or not isinstance(pending["prompt_id"], str)
                            or not _ID_RE.fullmatch(pending["prompt_id"])
                        ):
                            raise ProductError("ERR_GENERATION_COMFY_IMAGE_TEMP_CONFLICT", "Residual image journal is not the exact queued transition", ProductErrorCategory.DATA_INTEGRITY)
                        journal_dir.write_atomic(temporary_name, path.name, canonical_json_bytes(pending))
                        journal_dir.assert_current()
                        value = pending
        except ProductError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
        return value

    def _write_journal(self, directory: _PinnedDirectory, path: Path,
                       value: dict[str, Any]) -> None:
        self._validate_journal(value)
        directory.write_atomic(f".{path.name}.tmp", path.name, canonical_json_bytes(value))
        directory.assert_current()

    def _reserve(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> tuple[Path, dict[str, Any]]:
        self._validate_roots()
        path = self._journal_path(request.execution_id)
        try:
            with _PinnedDirectory(self.comfy_output_root) as output_dir:
                output_dir.mkdir("bai-task013-image", exist_ok=True)
                with output_dir.pin_child("bai-task013-image") as owned_dir:
                    if owned_dir.child_exists(request.execution_id):
                        raise ProductError("ERR_GENERATION_COMFY_IMAGE_OUTPUT_EXISTS", "Image execution output prefix already exists", ProductErrorCategory.STATE)
        except ProductError:
            raise
        except OSError as exc:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_OUTPUT_ESCAPE", "Image output root is unsafe", ProductErrorCategory.SECURITY) from exc
        with _exclusive_snapshot_lock(path):
            if path.exists() or path.is_symlink():
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_ALREADY_DISPATCHED", "Image execution already has a journal", ProductErrorCategory.STATE)
            value = _with_hash({
                "journal_version": "1.0.0", "task_owner": "TASK-013", "media_kind": "IMAGE",
                "execution_id": request.execution_id, "queue_entry_id": request.queue_entry_id,
                "route_id": route.route_id, "provider_id": route.provider_id,
                "model_id": route.model_id, "capability": request.capability,
                "workflow_sha256": self.config.workflow_sha256,
                "prompt_sha256": request.prompt_sha256, "state": "PREPARED",
                "prompt_id": None, "output_ref": None, "output_sha256": None,
            })
            with _PinnedDirectory(self.dispatch_journal_root) as journal_dir:
                self._write_journal(journal_dir, path, value)
        return path, value

    def _advance(self, path: Path, expected: dict[str, Any], *, state: str,
                 prompt_id: str, output_ref: str | None = None,
                 output_sha256: str | None = None) -> dict[str, Any]:
        with _exclusive_snapshot_lock(path):
            with _PinnedDirectory(self.dispatch_journal_root) as journal_dir:
                raw = journal_dir.read(path.name, max_bytes=1024 * 1024)
                try:
                    current = json.loads(raw.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL", "Image journal is unreadable", ProductErrorCategory.DATA_INTEGRITY) from exc
                self._validate_journal(current)
                if current != expected:
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL_CONFLICT", "Image journal changed concurrently", ProductErrorCategory.STATE)
                allowed = {"PREPARED": {"QUEUED", "FAILED"}, "QUEUED": {"COMPLETED", "FAILED"}}
                if state not in allowed.get(current["state"], set()):
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_JOURNAL_TRANSITION", "Image journal transition is invalid", ProductErrorCategory.STATE)
                updated = dict(current)
                updated.update({"state": state, "prompt_id": prompt_id, "output_ref": output_ref, "output_sha256": output_sha256})
                updated = _with_hash(updated)
                self._write_journal(journal_dir, path, updated)
                return updated

    @staticmethod
    def _uncertain(code: str, message: str, *, prompt_id: str | None = None) -> ProductError:
        details: dict[str, Any] = {"execution_state_uncertain": True, "automatic_retry_allowed": False}
        if prompt_id is not None:
            details["provider_operation_id"] = prompt_id
        return ProductError(code, message, ProductErrorCategory.STATE, retryable=False, details=details)

    def _publish(self, source_raw: bytes, execution_id: str) -> tuple[str, str]:
        self._validate_roots()
        _probe_png(raw=source_raw, width=self.config.width, height=self.config.height, max_bytes=self.config.max_output_bytes)
        source_sha = sha256_bytes(source_raw)
        relative = PurePosixPath("generated") / execution_id / "result.png"
        try:
            with _PinnedDirectory(self.project_output_root) as project_dir:
                project_dir.mkdir("generated", exist_ok=True)
                with project_dir.pin_child("generated") as generated_dir:
                    generated_dir.mkdir(execution_id, exist_ok=True)
                    with generated_dir.pin_child(execution_id) as operation_dir:
                        if operation_dir.child_exists("result.png"):
                            existing_raw = operation_dir.read("result.png", max_bytes=self.config.max_output_bytes)
                            _probe_png(raw=existing_raw, width=self.config.width, height=self.config.height, max_bytes=self.config.max_output_bytes)
                            existing_sha = sha256_bytes(existing_raw)
                            if existing_sha != source_sha:
                                raise ProductError("ERR_GENERATION_COMFY_IMAGE_PROJECT_EXISTS", "Canonical image target differs from recovered output", ProductErrorCategory.STATE)
                            return f"project-output://{relative.as_posix()}", existing_sha
                        operation_dir.write_atomic(".result.png.tmp", "result.png", source_raw)
                        target_raw = operation_dir.read("result.png", max_bytes=self.config.max_output_bytes)
                        _probe_png(raw=target_raw, width=self.config.width, height=self.config.height, max_bytes=self.config.max_output_bytes)
                        operation_dir.assert_current()
        except ProductError:
            raise
        except OSError as exc:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_PROJECT_WRITE", "Canonical image could not be written", ProductErrorCategory.DATA_INTEGRITY) from exc
        target_sha = sha256_bytes(target_raw)
        if target_sha != source_sha:
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_PROJECT_CHECKSUM", "Canonical image changed after publication", ProductErrorCategory.DATA_INTEGRITY)
        return f"project-output://{relative.as_posix()}", target_sha

    def _fail_output(
        self,
        path: Path,
        journal: dict[str, Any],
        prompt_id: str,
        error: ProductError,
    ) -> None:
        try:
            self._advance(path, journal, state="FAILED", prompt_id=prompt_id)
        except ProductError as exc:
            raise self._uncertain(
                "ERR_GENERATION_COMFY_IMAGE_FAILURE_JOURNAL_UNCERTAIN",
                "Failed image output could not be durably reconciled",
                prompt_id=prompt_id,
            ) from exc
        error.details = {**error.details, "execution_state_terminal_failure": True}
        raise error

    def _complete(self, path: Path, journal: dict[str, Any], prompt_id: str,
                  entry: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
        images = _image_descriptors(entry)
        if len(images) != 1:
            self._fail_output(
                path,
                journal,
                prompt_id,
                ProductError(
                    "ERR_GENERATION_COMFY_IMAGE_OUTPUT_AMBIGUOUS",
                    "ComfyUI did not return exactly one image",
                    ProductErrorCategory.HUMAN_REVIEW_REQUIRED,
                    details={"image_count": len(images)},
                ),
            )
        try:
            descriptor = images[0]
            expected_subfolder = f"bai-task013-image/{journal['execution_id']}"
            if (
                descriptor.get("subfolder", "").replace("\\", "/") != expected_subfolder
                or not isinstance(descriptor.get("filename"), str)
                or not descriptor["filename"].startswith("result")
            ):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_OUTPUT_IDENTITY", "Image descriptor differs from the execution prefix", ProductErrorCategory.SECURITY)
            with _PinnedDirectory(self.comfy_output_root) as output_dir:
                with output_dir.pin_child("bai-task013-image") as owned_dir:
                    with owned_dir.pin_child(journal["execution_id"]) as execution_dir:
                        source_raw = execution_dir.read(descriptor["filename"], max_bytes=self.config.max_output_bytes)
                        execution_dir.assert_current()
                        if Path(descriptor["filename"]).suffix.lower() != ".png":
                            raise ProductError("ERR_GENERATION_COMFY_IMAGE_SUFFIX", "FLUX output must be PNG", ProductErrorCategory.DATA_INTEGRITY)
                        output_ref, output_sha = self._publish(source_raw, journal["execution_id"])
        except (FileNotFoundError, ValueError) as exc:
            error = ProductError(
                "ERR_GENERATION_COMFY_IMAGE_OUTPUT_IDENTITY",
                "Image output is outside its execution prefix",
                ProductErrorCategory.SECURITY,
            )
            try:
                self._fail_output(path, journal, prompt_id, error)
            except ProductError as terminal:
                raise terminal from exc
        except ProductError as exc:
            self._fail_output(path, journal, prompt_id, exc)
        try:
            completed = self._advance(path, journal, state="COMPLETED", prompt_id=prompt_id, output_ref=output_ref, output_sha256=output_sha)
        except ProductError as exc:
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_COMPLETION_JOURNAL_UNCERTAIN", "Completed image output could not be durably reconciled", prompt_id=prompt_id) from exc
        return completed, output_ref, output_sha

    def _wait(self, path: Path, journal: dict[str, Any], prompt_id: str) -> tuple[dict[str, Any], str, str]:
        deadline = self._monotonic() + self.config.completion_timeout_seconds
        while self._monotonic() < deadline:
            try:
                entry = _history_entry(self.client.history(prompt_id), prompt_id)
            except ProductError as exc:
                raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_HISTORY_UNCERTAIN", "ComfyUI image history is unavailable", prompt_id=prompt_id) from exc
            if entry is not None:
                status = entry.get("status")
                if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
                    self._advance(path, journal, state="FAILED", prompt_id=prompt_id)
                    raise ProductError("ERR_GENERATION_COMFY_IMAGE_EXECUTION_FAILED", "ComfyUI reported image generation failure", ProductErrorCategory.EXTERNAL_DEPENDENCY)
                if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"success", "completed"}:
                    return self._complete(path, journal, prompt_id, entry)
            self._sleeper(self.config.poll_interval_seconds)
        raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_TIMEOUT_UNCERTAIN", "ComfyUI image generation timed out", prompt_id=prompt_id)

    def execute(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> LocalGenerationExecutionResult:
        self._authorize(route, request)
        workflow = self._render(request.prompt_text, int(request.prompt_sha256[-16:], 16) & (2**63 - 1), f"bai-task013-image/{request.execution_id}/result")
        self._inspect_runtime(workflow)
        path, journal = self._reserve(route, request)
        started = self._monotonic()
        try:
            prompt_id = self.client.queue(workflow, client_id=request.execution_id)
        except ProductError as exc:
            if exc.code == "ERR_PROVIDER_COMFY_HTTP" and isinstance(exc.details.get("status"), int) and exc.details["status"] < 500:
                self._advance(path, journal, state="FAILED", prompt_id="REQUEST_REJECTED")
                raise
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_DISPATCH_UNCERTAIN", "ComfyUI image dispatch is uncertain") from exc
        if not isinstance(prompt_id, str) or not _ID_RE.fullmatch(prompt_id):
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_PROMPT_ID", "ComfyUI returned an unsafe image prompt identity")
        try:
            journal = self._advance(path, journal, state="QUEUED", prompt_id=prompt_id)
        except ProductError as exc:
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_QUEUE_JOURNAL_UNCERTAIN", "Queued image prompt could not be durably recorded", prompt_id=prompt_id) from exc
        _completed, output_ref, output_sha = self._wait(path, journal, prompt_id)
        latency_ms = max(0, int((self._monotonic() - started) * 1000))
        return LocalGenerationExecutionResult(
            route.route_id, route.provider_family, route.provider_id, route.model_id,
            request.capability, prompt_id, output_ref, output_sha, "IMAGE", latency_ms,
        )

    def recover(self, route: ModelRoute, request: LocalGenerationExecutionRequest) -> LocalGenerationExecutionResult:
        """Reconcile one stored prompt only; this method never queues Provider work."""
        self._authorize(route, request)
        self._validate_roots()
        path = self._journal_path(request.execution_id)
        journal = self._load_journal(path)
        expected = {
            "execution_id": request.execution_id, "queue_entry_id": request.queue_entry_id,
            "route_id": route.route_id, "provider_id": route.provider_id,
            "model_id": route.model_id, "capability": request.capability,
            "workflow_sha256": self.config.workflow_sha256,
            "prompt_sha256": request.prompt_sha256,
        }
        if any(journal[name] != value for name, value in expected.items()):
            raise ProductError("ERR_GENERATION_COMFY_IMAGE_RECOVERY_IDENTITY", "Image recovery identity differs from the journal", ProductErrorCategory.AUTHORIZATION)
        if journal["state"] == "PREPARED":
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_RECOVERY_PROMPT_UNKNOWN", "Image dispatch prompt identity was not durably recorded")
        if journal["state"] == "FAILED":
            raise ProductError(
                "ERR_GENERATION_COMFY_IMAGE_RECOVERY_FAILED",
                "Image execution is already terminal failed",
                ProductErrorCategory.STATE,
                details={"execution_state_terminal_failure": True},
            )
        if journal["state"] == "COMPLETED":
            prefix = "project-output://"
            ref = journal["output_ref"]
            if not isinstance(ref, str) or not ref.startswith(prefix):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_RECOVERY_OUTPUT", "Completed image output reference is invalid", ProductErrorCategory.DATA_INTEGRITY)
            relative = PurePosixPath(ref[len(prefix):])
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_RECOVERY_OUTPUT", "Completed image output path is unsafe", ProductErrorCategory.SECURITY)
            with _PinnedDirectory(self.project_output_root) as project_dir:
                with project_dir.pin_child("generated") as generated_dir:
                    with generated_dir.pin_child(request.execution_id) as operation_dir:
                        target_raw = operation_dir.read("result.png", max_bytes=self.config.max_output_bytes)
            _probe_png(raw=target_raw, width=self.config.width, height=self.config.height, max_bytes=self.config.max_output_bytes)
            if sha256_bytes(target_raw) != journal["output_sha256"]:
                raise ProductError("ERR_GENERATION_COMFY_IMAGE_RECOVERY_OUTPUT", "Completed image output checksum changed", ProductErrorCategory.DATA_INTEGRITY)
            return LocalGenerationExecutionResult(route.route_id, route.provider_family, route.provider_id, route.model_id, request.capability, journal["prompt_id"], ref, journal["output_sha256"], "IMAGE")
        self._inspect_runtime(self._render(_PREFLIGHT_PROMPT, 0, "bai-task013-image-preflight/no-dispatch"))
        prompt_id = journal["prompt_id"]
        try:
            entry = _history_entry(self.client.history(prompt_id), prompt_id)
        except ProductError as exc:
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_HISTORY_UNCERTAIN", "ComfyUI image history is unavailable", prompt_id=prompt_id) from exc
        if entry is None:
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_RECOVERY_PENDING", "Stored image prompt has no terminal history", prompt_id=prompt_id)
        status = entry.get("status")
        if isinstance(status, dict) and str(status.get("status_str", "")).lower() in {"error", "failed"}:
            self._advance(path, journal, state="FAILED", prompt_id=prompt_id)
            raise ProductError(
                "ERR_GENERATION_COMFY_IMAGE_EXECUTION_FAILED",
                "ComfyUI reported image generation failure",
                ProductErrorCategory.EXTERNAL_DEPENDENCY,
                details={"execution_state_terminal_failure": True},
            )
        if not (
            isinstance(status, dict)
            and str(status.get("status_str", "")).lower() in {"success", "completed"}
        ):
            raise self._uncertain("ERR_GENERATION_COMFY_IMAGE_RECOVERY_PENDING", "Stored image prompt is not complete", prompt_id=prompt_id)
        _completed, output_ref, output_sha = self._complete(path, journal, prompt_id, entry)
        return LocalGenerationExecutionResult(route.route_id, route.provider_family, route.provider_id, route.model_id, request.capability, prompt_id, output_ref, output_sha, "IMAGE")


__all__ = [
    "FLUX1_SCHNELL_FP8_WORKFLOW_SHA256", "LocalComfyImageGenerationConfig",
    "LocalComfyTextToImagePort", "default_flux1_schnell_fp8_workflow_path",
]
