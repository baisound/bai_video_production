import json
import pytest
from ai_video_production.atomic import AtomicJsonWriter

def test_atomic_write_replaces_only_after_validation(tmp_path):
    target = tmp_path / "manifest.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    def fail(stage, _tmp):
        if stage == "before_replace": raise RuntimeError("fault")
    with pytest.raises(RuntimeError):
        AtomicJsonWriter.write(target, {"new": True}, failure_injector=fail)
    assert json.loads(target.read_text()) == {"old": True}
    assert not list(tmp_path.glob("*.tmp"))

def test_atomic_write_success(tmp_path):
    target = tmp_path / "manifest.json"
    result = AtomicJsonWriter.write(target, {"b":2,"a":1})
    assert json.loads(target.read_text()) == {"a":1,"b":2}
    assert result.checksum.startswith("sha256:")
