from __future__ import annotations

import json
from pathlib import Path
import struct
import zlib

import pytest

from ai_video_production.ai_connections import AiWorkload, CostClass, ModelRoute, ProviderFamily
from ai_video_production.comfyui import ComfyResourcePolicy
from ai_video_production.creative_generation_execution_application import LocalGenerationExecutionRequest
from ai_video_production.errors import ProductError
from ai_video_production.local_comfy_image_generation_port import (
    FLUX1_SCHNELL_FP8_WORKFLOW_SHA256,
    LocalComfyImageGenerationConfig,
    LocalComfyTextToImagePort,
    default_flux1_schnell_fp8_workflow_path,
)
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes


def png_bytes(width: int = 64, height: int = 64, *, extra_decoded: bytes = b"") -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = b"".join(b"\x00" + b"\x20\x40\x80" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows + extra_decoded)) + chunk(b"IEND", b"")


def png_with_text(text: str) -> bytes:
    raw = png_bytes()
    position = raw.index(b"IDAT") - 4
    data = b"prompt\x00" + text.encode()
    chunk = struct.pack(">I", len(data)) + b"tEXt" + data + struct.pack(">I", zlib.crc32(b"tEXt" + data) & 0xFFFFFFFF)
    return raw[:position] + chunk + raw[position:]


def png_with_palette() -> bytes:
    raw = png_bytes()
    position = raw.index(b"IDAT") - 4
    data = b"\x00\x00\x00"
    chunk = struct.pack(">I", len(data)) + b"PLTE" + data + struct.pack(">I", zlib.crc32(b"PLTE" + data) & 0xFFFFFFFF)
    return raw[:position] + chunk + raw[position:]


class Client:
    endpoint = "http://127.0.0.1:8188"

    def __init__(self, output_root: Path, *, images: int = 1, corrupt: bool = False,
                 dimensions: tuple[int, int] = (64, 64), suffix: str = ".png"):
        self.output_root = output_root
        self.images = images
        self.corrupt = corrupt
        self.dimensions = dimensions
        self.suffix = suffix
        self.queued = 0
        self.workflow = None
        self.history_error: ProductError | None = None
        self.payload: bytes | None = None
        self.status = "success"

    def object_info(self):
        result = {name: {"input": {"required": {}, "optional": {}}} for name in (
            "CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage",
            "KSampler", "VAEDecode", "SaveImage",
        )}
        result["CheckpointLoaderSimple"]["input"]["required"] = {
            "ckpt_name": [["flux1-schnell-fp8.safetensors"]],
        }
        return result

    def system_stats(self):
        return {
            "system": {
                "ram_free": 64 * 1024**3,
                "argv": [
                    "main.py", "--listen", "127.0.0.1", "--port", "8188",
                    "--disable-auto-launch", "--disable-metadata",
                    "--output-directory", str(self.output_root),
                ],
            },
            "devices": [{"name": "cuda", "type": "cuda", "vram_free": 16 * 1024**3}],
        }

    def queue(self, workflow, *, client_id):
        self.queued += 1
        self.workflow = workflow
        return "prompt-image-1"

    def history(self, prompt_id):
        if self.history_error is not None:
            raise self.history_error
        descriptors = []
        for index in range(self.images):
            target = self.output_root / "bai-task013-image" / "EXEC-IMAGE-1" / f"result-{index}{self.suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            data = self.payload if self.payload is not None else (
                b"not-an-image" if self.corrupt else png_bytes(*self.dimensions)
            )
            target.write_bytes(data)
            descriptors.append({
                "filename": target.name,
                "subfolder": "bai-task013-image/EXEC-IMAGE-1",
                "type": "output",
            })
        return {prompt_id: {"status": {"status_str": self.status}, "outputs": {"7": {"images": descriptors}}}}


