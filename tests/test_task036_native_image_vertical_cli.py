from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_video_production.errors import ProductError, ProductErrorCategory
from ai_video_production.task036_native_image_vertical_cli import build_parser, run, _load_config_scope


H = lambda text: "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
QUEUE_ID = "QUEUE-1234567890ABCDEF12345678"
EXECUTION_ID = "EXEC-1234567890ABCDEF12345678"
OUTPUT_REF = f"project-output://generated/{EXECUTION_ID}/result.png"


class FakeBridge:
    def __init__(self, *, execution_state: str | None = None, adopted: bool = False) -> None:
        self.calls: list[str] = []
        self.cancelled: list[str] = []
        self.entry = {
            "queue_entry_id": QUEUE_ID,
            "scene_id": "scene-1",
            "slot_id": "slot-image",
            "prompt_id": "prompt-1",
            "prompt_version": 1,
            "prompt_sha256": H("p"),
            "queue_status": "ADMISSION_READY",
            "provider_execution_authorized": False,
            "paid_execution_authorized": False,
            "candidate_creation_authorized": False,
        }
        self.execution_event = None if execution_state is None else self._event(execution_state)
        self.adopted = adopted

    def _event(self, state: str) -> dict:
        event = {
            "execution_id": EXECUTION_ID,
            "queue_entry_id": QUEUE_ID,
            "state": state,
            "failure_code": None,
        }
        if state == "COMPLETED":
            event.update({
                "output_ref": OUTPUT_REF,
                "output_sha256": H("o"),
                "media_kind": "IMAGE",
            })
        return event

    def _execution(self) -> dict:
        latest = [] if self.execution_event is None else [self.execution_event]
        recovery = []
        if self.execution_event is not None and self.execution_event["state"] == "DISPATCHING":
            recovery = [{**self.execution_event, "recovery_supported": True}]
        return {
            "available": True,
            "execution_snapshot_sha256": H("e"),
            "latest_executions": latest,
            "recovery": {"required": bool(recovery), "dispatching": recovery},
        }

    def _adoption(self) -> dict:
        records = []
        eligible = []
        if self.adopted:
            records = [{
                "adoption_id": "adoption-1",
                "execution_id": EXECUTION_ID,
                "queue_entry_id": QUEUE_ID,
                "slot_id": "slot-image",
                "candidate_id": "candidate-1",
                "asset_id": "AST-1234567890ABCDEF12345678",
                "output_ref": OUTPUT_REF,
                "output_sha256": H("o"),
                "media_kind": "IMAGE",
                "state": "READY_FOR_AUDIT",
            }]
        elif self.execution_event is not None and self.execution_event["state"] == "COMPLETED":
            eligible = [{
                "execution_id": EXECUTION_ID,
                "queue_entry_id": QUEUE_ID,
                "output_sha256": H("o"),
                "media_kind": "IMAGE",
                "adoption_status": "READY",
            }]
        return {
            "available": True,
            "adoption_snapshot_sha256": H("a"),
            "latest_adoptions": records,
            "eligible_completed_outputs": eligible,
            "provider_execution_started": False,
            "provider_execution_replayed": False,
            "paid_execution_authorized": False,
            "human_audit_decision_created": False,
            "candidate_accepted": False,
            "candidate_locked": False,
            "publication_authorized": False,
            "nle_mutation_started": False,
        }

    def generation_queue_snapshot(self, _args):
        self.calls.append("queue_snapshot")
        return {
            "available": True,
            "queue_snapshot_sha256": H("q"),
            "entries": [self.entry],
            "execution_control": self._execution(),
            "output_adoption_control": self._adoption(),
        }

    def generation_execution_snapshot(self, _args):
        self.calls.append("execution_snapshot")
        return self._execution()

    def generation_execution_preflight(self, args):
        self.calls.append("execution_preflight")
        assert args == {"queue_entry_id": QUEUE_ID}
        return {
            "route_id": "local-image",
            "provider_id": "comfy-image",
            "model_id": "flux-schnell-fp8",
            "workflow_sha256": H("w"),
            "runtime_policy": "FLUX_IMAGE_LOCAL_ONLY_V1",
            "dispatch_performed": False,
        }

    def generation_execution_prepare(self, args):
        self.calls.append("execution_prepare")
        assert args == {
            "queue_entry_id": QUEUE_ID,
            "expected_queue_snapshot_sha256": H("q"),
            "expected_execution_snapshot_sha256": H("e"),
            "expected_project_manifest_sha256": H("m"),
        }
        return {
            "confirmation_id": "private-execution-token",
            "queue_entry_id": QUEUE_ID,
            "scene_id": "scene-1",
            "slot_id": "slot-image",
            "prompt_id": "prompt-1",
            "prompt_version": 1,
            "prompt_sha256": H("p"),
            "route_id": "local-image",
            "provider_id": "comfy-image",
            "model_id": "flux-schnell-fp8",
            "capability": "TEXT_TO_IMAGE",
            "cost_class": "LOCAL_FREE_AI",
            "media_kind": "IMAGE",
            "paid_execution_authorized": False,
            "provider_execution_started": False,
        }

    def generation_execution_cancel(self, args):
        self.calls.append("execution_cancel")
        self.cancelled.append(args["confirmation_id"])
        return {"cancelled": True}

    def generation_execution_apply(self, args):
        self.calls.append("execution_apply")
        assert args == {"confirmation_id": "private-execution-token"}
        self.execution_event = self._event("COMPLETED")
        result = self._execution()
        result.pop("available")
        return result

    def production_snapshot(self, _args):
        self.calls.append("production_snapshot")
        candidates = []
        if self.adopted:
            candidates = [{
                "candidate_id": "candidate-1",
                "asset_id": "AST-1234567890ABCDEF12345678",
                "asset_sha256": H("o"),
                "generation_job_id": EXECUTION_ID,
                "slot_id": "slot-image",
                "lifecycle_state": "READY_FOR_AUDIT",
            }]
        return {
            "available": True,
            "snapshot_sha256": H("r"),
            "slots": [{"slot_id": "slot-image", "locked_candidate_id": None, "candidates": candidates}],
        }

    def prompt_evidence_snapshot(self, _args):
        self.calls.append("prompt_snapshot")
        return {"available": True, "prompt_snapshot_sha256": H("p")}

    def generation_output_adoption_prepare(self, args):
        self.calls.append("adoption_prepare")
        assert args == {
            "execution_id": EXECUTION_ID,
            "expected_execution_snapshot_sha256": H("e"),
            "expected_queue_snapshot_sha256": H("q"),
            "expected_production_snapshot_sha256": H("r"),
            "expected_prompt_snapshot_sha256": H("p"),
            "expected_adoption_snapshot_sha256": H("a"),
            "expected_project_manifest_sha256": H("m"),
        }
        return {
            "confirmation_id": "private-adoption-token",
            "execution_id": EXECUTION_ID,
            "slot_id": "slot-image",
            "candidate_id": "candidate-1",
            "output_sha256": H("o"),
            "provider_execution_started": False,
            "provider_execution_replayed": False,
            "paid_execution_authorized": False,
            "human_audit_decision_created": False,
            "candidate_accepted": False,
            "candidate_locked": False,
            "publication_authorized": False,
            "nle_mutation_started": False,
        }

    def generation_output_adoption_apply(self, args):
        self.calls.append("adoption_apply")
        assert args == {"confirmation_id": "private-adoption-token"}
        self.adopted = True
        result = self._adoption()
        result.pop("available")
        return result


