from __future__ import annotations

import json
import struct
import subprocess
import zlib
from pathlib import Path, PureWindowsPath

import pytest

from ai_video_production import (
    AssetType,
    AudioRightsStatus,
    ComfyResourcePolicy,
    DerivedAssetPublisher,
    DerivedAssetSpec,
    H3FoleyMode,
    H3FoleyRequest,
    H3FoleyService,
    H3ProductionBriefBuilder,
    H3ReferenceBinding,
    H3ReferenceKind,
    H3ReferenceRole,
    H3Shot,
    H3SingleFrameContract,
    H3SingleFrameMode,
    H3SingleFrameRequest,
    H3SingleFrameService,
    H3VisibleRetention,
    IdKind,
    generate_id,
    LogicalPathResolver,
    PathMapping,
    PermissionState,
    ProductError,
    ProfileSnapshot,
    RightsStatus,
    SQLiteProductStore,
    SourcePathPolicy,
)


def write_test_png(path: Path) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = bytes((0, 0, 0, 0, 255))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(raw))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


def make_video_with_audio(path: Path, *, duration: float = 0.5) -> None:
    subprocess.run([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s=32x32:r=24:d={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}",
        "-c:v", "mpeg4", "-c:a", "aac", "-shortest", "-y", str(path),
    ], check=True)


def make_wav(path: Path, *, duration: float = 0.25) -> None:
    subprocess.run([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:duration={duration}",
        "-c:a", "pcm_s16le", "-y", str(path),
    ], check=True)


def roots(tmp_path: Path):
    asset_root = tmp_path / "assets"
    job_root = tmp_path / "jobs"
    workflows = tmp_path / "workflows"
    output = tmp_path / "comfy-output"
    inp = tmp_path / "comfy-input"
    stage = tmp_path / "stage"
    for p in (asset_root, job_root, workflows, output, inp, stage):
        p.mkdir()
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    job = store.create_job(ProfileSnapshot.create("task004-h3", "1.0.0", {}).profile_snapshot_id)
    resolver = LogicalPathResolver([
        PathMapping("asset://", asset_root, PureWindowsPath("D:/assets")),
        PathMapping("job://", job_root, PureWindowsPath("D:/jobs")),
    ])
    return store, job, resolver, workflows, output, inp, stage


def canonical_asset(store, resolver, job, path: Path, asset_type: AssetType):
    op = store.reserve_operation(job.job_id, "TEST_H3_REFERENCE", f"ref-{path.name}")[0]
    return DerivedAssetPublisher(store=store, resolver=resolver).publish(
        path,
        DerivedAssetSpec(
            job.job_id,
            "h3-reference",
            asset_type,
            "USER",
            rights_status=RightsStatus.OWNED,
            commercial_use=PermissionState.ALLOWED,
            derivative_allowed=PermissionState.ALLOWED,
            reuse_allowed=PermissionState.ALLOWED,
            audio_rights_status=AudioRightsStatus.SAFE if asset_type in {AssetType.AUDIO, AssetType.SFX, AssetType.BGM} else AudioRightsStatus.NOT_APPLICABLE,
        ),
        operation_id=op.operation_id,
    )


class FakeSingleFrameClient:
    def __init__(self, output_name: str = "single.png"):
        self.output_name = output_name
        self.queued = 0
        self.workflow = None

    def system_stats(self):
        return {"devices": [{"name": "GPU", "type": "cuda", "vram_free": 16 * 1024**3}]}

    def object_info(self):
        return {
            "MiniMaxH3SingleFrameEdit": {},
            "MiniMaxH3StartEndFrameInterpolate": {},
            "MiniMaxH3SelectFrame": {},
            "MiniMaxH3TemporalRoPEPatch": {},
        }

    def queue(self, workflow, *, client_id):
        self.queued += 1
        self.workflow = workflow
        return "h3-single-prompt"

    def history(self, prompt_id):
        return {prompt_id: {"outputs": {"9": {"images": [{"filename": self.output_name, "type": "output"}]}}}}


