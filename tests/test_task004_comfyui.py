from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
import subprocess

import pytest

from ai_video_production import (
    ComfyEndpointPolicy, ComfyResourcePolicy, LocalVideoGenerationRequest, LocalVideoGenerationService,
    LogicalPathResolver, PathMapping, ProductError, ProfileSnapshot, SQLiteProductStore, SourcePathPolicy,
    VideoGenerationMode,
)
from ai_video_production.comfyui import (
    _request_bound_command, admit_comfy_resources, assert_workflow_supported, render_workflow_placeholders, resolve_comfy_output,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


@pytest.mark.parametrize("url", ["https://127.0.0.1:8188", "http://example.com:8188", "http://8.8.8.8:8188", "http://user:pw@127.0.0.1:8188", "http://127.0.0.1:8188/x", "http://127.0.0.1:8188?x=1", "http://0.0.0.0:8188"])
def test_comfy_endpoint_policy_denies_untrusted_origins(url):
    with pytest.raises(ProductError):
        ComfyEndpointPolicy().authorize(url)


@pytest.mark.parametrize("url", ["http://127.0.0.1:8188", "http://localhost:8188", "http://192.168.1.20:8188", "http://10.0.0.5:9000"])
def test_comfy_endpoint_policy_accepts_loopback_private(url):
    assert ComfyEndpointPolicy().authorize(url).startswith("http://")


def test_comfy_endpoint_explicit_hostname_allowlist():
    assert ComfyEndpointPolicy(("my-gpu-box",)).authorize("http://my-gpu-box:8188") == "http://my-gpu-box:8188"


def test_workflow_substitution_is_typed_and_no_eval():
    source = {"1":{"class_type":"Node","inputs":{"text":"{{PROMPT}}","seed":"{{SEED}}","literal":"prefix {{PROMPT}}","danger":"{{DANGER}}"}}}
    rendered = render_workflow_placeholders(source, {"PROMPT":"hello", "SEED":123, "DANGER":"__import__('os').system('x')"})
    assert rendered["1"]["inputs"]["seed"] == 123
    assert rendered["1"]["inputs"]["literal"] == "prefix {{PROMPT}}"
    assert rendered["1"]["inputs"]["danger"].startswith("__import__")


def test_workflow_missing_placeholder_fails():
    with pytest.raises(ProductError) as exc:
        render_workflow_placeholders({"x":"{{NOPE}}"}, {})
    assert exc.value.code == "ERR_INPUT_COMFY_PLACEHOLDER_MISSING"


def test_workflow_class_validation_fails_before_queue():
    with pytest.raises(ProductError) as exc:
        assert_workflow_supported({"1":{"class_type":"Missing"}}, {"Present":{}})
    assert exc.value.code == "ERR_PROVIDER_COMFY_NODE_UNAVAILABLE"


def test_resource_admission_vram_unknown_fails_closed(tmp_path):
    with pytest.raises(ProductError) as exc:
        admit_comfy_resources({"devices":[{"name":"NVIDIA GPU","type":"cuda"}]}, ComfyResourcePolicy(min_free_vram_bytes=1), staging_root=tmp_path)
    assert exc.value.code == "ERR_RESOURCE_COMFY_VRAM_UNKNOWN"


def test_resource_admission_low_vram_fails(tmp_path):
    with pytest.raises(ProductError) as exc:
        admit_comfy_resources({"devices":[{"name":"GPU","type":"cuda","vram_free":100}]}, ComfyResourcePolicy(min_free_vram_bytes=101, min_free_disk_bytes=0), staging_root=tmp_path)
    assert exc.value.code == "ERR_RESOURCE_COMFY_VRAM_LOW"


def test_resource_admission_passes_verified_vram(tmp_path):
    value = admit_comfy_resources({"devices":[{"name":"GPU","type":"cuda","vram_free":1000}]}, ComfyResourcePolicy(min_free_vram_bytes=100, min_free_disk_bytes=0), staging_root=tmp_path)
    assert value["max_verified_free_vram_bytes"] == 1000


def test_resolve_comfy_output_blocks_traversal_and_symlink(tmp_path):
    root = tmp_path / "out"; root.mkdir()
    good = root / "ok.mp4"; good.write_bytes(b"x")
    assert resolve_comfy_output(root, {"filename":"ok.mp4","type":"output"}) == good
    for desc in [
        {"filename":"../x.mp4","type":"output"},
        {"filename":"x.mp4","subfolder":"../evil","type":"output"},
        {"filename":"ok.mp4","type":"temp"},
    ]:
        with pytest.raises(ProductError): resolve_comfy_output(root, desc)
    link = root / "link.mp4"
    try: link.symlink_to(good)
    except OSError: return
    with pytest.raises(ProductError): resolve_comfy_output(root, {"filename":"link.mp4","type":"output"})


class FakeClient:
    def __init__(self, output_name="generated.mp4", *, classes=None, videos=1):
        self.output_name=output_name; self.classes=classes or {"MiniMaxNode":{}}; self.videos=videos; self.queued=0
    def system_stats(self): return {"devices":[{"name":"GPU","type":"cuda","vram_free":16*1024**3}]}
    def object_info(self): return self.classes
    def queue(self, workflow, *, client_id): self.queued += 1; self.workflow=workflow; return "prompt-1"
    def history(self, prompt_id):
        return {prompt_id:{"outputs":{"9":{"videos":[{"filename":self.output_name,"type":"output"} for _ in range(self.videos)]}}}}


def make_service(tmp_path, client):
    asset_root=tmp_path/"assets"; job_root=tmp_path/"jobs"; workflow_root=tmp_path/"workflows"; out=tmp_path/"comfy-output"; inp=tmp_path/"comfy-input"; stage=tmp_path/"stage"
    for p in (asset_root,job_root,workflow_root,out,inp,stage): p.mkdir()
    store=SQLiteProductStore(tmp_path/"db.sqlite3"); ps=ProfileSnapshot.create("t4","1.0.0",{}); job=store.create_job(ps.profile_snapshot_id)
    resolver=LogicalPathResolver([PathMapping("asset://",asset_root,PureWindowsPath("D:/a")),PathMapping("job://",job_root,PureWindowsPath("D:/j"))])
    service=LocalVideoGenerationService(store=store,resolver=resolver,client=client,workflow_policy=SourcePathPolicy((workflow_root,)),comfy_output_root=out,comfy_input_root=inp,staging_root=stage,resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1,min_free_disk_bytes=0))
    return service,store,resolver,workflow_root,out,job