class FakeLaunch:
    def __init__(self, bridge: FakeBridge) -> None:
        self.bridge = bridge
        self.closed = 0

    def close(self):
        self.closed += 1


def dependencies(bridge: FakeBridge, output: list[str]):
    configuration = SimpleNamespace(
        project_id="project-1",
        project_root=Path("C:/private/project"),
        local_image_generation=object(),
    )
    manifest = SimpleNamespace(project_id="project-1", project_manifest_sha256=H("m"))
    launch = FakeLaunch(bridge)
    builder_calls = []

    def builder(config, **kwargs):
        builder_calls.append((config, kwargs))
        return launch

    return {
        "config_scope_loader": lambda _path: (configuration, H("c")),
        "manifest_loader": lambda _root: manifest,
        "initialization_checker": lambda _config: None,
        "launch_builder": builder,
        "output_writer": output.append,
    }, launch, builder_calls


def execute_args(operation: str = "execute") -> list[str]:
    return [
        operation,
        "--launch-config", r"C:\private\task036-launch.json",
        "--expected-launch-config-sha256", H("c"),
        "--expected-project-id", "project-1",
        "--expected-manifest-sha256", H("m"),
        "--queue-entry-id", QUEUE_ID,
    ]


def adoption_args(operation: str = "adopt") -> list[str]:
    return [
        operation,
        "--launch-config", r"C:\private\task036-launch.json",
        "--expected-launch-config-sha256", H("c"),
        "--expected-project-id", "project-1",
        "--expected-manifest-sha256", H("m"),
        "--execution-id", EXECUTION_ID,
        "--expected-output-sha256", H("o"),
    ]


def test_status_execution_is_read_only_and_closes_trusted_launch():
    output = []
    bridge = FakeBridge()
    deps, launch, calls = dependencies(bridge, output)

    assert run(execute_args("status-execution"), **deps) == 0

    result = json.loads(output[-1])
    assert result["status"] == "READY_TO_EXECUTE"
    assert result["provider_dispatch_started"] is False
    assert bridge.calls == ["queue_snapshot", "execution_preflight"]
    assert calls[0][1] == {"allow_product_job_bootstrap": False}
    assert launch.closed == 1


