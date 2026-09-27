from pathlib import Path
from email.message import Message
import json, math, wave, shutil, sys
from types import SimpleNamespace
import pytest
from ai_video_production.task014_srt_owner_voice_wav import *
from ai_video_production.task014_srt_owner_voice_wav import _load_candidates
from ai_video_production.voice_reference_selector import VoiceReferenceCandidate
from ai_video_production.owner_voice_wav import new_canonical_writer,read_pcm_wav_info

def wav(path:Path, seconds:float, amp:int=1000):
    n=round(seconds*48_000)
    frame=int(amp).to_bytes(3,'little',signed=True)
    with new_canonical_writer(path) as w: w.writeframesraw(frame*n)
    return n

def srt(path:Path):
    path.write_text('1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n2\n00:00:04,000 --> 00:00:06,500\n実況です\n',encoding='utf-8')

class FakeRenderer:
    def __init__(self,seconds=1.0): self.seconds=seconds; self.refs=[]
    def render(self,*,text,reference,output_path): self.refs.append(reference.candidate_id); wav(output_path,self.seconds)

def candidate(tmp:Path,cid='n',style='NORMAL',emotion='NORMAL'):
    w=tmp/f'{cid}.wav'; wav(w,8); t=tmp/f'{cid}.txt'; t.write_text('参照テキスト',encoding='utf-8')
    return VoiceReferenceCandidate(cid,w,t,'sha256:'+('a' if cid=='n' else 'b')*64,8*48_000,style,emotion,True,True,True)

def test_srt_plan_samples_and_public_hash(tmp_path):
    p=tmp_path/'x.srt'; srt(p); plan=build_srt_plan(p)
    assert (plan[0].start_sample,plan[0].end_sample)==(48_000,144_000)
    assert plan[0].to_public_dict()['text_sha256'].startswith('sha256:')

def test_assemble_preserves_srt_timeline_and_silence(tmp_path):
    p=tmp_path/'x.srt'; srt(p); plan=build_srt_plan(p); d=tmp_path/'c'; d.mkdir()
    for c in plan: wav(d/f'{c.cue_id}.wav',1)
    out=tmp_path/'final.wav'; report=assemble_cue_wavs(plan,{c.cue_id:d/f'{c.cue_id}.wav' for c in plan},out)
    assert read_pcm_wav_info(out,require_canonical=True).sample_count==round(6.5*48_000)
    assert report['sample_count']==round(6.5*48_000)

def test_fit_uses_ffmpeg_without_truncation(tmp_path):
    if shutil.which('ffmpeg') is None: pytest.skip('ffmpeg unavailable')
    src=tmp_path/'src.wav'; wav(src,2.4); dst=tmp_path/'fit.wav'
    report=fit_cue_wav(src,dst,slot_samples=2*48_000)
    assert report['tempo']>1
    assert read_pcm_wav_info(dst,require_canonical=True).sample_count<=2*48_000

def test_fit_rejects_excessive_speed(tmp_path):
    src=tmp_path/'src.wav'; wav(src,4); dst=tmp_path/'fit.wav'
    with pytest.raises(ValueError,match='bounded fit'): fit_cue_wav(src,dst,slot_samples=2*48_000)

def test_style_emotion_routes_distinct_references(tmp_path):
    p=tmp_path/'x.srt'; srt(p); r=FakeRenderer(); refs=(candidate(tmp_path),candidate(tmp_path,'e','SPORTS_COMMENTARY','EXCITED'))
    out=tmp_path/'final.wav'
    render_srt_to_wav(p,renderer=r,candidates=refs,work_dir=tmp_path/'work',output=out,cue_overrides={'cue-000002':{'style_id':'SPORTS_COMMENTARY','emotion_id':'EXCITED'}})
    assert r.refs==['n','e']

def test_neutral_fallback_is_opt_in(tmp_path):
    p=tmp_path/'x.srt'; srt(p); refs=(candidate(tmp_path),); r=FakeRenderer()
    with pytest.raises(ValueError,match='NO_APPROVED_REFERENCE'):
        render_srt_to_wav(p,renderer=r,candidates=refs,work_dir=tmp_path/'a',output=tmp_path/'a.wav',style_id='WHISPER',emotion_id='SAD')
    render_srt_to_wav(p,renderer=r,candidates=refs,work_dir=tmp_path/'b',output=tmp_path/'b.wav',style_id='WHISPER',emotion_id='SAD',allow_neutral_fallback=True)