def make_video(path: Path):
    subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=black:s=160x90:r=24:d=0.5","-c:v","mpeg4","-y",str(path)],check=True)


def test_local_video_generation_e2e_fake_comfy_real_media(tmp_path):
    client=FakeClient(); service,store,resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"MiniMaxNode","inputs":{"prompt":"{{PROMPT}}","seed":"{{SEED}}"}}}))
    result=service.generate(LocalVideoGenerationRequest(job.job_id,"g1",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{},"a cinematic test",42,True,license_authorization_ref="MINIMAX-H3-LICENSE-ACK",poll_interval_seconds=.1,completion_timeout_seconds=2))
    asset=store.get_asset(result.asset_id)
    assert asset.asset_type.value == "GENERATED_VIDEO"
    assert asset.generation_provenance["model_family"] == "MiniMax-H3"
    assert asset.generation_provenance["seed"] == 42
    assert asset.rights_review_required
    assert client.queued == 1
    doc=json.loads(resolver.resolve(result.manifest_uri).read_text())
    assert doc["payload"]["details"]["prompt_checksum"].startswith("sha256:")
    assert "a cinematic test" not in json.dumps(doc)


def test_local_video_generation_requires_explicit_authorization_before_queue(tmp_path):
    client=FakeClient(); service,_store,_resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"MiniMaxNode"}}))
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(job.job_id,"g",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{},"x",1,False))
    assert exc.value.code == "ERR_AUTH_LOCAL_VIDEO_EXECUTION_REQUIRED"
    assert client.queued == 0


def test_local_video_generation_missing_class_does_not_queue(tmp_path):
    client=FakeClient(classes={}); service,_store,_resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"NoSuchNode"}}))
    with pytest.raises(ProductError): service.generate(LocalVideoGenerationRequest(job.job_id,"g",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{},"x",1,True,license_authorization_ref="MINIMAX-H3-LICENSE-ACK"))
    assert client.queued == 0


def test_local_video_multiple_history_outputs_fail_human_review(tmp_path):
    client=FakeClient(videos=2); service,_store,_resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"MiniMaxNode"}}))
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(job.job_id,"g",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{},"x",1,True,license_authorization_ref="MINIMAX-H3-LICENSE-ACK",poll_interval_seconds=.1,completion_timeout_seconds=2))
    assert exc.value.code == "ERR_PROVIDER_COMFY_VIDEO_AMBIGUOUS"


