from pathlib import Path
import json, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/'tools/windows/run-owner-voice-recording-preflight.ps1'
PREP=ROOT/'tools/windows/run-owner-voice-recording-prepare.ps1'


def test_windows_wrappers_are_non_mutating_launchers():
    pre=PRE.read_text(encoding='utf-8')
    prep=PREP.read_text(encoding='utf-8')
    for text in (pre,prep):
        assert 'Start-Process' not in text
        assert 'obs64.exe' not in text.lower()
        assert 'Remove-Item' not in text
    assert 'owner_voice_recording_pipeline", "preflight"' in pre
    assert 'owner_voice_recording_pipeline", "prepare"' in prep
    assert '--overall-target-seconds' in prep


def test_preflight_cli_exit_codes_and_json(tmp_path):
    env=os.environ.copy(); env['PYTHONPATH']=str(ROOT/'src')
    out=tmp_path/'preflight.json'
    ready=[sys.executable,'-m','ai_video_production.owner_voice_recording_pipeline','preflight','--obs-current','--sample-rate-hz','48000','--gain-ready','--meter-peak-dbfs','-12','--quality-state','PASS','--clip-sample-count','0','--output',str(out)]
    p=subprocess.run(ready,cwd=ROOT,env=env,check=False,capture_output=True,text=True)
    assert p.returncode==0
    body=json.loads(out.read_text(encoding='utf-8'))
    assert body['state']=='READY' and body['recording_start_authorized'] is True
    blocked=[sys.executable,'-m','ai_video_production.owner_voice_recording_pipeline','preflight','--sample-rate-hz','44100','--quality-state','FAIL','--clip-sample-count','1']
    p=subprocess.run(blocked,cwd=ROOT,env=env,check=False,capture_output=True,text=True)
    assert p.returncode==2
    body=json.loads(p.stdout)
    assert body['state']=='BLOCKED' and body['recording_start_authorized'] is False
