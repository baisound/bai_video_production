from __future__ import annotations

import hashlib
import json
import multiprocessing
from pathlib import Path
from threading import Event, Thread
from time import sleep

import pytest

from ai_video_production.errors import ProductError
from ai_video_production.faster_whisper_asr import FasterWhisperConfig, LocalTranscriptionService
from ai_video_production.profile import ProfileSnapshot
from ai_video_production.store import SQLiteProductStore
from ai_video_production.serialization import canonical_json_bytes, sha256_bytes
from ai_video_production.subtitles import TranscriptManifest, TranscriptSegment
from ai_video_production.task036_product_ports import Task036LocalTranscriptionPort


ASSET_ID = "ASSET-00000000000000000000000000"
PROJECT_ID = "project-1"
JOB_ID = "JOB-00000000000000000000000000"
PROCESS_COMPLETION_TIMEOUT_SECONDS = 30
PROCESS_CLEANUP_TIMEOUT_SECONDS = 5
THREAD_COMPLETION_TIMEOUT_SECONDS = 30


def file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class FakeProvider:
    provider_id = "faster-whisper"
    model_id = "cached-local-model"
    config = FasterWhisperConfig(model="cached-local-model", allow_model_download=False)

    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, request):
        self.calls += 1
        return TranscriptManifest(
            request.source_asset_id,
            "ja",
            self.provider_id,
            self.model_id,
            (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
        )


class ProcessProvider(FakeProvider):
    def __init__(self, marker: Path) -> None:
        super().__init__()
        self.marker = marker

    def transcribe(self, request):
        with self.marker.open("a", encoding="utf-8") as handle:
            handle.write("provider-call\n")
            handle.flush()
        sleep(0.2)
        return super().transcribe(request)


def make_port(provider, root: Path) -> Task036LocalTranscriptionPort:
    output = root / "transcription"
    output.mkdir(exist_ok=True)
    store = SQLiteProductStore(root / "product.sqlite3")
    try:
        store.get_job_state(JOB_ID)
    except ProductError:
        profile = ProfileSnapshot.create("task036-test", "1.0.0", {})
        store.create_job(profile.profile_snapshot_id, job_id=JOB_ID)
    return Task036LocalTranscriptionPort(provider, output, store, JOB_ID)


def process_execute(source: str, root: str, marker: str, admission_barrier, result_queue) -> None:
    provider = ProcessProvider(Path(marker))
    store = SQLiteProductStore(
        Path(root) / "product.sqlite3", require_existing=True, required_job_id=JOB_ID,
    )
    port = Task036LocalTranscriptionPort(
        provider, Path(root) / "transcription", store, JOB_ID,
    )
    try:
        admission_barrier.wait(10)
        execute(port, Path(source))
        result_queue.put("COMPLETED")
    except ProductError as exc:
        result_queue.put(exc.code)


def execute(port: Task036LocalTranscriptionPort, source: Path):
    return port.transcribe_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=file_sha(source),
    )


def test_completed_durable_result_requires_explicit_recovery_without_provider_replay(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)

    first = execute(port, source)
    restarted = make_port(provider, tmp_path)
    with pytest.raises(ProductError) as retry:
        execute(restarted, source)
    second = restarted.recover_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=file_sha(source),
    )

    assert provider.calls == 1
    assert retry.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED"
    assert first.provider_execution_started is True
    assert first.recovered_from_durable_result is False
    assert second.provider_execution_started is False
    assert second.recovered_from_durable_result is True
    assert first.transcript.to_dict()["manifest_sha256"] == second.transcript.to_dict()["manifest_sha256"]


def test_durable_operation_is_scoped_to_exact_project_identity(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)
    execute(port, source)

    assert port.recovery_required(PROJECT_ID, ASSET_ID, file_sha(source)) is True
    assert port.recovery_required("project-2", ASSET_ID, file_sha(source)) is False
    with pytest.raises(ProductError) as missing:
        port.recover_local_media(
            project_id="project-2",
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=file_sha(source),
        )
    assert missing.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_NOT_AVAILABLE"
    assert provider.calls == 1