def test_local_video_idempotent_replay_does_not_queue_twice(tmp_path):
    client=FakeClient(); service,store,_resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"MiniMaxNode"}}))
    req=LocalVideoGenerationRequest(job.job_id,"same",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{},"x",1,True,license_authorization_ref="MINIMAX-H3-LICENSE-ACK",poll_interval_seconds=.1,completion_timeout_seconds=2)
    a=service.generate(req); b=service.generate(req)
    assert a.asset_id == b.asset_id and client.queued == 1
    assert store.latest_manifest(job.job_id,"local-video-generation-manifest").version == 1



def test_minimax_h3_license_ack_required_before_queue(tmp_path):
    client=FakeClient(); service,_store,_resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"MiniMaxNode"}}))
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(job.job_id,"lic",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{},"x",1,True))
    assert exc.value.code == "ERR_AUTH_VIDEO_MODEL_RUNTIME_LICENSE" and client.queued == 0


def test_video_reserved_substitution_cannot_override_prompt_or_seed(tmp_path):
    client=FakeClient(); service,_store,_resolver,workflow_root,out,job=make_service(tmp_path,client)
    make_video(out/"generated.mp4")
    workflow=workflow_root/"h3.json"; workflow.write_text(json.dumps({"1":{"class_type":"MiniMaxNode","inputs":{"prompt":"{{PROMPT}}"}}}))
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(job.job_id,"override",VideoGenerationMode.TEXT_TO_VIDEO,workflow,{"PROMPT":"different"},"canonical",1,True,license_authorization_ref="ACK"))
    assert exc.value.code == "ERR_INPUT_COMFY_RESERVED_SUBSTITUTION" and client.queued == 0

from ai_video_production import (
    AssetType, DerivedAssetPublisher, DerivedAssetSpec, ImageGenerationMode, LocalImageGenerationRequest,
    LocalImageGenerationService, PermissionState, RightsStatus, RuntimeLicenseState, VisualModelFamily,
    builtin_image_model_profile,
)


class FakeImageClient:
    def __init__(self, output_name="generated.png", *, classes=None, images=1):
        self.output_name = output_name
        self.classes = {"ImageNode": {}} if classes is None else classes
        self.images = images
        self.queued = 0
        self.workflow = None

    def system_stats(self):
        return {"devices": [{"name": "GPU", "type": "cuda", "vram_free": 16 * 1024**3}]}

    def object_info(self):
        return self.classes

    def queue(self, workflow, *, client_id):
        self.queued += 1
        self.workflow = workflow
        return "image-prompt-1"

    def history(self, prompt_id):
        return {prompt_id: {"outputs": {"9": {"images": [
            {"filename": self.output_name, "type": "output"} for _ in range(self.images)
        ]}}}}


def write_test_png(path: Path, rgba: tuple[int, int, int, int] = (0, 0, 0, 255)) -> None:
    # Minimal valid 1x1 RGBA PNG built with stdlib only.
    import struct, zlib
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    raw = bytes((0, *rgba))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(raw))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


def make_image_service(tmp_path, client):
    asset_root = tmp_path / "assets"
    job_root = tmp_path / "jobs"
    workflow_root = tmp_path / "workflows"
    out = tmp_path / "comfy-output"
    inp = tmp_path / "comfy-input"
    stage = tmp_path / "stage"
    for p in (asset_root, job_root, workflow_root, out, inp, stage):
        p.mkdir()
    store = SQLiteProductStore(tmp_path / "db.sqlite3")
    ps = ProfileSnapshot.create("t4-image", "1.0.0", {})
    job = store.create_job(ps.profile_snapshot_id)
    resolver = LogicalPathResolver([
        PathMapping("asset://", asset_root, PureWindowsPath("D:/a")),
        PathMapping("job://", job_root, PureWindowsPath("D:/j")),
    ])
    service = LocalImageGenerationService(
        store=store, resolver=resolver, client=client, workflow_policy=SourcePathPolicy((workflow_root,)),
        comfy_output_root=out, comfy_input_root=inp, staging_root=stage,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_disk_bytes=0),
    )
    return service, store, resolver, workflow_root, out, inp, job


def test_builtin_image_model_license_profiles():
    schnell = builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL)
    dev = builtin_image_model_profile(VisualModelFamily.FLUX_1_DEV)
    sdxl = builtin_image_model_profile(VisualModelFamily.SDXL_1_0)
    sd35 = builtin_image_model_profile(VisualModelFamily.SD3_5)
    legacy = builtin_image_model_profile(VisualModelFamily.SD1_5)
    assert schnell.runtime_license_state is RuntimeLicenseState.ALLOWED and schnell.license_id == "Apache-2.0"
    assert dev.runtime_license_state is RuntimeLicenseState.RESTRICTED
    assert sdxl.runtime_license_state is RuntimeLicenseState.CONDITIONAL
    assert sd35.runtime_license_state is RuntimeLicenseState.CONDITIONAL
    assert legacy.runtime_license_state is RuntimeLicenseState.UNKNOWN