def test_cue_overrides_are_strict_and_drive_two_expressions(tmp_path):
    override=tmp_path/'overrides.json'
    override.write_text(json.dumps({'cue-000002':{'style_id':'SPORTS_COMMENTARY','emotion_id':'EXCITED','speaking_rate':1.1}}),encoding='utf-8')
    loaded=load_cue_overrides(override)
    p=tmp_path/'x.srt'; srt(p)
    plan=build_srt_plan(p,cue_overrides=loaded)
    assert (plan[0].style_id,plan[0].emotion_id)==('NORMAL','NORMAL')
    assert (plan[1].style_id,plan[1].emotion_id,plan[1].speaking_rate)==('SPORTS_COMMENTARY','EXCITED',1.1)
    override.write_text(json.dumps({'cue-000001':{'private_path':'x'}}),encoding='utf-8')
    with pytest.raises(ValueError,match='unknown fields'): load_cue_overrides(override)
    override.write_text(json.dumps({'cue-missing':{'emotion_id':'SAD'}}),encoding='utf-8')
    with pytest.raises(ValueError,match='unknown cue ids'):
        build_srt_plan(p,cue_overrides=load_cue_overrides(override))


class FakeHttpResponse:
    def __init__(self,body:bytes,content_type:str,content_length:int|None=None):
        self.body=body; self.headers=Message()
        self.headers['Content-Type']=content_type
        if content_length is not None: self.headers['Content-Length']=str(content_length)
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size=-1): return self.body if size<0 else self.body[:size]


def test_gpt_sovits_renderer_configures_selected_pair_then_renders_canonical_wav(tmp_path,monkeypatch):
    reference=candidate(tmp_path)
    source=tmp_path/'server.wav'; wav(source,0.2)
    server_wav=source.read_bytes(); calls=[]
    def opener(request,timeout):
        calls.append((request.full_url,request.data,timeout))
        if '/set_' in request.full_url: return FakeHttpResponse(b'{"message":"success"}','application/json')
        assert request.full_url.endswith('/tts')
        payload=json.loads(request.data.decode('utf-8'))
        assert payload['text']=='生成テキスト'
        assert payload['prompt_text']=='参照テキスト'
        assert payload['ref_audio_path'].startswith('/mnt/')
        return FakeHttpResponse(server_wav,'audio/wav',len(server_wav))
    def run(argv,**kwargs):
        wav(Path(argv[-1]),0.2)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('ai_video_production.task014_srt_owner_voice_wav.subprocess.run',run)
    renderer=GptSoVitsHttpRenderer(gpt_weights_path='/models/selected.ckpt',sovits_weights_path='/models/selected.pth',opener=opener)
    output=tmp_path/'out.wav'
    renderer.render(text='生成テキスト',reference=reference,output_path=output)
    renderer.render(text='生成テキスト',reference=reference,output_path=tmp_path/'out2.wav')
    assert [x[0].split('/')[-1].split('?')[0] for x in calls]==['set_sovits_weights','set_gpt_weights','tts','tts']
    assert read_pcm_wav_info(output,require_canonical=True).sample_count>0
    assert not output.with_suffix('.gpt-sovits.wav').exists()


def test_gpt_sovits_renderer_rejects_non_loopback_and_weight_failure(tmp_path):
    with pytest.raises(ValueError,match='loopback'):
        GptSoVitsHttpRenderer('http://example.com:9880',gpt_weights_path='g',sovits_weights_path='s')
    with pytest.raises(ValueError,match='loopback'):
        GptSoVitsHttpRenderer('http://localhost:9880',gpt_weights_path='g',sovits_weights_path='s')
    def opener(request,timeout): return FakeHttpResponse(b'{"message":"failed"}','application/json')
    renderer=GptSoVitsHttpRenderer(gpt_weights_path='g',sovits_weights_path='s',opener=opener)
    with pytest.raises(RuntimeError,match='rejected'):
        renderer.configure()


def test_gpt_sovits_renderer_bounds_audio_response(tmp_path):
    replies=iter((
        FakeHttpResponse(b'{"message":"success"}','application/json'),
        FakeHttpResponse(b'{"message":"success"}','application/json'),
        FakeHttpResponse(b'RIFFtoolarge','audio/wav'),
    ))
    renderer=GptSoVitsHttpRenderer(gpt_weights_path='g',sovits_weights_path='s',max_response_bytes=4,opener=lambda *a,**k:next(replies))
    with pytest.raises(RuntimeError,match='size limit'):
        renderer.render(text='x',reference=candidate(tmp_path),output_path=tmp_path/'out.wav')


def test_gpt_sovits_preflight_requires_exact_loopback_api_contract(monkeypatch):
    contract=json.dumps({'paths':{'/tts':{},'/set_gpt_weights':{},'/set_sovits_weights':{}}}).encode()
    monkeypatch.setattr('ai_video_production.task014_srt_owner_voice_wav.shutil.which',lambda value:'ffmpeg')
    ready=gpt_sovits_preflight(base_url='http://127.0.0.1:9880',gpt_weights_path='g',sovits_weights_path='s',opener=lambda *a,**k:FakeHttpResponse(contract,'application/json'))
    assert ready['state']=='READY'
    blocked=gpt_sovits_preflight(base_url='http://remote.invalid:9880',gpt_weights_path='g',sovits_weights_path='s',opener=lambda *a,**k:FakeHttpResponse(contract,'application/json'))
    assert blocked['state']=='BLOCKED'


