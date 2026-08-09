from __future__ import annotations

import io
import json
import math
from pathlib import Path, PureWindowsPath
import wave

import pytest

from ai_video_production import (
    AssetIngestRequest, AssetIngestService, AssetType, AudioAiOperation, AudioAiRequest, AudacityOpenVinoService,
    LogicalPathResolver, PathMapping, PermissionState, ProductError, ProfileSnapshot, RightsStatus,
    SeparationMode, SQLiteProductStore, SourcePathPolicy,
)
from ai_video_production.audacity_openvino_worker import (
    AudacityPipe, _command_eol_for_os_name, _export, build_command, discover_features, separation_parameters, validate_effect_parameters,
)


def write_wav(path: Path, *, frames=8000, value=0):
    with wave.open(str(path),"wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(8000); out.writeframes(bytes([value,0]) * frames)


def make_env(tmp_path, runner):
    incoming=tmp_path/"incoming"; assets=tmp_path/"assets"; jobs=tmp_path/"jobs"
    for p in (incoming,assets,jobs): p.mkdir()
    store=SQLiteProductStore(tmp_path/"db.sqlite3"); ps=ProfileSnapshot.create("t4","1.0.0",{}); job=store.create_job(ps.profile_snapshot_id)
    resolver=LogicalPathResolver([PathMapping("asset://",assets,PureWindowsPath("D:/a")),PathMapping("job://",jobs,PureWindowsPath("D:/j"))])
    ingest=AssetIngestService(store=store,resolver=resolver,source_policy=SourcePathPolicy((incoming,)))
    source=incoming/"source.wav"; write_wav(source)
    asset=ingest.ingest(AssetIngestRequest(job.job_id,source,AssetType.AUDIO,RightsStatus.OWNED,"USER","ing",
        derivative_allowed=PermissionState.ALLOWED)).asset
    return AudacityOpenVinoService(store=store,resolver=resolver,worker_runner=runner),store,resolver,job,asset


def capability(features=None):
    features=features or ["NOISE_SUPPRESSION","MUSIC_SEPARATION","WHISPER_TRANSCRIPTION","MUSIC_GENERATION","AUDIO_SUPER_RESOLUTION"]
    return {"connected":True,"current_track_count":0,"features":{k:{"available":k in features} for k in features}}


def noise_runner(request, work_root, timeout):
    out=Path(request["output_dir"]); out.mkdir(parents=True,exist_ok=True); path=out/"noise-suppressed.wav"; write_wav(path,frames=8100,value=1)
    return {"ok":True,"outputs":[{"role":"noise_suppressed","path":str(path)}],"effect":{"command_id":"OpenVINONoise","parameters":{"Device":"CPU"}},"capabilities":capability()}


def separation_runner(mode):
    def run(request, work_root, timeout):
        out=Path(request["output_dir"]); out.mkdir(parents=True,exist_ok=True)
        roles=["vocals","instrumental"] if mode=="2_STEM" else ["drums","bass","other","vocals"]
        outputs=[]
        for i,role in enumerate(roles,1):
            p=out/f"stem-{role}.wav"; write_wav(p,frames=8000+i,value=i); outputs.append({"role":role,"path":str(p)})
        return {"ok":True,"outputs":outputs,"effect":{"command_id":"OpenVINOSep","parameters":{"Mode":mode}},"capabilities":capability()}
    return run


def test_feature_discovery_uses_openvino_semantics_not_position():
    commands=[{"id":"Other","name":"Noise Suppression"},{"id":"OVNS","name":"OpenVINO Noise Suppression"},{"id":"OVMS","label":"OpenVINO Music Separation"},{"id":"OVW","name":"OpenVINO Whisper Transcription"},{"id":"OVG","name":"OpenVINO Music Generation"},{"id":"OVSR","name":"OpenVINO Audio Super Resolution"}]
    found=discover_features(commands)
    assert found["NOISE_SUPPRESSION"]["id"] == "OVNS"
    assert found["MUSIC_SEPARATION"]["id"] == "OVMS"
    assert all(found[k] is not None for k in found)


def test_effect_parameter_validation_rejects_unknown():
    descriptor={"id":"Effect","params":[{"name":"Device","default":"CPU","choices":["CPU","GPU"]}]}
    assert validate_effect_parameters(descriptor,{"Device":"GPU"})["Device"] == "GPU"
    with pytest.raises(ValueError): validate_effect_parameters(descriptor,{"TotallyUnknown":1})


def test_separation_parameter_is_derived_only_from_provable_choice():
    descriptor={"id":"Effect","params":[{"name":"Separation Mode","choices":["2 Stem - Vocals/Instrumental","4 Stem - Drums/Bass/Other/Vocals"],"default":"2 Stem - Vocals/Instrumental"}]}
    assert "4 Stem" in separation_parameters(descriptor,"4_STEM",{})["Separation Mode"]


def test_separation_parameter_fail_closed_when_runtime_contract_unclear():
    descriptor={"id":"Effect","params":[{"name":"Device","choices":["CPU","GPU"]}]}
    with pytest.raises(ValueError): separation_parameters(descriptor,"2_STEM",{})


def test_audacity_command_builder_blocks_command_injection():
    assert build_command("Import2",{"Filename":"C:/safe/a.wav"}).startswith("Import2:")
    with pytest.raises(ValueError): build_command("Bad:\nCommand",{})
    with pytest.raises(ValueError): build_command("Import2",{"Filename":"x\"\nRemoveTracks:"})




def test_audacity_pipe_ignores_leading_blank_lines_before_json_response():
    pipe = AudacityPipe()
    pipe._to = io.StringIO()
    pipe._from = io.StringIO(
        "\r\n\r\n[{\"id\":\"OVNS\",\"name\":\"OpenVINO Noise Suppression\"}]\r\n"
        "BatchCommand finished: OK\r\n\r\n"
    )
    reply = pipe.command("GetInfo: Type=Commands Format=JSON")
    assert _json_ids(reply) == ["OVNS"]
    assert "BatchCommand finished: OK" in reply


def test_audacity_pipe_still_terminates_on_blank_line_after_content():
    pipe = AudacityPipe()
    pipe._to = io.StringIO()
    pipe._from = io.StringIO("first\r\n\r\nsecond-response\r\n\r\n")
    assert pipe.command("Message: Text=first") == "first\r\n"
    assert pipe.command("Message: Text=second") == "second-response\r\n"


def _json_ids(reply):
    import ai_video_production.audacity_openvino_worker as worker
    value = worker._extract_json(reply)
    return [item.get("id") for item in value]

def test_noise_suppression_registers_derived_audio_and_manifest(tmp_path):
    service,store,resolver,job,source=make_env(tmp_path,noise_runner)
    result=service.process(AudioAiRequest(job.job_id,source.asset_id,"ns",AudioAiOperation.NOISE_SUPPRESSION,True))
    assert result.operation.status == "COMPLETED"
    assert result.roles == ("noise_suppressed",)
    assert result.output_assets[0].generation_provenance["provider"] == "AUDACITY_OPENVINO_EXTERNAL"
    assert result.output_assets[0].source_ref == source.asset_id
    doc=json.loads(resolver.resolve(result.manifest_uri).read_text())
    assert doc["payload"]["details"]["license_boundary"] == "EXTERNAL_GPL_RUNTIME_NOT_COPIED_INTO_CORE"


@pytest.mark.parametrize("mode,expected", [(SeparationMode.TWO_STEM,{"vocals","instrumental"}),(SeparationMode.FOUR_STEM,{"drums","bass","other","vocals"})])
def test_music_separation_registers_complete_stem_set(tmp_path,mode,expected):
    service,store,_resolver,job,source=make_env(tmp_path,separation_runner(mode.value))
    result=service.process(AudioAiRequest(job.job_id,source.asset_id,"sep-"+mode.value,AudioAiOperation.MUSIC_SEPARATION,True,separation_mode=mode))
    assert set(result.roles) == expected
    assert len(result.output_assets) == len(expected)
    assert all(a.asset_type is AssetType.AUDIO for a in result.output_assets)
    assert len(store.list_assets(job.job_id)) == 1 + len(expected)


def test_audio_ai_requires_authorization_before_worker(tmp_path):
    calls=[]
    def runner(*args): calls.append(1); return {}
    service,_store,_resolver,job,source=make_env(tmp_path,runner)
    with pytest.raises(ProductError) as exc:
        service.process(AudioAiRequest(job.job_id,source.asset_id,"no",AudioAiOperation.NOISE_SUPPRESSION,False))
    assert exc.value.code == "ERR_AUTH_LOCAL_AUDIO_EXECUTION_REQUIRED" and calls == []


def test_worker_existing_project_security_error_is_preserved(tmp_path):
    def runner(*a): return {"ok":False,"error_code":"ERR_AUDIO_RUNTIME_EXISTING_PROJECT_PROTECTED","category":"SECURITY","message":"current Audacity project has existing tracks"}
    service,_store,_resolver,job,source=make_env(tmp_path,runner)
    with pytest.raises(ProductError) as exc:
        service.process(AudioAiRequest(job.job_id,source.asset_id,"p",AudioAiOperation.NOISE_SUPPRESSION,True))
    assert exc.value.category.value == "SECURITY"


def test_audio_worker_output_escape_is_rejected(tmp_path):
    outside=tmp_path/"outside.wav"; write_wav(outside,frames=9000,value=2)
    def runner(request,*a): return {"ok":True,"outputs":[{"role":"noise_suppressed","path":str(outside)}],"capabilities":capability()}
    service,_store,_resolver,job,source=make_env(tmp_path,runner)
    with pytest.raises(ProductError) as exc:
        service.process(AudioAiRequest(job.job_id,source.asset_id,"escape",AudioAiOperation.NOISE_SUPPRESSION,True))
    assert exc.value.code == "ERR_SECURITY_AUDIO_AI_OUTPUT_ESCAPE"


def test_incomplete_music_stem_set_is_rejected(tmp_path):
    def runner(request,*a):
        out=Path(request["output_dir"]); out.mkdir(parents=True,exist_ok=True); p=out/"vocals.wav"; write_wav(p,value=3)
        return {"ok":True,"outputs":[{"role":"vocals","path":str(p)}],"capabilities":capability()}
    service,store,_resolver,job,source=make_env(tmp_path,runner)
    with pytest.raises(ProductError) as exc:
        service.process(AudioAiRequest(job.job_id,source.asset_id,"bad",AudioAiOperation.MUSIC_SEPARATION,True,separation_mode=SeparationMode.TWO_STEM))
    assert exc.value.code == "ERR_INTEGRITY_AUDIO_AI_STEM_SET"
    assert [a.asset_id for a in store.list_assets(job.job_id)] == [source.asset_id]


def test_audio_ai_idempotent_replay_does_not_run_worker_twice(tmp_path):
    calls=[]
    def runner(request,*a): calls.append(1); return noise_runner(request,*a)
    service,store,_resolver,job,source=make_env(tmp_path,runner)
    req=AudioAiRequest(job.job_id,source.asset_id,"same",AudioAiOperation.NOISE_SUPPRESSION,True)
    a=service.process(req); b=service.process(req)
    assert a.output_assets[0].asset_id == b.output_assets[0].asset_id
    assert len(calls)==1 and store.latest_manifest(job.job_id,"local-audio-ai-manifest").version==1


def test_capability_only_reports_whisper_musicgen_audio_sr_without_execution_claim(tmp_path):
    observed_timeout = []
    def runner(request, work_root, timeout):
        assert request["operation"] == "CAPABILITY"
        observed_timeout.append(timeout)
        return capability()
    service,_store,_resolver,_job,_source=make_env(tmp_path,runner)
    report=service.capability_report(work_root=tmp_path/"cap")
    assert report["features"]["WHISPER_TRANSCRIPTION"]["available"]
    assert report["features"]["MUSIC_GENERATION"]["available"]
    assert report["features"]["AUDIO_SUPER_RESOLUTION"]["available"]
    assert observed_timeout == [120]




def test_worker_timeout_reports_current_phase_and_discards_stale_progress(tmp_path, monkeypatch):
    import subprocess
    import ai_video_production.audacity_openvino as adapter

    service, _store, _resolver, _job, _source = make_env(tmp_path, lambda *args: {})
    work = tmp_path / "worker-timeout"
    work.mkdir()
    progress = work / "progress.json"
    progress.write_text('{"phase":"STALE_PHASE"}', encoding="utf-8")

    def fake_run(command, **kwargs):
        assert not progress.exists()
        progress.write_text('{"phase":"DISCOVERING_COMMANDS"}', encoding="utf-8")
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    with pytest.raises(ProductError) as exc:
        service._run_worker({"operation":"CAPABILITY"}, work, 120)
    assert exc.value.code == "ERR_PROVIDER_AUDACITY_OPENVINO_TIMEOUT"
    assert exc.value.details == {"timeout_seconds":120, "progress":{"phase":"DISCOVERING_COMMANDS"}}

def test_worker_execute_reports_discovery_phases(monkeypatch):
    import ai_video_production.audacity_openvino_worker as worker

    phases = []
    class FakePipe:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def command(self, command):
            if "Type=Commands" in command:
                return '[{"id":"OVNS","name":"OpenVINO Noise Suppression"}]\n\n'
            if "Type=Tracks" in command:
                return '[]\n\n'
            raise AssertionError(command)

    monkeypatch.setattr(worker, "AudacityPipe", FakePipe)
    report = worker.execute({"operation":"CAPABILITY"}, progress=phases.append)
    assert report["connected"] is True
    assert phases == [
        "OPENING_PIPE", "PIPE_CONNECTED", "DISCOVERING_COMMANDS",
        "COMMANDS_DISCOVERED", "DISCOVERING_TRACKS", "TRACKS_DISCOVERED",
    ]

def test_audio_ai_denied_derivative_rights_fails_before_worker(tmp_path):
    calls=[]
    incoming=tmp_path/"incoming"; assets=tmp_path/"assets"; jobs=tmp_path/"jobs"
    for p in (incoming,assets,jobs): p.mkdir()
    store=SQLiteProductStore(tmp_path/"db.sqlite3"); ps=ProfileSnapshot.create("t4","1.0.0",{}); job=store.create_job(ps.profile_snapshot_id)
    resolver=LogicalPathResolver([PathMapping("asset://",assets,PureWindowsPath("D:/a")),PathMapping("job://",jobs,PureWindowsPath("D:/j"))])
    source=incoming/"source.wav"; write_wav(source)
    asset=AssetIngestService(store=store,resolver=resolver,source_policy=SourcePathPolicy((incoming,))).ingest(
        AssetIngestRequest(job.job_id,source,AssetType.AUDIO,RightsStatus.LICENSED,"VENDOR","ing-denied",derivative_allowed=PermissionState.DENIED)
    ).asset
    def runner(*args): calls.append(1); return {}
    service=AudacityOpenVinoService(store=store,resolver=resolver,worker_runner=runner)
    with pytest.raises(ProductError) as exc:
        service.process(AudioAiRequest(job.job_id,asset.asset_id,"denied",AudioAiOperation.NOISE_SUPPRESSION,True))
    assert exc.value.code == "ERR_POLICY_DERIVATIVE_DENIED" and calls == []


def test_audio_effect_parameters_are_hashed_not_persisted_raw(tmp_path):
    secret = "D:/private/models/secret.bin"
    def runner(request, work_root, timeout):
        out=Path(request["output_dir"]); out.mkdir(parents=True,exist_ok=True); path=out/"noise-suppressed.wav"; write_wav(path,frames=8101,value=7)
        return {"ok":True,"outputs":[{"role":"noise_suppressed","path":str(path)}],
                "effect":{"command_id":"OpenVINONoise","parameters":{"Device":"GPU","ModelPath":secret}},"capabilities":capability()}
    service,_store,resolver,job,source=make_env(tmp_path,runner)
    result=service.process(AudioAiRequest(job.job_id,source.asset_id,"secret",AudioAiOperation.NOISE_SUPPRESSION,True))
    doc=json.loads(resolver.resolve(result.manifest_uri).read_text())
    serialized=json.dumps(doc)
    assert secret not in serialized
    effect=doc["payload"]["details"]["effect"]
    assert effect["device"] == "GPU" and effect["parameters_sha256"].startswith("sha256:")
    assert set(effect["parameter_names"]) == {"Device","ModelPath"}


def test_byte_identical_audio_output_reuses_asset_but_manifest_keeps_operation_lineage(tmp_path):
    import shutil
    def runner(request, work_root, timeout):
        out=Path(request["output_dir"]); out.mkdir(parents=True,exist_ok=True); path=out/"noise-suppressed.wav"
        shutil.copyfile(request["source_path"], path)
        return {"ok":True,"outputs":[{"role":"noise_suppressed","path":str(path)}],
                "effect":{"command_id":"OpenVINONoise","parameters":{"Device":"CPU"}},"capabilities":capability()}
    service,store,resolver,job,source=make_env(tmp_path,runner)
    result=service.process(AudioAiRequest(job.job_id,source.asset_id,"same-bytes",AudioAiOperation.NOISE_SUPPRESSION,True))
    assert result.output_assets[0].asset_id == source.asset_id
    doc=json.loads(resolver.resolve(result.manifest_uri).read_text())
    details=doc["payload"]["details"]
    assert details["provider"] == "AUDACITY_OPENVINO_EXTERNAL"
    assert details["output_bindings"] == [{"role":"noise_suppressed","asset_id":source.asset_id,"checksum":source.checksum}]
    assert len(store.list_assets(job.job_id)) == 1


def test_audacity_command_builder_rejects_parameter_name_injection_and_nonfinite_numbers():
    for key in ("Device\nRemoveTracks", "Device=GPU", 'Device"Bad', "Bad:Key"):
        with pytest.raises(ValueError):
            build_command("Effect", {key: "CPU"})
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            build_command("Effect", {"Gain": value})




def test_audacity_windows_pipe_uses_required_crlf_nul_terminator():
    assert _command_eol_for_os_name("nt") == "\r\n\0"
    assert _command_eol_for_os_name("posix") == "\n"


def test_audacity_pipe_command_writes_configured_protocol_terminator():
    pipe = AudacityPipe()
    pipe._command_eol = "\r\n\0"
    pipe._to = io.StringIO()
    pipe._from = io.StringIO('[]\n\n')
    reply = pipe.command("GetInfo: Type=Tracks Format=JSON")
    assert pipe._to.getvalue().endswith("\r\n\0")
    assert reply == '[]\n'

def test_audacity_pipe_caps_untrusted_reply_size():
    pipe = AudacityPipe(max_reply_bytes=1024)
    pipe._to = io.StringIO()
    pipe._from = io.StringIO(("x" * 1025) + "\n\n")
    with pytest.raises(RuntimeError, match="safety limit"):
        pipe.command("GetInfo: Type=Commands Format=JSON")


def test_audacity_export_preserves_stereo_capability():
    class Pipe:
        def __init__(self):
            self.commands = []
        def command(self, command):
            self.commands.append(command)
            return ""
    pipe = Pipe()
    _export(pipe, Path("out.wav"))
    assert "NumChannels=2" in pipe.commands[-1]


def test_audacity_ambiguous_in_progress_operation_fails_closed_without_replay(tmp_path):
    from ai_video_production.serialization import canonical_json_bytes, sha256_bytes

    calls=[]
    def runner(*args):
        calls.append(1)
        return noise_runner(*args)

    service,store,_resolver,job,source=make_env(tmp_path,runner)
    req=AudioAiRequest(job.job_id,source.asset_id,"ambiguous",AudioAiOperation.NOISE_SUPPRESSION,True)
    fingerprint=sha256_bytes(canonical_json_bytes({
        "operation": req.operation.value,
        "source_asset_id": source.asset_id,
        "source_checksum": source.checksum,
        "separation_mode": None,
        "effect_parameters": {},
    })).removeprefix("sha256:")
    operation,_=store.reserve_operation(job.job_id,f"LOCAL_AUDIO_{req.operation.value}:{fingerprint}",req.idempotency_key)
    store.update_operation_status(operation.operation_id,"IN_PROGRESS",increment_attempt=True)

    with pytest.raises(ProductError) as exc:
        service.process(req)

    assert exc.value.code == "ERR_STATE_AUDACITY_RECONCILIATION_REQUIRED"
    assert calls == []