def fixture(tmp_path: Path, **client_values):
    roots = {name: tmp_path / name for name in ("comfy-output", "project-output", "stage", "journal")}
    for root in roots.values():
        root.mkdir(parents=True)
    client = Client(roots["comfy-output"], **client_values)
    config = LocalComfyImageGenerationConfig(
        endpoint=client.endpoint,
        workflow_path=default_flux1_schnell_fp8_workflow_path(),
        workflow_sha256=FLUX1_SCHNELL_FP8_WORKFLOW_SHA256,
        comfy_output_root=roots["comfy-output"],
        project_output_root=roots["project-output"],
        staging_root=roots["stage"],
        dispatch_journal_root=roots["journal"],
        route_id="local-image", provider_id="comfy-image", model_id="flux-schnell-fp8",
        width=64, height=64, steps=1, poll_interval_seconds=0.1,
        completion_timeout_seconds=2, max_output_bytes=1024 * 1024,
    )
    port = LocalComfyTextToImagePort(
        config=config, client=client,
        resource_policy=ComfyResourcePolicy(
            min_free_vram_bytes=1, min_free_ram_bytes=1, min_free_disk_bytes=0,
        ),
        sleeper=lambda _seconds: None,
    )
    route = ModelRoute(
        "local-image", AiWorkload.IMAGE, ProviderFamily.COMFYUI,
        "comfy-image", "flux-schnell-fp8", CostClass.LOCAL_FREE_AI,
        capabilities=("TEXT_TO_IMAGE",),
    )
    prompt = "cinematic city at dawn"
    request = LocalGenerationExecutionRequest(
        "EXEC-IMAGE-1", "QUEUE-IMAGE-1", "scene-1", "slot-start",
        "TEXT_TO_IMAGE", prompt, sha256_bytes(prompt.encode()), (),
        "rights://project/scene-1",
    )
    return port, client, route, request, roots


def test_packaged_flux_workflow_is_checksum_closed_and_body_free():
    path = default_flux1_schnell_fp8_workflow_path()
    value = json.loads(path.read_text(encoding="utf-8"))
    assert sha256_bytes(canonical_json_bytes(value)) == FLUX1_SCHNELL_FP8_WORKFLOW_SHA256
    assert "{{PROMPT}}" in path.read_text(encoding="utf-8")
    assert "cinematic city" not in path.read_text(encoding="utf-8")


def test_image_preflight_is_read_only_and_never_dispatches(tmp_path: Path):
    port, client, _route, request, roots = fixture(tmp_path)
    result = port.preflight().as_dict()
    assert result["route_id"] == "local-image"
    assert result["model_id"] == "flux-schnell-fp8"
    assert result["dispatch_performed"] is False
    assert result["journal_created"] is False
    assert client.queued == 0
    assert list(roots["journal"].iterdir()) == []
    assert request.prompt_text not in json.dumps(result)


def test_local_flux_port_publishes_one_structurally_verified_png(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    result = port.execute(route, request)
    assert client.queued == 1
    assert client.workflow["2"]["inputs"]["text"] == request.prompt_text
    assert client.workflow["4"]["inputs"]["width"] == 64
    assert result.media_kind == "IMAGE"
    assert result.output_ref == "project-output://generated/EXEC-IMAGE-1/result.png"
    output = roots["project-output"] / "generated" / "EXEC-IMAGE-1" / "result.png"
    assert output.read_bytes() == png_bytes()
    journal = json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text(encoding="utf-8"))
    assert journal["state"] == "COMPLETED"
    assert request.prompt_text not in json.dumps(journal)


@pytest.mark.parametrize(
    ("client_values", "code"),
    (
        ({"corrupt": True}, "ERR_GENERATION_COMFY_IMAGE_DECODE"),
        ({"dimensions": (32, 64)}, "ERR_GENERATION_COMFY_IMAGE_DIMENSIONS"),
        ({"suffix": ".jpg"}, "ERR_GENERATION_COMFY_IMAGE_SUFFIX"),
        ({"images": 2}, "ERR_GENERATION_COMFY_IMAGE_OUTPUT_AMBIGUOUS"),
    ),
)
def test_invalid_image_output_is_terminal_failed_before_canonical_completion(tmp_path: Path, client_values, code):
    port, client, route, request, roots = fixture(tmp_path, **client_values)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == code
    assert client.queued == 1
    assert not (roots["project-output"] / "generated" / "EXEC-IMAGE-1" / "result.png").exists()
    journal = json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text(encoding="utf-8"))
    assert journal["state"] == "FAILED"