def test_local_image_generation_t2i_fake_comfy_real_png(tmp_path):
    client = FakeImageClient()
    service, store, resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    workflow = workflow_root / "flux.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode", "inputs": {
        "prompt": "{{PROMPT}}", "negative": "{{NEGATIVE_PROMPT}}", "seed": "{{SEED}}",
        "width": "{{WIDTH}}", "height": "{{HEIGHT}}",
    }}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-1", ImageGenerationMode.TEXT_TO_IMAGE, workflow, {}, "cinematic frame", 7, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL), negative_prompt="artifact", width=1024, height=576,
        commercial_runtime_requested=True, poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    result = service.generate(req)
    asset = store.get_asset(result.asset_id)
    assert asset.asset_type is AssetType.IMAGE
    assert asset.generation_provenance["model_family"] == "FLUX_1_SCHNELL"
    assert asset.generation_provenance["model_license_id"] == "Apache-2.0"
    assert asset.rights_review_required
    assert client.queued == 1
    assert client.workflow["1"]["inputs"]["width"] == 1024
    doc = json.loads(resolver.resolve(result.manifest_uri).read_text())
    serialized = json.dumps(doc, ensure_ascii=False)
    assert "cinematic frame" not in serialized and "artifact" not in serialized
    assert doc["payload"]["details"]["commercial_runtime_requested"] is True


def test_local_image_flux_dev_commercial_runtime_denied_before_queue(tmp_path):
    client = FakeImageClient()
    service, _store, _resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    workflow = workflow_root / "dev.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode"}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-dev", ImageGenerationMode.TEXT_TO_IMAGE, workflow, {}, "x", 1, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_DEV), commercial_runtime_requested=True,
    )
    with pytest.raises(ProductError) as exc:
        service.generate(req)
    assert exc.value.code == "ERR_AUTH_MODEL_COMMERCIAL_RUNTIME_LICENSE"
    assert client.queued == 0


def test_local_image_conditional_profile_commercial_can_use_explicit_license_ref(tmp_path):
    client = FakeImageClient()
    service, store, _resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    workflow = workflow_root / "sd35.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode"}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-sd35", ImageGenerationMode.TEXT_TO_IMAGE, workflow, {}, "x", 1, True,
        builtin_image_model_profile(VisualModelFamily.SD3_5), commercial_runtime_requested=True,
        license_authorization_ref="LIC-AUTH-LOCAL-001", poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    result = service.generate(req)
    provenance = store.get_asset(result.asset_id).generation_provenance
    assert provenance["license_authorization_ref_checksum"].startswith("sha256:")
    assert "LIC-AUTH-LOCAL-001" not in json.dumps(provenance)
    assert client.queued == 1


def test_local_image_multiple_outputs_fail_human_review(tmp_path):
    client = FakeImageClient(images=2)
    service, _store, _resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    workflow = workflow_root / "many.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode"}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-many", ImageGenerationMode.TEXT_TO_IMAGE, workflow, {}, "x", 1, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL), poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    with pytest.raises(ProductError) as exc:
        service.generate(req)
    assert exc.value.code == "ERR_PROVIDER_COMFY_IMAGE_AMBIGUOUS"


def test_local_image_i2i_stages_authorized_reference_and_cleans_it(tmp_path):
    client = FakeImageClient()
    service, store, _resolver, workflow_root, out, inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png", (255, 255, 255, 255))
    source_file = tmp_path / "reference.png"
    write_test_png(source_file)
    op = store.reserve_operation(job.job_id, "TEST_REFERENCE", "ref-1")[0]
    ref_asset = DerivedAssetPublisher(store=store, resolver=service.resolver).publish(
        source_file,
        DerivedAssetSpec(
            job.job_id, "reference", AssetType.IMAGE, "USER", rights_status=RightsStatus.OWNED,
            commercial_use=PermissionState.ALLOWED, derivative_allowed=PermissionState.ALLOWED,
            reuse_allowed=PermissionState.ALLOWED,
        ),
        operation_id=op.operation_id,
    )
    workflow = workflow_root / "i2i.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode", "inputs": {"image": "{{REFERENCE_IMAGE}}"}}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-i2i", ImageGenerationMode.IMAGE_TO_IMAGE, workflow, {}, "transform", 3, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL), reference_asset_id=ref_asset.asset_id,
        poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    result = service.generate(req)
    generated = store.get_asset(result.asset_id)
    assert generated.source_ref == ref_asset.asset_id
    assert client.workflow["1"]["inputs"]["image"].startswith("bai-task004/")
    assert not any(inp.rglob("reference.png"))


