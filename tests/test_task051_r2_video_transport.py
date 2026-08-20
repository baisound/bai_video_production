from ai_video_production.dbd_video_transport import *
def test_ntsc_seconds_jump():
    m=metadata_from_ffprobe_payload({"streams":[{"avg_frame_rate":"30000/1001","nb_frames":"3000","duration":"100.1"}],"format":{"duration":"100.1"}})
    assert round(m.fps,3)==29.970
    x=VideoTransportModel(m,1000); assert x.step_seconds(1)==1030; assert x.step_seconds(-10)==730
def test_boundaries():
    m=VideoTransportModel(VideoTransportMetadata(30,1,10,300),0)
    assert m.step_frames(-1)==0; assert m.last()==299; assert m.step_frames(1)==299; assert m.first()==0
def test_states_stop_rewind_ff():
    m=VideoTransportModel(VideoTransportMetadata(60,1,5,300),0)
    m.play(); assert m.tick()==1
    m.rewind(); assert m.tick()==0 and m.state is VideoTransportState.STOPPED
    m.fast_forward(); assert m.tick()==4; m.stop(); assert m.tick()==4
def test_exact_button_order_and_icons():
    assert [x[1] for x in BUTTON_LAYOUT]==["最初へ","巻き戻し","停止","再生","早送り","最後へ","-10秒","-1秒","-1フレーム","+1フレーム","+1秒","+10秒"]
    assert len(ICON_PNG_BASE64)==12 and all(len(v)>100 for v in ICON_PNG_BASE64.values())