def test_qwen_renderer_uses_generated_sample_rate_not_reference_rate(tmp_path, monkeypatch):
    reference=candidate(tmp_path)
    writes=[]

    class Model:
        def generate_voice_clone(self, **kwargs):
            assert kwargs['ref_audio'][1] == 48_000
            return [[0.0, 0.1]], 24_000

    class ModelFactory:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return Model()

    fake_soundfile=SimpleNamespace(
        read=lambda *args, **kwargs: ([0.0], 48_000),
        write=lambda path, data, sample_rate, subtype: writes.append((path, sample_rate, subtype)),
    )
    fake_torch=SimpleNamespace(bfloat16='bf16')
    fake_qwen=SimpleNamespace(Qwen3TTSModel=ModelFactory)
    monkeypatch.setitem(sys.modules, 'soundfile', fake_soundfile)
    monkeypatch.setitem(sys.modules, 'torch', fake_torch)
    monkeypatch.setitem(sys.modules, 'qwen_tts', fake_qwen)
    monkeypatch.setattr('ai_video_production.task014_srt_owner_voice_wav.subprocess.run', lambda *args, **kwargs: SimpleNamespace(returncode=1))

    renderer=Qwen3OwnerVoiceRenderer(tmp_path/'model')
    with pytest.raises(RuntimeError, match='normalization failed'):
        renderer.render(text='こんにちは', reference=reference, output_path=tmp_path/'out.wav')
    assert writes[0][1:] == (24_000, 'FLOAT')


def test_prepare_reference_manifest_builds_eligible_exact_reference(tmp_path):
    reference=tmp_path/'reference.wav'; count=wav(reference,8)
    transcript=tmp_path/'reference.txt'; transcript.write_text('これは本人の見本音声です。',encoding='utf-8')
    output=tmp_path/'private'/'references.json'

    result=prepare_reference_manifest(
        reference_wav=reference,
        reference_text=transcript,
        output=output,
        owner_approved=True,
        quality_pass=True,
        transcript_verified=True,
    )

    saved=json.loads(output.read_text(encoding='utf-8'))
    candidate=saved['candidates'][0]
    assert result == saved
    assert candidate['candidate_id'] == 'OWNER_NORMAL_001'
    assert candidate['duration_samples'] == count
    assert candidate['wav_path'] == str(reference.resolve())
    assert candidate['transcript_path'] == str(transcript.resolve())
    assert candidate['content_sha256'].startswith('sha256:')
    assert candidate['quality_pass'] is True
    assert candidate['owner_approved'] is True
    assert candidate['transcript_verified'] is True


def test_prepare_reference_manifest_requires_explicit_confirmations(tmp_path):
    reference=tmp_path/'reference.wav'; wav(reference,8)
    transcript=tmp_path/'reference.txt'; transcript.write_text('一致する文章',encoding='utf-8')
    with pytest.raises(ValueError,match='confirmations'):
        prepare_reference_manifest(reference_wav=reference,reference_text=transcript,output=tmp_path/'references.json')


def test_load_candidates_revalidates_reference_wav_checksum(tmp_path):
    reference=tmp_path/'reference.wav'; wav(reference,8)
    transcript=tmp_path/'reference.txt'; transcript.write_text('一致する文章',encoding='utf-8')
    manifest=tmp_path/'references.json'
    prepare_reference_manifest(reference_wav=reference,reference_text=transcript,output=manifest,
        owner_approved=True,quality_pass=True,transcript_verified=True)
    reference.write_bytes(reference.read_bytes()+b'tampered')
    with pytest.raises(ValueError,match='checksum mismatch'):
        _load_candidates(manifest)


def test_installed_windows_wrapper_is_explicit_noninteractive_command():
    script=(Path(__file__).parents[1]/'tools'/'windows'/'make-owner-voice-wav.ps1').read_text(encoding='utf-8')
    for required in (
        'ReferenceManifest',
        'voice-dataset\\dataset\\reference-manifest.json',
        'ConfirmOwnerApproved',
        'runtime-config.json',
        'prepare-reference',
        'preflight',
        "'plan'",
        "'render'",
        'gpt-sovits',
        'CueOverrides',
        'GptWeights',
        'SoVitsWeights',
        'master-owner-voice.wav',
    ):
        assert required in script
    assert 'Read-Host' not in script
    assert 'D:\\BAI\\BAI_VIDEO_PRODUCTION_20260914\\owner-voice-jobs' not in script
    assert '/home/baisound/' not in script
    assert "Join-Path $datasetRoot 'master-wav-jobs'" in script