class FakeFoleyClient:
    def __init__(self, output_name: str = "foley.mp4"):
        self.output_name = output_name
        self.queued = 0
        self.workflow = None

    def system_stats(self):
        return {"devices": [{"name": "GPU", "type": "cuda", "vram_free": 24 * 1024**3}]}

    def object_info(self):
        return {"MiniMaxNode": {}}

    def queue(self, workflow, *, client_id):
        self.queued += 1
        self.workflow = workflow
        return "h3-foley-prompt"

    def history(self, prompt_id):
        return {prompt_id: {"outputs": {"9": {"videos": [{"filename": self.output_name, "type": "output"}]}}}}


def test_h3_production_brief_preserves_reference_order_and_duration_tier():
    refs = (
        H3ReferenceBinding(generate_id(IdKind.ASSET), H3ReferenceKind.IMAGE, H3ReferenceRole.GENERAL_REFERENCE, "hero face", H3VisibleRetention.FULLY_PRESERVED),
        H3ReferenceBinding(generate_id(IdKind.ASSET), H3ReferenceKind.VIDEO, H3ReferenceRole.GENERAL_REFERENCE, "motion", H3VisibleRetention.ATTRIBUTE_TRANSFER),
    )
    plan = H3ProductionBriefBuilder.build(
        user_intent="A fixed hero opens a door.",
        target_duration_seconds=15,
        target_aspect_ratio="16:9",
        references=refs,
        shots=(H3Shot(1, "Hero waits."), H3Shot(2, "Hero opens the door.", start_ms=5000)),
        overall_soundscape="Indoor room tone and a wooden door sound.",
        non_diegetic_music="N/A",
    )
    assert plan.reference_tags == ("<Picture 1>", "<Video 1>")
    assert plan.duration_tier.value == "STANDARD_1_15"
    assert "fully_preserved" in plan.text
    assert plan.to_dict()["text_sha256"].startswith("sha256:")
    assert "A fixed hero" not in json.dumps(plan.to_dict())


def test_h3_production_brief_marks_16_45_experimental_and_enforces_reference_limits():
    plan = H3ProductionBriefBuilder.build(
        user_intent="Ambient sound study.",
        target_duration_seconds=30,
        target_aspect_ratio="1:1",
        shots=(H3Shot(1, "Static room."),),
    )
    assert plan.duration_tier.value == "EXPERIMENTAL_16_45"
    refs = tuple(H3ReferenceBinding(generate_id(IdKind.ASSET), H3ReferenceKind.IMAGE) for _ in range(10))
    with pytest.raises(ValueError):
        H3ProductionBriefBuilder.build(
            user_intent="x", target_duration_seconds=5, target_aspect_ratio="16:9", references=refs, shots=(H3Shot(1, "x"),)
        )


def test_h3_single_frame_contract_normalizes_sequence():
    assert H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT, 5).actual_frame_count == 5
    assert H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT, 6).actual_frame_count == 22
    assert H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT, 23).actual_frame_count == 39
    with pytest.raises(ProductError):
        H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT, 5, selected_frame_index=5).validate_selected_frame()


