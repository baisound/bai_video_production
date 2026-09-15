from pathlib import Path
import json, math, shutil, struct, subprocess, wave
import pytest
import ai_video_production.owner_voice_recording_pipeline as recording_pipeline_module
from ai_video_production.ids import IdKind,generate_id
from ai_video_production.owner_voice_wav import copy_pcm24_range,new_canonical_writer,read_pcm24_samples,read_pcm_wav_info
from ai_video_production.owner_voice_recording_pipeline import *
from ai_video_production.subtitles import TranscriptManifest,TranscriptSegment,TranscriptWord
from ai_video_production.voice_recording_coverage import RecordingCoverageTarget


def canonical(path:Path, parts):
    # parts: (seconds, amplitude)
    with new_canonical_writer(path) as w:
        for seconds,amp in parts:
            n=round(seconds*48_000); frame=int(amp).to_bytes(3,'little',signed=True); w.writeframesraw(frame*n)


def manifest(segments,words=False):
    return TranscriptManifest(generate_id(IdKind.ASSET,timestamp_ms=1),'ja','test','test-model',tuple(segments),words)


def test_recording_start_preflight_requires_all_conditions():
    ok=recording_start_preflight(obs_current=True,sample_rate_hz=48_000,gain_ready=True,meter_peak_dbfs=-12,target_floor_dbfs=-18,target_ceiling_dbfs=-6,quality_state='PASS',clip_sample_count=0)
    assert ok['state']=='READY' and ok['recording_start_authorized'] is True
    bad=recording_start_preflight(obs_current=True,sample_rate_hz=48_000,gain_ready=True,meter_peak_dbfs=-2,target_floor_dbfs=-18,target_ceiling_dbfs=-6,quality_state='PASS',clip_sample_count=3)
    assert bad['state']=='BLOCKED' and {'CLIPPING_DETECTED','PEAK_OUTSIDE_TARGET'}<=set(bad['reason_codes'])


def test_canonicalizer_preserves_source_and_is_resumable(tmp_path):
    if shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None: pytest.skip('ffmpeg unavailable')
    base=tmp_path/'base.wav'; canonical(base,[(1,1000)])
    raw=tmp_path/'raw.wav'; subprocess.run(['ffmpeg','-v','error','-y','-i',str(base),'-ar','44100','-c:a','pcm_f32le',str(raw)],check=True)
    before=sha256_file(raw); out=tmp_path/'canonical.wav'; report=tmp_path/'report.json'
    r1=canonicalize_obs_recording(raw,out,report_path=report); r2=canonicalize_obs_recording(raw,out,report_path=report)
    assert r1==r2 and sha256_file(raw)==before
    info=read_pcm_wav_info(out,require_canonical=True); assert info.sample_rate_hz==48_000
    assert r1['raw_source_preserved'] is True and r1['source_sample_rate_hz']==44100


def test_canonicalizer_falls_back_only_when_soxr_is_unavailable(tmp_path,monkeypatch):
    source=tmp_path/'source.wav'; canonical(source,[(1,1000)])
    calls=[]
    monkeypatch.setattr(recording_pipeline_module,'_ffprobe',lambda *_args,**_kwargs:{'channels':1,'sample_rate':'48000','sample_fmt':'s32'})
    def fake_run(argv,**kwargs):
        calls.append(argv)
        if 'resampler=soxr' in argv[argv.index('-af')+1]:
            return subprocess.CompletedProcess(argv,1,b'',b'Requested resampling engine is unavailable')
        shutil.copyfile(source,Path(argv[-1]))
        return subprocess.CompletedProcess(argv,0,b'',b'')
    monkeypatch.setattr(recording_pipeline_module.subprocess,'run',fake_run)
    report=recording_pipeline_module.canonicalize_obs_recording(source,tmp_path/'output.wav')
    assert len(calls)==2
    assert report['resampler']=='swresample' and report['resampler_precision'] is None


