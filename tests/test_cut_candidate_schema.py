from __future__ import annotations
import json
import math
from pathlib import Path
import struct
import wave
import jsonschema
from importlib import resources

from ai_video_production.cut_candidates import CutCandidateAnalyzer, SilenceRange

ASSET_ID = "ASSET-00000000000000000000000000"

class Detector:
    def detect(self, source, *, duration_us, config):
        return (SilenceRange(200_000, 1_500_000),)

def test_manifest_validates_against_schema(tmp_path: Path):
    audio=tmp_path/"a.wav"
    with wave.open(str(audio),"wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000)
        out.writeframes(b"\x01\x00"*32000)
    manifest=CutCandidateAnalyzer.analyze(audio,source_asset_id=ASSET_ID,detector=Detector())
    schema=json.loads((Path(__file__).parents[1]/"schemas"/"cut-candidate-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(manifest.to_dict())


def test_packaged_schema_matches_canonical():
    name = "cut-candidate-manifest.schema.json"
    canonical = (Path(__file__).parents[1] / "schemas" / name).read_text(encoding="utf-8")
    packaged = resources.files("ai_video_production").joinpath("schema_resources", name).read_text(encoding="utf-8")
    assert canonical == packaged