def test_local_image_i2i_denies_reference_without_derivative_rights(tmp_path):
    client = FakeImageClient()
    service, store, _resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    source_file = tmp_path / "reference.png"
    write_test_png(source_file)
    op = store.reserve_operation(job.job_id, "TEST_REFERENCE", "ref-2")[0]
    ref_asset = DerivedAssetPublisher(store=store, resolver=service.resolver).publish(
        source_file, DerivedAssetSpec(job.job_id, "reference", AssetType.IMAGE, "USER", rights_status=RightsStatus.OWNED,
        commercial_use=PermissionState.ALLOWED, derivative_allowed=PermissionState.DENIED, reuse_allowed=PermissionState.ALLOWED),
        operation_id=op.operation_id,
    )
    workflow = workflow_root / "i2i-denied.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode"}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-i2i-denied", ImageGenerationMode.IMAGE_TO_IMAGE, workflow, {}, "transform", 3, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL), reference_asset_id=ref_asset.asset_id,
    )
    with pytest.raises(ProductError) as exc:
        service.generate(req)
    assert exc.value.code == "ERR_AUTH_IMAGE_REFERENCE_DERIVATIVE_RIGHTS"
    assert client.queued == 0


def test_local_image_idempotent_replay_does_not_queue_twice(tmp_path):
    client = FakeImageClient()
    service, _store, _resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    workflow = workflow_root / "replay.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode"}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-same", ImageGenerationMode.TEXT_TO_IMAGE, workflow, {}, "x", 1, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL), poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    a = service.generate(req)
    b = service.generate(req)
    assert a.asset_id == b.asset_id and client.queued == 1


def _publish_reference_image(service, store, job, tmp_path, *, key: str, derivative=PermissionState.ALLOWED):
    source_file = tmp_path / f"{key}.png"
    write_test_png(source_file, (32, 64, 96, 255))
    op = store.reserve_operation(job.job_id, "TEST_VIDEO_REFERENCE", key)[0]
    return DerivedAssetPublisher(store=store, resolver=service.resolver).publish(
        source_file,
        DerivedAssetSpec(
            job.job_id, "video-reference", AssetType.IMAGE, "USER", rights_status=RightsStatus.OWNED,
            commercial_use=PermissionState.ALLOWED, derivative_allowed=derivative,
            reuse_allowed=PermissionState.ALLOWED,
        ),
        operation_id=op.operation_id,
    )


def test_video_i2v_stages_canonical_reference_and_cleans_it(tmp_path):
    client = FakeClient()
    service, store, resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    ref = _publish_reference_image(service, store, job, tmp_path, key="vref")
    workflow = workflow_root / "i2v.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode", "inputs": {"image": "{{FIRST_FRAME}}", "prompt": "{{PROMPT}}"}}}))
    req = LocalVideoGenerationRequest(
        job.job_id, "i2v", VideoGenerationMode.IMAGE_TO_VIDEO, workflow, {}, "animate", 5, True,
        license_authorization_ref="MINIMAX-H3-LICENSE-ACK", reference_bindings={"FIRST_FRAME": ref.asset_id},
        poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    result = service.generate(req)
    assert client.workflow["1"]["inputs"]["image"].startswith("bai-task004-video/")
    assert not any((tmp_path / "comfy-input").rglob("ref-*.png"))
    doc = json.loads(resolver.resolve(result.manifest_uri).read_text())
    assert doc["payload"]["details"]["reference_bindings"] == [{"placeholder": "FIRST_FRAME", "asset_id": ref.asset_id}]
    asset = store.get_asset(result.asset_id)
    assert "MODEL_LICENSE_TERRITORY_REVIEW" in asset.publication_restrictions
    assert "MINIMAX-H3-LICENSE-ACK" not in json.dumps(doc)


def test_video_first_last_requires_two_images(tmp_path):
    client = FakeClient()
    service, store, _resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    ref = _publish_reference_image(service, store, job, tmp_path, key="first")
    workflow = workflow_root / "fl.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode"}}))
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(
            job.job_id, "fl", VideoGenerationMode.FIRST_LAST, workflow, {}, "x", 1, True,
            license_authorization_ref="ACK", reference_bindings={"FIRST_FRAME": ref.asset_id},
        ))
    assert exc.value.code == "ERR_INPUT_VIDEO_REFERENCE_MODE" and client.queued == 0


