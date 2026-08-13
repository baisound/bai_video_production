from __future__ import annotations

from pathlib import Path
import wave

import pytest

from ai_video_production.cut_candidates import CutCandidate, CutCandidateKind, CutCandidateManifest
from ai_video_production.edit_plan import CandidateReviewDecision, EditDecision, EditPlanService
from ai_video_production.errors import ProductError
from ai_video_production.manual_handoff import EditorHandoffService
from ai_video_production.media_probe import MediaProbeResult
from ai_video_production.render_qa import RenderQAReport
from ai_video_production.resolve_assembly import ResolveAssemblyResult
from ai_video_production.task012_native_handoff_gate import Task012NativeHandoffGate, Task012NativeHandoffRequest
from ai_video_production.timebase import FrameRate


ASSET_ID = "ASSET-00000000000000000000000000"
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def approved_plan():
    manifest = CutCandidateManifest(
        ASSET_ID,
        SHA_A,
        48000,
        3_000_000,
        SHA_B,
        None,
        (CutCandidate("cut-000001", CutCandidateKind.SILENCE, 1_000_000, 1_500_000, 90, ("FFMPEG_SILENCEDETECT",)),),
        (),
    )
    return EditPlanService.build(
        manifest,
        reviews=(CandidateReviewDecision("cut-000001", EditDecision.KEEP),),
        approve=True,
        approved_by="owner",
    )


def qa_for(path: Path) -> RenderQAReport:
    import hashlib

    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    probe = MediaProbeResult("mp4", 3_000_000, path.stat().st_size, None, ({"codec_type": "video"}, {"codec_type": "audio"}))
    return RenderQAReport(
        digest,
        path.stat().st_size,
        probe,
        None,
        None,
        90,
        FrameRate(30),
        2,
        ({"check": "NON_EMPTY_ARTIFACT", "status": "PASS"},),
    )


def write_wav(path: Path, *, rate=48000, seconds=3):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x00\x00\x00\x00" * rate * seconds)


def prepare(tmp_path: Path, *, roundtrip=True):
    render = tmp_path / "master.mp4"
    render.write_bytes(b"master-render")
    exports = ()
    if roundtrip:
        audio = tmp_path / "mix-export.wav"
        write_wav(audio)
        exports = (audio,)
    root, manifest = EditorHandoffService.prepare(
        tmp_path / "handoff",
        edit_plan=approved_plan(),
        assembly_result=ResolveAssemblyResult(
            "sha256:" + "c" * 64,
            "BAI_AUTO_TEST",
            "APPLIED",
            False,
            "IMPORTED",
            "NOT_REQUESTED",
        ),
        render_qa=qa_for(render),
        render_path=render,
        audio_roundtrip_exports=exports,
    )
    return root, manifest


def test_task012_native_gate_passes_editor_work_before_optional_cubase_return(tmp_path: Path):
    root, _ = prepare(tmp_path)
    report = Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert report["status"] == "PASS"
    assert report["cubase_roundtrip"]["status"] == "NOT_PRESENT"
    assert report["editor_work_root_persisted"] is False
    assert {"EDIT_PLAN", "RESOLVE_ASSEMBLY_REPORT", "RENDER_QA", "RENDER_MASTER"}.issubset(report["verified_roles"])


def test_task012_native_gate_requires_real_cubase_return_for_final_native_close(tmp_path: Path):
    root, _ = prepare(tmp_path)
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root, require_cubase_return=True)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_CUBASE_RETURN_REQUIRED"


def test_task012_native_gate_passes_registered_48k_cubase_return(tmp_path: Path):
    root, _ = prepare(tmp_path)
    returned = tmp_path / "cubase-return.wav"
    write_wav(returned)
    EditorHandoffService.register_cubase_return(root, returned, expected_duration_us=3_000_000)
    report = Task012NativeHandoffGate(
        Task012NativeHandoffRequest(root, require_cubase_return=True)
    ).run(output_path=tmp_path / "report.json")
    assert report["cubase_roundtrip"]["status"] == "PASS"
    assert report["cubase_roundtrip"]["sample_rate"] == 48000
    assert report["cubase_roundtrip"]["path_persisted"] is False


