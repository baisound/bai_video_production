from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
STUDIO=ROOT/"src"/"ai_video_production"/"dbd_training_studio.py"
EXPECTED_CANONICAL_TEXT_SHA256 = "3c5b45b2d11dfef550797bae8057dde08129deba2286c626a244d9e13759f44f"


def test_r7_training_studio_gate_uses_current_accepted_source():
    assert STUDIO.is_file()
    # The accepted-source gate is content-exact while remaining portable across
    # Git's LF/CRLF checkout policy. Python universal-newline text reading
    # canonicalizes platform EOLs to LF before hashing.
    canonical = STUDIO.read_text(encoding="utf-8").encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest()==EXPECTED_CANONICAL_TEXT_SHA256
