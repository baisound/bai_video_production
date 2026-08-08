import pytest
from ai_video_production import PluginDescriptor, ProfileSnapshot, merge_allowed_overrides

def test_profile_snapshot_is_checksum_bound_and_override_is_limited():
    merged=merge_allowed_overrides({"quality":{"crf":18}},{"quality":{"crf":20}})
    snap=ProfileSnapshot.create("youtube-long","1.0.0",merged)
    assert snap.checksum.startswith("sha256:") and snap.config["quality"]["crf"]==20
    with pytest.raises(ValueError): merge_allowed_overrides({}, {"rights_status":"OWNED"})

def test_plugin_cannot_claim_core_mutation():
    plugin=PluginDescriptor("dbd","1",("DETECT_HUD",),(),(),("ERR_PLUGIN",)); plugin.validate_boundary()
    with pytest.raises(ValueError):
        PluginDescriptor("bad","1",("MUTATE_JOB_STATE",),(),(),()).validate_boundary()


def test_profile_snapshot_config_cannot_mutate_canonical_value():
    snap=ProfileSnapshot.create("x","1",{"nested":{"value":1}})
    copy=snap.config
    copy["nested"]["value"]=999
    assert snap.config["nested"]["value"]==1
