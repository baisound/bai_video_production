from pathlib import Path, PureWindowsPath
import pytest
from ai_video_production.paths import LogicalPathResolver, PathMapping, _is_canonically_contained
from ai_video_production.errors import ProductError
from ai_video_production.ids import IdKind, generate_id

def resolver(tmp_path):
    assets = tmp_path / "assets"; jobs = tmp_path / "jobs"; assets.mkdir(); jobs.mkdir()
    return LogicalPathResolver([
        PathMapping("asset://", assets, PureWindowsPath("D:/AI-VIDEO/assets")),
        PathMapping("job://", jobs, PureWindowsPath("D:/AI-VIDEO/jobs")),
    ]), assets

def test_allowlisted_resolution_and_windows_translation(tmp_path):
    r, assets = resolver(tmp_path)
    job=generate_id(IdKind.JOB)
    assert r.resolve(f"asset://{job}/source/a.mp4") == assets / f"{job}/source/a.mp4"
    assert str(r.resolve(f"asset://{job}/source/a.mp4", environment="windows")) == rf"D:\AI-VIDEO\assets\{job}\source\a.mp4"

def test_path_escape_patterns_rejected(tmp_path):
    r, _ = resolver(tmp_path)
    job=generate_id(IdKind.JOB)
    uris=["file://etc/passwd", "asset://../escape", "asset:///abs", r"asset://C:\Windows\x", f"asset://{job}//b", "asset://NOT-A-JOB/source/a"]
    for uri in uris:
        with pytest.raises(ProductError): r.resolve(uri)

def test_existing_symlink_escape_rejected(tmp_path):
    r, assets = resolver(tmp_path)
    outside = tmp_path / "outside"; outside.mkdir()
    job=generate_id(IdKind.JOB)
    (assets / job).mkdir()
    (assets / job / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProductError) as exc:
        r.resolve(f"asset://{job}/link/secret.txt")
    assert exc.value.code == "ERR_SECURITY_PATH_DENIED"

def test_windows_extended_length_prefix_is_same_canonical_root():
    root = Path(r"C:\Users\user\jobs")
    candidate = Path(r"\\?\C:\Users\user\jobs\JOB-01ABCDEFGHJKMNPQRSTVWXYZ0\evidence\ingest.jsonl")
    assert _is_canonically_contained(root, candidate, os_name="nt")

def test_windows_extended_length_prefix_does_not_relax_containment():
    root = Path(r"C:\Users\user\jobs")
    candidate = Path(r"\\?\C:\Users\user\jobs-escape\file.json")
    assert not _is_canonically_contained(root, candidate, os_name="nt")
