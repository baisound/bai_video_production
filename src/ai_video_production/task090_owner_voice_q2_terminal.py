"""Pure durable Q2 terminal/currentness record for Owner Voice candidates.

This successor to TASK-089 consumes only body-free hashes.  It deliberately
creates no Asset, publication, private-media body, or provider side effect.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any
from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256

@dataclass(frozen=True, slots=True)
class Q2TerminalRecord:
    pair_handoff_sha256: str
    processed_asset_sha256: str
    training_copy_asset_sha256: str
    policy_revision_sha256: str
    producer_operation_sha256: str
    revision: int
    parent_terminal_sha256: str | None = None

    def __post_init__(self) -> None:
        for n in ("pair_handoff_sha256","processed_asset_sha256","training_copy_asset_sha256","policy_revision_sha256","producer_operation_sha256"):
            validate_sha256(getattr(self,n), field_name=n)
        if self.parent_terminal_sha256 is not None:
            validate_sha256(self.parent_terminal_sha256, field_name="parent_terminal_sha256")
        if isinstance(self.revision,bool) or not isinstance(self.revision,int) or self.revision < 1:
            raise ValueError("revision must be positive")

    def to_dict(self) -> dict[str, Any]:
        body={
            "record_type":"OwnerVoiceQ2Terminal",
            "schema_version":1,
            "pair_handoff_sha256":self.pair_handoff_sha256,
            "processed_asset_sha256":self.processed_asset_sha256,
            "training_copy_asset_sha256":self.training_copy_asset_sha256,
            "policy_revision_sha256":self.policy_revision_sha256,
            "producer_operation_sha256":self.producer_operation_sha256,
            "revision":self.revision,
            "parent_terminal_sha256":self.parent_terminal_sha256,
            "state":"BOUND_VERIFIED",
            "audio_body_persisted":False,
            "publication_started":False,
        }
        body["terminal_sha256"]=sha256_bytes(canonical_json_bytes(body))
        return body


def parse_q2_terminal(value: Mapping[str, Any]) -> Q2TerminalRecord:
    expected={"record_type","schema_version","pair_handoff_sha256","processed_asset_sha256","training_copy_asset_sha256","policy_revision_sha256","producer_operation_sha256","revision","parent_terminal_sha256","state","audio_body_persisted","publication_started","terminal_sha256"}
    if not isinstance(value,Mapping) or set(value)!=expected:
        raise ValueError("terminal fields are incomplete or unknown")
    if value["record_type"]!="OwnerVoiceQ2Terminal" or value["schema_version"]!=1 or value["state"]!="BOUND_VERIFIED":
        raise ValueError("terminal identity is invalid")
    if value["audio_body_persisted"] is not False or value["publication_started"] is not False:
        raise ValueError("terminal crosses body/publication boundary")
    rec=Q2TerminalRecord(
        value["pair_handoff_sha256"], value["processed_asset_sha256"], value["training_copy_asset_sha256"],
        value["policy_revision_sha256"], value["producer_operation_sha256"], value["revision"], value["parent_terminal_sha256"],
    )
    if rec.to_dict()["terminal_sha256"] != value["terminal_sha256"]:
        raise ValueError("terminal_sha256 mismatch")
    return rec

__all__=["Q2TerminalRecord","parse_q2_terminal"]
