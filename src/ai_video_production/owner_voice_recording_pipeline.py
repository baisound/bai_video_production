"""Local Owner Voice recording preparation pipeline.

This module connects existing Voice Studio contracts to practical local files:
OBS/raw WAV -> canonical 48 kHz mono PCM24 -> ASR -> safe 3-15 second
Dataset/reference segments -> speech-continuous WAV -> coverage/workspace reports.
Raw recordings are never overwritten.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import argparse, hashlib, json, math, os, shutil, statistics, subprocess, tempfile, wave

from .atomic import AtomicJsonWriter
from .cut_candidates import load_transcript_manifest
from .faster_whisper_asr import FasterWhisperConfig, FasterWhisperProvider
from .large_media_transcription import ChunkedTranscriptionConfig, ResumableTranscriptionService
from .owner_voice_wav import (
    SAMPLE_RATE_HZ, SAMPLE_WIDTH_BYTES, copy_pcm24_range, encode_pcm24_samples,
    new_canonical_writer, read_pcm24_samples, read_pcm_wav_info,
)
from .subtitles import TranscriptManifest, TranscriptSegment, TranscriptWord
from .voice_recording_coverage import (
    RecordingCoverageSegment, RecordingCoverageTarget, compute_recording_coverage,
)
from .voice_reference_selector import VoiceReferenceCandidate, build_reference_manifest, sha256_file


def _sha(path: Path) -> str:
    return sha256_file(path)


def _json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict): raise ValueError('JSON root must be an object')
    return value


def _ffprobe(path: Path, ffprobe: str='ffprobe') -> dict[str, Any]:
    proc=subprocess.run([ffprobe,'-v','error','-select_streams','a:0','-show_entries','stream=codec_name,sample_fmt,sample_rate,channels,duration','-of','json',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120,shell=False)
    if proc.returncode!=0: raise RuntimeError('ffprobe could not inspect recording')
    data=json.loads(proc.stdout.decode('utf-8')); streams=data.get('streams',[])
    if len(streams)!=1: raise ValueError('recording must expose exactly one selected audio stream')
    return streams[0]


def canonicalize_obs_recording(
    source: str|Path, output: str|Path, *, report_path: str|Path|None=None,
    channel_index: int|None=None, ffmpeg: str='ffmpeg', ffprobe: str='ffprobe', resume: bool=True,
) -> dict[str, Any]:
    """Convert one local recording to canonical 48kHz/mono/PCM24 without mutating source."""
    src=Path(source).resolve(); dst=Path(output).resolve(); report=Path(report_path).resolve() if report_path else dst.with_suffix('.canonical.json')
    if not src.is_file() or src.stat().st_size<=0: raise ValueError('source recording is missing or empty')
    source_sha=_sha(src)
    if resume and dst.is_file() and report.is_file():
        old=_json(report)
        if old.get('source_sha256')!=source_sha or old.get('output_sha256')!=_sha(dst): raise ValueError('existing canonical output/report does not match source')
        read_pcm_wav_info(dst,require_canonical=True)
        return old
    if dst.exists()!=report.exists(): raise ValueError('partial canonicalization output exists')
    stream=_ffprobe(src,ffprobe); channels=int(stream['channels']); rate=int(stream['sample_rate']); sample_fmt=str(stream.get('sample_fmt','unknown'))
    if channels<1: raise ValueError('source channel count is invalid')
    if channels>1:
        if channel_index is None: raise ValueError('multichannel input requires explicit channel_index')
        if not 0<=channel_index<channels: raise ValueError('channel_index is outside source channels')
        af=f'pan=mono|c0=c{channel_index},aresample=48000:resampler=soxr:precision=28:dither_method=triangular'
        channel_policy=f'SELECT_CHANNEL_{channel_index}'
    else:
        if channel_index not in (None,0): raise ValueError('mono input cannot select a nonzero channel')
        af='aresample=48000:resampler=soxr:precision=28:dither_method=triangular'; channel_policy='MONO_PRESERVE'
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_suffix(dst.suffix+'.tmp.wav'); tmp.unlink(missing_ok=True)
    argv=[ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-y','-i',str(src),'-map','0:a:0','-vn','-af',af,'-ar','48000','-ac','1','-c:a','pcm_s24le',str(tmp)]
    proc=subprocess.run(argv,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False,timeout=3600,shell=False)
    if proc.returncode!=0: tmp.unlink(missing_ok=True); raise RuntimeError('ffmpeg canonicalization failed')
    info=read_pcm_wav_info(tmp,require_canonical=True); os.replace(tmp,dst)
    if _sha(src)!=source_sha: raise RuntimeError('raw source changed during canonicalization')
    body={
        'report_version':'1.0.0','source_sha256':source_sha,'source_size_bytes':src.stat().st_size,
        'source_sample_rate_hz':rate,'source_channels':channels,'source_sample_format':sample_fmt,
        'channel_policy':channel_policy,'resampler':'libsoxr','resampler_precision':28,'dither_policy':'FFMPEG_TRIANGULAR_TPDF',
        'output_sample_rate_hz':48_000,'output_channels':1,'output_sample_format':'PCM_S24LE','output_samples':info.sample_count,
        'output_sha256':_sha(dst),'raw_source_preserved':True,'source_sha256_after':_sha(src),
    }
    AtomicJsonWriter.write(report,body); return body


def analyze_canonical_recording(path: str|Path, *, chunk_frames: int=48_000) -> dict[str, Any]:
    """Streaming calibration metrics for canonical recording."""
    p=Path(path); info=read_pcm_wav_info(p,require_canonical=True)
    peak=0; sum_sq=0.0; count=0; clipped=0; chunk_rms=[]; dc_sum=0
    with wave.open(str(p),'rb') as w:
        while True:
            raw=w.readframes(chunk_frames)
            if not raw: break
            vals=[]
            for i in range(0,len(raw),3):
                x=raw[i]|(raw[i+1]<<8)|(raw[i+2]<<16); x=x-(1<<24) if x&0x800000 else x; vals.append(x)
            if not vals: continue
            local_sq=sum(x*x for x in vals); local_peak=max(abs(x) for x in vals)
            peak=max(peak,local_peak); sum_sq+=local_sq; count+=len(vals); dc_sum+=sum(vals); clipped+=sum(1 for x in vals if abs(x)>=8387000)
            chunk_rms.append(math.sqrt(local_sq/len(vals))/8388607)
    if not count: raise ValueError('recording contains no samples')
    rms=math.sqrt(sum_sq/count)/8388607; peak_norm=peak/8388607
    db=lambda x: -120.0 if x<=0 else 20*math.log10(x)
    sorted_chunks=sorted(chunk_rms); noise=sorted_chunks[max(0,min(len(sorted_chunks)-1,int(len(sorted_chunks)*0.1)))]
    noise_db=db(noise); rms_db=db(rms); peak_db=db(peak_norm)
    return {'sample_rate_hz':48_000,'channels':1,'sample_format':'PCM_S24LE','sample_count':info.sample_count,'duration_seconds':info.duration_seconds,
            'peak_dbfs':peak_db,'rms_dbfs':rms_db,'headroom_db':-peak_db,'clip_sample_count':clipped,'noise_floor_estimate_dbfs':noise_db,
            'snr_estimate_db':rms_db-noise_db,'dc_offset_abs':abs(dc_sum/count)/8388607}


def recording_start_preflight(*,obs_current:bool,sample_rate_hz:int,gain_ready:bool,meter_peak_dbfs:float|None,target_floor_dbfs:float,target_ceiling_dbfs:float,quality_state:str,clip_sample_count:int,noise_floor_dbfs:float|None=None,snr_db:float|None=None)->dict[str,Any]:
    blockers=[]; unknown=[]
    if obs_current is not True: blockers.append('OBS_INPUT_NOT_CURRENT')
    if sample_rate_hz!=48_000: blockers.append('SAMPLE_RATE_NOT_48000')
    if gain_ready is not True: blockers.append('GAIN_NOT_READY')
    if clip_sample_count!=0: blockers.append('CLIPPING_DETECTED')
    if meter_peak_dbfs is None: unknown.append('PEAK_UNKNOWN')
    elif not target_floor_dbfs<=meter_peak_dbfs<=target_ceiling_dbfs: blockers.append('PEAK_OUTSIDE_TARGET')
    if quality_state=='FAIL': blockers.append('CANONICAL_QUALITY_NOT_PASS')
    elif quality_state=='UNKNOWN': unknown.append('CANONICAL_QUALITY_UNKNOWN')
    elif quality_state!='PASS': raise ValueError('quality_state must be PASS, FAIL, or UNKNOWN')
    state='BLOCKED' if blockers else ('UNKNOWN' if unknown else 'READY')
    reasons=blockers+unknown
    return {'state':state,'recording_start_authorized':state=='READY','reason_codes':reasons,'sample_rate_hz':sample_rate_hz,'peak_dbfs':meter_peak_dbfs,'target_floor_dbfs':target_floor_dbfs,'target_ceiling_dbfs':target_ceiling_dbfs,'clip_sample_count':clip_sample_count,'noise_floor_dbfs':noise_floor_dbfs,'snr_db':snr_db}


def _quiet_ratio(path:Path,start:int,end:int,threshold:int)->float:
    if end<=start: return 1.0
    quiet=total=0
    with wave.open(str(path),'rb') as w:
        w.setpos(start); remain=end-start
        while remain:
            n=min(remain,262_144); raw=w.readframes(n); remain-=n
            for i in range(0,len(raw),3):
                x=raw[i]|(raw[i+1]<<8)|(raw[i+2]<<16); x=x-(1<<24) if x&0x800000 else x; total+=1
                if abs(x)<=threshold: quiet+=1
    return quiet/total if total else 1.0


def _merge_ranges(ranges:Iterable[tuple[int,int]])->list[tuple[int,int]]:
    result=[]
    for a,b in sorted(ranges):
        if b<=a: continue
        if not result or a>result[-1][1]: result.append([a,b])
        else: result[-1][1]=max(result[-1][1],b)
    return [(a,b) for a,b in result]


def _speech_retained_ranges(path:Path, transcript:TranscriptManifest, *, quiet_dbfs:float=-50.0, quiet_ratio_min:float=.98)->tuple[list[tuple[int,int]],list[dict[str,Any]]]:
    info=read_pcm_wav_info(path,require_canonical=True); total=info.sample_count; speech=[]
    for s in transcript.segments:
        a=max(0,(s.start_us*48_000)//1_000_000); b=min(total,math.ceil(s.end_us*48_000/1_000_000));
        if b>a: speech.append((a,b))
    if not speech: raise ValueError('transcript contains no speech segments')
    speech=_merge_ranges(speech); threshold=round(8388607*(10**(quiet_dbfs/20)))
    removals=[]; gap_reports=[]; prev=0
    for a,b in speech+[(total,total)]:
        gap_a=prev; gap_b=a; gap=gap_b-gap_a
        if gap>=48_000:
            ratio=_quiet_ratio(path,gap_a,gap_b,threshold); confirmed=ratio>=quiet_ratio_min
            gap_reports.append({'start_sample':gap_a,'end_sample':gap_b,'samples':gap,'quiet_ratio':ratio,'confirmed_non_speech':confirmed})
            if confirmed:
                # Preserve 125 ms after prior speech and 50 ms before next speech.
                left=gap_a+(6_000 if gap_a>0 else 0); right=gap_b-(2_400 if gap_b<total else 0)
                if right>left: removals.append((left,right))
        prev=max(prev,b)
    retained=[]; cursor=0
    for a,b in removals:
        if cursor<a: retained.append((cursor,a))
        cursor=b
    if cursor<total: retained.append((cursor,total))
    retained=_merge_ranges(retained)
    return retained,gap_reports


def _crossfade(a:list[int],b:list[int])->list[int]:
    n=min(len(a),len(b)); out=[]
    for i in range(n):
        theta=((i+1)/(n+1))*math.pi/2; out.append(round(a[i]*math.cos(theta)+b[i]*math.sin(theta)))
    return out


def create_speech_continuous_wav(canonical_wav:str|Path,transcript:TranscriptManifest,output:str|Path,*,report_path:str|Path|None=None,fade_samples:int=240)->dict[str,Any]:
    src=Path(canonical_wav); dst=Path(output); info=read_pcm_wav_info(src,require_canonical=True)
    retained,gaps=_speech_retained_ranges(src,transcript)
    if not retained: raise ValueError('no retained speech ranges')
    for a,b in retained:
        if b-a < fade_samples and len(retained)>1: raise ValueError('retained range too short for crossfade')
    with new_canonical_writer(dst) as w:
        tail=None; output_samples=0
        for idx,(a,b) in enumerate(retained):
            has_next=idx<len(retained)-1
            if idx==0:
                inner_end=b-fade_samples if has_next else b
                if inner_end>a: copy_pcm24_range(src,w,a,inner_end); output_samples+=inner_end-a
                tail=read_pcm24_samples(src,b-fade_samples,b) if has_next else None
            else:
                head=read_pcm24_samples(src,a,a+fade_samples); mixed=_crossfade(tail or [],head); w.writeframesraw(encode_pcm24_samples(mixed)); output_samples+=len(mixed)
                inner_start=a+fade_samples; inner_end=b-fade_samples if has_next else b
                if inner_end>inner_start: copy_pcm24_range(src,w,inner_start,inner_end); output_samples+=inner_end-inner_start
                tail=read_pcm24_samples(src,b-fade_samples,b) if has_next else None
    final=read_pcm_wav_info(dst,require_canonical=True)
    removed=info.sample_count-final.sample_count
    report={'report_version':'1.0.0','input_sha256':_sha(src),'output_sha256':_sha(dst),'input_samples':info.sample_count,'output_samples':final.sample_count,'removed_samples':removed,'input_duration_seconds':info.duration_seconds,'output_duration_seconds':final.duration_seconds,'removed_duration_seconds':removed/48_000,'retained_ranges':[{'start_sample':a,'end_sample':b} for a,b in retained],'gap_analysis':gaps,'crossfade_samples_per_boundary':fade_samples,'boundary_count':max(0,len(retained)-1),'raw_source_preserved':True}
    if report_path: AtomicJsonWriter.write(Path(report_path),report)
    return report


def _split_transcript(transcript:TranscriptManifest,*,min_seconds:float=3,max_seconds:float=15)->tuple[list[tuple[int,int,str]],list[str]]:
    min_us=round(min_seconds*1e6); max_us=round(max_seconds*1e6); out=[]; omitted=[]; i=0; segs=list(transcript.segments)
    while i<len(segs):
        s=segs[i]; dur=s.end_us-s.start_us
        if min_us<=dur<=max_us: out.append((s.start_us,s.end_us,s.text)); i+=1; continue
        if dur>max_us and s.words:
            words=list(s.words); j=0
            while j<len(words):
                start=words[j].start_us; end=start; texts=[]; k=j
                while k<len(words) and words[k].end_us-start<=max_us:
                    end=words[k].end_us; texts.append(words[k].text); k+=1
                if end-start>=min_us: out.append((start,end,''.join(texts))); j=k
                else: omitted.append(s.segment_id); break
            i+=1; continue
        # Merge short adjacent segments while keeping a bounded gap and <= max.
        start=s.start_us; end=s.end_us; texts=[s.text]; j=i+1
        while end-start<min_us and j<len(segs) and segs[j].start_us-end<=1_000_000 and segs[j].end_us-start<=max_us:
            end=segs[j].end_us; texts.append(segs[j].text); j+=1
        if min_us<=end-start<=max_us: out.append((start,end,' '.join(texts))); i=j
        else: omitted.append(s.segment_id); i+=1
    return out,omitted


def prepare_dataset_from_transcript(canonical_wav:str|Path,transcript:TranscriptManifest,output_dir:str|Path,*,style_id:str,emotion_id:str,quality_pass:bool,owner_approved:bool,accept_transcripts:bool,target:RecordingCoverageTarget)->dict[str,Any]:
    src=Path(canonical_wav); root=Path(output_dir); segroot=root/'segments'; txtroot=root/'transcripts'; segroot.mkdir(parents=True,exist_ok=True); txtroot.mkdir(parents=True,exist_ok=True)
    chunks,omitted=_split_transcript(transcript); coverage_segments=[]; refs=[]; rows=[]
    for idx,(start_us,end_us,text) in enumerate(chunks,1):
        a=(start_us*48_000)//1_000_000; b=math.ceil(end_us*48_000/1_000_000); sid=f'voice-seg-{idx:06d}'; wavp=segroot/f'{sid}.wav'; txtp=txtroot/f'{sid}.txt'
        with new_canonical_writer(wavp) as w: copy_pcm24_range(src,w,a,b)
        txtp.write_text(text,encoding='utf-8'); sha=_sha(wavp); n=read_pcm_wav_info(wavp,require_canonical=True).sample_count
        cs=RecordingCoverageSegment(sid,sha,n,style_id,emotion_id,quality_pass,owner_approved,accept_transcripts); coverage_segments.append(cs)
        if quality_pass and owner_approved and accept_transcripts and 3*48_000<=n<=15*48_000:
            refs.append(VoiceReferenceCandidate(sid,wavp,txtp,sha,n,style_id,emotion_id,True,True,True))
        rows.append({'segment_id':sid,'wav_path':str(wavp),'transcript_path':str(txtp),'content_sha256':sha,'duration_samples':n,'style_id':style_id,'emotion_id':emotion_id,'quality_pass':quality_pass,'owner_approved':owner_approved,'transcript_verified':accept_transcripts})
    cov=compute_recording_coverage(coverage_segments,target); ref_manifest=build_reference_manifest(refs)
    ref_path=root/'reference-manifest.json'; AtomicJsonWriter.write(ref_path,ref_manifest)
    manifest={'manifest_version':'1.0.0','source_sha256':_sha(src),'segments':rows,'omitted_transcript_segment_ids':omitted,'coverage':cov.to_dict(),'reference_manifest_path':str(ref_path)}
    AtomicJsonWriter.write(root/'dataset-manifest.json',manifest); return manifest


def merge_dataset_workspaces(batch_manifests:Sequence[str|Path],output_dir:str|Path,*,target:RecordingCoverageTarget)->dict[str,Any]:
    segments=[]; ref_candidates=[]
    for path in batch_manifests:
        data=_json(Path(path))
        for x in data.get('segments',[]):
            seg=RecordingCoverageSegment(x['segment_id'],x['content_sha256'],int(x['duration_samples']),x['style_id'],x['emotion_id'],bool(x['quality_pass']),bool(x['owner_approved']),bool(x.get('transcript_verified',False))); segments.append(seg)
            if seg.quality_pass and seg.owner_approved and seg.transcript_verified and 3*48_000<=seg.duration_samples<=15*48_000:
                ref_candidates.append(VoiceReferenceCandidate(x['segment_id'],Path(x['wav_path']),Path(x['transcript_path']),x['content_sha256'],seg.duration_samples,seg.style_id,seg.emotion_id,True,True,True))
    # Reference manifest is also de-duplicated by content.
    dedup={}
    for x in ref_candidates: dedup.setdefault(x.content_sha256,x)
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=True); ref=build_reference_manifest(dedup.values()); refp=root/'master-reference-manifest.json'; AtomicJsonWriter.write(refp,ref)
    cov=compute_recording_coverage(segments,target); body={'workspace_version':'1.0.0','batch_manifest_count':len(batch_manifests),'coverage':cov.to_dict(),'master_reference_manifest_path':str(refp),'unique_reference_count':len(dedup)}; AtomicJsonWriter.write(root/'workspace.json',body); return body


def _target_from_json(overall:float,style_targets:str|None,emotion_targets:str|None)->RecordingCoverageTarget:
    def parse(v): return {} if not v else {str(k):float(x) for k,x in json.loads(v).items()}
    return RecordingCoverageTarget.from_seconds(overall,style_target_seconds=parse(style_targets),emotion_target_seconds=parse(emotion_targets))


def prepare_long_recording(*,input_path:str|Path,output_dir:str|Path,style_id:str,emotion_id:str,overall_target_seconds:float,style_target_seconds:str|None=None,emotion_target_seconds:str|None=None,channel_index:int|None=None,transcript_path:str|Path|None=None,model:str='small',device:str='auto',compute_type:str='int8',approve_derived_segments:bool=False,accept_asr_transcripts:bool=False,resume:bool=True)->dict[str,Any]:
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=True); canonical=root/'recording_canonical.wav'; can_report=canonicalize_obs_recording(input_path,canonical,report_path=root/'canonical-report.json',channel_index=channel_index,resume=resume)
    metrics=analyze_canonical_recording(canonical); AtomicJsonWriter.write(root/'quality-metrics.json',metrics)
    if transcript_path:
        transcript=load_transcript_manifest(transcript_path); transcript_file=Path(transcript_path)
    else:
        provider=FasterWhisperProvider(FasterWhisperConfig(model=model,device=device,compute_type=compute_type,vad_filter=True,allow_model_download=False))
        publication=ResumableTranscriptionService.run(canonical,root/'asr',provider=provider,config=ChunkedTranscriptionConfig(chunk_seconds=900,overlap_seconds=2,audio_sample_rate=16_000),language='ja',include_word_timestamps=True,resume=resume)
        transcript=publication.transcript; transcript_file=publication.transcript_path
    cont=create_speech_continuous_wav(canonical,transcript,root/'speech-continuous'/'speech_continuous.wav',report_path=root/'speech-continuous'/'speech_continuous_report.json')
    target=_target_from_json(overall_target_seconds,style_target_seconds,emotion_target_seconds)
    dataset=prepare_dataset_from_transcript(canonical,transcript,root/'dataset',style_id=style_id,emotion_id=emotion_id,quality_pass=True,owner_approved=approve_derived_segments,accept_transcripts=accept_asr_transcripts,target=target)
    report={'pipeline_version':'1.0.0','canonical':can_report,'quality_metrics':metrics,'transcript_path':str(transcript_file),'speech_continuous':cont,'dataset_manifest_path':str(root/'dataset'/'dataset-manifest.json')}; AtomicJsonWriter.write(root/'prepare-report.json',report); return report


def main(argv:Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('canonicalize'); c.add_argument('--input',required=True); c.add_argument('--output',required=True); c.add_argument('--report'); c.add_argument('--channel-index',type=int)
    r=sub.add_parser('preflight'); r.add_argument('--obs-current',action='store_true'); r.add_argument('--sample-rate-hz',type=int,required=True); r.add_argument('--gain-ready',action='store_true'); r.add_argument('--meter-peak-dbfs',type=float); r.add_argument('--target-floor-dbfs',type=float,default=-18.0); r.add_argument('--target-ceiling-dbfs',type=float,default=-6.0); r.add_argument('--quality-state',choices=('PASS','FAIL','UNKNOWN'),required=True); r.add_argument('--clip-sample-count',type=int,default=0); r.add_argument('--noise-floor-dbfs',type=float); r.add_argument('--snr-db',type=float); r.add_argument('--output')
    q=sub.add_parser('prepare'); q.add_argument('--input',required=True); q.add_argument('--output-dir',required=True); q.add_argument('--style-id',default='NORMAL'); q.add_argument('--emotion-id',default='NORMAL'); q.add_argument('--overall-target-seconds',type=float,default=7200); q.add_argument('--style-target-seconds'); q.add_argument('--emotion-target-seconds'); q.add_argument('--channel-index',type=int); q.add_argument('--transcript'); q.add_argument('--model',default='small'); q.add_argument('--device',default='auto'); q.add_argument('--compute-type',default='int8'); q.add_argument('--approve-derived-segments',action='store_true'); q.add_argument('--accept-asr-transcripts',action='store_true'); q.add_argument('--no-resume',action='store_true')
    w=sub.add_parser('workspace'); w.add_argument('--batch-manifest',action='append',required=True); w.add_argument('--output-dir',required=True); w.add_argument('--overall-target-seconds',type=float,default=7200); w.add_argument('--style-target-seconds'); w.add_argument('--emotion-target-seconds')
    a=p.parse_args(argv)
    if a.cmd=='canonicalize': canonicalize_obs_recording(a.input,a.output,report_path=a.report,channel_index=a.channel_index); return 0
    if a.cmd=='preflight':
        report=recording_start_preflight(obs_current=a.obs_current,sample_rate_hz=a.sample_rate_hz,gain_ready=a.gain_ready,meter_peak_dbfs=a.meter_peak_dbfs,target_floor_dbfs=a.target_floor_dbfs,target_ceiling_dbfs=a.target_ceiling_dbfs,quality_state=a.quality_state,clip_sample_count=a.clip_sample_count,noise_floor_dbfs=a.noise_floor_dbfs,snr_db=a.snr_db)
        payload=json.dumps(report,ensure_ascii=False,indent=2)
        if a.output: AtomicJsonWriter.write(Path(a.output),report)
        else: print(payload)
        return 0 if report['state']=='READY' else 2
    if a.cmd=='prepare': prepare_long_recording(input_path=a.input,output_dir=a.output_dir,style_id=a.style_id,emotion_id=a.emotion_id,overall_target_seconds=a.overall_target_seconds,style_target_seconds=a.style_target_seconds,emotion_target_seconds=a.emotion_target_seconds,channel_index=a.channel_index,transcript_path=a.transcript,model=a.model,device=a.device,compute_type=a.compute_type,approve_derived_segments=a.approve_derived_segments,accept_asr_transcripts=a.accept_asr_transcripts,resume=not a.no_resume); return 0
    target=_target_from_json(a.overall_target_seconds,a.style_target_seconds,a.emotion_target_seconds); merge_dataset_workspaces(a.batch_manifest,a.output_dir,target=target); return 0

if __name__=='__main__': raise SystemExit(main())
