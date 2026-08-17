"""Beginner-facing, non-executing TASK-046 Voice Model Builder client.

The client projects an already validated ``VerticalSliceWorkflowRevision``
into twelve friendly steps. R3 validates a bounded UTF-8 JSON workflow selected
by the user. R4 adds localized status and next-action guidance without changing
the canonical snapshot. It still has no Dataset, Job, training, model, audio,
provider or network execution surface.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from html import escape
import inspect
import json
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Mapping, Sequence

from .serialization import canonical_json_bytes, sha256_bytes, validate_sha256
from .voice_model_builder_workflow import validate_record as validate_workflow_record


SCHEMA_ID = "bai.task046.voice-model-builder-beginner-client.v1"
MAX_WORKFLOW_JSON_BYTES = 1_048_576


class Locale(str, Enum):
    JA = "ja"
    EN = "en"


class ClientState(str, Enum):
    NOT_CHECKED = "NOT_CHECKED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"


class ClientStepKey(str, Enum):
    CHOOSE_RECORDINGS = "CHOOSE_RECORDINGS"
    CHECK_RECORDINGS = "CHECK_RECORDINGS"
    REVIEW_DATASET = "REVIEW_DATASET"
    CHOOSE_TRAINING_RECIPE = "CHOOSE_TRAINING_RECIPE"
    REVIEW_TRAINING_RUN = "REVIEW_TRAINING_RUN"
    START_TRAINING = "START_TRAINING"
    MONITOR_TRAINING = "MONITOR_TRAINING"
    REGISTER_MODEL = "REGISTER_MODEL"
    EVALUATE_AND_APPROVE = "EVALUATE_AND_APPROVE"
    GENERATE_STYLE_TEST = "GENERATE_STYLE_TEST"
    REVIEW_MASTER_WAV = "REVIEW_MASTER_WAV"
    USE_FOR_NARRATION = "USE_FOR_NARRATION"


_STEP_ORDER = tuple(ClientStepKey)
_CURRENT_STEP_BY_WORKFLOW_STATE = {
    "RECORDINGS_REVIEW_REQUIRED": 1,
    "DATASET_PROPOSAL_READY": 2,
    "DATASET_ADOPTION_BLOCKED": 2,
    "TRAINING_RECIPE_NOT_VERIFIED": 3,
    "READY_FOR_OWNER_TRAINING_CONFIRMATION": 5,
    "TRAINING_IN_PROGRESS": 6,
    "TRAINING_COMPLETED_ARTIFACT_UNBOUND": 7,
    "MODEL_CANDIDATE_REGISTERED": 8,
    "EVALUATION_PENDING": 8,
    "EVALUATED_CANDIDATE": 8,
    "OWNER_APPROVED": 9,
    "STYLE_CUES_PENDING": 9,
    "MASTER_ASSEMBLY_PENDING": 10,
    "MASTER_REVIEW_REQUIRED": 10,
    "MASTER_ACCEPTED": 11,
    "MASTER_REJECTED": 10,
    "FAILED_KNOWN": 0,
    "UNKNOWN": 0,
}
_BLOCKED_WORKFLOW_STATES = frozenset(
    {"UNKNOWN", "FAILED_KNOWN", "DATASET_ADOPTION_BLOCKED", "TRAINING_RECIPE_NOT_VERIFIED", "MASTER_REJECTED"}
)

_LABELS = {
    Locale.JA: {
        ClientStepKey.CHOOSE_RECORDINGS: "録音を選ぶ",
        ClientStepKey.CHECK_RECORDINGS: "録音品質を確認する",
        ClientStepKey.REVIEW_DATASET: "学習に使う録音を確認する",
        ClientStepKey.CHOOSE_TRAINING_RECIPE: "学習方法を確認する",
        ClientStepKey.REVIEW_TRAINING_RUN: "学習内容を最終確認する",
        ClientStepKey.START_TRAINING: "Owner確認後に学習を開始する",
        ClientStepKey.MONITOR_TRAINING: "学習状況を監視する",
        ClientStepKey.REGISTER_MODEL: "生成物をモデル候補として登録する",
        ClientStepKey.EVALUATE_AND_APPROVE: "品質を評価してOwnerが承認する",
        ClientStepKey.GENERATE_STYLE_TEST: "スタイル別の短い音声を作る",
        ClientStepKey.REVIEW_MASTER_WAV: "自然につないだMaster WAVを確認する",
        ClientStepKey.USE_FOR_NARRATION: "ナレーション利用を別Gateで許可する",
    },
    Locale.EN: {
        ClientStepKey.CHOOSE_RECORDINGS: "Choose recordings",
        ClientStepKey.CHECK_RECORDINGS: "Check recording quality",
        ClientStepKey.REVIEW_DATASET: "Review recordings selected for training",
        ClientStepKey.CHOOSE_TRAINING_RECIPE: "Review the training recipe",
        ClientStepKey.REVIEW_TRAINING_RUN: "Review the exact training run",
        ClientStepKey.START_TRAINING: "Start only after Owner confirmation",
        ClientStepKey.MONITOR_TRAINING: "Monitor the training run",
        ClientStepKey.REGISTER_MODEL: "Register output as a model candidate",
        ClientStepKey.EVALUATE_AND_APPROVE: "Evaluate quality and obtain Owner approval",
        ClientStepKey.GENERATE_STYLE_TEST: "Generate short style tests",
        ClientStepKey.REVIEW_MASTER_WAV: "Review one naturally joined Master WAV",
        ClientStepKey.USE_FOR_NARRATION: "Admit narration use through a separate gate",
    },
}

_STATE_LABELS = {
    Locale.JA: {
        ClientState.NOT_CHECKED: "まだ確認していません",
        ClientState.ACTION_REQUIRED: "次の対応が必要です",
        ClientState.BLOCKED: "現在は進められません",
        ClientState.COMPLETE: "完了",
    },
    Locale.EN: {
        ClientState.NOT_CHECKED: "Not checked yet",
        ClientState.ACTION_REQUIRED: "Next action needed",
        ClientState.BLOCKED: "Cannot proceed now",
        ClientState.COMPLETE: "Complete",
    },
}

_WORKFLOW_GUIDANCE = {
    Locale.JA: {
        "RECORDINGS_REVIEW_REQUIRED": ("録音の確認が必要です", "録音品質の確認結果を見て、学習候補に進める録音を確認してください。"),
        "DATASET_PROPOSAL_READY": ("学習候補の確認準備ができました", "学習に使う録音の候補と権利・同意の状態を確認してください。"),
        "DATASET_ADOPTION_BLOCKED": ("学習用録音の採用を進められません", "不足している品質・権利・同意の確認を完了してから、もう一度判定してください。"),
        "TRAINING_RECIPE_NOT_VERIFIED": ("学習方法をまだ確認できません", "公式の学習手順と、このPCで動かせることを示す検証結果をそろえてください。"),
        "READY_FOR_OWNER_TRAINING_CONFIRMATION": ("学習開始前のOwner確認待ちです", "使用する録音・モデル・設定・保存先を確認し、別の開始確認を行ってください。"),
        "TRAINING_IN_PROGRESS": ("学習処理が進行中です", "同じ学習を重複して開始せず、外部ジョブの状態を確認してください。"),
        "TRAINING_COMPLETED_ARTIFACT_UNBOUND": ("学習処理は完了しましたが、生成物は未確認です", "生成物の保存先・チェックサム・元データとのつながりを確認してください。"),
        "MODEL_CANDIDATE_REGISTERED": ("モデル候補を登録しました", "品質評価を行い、録音に含まれない評価用データとの混入がないか確認してください。"),
        "EVALUATION_PENDING": ("モデル候補の品質評価待ちです", "評価結果がそろうまで、承認やナレーション利用へ進めないでください。"),
        "EVALUATED_CANDIDATE": ("モデル候補の品質評価が完了しました", "評価結果を確認し、Ownerが承認・却下・再試験を選んでください。"),
        "OWNER_APPROVED": ("モデル候補がOwner承認されました", "スタイル別の短い試験音声を作るための別Gateを確認してください。"),
        "STYLE_CUES_PENDING": ("スタイル別の試験音声が必要です", "各スタイルの短い音声を確認し、自然につなぐ候補を選んでください。"),
        "MASTER_ASSEMBLY_PENDING": ("Master WAVの組み立て待ちです", "承認済みのスタイル音声を自然につなぐ外部処理を、別Gateで実行してください。"),
        "MASTER_REVIEW_REQUIRED": ("Master WAVの試聴確認が必要です", "全体を聞き、つながり・話者らしさ・ノイズ・長さを確認してください。"),
        "MASTER_ACCEPTED": ("Master WAVが承認されました", "実際のナレーション利用は別Gateなので、用途・権利・出力先を確認してください。"),
        "MASTER_REJECTED": ("Master WAVの修正が必要です", "却下理由を確認し、必要なスタイル音声またはつなぎ方を見直してください。"),
        "FAILED_KNOWN": ("処理に確認済みの失敗があります", "原因の記録を確認してください。自動で同じ処理を再実行しないでください。"),
        "UNKNOWN": ("現在の状態を確認できません", "正本のジョブ・生成物・保存先を再確認し、状態が確定するまで新しい処理を始めないでください。"),
    },
    Locale.EN: {
        "RECORDINGS_REVIEW_REQUIRED": ("Recordings need review", "Review the recording-quality results and confirm which recordings may move forward."),
        "DATASET_PROPOSAL_READY": ("The training selection is ready for review", "Review the proposed recordings and their current rights and consent state."),
        "DATASET_ADOPTION_BLOCKED": ("The training selection cannot proceed", "Resolve the missing quality, rights, or consent checks, then evaluate it again."),
        "TRAINING_RECIPE_NOT_VERIFIED": ("The training method is not verified", "Provide an official recipe and evidence that the exact mode works on this computer."),
        "READY_FOR_OWNER_TRAINING_CONFIRMATION": ("Waiting for Owner confirmation before training", "Review the recordings, model, settings, and destination, then use the separate start gate."),
        "TRAINING_IN_PROGRESS": ("Training is in progress", "Do not start a duplicate run; monitor the authoritative external job instead."),
        "TRAINING_COMPLETED_ARTIFACT_UNBOUND": ("Training finished, but its output is not verified", "Verify the output destination, checksums, and lineage before registration."),
        "MODEL_CANDIDATE_REGISTERED": ("The model candidate is registered", "Evaluate quality and verify that held-out evaluation data did not leak into training."),
        "EVALUATION_PENDING": ("The model candidate is waiting for evaluation", "Do not approve or use it for narration until evaluation results are complete."),
        "EVALUATED_CANDIDATE": ("The model candidate evaluation is complete", "Review the results and let the Owner choose approve, reject, or retest."),
        "OWNER_APPROVED": ("The Owner approved the model candidate", "Check the separate gate for creating short style-test audio."),
        "STYLE_CUES_PENDING": ("Short style tests are needed", "Review each style sample and select the cues to join naturally."),
        "MASTER_ASSEMBLY_PENDING": ("The Master WAV is waiting to be assembled", "Use a separate gate to join approved style cues into one natural result."),
        "MASTER_REVIEW_REQUIRED": ("The Master WAV needs listening review", "Listen end to end and check joins, speaker identity, noise, and duration."),
        "MASTER_ACCEPTED": ("The Master WAV is approved", "Narration use is a separate gate; review its purpose, rights, and destination."),
        "MASTER_REJECTED": ("The Master WAV needs revision", "Review the rejection reasons and revise the relevant style cue or join."),
        "FAILED_KNOWN": ("A known failure was recorded", "Review the recorded cause. Do not automatically repeat the same operation."),
        "UNKNOWN": ("The current state cannot be verified", "Reconcile the authoritative job, artifact, and destination before starting anything new."),
    },
}


def _expected_step(
    workflow_state: str, index: int,
) -> tuple[ClientState, list[str]]:
    current_index = _CURRENT_STEP_BY_WORKFLOW_STATE[workflow_state]
    if workflow_state in _BLOCKED_WORKFLOW_STATES and index == current_index:
        return ClientState.BLOCKED, [f"WORKFLOW_{workflow_state}"]
    if index < current_index:
        return ClientState.COMPLETE, []
    if index == current_index:
        return ClientState.ACTION_REQUIRED, ["EXTERNAL_HUMAN_OR_EFFECT_GATE_REQUIRED"]
    return ClientState.NOT_CHECKED, ["PREVIOUS_STEP_NOT_COMPLETE"]


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be SHA-256")
    return validate_sha256(value, field_name=name)


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must be UTC")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _body_digest(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes({key: item for key, item in value.items() if key != "snapshot_sha256"}))


def validate_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "record_type", "snapshot_id", "workflow_sha256", "workflow_revision",
        "workflow_state", "locale", "steps", "current_step", "client_state",
        "reason_codes", "display_only", "execution_started", "dataset_effect_started",
        "training_started", "model_inference_started", "audio_access_started",
        "publication_started", "created_at", "snapshot_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("BeginnerClientSnapshot fields are incomplete or unknown")
    if value["record_type"] != "BeginnerClientSnapshot":
        raise ValueError("record_type is invalid")
    if not isinstance(value["snapshot_id"], str) or not value["snapshot_id"].startswith("client-snapshot:"):
        raise ValueError("snapshot_id is invalid")
    _sha(value["workflow_sha256"], "workflow_sha256")
    if not isinstance(value["workflow_revision"], int) or value["workflow_revision"] < 1:
        raise ValueError("workflow_revision is invalid")
    try:
        locale = Locale(value["locale"])
        state = ClientState(value["client_state"])
    except (TypeError, ValueError) as exc:
        raise ValueError("closed client enum is invalid") from exc
    workflow_state = value["workflow_state"]
    if not isinstance(workflow_state, str) or workflow_state not in _CURRENT_STEP_BY_WORKFLOW_STATE:
        raise ValueError("workflow_state is invalid")
    blocked = workflow_state in _BLOCKED_WORKFLOW_STATES
    expected_client_state = ClientState.BLOCKED if blocked else ClientState.ACTION_REQUIRED
    if state is not expected_client_state:
        raise ValueError("client_state does not match workflow_state")
    steps = value["steps"]
    if not isinstance(steps, list) or len(steps) != len(_STEP_ORDER):
        raise ValueError("steps must contain the exact twelve-step guide")
    for ordinal, (step, expected_key) in enumerate(zip(steps, _STEP_ORDER, strict=True), start=1):
        fields = {"ordinal", "step_key", "label", "state", "reason_codes", "operation_effect_authorized"}
        if not isinstance(step, Mapping) or set(step) != fields:
            raise ValueError("client step fields are invalid")
        if step["ordinal"] != ordinal or step["step_key"] != expected_key.value:
            raise ValueError("client step order is invalid")
        if step["label"] != _LABELS[locale][expected_key]:
            raise ValueError("client step label does not match locale")
        try:
            step_state = ClientState(step["state"])
        except (TypeError, ValueError) as exc:
            raise ValueError("client step state is invalid") from exc
        if not isinstance(step["reason_codes"], list) or len(step["reason_codes"]) != len(set(step["reason_codes"])):
            raise ValueError("client step reason_codes are invalid")
        expected_state, expected_reasons = _expected_step(workflow_state, ordinal - 1)
        if step_state is not expected_state or step["reason_codes"] != expected_reasons:
            raise ValueError("client step state does not match workflow_state")
        if step["operation_effect_authorized"] is not False:
            raise ValueError("R0 client cannot authorize an operation effect")
    expected_current_step = _CURRENT_STEP_BY_WORKFLOW_STATE[workflow_state] + 1
    if value["current_step"] != expected_current_step:
        raise ValueError("current_step does not match workflow_state")
    reasons = value["reason_codes"]
    if not isinstance(reasons, list) or len(reasons) != len(set(reasons)):
        raise ValueError("reason_codes are invalid")
    expected_reasons = (
        [f"WORKFLOW_{workflow_state}"] if blocked
        else ["EXTERNAL_HUMAN_OR_EFFECT_GATE_REQUIRED"]
    )
    if reasons != expected_reasons:
        raise ValueError("reason_codes do not match workflow_state")
    for name in (
        "display_only", "execution_started", "dataset_effect_started", "training_started",
        "model_inference_started", "audio_access_started", "publication_started",
    ):
        expected_value = name == "display_only"
        if value[name] is not expected_value:
            raise ValueError(f"{name} violates the R0 no-effect boundary")
    _timestamp(value["created_at"], "created_at")
    _sha(value["snapshot_sha256"], "snapshot_sha256")
    if value["snapshot_sha256"] != _body_digest(value):
        raise ValueError("snapshot_sha256 mismatch")
    return _thaw(value)


@dataclass(frozen=True, slots=True)
class BeginnerClientSnapshot:
    data: Mapping[str, Any]
    RECORD_TYPE: ClassVar[str] = "BeginnerClientSnapshot"

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(validate_snapshot(self.data)))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.data)

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def compile_beginner_snapshot(
    *, snapshot_id: str, workflow: Mapping[str, Any], locale: str, created_at: str,
) -> BeginnerClientSnapshot:
    validated = validate_workflow_record(workflow, expected_type="VerticalSliceWorkflowRevision")
    selected_locale = Locale(locale)
    workflow_state = validated["state"]
    current_index = _CURRENT_STEP_BY_WORKFLOW_STATE[workflow_state]
    blocked = workflow_state in _BLOCKED_WORKFLOW_STATES
    steps: list[dict[str, Any]] = []
    for index, key in enumerate(_STEP_ORDER):
        step_state, step_reasons = _expected_step(workflow_state, index)
        steps.append(
            {
                "ordinal": index + 1,
                "step_key": key.value,
                "label": _LABELS[selected_locale][key],
                "state": step_state.value,
                "reason_codes": step_reasons,
                "operation_effect_authorized": False,
            }
        )
    body = {
        "record_type": "BeginnerClientSnapshot",
        "snapshot_id": snapshot_id,
        "workflow_sha256": validated["workflow_sha256"],
        "workflow_revision": validated["revision"],
        "workflow_state": workflow_state,
        "locale": selected_locale.value,
        "steps": steps,
        "current_step": current_index + 1,
        "client_state": (ClientState.BLOCKED if blocked else ClientState.ACTION_REQUIRED).value,
        "reason_codes": [f"WORKFLOW_{workflow_state}"] if blocked else ["EXTERNAL_HUMAN_OR_EFFECT_GATE_REQUIRED"],
        "display_only": True,
        "execution_started": False,
        "dataset_effect_started": False,
        "training_started": False,
        "model_inference_started": False,
        "audio_access_started": False,
        "publication_started": False,
        "created_at": created_at,
    }
    body["snapshot_sha256"] = _body_digest(body)
    return BeginnerClientSnapshot(body)


def compile_beginner_snapshot_from_workflow_json(
    *, payload: bytes, locale: str, created_at: str,
) -> BeginnerClientSnapshot:
    """Validate one bounded workflow JSON document and project it without effects."""
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_WORKFLOW_JSON_BYTES:
        raise ValueError("workflow JSON must be between 1 byte and 1 MiB")
    if payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError("workflow JSON must be UTF-8 without a byte-order mark")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("workflow JSON must be valid UTF-8") from exc

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("workflow JSON contains a duplicate key")
            result[key] = item
        return result

    try:
        workflow = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("workflow JSON is malformed or too deeply nested") from exc
    if not isinstance(workflow, Mapping):
        raise ValueError("workflow JSON root must be an object")
    validated = validate_workflow_record(workflow, expected_type="VerticalSliceWorkflowRevision")
    return compile_beginner_snapshot(
        snapshot_id=f'client-snapshot:workflow:{validated["workflow_sha256"].removeprefix("sha256:")}',
        workflow=validated,
        locale=locale,
        created_at=created_at,
    )


def public_projection(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_snapshot(snapshot)
    locale = Locale(value["locale"])
    summary, next_action = _WORKFLOW_GUIDANCE[locale][value["workflow_state"]]
    return {
        "record_type": value["record_type"],
        "locale": value["locale"],
        "current_step": value["current_step"],
        "client_state": value["client_state"],
        "client_state_label": _STATE_LABELS[locale][ClientState(value["client_state"])],
        "progress_completed": sum(step["state"] == ClientState.COMPLETE.value for step in value["steps"]),
        "progress_total": len(_STEP_ORDER),
        "current_summary": summary,
        "next_action": next_action,
        "steps": [
            {
                "ordinal": step["ordinal"],
                "label": step["label"],
                "state": step["state"],
                "state_label": _STATE_LABELS[locale][ClientState(step["state"])],
                "operation_effect_authorized": False,
            }
            for step in value["steps"]
        ],
        "safety_notice": (
            "この画面だけでは学習・音声生成を開始しません。" if value["locale"] == "ja"
            else "This screen never starts training or audio generation by itself."
        ),
    }


def render_beginner_html(snapshot: Mapping[str, Any]) -> str:
    view = public_projection(snapshot)
    rows = "".join(
        f'<li class="{escape(step["state"].lower())}"><span>{step["ordinal"]}</span>'
        f'<strong>{escape(step["label"])}</strong><em>{escape(step["state_label"])}</em></li>'
        for step in view["steps"]
    )
    title = "音声モデル作成ガイド" if view["locale"] == "ja" else "Voice Model Builder Guide"
    next_title = "次にすること" if view["locale"] == "ja" else "What to do next"
    return f"""<!doctype html><html lang="{escape(view['locale'])}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<style>body{{margin:0;background:#10141b;color:#eef2f7;font:16px/1.5 'Segoe UI',sans-serif}}main{{max-width:840px;margin:auto;padding:28px}}h1{{font-size:28px}}p{{padding:14px;background:#18202b;border-left:4px solid #5b8def}}section{{padding:16px;background:#171d26;border:1px solid #303b4a;border-radius:8px;margin:12px 0}}section h2{{font-size:19px;margin:0 0 6px}}section p{{padding:0;background:transparent;border:0;margin:0}}ol{{list-style:none;padding:0;display:grid;gap:9px}}li{{display:grid;grid-template-columns:38px 1fr auto;align-items:center;gap:12px;padding:13px;border:1px solid #303b4a;border-radius:8px;background:#171d26}}li span{{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:#2a3544}}li em{{font-size:12px;color:#aab5c3}}li.complete{{border-color:#347d5b}}li.action_required{{border-color:#b58535}}li.blocked{{border-color:#b34d55}}footer{{color:#aab5c3;font-size:13px}}</style></head>
