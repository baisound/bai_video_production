"""Small PCM WAV helpers used by the local Owner Voice pipeline."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import struct
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


@dataclass(frozen=True, slots=True)
class _PcmWavLayout:
    info:PcmWavInfo
    data_offset:int
    data_size:int


_PCM_FORMAT_TAG=0x0001
_EXTENSIBLE_FORMAT_TAG=0xFFFE
_PCM_SUBFORMAT_GUID=bytes.fromhex("0100000000001000800000aa00389b71")


def _read_pcm_wav_layout(path:str|Path)->_PcmWavLayout:
    """Read PCM RIFF/WAVE metadata without depending on Python's wave parser.

    Python 3.11 rejects WAVE_FORMAT_EXTENSIBLE even when its subformat is
    ordinary PCM. FFmpeg legitimately emits that header for packed PCM24, so
    the Owner Voice contract parses the two supported PCM headers explicitly.
    """
    p=Path(path)
    if not p.is_file(): raise ValueError("WAV does not exist")
    file_size=p.stat().st_size
    try:
        with p.open("rb") as stream:
            header=stream.read(12)
            if len(header)!=12 or header[:4]!=b"RIFF" or header[8:]!=b"WAVE":
                raise ValueError("invalid PCM WAV")
            fmt:tuple[int,int,int]|None=None
            data_offset=data_size=None
            while stream.tell()+8<=file_size:
                chunk_header=stream.read(8)
                chunk_id=chunk_header[:4]
                chunk_size=struct.unpack("<I",chunk_header[4:])[0]
                chunk_start=stream.tell()
                chunk_end=chunk_start+chunk_size
                if chunk_end>file_size: raise ValueError("truncated WAV chunk")
                # Python's wave writer omits the optional final data pad byte.
                padded_end=chunk_end+((chunk_size&1) if chunk_end<file_size else 0)
                if padded_end>file_size: raise ValueError("truncated WAV padding")
                if chunk_id==b"fmt ":
                    if fmt is not None: raise ValueError("duplicate WAV fmt chunk")
                    raw=stream.read(chunk_size)
                    if len(raw)<16: raise ValueError("invalid WAV fmt chunk")
                    format_tag,channels,rate,byte_rate,block_align,bits=struct.unpack_from("<HHIIHH",raw)
                    if format_tag==_EXTENSIBLE_FORMAT_TAG:
                        if len(raw)<40 or struct.unpack_from("<H",raw,16)[0]<22:
                            raise ValueError("invalid extensible WAV fmt chunk")
                        valid_bits=struct.unpack_from("<H",raw,18)[0]
                        if raw[24:40]!=_PCM_SUBFORMAT_GUID or valid_bits!=bits:
                            raise ValueError("unsupported extensible WAV subtype")
                    elif format_tag!=_PCM_FORMAT_TAG:
                        raise ValueError("compressed WAV is unsupported")
                    if channels<=0 or rate<=0 or bits<=0 or bits%8:
                        raise ValueError("invalid PCM WAV format")
                    width=bits//8
                    if block_align!=channels*width or byte_rate!=rate*block_align:
                        raise ValueError("invalid PCM WAV alignment")
                    fmt=(rate,channels,width)
                elif chunk_id==b"data":
                    if data_offset is not None: raise ValueError("duplicate WAV data chunk")
                    data_offset=chunk_start; data_size=chunk_size
                stream.seek(padded_end)
            if stream.tell()!=file_size: raise ValueError("truncated WAV chunk header")
    except OSError as exc:
        raise ValueError("invalid PCM WAV") from exc
    if fmt is None or data_offset is None or data_size is None:
        raise ValueError("invalid PCM WAV")
    rate,channels,width=fmt
    block_align=channels*width
    if data_size%block_align: raise ValueError("unaligned PCM WAV data")
    info=PcmWavInfo(rate,channels,width,data_size//block_align)
    return _PcmWavLayout(info,data_offset,data_size)


def read_pcm_wav_info(path:str|Path, *, require_canonical:bool=False)->PcmWavInfo:
    info=_read_pcm_wav_layout(path).info
    if info.sample_count<=0: raise ValueError("WAV is empty")
    if require_canonical and (info.sample_rate_hz,info.channels,info.sample_width_bytes)!=(SAMPLE_RATE_HZ,CHANNELS,SAMPLE_WIDTH_BYTES):
        raise ValueError("WAV must be 48000 Hz mono PCM24")
    return info


def copy_pcm24_range(source:str|Path, target:wave.Wave_write, start_sample:int, end_sample:int, *, chunk_frames:int=262_144)->None:
    if start_sample<0 or end_sample<=start_sample or chunk_frames<=0: raise ValueError("sample range is invalid")
    layout=_read_pcm_wav_layout(source); info=layout.info
    if (info.sample_rate_hz,info.channels,info.sample_width_bytes)!=(SAMPLE_RATE_HZ,CHANNELS,SAMPLE_WIDTH_BYTES):
        raise ValueError("source must be canonical PCM24")
    if end_sample>info.sample_count: raise ValueError("sample range exceeds source")
    with Path(source).open('rb') as r:
        r.seek(layout.data_offset+start_sample*SAMPLE_WIDTH_BYTES)
        remaining=end_sample-start_sample
        while remaining:
            n=min(remaining,chunk_frames)
            data=r.read(n*SAMPLE_WIDTH_BYTES)
            if len(data)!=n*SAMPLE_WIDTH_BYTES: raise ValueError("truncated WAV")
            target.writeframesraw(data)
            remaining-=n


def _decode_pcm24(raw:bytes)->list[int]:
    out=[]
    for i in range(0,len(raw),3):
        x=raw[i] | (raw[i+1]<<8) | (raw[i+2]<<16)
        if x & 0x800000: x-=1<<24
        out.append(x)
    return out


def read_pcm24_samples(path:str|Path,start_sample:int,end_sample:int)->list[int]:
    return next(iter_pcm24_sample_chunks(path,start_sample,end_sample,chunk_frames=end_sample-start_sample))


def iter_pcm24_sample_chunks(path:str|Path, start_sample:int=0, end_sample:int|None=None, *, chunk_frames:int=262_144)->Iterator[list[int]]:
    layout=_read_pcm_wav_layout(path); info=layout.info
    if (info.sample_rate_hz,info.channels,info.sample_width_bytes)!=(SAMPLE_RATE_HZ,CHANNELS,SAMPLE_WIDTH_BYTES):
        raise ValueError("source must be canonical PCM24")
    stop=info.sample_count if end_sample is None else end_sample
    if start_sample<0 or stop<=start_sample or stop>info.sample_count or chunk_frames<=0: raise ValueError("sample range invalid")
    with Path(path).open('rb') as stream:
        stream.seek(layout.data_offset+start_sample*SAMPLE_WIDTH_BYTES)
        remaining=stop-start_sample
        while remaining:
            frames=min(remaining,chunk_frames); raw=stream.read(frames*SAMPLE_WIDTH_BYTES)
            if len(raw)!=frames*SAMPLE_WIDTH_BYTES: raise ValueError("truncated WAV")
            yield _decode_pcm24(raw)
            remaining-=frames


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

__all__=["CHANNELS","PcmWavInfo","SAMPLE_RATE_HZ","SAMPLE_WIDTH_BYTES","copy_pcm24_range","encode_pcm24_samples","iter_pcm24_sample_chunks","new_canonical_writer","read_pcm24_samples","read_pcm_wav_info"]