def test_pcm24_extensible_header_is_supported_without_stdlib_wave(tmp_path):
    samples=[-8388608,-1,0,1,8388607]
    pcm=b''.join(value.to_bytes(3,'little',signed=True) for value in samples)
    fmt=struct.pack('<HHIIHHHHI16s',0xFFFE,1,48_000,144_000,3,24,22,24,4,bytes.fromhex('0100000000001000800000aa00389b71'))
    body=b'fmt '+struct.pack('<I',len(fmt))+fmt+b'data'+struct.pack('<I',len(pcm))+pcm+(b'\0' if len(pcm)%2 else b'')
    path=tmp_path/'extensible.wav'; path.write_bytes(b'RIFF'+struct.pack('<I',len(body)+4)+b'WAVE'+body)
    info=read_pcm_wav_info(path,require_canonical=True)
    assert info.sample_count==len(samples)
    assert read_pcm24_samples(path,0,len(samples))==samples
    copied=tmp_path/'copied.wav'
    with new_canonical_writer(copied) as writer: copy_pcm24_range(path,writer,0,len(samples))
    assert read_pcm24_samples(copied,0,len(samples))==samples

    not_pcm=bytearray(path.read_bytes()); not_pcm[44]=3
    invalid=tmp_path/'extensible-float.wav'; invalid.write_bytes(not_pcm)
    with pytest.raises(ValueError,match='unsupported extensible WAV subtype'):
        read_pcm_wav_info(invalid)


def test_multichannel_requires_explicit_channel(tmp_path):
    if shutil.which('ffmpeg') is None: pytest.skip('ffmpeg unavailable')
    mono=tmp_path/'m.wav'; canonical(mono,[(1,1000)]); stereo=tmp_path/'s.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(mono),'-ac','2','-c:a','pcm_s24le',str(stereo)],check=True)
    with pytest.raises(ValueError,match='channel_index'): canonicalize_obs_recording(stereo,tmp_path/'o.wav')
    canonicalize_obs_recording(stereo,tmp_path/'o.wav',channel_index=0)


def test_speech_continuous_removes_long_silence_and_keeps_short_pause(tmp_path):
    src=tmp_path/'src.wav'
    # speech1 2s, short pause .3s, speech2 2s, long silence 2s, speech3 2s
    canonical(src,[(2,3000),(.3,0),(2,3000),(2,0),(2,3000)])
    segs=(
        TranscriptSegment('seg-1',0,2_000_000,'a'),
        TranscriptSegment('seg-2',2_300_000,4_300_000,'b'),
        TranscriptSegment('seg-3',6_300_000,8_300_000,'c'),
    )
    out=tmp_path/'continuous.wav'; rep=create_speech_continuous_wav(src,manifest(segs),out)
    assert rep['removed_duration_seconds']>1.7
    assert rep['boundary_count']==1
    assert read_pcm_wav_info(out,require_canonical=True).duration_seconds>6.2 # short pause remains


def test_dataset_segments_coverage_and_reference_candidates(tmp_path):
    src=tmp_path/'src.wav'; canonical(src,[(4,2000),(1,0),(4,3000)])
    segs=(TranscriptSegment('seg-1',0,4_000_000,'hello'),TranscriptSegment('seg-2',5_000_000,9_000_000,'world'))
    target=RecordingCoverageTarget.from_seconds(100,style_target_seconds={'NORMAL':20},emotion_target_seconds={'NORMAL':20})
    body=prepare_dataset_from_transcript(src,manifest(segs),tmp_path/'d',style_id='NORMAL',emotion_id='NORMAL',quality_pass=True,owner_approved=True,accept_transcripts=True,target=target)
    assert len(body['segments'])==2
    refs=json.loads((tmp_path/'d'/'reference-manifest.json').read_text())['candidates']; assert len(refs)==2
    assert body['coverage']['overall']['percentage']==8.0


def test_dataset_deduplicates_identical_audio_in_cumulative_workspace(tmp_path):
    src=tmp_path/'src.wav'; canonical(src,[(4,2000),(4,2000)])
    segs=(TranscriptSegment('seg-1',0,4_000_000,'same'),TranscriptSegment('seg-2',4_000_000,8_000_000,'same'))
    target=RecordingCoverageTarget.from_seconds(20,style_target_seconds={'NORMAL':20})
    b1=prepare_dataset_from_transcript(src,manifest(segs),tmp_path/'b1',style_id='NORMAL',emotion_id='NORMAL',quality_pass=True,owner_approved=True,accept_transcripts=True,target=target)
    ws=merge_dataset_workspaces([tmp_path/'b1'/'dataset-manifest.json',tmp_path/'b1'/'dataset-manifest.json'],tmp_path/'ws',target=target)
    # repeated batch must not double-count identical content
    assert ws['coverage']['overall']['percentage']==20.0
    assert ws['unique_reference_count']==1


def test_analyze_canonical_recording_reports_clip_headroom_and_noise(tmp_path):
    src=tmp_path/'src.wav'; canonical(src,[(1,1000),(1,100000)])
    m=analyze_canonical_recording(src); assert m['clip_sample_count']==0; assert m['headroom_db']>0; assert 'snr_estimate_db' in m
