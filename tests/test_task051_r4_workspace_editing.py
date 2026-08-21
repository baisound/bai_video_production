from ai_video_production.dbd_training_workspace import *
def test_visual_replace_delete(tmp_path):
 p1=tmp_path/"a.pgm";p2=tmp_path/"b.pgm";p1.write_bytes(b"P5\n1 1\n255\n\x00");p2.write_bytes(b"P5\n1 1\n255\n\x01")
 m=VisualTrainingManifest(tmp_path/"v.csv");a=VisualTrainingSample(VisualTrainingDomain.PERK_ICON,"a",str(p1));b=VisualTrainingSample(VisualTrainingDomain.PERK_ICON,"b",str(p2));assert m.append(a);assert m.replace(a,b);assert m.list()==(b,);assert m.delete(b)
def test_ocr_replace_delete(tmp_path):
 m=OcrVocabularyManifest(tmp_path/"o.csv");a=OcrVocabularySample("CHASE","追跡");b=OcrVocabularySample("CHASE","チェイス");assert m.append(a);assert m.replace(a,b);assert m.list()==(b,);assert m.delete(b)