<body><main><h1>{escape(title)}</h1><p>{escape(view['safety_notice'])}</p>
<section><h2>{escape(view['current_summary'])}</h2><p><strong>{escape(next_title)}:</strong> {escape(view['next_action'])}</p></section>
<ol>{rows}</ol><footer>R4 · FRIENDLY VALIDATION PREVIEW · execution_started=false</footer></main></body></html>"""


def build_demo_snapshot(*, locale: str = "ja") -> BeginnerClientSnapshot:
    from .voice_model_builder_workflow import add_record_digest

    source = add_record_digest(
        {
            "record_type": "CanonicalSourceBinding",
            "contract_state": "CANONICAL_REF_NOT_PROVIDED",
            "source_kind": "OBS_CAPTURE_SESSION",
            "canonical_ref": None,
            "canonical_revision": None,
            "canonical_sha256": None,
            "current_valid": None,
            "evaluated_at": None,
        },
        "binding_sha256",
    )
    workflow = add_record_digest(
        {
            "record_type": "VerticalSliceWorkflowRevision",
            "workflow_id": "workflow:synthetic-demo",
            "revision": 1,
            "parent_workflow_sha256": None,
            "project_id": "project:synthetic-demo",
            "source_bindings": [source],
            "state": "RECORDINGS_REVIEW_REQUIRED",
            "ordered_cue_sha256": [],
            "master_candidate_sha256": None,
            "reason_codes": ["SYNTHETIC_DEMO_ONLY"],
            "created_at": "2026-08-17T00:00:00Z",
            "dataset_effect_started": False,
            "training_started": False,
            "render_started": False,
        },
        "workflow_sha256",
    )
    return compile_beginner_snapshot(
        snapshot_id="client-snapshot:synthetic-demo",
        workflow=workflow,
        locale=locale,
        created_at="2026-08-17T00:00:00Z",
    )


def launch_demo(
    *,
    locale: str = "ja",
    initial_snapshot: Mapping[str, Any] | None = None,
    workflow_loader: Callable[[], tuple[bytes, str] | None] | None = None,
) -> None:
    """Launch a preview; an optional callback may supply bounded JSON bytes."""
    import tkinter as tk
    from tkinter import ttk

    current = initial_snapshot or build_demo_snapshot(locale=locale).to_dict()
    snapshot = public_projection(current)
    window = tk.Tk()
    window.title("BAI Voice Model Builder — Workflow Preview")
    window.geometry("820x780")
    frame = ttk.Frame(window, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="音声モデル作成ガイド" if locale == "ja" else "Voice Model Builder Guide", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(frame, text=snapshot["safety_notice"], wraplength=760).pack(anchor="w", pady=(8, 16))
    status = tk.StringVar(
        value=("合成Demoを表示中" if locale == "ja" else "Showing the synthetic demo")
        if initial_snapshot is None
        else ("検証済みworkflowを表示中" if locale == "ja" else "Showing a validated workflow")
    )
    guidance = tk.StringVar()
    next_action = tk.StringVar()
    ttk.Label(frame, textvariable=guidance, font=("Segoe UI", 12, "bold"), wraplength=760).pack(anchor="w")
    ttk.Label(frame, textvariable=next_action, wraplength=760).pack(anchor="w", pady=(4, 12))
    steps_frame = ttk.Frame(frame)
    steps_frame.pack(fill="x")

    def show_steps(value: Mapping[str, Any]) -> None:
        view = public_projection(value)
        guidance.set(view["current_summary"])
        prefix = "次にすること: " if locale == "ja" else "What to do next: "
        next_action.set(prefix + view["next_action"])
        for child in steps_frame.winfo_children():
            child.destroy()
        for step in view["steps"]:
            ttk.Label(
                steps_frame,
                text=f'{step["ordinal"]}. {step["label"]}  —  {step["state_label"]}',
                wraplength=760,
            ).pack(anchor="w", pady=3)

    def load_workflow() -> None:
        if workflow_loader is None:
            return
        try:
            supplied = workflow_loader()
        except (OSError, TypeError, ValueError):
            status.set(
                "読み取れませんでした。元ファイルは変更されていません。"
                if locale == "ja"
                else "The file could not be read. The original was not changed."
            )
            return
        if supplied is None:
            status.set("選択をキャンセルしました" if locale == "ja" else "Selection cancelled")
            return
        payload, created_at = supplied
        try:
            imported = compile_beginner_snapshot_from_workflow_json(
                payload=payload, locale=locale, created_at=created_at,
            )
        except (TypeError, ValueError):
            status.set(
                "検証に失敗しました。workflow JSONは変更・実行されていません。"
                if locale == "ja"
                else "Validation failed. The workflow JSON was not changed or executed."
            )
            return
        show_steps(imported.to_dict())
        status.set("検証済みworkflowを表示中" if locale == "ja" else "Showing a validated workflow")

    show_steps(current)
    if workflow_loader is not None:
        ttk.Button(
            frame,
            text="workflow JSONを選ぶ" if locale == "ja" else "Choose workflow JSON",
            command=load_workflow,
        ).pack(anchor="w", pady=(16, 6))
    ttk.Label(frame, textvariable=status, wraplength=760).pack(anchor="w")
    ttk.Label(frame, text="R4 / FRIENDLY VALIDATION PREVIEW / execution_started=false").pack(anchor="w", pady=(14, 0))
    window.mainloop()


def assert_no_forbidden_effect_surface() -> None:
    module = inspect.getmodule(assert_no_forbidden_effect_surface)
    forbidden = {"subprocess", "socket", "requests", "urllib", "torch", "wave", "pathlib"}
    if module is None or forbidden.intersection(module.__dict__):
        raise AssertionError("forbidden client effect surface detected")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TASK-046 synthetic beginner-client preview")
    parser.add_argument("--demo", action="store_true", help="open the display-only synthetic preview")
    parser.add_argument("--locale", choices=("ja", "en"), default="ja")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error("R0 supports only --demo; real workflow effects are not available")
    launch_demo(locale=args.locale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