def test_h3_single_frame_service_e2e_fake_runtime(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    source = tmp_path / "reference.png"
    write_test_png(source)
    ref = canonical_asset(store, resolver, job, source, AssetType.IMAGE)
    write_test_png(output / "single.png")
    # Avoid byte-dedupe with the canonical reference so output provenance stays on the generated Asset.
    data = bytearray((output / "single.png").read_bytes())
    data[-12] ^= 1
    # Rebuild a valid different PNG instead of relying on mutation.
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    raw = bytes((0, 255, 255, 255, 255))
    payload = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    (output / "single.png").write_bytes(payload)
    workflow = workflows / "single.json"
    workflow.write_text(json.dumps({
        "1": {"class_type": "MiniMaxH3SingleFrameEdit", "inputs": {"image": "{{REFERENCE_1}}", "frames": "{{FRAME_COUNT}}", "prompt": "{{PROMPT}}"}},
        "2": {"class_type": "MiniMaxH3SelectFrame", "inputs": {"frame_index": "{{SELECT_FRAME}}"}},
    }))
    client = FakeSingleFrameClient()
    service = H3SingleFrameService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    req = H3SingleFrameRequest(
        job.job_id, "h3-single", workflow, {}, "Keep the character fixed and close the eyes.", 7,
        H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT, requested_frame_count=6, selected_frame_index=0, temporal_rope_strength=1.0),
        (ref.asset_id,), True, "MINIMAX-H3-LICENSE-ACK", "H3-SINGLEFRAME-LOCAL-USE-ACK", poll_interval_seconds=0.1, completion_timeout_seconds=2,
    )
    first = service.generate(req)
    second = service.generate(req)
    asset = store.get_asset(first.asset_id)
    assert asset.asset_type is AssetType.IMAGE
    assert asset.generation_provenance["contract"]["actual_frame_count"] == 22
    assert client.workflow["1"]["inputs"]["frames"] == 22
    assert first.asset_id == second.asset_id
    assert client.queued == 1


def test_h3_single_frame_requires_license_before_queue(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    source = tmp_path / "reference.png"
    write_test_png(source)
    ref = canonical_asset(store, resolver, job, source, AssetType.IMAGE)
    workflow = workflows / "single.json"
    workflow.write_text(json.dumps({
        "1": {"class_type": "MiniMaxH3SingleFrameEdit", "inputs": {"image": "{{REFERENCE_1}}"}},
        "2": {"class_type": "MiniMaxH3SelectFrame", "inputs": {}},
    }))
    client = FakeSingleFrameClient()
    service = H3SingleFrameService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    with pytest.raises(ProductError) as exc:
        service.generate(H3SingleFrameRequest(
            job.job_id, "no-lic", workflow, {}, "x", 1,
            H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT), (ref.asset_id,), True, None,
        ))
    assert exc.value.code == "ERR_AUTH_H3_SINGLE_FRAME_MODEL_LICENSE"
    assert client.queued == 0


def test_h3_foley_fast32_requires_explicit_experimental_ack(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    workflow = workflows / "foley.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode", "inputs": {"w": "{{WIDTH}}", "h": "{{HEIGHT}}", "prompt": "{{PROMPT}}"}}}))
    client = FakeFoleyClient()
    service = H3FoleyService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    with pytest.raises(ProductError) as exc:
        service.generate(H3FoleyRequest(job.job_id, "foley-no-ack", workflow, {}, "door slam", 1, True, "MINIMAX-H3-LICENSE-ACK"))
    assert exc.value.code == "ERR_AUTH_H3_FOLEY_FAST32_EXPERIMENTAL"
    assert client.queued == 0


def test_h3_foley_e2e_extracts_48k_sfx_and_is_idempotent(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    make_video_with_audio(output / "foley.mp4")
    workflow = workflows / "foley.json"
    workflow.write_text(json.dumps({
        "1": {"class_type": "MiniMaxNode", "inputs": {
            "w": "{{WIDTH}}", "h": "{{HEIGHT}}", "duration": "{{DURATION_SECONDS}}", "prompt": "{{PROMPT}}", "seed": "{{SEED}}"
        }}
    }))
    client = FakeFoleyClient()
    service = H3FoleyService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    req = H3FoleyRequest(
        job.job_id, "foley", workflow, {}, "A heavy wooden door slam. No music. No dialogue.", 22,
        True, "MINIMAX-H3-LICENSE-ACK", mode=H3FoleyMode.FAST_32, target_duration_seconds=5,
        accept_experimental_low_resolution_audio=True, poll_interval_seconds=0.1, completion_timeout_seconds=2,
    )
    first = service.generate(req)
    second = service.generate(req)
    asset = store.get_asset(first.asset_id)
    assert asset.asset_type is AssetType.SFX
    streams = [s for s in asset.media_metadata["streams"] if s.get("codec_type") == "audio"]
    assert streams[0]["sample_rate"] == 48000
    assert asset.generation_provenance["width"] == 32 and asset.generation_provenance["height"] == 32
    assert "EXPERIMENTAL_COMMUNITY_FAST_PATH" in asset.publication_restrictions
    assert client.workflow["1"]["inputs"]["w"] == 32
    assert first.asset_id == second.asset_id and client.queued == 1


def test_h3_foley_long_duration_requires_second_ack(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    workflow = workflows / "foley.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode", "inputs": {"prompt": "{{PROMPT}}"}}}))
    client = FakeFoleyClient()
    service = H3FoleyService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    with pytest.raises(ProductError) as exc:
        service.generate(H3FoleyRequest(
            job.job_id, "long", workflow, {}, "room ambience", 1, True, "MINIMAX-H3-LICENSE-ACK",
            target_duration_seconds=30, accept_experimental_low_resolution_audio=True,
        ))
    assert exc.value.code == "ERR_AUTH_H3_FOLEY_EXPERIMENTAL_DURATION"
    assert client.queued == 0


