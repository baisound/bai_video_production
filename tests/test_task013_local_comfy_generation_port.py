from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_video_production.ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily
from ai_video_production.comfyui import ComfyResourcePolicy
from ai_video_production.creative_generation_execution_application import LocalGenerationExecutionRequest
from ai_video_production.errors import ProductError
from ai_video_production.local_comfy_generation_port import (
    LocalComfyGenerationConfig,
    LocalComfyTextToVideoPort,
    MINIMAX_H3_NATIVE_WORKFLOW_SHA256,
    default_minimax_h3_workflow_path,
)
from ai_video_production.serialization import sha256_bytes


class Probe:
    def __init__(self, has_video: bool = True):
        self.has_video = has_video
        self.paths: list[Path] = []

    def probe(self, path):
        self.paths.append(Path(path))
        return type("Result", (), {"has_video": self.has_video})()


class Client:
    endpoint = "http://127.0.0.1:8188"

    def __init__(self, output_root: Path, *, videos: int = 1, history_error: ProductError | None = None):
        self.output_root = output_root
        self.videos = videos
        self.history_error = history_error
        self.queued = 0
        self.workflow = None
        self.client_id = None

    def object_info(self):
        result = {name: {"input": {"required": {}, "optional": {}}} for name in (
            "UNETLoader", "CLIPLoader", "VAELoader", "MiniMaxH3ImageToVideo", "BasicGuider",
            "RandomNoise", "KSamplerSelect", "BasicScheduler", "SamplerCustomAdvanced",
            "VAEDecode", "VAEDecodeAudio", "CreateVideo", "SaveVideo",
        )}
        result["UNETLoader"]["input"]["required"] = {"unet_name": [["minimax_h3_fl2va_pruned_int8_convrot.safetensors"]]}
        result["CLIPLoader"]["input"]["required"] = {
            "clip_name": [["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]],
            "type": [["minimax"]],
        }
        result["VAELoader"]["input"]["required"] = {"vae_name": [[
            "minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors",
        ]]}
        return result

    def system_stats(self):
        return {
            "system": {
                "ram_free": 64 * 1024**3,
                "argv": [
                    "main.py", "--listen", "127.0.0.1", "--port", "8188",
                    "--disable-auto-launch", "--output-directory", str(self.output_root),
                ],
            },
            "devices": [{"name": "cuda", "type": "cuda", "vram_free": 16 * 1024**3}],
        }

    def queue(self, workflow, *, client_id):
        self.queued += 1
        self.workflow = workflow
        self.client_id = client_id
        return "prompt-native-1"

    def history(self, prompt_id):
        if self.history_error is not None:
            raise self.history_error
        descriptors = []
        for index in range(self.videos):
            target = self.output_root / "bai-task013" / "EXEC-LOCAL-1" / f"result-{index}.mp4"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"native-video-" + str(index).encode())
            descriptors.append({"filename": target.name, "subfolder": "bai-task013/EXEC-LOCAL-1", "type": "output"})
        return {prompt_id: {"status": {"status_str": "success"}, "outputs": {"14": {"videos": descriptors}}}}


def fixture(tmp_path: Path, *, videos: int = 1, history_error: ProductError | None = None, probe: Probe | None = None):
    roots = {name: tmp_path / name for name in ("comfy-output", "project-output", "stage", "journal")}
    for root in roots.values():
        root.mkdir()
    client = Client(roots["comfy-output"], videos=videos, history_error=history_error)
    config = LocalComfyGenerationConfig(
        endpoint=client.endpoint,
        workflow_path=default_minimax_h3_workflow_path(),
        workflow_sha256=MINIMAX_H3_NATIVE_WORKFLOW_SHA256,
        comfy_output_root=roots["comfy-output"],
        project_output_root=roots["project-output"],
        staging_root=roots["stage"],
        dispatch_journal_root=roots["journal"],
        route_id="local-video", provider_id="comfy", model_id="minimax-h3-native",
        width=64, height=64, length=5, steps=1, poll_interval_seconds=0.1,
        completion_timeout_seconds=2,
    )
    port = LocalComfyTextToVideoPort(
        config=config, client=client,
        resource_policy=ComfyResourcePolicy(min_free_vram_bytes=1, min_free_ram_bytes=1, min_free_disk_bytes=0),
        media_probe=probe or Probe(), sleeper=lambda _: None,
    )
    route = ModelRoute(
        "local-video", AiWorkload.VIDEO, ProviderFamily.COMFYUI, "comfy", "minimax-h3-native",
        CostClass.LOCAL_FREE_AI, capabilities=("TEXT_TO_VIDEO",),
    )
    prompt = "body private test prompt"
    request = LocalGenerationExecutionRequest(
        "EXEC-LOCAL-1", "QUEUE-LOCAL-1", "scene-1", "slot-1", "TEXT_TO_VIDEO",
        prompt, sha256_bytes(prompt.encode()), (), "rights://project/scene-1",
    )
    return port, client, route, request, roots


def test_packaged_workflow_is_body_free_and_checksum_bound():
    path = default_minimax_h3_workflow_path()
    text = path.read_text(encoding="utf-8")
    assert "{{PROMPT}}" in text
    assert "body private" not in text
    value = json.loads(text)
    from ai_video_production.serialization import canonical_json_bytes
    assert sha256_bytes(canonical_json_bytes(value)) == MINIMAX_H3_NATIVE_WORKFLOW_SHA256


def test_local_native_port_publishes_one_verified_body_private_video(tmp_path: Path):
    probe = Probe()
    port, client, route, request, roots = fixture(tmp_path, probe=probe)
    result = port.execute(route, request)
    assert client.queued == 1
    assert client.client_id == request.execution_id
    assert client.workflow["5"]["inputs"]["prompt"] == request.prompt_text
    assert client.workflow["5"]["inputs"]["length"] == 5
    assert result.provider_operation_id == "prompt-native-1"
    assert result.output_ref == "project-output://generated/EXEC-LOCAL-1/result.mp4"
    output = roots["project-output"] / "generated" / "EXEC-LOCAL-1" / "result.mp4"
    assert output.read_bytes() == b"native-video-0"
    journal = json.loads((roots["journal"] / "EXEC-LOCAL-1.json").read_text(encoding="utf-8"))
    assert journal["state"] == "COMPLETED"
    assert journal["prompt_id"] == "prompt-native-1"
    assert request.prompt_text not in json.dumps(journal)
    assert probe.paths == [output]


def test_exact_local_free_route_is_required_before_queue(tmp_path: Path):
    port, client, route, request, _ = fixture(tmp_path)
    wrong = ModelRoute(
        route.route_id, route.workload, route.provider_family, route.provider_id, route.model_id,
        CostClass.LOCAL_LICENSED_AI, capabilities=route.capabilities,
    )
    with pytest.raises(ProductError) as exc:
        port.execute(wrong, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_ROUTE"
    assert client.queued == 0


def test_config_rejects_lan_or_noncanonical_endpoint_before_composition(tmp_path: Path):
    roots = [tmp_path / name for name in ("out", "canonical", "stage", "journal")]
    for root in roots:
        root.mkdir()
    values = dict(
        workflow_path=default_minimax_h3_workflow_path(),
        workflow_sha256=MINIMAX_H3_NATIVE_WORKFLOW_SHA256,
        comfy_output_root=roots[0], project_output_root=roots[1],
        staging_root=roots[2], dispatch_journal_root=roots[3],
        route_id="local-video", provider_id="comfy", model_id="minimax-h3-native",
    )
    for endpoint in (
        "http://192.168.1.20:8188", "http://localhost:8188",
        "https://127.0.0.1:8188", "http://127.0.0.1:8188/path",
    ):
        with pytest.raises(ValueError):
            LocalComfyGenerationConfig(endpoint=endpoint, **values)


def test_runtime_rejects_legacy_low_vram_mode_before_dispatch(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = client.system_stats

    def unsafe_stats():
        value = original()
        value["system"]["argv"].extend(["--disable-dynamic-vram", "--lowvram"])
        return value

    client.system_stats = unsafe_stats
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_RUNTIME_UNSAFE"
    assert exc.value.details["prohibited_flags"] == ["--disable-dynamic-vram", "--lowvram"]
    assert client.queued == 0
    assert list(roots["journal"].iterdir()) == []


@pytest.mark.parametrize(
    "unsafe_flag",
    (
        "--disable-async-offload",
        "--disable-pinned-memory",
        "--disable-dynamic-vram=true",
        "--lowvram=true",
    ),
)
def test_runtime_rejects_every_incident_memory_flag_and_assignment_form_before_dispatch(
    tmp_path: Path,
    unsafe_flag: str,
):
    port, client, route, request, roots = fixture(tmp_path)
    original = client.system_stats

    def unsafe_stats():
        value = original()
        value["system"]["argv"].append(unsafe_flag)
        return value

    client.system_stats = unsafe_stats
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_RUNTIME_UNSAFE"
    assert exc.value.details["prohibited_flags"] == [unsafe_flag]
    assert client.queued == 0
    assert list(roots["journal"].iterdir()) == []


def test_runtime_output_root_must_match_product_owned_root(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = client.system_stats

    def drifted_stats():
        value = original()
        index = value["system"]["argv"].index("--output-directory")
        value["system"]["argv"][index + 1] = str(tmp_path / "shared-output")
        return value

    client.system_stats = drifted_stats
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_RUNTIME_OUTPUT"
    assert client.queued == 0
    assert list(roots["journal"].iterdir()) == []


def test_prompt_checksum_and_external_inputs_fail_before_queue(tmp_path: Path):
    port, client, route, request, _ = fixture(tmp_path)
    changed = LocalGenerationExecutionRequest(
        request.execution_id, request.queue_entry_id, request.scene_id, request.slot_id,
        request.capability, request.prompt_text + " changed", request.prompt_sha256,
        request.input_bindings, request.rights_authorization_ref,
    )
    with pytest.raises(ProductError) as exc:
        port.execute(route, changed)
    assert exc.value.code == "ERR_GENERATION_COMFY_PROMPT_CHECKSUM"
    assert client.queued == 0

    bound = LocalGenerationExecutionRequest(
        request.execution_id, request.queue_entry_id, request.scene_id, request.slot_id,
        request.capability, request.prompt_text, request.prompt_sha256,
        ({"asset_id": "asset-1"},), request.rights_authorization_ref,
    )
    with pytest.raises(ProductError) as exc:
        port.execute(route, bound)
    assert exc.value.code == "ERR_GENERATION_COMFY_INPUTS"
    assert client.queued == 0


def test_workflow_tamper_is_rejected_at_composition(tmp_path: Path):
    source = default_minimax_h3_workflow_path()
    workflow = tmp_path / "workflow.json"
    workflow.write_bytes(source.read_bytes() + b"\n")
    roots = [tmp_path / name for name in ("out", "canonical", "stage", "journal")]
    for root in roots:
        root.mkdir()
    config = LocalComfyGenerationConfig(
        "http://127.0.0.1:8188", workflow, MINIMAX_H3_NATIVE_WORKFLOW_SHA256,
        *roots, "local-video", "comfy", "minimax-h3-native",
    )
    # Whitespace does not alter the canonical Product workflow identity.
    LocalComfyTextToVideoPort(config=config, client=Client(roots[0]), resource_policy=ComfyResourcePolicy(min_free_disk_bytes=0), media_probe=Probe())
    value = json.loads(workflow.read_text(encoding="utf-8"))
    value["1"]["inputs"]["weight_dtype"] = "fp8_e4m3fn"
    workflow.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        LocalComfyTextToVideoPort(config=config, client=Client(roots[0]), resource_policy=ComfyResourcePolicy(min_free_disk_bytes=0), media_probe=Probe())
    assert exc.value.code == "ERR_GENERATION_COMFY_WORKFLOW_CHECKSUM"


def test_ambiguous_output_is_terminal_and_never_published(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path, videos=2)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_OUTPUT_AMBIGUOUS"
    assert client.queued == 1
    assert not (roots["project-output"] / "generated").exists()
    journal = json.loads((roots["journal"] / "EXEC-LOCAL-1.json").read_text(encoding="utf-8"))
    assert journal["state"] == "FAILED"


def test_post_dispatch_history_failure_is_uncertain_and_blocks_replay(tmp_path: Path):
    error = ProductError("ERR_PROVIDER_COMFY_UNREACHABLE", "offline")
    port, client, route, request, roots = fixture(tmp_path, history_error=error)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_HISTORY_UNCERTAIN"
    assert exc.value.details["execution_state_uncertain"] is True
    assert exc.value.details["automatic_retry_allowed"] is False
    journal = json.loads((roots["journal"] / "EXEC-LOCAL-1.json").read_text(encoding="utf-8"))
    assert journal["state"] == "QUEUED"
    assert journal["prompt_id"] == "prompt-native-1"
    with pytest.raises(ProductError) as replay:
        port.execute(route, request)
    assert replay.value.code == "ERR_GENERATION_COMFY_ALREADY_DISPATCHED"
    assert client.queued == 1


def test_output_descriptor_must_match_exact_execution_prefix(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)

    def unrelated(_prompt_id):
        target = roots["comfy-output"] / "other" / "result.mp4"
        target.parent.mkdir()
        target.write_bytes(b"other")
        return {"prompt-native-1": {"outputs": {"14": {"videos": [{"filename": "result.mp4", "subfolder": "other", "type": "output"}]}}}}

    client.history = unrelated
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_OUTPUT_IDENTITY"
    assert not (roots["project-output"] / "generated").exists()


def test_canonical_generated_symlink_is_rejected(tmp_path: Path):
    port, _client, route, request, roots = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (roots["project-output"] / "generated").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_PROJECT_OUTPUT_SYMLINK"
    assert list(outside.iterdir()) == []
