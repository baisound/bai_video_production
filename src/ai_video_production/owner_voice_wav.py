"""Small PCM WAV helpers used by the local Owner Voice pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import wave

SAMPLE_RATE_HZ=48_000
CHANNELS=1
SAMPLE_WIDTH_BYTES=3

@dataclass(frozen=True, slots=True)
class PcmWavInfo:
    sample_rate_hz:int
    channels:int
    sample_width_bytes:int
    sample_count:int

    @property
    def duration_seconds(self)->float:
        return self.sample_count/self.sample_rate_hz


def read_pcm_wav_info(path:str|Path, *, require_canonical:bool=False)->PcmWavInfo:
    p=Path(path)
    if not p.is_file(): raise ValueError("WAV does not exist")
    try:
        with wave.open(str(p),'rb') as w:
            if w.getcomptype()!='NONE': raise ValueError("compressed WAV is unsupported")
            info=PcmWavInfo(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())
    except wave.Error as exc:
        raise ValueError("invalid PCM WAV") from exc
    if info.sample_count<=0: raise ValueError("WAV is empty")
    if require_canonical and (info.sample_rate_hz,info.channels,info.sample_width_bytes)!=(SAMPLE_RATE_HZ,CHANNELS,SAMPLE_WIDTH_BYTES):
        raise ValueError("WAV must be 48000 Hz mono PCM24")
    return info


def copy_pcm24_range(source:str|Path, target:wave.Wave_write, start_sample:int, end_sample:int, *, chunk_frames:int=262_144)->None:
    if start_sample<0 or end_sample<=start_sample: raise ValueError("sample range is invalid")
    with wave.open(str(source),'rb') as r:
        info=PcmWavInfo(r.getframerate(),r.getnchannels(),r.getsampwidth(),r.getnframes())
        if (info.sample_rate_hz,info.channels,info.sample_width_bytes)!=(SAMPLE_RATE_HZ,CHANNELS,SAMPLE_WIDTH_BYTES):
            raise ValueError("source must be canonical PCM24")
        if end_sample>info.sample_count: raise ValueError("sample range exceeds source")
        r.setpos(start_sample)
        remaining=end_sample-start_sample
        while remaining:
            n=min(remaining,chunk_frames)
            data=r.readframes(n)
            if len(data)!=n*SAMPLE_WIDTH_BYTES: raise ValueError("truncated WAV")
            target.writeframesraw(data)
            remaining-=n


def read_pcm24_samples(path:str|Path,start_sample:int,end_sample:int)->list[int]:
    with wave.open(str(path),'rb') as r:
        if (r.getframerate(),r.getnchannels(),r.getsampwidth())!=(SAMPLE_RATE_HZ,CHANNELS,SAMPLE_WIDTH_BYTES):
            raise ValueError("source must be canonical PCM24")
        if start_sample<0 or end_sample<=start_sample or end_sample>r.getnframes(): raise ValueError("sample range invalid")
        r.setpos(start_sample); raw=r.readframes(end_sample-start_sample)
    out=[]
    for i in range(0,len(raw),3):
        x=raw[i] | (raw[i+1]<<8) | (raw[i+2]<<16)
        if x & 0x800000: x-=1<<24
        out.append(x)
    return out


def encode_pcm24_samples(values:list[int])->bytes:
    out=bytearray(len(values)*3)
    j=0
    for x in values:
        x=max(-8388608,min(8388607,int(x)))
        if x<0: x+=1<<24
        out[j]=x&255; out[j+1]=(x>>8)&255; out[j+2]=(x>>16)&255; j+=3
    return bytes(out)


def new_canonical_writer(path:str|Path)->wave.Wave_write:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    w=wave.open(str(p),'wb'); w.setnchannels(CHANNELS); w.setsampwidth(SAMPLE_WIDTH_BYTES); w.setframerate(SAMPLE_RATE_HZ)
    return w

__all__=["CHANNELS","PcmWavInfo","SAMPLE_RATE_HZ","SAMPLE_WIDTH_BYTES","copy_pcm24_range","encode_pcm24_samples","new_canonical_writer","read_pcm24_samples","read_pcm_wav_info"]