def test_cross_instance_admission_executes_provider_exactly_once(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    entered, release = Event(), Event()

    class BlockingProvider(FakeProvider):
        def transcribe(self, request):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return TranscriptManifest(
                request.source_asset_id, "ja", self.provider_id, self.model_id,
                (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
            )

    provider = BlockingProvider()
    ports = (make_port(provider, tmp_path), make_port(provider, tmp_path))
    results = []
    errors = []

    def invoke(port):
        try:
            results.append(execute(port, source))
        except ProductError as exc:
            errors.append(exc.code)

    threads = [Thread(target=invoke, args=(port,)) for port in ports]
    threads[0].start()
    assert entered.wait(5)
    threads[1].start()
    release.set()
    for thread in threads:
        thread.join(THREAD_COMPLETION_TIMEOUT_SECONDS)
        assert not thread.is_alive()
    assert provider.calls == 1
    assert [item.provider_execution_started for item in results] == [True]
    assert errors == ["ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED"]


def test_cross_process_admission_executes_provider_exactly_once(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    seed_port = make_port(FakeProvider(), tmp_path)
    seed_port.store.close()
    marker = tmp_path / "provider-calls.txt"
    context = multiprocessing.get_context("spawn")
    admission_barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=process_execute,
            args=(str(source), str(tmp_path), str(marker), admission_barrier, results),
        )
        for _ in range(2)
    ]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(PROCESS_COMPLETION_TIMEOUT_SECONDS)
            assert not process.is_alive(), "spawned transcription process exceeded completion timeout"
            assert process.exitcode == 0

        observed = sorted(results.get(timeout=2) for _ in range(2))
        assert observed == ["COMPLETED", "ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED"]
        assert marker.read_text(encoding="utf-8").splitlines() == ["provider-call"]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(PROCESS_CLEANUP_TIMEOUT_SECONDS)
            if process.is_alive():
                process.kill()
                process.join(PROCESS_CLEANUP_TIMEOUT_SECONDS)
            assert not process.is_alive(), "spawned transcription process could not be stopped"


def test_source_mismatch_and_symlink_fail_before_provider(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)

    with pytest.raises(ProductError) as mismatch:
        port.transcribe_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256="sha256:" + "0" * 64,
        )
    assert mismatch.value.code == "ERR_TASK036_TRANSCRIPTION_SOURCE_MISMATCH"
    assert provider.calls == 0

    link = tmp_path / "link.mp4"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ProductError) as symlink:
        port.transcribe_local_media(
            project_id=PROJECT_ID,
            source_path=link,
            source_asset_id=ASSET_ID,
            source_asset_sha256=file_sha(source),
        )
    assert symlink.value.code == "ERR_TASK036_TRANSCRIPTION_SOURCE_INVALID"
    assert provider.calls == 0


@pytest.mark.parametrize("download_value", [True, None])
def test_provider_download_authority_must_be_exactly_false_before_execution(
    tmp_path: Path, download_value,
) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")

    class UnsafeProvider(FakeProvider):
        config = object() if download_value is None else FasterWhisperConfig(
            model="cached-local-model", allow_model_download=download_value,
        )

    provider = UnsafeProvider()
    port = make_port(provider, tmp_path)
    with pytest.raises(ProductError) as unauthorized:
        execute(port, source)
    assert unauthorized.value.code == "ERR_TASK036_TRANSCRIPTION_PROVIDER_NOT_AUTHORIZED"
    assert provider.calls == 0
    assert not (tmp_path / "transcription" / ".task036-transcription").exists()


@pytest.mark.parametrize(
    "tamper", ["output-root", "publication-root", "transcript", "subtitle", "report"],
)
def test_output_symlinks_fail_closed_without_replacement_or_provider(tmp_path: Path, tamper: str) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    source_sha = file_sha(source)
    output = tmp_path / "transcription"
    outside = tmp_path / "outside"
    outside.mkdir()
    if tamper == "output-root":
        link = output
        link.symlink_to(outside, target_is_directory=True)
    elif tamper == "publication-root":
        output.mkdir()
        link = output / ".task036-publications"
        link.symlink_to(outside, target_is_directory=True)
    else:
        output.mkdir()
        name = {
            "transcript": "transcript.json",
            "subtitle": "subtitles.srt",
            "report": "transcription-report.json",
        }[tamper]
        link = output / name
        link.symlink_to(outside / f"missing-{name}")
    provider = FakeProvider()
    store = SQLiteProductStore(tmp_path / "product.sqlite3")
    profile = ProfileSnapshot.create("task036-test", "1.0.0", {})
    store.create_job(profile.profile_snapshot_id, job_id=JOB_ID)
    port = Task036LocalTranscriptionPort(provider, output, store, JOB_ID)

    with pytest.raises(ProductError) as invalid:
        execute(port, source)
    assert invalid.value.code in {
        "ERR_TASK036_TRANSCRIPTION_PRIVATE_PATH_INVALID",
        "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID",
        "ERR_TASK036_TRANSCRIPTION_PUBLICATION_SET_INVALID",
    }
    assert provider.calls == 0
    assert link.is_symlink()