def test_video_reference_derivative_rights_denied_before_queue(tmp_path):
    client = FakeClient()
    service, store, _resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    ref = _publish_reference_image(service, store, job, tmp_path, key="denied-video-ref", derivative=PermissionState.DENIED)
    workflow = workflow_root / "ref-denied.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode"}}))
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(
            job.job_id, "ref-denied", VideoGenerationMode.REFERENCE, workflow, {}, "x", 1, True,
            license_authorization_ref="ACK", reference_bindings={"REFERENCE_IMAGE_1": ref.asset_id},
        ))
    assert exc.value.code == "ERR_AUTH_VIDEO_REFERENCE_DERIVATIVE_RIGHTS" and client.queued == 0


def test_image_i2i_replaces_stale_product_owned_reference_staging(tmp_path):
    client = FakeImageClient()
    service, store, _resolver, workflow_root, out, inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png", (255, 255, 255, 255))
    ref = _publish_reference_image(service, store, job, tmp_path, key="stale-img-ref")
    workflow = workflow_root / "stale-i2i.json"
    workflow_doc = {"1": {"class_type": "ImageNode", "inputs": {"image": "{{REFERENCE_IMAGE}}"}}}
    workflow.write_text(json.dumps(workflow_doc))
    profile = builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL)
    req = LocalImageGenerationRequest(
        job.job_id, "stale-i2i", ImageGenerationMode.IMAGE_TO_IMAGE, workflow, {}, "transform", 3, True,
        profile, reference_asset_id=ref.asset_id, poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    command = _request_bound_command("LOCAL_IMAGE_GENERATE", {
        "mode": req.mode.value, "workflow_checksum": sha256_bytes(canonical_json_bytes(workflow_doc)),
        "substitutions": req.substitutions, "prompt_checksum": sha256_bytes(req.prompt.encode("utf-8")),
        "negative_prompt_checksum": sha256_bytes(req.negative_prompt.encode("utf-8")), "seed": req.seed,
        "width": req.width, "height": req.height, "model_profile": profile.to_dict(),
        "commercial_runtime_requested": req.commercial_runtime_requested, "license_authorization_ref_checksum": None,
        "reference_asset_id": ref.asset_id,
    })
    operation = store.reserve_operation(job.job_id, command, "stale-i2i")[0]
    stale = inp / "bai-task004" / job.job_id / operation.operation_id
    stale.mkdir(parents=True)
    (stale / "old.txt").write_text("stale")
    service.generate(req)
    assert not stale.exists()


def test_image_reserved_substitution_cannot_falsify_provenance(tmp_path):
    client = FakeImageClient()
    service, _store, _resolver, workflow_root, out, _inp, job = make_image_service(tmp_path, client)
    write_test_png(out / "generated.png")
    workflow = workflow_root / "override-image.json"
    workflow.write_text(json.dumps({"1": {"class_type": "ImageNode", "inputs": {"prompt": "{{PROMPT}}"}}}))
    req = LocalImageGenerationRequest(
        job.job_id, "img-override", ImageGenerationMode.TEXT_TO_IMAGE, workflow, {"PROMPT": "different"}, "canonical", 1, True,
        builtin_image_model_profile(VisualModelFamily.FLUX_1_SCHNELL),
    )
    with pytest.raises(ProductError) as exc:
        service.generate(req)
    assert exc.value.code == "ERR_INPUT_COMFY_RESERVED_SUBSTITUTION" and client.queued == 0


def test_resource_admission_ram_unknown_or_low_fails_closed(tmp_path):
    stats={"system":{},"devices":[{"name":"GPU","type":"cuda","vram_free":1000}]}
    with pytest.raises(ProductError) as exc:
        admit_comfy_resources(stats, ComfyResourcePolicy(min_free_vram_bytes=1,min_free_ram_bytes=1,min_free_disk_bytes=0), staging_root=tmp_path)
    assert exc.value.code == "ERR_RESOURCE_COMFY_RAM_UNKNOWN"
    stats["system"]["ram_free"]=10
    with pytest.raises(ProductError) as exc:
        admit_comfy_resources(stats, ComfyResourcePolicy(min_free_vram_bytes=1,min_free_ram_bytes=11,min_free_disk_bytes=0), staging_root=tmp_path)
    assert exc.value.code == "ERR_RESOURCE_COMFY_RAM_LOW"


def test_workflow_enumerated_model_choice_must_exist_before_queue():
    from ai_video_production.comfyui import assert_workflow_inputs_available
    workflow={"1":{"class_type":"CheckpointLoader","inputs":{"ckpt_name":"missing.safetensors"}}}
    object_info={"CheckpointLoader":{"input":{"required":{"ckpt_name":[["present.safetensors"]]}}}}
    with pytest.raises(ProductError) as exc:
        assert_workflow_inputs_available(workflow,object_info)
    assert exc.value.code == "ERR_PROVIDER_COMFY_INPUT_CHOICE_UNAVAILABLE"


def test_comfy_endpoint_policy_rejects_link_local_and_metadata_ranges():
    for url in ("http://169.254.169.254:8188", "http://169.254.1.1:8188", "http://[fe80::1]:8188"):
        with pytest.raises(ProductError) as exc:
            ComfyEndpointPolicy().authorize(url)
        assert exc.value.code == "ERR_SECURITY_COMFY_ENDPOINT_DENIED"


def test_comfy_endpoint_policy_accepts_ipv6_loopback_and_ula():
    assert ComfyEndpointPolicy().authorize("http://[::1]:8188") == "http://[::1]:8188"
    assert ComfyEndpointPolicy().authorize("http://[fd00::5]:8188") == "http://[fd00::5]:8188"


def test_comfy_client_caps_json_response(monkeypatch):
    import ai_video_production.comfyui as comfy

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return None
        def read(self, amount=-1):
            assert amount == 1025
            return b"x" * 1025

    monkeypatch.setattr(comfy, "urlopen", lambda *_args, **_kwargs: Response())
    client = comfy.ComfyUIClient("http://127.0.0.1:8188", max_response_bytes=1024)
    with pytest.raises(ProductError) as exc:
        client.system_stats()
    assert exc.value.code == "ERR_PROVIDER_COMFY_RESPONSE_TOO_LARGE"


def test_comfy_workflow_file_size_is_bounded(tmp_path):
    from ai_video_production.comfyui import _load_workflow_json
    workflow = tmp_path / "huge.json"
    with workflow.open("wb") as out:
        out.truncate(10 * 1024 * 1024 + 1)
    with pytest.raises(ProductError) as exc:
        _load_workflow_json(workflow)
    assert exc.value.code == "ERR_INPUT_COMFY_WORKFLOW_SIZE"


def test_video_reference_staging_checks_input_disk_before_copy(tmp_path, monkeypatch):
    import ai_video_production.comfyui as comfy
    client = FakeClient()
    service, store, _resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    ref = _publish_reference_image(service, store, job, tmp_path, key="disk-ref")
    workflow = workflow_root / "disk-ref.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode", "inputs": {"image": "{{FIRST_FRAME}}"}}}))
    monkeypatch.setattr(comfy.shutil, "disk_usage", lambda _root: type("DU", (), {"free": 0})())
    with pytest.raises(ProductError) as exc:
        service.generate(LocalVideoGenerationRequest(
            job.job_id, "disk-ref-op", VideoGenerationMode.IMAGE_TO_VIDEO, workflow, {}, "animate", 5, True,
            license_authorization_ref="ACK", reference_bindings={"FIRST_FRAME": ref.asset_id},
        ))
    assert exc.value.code == "ERR_RESOURCE_COMFY_INPUT_DISK_LOW"
    assert client.queued == 0
    assert not any((tmp_path / "comfy-input").rglob("ref-*"))


