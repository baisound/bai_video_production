from pathlib import Path
import json, math, wave, shutil
import pytest
from ai_video_production.task014_srt_owner_voice_wav import *
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
