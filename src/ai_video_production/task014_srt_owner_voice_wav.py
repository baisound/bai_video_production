"""SRT -> local Owner Voice -> final PCM24 WAV.

The CLI supports planning, assembly of existing Cue WAVs, and local Qwen3-TTS
rendering.  It never truncates speech to make it fit a subtitle slot: bounded
pitch-preserving tempo adjustment is attempted, then the operation fails.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence
import argparse, hashlib, importlib, importlib.util, json, math, shutil, subprocess, tempfile

from .subtitle_workspace import SrtWorkspaceCodec
from .owner_voice_wav import SAMPLE_RATE_HZ, SAMPLE_WIDTH_BYTES, copy_pcm24_range, new_canonical_writer, read_pcm_wav_info
from .voice_reference_selector import VoiceReferenceCandidate, build_reference_manifest, select_reference, sha256_file

DEFAULT_MAX_TOTAL_SPEED=1.35

@dataclass(frozen=True, slots=True)
class OwnerVoiceCuePlan:
    cue_id:str
    start_sample:int
    end_sample:int
    text:str
    style_id:str="NORMAL"
    emotion_id:str="NORMAL"
    speaking_rate:float=1.0

    def __post_init__(self)->None:
        if self.start_sample<0 or self.end_sample<=self.start_sample: raise ValueError("cue sample range is invalid")
        if not self.text.strip(): raise ValueError("cue text is empty")
        if not 0.75<=float(self.speaking_rate)<=DEFAULT_MAX_TOTAL_SPEED: raise ValueError("speaking_rate is out of range")

    @property
    def target_samples(self)->int: return self.end_sample-self.start_sample
    def to_public_dict(self)->dict[str,Any]:
        return {"cue_id":self.cue_id,"start_sample":self.start_sample,"end_sample":self.end_sample,"target_samples":self.target_samples,
                "text_sha256":"sha256:"+hashlib.sha256(self.text.encode()).hexdigest(),"text_code_points":len(self.text),
                "style_id":self.style_id,"emotion_id":self.emotion_id,"speaking_rate":self.speaking_rate}


def build_srt_plan(srt_path:str|Path, *, style_id:str="NORMAL", emotion_id:str="NORMAL", speaking_rate:float=1.0,
                   cue_overrides:Mapping[str,Mapping[str,Any]]|None=None)->tuple[OwnerVoiceCuePlan,...]:
    ws=SrtWorkspaceCodec.import_path(srt_path); out=[]; overrides=cue_overrides or {}
    for cue in ws.cues:
        ov=overrides.get(cue.cue_id,{})
        out.append(OwnerVoiceCuePlan(cue.cue_id, cue.start_ms*48, cue.end_ms*48, cue.text,
                    str(ov.get("style_id",style_id)),str(ov.get("emotion_id",emotion_id)),float(ov.get("speaking_rate",speaking_rate))))
    return tuple(out)


def _ffmpeg_tempo(source:Path,target:Path,speed:float,ffmpeg:str)->None:
    if not 0.5<=speed<=2.0: raise ValueError("ffmpeg atempo speed is unsupported")
    argv=[ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y","-i",str(source),"-af",f"atempo={speed:.8f}","-ar","48000","-ac","1","-c:a","pcm_s24le",str(target)]
    proc=subprocess.run(argv,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False,timeout=180,shell=False)
    if proc.returncode!=0: raise RuntimeError("ffmpeg tempo conversion failed")
    read_pcm_wav_info(target,require_canonical=True)


def fit_cue_wav(source:str|Path,target:str|Path,*,slot_samples:int,speaking_rate:float=1.0,max_total_speed:float=DEFAULT_MAX_TOTAL_SPEED,ffmpeg:str="ffmpeg")->dict[str,Any]:
    src=Path(source); dst=Path(target); info=read_pcm_wav_info(src,require_canonical=True)
    if slot_samples<=0: raise ValueError("slot_samples must be positive")
    requested=float(speaking_rate)
    minimum_fit=(info.sample_count/slot_samples)*1.005 if info.sample_count>slot_samples else 1.0
    chosen=max(requested,minimum_fit if info.sample_count/requested>slot_samples else requested)
    if chosen>max_total_speed+1e-9: raise ValueError("rendered audio exceeds SRT slot and bounded fit limit")
    if math.isclose(chosen,1.0,rel_tol=0,abs_tol=1e-9):
        shutil.copyfile(src,dst)
    else:
        _ffmpeg_tempo(src,dst,chosen,ffmpeg)
    final=read_pcm_wav_info(dst,require_canonical=True)
    if final.sample_count>slot_samples: raise ValueError("rendered audio exceeds SRT slot after bounded fit")
    return {"input_samples":info.sample_count,"output_samples":final.sample_count,"slot_samples":slot_samples,"tempo":chosen}


def assemble_cue_wavs(plan:Sequence[OwnerVoiceCuePlan],cue_paths:Mapping[str,str|Path],output:str|Path)->dict[str,Any]:
    if not plan: raise ValueError("SRT plan is empty")
    cursor=0; rows=[]; out=Path(output)
    with new_canonical_writer(out) as w:
        for cue in plan:
            if cue.start_sample<cursor: raise ValueError("SRT cues overlap")
            if cue.start_sample>cursor:
                w.writeframesraw(b"\0"*((cue.start_sample-cursor)*SAMPLE_WIDTH_BYTES)); cursor=cue.start_sample
            p=Path(cue_paths[cue.cue_id]); info=read_pcm_wav_info(p,require_canonical=True)
            if info.sample_count>cue.target_samples: raise ValueError("cue WAV exceeds SRT slot")
            copy_pcm24_range(p,w,0,info.sample_count)
            cursor+=info.sample_count
            rows.append({"cue_id":cue.cue_id,"start_sample":cue.start_sample,"rendered_samples":info.sample_count,"slot_samples":cue.target_samples})
        final_end=max(c.end_sample for c in plan)
        if cursor<final_end: w.writeframesraw(b"\0"*((final_end-cursor)*SAMPLE_WIDTH_BYTES)); cursor=final_end
    return {"output":str(out),"sample_rate_hz":48_000,"channels":1,"sample_format":"PCM_S24LE","sample_count":cursor,"cues":rows}


class CueRenderer(Protocol):
    def render(self, *, text:str, reference:VoiceReferenceCandidate, output_path:Path)->None: ...


class Qwen3OwnerVoiceRenderer:
    def __init__(self,model_root:str|Path,*,device_map:str="cuda:0",ffmpeg:str="ffmpeg"):
        self.model_root=Path(model_root); self.device_map=device_map; self.ffmpeg=ffmpeg; self._model=None
    def _load(self):
        if self._model is None:
            torch=importlib.import_module("torch"); qwen=importlib.import_module("qwen_tts")
            cls=getattr(qwen,"Qwen3TTSModel")
            self._model=cls.from_pretrained(str(self.model_root),device_map=self.device_map,dtype=torch.bfloat16,attn_implementation="sdpa",local_files_only=True)
        return self._model
    def render(self,*,text:str,reference:VoiceReferenceCandidate,output_path:Path)->None:
        sf=importlib.import_module("soundfile"); model=self._load()
        waveform,sr=sf.read(str(reference.wav_path),dtype="float32",always_2d=False)
        ref_text=reference.transcript_path.read_text(encoding="utf-8").strip()
        result=model.generate_voice_clone(text=text,language="Japanese",ref_audio=(waveform,sr),ref_text=ref_text,x_vector_only_mode=False,max_new_tokens=2048)
        if not isinstance(result,tuple) or len(result)!=2: raise RuntimeError("Qwen voice clone returned an invalid result")
        waves,output_sr=result
        if isinstance(waves,(list,tuple)) and len(waves)==1: waves=waves[0]
        if hasattr(waves,"detach"): waves=waves.detach().cpu().numpy()
        if not isinstance(output_sr,(int,float)) or int(output_sr)<=0: raise RuntimeError("Qwen voice clone returned an invalid sample rate")
        temp=output_path.with_suffix('.qwen.wav'); sf.write(str(temp),waves,int(output_sr),subtype="FLOAT")
        proc=subprocess.run([self.ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y","-i",str(temp),"-ar","48000","-ac","1","-c:a","pcm_s24le",str(output_path)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False,timeout=180,shell=False)
        temp.unlink(missing_ok=True)
        if proc.returncode!=0: raise RuntimeError("Qwen output normalization failed")
        read_pcm_wav_info(output_path,require_canonical=True)


def render_srt_to_wav(srt_path:str|Path,*,renderer:CueRenderer,candidates:Sequence[VoiceReferenceCandidate],work_dir:str|Path,output:str|Path,
                      style_id:str="NORMAL",emotion_id:str="NORMAL",speaking_rate:float=1.0,cue_overrides:Mapping[str,Mapping[str,Any]]|None=None,
                      allow_neutral_fallback:bool=False,ffmpeg:str="ffmpeg")->dict[str,Any]:
    plan=build_srt_plan(srt_path,style_id=style_id,emotion_id=emotion_id,speaking_rate=speaking_rate,cue_overrides=cue_overrides)
    root=Path(work_dir); root.mkdir(parents=True,exist_ok=True); paths={}; rows=[]
    for cue in plan:
        ref=select_reference(candidates,style_id=cue.style_id,emotion_id=cue.emotion_id,allow_neutral_fallback=allow_neutral_fallback)
        raw=root/f"{cue.cue_id}.raw.wav"; fitted=root/f"{cue.cue_id}.wav"
        renderer.render(text=cue.text,reference=ref,output_path=raw)
        fit=fit_cue_wav(raw,fitted,slot_samples=cue.target_samples,speaking_rate=cue.speaking_rate,ffmpeg=ffmpeg)
        paths[cue.cue_id]=fitted; rows.append({"cue_id":cue.cue_id,"reference_candidate_id":ref.candidate_id,**fit})
    assembled=assemble_cue_wavs(plan,paths,output); assembled["rendering"]=rows; return assembled


def qwen_preflight(*,model_root:str|Path,reference_wav:str|Path|None=None,reference_text:str|Path|None=None,ffmpeg:str="ffmpeg")->dict[str,Any]:
    checks={"model_root":Path(model_root).is_dir(),"ffmpeg":shutil.which(ffmpeg) is not None,"numpy":importlib.util.find_spec("numpy") is not None,"soundfile":importlib.util.find_spec("soundfile") is not None,"torch":importlib.util.find_spec("torch") is not None,"qwen_tts":importlib.util.find_spec("qwen_tts") is not None}
    if reference_wav is not None: checks["reference_wav"]=Path(reference_wav).is_file()
    if reference_text is not None: checks["reference_text"]=Path(reference_text).is_file()
    cuda=None
    if checks["torch"]:
        try: cuda=bool(importlib.import_module("torch").cuda.is_available())
        except Exception: cuda=None
    checks["cuda"]=cuda
    blocked=any(v is False for k,v in checks.items() if k!="cuda")
    state="BLOCKED" if blocked else ("READY_WITH_WARNING" if cuda is not True else "READY")
    return {"state":state,"checks":checks,"model_loaded":False,"generation_started":False}


def _load_candidates(path:Path)->tuple[VoiceReferenceCandidate,...]:
    data=json.loads(path.read_text(encoding='utf-8')); out=[]
    for x in data.get("candidates",[]):
        candidate=VoiceReferenceCandidate(x["candidate_id"],Path(x["wav_path"]),Path(x["transcript_path"]),x["content_sha256"],int(x["duration_samples"]),x["style_id"],x["emotion_id"],bool(x["quality_pass"]),bool(x["owner_approved"]),bool(x["transcript_verified"]))
        if not candidate.wav_path.is_file() or not candidate.transcript_path.is_file():
            raise ValueError("reference file is missing")
        if sha256_file(candidate.wav_path)!=candidate.content_sha256:
            raise ValueError("reference WAV checksum mismatch")
        if not candidate.transcript_path.read_text(encoding="utf-8").strip():
            raise ValueError("reference transcript is empty")
        out.append(candidate)
    return tuple(out)


def prepare_reference_manifest(*, reference_wav:str|Path, reference_text:str|Path, output:str|Path,
                               owner_approved:bool=False, quality_pass:bool=False,
                               transcript_verified:bool=False)->dict[str,Any]:
    """Create the one-reference manifest used by the beginner Windows wrapper."""
    wav_path=Path(reference_wav).resolve(strict=True)
    text_path=Path(reference_text).resolve(strict=True)
    if not text_path.read_text(encoding="utf-8").strip():
        raise ValueError("reference transcript is empty")
    info=read_pcm_wav_info(wav_path,require_canonical=True)
    candidate=VoiceReferenceCandidate(
        "OWNER_NORMAL_001", wav_path, text_path, sha256_file(wav_path), info.sample_count,
        "NORMAL", "NORMAL", quality_pass, owner_approved, transcript_verified,
    )
    if not candidate.eligible:
        raise ValueError("reference confirmations are required")
    manifest=build_reference_manifest((candidate,))
    destination=Path(output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return manifest

def main(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    planp=sub.add_parser('plan'); planp.add_argument('--srt',required=True); planp.add_argument('--output',required=True); planp.add_argument('--style',default='NORMAL'); planp.add_argument('--emotion',default='NORMAL'); planp.add_argument('--speaking-rate',type=float,default=1.0)
    asmp=sub.add_parser('assemble'); asmp.add_argument('--srt',required=True); asmp.add_argument('--cue-dir',required=True); asmp.add_argument('--output',required=True); asmp.add_argument('--report')
    prep=sub.add_parser('preflight'); prep.add_argument('--model-root',required=True); prep.add_argument('--reference-wav'); prep.add_argument('--reference-text'); prep.add_argument('--ffmpeg',default='ffmpeg'); prep.add_argument('--output')
    refp=sub.add_parser('prepare-reference'); refp.add_argument('--reference-wav',required=True); refp.add_argument('--reference-text',required=True); refp.add_argument('--output',required=True); refp.add_argument('--confirm-owner-approved',action='store_true'); refp.add_argument('--confirm-quality-pass',action='store_true'); refp.add_argument('--confirm-transcript-verified',action='store_true')
    rnd=sub.add_parser('render'); rnd.add_argument('--srt',required=True); rnd.add_argument('--model-root',required=True); rnd.add_argument('--references',required=True); rnd.add_argument('--work-dir',required=True); rnd.add_argument('--output',required=True); rnd.add_argument('--report'); rnd.add_argument('--ffmpeg',default='ffmpeg'); rnd.add_argument('--style',default='NORMAL'); rnd.add_argument('--emotion',default='NORMAL'); rnd.add_argument('--speaking-rate',type=float,default=1.0); rnd.add_argument('--allow-neutral-fallback',action='store_true')
    a=p.parse_args(argv)
    if a.cmd=='plan':
        value=[x.to_public_dict() for x in build_srt_plan(a.srt,style_id=a.style,emotion_id=a.emotion,speaking_rate=a.speaking_rate)]; Path(a.output).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); return 0
    if a.cmd=='assemble':
        plan=build_srt_plan(a.srt); d=Path(a.cue_dir); report=assemble_cue_wavs(plan,{x.cue_id:d/f"{x.cue_id}.wav" for x in plan},a.output);
        if a.report: Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return 0
    if a.cmd=='preflight':
        report=qwen_preflight(model_root=a.model_root,reference_wav=a.reference_wav,reference_text=a.reference_text,ffmpeg=a.ffmpeg)
        if a.output: Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        else: print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if report['state']!='BLOCKED' else 2
    if a.cmd=='prepare-reference':
        prepare_reference_manifest(reference_wav=a.reference_wav,reference_text=a.reference_text,output=a.output,
            owner_approved=a.confirm_owner_approved,quality_pass=a.confirm_quality_pass,
            transcript_verified=a.confirm_transcript_verified)
        return 0
    refs=_load_candidates(Path(a.references)); report=render_srt_to_wav(a.srt,renderer=Qwen3OwnerVoiceRenderer(a.model_root,ffmpeg=a.ffmpeg),candidates=refs,work_dir=a.work_dir,output=a.output,style_id=a.style,emotion_id=a.emotion,speaking_rate=a.speaking_rate,allow_neutral_fallback=a.allow_neutral_fallback,ffmpeg=a.ffmpeg)
    if a.report: Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