def test_h3_spectrum_contract_is_optional_approximate_and_mutually_exclusive(tmp_path):
    from ai_video_production import H3AccelerationContract, H3AccelerationMode

    native = {"1": {"class_type": "MiniMaxNode"}}
    spectrum = {
        "1": {"class_type": "MiniMaxNode"},
        "2": {"class_type": "SpectrumApplyMiniMaxH3", "inputs": {"enabled": True, "history_storage": "system_ram"}},
    }
    assert H3AccelerationContract(H3AccelerationMode.NATIVE).validate_workflow(native)["approximate"] is False
    evidence = H3AccelerationContract(H3AccelerationMode.SPECTRUM_FAST).validate_workflow(spectrum, configured_vram_floor_bytes=1)
    assert evidence["approximate"] is True and evidence["external_node_license"] == "GPL-3.0"

    with pytest.raises(ProductError) as exc:
        H3AccelerationContract(H3AccelerationMode.NATIVE).validate_workflow(spectrum)
    assert exc.value.code == "ERR_INPUT_H3_NATIVE_WORKFLOW_ACCELERATED"

    with pytest.raises(ProductError) as exc:
        H3AccelerationContract(H3AccelerationMode.SPECTRUM_QUALITY).validate_workflow(native)
    assert exc.value.code == "ERR_PROVIDER_H3_SPECTRUM_NODE_REQUIRED"

    conflicting = dict(spectrum)
    conflicting["3"] = {"class_type": "SomeEasyCacheNode"}
    with pytest.raises(ProductError) as exc:
        H3AccelerationContract(H3AccelerationMode.SPECTRUM_FAST).validate_workflow(conflicting, configured_vram_floor_bytes=1)
    assert exc.value.code == "ERR_INPUT_H3_ACCELERATOR_CONFLICT"

    vram = {
        "1": {"class_type": "MiniMaxNode"},
        "2": {"class_type": "SpectrumApplyMiniMaxH3", "inputs": {"enabled": True, "history_storage": "vram"}},
    }
    with pytest.raises(ProductError) as exc:
        H3AccelerationContract(H3AccelerationMode.SPECTRUM_FAST).validate_workflow(vram, configured_vram_floor_bytes=0)
    assert exc.value.code == "ERR_RESOURCE_H3_SPECTRUM_VRAM_FLOOR_REQUIRED"


