"""Pure, body-free TASK-073 ReceiptRefV2 composition."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256

SCHEMA_VERSION = "TASK073_OWNER_VOICE_LOCAL_WAV_COMPOSITION_V4"
RECORD_TYPE = "OwnerVoiceLocalWavCompositionV4"
TASK_OWNER = "TASK-073"
DESIGN_BUNDLE_SHA256 = "sha256:a56472b0d99f58a9170838e113efd0f75565e42490e477e2640a07b86c4ac71a"
RECEIPT_SLOTS = ("installed_session", "quick_clone", "selection", "reference", "call_profile", "compute_admission", "human_plan", "operation_ticket", "durable_job", "inference", "wav", "qa", "playback", "listening_join")
RECEIPT_ALLOWLIST = {"installed_session":("TASK-036","INSTALLED_STARTUP_CONTEXT_V1",1),"quick_clone":("TASK-046","QUICK_CLONE_FLOW_READBACK_V2",2),"selection":("TASK-074","VOICE_PROFILE_ROUTE_SELECTION_READBACK_V1",1),"reference":("TASK-074","OWNER_VOICE_PRIVATE_REFERENCE_READBACK_V1",1),"call_profile":("TASK-014","LOCAL_PRIMARY_NARRATION_CALL_PROFILE_V2",2),"compute_admission":("TASK-066","AUDIO_VOICE_COMPUTE_ADMISSION_V1",1),"human_plan":("TASK-071","OWNER_VOICE_LOCAL_INFERENCE_PLAN_V1",1),"operation_ticket":("TASK-072","OWNER_VOICE_LOCAL_INFERENCE_TICKET_V3",3),"durable_job":("TASK-076","DURABLE_PRODUCT_JOB_READBACK_V1",1),"inference":("TASK-075","TASK075_LOCAL_VOICE_EXECUTION_RESULT_V1",1),"wav":("TASK-014","TASK014_LOCAL_PRIMARY_NARRATION_POST_RECEIPT_V1",1),"qa":("TASK-048","OWNER_VOICE_TECHNICAL_QA_RECEIPT_V1",1),"playback":("TASK-075","VOICE_PLAYBACK_OBSERVATION_V1",1),"listening_join":("TASK-075","VOICE_QA_LISTENING_BINDING_V1",1)}
DERIVED_STATES = frozenset({"SETUP_REQUIRED","REFERENCE_REQUIRED","MODEL_SELECTION_REQUIRED","READY_TO_RENDER","CONFIRMATION_REQUIRED","QUEUED","RUNNING","RECOVERY_REQUIRED","UNKNOWN","QA_REQUIRED","LISTENING_REQUIRED","WAV_RETEST_REQUIRED","WAV_ACCEPTED","WAV_REJECTED","BLOCKED"})
REASON_CODES = frozenset({"MISSING_REQUIRED_RECEIPT","UNKNOWN_RECEIPT_TYPE","UNKNOWN_RECEIPT_VERSION","STALE_RECEIPT","EXPIRED_RECEIPT","PROJECT_MISMATCH","INSTALL_MISMATCH","OPERATION_MISMATCH","QUICK_CLONE_HEAD_MISMATCH","CANDIDATE_MISMATCH","MULTIPLE_CURRENT_RECEIPTS","PRODUCER_BLOCKED","PRODUCER_UNKNOWN","FIXTURE_ONLY","FIXTURE_TAINT_MISMATCH","PRIVACY_BOUNDARY_VIOLATION"})
_TOP = ("schema","record_type","task_owner","composition_id","composition_revision","parent_composition_sha256","observed_at","project_id","project_manifest_revision","project_manifest_sha256","installed_session_sha256","operation_plan_sha256","design_bundle_sha256","receipts","derived_state","reason_codes","fixture_lineage","composition_sha256")
_RFIELDS = ("owner_task","receipt_type","schema_version","opaque_ref","receipt_sha256","producer_build_sha256","producer_state","candidate_id","candidate_sha256","project_id","project_manifest_sha256","installed_session_sha256","operation_plan_sha256","quick_clone_flow_sha256","revision","head_sha256","observed_at","expires_at","current","fixture_only","authority_created","production_eligible")
_LFIELDS = ("fixture_only","authority_created","production_eligible","fixture_set_sha256","producer_fixture_count")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$")
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")
_STATES = {"installed_session":{"READY","BLOCKED","UNKNOWN"},"quick_clone":{"ACTIVE","RETEST_REQUIRED","ACCEPTED","REJECTED","BLOCKED","UNKNOWN"},"selection":{"SELECTED","BLOCKED","UNKNOWN"},"reference":{"PREPARED_VERIFIED","BLOCKED","UNKNOWN"},"call_profile":{"READY_FOR_TASK075_DISPATCH","BLOCKED","UNKNOWN"},"compute_admission":{"ADMITTED","BLOCKED","UNKNOWN"},"human_plan":{"CONFIRMATION_REQUIRED","CONFIRMED","BLOCKED","UNKNOWN"},"operation_ticket":{"ISSUED","CONSUMED","BURNED","BLOCKED","UNKNOWN"},"durable_job":{"QUEUED","DISPATCHING","RUNNING","RECOVERY_REQUIRED","SUCCEEDED","FAILED_KNOWN","UNKNOWN"},"inference":{"SUCCESS","FAILED_KNOWN","UNKNOWN"},"wav":{"PUBLISHED_READBACK_VERIFIED","FAILED_KNOWN","UNKNOWN"},"qa":{"PASS","FAIL","UNKNOWN"},"playback":{"READY","PLAYING","COMPLETED","STOPPED","FAILED_KNOWN","UNKNOWN"},"listening_join":{"ACCEPTED","REJECTED","RETEST_REQUIRED","BLOCKED","UNKNOWN"}}
# project, manifest, installed session, operation plan, quick-clone head, expiry
_COORDS = {"installed_session":(1,1,1,0,0,0),"quick_clone":(1,1,1,0,1,0),"selection":(1,1,1,0,1,0),"reference":(1,1,1,0,1,1),"call_profile":(1,1,1,1,1,1),"compute_admission":(1,1,1,1,1,1),"human_plan":(1,1,1,1,1,1),"operation_ticket":(1,1,1,1,1,1),"durable_job":(1,1,1,1,1,1),"inference":(1,1,1,1,1,0),"wav":(1,1,1,1,1,0),"qa":(1,1,1,1,1,0),"playback":(1,1,1,1,1,0),"listening_join":(1,1,1,1,1,0)}
_LATE = frozenset({"quick_clone","wav","qa","playback","listening_join"})

def _exact(v: Any, fields: Any, n: str) -> None:
    if not isinstance(v, Mapping) or tuple(v) != tuple(fields): raise ValueError(f"{n} fields are incomplete, unknown, or reordered")
def _id(v: Any, n: str) -> str:
    if not isinstance(v,str) or len(v)>200 or not _ID.fullmatch(v): raise ValueError(f"{n} is invalid or exposes a location")
    return v
def _digest(v: Any, n: str, nullable: bool=False) -> str|None:
    if v is None and nullable:return None
    if not isinstance(v,str):raise ValueError(f"{n} is invalid")
    return validate_sha256(v,field_name=n)
def _positive(v: Any,n: str)->int:
    if isinstance(v,bool) or not isinstance(v,int) or not 1<=v<=2147483647:raise ValueError(f"{n} must be a positive bounded integer")
    return v
def _time(v: Any,n: str)->datetime:
    if not isinstance(v,str) or not _TIME.fullmatch(v):raise ValueError(f"{n} must be canonical RFC3339 UTC")
    try:return datetime.fromisoformat(v[:-1]+"+00:00")
    except ValueError as e:raise ValueError(f"{n} must be canonical RFC3339 UTC") from e

def _receipt(slot: str,v: Mapping[str,Any])->dict[str,Any]:
    _exact(v,_RFIELDS,f"receipts.{slot}")
    if tuple(v[k] for k in ("owner_task","receipt_type","schema_version")) != RECEIPT_ALLOWLIST[slot]:raise ValueError(f"receipts.{slot} is outside the allowlist")
    if v["producer_state"] not in _STATES[slot]:raise ValueError(f"receipts.{slot}.producer_state is outside the slot state vocabulary")
    _id(v["opaque_ref"],"opaque_ref");_id(v["project_id"],"project_id");_positive(v["revision"],"revision");_time(v["observed_at"],"observed_at")
    for k in ("receipt_sha256","producer_build_sha256","project_manifest_sha256","head_sha256"): _digest(v[k],k)
    for k in ("installed_session_sha256","operation_plan_sha256","quick_clone_flow_sha256","candidate_sha256"): _digest(v[k],k,True)
    p=(v["candidate_id"],v["candidate_sha256"])
    if (p[0] is None)!=(p[1] is None):raise ValueError("candidate pair must be both null or both non-null")
    if p[0] is not None:_id(p[0],"candidate_id")
    if slot not in _LATE and p[0] is not None:raise ValueError(f"receipts.{slot} candidate pair must be null")
    if slot in _LATE-{"quick_clone"} and p[0] is None:raise ValueError(f"receipts.{slot} candidate pair is required")
    if slot=="quick_clone" and v["producer_state"]=="ACTIVE" and p[0] is not None:raise ValueError("active quick clone candidate pair must be null")
    if slot=="quick_clone" and v["producer_state"] in {"RETEST_REQUIRED","ACCEPTED","REJECTED"} and p[0] is None:raise ValueError("terminal quick clone candidate pair is required")
    exp=_COORDS[slot][5]
    if exp != (v["expires_at"] is not None):raise ValueError(f"receipts.{slot}.expires_at has invalid applicability")
    if exp and _time(v["expires_at"],"expires_at")<=_time(v["observed_at"],"observed_at"):raise ValueError("expires_at must follow observed_at")
    for k in ("current","fixture_only","authority_created","production_eligible"):
        if not isinstance(v[k],bool):raise ValueError(f"receipts.{slot}.{k} must be boolean")
    if v["fixture_only"] and (v["authority_created"] or v["production_eligible"]):raise ValueError("fixture cannot claim authority or production eligibility")
    return copy.deepcopy(dict(v))

def _lineage(r:Mapping[str,Mapping[str,Any]|None], state: str, reasons: Sequence[str])->dict[str,Any]:
    t=[[s,x["receipt_sha256"]] for s,x in r.items() if x is not None and (x["fixture_only"] or not x["authority_created"] or not x["production_eligible"])]
    eligible = state == "WAV_ACCEPTED" and not reasons and all(x and x["current"] and not x["fixture_only"] and x["authority_created"] and x["production_eligible"] for x in r.values())
    return {"fixture_only":any(x["fixture_only"] for x in r.values() if x),"authority_created":False,"production_eligible":eligible,"fixture_set_sha256":sha256_bytes(canonical_json_bytes(t)),"producer_fixture_count":len(t)}

def _prefix_invalid(r: Mapping[str, Mapping[str, Any] | None]) -> bool:
    groups = (
        (r["installed_session"] is not None,),
        (r["quick_clone"] is not None,),
        (r["reference"] is not None,),
        (r["selection"] is not None,),
        (r["call_profile"] is not None, r["compute_admission"] is not None),
        (r["human_plan"] is not None,),
        (r["operation_ticket"] is not None,),
        (r["durable_job"] is not None,),
        (r["inference"] is not None,),
        (r["wav"] is not None,),
        (r["qa"] is not None,),
        (r["playback"] is not None,),
        (r["listening_join"] is not None,),
    )
    if groups[4][0] != groups[4][1]:
        return True
    present = tuple(all(group) for group in groups)
    seen_gap = False
    for item in present:
        if not item:
            seen_gap = True
        elif seen_gap:
            return True
    return False

def _automatic(v:Mapping[str,Any],r:Mapping[str,Mapping[str,Any]|None])->set[str]:
    out:set[str]=set();now=_time(v["observed_at"],"observed_at");quick=r["quick_clone"];qh=quick["head_sha256"] if quick else None;pairs=set()
    g4_operations = {
        r[slot]["operation_plan_sha256"]
        for slot in ("call_profile", "compute_admission")
        if r[slot] is not None
    }
    if v["operation_plan_sha256"] is None and len(g4_operations) > 1:
        out.add("OPERATION_MISMATCH")
    g4_operation = next(iter(g4_operations), None)
    for s,x in r.items():
        if x is None:continue
        if not x["current"]:out.add("STALE_RECEIPT")
        if x["producer_state"]=="BLOCKED":out.add("PRODUCER_BLOCKED")
        if x["producer_state"] in {"BURNED", "FAILED_KNOWN", "FAIL"}:out.add("PRODUCER_BLOCKED")
        if _COORDS[s][5] and _time(x["expires_at"],"expires_at")<=now:out.add("EXPIRED_RECEIPT")
        expected_operation = g4_operation if v["operation_plan_sha256"] is None and s in {"call_profile", "compute_admission"} else v["operation_plan_sha256"]
        expected=(v["project_id"],v["project_manifest_sha256"],v["installed_session_sha256"],expected_operation,qh)
        for field,required,want,code in zip(("project_id","project_manifest_sha256","installed_session_sha256","operation_plan_sha256","quick_clone_flow_sha256"),_COORDS[s][:5],expected,("PROJECT_MISMATCH","PROJECT_MISMATCH","INSTALL_MISMATCH","OPERATION_MISMATCH","QUICK_CLONE_HEAD_MISMATCH")):
            if (required and x[field]!=want) or (not required and x[field] is not None):out.add(code)
        if s in _LATE and x["candidate_id"] is not None:pairs.add((x["candidate_id"],x["candidate_sha256"]))
    if quick is not None and r["listening_join"] is not None:
        qstate, lstate = quick["producer_state"], r["listening_join"]["producer_state"]
        if "RETEST_REQUIRED" not in {qstate, lstate}:
            if qstate in {"ACCEPTED", "REJECTED"} and qstate != lstate: out.add("CANDIDATE_MISMATCH")
            if qstate not in {"ACCEPTED", "REJECTED"} and lstate in {"ACCEPTED", "REJECTED"}: out.add("CANDIDATE_MISMATCH")
    if quick is not None and quick["candidate_id"] is None and any(r[s] is not None for s in _LATE - {"quick_clone"}): out.add("CANDIDATE_MISMATCH")
    if len(pairs)>1:out.add("CANDIDATE_MISMATCH")
    if _prefix_invalid(r): out.add("MISSING_REQUIRED_RECEIPT")
    if r["operation_ticket"] is not None and r["operation_ticket"]["producer_state"] == "CONSUMED" and r["durable_job"] is None: out.add("MISSING_REQUIRED_RECEIPT")
    if r["durable_job"] is not None and r["durable_job"]["producer_state"] == "SUCCEEDED" and r["inference"] is None: out.add("MISSING_REQUIRED_RECEIPT")
    return out

def _derive(r: Mapping[str, Mapping[str, Any] | None], reasons: set[str]) -> str:
    if reasons: return "BLOCKED"
    quick = r["quick_clone"]
    listening = r["listening_join"]
    if quick is not None and listening is not None:
        quick_state = quick["producer_state"]
        listening_state = listening["producer_state"]
        if quick_state == listening_state == "ACCEPTED": return "WAV_ACCEPTED"
        if quick_state == listening_state == "REJECTED": return "WAV_REJECTED"
        if "RETEST_REQUIRED" in {quick_state, listening_state}: return "WAV_RETEST_REQUIRED"
    if any(x is not None and x["producer_state"] == "UNKNOWN" for x in r.values()): return "UNKNOWN"
    job = r["durable_job"]
    if job is not None and job["producer_state"] == "RECOVERY_REQUIRED": return "RECOVERY_REQUIRED"
    if r["qa"] is not None and r["qa"]["producer_state"] == "PASS" and listening is None: return "LISTENING_REQUIRED"
    if r["wav"] is not None and r["qa"] is None: return "QA_REQUIRED"
    if r["inference"] is not None and r["inference"]["producer_state"] == "SUCCESS" and r["wav"] is None: return "RUNNING"
    if job is not None and job["producer_state"] in {"DISPATCHING", "RUNNING"}: return "RUNNING"
    if (r["operation_ticket"] is not None and job is None) or (job is not None and job["producer_state"] == "QUEUED"): return "QUEUED"
    if r["call_profile"] is not None and r["compute_admission"] is not None and r["operation_ticket"] is None: return "CONFIRMATION_REQUIRED"
    if r["installed_session"] is not None and quick is not None and r["reference"] is not None and r["selection"] is not None: return "READY_TO_RENDER"
    if r["installed_session"] is not None and quick is not None and r["reference"] is not None: return "MODEL_SELECTION_REQUIRED"
    if r["installed_session"] is not None: return "REFERENCE_REQUIRED"
    return "SETUP_REQUIRED"

def _normalize(v:Mapping[str,Any],verify:bool,observation_reasons:Sequence[str]=())->dict[str,Any]:
    _exact(v,_TOP,"composition")
    if tuple(v[k] for k in ("schema","record_type","task_owner"))!=(SCHEMA_VERSION,RECORD_TYPE,TASK_OWNER):raise ValueError("composition identity is invalid")
    _id(v["composition_id"],"composition_id");rev=_positive(v["composition_revision"],"composition_revision");parent=_digest(v["parent_composition_sha256"],"parent_composition_sha256",True)
    if (rev==1)!=(parent is None):raise ValueError("parent_composition_sha256 must be null only for revision 1")
    _time(v["observed_at"],"observed_at");_id(v["project_id"],"project_id");_positive(v["project_manifest_revision"],"project_manifest_revision");_digest(v["project_manifest_sha256"],"project_manifest_sha256")
    for k in ("installed_session_sha256","operation_plan_sha256"): _digest(v[k],k,True)
    if v["design_bundle_sha256"]!=DESIGN_BUNDLE_SHA256:raise ValueError("design_bundle_sha256 is not the accepted D4-R4 bundle")
    if v["derived_state"] not in DERIVED_STATES:raise ValueError("derived_state is outside the closed state inventory")
    if not isinstance(v["receipts"],Mapping) or tuple(v["receipts"])!=RECEIPT_SLOTS:raise ValueError("receipts must use the exact fixed slot order")
    r={s:None if v["receipts"][s] is None else _receipt(s,v["receipts"][s]) for s in RECEIPT_SLOTS}
    if not isinstance(v["reason_codes"],list) or v["reason_codes"]!=sorted(set(v["reason_codes"])) or any(x not in REASON_CODES for x in v["reason_codes"]):raise ValueError("reason_codes must be sorted, unique, and closed")
    auto=_automatic(v,r)
    declared_reasons = set(v["reason_codes"])
    auto.update(observation_reasons)
    expected_state = _derive(r, auto)
    if expected_state in {"WAV_RETEST_REQUIRED","WAV_ACCEPTED","WAV_REJECTED"}:
        pairs = {(x["candidate_id"],x["candidate_sha256"]) for s,x in r.items() if s in _LATE and x is not None}
        if len(pairs) != 1: auto.add("CANDIDATE_MISMATCH"); expected_state = "BLOCKED"
    if v["derived_state"] != expected_state: raise ValueError("derived_state is derived from receipts and must fail closed")
    if expected_state != "BLOCKED":
        if (expected_state == "SETUP_REQUIRED") != (v["installed_session_sha256"] is None): raise ValueError("installed_session_sha256 has invalid state applicability")
        early = {"SETUP_REQUIRED", "REFERENCE_REQUIRED", "MODEL_SELECTION_REQUIRED", "READY_TO_RENDER"}
        if (expected_state in early) != (v["operation_plan_sha256"] is None): raise ValueError("operation_plan_sha256 has invalid state applicability")
    if declared_reasons != auto:raise ValueError("reason_codes must exactly match automatic receipt findings")
    if auto and v["derived_state"]!="BLOCKED":raise ValueError("invalid receipt topology/currentness must fail closed as BLOCKED")
    if v["derived_state"]=="BLOCKED" and not v["reason_codes"]:raise ValueError("BLOCKED requires at least one reason code")
    if v["derived_state"] not in {"BLOCKED","UNKNOWN","RECOVERY_REQUIRED"} and v["reason_codes"]:raise ValueError("non-failure derived state cannot carry reason codes")
    _exact(v["fixture_lineage"],_LFIELDS,"fixture_lineage");lineage=_lineage(r, v["derived_state"], v["reason_codes"])
    if dict(v["fixture_lineage"])!=lineage:raise ValueError("fixture_lineage does not match receipt taint")
    _digest(v["composition_sha256"],"composition_sha256");out=copy.deepcopy(dict(v));out["receipts"]=r;out["fixture_lineage"]=lineage;want=sha256_bytes(canonical_json_bytes({k:out[k] for k in _TOP if k!="composition_sha256"}))
    if verify and out["composition_sha256"]!=want:raise ValueError("composition_sha256 does not match canonical content")
    out["composition_sha256"]=want;return out

@dataclass(frozen=True)
class OwnerVoiceLocalWavCompositionV4:
    _value:Mapping[str,Any]
    def __post_init__(self) -> None:
        object.__setattr__(self, "_value", _normalize(self._value, True))
    @classmethod
    def _create_validated(cls, *, observation_reasons: Sequence[str] = (), composition_id:str,composition_revision:int,parent_composition_sha256:str|None,observed_at:str,project_id:str,project_manifest_revision:int,project_manifest_sha256:str,installed_session_sha256:str|None,operation_plan_sha256:str|None,receipts:Mapping[str,Mapping[str,Any]|None],derived_state:str,reason_codes:Sequence[str]=())->"OwnerVoiceLocalWavCompositionV4":
        if tuple(receipts)!=RECEIPT_SLOTS:raise ValueError("receipts must contain exactly the 14 fixed slots in order")
        r={s:None if receipts[s] is None else _receipt(s,receipts[s]) for s in RECEIPT_SLOTS}
        body={"schema":SCHEMA_VERSION,"record_type":RECORD_TYPE,"task_owner":TASK_OWNER,"composition_id":composition_id,"composition_revision":composition_revision,"parent_composition_sha256":parent_composition_sha256,"observed_at":observed_at,"project_id":project_id,"project_manifest_revision":project_manifest_revision,"project_manifest_sha256":project_manifest_sha256,"installed_session_sha256":installed_session_sha256,"operation_plan_sha256":operation_plan_sha256,"design_bundle_sha256":DESIGN_BUNDLE_SHA256,"receipts":r,"derived_state":derived_state,"reason_codes":list(reason_codes),"fixture_lineage":_lineage(r, derived_state, reason_codes),"composition_sha256":"sha256:"+"0"*64}
        instance = object.__new__(cls)
        object.__setattr__(instance, "_value", _normalize(body,False,observation_reasons))
        return instance
    @classmethod
    def create(cls,*,composition_id:str,composition_revision:int,parent_composition_sha256:str|None,observed_at:str,project_id:str,project_manifest_revision:int,project_manifest_sha256:str,installed_session_sha256:str|None,operation_plan_sha256:str|None,receipts:Mapping[str,Mapping[str,Any]|None],derived_state:str,reason_codes:Sequence[str]=())->"OwnerVoiceLocalWavCompositionV4":
        return cls._create_validated(composition_id=composition_id,composition_revision=composition_revision,parent_composition_sha256=parent_composition_sha256,observed_at=observed_at,project_id=project_id,project_manifest_revision=project_manifest_revision,project_manifest_sha256=project_manifest_sha256,installed_session_sha256=installed_session_sha256,operation_plan_sha256=operation_plan_sha256,receipts=receipts,derived_state=derived_state,reason_codes=reason_codes)
    @classmethod
    def create_from_observations(cls,*,observations:Mapping[str,Sequence[Mapping[str,Any]]],**kw:Any)->"OwnerVoiceLocalWavCompositionV4":
        if tuple(observations)!=RECEIPT_SLOTS:raise ValueError("observations must contain exactly 14 slots in order")
        if kw.pop("reason_codes", ()):
            raise ValueError("reason_codes are derived from observations")
        r={};reasons=set()
        for s in RECEIPT_SLOTS:
            entries=observations[s]
            if isinstance(entries,(str,bytes)) or not isinstance(entries,Sequence):raise ValueError(f"observations.{s} must be a sequence")
            if any(not isinstance(x, Mapping) for x in entries):raise ValueError(f"observations.{s} entries must be mappings")
            current=[_receipt(s,x) for x in entries if x.get("current")];unique={x["receipt_sha256"]:x for x in current}
            if len(unique)>1:r[s]=None;reasons.add("MULTIPLE_CURRENT_RECEIPTS")
            elif current:
                if any(x!=next(iter(unique.values())) for x in current):raise ValueError(f"observations.{s} reuses one receipt hash for different content")
                r[s]=next(iter(unique.values()))
            else:
                r[s]=None
                if entries: reasons.add("STALE_RECEIPT")
        automatic = _automatic(kw, r)
        reasons.update(automatic)
        if reasons:kw["derived_state"]="BLOCKED"
        return cls._create_validated(receipts=r,reason_codes=sorted(reasons),observation_reasons=sorted(reasons),**kw)
    @classmethod
    def from_dict(cls,value:Mapping[str,Any])->"OwnerVoiceLocalWavCompositionV4":
        observation_reasons = tuple(code for code in value.get("reason_codes", ()) if code in {"MULTIPLE_CURRENT_RECEIPTS", "STALE_RECEIPT"})
        instance = object.__new__(cls)
        object.__setattr__(instance, "_value", _normalize(value,True,observation_reasons))
        return instance
    def to_dict(self)->dict[str,Any]:return copy.deepcopy(dict(self._value))

__all__=["DESIGN_BUNDLE_SHA256","DERIVED_STATES","OwnerVoiceLocalWavCompositionV4","REASON_CODES","RECEIPT_ALLOWLIST","RECEIPT_SLOTS","RECORD_TYPE","SCHEMA_VERSION","TASK_OWNER"]
