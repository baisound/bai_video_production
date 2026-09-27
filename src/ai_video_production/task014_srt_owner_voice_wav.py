"""SRT -> local Owner Voice -> final PCM24 WAV.

The CLI supports planning, assembly of existing Cue WAVs, and local Qwen3-TTS
rendering.  It never truncates speech to make it fit a subtitle slot: bounded
pitch-preserving tempo adjustment is attempted, then the operation fails.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
import argparse, hashlib, importlib, importlib.util, json, math, shutil, subprocess
import urllib.error, urllib.parse, urllib.request

from .subtitle_workspace import SrtWorkspaceCodec
from .owner_voice_wav import SAMPLE_RATE_HZ, SAMPLE_WIDTH_BYTES, copy_pcm24_range, new_canonical_writer, read_pcm_wav_info
from .voice_reference_selector import VoiceReferenceCandidate, build_reference_manifest, select_reference, sha256_file

DEFAULT_MAX_TOTAL_SPEED=1.35
DEFAULT_GPT_SOVITS_URL="http://127.0.0.1:9880"
DEFAULT_GPT_SOVITS_MAX_RESPONSE_BYTES=128*1024*1024

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise urllib.error.HTTPError(req.full_url,code,"GPT-SoVITS redirects are disabled",headers,fp)

_NO_REDIRECT_OPENER=urllib.request.build_opener(_NoRedirectHandler())

def _loopback_urlopen(request:urllib.request.Request,*,timeout:float):
    return _NO_REDIRECT_OPENER.open(request,timeout=timeout)

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
    cue_ids={cue.cue_id for cue in ws.cues}
    if set(overrides)-cue_ids: raise ValueError("cue overrides contain unknown cue ids")
    for cue in ws.cues:
        ov=overrides.get(cue.cue_id,{})
        out.append(OwnerVoiceCuePlan(cue.cue_id, cue.start_ms*48, cue.end_ms*48, cue.text,
                    str(ov.get("style_id",style_id)),str(ov.get("emotion_id",emotion_id)),float(ov.get("speaking_rate",speaking_rate))))
    return tuple(out)


def load_cue_overrides(path:str|Path|None)->dict[str,dict[str,Any]]:
    if path is None: return {}
    value=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("cue overrides must be a JSON object")
    result:dict[str,dict[str,Any]]={}
    for cue_id,raw in value.items():
        if not isinstance(cue_id,str) or not cue_id or len(cue_id)>200 or not isinstance(raw,dict):
            raise ValueError("cue override entry is invalid")
        unknown=set(raw)-{"style_id","emotion_id","speaking_rate"}
        if unknown: raise ValueError("cue override contains unknown fields")
        normalized:dict[str,Any]={}
        for key in ("style_id","emotion_id"):
            if key in raw:
                if not isinstance(raw[key],str) or not raw[key].strip():
                    raise ValueError(f"cue override {key} is invalid")
                normalized[key]=raw[key].strip()
        if "speaking_rate" in raw:
            rate=raw["speaking_rate"]
            if isinstance(rate,bool) or not isinstance(rate,(int,float)) or not math.isfinite(float(rate)):
                raise ValueError("cue override speaking_rate is invalid")
            normalized["speaking_rate"]=float(rate)
        result[cue_id]=normalized
    return result


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


def _validated_loopback_url(value:str)->str:
    parsed=urllib.parse.urlsplit(value)
    if parsed.scheme!="http" or parsed.hostname not in {"127.0.0.1","::1"}:
        raise ValueError("GPT-SoVITS URL must use loopback HTTP")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("GPT-SoVITS URL contains unsupported components")
    if parsed.path not in {"","/"}: raise ValueError("GPT-SoVITS URL must not contain a path")
    try: _=parsed.port
    except ValueError as exc: raise ValueError("GPT-SoVITS URL port is invalid") from exc
    return value.rstrip("/")


def _server_reference_path(path:Path,mode:str)->str:
    resolved=path.resolve(strict=True)
    if mode=="native": return str(resolved)
    if mode!="wsl": raise ValueError("server path mode is invalid")
    drive=resolved.drive
    if not drive or len(drive)!=2 or drive[1] != ":":
        raise ValueError("WSL path translation requires a local drive path")
    relative=resolved.as_posix()[3:]
    return f"/mnt/{drive[0].lower()}/{relative}"


class GptSoVitsHttpRenderer:
    """Render one Cue through a Human-started loopback GPT-SoVITS v2 API."""
    def __init__(self,base_url:str=DEFAULT_GPT_SOVITS_URL,*,gpt_weights_path:str,sovits_weights_path:str,
                 server_path_mode:str="wsl",ffmpeg:str="ffmpeg",timeout_seconds:float=180.0,
                 max_response_bytes:int=DEFAULT_GPT_SOVITS_MAX_RESPONSE_BYTES,
                 opener:Callable[...,Any]=_loopback_urlopen):
        self.base_url=_validated_loopback_url(base_url)
        if not isinstance(gpt_weights_path,str) or not gpt_weights_path.strip(): raise ValueError("GPT weights path is required")
        if not isinstance(sovits_weights_path,str) or not sovits_weights_path.strip(): raise ValueError("SoVITS weights path is required")
        if server_path_mode not in {"native","wsl"}: raise ValueError("server path mode is invalid")
        if not isinstance(timeout_seconds,(int,float)) or timeout_seconds<=0: raise ValueError("timeout must be positive")
        if isinstance(max_response_bytes,bool) or not isinstance(max_response_bytes,int) or max_response_bytes<=0:
            raise ValueError("response limit must be positive")
        self.gpt_weights_path=gpt_weights_path.strip(); self.sovits_weights_path=sovits_weights_path.strip()
        self.server_path_mode=server_path_mode; self.ffmpeg=ffmpeg; self.timeout_seconds=float(timeout_seconds)
        self.max_response_bytes=max_response_bytes; self._opener=opener; self._configured=False

    def _read(self,request:urllib.request.Request,*,limit:int)->tuple[bytes,str]:
        try:
            with self._opener(request,timeout=self.timeout_seconds) as response:
                length=response.headers.get("Content-Length")
                try: declared_length=None if length is None else int(length)
                except ValueError as exc: raise RuntimeError("GPT-SoVITS response length is invalid") from exc
                if declared_length is not None and declared_length>limit: raise RuntimeError("GPT-SoVITS response exceeded the size limit")
                data=response.read(limit+1)
                if len(data)>limit: raise RuntimeError("GPT-SoVITS response exceeded the size limit")
                return data,response.headers.get_content_type()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"GPT-SoVITS request failed with HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("GPT-SoVITS loopback server is unavailable") from exc

    def _set_weights(self,endpoint:str,path:str)->None:
        url=f"{self.base_url}/{endpoint}?{urllib.parse.urlencode({'weights_path':path})}"
        body,content_type=self._read(urllib.request.Request(url,method="GET"),limit=64*1024)
        try: value=json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise RuntimeError("GPT-SoVITS weight response is invalid") from exc
        if content_type!="application/json" or value!={"message":"success"}:
            raise RuntimeError("GPT-SoVITS rejected the selected weights")

    def configure(self)->None:
        if self._configured: return
        self._set_weights("set_sovits_weights",self.sovits_weights_path)
        self._set_weights("set_gpt_weights",self.gpt_weights_path)
        self._configured=True

    def render(self,*,text:str,reference:VoiceReferenceCandidate,output_path:Path)->None:
        self.configure()
        prompt_text=reference.transcript_path.read_text(encoding="utf-8").strip()
        if not prompt_text: raise ValueError("reference transcript is empty")
        payload={"text":text,"text_lang":"ja","ref_audio_path":_server_reference_path(reference.wav_path,self.server_path_mode),
                 "prompt_text":prompt_text,"prompt_lang":"ja","text_split_method":"cut5","batch_size":1,
                 "speed_factor":1.0,"seed":-1,"media_type":"wav","streaming_mode":False}
        request=urllib.request.Request(f"{self.base_url}/tts",data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type":"application/json","Accept":"audio/wav"},method="POST")
        body,content_type=self._read(request,limit=self.max_response_bytes)
        if content_type not in {"audio/wav","audio/x-wav","application/octet-stream"} or not body.startswith(b"RIFF"):
            raise RuntimeError("GPT-SoVITS returned invalid WAV audio")
        output_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=output_path.with_suffix(".gpt-sovits.wav")
        temporary.write_bytes(body)
        try:
            proc=subprocess.run([self.ffmpeg,"-nostdin","-hide_banner","-loglevel","error","-y","-i",str(temporary),
                "-ar","48000","-ac","1","-c:a","pcm_s24le",str(output_path)],stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,check=False,timeout=180,shell=False)
            if proc.returncode!=0: raise RuntimeError("GPT-SoVITS output normalization failed")
            read_pcm_wav_info(output_path,require_canonical=True)
        finally: temporary.unlink(missing_ok=True)


def gpt_sovits_preflight(*,base_url:str,gpt_weights_path:str,sovits_weights_path:str,ffmpeg:str="ffmpeg",
                         opener:Callable[...,Any]=_loopback_urlopen)->dict[str,Any]:
    checks={"loopback_url":False,"ffmpeg":shutil.which(ffmpeg) is not None,"server_contract":False,
            "gpt_weights_path":bool(gpt_weights_path.strip()),"sovits_weights_path":bool(sovits_weights_path.strip())}
    try:
        url=_validated_loopback_url(base_url); checks["loopback_url"]=True
        request=urllib.request.Request(f"{url}/openapi.json",method="GET")
        with opener(request,timeout=10.0) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)<=2*1024*1024:
            contract=json.loads(raw.decode("utf-8")); paths=contract.get("paths",{})
            checks["server_contract"]=all(path in paths for path in ("/tts","/set_gpt_weights","/set_sovits_weights"))
    except (ValueError,urllib.error.URLError,urllib.error.HTTPError,UnicodeDecodeError,json.JSONDecodeError): pass
    return {"state":"READY" if all(checks.values()) else "BLOCKED","checks":checks,"model_loaded":False,"generation_started":False}


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
    planp=sub.add_parser('plan'); planp.add_argument('--srt',required=True); planp.add_argument('--output',required=True); planp.add_argument('--style',default='NORMAL'); planp.add_argument('--emotion',default='NORMAL'); planp.add_argument('--speaking-rate',type=float,default=1.0); planp.add_argument('--cue-overrides')
    asmp=sub.add_parser('assemble'); asmp.add_argument('--srt',required=True); asmp.add_argument('--cue-dir',required=True); asmp.add_argument('--output',required=True); asmp.add_argument('--report')
    prep=sub.add_parser('preflight'); prep.add_argument('--backend',choices=('qwen3','gpt-sovits'),default='qwen3'); prep.add_argument('--model-root'); prep.add_argument('--reference-wav'); prep.add_argument('--reference-text'); prep.add_argument('--ffmpeg',default='ffmpeg'); prep.add_argument('--output'); prep.add_argument('--gpt-sovits-url',default=DEFAULT_GPT_SOVITS_URL); prep.add_argument('--gpt-weights'); prep.add_argument('--sovits-weights')
    refp=sub.add_parser('prepare-reference'); refp.add_argument('--reference-wav',required=True); refp.add_argument('--reference-text',required=True); refp.add_argument('--output',required=True); refp.add_argument('--confirm-owner-approved',action='store_true'); refp.add_argument('--confirm-quality-pass',action='store_true'); refp.add_argument('--confirm-transcript-verified',action='store_true')
    rnd=sub.add_parser('render'); rnd.add_argument('--backend',choices=('qwen3','gpt-sovits'),default='qwen3'); rnd.add_argument('--srt',required=True); rnd.add_argument('--model-root'); rnd.add_argument('--references',required=True); rnd.add_argument('--work-dir',required=True); rnd.add_argument('--output',required=True); rnd.add_argument('--report'); rnd.add_argument('--ffmpeg',default='ffmpeg'); rnd.add_argument('--style',default='NORMAL'); rnd.add_argument('--emotion',default='NORMAL'); rnd.add_argument('--speaking-rate',type=float,default=1.0); rnd.add_argument('--cue-overrides'); rnd.add_argument('--allow-neutral-fallback',action='store_true'); rnd.add_argument('--gpt-sovits-url',default=DEFAULT_GPT_SOVITS_URL); rnd.add_argument('--gpt-weights'); rnd.add_argument('--sovits-weights'); rnd.add_argument('--server-path-mode',choices=('native','wsl'),default='wsl')
    a=p.parse_args(argv)
    if a.cmd=='plan':
        value=[x.to_public_dict() for x in build_srt_plan(a.srt,style_id=a.style,emotion_id=a.emotion,speaking_rate=a.speaking_rate,cue_overrides=load_cue_overrides(a.cue_overrides))]; Path(a.output).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); return 0
    if a.cmd=='assemble':
        plan=build_srt_plan(a.srt); d=Path(a.cue_dir); report=assemble_cue_wavs(plan,{x.cue_id:d/f"{x.cue_id}.wav" for x in plan},a.output);
        if a.report: Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return 0
    if a.cmd=='preflight':
        if a.backend=='qwen3':
            if not a.model_root: p.error('--model-root is required for qwen3')
            report=qwen_preflight(model_root=a.model_root,reference_wav=a.reference_wav,reference_text=a.reference_text,ffmpeg=a.ffmpeg)
        else:
            if not a.gpt_weights or not a.sovits_weights: p.error('--gpt-weights and --sovits-weights are required for gpt-sovits')
            report=gpt_sovits_preflight(base_url=a.gpt_sovits_url,gpt_weights_path=a.gpt_weights,sovits_weights_path=a.sovits_weights,ffmpeg=a.ffmpeg)
        if a.output: Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        else: print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if report['state']!='BLOCKED' else 2
    if a.cmd=='prepare-reference':
        prepare_reference_manifest(reference_wav=a.reference_wav,reference_text=a.reference_text,output=a.output,
            owner_approved=a.confirm_owner_approved,quality_pass=a.confirm_quality_pass,
            transcript_verified=a.confirm_transcript_verified)
        return 0
    refs=_load_candidates(Path(a.references))
    if a.backend=='qwen3':
        if not a.model_root: p.error('--model-root is required for qwen3')
        renderer:CueRenderer=Qwen3OwnerVoiceRenderer(a.model_root,ffmpeg=a.ffmpeg)
    else:
        if not a.gpt_weights or not a.sovits_weights: p.error('--gpt-weights and --sovits-weights are required for gpt-sovits')
        renderer=GptSoVitsHttpRenderer(a.gpt_sovits_url,gpt_weights_path=a.gpt_weights,sovits_weights_path=a.sovits_weights,server_path_mode=a.server_path_mode,ffmpeg=a.ffmpeg)
    report=render_srt_to_wav(a.srt,renderer=renderer,candidates=refs,work_dir=a.work_dir,output=a.output,style_id=a.style,emotion_id=a.emotion,speaking_rate=a.speaking_rate,cue_overrides=load_cue_overrides(a.cue_overrides),allow_neutral_fallback=a.allow_neutral_fallback,ffmpeg=a.ffmpeg)
    if a.report: Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