def test_execution_requires_exact_digest_phrase_and_cancel_is_provider_zero():
    output = []
    bridge = FakeBridge()
    deps, launch, _calls = dependencies(bridge, output)
    deps["input_reader"] = lambda: "NO"

    assert run(execute_args(), **deps) == 0

    confirmation = json.loads(output[0])
    result = json.loads(output[-1])
    assert confirmation["confirmation_phrase"] == f"EXECUTE {confirmation['confirmation_sha256']}"
    assert result == {
        "operation": "EXECUTE",
        "provider_dispatch_started": False,
        "queue_entry_id": QUEUE_ID,
        "status": "CANCELLED",
    }
    assert bridge.cancelled == ["private-execution-token"]
    assert "execution_apply" not in bridge.calls
    assert launch.closed == 1


def test_execution_exact_phrase_dispatches_once_and_returns_body_free_identity():
    output = []
    bridge = FakeBridge()
    deps, launch, _calls = dependencies(bridge, output)
    deps["input_reader"] = lambda: json.loads(output[-1])["confirmation_phrase"]

    assert run(execute_args(), **deps) == 0

    result = json.loads(output[-1])
    assert result["status"] == "COMPLETED"
    assert result["execution_id"] == EXECUTION_ID
    assert result["output_ref"] == OUTPUT_REF
    assert result["output_sha256"] == H("o")
    assert bridge.calls.count("execution_apply") == 1
    assert "adoption_prepare" not in bridge.calls
    assert launch.closed == 1
    serialized = "\n".join(output)
    assert "private-execution-token" not in serialized
    assert "C:\\private" not in serialized
    assert "prompt body" not in serialized