def test_h3_foley_audio_reference_is_same_job_and_staged(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    make_video_with_audio(output / "foley.mp4")
    wav = tmp_path / "reference.wav"
    make_wav(wav)
    ref = canonical_asset(store, resolver, job, wav, AssetType.SFX)
    workflow = workflows / "foley-ref.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode", "inputs": {"audio": "{{REFERENCE_AUDIO}}", "w": "{{WIDTH}}", "h": "{{HEIGHT}}", "prompt": "{{PROMPT}}"}}}))
    client = FakeFoleyClient()
    service = H3FoleyService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    result = service.generate(H3FoleyRequest(
        job.job_id, "foley-ref", workflow, {}, "Make a shorter variation.", 2, True, "MINIMAX-H3-LICENSE-ACK",
        reference_audio_asset_id=ref.asset_id, accept_experimental_low_resolution_audio=True,
        poll_interval_seconds=0.1, completion_timeout_seconds=2,
    ))
    asset = store.get_asset(result.asset_id)
    assert asset.generation_provenance["reference_audio_asset_id"] == ref.asset_id
    assert "bai-task004-h3-foley" in client.workflow["1"]["inputs"]["audio"]
    # Operation-owned ComfyUI staging is removed after completion.
    assert not any(inp.rglob("reference-audio.wav"))


def test_h3_production_brief_rejects_reserved_reference_tag_injection():
    with pytest.raises(ValueError):
        H3ProductionBriefBuilder.build(
            user_intent="Make <Picture 99> the hero.",
            target_duration_seconds=5,
            target_aspect_ratio="16:9",
            shots=(H3Shot(1, "Static hero."),),
        )


def test_h3_single_frame_requires_external_node_ack_after_model_ack(tmp_path):
    store, job, resolver, workflows, output, inp, stage = roots(tmp_path)
    source = tmp_path / "reference.png"
    write_test_png(source)
    ref = canonical_asset(store, resolver, job, source, AssetType.IMAGE)
    workflow = workflows / "single.json"
    workflow.write_text(json.dumps({
        "1": {"class_type": "MiniMaxH3SingleFrameEdit", "inputs": {"image": "{{REFERENCE_1}}"}},
        "2": {"class_type": "MiniMaxH3SelectFrame", "inputs": {}},
    }))
    client = FakeSingleFrameClient()
    service = H3SingleFrameService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflows,)),
        comfy_output_root=output, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    with pytest.raises(ProductError) as exc:
        service.generate(H3SingleFrameRequest(
            job.job_id, "no-node-ack", workflow, {}, "x", 1,
            H3SingleFrameContract(H3SingleFrameMode.SINGLE_FRAME_EDIT), (ref.asset_id,), True,
            "MINIMAX-H3-LICENSE-ACK", None,
        ))
    assert exc.value.code == "ERR_AUTH_H3_SINGLE_FRAME_EXTERNAL_NODE_LICENSE"
    assert client.queued == 0