def test_paid_or_input_bound_route_fails_before_dispatch(tmp_path: Path):
    port, client, route, request, _roots = fixture(tmp_path)
    paid = ModelRoute(
        route.route_id, route.workload, route.provider_family, route.provider_id,
        route.model_id, CostClass.CLOUD_PAID_AI,
        credential_ref="credential://paid/key", capabilities=route.capabilities,
    )
    with pytest.raises(ProductError) as exc:
        port.execute(paid, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_ROUTE"
    bound = LocalGenerationExecutionRequest(
        request.execution_id, request.queue_entry_id, request.scene_id,
        request.slot_id, request.capability, request.prompt_text,
        request.prompt_sha256, ({"asset_id": "asset-1"},),
        request.rights_authorization_ref,
    )
    with pytest.raises(ProductError) as exc:
        port.execute(route, bound)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_ROUTE"
    assert client.queued == 0


def test_post_dispatch_history_failure_is_uncertain_and_never_replayed(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.history_error = ProductError("ERR_PROVIDER_COMFY_UNREACHABLE", "offline")
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_HISTORY_UNCERTAIN"
    assert exc.value.details["automatic_retry_allowed"] is False
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "QUEUED"
    with pytest.raises(ProductError) as replay:
        port.execute(route, request)
    assert replay.value.code == "ERR_GENERATION_COMFY_IMAGE_ALREADY_DISPATCHED"
    assert client.queued == 1


def test_recovery_reads_stored_prompt_without_queueing_again(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.history_error = ProductError("ERR_PROVIDER_COMFY_UNREACHABLE", "offline")
    with pytest.raises(ProductError):
        port.execute(route, request)
    client.history_error = None
    result = port.recover(route, request)
    assert result.media_kind == "IMAGE"
    assert result.provider_operation_id == "prompt-image-1"
    assert client.queued == 1
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "COMPLETED"


def test_recovery_rejects_checksum_valid_identity_tamper(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.history_error = ProductError("ERR_PROVIDER_COMFY_UNREACHABLE", "offline")
    with pytest.raises(ProductError):
        port.execute(route, request)
    path = roots["journal"] / "EXEC-IMAGE-1.json"
    value = json.loads(path.read_text())
    value["model_id"] = "other-model"
    body = {key: item for key, item in value.items() if key != "journal_sha256"}
    value["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        port.recover(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_RECOVERY_IDENTITY"
    assert client.queued == 1


def test_runtime_output_root_drift_fails_before_queue(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = client.system_stats

    def drifted():
        value = original()
        index = value["system"]["argv"].index("--output-directory")
        value["system"]["argv"][index + 1] = str(tmp_path / "other-output")
        return value

    client.system_stats = drifted
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_RUNTIME_OUTPUT"
    assert client.queued == 0
    assert list(roots["journal"].iterdir()) == []


def test_post_copy_corruption_is_rejected_before_terminal_completion(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    from ai_video_production import local_comfy_image_generation_port as module
    original = module._PinnedDirectory.write_atomic

    def corrupt_write(directory, temporary, target, data):
        result = original(directory, temporary, target, data)
        if target == "result.png":
            if directory.fd is not None:
                descriptor = module.os.open(target, module.os.O_WRONLY, dir_fd=directory.fd)
                try:
                    module.os.write(descriptor, b"corrupt-after-copy")
                finally:
                    module.os.close(descriptor)
            else:
                (directory.path / target).write_bytes(b"corrupt-after-copy")
        return result

    monkeypatch.setattr(module._PinnedDirectory, "write_atomic", corrupt_write)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_DECODE"
    assert client.queued == 1
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "FAILED"


@pytest.mark.parametrize("payload", (
    png_bytes() + b"trailing-polyglot",
    png_bytes(extra_decoded=b"decompression-overrun"),
    png_bytes()[:-1] + bytes([png_bytes()[-1] ^ 0xFF]),
))
def test_png_polyglot_bomb_or_crc_tamper_is_rejected(tmp_path: Path, payload: bytes):
    port, client, route, request, roots = fixture(tmp_path)
    client.payload = payload
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_DECODE"
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "FAILED"


def test_runtime_root_symlink_replacement_after_composition_fails_before_queue(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = tmp_path / "original-output"
    roots["comfy-output"].rename(original)
    outside = tmp_path / "outside-output"
    outside.mkdir()
    try:
        roots["comfy-output"].symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_OUTPUT_ROOT"
    assert client.queued == 0
    assert list(outside.iterdir()) == []


def test_prompt_bearing_png_metadata_is_rejected_before_publication(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.payload = png_with_text(request.prompt_text)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_METADATA"
    assert request.prompt_text not in json.dumps(
        json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())
    )
    assert not (roots["project-output"] / "generated" / "EXEC-IMAGE-1" / "result.png").exists()


def test_queue_success_journal_failure_is_uncertain_and_not_requeued(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    original = port._advance

    def fail_queue(path, expected, **values):
        if values["state"] == "QUEUED":
            raise ProductError("ERR_INJECTED_JOURNAL_WRITE", "injected")
        return original(path, expected, **values)

    monkeypatch.setattr(port, "_advance", fail_queue)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_QUEUE_JOURNAL_UNCERTAIN"
    assert exc.value.details["execution_state_uncertain"] is True
    assert exc.value.details["provider_operation_id"] == "prompt-image-1"
    assert client.queued == 1
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "PREPARED"
    with pytest.raises(ProductError) as replay:
        port.execute(route, request)
    assert replay.value.code == "ERR_GENERATION_COMFY_IMAGE_ALREADY_DISPATCHED"
    assert client.queued == 1


def test_crash_left_exact_queued_temp_recovers_prompt_without_requeue(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    from ai_video_production import local_comfy_image_generation_port as module
    original = module._PinnedDirectory.write_atomic
    crashed = False

    def crash_after_queued_temp_fsync(directory, temporary, target, data):
        nonlocal crashed
        value = json.loads(data.decode("utf-8")) if target.endswith(".json") else {}
        if value.get("state") == "QUEUED" and not crashed:
            crashed = True
            if directory.fd is None:
                pytest.skip("POSIX directory-fsync crash injection required")
            descriptor = module.os.open(
                temporary,
                module.os.O_WRONLY | module.os.O_CREAT | module.os.O_EXCL | module.os.O_NOFOLLOW,
                0o600,
                dir_fd=directory.fd,
            )
            try:
                module.os.write(descriptor, data)
                module.os.fsync(descriptor)
            finally:
                module.os.close(descriptor)
            module.os.fsync(directory.fd)
            raise ProductError("ERR_INJECTED_AFTER_QUEUED_TEMP_FSYNC", "injected")
        return original(directory, temporary, target, data)

    monkeypatch.setattr(module._PinnedDirectory, "write_atomic", crash_after_queued_temp_fsync)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_QUEUE_JOURNAL_UNCERTAIN"
    journal_path = roots["journal"] / "EXEC-IMAGE-1.json"
    temporary = roots["journal"] / ".EXEC-IMAGE-1.json.tmp"
    assert json.loads(journal_path.read_text())["state"] == "PREPARED"
    assert json.loads(temporary.read_text())["state"] == "QUEUED"

    monkeypatch.setattr(module._PinnedDirectory, "write_atomic", original)
    result = port.recover(route, request)
    assert result.provider_operation_id == "prompt-image-1"
    assert json.loads(journal_path.read_text())["state"] == "COMPLETED"
    assert not temporary.exists()
    assert client.queued == 1


def test_completed_output_journal_failure_recovers_without_requeue(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    original = port._advance
    failed_once = False

    def fail_completed(path, expected, **values):
        nonlocal failed_once
        if values["state"] == "COMPLETED" and not failed_once:
            failed_once = True
            raise ProductError("ERR_INJECTED_JOURNAL_WRITE", "injected")
        return original(path, expected, **values)

    monkeypatch.setattr(port, "_advance", fail_completed)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_COMPLETION_JOURNAL_UNCERTAIN"
    assert exc.value.details["execution_state_uncertain"] is True
    target = roots["project-output"] / "generated" / "EXEC-IMAGE-1" / "result.png"
    assert target.is_file()
    result = port.recover(route, request)
    assert result.output_ref == "project-output://generated/EXEC-IMAGE-1/result.png"
    assert client.queued == 1
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "COMPLETED"


def test_crash_left_exact_journal_temp_is_reconciled_without_requeue(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    from ai_video_production import local_comfy_image_generation_port as module
    original = module._PinnedDirectory.write_atomic
    crashed = False

    def crash_after_temp_fsync(directory, temporary, target, data):
        nonlocal crashed
        value = json.loads(data.decode("utf-8")) if target.endswith(".json") else {}
        if value.get("state") == "COMPLETED" and not crashed:
            crashed = True
            if directory.fd is None:
                pytest.skip("POSIX directory-fsync crash injection required")
            descriptor = module.os.open(
                temporary,
                module.os.O_WRONLY | module.os.O_CREAT | module.os.O_EXCL | module.os.O_NOFOLLOW,
                0o600,
                dir_fd=directory.fd,
            )
            try:
                module.os.write(descriptor, data)
                module.os.fsync(descriptor)
            finally:
                module.os.close(descriptor)
            module.os.fsync(directory.fd)
            raise ProductError("ERR_INJECTED_AFTER_TEMP_FSYNC", "injected")
        return original(directory, temporary, target, data)

    monkeypatch.setattr(module._PinnedDirectory, "write_atomic", crash_after_temp_fsync)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_COMPLETION_JOURNAL_UNCERTAIN"
    journal_path = roots["journal"] / "EXEC-IMAGE-1.json"
    temporary = roots["journal"] / ".EXEC-IMAGE-1.json.tmp"
    assert json.loads(journal_path.read_text())["state"] == "QUEUED"
    assert json.loads(temporary.read_text())["state"] == "COMPLETED"

    monkeypatch.setattr(module._PinnedDirectory, "write_atomic", original)
    result = port.recover(route, request)
    assert result.output_ref == "project-output://generated/EXEC-IMAGE-1/result.png"
    assert json.loads(journal_path.read_text())["state"] == "COMPLETED"
    assert not temporary.exists()
    assert client.queued == 1


def test_journal_temp_name_substitution_never_returns_terminal_success(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    from ai_video_production import local_comfy_image_generation_port as module
    journal_moves = 0

    if module.os.name == "nt":
        original_windows_move = module._windows_move_replace_write_through

        def substitute_windows(source: Path, target: Path) -> bool:
            nonlocal journal_moves
            if target.name.endswith(".json"):
                journal_moves += 1
                if journal_moves == 3:
                    source.unlink()
                    source.write_bytes(b"{}")
            return original_windows_move(source, target)

        monkeypatch.setattr(module, "_windows_move_replace_write_through", substitute_windows)
    else:
        original_replace = module.os.replace

        def substitute_posix(source, target, *args, **kwargs):
            nonlocal journal_moves
            if isinstance(target, str) and target.endswith(".json"):
                journal_moves += 1
                if journal_moves == 3:
                    directory_fd = kwargs["src_dir_fd"]
                    module.os.unlink(source, dir_fd=directory_fd)
                    descriptor = module.os.open(
                        source,
                        module.os.O_WRONLY | module.os.O_CREAT | module.os.O_EXCL | module.os.O_NOFOLLOW,
                        0o600,
                        dir_fd=directory_fd,
                    )
                    try:
                        module.os.write(descriptor, b"{}")
                        module.os.fsync(descriptor)
                    finally:
                        module.os.close(descriptor)
            return original_replace(source, target, *args, **kwargs)

        monkeypatch.setattr(module.os, "replace", substitute_posix)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_COMPLETION_JOURNAL_UNCERTAIN"
    assert client.queued == 1
    assert (roots["journal"] / "EXEC-IMAGE-1.json").read_bytes() == b"{}"


def test_running_status_with_image_descriptor_does_not_terminalize(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.history_error = ProductError("ERR_PROVIDER_COMFY_UNREACHABLE", "offline")
    with pytest.raises(ProductError):
        port.execute(route, request)
    client.history_error = None
    client.status = "running"
    with pytest.raises(ProductError) as exc:
        port.recover(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_RECOVERY_PENDING"
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "QUEUED"
    assert not (roots["project-output"] / "generated").exists()


def test_execute_running_status_with_image_descriptor_times_out_without_completion(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.status = "running"
    port._monotonic = iter((0, 0, 1, 3)).__next__
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_TIMEOUT_UNCERTAIN"
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "QUEUED"
    assert not (roots["project-output"] / "generated").exists()


def test_completed_journal_cannot_project_another_execution_output(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    port.execute(route, request)
    other = roots["project-output"] / "generated" / "OTHER" / "result.png"
    other.parent.mkdir()
    other.write_bytes(png_bytes())
    path = roots["journal"] / "EXEC-IMAGE-1.json"
    value = json.loads(path.read_text())
    value["output_ref"] = "project-output://generated/OTHER/result.png"
    value["output_sha256"] = sha256_bytes(other.read_bytes())
    body = {key: item for key, item in value.items() if key != "journal_sha256"}
    value["journal_sha256"] = sha256_bytes(canonical_json_bytes(body))
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductError) as exc:
        port.recover(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_JOURNAL"
    assert client.queued == 1


def test_package_workflow_and_exact_8188_are_mandatory(tmp_path: Path):
    roots = [tmp_path / name for name in ("out", "project", "stage", "journal")]
    for root in roots:
        root.mkdir()
    copied = tmp_path / "copied-workflow.json"
    copied.write_bytes(default_flux1_schnell_fp8_workflow_path().read_bytes())
    config = LocalComfyImageGenerationConfig(
        "http://127.0.0.1:8188", copied, FLUX1_SCHNELL_FP8_WORKFLOW_SHA256,
        *roots, "local-image", "comfy-image", "flux-schnell-fp8",
    )
    with pytest.raises(ProductError) as workflow:
        LocalComfyTextToImagePort(config=config, client=Client(roots[0]))
    assert workflow.value.code == "ERR_GENERATION_COMFY_IMAGE_WORKFLOW_BINDING"
    with pytest.raises(ValueError):
        LocalComfyImageGenerationConfig(
            "http://127.0.0.1:8189", default_flux1_schnell_fp8_workflow_path(),
            FLUX1_SCHNELL_FP8_WORKFLOW_SHA256, *roots,
            "local-image", "comfy-image", "flux-schnell-fp8",
        )


def test_runtime_requires_disable_metadata_before_dispatch(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = client.system_stats

    def unsafe():
        value = original()
        value["system"]["argv"].remove("--disable-metadata")
        return value

    client.system_stats = unsafe
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_RUNTIME_IDENTITY"
    assert client.queued == 0
    assert list(roots["journal"].iterdir()) == []


def test_rgb_flux_png_rejects_palette_chunk(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    client.payload = png_with_palette()
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_METADATA"
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "FAILED"


@pytest.mark.parametrize(("payload", "code"), (
    (b"", "ERR_GENERATION_COMFY_IMAGE_SIZE"),
    (b"x" * (1024 * 1024 + 1), "ERR_GENERATION_COMFY_IMAGE_SIZE"),
), ids=("zero", "oversize"))
def test_zero_or_oversize_output_never_completes(tmp_path: Path, payload: bytes, code: str):
    port, client, route, request, roots = fixture(tmp_path)
    client.payload = payload
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == code
    assert json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "FAILED"


def test_execution_output_parent_symlink_is_rejected(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = client.history
    outside = tmp_path / "outside-execution"
    outside.mkdir()

    def symlinked(prompt_id):
        owned = roots["comfy-output"] / "bai-task013-image"
        execution = owned / "EXEC-IMAGE-1"
        try:
            execution.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
        return original(prompt_id)

    client.history = symlinked
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_DIRECTORY"
    assert not (roots["project-output"] / "generated").exists()


def test_source_parent_swap_between_pins_cannot_read_outside(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    from ai_video_production import local_comfy_image_generation_port as module
    original = module._PinnedDirectory.pin_child
    outside = tmp_path / "outside-source-tree"
    outside_execution = outside / "EXEC-IMAGE-1"
    outside_execution.mkdir(parents=True)
    outside_payload = png_bytes()
    outside_file = outside_execution / "result-0.png"
    outside_file.write_bytes(outside_payload)
    swapped = False

    def swap(parent, name):
        nonlocal swapped
        if parent.path.name == "bai-task013-image" and name == "EXEC-IMAGE-1" and not swapped:
            swapped = True
            held = parent.path.with_name("bai-task013-image-held")
            try:
                parent.path.rename(held)
                parent.path.symlink_to(outside, target_is_directory=True)
            except OSError:
                pytest.skip("mid-operation directory replacement unavailable")
        return original(parent, name)

    monkeypatch.setattr(module._PinnedDirectory, "pin_child", swap)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_DIRECTORY"
    assert outside_file.read_bytes() == outside_payload
    assert not (roots["project-output"] / "generated").exists()


def test_target_parent_swap_between_pins_cannot_write_outside(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    from ai_video_production import local_comfy_image_generation_port as module
    original = module._PinnedDirectory.pin_child
    outside = tmp_path / "outside-target-tree"
    (outside / "EXEC-IMAGE-1").mkdir(parents=True)
    swapped = False

    def swap(parent, name):
        nonlocal swapped
        if parent.path.name == "generated" and name == "EXEC-IMAGE-1" and not swapped:
            swapped = True
            held = parent.path.with_name("generated-held")
            try:
                parent.path.rename(held)
                parent.path.symlink_to(outside, target_is_directory=True)
            except OSError:
                pytest.skip("mid-operation directory replacement unavailable")
        return original(parent, name)

    monkeypatch.setattr(module._PinnedDirectory, "pin_child", swap)
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_DIRECTORY"
    assert list((outside / "EXEC-IMAGE-1").iterdir()) == []


def test_completed_recovery_parent_swap_cannot_read_outside(tmp_path: Path, monkeypatch):
    port, client, route, request, roots = fixture(tmp_path)
    port.execute(route, request)
    from ai_video_production import local_comfy_image_generation_port as module
    original = module._PinnedDirectory.pin_child
    outside = tmp_path / "outside-recovery-tree"
    outside_execution = outside / "EXEC-IMAGE-1"
    outside_execution.mkdir(parents=True)
    outside_file = outside_execution / "result.png"
    outside_file.write_bytes(b"not-the-canonical-image")
    swapped = False

    def swap(parent, name):
        nonlocal swapped
        if parent.path.name == "generated" and name == "EXEC-IMAGE-1" and not swapped:
            swapped = True
            held = parent.path.with_name("generated-recovery-held")
            try:
                parent.path.rename(held)
                parent.path.symlink_to(outside, target_is_directory=True)
            except OSError:
                pytest.skip("mid-operation directory replacement unavailable")
        return original(parent, name)

    monkeypatch.setattr(module._PinnedDirectory, "pin_child", swap)
    with pytest.raises(ProductError) as exc:
        port.recover(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_DIRECTORY"
    assert outside_file.read_bytes() == b"not-the-canonical-image"
    assert client.queued == 1


def test_journal_root_symlink_replacement_fails_before_queue(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    original = tmp_path / "original-journal"
    roots["journal"].rename(original)
    outside = tmp_path / "outside-journal"
    outside.mkdir()
    try:
        roots["journal"].symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    with pytest.raises(ProductError) as exc:
        port.execute(route, request)
    assert exc.value.code == "ERR_GENERATION_COMFY_IMAGE_JOURNAL_ROOT"
    assert client.queued == 0
    assert list(outside.iterdir()) == []


def test_completed_recovery_is_read_only_and_failed_recovery_stays_failed(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path)
    completed = port.execute(route, request)
    recovered = port.recover(route, request)
    assert recovered.output_ref == completed.output_ref
    assert client.queued == 1

    failed_port, failed_client, failed_route, failed_request, failed_roots = fixture(
        tmp_path / "failed", corrupt=True
    )
    with pytest.raises(ProductError):
        failed_port.execute(failed_route, failed_request)
    with pytest.raises(ProductError) as failed:
        failed_port.recover(failed_route, failed_request)
    assert failed.value.code == "ERR_GENERATION_COMFY_IMAGE_RECOVERY_FAILED"
    assert failed_client.queued == 1
    assert json.loads((failed_roots["journal"] / "EXEC-IMAGE-1.json").read_text())["state"] == "FAILED"


def test_first_recovery_output_failure_signals_terminal_after_durable_failed_journal(tmp_path: Path):
    port, client, route, request, roots = fixture(tmp_path, images=2)
    path, journal = port._reserve(route, request)
    port._advance(path, journal, state="QUEUED", prompt_id="prompt-image-1")
    with pytest.raises(ProductError) as failed:
        port.recover(route, request)
    assert failed.value.code == "ERR_GENERATION_COMFY_IMAGE_OUTPUT_AMBIGUOUS"
    assert failed.value.details["execution_state_terminal_failure"] is True
    stored = json.loads((roots["journal"] / "EXEC-IMAGE-1.json").read_text())
    assert stored["state"] == "FAILED"
    assert client.queued == 0


def test_config_rejects_non_loopback_endpoint(tmp_path: Path):
    roots = [tmp_path / name for name in ("out", "project", "stage", "journal")]
    for root in roots:
        root.mkdir()
    with pytest.raises(ValueError):
        LocalComfyImageGenerationConfig(
            "http://localhost:8188", default_flux1_schnell_fp8_workflow_path(),
            FLUX1_SCHNELL_FP8_WORKFLOW_SHA256, *roots,
            "local-image", "comfy-image", "flux-schnell-fp8",
        )