def test_local_video_spectrum_mode_records_external_accelerator_provenance(tmp_path):
    from ai_video_production import H3AccelerationMode

    client = FakeClient(classes={"MiniMaxNode": {}, "SpectrumApplyMiniMaxH3": {}})
    service, store, _resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    workflow = workflow_root / "h3-spectrum.json"
    workflow.write_text(json.dumps({
        "1": {"class_type": "MiniMaxNode"},
        "2": {"class_type": "SpectrumApplyMiniMaxH3", "inputs": {"enabled": True, "history_storage": "system_ram"}},
    }))
    result = service.generate(LocalVideoGenerationRequest(
        job.job_id, "spectrum-1", VideoGenerationMode.TEXT_TO_VIDEO, workflow, {}, "x", 3, True,
        license_authorization_ref="ACK", acceleration_mode=H3AccelerationMode.SPECTRUM_QUALITY,
        poll_interval_seconds=.1, completion_timeout_seconds=2,
    ))
    asset = store.get_asset(result.asset_id)
    assert asset.generation_provenance["acceleration"]["mode"] == "SPECTRUM_QUALITY"
    assert asset.generation_provenance["acceleration"]["external_node_code_incorporated"] is False
    assert "ACCELERATOR_OUTPUT_QA_REQUIRED" in asset.publication_restrictions


def test_local_video_idempotency_key_is_bound_to_request_fingerprint(tmp_path):
    client = FakeClient()
    service, _store, _resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    workflow = workflow_root / "fingerprint.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode"}}))
    first = LocalVideoGenerationRequest(
        job.job_id, "fingerprint-key", VideoGenerationMode.TEXT_TO_VIDEO, workflow, {}, "first", 1, True,
        license_authorization_ref="ACK", poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    service.generate(first)
    changed = LocalVideoGenerationRequest(
        job.job_id, "fingerprint-key", VideoGenerationMode.TEXT_TO_VIDEO, workflow, {}, "changed", 1, True,
        license_authorization_ref="ACK", poll_interval_seconds=.1, completion_timeout_seconds=2,
    )
    with pytest.raises(ProductError) as exc:
        service.generate(changed)
    assert exc.value.code == "ERR_INTEGRITY_IDEMPOTENCY_COMMAND_CONFLICT"
    assert client.queued == 1


class DeferredHistoryClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.ready = False

    def history(self, prompt_id):
        if not self.ready:
            return {}
        return super().history(prompt_id)


def test_local_video_timeout_replay_reconciles_same_prompt_without_second_queue(tmp_path):
    client = DeferredHistoryClient()
    service, _store, _resolver, workflow_root, out, job = make_service(tmp_path, client)
    make_video(out / "generated.mp4")
    workflow = workflow_root / "resume.json"
    workflow.write_text(json.dumps({"1": {"class_type": "MiniMaxNode"}}))
    req = LocalVideoGenerationRequest(
        job.job_id, "resume-key", VideoGenerationMode.TEXT_TO_VIDEO, workflow, {}, "resume", 9, True,
        license_authorization_ref="ACK", poll_interval_seconds=.1, completion_timeout_seconds=1,
    )
    with pytest.raises(ProductError) as exc:
        service.generate(req)
    assert exc.value.code == "ERR_PROVIDER_COMFY_GENERATION_TIMEOUT"
    assert client.queued == 1
    client.ready = True
    result = service.generate(req)
    assert result.prompt_id == "prompt-1"
    assert client.queued == 1
