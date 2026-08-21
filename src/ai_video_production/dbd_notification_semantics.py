from __future__ import annotations
from dataclasses import dataclass, asdict
import json, os, tempfile, threading
from pathlib import Path
from .canonical_game_event import GameEventType

@dataclass(frozen=True, slots=True)
class NotificationSemanticRecord:
    signal_id:str
    phrase:str
    meaning:str=""
    related_event_type:str=""
    source_ref:str="manual://owner"
    def __post_init__(self):
        if not self.signal_id.strip(): raise ValueError("通知の種類が空です")
        if not self.phrase.strip(): raise ValueError("画面表示文字が空です")
        if len(self.meaning)>4000: raise ValueError("通知の意味・説明が長すぎます")
        if self.related_event_type: GameEventType(self.related_event_type)

class NotificationSemanticStore:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.RLock()
        if not self.path.exists(): self._write(())
    @staticmethod
    def _key(x): return (x.signal_id.casefold(),x.phrase.casefold())
    def list(self):
        with self._lock:
            body=json.loads(self.path.read_text(encoding="utf-8"))
            return tuple(NotificationSemanticRecord(**x) for x in body.get("records",[]))
    def _write(self,rows):
        rows=tuple(sorted(rows,key=lambda x:(x.signal_id,x.phrase)))
        fd,raw=tempfile.mkstemp(prefix=f".{self.path.name}.",suffix=".tmp",dir=self.path.parent); os.close(fd); tmp=Path(raw)
        try:
            tmp.write_text(json.dumps({"schema_version":"1.0.0","records":[asdict(x) for x in rows]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            os.replace(tmp,self.path)
        finally:
            if tmp.exists(): tmp.unlink()
    def find(self,signal_id,phrase):
        key=(signal_id.casefold(),phrase.casefold())
        return next((x for x in self.list() if self._key(x)==key),None)
    def upsert(self,row):
        with self._lock:
            values=list(self.list()); key=self._key(row)
            for i,x in enumerate(values):
                if self._key(x)==key: values[i]=row; self._write(values); return
            values.append(row); self._write(values)
    def delete(self,signal_id,phrase):
        with self._lock:
            values=list(self.list()); key=(signal_id.casefold(),phrase.casefold())
            kept=[x for x in values if self._key(x)!=key]
            if len(kept)==len(values): return False
            self._write(kept); return True

KNOWN_SIGNAL_JA={
    "MATCH":"試合・全体通知",
    "CHASE":"チェイス関連通知",
    "INJURY":"負傷関連通知",
    "DOWN":"ダウン関連通知",
    "HOOK":"フック関連通知",
    "UNHOOK":"救助関連通知",
    "WINDOW":"窓枠関連通知",
    "PALLET":"板関連通知",
    "KILL":"処刑・死亡関連通知",
    "ESCAPE":"脱出関連通知",
    "SYSTEM":"その他・システム通知",
}

def notification_signal_label(signal_id):
    signal=str(signal_id or "").strip().upper()
    return KNOWN_SIGNAL_JA.get(signal, f"既存通知種類: {signal}" if signal else "通知種類未設定")

def notification_signal_choices(samples):
    grouped={}
    for x in samples:
        grouped.setdefault(x.signal_id.strip().upper(),[]).append(x.phrase)
    ordered=list(grouped)
    ordered.extend(signal for signal in KNOWN_SIGNAL_JA if signal not in grouped)
    out=[]
    for signal in ordered:
        label=KNOWN_SIGNAL_JA.get(signal)
        if not label:
            phrases=sorted({p.strip() for p in grouped.get(signal,()) if p.strip()})
            label=f"既存通知：{phrases[0]}" if phrases else f"既存通知種類: {signal}"
        out.append((label,signal))
    return tuple(out)
