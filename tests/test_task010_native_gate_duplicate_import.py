from __future__ import annotations

from pathlib import Path

from ai_video_production.task010_native_gate import Task010NativeGateRunner


class Clip:
    def __init__(self, path: str):
        self.path = path

    def GetClipProperty(self, key):
        assert key == "File Path"
        return self.path


class Folder:
    def __init__(self, *, clips=(), subfolders=()):
        self.clips = list(clips)
        self.subfolders = list(subfolders)

    def GetClipList(self):
        return self.clips

    def GetSubFolderList(self):
        return self.subfolders


class MediaPool:
    def __init__(self, root):
        self.root = root

    def GetRootFolder(self):
        return self.root


def test_duplicate_import_fallback_finds_existing_media_pool_item(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    wanted = Clip(str(source.resolve()))
    media_pool = MediaPool(Folder(subfolders=[Folder(clips=[wanted])]))

    observed = Task010NativeGateRunner._find_media_pool_item_by_path(media_pool, source)

    assert observed is wanted


def test_duplicate_import_fallback_returns_none_when_source_is_absent(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    other = tmp_path / "other.mp4"
    other.write_bytes(b"fixture")
    media_pool = MediaPool(Folder(clips=[Clip(str(other.resolve()))]))

    observed = Task010NativeGateRunner._find_media_pool_item_by_path(media_pool, source)

    assert observed is None