def test_existing_dispatch_is_recovery_only_and_execute_never_replays():
    output = []
    bridge = FakeBridge(execution_state="DISPATCHING")
    deps, launch, _calls = dependencies(bridge, output)

    assert run(execute_args("status-execution"), **deps) == 0
    assert json.loads(output[-1])["status"] == "RECOVERY_REQUIRED"
    assert "execution_preflight" not in bridge.calls
    output.clear()
    assert run(execute_args(), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_EXECUTION_ALREADY_STARTED"
    assert "execution_apply" not in bridge.calls
    assert launch.closed == 2


def test_completed_execution_is_rediscovered_without_provider_call():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    deps, launch, _calls = dependencies(bridge, output)

    assert run(execute_args("status-execution"), **deps) == 0

    result = json.loads(output[-1])
    assert result["status"] == "COMPLETED_REDISCOVERED"
    assert result["output_sha256"] == H("o")
    assert bridge.calls == ["queue_snapshot"]


def test_adoption_is_separate_exact_confirmation_and_never_executes_provider():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    deps, launch, _calls = dependencies(bridge, output)
    deps["input_reader"] = lambda: json.loads(output[-1])["confirmation_phrase"]

    assert run(adoption_args(), **deps) == 0

    result = json.loads(output[-1])
    assert result["status"] == "READY_FOR_AUDIT"
    assert result["candidate_lifecycle"] == "READY_FOR_AUDIT"
    assert result["candidate_accepted"] is False
    assert result["candidate_locked"] is False
    assert result["publication_authorized"] is False
    assert result["provider_replay_started"] is False
    assert "execution_preflight" not in bridge.calls
    assert "execution_prepare" not in bridge.calls
    assert "execution_apply" not in bridge.calls
    assert bridge.calls.count("adoption_apply") == 1
    assert launch.closed == 1


def test_adoption_wrong_output_digest_fails_before_prepare_and_closes():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    deps, launch, _calls = dependencies(bridge, output)
    args = adoption_args()
    args[-1] = H("x")

    assert run(args, **deps) == 1

    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_OUTPUT_SHA_MISMATCH"
    assert "adoption_prepare" not in bridge.calls
    assert launch.closed == 1


def test_manifest_mismatch_fails_before_launch_and_error_is_path_free():
    output = []
    bridge = FakeBridge()
    deps, launch, calls = dependencies(bridge, output)
    args = execute_args("status-execution")
    args[args.index("--expected-manifest-sha256") + 1] = H("x")

    assert run(args, **deps) == 1

    result = json.loads(output[-1])
    assert result == {
        "automatic_retry_allowed": False,
        "error_category": "AUTHORIZATION",
        "error_code": "ERR_TASK036_NATIVE_MANIFEST_STALE",
        "operation": "STATUS_EXECUTION",
        "status": "ERROR",
    }
    assert calls == []
    assert launch.closed == 0
    assert "private" not in output[-1].lower()


def test_launch_config_digest_mismatch_fails_before_launch():
    output = []
    bridge = FakeBridge()
    deps, launch, calls = dependencies(bridge, output)
    args = execute_args("status-execution")
    args[args.index("--expected-launch-config-sha256") + 1] = H("other")
    assert run(args, **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_LAUNCH_CONFIG_STALE"
    assert calls == []
    assert launch.closed == 0


def test_product_error_message_details_and_host_path_are_not_printed():
    output = []
    bridge = FakeBridge()
    deps, launch, _calls = dependencies(bridge, output)

    def builder(_config, **_kwargs):
        raise ProductError(
            "ERR_TEST_PRIVATE",
            r"do not print C:\private\secret\prompt.txt",
            ProductErrorCategory.SECURITY,
            details={"prompt": "private prompt body"},
        )

    deps["launch_builder"] = builder
    assert run(execute_args("status-execution"), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TEST_PRIVATE"
    assert "secret" not in output[-1]
    assert "prompt" not in output[-1]
    assert launch.closed == 0


def test_private_product_error_code_is_replaced_before_output():
    output = []
    bridge = FakeBridge()
    deps, _launch, _calls = dependencies(bridge, output)

    def builder(_config, **_kwargs):
        raise ProductError(
            r"ERR_C:\PRIVATE\SECRET",
            "private",
            ProductErrorCategory.SECURITY,
        )

    deps["launch_builder"] = builder
    assert run(execute_args("status-execution"), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_VERTICAL_REJECTED"
    assert "PRIVATE" not in output[-1]


def test_parser_rejects_mixed_or_extra_phase_arguments_before_runtime():
    parser = build_parser()
    with pytest.raises(ProductError) as mixed:
        parser.parse_args(execute_args() + ["--execution-id", EXECUTION_ID])
    assert mixed.value.code == "ERR_TASK036_NATIVE_ARGUMENT_SCHEMA"
    with pytest.raises(ProductError) as extra:
        parser.parse_args(adoption_args() + ["--queue-entry-id", QUEUE_ID])
    assert extra.value.code == "ERR_TASK036_NATIVE_ARGUMENT_SCHEMA"


def test_run_rejects_invalid_arguments_without_echoing_host_path():
    output = []
    assert run(
        ["execute", "--launch-config", r"C:\private\secret.json"],
        output_writer=output.append,
    ) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_ARGUMENT_SCHEMA"
    assert "private" not in output[-1].lower()


@pytest.mark.parametrize(
    "args",
    [
        execute_args() + ["--queue-entry-id", QUEUE_ID],
        ["execute", "--launch-c", r"C:\private\secret.json", *execute_args()[3:]],
    ],
)
def test_run_rejects_duplicate_and_abbreviated_options(args):
    output = []
    assert run(args, output_writer=output.append) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_ARGUMENT_SCHEMA"
    assert "private" not in output[-1].lower()


def test_eof_cancels_execution_without_dispatch():
    output = []
    bridge = FakeBridge()
    deps, _launch, _calls = dependencies(bridge, output)

    def eof():
        raise EOFError

    deps["input_reader"] = eof
    assert run(execute_args(), **deps) == 0
    assert json.loads(output[-1])["status"] == "CANCELLED"
    assert bridge.cancelled == ["private-execution-token"]
    assert "execution_apply" not in bridge.calls


def test_stdout_failure_after_completion_returns_nonzero_and_status_can_rediscover():
    bridge = FakeBridge()
    confirmation_output = []
    deps, launch, _calls = dependencies(bridge, confirmation_output)
    writes = 0

    def writer(value: str):
        nonlocal writes
        writes += 1
        if writes == 1:
            confirmation_output.append(value)
            return
        raise OSError("console closed")

    deps["output_writer"] = writer
    deps["input_reader"] = lambda: json.loads(confirmation_output[-1])["confirmation_phrase"]
    assert run(execute_args(), **deps) == 1
    assert bridge.execution_event["state"] == "COMPLETED"
    assert bridge.calls.count("execution_apply") == 1
    assert launch.closed == 1

    recovered = []
    deps["output_writer"] = recovered.append
    assert run(execute_args("status-execution"), **deps) == 0
    assert json.loads(recovered[-1])["status"] == "COMPLETED_REDISCOVERED"
    assert bridge.calls.count("execution_apply") == 1


def test_closed_writer_value_error_and_launch_close_failure_are_sanitized():
    bridge = FakeBridge()
    output = []
    deps, launch, _calls = dependencies(bridge, output)

    def close_failure():
        launch.closed += 1
        raise RuntimeError(r"C:\private\close")

    launch.close = close_failure
    assert run(execute_args("status-execution"), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_LAUNCH_CLOSE_FAILED"
    assert "private" not in output[-1].lower()

    deps["output_writer"] = lambda _value: (_ for _ in ()).throw(ValueError("closed"))
    assert run(execute_args("status-execution"), **deps) == 1


def test_provider_interrupt_returns_closed_error_and_leaves_recovery_to_product_shell():
    bridge = FakeBridge()
    output = []
    deps, launch, _calls = dependencies(bridge, output)
    deps["input_reader"] = lambda: json.loads(output[-1])["confirmation_phrase"]

    def interrupted(_args):
        raise KeyboardInterrupt

    bridge.generation_execution_apply = interrupted
    assert run(execute_args(), **deps) == 1
    result = json.loads(output[-1])
    assert result["error_code"] == "ERR_TASK036_NATIVE_OPERATION_INTERRUPTED"
    assert result["automatic_retry_allowed"] is False
    assert launch.closed == 1


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("scene_id", r"C:\private\scene"),
        ("slot_id", "../private-slot"),
        ("prompt_id", "x" * 201),
        ("runtime_policy", "policy\x00private"),
    ],
)
def test_execute_rejects_untrusted_public_identity_before_confirmation(field, bad_value):
    output = []
    bridge = FakeBridge()
    original_prepare = bridge.generation_execution_prepare
    original_preflight = bridge.generation_execution_preflight

    if field == "runtime_policy":
        def bad_preflight(args):
            value = original_preflight(args)
            value[field] = bad_value
            return value

        bridge.generation_execution_preflight = bad_preflight
    else:
        def bad_prepare(args):
            value = original_prepare(args)
            value[field] = bad_value
            return value

        bridge.generation_execution_prepare = bad_prepare
    deps, _launch, _calls = dependencies(bridge, output)

    assert run(execute_args(), **deps) == 1
    assert json.loads(output[-1])["status"] == "ERROR"
    serialized = "\n".join(output)
    assert bad_value not in serialized
    assert "HUMAN_CONFIRMATION_REQUIRED" not in serialized
    assert bridge.cancelled == ["private-execution-token"]
    assert "execution_apply" not in bridge.calls


def test_status_rejects_path_like_runtime_identity_without_leakage():
    output = []
    bridge = FakeBridge()
    original = bridge.generation_execution_preflight

    def bad_preflight(args):
        value = original(args)
        value["route_id"] = r"C:\private\route"
        return value

    bridge.generation_execution_preflight = bad_preflight
    deps, _launch, _calls = dependencies(bridge, output)
    assert run(execute_args("status-execution"), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_ROUTE_ID_INVALID"
    assert "private" not in output[-1].lower()


def test_adopt_rejects_path_like_candidate_identity_before_confirmation():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    original = bridge.generation_output_adoption_prepare

    def bad_prepare(args):
        value = original(args)
        value["candidate_id"] = r"C:\private\candidate"
        return value

    bridge.generation_output_adoption_prepare = bad_prepare
    deps, _launch, _calls = dependencies(bridge, output)
    assert run(adoption_args(), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_CANDIDATE_ID_INVALID"
    assert "private" not in output[-1].lower()
    assert "adoption_apply" not in bridge.calls


def test_adopt_rejects_result_candidate_identity_drift():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    original = bridge.generation_output_adoption_apply

    def drifted(args):
        value = original(args)
        value["latest_adoptions"][0]["candidate_id"] = "candidate-other"
        return value

    bridge.generation_output_adoption_apply = drifted
    deps, _launch, _calls = dependencies(bridge, output)
    deps["input_reader"] = lambda: json.loads(output[-1])["confirmation_phrase"]
    assert run(adoption_args(), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_ADOPTION_RESULT_INVALID"


def test_status_rejects_dot_segment_output_reference():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    bridge.execution_event["output_ref"] = "project-output://generated/../private.png"
    deps, _launch, _calls = dependencies(bridge, output)
    assert run(execute_args("status-execution"), **deps) == 1
    assert json.loads(output[-1])["error_code"] == "ERR_TASK036_NATIVE_OUTPUT_REF_INVALID"
    assert "private.png" not in output[-1]


def test_status_projects_unsupported_execution_recovery_truthfully():
    output = []
    bridge = FakeBridge(execution_state="DISPATCHING")
    original = bridge._execution

    def unsupported():
        value = original()
        value["recovery"]["dispatching"][0]["recovery_supported"] = False
        return value

    bridge._execution = unsupported
    deps, _launch, _calls = dependencies(bridge, output)
    assert run(execute_args("status-execution"), **deps) == 0
    result = json.loads(output[-1])
    assert result["status"] == "RECOVERY_UNSUPPORTED"
    assert result["use_product_shell_recovery"] is False


def test_status_projects_terminal_adoption_failure_without_recovery_action():
    output = []
    bridge = FakeBridge(execution_state="COMPLETED")
    original = bridge._adoption

    def failed():
        value = original()
        value["latest_adoptions"] = [{
            "adoption_id": "adoption-1",
            "execution_id": EXECUTION_ID,
            "queue_entry_id": QUEUE_ID,
            "slot_id": "slot-image",
            "candidate_id": "candidate-1",
            "asset_id": None,
            "output_sha256": H("o"),
            "state": "FAILED_KNOWN",
            "failure_code": "ERR_IMAGE_INVALID",
        }]
        value["eligible_completed_outputs"] = []
        return value

    bridge._adoption = failed
    deps, _launch, _calls = dependencies(bridge, output)
    assert run(adoption_args("status-adoption"), **deps) == 0
    result = json.loads(output[-1])
    assert result["status"] == "FAILED_KNOWN"
    assert result["use_product_shell_recovery"] is False


def test_actual_trusted_composition_executes_once_then_fresh_launch_adopts_without_replay(tmp_path: Path):
    """Close the CLI/launcher/Shell/port/store seam without a native provider."""
    import struct
    import zlib
    from decimal import Decimal

    from ai_video_production.ai_connections import (
        AiConnectionProfile, AiWorkload, CostClass, ModelRoute,
        ProviderFamily, SelectionMode,
    )
    from ai_video_production.connection_settings_store import ConnectionSettingsStore
    from ai_video_production.continuity_application import Task039ContinuityApplication
    from ai_video_production.generation_safety_application import Task013GenerationSafetyApplication
    from ai_video_production.planning_application import Task027PlanningApplication
    from ai_video_production.production_blueprint import (
        AssetSourceStrategy, BlueprintScene, CameraMotion, GenerationRisk,
        ProductionBlueprint,
    )
    from ai_video_production.production_proposal import (
        CreationIntent, ProductionProposalRegistry, ProductionProposalRevision,
        ProposalSection, ProviderPolicyBinding,
    )
    from ai_video_production.production_proposal_store import ProductionProposalSnapshotStore
    from ai_video_production.product_project import ProductProjectManifest, ProjectTimebase
    from ai_video_production.product_project_store import ProductProjectManifestStore
    from ai_video_production.prompt_evidence_application import Task040PromptEvidenceApplication
    from ai_video_production.generation_queue_application import Task027GenerationQueueApplication
    from ai_video_production.serialization import sha256_bytes
    from ai_video_production.store import SQLiteProductStore
    from ai_video_production.task036_trusted_launcher import build_trusted_launch
    from ai_video_production.timebase import FrameRate

    project = tmp_path / "project"
    incoming = tmp_path / "incoming"
    comfy_output = tmp_path / "comfy-output"
    project.mkdir(); incoming.mkdir(); comfy_output.mkdir()
    source = incoming / "source.mp4"; source.write_bytes(b"source")
    analysis = project / "analysis.wav"; analysis.write_bytes(b"wav")
    cache = project / "model-cache"; cache.mkdir()
    for relative in (
        "assets", "jobs", "transcription", "cut", "handoff", "native-render",
        "generation-output", "image-stage", "image-journal", "private/prompts/prompt-1",
    ):
        (project / relative).mkdir(parents=True)

    project_id = "project-1"
    job_id = "JOB-00000000000000000000000000"
    profile_snapshot_id = "PSN-00000000000000000000000000"
    config_path = project / "task036-launch.json"
    raw_config = {
        "launch_config_version": "1.2.0",
        "project": {"project_id": project_id, "display_name": "Native image vertical", "project_root": str(project)},
        "paths": {
            "source_roots": [str(incoming)], "asset_root": str(project / "assets"),
            "job_root": str(project / "jobs"), "database_path": str(project / "product.sqlite3"),
            "analysis_source_path": str(source), "analysis_audio_path": str(analysis),
            "asr_cache_directory": str(cache), "transcription_output": str(project / "transcription"),
            "cut_output": str(project / "cut"), "handoff_destination": str(project / "handoff"),
            "native_render_evidence_root": str(project / "native-render"),
            "native_render_report_path": str(project / "native-render-report.json"),
        },
        "ingest": {"production_job_id": job_id, "profile_snapshot_id": profile_snapshot_id, "owner": "owner"},
        "asr": {"model": "cached", "device": "cpu", "compute_type": "int8", "beam_size": 5,
                "vad_filter": True, "allow_model_download": False, "language": "ja"},
        "resolve": {"sandbox_project": "BAI_CAPABILITY_PROBE_TASK036_NATIVE_IMAGE", "timeline_rate": "30", "source_frame_rate": "30"},
        "local_generation": None,
        "local_image_generation": {
            "endpoint": "http://127.0.0.1:8188", "comfy_output_root": str(comfy_output),
            "project_output_root": str(project / "generation-output"),
            "staging_root": str(project / "image-stage"),
            "dispatch_journal_root": str(project / "image-journal"),
            "route_id": "local-image", "provider_id": "comfy-image", "model_id": "flux-schnell-fp8",
            "width": 64, "height": 64, "steps": 4, "poll_interval_seconds": 0.1,
            "completion_timeout_seconds": 2, "max_output_bytes": 1024 * 1024,
        },
    }
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")
    _configuration, config_sha = _load_config_scope(config_path)

    product_store = SQLiteProductStore(project / "product.sqlite3")
    product_store.create_job(profile_snapshot_id, job_id=job_id)
    route = ModelRoute(
        "local-image", AiWorkload.IMAGE, ProviderFamily.COMFYUI,
        "comfy-image", "flux-schnell-fp8", CostClass.LOCAL_FREE_AI,
        capabilities=("TEXT_TO_IMAGE",),
    )
    profile = AiConnectionProfile("profile-1", "v1", SelectionMode.AUTO, (route,))
    ConnectionSettingsStore.save(project / "ai-connection-settings.json", profile)

    proposals = ProductionProposalRegistry()
    intent = CreationIntent(
        "INTENT-IMAGE", 1, "Image scene", "Viewer", "Video", "16:9", Decimal("2"),
        "Calm", "Show one image", "ja-JP", budget_ceiling=Decimal("0"),
    )
    proposals.add_intent(intent)
    scene = BlueprintScene(
        "SC01", 0, 60, "Opening", AssetSourceStrategy.AI_GENERATED,
        GenerationRisk.A_LOW_TEXT, CameraMotion.STATIC, (),
    )
    blueprint = ProductionBlueprint("BP-IMAGE", "Image", FrameRate(30), 60, (), (scene,))
    proposals.add_proposal(ProductionProposalRevision(
        "PROPOSAL-IMAGE", 1, intent.to_dict()["intent_sha256"], blueprint,
        (ProposalSection("concept", "CONCEPT", "Concept", "One local image"),),
        ProviderPolicyBinding("profile-1", "v1", profile.to_dict()["profile_sha256"]),
        Decimal("0"), Decimal("0"), "JPY",
    ))
    ProductionProposalSnapshotStore.save(
        project / "production-proposal.json", proposals, project_id=project_id,
    )
    tokens = iter(("go-confirm", "install-confirm"))
    planning = Task027PlanningApplication(
        project_root=project, project_id=project_id, token_factory=lambda: next(tokens),
    )
    planning_state = planning.snapshot()
    go = planning.prepare_go(
        proposal_id="PROPOSAL-IMAGE", proposal_revision=1, reference_bindings=(),
        cost_ceiling="0", rights_warnings_acknowledged=False,
        expected_snapshot_sha256=planning_state["snapshot_sha256"],
    )
    approved = planning.approve_go(confirmation_id=go["confirmation_id"], approved_by="owner")
    planning_state = planning.snapshot()
    install = planning.prepare_install_plan(
        plan_id=approved["approved_plan"]["plan_id"],
        expected_proposal_snapshot_sha256=planning_state["snapshot_sha256"],
        expected_production_snapshot_sha256=planning_state["installation"]["production"]["snapshot_sha256"],
    )
    planning.apply_install_plan(confirmation_id=install["confirmation_id"])

    safety = Task013GenerationSafetyApplication(
        project_root=project, project_id=project_id, planning_application=planning,
        token_factory=lambda: "safety-confirm",
    )
    safety_state = safety.snapshot()
    human_checks = {name: "PASS" for name in (
        "subject_position_exists", "orientation_camera_compatible", "required_visible_coexists",
        "prohibited_change_not_required", "shot_reference_matches_final_camera", "task_axis_valid",
        "depth_order_valid", "occlusion_valid", "furniture_integrity_valid",
        "room_anchor_integrity_valid", "production_gear_absent", "character_identity_valid",
    )}
    feasibility = safety.prepare_feasibility(
        spec={
            "scene_id": "SC01", "continuity_type": "CUT", "character_required": True,
            "character_identity_profile_id": "CHAR-1", "character_reference_asset_ids": ["ASSET-CHAR"],
            "room_master_asset_id": "ASSET-ROOM", "room_shot_reference_asset_id": "ASSET-SHOT",
            "style_reference_asset_id": None, "required_visible": ["FACE"],
            "subject_orientation": "THREE_QUARTER", "camera_semantic": "DESK_FRONT",
            "start_frame_source": "NEW", "previous_end_asset_id": None, "previous_end_sha256": None,
            "start_asset_id": None, "start_asset_sha256": None, "prohibited_changes": ["MOVE_FURNITURE"],
        },
        human_reviewed_checks=human_checks, blocking_reasons=(),
        expected_planning_snapshot_sha256=safety_state["planning_snapshot_sha256"],
        expected_safety_snapshot_sha256=safety_state["safety_snapshot_sha256"],
    )
    safety.apply_feasibility(confirmation_id=feasibility["confirmation_id"], reviewed_by="owner")

    prompt_text = "cinematic blue room at dawn"
    prompt_raw = prompt_text.encode("utf-8")
    prompt_sha = sha256_bytes(prompt_raw)
    (project / "private/prompts/prompt-1/v1").write_bytes(prompt_raw)
    prompt_app = Task040PromptEvidenceApplication(
        project_root=project, project_id=project_id, token_factory=lambda: "prompt-confirm",
    )
    prompt_state = prompt_app.snapshot()
    prompt = prompt_app.prepare_prompt(
        prompt_id="prompt-1", prompt_version=1, purpose="scene image", scene_id="SC01",
        slot_id="slot:SC01:START_FRAME", body_ref="project-private://prompts/prompt-1/v1",
        body_sha256=prompt_sha, provider_profile_id="profile-1", provider_profile_version="v1",
        input_asset_hashes=(), keep_conditions=("keep composition",),
        expected_prompt_snapshot_sha256=prompt_state["prompt_snapshot_sha256"],
        expected_production_snapshot_sha256=prompt_state["production_snapshot_sha256"],
    )
    prompt_app.apply_prompt(confirmation_id=prompt["confirmation_id"])

    continuity = Task039ContinuityApplication(
        project_root=project, project_id=project_id,
        production_control=planning.production_control,
    )
    queue = Task027GenerationQueueApplication(
        project_root=project, project_id=project_id,
        production_control=planning.production_control,
        planning_application=planning,
        generation_safety_application=safety,
        continuity_application=continuity,
        prompt_evidence_application=prompt_app,
        token_factory=lambda: "queue-confirm",
    )
    queue_state = queue.snapshot()
    assert queue_state["upstream_snapshots"] is not None
    queued = queue.prepare_enqueue(
        prompt_id="prompt-1", prompt_version=1,
        expected_queue_snapshot_sha256=queue_state["queue_snapshot_sha256"],
        expected_upstream_snapshots=queue_state["upstream_snapshots"],
    )
    queue_state = queue.apply_enqueue(confirmation_id=queued["confirmation_id"])
    queue_entry_id = queue_state["entries"][0]["queue_entry_id"]

    manifest = ProductProjectManifest.create(
        project_id=project_id, project_revision=1, product_version="0.22.0",
        timebase=ProjectTimebase(30, 1), child_bindings=(),
        created_at="2026-08-21T00:00:00.000Z", updated_at="2026-08-21T00:00:00.000Z",
    )
    ProductProjectManifestStore.save(project, manifest)

    def png_bytes() -> bytes:
        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        ihdr = struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)
        rows = b"".join(b"\x00" + b"\x20\x40\x80" * 64 for _ in range(64))
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")

    class FakeComfy:
        endpoint = "http://127.0.0.1:8188"
        def __init__(self): self.queued = 0; self.prefix = None
        def object_info(self):
            result = {name: {"input": {"required": {}, "optional": {}}} for name in (
                "CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage",
            )}
            result["CheckpointLoaderSimple"]["input"]["required"] = {"ckpt_name": [["flux1-schnell-fp8.safetensors"]]}
            return result
        def system_stats(self):
            return {"system": {"ram_free": 64 * 1024**3, "argv": [
                "main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-auto-launch",
                "--disable-metadata", "--output-directory", str(comfy_output),
            ]}, "devices": [{"name": "cuda", "type": "cuda", "vram_free": 16 * 1024**3}]}
        def queue(self, workflow, *, client_id):
            self.queued += 1
            self.prefix = next(
                node["inputs"]["filename_prefix"] for node in workflow.values()
                if "filename_prefix" in node.get("inputs", {})
            )
            return "prompt-image-1"
        def history(self, prompt_id):
            prefix = Path(self.prefix)
            target = comfy_output / prefix.parent / "result-0.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(png_bytes())
            return {prompt_id: {"status": {"status_str": "success"}, "outputs": {"7": {"images": [{
                "filename": target.name, "subfolder": prefix.parent.as_posix(), "type": "output",
            }]}}}}

    client = FakeComfy()
    launches = []
    def launch_builder(configuration, **kwargs):
        launch = build_trusted_launch(configuration, comfy_client=client, **kwargs)
        launches.append(launch)
        return launch

    execute_output: list[str] = []
    execute_args_actual = [
        "execute", "--launch-config", str(config_path),
        "--expected-launch-config-sha256", config_sha,
        "--expected-project-id", project_id,
        "--expected-manifest-sha256", manifest.project_manifest_sha256,
        "--queue-entry-id", queue_entry_id,
    ]
    assert run(
        execute_args_actual,
        input_reader=lambda: json.loads(execute_output[-1])["confirmation_phrase"],
        output_writer=execute_output.append,
        launch_builder=launch_builder,
    ) == 0
    completed = json.loads(execute_output[-1])
    assert completed["status"] == "COMPLETED"
    assert client.queued == 1
    assert launches[-1]._runtime_lease is None
    assert launches[-1]._product_store is None

    adopt_output: list[str] = []
    adopt_args_actual = [
        "adopt", "--launch-config", str(config_path),
        "--expected-launch-config-sha256", config_sha,
        "--expected-project-id", project_id,
        "--expected-manifest-sha256", manifest.project_manifest_sha256,
        "--execution-id", completed["execution_id"],
        "--expected-output-sha256", completed["output_sha256"],
    ]
    assert run(
        adopt_args_actual,
        input_reader=lambda: json.loads(adopt_output[-1])["confirmation_phrase"],
        output_writer=adopt_output.append,
        launch_builder=launch_builder,
    ) == 0
    adopted = json.loads(adopt_output[-1])
    assert adopted["status"] == "READY_FOR_AUDIT"
    assert adopted["candidate_lifecycle"] == "READY_FOR_AUDIT"
    assert adopted["candidate_accepted"] is False
    assert adopted["candidate_locked"] is False
    assert adopted["publication_authorized"] is False
    assert client.queued == 1
    assert launches[-1]._runtime_lease is None
    assert launches[-1]._product_store is None
