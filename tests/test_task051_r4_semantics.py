from ai_video_production.dbd_notification_semantics import *
from ai_video_production.dbd_training_workspace import OcrVocabularySample
def test_store(tmp_path):
 s=NotificationSemanticStore(tmp_path/"s.json");r=NotificationSemanticRecord("CHASE","追跡","チェイス開始","CHASE_START");s.upsert(r);assert s.find("CHASE","追跡")==r;assert s.delete("CHASE","追跡")
def test_label_hides_code():
 c=notification_signal_choices([OcrVocabularySample("CHASE","追跡")]);assert c[0][0]=="チェイス関連通知" and "CHASE" not in c[0][0]