def test_task012_native_gate_detects_changed_manifested_file(tmp_path: Path):
    root, _ = prepare(tmp_path)
    (root / "RENDER" / "master.mp4").write_bytes(b"tampered")
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_HANDOFF_FILE_CHANGED"


def test_task012_native_gate_detects_upstream_identity_mismatch(tmp_path: Path):
    root, _ = prepare(tmp_path)
    path = root / "MANIFESTS" / "render-qa.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"report_sha256":"sha256:', '"report_sha256":"sha256:0'), encoding="utf-8")
    # The manifested checksum catches the mutation before cross-linking; both are valid fail-closed outcomes.
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_HANDOFF_FILE_CHANGED"


def test_task012_native_gate_rejects_absolute_path_contract(tmp_path: Path):
    root, _ = prepare(tmp_path)
    manifest_path = root / "editor-handoff-manifest.json"
    import json

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["absolute_paths_persisted"] = True
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_MANIFEST_HASH"


def test_task012_native_gate_rejects_cubase_return_when_roundtrip_not_enabled(tmp_path: Path):
    root, _ = prepare(tmp_path, roundtrip=False)
    return_dir = root / "AUDIO_ROUNDTRIP" / "RETURN"
    write_wav(return_dir / "cubase-return.wav")
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_CUBASE_RETURN_UNEXPECTED"


def _rewrite_manifest_with_valid_hash(path: Path, mutate):
    import json
    from ai_video_production.serialization import canonical_json_bytes, sha256_bytes

    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    payload.pop("manifest_sha256", None)
    payload["manifest_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def test_task012_native_gate_requires_unique_required_manifest_role(tmp_path: Path):
    import hashlib
    import json

    root, _ = prepare(tmp_path)
    manifest_path = root / "editor-handoff-manifest.json"
    duplicate = root / "MANIFESTS" / "edit-plan-copy.json"
    duplicate.write_bytes((root / "MANIFESTS" / "edit-plan.json").read_bytes())

    def mutate(payload):
        payload["files"].append({
            "role": "EDIT_PLAN",
            "relative_path": "MANIFESTS/edit-plan-copy.json",
            "sha256": "sha256:" + hashlib.sha256(duplicate.read_bytes()).hexdigest(),
            "size_bytes": duplicate.stat().st_size,
        })

    _rewrite_manifest_with_valid_hash(manifest_path, mutate)
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_REQUIRED_FILE_ROLE_AMBIGUOUS"


def test_task012_native_gate_requires_canonical_path_for_upstream_role(tmp_path: Path):
    import hashlib

    root, _ = prepare(tmp_path)
    manifest_path = root / "editor-handoff-manifest.json"
    alternate = root / "MANIFESTS" / "alternate-edit-plan.json"
    alternate.write_bytes((root / "MANIFESTS" / "edit-plan.json").read_bytes())

    def mutate(payload):
        record = next(item for item in payload["files"] if item["role"] == "EDIT_PLAN")
        record["relative_path"] = "MANIFESTS/alternate-edit-plan.json"
        record["sha256"] = "sha256:" + hashlib.sha256(alternate.read_bytes()).hexdigest()
        record["size_bytes"] = alternate.stat().st_size

    _rewrite_manifest_with_valid_hash(manifest_path, mutate)
    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root)).run(output_path=tmp_path / "report.json")
    assert exc.value.code == "ERR_TASK012_NATIVE_REQUIRED_FILE_ROLE_PATH"


def test_task012_native_gate_verifies_cubase_return_record_self_hash(tmp_path: Path):
    import json

    root, _ = prepare(tmp_path)
    returned = tmp_path / "cubase-return.wav"
    write_wav(returned)
    EditorHandoffService.register_cubase_return(root, returned, expected_duration_us=3_000_000)
    record_path = root / "AUDIO_ROUNDTRIP" / "audio-roundtrip-return.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["duration_delta_us"] = 123
    record_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ProductError) as exc:
        Task012NativeHandoffGate(Task012NativeHandoffRequest(root, require_cubase_return=True)).run(
            output_path=tmp_path / "report.json"
        )
    assert exc.value.code == "ERR_TASK012_NATIVE_CUBASE_RETURN_RECORD_HASH"