def test_uncertain_provider_state_blocks_retry_without_explicit_recovery(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")

    class InterruptingProvider(FakeProvider):
        def transcribe(self, request):
            self.calls += 1
            raise KeyboardInterrupt()

    provider = InterruptingProvider()
    port = make_port(provider, tmp_path)
    with pytest.raises(KeyboardInterrupt):
        execute(port, source)
    assert port.recovery_required(PROJECT_ID, ASSET_ID, file_sha(source)) is True
    with pytest.raises(ProductError) as retry:
        execute(port, source)
    assert retry.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_REQUIRED"
    assert provider.calls == 1
    with pytest.raises(ProductError) as incomplete:
        port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=file_sha(source),
        )
    assert incomplete.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"
    assert provider.calls == 1


def test_provider_reads_only_the_stable_snapshot_when_canonical_path_changes_midflight(
    tmp_path: Path,
) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    expected_sha = file_sha(source)

    class MutatingProvider(FakeProvider):
        def transcribe(self, request):
            source.write_bytes(b"different bytes")
            provider_source = Path(request.media_path)
            assert provider_source != source
            assert provider_source.read_bytes() == b"canonical media"
            return super().transcribe(request)

    provider = MutatingProvider()
    port = make_port(provider, tmp_path)
    result = port.transcribe_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=expected_sha,
    )
    assert result.provider_execution_started is True
    assert provider.calls == 1


def test_completed_publication_with_terminal_operation_failure_recovers_without_provider_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)
    original_compare = SQLiteProductStore.compare_and_set_operation_status
    failed_once = False

    def fail_completed_operation(self, operation_id, **kwargs):
        nonlocal failed_once
        if kwargs.get("status") == "COMPLETED" and not failed_once:
            failed_once = True
            raise OSError("injected terminal operation failure")
        return original_compare(self, operation_id, **kwargs)

    monkeypatch.setattr(
        SQLiteProductStore,
        "compare_and_set_operation_status",
        fail_completed_operation,
    )
    with pytest.raises(OSError):
        execute(port, source)
    assert provider.calls == 1
    assert port.recovery_required(PROJECT_ID, ASSET_ID, file_sha(source)) is True

    recovered = port.recover_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=file_sha(source),
    )
    assert recovered.provider_execution_started is False
    assert recovered.recovered_from_durable_result is True
    assert provider.calls == 1


def test_recovery_rejects_checksum_valid_foreign_provider_publication(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)
    execute(port, source)
    transcript_path = tmp_path / "transcription" / "transcript.json"
    document = json.loads(transcript_path.read_text(encoding="utf-8"))
    body = dict(document)
    body.pop("manifest_sha256")
    body["provider_id"] = "foreign-provider"
    body["manifest_sha256"] = sha256_bytes(canonical_json_bytes(body))
    transcript_path.write_bytes(canonical_json_bytes(body))

    with pytest.raises(ProductError) as rejected:
        port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=file_sha(source),
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"
    assert provider.calls == 1


def test_recovery_applies_resource_bound_before_parsing_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)
    execute(port, source)
    monkeypatch.setattr(Task036LocalTranscriptionPort, "_TRANSCRIPT_MAX_BYTES", 8)

    with pytest.raises(ProductError) as rejected:
        port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=file_sha(source),
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"
    assert provider.calls == 1


def test_partial_fixed_output_promotion_rolls_forward_from_bound_immutable_set_without_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)
    from ai_video_production.local_comfy_image_generation_port import _PinnedDirectory

    original_write = _PinnedDirectory.write_atomic
    failed = False

    def fail_second_fixed_file(self, temporary, target, data):
        nonlocal failed
        if self.path == port.output_directory and target == "subtitles.srt" and not failed:
            failed = True
            raise OSError("injected fixed-set interruption")
        return original_write(self, temporary, target, data)

    monkeypatch.setattr(_PinnedDirectory, "write_atomic", fail_second_fixed_file)
    with pytest.raises(ProductError) as interrupted:
        execute(port, source)
    assert interrupted.value.code == "ERR_TASK036_TRANSCRIPTION_PUBLICATION_INVALID"
    assert provider.calls == 1
    operation = port.store.find_operation(
        JOB_ID, port._operation_key(PROJECT_ID, ASSET_ID, file_sha(source)),
    )
    assert operation is not None
    assert operation.status == "PARTIAL"
    assert operation.result_ref is not None

    monkeypatch.setattr(_PinnedDirectory, "write_atomic", original_write)
    recovered = port.recover_local_media(
        project_id=PROJECT_ID,
        source_path=source,
        source_asset_id=ASSET_ID,
        source_asset_sha256=file_sha(source),
    )
    assert recovered.recovered_from_durable_result is True
    assert recovered.publication_set_sha256 == operation.result_ref
    assert provider.calls == 1


