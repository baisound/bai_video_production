import pytest
from ai_video_production.task090_owner_voice_q2_terminal import Q2TerminalRecord,parse_q2_terminal
H=lambda c:'sha256:'+c*64

def test_q2_terminal_roundtrip_is_body_free_and_deterministic():
    r=Q2TerminalRecord(H('a'),H('b'),H('c'),H('d'),H('e'),1)
    body=r.to_dict(); assert body['state']=='BOUND_VERIFIED'; assert body['audio_body_persisted'] is False; assert parse_q2_terminal(body)==r

def test_q2_terminal_tamper_rejected():
    body=Q2TerminalRecord(H('a'),H('b'),H('c'),H('d'),H('e'),1).to_dict(); body['revision']=2
    with pytest.raises(ValueError,match='terminal_sha256'): parse_q2_terminal(body)