def test_in_progress_operation_never_infers_success_from_fabricated_fixed_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")

    class InterruptingProvider(FakeProvider):
        def transcribe(self, request):
            self.calls += 1
            raise KeyboardInterrupt()

    provider = InterruptingProvider()
    port = make_port(provider, tmp_path)
    with pytest.raises(KeyboardInterrupt):
        execute(port, source)
    forged = TranscriptManifest(
        ASSET_ID, "ja", "faster-whisper", "cached-local-model",
        (TranscriptSegment("seg-000001", 0, 1_000_000, "forged text"),),
    )
    LocalTranscriptionService.publish(
        forged, port.output_directory, timeline_rate=port.timeline_rate,
        model_download_authorized=False,
    )
    with pytest.raises(ProductError) as rejected:
        port.recover_local_media(
            project_id=PROJECT_ID,
            source_path=source,
            source_asset_id=ASSET_ID,
            source_asset_sha256=file_sha(source),
        )
    assert rejected.value.code == "ERR_TASK036_TRANSCRIPTION_RECOVERY_INCOMPLETE"
    assert provider.calls == 1


def test_different_sources_share_one_project_fixed_output_slot(tmp_path: Path) -> None:
    source_a = tmp_path / "a.mp4"
    source_b = tmp_path / "b.mp4"
    source_a.write_bytes(b"source a")
    source_b.write_bytes(b"source b")
    entered, release = Event(), Event()

    class BlockingProvider(FakeProvider):
        def transcribe(self, request):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return TranscriptManifest(
                request.source_asset_id, "ja", self.provider_id, self.model_id,
                (TranscriptSegment("seg-000001", 0, 1_000_000, "private text"),),
            )

    provider = BlockingProvider()
    first = make_port(provider, tmp_path)
    second = make_port(provider, tmp_path)
    first_result = []

    thread = Thread(target=lambda: first_result.append(execute(first, source_a)))
    thread.start()
    assert entered.wait(5)
    with pytest.raises(ProductError) as busy:
        second.transcribe_local_media(
            project_id=PROJECT_ID,
            source_path=source_b,
            source_asset_id="ASSET-11111111111111111111111111",
            source_asset_sha256=file_sha(source_b),
        )
    release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert busy.value.code == "ERR_TASK036_TRANSCRIPTION_OUTPUT_SLOT_BUSY"
    assert provider.calls == 1
    assert len(first_result) == 1
    waiting = second.store.find_operation(
        JOB_ID,
        second._operation_key(
            PROJECT_ID, "ASSET-11111111111111111111111111", file_sha(source_b),
        ),
    )
    assert waiting is not None
    assert waiting.status == "PENDING"
    assert waiting.result_ref is None


def test_asr_configuration_is_part_of_durable_operation_identity(tmp_path: Path) -> None:
    source = tmp_path / "canonical.mp4"
    source.write_bytes(b"canonical media")
    provider = FakeProvider()
    original = make_port(provider, tmp_path)
    execute(original, source)

    class ChangedProvider(FakeProvider):
        config = FasterWhisperConfig(
            model="cached-local-model", beam_size=7, allow_model_download=False,
        )

    changed = make_port(ChangedProvider(), tmp_path)
    assert changed.recovery_required(PROJECT_ID, ASSET_ID, file_sha(source)) is False


def test_output_slot_releases_only_after_exact_transcript_binding(tmp_path: Path) -> None:
    source_a = tmp_path / "a.mp4"
    source_b = tmp_path / "b.mp4"
    source_a.write_bytes(b"source a")
    source_b.write_bytes(b"source b")
    provider = FakeProvider()
    port = make_port(provider, tmp_path)
    first = execute(port, source_a)
    assert first.operation_id and first.slot_operation_id and first.publication_set_sha256
    port.finalize_local_media_binding(
        project_id=PROJECT_ID,
        source_asset_id=ASSET_ID,
        source_asset_sha256=file_sha(source_a),
        transcript_manifest_sha256=first.transcript.to_dict()["manifest_sha256"],
        operation_id=first.operation_id,
        slot_operation_id=first.slot_operation_id,
        publication_set_sha256=first.publication_set_sha256,
    )
    second = port.transcribe_local_media(
        project_id=PROJECT_ID,
        source_path=source_b,
        source_asset_id="ASSET-11111111111111111111111111",
        source_asset_sha256=file_sha(source_b),
    )
    assert second.provider_execution_started is True
    assert provider.calls == 2
